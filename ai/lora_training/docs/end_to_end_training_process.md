# End-To-End LoRA Training Process

This document explains the complete training path for the ClearRead summarisation model, from the accepted dataset to the final selected local LoRA adapter.

## 1. Accepted Source Dataset

The training source was the system-prompt-cleaned accepted dataset produced by the data preparation work. It contained 1452 records across seven domains:

| Domain | Records |
| --- | ---: |
| assignment_rubric | 83 |
| tech_doc | 89 |
| academic_book | 233 |
| academic_paper | 486 |
| public_service | 198 |
| medlineplus | 230 |
| gen_know | 133 |
| Total | 1452 |

Each record used a three-message structure:

```text
system / user / assistant
```

The assistant target was strict JSON with exactly two fields:

```json
{"main_idea":"...","key_points":["...","...","...","..."]}
```

## 2. Distribution Profiling And Split Creation

The first training step profiled the accepted records by domain and natural input length. The word-count rule was:

```text
[A-Za-z0-9]+(?:['-][A-Za-z0-9]+)*
```

The source length distribution was:

| Bucket | Rule | Records | Percentage |
| --- | --- | ---: | ---: |
| short | <= 400 user words | 241 | 16.60% |
| medium | 401-800 user words | 1018 | 70.11% |
| long | >= 801 user words | 193 | 13.29% |

The split was deterministic and preserved domain and length distribution as closely as possible:

| Split | Records | Percentage |
| --- | ---: | ---: |
| train | 1162 | 80.03% |
| validation | 145 | 9.99% |
| test | 145 | 9.99% |

A 10-record smoke set was selected only from the training split so early experiments would not touch validation or test data.

Relevant files:

- `scripts/create_stratified_splits.py`
- `reports/SOURCE_DISTRIBUTION_PROFILE.md`
- `reports/SPLIT_REPORT.md`
- `manifests/split_manifest.metadata.json`

## 3. Teammate Export

After splitting, aligned user-only and assistant-only exports were generated for teammate use. These exports were local derived data and are not committed here, but their counts and hashes are recorded.

The export preserved one-to-one alignment across:

```text
pair_index, pair_id, record_id, stable_hash, split, domain, source_file, source_line, natural_length_bucket
```

Relevant files:

- `scripts/create_teammate_exports.py`
- `reports/TEAMMATE_EXPORT_REPORT.md`
- `manifests/teammate_export_manifest.json`

## 4. Environment Setup

Training used a WSL2 Ubuntu conda environment with a local NVIDIA GPU. The final environment evidence recorded:

| Item | Value |
| --- | --- |
| Python | 3.11.15 |
| GPU | NVIDIA GeForce RTX 4070 Ti SUPER |
| VRAM | approximately 16 GB |
| CUDA runtime | 12.8 |
| BF16 support | available |
| PyTorch | 2.10.0+cu128 |
| Transformers | 5.5.0 |
| TRL | 0.24.0 |
| PEFT | 0.19.1 |
| BitsAndBytes | 0.49.2 |
| Unsloth | 2026.4.8 |

The environment check verified CUDA visibility, CUDA tensor execution, BF16 support, package imports, and Hugging Face CLI availability.

Relevant files:

- `scripts/check_wsl_training_env.py`
- `scripts/check_wsl_training_env.sh`
- `configs/clearread-llama-lora_environment.example.yml`
- `configs/clearread-llama-lora_pip_freeze.txt`
- `reports/WSL_ENVIRONMENT_REPORT.md`

## 5. Smoke Training Preparation

Before full training, the package added:

- training data loading utilities
- assistant-only label masking
- tokenization checks
- smoke training config
- smoke training script
- inference sanity-check script

The important label-mask decision was that only assistant JSON completion tokens should contribute to loss. System and user/source tokens were masked with `-100`.

Relevant files:

- `scripts/training_data_utils.py`
- `scripts/verify_assistant_loss_mask.py`
- `scripts/train_smoke_qlora.py`
- `scripts/run_inference_check.py`
- `configs/smoke_llama31_8b_qlora.example.yaml`
- `reports/LABEL_MASK_SANITY_CHECK.md`
- `reports/SMOKE_TRAINING_PREP_REPORT.md`

## 6. Smoke Training Run

The smoke run trained on the 10-record smoke split and verified that the environment, tokenizer, label masking, QLoRA setup, adapter saving, and inference flow worked end to end.

Results:

