#!/usr/bin/env python
"""Select a small set of epochs for judge scoring after full validation."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def score_row(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        int(row["parsed_ok_count"]),
        -int(row["parse_failure_count"]),
        int(row.get("no_refusal_or_meta_count") or 0),
        int(row.get("no_markdown_fence_count") or 0),
        int(row.get("no_mojibake_count") or 0),
        -int(row["epoch"]),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Select top validation epochs for judge scoring.")
    parser.add_argument("--candidate-key", required=True)
    parser.add_argument("--train-run-id", required=True)
    parser.add_argument("--epochs", nargs="+", type=int, default=[1, 2, 3, 4, 5])
    parser.add_argument("--max-judge-epochs", type=int, default=2)
    parser.add_argument("--include-third-if-parse-within", type=int, default=1)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    rows: list[dict[str, Any]] = []
    for epoch in args.epochs:
        metrics_path = (
            ROOT
            / "model_workspaces"
            / args.candidate_key
            / "outputs"
            / "validation"
            / f"{args.train_run_id}_epoch_{epoch}_record_messages"
            / "metrics.json"
        )
        if not metrics_path.exists():
            continue
        metrics = read_json(metrics_path)
        counts = metrics.get("counts", {})
        rows.append(
            {
                "epoch": epoch,
                "metrics_path": str(metrics_path.relative_to(ROOT)),
                "raw_output_count": int(counts.get("raw_output_count", 0)),
                "parsed_ok_count": int(counts.get("parsed_ok_count", 0)),
                "parse_failure_count": int(counts.get("parse_failure_count", 0)),
                "no_refusal_or_meta_count": int(counts.get("no_refusal_or_meta_count", 0)),
                "no_markdown_fence_count": int(counts.get("no_markdown_fence_count", 0)),
                "no_mojibake_count": int(counts.get("no_mojibake_count", 0)),
            }
        )
    if not rows:
        raise SystemExit(f"No validation metrics found for {args.candidate_key} / {args.train_run_id}")

    ranked = sorted(rows, key=score_row, reverse=True)
    selected = ranked[: args.max_judge_epochs]
    if len(ranked) > args.max_judge_epochs:
        top_parse = int(ranked[0]["parsed_ok_count"])
        third = ranked[args.max_judge_epochs]
        if top_parse - int(third["parsed_ok_count"]) <= args.include_third_if_parse_within:
            selected.append(third)
    selected_epochs = sorted({int(row["epoch"]) for row in selected})
    payload = {
        "created_at_utc": utc_now(),
        "candidate_key": args.candidate_key,
        "train_run_id": args.train_run_id,
        "selection_policy": "Rank by full-validation parse readiness; judge only top 2 epochs, with a third if parse is within 1 of the best.",
        "rows": rows,
        "ranked_rows": ranked,
        "selected_epochs": selected_epochs,
    }
    out_path = Path(args.out) if args.out else ROOT / "reports" / "phase2" / f"{args.candidate_key}_{args.train_run_id}_selected_judge_epochs.json"
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    write_json(out_path, payload)
    print(" ".join(str(epoch) for epoch in selected_epochs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
