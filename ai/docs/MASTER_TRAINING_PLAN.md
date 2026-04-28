# ClearRead Llama LoRA Training Master Plan

Last updated: 2026-04-28

This plan is written for review by the central-brain chat. It defines the intended sequence, worker-chat boundaries, deliverables, and pass/fail gates for the ClearRead local Llama LoRA training phase.

## 0. Operating Principles

- The current chat is the central-brain chat.
- Execution work should be done by worker chats using task files in `training/work_orders`.
- Every worker must read `TRAINING_MEMORY.md` first, then read its assigned work order.
- The central-brain chat reviews worker results before the next worker starts.
- Worker memory updates are provisional until central-brain review. Workers must not overwrite central-brain decisions or approved facts.
- The central-brain chat independently verifies important worker claims before promoting them into approved memory.
- Source datasets are read-only. Any data operation must create new derived outputs.
- The current working area for this phase is:

```text
C:\Users\Aufb\Desktop\fit5120\iteration1\training
```

## 1. Current Goal

Train, test, and prepare a local Llama-3.1-8B LoRA/QLoRA summarization model for ClearRead.

The model should read dense English source text and output exactly one JSON object:

```json
{"main_idea":"...","key_points":["...","...","...","..."]}
```

The output must have exactly two short faithful `main_idea` sentences and exactly four short high-level `key_points`.

## 2. Source Data

Use the system-prompt-cleaned derived dataset:

```text
C:\Users\Aufb\Desktop\fit5120\iteration1\data\final_lora_data\outputs\final_dataset_v1_training_system_clean\accepted
```

Use the 7 per-domain files as the source for split work:

| Domain | File | Count | Percent |
|---|---|---:|---:|
| assignment_rubric | `assignment_rubric_v1.jsonl` | 83 | 5.72% |
| tech_doc | `tech_doc_v1.jsonl` | 89 | 6.13% |
| academic_book | `academic_book_v1.jsonl` | 233 | 16.05% |
| academic_paper | `academic_paper_v1.jsonl` | 486 | 33.47% |
| public_service | `public_service_v1.jsonl` | 198 | 13.64% |
| medlineplus | `medlineplus_v1.jsonl` | 230 | 15.84% |
| gen_know | `gen_know_v1.jsonl` | 133 | 9.16% |
| Total | `all_v1.jsonl` | 1452 | 100.00% |

Do not modify:

```text
C:\Users\Aufb\Desktop\fit5120\iteration1\data\final_lora_data\outputs\final_dataset_v1
```

## 3. Split Design

The overall split is fixed:

| Split | Count | Percent |
|---|---:|---:|
| train | 1162 | 80% |
| validation | 145 | 10% |
| test | 145 | 10% |

Domain targets:

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

Length buckets for balancing must preserve the real data shape:

| Bucket | Rule | Source Count | Source Percent |
|---|---|---:|---:|
| short | `<=400` words | 241 | 16.60% |
| medium | `401-800` words | 1018 | 70.11% |
| long | `>=801` words | 193 | 13.29% |

These are the canonical Worker 001 counts using regex `[A-Za-z0-9]+(?:['-][A-Za-z0-9]+)*`.

The split should use approximate joint stratification over:

```text
domain x natural_length_bucket
```

This means validation and test should first match the accepted per-domain target counts, then within each domain preserve that domain's real short/medium/long distribution as closely as integer counts allow. Train receives the remaining records.

## 4. Worker Sequence

### Worker 000: Git Branch And Safety Setup

Task file:

```text
training/work_orders/000_git_branch_and_safety_setup.md
```

Scope:

- Go to the team repo:

```text
C:\Users\Aufb\Desktop\fit5120\iteration1\code\fit5120-tp43-newclearread
```

- Fetch latest remote.
- Checkout latest `dev`.
- Create or verify branch:

```text
feature/ai-llama-lora-training
```

- Add or confirm `.gitignore` rules for AI training artifacts.
- Decide the repo-side folder for small AI training files, likely `ai/`.
- Do not copy full JSONL data, model weights, adapters, checkpoints, or caches into Git.

Acceptance gate:

- Branch exists and is based on latest available `dev`.
- Worktree status is understood and reported.
- `.gitignore` protects data/model/checkpoint/cache artifacts.
- A short Git setup report is saved under `training/logs/decisions/`.
- No large files are staged.

