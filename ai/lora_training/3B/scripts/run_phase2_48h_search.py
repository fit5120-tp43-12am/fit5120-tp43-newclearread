#!/usr/bin/env python
"""Run the isolated phase2 48-hour fine-tuning search.

The script is resumable: completed training/postprocess/benchmark steps are
skipped, and all new artifacts stay under phase2_48h_search.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from phase2_status import update_status


ROOT = Path(__file__).resolve().parents[1]
OLD_ROOT = ROOT.parent
EPOCHS = [1, 2, 3, 4, 5]


INITIAL_RUNS: list[dict[str, Any]] = [
    {"candidate": "phi4_mini_instruct", "run_id": "phase2_r32_a64_lr1e4", "stage_label": "phase2_r32_a64_lr1e4", "lr": 0.0001, "r": 32, "alpha": 64, "dropout": 0.05},
    {"candidate": "phi4_mini_instruct", "run_id": "phase2_r32_a64_lr1p5e4", "stage_label": "phase2_r32_a64_lr1p5e4", "lr": 0.00015, "r": 32, "alpha": 64, "dropout": 0.05},
    {"candidate": "phi4_mini_instruct", "run_id": "phase2_r64_a128_lr1e4", "stage_label": "phase2_r64_a128_lr1e4", "lr": 0.0001, "r": 64, "alpha": 128, "dropout": 0.05},
    {"candidate": "llama32_3b_instruct", "run_id": "phase2_r32_a64_lr1e4", "stage_label": "phase2_r32_a64_lr1e4", "lr": 0.0001, "r": 32, "alpha": 64, "dropout": 0.05},
    {"candidate": "llama32_3b_instruct", "run_id": "phase2_r32_a64_lr1p5e4", "stage_label": "phase2_r32_a64_lr1p5e4", "lr": 0.00015, "r": 32, "alpha": 64, "dropout": 0.05},
    {"candidate": "llama32_3b_instruct", "run_id": "phase2_r64_a128_lr1e4", "stage_label": "phase2_r64_a128_lr1e4", "lr": 0.0001, "r": 64, "alpha": 128, "dropout": 0.05},
    {"candidate": "ministral3_3b_instruct", "run_id": "phase2_r32_a64_lr1e4", "stage_label": "phase2_r32_a64_lr1e4", "lr": 0.0001, "r": 32, "alpha": 64, "dropout": 0.05},
    {"candidate": "ministral3_3b_instruct", "run_id": "phase2_r32_a64_lr1p5e4", "stage_label": "phase2_r32_a64_lr1p5e4", "lr": 0.00015, "r": 32, "alpha": 64, "dropout": 0.05},
    {"candidate": "ministral3_3b_instruct", "run_id": "phase2_r64_a128_lr1e4", "stage_label": "phase2_r64_a128_lr1e4", "lr": 0.0001, "r": 64, "alpha": 128, "dropout": 0.05},
    {"candidate": "qwen35_4b", "run_id": "phase2_r32_a64_lr1e4", "stage_label": "phase2_qwen_challenger_r32_a64_lr1e4", "lr": 0.0001, "r": 32, "alpha": 64, "dropout": 0.05},
]


FINALIST_TEMPLATE = {"lr": 0.00015, "r": 64, "alpha": 128, "dropout": 0.05}
DROPOUT_TEMPLATE = {"lr": 0.00015, "r": 64, "alpha": 128, "dropout": 0.10}
ALPHA4_TEMPLATE = {"lr": 0.00015, "r": 64, "alpha": 256, "dropout": 0.05}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def decision_note(name: str, lines: list[str]) -> Path:
    path = ROOT / "logs" / "decisions" / f"{name}_{stamp()}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def run_logged(name: str, cmd: list[str], *, continue_on_failure: bool = False) -> dict[str, Any]:
    run_stamp = stamp()
    log_path = ROOT / "logs" / "command_outputs" / f"{name}_{run_stamp}.log"
    exit_path = ROOT / "logs" / "tests" / f"{name}_{run_stamp}.exitcode"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    exit_path.parent.mkdir(parents=True, exist_ok=True)
    started = utc_now()
    update_status(phase="command_running", command_name=name, cmd=cmd, log_path=rel(log_path))
    with log_path.open("w", encoding="utf-8", newline="\n") as log_handle:
        log_handle.write(json.dumps({"event": "command_started", "created_at_utc": started, "cmd": cmd}, ensure_ascii=False) + "\n")
        log_handle.flush()
        proc = subprocess.run(cmd, cwd=ROOT, stdout=log_handle, stderr=subprocess.STDOUT, text=True)
    exit_path.write_text(f"{proc.returncode}\n", encoding="utf-8")
    record = {
        "name": name,
        "cmd": cmd,
        "started_at_utc": started,
        "finished_at_utc": utc_now(),
        "exit_code": proc.returncode,
        "log_path": rel(log_path),
        "exit_path": rel(exit_path),
    }
    write_jsonl(ROOT / "logs" / "tests" / "phase2_command_history.jsonl", record)
    update_status(phase="command_finished", command_name=name, exit_code=proc.returncode, log_path=rel(log_path))
    if proc.returncode != 0 and not continue_on_failure:
        raise RuntimeError(f"{name} failed with exit code {proc.returncode}; see {log_path}")
    return record


def source_manifest() -> Path:
    rows: list[dict[str, Any]] = []
    include_roots = [
        ROOT / "configs",
        ROOT / "data" / "source_snapshot",
    ]
    for base in include_roots:
        for path in sorted(item for item in base.rglob("*") if item.is_file()):
            rows.append(
                {
                    "relative_path": rel(path),
                    "size_bytes": path.stat().st_size,
                    "sha256": file_sha256(path),
                    "modified_utc": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
                    .replace(microsecond=0)
                    .isoformat()
                    .replace("+00:00", "Z"),
                }
            )
    payload = {
        "created_at_utc": utc_now(),
        "phase2_root": str(ROOT),
        "old_root": str(OLD_ROOT),
        "policy": "All phase2 outputs are written under phase2_48h_search; old artifacts are read-only evidence.",
        "file_count": len(rows),
        "files": rows,
    }
    out = ROOT / "manifests" / "phase2_source_snapshot_manifest.json"
    write_json(out, payload)
    return out


def write_run_matrix(runs: list[dict[str, Any]], name: str = "phase2_initial_run_matrix") -> Path:
    path = ROOT / "reports" / "phase2" / f"{name}.json"
    payload = {
        "created_at_utc": utc_now(),
        "epochs": EPOCHS,
        "runs": runs,
        "selection_policy": {
            "hard_filters": {"severe_fail": 0, "preferred_min_parsed_ok": 140, "fallback_min_parsed_ok": 137},
            "rank_order": ["judge score", "parsed success", "source safety", "main salience", "lower major risk", "lower deployment cost"],
        },
    }
    write_json(path, payload)
    return path


def training_complete(run: dict[str, Any]) -> bool:
    result_path = ROOT / "model_workspaces" / run["candidate"] / "outputs" / "training" / f"{run['run_id']}_training_result.json"
    result = read_json(result_path, {})
    if result.get("status") != "success":
        return False
    adapter_root = ROOT / "model_workspaces" / run["candidate"] / "models" / "adapters"
    return all((adapter_root / f"{run['run_id']}_epoch_{epoch}").exists() for epoch in EPOCHS)


def postprocess_complete(run: dict[str, Any]) -> bool:
    pattern = f"{run['candidate']}_{run['run_id']}_checkpoint_selection_*.md"
    return any((ROOT / "logs" / "decisions").glob(pattern))


def train_command(run: dict[str, Any]) -> list[str]:
    return [
        "bash",
        "scripts/run_qlora_training_with_fallback.sh",
        run["candidate"],
        run["run_id"],
        "5",
        str(run["lr"]),
        str(run["r"]),
        str(run["alpha"]),
        str(run["dropout"]),
        "2",
        "4",
        "1",
        "8",
    ]


def postprocess_command(run: dict[str, Any]) -> list[str]:
    judge_run_id = f"val50_{run['candidate']}_{run['stage_label']}"
    return [
        "bash",
        "scripts/postprocess_run_candidate.sh",
        run["candidate"],
        run["run_id"],
        run["stage_label"],
        judge_run_id,
        "1 2 3 4 5",
    ]


def preflight_command(candidate: str) -> list[str]:
    return [
        "python",
        "scripts/train_sweep_qlora.py",
        "--candidate-key",
        candidate,
        "--run-id",
        f"phase2_preflight_{candidate}",
        "--epochs",
        "5",
        "--learning-rate",
        "0.0001",
        "--lora-r",
        "32",
        "--lora-alpha",
        "64",
        "--lora-dropout",
        "0.05",
        "--preflight-only",
    ]


def run_train_and_postprocess(run: dict[str, Any]) -> dict[str, Any]:
    record: dict[str, Any] = {"run": run, "started_at_utc": utc_now()}
    if training_complete(run):
        record["training"] = {"skipped": True, "reason": "already_complete", "exit_code": 0}
    else:
        record["training"] = run_logged(f"train_{run['candidate']}_{run['run_id']}", train_command(run), continue_on_failure=True)
    if record["training"].get("exit_code") != 0:
        record["status"] = "training_failed"
        decision_note(
            f"phase2_training_failed_{run['candidate']}_{run['run_id']}",
            [
                f"# Phase2 Training Failed: {run['candidate']} / {run['run_id']}",
                "",
                f"- Exit code: `{record['training'].get('exit_code')}`",
                f"- Log: `{record['training'].get('log_path')}`",
                "- The run was recorded and the queue will continue.",
            ],
        )
        return record
    if postprocess_complete(run):
        record["postprocess"] = {"skipped": True, "reason": "already_complete", "exit_code": 0}
    else:
        record["postprocess"] = run_logged(f"postprocess_{run['candidate']}_{run['run_id']}", postprocess_command(run), continue_on_failure=True)
    record["status"] = "success" if record.get("postprocess", {}).get("exit_code") == 0 else "postprocess_failed"
    return record


def float_or_none(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def int_or_zero(value: Any) -> int:
    if value in (None, ""):
        return 0
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def deployment_metrics() -> dict[str, dict[str, Any]]:
    path = OLD_ROOT / "outputs" / "local_inference_resource_probe" / "20260513" / "summary.json"
    summary = read_json(path, {})
    return {row["model_key"]: row for row in summary.get("rows", []) if row.get("model_key")}


def stage1_reference_rows() -> list[dict[str, Any]]:
    path = ROOT / "data" / "source_snapshot" / "stage1_reference" / "stage1_anchor_summary.csv"
    resources = deployment_metrics()
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8", newline="") as handle:
        for item in csv.DictReader(handle):
            candidate = item["candidate"]
            epoch = int_or_zero(item["epoch"])
            run_id = item["run_id"]
            adapter_dir = OLD_ROOT / "model_workspaces" / candidate / "models" / "adapters" / f"{run_id}_epoch_{epoch}"
            resource = resources.get(candidate, {})
            rows.append(
                {
                    "source": "stage1_reference",
                    "candidate": candidate,
                    "run_id": run_id,
                    "stage_label": "stage1_anchor",
                    "epoch": epoch,
                    "parsed_ok_count": int_or_zero(item.get("parsed_ok_count")),
                    "raw_output_count": int_or_zero(item.get("raw_output_count")),
                    "judge_mean_capped_score": float_or_none(item.get("judge_mean_capped_score")),
                    "judge_count": int_or_zero(item.get("judge_count")),
                    "source_safety_margin": float_or_none(item.get("source_safety_margin")),
                    "main_message_salience": float_or_none(item.get("main_message_salience")),
                    "major_risk_count": int_or_zero(item.get("major_risk_count")),
                    "severe_fail_count": int_or_zero(item.get("severe_fail_count")),
                    "adapter_dir": adapter_dir.as_posix(),
                    "peak_gpu_mib": resource.get("peak_gpu_used_mib_after_load_or_run"),
                    "three_block_mean_seconds": resource.get("three_block_mean_seconds"),
                }
            )
    return rows


def find_judge_system(system_id: str) -> dict[str, Any]:
    for path in (ROOT / "outputs" / "judge").glob("*/scoring/accessibility_first_v2/system_score_summary.json"):
        summary = read_json(path, {})
        system = summary.get("systems", {}).get(system_id)
        if system:
            out = dict(system)
            out["judge_run_id"] = summary.get("judge_run_id")
            out["judge_summary_path"] = rel(path)
            return out
    return {}


def phase2_rows_for_run(run: dict[str, Any]) -> list[dict[str, Any]]:
    resources = deployment_metrics()
    rows: list[dict[str, Any]] = []
    for epoch in EPOCHS:
        metrics_path = ROOT / "model_workspaces" / run["candidate"] / "outputs" / "validation" / f"{run['run_id']}_epoch_{epoch}_record_messages" / "metrics.json"
        if not metrics_path.exists():
            continue
        metrics = read_json(metrics_path, {})
        counts = metrics.get("counts", {})
        system_id = f"{run['candidate']}_{run['stage_label']}_epoch_{epoch}"
        judge = find_judge_system(system_id)
        score = judge.get("capped_official_item_score", {})
        fields = judge.get("per_field_mean_scores", {})
        safety = judge.get("safety_level_counts", {})
        adapter_dir = ROOT / "model_workspaces" / run["candidate"] / "models" / "adapters" / f"{run['run_id']}_epoch_{epoch}"
        resource = resources.get(run["candidate"], {})
        rows.append(
            {
                "source": "phase2",
                "candidate": run["candidate"],
                "run_id": run["run_id"],
                "stage_label": run["stage_label"],
                "epoch": epoch,
                "parsed_ok_count": int_or_zero(counts.get("parsed_ok_count")),
                "raw_output_count": int_or_zero(counts.get("raw_output_count")),
                "judge_mean_capped_score": float_or_none(score.get("mean")),
                "judge_count": int_or_zero(score.get("count")),
                "source_safety_margin": float_or_none(fields.get("source_safety_margin")),
                "main_message_salience": float_or_none(fields.get("main_message_salience_and_quick_understanding")),
                "major_risk_count": int_or_zero(safety.get("major_risk")),
                "severe_fail_count": int_or_zero(safety.get("severe_fail")),
                "adapter_dir": adapter_dir.as_posix(),
                "peak_gpu_mib": resource.get("peak_gpu_used_mib_after_load_or_run"),
                "three_block_mean_seconds": resource.get("three_block_mean_seconds"),
                "metrics_path": rel(metrics_path),
            }
        )
    return rows


def collect_rows(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = stage1_reference_rows()
    for run in runs:
        rows.extend(phase2_rows_for_run(run))
    return rows


def rank_rows(rows: list[dict[str, Any]], *, unique_candidates: bool) -> list[dict[str, Any]]:
    with_judge = [row for row in rows if row.get("judge_mean_capped_score") is not None and int_or_zero(row.get("judge_count")) > 0]
    hard = [row for row in with_judge if int_or_zero(row.get("severe_fail_count")) == 0]
    preferred = [row for row in hard if int_or_zero(row.get("parsed_ok_count")) >= 140]
    eligible = preferred if len({row["candidate"] for row in preferred}) >= 2 else [row for row in hard if int_or_zero(row.get("parsed_ok_count")) >= 137]

    def key(row: dict[str, Any]) -> tuple[Any, ...]:
        return (
            float_or_none(row.get("judge_mean_capped_score")) or -1,
            int_or_zero(row.get("parsed_ok_count")),
            float_or_none(row.get("source_safety_margin")) or -1,
            float_or_none(row.get("main_message_salience")) or -1,
            -int_or_zero(row.get("major_risk_count")),
            -(float_or_none(row.get("three_block_mean_seconds")) or 9999),
            -(float_or_none(row.get("peak_gpu_mib")) or 999999),
        )

    ranked = sorted(eligible, key=key, reverse=True)
    if not unique_candidates:
        return ranked
    best_by_candidate: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in ranked:
        if row["candidate"] in seen:
            continue
        best_by_candidate.append(row)
        seen.add(row["candidate"])
    return best_by_candidate


def write_ranking(rows: list[dict[str, Any]], name: str) -> Path:
    ranked = rank_rows(rows, unique_candidates=False)
    unique = rank_rows(rows, unique_candidates=True)
    payload = {
        "created_at_utc": utc_now(),
        "row_count": len(rows),
        "ranked_checkpoint_count": len(ranked),
        "ranked_unique_candidate_count": len(unique),
        "ranked_checkpoints": ranked,
        "ranked_unique_candidates": unique,
    }
    out = ROOT / "reports" / "phase2" / f"{name}.json"
    write_json(out, payload)
    return out


def finalist_run(candidate: str, template: dict[str, Any], suffix: str) -> dict[str, Any]:
    return {
        "candidate": candidate,
        "run_id": f"phase2_final_{suffix}",
        "stage_label": f"phase2_final_{suffix}",
        "lr": template["lr"],
        "r": template["r"],
        "alpha": template["alpha"],
        "dropout": template["dropout"],
    }


def curve_overfit(rows: list[dict[str, Any]], candidate: str, run_id: str) -> bool:
    curve = [row for row in rows if row["candidate"] == candidate and row["run_id"] == run_id]
    curve = sorted(curve, key=lambda row: row["epoch"])
    if len(curve) < 2:
        return False
    best = max(curve, key=lambda row: float_or_none(row.get("judge_mean_capped_score")) or -1)
    later = [row for row in curve if row["epoch"] > best["epoch"]]
    if not later:
        return False
    best_score = float_or_none(best.get("judge_mean_capped_score")) or 0.0
    best_major = int_or_zero(best.get("major_risk_count"))
    return any((best_score - (float_or_none(row.get("judge_mean_capped_score")) or 0.0) >= 3.0) or (int_or_zero(row.get("major_risk_count")) - best_major >= 3) for row in later)


def curve_still_rising_at_epoch5(rows: list[dict[str, Any]], candidate: str, run_id: str) -> bool:
    curve = [row for row in rows if row["candidate"] == candidate and row["run_id"] == run_id]
    by_epoch = {row["epoch"]: row for row in curve}
    if 4 not in by_epoch or 5 not in by_epoch:
        return False
    e4 = float_or_none(by_epoch[4].get("judge_mean_capped_score")) or -1
    e5 = float_or_none(by_epoch[5].get("judge_mean_capped_score")) or -1
    best_epoch = max(curve, key=lambda row: float_or_none(row.get("judge_mean_capped_score")) or -1)["epoch"]
    return best_epoch == 5 and e5 > e4


def run_final_benchmark(finalists: list[dict[str, Any]]) -> list[dict[str, Any]]:
    benchmark_run_id = f"phase2_final_benchmark_{datetime.now().strftime('%Y%m%d')}"
    judge_run_id = f"phase2_final_benchmark_judge_{datetime.now().strftime('%Y%m%d')}"
    results: list[dict[str, Any]] = []
    for row in finalists:
        system_id = f"phase2_final_{row['candidate']}_{row['run_id']}_epoch_{row['epoch']}"
        system_id = system_id.replace(".", "_").replace("-", "_")
        inference_cmd = [
            "python",
            "scripts/run_finalist_benchmark_inference.py",
            "--candidate-key",
            row["candidate"],
            "--system-id",
            system_id,
            "--benchmark-run-id",
            benchmark_run_id,
            "--adapter-dir",
            row["adapter_dir"],
            "--max-new-tokens",
            "320",
        ]
        post_cmd = ["bash", "scripts/postprocess_final_benchmark_system.sh", benchmark_run_id, judge_run_id, system_id]
        inference = run_logged(f"final_inference_{system_id}", inference_cmd, continue_on_failure=True)
        postprocess = {"skipped": True, "reason": "inference_failed", "exit_code": 99}
        if inference.get("exit_code") == 0:
            postprocess = run_logged(f"final_postprocess_{system_id}", post_cmd, continue_on_failure=True)
        results.append(
            {
                "system_id": system_id,
                "candidate": row["candidate"],
                "run_id": row["run_id"],
                "epoch": row["epoch"],
                "adapter_dir": row["adapter_dir"],
                "benchmark_run_id": benchmark_run_id,
                "judge_run_id": judge_run_id,
                "inference": inference,
                "postprocess": postprocess,
            }
        )
    return results


def final_benchmark_scores(results: list[dict[str, Any]]) -> dict[str, Any]:
    payload: dict[str, Any] = {"systems": {}, "winner": None}
    for item in results:
        summary_path = ROOT / "outputs" / "judge" / item["judge_run_id"] / "scoring" / "accessibility_first_v2" / "system_score_summary.json"
        summary = read_json(summary_path, {})
        system = summary.get("systems", {}).get(item["system_id"])
        if not system:
            continue
        payload["systems"][item["system_id"]] = system
    if payload["systems"]:
        payload["winner"] = max(
            payload["systems"].items(),
            key=lambda kv: float_or_none(kv[1].get("capped_official_item_score", {}).get("mean")) or -1,
        )[0]
    return payload


def write_final_report(rows: list[dict[str, Any]], finalists: list[dict[str, Any]], benchmark_results: list[dict[str, Any]]) -> Path:
    scores = final_benchmark_scores(benchmark_results)
    old_score = 78.055556
    winner_id = scores.get("winner")
    winner_score = None
    if winner_id:
        winner_score = float_or_none(scores["systems"][winner_id].get("capped_official_item_score", {}).get("mean"))
    gap = None if winner_score is None else round(old_score - winner_score, 6)
    recommendation = "blocked_pending_final_judge"
    if gap is not None:
        if gap <= 1.5:
            recommendation = "replace_8b_candidate_a_is_supported"
        elif gap <= 3.0:
            recommendation = "close_but_not_full_replacement"
        else:
            recommendation = "best_small_model_found_but_do_not_claim_8b_equivalence"
    payload = {
        "created_at_utc": utc_now(),
        "old_8b_candidate_a_score": old_score,
        "winner_system_id": winner_id,
        "winner_score": winner_score,
        "gap_to_old_8b": gap,
        "recommendation": recommendation,
        "finalists": finalists,
        "benchmark_results": benchmark_results,
        "final_benchmark_scores": scores,
        "ranked_unique_candidates": rank_rows(rows, unique_candidates=True)[:8],
    }
    json_path = ROOT / "reports" / "final" / "phase2_final_selection_report.json"
    write_json(json_path, payload)
    lines = [
        "# Phase2 Final Selection Report",
        "",
        f"- Created UTC: `{payload['created_at_utc']}`",
        f"- Old 8B Candidate A score: `{old_score}`",
        f"- Winner system id: `{winner_id}`",
        f"- Winner score: `{winner_score}`",
        f"- Gap to old 8B: `{gap}`",
        f"- Recommendation: `{recommendation}`",
        "",
        "## Finalists",
        "",
        "| Candidate | Run | Epoch | Validation score | Parsed | Adapter |",
        "|---|---|---:|---:|---:|---|",
    ]
    for row in finalists:
        lines.append(
            f"| {row['candidate']} | {row['run_id']} | {row['epoch']} | {row.get('judge_mean_capped_score')} | {row.get('parsed_ok_count')}/145 | `{row['adapter_dir']}` |"
        )
    lines.extend(["", "## Final Benchmark Systems", ""])
    for item in benchmark_results:
        system = scores.get("systems", {}).get(item["system_id"], {})
        score = (system.get("capped_official_item_score") or {}).get("mean")
        lines.append(f"- `{item['system_id']}`: score `{score}`, inference exit `{item['inference'].get('exit_code')}`, judge exit `{item['postprocess'].get('exit_code')}`")
    md_path = ROOT / "reports" / "final" / "phase2_final_selection_report.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return md_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run phase2 48-hour search.")
    parser.add_argument("--skip-preflight", action="store_true")
    parser.add_argument("--skip-final-benchmark", action="store_true")
    args = parser.parse_args()

    started = time.time()
    all_runs: list[dict[str, Any]] = list(INITIAL_RUNS)
    write_run_matrix(INITIAL_RUNS)
    manifest_path = source_manifest()
    decision_note(
        "phase2_search_started",
        [
            "# Phase2 48h Search Started",
            "",
            f"- Started UTC: `{utc_now()}`",
            f"- Root: `{ROOT}`",
            f"- Source manifest: `{rel(manifest_path)}`",
            "- Old Stage 2 selection is treated as stale because Qwen completed after it.",
            "- New artifacts remain isolated under phase2_48h_search.",
        ],
    )
    update_status(phase="started", root=str(ROOT), initial_run_count=len(INITIAL_RUNS), openai_api_key_available=bool(os.environ.get("OPENAI_API_KEY")))

    if not args.skip_preflight:
        for candidate in ["phi4_mini_instruct", "llama32_3b_instruct", "ministral3_3b_instruct", "qwen35_4b"]:
            run_logged(f"preflight_{candidate}", preflight_command(candidate), continue_on_failure=True)

    records: list[dict[str, Any]] = []
    for index, run in enumerate(INITIAL_RUNS, start=1):
        update_status(phase="initial_matrix", index=index, total=len(INITIAL_RUNS), current_run=run)
        record = run_train_and_postprocess(run)
        records.append(record)
        write_json(ROOT / "reports" / "phase2" / "phase2_initial_execution_records.json", records)

    rows = collect_rows(all_runs)
    ranking_path = write_ranking(rows, "phase2_after_initial_ranking")
    unique = rank_rows(rows, unique_candidates=True)
    finalists_seed = unique[:2]
    decision_note(
        "phase2_initial_top2_selected",
        [
            "# Phase2 Initial Top 2 Selected",
            "",
            f"- Ranking report: `{rel(ranking_path)}`",
            "",
            "| Rank | Candidate | Run | Epoch | Score | Parsed | Major risk |",
            "|---:|---|---|---:|---:|---:|---:|",
            *[
                f"| {i} | {row['candidate']} | {row['run_id']} | {row['epoch']} | {row.get('judge_mean_capped_score')} | {row.get('parsed_ok_count')}/145 | {row.get('major_risk_count')} |"
                for i, row in enumerate(finalists_seed, start=1)
            ],
        ],
    )

    finalist_runs: list[dict[str, Any]] = []
    for row in finalists_seed:
        finalist_runs.append(finalist_run(row["candidate"], FINALIST_TEMPLATE, "r64_a128_lr1p5e4"))
    write_run_matrix(finalist_runs, "phase2_finalist_run_matrix")
    all_runs.extend(finalist_runs)
    for index, run in enumerate(finalist_runs, start=1):
        update_status(phase="finalist_matrix", index=index, total=len(finalist_runs), current_run=run)
        records.append(run_train_and_postprocess(run))
        write_json(ROOT / "reports" / "phase2" / "phase2_execution_records.json", records)

    rows = collect_rows(all_runs)
    optional_runs: list[dict[str, Any]] = []
    for run in finalist_runs:
        if curve_overfit(rows, run["candidate"], run["run_id"]):
            optional_runs.append(finalist_run(run["candidate"], DROPOUT_TEMPLATE, "r64_a128_lr1p5e4_dropout10"))
        if curve_still_rising_at_epoch5(rows, run["candidate"], run["run_id"]):
            optional_runs.append(finalist_run(run["candidate"], ALPHA4_TEMPLATE, "r64_a256_lr1p5e4"))
    if optional_runs:
        write_run_matrix(optional_runs, "phase2_optional_finalist_run_matrix")
        all_runs.extend(optional_runs)
        for index, run in enumerate(optional_runs, start=1):
            update_status(phase="optional_finalist_matrix", index=index, total=len(optional_runs), current_run=run)
            records.append(run_train_and_postprocess(run))
            write_json(ROOT / "reports" / "phase2" / "phase2_execution_records.json", records)

    rows = collect_rows(all_runs)
    final_ranking_path = write_ranking(rows, "phase2_final_validation_ranking")
    final_unique = rank_rows(rows, unique_candidates=True)
    finalists = final_unique[:2]
    write_json(ROOT / "reports" / "phase2" / "phase2_selected_finalists.json", {"created_at_utc": utc_now(), "finalists": finalists, "ranking_path": rel(final_ranking_path)})

    benchmark_results: list[dict[str, Any]] = []
    if not args.skip_final_benchmark and finalists:
        update_status(phase="final_benchmark", finalist_count=len(finalists), finalists=finalists)
        benchmark_results = run_final_benchmark(finalists)
        write_json(ROOT / "reports" / "phase2" / "phase2_final_benchmark_execution.json", benchmark_results)

    report_path = write_final_report(rows, finalists, benchmark_results)
    run_logged("generate_evidence_inventory_after_phase2", ["python", "scripts/generate_evidence_inventory.py"], continue_on_failure=True)
    update_status(
        phase="completed",
        runtime_seconds=round(time.time() - started, 2),
        report_path=rel(report_path),
        final_ranking_path=rel(final_ranking_path),
        finalist_count=len(finalists),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
