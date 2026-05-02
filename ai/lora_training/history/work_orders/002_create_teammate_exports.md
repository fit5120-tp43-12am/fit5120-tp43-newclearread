# Worker 002: Create Teammate User And Assistant Exports

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
ai/lora_training/data/splits\SPLIT_REPORT.md
ai/lora_training/history/decision_reviews/worker_001_profile_split.md
```

## Purpose

Create simple paired export datasets for the teammate after the approved train/validation/test split.

The user explicitly wants the source text and assistant answer split into two corresponding datasets:

- one user/source-text dataset,
- one assistant/answer dataset,
- no system prompt in either export.

This worker must:

- read only the approved split outputs from Worker 001,
- create aligned user and assistant JSONL export files,
- keep stable pair ids so rows can be joined exactly,
- create metadata-only manifest/report files,
- update the local training memory,
- commit and push only Git-safe scripts/reports/logs to the team repo.

Do not train any model in this worker.

## Approved Inputs

Use only these approved derived split files:

```text
ai/lora_training/data/splits\train.jsonl
ai/lora_training/data/splits\val.jsonl
ai/lora_training/data/splits\test.jsonl
ai/lora_training/data/splits\split_manifest.json
```

Optional read-only input for comparison only:

```text
ai/lora_training/data/splits\smoke_test_10.jsonl
```

Do not modify any file under:

```text
ai/data_preparation/final_lora_data/outputs/final_dataset_v1
ai/data_preparation/final_lora_data/outputs/final_dataset_v1_training_system_clean
ai/lora_training/data/splits
```

## Training Workspace Outputs

Create or update these files under:

```text
ai/lora_training
```

Required script:

```text
scripts\create_teammate_exports.py
```

Required export output directory:

```text
data\teammate_exports
```

Required export files:

```text
data\teammate_exports\user_all.jsonl
data\teammate_exports\assistant_all.jsonl
data\teammate_exports\user_train.jsonl
data\teammate_exports\assistant_train.jsonl
data\teammate_exports\user_val.jsonl
data\teammate_exports\assistant_val.jsonl
data\teammate_exports\user_test.jsonl
data\teammate_exports\assistant_test.jsonl
```

Required metadata/report outputs:

```text
data\teammate_exports\teammate_export_manifest.json
reports\TEAMMATE_EXPORT_REPORT.md
logs\decisions\worker_002_teammate_exports.md
```

Update the local memory file at the end:

```text
TRAINING_MEMORY.md
```

## Export Row Shape

Each user JSONL row must contain exactly these keys in this order:

```json
{
  "pair_index": 0,
  "pair_id": "...",
  "record_id": "...",
  "stable_hash": "...",
  "split": "train",
  "domain": "...",
  "source_file": "...",
  "source_line": 1,
  "natural_length_bucket": "medium",
  "user_word_count": 493,
  "user_char_count": 3130,
  "text": "..."
}
```

Each assistant JSONL row must contain exactly these keys in this order:

```json
{
  "pair_index": 0,
  "pair_id": "...",
  "record_id": "...",
  "stable_hash": "...",
  "split": "train",
  "domain": "...",
  "source_file": "...",
  "source_line": 1,
  "natural_length_bucket": "medium",
  "assistant_word_count": 102,
  "text": "..."
}
```

Rules:

- `pair_id` should be identical in the matching user and assistant rows.
- Use the Worker 001 `record_id` from `split_manifest.json` as `pair_id` unless a strong reason exists not to.
- `pair_index` starts at 0 within each file pair.
- User and assistant files must have the same number of rows and the same row order.
- `text` in user exports must come only from the `messages` role `user`.
- `text` in assistant exports must come only from the `messages` role `assistant`.
- Do not include system prompt text anywhere in the export datasets.
- Do not include a `messages` array in the export datasets.
- Do not change or normalize the user/assistant text unless required for valid JSONL escaping.

## Export Scope And Counts

Create per-split exports:

| File Pair | Source Split | Expected Rows Per File |
|---|---|---:|
| `user_train.jsonl` + `assistant_train.jsonl` | `train.jsonl` | 1162 |
| `user_val.jsonl` + `assistant_val.jsonl` | `val.jsonl` | 145 |
| `user_test.jsonl` + `assistant_test.jsonl` | `test.jsonl` | 145 |

Create all-split exports:

| File Pair | Source Scope | Expected Rows Per File |
|---|---|---:|
| `user_all.jsonl` + `assistant_all.jsonl` | train then val then test | 1452 |

Do not include `smoke_test_10.jsonl` in `user_all.jsonl` or `assistant_all.jsonl`, because smoke records are a subset of train and would duplicate rows.

## Script Requirements

Implement `scripts\create_teammate_exports.py`.

The script should:

1. Load `split_manifest.json` and its `entries`.
2. Load `train.jsonl`, `val.jsonl`, and `test.jsonl`.
3. Parse every JSONL record safely.
4. Require exactly three messages with roles in this order:

```text
system / user / assistant
```

5. Compute the same stable hash method used by Worker 001:

```text
sha256(json.dumps(record, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
```

6. Join each split record to the manifest by `stable_hash`.
7. Extract only the user content and assistant content.
8. Write the paired JSONL exports with deterministic ordering:
   - train source order,
   - then val source order,
   - then test source order for the all files.
9. Write `teammate_export_manifest.json` as metadata only.
10. Write `TEAMMATE_EXPORT_REPORT.md`.

The metadata manifest must not contain raw `text`, `messages`, `system`, `user`, `assistant`, or `content` fields. It may contain:

- source split file hashes,
- output file hashes,
- counts,
- pair-id checks,
- schema version,
- row-shape descriptions,
- date/time,
- script hash,
- Git commit hash if available.

## Required Verification

After running the script, verify:

- `user_train.jsonl` and `assistant_train.jsonl` each have 1162 rows.
- `user_val.jsonl` and `assistant_val.jsonl` each have 145 rows.
- `user_test.jsonl` and `assistant_test.jsonl` each have 145 rows.
- `user_all.jsonl` and `assistant_all.jsonl` each have 1452 rows.
- For each file pair, `pair_index`, `pair_id`, `record_id`, `stable_hash`, `split`, `domain`, `source_file`, `source_line`, and `natural_length_bucket` match row by row.
- No export row contains a `messages` field.
- User export text equals the source record's user message content.
- Assistant export text equals the source record's assistant message content.
- No system prompt text appears in any export `text`.
- The all exports contain train, then val, then test, with no smoke duplicates.
- `teammate_export_manifest.json` contains no raw text fields.
- The original split files remain unchanged. Record pre-run and post-run SHA256 hashes for `train.jsonl`, `val.jsonl`, `test.jsonl`, and `split_manifest.json`.
- The script is deterministic when rerun.

Include verification results in `TEAMMATE_EXPORT_REPORT.md` and `worker_002_teammate_exports.md`.

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
ai\scripts\create_teammate_exports.py
ai\reports\TEAMMATE_EXPORT_REPORT.md
ai\reports\teammate_export_manifest.json
ai\logs\decisions\worker_002_teammate_exports.md
```

Important:

- `teammate_export_manifest.json` is allowed in Git only if it is metadata-only and contains no raw text.
- Do not copy any `data\teammate_exports\*.jsonl` file into the team repo.
- Do not commit source datasets, split JSONL files, teammate export JSONL files, models, adapters, checkpoints, or caches.
- Before committing, check staged files carefully.
- After committing, verify `git ls-files 'ai/**/*.jsonl'` returns nothing.

## Git Gate

Before repo-side changes:

1. Verify the team repo is on:

```text
feature/ai-llama-lora-training
```

2. Verify the team repo worktree is clean or only contains your own intended Worker 002 changes.
3. Do not overwrite unrelated changes.

After creating workspace outputs:

1. Copy/mirror Git-safe files to the repo paths listed above.
2. Stage only Git-safe files.
3. Check staged files before committing.
4. Commit with:

```text
feat(ai): add teammate export workflow
```

5. Push to:

```text
origin/feature/ai-llama-lora-training
```

If there are no repo-side changes to commit, explain why.

## Required Worker Log

Create:

```text
ai/lora_training/history/decision_reviews/worker_002_teammate_exports.md
```

It must include:

- date/time,
- work order path,
- input split paths,
- input split SHA256 hashes before and after,
- script path,
- export paths,
- export file hashes,
- row counts by file,
- pair alignment verification,
- no-system-prompt verification,
- metadata manifest safety verification,
- Git branch,
- commit hash if committed,
- push result,
- blockers or deviations,
- recommendation for central-brain pass/fail.

## Memory Update

Update:

```text
ai/lora_training/history/internal_planning/TRAINING_MEMORY_SUMMARY.md
```

Record:

- Worker 002 was executed,
- files created,
- counts,
- verification summary,
- Git commit/push result,
- any blocker or deviation,
- recommended next worker.

Keep the memory concise and factual.

## Acceptance Criteria

This worker passes if:

- all required export files are created,
- per-split and all-split counts match exactly,
- user and assistant rows align one-to-one by `pair_id` and order,
- no system prompt is included in the exports,
- no source dataset or split file is modified,
- manifest/report/log files exist and record hashes plus verification,
- Git-safe files are committed and pushed,
- raw export JSONL files are not committed to Git,
- final response clearly reports files changed, commands run, verification results, Git result, and blockers.

## Final Response Template

Return a concise report with these headings:

```text
Status:
Files created/changed:
Commands run:
Export verification:
Pairing verification:
Safety checks:
Git commit/push:
Blockers or deviations:
Next recommended worker:
```

Do not include unnecessary long command output. Summarize important command results.
