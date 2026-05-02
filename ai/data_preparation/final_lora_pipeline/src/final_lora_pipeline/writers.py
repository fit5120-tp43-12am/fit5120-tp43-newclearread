from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from .checkpoint import CheckpointStore
from .json_utils import compact_json
from .models import PipelineConfig, SourceRecord
from .structural_gate import canonical_assistant_content, canonicalize_assistant_label


def accepted_path_for_slug(config: PipelineConfig, dataset_slug: str) -> Path:
    for dataset in config.datasets:
        if dataset.slug == dataset_slug:
            return config.paths.accepted_dir / dataset.accepted_filename
    raise KeyError(f"Unknown dataset slug: {dataset_slug}")


def quarantine_path_for_slug(config: PipelineConfig, dataset_slug: str) -> Path:
    return config.paths.quarantine_dir / f"{dataset_slug}_quarantine.jsonl"


def build_training_record(
    record: SourceRecord,
    candidate_label: Dict[str, Any],
    generation_prompt: str,
) -> Dict[str, Any]:
    return {
        "messages": [
            {
                "role": "system",
                "content": generation_prompt,
            },
            {
                "role": "user",
                "content": record.source_text,
            },
            {
                "role": "assistant",
                "content": canonical_assistant_content(candidate_label),
            },
        ]
    }


def build_quarantine_record(
    record: SourceRecord,
    run_id: str,
    reason: str,
    attempts_used: int,
    last_stage: str,
    last_raw_generation: str = "",
    last_cleaned_generation: str = "",
    last_candidate: Dict[str, Any] | None = None,
    last_judge: Dict[str, Any] | None = None,
    structural_issues: List[str] | None = None,
) -> Dict[str, Any]:
    return {
        "run_id": run_id,
        "record_id": record.record_id,
        "dataset_slug": record.dataset_slug,
        "domain_hint": record.domain_hint,
        "line_number": record.line_number,
        "source_path": str(record.source_path),
        "source_sha256": record.source_sha256,
        "attempts_used": attempts_used,
        "last_stage": last_stage,
        "reason": reason,
        "structural_issues": structural_issues or [],
        "last_raw_generation": last_raw_generation,
        "last_cleaned_generation": last_cleaned_generation,
        "last_candidate": last_candidate,
        "last_judge": last_judge,
        "source_text": record.source_text,
        "original_record": record.original_record,
    }


def _atomic_write_jsonl(path: Path, records: Iterable[Dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    count = 0
    with tmp_path.open("w", encoding="utf-8", newline="\n") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
            fh.write("\n")
            count += 1
    tmp_path.replace(path)
    return count


def flush_outputs_from_checkpoint(store: CheckpointStore, config: PipelineConfig) -> Dict[str, Any]:
    accepted_by_slug: Dict[str, List[Dict[str, Any]]] = {dataset.slug: [] for dataset in config.datasets}
    for row in store.fetch_accepted_records():
        accepted_by_slug.setdefault(row["dataset_slug"], []).append(json.loads(row["accepted_json"]))

    quarantine_by_slug: Dict[str, List[Dict[str, Any]]] = {dataset.slug: [] for dataset in config.datasets}
    for row in store.fetch_quarantine_records():
        quarantine_by_slug.setdefault(row["dataset_slug"], []).append(json.loads(row["quarantine_json"]))

    accepted_counts: Dict[str, int] = {}
    accepted_paths: Dict[str, str] = {}
    for dataset in config.datasets:
        path = accepted_path_for_slug(config, dataset.slug)
        accepted_counts[dataset.slug] = _atomic_write_jsonl(path, accepted_by_slug.get(dataset.slug, []))
        accepted_paths[dataset.slug] = str(path)

    quarantine_counts: Dict[str, int] = {}
    quarantine_paths: Dict[str, str] = {}
    for dataset in config.datasets:
        path = quarantine_path_for_slug(config, dataset.slug)
        quarantine_counts[dataset.slug] = _atomic_write_jsonl(path, quarantine_by_slug.get(dataset.slug, []))
        quarantine_paths[dataset.slug] = str(path)

    combined_path = None
    combined_count = 0
    if config.write_combined_file:
        combined_path = config.paths.accepted_dir / "all_v1.jsonl"
        combined_records: List[Dict[str, Any]] = []
        for dataset in config.datasets:
            combined_records.extend(accepted_by_slug.get(dataset.slug, []))
        combined_count = _atomic_write_jsonl(combined_path, combined_records)

        all_quarantine_path = config.paths.quarantine_dir / "all_quarantine.jsonl"
        all_quarantine_records: List[Dict[str, Any]] = []
        for dataset in config.datasets:
            all_quarantine_records.extend(quarantine_by_slug.get(dataset.slug, []))
        _atomic_write_jsonl(all_quarantine_path, all_quarantine_records)

    return {
        "accepted_counts": accepted_counts,
        "accepted_paths": accepted_paths,
        "quarantine_counts": quarantine_counts,
        "quarantine_paths": quarantine_paths,
        "combined_path": str(combined_path) if combined_path else None,
        "combined_count": combined_count,
    }
