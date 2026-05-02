# Worker 006: Full Training Candidate A

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
ai/lora_training/history/decision_reviews/central_review_worker_005.md
ai/lora_training/reports/SMOKE_TRAINING_RUN_REPORT.md
ai/lora_training/history/run_logs/smoke_test_001.md
```

## Purpose

Run the first formal full training candidate for ClearRead:

```text
Llama-3.1-8B-Instruct + SFT + QLoRA, Candidate A, 3 epochs
```

This worker must:

- create a full-train config for Candidate A,
- create or adapt a full training script from the approved smoke script,
- preserve explicit assistant-token-only loss masking,
- run a full train/validation tokenization preflight before training,
- run 3-epoch training only if the preflight is acceptable,
- save the local LoRA adapter,
- run validation inference sanity checks,
- record validation loss, timing, ETA/progress, and artifact paths,
- commit and push only Git-safe scripts/configs/reports/logs.

This worker is allowed to run actual training on `train.jsonl` and validation on `val.jsonl`.

This worker must not use `test.jsonl`.

## Environment

Use WSL and the Worker 003 environment:

```bash
source <conda-root>/etc/profile.d/conda.sh
conda activate clearread-llama-lora
cd ai/lora_training
```

Do not use Windows Python for training.

Recommended cache environment variables:

```bash
export HF_HOME=ai/lora_training/cache/huggingface
export TRANSFORMERS_CACHE=ai/lora_training/cache/huggingface/transformers
```

Do not copy cache files into Git.

## Inputs

Use only approved split files:

```text
ai/lora_training/data/splits\train.jsonl
ai/lora_training/data/splits\val.jsonl
ai/lora_training/data/splits\split_manifest.json
```

Read-only rule:

- Do not modify `data\splits`.
- Do not modify `data\teammate_exports`.
- Do not modify source datasets under `final_dataset_v1` or `final_dataset_v1_training_system_clean`.
- Do not modify old WSL env/project.
- Do not use `test.jsonl` in this worker.

## Required Outputs

Create or update these files under:

```text
ai/lora_training
```

Required config:

```text
configs\train_llama31_8b_qlora_candidate_a.yaml
```

Required scripts:

```text
scripts\train_full_qlora.py
```

You may update these existing scripts only if needed, and only in a backward-compatible way:

```text
scripts\training_data_utils.py
scripts\run_inference_check.py
scripts\verify_assistant_loss_mask.py
```

Required reports/logs:

```text
logs\full_train_candidate_a_3epoch.md
reports\FULL_TRAIN_CANDIDATE_A_REPORT.md
logs\decisions\worker_006_train_candidate_a_3epoch.md
```

Update local memory with a provisional Worker 006 section only:

```text
TRAINING_MEMORY.md
```

## Candidate A Config Requirements

Use the smoke-tested route:

```text
unsloth/Llama-3.1-8B-Instruct-unsloth-bnb-4bit
```

Keep the same fallback list:

```text
unsloth/Llama-3.1-8B-Instruct-bnb-4bit
meta-llama/Meta-Llama-3.1-8B-Instruct
```

Candidate A initial settings:

- max sequence length: `3072`
- QLoRA: 4-bit NF4
- LoRA r/alpha/dropout: `16 / 32 / 0.05`
- target modules: `q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj`
- per-device train batch size: `1`
- gradient accumulation steps: `8`
- effective train batch size: `8`
- epochs: `3`
- learning rate: `2e-4`
- warmup ratio or warmup steps: conservative, record exact value
- optimizer: `adamw_8bit`
- scheduler: `linear` unless a strong local reason exists
- seed: `5120`
- bf16: use when supported
- assistant-only loss masking: required
- training log path: `logs/full_train_candidate_a_3epoch.md`
- adapter output path: `models/adapters/full_candidate_a_3epoch`
- output/checkpoint path: `outputs/full/candidate_a_3epoch`

If `models\adapters\full_candidate_a_3epoch` is non-empty before training, do not overwrite it silently. Create a timestamped adapter path and record the actual path.

## Preflight Gate Before Training

Before full training, run a dry-run/tokenization preflight on train and validation.

The preflight must report:

- train records: expected `1162`
- validation records: expected `145`
- split manifest SHA256
- train SHA256
- validation SHA256
- max input tokens for train and validation
- max trainable assistant tokens for train and validation
- total trainable assistant tokens
- truncated record count for train and validation
- whether every record has non-empty assistant trainable labels
- whether decoded trainable labels parse as JSON for sampled examples

If any record has zero trainable assistant tokens, stop and report a blocker.

If truncation is above 2% in either train or validation, stop before full training and report the exact count, affected domains/length buckets if available, and a recommendation for central-brain review. Do not switch to `4096` or change hyperparameters without central-brain approval.

If truncation is at or below 2% and no assistant labels are lost, proceed with Candidate A and record the truncation clearly in the experiment log.

## Required Commands

Run these from WSL inside `clearread-llama-lora`.

Compile checks:

```bash
python -m py_compile scripts/training_data_utils.py scripts/verify_assistant_loss_mask.py scripts/train_full_qlora.py scripts/run_inference_check.py
```

Preflight:

```bash
python scripts/train_full_qlora.py --config configs/train_llama31_8b_qlora_candidate_a.example.yaml --dry-run
```

If the preflight gate passes, run actual Candidate A training:

```bash
python scripts/train_full_qlora.py --config configs/train_llama31_8b_qlora_candidate_a.example.yaml
```

After training, run validation inference sanity checks on validation data, not test data. If `run_inference_check.py` is extended, use a command like:

```bash
python scripts/run_inference_check.py --config configs/train_llama31_8b_qlora_candidate_a.example.yaml --adapter-path models/adapters/full_candidate_a_3epoch --data-path data/splits/val.jsonl --num-examples 10
```

If you choose a different CLI shape, document it clearly in the logs and keep smoke compatibility intact.

## Training Expectations

Expected optimizer steps are roughly:

```text
ceil(1162 / 8) * 3 = about 438 update steps
```

Use the ETA/progress callback pattern from the smoke script. The console and experiment log should include:

- current step and total steps,
- elapsed time,
- average seconds per step,
- estimated remaining time,
- estimated completion timestamp,
- actual completion time,
- short note on ETA accuracy after the run.

Validation loss is required. Use validation during training or run evaluation at the end, but record exactly how it was computed.

## OOM Or Runtime Failure Policy

If OOM occurs:

- stop and record the exact OOM context,
- record GPU memory information if available,
- do not try multiple random changes,
- one safe retry is allowed only if it is clearly scoped and recorded:
  - keep per-device batch size `1`,
  - reduce gradient accumulation only if necessary for script behavior, or
  - disable nonessential evaluation during training and run evaluation afterward.
- If uncertain, stop and report a blocker.

If model download fails due Hugging Face auth/rate limit:

- record the exact error,
- do not print tokens,
- do not switch to official Meta gated fallback unless authentication is already available and safe,
- report blocker for central-brain decision.

## Required Experiment Log

Create:

```text
logs\full_train_candidate_a_3epoch.md
```

It must include:

- date/time,
- worker id,
- Git branch and commit before run,
- exact commands run,
- train/val dataset paths and SHA256 hashes,
- split manifest SHA256,
- train/val counts,
- model id actually used,
- environment name and Python/package versions,
- GPU name and VRAM,
- key config values,
- preflight tokenization summary,
- truncation summary,
- start time,
- end time,
- elapsed runtime,
- ETA/progress summary,
- average seconds per step,
- train loss trend,
- validation loss,
- OOM or not,
- adapter output path,
- adapter file list and small metadata hashes,
- validation inference command,
- validation inference schema results,
- sample output previews,
- decision/recommendation.

## Required Report

Create:

```text
reports\FULL_TRAIN_CANDIDATE_A_REPORT.md
```

It should summarize:

- whether Candidate A completed,
- whether it should be considered a viable candidate for later final evaluation,
- training/validation loss,
- schema sanity results on validation examples,
- any truncation or quality concerns,
- whether Candidate B is recommended or not.

Do not use the test set to decide Candidate B.

## Required Worker Log

Create:

```text
logs\decisions\worker_006_train_candidate_a_3epoch.md
```

It must summarize:

- work order path,
- files created/changed,
- commands run,
- preflight result,
- training success/failure,
- adapter path,
- validation inference result,
- timing and ETA behavior,
- Git branch/commit/push result,
- blockers or deviations,
- recommendation for central-brain pass/fail and next step.

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
ai\configs\train_llama31_8b_qlora_candidate_a.yaml
ai\scripts\train_full_qlora.py
ai\scripts\training_data_utils.py
ai\scripts\run_inference_check.py
ai\scripts\verify_assistant_loss_mask.py
ai\logs\full_train_candidate_a_3epoch.md
ai\logs\decisions\worker_006_train_candidate_a_3epoch.md
ai\reports\FULL_TRAIN_CANDIDATE_A_REPORT.md
```

