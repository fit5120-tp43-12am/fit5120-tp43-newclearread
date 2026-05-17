from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRAIN = ROOT / "data" / "source_snapshot" / "training3b_splits" / "train.jsonl"
DEFAULT_MANIFEST = ROOT / "data" / "source_snapshot" / "training3b_splits" / "split_manifest.json"
DEFAULT_OUT_DIR = ROOT / "outputs" / "data_audit" / "random_sample_100_20260513"
WORD_RE = re.compile(r"[A-Za-z0-9]+(?:['-][A-Za-z0-9]+)*")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def stable_hash(record: dict[str, Any]) -> str:
    payload = json.dumps(record, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def message_content(record: dict[str, Any], role: str) -> str:
    for message in record.get("messages", []):
        if isinstance(message, dict) and message.get("role") == role and isinstance(message.get("content"), str):
            return message["content"]
    raise ValueError(f"Missing message role={role}")


def parse_target(text: str) -> tuple[dict[str, Any] | None, str | None]:
    try:
        value = json.loads(text)
    except Exception:
        return None, "target_not_json"
    if not isinstance(value, dict):
        return None, "target_not_object"
    return value, None


def sentence_count(text: str) -> int:
    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text.strip()) if part.strip()]
    return len(parts)


def structure_checks(target_text: str) -> dict[str, Any]:
    target, error = parse_target(target_text)
    checks: dict[str, Any] = {
        "json_parse_ok": error is None,
        "parse_error": error,
        "exact_key_order": False,
        "main_idea_two_sentences": False,
        "key_points_exactly_four": False,
        "key_points_one_sentence_each": False,
        "has_markdown_fence": "```" in target_text,
    }
    if target is None:
        return checks
    checks["exact_key_order"] = list(target.keys()) == ["main_idea", "key_points"]
    main_idea = target.get("main_idea")
    checks["main_idea_two_sentences"] = isinstance(main_idea, str) and sentence_count(main_idea) == 2
    key_points = target.get("key_points")
    checks["key_points_exactly_four"] = isinstance(key_points, list) and len(key_points) == 4 and all(isinstance(x, str) and x.strip() for x in key_points)
    if isinstance(key_points, list):
        checks["key_points_one_sentence_each"] = all(isinstance(x, str) and sentence_count(x) == 1 for x in key_points)
    return checks


def load_manifest_entries(path: Path) -> dict[str, dict[str, Any]]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    entries = manifest.get("entries", [])
    return {entry["stable_hash"]: entry for entry in entries if isinstance(entry, dict) and "stable_hash" in entry}


def summarize_counts(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "by_domain": dict(Counter(row.get("domain") for row in rows)),
        "by_length_bucket": dict(Counter(row.get("natural_length_bucket") for row in rows)),
        "by_domain_x_length": {
            f"{domain}/{bucket}": count
            for (domain, bucket), count in Counter((row.get("domain"), row.get("natural_length_bucket")) for row in rows).items()
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a fixed random sample of training source-target pairs for API audit.")
    parser.add_argument("--train", type=Path, default=DEFAULT_TRAIN)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--sample-size", type=int, default=100)
    parser.add_argument("--seed", type=int, default=20260513)
    args = parser.parse_args()

    records = read_jsonl(args.train)
    manifest_by_hash = load_manifest_entries(args.manifest)
    rng = random.Random(args.seed)
    selected_indices = sorted(rng.sample(range(len(records)), args.sample_size))

    sample_rows: list[dict[str, Any]] = []
    public_rows: list[dict[str, Any]] = []
    for sample_number, train_index in enumerate(selected_indices, start=1):
        record = records[train_index]
        record_hash = stable_hash(record)
        entry = manifest_by_hash.get(record_hash, {})
        system_text = message_content(record, "system")
        user_text = message_content(record, "user")
        assistant_text = message_content(record, "assistant")
        row = {
            "audit_sample_id": f"audit100_{sample_number:03d}",
            "train_row_index_0_based": train_index,
            "stable_hash": record_hash,
            "record_id": entry.get("record_id", f"unknown:{train_index}"),
            "domain": entry.get("domain"),
            "source_file": entry.get("source_file"),
            "source_line": entry.get("source_line"),
            "natural_length_bucket": entry.get("natural_length_bucket"),
            "user_word_count": len(WORD_RE.findall(user_text)),
            "user_char_count": len(user_text),
            "assistant_word_count": len(WORD_RE.findall(assistant_text)),
            "system_prompt_sha256": hashlib.sha256(system_text.encode("utf-8")).hexdigest(),
            "source_text": user_text,
            "target_output_text": assistant_text,
            "local_structure_checks": structure_checks(assistant_text),
        }
        sample_rows.append(row)
        public_rows.append({key: value for key, value in row.items() if key not in {"source_text", "target_output_text"}})

    manifest = {
        "created_at_utc": utc_now(),
        "sample_method": "Fixed-seed simple random sample without replacement from the frozen train split.",
        "sample_seed": args.seed,
        "sample_size": args.sample_size,
        "train_path": str(args.train),
        "manifest_path": str(args.manifest),
        "train_record_count": len(records),
        "output_sample_jsonl": str(args.out_dir / "sample_with_text.jsonl"),
        "output_public_manifest_json": str(args.out_dir / "sample_manifest_public.json"),
        "distribution": summarize_counts(sample_rows),
        "raw_source_and_target_text_saved": True,
        "training_data_modified": False,
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.out_dir / "sample_with_text.jsonl", sample_rows)
    write_json(args.out_dir / "sample_manifest_public.json", {"manifest": manifest, "rows": public_rows})
    write_json(args.out_dir / "sample_summary.json", manifest)

    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
