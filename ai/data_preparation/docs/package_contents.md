# Package Contents

This package is intended for Git review of the data-preparation work.

## Included

### `source_pipelines/`

Extraction, generation, validation, and repair scripts for the seven source groups.

### `final_lora_pipeline/`

The final v1 regeneration pipeline, including:

- generation and judge prompts,
- JSON schemas,
- pipeline source code,
- entry-point scripts,
- recovery allowlist,
- Python requirements.

### `docs/`

Teacher-facing explanations of the end-to-end workflow and package layout.

### `manifests/`

Machine-readable summary of source counts, final counts, and intentionally excluded generated artifacts.

### `reports/`

Short QA summary suitable for review.

## Excluded

The following are intentionally excluded from Git:

- generated `.jsonl` datasets,
- raw XML/ZIP source snapshots,
- SQLite checkpoints,
- API logs and stdout/stderr logs,
- Python bytecode and `__pycache__`,
- local environment files,
- model checkpoints and training artifacts.

## Reason For Exclusion

The goal of this branch is to make the processing logic inspectable. Large generated data files and runtime artifacts should be transferred through a data handoff channel if needed, not committed to the application repository.
