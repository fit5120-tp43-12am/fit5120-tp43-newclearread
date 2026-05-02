#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


HERE = Path(__file__).resolve().parent
DEFAULT_DATA_PATH = HERE / "assignment_rubric_150_samples.jsonl"

RISK_PATTERN = re.compile(
    r"\b("
    r"translate|translation|bilingual|nodejs|react|frontend|marketing|sales|"
    r"website|blog|newsletter|story|poem|song|screenplay|syllabus|lesson plan|"
    r"medical report|doctor|patient|resume|cover letter|personal statement|"
    r"prompt injection|start and end your response|first word of your response|"
    r"answerable question based on the context|template\b|thesis statement\b"
    r")\b",
    re.IGNORECASE,
)

MOJIBAKE_PATTERN = re.compile(r"(?:Ã.|Â.|â[\x80-\xbf]?|鈥|鈧|锟|�|憁|€|™|œ|ž)")


def load_rows(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            rows.append(json.loads(line))
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Heuristic audit for assignment_rubric samples.")
    parser.add_argument("--samples", type=Path, default=DEFAULT_DATA_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = load_rows(args.samples)
    bucket_counts = Counter()
    source_counts = Counter()
    risk_rows = []
    bucket_samples: dict[str, list[tuple[int, str, int]]] = defaultdict(list)

    for idx, row in enumerate(rows, start=1):
        text = row["text"]
        title = row["task_title"]
        bucket = row["bucket"]
        wc = row["word_count"]

        bucket_counts[bucket] += 1
        source_counts[row["source_dataset_file"]] += 1
        if MOJIBAKE_PATTERN.search(text):
            raise SystemExit(f"Found mojibake in row {idx}: {title}")
        if re.search(r"[\u4e00-\u9fff]", text):
            raise SystemExit(f"Found CJK text in row {idx}: {title}")
        match = RISK_PATTERN.search(text)
        if match:
            risk_rows.append((idx, title, match.group(0)))
        if len(bucket_samples[bucket]) < 8:
            bucket_samples[bucket].append((idx, title, wc))

    print("rows=", len(rows))
    print("bucket_counts=", dict(bucket_counts))
    print("source_counts=", dict(source_counts))
    print("risk_row_count=", len(risk_rows))
    if risk_rows:
        print("risk_rows=", risk_rows[:20])
    print("sample_titles=")
    for bucket in ("short", "medium", "long"):
        print(bucket, bucket_samples[bucket])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
