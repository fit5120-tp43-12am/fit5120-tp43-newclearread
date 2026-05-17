# Local Inference Runbook

This runbook explains how the selected Candidate A adapter was intended to be used locally. Model weights and adapters are not included in this package.

## Required Local Artifacts

To run inference locally, provide these outside the repository:

- the selected Candidate A LoRA adapter directory
- the base model cache or permission to download the base model
- the local split files if running smoke or validation checks

Expected package-relative paths in the example config:

```text
<external-local-raw-8b-training-workspace-not-in-git>/models/adapters/full_candidate_a_3epoch
<external-local-raw-8b-training-workspace-not-in-git>/data/splits/smoke_test_10.jsonl
<external-local-raw-8b-training-workspace-not-in-git>/data/splits/val.jsonl
<external-local-raw-8b-training-workspace-not-in-git>/data/splits/split_manifest.json
```

These paths are expected to be provided locally when running inference.

## Environment

Use the validated environment described by:

- `configs/clearread-llama-lora_environment.example.yml`
- `configs/clearread-llama-lora_pip_freeze.txt`
- `reports/WSL_ENVIRONMENT_REPORT.md`

Run commands from the package root:

```bash
cd ai/lora_training
```

## Single-Input Inference

```bash
python scripts/infer_clearread_candidate_a.py \
  --config configs/final_candidate_a_inference.example.yaml \
  --text "Photosynthesis lets plants use sunlight, water, and carbon dioxide to make glucose and oxygen."
```

The expected successful shape is:

```json
{"main_idea":"...","key_points":["...","...","...","..."]}
```

## Smoke Check

```bash
python scripts/run_inference_check.py \
  --config configs/final_candidate_a_inference.example.yaml \
  --adapter-path <external-local-raw-8b-training-workspace-not-in-git>/models/adapters/full_candidate_a_3epoch \
  --data-path <external-local-raw-8b-training-workspace-not-in-git>/data/splits/smoke_test_10.jsonl \
  --num-examples 3
```

## Schema Guard

The inference wrapper enforces the deployment contract:

- output must be parseable JSON
- keys must be `main_idea` and `key_points`
- `main_idea` must be a string
- `key_points` must be a list of strings
- exactly four key points are required

Guard policy:

| Case | Action |
| --- | --- |
| More than four key points | Keep the first four and mark `schema_guard_action: truncated_key_points`. |
| Fewer than four key points | Return a machine-readable error object. |
| JSON parse failure | Return a machine-readable error object. |
| Wrong keys or value types | Return a machine-readable error object. |

The guard is a deployment safety layer. It does not change the final held-out test result.