### Worker 001: Profile Source Distributions And Create Splits

Status: completed and passed central-brain review on 2026-04-28.

Task file to create:

```text
training/work_orders/001_profile_and_create_data_splits.md
```

Scope:

- Implement `scripts/create_stratified_splits.py`.
- Profile source domain counts and percentages.
- Profile source length statistics and fixed length buckets.
- Create train/val/test/smoke split files.
- Create manifest and reports.

Required outputs:

```text
reports/source_distribution_profile.json
reports/SOURCE_DISTRIBUTION_PROFILE.md
data/splits/train.jsonl
data/splits/val.jsonl
data/splits/test.jsonl
data/splits/smoke_test_10.jsonl
data/splits/split_manifest.json
data/splits/SPLIT_REPORT.md
```

Acceptance gate:

- Counts exactly match the domain target table.
- `smoke_test_10.jsonl` is sampled only from train.
- No record appears in more than one of train/val/test.
- Manifest records domain, source file, source line, stable hash, word count, length bucket, and split.
- `SPLIT_REPORT.md` compares source/train/val/test by domain and by `domain x natural_length_bucket`.
- Source datasets are not modified.

Git gate after Worker 001:

- Copy or mirror Git-safe files into the team repo, such as split script, source distribution report, split report, and any small manifest/hash summaries.
- Do not commit full `train.jsonl`, `val.jsonl`, `test.jsonl`, or `smoke_test_10.jsonl` unless the user explicitly changes the policy.
- Commit and push the Git-safe process records to `feature/ai-llama-lora-training`.

### Worker 002: Teammate Export After Split

Status: completed and passed central-brain review on 2026-04-28.

Run only after Worker 001 passes.

Task file:

```text
training/work_orders/002_create_teammate_exports.md
```

Scope:

- Create simple paired user/assistant exports from the accepted split outputs.
- Do not include system prompt unless the user later asks for it.
- Keep stable ids so user and assistant files align.

Expected output directory:

```text
data/teammate_exports
```

Acceptance gate:

- Exports contain only derived data from approved split files.
- Each user row maps cleanly to one assistant row by stable id.
- Counts match the selected split/source scope.

Git gate after Worker 002:

- Commit only scripts/docs/reports describing the export process.
- Do not commit teammate export datasets unless the user explicitly approves.

### Worker 003: Clean WSL Environment Setup

Status: completed and passed central-brain review with notes on 2026-04-28.

Task file:

```text
training/work_orders/003_setup_wsl_training_environment.md
```

Scope:

- Create or verify WSL conda env `clearread-llama-lora`.
- Install the minimum stack for Llama 3.1 8B QLoRA.
- Prefer Unsloth QLoRA route first.
- Verify CUDA and core imports.
- Check Hugging Face authentication/access for Llama 3.1 models.

Acceptance gate:

- `torch.cuda.is_available()` is true in WSL.
- GPU is visible.
- Required packages import cleanly.
- Environment report is saved under `logs/`.
- Old WSL env/project remains untouched.

Git gate after Worker 003:

- Commit environment setup notes, dependency list, and runbook updates.
- Do not commit conda environments, package caches, or downloaded models.

### Worker 004: Smoke Training Scripts And Configs

Status: completed and passed central-brain review on 2026-04-28.

Task file:

```text
training/work_orders/004_prepare_smoke_training.md
```

Scope:

- Create smoke config for Llama-3.1-8B-Instruct QLoRA.
- Create smoke training script.
- Create inference sanity-check script.
- Add a label-mask sanity check proving only assistant JSON tokens train.
- Add training progress and estimated remaining/completion time reporting to the smoke/full training scripts where practical.

Acceptance gate:

- Scripts are runnable from the current training folder.
- Config records model id, LoRA settings, max sequence length, batch settings, and output paths.
- Label-mask check shows system/user tokens are masked from loss.
- Scripts show or log progress with elapsed time, estimated remaining time, and estimated completion time.

Git gate after Worker 004:

- Commit smoke scripts, configs, and label-mask validation report.

### Worker 005: Run Llama Smoke Test

Status: completed and passed central-brain review on 2026-04-28.

Task file:

```text
training/work_orders/005_run_llama_smoke_test.md
```

Scope:

