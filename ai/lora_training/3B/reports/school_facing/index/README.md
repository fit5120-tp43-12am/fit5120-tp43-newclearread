# 3B School-Facing Report Index

This index collects the school-facing reports for the Clearead 3B model selection work. The report set separates testing evidence from safety, privacy, and compliance evidence so each area can be reviewed directly.

The evidence matrix in this folder maps the underlying logs, reports, manifests, score files, and decision records to the report where each item is used.

## Report Set

| Area | Report | Main Use |
| --- | --- | --- |
| Testing | `testing/01_training_data_quality_audit_report.md` | Training-label audit and results. |
| Testing | `testing/02_model_training_validation_search_report.md` | Model training, validation, parameter search, and checkpoint selection. |
| Testing | `testing/03_frozen_benchmark_and_content_quality_report.md` | Frozen benchmark comparison across the 8B baseline, Llama 3.2 3B, and Phi-4-mini. |
| Testing | `testing/04_deployment_resource_probe_report.md` | Local inference time, GPU memory, and deployment observations. |
| Safety and Privacy | `safety_privacy/01_safety_privacy_and_compliance_report.md` | Data handling, workspace isolation, credential handling, benchmark safety scoring, and package policy. |
| Index | `index/EVIDENCE_TO_REPORT_MATRIX.md` | Evidence allocation across the report set. |

## Shared Report Structure

Each report follows the same review structure:

1. project purpose;
2. work completed;
3. rationale;
4. verification results;
5. deployment observations and handling;
6. final conclusion;
7. evidence locations.

## Final Selection

| Field | Value |
| --- | --- |
| Base model | `unsloth/Llama-3.2-3B-Instruct-bnb-4bit` |
| Method | SFT + QLoRA |
| Adapter | `phase2_r32_a64_lr1p5e4_epoch_4` |
| LoRA rank / alpha | `r=32`, `alpha=64` |
| Learning rate | `1.5e-4` |
| Selected checkpoint | epoch 4 |

The final model selection is explained in:

```text
../../final/school_final_3b_experiment_report_en.md
```
