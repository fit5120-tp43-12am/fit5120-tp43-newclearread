# Final LoRA Data Pipeline

This package contains the final regeneration pipeline used to produce the Clearead LoRA training dataset. It turns cleaned source SFT records into a consistent training target, validates each assistant label, and writes accepted and quarantine outputs.

## What The Pipeline Does

- Loads the seven cleaned source SFT files defined in the pipeline config.
- Extracts the original `user` source text from each chat-style record.
- Generates a strict assistant label with `main_idea` and `key_points`.
- Validates the assistant label against the JSON schema and deterministic structural rules.
- Runs a semantic judge against the source text.
- Retries records that fail structural or semantic checks within the configured attempt budget.
- Stores progress in SQLite so interrupted runs can resume with drift checks.
- Writes accepted, quarantine, log, and report outputs under configured output directories.

## Directory Structure

```text
final_lora_pipeline/
  configs/                 Example pipeline configuration and recovery allowlist
  prompts/                 Generation and judge system prompts
  schemas/                 Assistant-label and judge-result JSON schemas
  scripts/                 Script entry points for main and merge stages
  src/final_lora_pipeline/ Reusable pipeline implementation
  requirements.txt         Python dependency list
```

## Main Entry Point

The main script calls `final_lora_pipeline.cli`:

```powershell
cd ai/data_preparation/final_lora_pipeline
python scripts/run_stage4_pipeline.py --config configs/pipeline_config.example.json --validate-only
```

For a real run, use a local config derived from `configs/pipeline_config.example.json` with source and output paths available on the review machine.

Required environment:

```env
OPENAI_API_KEY=replace-with-your-key
```

## Useful Options

| Option | Purpose |
| --- | --- |
| `--validate-only` | Validate config, prompts, schemas, and source loading without API calls or output writes. |
| `--datasets` | Process a comma-separated subset such as `medlineplus,tech_doc`. |
| `--limit-per-dataset` | Run a bounded pilot sample for each selected source group. |
| `--record-ids-file` | Run a targeted allowlist for recovery work. |
| `--rebuild-outputs` | Rebuild accepted and quarantine JSONL outputs from the checkpoint. |
| `--allow-drift` | Explicitly continue when checkpoint expectations differ from the current config, prompts, models, or source manifest. |

## Outputs

The configured output directories contain generated JSONL files, logs, checkpoints, and reports. These runtime outputs are excluded from Git. The reviewed counts and package policy are recorded in [../manifests/final_dataset_manifest.json](../manifests/final_dataset_manifest.json).
