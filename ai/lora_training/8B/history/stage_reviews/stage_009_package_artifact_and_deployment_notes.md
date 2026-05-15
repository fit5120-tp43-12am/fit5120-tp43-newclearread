# Stage 009 Package Artifact And Deployment Notes

Date/time: 2026-04-28

Status: completed and pushed; pending model-selection review.

## Scope

Stage 009 packaged Candidate A as the selected final raw adapter and prepared local inference/deployment notes. No training, tuning, Candidate B work, held-out test rerun, source split modification, or adapter modification was performed.

## Selected Artifact

- Adapter: `ai/lora_training/models/adapters/full_candidate_a_3epoch`
- Base model: `unsloth/Llama-3.1-8B-Instruct-unsloth-bnb-4bit`
- Training config: `configs\train_llama31_8b_qlora_candidate_a.yaml`
- Inference config: `configs\final_candidate_a_inference.yaml`
- Local metadata: `models\final\clearread_llama31_8b_qlora_candidate_a`

## Files Created

- `configs\final_candidate_a_inference.yaml`
- `scripts\infer_clearread_candidate_a.py`
- `docs\LOCAL_INFERENCE_RUNBOOK.md`
- `reports\FINAL_MODEL_SELECTION_REPORT.md`
- `models\final\clearread_llama31_8b_qlora_candidate_a\FINAL_ARTIFACT_MANIFEST.json`
- `models\final\clearread_llama31_8b_qlora_candidate_a\README.md`
- `logs\decisions\stage_009_package_artifact_and_deployment_notes.md`

## Artifact Hashes

- train split SHA256: `b99caa6b06963a05ca7e32da3c3be3237c9ea6b128ce1ccf329b78d2d56929fb`
- validation split SHA256: `a7cf5277eda97ef1868376caa79343b040ba6920602bc607dc145a2039d2d4be`
- test split SHA256: `6613390f654c55a69c5ddb90234f81005fc3baca8e57651206f1ef024c939b7f`
- split manifest SHA256: `42bfe9974c31e74b98b45d45daa792f8582d517541e153439b510e9a9b307f19`
- adapter model SHA256: `ef220721c78e72f41c3b14749f25a09ef39f6aaf351266b276cee41ec724cf92`

## Schema Guard

The inference wrapper validates exact JSON shape and key order before returning output. It returns only the final JSON object by default when output is valid after guard.

- Parseable JSON with more than four key points is truncated to the first four generated key points and records `schema_guard_action: truncated_key_points` in debug output.
- Parse errors, fewer than four key points, wrong keys, wrong key order, and wrong value types return a machine-readable error object.
- This guard is a deployment safety layer and does not alter the final held-out test score.

## Verification

Passed in WSL env `clearread-llama-lora` from `ai/lora_training`:

```bash
python -m py_compile scripts/infer_clearread_candidate_a.py
python scripts/infer_clearread_candidate_a.py --config configs/final_candidate_a_inference.example.yaml --dry-run
python -m json.tool models/final/clearread_llama31_8b_qlora_candidate_a/FINAL_ARTIFACT_MANIFEST.json
python scripts/infer_clearread_candidate_a.py --config configs/final_candidate_a_inference.example.yaml --input-jsonl data/splits/smoke_test_10.jsonl --num-examples 1 --debug
```

Dry-run result:

- `status: dry_run_ok`
- adapter path exists: `true`
- schema guard fixtures: valid -> `none`; too many key points -> `truncated_key_points`; too few key points -> `return_error_object`; invalid JSON -> `return_error_object`

Smoke wrapper check:

- Data: `data/splits/smoke_test_10.jsonl`
- Examples: `1`
- Status: `ok`
- Schema guard action: `none`
- Note: this was a wrapper smoke check only, not model selection, and did not use `test.jsonl`.

## Git

package-ready files mirrored to `<team-repo-root>`:

- `ai\configs\final_candidate_a_inference.yaml`
- `ai\scripts\infer_clearread_candidate_a.py`
- `ai\docs\LOCAL_INFERENCE_RUNBOOK.md`
- `ai\reports\FINAL_MODEL_SELECTION_REPORT.md`
- `ai\logs\decisions\stage_009_package_artifact_and_deployment_notes.md`

Pre-commit safety checks:

```powershell
git ls-files 'ai/**/*.jsonl'
git ls-files 'ai/**/*.safetensors' 'ai/**/*.pt' 'ai/**/*.pth' 'ai/**/*.bin'
```

Both returned nothing.

Primary commit and push result:

- Commit: `3418651dc914cec4182dfa8d44a5341fba2e8854`
- Message: `docs(ai): package final candidate a artifact`
- Push target: `origin/feature/ai-llama-lora-training`
- Push result: success

Post-push verification:

- Local HEAD equals upstream at `3418651dc914cec4182dfa8d44a5341fba2e8854`.
- Worktree was clean after the primary push.
- `git ls-files 'ai/**/*.jsonl'` returned nothing.
- `git ls-files 'ai/**/*.safetensors' 'ai/**/*.pt' 'ai/**/*.pth' 'ai/**/*.bin'` returned nothing.

This stage log is updated after the primary push and should be committed in a follow-up docs/log commit.

## Recommendation

Submit to model-selection review after verification, artifact storage checks, commit, push, and provisional memory update are complete.
