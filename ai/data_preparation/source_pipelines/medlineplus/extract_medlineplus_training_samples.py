#!/usr/bin/env python3
"""
Extract a stratified random sample of English MedlinePlus topic summaries for downstream LLM use.

Each record is ONE <full-summary> from ONE <health-topic language="English"> — never concatenated.

Word-count buckets (non-overlapping, by whitespace token count after HTML stripping):
  - short:  250 <= n <= 499   (target 20% of 250 = 50)
  - medium: 500 <= n <= 800 (target 70% of 250 = 175)
  - long:   801 <= n <= 1200 (target 10% of 250 = 25)

Output: UTF-8 JSON Lines (.jsonl), one JSON object per line — common for training pipelines and agents.

Usage:
  py extract_medlineplus_training_samples.py
  py extract_medlineplus_training_samples.py --xml-path "..." --output "..." --seed 42
"""

from __future__ import annotations

import argparse
import html
import json
import random
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def strip_html_to_plain(raw: str) -> str:
    if not raw:
        return ""
    text = html.unescape(raw)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def word_count(text: str) -> int:
    return len(text.split()) if text else 0


@dataclass
class TopicRow:
    topic_id: str
    title: str
    url: str
    plain_text: str
    words: int


def iter_english_topics(xml_path: Path) -> list[TopicRow]:
    rows: list[TopicRow] = []
    context = ET.iterparse(str(xml_path), events=("end",))
    for _event, elem in context:
        if elem.tag != "health-topic":
            continue
        if elem.get("language", "") != "English":
            elem.clear()
            continue
        fs = elem.find("full-summary")
        if fs is None or not (fs.text or "").strip():
            elem.clear()
            continue
        plain = strip_html_to_plain(fs.text or "")
        wc = word_count(plain)
        if wc < 250:
            elem.clear()
            continue
        rows.append(
            TopicRow(
                topic_id=str(elem.get("id", "")),
                title=(elem.get("title") or "").strip(),
                url=(elem.get("url") or "").strip(),
                plain_text=plain,
                words=wc,
            )
        )
        elem.clear()
    return rows


def classify_bucket(w: int) -> str | None:
    if 250 <= w <= 499:
        return "short"
    if 500 <= w <= 800:
        return "medium"
    if 801 <= w <= 1200:
        return "long"
    return None


def stratified_sample(
    rows: list[TopicRow],
    n_short: int,
    n_medium: int,
    n_long: int,
    seed: int,
) -> tuple[list[TopicRow], dict[str, Any]]:
    buckets: dict[str, list[TopicRow]] = {"short": [], "medium": [], "long": []}
    skipped: list[int] = []
    for r in rows:
        b = classify_bucket(r.words)
        if b:
            buckets[b].append(r)
        else:
            skipped.append(r.words)

    rng = random.Random(seed)
    report: dict[str, Any] = {
        "available": {k: len(v) for k, v in buckets.items()},
        "requested": {"short": n_short, "medium": n_medium, "long": n_long},
        "skipped_out_of_range_word_counts": len(skipped),
    }

    def take(bucket: str, n: int) -> list[TopicRow]:
        pool = buckets[bucket]
        if len(pool) < n:
            raise ValueError(
                f"Not enough items in bucket '{bucket}': need {n}, have {len(pool)}. "
                "Relax quotas or use a different source."
            )
        return rng.sample(pool, n)

    chosen = take("short", n_short) + take("medium", n_medium) + take("long", n_long)
    rng.shuffle(chosen)
    return chosen, report


def row_to_record(idx: int, r: TopicRow) -> dict[str, Any]:
    b = classify_bucket(r.words)
    return {
        "sample_index": idx,
        "bucket": b,
        "word_count": r.words,
        "medlineplus_topic_id": r.topic_id,
        "title": r.title,
        "source_url": r.url,
        "source_field": "full-summary",
        "source_dataset": "MedlinePlus health-topics XML",
        "text": r.plain_text,
    }


def main() -> int:
    default_xml = (
        Path(__file__).resolve().parent.parent
        / "data"
        / "mplus_topics_compressed_2026-04-11"
        / "mplus_topics_2026-04-11.xml"
    )
    default_out = (
        Path(__file__).resolve().parent.parent
        / "data"
        / "medlineplus_250_english_samples.jsonl"
    )

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--xml-path", type=Path, default=default_xml, help="Path to mplus_topics_*.xml")
    p.add_argument("--output", type=Path, default=default_out, help="Output .jsonl path")
    p.add_argument("--seed", type=int, default=42, help="RNG seed for reproducibility")
    p.add_argument(
        "--n-total",
        type=int,
        default=250,
        help="Total samples (default 250 → 50 short / 175 medium / 25 long)",
    )
    args = p.parse_args()

    n_total = args.n_total
    if n_total <= 0 or n_total % 10 != 0:
        print("n-total should be positive; for default ratios use a multiple of 10.", file=sys.stderr)
        return 2

    n_short = n_total * 20 // 100
    n_medium = n_total * 70 // 100
    n_long = n_total * 10 // 100
    if n_short + n_medium + n_long != n_total:
        n_medium += n_total - (n_short + n_medium + n_long)

    xml_path: Path = args.xml_path
    if not xml_path.is_file():
        print(f"XML not found: {xml_path}", file=sys.stderr)
        return 1

    print(f"Parsing {xml_path} ...")
    rows = iter_english_topics(xml_path)
    print(f"English topics with full-summary and 250+ words: {len(rows)}")

    try:
        chosen, report = stratified_sample(rows, n_short, n_medium, n_long, args.seed)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as f:
        for i, row in enumerate(chosen, start=1):
            rec = row_to_record(i, row)
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    meta_path = args.output.with_suffix(".meta.json")
    meta = {
        "xml_file": str(xml_path.resolve()),
        "output_file": str(args.output.resolve()),
        "seed": args.seed,
        "totals": {"short": n_short, "medium": n_medium, "long": n_long, "total": n_total},
        "bucket_word_ranges": {
            "short": "250–499 inclusive",
            "medium": "500–800 inclusive",
            "long": "801–1200 inclusive",
        },
        "sampling_report": report,
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote {len(chosen)} records to {args.output}")
    print(f"Wrote run metadata to {meta_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
