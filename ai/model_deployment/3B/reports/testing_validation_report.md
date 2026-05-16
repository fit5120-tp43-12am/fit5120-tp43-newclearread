# Testing and Validation Report

Date: 2026-05-16

## Summary

The ClearRead 3B model service passed deployment validation, runtime checks, public API checks, batch processing checks, and post-reboot recovery checks.

## Environment

```text
GCP project: clearead-junwei
Instance: instance-20260516-075135
Zone: asia-southeast1-c
GPU: NVIDIA L4
Model: clearread-llama32-3b-qlora-phase2-r32-a64-lr1p5e4-epoch4
Backend: vLLM
```

## Completed Checks

| Area | Result | Evidence |
|---|---:|---|
| VM baseline | Pass | Ubuntu 22.04, 100 GB disk, NVIDIA L4 available |
| Docker GPU runtime | Pass | Docker with NVIDIA runtime returned `nvidia-smi` |
| Adapter hash verification | Pass | Uploaded adapter files matched expected SHA-256 hashes |
| vLLM startup | Pass | Base model and LoRA adapter loaded successfully |
| Health/readiness | Pass | `/health` returned `ok`; `/ready` returned `ready` |
| One-block smoke | Pass | Summary and key points returned |
| 4-block batch | Pass | 4/4 blocks returned `ok`; elapsed time about 2.818 seconds |
| 8-block batch | Pass | 8/8 blocks returned `ok`; elapsed time about 2.891 seconds |
| Real test split, 16 blocks | Pass | 16/16 blocks returned `ok`; total input 87,191 characters; elapsed time about 11.897 seconds |
| Post-reboot recovery | Pass | vLLM reloaded the LoRA adapter; 2/2 smoke blocks returned `ok`; elapsed time about 2.940 seconds |

## Project Environment Comparison

A teammate also tested the 8B and 3B services through the project environment using the same input document. The document contained about 48,000 characters and was processed as 16 text blocks. Both services used one NVIDIA L4 GPU.

| Model service | VM shape | GPU | Total seconds | Model seconds | Blocks | Fallback blocks |
|---|---|---|---:|---:|---:|---:|
| 8B service | `g2-standard-8`, 8 vCPU, 32 GB RAM | 1 x NVIDIA L4 | 23.19 | 20.72 | 16 | 0 |
| 3B service | `g2-standard-4`, 4 vCPU, 16 GB RAM | 1 x NVIDIA L4 | 12.44 | 8.37 | 16 | 0 |

Measured on the model-processing portion, the 3B service completed the request about 2.47 times faster than the 8B service. Measured on the full project processing time, the 3B service completed the request about 1.86 times faster. The comparison is notable because the 3B service used the smaller CPU and memory configuration while running on the same GPU class.

## Batch Processing Observation

The wrapper creates one asynchronous task per valid text block and uses a concurrency limit of 32. A 20-block request is therefore processed concurrently by the wrapper and scheduled by vLLM on the GPU.

## Runtime Limits Confirmed

```text
MAX_BLOCKS=32
MAX_CHARS_PER_BLOCK=11000
REQUEST_BODY_LIMIT_BYTES=2097152
VLLM_MAX_CONCURRENCY=32
VLLM_MAX_TOKENS=260
VLLM_TIMEOUT_SECONDS=90
VLLM_MAX_MODEL_LEN=8192
```

## Result

The service is ready for backend integration and controlled production demonstration.
