from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional, Sequence, Set

from .pipeline import Stage4Pipeline
from .source_loader import parse_dataset_slugs


DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "configs" / "pipeline_config.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Stage 4 final LoRA data pipeline.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Path to pipeline_config.json.")
    parser.add_argument("--run-id", default=None, help="Optional stable run id.")
    parser.add_argument(
        "--datasets",
        default=None,
        help="Comma-separated dataset slugs to process, for example: medlineplus,tech_doc.",
    )
    parser.add_argument(
        "--limit-per-dataset",
        type=int,
        default=None,
        help="Limit records per selected dataset. Useful for Stage 5 pilot runs.",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate config, prompts, schemas, and source loading without API calls or output/checkpoint writes.",
    )
    parser.add_argument(
        "--rebuild-outputs",
        action="store_true",
        help="Rewrite accepted and quarantine JSONL outputs from the SQLite checkpoint, then exit.",
    )
    parser.add_argument(
        "--allow-drift",
        action="store_true",
        help="Explicitly continue when checkpoint prompt/config/model/source expectations differ.",
    )
    parser.add_argument(
        "--record-ids-file",
        type=Path,
        default=None,
        help="Optional newline-delimited SourceRecord.record_id allowlist for targeted reruns.",
    )
    return parser


def read_record_ids_file(path: Optional[Path]) -> Optional[Set[str]]:
    if path is None:
        return None
    record_ids = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            record_ids.append(stripped)
    if not record_ids:
        raise ValueError(f"Record id allowlist is empty: {path}")
    duplicates = sorted({record_id for record_id in record_ids if record_ids.count(record_id) > 1})
    if duplicates:
        raise ValueError(f"Duplicate record ids in allowlist: {', '.join(duplicates)}")
    return set(record_ids)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.validate_only and args.rebuild_outputs:
        parser.error("--validate-only and --rebuild-outputs cannot be used together.")
    dataset_slugs = parse_dataset_slugs(args.datasets)
    record_ids = read_record_ids_file(args.record_ids_file)
    pipeline = Stage4Pipeline(args.config)
    try:
        summary = pipeline.run(
            run_id=args.run_id,
            dataset_slugs=dataset_slugs,
            limit_per_dataset=args.limit_per_dataset,
            record_ids=record_ids,
            validate_only=args.validate_only,
            rebuild_outputs=args.rebuild_outputs,
            allow_drift=args.allow_drift,
        )
    finally:
        pipeline.close()
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0
