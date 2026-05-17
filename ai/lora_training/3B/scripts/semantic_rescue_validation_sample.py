#!/usr/bin/env python
"""Classify validation parse failures as likely content failures or format-only failures."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def sentence_count(text: str) -> int:
    return len([part for part in re.split(r"[.!?。！？]+", text) if part.strip()])


def classify_raw(raw: str) -> dict[str, Any]:
    lowered = raw.lower()
    list_markers = len(re.findall(r"(^|\n)\s*(?:[-*]|\d+[.)])\s+", raw))
    has_json_substring = bool(re.search(r"\{.*\}", raw, flags=re.S))
    has_summary_terms = any(term in lowered for term in ["main_idea", "main idea", "summary", "key_points", "key points"])
    has_refusal_or_meta = any(term in lowered for term in ["i cannot", "i can't", "as an ai", "i am unable", "cannot summarize"])
    sents = sentence_count(raw)
    chars = len(raw.strip())
    if chars < 40:
        label = "not_readable_or_empty"
    elif has_refusal_or_meta:
        label = "refusal_or_meta"
    elif has_json_substring or has_summary_terms or (list_markers >= 3 and sents >= 2):
        label = "likely_format_only_failure"
    elif sents >= 2 and chars >= 120:
        label = "ambiguous_but_readable"
    else:
        label = "likely_content_failure"
    return {
        "semantic_rescue_label": label,
        "char_count": chars,
        "sentence_count": sents,
        "list_marker_count": list_markers,
        "has_json_substring": has_json_substring,
        "has_summary_terms": has_summary_terms,
        "has_refusal_or_meta": has_refusal_or_meta,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Create semantic-rescue samples for parse failures.")
    parser.add_argument("--candidate-key", required=True)
    parser.add_argument("--train-run-id", required=True)
    parser.add_argument("--epochs", nargs="+", type=int, required=True)
    parser.add_argument("--prompt-mode", default="record_messages")
    parser.add_argument("--sample-size", type=int, default=10)
    args = parser.parse_args()

    workspace = ROOT / "model_workspaces" / args.candidate_key
    rows: list[dict[str, Any]] = []
    epoch_summaries: list[dict[str, Any]] = []
    for epoch in args.epochs:
        validation_id = f"{args.train_run_id}_epoch_{epoch}_{args.prompt_mode}"
        validation_dir = workspace / "outputs" / "validation" / validation_id
        failures = read_jsonl(validation_dir / "parse_failures.jsonl")
        classified = []
        for failure in failures:
            rescue = classify_raw(str(failure.get("raw_output", "")))
            classified.append(
                {
                    "candidate_key": args.candidate_key,
                    "train_run_id": args.train_run_id,
                    "validation_id": validation_id,
                    "epoch": epoch,
                    "index": failure.get("index"),
                    "record_id": failure.get("record_id"),
                    "parse_error": failure.get("parse_error"),
                    "raw_output": failure.get("raw_output"),
                    **rescue,
                }
            )
        sample = classified[: args.sample_size]
        rows.extend(sample)
        counts = Counter(row["semantic_rescue_label"] for row in classified)
        epoch_summaries.append(
            {
                "epoch": epoch,
                "validation_id": validation_id,
                "parse_failure_count": len(failures),
                "sampled_count": len(sample),
                "semantic_rescue_label_counts": dict(sorted(counts.items())),
            }
        )

    out_dir = workspace / "outputs" / "validation" / f"{args.train_run_id}_{args.prompt_mode}_semantic_rescue"
    write_jsonl(out_dir / "semantic_rescue_sample.jsonl", rows)
    write_json(
        out_dir / "semantic_rescue_summary.json",
        {
            "created_at_utc": utc_now(),
            "candidate_key": args.candidate_key,
            "train_run_id": args.train_run_id,
            "prompt_mode": args.prompt_mode,
            "sample_size_per_epoch": args.sample_size,
            "classification_policy": "deterministic heuristic to separate likely format-only failures from likely content failures; it is not a replacement for judge scoring.",
            "epoch_summaries": epoch_summaries,
            "sample_path": str(out_dir / "semantic_rescue_sample.jsonl"),
        },
    )
    print(json.dumps({"status": "completed", "out_dir": str(out_dir), "rows": len(rows)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