- Train on `data/splits/smoke_test_10.jsonl` for 20-50 steps.
- Save adapter under `models/adapters` or smoke output folder.
- Run inference sanity checks.
- Create smoke log.
- Capture elapsed time, average seconds per step, estimated remaining time while running, and actual finish time in the smoke log.

Acceptance gate:

- No OOM.
- Adapter saves.
- Inference runs.
- Outputs are usually valid JSON and use the required keys.
- `logs/smoke_test_001.md` records command, environment, package versions, config, timing/ETA, results, and decision.

Central-brain review summary:

- Smoke training completed without OOM.
- Local adapter saved under `models/adapters/smoke_llama31_8b_qlora`.
- Central-brain independently reran inference against the saved adapter and confirmed `3/3` schema pass.
- Git HEAD matched upstream at `919fc29575075e0fd60664ae1f6e7792de2f377c`.
- No JSONL data or model binaries were tracked by Git.

Git gate after Worker 005:

- Commit smoke-test markdown log and small report summaries.
- Do not commit adapter files, checkpoints, or raw large logs.

### Worker 006: Full Training Candidate A

Status: completed and passed central-brain review with notes on 2026-04-28.

Task file:

```text
training/work_orders/006_train_candidate_a_3epoch.md
```

Scope:

- Train with train/val using first formal config.
- Starting route: Llama-3.1-8B-Instruct + SFT + QLoRA.
- Initial settings: max seq 3072, LoRA r 16, alpha 32, dropout 0.05, effective batch 8, 3 epochs, learning rate 2e-4.

Acceptance gate:

- Training completes without OOM.
- Validation loss is logged.
- Adapter/checkpoint path is recorded.
- Format sanity checks run on validation samples.
- Training progress exposes elapsed time, estimated remaining time, and estimated completion time during the run where practical.
- `logs/full_train_candidate_3epoch.md` records the full experiment, including timing/ETA accuracy.

Git gate after Worker 006:

- Commit formal training config, training script changes, and markdown experiment log.
- Do not commit adapters/checkpoints/model files.

Central-brain review summary:

- Candidate A completed 3 epochs without OOM.
- Train/validation preflight found `0` truncated records and non-empty assistant labels for all records.
- Final train loss was `0.4797596574748216`.
- Validation loss was `0.9654271602630615`.
- Validation inference schema check passed in Worker 006 on `10/10` examples.
- Central brain independently reran validation inference on `5` examples and got `5/5` schema pass.
- No test set usage was found.
- Candidate A is viable for validation-quality audit, but not yet selected as final model.

### Worker 007: Candidate A Validation Quality Audit

Status: completed and passed central-brain review on 2026-04-28.

Task file:

```text
training/work_orders/007_candidate_a_validation_quality_audit.md
```

Scope:

- Use Candidate A only.
- Generate predictions for all validation records.
- Compute deterministic JSON/schema/sentence/readability/encoding checks.
- Break down metrics by domain and length bucket.
- Perform stratified manual validation review.
- Decide whether Candidate A is ready for final evaluation or whether Candidate B should be considered.
- Do not train.
- Do not use the test set.

Acceptance gate:

- All 145 validation records are evaluated or any missing records are explained.
- Reports separate deterministic checks from manual/heuristic quality judgments.
- Mojibake/encoding artifacts are counted in both predictions and gold targets.
- Local prediction JSONL is not committed to normal Git.

Git gate after Worker 007:

- Commit validation-audit script, markdown report, and decision log only.
- Do not commit prediction JSONL, raw data, adapters, checkpoints, or model files.

Central-brain review summary:

- Validation audit evaluated `145/145` validation records.
- JSON parse/schema/key-order compliance was `145/145`.
- Main-idea two-sentence heuristic was `144/145`.
- Key-point one-sentence heuristic was `143/145`.
- Manual review found `pass` 14, `minor_issue` 2, `major_issue` 0, `uncertain` 0.
- Candidate B is not recommended from validation evidence.
- Candidate A is selected for final held-out test evaluation, but not yet declared final artifact.

### Optional Candidate B

Status: skipped for now.

Run only if Candidate A underfits or format/quality checks are weak.

Task file:

```text
not created
```

Possible changes:

- 5 epochs with same split.
- Learning rate adjustment only if Candidate A evidence supports it.
- Max sequence length 4096 only if memory and tokenizer evidence supports it.

