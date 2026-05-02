# Experiment History

This history summarizes the main iterations and decision gates behind the final LoRA training package. The sanitized source records for each step are kept under `history/`.

## Timeline

| Step | Purpose | Outcome |
| --- | --- | --- |
| 000 | Branch and artifact-safety setup | Added Git protections for generated data, model files, checkpoints, and cache artifacts. |
| 001 | Profile accepted data and create splits | Created deterministic train/validation/test/smoke splits from 1452 records. |
| 002 | Create teammate exports | Created aligned user-only and assistant-only local exports with metadata-only manifest. |
| 003 | Build clean WSL training environment | Verified CUDA, BF16, package imports, and Llama training dependencies. |
| 004 | Prepare smoke training | Added QLoRA smoke config, assistant-only label masking, dry-run checks, and reports. |
| 005 | Run smoke training | Initial background launch failed before training because of shell quoting; direct WSL run succeeded. |
| 006 | Train Candidate A | Completed 3-epoch full QLoRA training without OOM. |
| 007 | Validation quality audit | Candidate A passed validation strongly; Candidate B was not recommended. |
| 008 | Final held-out test | Candidate A was tested once on the final test split. |
| 009 | Package final artifact metadata | Candidate A was selected, with a schema guard required for deployment. |

## Important Retry And Repair Points

### Clean Environment Instead Of Reusing Old Work

The training was moved into a dedicated environment named `clearread-llama-lora`. Older experiments and older environments were treated as separate history and were not modified. This reduced the risk of hidden dependency drift from earlier attempts.

### Hugging Face Authentication Constraint

The official gated Meta model was not used directly because the local Hugging Face CLI was not authenticated. The public Unsloth 4-bit Llama 3.1 8B Instruct model became the practical base model.

### Flash Attention Fallback

Flash Attention 2 was unavailable in the local setup. Unsloth used the xformers fallback. CUDA tensor execution, BF16 support, imports, smoke training, and full training all passed, so this was accepted.

### Smoke Training Launch Retry

One smoke training launch through a PowerShell background process failed before conda activation because nested shell quoting broke the WSL command. No model training or adapter write occurred during that failed launch. The command was rerun directly in WSL and completed successfully.

### Tokenizer Decode Mismatch

During full-training preflight, two training rows had exact decoded-label mismatches caused by tokenizer spacing around `.gov`. The labels still parsed as JSON, were non-empty, and had no truncation, so this was recorded as evidence instead of blocking training.

### Candidate B Decision

Candidate B was planned as an optional fallback, but validation evidence did not justify it. Candidate A had 145/145 validation schema pass and no broad quality collapse, so additional training was skipped.

### Final Test Schema Caveat

The final held-out test found one schema-contract failure: a parseable academic-paper output with seven key points instead of four. This did not trigger retraining, because tuning on the held-out test would contaminate the final evaluation. Instead, the final deployment path requires a schema guard.

## History Folder

The `history/` folder keeps sanitized details:

- `history/work_orders/` - task definitions for each worker stage
- `history/decision_reviews/` - central review and worker decision records
- `history/run_logs/` - selected smoke, training, validation, and final-test run logs

These files are optional reading. The primary teacher-facing narrative is in this document and `docs/end_to_end_training_process.md`.
