# Worker 005: Run Llama Smoke Training Test

Last updated: 2026-04-28

## Role

You are a worker chat for the ClearRead Llama LoRA training project.

You are not the central-brain chat. Execute only this work order, stay within scope, and report back clearly for central-brain review.

## Required Reading

Read these files first, in this order:

```text
ai/lora_training/history/internal_planning/TRAINING_MEMORY_SUMMARY.md
ai/lora_training/history/internal_planning/CENTRAL_BRAIN_WORKER_PROTOCOL.md
ai/lora_training/history/internal_planning/MASTER_TRAINING_PLAN.md
ai/lora_training/history/decision_reviews/central_review_worker_004.md
ai/lora_training/reports/SMOKE_TRAINING_PREP_REPORT.md
ai/lora_training/reports/LABEL_MASK_SANITY_CHECK.md
```

## Purpose

Run the first real Llama-3.1-8B-Instruct QLoRA smoke training test.

This worker must:

- run the prepared smoke training script on the 10-record smoke set,
- allow model/tokenizer downloads into cache if needed,
- save a LoRA adapter,
- run inference sanity checks with the saved adapter,
- record runtime, ETA/progress, GPU/memory status, and results,
- create a smoke-test decision log,
- commit and push only Git-safe reports/logs/config/script updates.

This worker is allowed to run actual training on the smoke set.

This worker must not run full training on `train.jsonl`.

## Environment

Use WSL and the Worker 003 environment:

```bash
source <conda-root>/etc/profile.d/conda.sh
conda activate clearread-llama-lora
cd ai/lora_training
```

Do not use Windows Python for training.

Recommended cache environment variables for this worker:

```bash
export HF_HOME=ai/lora_training/cache/huggingface
export TRANSFORMERS_CACHE=ai/lora_training/cache/huggingface/transformers
```

If these cache paths cause a blocker, record the issue and use the default Hugging Face cache instead. Do not copy cache files into Git.

## Inputs

Use only:

```text
ai/lora_training/configs/smoke_llama31_8b_qlora.example.yaml
ai/lora_training/data/splits\smoke_test_10.jsonl
ai/lora_training/data/splits\split_manifest.json
```

Read-only rule:

- Do not modify `data\splits`.
- Do not modify `data\teammate_exports`.
- Do not modify source datasets under `final_dataset_v1` or `final_dataset_v1_training_system_clean`.
- Do not modify old WSL env/project.

## Expected Large/Local Artifacts

This worker may create local large artifacts:

```text
cache\huggingface\
outputs\smoke\
models\adapters\smoke_llama31_8b_qlora\
unsloth_compiled_cache\
```

These artifacts are allowed locally but must not be committed to Git.

The adapter path from config is:

```text
ai/lora_training/models/adapters/smoke_llama31_8b_qlora
```

Before training:

- If this adapter directory already contains adapter files, do not overwrite it silently.
- If it is non-empty from a previous run, create a run-specific adapter path such as `models\adapters\smoke_llama31_8b_qlora_run_YYYYMMDD_HHMMSS`, record it in the log, and pass it to inference with `--adapter-path`.
- If it is empty, use the configured adapter path.

## Required Commands

Run these from WSL inside `clearread-llama-lora`.

First re-run the preparation checks:

```bash
python -m py_compile scripts/training_data_utils.py scripts/verify_assistant_loss_mask.py scripts/train_smoke_qlora.py scripts/run_inference_check.py
python scripts/verify_assistant_loss_mask.py --config configs/smoke_llama31_8b_qlora.example.yaml
python scripts/train_smoke_qlora.py --config configs/smoke_llama31_8b_qlora.example.yaml --dry-run
```

Then run actual smoke training:

```bash
python scripts/train_smoke_qlora.py --config configs/smoke_llama31_8b_qlora.example.yaml
```

Then run inference sanity checks:

```bash
python scripts/run_inference_check.py --config configs/smoke_llama31_8b_qlora.example.yaml --num-examples 3
```

If the adapter path had to be changed because a previous adapter existed, add:

```bash
--adapter-path <actual_adapter_path>
```

## Training Expectations

Expected config:

- base model: `unsloth/Llama-3.1-8B-Instruct-unsloth-bnb-4bit`
- smoke data: 10 records
- max sequence length: 3072
- QLoRA 4-bit NF4
- LoRA r/alpha/dropout: `16 / 32 / 0.05`
- batch size: 1
- gradient accumulation: 4
- max steps: 20
- learning rate: 2e-4
- assistant-only loss masking

