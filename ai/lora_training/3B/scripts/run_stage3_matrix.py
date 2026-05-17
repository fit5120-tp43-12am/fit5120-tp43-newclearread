#!/usr/bin/env python
"""Run the Stage 3 training/postprocess matrix sequentially with evidence logs."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def local_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def training_complete(run: dict[str, Any]) -> bool:
    result_path = (
        ROOT
        / "model_workspaces"
        / run["candidate"]
        / "outputs"
        / "training"
        / f"{run['run_id']}_training_result.json"
    )
    if not result_path.exists():
        return False
    try:
        result = read_json(result_path)
    except json.JSONDecodeError:
        return False
    if result.get("status") != "success":
        return False
    expected_epochs = int(run["epochs"])
    adapter_root = ROOT / "model_workspaces" / run["candidate"] / "models" / "adapters"
    return all((adapter_root / f"{run['run_id']}_epoch_{epoch}").exists() for epoch in range(1, expected_epochs + 1))


def postprocess_complete(run: dict[str, Any]) -> bool:
    decision_glob = f"{run['candidate']}_{run['run_id']}_checkpoint_selection_*.md"
    return any((ROOT / "logs" / "decisions").glob(decision_glob))


def run_logged(name: str, cmd: list[str], stamp: str) -> dict[str, Any]:
    log_path = ROOT / "logs" / "command_outputs" / f"{name}_{stamp}.log"
    exit_path = ROOT / "logs" / "tests" / f"{name}_{stamp}.exitcode"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    exit_path.parent.mkdir(parents=True, exist_ok=True)
    started = utc_now()
    with log_path.open("w", encoding="utf-8", newline="\n") as log_handle:
        log_handle.write(json.dumps({"event": "command_started", "created_at_utc": started, "cmd": cmd}, ensure_ascii=False) + "\n")
        log_handle.flush()
        proc = subprocess.run(cmd, cwd=ROOT, stdout=log_handle, stderr=subprocess.STDOUT, text=True)
    exit_path.write_text(f"{proc.returncode}\n", encoding="utf-8")
    return {
        "name": name,
        "cmd": cmd,
        "started_at_utc": started,
        "finished_at_utc": utc_now(),
        "exit_code": proc.returncode,
        "log_path": str(log_path.relative_to(ROOT)),
        "exit_path": str(exit_path.relative_to(ROOT)),
    }


def train_command(run: dict[str, Any]) -> list[str]:
    return [
        "bash",
        "scripts/run_qlora_training_with_fallback.sh",
        str(run["candidate"]),
        str(run["run_id"]),
        str(run["epochs"]),
        str(run["learning_rate"]),
        str(run["lora_r"]),
        str(run["lora_alpha"]),
        str(run["lora_dropout"]),
    ]


def postprocess_command(run: dict[str, Any]) -> list[str]:
    return [
        "bash",
        "scripts/postprocess_run_candidate.sh",
        str(run["candidate"]),
        str(run["run_id"]),
        str(run["stage_label"]),
        f"val50_{run['candidate']}_{run['stage_label']}",
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Stage 3 matrix sequentially.")
    parser.add_argument("--matrix", default=str(ROOT / "reports" / "stage3" / "stage3_run_matrix.json"))
    parser.add_argument("--start-index", type=int, default=1, help="1-based row number to start from.")
    parser.add_argument("--only-candidate", action="append", default=[])
    parser.add_argument("--continue-on-failure", action="store_true")
    args = parser.parse_args()

    matrix_path = Path(args.matrix)
    if not matrix_path.is_absolute():
        matrix_path = ROOT / matrix_path
    matrix = read_json(matrix_path)
    runs = list(matrix.get("runs", []))
    if args.only_candidate:
        allowed = set(args.only_candidate)
        runs = [run for run in runs if run["candidate"] in allowed]
    stamp = local_stamp()
    status_path = ROOT / "logs" / "tests" / f"stage3_matrix_execution_{stamp}.jsonl"
    report_path = ROOT / "reports" / "stage3" / f"stage3_matrix_execution_{stamp}.json"
    records: list[dict[str, Any]] = []

    for index, run in enumerate(runs, start=1):
        if index < args.start_index:
            continue
        record: dict[str, Any] = {
            "event": "stage3_run_started",
            "created_at_utc": utc_now(),
            "index": index,
            "candidate": run["candidate"],
            "run_id": run["run_id"],
            "stage_label": run["stage_label"],
            "epochs": run["epochs"],
            "lora_r": run["lora_r"],
            "lora_alpha": run["lora_alpha"],
            "learning_rate": run["learning_rate"],
        }
        print(json.dumps(record, ensure_ascii=False), flush=True)
        append_jsonl(status_path, record)

        if training_complete(run):
            train_result = {"name": "training", "exit_code": 0, "skipped": True, "reason": "already_complete"}
        else:
            train_result = run_logged(
                f"stage3_train_{run['candidate']}_{run['run_id']}",
                train_command(run),
                stamp,
            )
        record["training"] = train_result
        append_jsonl(status_path, {"event": "stage3_training_finished", **record})
        if train_result["exit_code"] != 0:
            record["status"] = "training_failed"
            records.append(record)
            append_jsonl(status_path, {"event": "stage3_run_failed", **record})
            if not args.continue_on_failure:
                break
            continue

        if postprocess_complete(run):
            post_result = {"name": "postprocess", "exit_code": 0, "skipped": True, "reason": "already_complete"}
        else:
            post_result = run_logged(
                f"stage3_postprocess_{run['candidate']}_{run['run_id']}",
                postprocess_command(run),
                stamp,
            )
        record["postprocess"] = post_result
        record["status"] = "success" if post_result["exit_code"] == 0 else "postprocess_failed"
        records.append(record)
        append_jsonl(status_path, {"event": "stage3_run_finished", **record})
        if post_result["exit_code"] != 0 and not args.continue_on_failure:
            break

    payload = {
        "created_at_utc": utc_now(),
        "source_matrix": str(matrix_path.relative_to(ROOT)),
        "status_jsonl": str(status_path.relative_to(ROOT)),
        "continue_on_failure": bool(args.continue_on_failure),
        "run_count_attempted": len(records),
        "success_count": sum(1 for item in records if item.get("status") == "success"),
        "failure_count": sum(1 for item in records if item.get("status") != "success"),
        "records": records,
    }
    write_json(report_path, payload)
    print(json.dumps({"status": "completed", "report": str(report_path), "success_count": payload["success_count"]}, indent=2), flush=True)
    return 0 if payload["failure_count"] == 0 else (0 if args.continue_on_failure else 1)


if __name__ == "__main__":
    raise SystemExit(main())
