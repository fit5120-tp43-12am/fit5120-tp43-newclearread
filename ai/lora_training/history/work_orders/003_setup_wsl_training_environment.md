# Worker 003: Clean WSL Training Environment Setup

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
ai/lora_training/history/decision_reviews/central_review_worker_002.md
```

Also read the current official installation/training docs before choosing exact install commands, because package compatibility changes over time:

```text
https://unsloth.ai/docs/get-started/install/pip-install
https://unsloth.ai/docs/get-started/fine-tuning-llms-guide
https://huggingface.co/docs/trl/sft_trainer
```

## Purpose

Create and verify a clean WSL training environment for the Llama-3.1-8B-Instruct SFT + QLoRA route.

This worker must:

- inspect the existing WSL and conda state,
- create or verify a clean conda environment named `clearread-llama-lora`,
- install the minimum stack needed for Llama QLoRA training,
- verify CUDA/GPU visibility from inside the new environment,
- verify core package imports and versions,
- check Hugging Face CLI/auth/model-access status without exposing tokens,
- save reproducible environment scripts, reports, and logs,
- commit and push only Git-safe scripts/configs/reports/logs to the team repo.

Do not train a model in this worker.

Do not download base model weights in this worker unless a small metadata-only access check unexpectedly requires it. Prefer metadata/API checks only.

## Central-Brain Preflight Context

Central-brain preflight on 2026-04-28 found:

- WSL distribution: `Ubuntu`, WSL version 2.
- Training workspace is visible in WSL:

```bash
ai/lora_training
```

- GPU visible through WSL:

```text
NVIDIA GeForce RTX 4070 Ti SUPER, 16376 MiB, driver 560.94
```

- Conda exists at:

```bash
<conda-root>/bin/conda
```

- Existing conda envs observed:

```text
base
dyslexia-summary
```

- `conda` and `python` may not be on PATH in a non-login `wsl.exe -e bash -lc` shell. Use the explicit conda profile path:

```bash
source <conda-root>/etc/profile.d/conda.sh
```

## Read-Only / Do-Not-Touch Paths

Do not modify source datasets:

```text
ai/data_preparation/final_lora_data/outputs/final_dataset_v1
ai/data_preparation/final_lora_data/outputs/final_dataset_v1_training_system_clean
```

Do not modify approved split/export data except by reading:

```text
ai/lora_training/data/splits
ai/lora_training/data/teammate_exports
```

Do not delete or modify the old WSL reference project/env:

```bash
<previous-project-path>
<previous-conda-env-path>/dyslexia-summary
```

If `clearread-llama-lora` already exists, inspect it first. Do not delete/recreate it unless you can prove it was created by this worker and is safe to replace. If unsure, stop and report the blocker.

## Writable Paths

The new conda environment may be created under:

```bash
<conda-env-path>/clearread-llama-lora
```

Create or update these files under the training workspace:

```text
scripts\check_wsl_training_env.py
scripts\check_wsl_training_env.sh
configs\clearread-llama-lora_environment.yml
configs\clearread-llama-lora_pip_freeze.txt
reports\WSL_ENVIRONMENT_REPORT.md
logs\decisions\worker_003_wsl_environment_setup.md
```

If a file cannot be created because the environment setup fails early, create the report/log with the failure details instead.

## Installation Strategy

Use WSL, not Windows Python.

Start from the known conda path:

```powershell
wsl.exe -e bash -lc 'source <conda-root>/etc/profile.d/conda.sh && conda --version'
```

Recommended default environment:

```bash
conda create -y -n clearread-llama-lora python=3.11 pip
conda activate clearread-llama-lora
python -m pip install --upgrade pip setuptools wheel packaging ninja cmake
```

Then install a CUDA-enabled PyTorch build and QLoRA stack using the current official docs you read. Prefer a route compatible with the observed WSL driver and RTX 4070 Ti SUPER.

Current central-brain preference:

1. Install PyTorch with a CUDA wheel compatible with the driver, starting with CUDA 12.4 or the current officially recommended compatible wheel if docs indicate a better choice.
2. Install Unsloth by the current official simple WSL/Linux route where possible.
3. Install or verify these packages:
   - `torch`
   - `transformers`
   - `datasets`
   - `accelerate`
   - `peft`
   - `trl`
   - `bitsandbytes`
   - `unsloth`
   - `huggingface_hub`
   - `safetensors`
   - `sentencepiece`
   - `protobuf`
4. If the simple route fails, record the exact failure and try at most one official Unsloth fallback route, such as the auto-install command generator from the official docs. Record the generated command before executing it.
5. If Unsloth remains blocked but the vanilla `transformers` + `peft` + `trl` + `bitsandbytes` stack works, report this as a blocker for central-brain decision. Do not silently switch the training route.

Important:

- Do not install packages into the old `dyslexia-summary` env.
- Do not run full model training.
- Do not put package caches, conda env directories, Hugging Face caches, base models, adapters, or checkpoints into Git.
- Do not print or save Hugging Face tokens.

## Required Verification Script

Create:

```text
scripts\check_wsl_training_env.py
```

The script must print JSON or clear key/value output containing:

- Python executable and version.
- Platform info.
- `torch.__version__`.
- `torch.version.cuda`.
- `torch.cuda.is_available()`.
- CUDA device count.
- GPU name.
- GPU total VRAM.
- `torch.cuda.is_bf16_supported()`.
- Versions for `transformers`, `datasets`, `accelerate`, `peft`, `trl`, `bitsandbytes`, `unsloth`, `huggingface_hub`, `safetensors`, and `sentencepiece` if installed.
- A check that `unsloth` can be imported before `transformers` in a fresh Python process.

Run it from WSL inside `clearread-llama-lora`.

Also create:

```text
scripts\check_wsl_training_env.sh
```

This shell script should activate the conda env and run the Python checker from:

```bash
ai/lora_training
```

## Hugging Face Access Check

Check Hugging Face status without exposing secrets.

Required checks:

- Whether `hf` CLI is available.
- Whether `hf auth whoami` succeeds.
- Whether `huggingface_hub.HfApi().model_info(...)` can access metadata for:

```text
unsloth/Llama-3.1-8B-Instruct-unsloth-bnb-4bit
unsloth/Llama-3.1-8B-Instruct-bnb-4bit
meta-llama/Meta-Llama-3.1-8B-Instruct
```

If a model id is not found or access is denied, record it clearly. Do not download the model.

If the installed current Unsloth catalog uses a corrected model id, record the corrected id and the source used to decide it.

## Required Reports

Create:

```text
reports\WSL_ENVIRONMENT_REPORT.md
```

It must include:

- date/time,
- WSL distribution/version,
- conda path,
- env name and path,
- Python version,
- exact install commands used,
- docs consulted and URLs,
- GPU/driver info from WSL,
- `torch.cuda.is_available()` result,
- package versions,
- import verification results,
- BF16 support result,
- Hugging Face auth/model metadata check result,
- environment export paths,
- known limitations,
- pass/fail recommendation.

Create:

```text
logs\decisions\worker_003_wsl_environment_setup.md
```

It must include:

- work order path,
- command summary,
- env creation status,
- verification command output summary,
- Git branch/commit/push result,
- blockers or deviations,
- recommendation for central-brain pass/fail.

Export environment records:

```bash
conda env export -n clearread-llama-lora --no-builds > configs/clearread-llama-lora_environment.yml
conda run -n clearread-llama-lora python -m pip freeze > configs/clearread-llama-lora_pip_freeze.txt
```

Ensure these files contain no secrets before committing.

## Team Repo

Team repo path:

```text
<team-repo-root>
```

Required branch:

```text
feature/ai-llama-lora-training
```

Verify the branch before making repo-side changes.

## Git-Safe Repo Outputs

Mirror only Git-safe files into the team repo. Use these paths unless the repo already has a better AI convention:

```text
ai\scripts\check_wsl_training_env.py
ai\scripts\check_wsl_training_env.sh
ai\configs\clearread-llama-lora_environment.yml
ai\configs\clearread-llama-lora_pip_freeze.txt
ai\reports\WSL_ENVIRONMENT_REPORT.md
ai\logs\decisions\worker_003_wsl_environment_setup.md
```

Do not commit:

- conda env directories,
- package caches,
- Hugging Face caches,
- downloaded model files,
- adapters,
- checkpoints,
- `.safetensors`, `.pt`, `.pth`, `.bin`,
- raw JSONL data.

Before committing, verify:

```powershell
git ls-files 'ai/**/*.jsonl'
git ls-files 'ai/**/*.safetensors' 'ai/**/*.pt' 'ai/**/*.pth' 'ai/**/*.bin'
```

Both should return nothing.

## Git Gate

Before repo-side changes:

1. Verify the team repo is on:

```text
feature/ai-llama-lora-training
```

2. Verify the team repo worktree is clean or only contains your own intended Worker 003 changes.
3. Do not overwrite unrelated changes.

After creating workspace outputs:

1. Copy/mirror Git-safe files to the repo paths listed above.
2. Stage only Git-safe files.
3. Check staged files before committing.
4. Commit with:

```text
chore(ai): document WSL training environment
```

5. Push to:

```text
origin/feature/ai-llama-lora-training
```

If there are no repo-side changes to commit, explain why.

## Memory Update

Update:

```text
ai/lora_training/history/internal_planning/TRAINING_MEMORY_SUMMARY.md
```

Record:

- Worker 003 was executed,
- env name/path,
- Python version,
- key package versions,
- CUDA/GPU verification,
- Hugging Face auth/model access result,
- report/log/config files created,
- Git commit/push result,
- blockers or deviations,
- recommended next worker.

Important memory-safety rule:

- Worker 003 must write its memory update as provisional, clearly labeled `Worker 003 reported, pending central-brain review`.
- Do not rewrite, delete, or reinterpret central-brain pass/fail decisions or approved facts.
- Do not mark Worker 003 as passed. Only the central-brain chat can mark a worker as passed after review.
- Keep the memory concise and factual.

## Acceptance Criteria

This worker passes if:

- `clearread-llama-lora` exists and can be activated in WSL,
- `torch.cuda.is_available()` is true inside the env,
- the RTX 4070 Ti SUPER is visible inside the env,
- the core packages import successfully,
- `unsloth` import works, preferably before `transformers` in a fresh process,
- Hugging Face auth/model metadata status is checked and recorded,
- environment report/log/config files exist,
- Git-safe files are committed and pushed,
- no raw JSONL/model/cache/checkpoint files are committed,
- final response clearly reports files changed, commands run, verification results, Git result, and blockers.

If package installation fails, this worker can still return a useful failure report, but central brain will not pass it for smoke training until CUDA and imports are working.

## Final Response Template

Return a concise report with these headings:

```text
Status:
Files created/changed:
Commands run:
Environment verification:
Package versions:
Hugging Face access:
Git commit/push:
Safety checks:
Blockers or deviations:
Next recommended worker:
```

Do not include unnecessary long command output. Summarize important command results.
