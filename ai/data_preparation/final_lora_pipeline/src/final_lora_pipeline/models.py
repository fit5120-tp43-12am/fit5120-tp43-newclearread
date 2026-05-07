from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class DatasetConfig:
    slug: str
    domain_hint: str
    source_path: Path
    expected_records: int
    accepted_filename: str


@dataclass(frozen=True)
class ApiConfig:
    provider: str
    use_structured_outputs: bool
    generation_max_output_tokens: int
    judge_max_output_tokens: int
    generation_reasoning_effort: Optional[str]
    judge_reasoning_effort: Optional[str]
    text_verbosity: Optional[str]
    request_timeout_seconds: int
    max_api_retries: int
    backoff_base_seconds: float
    backoff_max_seconds: float


@dataclass(frozen=True)
class PipelinePaths:
    generation_prompt: Path
    judge_prompt: Path
    assistant_schema: Path
    judge_schema: Path
    accepted_dir: Path
    quarantine_dir: Path
    logs_dir: Path
    checkpoint_db: Path
    reports_dir: Path


@dataclass(frozen=True)
class PipelineConfig:
    project_root: Path
    generation_model: str
    judge_model: str
    max_attempts: int
    write_combined_file: bool
    flush_every_records: int
    api: ApiConfig
    paths: PipelinePaths
    datasets: List[DatasetConfig]
    raw: Dict[str, Any] = field(repr=False)


@dataclass(frozen=True)
class SourceRecord:
    record_id: str
    dataset_slug: str
    domain_hint: str
    line_number: int
    record_index: int
    source_path: Path
    source_text: str
    source_sha256: str
    original_record: Dict[str, Any]


@dataclass(frozen=True)
class GateResult:
    ok: bool
    parsed: Optional[Dict[str, Any]]
    cleaned_text: str
    issues: List[str]


@dataclass(frozen=True)
class ApiCallResult:
    text: str
    response_id: Optional[str]
    model: str
    usage: Dict[str, Any]
    raw_metadata: Dict[str, Any]
