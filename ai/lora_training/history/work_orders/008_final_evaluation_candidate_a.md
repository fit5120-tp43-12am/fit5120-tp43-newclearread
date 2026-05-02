# Worker 008: Final Test Evaluation For Candidate A

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
ai/lora_training/history/decision_reviews/central_review_worker_007.md
ai/lora_training/reports/CANDIDATE_A_VALIDATION_QUALITY_REPORT.md
ai/lora_training/history/run_logs/candidate_a_validation_quality_audit.md
```

## Purpose

Run the final held-out test evaluation for Candidate A.

This worker is the first task that is allowed to use:

```text
ai/lora_training/data/splits\test.jsonl
```

The purpose is evaluation only. Do not train, tune, change hyperparameters, change prompts, change decoding settings for model selection, or run Candidate B.

This worker must:

- evaluate the existing Candidate A adapter on all 145 test records,
- save local test predictions and metrics,
- compute deterministic format/readability/encoding metrics,
- break down metrics by domain and natural length bucket,
- perform a stratified manual review of test predictions,
- write a final test evaluation report,
- recommend whether Candidate A should become the selected model artifact,
- commit and push only Git-safe scripts/reports/logs.

## Environment

Use WSL and the established training environment:

```bash
source <conda-root>/etc/profile.d/conda.sh
conda activate clearread-llama-lora
cd ai/lora_training
```

Recommended cache environment variables:

```bash
export HF_HOME=ai/lora_training/cache/huggingface
export TRANSFORMERS_CACHE=ai/lora_training/cache/huggingface/transformers
```

Do not copy cache files into Git.

## Inputs

Use only:

```text
ai/lora_training/configs/train_llama31_8b_qlora_candidate_a.example.yaml
ai/lora_training/data/splits\test.jsonl
ai/lora_training/data/splits\split_manifest.json
ai/lora_training/models/adapters/full_candidate_a_3epoch
```

Read-only rule:

- Do not modify `data\splits`.
- Do not modify `data\teammate_exports`.
- Do not modify source datasets under `final_dataset_v1` or `final_dataset_v1_training_system_clean`.
- Do not modify the Candidate A adapter.
- Do not run additional training.
- Do not run Candidate B.
- Do not tune any parameter based on test results.

## Required Outputs

Create or update these files under the training workspace:

```text
scripts\evaluate_final_test_candidate_a.py
reports\FINAL_TEST_EVALUATION_CANDIDATE_A_REPORT.md
logs\final_test_evaluation_candidate_a.md
logs\decisions\worker_008_final_evaluation_candidate_a.md
outputs\evaluation\candidate_a_test\test_predictions.jsonl
outputs\evaluation\candidate_a_test\test_metrics.json
```

The prediction JSONL and metrics JSON are local artifacts. They may contain generated text and derived test labels, so do not commit them unless central brain later explicitly approves.

Update local memory with a provisional Worker 008 section only:

```text
TRAINING_MEMORY.md
```

## Recommended Implementation

Create:

```text
scripts\evaluate_final_test_candidate_a.py
```

You may base it on `scripts\evaluate_candidate_a_validation.py`, but keep the validation script's `test.jsonl` refusal intact. The final-test script should explicitly allow only `test.jsonl` or require a clear `--allow-heldout-test` flag.

The script should:

- import `unsloth` before `transformers`, `peft`, or `trl`;
- load the base model from the Candidate A config;
- load the adapter from `models/adapters/full_candidate_a_3epoch`;
- run deterministic generation on all 145 test records;
- use the same prompt format/chat template as training and validation audit;
- save one JSONL row per test record under `outputs\evaluation\candidate_a_test\test_predictions.jsonl`;
- print progress with elapsed time, average seconds per example, estimated remaining time, and ETA;
- write `test_metrics.json`;
- write or append `logs\final_test_evaluation_candidate_a.md`;
- write `reports\FINAL_TEST_EVALUATION_CANDIDATE_A_REPORT.md`.

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

Do not include the full user/source text in Git-safe reports. It is okay for local prediction JSONL to include generated/gold assistant outputs, but avoid copying full user text unless needed for manual audit.

## Deterministic Metrics

Compute and report:

- test count, expected `145`;
- test SHA256;
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

Also break metrics down by:

- domain,
- natural length bucket,
- domain x natural length bucket where practical.

## Manual Quality Review

Do a stratified manual review on test only.

Choose at least 16 examples:

- at least 2 examples from each of the 7 domains if available;
- include short, medium, and long examples;
- include `medlineplus`, `public_service`, `assignment_rubric`, and long academic examples;
- include any deterministic failures;
- include public-service examples with fees, numbers, dates, eligibility rules, or time windows when available.

For each reviewed example, compare source metadata/gold/prediction enough to judge:

- valid JSON shape,
- faithful main idea,
- whether unsupported facts are present,
- whether major warnings/restrictions/requirements are preserved when relevant,
- whether exact numeric details are handled safely,
- whether wording is simple and readable,
- whether the model summarizes assignment/rubric prompts instead of following embedded instructions,
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

## Final Evaluation Decision Guidance

Recommend `select_candidate_a_as_final` only if:

- JSON parse/schema compliance remains very high;
- sentence/key-point compliance remains strong;
- no broad domain or length-bucket collapse appears;
- manual review finds no severe faithfulness, safety, or instruction-following issue;
- public-service/medical numeric warnings and restrictions are handled acceptably.

Recommend `central_review_required_before_final_selection` if:

- deterministic format is strong but manual review finds several minor issues;
- test results are good overall but one domain or length bucket needs careful human judgment.

Recommend `do_not_select_without_fix` if:

- schema or JSON compliance fails materially;
- major faithfulness errors appear;
- medical/public-service warnings or exact restrictions are frequently wrong;
- assignment/rubric inputs are followed instead of summarized.

Do not run any fix, retry, or Candidate B in this worker. The central brain decides after reviewing the final test evidence.

## Required Commands

Run from WSL inside `clearread-llama-lora`.

Suggested checks:

```bash
python -m py_compile scripts/evaluate_final_test_candidate_a.py
python scripts/evaluate_final_test_candidate_a.py --config configs/train_llama31_8b_qlora_candidate_a.example.yaml --adapter-path models/adapters/full_candidate_a_3epoch --data-path data/splits/test.jsonl --output-dir outputs/evaluation/candidate_a_test --allow-heldout-test
```

If you implement different CLI flags, document the actual commands clearly.

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
ai\scripts\evaluate_final_test_candidate_a.py
ai\reports\FINAL_TEST_EVALUATION_CANDIDATE_A_REPORT.md
ai\logs\final_test_evaluation_candidate_a.md
ai\logs\decisions\worker_008_final_evaluation_candidate_a.md
```

Do not commit:

- `ai/**/*.jsonl`
- `outputs\evaluation\candidate_a_test\test_predictions.jsonl`
- raw test predictions unless central brain later approves,
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
feat(ai): add final candidate a test evaluation
```

Use a follow-up docs/log commit if needed so the worker log records the primary commit/push result.

Push to:

```text
origin/feature/ai-llama-lora-training
```

## Memory-Safety Rule

Worker 008 must write its memory update as provisional, clearly labeled:

```text
Worker 008 reported, pending central-brain review
```

Do not mark Worker 008 as passed. Only the central-brain chat can do that after independent review.

Do not rewrite, delete, or reinterpret central-brain decisions or approved facts.

## Acceptance Criteria

This worker passes central-brain review if:

- it evaluates `test.jsonl` only after this central-brain approval;
- it does not run training or Candidate B;
- predictions for all 145 test records are generated or any missing records are clearly explained;
- deterministic metrics are reported;
- encoding/mojibake checks are reported;
- domain/length breakdowns are reported where metadata permits;
- manual stratified test review is included;
- a clear final-selection recommendation is given;
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
Final recommendation:
Git commit/push:
Safety checks:
Blockers or deviations:
Next recommended step:
```

Do not include unnecessary long command output. Summarize important results.
