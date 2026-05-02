# Data Preparation Pipeline

This directory documents and preserves the data-processing work used to prepare the LoRA training dataset for the reading-support summarization feature.

The package is organized for code review. It includes scripts, prompts, schemas, configuration examples, and QA summaries. Generated datasets, raw XML/ZIP files, SQLite checkpoints, API logs, model artifacts, and Python caches are intentionally excluded from Git.

## What This Pipeline Produces

The final approved dataset version contains:

| Split | Records | Purpose |
| --- | ---: | --- |
| accepted | 1452 | Training-ready v1 LoRA records |
| quarantine | 85 | Excluded records retained for audit |
| total source coverage | 1537 | All source records are either accepted or quarantined |

Each accepted training record uses the chat-style SFT shape:

```json
{
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "source text to summarize"},
    {"role": "assistant", "content": "{\"main_idea\":\"...\",\"key_points\":[\"...\",\"...\",\"...\",\"...\"]}"}
  ]
}
```

The final assistant label is fixed to:

- `main_idea`: exactly 2 short faithful sentences
- `key_points`: exactly 4 short high-level sentences

## Directory Layout

```text
ai/data_preparation/
  README.md
  docs/
    end_to_end_process.md
    package_contents.md
  final_lora_pipeline/
    configs/
    prompts/
    schemas/
    scripts/
    src/final_lora_pipeline/
  manifests/
    final_dataset_manifest.json
  reports/
    qa_summary.md
  source_pipelines/
    medlineplus/
    assignment_rubric/
    tech_doc/
    academic_book/
    academic_paper/
    public_service/
    gen_know/
    historical_repairs/
```

## Source Dataset Groups

| Group | Source type | Final source count used by v1 pipeline |
| --- | --- | ---: |
| `assignment_rubric` | RubricHub writing-style assignment/rubric records | 89 |
| `tech_doc` | Wikimedia technical/tutorial documentation | 99 |
| `academic_book` | OpenStax textbook excerpts | 250 |
| `academic_paper` | open-access academic paper excerpts | 500 |
| `public_service` | WikiHow-style public-service/process guides | 200 |
| `medlineplus` | MedlinePlus health-topic summaries | 250 |
| `gen_know` | Wikipedia general-knowledge excerpts | 149 |

## Final Regeneration Pipeline

The latest v1 pipeline is under `final_lora_pipeline/`.

It:

1. reads the seven cleaned/repaired source SFT files,
2. extracts the original `user` source text,
3. generates a new strict `2 + 4` assistant label,
4. runs a deterministic structural gate,
5. runs a semantic judge,
6. retries failed records up to a fixed budget,
7. writes accepted records,
8. quarantines unresolved records,
9. merges targeted recovery outputs into a final dataset view.

The production run used:

- generation model: `gpt-5.4-mini-2026-03-17`
- judge model: `gpt-5.5`
- retry budget: 4 attempts per record
- checkpoint store: SQLite
- recovery strategy: allowlisted targeted rerun, not a full redesign

## Why The Dataset Was Rebuilt

The original seven SFT files were valid enough to inspect, but not consistent enough for a clean LoRA target:

- `main_idea` sentence counts varied.
- `key_points` counts varied heavily across datasets.
- public-service and medical records exposed high-risk omission and formatting issues.
- two broken source JSONL records were removed before the v1 rebuild.

The v1 pipeline therefore regenerated labels into one stable output contract rather than training directly on the older mixed-format labels.

## Review Notes

The first full run was not accepted blindly. It produced 1375 accepted records and 162 quarantines. A hotspot review found:

- many public-service structural failures were false positives from abbreviation sentence splitting,
- several judge invalid-output cases were caused by judge response truncation,
- MedlinePlus remained genuinely difficult because dense medical pages can lose key warnings or treatment details under strict compression.

A targeted recovery rerun processed 100 allowlisted records in a separate namespace and recovered 77 of them. The final merged dataset contains 1452 accepted records and 85 quarantines.

## Important Files For Review

- `docs/end_to_end_process.md`: human-readable end-to-end process
- `manifests/final_dataset_manifest.json`: source counts and final output counts
- `reports/qa_summary.md`: final QA and known limitations
- `final_lora_pipeline/src/final_lora_pipeline/`: reusable pipeline implementation
- `final_lora_pipeline/prompts/`: generation and judge prompts
- `final_lora_pipeline/schemas/`: assistant and judge JSON schemas
- `source_pipelines/`: extraction, generation, validation, and repair scripts for the seven source groups

## Data Files

The large generated `.jsonl` datasets are not committed here. The repository `.gitignore` excludes generated JSONL, model artifacts, checkpoints, logs, and caches to keep the Git history lightweight and reviewable.

If a reviewer needs the actual training JSONL files, they should be supplied through the agreed project data handoff channel rather than committed with the application source code.
