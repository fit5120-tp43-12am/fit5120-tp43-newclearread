# Smoke Training Prep Report

Date/time: 2026-04-28T14:28:11+10:00

## Scope

Prepared smoke-test scripts and config for ClearRead Llama-3.1-8B-Instruct SFT + QLoRA. No model training was run, no adapter was created, and no full model weights were downloaded by these checks.

## Docs Checked

- Unsloth fine-tuning guide: https://unsloth.ai/docs/get-started/fine-tuning-llms-guide
- Hugging Face TRL SFTTrainer docs: https://huggingface.co/docs/trl/sft_trainer

The implementation follows the current Unsloth guidance to start with Instruct models and QLoRA for local fine-tuning. It does not rely blindly on TRL `assistant_only_loss` because the TRL docs require chat-template generation masks for that path; instead, labels are masked explicitly.

## Files Prepared

| File | Purpose |
| --- | --- |
| `configs/smoke_llama31_8b_qlora.yaml` | Smoke QLoRA config for model ids, data, LoRA, training, output, and ETA settings. |
| `scripts/training_data_utils.py` | Shared JSONL loading, role validation, chat rendering, assistant-only label masking, token summaries, duration/ETA helpers, and a supervised collator. |
| `scripts/verify_assistant_loss_mask.py` | Tokenizer-only label-mask sanity check for the 10-record smoke set. |
| `scripts/train_smoke_qlora.py` | Worker 005 smoke training entry point with Unsloth QLoRA loading, explicit assistant-only labels, dry-run mode, adapter saving, and ETA progress callback. |
| `scripts/run_inference_check.py` | Worker 005 inference sanity-check entry point with adapter loading, JSON/schema checks, dry-run mode, and smoke-log append support. |
| `reports/LABEL_MASK_SANITY_CHECK.md` | Generated label-mask verification report. |

## Config Summary

- Base model id: `unsloth/Llama-3.1-8B-Instruct-unsloth-bnb-4bit`
- Fallback model ids: `unsloth/Llama-3.1-8B-Instruct-bnb-4bit`, `meta-llama/Meta-Llama-3.1-8B-Instruct`
- Data path: `data/splits/smoke_test_10.jsonl`
- Output dir: `outputs/smoke`
- Adapter path: `models/adapters/smoke_llama31_8b_qlora`
- Smoke log path: `logs/smoke_test_001.md`
- Max sequence length: `3072`
- QLoRA: `load_in_4bit: true`, `bnb_4bit_quant_type: nf4`, BF16 auto-enabled when CUDA reports support
- LoRA: `r=16`, `alpha=32`, `dropout=0.05`
- Target modules: `q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj`
- Smoke run: batch size `1`, gradient accumulation `4`, max steps `20`, learning rate `2e-4`, seed `5120`
- Progress: elapsed time, average seconds/step, estimated remaining time, and estimated completion timestamp are enabled.

## Assistant-Only Masking

`scripts/training_data_utils.py` renders each example twice with the target tokenizer chat template:

1. system + user with an assistant generation prompt,
2. system + user + assistant full text.

It tokenizes both forms, masks the prompt prefix labels with `-100`, and leaves only assistant JSON completion tokens trainable. The implementation first uses exact token-prefix matching and has an offset-based fallback if a tokenizer boundary ever prevents an exact prefix match.

## Verification

Commands run in WSL inside `clearread-llama-lora`:

```bash
python -m py_compile scripts/training_data_utils.py scripts/verify_assistant_loss_mask.py scripts/train_smoke_qlora.py scripts/run_inference_check.py
python scripts/verify_assistant_loss_mask.py --config configs/smoke_llama31_8b_qlora.yaml
python scripts/train_smoke_qlora.py --config configs/smoke_llama31_8b_qlora.yaml --dry-run
python scripts/run_inference_check.py --config configs/smoke_llama31_8b_qlora.yaml --dry-run
```

Results:

- Compile check: passed.
- Loss-mask check: passed on all 10 smoke records.
- Mask method: 10 token-prefix masks, 0 offset-fallback masks.
- Prompt tokens masked with `-100`: 12071 total.
- Trainable assistant tokens: 1323 total.
- Decoded trainable labels parsed as JSON and matched the source assistant JSON for all 10 records.
- Train dry-run: passed; max input tokens `1914`, max trainable tokens `164`, truncated records `0`.
- Inference dry-run: passed; checked gold assistant schema for 3 examples without loading model or adapter.

## Safety Notes

- No actual training was run.
- No inference against a trained adapter was run.
- No `.safetensors`, `.pt`, `.pth`, or `.bin` files were found under the training workspace after checks.
- `models/adapters` exists as an empty prepared directory only.
- `outputs/smoke` is empty.
- Tokenizer access produced an unauthenticated Hugging Face warning only; no token was printed or saved.
- Importing Unsloth emitted the known Flash Attention 2 warning and xformers fallback; this matches Worker 003 notes and did not block dry-run checks.

## File Hashes

| File | SHA256 |
| --- | --- |
| `configs/smoke_llama31_8b_qlora.yaml` | `86e3f4ef02eb058d7662f2ecac8f662fe545f119cba2d8070c374d071c899721` |
| `scripts/training_data_utils.py` | `5bf78ee3ccecb8e1df7efd02c8038d5019d687d85ed121206ffa4ce65f906be6` |
| `scripts/verify_assistant_loss_mask.py` | `0dd8d321f2c019b5bc2d209c34dd92b9d6a8c2202a0ba163057d50099953a16a` |
| `scripts/train_smoke_qlora.py` | `748147f17d311a9c2cc3bd1df7af8bd1318cf801a751ee6ea510635045ac34c2` |
| `scripts/run_inference_check.py` | `e53c2fd258c3c719760e068956b4feeaed3bc269456a71681d18676825d711cd` |
| `reports/LABEL_MASK_SANITY_CHECK.md` | `75c702f8984576885461edf144d05d0801eab5db60875fdbb32f527f14fa11ba` |

## Decision

Worker 004 preparation checks pass locally and are ready for central-brain review. Recommended next worker: Worker 005, run the Llama smoke training test.
