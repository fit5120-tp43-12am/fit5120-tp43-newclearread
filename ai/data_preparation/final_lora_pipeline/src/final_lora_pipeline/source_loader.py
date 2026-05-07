from __future__ import annotations

import json
from pathlib import Path
from typing import AbstractSet, Dict, Iterable, Iterator, List, Optional, Sequence

from .config import sha256_text
from .models import DatasetConfig, PipelineConfig, SourceRecord


class SourceLoadError(ValueError):
    pass


def _selected_datasets(config: PipelineConfig, dataset_slugs: Optional[Sequence[str]] = None) -> List[DatasetConfig]:
    if not dataset_slugs:
        return list(config.datasets)
    selected = set(dataset_slugs)
    known = {dataset.slug for dataset in config.datasets}
    unknown = sorted(selected - known)
    if unknown:
        raise SourceLoadError(f"Unknown dataset slug(s): {', '.join(unknown)}")
    return [dataset for dataset in config.datasets if dataset.slug in selected]


def _extract_user_text(record: Dict[str, object], source_path: Path, line_number: int) -> str:
    messages = record.get("messages")
    if not isinstance(messages, list):
        raise SourceLoadError(f"{source_path}:{line_number} missing messages list")
    for message in messages:
        if not isinstance(message, dict):
            continue
        if message.get("role") == "user":
            content = message.get("content")
            if not isinstance(content, str) or not content.strip():
                raise SourceLoadError(f"{source_path}:{line_number} has empty user content")
            return content
    raise SourceLoadError(f"{source_path}:{line_number} missing user message")


def iter_dataset_records(dataset: DatasetConfig) -> Iterator[SourceRecord]:
    if not dataset.source_path.exists():
        raise SourceLoadError(f"Source file not found: {dataset.source_path}")

    with dataset.source_path.open("r", encoding="utf-8") as fh:
        for record_index, line in enumerate(fh):
            line_number = record_index + 1
            raw_line = line.rstrip("\n")
            if not raw_line.strip():
                continue
            try:
                record = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                raise SourceLoadError(f"{dataset.source_path}:{line_number} invalid JSON: {exc}") from exc
            if not isinstance(record, dict):
                raise SourceLoadError(f"{dataset.source_path}:{line_number} is not a JSON object")
            source_text = _extract_user_text(record, dataset.source_path, line_number)
            source_sha = sha256_text(source_text)
            record_id = f"{dataset.slug}:{line_number}:{source_sha[:12]}"
            yield SourceRecord(
                record_id=record_id,
                dataset_slug=dataset.slug,
                domain_hint=dataset.domain_hint,
                line_number=line_number,
                record_index=record_index,
                source_path=dataset.source_path,
                source_text=source_text,
                source_sha256=source_sha,
                original_record=record,
            )


def iter_source_records(
    config: PipelineConfig,
    dataset_slugs: Optional[Sequence[str]] = None,
    limit_per_dataset: Optional[int] = None,
    record_ids: Optional[AbstractSet[str]] = None,
) -> Iterator[SourceRecord]:
    for dataset in _selected_datasets(config, dataset_slugs):
        count = 0
        for record in iter_dataset_records(dataset):
            if record_ids is not None and record.record_id not in record_ids:
                continue
            yield record
            count += 1
            if limit_per_dataset is not None and count >= limit_per_dataset:
                break


def validate_sources(config: PipelineConfig, dataset_slugs: Optional[Sequence[str]] = None) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    errors: List[str] = []
    for dataset in _selected_datasets(config, dataset_slugs):
        observed = sum(1 for _ in iter_dataset_records(dataset))
        counts[dataset.slug] = observed
        if observed != dataset.expected_records:
            errors.append(f"{dataset.slug}: expected {dataset.expected_records} records, found {observed}")
    if errors:
        raise SourceLoadError("Source validation failed: " + "; ".join(errors))
    return counts


def parse_dataset_slugs(raw: Optional[str]) -> Optional[List[str]]:
    if not raw:
        return None
    slugs = [part.strip() for part in raw.split(",") if part.strip()]
    return slugs or None
