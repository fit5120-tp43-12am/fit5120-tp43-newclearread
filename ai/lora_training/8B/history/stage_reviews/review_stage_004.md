# Project Review: Stage 004 Smoke Training Preparation

Date: 2026-04-28

## Reviewed Inputs

- Stage review summary.
- `ai/lora_training/configs/smoke_llama31_8b_qlora.example.yaml`
- `ai/lora_training/scripts/training_data_utils.py`
- `ai/lora_training/scripts/verify_assistant_loss_mask.py`
- `ai/lora_training/scripts/train_smoke_qlora.py`
- `ai/lora_training/scripts/run_inference_check.py`
- `ai/lora_training/reports/LABEL_MASK_SANITY_CHECK.md`
- `ai/lora_training/reports/SMOKE_TRAINING_PREP_REPORT.md`
- `ai/lora_training/history/stage_reviews/stage_004_prepare_smoke_training.md`

## Independent Verification

- Reran the Stage 004 verification commands inside WSL env `clearread-llama-lora`.
- Compile check passed for all four scripts.
- Loss-mask check passed on all 10 smoke records.
- 10 records had trainable assistant tokens.
- 10 decoded trainable label regions parsed as JSON.
- 10 decoded trainable JSON objects matched the source assistant JSON.
- Prompt/system/user region labels are masked with `-100`.
- Total masked prompt tokens: `12071`.
- Total trainable assistant tokens: `1323`.
- No records were truncated at `max_seq_length = 3072`.
- Training dry-run passed without training or loading full model weights.
- Training dry-run reported smoke data hash `8f51d083e8fafae143ec146c0155f85dc23a5cfdaf931a04092e7f8543d2d3a8`, max input tokens `1914`, max trainable tokens `164`, and truncated records `0`.
- Inference dry-run passed without loading model or adapter and validated gold assistant schema on 3 examples.
- `train_smoke_qlora.py` imports `unsloth` before `transformers`.
- `run_inference_check.py` imports `unsloth` before `peft`/model loading.
- `training_data_utils.py` explicitly masks prompt tokens with `-100` and keeps only assistant completion tokens trainable.
- ETA/progress callback reports current step, total steps, elapsed time, average seconds per step, estimated remaining time, and estimated completion time.
- `models\adapters` and `outputs\smoke` exist but are empty; no adapter/checkpoint was created by Stage 004.
- No `.safetensors`, `.pt`, `.pth`, or `.bin` files were found under the training workspace after review.

## Git Verification

- Team repo branch is `feature/ai-llama-lora-training`.
- Local HEAD equals upstream at `e977769ab29fc7eb6242f5c32599d34eb7fc5cd2`.
- Worktree is clean.
- No `ai/**/*.jsonl` files are tracked.
- No checked model binary patterns are tracked.

## Notes

- Tokenizer access emitted unauthenticated Hugging Face warnings only. No token was printed or saved.
- Unsloth still reports Flash Attention 2 as broken and falls back to xformers, matching Stage 003.
- Stage 004 intentionally did not run training and did not load full model weights.

## Decision

Stage 004 passes model-selection review.

The next approved work unit is Stage 005, Llama smoke training run, using:

```text
Stage 005 Llama smoke test
```