Acceptance gate:

- Same reporting requirements as Candidate A.
- Decision explains whether Candidate B replaces Candidate A.
- Test set is still unused.

Git gate if Candidate B is later reopened:

- Commit Candidate B config and experiment log if Candidate B is run.
- Do not commit adapters/checkpoints/model files.

### Worker 008: Final Test Evaluation For Candidate A

Status: completed and passed central-brain review with final-selection note on 2026-04-28.

Task file:

```text
training/work_orders/008_final_evaluation_candidate_a.md
```

Scope:

- Use the final chosen model.
- Evaluate only once on `data/splits/test.jsonl` after model choice is made.
- Measure JSON parse rate, schema accuracy, sentence-count compliance, key-point count compliance, readability signals, and manual spot checks.

Acceptance gate:

- Test report is saved under `reports/`.
- Evaluation clearly separates deterministic checks from human/LLM semantic judgments.
- Special attention is given to `medlineplus`, `public_service`, long inputs, and assignment/rubric instruction-like inputs.

Git gate after Worker 008:

- Commit final evaluation scripts, reports, and markdown summary.
- Do not commit test JSONL data or model artifacts.

Central-brain review summary:

- Final held-out test evaluation used `145/145` test records.
- JSON parse was `145/145`.
- Raw schema compliance was `144/145`.
- The only schema miss was row 87, an academic-paper medium record with `7` key points instead of exactly `4`.
- Manual review found `pass` 14, `minor_issue` 2, `major_issue` 1, `uncertain` 0.
- No broad domain, length, safety, instruction-following, refusal, markdown, extra-text, or mojibake collapse was found.
- Candidate A is selected as the final raw LoRA adapter for this training cycle.
- Deployment/local inference must use a schema guard because raw output compliance was not perfect.

### Worker 009: Artifact Packaging And Local Deployment Notes

Status: task file created on 2026-04-28 and ready for a worker chat.

Task file:

```text
training/work_orders/009_package_artifact_and_deployment_notes.md
```

Scope:

- Organize final LoRA adapter files.
- Document how to load/run the model locally.
- Decide whether backend loads adapter locally or uses a service.
- Do not commit large model artifacts to normal Git.

Acceptance gate:

- Final artifact location is clear.
- Run instructions are reproducible.
- Git-safe files are separated from large artifacts.

Git gate after Worker 009:

- Commit deployment notes and artifact metadata only.
- Keep actual model artifacts outside normal Git.

## 5. Central-Brain Review Gates

After each worker returns, the central-brain chat should check:

- Did the worker read `TRAINING_MEMORY.md` and the assigned work order?
- Did it stay inside scope?
- Did it modify any read-only source data?
- Are required outputs present?
- Do counts, hashes, and validation checks pass?
- Are reports detailed enough for project process records?
- Did the worker mark any memory updates as provisional rather than overwriting approved central-brain conclusions?
- Are worker claims independently supported by local evidence?
- Is the next worker unblocked?

The central-brain decision should be one of:

- pass,
- pass with notes,
- request fixes,
- reject and rewrite task.

## 6. Git Plan

Recommended branch:

```text
feature/ai-llama-lora-training
```

Git is not optional process decoration. It is a required gate at major milestones.

Commit to Git:

- scripts,
- configs,
- README/runbook,
- reports and markdown logs,
- small metadata/manifests where appropriate.

Required Git checkpoints:

- after Worker 000: branch and `.gitignore` setup,
- after Worker 001: split/profile scripts and reports,
- after Worker 002: teammate export scripts/reports if run,
- after Worker 003: environment setup docs,
- after Worker 004: smoke scripts/configs,
- after Worker 005: smoke-test log and summary,
- after Worker 006: Candidate A config/scripts/log,
- after Worker 007: Candidate B config/scripts/log if run,
- after Worker 008: final evaluation scripts/reports,
- after Worker 009: deployment notes/artifact metadata.

Do not commit:

- full JSONL training data,
- base model files,
- LoRA `.safetensors`,
- checkpoints,
- optimizer states,
- Hugging Face or Unsloth caches.

## 7. Immediate Next Step

Worker 008 has passed. The immediate next step is to run Worker 009 from:

```text
training/work_orders/009_package_artifact_and_deployment_notes.md
```

The user can open a worker chat and instruct it to read that work order and execute it fully.
