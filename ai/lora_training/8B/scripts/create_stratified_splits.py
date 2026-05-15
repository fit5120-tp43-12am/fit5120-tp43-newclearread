#!/usr/bin/env python3
"""Profile ClearRead source data and create deterministic stratified splits.

The script reads the seven per-domain JSONL files from the training-system-clean
accepted dataset. It never writes to the source directory. Outputs are written
under this training workspace. Use ``--source-dir`` when the accepted dataset
is stored outside this package.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


TRAINING_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_DIR = TRAINING_ROOT / "data" / "source" / "accepted"
DEFAULT_REPORT_DIR = TRAINING_ROOT / "reports"
DEFAULT_SPLIT_DIR = TRAINING_ROOT / "data" / "splits"

SEED = 5120
WORD_RE = re.compile(r"[A-Za-z0-9]+(?:['-][A-Za-z0-9]+)*")
EXPECTED_ROLES = ["system", "user", "assistant"]
BUCKETS = ["short", "medium", "long"]
BUCKET_RULES = {
    "short": "<=400 user words",
    "medium": "401-800 user words",
    "long": ">=801 user words",
}

DOMAIN_FILES = [
    ("assignment_rubric", "assignment_rubric_v1.jsonl"),
    ("tech_doc", "tech_doc_v1.jsonl"),
    ("academic_book", "academic_book_v1.jsonl"),
    ("academic_paper", "academic_paper_v1.jsonl"),
    ("public_service", "public_service_v1.jsonl"),
    ("medlineplus", "medlineplus_v1.jsonl"),
    ("gen_know", "gen_know_v1.jsonl"),
]

TARGETS = {
    "assignment_rubric": {"total": 83, "train": 67, "val": 8, "test": 8},
    "tech_doc": {"total": 89, "train": 71, "val": 9, "test": 9},
    "academic_book": {"total": 233, "train": 187, "val": 23, "test": 23},
    "academic_paper": {"total": 486, "train": 388, "val": 49, "test": 49},
    "public_service": {"total": 198, "train": 158, "val": 20, "test": 20},
    "medlineplus": {"total": 230, "train": 184, "val": 23, "test": 23},
    "gen_know": {"total": 133, "train": 107, "val": 13, "test": 13},
}

SMOKE_PLAN = [
    ("medlineplus", "short"),
    ("medlineplus", "medium"),
    ("public_service", "medium"),
    ("public_service", "long"),
    ("academic_paper", "short"),
    ("academic_paper", "medium"),
    ("academic_book", "medium"),
    ("tech_doc", "medium"),
    ("assignment_rubric", "long"),
    ("gen_know", "medium"),
]


@dataclass(frozen=True)
class SourceRecord:
    domain: str
    source_file: str
    source_line: int
    stable_hash: str
    record_id: str
    user_word_count: int
    user_char_count: int
    assistant_word_count: int
    natural_length_bucket: str
    raw_line: str
    record: dict[str, Any]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create ClearRead source profile and deterministic stratified splits."
    )
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--split-dir", type=Path, default=DEFAULT_SPLIT_DIR)
    parser.add_argument("--seed", type=int, default=SEED)
    return parser.parse_args()


def stable_record_hash(record: dict[str, Any]) -> str:
    payload = json.dumps(record, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def line_count(path: Path) -> int:
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for _ in handle)


def word_count(text: str) -> int:
    return len(WORD_RE.findall(text))


def bucket_for_user_words(count: int) -> str:
    if count <= 400:
        return "short"
    if count <= 800:
        return "medium"
    return "long"


def clean_number(value: float) -> int | float:
    if math.isfinite(value) and abs(value - round(value)) < 1e-9:
        return int(round(value))
    return round(value, 2)


def percent(part: int, total: int) -> float:
    if total == 0:
        return 0.0
    return round(part * 100.0 / total, 2)


def percentile(values: list[int], pct: float) -> int | float:
    if not values:
        return 0
    sorted_values = sorted(values)
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = (pct / 100.0) * (len(sorted_values) - 1)
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return sorted_values[low]
    weight = rank - low
    value = sorted_values[low] * (1.0 - weight) + sorted_values[high] * weight
    return clean_number(value)


def stats(values: list[int]) -> dict[str, int | float]:
    if not values:
        return {
            "min": 0,
            "p10": 0,
            "p25": 0,
            "p33": 0,
            "p50": 0,
            "p67": 0,
            "p75": 0,
            "p90": 0,
            "p95": 0,
            "p99": 0,
            "max": 0,
            "mean": 0,
        }
    return {
        "min": min(values),
        "p10": percentile(values, 10),
        "p25": percentile(values, 25),
        "p33": percentile(values, 33),
        "p50": percentile(values, 50),
        "p67": percentile(values, 67),
        "p75": percentile(values, 75),
        "p90": percentile(values, 90),
        "p95": percentile(values, 95),
        "p99": percentile(values, 99),
        "max": max(values),
        "mean": clean_number(sum(values) / len(values)),
    }


def table_row(values: list[Any]) -> str:
    return "| " + " | ".join(str(value) for value in values) + " |"


def md_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = [table_row(headers), table_row(["---"] * len(headers))]
    lines.extend(table_row(row) for row in rows)
    return "\n".join(lines)


def source_file_info(source_dir: Path) -> dict[str, dict[str, Any]]:
    names = [file_name for _, file_name in DOMAIN_FILES] + ["all_v1.jsonl"]
    info: dict[str, dict[str, Any]] = {}
    for name in names:
        path = source_dir / name
        if not path.exists():
            raise FileNotFoundError(f"Expected source file is missing: {path}")
        info[name] = {
            "path": str(path),
            "line_count": line_count(path),
            "bytes": path.stat().st_size,
            "sha256": file_sha256(path),
            "used_for_split": name != "all_v1.jsonl",
        }
    return info


def load_records(source_dir: Path) -> tuple[list[SourceRecord], dict[str, Any]]:
    records: list[SourceRecord] = []
    errors: list[dict[str, Any]] = []

    for domain, file_name in DOMAIN_FILES:
        path = source_dir / file_name
        if not path.exists():
            raise FileNotFoundError(f"Expected source file is missing: {path}")
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                raw_line = line.rstrip("\r\n")
                if not raw_line.strip():
                    errors.append(
                        {
                            "source_file": file_name,
                            "source_line": line_number,
                            "error": "blank JSONL line",
                        }
                    )
                    continue
                try:
                    record = json.loads(raw_line)
                except json.JSONDecodeError as exc:
                    errors.append(
                        {
                            "source_file": file_name,
                            "source_line": line_number,
                            "error": f"JSON parse error: {exc}",
                        }
                    )
                    continue

                messages = record.get("messages") if isinstance(record, dict) else None
                roles = []
                if isinstance(messages, list):
                    roles = [
                        message.get("role") if isinstance(message, dict) else None
                        for message in messages
                    ]
                if roles != EXPECTED_ROLES:
                    errors.append(
                        {
                            "source_file": file_name,
                            "source_line": line_number,
                            "error": f"invalid role order: {roles}",
                        }
                    )
                    continue

                user_content = messages[1].get("content")
                assistant_content = messages[2].get("content")
                if not isinstance(user_content, str) or not isinstance(
                    assistant_content, str
                ):
                    errors.append(
                        {
                            "source_file": file_name,
                            "source_line": line_number,
                            "error": "user or assistant content is not a string",
                        }
                    )
                    continue

                user_words = word_count(user_content)
                assistant_words = word_count(assistant_content)
                stable_hash = stable_record_hash(record)
                record_id = f"{domain}:{line_number:06d}:{stable_hash[:12]}"
                records.append(
                    SourceRecord(
                        domain=domain,
                        source_file=file_name,
                        source_line=line_number,
                        stable_hash=stable_hash,
                        record_id=record_id,
                        user_word_count=user_words,
                        user_char_count=len(user_content),
                        assistant_word_count=assistant_words,
                        natural_length_bucket=bucket_for_user_words(user_words),
                        raw_line=raw_line,
                        record=record,
                    )
                )

    if errors:
        preview = json.dumps(errors[:5], indent=2, ensure_ascii=False)
        raise ValueError(f"Source validation failed with {len(errors)} errors:\n{preview}")

    role_validation = {
        "expected_roles": EXPECTED_ROLES,
        "valid_records": len(records),
        "invalid_records": 0,
        "errors": [],
    }
    return records, role_validation


def count_by_domain(records: list[SourceRecord]) -> dict[str, int]:
    counts = Counter(record.domain for record in records)
    return {domain: counts.get(domain, 0) for domain, _ in DOMAIN_FILES}


def count_by_bucket(records: list[SourceRecord]) -> dict[str, int]:
    counts = Counter(record.natural_length_bucket for record in records)
    return {bucket: counts.get(bucket, 0) for bucket in BUCKETS}


def cross_tab(records: list[SourceRecord]) -> dict[str, dict[str, int]]:
    output: dict[str, dict[str, int]] = {}
    for domain, _ in DOMAIN_FILES:
        domain_records = [record for record in records if record.domain == domain]
        bucket_counts = count_by_bucket(domain_records)
        output[domain] = {bucket: bucket_counts[bucket] for bucket in BUCKETS}
        output[domain]["total"] = len(domain_records)
    return output


def distribution_rows(counts: dict[str, int], total: int) -> list[dict[str, Any]]:
    return [
        {"label": label, "count": count, "percent": percent(count, total)}
        for label, count in counts.items()
    ]


def histogram_100(records: list[SourceRecord]) -> list[dict[str, Any]]:
    bins: list[tuple[str, int | None, int | None]] = [
        ("<=300", None, 300),
        ("301-400", 301, 400),
        ("401-500", 401, 500),
        ("501-600", 501, 600),
        ("601-700", 601, 700),
        ("701-800", 701, 800),
        ("801-900", 801, 900),
        ("901-1000", 901, 1000),
        ("1001-1100", 1001, 1100),
        ("1101-1200", 1101, 1200),
        (">1200", 1201, None),
    ]
    values = [record.user_word_count for record in records]
    rows = []
    for label, lower, upper in bins:
        count = 0
        for value in values:
            if lower is not None and value < lower:
                continue
            if upper is not None and value > upper:
                continue
            count += 1
        rows.append({"bin": label, "count": count, "percent": percent(count, len(values))})
    return rows


def build_source_profile(
    records: list[SourceRecord],
    source_dir: Path,
    source_files: dict[str, dict[str, Any]],
    role_validation: dict[str, Any],
) -> dict[str, Any]:
    total = len(records)
    domain_counts = count_by_domain(records)
    bucket_counts = count_by_bucket(records)
    by_domain_bucket: dict[str, list[dict[str, Any]]] = {}
    by_domain_user_stats: dict[str, dict[str, int | float]] = {}
    by_domain_assistant_stats: dict[str, dict[str, int | float]] = {}

    for domain, _ in DOMAIN_FILES:
        domain_records = [record for record in records if record.domain == domain]
        domain_total = len(domain_records)
        domain_bucket_counts = count_by_bucket(domain_records)
        by_domain_bucket[domain] = [
            {
                "bucket": bucket,
                "count": domain_bucket_counts[bucket],
                "percent": percent(domain_bucket_counts[bucket], domain_total),
            }
            for bucket in BUCKETS
        ]
        by_domain_user_stats[domain] = stats(
            [record.user_word_count for record in domain_records]
        )
        by_domain_assistant_stats[domain] = stats(
            [record.assistant_word_count for record in domain_records]
        )

    academic_paper_count = domain_counts["academic_paper"]
    medium_count = bucket_counts["medium"]
    profile = {
        "source_dataset_path": str(source_dir),
        "used_source_files": [file_name for _, file_name in DOMAIN_FILES],
        "stable_hash_method": (
            "sha256(json.dumps(record, ensure_ascii=False, sort_keys=True)"
            ".encode('utf-8')).hexdigest()"
        ),
        "word_count_regex": WORD_RE.pattern,
        "word_count_regex_note": (
            "Counts English alphanumeric tokens, including tokens with internal "
            "apostrophes or hyphens."
        ),
        "natural_length_buckets": BUCKET_RULES,
        "total_record_count": total,
        "domain_distribution": [
            {
                "domain": domain,
                "count": domain_counts[domain],
                "percent": percent(domain_counts[domain], total),
            }
            for domain, _ in DOMAIN_FILES
        ],
        "overall_natural_length_bucket_distribution": [
            {
                "bucket": bucket,
                "count": bucket_counts[bucket],
                "percent": percent(bucket_counts[bucket], total),
            }
            for bucket in BUCKETS
        ],
        "per_domain_natural_length_bucket_distribution": by_domain_bucket,
        "domain_x_natural_length_bucket_source_cross_tab": cross_tab(records),
        "user_word_count_histogram_100": histogram_100(records),
        "overall_user_word_count_stats": stats(
            [record.user_word_count for record in records]
        ),
        "per_domain_user_word_count_stats": by_domain_user_stats,
        "assistant_word_count_summary": {
            "overall": stats([record.assistant_word_count for record in records]),
            "by_domain": by_domain_assistant_stats,
        },
        "role_order_validation": role_validation,
        "source_file_counts": source_files,
        "known_fact_checks": {
            "total_records_is_1452": total == 1452,
            "medium_401_800_count": medium_count,
            "medium_401_800_percent": percent(medium_count, total),
            "median_user_word_count": stats(
                [record.user_word_count for record in records]
            )["p50"],
            "academic_paper_count": academic_paper_count,
            "academic_paper_percent": percent(academic_paper_count, total),
        },
    }
    return profile


def allocation_largest_remainder(
    domain: str, split: str, target: int, bucket_counts: dict[str, int]
) -> tuple[dict[str, int], list[dict[str, Any]]]:
    domain_total = sum(bucket_counts.values())
    allocation = {bucket: 0 for bucket in BUCKETS}
    details = []
    if target == 0:
        return allocation, details

    floor_sum = 0
    for bucket in BUCKETS:
        source_count = bucket_counts[bucket]
        ideal = target * source_count / domain_total if domain_total else 0.0
        floored = min(math.floor(ideal), source_count)
        allocation[bucket] = floored
        floor_sum += floored
        details.append(
            {
                "domain": domain,
                "split": split,
                "bucket": bucket,
                "source_count": source_count,
                "ideal": round(ideal, 4),
                "floor": floored,
                "fractional_remainder": round(ideal - math.floor(ideal), 4),
            }
        )

    remaining = target - floor_sum
    candidates = sorted(
        BUCKETS,
        key=lambda bucket: (
            -(target * bucket_counts[bucket] / domain_total - math.floor(target * bucket_counts[bucket] / domain_total))
            if domain_total
            else 0.0,
            BUCKETS.index(bucket),
        ),
    )
    while remaining > 0:
        changed = False
        for bucket in candidates:
            if allocation[bucket] < bucket_counts[bucket]:
                allocation[bucket] += 1
                remaining -= 1
                changed = True
                if remaining == 0:
                    break
        if not changed:
            raise ValueError(
                f"Cannot allocate {target} records for {domain}/{split}; "
                f"source buckets only have {bucket_counts}"
            )

    for detail in details:
        detail["allocated"] = allocation[detail["bucket"]]
    return allocation, details


def adjust_overdraw(
    domain: str,
    source_counts: dict[str, int],
    val_alloc: dict[str, int],
    test_alloc: dict[str, int],
) -> list[str]:
    deviations: list[str] = []
    split_allocs = {"val": val_alloc, "test": test_alloc}

    for bucket in BUCKETS:
        while val_alloc[bucket] + test_alloc[bucket] > source_counts[bucket]:
            overflow_split = "test" if test_alloc[bucket] >= val_alloc[bucket] else "val"
            if split_allocs[overflow_split][bucket] == 0:
                overflow_split = "val" if overflow_split == "test" else "test"
            split_allocs[overflow_split][bucket] -= 1

            replacement = None
            for candidate in BUCKETS:
                if candidate == bucket:
                    continue
                capacity = (
                    source_counts[candidate]
                    - val_alloc[candidate]
                    - test_alloc[candidate]
                )
                if capacity > 0:
                    replacement = candidate
                    break
            if replacement is None:
                raise ValueError(
                    f"Cannot resolve allocation overdraw for {domain}/{bucket}"
                )
            split_allocs[overflow_split][replacement] += 1
            deviations.append(
                f"{domain}: moved one {overflow_split} record from {bucket} "
                f"to {replacement} to avoid overdrawing a small bucket."
            )
    return deviations


def select_even_indices(size: int, count: int) -> list[int]:
    if count <= 0:
        return []
    if count >= size:
        return list(range(size))

    selected: list[int] = []
    used: set[int] = set()
    for i in range(count):
        raw = ((i + 0.5) * size / count) - 0.5
        candidate = max(0, min(size - 1, int(round(raw))))
        if candidate in used:
            for distance in range(1, size):
                left = candidate - distance
                right = candidate + distance
                if left >= 0 and left not in used:
                    candidate = left
                    break
                if right < size and right not in used:
                    candidate = right
                    break
        selected.append(candidate)
        used.add(candidate)
    return sorted(selected)


def build_split_assignments(
    records: list[SourceRecord],
) -> tuple[dict[str, str], dict[str, Any], list[str]]:
    records_by_cell: dict[tuple[str, str], list[SourceRecord]] = defaultdict(list)
    for record in records:
        records_by_cell[(record.domain, record.natural_length_bucket)].append(record)

    allocation_details: list[dict[str, Any]] = []
    allocations: dict[str, dict[str, dict[str, int]]] = {}
    deviations: list[str] = []

    for domain, _ in DOMAIN_FILES:
        source_counts = {
            bucket: len(records_by_cell[(domain, bucket)]) for bucket in BUCKETS
        }
        val_alloc, val_details = allocation_largest_remainder(
            domain, "val", TARGETS[domain]["val"], source_counts
        )
        test_alloc, test_details = allocation_largest_remainder(
            domain, "test", TARGETS[domain]["test"], source_counts
        )
        deviations.extend(adjust_overdraw(domain, source_counts, val_alloc, test_alloc))
        allocation_details.extend(val_details)
        allocation_details.extend(test_details)
        allocations[domain] = {
            "source": source_counts,
            "val": val_alloc,
            "test": test_alloc,
        }

    assignments: dict[str, str] = {}
    for domain, _ in DOMAIN_FILES:
        for bucket in BUCKETS:
            cell_records = sorted(
                records_by_cell[(domain, bucket)],
                key=lambda record: (
                    record.user_word_count,
                    record.stable_hash,
                    record.source_line,
                ),
            )
            cell_size = len(cell_records)
            val_count = allocations[domain]["val"][bucket]
            test_count = allocations[domain]["test"][bucket]
            heldout_count = val_count + test_count
            if heldout_count > cell_size:
                raise ValueError(
                    f"Split allocation overdraws {domain}/{bucket}: "
                    f"{heldout_count} requested from {cell_size}"
                )

            heldout_indices = select_even_indices(cell_size, heldout_count)
            val_positions = set(select_even_indices(len(heldout_indices), val_count))
            heldout_index_set = set(heldout_indices)
            for position, index in enumerate(heldout_indices):
                split = "val" if position in val_positions else "test"
                assignments[cell_records[index].stable_hash] = split
            for index, record in enumerate(cell_records):
                if index not in heldout_index_set:
                    assignments[record.stable_hash] = "train"

    if len(assignments) != len(records):
        raise ValueError(
            f"Internal error: assigned {len(assignments)} of {len(records)} records"
        )
    return assignments, {"allocations": allocations, "details": allocation_details}, deviations


def split_records(
    records: list[SourceRecord], assignments: dict[str, str]
) -> dict[str, list[SourceRecord]]:
    output = {"train": [], "val": [], "test": []}
    for record in records:
        output[assignments[record.stable_hash]].append(record)
    for split in output:
        output[split].sort(
            key=lambda record: (
                [domain for domain, _ in DOMAIN_FILES].index(record.domain),
                record.source_line,
            )
        )
    return output


def select_smoke_records(train_records: list[SourceRecord]) -> tuple[list[SourceRecord], list[str]]:
    selected: list[SourceRecord] = []
    used_hashes: set[str] = set()
    notes: list[str] = []

    def choose(candidates: list[SourceRecord]) -> SourceRecord | None:
        unused = [record for record in candidates if record.stable_hash not in used_hashes]
        if not unused:
            return None
        ordered = sorted(
            unused,
            key=lambda record: (
                record.user_word_count,
                record.stable_hash,
                record.source_line,
            ),
        )
        return ordered[len(ordered) // 2]

    for domain, bucket in SMOKE_PLAN:
        candidates = [
            record
            for record in train_records
            if record.domain == domain and record.natural_length_bucket == bucket
        ]
        chosen = choose(candidates)
        if chosen is None:
            same_domain = [record for record in train_records if record.domain == domain]
            chosen = choose(same_domain)
            if chosen is not None:
                notes.append(
                    f"Fallback for {domain}/{bucket}: selected "
                    f"{chosen.natural_length_bucket} in same domain."
                )
        if chosen is None:
            same_bucket = [
                record
                for record in train_records
                if record.natural_length_bucket == bucket
            ]
            chosen = choose(same_bucket)
            if chosen is not None:
                notes.append(
                    f"Fallback for {domain}/{bucket}: selected same bucket "
                    f"from {chosen.domain}."
                )
        if chosen is None:
            chosen = choose(train_records)
            if chosen is not None:
                notes.append(
                    f"Fallback for {domain}/{bucket}: selected any remaining train record."
                )
        if chosen is None:
            raise ValueError("Could not choose enough smoke records from train.")
        selected.append(chosen)
        used_hashes.add(chosen.stable_hash)

    selected_buckets = {record.natural_length_bucket for record in selected}
    available_buckets = {record.natural_length_bucket for record in train_records}
    missing = available_buckets.difference(selected_buckets)
    if missing:
        raise ValueError(
            "Smoke selection failed to cover available length buckets: "
            f"missing {sorted(missing)}"
        )
    return selected, notes


def manifest_entries(
    records: list[SourceRecord], assignments: dict[str, str]
) -> list[dict[str, Any]]:
    ordered = sorted(
        records,
        key=lambda record: (
            [domain for domain, _ in DOMAIN_FILES].index(record.domain),
            record.source_line,
        ),
    )
    return [
        {
            "record_id": record.record_id,
            "stable_hash": record.stable_hash,
            "domain": record.domain,
            "source_file": record.source_file,
            "source_line": record.source_line,
            "user_word_count": record.user_word_count,
            "user_char_count": record.user_char_count,
            "assistant_word_count": record.assistant_word_count,
            "natural_length_bucket": record.natural_length_bucket,
            "split": assignments[record.stable_hash],
        }
        for record in ordered
    ]


def split_count_summary(split_map: dict[str, list[SourceRecord]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for split, records in split_map.items():
        summary[split] = {
            "total": len(records),
            "by_domain": count_by_domain(records),
            "by_natural_length_bucket": count_by_bucket(records),
            "domain_x_natural_length_bucket": cross_tab(records),
        }
    return summary


def verify_splits(
    source_records: list[SourceRecord],
    split_map: dict[str, list[SourceRecord]],
    smoke_records: list[SourceRecord],
    entries: list[dict[str, Any]],
) -> dict[str, Any]:
    train_hashes = {record.stable_hash for record in split_map["train"]}
    val_hashes = {record.stable_hash for record in split_map["val"]}
    test_hashes = {record.stable_hash for record in split_map["test"]}
    smoke_hashes = {record.stable_hash for record in smoke_records}
    all_split_hashes = train_hashes | val_hashes | test_hashes

    domain_match: dict[str, bool] = {}
    for domain, _ in DOMAIN_FILES:
        domain_match[domain] = all(
            len([record for record in split_map[split] if record.domain == domain])
            == TARGETS[domain][split]
            for split in ["train", "val", "test"]
        )

    verification = {
        "train_count_is_1162": len(split_map["train"]) == 1162,
        "val_count_is_145": len(split_map["val"]) == 145,
        "test_count_is_145": len(split_map["test"]) == 145,
        "total_unique_train_val_test_hashes_is_1452": len(all_split_hashes) == 1452,
        "no_train_val_overlap": train_hashes.isdisjoint(val_hashes),
        "no_train_test_overlap": train_hashes.isdisjoint(test_hashes),
        "no_val_test_overlap": val_hashes.isdisjoint(test_hashes),
        "per_domain_counts_match_targets": all(domain_match.values()),
        "per_domain_count_results": domain_match,
        "smoke_count_is_10": len(smoke_records) == 10,
        "smoke_records_all_from_train": smoke_hashes.issubset(train_hashes),
        "manifest_entry_count_is_1452": len(entries) == 1452,
        "manifest_has_no_message_text_fields": not any(
            key in entry for entry in entries for key in ["messages", "system", "user", "assistant"]
        ),
        "source_record_count_is_1452": len(source_records) == 1452,
    }
    verification["all_checks_passed"] = all(
        value for key, value in verification.items() if key != "per_domain_count_results"
    )
    return verification


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def write_jsonl(path: Path, records: list[SourceRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(record.raw_line)
            handle.write("\n")


def relative_or_name(path: Path) -> str:
    try:
        return str(path.relative_to(TRAINING_ROOT))
    except ValueError:
        return str(path)


def output_hashes(paths: dict[str, Path]) -> dict[str, str]:
    return {name: file_sha256(path) for name, path in paths.items() if path.exists()}


def render_source_profile_md(profile: dict[str, Any]) -> str:
    domain_rows = [
        [row["domain"], row["count"], f'{row["percent"]:.2f}%']
        for row in profile["domain_distribution"]
    ]
    bucket_rows = [
        [row["bucket"], row["count"], f'{row["percent"]:.2f}%']
        for row in profile["overall_natural_length_bucket_distribution"]
    ]
    crosstab_rows = [
        [
            domain,
            profile["domain_x_natural_length_bucket_source_cross_tab"][domain]["short"],
            profile["domain_x_natural_length_bucket_source_cross_tab"][domain]["medium"],
            profile["domain_x_natural_length_bucket_source_cross_tab"][domain]["long"],
            profile["domain_x_natural_length_bucket_source_cross_tab"][domain]["total"],
        ]
        for domain, _ in DOMAIN_FILES
    ]
    hist_rows = [
        [row["bin"], row["count"], f'{row["percent"]:.2f}%']
        for row in profile["user_word_count_histogram_100"]
    ]
    stats_obj = profile["overall_user_word_count_stats"]
    stats_rows = [[key, value] for key, value in stats_obj.items()]
    per_domain_stats_rows = []
    for domain, _ in DOMAIN_FILES:
        values = profile["per_domain_user_word_count_stats"][domain]
        per_domain_stats_rows.append(
            [
                domain,
                values["min"],
                values["p10"],
                values["p25"],
                values["p33"],
                values["p50"],
                values["p67"],
                values["p75"],
                values["p90"],
                values["p95"],
                values["p99"],
                values["max"],
                values["mean"],
            ]
        )
    assistant_stats = profile["assistant_word_count_summary"]["overall"]
    assistant_rows = [[key, value] for key, value in assistant_stats.items()]
    source_rows = [
        [
            name,
            info["line_count"],
            info["bytes"],
            info["sha256"],
            info["used_for_split"],
        ]
        for name, info in profile["source_file_counts"].items()
    ]

    lines = [
        "# Source Distribution Profile",
        "",
        f"Source dataset: `{profile['source_dataset_path']}`",
        "",
        f"Total records: **{profile['total_record_count']}**",
        "",
        "Word counts use this documented regex:",
        "",
        f"`{profile['word_count_regex']}`",
        "",
        profile["word_count_regex_note"],
        "",
        "## Domain Distribution",
        "",
        md_table(["Domain", "Count", "Percent"], domain_rows),
        "",
        "## Natural Length Bucket Distribution",
        "",
        md_table(["Bucket", "Count", "Percent"], bucket_rows),
        "",
        "## Domain x Natural Length Bucket Cross-Tab",
        "",
        md_table(["Domain", "Short", "Medium", "Long", "Total"], crosstab_rows),
        "",
        "## 100-Word User Word Count Histogram",
        "",
        md_table(["Bin", "Count", "Percent"], hist_rows),
        "",
        "## Overall User Word Count Stats",
        "",
        md_table(["Metric", "Value"], stats_rows),
        "",
        "## Per-Domain User Word Count Stats",
        "",
        md_table(
            [
                "Domain",
                "Min",
                "P10",
                "P25",
                "P33",
                "P50",
                "P67",
                "P75",
                "P90",
                "P95",
                "P99",
                "Max",
                "Mean",
            ],
            per_domain_stats_rows,
        ),
        "",
        "## Assistant Word Count Summary",
        "",
        md_table(["Metric", "Value"], assistant_rows),
        "",
        "## Role-Order Validation",
        "",
        f"- Expected roles: `{' / '.join(profile['role_order_validation']['expected_roles'])}`",
        f"- Valid records: `{profile['role_order_validation']['valid_records']}`",
        f"- Invalid records: `{profile['role_order_validation']['invalid_records']}`",
        "",
        "## Source File Counts And Hashes",
        "",
        md_table(
            ["File", "Line Count", "Bytes", "SHA256", "Used For Split"], source_rows
        ),
        "",
        "## Known Fact Checks",
        "",
        md_table(
            ["Check", "Value"],
            [[key, value] for key, value in profile["known_fact_checks"].items()],
        ),
        "",
    ]
    return "\n".join(lines)


def split_distribution_rows(
    split_counts: dict[str, Any], split: str, total: int
) -> list[list[Any]]:
    counts = split_counts[split]["by_natural_length_bucket"]
    return [[bucket, counts[bucket], f"{percent(counts[bucket], total):.2f}%"] for bucket in BUCKETS]


def render_crosstab_table(crosstab: dict[str, dict[str, int]]) -> str:
    rows = []
    for domain, _ in DOMAIN_FILES:
        row = crosstab[domain]
        rows.append([domain, row["short"], row["medium"], row["long"], row["total"]])
    return md_table(["Domain", "Short", "Medium", "Long", "Total"], rows)


def render_split_report_md(
    profile: dict[str, Any],
    split_counts: dict[str, Any],
    allocation_summary: dict[str, Any],
    deviations: list[str],
    verification: dict[str, Any],
    smoke_records: list[SourceRecord],
    smoke_notes: list[str],
    hashes: dict[str, str],
) -> str:
    split_rows = [
        [split, split_counts[split]["total"], f"{percent(split_counts[split]['total'], 1452):.2f}%"]
        for split in ["train", "val", "test"]
    ]
    domain_rows = []
    for domain, _ in DOMAIN_FILES:
        domain_rows.append(
            [
                domain,
                TARGETS[domain]["total"],
                split_counts["train"]["by_domain"][domain],
                split_counts["val"]["by_domain"][domain],
                split_counts["test"]["by_domain"][domain],
            ]
        )

    source_bucket_rows = [
        [
            row["bucket"],
            row["count"],
            f'{row["percent"]:.2f}%',
            split_counts["train"]["by_natural_length_bucket"][row["bucket"]],
            split_counts["val"]["by_natural_length_bucket"][row["bucket"]],
            split_counts["test"]["by_natural_length_bucket"][row["bucket"]],
        ]
        for row in profile["overall_natural_length_bucket_distribution"]
    ]
    allocation_rows = []
    for domain, _ in DOMAIN_FILES:
        allocation = allocation_summary["allocations"][domain]
        for bucket in BUCKETS:
            allocation_rows.append(
                [
                    domain,
                    bucket,
                    allocation["source"][bucket],
                    allocation["val"][bucket],
                    allocation["test"][bucket],
                    allocation["source"][bucket]
                    - allocation["val"][bucket]
                    - allocation["test"][bucket],
                ]
            )
    smoke_rows = [
        [
            index + 1,
            record.domain,
            record.natural_length_bucket,
            record.user_word_count,
            record.source_file,
            record.source_line,
            record.record_id,
            record.stable_hash,
        ]
        for index, record in enumerate(smoke_records)
    ]
    verification_rows = [
        [key, value]
        for key, value in verification.items()
        if key != "per_domain_count_results"
    ]
    hash_rows = [[name, digest] for name, digest in hashes.items()]

    lines = [
        "# Split Report",
        "",
        "Split method: deterministic approximate joint stratification over "
        "`domain x natural_length_bucket`.",
        "",
        "Validation and test first match the accepted per-domain targets, then "
        "largest-remainder rounding preserves each domain's natural short/medium/long "
        "distribution as closely as integer counts allow. Within each domain-bucket "
        "cell, held-out records are selected evenly across records sorted by user "
        "word count, stable hash, and source line.",
        "",
        f"Seed recorded for reproducibility: `{SEED}`. No random draw is used in the final selection.",
        "",
        "## Split Counts",
        "",
        md_table(["Split", "Count", "Percent of Source"], split_rows),
        "",
        "## Domain Count Verification",
        "",
        md_table(["Domain", "Source", "Train", "Val", "Test"], domain_rows),
        "",
        "## Overall Natural Length Bucket Counts",
        "",
        md_table(["Bucket", "Source", "Source %", "Train", "Val", "Test"], source_bucket_rows),
        "",
        "## Source Cross-Tab",
        "",
        render_crosstab_table(profile["domain_x_natural_length_bucket_source_cross_tab"]),
        "",
        "## Train Cross-Tab",
        "",
        render_crosstab_table(split_counts["train"]["domain_x_natural_length_bucket"]),
        "",
        "## Validation Cross-Tab",
        "",
        render_crosstab_table(split_counts["val"]["domain_x_natural_length_bucket"]),
        "",
        "## Test Cross-Tab",
        "",
        render_crosstab_table(split_counts["test"]["domain_x_natural_length_bucket"]),
        "",
        "## Val/Test Bucket Allocation By Domain",
        "",
        md_table(
            ["Domain", "Bucket", "Source", "Val", "Test", "Train Remainder"],
            allocation_rows,
        ),
        "",
        "## Allocation Deviations",
        "",
    ]

    if deviations:
        lines.extend(f"- {deviation}" for deviation in deviations)
    else:
        lines.append("- None. Largest-remainder allocations were feasible without adjustment.")

    lines.extend(
        [
            "",
            "## Smoke Set Selection",
            "",
            "The smoke set contains 10 records, all selected from train only.",
            "",
            md_table(
                [
                    "#",
                    "Domain",
                    "Bucket",
                    "User Words",
                    "Source File",
                    "Line",
                    "Record ID",
                    "Stable Hash",
                ],
                smoke_rows,
            ),
            "",
            "Smoke selection notes:",
            "",
        ]
    )
    if smoke_notes:
        lines.extend(f"- {note}" for note in smoke_notes)
    else:
        lines.append("- No fallback was needed; preferred domain/bucket composition was available.")

    lines.extend(
        [
            "",
            "## Verification",
            "",
            md_table(["Check", "Result"], verification_rows),
            "",
            "## Output File Hashes",
            "",
            md_table(["Output", "SHA256"], hash_rows),
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    source_dir = args.source_dir
    report_dir = args.report_dir
    split_dir = args.split_dir

    if args.seed != SEED:
        raise ValueError(
            f"This workflow records fixed seed {SEED}; got unsupported seed {args.seed}."
        )

    source_files = source_file_info(source_dir)
    records, role_validation = load_records(source_dir)
    source_counts = count_by_domain(records)
    for domain, expected in TARGETS.items():
        if source_counts[domain] != expected["total"]:
            raise ValueError(
                f"{domain} count mismatch: expected {expected['total']}, "
                f"found {source_counts[domain]}"
            )
    if len(records) != 1452:
        raise ValueError(f"Expected 1452 records, found {len(records)}")

    profile = build_source_profile(records, source_dir, source_files, role_validation)
    assignments, allocation_summary, deviations = build_split_assignments(records)
    split_map = split_records(records, assignments)
    smoke_records, smoke_notes = select_smoke_records(split_map["train"])
    entries = manifest_entries(records, assignments)
    split_counts = split_count_summary(split_map)
    verification = verify_splits(records, split_map, smoke_records, entries)
    if not verification["all_checks_passed"]:
        raise ValueError(f"Split verification failed: {verification}")

    report_dir.mkdir(parents=True, exist_ok=True)
    split_dir.mkdir(parents=True, exist_ok=True)

    train_path = split_dir / "train.jsonl"
    val_path = split_dir / "val.jsonl"
    test_path = split_dir / "test.jsonl"
    smoke_path = split_dir / "smoke_test_10.jsonl"
    manifest_path = split_dir / "split_manifest.json"
    split_report_path = split_dir / "SPLIT_REPORT.md"
    profile_json_path = report_dir / "source_distribution_profile.json"
    profile_md_path = report_dir / "SOURCE_DISTRIBUTION_PROFILE.md"

    write_jsonl(train_path, split_map["train"])
    write_jsonl(val_path, split_map["val"])
    write_jsonl(test_path, split_map["test"])
    write_jsonl(smoke_path, smoke_records)

    manifest = {
        "manifest_type": "metadata_only_no_raw_messages",
        "source_dataset_path": str(source_dir),
        "source_file_hashes": {
            name: info["sha256"] for name, info in source_files.items()
        },
        "stable_hash_method": profile["stable_hash_method"],
        "word_count_regex": WORD_RE.pattern,
        "natural_length_buckets": BUCKET_RULES,
        "split_targets": TARGETS,
        "split_counts": split_counts,
        "verification": verification,
        "entries": entries,
    }
    write_json(manifest_path, manifest)
    write_json(profile_json_path, profile)
    write_text(profile_md_path, render_source_profile_md(profile))

    hashes = output_hashes(
        {
            "reports/source_distribution_profile.json": profile_json_path,
            "reports/SOURCE_DISTRIBUTION_PROFILE.md": profile_md_path,
            "data/splits/train.jsonl": train_path,
            "data/splits/val.jsonl": val_path,
            "data/splits/test.jsonl": test_path,
            "data/splits/smoke_test_10.jsonl": smoke_path,
            "data/splits/split_manifest.json": manifest_path,
        }
    )
    write_text(
        split_report_path,
        render_split_report_md(
            profile,
            split_counts,
            allocation_summary,
            deviations,
            verification,
            smoke_records,
            smoke_notes,
            hashes,
        ),
    )

    print(
        json.dumps(
            {
                "status": "ok",
                "records": len(records),
                "split_counts": {
                    split: len(split_map[split]) for split in ["train", "val", "test"]
                },
                "smoke_count": len(smoke_records),
                "manifest_entries": len(entries),
                "all_checks_passed": verification["all_checks_passed"],
                "outputs": {
                    "profile_json": str(profile_json_path),
                    "profile_md": str(profile_md_path),
                    "train": str(train_path),
                    "val": str(val_path),
                    "test": str(test_path),
                    "smoke": str(smoke_path),
                    "manifest": str(manifest_path),
                    "split_report": str(split_report_path),
                },
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
