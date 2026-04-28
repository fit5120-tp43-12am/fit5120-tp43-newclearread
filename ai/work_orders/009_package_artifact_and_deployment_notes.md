# Worker 009: Package Final Artifact And Local Deployment Notes

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
C:\Users\Aufb\Desktop\fit5120\iteration1\training\logs\decisions\central_review_worker_008.md
C:\Users\Aufb\Desktop\fit5120\iteration1\training\reports\FINAL_TEST_EVALUATION_CANDIDATE_A_REPORT.md
C:\Users\Aufb\Desktop\fit5120\iteration1\training\logs\final_test_evaluation_candidate_a.md
```

## Purpose

Package Candidate A as the selected final raw adapter for this training cycle and prepare local deployment/run instructions.

This worker must not train, tune, run Candidate B, or rerun final test evaluation for model selection.

The key deployment requirement is to document and implement a schema guard because raw held-out test compliance was `144/145`, with one output producing 7 key points instead of exactly 4.

## Final Selected Raw Artifact

Selected adapter directory:

```text
C:\Users\Aufb\Desktop\fit5120\iteration1\training\models\adapters\full_candidate_a_3epoch
```

Base model:

```text
unsloth/Llama-3.1-8B-Instruct-unsloth-bnb-4bit
```

Config:

```text
C:\Users\Aufb\Desktop\fit5120\iteration1\training\configs\train_llama31_8b_qlora_candidate_a.yaml
```

Final test report:

```text
C:\Users\Aufb\Desktop\fit5120\iteration1\training\reports\FINAL_TEST_EVALUATION_CANDIDATE_A_REPORT.md
```

## Environment

Use WSL and the established training environment for any Python checks:

```bash
source /home/aufb/miniconda3/etc/profile.d/conda.sh
conda activate clearread-llama-lora
cd /mnt/c/Users/Aufb/Desktop/fit5120/iteration1/training
```

Do not copy cache files into Git.

## Scope Rules

Allowed:

- create final artifact metadata,
- create a local inference script or wrapper,
- create deployment/runbook documentation,
- compute hashes for local adapter files,
- run compile/dry-run checks,
- optionally run one or two non-test smoke/validation inference sanity checks only to prove the wrapper loads and validates output.

Not allowed:

- training,
- Candidate B,
- hyperparameter changes,
- prompt changes for model selection,
- final test reruns for model selection,
- modifying split/source datasets,
- modifying the selected adapter files,
- committing adapter/model/checkpoint/cache files.

If you run any functional inference check, use `smoke_test_10.jsonl` or `val.jsonl`, not `test.jsonl`, and state clearly that it is a wrapper smoke check, not model selection.

## Required Outputs

Create or update these files under the training workspace:

```text
configs\final_candidate_a_inference.yaml
scripts\infer_clearread_candidate_a.py
docs\LOCAL_INFERENCE_RUNBOOK.md
reports\FINAL_MODEL_SELECTION_REPORT.md
logs\decisions\worker_009_package_artifact_and_deployment_notes.md
```

Create a local artifact metadata directory:

```text
models\final\clearread_llama31_8b_qlora_candidate_a
```

Inside it, create:

```text
FINAL_ARTIFACT_MANIFEST.json
README.md
```

This local `models\final` metadata directory may point to the selected adapter directory instead of copying the adapter. Do not duplicate or move the `.safetensors` unless there is a clear reason. Do not commit `models\final` to normal Git unless it contains only tiny metadata and the repo ignore rules allow it safely. Prefer mirroring Git-safe summaries under `ai\reports` and `ai\docs`.

Update local memory with a provisional Worker 009 section only:

```text
TRAINING_MEMORY.md
```

## Final Artifact Manifest Requirements

`FINAL_ARTIFACT_MANIFEST.json` should include:

- artifact name,
- selection status,
- selected adapter path,
- base model id,
- config path,
- train/validation/test split hashes,
- split manifest hash,
- training summary:
  - 3 epochs,
  - 438 optimizer steps,
  - final train loss,
  - validation loss,
  - no OOM,
- validation audit summary,
- final test summary:
  - JSON parse `145/145`,
  - schema pass `144/145`,
  - row 87 `key_points_len_7` caveat,
  - manual review summary,
- local adapter file list,
- SHA256 hashes for small metadata files,
- SHA256 hash for `adapter_model.safetensors` if practical,
- explicit Git policy saying adapter/model/cache/checkpoint files are not committed.

## Inference Wrapper Requirements

Create:

```text
scripts\infer_clearread_candidate_a.py
```

It should:

- import `unsloth` before `transformers`, `peft`, or related libraries;
- load the selected base model and adapter;
- accept input text from either:
  - `--text`,
  - `--input-file`, or
  - stdin;
- use the same system prompt and output contract as the training data;
- generate deterministically by default;
- parse the raw model output as JSON;
- validate exact keys and key order;
- validate `main_idea` is a string;
- validate `key_points` is a list of strings;
- enforce exactly four key points before returning the final user-facing output.

Schema guard policy:

- If JSON is parseable and `key_points` has more than 4 items, produce a guarded output with only the first 4 high-level key points and record `schema_guard_action: truncated_key_points`.
- If JSON is parseable and `key_points` has fewer than 4 items, return an error object or retry once with a strict formatting instruction; document the behavior.
- If JSON is not parseable, return an error object or retry once; document the behavior.
- Do not silently hide guard actions. Include a machine-readable status field in logs or optional debug output.
- The default user-facing mode should return only the final JSON object if valid after guard. A `--debug` option may print raw output and guard metadata.

This wrapper is a deployment safety layer, not a new model-training result. Do not use it to alter the final held-out test score.

## Runbook Requirements

Create:

```text
docs\LOCAL_INFERENCE_RUNBOOK.md
```

It should explain:

- what the final model artifact is in plain language,
- base model and adapter path,
- environment activation commands,
- how to run the inference wrapper,
- example command using `--text`,
- expected output JSON,
- schema guard behavior,
- known caveat from final test row 87,
- why Candidate B was skipped,
- what is and is not committed to Git.

## Final Selection Report

Create:

```text
reports\FINAL_MODEL_SELECTION_REPORT.md
```

It should summarize:

- selected model: Candidate A,
- why Candidate A was selected,
- validation metrics,
- final test metrics,
- row 87 schema miss and deployment guard decision,
- manual review findings,
- final artifact location,
- remaining risks,
- next integration/deployment steps.

## Required Verification

Run at least:

```bash
python -m py_compile scripts/infer_clearread_candidate_a.py
```

If feasible, run a lightweight wrapper dry-run that does not load the model:

```bash
python scripts/infer_clearread_candidate_a.py --config configs/final_candidate_a_inference.yaml --dry-run
```

If you run a live wrapper inference check, use smoke or validation only:

```bash
python scripts/infer_clearread_candidate_a.py --config configs/final_candidate_a_inference.yaml --input-jsonl data/splits/smoke_test_10.jsonl --num-examples 1 --debug
```

The exact CLI may differ if you design it differently; document the actual commands.

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
ai\configs\final_candidate_a_inference.yaml
ai\scripts\infer_clearread_candidate_a.py
ai\docs\LOCAL_INFERENCE_RUNBOOK.md
ai\reports\FINAL_MODEL_SELECTION_REPORT.md
ai\logs\decisions\worker_009_package_artifact_and_deployment_notes.md
```

