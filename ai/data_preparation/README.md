# Clearead Data Preparation

This directory documents the data preparation work used to create the supervised fine-tuning dataset for Clearead's reading-support summarisation model.

The final dataset package is designed for review. It includes source-pipeline scripts, the final regeneration pipeline, prompts, schemas, configuration examples, manifests, and QA summaries. Generated datasets, raw source archives, API logs, SQLite checkpoints, caches, and model artifacts are excluded from Git and tracked through counts, manifests, and reports.

## Final Dataset

The approved dataset version is `final_lora_v1_training_system_clean`.

| Category | Records |
| --- | ---: |
| Source records covered | 1,537 |
| Accepted training records | 1,452 |
| Quarantined audit records | 85 |
| Missing source records | 0 |
| Accepted structural validation issues | 0 |

Each accepted record uses chat-style SFT messages:

```json
{
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "source text to summarize"},
    {"role": "assistant", "content": "{\"main_idea\":\"...\",\"key_points\":[\"...\",\"...\",\"...\",\"...\"]}"}
  ]
}
```

The assistant label contract is:

- `main_idea`: exactly 2 short faithful sentences.
- `key_points`: exactly 4 short high-level sentences.

## Source Coverage

| Source group | Source type | Source records | Accepted records |
| --- | --- | ---: | ---: |
| `assignment_rubric` | RubricHub writing-style assignment and rubric records | 89 | 83 |
| `tech_doc` | Wikimedia technical and tutorial documentation | 99 | 89 |
| `academic_book` | OpenStax textbook excerpts | 250 | 233 |
| `academic_paper` | Open-access academic paper excerpts | 500 | 486 |
| `public_service` | WikiHow-style public-service and process guides | 200 | 198 |
| `medlineplus` | MedlinePlus health-topic summaries | 250 | 230 |
| `gen_know` | Wikipedia general-knowledge excerpts | 149 | 133 |

## Directory Structure

```text
ai/data_preparation/
  README.md
  docs/                    End-to-end process and package contents
  final_lora_pipeline/     Final label regeneration and QA pipeline
  manifests/               Final dataset counts and artifact policy
  reports/                 Final QA summary
  source_pipelines/        Per-source extraction, validation, and repair scripts
```

## Pipeline Summary

The final regeneration pipeline performs:

1. source validation against locked expected counts;
2. extraction of source text from existing chat-style source records;
3. generation of a strict `2 + 4` assistant label;
4. deterministic structural validation;
5. semantic judging against the source text;
6. retry within a fixed attempt budget;
7. accepted and quarantine output writing;
8. checkpointing, logging, and report generation;
9. targeted recovery merge for approved recoverable records.

The implementation is in [final_lora_pipeline/](final_lora_pipeline/README.md).

## Review Documents

- [docs/end_to_end_process.md](docs/end_to_end_process.md): complete source-to-final-data process.
- [docs/package_contents.md](docs/package_contents.md): package contents summary.
- [manifests/final_dataset_manifest.json](manifests/final_dataset_manifest.json): machine-readable final counts and artifact policy.
- [reports/qa_summary.md](reports/qa_summary.md): final QA summary and known limitations.
- [source_pipelines/](source_pipelines/README.md): per-source extraction and repair scripts.

## Data Handoff

The large `.jsonl` outputs are intentionally outside this Git repository. If a reviewer needs the actual training data files, they should be supplied through the agreed project data handoff channel with the same version name and counts recorded in `manifests/final_dataset_manifest.json`.
