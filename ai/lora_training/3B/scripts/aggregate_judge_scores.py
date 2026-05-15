from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LEGACY_PROJECT_SCRIPTS = ROOT / "scripts" / "legacy_old_harness" / "project_scripts"
if str(LEGACY_PROJECT_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(LEGACY_PROJECT_SCRIPTS))

from freeze_scaffold import ACTIVE_SCORE_WEIGHTS, SAFETY_CAPS, aggregate_judge_output, sha256_json  # type: ignore  # noqa: E402


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
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


def stats(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"count": 0, "mean": None, "median": None, "min": None, "max": None, "standard_deviation": None}
    return {"count": len(values), "mean": round(statistics.fmean(values), 6), "median": round(statistics.median(values), 6), "min": round(min(values), 6), "max": round(max(values), 6), "standard_deviation": round(statistics.pstdev(values), 6)}


def rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6) if denominator else 0.0


def active_field_scores(aggregate: dict[str, Any]) -> dict[str, Any]:
    active = aggregate["source_fields_used"]["active_accessibility_score_inputs"]
    return {field: {"score": active[field]["score"], "weight": active[field]["weight"], "weighted_points": active[field]["weighted_points"]} for field, _ in ACTIVE_SCORE_WEIGHTS}


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate judge outputs for the base-model shootout.")
    parser.add_argument("--judge-run-id", required=True)
    args = parser.parse_args()

    settings = read_json(ROOT / "configs" / "eval_settings.json")
    judge_model = settings["judge_policy"]["judge_model"].replace(".", "_").replace("-", "_")
    candidates = read_json(ROOT / "configs" / "model_candidates.json")["candidates"]
    judge_root = ROOT / "outputs" / "judge" / args.judge_run_id
    scoring_dir = judge_root / "scoring" / "accessibility_first_v2"
    candidates = [
        candidate
        for candidate in candidates
        if (judge_root / "judge_inputs" / candidate["key"] / "judge_input_manifest.json").exists()
    ]

    systems: dict[str, Any] = {}
    all_item_rows: list[dict[str, Any]] = []
    ranking: list[dict[str, Any]] = []
    for candidate in candidates:
        key = candidate["key"]
        input_manifest = read_json(judge_root / "judge_inputs" / key / "judge_input_manifest.json", {})
        judge_dir = judge_root / "judge_outputs" / judge_model / key
        parsed_outputs = read_jsonl(judge_dir / "judge_outputs.jsonl")
        parsed_ids = {row.get("judge_input_id") for row in parsed_outputs}
        unresolved_failures = [row for row in read_jsonl(judge_dir / "judge_validation_failures.jsonl") if row.get("judge_input_id") and row.get("judge_input_id") not in parsed_ids]
        item_rows: list[dict[str, Any]] = []
        for row in parsed_outputs:
            parsed = row["parsed_judge_output"]
            aggregate = aggregate_judge_output(parsed, source_file=judge_dir / "judge_outputs.jsonl")
            item = {
                "aggregation_schema_version": "base_shootout_accessibility_first_v2_item_score",
                "judge_run_id": args.judge_run_id,
                "run_id": row["run_id"],
                "system_id": key,
                "model_id": candidate["model_id"],
                "record_run_id": row["record_run_id"],
                "input_id": row["input_id"],
                "judge_input_id": row["judge_input_id"],
                "parsed_judge_output_sha256": row["parsed_judge_output_sha256"],
                "item_score_sha256": sha256_json(aggregate),
                "weighted_accessibility_score_before_cap": aggregate["weighted_accessibility_score_before_cap"],
                "derived_safety_level": aggregate["derived_safety_level"],
                "safety_cap_max_score": aggregate["safety_cap_max_score"],
                "capped_official_item_score": aggregate["capped_official_item_score"],
                "ranking_status": aggregate["ranking_status"],
                "safety_cap_applied": aggregate["safety_cap_applied"],
                "active_field_scores": active_field_scores(aggregate),
                "safety_derivation_triggers": aggregate["safety_derivation_triggers"],
            }
            item_rows.append(item)
            all_item_rows.append(item)
        capped = [float(row["capped_official_item_score"]) for row in item_rows]
        weighted = [float(row["weighted_accessibility_score_before_cap"]) for row in item_rows]
        safety_counts = Counter(row["derived_safety_level"] for row in item_rows)
        ranking_counts = Counter(row["ranking_status"] for row in item_rows)
        field_means: dict[str, Any] = {}
        for field, _weight in ACTIVE_SCORE_WEIGHTS:
            values = [float(row["active_field_scores"][field]["score"]) for row in item_rows]
            field_means[field] = round(statistics.fmean(values), 6) if values else None
        prepared_count = int(input_manifest.get("judge_input_count", 0))
        systems[key] = {
            "system_id": key,
            "model_id": candidate["model_id"],
            "judge_input_count": prepared_count,
            "schema_valid_judge_output_count": len(item_rows),
            "judge_validation_failure_count": len(unresolved_failures),
            "judge_valid_rate_over_prepared_inputs": rate(len(item_rows), prepared_count),
            "weighted_accessibility_score_before_cap": stats(weighted),
            "capped_official_item_score": stats(capped),
            "safety_level_counts": {level: int(safety_counts.get(level, 0)) for level in SAFETY_CAPS},
            "safety_level_rates": {level: rate(int(safety_counts.get(level, 0)), len(item_rows)) for level in SAFETY_CAPS},
            "ranking_status_counts": dict(sorted(ranking_counts.items())),
            "per_field_mean_scores": field_means,
            "safety_cap_applied_count": sum(1 for row in item_rows if row["safety_cap_applied"]),
            "safety_cap_applied_rate": rate(sum(1 for row in item_rows if row["safety_cap_applied"]), len(item_rows)),
        }
        ranking.append({"system_id": key, "model_id": candidate["model_id"], "mean_capped_official_item_score": stats(capped)["mean"], "schema_valid_judge_output_count": len(item_rows), "judge_valid_rate_over_prepared_inputs": rate(len(item_rows), prepared_count)})
        write_jsonl(scoring_dir / "item_scores" / f"{key}.jsonl", item_rows)

    ranking = sorted(ranking, key=lambda row: (row["mean_capped_official_item_score"] is not None, row["mean_capped_official_item_score"] or -1, row["judge_valid_rate_over_prepared_inputs"]), reverse=True)
    for idx, row in enumerate(ranking, start=1):
        row["rank"] = idx
    summary = {
        "summary_schema_version": "base_shootout_system_score_summary_v1",
        "created_at_utc": utc_now(),
        "judge_run_id": args.judge_run_id,
        "score_policy": {
            "primary_ranking_metric": "mean_capped_official_item_score",
            "primary_ranking_population": "schema_valid_judged_rows_only",
            "parse_product_readiness_reported_separately": True,
        },
        "systems": systems,
        "primary_accessibility_ranking": ranking,
    }
    write_jsonl(scoring_dir / "item_scores_all_systems.jsonl", all_item_rows)
    write_json(scoring_dir / "system_score_summary.json", summary)
    write_json(scoring_dir / "worker_scoring_manifest.json", {"created_at_utc": utc_now(), "status": "completed", "judge_run_id": args.judge_run_id, "systems": len(systems), "item_score_rows": len(all_item_rows)})
    print(json.dumps({"status": "completed", "judge_run_id": args.judge_run_id, "systems": len(systems), "item_scores": len(all_item_rows)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
