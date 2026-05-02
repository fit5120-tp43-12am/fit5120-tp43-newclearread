# Central Review: Worker 001 Profile And Split

Date: 2026-04-28

## Reviewed Inputs

- Worker return summary from the central-brain chat.
- `ai/lora_training/data/splits\SPLIT_REPORT.md`
- `ai/lora_training/history/decision_reviews/worker_001_profile_split.md`
- `ai/lora_training/reports/source_distribution_profile.json`
- Team repo status under `<team-repo-root>`

## Central Verification

- Train/validation/test counts are `1162 / 145 / 145`.
- Train/validation/test contain `1452` unique stable hashes.
- Train/validation/test overlaps are all zero.
- Smoke set has `10` records and all smoke hashes are from train.
- Manifest contains `1452` entries under the metadata-only `entries` key.
- Manifest entries contain no raw `messages`, `system`, `user`, `assistant`, or `content` fields.
- Per-domain split counts match the target table exactly.
- Canonical Worker 001 word-count regex is `[A-Za-z0-9]+(?:['-][A-Za-z0-9]+)*`.
- Canonical source natural length buckets are short `241`, medium `1018`, long `193`.
- Validation and test both preserve per-domain targets and approximate each domain's source length-bucket distribution.

## Git Verification

- Team repo branch is `feature/ai-llama-lora-training`.
- Local HEAD equals upstream at `e720eaa6661cdaf4e04fc3819a68e405250b61f6`.
- Worktree is clean.
- No `ai/**/*.jsonl` files are tracked.
- No model binary patterns checked during review were tracked.

## Decision

Worker 001 passes central-brain review.

The next approved work unit is Worker 002, teammate user/assistant exports, using:

```text
ai/lora_training/history/work_orders/002_create_teammate_exports.md
```