Do not commit:

- `ai/**/*.jsonl`,
- test/validation prediction JSONL,
- adapter `.safetensors`,
- base model files,
- Hugging Face cache,
- Unsloth compiled cache,
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
docs(ai): package final candidate a artifact
```

Use a follow-up docs/log commit if needed so the worker log records the primary commit/push result.

Push to:

```text
origin/feature/ai-llama-lora-training
```

## Memory-Safety Rule

Worker 009 must write its memory update as provisional, clearly labeled:

```text
Worker 009 reported, pending central-brain review
```

Do not mark Worker 009 as passed. Only the central-brain chat can do that after independent review.

Do not rewrite, delete, or reinterpret central-brain decisions or approved facts.

## Acceptance Criteria

This worker passes central-brain review if:

- final selected artifact path is documented;
- final artifact manifest exists locally;
- inference wrapper exists and compiles;
- schema guard behavior is documented and implemented;
- runbook and final model selection report exist;
- no training, tuning, Candidate B, or test-set model-selection rerun occurred;
- adapter/model/cache/checkpoint files are not committed to Git;
- Git-safe scripts/configs/docs/reports/logs are committed and pushed;
- memory update is clearly provisional.

## Final Response Template

Return a concise report with these headings:

```text
Status:
Files created/changed:
Commands run:
Final artifact:
Inference wrapper:
Schema guard:
Runbook/report:
Git commit/push:
Safety checks:
Blockers or deviations:
Next recommended step:
```

Do not include unnecessary long command output. Summarize important results.