| Metric | Value |
| --- | --- |
| Status | success |
| OOM | no |
| Max input tokens | 1914 |
| Total trainable assistant tokens | 1323 |
| Truncated records | 0 |
| Final training loss | 0.5587 |
| Inference schema pass | 3/3 |

One attempted background launch from PowerShell failed because shell quoting broke WSL conda activation. No training or adapter write occurred during that failed launch. The command was then run directly through WSL and succeeded.

Relevant files:

- `reports/SMOKE_TRAINING_RUN_REPORT.md`
- `history/run_logs/smoke_test_001.md`

## 7. Candidate A Full Training

Candidate A used Llama-3.1-8B-Instruct with supervised fine-tuning and QLoRA.

Main training settings:

| Setting | Value |
| --- | --- |
| Base model | `unsloth/Llama-3.1-8B-Instruct-unsloth-bnb-4bit` |
| Method | SFT + QLoRA |
| LoRA rank | 16 |
| LoRA alpha | 32 |
| LoRA dropout | 0.05 |
| Max sequence length | 3072 |
| Epochs | 3 |
| Effective batch size | 8 |
| Learning rate | 0.0002 |

Results:

| Metric | Value |
| --- | --- |
| OOM | no |
| Optimizer steps | 438 |
| Final train loss | 0.4797596574748216 |
| Validation loss | 0.9654271602630615 |
| Validation inference sanity | 10/10 schema pass |

Two training records had decoded-label exact-match differences caused by tokenizer spacing around `.gov`. The decoded labels still parsed as JSON, were non-empty, and had no truncation, so this was recorded but not treated as label loss.

Relevant files:

- `scripts/train_full_qlora.py`
- `configs/train_llama31_8b_qlora_candidate_a.example.yaml`
- `reports/FULL_TRAIN_CANDIDATE_A_REPORT.md`
- `history/run_logs/full_train_candidate_a_3epoch.md`

## 8. Validation Quality Audit

Candidate A was evaluated on the validation split before any final test evaluation.

Validation results:

| Metric | Value |
| --- | --- |
| Records | 145 |
| JSON parse | 145/145 |
| Schema pass | 145/145 |
| Exact key order | 145/145 |
| Exactly 4 key points | 145/145 |
| Manual review | pass 14, minor issue 2, major issue 0, uncertain 0 |

Validation evidence did not justify training Candidate B. Candidate B was skipped to keep the workflow clean and avoid unnecessary tuning.

Relevant files:

- `scripts/evaluate_candidate_a_validation.py`
- `reports/CANDIDATE_A_VALIDATION_QUALITY_REPORT.md`
- `history/run_logs/candidate_a_validation_quality_audit.md`

## 9. Final Held-Out Test Evaluation

Candidate A was then evaluated once on the final held-out test split.

Final test results:

| Metric | Value |
| --- | --- |
| Records | 145 |
| JSON parse | 145/145 |
| Schema pass | 144/145 |
| Exact key order | 145/145 |
| Exactly 4 key points | 144/145 |
| Markdown/code-fence leakage | 0 |
| Extra text outside JSON | 0 |
| Refusal/meta-response phrases | 0 |
| Prediction mojibake rows | 0 |
| Gold mojibake rows | 0 |
| Manual review | pass 14, minor issue 2, major issue 1, uncertain 0 |

The single schema failure was row 87 from `academic_paper`, where the output was parseable and broadly faithful but contained seven key points instead of exactly four.

Relevant files:

- `scripts/evaluate_final_test_candidate_a.py`
- `reports/FINAL_TEST_EVALUATION_CANDIDATE_A_REPORT.md`
- `history/run_logs/final_test_evaluation_candidate_a.md`

## 10. Final Selection And Inference Wrapper

Candidate A was selected as the final raw LoRA adapter for this training cycle. The selected adapter remains a local model artifact and is not committed to Git.

Because the final held-out test had one key-point-count failure, deployment requires a schema guard. The inference wrapper validates:

- JSON parse
- exact expected keys
- `main_idea` string
- `key_points` list
- exactly four key points

If an output has more than four key points, the wrapper truncates to the first four and records `schema_guard_action: truncated_key_points`. If parsing fails, keys are wrong, types are wrong, or too few key points are produced, it returns a machine-readable error object.

Relevant files:

- `scripts/infer_clearread_candidate_a.py`
- `configs/final_candidate_a_inference.example.yaml`
- `reports/FINAL_MODEL_SELECTION_REPORT.md`
- `manifests/final_artifact_manifest.json`
- `docs/local_inference_runbook.md`
