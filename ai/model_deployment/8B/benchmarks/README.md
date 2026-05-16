# Deployment Benchmarks

This folder contains scripts used to evaluate deployment feasibility and cloud capacity. They are grouped by testing purpose.

| Folder | Purpose |
|---|---|
| `machine_sizing/` | Starts the persistent Transformers service and measures local latency, memory, and response safety. |
| `vllm_30s_sla/` | Measures local vLLM latency and wrapper behaviour for the 30-second target. |
| `gcp_pressure/` | Sends batched requests to a ClearRead wrapper endpoint and records metadata-only pressure results. |
| `gcp_l4_diagnosis/` | Builds payloads and probes wrapper/direct-vLLM behaviour for L4 diagnosis. |

Benchmark scripts do not include model artifacts. Configure external paths through environment variables such as:

```text
CLEARREAD_AI_ARTIFACT_DIR=/opt/clearread-ai/artifacts
CLEARREAD_AI_WRAPPER_PATH=/opt/clearread-ai/artifacts/infer_clearread_candidate_a.py
CLEARREAD_AI_INFERENCE_CONFIG=/opt/clearread-ai/artifacts/final_candidate_a_inference.yaml
CLEARREAD_AI_ADAPTER_DIR=/opt/clearread-ai/artifacts/full_candidate_a_3epoch
CLEARREAD_BENCHMARK_DATASET=data/final_lora_data/outputs/accepted/all_v1.jsonl
```

Pressure-test scripts should be run against a controlled staging or internal endpoint. They record metadata such as latency, counts, statuses, token statistics, and schema validity. They should not save raw private source text or raw model output.
