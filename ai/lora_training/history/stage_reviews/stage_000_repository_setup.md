# Stage 000 Git Branch And Safety Setup

Date/time: 2026-04-28 12:58:37 +10:00

## Repository

- Team repo path: `<team-repo-root>`
- Starting branch: `feature/text-chunking`
- Final branch: `feature/ai-llama-lora-training`
- Remote URL: `https://github.com/fit5120-tp43-12am/fit5120-tp43-newclearread`
- Worktree clean before branch switch: yes

## Git Actions

- Read required memory/protocol/plan files before touching the repo: yes
- Fetched remote: yes, `git fetch origin`
- Checked out `dev`: yes
- Pulled latest `dev`: yes, `git pull --ff-only origin dev`
- Latest available `dev` commit before branch creation: `a868435`
- Target branch status: created locally from latest available `dev`

## Gitignore Protection

The root `.gitignore` did not already contain the required AI training artifact protections. Added:

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

Also added a narrow exception so package-ready process records can be committed under `ai/logs/decisions/*.md` while general logs remain ignored.

## Files Staged Or Committed

Expected package-ready files:

- `.gitignore`
- `ai/logs/decisions/git_setup_000.md`

Commit hashes:

- `cea843f` for `chore(ai): set up training branch safety`
- `c017273` for `docs(ai): record git setup push result` (final pushed HEAD)

Push result: pushed `feature/ai-llama-lora-training` to `origin`, set upstream tracking to `origin/feature/ai-llama-lora-training`, and verified local HEAD matches upstream at `c017273`.

## Safety Checks

- No source dataset directories were modified.
- No old WSL training projects or environments were modified.
- No JSONL data, model weights, adapters, checkpoints, optimizer states, Hugging Face cache, Unsloth cache, or large logs were staged.

## Blockers Or Deviations

- No blockers.
- The existing repo-side AI convention is `ai/`, so the package-ready decision log mirror is placed under `ai/logs/decisions/`.

## Next Recommended Stage

Stage 001: Profile Source Distributions And Create Splits.
