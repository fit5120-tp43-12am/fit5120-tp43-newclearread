#!/usr/bin/env python3
"""
Assemble a repaired/reviewed public-service sample file by replacing rows that
failed manual content review with manually approved rows from the stricter pool.

Outputs:
  - public_service_200_samples_reviewed.jsonl
  - public_service_200_outputs_reviewed.jsonl   (seeded with reusable good rows)
  - public_service_200_review_map.json
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


FAIL_INDICES = [
    1,
    2,
    8,
    10,
    26,
    36,
    40,
    43,
    48,
    50,
    57,
    58,
    68,
    72,
    75,
    80,
    82,
    83,
    86,
    88,
    89,
    94,
    96,
    97,
    102,
    109,
    110,
    121,
    123,
    129,
    134,
    137,
    145,
    147,
    152,
    153,
    156,
    158,
    171,
    172,
    173,
    177,
    180,
    188,
    189,
    196,
    197,
    200,
]

SHORT_REPLACEMENTS = [3, 5, 6, 19, 26, 35, 52, 56, 85, 103, 135]
MEDIUM_REPLACEMENTS = [
    2,
    7,
    13,
    15,
    16,
    17,
    27,
    28,
    31,
    34,
    42,
    43,
    44,
    48,
    49,
    60,
    63,
    64,
    73,
    77,
    78,
    86,
    92,
    104,
    105,
    109,
    123,
    132,
    133,
    148,
    154,
    191,
]
LONG_REPLACEMENTS = [18, 25, 53, 138, 198]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def norm_title(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"\s+", " ", s).strip()
    return s


def main() -> int:
    base = Path(__file__).resolve().parent
    orig_samples_path = base / "public_service_200_samples.jsonl"
    strict_samples_path = base / "public_service_200_samples_strict.jsonl"
    orig_outputs_path = base / "public_service_200_outputs.jsonl"

    out_samples_path = base / "public_service_200_samples_reviewed.jsonl"
    out_outputs_path = base / "public_service_200_outputs_reviewed.jsonl"
    out_map_path = base / "public_service_200_review_map.json"

    orig_samples = load_jsonl(orig_samples_path)
    strict_samples = load_jsonl(strict_samples_path)
    orig_outputs = load_jsonl(orig_outputs_path)

    if len(orig_samples) != 200 or len(orig_outputs) != 200 or len(strict_samples) != 200:
        raise ValueError("Expected all three source JSONL files to contain exactly 200 rows.")

    fail_set = set(FAIL_INDICES)
    orig_fail_buckets = Counter(orig_samples[idx - 1]["bucket"] for idx in FAIL_INDICES)
    expected = {"short": len(SHORT_REPLACEMENTS), "medium": len(MEDIUM_REPLACEMENTS), "long": len(LONG_REPLACEMENTS)}
    if dict(orig_fail_buckets) != expected:
        raise ValueError(f"Replacement bucket counts do not match failed rows: fail={orig_fail_buckets} replacement={expected}")

    strict_by_idx = {int(r["sample_index"]): r for r in strict_samples}
    replacements_by_bucket = {
        "short": [strict_by_idx[idx] for idx in SHORT_REPLACEMENTS],
        "medium": [strict_by_idx[idx] for idx in MEDIUM_REPLACEMENTS],
        "long": [strict_by_idx[idx] for idx in LONG_REPLACEMENTS],
    }
    fail_indices_by_bucket = {
        "short": [idx for idx in FAIL_INDICES if orig_samples[idx - 1]["bucket"] == "short"],
        "medium": [idx for idx in FAIL_INDICES if orig_samples[idx - 1]["bucket"] == "medium"],
        "long": [idx for idx in FAIL_INDICES if orig_samples[idx - 1]["bucket"] == "long"],
    }

    keep_titles = {
        norm_title(row["title"])
        for i, row in enumerate(orig_samples, start=1)
        if i not in fail_set
    }
    replacement_titles = set()
    review_map: list[dict[str, Any]] = []

    reviewed_samples: list[dict[str, Any]] = []
    seeded_outputs: list[dict[str, Any]] = []

    bucket_positions = {"short": 0, "medium": 0, "long": 0}

    for idx, sample in enumerate(orig_samples, start=1):
        if idx not in fail_set:
            reviewed_samples.append(sample)
            seeded_outputs.append(orig_outputs[idx - 1])
            review_map.append(
                {
                    "sample_index": idx,
                    "action": "kept",
                    "bucket": sample["bucket"],
                    "original_title": sample["title"],
                    "final_title": sample["title"],
                    "replacement_from_strict_index": None,
                }
            )
            continue

        bucket = sample["bucket"]
        pos = bucket_positions[bucket]
        repl = dict(replacements_by_bucket[bucket][pos])
        bucket_positions[bucket] += 1

        repl_title = norm_title(repl["title"])
        if repl_title in keep_titles or repl_title in replacement_titles:
            raise ValueError(f"Replacement title duplicates an existing kept/replacement title: {repl['title']}")
        replacement_titles.add(repl_title)

        reviewed_row = {
            **sample,
            "sample_index": idx,
            "bucket": bucket,
            "word_count": repl["word_count"],
            "wikihow_id": repl.get("wikihow_id", ""),
            "title": repl.get("title", ""),
            "category": repl.get("category", ""),
            "source_url": repl.get("source_url", ""),
            "text": repl["text"],
        }
        reviewed_samples.append(reviewed_row)

        review_map.append(
            {
                "sample_index": idx,
                "action": "replaced",
                "bucket": bucket,
                "original_title": sample["title"],
                "final_title": repl["title"],
                "replacement_from_strict_index": int(repl["sample_index"]),
            }
        )

    if len(reviewed_samples) != 200:
        raise ValueError("Reviewed sample assembly failed to preserve 200 rows.")

    bucket_counts = Counter(row["bucket"] for row in reviewed_samples)
    if bucket_counts != Counter({"medium": 140, "short": 40, "long": 20}):
        raise ValueError(f"Reviewed sample bucket counts invalid: {bucket_counts}")

    write_jsonl(out_samples_path, reviewed_samples)
    write_jsonl(out_outputs_path, seeded_outputs)
    out_map_path.write_text(json.dumps(review_map, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote reviewed samples to {out_samples_path}")
    print(f"Wrote seeded reviewed outputs to {out_outputs_path}")
    print(f"Wrote review map to {out_map_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
