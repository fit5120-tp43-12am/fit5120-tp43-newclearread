from __future__ import annotations

import json
import hashlib
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from final_lora_pipeline.structural_gate import validate_assistant_label_text

CONFIG_PATH = ROOT / "configs" / "pipeline_config.json"
STAGE6_ACCEPTED_DIR = ROOT / "outputs" / "accepted"
STAGE6_QUARANTINE_DIR = ROOT / "outputs" / "quarantine"
RECOVERY_DIR = ROOT / "outputs" / "stage6b_recovery_v2"
FINAL_DIR = ROOT / "outputs" / "final_dataset_v1"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line_number, line in enumerate(fh, 1):
            text = line.strip()
            if not text:
                continue
            try:
                records.append(json.loads(text))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSONL: {exc}") from exc
    return records


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8", newline="\n") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
            fh.write("\n")
    tmp_path.replace(path)
    return len(records)


def user_text_from_training_record(record: dict[str, Any]) -> str:
    messages = record.get("messages")
    if not isinstance(messages, list):
        raise ValueError("training record has no messages list")
    for message in messages:
        if isinstance(message, dict) and message.get("role") == "user":
            content = message.get("content")
            if isinstance(content, str):
                return content
    raise ValueError("training record has no user message content")


def assistant_text_from_training_record(record: dict[str, Any]) -> str:
    messages = record.get("messages")
    if not isinstance(messages, list):
        raise ValueError("training record has no messages list")
    for message in messages:
        if isinstance(message, dict) and message.get("role") == "assistant":
            content = message.get("content")
            if isinstance(content, str):
                return content
    raise ValueError("training record has no assistant message content")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_source_index(config: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    source_index: dict[tuple[str, str], dict[str, Any]] = {}
    for dataset in config["datasets"]:
        slug = dataset["slug"]
        path = Path(dataset["source_path"])
        with path.open("r", encoding="utf-8") as fh:
            for line_number, line in enumerate(fh, 1):
                record = json.loads(line)
                source_text = user_text_from_training_record(record)
                source_sha = sha256_text(source_text)
                key = (slug, source_sha)
                if key in source_index:
                    raise ValueError(f"duplicate source hash for {slug}:{source_sha[:12]}")
                source_index[key] = {
                    "dataset_slug": slug,
                    "line_number": line_number,
                    "source_sha256": source_sha,
                    "record_id": f"{slug}:{line_number}:{source_sha[:12]}",
                    "source_text": source_text,
                }
        expected = dataset["expected_records"]
        observed = sum(1 for key in source_index if key[0] == slug)
        if observed != expected:
            raise ValueError(f"{slug}: expected {expected} source records, observed {observed}")
    return source_index


def key_for_training_record(
    dataset_slug: str,
    record: dict[str, Any],
    source_index: dict[tuple[str, str], dict[str, Any]],
) -> tuple[str, str]:
    source_sha = sha256_text(user_text_from_training_record(record))
    key = (dataset_slug, source_sha)
    if key not in source_index:
        raise ValueError(f"{dataset_slug}:{source_sha[:12]} not found in source index")
    return key


def key_for_quarantine_record(record: dict[str, Any]) -> tuple[str, str]:
    slug = record.get("dataset_slug")
    source_sha = record.get("source_sha256")
    if not isinstance(slug, str) or not isinstance(source_sha, str):
        raise ValueError("quarantine record missing dataset_slug or source_sha256")
    return slug, source_sha


def validate_training_records(
    records_by_slug: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    role_shape_counts: Counter[str] = Counter()
    assistant_key_order_issues = 0
    for slug, records in records_by_slug.items():
        for index, record in enumerate(records, 1):
            messages = record.get("messages")
            roles = [message.get("role") for message in messages] if isinstance(messages, list) else []
            role_shape_counts["|".join(str(role) for role in roles)] += 1
            if roles != ["system", "user", "assistant"]:
                issues.append({"dataset_slug": slug, "index": index, "issue": "bad_message_roles", "roles": roles})
                continue
            assistant_text = assistant_text_from_training_record(record)
            gate = validate_assistant_label_text(assistant_text)
            if not gate.ok:
                issues.append(
                    {
                        "dataset_slug": slug,
                        "index": index,
                        "issue": "assistant_structural_gate_failed",
                        "issues": gate.issues,
                    }
                )
                continue
            parsed = gate.parsed
            if list(parsed.keys()) != ["main_idea", "key_points"]:
                assistant_key_order_issues += 1
    return {
        "issue_count": len(issues),
        "issues": issues[:50],
        "role_shapes": dict(role_shape_counts),
        "assistant_key_order_issues": assistant_key_order_issues,
    }


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    datasets = config["datasets"]
    source_index = load_source_index(config)

    stage6_accepted_by_slug: dict[str, list[dict[str, Any]]] = {}
    stage6_quarantine_by_slug: dict[str, list[dict[str, Any]]] = {}
    recovery_accepted_by_slug: dict[str, list[dict[str, Any]]] = {}
    recovery_quarantine_by_slug: dict[str, list[dict[str, Any]]] = {}

    recovery_accepted_keys: set[tuple[str, str]] = set()
    recovery_quarantine_keys: set[tuple[str, str]] = set()
    recovery_scope_keys: set[tuple[str, str]] = set()

    duplicate_checks: dict[str, list[str]] = defaultdict(list)

    for dataset in datasets:
        slug = dataset["slug"]
        accepted_filename = dataset["accepted_filename"]
        quarantine_filename = f"{slug}_quarantine.jsonl"

        stage6_accepted = read_jsonl(STAGE6_ACCEPTED_DIR / accepted_filename)
        stage6_quarantine = read_jsonl(STAGE6_QUARANTINE_DIR / quarantine_filename)
        recovery_accepted = read_jsonl(RECOVERY_DIR / "accepted" / accepted_filename)
        recovery_quarantine = read_jsonl(RECOVERY_DIR / "quarantine" / quarantine_filename)

        stage6_accepted_by_slug[slug] = stage6_accepted
        stage6_quarantine_by_slug[slug] = stage6_quarantine
        recovery_accepted_by_slug[slug] = recovery_accepted
        recovery_quarantine_by_slug[slug] = recovery_quarantine

        seen_stage6_accepted: set[tuple[str, str]] = set()
        for record in stage6_accepted:
            key = key_for_training_record(slug, record, source_index)
            if key in seen_stage6_accepted:
                duplicate_checks["stage6_accepted"].append(f"{slug}:{key[1][:12]}")
            seen_stage6_accepted.add(key)

        seen_stage6_quarantine: set[tuple[str, str]] = set()
        for record in stage6_quarantine:
            key = key_for_quarantine_record(record)
            if key in seen_stage6_quarantine:
                duplicate_checks["stage6_quarantine"].append(f"{slug}:{key[1][:12]}")
            seen_stage6_quarantine.add(key)

        for record in recovery_accepted:
            key = key_for_training_record(slug, record, source_index)
            recovery_accepted_keys.add(key)
            recovery_scope_keys.add(key)
        for record in recovery_quarantine:
            key = key_for_quarantine_record(record)
            recovery_quarantine_keys.add(key)
            recovery_scope_keys.add(key)

    if recovery_accepted_keys & recovery_quarantine_keys:
        overlap = sorted(f"{slug}:{sha[:12]}" for slug, sha in recovery_accepted_keys & recovery_quarantine_keys)
        raise ValueError(f"recovery accepted/quarantine overlap: {overlap[:20]}")

    final_accepted_by_slug: dict[str, list[dict[str, Any]]] = {}
    final_quarantine_by_slug: dict[str, list[dict[str, Any]]] = {}

    for dataset in datasets:
        slug = dataset["slug"]
        final_accepted_by_slug[slug] = list(stage6_accepted_by_slug[slug]) + list(recovery_accepted_by_slug[slug])
        final_quarantine_by_slug[slug] = [
            record
            for record in stage6_quarantine_by_slug[slug]
            if key_for_quarantine_record(record) not in recovery_scope_keys
        ] + list(recovery_quarantine_by_slug[slug])

    final_accepted_keys: set[tuple[str, str]] = set()
    final_quarantine_keys: set[tuple[str, str]] = set()
    for slug, records in final_accepted_by_slug.items():
        for record in records:
            key = key_for_training_record(slug, record, source_index)
            if key in final_accepted_keys:
                duplicate_checks["final_accepted"].append(f"{slug}:{key[1][:12]}")
            final_accepted_keys.add(key)
    for records in final_quarantine_by_slug.values():
        for record in records:
            key = key_for_quarantine_record(record)
            if key in final_quarantine_keys:
                duplicate_checks["final_quarantine"].append(f"{key[0]}:{key[1][:12]}")
            final_quarantine_keys.add(key)

    source_keys = set(source_index.keys())
    final_overlap = final_accepted_keys & final_quarantine_keys
    missing = source_keys - final_accepted_keys - final_quarantine_keys
    unexpected = (final_accepted_keys | final_quarantine_keys) - source_keys

    validation = validate_training_records(final_accepted_by_slug)

    accepted_dir = FINAL_DIR / "accepted"
    quarantine_dir = FINAL_DIR / "quarantine"
    reports_dir = FINAL_DIR / "reports"

    accepted_counts: dict[str, int] = {}
    quarantine_counts: dict[str, int] = {}
    for dataset in datasets:
        slug = dataset["slug"]
        accepted_counts[slug] = write_jsonl(
            accepted_dir / dataset["accepted_filename"],
            final_accepted_by_slug[slug],
        )
        quarantine_counts[slug] = write_jsonl(
            quarantine_dir / f"{slug}_quarantine.jsonl",
            final_quarantine_by_slug[slug],
        )

    all_accepted: list[dict[str, Any]] = []
    all_quarantine: list[dict[str, Any]] = []
    for dataset in datasets:
        slug = dataset["slug"]
        all_accepted.extend(final_accepted_by_slug[slug])
        all_quarantine.extend(final_quarantine_by_slug[slug])
    write_jsonl(accepted_dir / "all_v1.jsonl", all_accepted)
    write_jsonl(quarantine_dir / "all_quarantine.jsonl", all_quarantine)

    summary = {
        "final_namespace": str(FINAL_DIR),
        "source_total": len(source_keys),
        "stage6_counts": {
            "accepted_by_slug": {slug: len(records) for slug, records in stage6_accepted_by_slug.items()},
            "quarantine_by_slug": {slug: len(records) for slug, records in stage6_quarantine_by_slug.items()},
            "accepted_total": sum(len(records) for records in stage6_accepted_by_slug.values()),
            "quarantine_total": sum(len(records) for records in stage6_quarantine_by_slug.values()),
        },
        "recovery_counts": {
            "accepted_by_slug": {slug: len(records) for slug, records in recovery_accepted_by_slug.items()},
            "quarantine_by_slug": {slug: len(records) for slug, records in recovery_quarantine_by_slug.items()},
            "accepted_total": sum(len(records) for records in recovery_accepted_by_slug.values()),
            "quarantine_total": sum(len(records) for records in recovery_quarantine_by_slug.values()),
            "scope_total": len(recovery_scope_keys),
        },
        "final_counts": {
            "accepted_by_slug": accepted_counts,
            "quarantine_by_slug": quarantine_counts,
            "accepted_total": sum(accepted_counts.values()),
            "quarantine_total": sum(quarantine_counts.values()),
            "covered_total": sum(accepted_counts.values()) + sum(quarantine_counts.values()),
        },
        "coverage": {
            "accepted_quarantine_overlap_count": len(final_overlap),
            "missing_source_count": len(missing),
            "unexpected_record_count": len(unexpected),
            "duplicate_checks": {key: value for key, value in duplicate_checks.items() if value},
        },
        "structural_validation": validation,
        "files_written": {
            "accepted_dir": str(accepted_dir),
            "quarantine_dir": str(quarantine_dir),
            "combined_accepted": str(accepted_dir / "all_v1.jsonl"),
            "combined_quarantine": str(quarantine_dir / "all_quarantine.jsonl"),
            "report_json": str(reports_dir / "stage7_final_merge_qa.json"),
        },
    }
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "stage7_final_merge_qa.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
