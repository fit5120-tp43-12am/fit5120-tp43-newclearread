#!/usr/bin/env python
"""Select up to three model families for Stage 3 from completed Stage 1 anchors."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SUMMARY_CSV = ROOT / "reports" / "stage1" / "stage1_anchor_summary.csv"
OUT_DIR = ROOT / "reports" / "stage2"
CONFIG_PATH = ROOT / "configs" / "sweep_candidates.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_float(value: str | None, default: float = -1.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except ValueError:
        return default


def parse_int(value: str | None, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(float(value))
    except ValueError:
        return default


def read_rows() -> list[dict[str, str]]:
    if not SUMMARY_CSV.exists():
        raise FileNotFoundError(SUMMARY_CSV)
    with SUMMARY_CSV.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def expected_candidates() -> list[str]:
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return [str(candidate["key"]) for candidate in cfg["candidates"]]


def best_epoch(row_group: list[dict[str, str]]) -> dict[str, Any]:
    def row_key(row: dict[str, str]) -> tuple[Any, ...]:
        return (
            parse_int(row.get("parsed_ok_count")),
            parse_float(row.get("judge_mean_capped_score")),
            parse_float(row.get("source_safety_margin")),
            parse_float(row.get("main_message_salience")),
            -parse_int(row.get("severe_fail_count"), 999),
            -parse_int(row.get("major_risk_count"), 999),
            -parse_int(row.get("epoch")),
        )

    row = max(row_group, key=row_key)
    return {
        "candidate": row["candidate"],
        "selected_epoch": parse_int(row["epoch"]),
        "parsed_ok_count": parse_int(row.get("parsed_ok_count")),
        "raw_output_count": parse_int(row.get("raw_output_count")),
        "judge_mean_capped_score": parse_float(row.get("judge_mean_capped_score"), None),  # type: ignore[arg-type]
        "judge_count": parse_int(row.get("judge_count")),
        "source_safety_margin": parse_float(row.get("source_safety_margin"), None),  # type: ignore[arg-type]
        "main_message_salience": parse_float(row.get("main_message_salience"), None),  # type: ignore[arg-type]
        "major_risk_count": parse_int(row.get("major_risk_count"), 999),
        "severe_fail_count": parse_int(row.get("severe_fail_count"), 999),
        "training_runtime_seconds": parse_float(row.get("training_runtime_seconds"), None),  # type: ignore[arg-type]
        "train_loss": parse_float(row.get("train_loss"), None),  # type: ignore[arg-type]
        "eval_loss": parse_float(row.get("eval_loss"), None),  # type: ignore[arg-type]
        "metrics_path": row.get("metrics_path"),
        "judge_summary_path": row.get("judge_summary_path"),
    }


def candidate_rank_key(row: dict[str, Any]) -> tuple[Any, ...]:
    trend_bonus = 0
    if row["selected_epoch"] >= 4:
        trend_bonus = 1
    return (
        row["parsed_ok_count"],
        row["judge_mean_capped_score"] if row["judge_mean_capped_score"] is not None else -1,
        row["source_safety_margin"] if row["source_safety_margin"] is not None else -1,
        row["main_message_salience"] if row["main_message_salience"] is not None else -1,
        trend_bonus,
        -row["severe_fail_count"],
        -row["major_risk_count"],
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--allow-partial-stage1", action="store_true")
    args = parser.parse_args()

    rows = read_rows()
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(row["candidate"], []).append(row)

    expected = expected_candidates()
    completed = {candidate: grouped[candidate] for candidate in expected if len(grouped.get(candidate, [])) >= 5}
    incomplete = {candidate: len(grouped.get(candidate, [])) for candidate in expected if len(grouped.get(candidate, [])) < 5}
    if incomplete and not args.allow_partial_stage1:
        raise SystemExit(f"Incomplete Stage 1 candidates found: {incomplete}")

    best_rows = [best_epoch(group) for group in completed.values()]
    ranked = sorted(best_rows, key=candidate_rank_key, reverse=True)
    selected = ranked[: args.top_k]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "created_at_utc": utc_now(),
        "source_summary_csv": str(SUMMARY_CSV.relative_to(ROOT)),
        "selection_rule": [
            "best checkpoint per candidate by product readiness first",
            "then candidate ranking by parsed OK count",
            "then capped judge score",
            "then source safety margin",
            "then main-message salience",
            "then trend bonus for selected epoch >= 4",
            "then lower severe/major risk count",
        ],
        "expected_candidates": expected,
        "completed_candidate_count": len(completed),
        "incomplete_candidates": incomplete,
        "ranked_candidates": ranked,
        "selected_top_k": selected,
    }
    json_path = OUT_DIR / "stage2_top_models.json"
    md_path = OUT_DIR / "stage2_top_models.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [
        "# Stage 2 Top Model Selection",
        "",
        f"- Created UTC: `{payload['created_at_utc']}`",
        f"- Completed candidates: `{len(completed)}`",
        f"- Selected top K: `{len(selected)}`",
        "",
        "| Rank | Candidate | Epoch | Parsed OK | Judge mean | Source safety | Main salience | Severe | Major |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for idx, row in enumerate(ranked, start=1):
        lines.append(
            f"| {idx} | {row['candidate']} | {row['selected_epoch']} | {row['parsed_ok_count']}/{row['raw_output_count']} | {row['judge_mean_capped_score']} | {row['source_safety_margin']} | {row['main_message_salience']} | {row['severe_fail_count']} | {row['major_risk_count']} |"
        )
    if incomplete:
        lines.extend(["", "## Incomplete Stage 1 Candidates", "", json.dumps(incomplete, indent=2, ensure_ascii=False)])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"json": str(json_path), "markdown": str(md_path), "selected": [row["candidate"] for row in selected]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
