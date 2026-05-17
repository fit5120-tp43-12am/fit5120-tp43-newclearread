#!/usr/bin/env python
"""Run the compressed local Phase2 plan after the Phi r64 postprocess boundary."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from phase2_status import update_status


ROOT = Path(__file__).resolve().parents[1]
OLD_8B_SCORE = 78.055556
LEAD_GAP_FOR_R64 = 3.0
EPOCHS = [1, 2, 3, 4, 5]
CANDIDATES = ["phi4_mini_instruct", "llama32_3b_instruct", "ministral3_3b_instruct"]


CHALLENGER_RUNS = [
    {
        "candidate": "llama32_3b_instruct",
        "run_id": "phase2_r32_a64_lr1p5e4",
        "stage_label": "phase2_r32_a64_lr1p5e4",
        "lr": 0.00015,
        "r": 32,
        "alpha": 64,
        "dropout": 0.05,
    },
    {
        "candidate": "ministral3_3b_instruct",
        "run_id": "phase2_r32_a64_lr1p5e4",
        "stage_label": "phase2_r32_a64_lr1p5e4",
        "lr": 0.00015,
        "r": 32,
        "alpha": 64,
        "dropout": 0.05,
    },
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


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
    update_status(phase="compressed_command_running", command_name=name, cmd=cmd, log_path=rel(log_path))
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
    append_jsonl(ROOT / "logs" / "tests" / "phase2_compressed_command_history.jsonl", record)
    update_status(phase="compressed_command_finished", command_name=name, exit_code=proc.returncode, log_path=rel(log_path))
    if proc.returncode != 0 and not continue_on_failure:
        raise RuntimeError(f"{name} failed with exit code {proc.returncode}; see {log_path}")
    return record


def train_command(run: dict[str, Any], *, seed: int | None = None) -> list[str]:
    cmd = [
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
    if seed is not None:
        # The fallback shell does not expose seed, so seed sanity uses direct Python command.
        return [
            "python",
            "scripts/train_sweep_qlora.py",
            "--candidate-key",
            run["candidate"],
            "--run-id",
            run["run_id"],
            "--epochs",
            "5",
            "--learning-rate",
            str(run["lr"]),
            "--lora-r",
            str(run["r"]),
            "--lora-alpha",
            str(run["alpha"]),
            "--lora-dropout",
            str(run["dropout"]),
            "--per-device-train-batch-size",
            "2",
            "--gradient-accumulation-steps",
            "4",
            "--seed",
            str(seed),
        ]
    return cmd


def postprocess_command(run: dict[str, Any]) -> list[str]:
    return [
        "bash",
        "scripts/postprocess_run_candidate_top_epochs.sh",
        run["candidate"],
        run["run_id"],
        run["stage_label"],
        f"val50_{run['candidate']}_{run['stage_label']}",
        "1 2 3 4 5",
    ]


def training_complete(run: dict[str, Any]) -> bool:
    result = read_json(
        ROOT / "model_workspaces" / run["candidate"] / "outputs" / "training" / f"{run['run_id']}_training_result.json",
        {},
    )
    if result.get("status") != "success":
        return False
    adapter_root = ROOT / "model_workspaces" / run["candidate"] / "models" / "adapters"
    return all((adapter_root / f"{run['run_id']}_epoch_{epoch}").exists() for epoch in EPOCHS)


def postprocess_complete(run: dict[str, Any]) -> bool:
    return any((ROOT / "logs" / "decisions").glob(f"{run['candidate']}_{run['run_id']}_checkpoint_selection_*.md"))


def run_training_and_top_postprocess(run: dict[str, Any], *, seed: int | None = None) -> dict[str, Any]:
    record: dict[str, Any] = {"run": run, "started_at_utc": utc_now()}
    if training_complete(run):
        record["training"] = {"skipped": True, "reason": "already_complete", "exit_code": 0}
    else:
        record["training"] = run_logged(f"compressed_train_{run['candidate']}_{run['run_id']}", train_command(run, seed=seed), continue_on_failure=True)
    if record["training"].get("exit_code") != 0:
        record["status"] = "training_failed"
        return record
    if postprocess_complete(run):
        record["postprocess"] = {"skipped": True, "reason": "already_complete", "exit_code": 0}
    else:
        record["postprocess"] = run_logged(f"compressed_postprocess_{run['candidate']}_{run['run_id']}", postprocess_command(run), continue_on_failure=True)
    record["status"] = "success" if record["postprocess"].get("exit_code") == 0 else "postprocess_failed"
    return record


def parse_system_id(system_id: str) -> dict[str, Any] | None:
    for candidate in CANDIDATES:
        prefix = f"{candidate}_"
        if not system_id.startswith(prefix) or "_epoch_" not in system_id:
            continue
        rest = system_id[len(prefix) :]
        stage_label, epoch_text = rest.rsplit("_epoch_", 1)
        try:
            epoch = int(epoch_text)
        except ValueError:
            return None
        return {"candidate": candidate, "stage_label": stage_label, "run_id": stage_label, "epoch": epoch}
    return None


def validation_metrics(candidate: str, run_id: str, epoch: int) -> dict[str, Any]:
    path = ROOT / "model_workspaces" / candidate / "outputs" / "validation" / f"{run_id}_epoch_{epoch}_record_messages" / "metrics.json"
    metrics = read_json(path, {})
    counts = metrics.get("counts", {})
    return {
        "metrics_path": rel(path) if path.exists() else None,
        "parsed_ok_count": int(counts.get("parsed_ok_count", 0)),
        "raw_output_count": int(counts.get("raw_output_count", 0)),
        "parse_failure_count": int(counts.get("parse_failure_count", 0)),
    }


def judged_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in (ROOT / "outputs" / "judge").glob("*/scoring/accessibility_first_v2/system_score_summary.json"):
        summary = read_json(path, {})
        for system_id, system in (summary.get("systems") or {}).items():
            parsed_id = parse_system_id(system_id)
            if parsed_id is None:
                continue
            score = system.get("capped_official_item_score", {})
            fields = system.get("per_field_mean_scores", {})
            safety = system.get("safety_level_counts", {})
            metrics = validation_metrics(parsed_id["candidate"], parsed_id["run_id"], parsed_id["epoch"])
            row = {
                **parsed_id,
                "system_id": system_id,
                "judge_run_id": summary.get("judge_run_id"),
                "judge_summary_path": rel(path),
                "judge_mean_capped_score": score.get("mean"),
                "judge_count": score.get("count", 0),
                "source_safety_margin": fields.get("source_safety_margin"),
                "main_message_salience": fields.get("main_message_salience_and_quick_understanding"),
                "major_risk_count": safety.get("major_risk", 999),
                "severe_fail_count": safety.get("severe_fail", 999),
                **metrics,
            }
            adapter_dir = ROOT / "model_workspaces" / row["candidate"] / "models" / "adapters" / f"{row['run_id']}_epoch_{row['epoch']}"
            row["adapter_dir"] = adapter_dir.as_posix()
            rows.append(row)
    return rows


def eligible(row: dict[str, Any]) -> bool:
    severe_fail_count = row.get("severe_fail_count")
    if severe_fail_count is None:
        severe_fail_count = 999
    return (
        row.get("judge_mean_capped_score") is not None
        and int(row.get("parsed_ok_count") or 0) >= 137
        and int(severe_fail_count) == 0
    )


def rank_key(row: dict[str, Any]) -> tuple[Any, ...]:
    major_risk_count = row.get("major_risk_count")
    if major_risk_count is None:
        major_risk_count = 999
    return (
        float(row.get("judge_mean_capped_score") or -1),
        int(row.get("parsed_ok_count") or 0),
        -int(major_risk_count),
        float(row.get("source_safety_margin") or -1),
        float(row.get("main_message_salience") or -1),
    )


def best_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted([row for row in rows if eligible(row)], key=rank_key, reverse=True)


def best_for_candidate(candidate: str) -> dict[str, Any] | None:
    rows = [row for row in best_rows(judged_rows()) if row["candidate"] == candidate]
    return rows[0] if rows else None


def maybe_add_r64(candidate: str, current_leader: dict[str, Any]) -> dict[str, Any] | None:
    best = best_for_candidate(candidate)
    if best is None:
        decision_note(
            f"compressed_{candidate}_r64_skipped_no_eligible_lr",
            [f"# {candidate} r64 Skipped", "", "- Reason: no eligible lr1.5e-4 checkpoint after hard filters."],
        )
        return None
    gap = float(current_leader["judge_mean_capped_score"]) - float(best["judge_mean_capped_score"])
    if gap > LEAD_GAP_FOR_R64:
        decision_note(
            f"compressed_{candidate}_r64_skipped_gap",
            [
                f"# {candidate} r64 Skipped",
                "",
                f"- Best challenger score: `{best['judge_mean_capped_score']}`",
                f"- Current leader score: `{current_leader['judge_mean_capped_score']}`",
                f"- Gap: `{round(gap, 6)}`",
                f"- Rule: skip r64 when gap is greater than `{LEAD_GAP_FOR_R64}`.",
            ],
        )
        return None
    return {
        "candidate": candidate,
        "run_id": "phase2_r64_a128_lr1e4",
        "stage_label": "phase2_r64_a128_lr1e4",
        "lr": 0.0001,
        "r": 64,
        "alpha": 128,
        "dropout": 0.05,
    }


def final_benchmark(finalists: list[dict[str, Any]]) -> list[dict[str, Any]]:
    benchmark_run_id = f"phase2_compressed_final_benchmark_{datetime.now().strftime('%Y%m%d')}"
    judge_run_id = f"phase2_compressed_final_benchmark_judge_{datetime.now().strftime('%Y%m%d')}"
    results: list[dict[str, Any]] = []
    for row in finalists:
        system_id = f"compressed_final_{row['candidate']}_{row['run_id']}_epoch_{row['epoch']}"
        inference = run_logged(
            f"compressed_final_inference_{system_id}",
            [
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
            ],
            continue_on_failure=True,
        )
        post = {"skipped": True, "reason": "inference_failed", "exit_code": 99}
        if inference.get("exit_code") == 0:
            post = run_logged(
                f"compressed_final_postprocess_{system_id}",
                ["bash", "scripts/postprocess_final_benchmark_system.sh", benchmark_run_id, judge_run_id, system_id],
                continue_on_failure=True,
            )
        results.append({"system_id": system_id, "source_row": row, "benchmark_run_id": benchmark_run_id, "judge_run_id": judge_run_id, "inference": inference, "postprocess": post})
    return results


def final_scores(results: list[dict[str, Any]]) -> dict[str, Any]:
    systems: dict[str, Any] = {}
    for item in results:
        summary = read_json(ROOT / "outputs" / "judge" / item["judge_run_id"] / "scoring" / "accessibility_first_v2" / "system_score_summary.json", {})
        for key, value in (summary.get("systems") or {}).items():
            systems[key] = value
    winner = None
    if systems:
        winner = max(systems, key=lambda key: float(systems[key].get("capped_official_item_score", {}).get("mean") or -1))
    return {"systems": systems, "winner": winner}


def write_candidate_ranking(path: Path, rows: list[dict[str, Any]]) -> None:
    payload = {
        "created_at_utc": utc_now(),
        "old_8b_candidate_a_score": OLD_8B_SCORE,
        "hard_filters": {"min_parsed": 137, "severe_fail": 0},
        "ranked_rows": best_rows(rows),
    }
    write_json(path, payload)


def seed_run_from_row(row: dict[str, Any]) -> dict[str, Any]:
    run_id = f"phase2_seed5141_{row['run_id']}_epoch{row['epoch']}"
    if "r64_a128_lr1e4" in row["run_id"]:
        lr, r, alpha = 0.0001, 64, 128
    elif "r32_a64_lr1p5e4" in row["run_id"]:
        lr, r, alpha = 0.00015, 32, 64
    else:
        lr, r, alpha = 0.0001, 32, 64
    return {"candidate": row["candidate"], "run_id": run_id, "stage_label": run_id, "lr": lr, "r": r, "alpha": alpha, "dropout": 0.05}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run compressed local Phase2 plan.")
    parser.add_argument("--skip-final-benchmark", action="store_true")
    parser.add_argument("--skip-seed-sanity", action="store_true")
    args = parser.parse_args()

    started = time.time()
    update_status(phase="compressed_started", command_name=None, updated_reason="compressed_plan_takeover")
    decision_note(
        "compressed_plan_takeover",
        [
            "# Compressed Phase2 Plan Takeover",
            "",
            f"- Started UTC: `{utc_now()}`",
            "- The old full matrix was superseded after the Phi r64 postprocess boundary.",
            "- New rule: run only Llama/Ministral lr1.5e-4 challengers first; r64 only if within 3 points of the current leader.",
        ],
    )

    records: list[dict[str, Any]] = []
    for run in CHALLENGER_RUNS:
        records.append(run_training_and_top_postprocess(run))
        write_json(ROOT / "reports" / "phase2" / "compressed_execution_records.json", records)
        leader = best_rows(judged_rows())[0]
        optional = maybe_add_r64(run["candidate"], leader)
        if optional is not None:
            records.append(run_training_and_top_postprocess(optional))
            write_json(ROOT / "reports" / "phase2" / "compressed_execution_records.json", records)

    rows = judged_rows()
    ranking_path = ROOT / "reports" / "phase2" / "compressed_candidate_ranking.json"
    write_candidate_ranking(ranking_path, rows)
    ranked = best_rows(rows)
    finalists = ranked[:2]
    write_json(ROOT / "reports" / "phase2" / "compressed_selected_finalists.json", {"created_at_utc": utc_now(), "finalists": finalists})

    benchmark_results: list[dict[str, Any]] = []
    scores: dict[str, Any] = {}
    if finalists and not args.skip_final_benchmark:
        benchmark_results = final_benchmark(finalists)
        scores = final_scores(benchmark_results)
        write_json(ROOT / "reports" / "phase2" / "compressed_final_benchmark_execution.json", benchmark_results)

    seed_record: dict[str, Any] | None = None
    winner_row = finalists[0] if finalists else None
    if scores.get("winner"):
        winner_system = scores["winner"]
        for item in benchmark_results:
            if item["system_id"] == winner_system:
                winner_row = item["source_row"]
                break
    if winner_row and not args.skip_seed_sanity:
        seed_run = seed_run_from_row(winner_row)
        seed_record = run_training_and_top_postprocess(seed_run, seed=5141)
        write_json(ROOT / "reports" / "phase2" / "compressed_seed_sanity_record.json", seed_record)

    final_report = {
        "created_at_utc": utc_now(),
        "runtime_seconds": round(time.time() - started, 2),
        "old_8b_candidate_a_score": OLD_8B_SCORE,
        "ranking_path": str(ranking_path.relative_to(ROOT)),
        "finalists": finalists,
        "benchmark_results": benchmark_results,
        "final_scores": scores,
        "seed_sanity_record": seed_record,
    }
    write_json(ROOT / "reports" / "final" / "compressed_phase2_final_selection_report.json", final_report)
    run_logged("compressed_generate_evidence_inventory", ["python", "scripts/generate_evidence_inventory.py"], continue_on_failure=True)
    update_status(phase="compressed_completed", runtime_seconds=round(time.time() - started, 2), report_path="reports/final/compressed_phase2_final_selection_report.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
