#!/usr/bin/env python
"""Summarize Stage 1 validation and judge results into JSON/CSV artifacts."""

from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "stage1_anchor_r32_lr2e4"
OUT_DIR = ROOT / "reports" / "stage1"
EPOCH_RE = re.compile(rf"{RUN_ID}_epoch_(\d+)_record_messages$")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def find_judge_by_system() -> dict[str, dict]:
    systems: dict[str, dict] = {}
    for path in (ROOT / "outputs" / "judge").glob("*/scoring/accessibility_first_v2/system_score_summary.json"):
        summary = load_json(path)
        for system_id, system in summary.get("systems", {}).items():
            item = dict(system)
            item["judge_run_id"] = summary.get("judge_run_id")
            item["judge_summary_path"] = str(path.relative_to(ROOT))
            systems[system_id] = item
    return systems


def summarize() -> list[dict]:
    judge_by_system = find_judge_by_system()
    rows: list[dict] = []
    workspaces_dir = ROOT / "model_workspaces"

    for workspace in sorted(workspaces_dir.iterdir()):
        if not workspace.is_dir():
            continue
        candidate = workspace.name
        training_result_path = workspace / "outputs" / "training" / f"{RUN_ID}_training_result.json"
        training_result = load_json(training_result_path) if training_result_path.exists() else {}

        validation_dir = workspace / "outputs" / "validation"
        if not validation_dir.exists():
            continue

        for metrics_path in sorted(validation_dir.glob(f"{RUN_ID}_epoch_*_record_messages/metrics.json")):
            match = EPOCH_RE.search(metrics_path.parent.name)
            if not match:
                continue
            epoch = int(match.group(1))
            metrics = load_json(metrics_path)
            counts = metrics.get("counts", {})
            rates = metrics.get("rates", {})
            system_id = f"{candidate}_stage1_epoch_{epoch}"
            judge = judge_by_system.get(system_id, {})
            score = judge.get("capped_official_item_score", {})
            safety = judge.get("safety_level_counts", {})
            fields = judge.get("per_field_mean_scores", {})

            rows.append(
                {
                    "candidate": candidate,
                    "epoch": epoch,
                    "run_id": RUN_ID,
                    "raw_output_count": counts.get("raw_output_count"),
                    "parsed_ok_count": counts.get("parsed_ok_count"),
                    "parse_failure_count": counts.get("parse_failure_count"),
                    "parsed_ok_rate": rates.get("parsed_ok_rate"),
                    "no_refusal_or_meta_count": counts.get("no_refusal_or_meta_count"),
                    "no_markdown_fence_count": counts.get("no_markdown_fence_count"),
                    "no_mojibake_count": counts.get("no_mojibake_count"),
                    "judge_mean_capped_score": score.get("mean"),
                    "judge_count": score.get("count"),
                    "judge_run_id": judge.get("judge_run_id"),
                    "source_safety_margin": fields.get("source_safety_margin"),
                    "main_message_salience": fields.get("main_message_salience_and_quick_understanding"),
                    "major_risk_count": safety.get("major_risk"),
                    "severe_fail_count": safety.get("severe_fail"),
                    "training_runtime_seconds": training_result.get("runtime_seconds"),
                    "train_loss": training_result.get("train_loss"),
                    "eval_loss": training_result.get("eval_loss"),
                    "training_oom": training_result.get("oom"),
                    "metrics_path": str(metrics_path.relative_to(ROOT)),
                    "judge_summary_path": judge.get("judge_summary_path"),
                    "training_result_path": str(training_result_path.relative_to(ROOT))
                    if training_result_path.exists()
                    else None,
                }
            )

    return sorted(rows, key=lambda r: (r["candidate"], r["epoch"]))


def write_outputs(rows: list[dict]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "run_id": RUN_ID,
        "row_count": len(rows),
        "rows": rows,
    }
    json_path = OUT_DIR / "stage1_anchor_summary.json"
    csv_path = OUT_DIR / "stage1_anchor_summary.csv"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    fieldnames = list(rows[0].keys()) if rows else []
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(json.dumps({"json": str(json_path), "csv": str(csv_path), "rows": len(rows)}, indent=2))


def main() -> None:
    write_outputs(summarize())


if __name__ == "__main__":
    main()
