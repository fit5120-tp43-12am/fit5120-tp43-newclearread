# Worker 001: Profile Source Distributions And Create Data Splits

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

Create a fully reproducible source distribution profile and fixed train/validation/test split for ClearRead LoRA training.

This worker must:

- profile source domain distribution,
- profile source text-length distribution,
- create train/val/test splits using approximate joint stratification over `domain x natural_length_bucket`,
- create a 10-record smoke set from train only,
- generate reports and manifest,
- commit and push Git-safe scripts/reports/logs to the team repo.

Do not train any model in this worker.

## Source Dataset

Use only this read-only source directory:

```text
ai/data_preparation/final_lora_data/outputs/final_dataset_v1_training_system_clean/accepted
```

Source files:

| Domain | File | Count |
|---|---|---:|
| assignment_rubric | `assignment_rubric_v1.jsonl` | 83 |
| tech_doc | `tech_doc_v1.jsonl` | 89 |
| academic_book | `academic_book_v1.jsonl` | 233 |
| academic_paper | `academic_paper_v1.jsonl` | 486 |
| public_service | `public_service_v1.jsonl` | 198 |
| medlineplus | `medlineplus_v1.jsonl` | 230 |
| gen_know | `gen_know_v1.jsonl` | 133 |
| Total | `all_v1.jsonl` | 1452 |

Do not modify this directory or any source JSONL file.

Also do not modify:

```text
ai/data_preparation/final_lora_data/outputs/final_dataset_v1
```

## Training Workspace Outputs

Create or update these files under:

```text
ai/lora_training
```

Required script:

```text
scripts\create_stratified_splits.py
```

Required profile outputs:

```text
reports\source_distribution_profile.json
reports\SOURCE_DISTRIBUTION_PROFILE.md
```

Required split outputs:

```text
data\splits\train.jsonl
data\splits\val.jsonl
data\splits\test.jsonl
data\splits\smoke_test_10.jsonl
data\splits\split_manifest.json
data\splits\SPLIT_REPORT.md
```

Required worker log:

```text
logs\decisions\worker_001_profile_split.md
```

## Team Repo

Team repo path:

```text
<team-repo-root>
```

Required branch:

```text
feature/ai-llama-lora-training
```

Worker 000 should already have created this branch and pushed it. Verify the branch before making repo-side changes.

## Git-Safe Repo Outputs

Mirror only Git-safe files into the team repo. Use these paths unless the repo already has a better AI convention:

```text
ai\scripts\create_stratified_splits.py
ai\reports\source_distribution_profile.json
ai\reports\SOURCE_DISTRIBUTION_PROFILE.md
ai\reports\SPLIT_REPORT.md
ai\reports\split_manifest.json
ai\logs\decisions\worker_001_profile_split.md
```

Important:

- `split_manifest.json` is allowed only if it contains metadata, hashes, counts, source file names, line numbers, domains, word counts, length buckets, and split labels.
- It must not contain raw `system`, `user`, or `assistant` text.
- Do not copy `train.jsonl`, `val.jsonl`, `test.jsonl`, or `smoke_test_10.jsonl` into the team repo.
- Do not commit source datasets, full split JSONL data, models, adapters, checkpoints, or caches.

## Split Design

Overall split:

| Split | Count | Percent |
|---|---:|---:|
| train | 1162 | 80% |
| validation | 145 | 10% |
| test | 145 | 10% |

Per-domain target counts:

| Domain | Total | Train | Val | Test |
|---|---:|---:|---:|---:|
| assignment_rubric | 83 | 67 | 8 | 8 |
| tech_doc | 89 | 71 | 9 | 9 |
| academic_book | 233 | 187 | 23 | 23 |
| academic_paper | 486 | 388 | 49 | 49 |
| public_service | 198 | 158 | 20 | 20 |
| medlineplus | 230 | 184 | 23 | 23 |
| gen_know | 133 | 107 | 13 | 13 |
| Total | 1452 | 1162 | 145 | 145 |

Natural length buckets:

| Bucket | Rule |
|---|---|
| short | `<=400` user words |
| medium | `401-800` user words |
| long | `>=801` user words |

Do not use equal tercile buckets for balancing. Terciles may be reported as descriptive statistics only.

The split must preserve the source dataset's joint distribution over:

```text
domain x natural_length_bucket
```

That means:

- validation/test first match accepted per-domain target counts,
- then within each domain, preserve that domain's real short/medium/long distribution as closely as integer counts allow,
- train receives the remaining records from each `domain x natural_length_bucket` cell.

## Required Parsing And Validation

For every record:

- parse JSONL safely,
- require `messages` roles exactly in this order:

```text
system / user / assistant
```

- extract the `user` message,
- compute English user word count using a documented regex,
- compute user character count,
- assign natural length bucket,
- compute a stable hash.

Recommended stable hash:

```text
sha256(json.dumps(record, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
```

The manifest must not include raw message text.

## Required Source Profile

`source_distribution_profile.json` and `SOURCE_DISTRIBUTION_PROFILE.md` must include:

