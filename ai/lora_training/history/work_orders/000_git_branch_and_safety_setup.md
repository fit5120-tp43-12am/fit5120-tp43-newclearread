# Worker 000: Git Branch And Safety Setup

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
```

## Purpose

Prepare the team Git repository for AI training process records before any data split, environment setup, smoke test, or training work begins.

This is a safety gate. Do not start data processing or model training in this worker.

## Team Repository

Team repo path:

```text
<team-repo-root>
```

Expected remote:

```text
https://github.com/fit5120-tp43-12am/fit5120-tp43-newclearread
```

Target base branch:

```text
dev
```

Target AI training branch:

```text
feature/ai-llama-lora-training
```

## Training Workspace

Training workspace path:

```text
ai/lora_training
```

You may write a local decision log here:

```text
ai/lora_training/history/decision_reviews/git_setup_000.md
```

You may also mirror a Git-safe copy of the decision log into the team repo under an AI folder, such as:

```text
ai\logs\decisions\git_setup_000.md
```

If the repo already has an established AI/documentation folder, use the existing convention instead and explain it.

## Read-Only / Do-Not-Touch Paths

Do not modify any source dataset:

```text
ai/data_preparation/final_lora_data/outputs/final_dataset_v1
ai/data_preparation/final_lora_data/outputs/final_dataset_v1_training_system_clean
```

Do not create, edit, delete, or move files under source data directories.

Do not modify old WSL training projects or environments:

```text
<previous-wsl-project-path>
<previous-conda-env-path>\dyslexia-summary
```

## Allowed Changes

Inside the team repo, you may:

- create or checkout `feature/ai-llama-lora-training`,
- update the root `.gitignore` to protect AI training artifacts,
- create a small AI process-record folder if none exists,
- create a small Git setup report,
- create/update a short AI README/runbook placeholder if useful.

Inside the training workspace, you may:

- create `logs\decisions\git_setup_000.md`.

## Hard Safety Rules

- Do not run destructive Git commands such as `git reset --hard`, `git clean`, or `git checkout -- <file>`.
- Do not discard or overwrite existing user/team changes.
- If the team repo has uncommitted changes before you start, stop before switching branches and report the dirty files.
- If branch checkout or pull would overwrite changes, stop and report the blocker.
- Do not commit large data or model files.
- Do not commit full JSONL split data, base models, LoRA adapters, checkpoints, optimizer states, Hugging Face cache, Unsloth cache, or large logs.

## Required Gitignore Protection

Ensure the team repo protects at least these patterns, adapting paths if the repo already has a better convention:

```gitignore
ai/data/**/*.jsonl
ai/data/**/*.json
ai/models/
ai/outputs/
ai/checkpoints/
ai/cache/
*.safetensors
*.pt
*.pth
*.bin
unsloth_compiled_cache/
```

If similar rules already exist, do not duplicate them unnecessarily. Report what already existed and what you added.

## Execution Steps

1. Read the required memory/protocol/plan files.
2. Inspect the team repo:
   - current branch,
   - remote URL,
   - worktree status,
   - existing `.gitignore`,
   - existing AI-related folders.
3. If the worktree is dirty, stop and report. Do not switch branches.
4. If clean, fetch the remote.
5. Checkout `dev`.
6. Pull latest `dev` using a fast-forward-only pull.
7. Create or checkout `feature/ai-llama-lora-training`.
   - If the branch already exists locally, checkout it without resetting it.
   - If it does not exist locally but exists on remote, checkout the remote branch.
   - If it does not exist anywhere, create it from latest `dev`.
8. Add or confirm `.gitignore` protection for AI training artifacts.
9. Create the local decision log:

```text
ai/lora_training/history/decision_reviews/git_setup_000.md
```

10. Create a Git-safe copy of the decision log inside the team repo, preferably:

```text
ai\logs\decisions\git_setup_000.md
```

11. Stage only Git-safe files.
12. Show staged files before committing.
13. If there are staged changes, commit with a clear message, such as:

```text
chore(ai): set up training branch safety
```

14. Push `feature/ai-llama-lora-training` to remote.

If there are no changes to commit, still verify the branch exists and report whether it was pushed/tracked.

## Required Report Contents

The local and repo decision logs should include:

- Date/time.
- Team repo path.
- Starting branch and final branch.
- Remote URL.
- Whether worktree was clean.
- Whether `dev` was fetched/pulled.
- Whether `feature/ai-llama-lora-training` was created or already existed.
- `.gitignore` rules confirmed or added.
- Files staged/committed.
- Commit hash if a commit was created.
- Push result.
- Any blockers or deviations.
- Clear next recommended worker: Worker 001 profile and split.

## Acceptance Criteria

This worker passes if:

- The team repo is on `feature/ai-llama-lora-training`, or a blocker is clearly reported before unsafe action.
- The branch is based on latest available `dev`, unless blocked and explained.
- AI data/model/checkpoint/cache artifacts are protected by `.gitignore`.
- No large files are staged or committed.
- A decision log exists in the training workspace.
- A Git-safe copy of the decision log exists in the team repo if possible.
- Git-safe changes are committed and pushed, or no-change state is clearly explained.

## Final Response Template

Return a concise report with these headings:

```text
Status:
Files changed:
Commands run:
Git branch/result:
Commit/push:
Safety checks:
Blockers:
Next recommended worker:
```

Do not include unnecessary long command output. Summarize important command results.
