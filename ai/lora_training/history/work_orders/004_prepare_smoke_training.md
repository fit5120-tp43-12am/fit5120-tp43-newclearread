# Worker 004: Prepare Smoke Training Scripts And Loss-Mask Checks

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
ai/lora_training/history/decision_reviews/central_review_worker_003.md
ai/lora_training/reports/WSL_ENVIRONMENT_REPORT.md
```

Also check current official docs before implementing training-script details:

```text
https://unsloth.ai/docs/get-started/fine-tuning-llms-guide
https://huggingface.co/docs/trl/sft_trainer
```

## Purpose

Prepare the smoke-test training scripts and configs for Llama-3.1-8B-Instruct SFT + QLoRA.

This worker must:

- create the smoke QLoRA config,
- create reusable training-data/tokenization helpers,
- create a smoke training script,
- create an inference sanity-check script,
- create an assistant-token-only loss mask verification script,
- run only compile/dry-run/mask checks,
- add ETA/progress reporting support to the training script,
- create reports/logs,
- commit and push only Git-safe scripts/configs/reports/logs.

Do not run model training in this worker.

Do not download full model weights in this worker. Tokenizer downloads are allowed only if needed for the loss-mask sanity check and must remain outside Git.

## Environment

Use WSL and the Worker 003 environment:

```bash
source <conda-root>/etc/profile.d/conda.sh
conda activate clearread-llama-lora
cd ai/lora_training
```

Do not use Windows Python for Llama training scripts.

## Inputs

Approved smoke data:

```text
ai/lora_training/data/splits\smoke_test_10.jsonl
```

Approved split manifest:

```text
ai/lora_training/data/splits\split_manifest.json
```

Read-only rule:

- Do not modify `data\splits`.
- Do not modify source datasets under `final_dataset_v1` or `final_dataset_v1_training_system_clean`.
- Do not modify teammate exports.
- Do not modify old WSL env/project.

## Required Outputs

Create or update these files under:

```text
ai/lora_training
```

Required config:

```text
configs\smoke_llama31_8b_qlora.yaml
```

Required scripts:

```text
scripts\training_data_utils.py
scripts\verify_assistant_loss_mask.py
scripts\train_smoke_qlora.py
scripts\run_inference_check.py
```

Required reports/logs:

```text
reports\LABEL_MASK_SANITY_CHECK.md
reports\SMOKE_TRAINING_PREP_REPORT.md
logs\decisions\worker_004_prepare_smoke_training.md
```

Update local memory with a provisional Worker 004 section only:

```text
TRAINING_MEMORY.md
```

## Config Requirements

`configs\smoke_llama31_8b_qlora.yaml` must include at least:

- base model id default:

```text
unsloth/Llama-3.1-8B-Instruct-unsloth-bnb-4bit
```

- fallback model ids:

```text
unsloth/Llama-3.1-8B-Instruct-bnb-4bit
meta-llama/Meta-Llama-3.1-8B-Instruct
```

- data path:

```text
data/splits/smoke_test_10.jsonl
```

- output/log paths:
  - `outputs/smoke`
  - `models/adapters/smoke_llama31_8b_qlora`
  - `logs/smoke_test_001.md`
- `max_seq_length: 3072`
- `load_in_4bit: true`
- `bnb_4bit_quant_type: nf4`
- BF16 enabled when supported.
- LoRA:
  - `r: 16`
  - `alpha: 32`
  - `dropout: 0.05`
  - target modules: `q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj`
- smoke run defaults:
  - `per_device_train_batch_size: 1`
  - `gradient_accumulation_steps: 4` or `8`
  - `max_steps: 20` to `50`
  - `learning_rate: 2e-4`
  - `seed: 5120`
- ETA/progress settings:
  - enable progress logging,
  - log elapsed time,
  - log average seconds per step,
  - log estimated remaining time,
  - log estimated completion time.

## Assistant-Only Loss Mask Requirement

The model must train only on assistant JSON output tokens, not on system or user/source tokens.

Implement this explicitly. Do not rely blindly on TRL `assistant_only_loss=True` unless the script proves the chat template provides a correct assistant mask.

Recommended implementation:

1. Load each `messages` example with roles exactly `system`, `user`, `assistant`.
2. Use the target tokenizer/chat template to build:
   - prompt text from system + user with generation prompt,
   - full text from system + user + assistant.
3. Tokenize prompt and full text.
4. Create `labels` equal to `-100` for prompt tokens.
5. Keep assistant/completion tokens trainable.
6. Ensure trainable decoded text contains the assistant JSON answer.
7. Ensure no system prompt/source text tokens are trainable.

If tokenizer boundary behavior makes exact prompt-prefix masking unsafe, document the issue and implement a safer collator/masking method before passing.

## Required Scripts

### `scripts\training_data_utils.py`

Include reusable functions for:

- reading JSONL,
- validating role order,
- formatting prompt/full chat text,
- tokenizing and creating labels,
- counting masked vs trainable tokens,
- optional dataset summary,
- formatting durations and ETA timestamps.

### `scripts\verify_assistant_loss_mask.py`

Run on the 10-record smoke set.

It should:

- load tokenizer for the configured default model id,
- avoid loading full model weights,
- verify all smoke examples,
- print a concise pass/fail summary,
- write `reports\LABEL_MASK_SANITY_CHECK.md`,
- include at least 3 example summaries:
  - record id or stable hash,
  - prompt token count,
  - trainable token count,
  - decoded trainable text preview,
  - whether decoded trainable text parses as JSON when practical.

Pass condition:

- all 10 smoke records have trainable assistant tokens,
- system/user prompt token region is masked with `-100`,
- decoded trainable region corresponds to assistant JSON,
- no empty assistant-label examples.

### `scripts\train_smoke_qlora.py`

Prepare the actual smoke training script for Worker 005 to run.

It should:

- import `unsloth` before `transformers`, `peft`, or `trl`,
- load the configured model/tokenizer with 4-bit QLoRA,
- apply LoRA with configured target modules,
- use the explicit assistant-only labels/masking path,
- train only on `smoke_test_10.jsonl`,
- support `--config`,
- support `--dry-run` that validates config/data/tokenization without training or loading full model weights if practical,
- save adapter to the configured smoke adapter path when actually trained,
- write or append `logs/smoke_test_001.md` when actually trained,
- expose ETA/progress during training:
  - current step,
  - total steps,
  - elapsed time,
  - average seconds per step,
  - estimated remaining time,
  - estimated completion timestamp.

### `scripts\run_inference_check.py`

Prepare an inference sanity-check script for Worker 005.

It should:

- accept `--adapter-path`,
- accept `--config`,
- run on a few smoke examples by default,
- check JSON parseability,
- check exact keys `main_idea` and `key_points`,
- check `key_points` length is 4,
- write a concise report or append to `logs/smoke_test_001.md`.

Do not run inference in Worker 004 unless it can run without trained adapter/model weights. Usually this script should only be syntax/dry-run checked here.

## Required Verification In Worker 004

Run these checks in WSL inside `clearread-llama-lora`:

```bash
python -m py_compile scripts/training_data_utils.py scripts/verify_assistant_loss_mask.py scripts/train_smoke_qlora.py scripts/run_inference_check.py
python scripts/verify_assistant_loss_mask.py --config configs/smoke_llama31_8b_qlora.example.yaml
python scripts/train_smoke_qlora.py --config configs/smoke_llama31_8b_qlora.example.yaml --dry-run
python scripts/run_inference_check.py --config configs/smoke_llama31_8b_qlora.example.yaml --dry-run
```

If a dry-run cannot avoid downloading model weights, do not run that part. Record the limitation clearly.

## Git-Safe Repo Outputs

Team repo path:

```text
<team-repo-root>
```

Required branch:

```text
feature/ai-llama-lora-training
```

Mirror only Git-safe files:

```text
ai\configs\smoke_llama31_8b_qlora.yaml
ai\scripts\training_data_utils.py
ai\scripts\verify_assistant_loss_mask.py
ai\scripts\train_smoke_qlora.py
ai\scripts\run_inference_check.py
ai\reports\LABEL_MASK_SANITY_CHECK.md
ai\reports\SMOKE_TRAINING_PREP_REPORT.md
ai\logs\decisions\worker_004_prepare_smoke_training.md
```

Do not commit:

- raw JSONL data,
- tokenizer caches,
- Hugging Face caches,
- model weights,
- adapters,
- checkpoints,
- `.safetensors`, `.pt`, `.pth`, `.bin`,
- `unsloth_compiled_cache`.

Before committing, verify:

```powershell
git ls-files 'ai/**/*.jsonl'
git ls-files 'ai/**/*.safetensors' 'ai/**/*.pt' 'ai/**/*.pth' 'ai/**/*.bin'
```

Both should return nothing.

Commit with:

```text
feat(ai): add smoke training preparation
```

Push to:

```text
origin/feature/ai-llama-lora-training
```

Use a follow-up docs/log commit if needed so the worker log records the primary commit/push result.

## Memory-Safety Rule

Worker 004 must write its memory update as provisional, clearly labeled:

```text
Worker 004 reported, pending central-brain review
```

Do not mark Worker 004 as passed. Only the central-brain chat can do that after independent review.

Do not rewrite, delete, or reinterpret central-brain decisions or approved facts.

## Acceptance Criteria

This worker passes if:

- required scripts/configs/reports/logs are created,
- scripts compile in WSL inside `clearread-llama-lora`,
- loss-mask sanity check passes on all 10 smoke examples,
- dry-run checks pass or limitations are clearly justified,
- smoke training script includes assistant-only masking and ETA/progress reporting,
- no actual model training is run,
- no full model weights/adapters/checkpoints are created,
- Git-safe files are committed and pushed,
- raw data/model/cache artifacts are not committed,
- memory update is clearly provisional.

## Final Response Template

Return a concise report with these headings:

```text
Status:
Files created/changed:
Commands run:
Config summary:
Loss-mask verification:
Dry-run verification:
ETA/progress support:
Git commit/push:
Safety checks:
Blockers or deviations:
Next recommended worker:
```

Do not include unnecessary long command output. Summarize important results.
