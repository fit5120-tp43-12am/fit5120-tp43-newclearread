# Package Contents

This package contains only Git-safe files needed to understand and reproduce the ClearRead LoRA training workflow.

## Main Folders

| Folder | Contents |
| --- | --- |
| `configs/` | Example YAML/YML configs for smoke training, full Candidate A training, final inference, and environment recreation. |
| `scripts/` | Python and shell scripts for split creation, teammate exports, environment checks, smoke training, full training, evaluation, and inference. |
| `docs/` | Human-readable process docs, experiment history, and inference runbook. |
| `reports/` | Data profile, split report, environment report, training reports, validation audit, final test report, model selection report, and QA summary. |
| `manifests/` | Metadata-only manifests for source profile, split metadata, teammate exports, final artifact metadata, and package contents. |
| `artifact_metadata/` | Local metadata pointer for the selected Candidate A adapter, without adapter weights. |
| `history/` | Sanitized work orders, decision reviews, and selected run logs from the training process. |

## Included Code

| Script | Purpose |
| --- | --- |
| `scripts/create_stratified_splits.py` | Profiles accepted source records and creates deterministic domain/length-aware splits. |
| `scripts/create_teammate_exports.py` | Creates aligned user-only and assistant-only local exports. |
| `scripts/check_wsl_training_env.py` | Verifies CUDA, package versions, WSL environment, and Hugging Face tooling. |
| `scripts/check_wsl_training_env.sh` | Convenience wrapper for the environment check in WSL. |
| `scripts/training_data_utils.py` | Shared data loading, chat-template rendering, assistant-only label masking, and collator utilities. |
| `scripts/verify_assistant_loss_mask.py` | Validates that only assistant JSON tokens contribute to training loss. |
| `scripts/train_smoke_qlora.py` | Runs the low-risk smoke QLoRA training job. |
| `scripts/train_full_qlora.py` | Runs the full Candidate A QLoRA training job. |
| `scripts/run_inference_check.py` | Runs quick schema sanity checks against a local adapter. |
| `scripts/evaluate_candidate_a_validation.py` | Evaluates Candidate A on the validation split. |
| `scripts/evaluate_final_test_candidate_a.py` | Evaluates Candidate A on the final held-out test split. |
| `scripts/infer_clearread_candidate_a.py` | Runs final local inference with schema guard behavior. |

## Excluded Artifacts

The package intentionally excludes:

- raw source `.jsonl` files
- train/validation/test/smoke `.jsonl` split files
- teammate export `.jsonl` files
- prediction `.jsonl` files
- model adapter `.safetensors` files
- tokenizer large artifacts
- checkpoints and optimizer states
- Hugging Face cache and Unsloth compiled cache
- local command-output `.log` files

These artifacts are represented by counts, SHA256 hashes, metadata manifests, and reports.
