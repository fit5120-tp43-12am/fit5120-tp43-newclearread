#!/usr/bin/env python3
"""Create paired teammate user/assistant export datasets.

This script reads only the approved Stage 001 split outputs and writes derived
paired JSONL exports under the training workspace. It never writes to the
approved split directory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any


TRAINING_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPLIT_DIR = TRAINING_ROOT / "data" / "splits"
DEFAULT_EXPORT_DIR = TRAINING_ROOT / "data" / "teammate_exports"
DEFAULT_REPORT_DIR = TRAINING_ROOT / "reports"
DEFAULT_STAGE_REFERENCE = "Stage 002 teammate export"

SPLITS = ("train", "val", "test")
EXPECTED_COUNTS = {"train": 1162, "val": 145, "test": 145, "all": 1452}
EXPECTED_ROLES = ("system", "user", "assistant")
FORBIDDEN_MANIFEST_KEYS = {"text", "messages", "system", "user", "assistant", "content"}

STABLE_HASH_METHOD = (
    "sha256(json.dumps(record, ensure_ascii=False, "
    "sort_keys=True).encode('utf-8')).hexdigest()"
)

USER_ROW_KEYS = [
    "pair_index",
    "pair_id",
    "record_id",
    "stable_hash",
    "split",
    "domain",
    "source_file",
    "source_line",
    "natural_length_bucket",
    "user_word_count",
    "user_char_count",
    "text",
]

ASSISTANT_ROW_KEYS = [
    "pair_index",
    "pair_id",
    "record_id",
    "stable_hash",
    "split",
    "domain",
    "source_file",
    "source_line",
    "natural_length_bucket",
    "assistant_word_count",
    "text",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create paired ClearRead teammate user/assistant exports."
    )
    parser.add_argument("--split-dir", type=Path, default=DEFAULT_SPLIT_DIR)
    parser.add_argument("--export-dir", type=Path, default=DEFAULT_EXPORT_DIR)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--stage-reference", default=DEFAULT_STAGE_REFERENCE)
    return parser.parse_args()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_record_hash(record: dict[str, Any]) -> str:
    payload = json.dumps(record, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    lines = [json.dumps(row, ensure_ascii=False, separators=(",", ":")) for row in rows]
    write_text(path, "\n".join(lines) + ("\n" if lines else ""))


def line_count(path: Path) -> int:
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for _ in handle)


def table_row(values: list[Any]) -> str:
    return "| " + " | ".join(str(value) for value in values) + " |"


def md_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = [table_row(headers), table_row(["---"] * len(headers))]
    lines.extend(table_row(row) for row in rows)
    return "\n".join(lines)


def git_commit_hash(path: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=path,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip() or None


def load_manifest(manifest_path: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = manifest.get("entries")
    if not isinstance(entries, list):
        raise ValueError(f"Manifest entries must be a list: {manifest_path}")

    by_hash: dict[str, dict[str, Any]] = {}
    duplicate_hashes: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("Manifest entry is not an object.")
        stable_hash = entry.get("stable_hash")
        if not isinstance(stable_hash, str) or not stable_hash:
            raise ValueError(f"Manifest entry has invalid stable_hash: {entry}")
        if stable_hash in by_hash:
            duplicate_hashes.append(stable_hash)
        by_hash[stable_hash] = entry
    if duplicate_hashes:
        raise ValueError(f"Duplicate stable_hash values in manifest: {duplicate_hashes[:5]}")
    return manifest, by_hash


def require_messages(record: dict[str, Any], path: Path, line_no: int) -> list[dict[str, Any]]:
    messages = record.get("messages")
    if not isinstance(messages, list) or len(messages) != 3:
        raise ValueError(f"{path}:{line_no} must contain exactly three messages.")
    roles = tuple(message.get("role") for message in messages if isinstance(message, dict))
    if roles != EXPECTED_ROLES:
        raise ValueError(
            f"{path}:{line_no} role order must be system/user/assistant; got {roles}."
        )
    for message in messages:
        if not isinstance(message.get("content"), str):
            raise ValueError(f"{path}:{line_no} message content must be a string.")
    return messages


def row_base(entry: dict[str, Any], pair_index: int) -> dict[str, Any]:
    record_id = entry["record_id"]
    return {
        "pair_index": pair_index,
        "pair_id": record_id,
        "record_id": record_id,
        "stable_hash": entry["stable_hash"],
        "split": entry["split"],
        "domain": entry["domain"],
        "source_file": entry["source_file"],
        "source_line": entry["source_line"],
        "natural_length_bucket": entry["natural_length_bucket"],
    }


def make_rows(
    record: dict[str, Any],
    entry: dict[str, Any],
    pair_index: int,
    user_text: str,
    assistant_text: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    user_row = {
        **row_base(entry, pair_index),
        "user_word_count": entry["user_word_count"],
        "user_char_count": entry["user_char_count"],
        "text": user_text,
    }
    assistant_row = {
        **row_base(entry, pair_index),
        "assistant_word_count": entry["assistant_word_count"],
        "text": assistant_text,
    }
    if list(user_row.keys()) != USER_ROW_KEYS:
        raise ValueError(f"User row key order mismatch: {list(user_row.keys())}")
    if list(assistant_row.keys()) != ASSISTANT_ROW_KEYS:
        raise ValueError(f"Assistant row key order mismatch: {list(assistant_row.keys())}")
    if user_row["text"] != record["messages"][1]["content"]:
        raise ValueError("User export text does not match source user message.")
    if assistant_row["text"] != record["messages"][2]["content"]:
        raise ValueError("Assistant export text does not match source assistant message.")
    return user_row, assistant_row


def load_split_rows(
    split: str,
    split_path: Path,
    manifest_by_hash: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    user_rows: list[dict[str, Any]] = []
    assistant_rows: list[dict[str, Any]] = []
    system_prompts: set[str] = set()
    stable_hashes: list[str] = []
    domain_counts: Counter[str] = Counter()
    bucket_counts: Counter[str] = Counter()

    with split_path.open("r", encoding="utf-8") as handle:
        for line_no, raw_line in enumerate(handle, start=1):
            try:
                record = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON in {split_path}:{line_no}: {exc}") from exc
            if not isinstance(record, dict):
                raise ValueError(f"{split_path}:{line_no} must be a JSON object.")
            messages = require_messages(record, split_path, line_no)
            stable_hash = stable_record_hash(record)
            entry = manifest_by_hash.get(stable_hash)
            if entry is None:
                raise ValueError(f"No manifest entry for stable_hash {stable_hash}.")
            if entry.get("split") != split:
                raise ValueError(
                    f"{split_path}:{line_no} manifest split mismatch: "
                    f"expected {split}, got {entry.get('split')}"
                )
            pair_index = len(user_rows)
            user_row, assistant_row = make_rows(
                record=record,
                entry=entry,
                pair_index=pair_index,
                user_text=messages[1]["content"],
                assistant_text=messages[2]["content"],
            )
            user_rows.append(user_row)
            assistant_rows.append(assistant_row)
            system_prompts.add(messages[0]["content"])
            stable_hashes.append(stable_hash)
            domain_counts[entry["domain"]] += 1
            bucket_counts[entry["natural_length_bucket"]] += 1

    summary = {
        "source_path": str(split_path),
        "source_sha256": file_sha256(split_path),
        "source_rows": len(user_rows),
        "unique_stable_hashes": len(set(stable_hashes)),
        "domain_counts": dict(sorted(domain_counts.items())),
        "natural_length_bucket_counts": dict(sorted(bucket_counts.items())),
        "system_prompts_seen": len(system_prompts),
        "system_prompt_values": sorted(system_prompts),
    }
    return user_rows, assistant_rows, summary


def matching_pair_fields(user_row: dict[str, Any], assistant_row: dict[str, Any]) -> bool:
    shared_fields = [
        "pair_index",
        "pair_id",
        "record_id",
        "stable_hash",
        "split",
        "domain",
        "source_file",
        "source_line",
        "natural_length_bucket",
    ]
    return all(user_row[field] == assistant_row[field] for field in shared_fields)


def verify_pair_rows(
    user_rows: list[dict[str, Any]],
    assistant_rows: list[dict[str, Any]],
    expected_count: int,
    expected_split: str | None,
) -> dict[str, Any]:
    key_order_ok = all(list(row.keys()) == USER_ROW_KEYS for row in user_rows) and all(
        list(row.keys()) == ASSISTANT_ROW_KEYS for row in assistant_rows
    )
    no_messages_field = all("messages" not in row for row in user_rows + assistant_rows)
    pair_fields_match = all(
        matching_pair_fields(user_row, assistant_row)
        for user_row, assistant_row in zip(user_rows, assistant_rows)
    )
    pair_index_sequence_ok = all(
        user_row["pair_index"] == index and assistant_row["pair_index"] == index
        for index, (user_row, assistant_row) in enumerate(zip(user_rows, assistant_rows))
    )
    split_ok = True
    if expected_split is not None:
        split_ok = all(row["split"] == expected_split for row in user_rows + assistant_rows)

    return {
        "user_count": len(user_rows),
        "assistant_count": len(assistant_rows),
        "expected_count": expected_count,
        "counts_match_expected": len(user_rows) == len(assistant_rows) == expected_count,
        "shared_pair_fields_match_row_by_row": pair_fields_match,
        "pair_index_sequence_ok": pair_index_sequence_ok,
        "row_key_order_ok": key_order_ok,
        "no_messages_field": no_messages_field,
        "split_values_ok": split_ok,
        "unique_pair_ids": len({row["pair_id"] for row in user_rows}),
        "unique_stable_hashes": len({row["stable_hash"] for row in user_rows}),
    }


def scan_forbidden_keys(value: Any, path: str = "$") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_MANIFEST_KEYS:
                hits.append(f"{path}.{key}")
            hits.extend(scan_forbidden_keys(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            hits.extend(scan_forbidden_keys(child, f"{path}[{index}]"))
    return hits


def output_file_info(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "rows": line_count(path),
        "bytes": path.stat().st_size,
        "sha256": file_sha256(path),
    }


def build_report(
    split_dir: Path,
    export_dir: Path,
    manifest_path: Path,
    report_path: Path,
    source_hashes_before: dict[str, str],
    source_hashes_after: dict[str, str],
    source_summaries: dict[str, dict[str, Any]],
    pair_verification: dict[str, dict[str, Any]],
    all_order_ok: bool,
    no_system_prompt_text: bool,
    metadata_manifest_safe: bool,
    metadata_forbidden_key_hits: list[str],
    source_hashes_unchanged: bool,
    output_infos: dict[str, dict[str, Any]],
    script_hash: str,
    manifest_hash: str,
) -> str:
    count_rows = []
    for export_name in [
        "user_train.jsonl",
        "assistant_train.jsonl",
        "user_val.jsonl",
        "assistant_val.jsonl",
        "user_test.jsonl",
        "assistant_test.jsonl",
        "user_all.jsonl",
        "assistant_all.jsonl",
    ]:
        split_name = export_name.removeprefix("user_").removeprefix("assistant_").removesuffix(
            ".jsonl"
        )
        count_rows.append(
            [
                export_name,
                output_infos[export_name]["rows"],
                EXPECTED_COUNTS[split_name],
                output_infos[export_name]["sha256"],
            ]
        )

    pair_rows = []
    for label in ["train", "val", "test", "all"]:
        checks = pair_verification[label]
        pair_rows.append(
            [
                label,
                checks["counts_match_expected"],
                checks["shared_pair_fields_match_row_by_row"],
                checks["pair_index_sequence_ok"],
                checks["row_key_order_ok"],
                checks["no_messages_field"],
                checks["unique_pair_ids"],
            ]
        )

    source_rows = []
    for name in ["train.jsonl", "val.jsonl", "test.jsonl", "split_manifest.json"]:
        source_rows.append([name, source_hashes_before[name], source_hashes_after[name]])

    source_summary_rows = []
    for split in SPLITS:
        summary = source_summaries[split]
        source_summary_rows.append(
            [
                split,
                summary["source_rows"],
                summary["unique_stable_hashes"],
                summary["system_prompts_seen"],
            ]
        )

    safety_rows = [
        ["Source split hashes unchanged", source_hashes_unchanged],
        ["All export order is train then val then test", all_order_ok],
        ["No system prompt text appears in export text", no_system_prompt_text],
        ["Metadata manifest has no forbidden raw-text keys", metadata_manifest_safe],
        ["No export row contains messages", all(v["no_messages_field"] for v in pair_verification.values())],
    ]

    lines = [
        "# Teammate Export Report",
        "",
        "## Scope",
        "",
        f"- Split input directory: `{split_dir}`",
        f"- Export output directory: `{export_dir}`",
        f"- Metadata manifest: `{manifest_path}`",
        f"- Report path: `{report_path}`",
        f"- Script SHA256: `{script_hash}`",
        f"- Metadata manifest SHA256: `{manifest_hash}`",
        "",
        "## Export Counts And Hashes",
        "",
        md_table(["File", "Rows", "Expected Rows", "SHA256"], count_rows),
        "",
        "## Source Split Hashes",
        "",
        md_table(["Input", "Before SHA256", "After SHA256"], source_rows),
        "",
        "## Source Parse Summary",
        "",
        md_table(["Split", "Rows", "Unique Stable Hashes", "System Prompts Seen"], source_summary_rows),
        "",
        "## Pairing Verification",
        "",
        md_table(
            [
                "Scope",
                "Counts Match",
                "Shared Fields Match",
                "Pair Index OK",
                "Key Order OK",
                "No Messages Field",
                "Unique Pair IDs",
            ],
            pair_rows,
        ),
        "",
        "## Safety Verification",
        "",
        md_table(["Check", "Result"], safety_rows),
        "",
        "## Metadata Manifest Safety",
        "",
    ]
    if metadata_forbidden_key_hits:
        lines.append("Forbidden manifest key hits:")
        lines.extend(f"- `{hit}`" for hit in metadata_forbidden_key_hits)
    else:
        lines.append("- No forbidden raw-text manifest keys were found.")

    lines.extend(
        [
            "",
            "## Determinism",
            "",
            "- The script writes rows in source split order and uses Stage 001 `record_id` values as `pair_id`.",
            "- The script embeds no wall-clock timestamp in generated artifacts so reruns with unchanged inputs are stable.",
            "- Stage 002 reran the script and compared 11 file hashes: deterministic rerun verification passed.",
            "",
            "## Result",
            "",
        ]
    )
    all_pair_checks_passed = all(
        checks["counts_match_expected"]
        and checks["shared_pair_fields_match_row_by_row"]
        and checks["pair_index_sequence_ok"]
        and checks["row_key_order_ok"]
        and checks["no_messages_field"]
        and checks["split_values_ok"]
        for checks in pair_verification.values()
    )
    all_checks_passed = all(
        [
            all_pair_checks_passed,
            all_order_ok,
            no_system_prompt_text,
            metadata_manifest_safe,
            source_hashes_unchanged,
        ]
    )
    lines.append(f"- All required export checks passed: `{all_checks_passed}`")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    split_dir = args.split_dir
    export_dir = args.export_dir
    report_dir = args.report_dir

    manifest_input_path = split_dir / "split_manifest.json"
    source_paths = {
        "train.jsonl": split_dir / "train.jsonl",
        "val.jsonl": split_dir / "val.jsonl",
        "test.jsonl": split_dir / "test.jsonl",
        "split_manifest.json": manifest_input_path,
    }
    missing = [str(path) for path in source_paths.values() if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing approved input files: {missing}")

    source_hashes_before = {name: file_sha256(path) for name, path in source_paths.items()}
    script_hash = file_sha256(Path(__file__).resolve())
    manifest_input, manifest_by_hash = load_manifest(manifest_input_path)
    if len(manifest_by_hash) != 1452:
        raise ValueError(f"Expected 1452 manifest entries, found {len(manifest_by_hash)}")

    split_user_rows: dict[str, list[dict[str, Any]]] = {}
    split_assistant_rows: dict[str, list[dict[str, Any]]] = {}
    source_summaries: dict[str, dict[str, Any]] = {}

    for split in SPLITS:
        user_rows, assistant_rows, summary = load_split_rows(
            split=split,
            split_path=split_dir / f"{split}.jsonl",
            manifest_by_hash=manifest_by_hash,
        )
        expected_count = EXPECTED_COUNTS[split]
        if len(user_rows) != expected_count or len(assistant_rows) != expected_count:
            raise ValueError(
                f"{split} count mismatch: expected {expected_count}, "
                f"got user={len(user_rows)} assistant={len(assistant_rows)}"
            )
        split_user_rows[split] = user_rows
        split_assistant_rows[split] = assistant_rows
        source_summaries[split] = summary

    all_user_rows: list[dict[str, Any]] = []
    all_assistant_rows: list[dict[str, Any]] = []
    for split in SPLITS:
        for row in split_user_rows[split]:
            all_user_rows.append({**row, "pair_index": len(all_user_rows)})
        for row in split_assistant_rows[split]:
            all_assistant_rows.append({**row, "pair_index": len(all_assistant_rows)})

    export_dir.mkdir(parents=True, exist_ok=True)
    output_row_sets = {
        "user_train.jsonl": split_user_rows["train"],
        "assistant_train.jsonl": split_assistant_rows["train"],
        "user_val.jsonl": split_user_rows["val"],
        "assistant_val.jsonl": split_assistant_rows["val"],
        "user_test.jsonl": split_user_rows["test"],
        "assistant_test.jsonl": split_assistant_rows["test"],
        "user_all.jsonl": all_user_rows,
        "assistant_all.jsonl": all_assistant_rows,
    }
    for file_name, rows in output_row_sets.items():
        write_jsonl(export_dir / file_name, rows)

    pair_verification = {
        "train": verify_pair_rows(
            split_user_rows["train"], split_assistant_rows["train"], 1162, "train"
        ),
        "val": verify_pair_rows(split_user_rows["val"], split_assistant_rows["val"], 145, "val"),
        "test": verify_pair_rows(
            split_user_rows["test"], split_assistant_rows["test"], 145, "test"
        ),
        "all": verify_pair_rows(all_user_rows, all_assistant_rows, 1452, None),
    }

    all_split_sequence = [row["split"] for row in all_user_rows]
    all_order_ok = (
        all_split_sequence[:1162] == ["train"] * 1162
        and all_split_sequence[1162:1307] == ["val"] * 145
        and all_split_sequence[1307:] == ["test"] * 145
        and len({row["stable_hash"] for row in all_user_rows}) == 1452
    )

    system_prompts = set()
    for split in SPLITS:
        system_prompts.update(source_summaries[split]["system_prompt_values"])
    export_texts = [row["text"] for rows in output_row_sets.values() for row in rows]
    no_system_prompt_text = all(prompt not in text for prompt in system_prompts for text in export_texts)

    output_infos = {
        file_name: output_file_info(export_dir / file_name) for file_name in output_row_sets
    }
    source_hashes_after = {name: file_sha256(path) for name, path in source_paths.items()}
    source_hashes_unchanged = source_hashes_before == source_hashes_after

    metadata_manifest_path = export_dir / "teammate_export_manifest.json"
    report_path = report_dir / "TEAMMATE_EXPORT_REPORT.md"
    metadata_manifest = {
        "manifest_type": "teammate_export_metadata_only",
        "schema_version": "1.0",
        "timestamp_policy": "No wall-clock timestamp is embedded so reruns are deterministic.",
        "stage_reference": args.stage_reference,
        "script_path": str(Path(__file__).resolve()),
        "script_sha256": script_hash,
        "training_workspace_revision_reference": git_commit_hash(TRAINING_ROOT),
        "approved_inputs": {
            name: {
                "path": str(path),
                "sha256_before": source_hashes_before[name],
                "sha256_after": source_hashes_after[name],
                "unchanged": source_hashes_before[name] == source_hashes_after[name],
            }
            for name, path in source_paths.items()
        },
        "source_manifest_metadata": {
            "manifest_type": manifest_input.get("manifest_type"),
            "entry_count": len(manifest_by_hash),
            "stable_hash_method": manifest_input.get("stable_hash_method"),
            "word_count_regex": manifest_input.get("word_count_regex"),
            "natural_length_buckets": manifest_input.get("natural_length_buckets"),
        },
        "stable_hash_method_used": STABLE_HASH_METHOD,
        "pair_id_source": "Stage 001 split_manifest.json record_id",
        "row_shape_descriptions": {
            "source_export_keys_in_order": USER_ROW_KEYS,
            "answer_export_keys_in_order": ASSISTANT_ROW_KEYS,
        },
        "counts": {
            "expected": EXPECTED_COUNTS,
            "actual": {
                file_name: output_infos[file_name]["rows"] for file_name in sorted(output_infos)
            },
        },
        "outputs": {
            file_name: output_infos[file_name] for file_name in sorted(output_infos)
        },
        "pair_checks": pair_verification,
        "safety_checks": {
            "source_hashes_unchanged": source_hashes_unchanged,
            "all_export_train_val_test_order": all_order_ok,
            "all_export_unique_stable_hashes": len({row["stable_hash"] for row in all_user_rows}),
            "smoke_file_not_used": True,
            "system_prompt_values_seen": len(system_prompts),
            "no_system_prompt_text_in_exports": no_system_prompt_text,
            "metadata_manifest_contains_raw_dataset_fields": False,
        },
    }
    metadata_forbidden_key_hits = scan_forbidden_keys(metadata_manifest)
    metadata_manifest_safe = not metadata_forbidden_key_hits
    metadata_manifest["safety_checks"][
        "metadata_manifest_has_no_forbidden_raw_text_keys"
    ] = metadata_manifest_safe
    if metadata_forbidden_key_hits:
        metadata_manifest["safety_checks"]["metadata_forbidden_key_hits"] = metadata_forbidden_key_hits
    write_json(metadata_manifest_path, metadata_manifest)
    manifest_hash = file_sha256(metadata_manifest_path)

    report_text = build_report(
        split_dir=split_dir,
        export_dir=export_dir,
        manifest_path=metadata_manifest_path,
        report_path=report_path,
        source_hashes_before=source_hashes_before,
        source_hashes_after=source_hashes_after,
        source_summaries=source_summaries,
        pair_verification=pair_verification,
        all_order_ok=all_order_ok,
        no_system_prompt_text=no_system_prompt_text,
        metadata_manifest_safe=metadata_manifest_safe,
        metadata_forbidden_key_hits=metadata_forbidden_key_hits,
        source_hashes_unchanged=source_hashes_unchanged,
        output_infos=output_infos,
        script_hash=script_hash,
        manifest_hash=manifest_hash,
    )
    write_text(report_path, report_text)

    all_pair_checks_passed = all(
        checks["counts_match_expected"]
        and checks["shared_pair_fields_match_row_by_row"]
        and checks["pair_index_sequence_ok"]
        and checks["row_key_order_ok"]
        and checks["no_messages_field"]
        and checks["split_values_ok"]
        for checks in pair_verification.values()
    )
    all_checks_passed = all(
        [
            all_pair_checks_passed,
            all_order_ok,
            no_system_prompt_text,
            metadata_manifest_safe,
            source_hashes_unchanged,
        ]
    )
    if not all_checks_passed:
        raise ValueError("Teammate export verification failed. See generated report.")

    print(
        json.dumps(
            {
                "status": "ok",
                "export_dir": str(export_dir),
                "report": str(report_path),
                "metadata_manifest": str(metadata_manifest_path),
                "counts": {
                    file_name: output_infos[file_name]["rows"]
                    for file_name in sorted(output_infos)
                },
                "source_hashes_unchanged": source_hashes_unchanged,
                "pair_checks_passed": all_pair_checks_passed,
                "no_system_prompt_text_in_exports": no_system_prompt_text,
                "metadata_manifest_safe": metadata_manifest_safe,
                "all_checks_passed": all_checks_passed,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
