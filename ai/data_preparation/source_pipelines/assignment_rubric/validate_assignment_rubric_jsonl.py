#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


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


def parse_bucket_counts(value: str | None) -> dict[str, int] | None:
    if not value:
        return None
    result: dict[str, int] = {}
    for part in value.split(","):
        name, raw_count = part.split("=", 1)
        result[name.strip()] = int(raw_count.strip())
    return result


def validate_samples(path: Path, expected_total: int, expected_buckets: dict[str, int] | None) -> None:
    rows = load_jsonl(path)
    if len(rows) != expected_total:
        raise ValueError(f"{path} has {len(rows)} rows, expected {expected_total}.")

    bucket_counts = Counter()
    tier_counts = Counter()
    min_wc = None
    max_wc = None
    seen_row_indexes: set[int] = set()

    for idx, row in enumerate(rows, start=1):
        if row.get("sample_index") != idx:
            raise ValueError(f"Sample index mismatch at row {idx}: {row.get('sample_index')}")

        bucket = row.get("bucket")
        wc = int(row.get("word_count", 0))
        text = str(row.get("text") or "")
        source_row_index = int(row.get("source_row_index", 0))
        tier = int(row.get("quality_tier", -1))

        if bucket not in {"short", "medium", "long"}:
            raise ValueError(f"Row {idx} has unexpected bucket: {bucket}")
        if not text.strip():
            raise ValueError(f"Row {idx} has empty text.")
        if not str(row.get("task_title") or "").strip():
            raise ValueError(f"Row {idx} has empty task_title.")
        if source_row_index <= 0:
            raise ValueError(f"Row {idx} has invalid source_row_index.")
        if source_row_index in seen_row_indexes:
            raise ValueError(f"Duplicate source_row_index found: {source_row_index}")

        actual_wc = len(text.split())
        if actual_wc != wc:
            raise ValueError(f"Row {idx} word_count mismatch: stored={wc}, actual={actual_wc}")
        if bucket == "short" and not (250 <= wc <= 499):
            raise ValueError(f"Row {idx} short bucket out of range: {wc}")
        if bucket == "medium" and not (500 <= wc <= 800):
            raise ValueError(f"Row {idx} medium bucket out of range: {wc}")
        if bucket == "long" and not (801 <= wc <= 1200):
            raise ValueError(f"Row {idx} long bucket out of range: {wc}")
        if "Assignment Brief:" not in text or "Scoring Rubric:" not in text:
            raise ValueError(f"Row {idx} is missing expected section headers.")

        bucket_counts[bucket] += 1
        tier_counts[f"tier_{tier}"] += 1
        seen_row_indexes.add(source_row_index)
        min_wc = wc if min_wc is None else min(min_wc, wc)
        max_wc = wc if max_wc is None else max(max_wc, wc)

    if expected_buckets and dict(bucket_counts) != expected_buckets:
        raise ValueError(f"Bucket counts mismatch: {dict(bucket_counts)}")

    print(f"{path}: OK")
    print(f"rows={len(rows)}")
    print(f"bucket_counts={dict(bucket_counts)}")
    print(f"quality_tiers={dict(tier_counts)}")
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
    parser = argparse.ArgumentParser(description="Validate assignment_rubric sample and SFT JSONL files.")
    parser.add_argument("--samples", type=Path)
    parser.add_argument("--sft", type=Path)
    parser.add_argument("--expected-total", type=int, default=150)
    parser.add_argument(
        "--expected-buckets",
        type=str,
        default="",
        help="Optional comma-separated bucket counts, e.g. short=25,medium=110,long=15",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.samples and not args.sft:
        print("Provide at least one of --samples or --sft.", file=sys.stderr)
        return 2

    expected_buckets = parse_bucket_counts(args.expected_buckets)
    if args.samples:
        validate_samples(args.samples, args.expected_total, expected_buckets)
    if args.sft:
        validate_sft(args.sft, args.expected_total)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
