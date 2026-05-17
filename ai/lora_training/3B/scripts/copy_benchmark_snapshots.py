#!/usr/bin/env python
"""Copy read-only benchmark source artifacts into the isolated sweep workspace."""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OLD_TEST_WINDOWS = Path(r"C:\Users\Aufb\Desktop\fit5120\iteration1\test")
OLD_TEST_WSL = Path("/mnt/c/Users/Aufb/Desktop/fit5120/iteration1/test")
OLD_TEST = OLD_TEST_WINDOWS if OLD_TEST_WINDOWS.exists() else OLD_TEST_WSL
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")


ARTIFACTS = [
    (
        "benchmark_prepared_inputs",
        "dyslexia_benchmark_handoff/03_project_workspace/09_run_config/worker_20_dataset_manifest_and_freeze_inputs/prepared_inputs.jsonl",
    ),
    (
        "benchmark_prepared_inputs",
        "dyslexia_benchmark_handoff/03_project_workspace/09_run_config/worker_20_dataset_manifest_and_freeze_inputs/preparation_manifest.json",
    ),
    (
        "benchmark_prepared_inputs",
        "dyslexia_benchmark_handoff/03_project_workspace/09_run_config/worker_20_dataset_manifest_and_freeze_inputs/prepared_inputs_validation_report.json",
    ),
    (
        "benchmark_prepared_inputs",
        "dyslexia_benchmark_handoff/03_project_workspace/09_run_config/worker_20_dataset_manifest_and_freeze_inputs/source_dataset_manifest.json",
    ),
    (
        "benchmark_prepared_inputs",
        "dyslexia_benchmark_handoff/03_project_workspace/09_run_config/worker_20_dataset_manifest_and_freeze_inputs/rejection_summary.json",
    ),
    (
        "benchmark_prepared_inputs",
        "dyslexia_benchmark_handoff/03_project_workspace/09_run_config/worker_20_dataset_manifest_and_freeze_inputs/rejections.jsonl",
    ),
    (
        "benchmark_prepared_inputs",
        "dyslexia_benchmark_handoff/03_project_workspace/09_run_config/worker_20_dataset_manifest_and_freeze_inputs/dataset_access_log.json",
    ),
    (
        "benchmark_prepared_inputs",
        "dyslexia_benchmark_handoff/03_project_workspace/09_run_config/worker_20_dataset_manifest_and_freeze_inputs/freeze_input_candidate_worker_20/freeze_input_candidate_manifest.json",
    ),
    (
        "benchmark_freeze_manifests",
        "dyslexia_benchmark_handoff/03_project_workspace/09_run_config/worker_21_final_freeze_preflight/final_freeze_manifest.json",
    ),
    (
        "benchmark_freeze_manifests",
        "dyslexia_benchmark_handoff/03_project_workspace/09_run_config/worker_21_final_freeze_preflight/artifact_hashes.json",
    ),
    (
        "benchmark_freeze_manifests",
        "dyslexia_benchmark_handoff/03_project_workspace/09_run_config/worker_21_final_freeze_preflight/model_backend_manifest.json",
    ),
    (
        "benchmark_freeze_manifests",
        "dyslexia_benchmark_handoff/03_project_workspace/09_run_config/worker_21_final_freeze_preflight/judge_manifest.json",
    ),
    (
        "benchmark_freeze_manifests",
        "dyslexia_benchmark_handoff/03_project_workspace/09_run_config/worker_21_final_freeze_preflight/scoring_manifest.json",
    ),
    ("baseline_benchmark_df_strict_20260504_fz1", "df_runs/df_strict_20260504_fz1/scoring/accessibility_first_v2/system_score_summary.json"),
    ("baseline_benchmark_df_strict_20260504_fz1", "df_runs/df_strict_20260504_fz1/scoring/accessibility_first_v2/parse_product_readiness_summary.json"),
    ("baseline_benchmark_df_strict_20260504_fz1", "df_runs/df_strict_20260504_fz1/scoring/accessibility_first_v2/score_distribution_summary.json"),
    ("baseline_benchmark_df_strict_20260504_fz1", "df_runs/df_strict_20260504_fz1/scoring/accessibility_first_v2/worker_25_scoring_manifest.json"),
    ("baseline_benchmark_df_strict_20260504_fz1", "df_runs/df_strict_20260504_fz1/scoring/accessibility_first_v2/worker_25_scoring_validation_report.json"),
    ("baseline_benchmark_df_strict_20260504_fz1", "df_runs/df_strict_20260504_fz1/scoring/accessibility_first_v2/item_scores.jsonl"),
    ("baseline_benchmark_df_strict_20260504_fz1", "df_runs/df_strict_20260504_fz1/reports/final_benchmark_report.md"),
    ("baseline_benchmark_df_strict_20260504_fz1", "df_runs/df_strict_20260504_fz1/model_raw_outputs/clearread_llama31_8b_qlora_candidate_a/raw_outputs.jsonl"),
    ("baseline_benchmark_df_strict_20260504_fz1", "df_runs/df_strict_20260504_fz1/model_raw_outputs/llama31_8b_base_prompt_only/raw_outputs.jsonl"),
    ("baseline_benchmark_df_strict_20260504_fz1", "df_runs/df_strict_20260504_fz1/model_raw_outputs/qwen3_8b_prompt_only/raw_outputs.jsonl"),
    ("baseline_benchmark_df_strict_20260504_fz1", "df_runs/df_strict_20260504_fz1/parsed_outputs/clearread_llama31_8b_qlora_candidate_a/parsed_outputs.jsonl"),
    ("baseline_benchmark_df_strict_20260504_fz1", "df_runs/df_strict_20260504_fz1/parsed_outputs/llama31_8b_base_prompt_only/parsed_outputs.jsonl"),
    ("baseline_benchmark_df_strict_20260504_fz1", "df_runs/df_strict_20260504_fz1/parsed_outputs/qwen3_8b_prompt_only/parsed_outputs.jsonl"),
    ("baseline_benchmark_df_strict_20260504_fz1", "df_runs/df_strict_20260504_fz1/parse_failures/clearread_llama31_8b_qlora_candidate_a/parse_failures.jsonl"),
    ("baseline_benchmark_df_strict_20260504_fz1", "df_runs/df_strict_20260504_fz1/parse_failures/llama31_8b_base_prompt_only/parse_failures.jsonl"),
    ("baseline_benchmark_df_strict_20260504_fz1", "df_runs/df_strict_20260504_fz1/parse_failures/qwen3_8b_prompt_only/parse_failures.jsonl"),
    ("baseline_final_reports", "dyslexia_benchmark_handoff/03_project_workspace/10_final_report/final_submission_report_en.md"),
    ("baseline_final_reports", "dyslexia_benchmark_handoff/03_project_workspace/10_final_report/final_submission_report_zh.md"),
    ("baseline_final_reports", "dyslexia_benchmark_handoff/03_project_workspace/10_final_report/submission_ready_final_report_en.md"),
    ("baseline_final_reports", "dyslexia_benchmark_handoff/03_project_workspace/10_final_report/submission_ready_final_report_zh.md"),
    ("baseline_final_reports", "dyslexia_benchmark_handoff/03_project_workspace/10_final_report/worker_26_final_benchmark_report.md"),
    ("legacy_project_scripts", "dyslexia_benchmark_handoff/03_project_workspace/scripts/benchmark_harness.py"),
    ("legacy_project_scripts", "dyslexia_benchmark_handoff/03_project_workspace/scripts/freeze_scaffold.py"),
    ("legacy_project_scripts", "dyslexia_benchmark_handoff/03_project_workspace/scripts/model_backend_adapters.py"),
    ("legacy_project_scripts", "dyslexia_benchmark_handoff/03_project_workspace/scripts/prepare_benchmark_inputs.py"),
    ("legacy_project_scripts", "dyslexia_benchmark_handoff/03_project_workspace/scripts/run_frozen_model_inference.py"),
    ("legacy_project_scripts", "dyslexia_benchmark_handoff/03_project_workspace/scripts/run_worker_17_synthetic_judge_smoke_v1_1.py"),
    ("legacy_project_scripts", "dyslexia_benchmark_handoff/03_project_workspace/scripts/synthetic_backend_adapter_test.py"),
    ("legacy_project_scripts", "dyslexia_benchmark_handoff/03_project_workspace/scripts/synthetic_fixture_test.py"),
    ("legacy_project_scripts", "dyslexia_benchmark_handoff/03_project_workspace/scripts/synthetic_model_smoke_test.py"),
    ("legacy_project_scripts", "dyslexia_benchmark_handoff/03_project_workspace/scripts/validate_prepared_inputs.py"),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def destination_for(group: str, relative_source: str) -> Path:
    return ROOT / "data" / "source_snapshot" / group / relative_source.replace("/", "__")


def copy_one(group: str, relative_source: str) -> dict[str, Any]:
    src = OLD_TEST / Path(relative_source)
    dst = destination_for(group, relative_source)
    row: dict[str, Any] = {
        "group": group,
        "relative_source": relative_source,
        "source_path": str(src),
        "destination_path": str(dst),
        "copied_at_utc": utc_now(),
    }
    if not src.exists():
        row["status"] = "missing_source"
        return row
    src_hash = sha256_file(src)
    row["source_size_bytes"] = src.stat().st_size
    row["source_sha256"] = src_hash
    if dst.exists():
        dst_hash = sha256_file(dst)
        row["existing_destination_sha256"] = dst_hash
        row["existing_destination_size_bytes"] = dst.stat().st_size
        if dst_hash == src_hash:
            row["status"] = "already_present_same_hash"
            return row
        dst = dst.with_name(f"{dst.name}.newcopy_{STAMP}")
        row["destination_path"] = str(dst)
        row["status"] = "copied_to_collision_safe_name"
    else:
        row["status"] = "copied"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    row["destination_size_bytes"] = dst.stat().st_size
    row["destination_sha256"] = sha256_file(dst)
    return row


def main() -> int:
    rows = [copy_one(group, relative_source) for group, relative_source in ARTIFACTS]
    manifest = {
        "created_at_utc": utc_now(),
        "source_root": str(OLD_TEST),
        "destination_root": str(ROOT / "data" / "source_snapshot"),
        "policy": "copy whitelisted old benchmark artifacts only; no deletion; no overwrite on hash mismatch",
        "artifact_count": len(rows),
        "status_counts": {status: sum(1 for row in rows if row.get("status") == status) for status in sorted({str(row.get("status")) for row in rows})},
        "artifacts": rows,
    }
    manifest_path = ROOT / "data" / "source_snapshot" / "benchmark_snapshot_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"manifest": str(manifest_path), "status_counts": manifest["status_counts"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
