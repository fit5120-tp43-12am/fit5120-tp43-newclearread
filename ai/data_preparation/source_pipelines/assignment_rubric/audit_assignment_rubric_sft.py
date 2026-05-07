#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from pathlib import Path


HERE = Path(__file__).resolve().parent
DEFAULT_SAMPLES = HERE / "assignment_rubric_cleaned_samples.jsonl"
DEFAULT_OUTPUTS = HERE / "assignment_rubric_cleaned_outputs.jsonl"
DEFAULT_SFT = HERE / "assignment_rubric_cleaned_sft.jsonl"

HEDGE_TERMS = (
    "may",
    "might",
    "could",
    "possibly",
    "likely",
    "perhaps",
)

BAD_MARKERS = (
    "figure ",
    "table ",
    "section ",
    "as shown",
    "according to the chart",
    "i cannot",
    "i can help",
    "let me know",
)


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def word_count(text: str) -> int:
    return len([part for part in text.split() if part])


def preview(text: str, limit: int = 220) -> str:
    collapsed = " ".join(text.split())
    return collapsed[:limit] + ("..." if len(collapsed) > limit else "")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Heuristic audit for assignment_rubric SFT files.")
    parser.add_argument("--samples", type=Path, default=DEFAULT_SAMPLES)
    parser.add_argument("--outputs", type=Path, default=DEFAULT_OUTPUTS)
    parser.add_argument("--sft", type=Path, default=DEFAULT_SFT)
    parser.add_argument("--expected-total", type=int, default=150)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    samples = load_jsonl(args.samples)
    outputs = load_jsonl(args.outputs)
    sft_rows = load_jsonl(args.sft)

    if not (len(samples) == len(outputs) == len(sft_rows) == args.expected_total):
        raise SystemExit(
            "Count mismatch: "
            f"samples={len(samples)} outputs={len(outputs)} sft={len(sft_rows)} expected={args.expected_total}"
        )

    sample_by_idx = {int(row["sample_index"]): row for row in samples}
    output_by_idx = {int(row["sample_index"]): row for row in outputs}

    bucket_counts = Counter()
    main_idea_counts = []
    key_point_counts = []
    hedge_rows = []
    bad_marker_rows = []
    duplicate_assistant = Counter()

    for idx, row in enumerate(sft_rows, start=1):
        messages = row["messages"]
        if [msg["role"] for msg in messages] != ["system", "user", "assistant"]:
            raise SystemExit(f"Bad role order in SFT row {idx}")

        sample = sample_by_idx[idx]
        output = output_by_idx[idx]
        assistant = json.loads(messages[2]["content"])

        if messages[1]["content"] != sample["text"]:
            raise SystemExit(f"User content mismatch at row {idx}")
        if assistant != output["target"]:
            raise SystemExit(f"Assistant content mismatch at row {idx}")

        bucket_counts[sample["bucket"]] += 1
        main_idea = assistant["main_idea"].strip()
        key_points = assistant["key_points"]
        main_idea_counts.append(word_count(main_idea))
        key_point_counts.extend(word_count(point.strip()) for point in key_points)
        duplicate_assistant[messages[2]["content"]] += 1

        lower = (main_idea + " " + " ".join(key_points)).lower()
        if any(f" {term} " in f" {lower} " for term in HEDGE_TERMS):
            hedge_rows.append((idx, sample["task_title"], preview(main_idea)))
        if any(marker in lower for marker in BAD_MARKERS):
            bad_marker_rows.append((idx, sample["task_title"], preview(lower)))

    print("SFT audit summary")
    print(f"rows={len(sft_rows)}")
    print(f"bucket_counts={dict(bucket_counts)}")
    print(
        "main_idea_words="
        f"(min={min(main_idea_counts)}, median={statistics.median(main_idea_counts)}, max={max(main_idea_counts)})"
    )
    print(
        "key_point_words="
        f"(min={min(key_point_counts)}, median={statistics.median(key_point_counts)}, max={max(key_point_counts)})"
    )
    print(f"duplicate_assistant_rows={sum(1 for count in duplicate_assistant.values() if count > 1)}")
    print(f"hedge_rows={len(hedge_rows)}")
    print(f"bad_marker_rows={len(bad_marker_rows)}")

    if bad_marker_rows:
        print("bad_marker_examples=")
        for row in bad_marker_rows[:10]:
            print(json.dumps(row, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