Expected console behavior:

- progress lines should print step/total,
- elapsed time,
- average seconds per step,
- estimated remaining time,
- estimated completion timestamp.

If OOM occurs:

- stop and record the exact OOM context,
- do not try many random changes,
- one safe fallback is allowed: reduce `gradient_accumulation_steps` only if the script/config supports it cleanly and record the change,
- otherwise report blocker for central-brain decision.

If the model download fails due Hugging Face auth/rate limit:

- record the exact error,
- do not print tokens,
- do not switch to official Meta gated fallback unless authentication is already available and safe,
- report blocker for central-brain decision.

## Required Smoke Log

Create or update:

```text
logs\smoke_test_001.md
```

It must include:

- date/time,
- worker id,
- Git branch and commit,
- dataset path and SHA256,
- split manifest SHA256,
- model id actually used,
- environment name and Python/package versions,
- GPU name and VRAM,
- exact commands run,
- key config values,
- max input tokens and trainable tokens from dry-run,
- start time,
- end time,
- elapsed runtime,
- ETA/progress summary,
- average seconds per step,
- final training loss if available,
- OOM or not,
- adapter output path,
- adapter file list and hashes for small metadata files,
- inference command,
- inference schema results,
- sample output previews,
- decision/recommendation.

## Required Worker Log

Create:

```text
logs\decisions\worker_005_llama_smoke_test.md
```

It must summarize:

- work order path,
- commands run,
- training success/failure,
- adapter path,
- inference result,
- timing and ETA behavior,
- Git branch/commit/push result,
- blockers or deviations,
- recommendation for central-brain pass/fail.

## Git-Safe Repo Outputs

Team repo path:

```text
<team-repo-root>
```

Required branch:

```text
feature/ai-llama-lora-training
```

Mirror only Git-safe files, such as:

```text
ai\logs\smoke_test_001.md
ai\logs\decisions\worker_005_llama_smoke_test.md
ai\reports\SMOKE_TRAINING_RUN_REPORT.md
```

If scripts/configs needed small fixes during the smoke run, mirror those Git-safe changes too and explain them.

Do not commit:

- `ai/**/*.jsonl`
- base model files,
- Hugging Face cache,
- Unsloth compiled cache,
- adapter `.safetensors`,
- checkpoints,
- optimizer states,
- `.pt`, `.pth`, `.bin`,
- large raw logs.

Before committing, verify:

```powershell
git ls-files 'ai/**/*.jsonl'
git ls-files 'ai/**/*.safetensors' 'ai/**/*.pt' 'ai/**/*.pth' 'ai/**/*.bin'
```

Both should return nothing.

Recommended commit message:

```text
docs(ai): record llama smoke test result
```

Push to:

```text
origin/feature/ai-llama-lora-training
```

Use a follow-up docs/log commit if needed so the worker log records the primary commit/push result.

## Memory-Safety Rule

Worker 005 must write its memory update as provisional, clearly labeled:

```text
Worker 005 reported, pending central-brain review
```

Do not mark Worker 005 as passed. Only the central-brain chat can do that after independent review.

Do not rewrite, delete, or reinterpret central-brain decisions or approved facts.

## Acceptance Criteria

This worker passes central-brain review if:

- smoke training completes without OOM,
- adapter saves successfully,
- inference script runs against the adapter,
- `logs\smoke_test_001.md` records training and inference results including timing/ETA,
- `logs\decisions\worker_005_llama_smoke_test.md` exists,
- adapter/model/cache/checkpoint files are not committed to Git,
- Git-safe logs/reports are committed and pushed,
- memory update is clearly provisional.

Schema quality note:

- The smoke model should ideally produce valid JSON for at least some inference samples.
- If inference runs but JSON/schema quality is poor, record that honestly. Do not tune on test data. Central brain will decide whether to adjust smoke steps/config before full training.

## Final Response Template

Return a concise report with these headings:

```text
Status:
Files created/changed:
Commands run:
Training result:
Timing/ETA:
Adapter artifact:
Inference sanity check:
Git commit/push:
Safety checks:
Blockers or deviations:
Next recommended worker:
```

Do not include unnecessary long command output. Summarize important results.
