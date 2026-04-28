# Worker 007: Candidate A Validation Quality Audit

Last updated: 2026-04-28

## Role

You are a worker chat for the ClearRead Llama LoRA training project.

You are not the central-brain chat. Execute only this work order, stay within scope, and report back clearly for central-brain review.

## Required Reading

Read these files first, in this order:

```text
C:\Users\Aufb\Desktop\fit5120\iteration1\training\TRAINING_MEMORY.md
C:\Users\Aufb\Desktop\fit5120\iteration1\training\docs\CENTRAL_BRAIN_WORKER_PROTOCOL.md
C:\Users\Aufb\Desktop\fit5120\iteration1\training\docs\MASTER_TRAINING_PLAN.md
C:\Users\Aufb\Desktop\fit5120\iteration1\training\logs\decisions\central_review_worker_006.md
C:\Users\Aufb\Desktop\fit5120\iteration1\training\logs\full_train_candidate_a_3epoch.md
C:\Users\Aufb\Desktop\fit5120\iteration1\training\reports\FULL_TRAIN_CANDIDATE_A_REPORT.md
```

## Purpose

Evaluate Candidate A on the validation split only, before the test set is touched.

This worker must:

- run Candidate A inference on all 145 validation records,
- save local validation predictions,
- compute deterministic output-quality metrics,
- run encoding/mojibake checks on predictions and gold assistant targets,
- compare quality by domain and natural length bucket where metadata allows,
- perform a stratified manual review of validation examples,
- recommend whether Candidate A is ready for final test evaluation or whether Candidate B should be considered,
- commit and push only Git-safe scripts/reports/logs.

This worker must not train a model.

This worker must not use `test.jsonl`.

## Environment

Use WSL and the established training environment:

```bash
source /home/aufb/miniconda3/etc/profile.d/conda.sh
conda activate clearread-llama-lora
cd /mnt/c/Users/Aufb/Desktop/fit5120/iteration1/training
```

Recommended cache environment variables:

```bash
export HF_HOME=/mnt/c/Users/Aufb/Desktop/fit5120/iteration1/training/cache/huggingface
export TRANSFORMERS_CACHE=/mnt/c/Users/Aufb/Desktop/fit5120/iteration1/training/cache/huggingface/transformers
```

Do not copy cache files into Git.

## Inputs

Use only:

```text
C:\Users\Aufb\Desktop\fit5120\iteration1\training\configs\train_llama31_8b_qlora_candidate_a.yaml
C:\Users\Aufb\Desktop\fit5120\iteration1\training\data\splits\val.jsonl
C:\Users\Aufb\Desktop\fit5120\iteration1\training\data\splits\split_manifest.json
C:\Users\Aufb\Desktop\fit5120\iteration1\training\models\adapters\full_candidate_a_3epoch
```

Read-only rule:

- Do not modify `data\splits`.
- Do not modify `data\teammate_exports`.
- Do not modify source datasets under `final_dataset_v1` or `final_dataset_v1_training_system_clean`.
- Do not use `test.jsonl`.
- Do not modify the Candidate A adapter.
- Do not run additional training.

## Required Outputs

Create or update these files under the training workspace:

```text
scripts\evaluate_candidate_a_validation.py
reports\CANDIDATE_A_VALIDATION_QUALITY_REPORT.md
logs\candidate_a_validation_quality_audit.md
logs\decisions\worker_007_candidate_a_validation_quality_audit.md
outputs\evaluation\candidate_a_validation\validation_predictions.jsonl
outputs\evaluation\candidate_a_validation\validation_metrics.json
```

The prediction JSONL and metrics JSON are local artifacts. They may contain generated text and derived validation text, so do not commit them unless central brain later explicitly approves.

Update local memory with a provisional Worker 007 section only:

```text
TRAINING_MEMORY.md
```

## Required Evaluation Script

Create:

```text
scripts\evaluate_candidate_a_validation.py
```

It should:

- import `unsloth` before `transformers`, `peft`, or `trl`;
- load the base model from the Candidate A config;
- load the adapter from `models/adapters/full_candidate_a_3epoch`;
- run deterministic generation on all 145 validation records;
- use the same prompt format/chat template as training and previous inference;
- save one JSONL row per validation record under `outputs\evaluation\candidate_a_validation\validation_predictions.jsonl`;
- print progress with elapsed time, average seconds per example, estimated remaining time, and ETA;
- write `validation_metrics.json`;
- append or write `logs\candidate_a_validation_quality_audit.md`;
- write `reports\CANDIDATE_A_VALIDATION_QUALITY_REPORT.md`.

Prediction rows should include at least:

- row index,
- stable hash or record id if available,
- domain,
- natural length bucket,
- source file/source line if available,
- generated text,
- parsed JSON if parseable,
- schema status,
- gold assistant JSON,
- deterministic metric flags.

Do not include the full user/source text in Git-safe reports. It is okay for the local prediction JSONL to include limited metadata and generated/gold assistant outputs, but avoid copying full user text unless needed for manual audit.

## Deterministic Metrics

Compute and report:

- validation count, expected `145`;
- validation SHA256;
- split manifest SHA256;
- JSON parse rate;
- exact key order rate: `["main_idea", "key_points"]`;
- `main_idea` string rate;
- `key_points` list rate;
- exactly 4 key points rate;
- all key points strings rate;
- approximate `main_idea` two-sentence compliance;
- approximate each-key-point one-sentence compliance;
- empty-string count;
- output too short/too long flags;
- average `main_idea` word count;
- average key-point word count;
- code fence / markdown leakage count;
- extra text outside JSON count;
- common refusal/meta-response phrases count;
- mojibake/encoding artifact count in predictions;
- mojibake/encoding artifact count in gold assistant targets.