Only mirror helper scripts that actually changed.

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

Recommended primary commit message:

```text
feat(ai): train candidate a qlora workflow
```

Use a follow-up docs/log commit if needed so the worker log records the primary commit/push result.

Push to:

```text
origin/feature/ai-llama-lora-training
```

## Memory-Safety Rule

Worker 006 must write its memory update as provisional, clearly labeled:

```text
Worker 006 reported, pending central-brain review
```

Do not mark Worker 006 as passed. Only the central-brain chat can do that after independent review.

Do not rewrite, delete, or reinterpret central-brain decisions or approved facts.

## Acceptance Criteria

This worker passes central-brain review if:

- required config/script/report/log files are created,
- preflight checks train and validation data,
- no record has zero trainable assistant labels,
- truncation is acceptable or the worker stops for central review as instructed,
- if training runs, it completes without OOM,
- adapter saves successfully,
- validation loss is logged,
- validation inference sanity check runs against the saved adapter,
- `logs\full_train_candidate_a_3epoch.md` records timing/ETA and experiment evidence,
- `reports\FULL_TRAIN_CANDIDATE_A_REPORT.md` gives a clear recommendation,
- adapter/model/cache/checkpoint files are not committed to Git,
- Git-safe logs/reports/config/scripts are committed and pushed,
- memory update is clearly provisional.

## Final Response Template

Return a concise report with these headings:

```text
Status:
Files created/changed:
Commands run:
Preflight result:
Training result:
Validation result:
Timing/ETA:
Adapter artifact:
Git commit/push:
Safety checks:
Blockers or deviations:
Recommendation:
```

Do not include unnecessary long command output. Summarize important results.