- total record count,
- per-domain counts and percentages,
- overall natural length bucket counts and percentages,
- per-domain natural length bucket counts and percentages,
- `domain x natural_length_bucket` source cross-tab,
- 100-word histogram for user word count,
- overall user word count stats:
  - min,
  - p10,
  - p25,
  - p33,
  - p50,
  - p67,
  - p75,
  - p90,
  - p95,
  - p99,
  - max,
  - mean,
- per-domain user word count stats using the same fields,
- assistant word count summary,
- role-order validation result,
- source file counts.

Expected known facts to confirm:

- total records: 1452,
- `401-800` user-word records are around 70.18%,
- median user word count is around 623,
- `academic_paper` has 486 records, around 33.47%.

## Required Split Algorithm

Implement the split algorithm in `scripts\create_stratified_splits.py`.

Recommended deterministic approach:

1. Load the 7 per-domain files.
2. Build records with metadata:
   - domain,
   - source file,
   - source line number,
   - stable hash,
   - user word count,
   - user char count,
   - assistant word count,
   - natural length bucket.
3. For each domain, compute source counts per natural length bucket.
4. For each domain and split target, allocate validation/test length-bucket counts using largest-remainder rounding:
   - ideal bucket count = domain split target x source bucket count / domain total.
   - floor all ideals.
   - distribute remaining integer slots to largest fractional remainders.
   - if a bucket has zero source records, it must receive zero.
5. Ensure each domain's validation/test counts match the target table exactly.
6. Ensure no bucket is overdrawn across validation and test.
7. Assign train to the remaining records in each `domain x natural_length_bucket` cell.
8. Within each `domain x natural_length_bucket` cell, choose validation and test records deterministically across the cell's internal length range:
   - sort by user word count, stable hash, source line,
   - select records evenly across the sorted cell rather than taking only the shortest or longest,
   - use a fixed seed only for tie-breaking or block shuffling if needed.
9. Produce train/val/test JSONL in the original message format.
10. Produce `split_manifest.json` with metadata only.
11. Produce reports.

If the largest-remainder method creates an impossible allocation in a small bucket, adjust to the nearest feasible allocation and explain the deviation in `SPLIT_REPORT.md`.

## Smoke Set

Create:

```text
data\splits\smoke_test_10.jsonl
```

Rules:

- sample only from train,
- never sample from validation or test,
- include multiple domains,
- prefer including `medlineplus` and `public_service`,
- include at least one short, one medium, and one long record if available in train,
- keep deterministic selection and record selected ids/hashes in `SPLIT_REPORT.md`.

Recommended composition if available:

- 2 `medlineplus`,
- 2 `public_service`,
- 2 `academic_paper`,
- 1 `academic_book`,
- 1 `tech_doc`,
- 1 `assignment_rubric`,
- 1 `gen_know`.

## Required Verification

After running the script, verify:

- train count = 1162,
- val count = 145,
- test count = 145,
- total unique train/val/test hashes = 1452,
- no overlap between train, val, and test,
- per-domain counts match exactly,
- source files remain unchanged,
- smoke records are all from train,
- smoke has 10 records,
- `split_manifest.json` has 1452 entries,
- manifest contains no raw message content,
- reports exist,
- script is deterministic when rerun with the same seed.

If you compute file hashes for outputs, include them in `SPLIT_REPORT.md` and the worker log.

## Git Gate

Before repo-side changes:

1. Verify the team repo is on:

```text
feature/ai-llama-lora-training
```

2. Verify the team repo worktree is clean or only contains your own intended Worker 001 changes.
3. Do not overwrite unrelated changes.

After creating workspace outputs:

1. Copy/mirror Git-safe files to the repo paths listed above.
2. Stage only Git-safe files.
3. Check staged files before committing.
4. Commit with:

```text
feat(ai): add stratified split profiling workflow
```

5. Push to:

```text
origin/feature/ai-llama-lora-training
```

If there are no repo-side changes to commit, explain why.

## Required Worker Log

Create:

```text
ai/lora_training/history/decision_reviews/worker_001_profile_split.md
```

It must include:

- date/time,
- source dataset path,
- source dataset hash or source file hashes,
- script path,
- output paths,
- split counts,
- domain count verification,
- length bucket verification,
- smoke set selection summary,
- Git branch,
- commit hash if committed,
- push result,
- blockers or deviations,
- recommendation for central-brain pass/fail.

## Acceptance Criteria

This worker passes if:

- all required files are created,
- all split counts match exactly,
- per-domain train/val/test counts match exactly,
- split approximates `domain x natural_length_bucket` distribution and reports any unavoidable integer deviations,
- no source dataset is modified,
- no overlap exists between train/val/test,
- smoke set is from train only,
- manifest has metadata only and no raw message text,
- Git-safe files are committed and pushed,
- full JSONL data files are not committed to Git,
- final response clearly reports files changed, commands run, verification results, Git result, and blockers.

## Final Response Template

Return a concise report with these headings:

```text
Status:
Files created/changed:
Commands run:
Split verification:
Distribution verification:
Smoke set:
Git commit/push:
Safety checks:
Blockers or deviations:
Next recommended worker:
```

Do not include unnecessary long command output. Summarize important command results.
