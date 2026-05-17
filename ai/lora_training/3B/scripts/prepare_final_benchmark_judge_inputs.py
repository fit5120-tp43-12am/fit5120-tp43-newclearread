#!/usr/bin/env python
"""Prepare judge inputs from final benchmark parsed outputs."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sweep_utils import ROOT, read_json, read_jsonl, write_json


PREPARED_INPUTS_PATH = (
    ROOT
    / "data"
    / "source_snapshot"
    / "benchmark_prepared_inputs"
    / "dyslexia_benchmark_handoff__03_project_workspace__09_run_config__worker_20_dataset_manifest_and_freeze_inputs__prepared_inputs.jsonl"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def update_model_candidates(system_id: str, model_id: str) -> None:
    path = ROOT / "configs" / "model_candidates.json"
    current = read_json(path) if path.exists() else {"candidates": []}
    by_key = {row["key"]: row for row in current.get("candidates", [])}
    by_key[system_id] = {"key": system_id, "model_id": model_id}
    current["candidates"] = [by_key[key] for key in sorted(by_key)]
    write_json(path, current)


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare final benchmark judge inputs.")
    parser.add_argument("--benchmark-run-id", required=True)
    parser.add_argument("--judge-run-id", required=True)
    parser.add_argument("--system-id", required=True)
    args = parser.parse_args()

    run_root = ROOT / "benchmark_workspace" / "runs" / args.benchmark_run_id
    parsed_path = run_root / "parsed_outputs" / args.system_id / "parsed_outputs.jsonl"
    manifest_path = run_root / "manifests_logs" / f"model_inference_{args.system_id}.json"
    parsed_rows = read_jsonl(parsed_path)
    manifest = read_json(manifest_path)
    prepared = {str(row["input_id"]): row for row in read_jsonl(PREPARED_INPUTS_PATH)}
    out_dir = ROOT / "outputs" / "judge" / args.judge_run_id / "judge_inputs" / args.system_id
    rows: list[dict[str, Any]] = []
    for parsed in parsed_rows:
        input_id = str(parsed["input_id"])
        prepared_record = prepared[input_id]
        raw_output = str(parsed.get("raw_output_text", ""))
        rows.append(
            {
                "candidate_output": parsed["parsed"],
                "input_id": input_id,
                "judge_input_id": f"{args.judge_run_id}_{args.system_id}_{input_id}",
                "judge_run_id": args.judge_run_id,
                "parser_version": "sweep_json_main2_kp4_v1",
                "raw_output_sha256": sha256_text(raw_output),
                "record_run_id": parsed["record_run_id"],
                "record_run_id_source": args.benchmark_run_id,
                "run_id": args.benchmark_run_id,
                "source_chunk_text": prepared_record["source_chunk_text"],
                "system_id": args.system_id,
            }
        )
    write_jsonl(out_dir / "judge_inputs.jsonl", rows)
    write_json(
        out_dir / "judge_input_manifest.json",
        {
            "created_at_utc": utc_now(),
            "benchmark_run_id": args.benchmark_run_id,
            "judge_run_id": args.judge_run_id,
            "system_id": args.system_id,
            "base_model_id": manifest.get("base_model_id"),
            "adapter_dir": manifest.get("adapter_dir"),
            "prepared_input_count": int(manifest.get("prepared_input_count", 0)),
            "judge_input_count": len(rows),
            "missing_from_benchmark_due_to_parse_failure": int(manifest.get("prepared_input_count", 0)) - len(rows),
            "judge_inputs_path": str(out_dir / "judge_inputs.jsonl"),
        },
    )
    update_model_candidates(args.system_id, f"{manifest.get('base_model_id')}::{manifest.get('adapter_dir')}")
    print(json.dumps({"status": "completed", "judge_inputs": len(rows), "out_dir": str(out_dir)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
