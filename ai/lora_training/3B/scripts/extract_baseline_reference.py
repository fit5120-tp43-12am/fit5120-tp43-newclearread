#!/usr/bin/env python
"""Extract copied old benchmark baseline numbers into a compact reference file."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASELINE_SUMMARY = (
    ROOT
    / "data"
    / "source_snapshot"
    / "baseline_benchmark_df_strict_20260504_fz1"
    / "df_runs__df_strict_20260504_fz1__scoring__accessibility_first_v2__system_score_summary.json"
)
READINESS_SUMMARY = (
    ROOT
    / "data"
    / "source_snapshot"
    / "baseline_benchmark_df_strict_20260504_fz1"
    / "df_runs__df_strict_20260504_fz1__scoring__accessibility_first_v2__parse_product_readiness_summary.json"
)
OUT_PATH = ROOT / "reports" / "baseline_reference" / "old_benchmark_baseline_reference.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    summary = load_json(BASELINE_SUMMARY)
    readiness = load_json(READINESS_SUMMARY) if READINESS_SUMMARY.exists() else {}
    systems: dict[str, Any] = {}
    for system_id, system in summary.get("systems", {}).items():
        score = system.get("capped_official_item_score", {})
        systems[system_id] = {
            "system_id": system_id,
            "model_id": system.get("model_id"),
            "capped_official_item_score_mean": score.get("mean"),
            "schema_valid_judge_output_count": system.get("schema_valid_judge_output_count"),
            "judge_input_count": system.get("judge_input_count"),
            "judge_validation_failure_count": system.get("judge_validation_failure_count"),
            "source_safety_margin": system.get("per_field_mean_scores", {}).get("source_safety_margin"),
            "main_message_salience": system.get("per_field_mean_scores", {}).get(
                "main_message_salience_and_quick_understanding"
            ),
            "safety_level_counts": system.get("safety_level_counts"),
        }
    payload = {
        "created_at_utc": utc_now(),
        "source_system_score_summary": str(BASELINE_SUMMARY.relative_to(ROOT)),
        "source_parse_product_readiness_summary": str(READINESS_SUMMARY.relative_to(ROOT)),
        "note": "Old baseline numbers are copied read-only references, not rerun in the new sweep.",
        "systems": systems,
        "parse_product_readiness_summary": readiness,
        "expected_reference_numbers_from_plan": {
            "clearread_llama31_8b_qlora_candidate_a": {"score": 78.055556, "parsed": "144/145"},
            "qwen3_8b_prompt_only": {"score": 72.853659, "parsed": "123/145"},
            "llama31_8b_base_prompt_only": {"score": 68.666667, "parsed": "18/145"},
        },
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUT_PATH), "systems": sorted(systems)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
