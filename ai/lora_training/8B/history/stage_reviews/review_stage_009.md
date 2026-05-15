# Project Review: Stage 009 Artifact Packaging And Deployment Notes

Date/time: 2026-04-28

## Decision

Result: pass.

Stage 009 successfully packaged Candidate A as the selected final raw adapter for this training cycle and created the local inference wrapper, runbook, final selection report, and artifact manifest.

The final selected raw adapter remains:

```text
ai/lora_training/models/adapters/full_candidate_a_3epoch
```

The wrapper schema guard is accepted as the required deployment safety layer for the known held-out row 87 risk. It does not change the final held-out test result.

## Evidence Reviewed

Local files reviewed:

```text
ai/lora_training/configs/final_candidate_a_inference.example.yaml
ai/lora_training/scripts/infer_clearread_candidate_a.py
ai/lora_training/docs/local_inference_runbook.md
ai/lora_training/reports/FINAL_MODEL_SELECTION_REPORT.md
ai/lora_training/models/final\clearread_llama31_8b_qlora_candidate_a\FINAL_ARTIFACT_MANIFEST.json
ai/lora_training/models/final\clearread_llama31_8b_qlora_candidate_a\README.md
ai/lora_training/history/stage_reviews/stage_009_package_artifact_and_deployment_notes.md
```

Key reviewed behavior:

- final inference config points to `unsloth/Llama-3.1-8B-Instruct-unsloth-bnb-4bit`;
- selected adapter path is `models/adapters/full_candidate_a_3epoch`;
- schema guard is enabled;
- successful default wrapper output is only the final JSON object;
- debug mode exposes raw output, guarded output, status, errors, and `schema_guard_action`;
- parseable outputs with more than four key points are truncated to the first four and marked `truncated_key_points`;
- parse errors, too few key points, wrong keys/order, or wrong value types return a machine-readable error object;
- runbook clearly states that smoke/validation checks are not model selection and must not use `test.jsonl`;
- final selection report documents Candidate A selection, row 87 caveat, Candidate B skip rationale, remaining risks, and next integration steps.

## Independent Verification

Independent review reran the wrapper compile, dry-run, and manifest JSON checks in WSL env `clearread-llama-lora`:

```bash
python -m py_compile scripts/infer_clearread_candidate_a.py
python scripts/infer_clearread_candidate_a.py --config configs/final_candidate_a_inference.example.yaml --dry-run
python -m json.tool models/final/clearread_llama31_8b_qlora_candidate_a/FINAL_ARTIFACT_MANIFEST.json
```

Result: pass.

Dry-run confirmed:

```text
status: dry_run_ok
base_model_id: unsloth/Llama-3.1-8B-Instruct-unsloth-bnb-4bit
adapter_path_exists: true
valid fixture: none
too-many-key-points fixture: truncated_key_points
too-few-key-points fixture: return_error_object
invalid-JSON fixture: return_error_object
```

Independent review independently verified split hashes still match the approved values:

```text
train.jsonl: b99caa6b06963a05ca7e32da3c3be3237c9ea6b128ce1ccf329b78d2d56929fb
val.jsonl: a7cf5277eda97ef1868376caa79343b040ba6920602bc607dc145a2039d2d4be
test.jsonl: 6613390f654c55a69c5ddb90234f81005fc3baca8e57651206f1ef024c939b7f
split_manifest.json: 42bfe9974c31e74b98b45d45daa792f8582d517541e153439b510e9a9b307f19
```

Independent review independently verified every manifest-listed local adapter file exists and matches its recorded SHA256, including:

```text
adapter_model.safetensors: ef220721c78e72f41c3b14749f25a09ef39f6aaf351266b276cee41ec724cf92
```

Independent review reran one live wrapper check on non-test smoke data:

```bash
python scripts/infer_clearread_candidate_a.py --config configs/final_candidate_a_inference.example.yaml --input-jsonl data/splits/smoke_test_10.jsonl --num-examples 1 --debug
```

Result:

```text
status: ok
schema_guard_action: none
input_id: smoke_test_10.jsonl:1
```

The live check loaded the selected adapter and returned valid guarded JSON. It did not train, tune, run Candidate B, or use `test.jsonl`.

## Git Verification

Team repo:

```text
<team-repo-root>
```

Independent review verified:

- branch: `feature/ai-llama-lora-training`
- local HEAD: `23c8e1fa0342e63c2656ed473caf6b52068d94ed`
- upstream HEAD: `23c8e1fa0342e63c2656ed473caf6b52068d94ed`
- latest Stage 009 commits:
  - `23c8e1f docs(ai): record stage 009 package result`
  - `3418651 docs(ai): package final candidate a artifact`

artifact storage checks returned no tracked raw data or model binary artifacts:

```text
git ls-files 'ai/**/*.jsonl' -> empty
git ls-files 'ai/**/*.safetensors' 'ai/**/*.pt' 'ai/**/*.pth' 'ai/**/*.bin' -> empty
```

Independent review also inspected the repo-side `ai` tree. The Stage 009 package copy contains only package-ready config/script/docs/report/log files, not adapter weights, split JSONL files, evaluation JSONL files, outputs, checkpoints, or cache artifacts.

## Notes

- The wrapper dry-run imports the Python runtime stack but does not load model weights or the adapter. This is acceptable for the current runbook.
- `--verbose-runtime` controls model-loading and generation verbosity after argument parsing. The initial Unsloth import remains quiet unless `CLEARREAD_VERBOSE_RUNTIME` is set, which is acceptable for keeping stdout machine-readable.
- The local `models\final\clearread_llama31_8b_qlora_candidate_a` directory is metadata only. It points to the selected adapter and does not duplicate `.safetensors`.

## Final State

The training/model-selection/packaging phase is complete.

Final selected model route:

```text
Llama-3.1-8B-Instruct + SFT + QLoRA
```

Base model:

```text
unsloth/Llama-3.1-8B-Instruct-unsloth-bnb-4bit
```

Final local adapter:

```text
ai/lora_training/models/adapters/full_candidate_a_3epoch
```

Final local wrapper:

```text
ai/lora_training/scripts/infer_clearread_candidate_a.py
```

Next work should be an integration or handoff phase, scoped separately. No new stage is required for training unless the user decides to start backend/application integration or a separate deployment task.