Mojibake scan should look for at least:

```text
Unicode replacement character
CJK-looking mojibake artifacts
Latin-1 mojibake markers
curly-quote mojibake sequences
misdecoded apostrophe/quote sequences
```

Also break metrics down by:

- domain,
- natural length bucket,
- domain x natural length bucket where practical.

## Manual Quality Review

Do a stratified manual review on validation only.

Choose at least 14 examples:

- at least 2 examples from each of the 7 domains if available;
- include short, medium, and long examples;
- include `medlineplus`, `public_service`, `assignment_rubric`, and at least one long academic example.

For each reviewed example, compare source metadata/gold/prediction enough to judge:

- valid JSON shape,
- faithful main idea,
- whether any unsupported facts are present,
- whether major warnings/restrictions/requirements are preserved when relevant,
- whether wording is simple and readable,
- whether the model seems to follow embedded instructions instead of summarizing them,
- whether output contains mojibake or awkward copied artifacts.

Do not paste long source text into the Git-safe report. Use short previews and metadata.

Use these manual labels:

```text
pass
minor_issue
major_issue
uncertain
```

Include a brief reason for each label.

## Decision Guidance

Recommend `proceed_to_final_evaluation` only if:

- JSON parse and schema compliance are very high, ideally near 100%;
- sentence/key-point compliance is strong;
- no broad domain or length bucket fails badly;
- manual review finds no severe faithfulness or instruction-following issues;
- mojibake/encoding artifacts are either absent or clearly inherited from source/gold and limited.

Recommend `consider_candidate_b` if:

- format/schema remains good but summaries are consistently weak, vague, too copied, or overfit;
- validation loss gap appears reflected in poor manual quality;
- specific domains/length buckets fail in a way that might improve with training changes.

Recommend `fix_data_or_eval_before_model_choice` if:

- mojibake or malformed gold targets are common enough to affect model choice;
- evaluation script/reporting is insufficient;
- validation artifacts are not trustworthy.

Do not decide final test results in this worker. The central brain will review and decide.

## Required Commands

Run from WSL inside `clearread-llama-lora`.

Suggested checks:

```bash
python -m py_compile scripts/evaluate_candidate_a_validation.py scripts/run_inference_check.py
python scripts/evaluate_candidate_a_validation.py --config configs/train_llama31_8b_qlora_candidate_a.yaml --adapter-path models/adapters/full_candidate_a_3epoch --data-path data/splits/val.jsonl --output-dir outputs/evaluation/candidate_a_validation
```

If you implement different CLI flags, document the actual commands clearly.

## Git-Safe Repo Outputs

Team repo path:

```text
C:\Users\Aufb\Desktop\fit5120\iteration1\code\fit5120-tp43-newclearread
```

Required branch:

```text
feature/ai-llama-lora-training
```

Mirror only Git-safe files:

```text
ai\scripts\evaluate_candidate_a_validation.py
ai\reports\CANDIDATE_A_VALIDATION_QUALITY_REPORT.md
ai\logs\candidate_a_validation_quality_audit.md
ai\logs\decisions\worker_007_candidate_a_validation_quality_audit.md
```

Do not commit:

- `ai/**/*.jsonl`
- `outputs\evaluation\candidate_a_validation\validation_predictions.jsonl`
- raw validation predictions unless central brain later approves,
- base model files,
- Hugging Face cache,
- Unsloth compiled cache,
- adapter `.safetensors`,
- checkpoints,
- optimizer states,
- `.pt`, `.pth`, `.bin`.

Before committing, verify:

```powershell
git ls-files 'ai/**/*.jsonl'
git ls-files 'ai/**/*.safetensors' 'ai/**/*.pt' 'ai/**/*.pth' 'ai/**/*.bin'
```

Both should return nothing.

Recommended primary commit message:

```text
feat(ai): add candidate a validation audit
```

Use a follow-up docs/log commit if needed so the worker log records the primary commit/push result.

Push to:

```text
origin/feature/ai-llama-lora-training
```

## Memory-Safety Rule

Worker 007 must write its memory update as provisional, clearly labeled:

```text
Worker 007 reported, pending central-brain review
```

Do not mark Worker 007 as passed. Only the central-brain chat can do that after independent review.

Do not rewrite, delete, or reinterpret central-brain decisions or approved facts.

## Acceptance Criteria

This worker passes central-brain review if:

- it uses validation only and does not touch the test set;
- it does not run training;
- predictions for all 145 validation records are generated or any failure is clearly explained;
- deterministic metrics are reported;
- encoding/mojibake checks are reported;
- domain/length breakdowns are reported where metadata permits;
- manual stratified validation review is included;
- a clear recommendation is given;
- local prediction JSONL is not committed to Git;
- model/data/cache/checkpoint files are not committed to Git;
- Git-safe scripts/reports/logs are committed and pushed;
- memory update is clearly provisional.

## Final Response Template

Return a concise report with these headings:

```text
Status:
Files created/changed:
Commands run:
Prediction run:
Deterministic metrics:
Manual review:
Encoding/mojibake audit:
Recommendation:
Git commit/push:
Safety checks:
Blockers or deviations:
Next recommended step:
```

Do not include unnecessary long command output. Summarize important results.
