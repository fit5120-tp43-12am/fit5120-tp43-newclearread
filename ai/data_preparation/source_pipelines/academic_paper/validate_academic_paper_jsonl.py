#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


EXPECTED_DOMAIN_COUNTS = {
    "cse": 125,
    "bfe": 125,
    "ssh": 125,
    "lsph": 125,
}

EXPECTED_BUCKET_COUNTS = {
    "short": 100,
    "medium": 350,
    "long": 50,
}

REJECT_TITLE_PATTERNS = [
    re.compile(r"\bcomment\b", re.IGNORECASE),
    re.compile(r"\breply\b", re.IGNORECASE),
    re.compile(r"\bresponse\b", re.IGNORECASE),
    re.compile(r"\bletter to the editor\b", re.IGNORECASE),
    re.compile(r"\bshort communication\b", re.IGNORECASE),
    re.compile(r"\beditorial\b", re.IGNORECASE),
    re.compile(r"\bcorrigendum\b", re.IGNORECASE),
    re.compile(r"\berratum\b", re.IGNORECASE),
    re.compile(r"\bretraction\b", re.IGNORECASE),
    re.compile(r"\bexpression of concern\b", re.IGNORECASE),
]

REJECT_EXCERPT_PATTERNS = [
    re.compile(r"(?im)^references\b"),
    re.compile(r"(?im)^acknowledg"),
]

SUSPICIOUS_TOKEN_PATTERN = re.compile(r"\b([A-Za-z]\d{5,})\b")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_no} of {path}: {exc}") from exc
    return rows


def validate_samples(path: Path, expected_total: int) -> None:
    rows = load_jsonl(path)
    if len(rows) != expected_total:
        raise ValueError(f"{path} has {len(rows)} rows, expected {expected_total}.")

    domain_counts = Counter()
    bucket_counts = Counter()
    seen_paper_ids: set[str] = set()
    min_wc = None
    max_wc = None

    for idx, row in enumerate(rows, start=1):
        if row.get("sample_index") != idx:
            raise ValueError(f"Sample index mismatch at row {idx}: {row.get('sample_index')}")
        if row.get("source_scope") != "single_article_excerpt":
            raise ValueError(f"Row {idx} is not marked as single_article_excerpt.")

        domain_key = row.get("domain_key")
        bucket = row.get("bucket")
        wc = int(row.get("word_count", 0))
        text = str(row.get("text") or "")
        paper_id = str(row.get("paper_id") or "").strip()
        title = str(row.get("title") or "").strip()

        if domain_key not in EXPECTED_DOMAIN_COUNTS:
            raise ValueError(f"Row {idx} has unexpected domain_key: {domain_key}")
        if bucket not in EXPECTED_BUCKET_COUNTS:
            raise ValueError(f"Row {idx} has unexpected bucket: {bucket}")
        if not paper_id:
            raise ValueError(f"Row {idx} missing paper_id.")
        if paper_id in seen_paper_ids:
            raise ValueError(f"Duplicate paper_id found: {paper_id}")
        if not text.strip():
            raise ValueError(f"Row {idx} has empty text.")
        if not title:
            raise ValueError(f"Row {idx} has empty title.")
        if any(pattern.search(title) for pattern in REJECT_TITLE_PATTERNS):
            raise ValueError(f"Row {idx} has rejected title pattern: {title}")

        actual_wc = len(text.split())
        if actual_wc != wc:
            raise ValueError(f"Row {idx} word_count mismatch: stored={wc}, actual={actual_wc}")

        if bucket == "short" and not (250 <= wc <= 499):
            raise ValueError(f"Row {idx} short bucket out of range: {wc}")
        if bucket == "medium" and not (500 <= wc <= 800):
            raise ValueError(f"Row {idx} medium bucket out of range: {wc}")
        if bucket == "long" and not (801 <= wc <= 1200):
            raise ValueError(f"Row {idx} long bucket out of range: {wc}")
        if text.lower().count("http") >= 2:
            raise ValueError(f"Row {idx} contains too many URLs.")
        if any(pattern.search(text) for pattern in REJECT_EXCERPT_PATTERNS):
            raise ValueError(f"Row {idx} contains a rejected excerpt section marker.")
        suspicious_counts = Counter(SUSPICIOUS_TOKEN_PATTERN.findall(text))
        if any(count >= 3 for count in suspicious_counts.values()):
            raise ValueError(f"Row {idx} contains repeated suspicious OCR-like tokens.")

        domain_counts[domain_key] += 1
        bucket_counts[bucket] += 1
        seen_paper_ids.add(paper_id)
        min_wc = wc if min_wc is None else min(min_wc, wc)
        max_wc = wc if max_wc is None else max(max_wc, wc)

    # Preserve the original strict quota check for the canonical 500-row dataset,
    # but allow structurally valid reviewed subsets to be validated with a smaller
    # expected total without forcing the 125/125/125/125 and 100/350/50 targets.
    if expected_total == 500:
        if dict(domain_counts) != EXPECTED_DOMAIN_COUNTS:
            raise ValueError(f"Domain counts mismatch: {dict(domain_counts)}")
        if dict(bucket_counts) != EXPECTED_BUCKET_COUNTS:
            raise ValueError(f"Bucket counts mismatch: {dict(bucket_counts)}")

    print(f"{path}: OK")
    print(f"rows={len(rows)}")
    print(f"domain_counts={dict(domain_counts)}")
    print(f"bucket_counts={dict(bucket_counts)}")
    print(f"word_count_range=({min_wc}, {max_wc})")


def validate_sft(path: Path, expected_total: int) -> None:
    rows = load_jsonl(path)
    if len(rows) != expected_total:
        raise ValueError(f"{path} has {len(rows)} rows, expected {expected_total}.")

    for idx, row in enumerate(rows, start=1):
        messages = row.get("messages")
        if not isinstance(messages, list) or len(messages) != 3:
            raise ValueError(f"Row {idx} must contain exactly 3 messages.")

        roles = [msg.get("role") for msg in messages]
        if roles != ["system", "user", "assistant"]:
            raise ValueError(f"Row {idx} has unexpected roles: {roles}")

        assistant_content = messages[2].get("content")
        if not isinstance(assistant_content, str) or not assistant_content.strip():
            raise ValueError(f"Row {idx} assistant content is empty.")

        try:
            parsed = json.loads(assistant_content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Row {idx} assistant content is not valid JSON: {exc}") from exc

        if set(parsed.keys()) != {"main_idea", "key_points"}:
            raise ValueError(f"Row {idx} assistant JSON has unexpected keys: {sorted(parsed.keys())}")
        if not isinstance(parsed["main_idea"], str) or not parsed["main_idea"].strip():
            raise ValueError(f"Row {idx} main_idea must be a non-empty string.")
        if not isinstance(parsed["key_points"], list) or len(parsed["key_points"]) != 3:
            raise ValueError(f"Row {idx} key_points must be a list of exactly 3 items.")
        if not all(isinstance(point, str) and point.strip() for point in parsed["key_points"]):
            raise ValueError(f"Row {idx} key_points must contain non-empty strings.")

    print(f"{path}: OK")
    print(f"rows={len(rows)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate academic-paper sample and SFT JSONL files.")
    parser.add_argument("--samples", type=Path)
    parser.add_argument("--sft", type=Path)
    parser.add_argument("--expected-total", type=int, default=500)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.samples and not args.sft:
        print("Provide at least one of --samples or --sft.", file=sys.stderr)
        return 2
    if args.samples:
        validate_samples(args.samples, args.expected_total)
    if args.sft:
        validate_sft(args.sft, args.expected_total)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
