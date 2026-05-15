from __future__ import annotations

import argparse
import hashlib
import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sweep_utils import ROOT, read_json, read_jsonl, write_json


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def assistant_parser_version(metrics_path: Path) -> str:
    metrics = read_json(metrics_path)
    return str(metrics.get("parser_version", "unknown_parser"))


def source_text_from_record(record: dict[str, Any]) -> str:
    for message in record["messages"]:
        if message.get("role") == "user":
            return str(message.get("content", ""))
    raise RuntimeError("Validation record has no user/source message.")


def ensure_subset(subset_path: Path, val_records: list[dict[str, Any]], subset_size: int, seed: int) -> dict[str, Any]:
    if subset_path.exists():
        subset = read_json(subset_path)
        return subset
    rng = random.Random(seed)
    indices = sorted(rng.sample(range(len(val_records)), subset_size))
    rows = []
    for index in indices:
        record_id = f"val_{index:03d}"
        rows.append(
            {
                "index": index,
                "record_id": record_id,
                "source_sha256": sha256_text(source_text_from_record(val_records[index])),
            }
        )
    subset = {
        "created_at_utc": utc_now(),
        "subset_schema_version": "validation_judge_subset_v1",
        "seed": seed,
        "subset_size": subset_size,
        "validation_record_count": len(val_records),
        "selection_policy": "deterministic random sample over validation indices, sorted after sampling",
        "rows": rows,
    }
    write_json(subset_path, subset)
    return subset


def update_model_candidates(system_rows: list[dict[str, str]]) -> None:
    path = ROOT / "configs" / "model_candidates.json"
    current = read_json(path) if path.exists() else {"candidates": []}
    by_key = {row["key"]: row for row in current.get("candidates", [])}
    for row in system_rows:
        by_key[row["key"]] = row
    current["candidates"] = [by_key[key] for key in sorted(by_key)]
    write_json(path, current)


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare fixed validation-subset judge inputs for sweep checkpoints.")
    parser.add_argument("--candidate-key", required=True)
    parser.add_argument("--train-run-id", required=True)
    parser.add_argument("--epochs", nargs="+", type=int, required=True)
    parser.add_argument("--judge-run-id", required=True)
    parser.add_argument("--stage-label", default="stage1")
    parser.add_argument("--subset-size", type=int, default=50)
    parser.add_argument("--seed", type=int, default=5120)
    args = parser.parse_args()

    sweep_config = read_json(ROOT / "configs" / "sweep_candidates.json")
    candidate = next(item for item in sweep_config["candidates"] if item["key"] == args.candidate_key)
    val_path = ROOT / sweep_config["data"]["val_path"]
    val_records = read_jsonl(val_path)
    subset_path = ROOT / "configs" / f"validation_judge_subset_{args.subset_size}.json"
    subset = ensure_subset(subset_path, val_records, args.subset_size, args.seed)
    wanted_indices = {int(row["index"]) for row in subset["rows"]}

    judge_root = ROOT / "outputs" / "judge" / args.judge_run_id
    system_rows: list[dict[str, str]] = []
    manifest_rows: list[dict[str, Any]] = []

    for epoch in args.epochs:
        validation_id = f"{args.train_run_id}_epoch_{epoch}_record_messages"
        validation_dir = ROOT / "model_workspaces" / args.candidate_key / "outputs" / "validation" / validation_id
        parsed_path = validation_dir / "parsed_outputs.jsonl"
        metrics_path = validation_dir / "metrics.json"
        parsed_rows = read_jsonl(parsed_path)
        parser_version = assistant_parser_version(metrics_path)
        parsed_by_index = {int(row["index"]): row for row in parsed_rows}

        system_id = f"{args.candidate_key}_{args.stage_label}_epoch_{epoch}"
        output_dir = judge_root / "judge_inputs" / system_id
        rows: list[dict[str, Any]] = []
        for index in sorted(wanted_indices):
            parsed_row = parsed_by_index.get(index)
            if parsed_row is None:
                continue
            record = val_records[index]
            raw_output = str(parsed_row.get("raw_output", ""))
            rows.append(
                {
                    "candidate_output": parsed_row["parsed"],
                    "input_id": parsed_row["record_id"],
                    "judge_input_id": f"{args.judge_run_id}_{system_id}_{parsed_row['record_id']}",
                    "judge_run_id": args.judge_run_id,
                    "parser_version": parser_version,
                    "raw_output_sha256": sha256_text(raw_output),
                    "record_run_id": validation_id,
                    "run_id": args.train_run_id,
                    "source_chunk_text": source_text_from_record(record),
                    "system_id": system_id,
                }
            )
        write_jsonl(output_dir / "judge_inputs.jsonl", rows)
        manifest = {
            "created_at_utc": utc_now(),
            "candidate_key": args.candidate_key,
            "model_id": candidate["model_id"],
            "system_id": system_id,
            "train_run_id": args.train_run_id,
            "stage_label": args.stage_label,
            "validation_id": validation_id,
            "subset_path": str(subset_path),
            "subset_size": int(args.subset_size),
            "judge_input_count": len(rows),
            "missing_from_subset_due_to_parse_failure": int(args.subset_size - len(rows)),
            "judge_inputs_path": str(output_dir / "judge_inputs.jsonl"),
        }
        write_json(output_dir / "judge_input_manifest.json", manifest)
        manifest_rows.append(manifest)
        system_rows.append({"key": system_id, "model_id": f"{candidate['model_id']}::{args.train_run_id}::epoch_{epoch}"})

    update_model_candidates(system_rows)
    write_json(
        judge_root / "judge_inputs" / f"{args.candidate_key}_{args.train_run_id}_manifest.json",
        {
            "created_at_utc": utc_now(),
            "judge_run_id": args.judge_run_id,
            "candidate_key": args.candidate_key,
            "train_run_id": args.train_run_id,
            "stage_label": args.stage_label,
            "epochs": args.epochs,
            "systems": manifest_rows,
        },
    )
    print(json.dumps({"status": "completed", "judge_run_id": args.judge_run_id, "systems": len(manifest_rows)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
