from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict

from .models import ApiConfig, DatasetConfig, PipelineConfig, PipelinePaths


def _resolve(root: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return root / path


def _required(raw: Dict[str, Any], key: str) -> Any:
    if key not in raw:
        raise ValueError(f"Missing required config key: {key}")
    return raw[key]


def load_pipeline_config(config_path: Path) -> PipelineConfig:
    config_path = config_path.resolve()
    with config_path.open("r", encoding="utf-8") as fh:
        raw = json.load(fh)

    project_root = Path(_required(raw, "project_root")).resolve()
    generation_model = os.getenv("FINAL_LORA_GENERATION_MODEL", raw["generation_model"])
    judge_model = os.getenv("FINAL_LORA_JUDGE_MODEL", raw["judge_model"])

    api_raw = _required(raw, "api")
    api = ApiConfig(
        provider=api_raw["provider"],
        use_structured_outputs=bool(api_raw.get("use_structured_outputs", True)),
        generation_max_output_tokens=int(api_raw.get("generation_max_output_tokens", 700)),
        judge_max_output_tokens=int(api_raw.get("judge_max_output_tokens", 900)),
        generation_reasoning_effort=api_raw.get("generation_reasoning_effort"),
        judge_reasoning_effort=api_raw.get("judge_reasoning_effort"),
        text_verbosity=api_raw.get("text_verbosity"),
        request_timeout_seconds=int(api_raw.get("request_timeout_seconds", 120)),
        max_api_retries=int(api_raw.get("max_api_retries", 5)),
        backoff_base_seconds=float(api_raw.get("backoff_base_seconds", 2.0)),
        backoff_max_seconds=float(api_raw.get("backoff_max_seconds", 60.0)),
    )

    paths_raw = _required(raw, "paths")
    paths = PipelinePaths(
        generation_prompt=_resolve(project_root, paths_raw["generation_prompt"]),
        judge_prompt=_resolve(project_root, paths_raw["judge_prompt"]),
        assistant_schema=_resolve(project_root, paths_raw["assistant_schema"]),
        judge_schema=_resolve(project_root, paths_raw["judge_schema"]),
        accepted_dir=_resolve(project_root, paths_raw["accepted_dir"]),
        quarantine_dir=_resolve(project_root, paths_raw["quarantine_dir"]),
        logs_dir=_resolve(project_root, paths_raw["logs_dir"]),
        checkpoint_db=_resolve(project_root, paths_raw["checkpoint_db"]),
        reports_dir=_resolve(project_root, paths_raw["reports_dir"]),
    )

    datasets = []
    seen_slugs = set()
    for item in _required(raw, "datasets"):
        slug = item["slug"]
        if slug in seen_slugs:
            raise ValueError(f"Duplicate dataset slug in config: {slug}")
        seen_slugs.add(slug)
        datasets.append(
            DatasetConfig(
                slug=slug,
                domain_hint=item["domain_hint"],
                source_path=Path(item["source_path"]).resolve(),
                expected_records=int(item["expected_records"]),
                accepted_filename=item["accepted_filename"],
            )
        )

    return PipelineConfig(
        project_root=project_root,
        generation_model=generation_model,
        judge_model=judge_model,
        max_attempts=int(raw["max_attempts"]),
        write_combined_file=bool(raw.get("write_combined_file", True)),
        flush_every_records=int(raw.get("flush_every_records", 25)),
        api=api,
        paths=paths,
        datasets=datasets,
        raw=raw,
    )


def read_text(path: Path) -> str:
    with path.open("r", encoding="utf-8") as fh:
        return fh.read().strip()


def read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def stable_json_hash(value: Any) -> str:
    data = json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_output_dirs(config: PipelineConfig) -> None:
    for path in (
        config.paths.accepted_dir,
        config.paths.quarantine_dir,
        config.paths.logs_dir,
        config.paths.checkpoint_db.parent,
        config.paths.reports_dir,
    ):
        path.mkdir(parents=True, exist_ok=True)
