# Local Inference Runbook

Last updated: 2026-04-28

## Final Artifact

The selected final raw model artifact for this training cycle is Candidate A: a LoRA adapter trained for ClearRead summarization on top of Llama 3.1 8B Instruct.

- Base model: `unsloth/Llama-3.1-8B-Instruct-unsloth-bnb-4bit`
- Adapter path: `C:\Users\Aufb\Desktop\fit5120\iteration1\training\models\adapters\full_candidate_a_3epoch`
- Inference config: `configs/final_candidate_a_inference.yaml`
- Local metadata: `models/final/clearread_llama31_8b_qlora_candidate_a`

The adapter files stay local. The Git-safe repo copy contains only the wrapper, config, documentation, report, and decision log.

## Environment

Run inference from WSL with the established training environment:

```bash
source /home/aufb/miniconda3/etc/profile.d/conda.sh
conda activate clearread-llama-lora
cd /mnt/c/Users/Aufb/Desktop/fit5120/iteration1/training
```

## Wrapper Commands

Compile check:

```bash
python -m py_compile scripts/infer_clearread_candidate_a.py
```

Dry run without loading the model:

```bash
python scripts/infer_clearread_candidate_a.py --config configs/final_candidate_a_inference.yaml --dry-run
```

Single text input:

```bash
python scripts/infer_clearread_candidate_a.py --config configs/final_candidate_a_inference.yaml --text "Paste source text here."
```

File input:

```bash
python scripts/infer_clearread_candidate_a.py --config configs/final_candidate_a_inference.yaml --input-file path/to/source.txt
```

Stdin input:

```bash
Get-Content source.txt | wsl bash -lc 'source /home/aufb/miniconda3/etc/profile.d/conda.sh && conda activate clearread-llama-lora && cd /mnt/c/Users/Aufb/Desktop/fit5120/iteration1/training && python scripts/infer_clearread_candidate_a.py --config configs/final_candidate_a_inference.yaml'
```

Optional wrapper smoke check using non-test data only:

```bash
python scripts/infer_clearread_candidate_a.py --config configs/final_candidate_a_inference.yaml --input-jsonl data/splits/smoke_test_10.jsonl --num-examples 1 --debug
```

The smoke command is only a wrapper sanity check. It is not model selection and must not use `data/splits/test.jsonl`.

## Expected Output

Default successful output is exactly one JSON object:

```json
{"main_idea":"...","key_points":["...","...","...","..."]}
```

With `--debug`, the wrapper prints raw model output, the final guarded output, `status`, `schema_guard_action`, and any schema errors.

The wrapper suppresses Unsloth/Transformers loading logs by default so stdout stays machine-readable. Use `--verbose-runtime` only when diagnosing local model-loading issues.

## Schema Guard

The raw held-out test result was strong but not perfect: JSON parsed for `145/145` rows, while exact schema passed for `144/145`. Row 87 produced parseable JSON with seven key points instead of exactly four.

The wrapper therefore validates every model response before returning it:

- Exact key order must be `main_idea`, then `key_points`.
- `main_idea` must be a string.
- `key_points` must be a list of strings.
- Exactly four key points are required for final user-facing output.
- If JSON is parseable and has more than four key points, the wrapper returns the first four generated key points and records `schema_guard_action: truncated_key_points` in debug output.
- If JSON is not parseable, has fewer than four key points, has wrong keys, or has wrong value types, the wrapper returns a machine-readable error object instead of silently returning invalid output.

This schema guard is a deployment safety layer. It does not change the held-out test score and must not be treated as a new model-training result.

## Why Candidate B Was Skipped

Candidate A passed validation audit well enough to proceed, and the final held-out test found no broad domain, length, safety, instruction-following, refusal, markdown, extra-text, or encoding collapse. Candidate B was skipped because training it after seeing the held-out test schema miss would risk contaminating the final evaluation.

## Git Policy

Committed to Git:

- `ai/configs/final_candidate_a_inference.yaml`
- `ai/scripts/infer_clearread_candidate_a.py`
- `ai/docs/LOCAL_INFERENCE_RUNBOOK.md`
- `ai/reports/FINAL_MODEL_SELECTION_REPORT.md`
- `ai/logs/decisions/worker_009_package_artifact_and_deployment_notes.md`

Not committed:

- split JSONL files,
- validation/test prediction JSONL,
- adapter `.safetensors`,
- base model weights,
- Hugging Face or Unsloth caches,
- checkpoints,
- optimizer states,
- `.pt`, `.pth`, or `.bin` files.
