# ClearRead 3B Model Deployment Package

This package documents the production deployment of the ClearRead 3B summary model service.

## Current Service

```text
Base URL: http://34.21.166.229:8010
Main endpoint: POST /v1/clearread/summarize
Authentication: Authorization: Bearer <service API key>
```

The project backend sends already chunked reading text in one request. The wrapper service validates the request, submits valid chunks concurrently to vLLM, and returns an ordered batch response.

## Model

```text
Base model: unsloth/Llama-3.2-3B-Instruct-bnb-4bit
Adapter: phase2_r32_a64_lr1p5e4_epoch_4
Public model name: clearread-llama32-3b-qlora-phase2-r32-a64-lr1p5e4-epoch4
Serving backend: vLLM
GPU: NVIDIA L4
```

## Runtime Limits

```text
MAX_BLOCKS=32
MAX_CHARS_PER_BLOCK=11000
REQUEST_BODY_LIMIT_BYTES=2097152
VLLM_MAX_CONCURRENCY=32
VLLM_MAX_TOKENS=260
VLLM_TIMEOUT_SECONDS=90
VLLM_MAX_MODEL_LEN=8192
```

The response includes a `summary` string and a dynamic `keyPoints` array for each successful text block.

## Contents

```text
configs/       Final service and model configuration records
deploy/        Docker Compose and runtime image templates
docs/          Architecture, API, operations, and handoff documentation
manifests/     Adapter file manifest and deployment hash records
reports/       Final testing and security summaries
scripts/       Selected deployment, verification, and operations scripts
service/       FastAPI wrapper service source
```

## Primary Documents

```text
docs/production_handoff.md
docs/api_contract.md
docs/vm_operations.md
reports/testing_validation_report.md
reports/security_privacy_report.md
```

## Operations

After the VM restarts, the service usually recovers through Docker restart policies. The standard VM check command is:

```bash
~/check-clearread-ai.sh
```

The recovery command is:

```bash
~/restart-clearread-ai.sh
```
