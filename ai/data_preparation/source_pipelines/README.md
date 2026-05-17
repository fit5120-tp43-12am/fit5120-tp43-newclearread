# Source Pipelines

This directory contains the per-source scripts used before the final LoRA regeneration pipeline. Each source group has its own extraction, filtering, SFT-output generation, validation, audit, or repair scripts.

## Source Groups

| Folder | Source type | Main role in the dataset |
| --- | --- | --- |
| `assignment_rubric/` | RubricHub writing and assignment records | Assignment instructions and assessment-language summaries. |
| `tech_doc/` | Wikimedia technical and tutorial pages | Technical explanations and tool/process documentation. |
| `academic_book/` | OpenStax textbook excerpts | Academic textbook explanations. |
| `academic_paper/` | Open-access academic paper excerpts | Dense research-style prose. |
| `public_service/` | WikiHow-style service and process guides | Practical administrative and procedural text. |
| `medlineplus/` | MedlinePlus health-topic summaries | Health and public-health explanations. |
| `gen_know/` | Wikipedia general-knowledge excerpts | General expository background text. |
| `historical_repairs/` | Targeted repair scripts | Preserved implementation evidence for source-level repair passes. |

## How These Scripts Fit The Project

The scripts in these folders prepare and audit the source SFT files that feed the final regeneration pipeline in [../final_lora_pipeline/](../final_lora_pipeline/README.md). They are retained so reviewers can trace how source material was selected, cleaned, validated, and repaired before the final `2 + 4` label contract was applied.

Large source exports and generated JSONL outputs are excluded from Git. Counts and final coverage are recorded in [../manifests/final_dataset_manifest.json](../manifests/final_dataset_manifest.json).
