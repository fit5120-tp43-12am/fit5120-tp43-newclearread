#!/usr/bin/env python
"""Select the best Stage 1 checkpoint for one candidate and copy it safely."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "stage1_anchor_r32_lr2e4"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def find_candidate_model_id(candidate_key: str) -> str:
    cfg = load_json(ROOT / "configs" / "sweep_candidates.json")
    candidates = cfg["candidates"]
    if isinstance(candidates, dict):
        return candidates[candidate_key]["model_id"]
    for candidate in candidates:
        if candidate.get("key") == candidate_key:
            return candidate["model_id"]
    raise KeyError(candidate_key)


def find_judge_system(candidate_key: str, epoch: int) -> dict:
    system_id = f"{candidate_key}_stage1_epoch_{epoch}"
    for path in (ROOT / "outputs" / "judge").glob("*/scoring/accessibility_first_v2/system_score_summary.json"):
        summary = load_json(path)
        system = summary.get("systems", {}).get(system_id)
        if system:
            item = dict(system)
            item["judge_run_id"] = summary.get("judge_run_id")
            item["judge_summary_path"] = str(path.relative_to(ROOT))
            return item
    return {}


def collect_rows(candidate_key: str, epochs: list[int]) -> list[dict]:
    workspace = ROOT / "model_workspaces" / candidate_key
    rows: list[dict] = []
    for epoch in epochs:
        metrics_path = (
            workspace
            / "outputs"
            / "validation"
            / f"{RUN_ID}_epoch_{epoch}_record_messages"
            / "metrics.json"
        )
        if not metrics_path.exists():
            continue
        metrics = load_json(metrics_path)
        counts = metrics.get("counts", {})
        rates = metrics.get("rates", {})
        judge = find_judge_system(candidate_key, epoch)
        score = judge.get("capped_official_item_score", {})
        fields = judge.get("per_field_mean_scores", {})
        safety = judge.get("safety_level_counts", {})
        rows.append(
            {
                "candidate_key": candidate_key,
                "epoch": epoch,
                "raw_output_count": counts.get("raw_output_count", 0),
                "parsed_ok_count": counts.get("parsed_ok_count", 0),
                "parse_failure_count": counts.get("parse_failure_count", 0),
                "parsed_ok_rate": rates.get("parsed_ok_rate", 0),
                "judge_mean_capped_score": score.get("mean"),
                "judge_count": score.get("count", 0),
                "source_safety_margin": fields.get("source_safety_margin"),
                "main_message_salience": fields.get("main_message_salience_and_quick_understanding"),
                "major_risk_count": safety.get("major_risk"),
                "severe_fail_count": safety.get("severe_fail"),
                "metrics_path": str(metrics_path.relative_to(ROOT)),
                "judge_run_id": judge.get("judge_run_id"),
                "judge_summary_path": judge.get("judge_summary_path"),
            }
        )
    return rows


def sort_key(row: dict) -> tuple:
    return (
        row["parsed_ok_count"],
        row["judge_mean_capped_score"] if row["judge_mean_capped_score"] is not None else -1,
        row["source_safety_margin"] if row["source_safety_margin"] is not None else -1,
        row["main_message_salience"] if row["main_message_salience"] is not None else -1,
        -(row["severe_fail_count"] if row["severe_fail_count"] is not None else 999),
        -(row["major_risk_count"] if row["major_risk_count"] is not None else 999),
        -row["epoch"],
    )


def copy_selected(candidate_key: str, epoch: int) -> Path:
    adapters_dir = ROOT / "model_workspaces" / candidate_key / "models" / "adapters"
    src = adapters_dir / f"{RUN_ID}_epoch_{epoch}"
    dst = adapters_dir / f"stage1_selected_anchor_epoch_{epoch}"
    if not src.exists():
        raise FileNotFoundError(src)
    if dst.exists():
        return dst
    shutil.copytree(src, dst)
    return dst


def write_decision(candidate_key: str, selected: dict, rows: list[dict], selected_dir: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = ROOT / "logs" / "decisions" / f"{candidate_key}_stage1_anchor_checkpoint_selection_{timestamp}.md"
    lines = [
        f"# {candidate_key} Stage 1 Anchor Checkpoint Selection",
        "",
        f"- Candidate: `{candidate_key}`",
        f"- Base model: `{find_candidate_model_id(candidate_key)}`",
        f"- Selected epoch: `{selected['epoch']}`",
        f"- Selected adapter copy: `{selected_dir.relative_to(ROOT)}`",
        "",
        "## Selection Rule",
        "",
        "The checkpoint is selected by product readiness first, then capped judge score, source safety margin, main message salience, and lower severe/major risk count.",
        "",
        "## Epoch Results",
        "",
        "| Epoch | Parsed OK | Judge mean | Judge count | Source safety | Main salience | Severe risk | Major risk |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| {epoch} | {parsed_ok_count}/{raw_output_count} | {judge_mean_capped_score} | {judge_count} | {source_safety_margin} | {main_message_salience} | {severe_fail_count} | {major_risk_count} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## Rationale",
            "",
            f"Epoch {selected['epoch']} was selected because it ranked highest under the stated rule.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-key", required=True)
    parser.add_argument("--epochs", nargs="+", type=int, default=[1, 2, 3, 4, 5])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    rows = collect_rows(args.candidate_key, args.epochs)
    if not rows:
        raise SystemExit(f"No validation rows found for {args.candidate_key}")
    selected = max(rows, key=sort_key)
    selected_dir = (
        ROOT
        / "model_workspaces"
        / args.candidate_key
        / "models"
        / "adapters"
        / f"stage1_selected_anchor_epoch_{selected['epoch']}"
    )
    if not args.dry_run:
        selected_dir = copy_selected(args.candidate_key, selected["epoch"])
    decision_path = write_decision(args.candidate_key, selected, rows, selected_dir)
    print(
        json.dumps(
            {
                "candidate_key": args.candidate_key,
                "selected_epoch": selected["epoch"],
                "selected_dir": str(selected_dir),
                "decision_path": str(decision_path),
                "dry_run": args.dry_run,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
