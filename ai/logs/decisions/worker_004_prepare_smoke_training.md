# Worker 004: Prepare Smoke Training

Date/time: 2026-04-28T14:28:11+10:00

## Scope

Prepared smoke training scripts, config, assistant-token-only label-mask verification, dry-run checks, and process reports for the ClearRead Llama-3.1-8B-Instruct SFT + QLoRA path.

This is a worker report and is provisional pending central-brain review.

## Files Created

- `configs/smoke_llama31_8b_qlora.yaml`
- `scripts/training_data_utils.py`
- `scripts/verify_assistant_loss_mask.py`
- `scripts/train_smoke_qlora.py`
- `scripts/run_inference_check.py`
- `reports/LABEL_MASK_SANITY_CHECK.md`
- `reports/SMOKE_TRAINING_PREP_REPORT.md`
- `logs/decisions/worker_004_prepare_smoke_training.md`

## Key Implementation Points

- Uses `unsloth/Llama-3.1-8B-Instruct-unsloth-bnb-4bit` as the default smoke model id.
- Keeps fallbacks for `unsloth/Llama-3.1-8B-Instruct-bnb-4bit` and `meta-llama/Meta-Llama-3.1-8B-Instruct`.
- Uses explicit assistant-only label masking instead of depending on TRL `assistant_only_loss`.
- Masks system/user/source prompt labels with `-100`.
- Leaves only assistant JSON completion tokens trainable.
- Imports `unsloth` before `transformers`, `peft`, or `trl` in scripts that use Unsloth.
- Adds an ETA progress callback with elapsed time, average seconds per step, estimated remaining time, and estimated completion time.
- Supports dry-run modes that do not train and do not load full model weights.

## Verification Commands

```bash
source /home/aufb/miniconda3/etc/profile.d/conda.sh
conda activate clearread-llama-lora
cd /mnt/c/Users/Aufb/Desktop/fit5120/iteration1/training
python -m py_compile scripts/training_data_utils.py scripts/verify_assistant_loss_mask.py scripts/train_smoke_qlora.py scripts/run_inference_check.py
python scripts/verify_assistant_loss_mask.py --config configs/smoke_llama31_8b_qlora.yaml
python scripts/train_smoke_qlora.py --config configs/smoke_llama31_8b_qlora.yaml --dry-run
python scripts/run_inference_check.py --config configs/smoke_llama31_8b_qlora.yaml --dry-run
```

## Verification Results

- Compile check: passed.
- Label-mask sanity check: passed on all 10 smoke records.
- Prompt labels masked with `-100`: 12071 total.
- Trainable assistant tokens: 1323 total.
- Decoded trainable labels parse as JSON and match assistant JSON for all 10 smoke records.
- Train dry-run: passed with 10 records, max input tokens `1914`, max trainable tokens `164`, and no truncation.
- Inference dry-run: passed without loading model or adapter; gold assistant schema checked for 3 examples.

## Safety Checks

- No actual training was run.
- No full model weights were downloaded by the verification commands.
- No adapter, checkpoint, or model binary was created.
- No `.safetensors`, `.pt`, `.pth`, or `.bin` file was found under the training workspace after checks.
- Raw JSONL split files were not modified.
- Source datasets and teammate exports were not modified.
- Hugging Face CLI remains unauthenticated; tokenizer access emitted an unauthenticated warning only.
- Unsloth still reports Flash Attention 2 as broken and falls back to xformers, matching Worker 003 notes.

## Git Result

Pending at initial log creation. This section should be updated after the Git-safe mirror, commit, and push complete.

## Recommended Next Worker

Worker 005: run the Llama smoke training test, save the adapter, run inference sanity checks, and write `logs/smoke_test_001.md`.
