from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Tuple

from .checkpoint import CheckpointStore, utc_now
from .models import PipelineConfig


def write_run_reports(
    store: CheckpointStore,
    config: PipelineConfig,
    run_id: str,
    config_hash: str,
    prompt_hashes: Dict[str, str],
    source_counts: Dict[str, int],
    output_summary: Dict[str, Any],
    notes: str = "",
    source_validation_counts: Dict[str, int] | None = None,
    expected_source_counts: Dict[str, int] | None = None,
    source_manifest_hash: str | None = None,
) -> Tuple[Path, Path]:
    config.paths.reports_dir.mkdir(parents=True, exist_ok=True)
    summary = store.status_summary()
    report = {
        "run_id": run_id,
        "created_at": utc_now(),
        "config_hash": config_hash,
        "prompt_hashes": prompt_hashes,
        "source_manifest_hash": source_manifest_hash,
        "generation_model": config.generation_model,
        "judge_model": config.judge_model,
        "max_attempts": config.max_attempts,
        "retry_policy": "blind_regeneration_only",
        "expected_source_counts": expected_source_counts or {},
        "source_validation_counts": source_validation_counts or {},
        "source_counts": source_counts,
        "checkpoint_db": str(config.paths.checkpoint_db),
        "outputs": output_summary,
        "checkpoint_summary": summary,
        "notes": notes,
    }

    json_path = config.paths.reports_dir / f"{run_id}_report.json"
    md_path = config.paths.reports_dir / f"{run_id}_report.md"
    with json_path.open("w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    with md_path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(f"# Stage 4 Run Report: {run_id}\n\n")
        fh.write(f"- created_at: {report['created_at']}\n")
        fh.write(f"- generation_model: `{config.generation_model}`\n")
        fh.write(f"- judge_model: `{config.judge_model}`\n")
        fh.write(f"- max_attempts: {config.max_attempts}\n")
        fh.write("- retry_policy: blind regeneration only\n\n")
        if source_manifest_hash:
            fh.write(f"- source_manifest_hash: `{source_manifest_hash}`\n\n")
        if expected_source_counts:
            fh.write("## Source Validation\n\n")
            for slug, expected in expected_source_counts.items():
                observed = (source_validation_counts or {}).get(slug)
                fh.write(f"- {slug}: expected {expected}, observed {observed}\n")
            fh.write("\n")
        fh.write("## Source Counts\n\n")
        for slug, count in source_counts.items():
            fh.write(f"- {slug}: {count}\n")
        fh.write("\n## Checkpoint Status\n\n")
        for status, count in summary["by_status"].items():
            fh.write(f"- {status}: {count}\n")
        fh.write("\n## Accepted Outputs\n\n")
        for slug, path in output_summary["accepted_paths"].items():
            count = output_summary["accepted_counts"].get(slug, 0)
            fh.write(f"- {slug}: {count} -> `{path}`\n")
        fh.write("\n## Quarantine Outputs\n\n")
        for slug, path in output_summary["quarantine_paths"].items():
            count = output_summary["quarantine_counts"].get(slug, 0)
            fh.write(f"- {slug}: {count} -> `{path}`\n")
        if notes:
            fh.write("\n## Notes\n\n")
            fh.write(notes.strip() + "\n")
    return json_path, md_path
