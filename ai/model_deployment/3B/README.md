# Clearead 3B Model Deployment Package

This package documents the production deployment route for the selected Clearead 3B summary model service, the core model-serving component for structured reading summaries.

## Service Contract

```text
Base URL: http://34.21.166.229:8010
Health: GET /health
Readiness: GET /ready
Summary: POST /v1/clearread/summarize
Authentication: Authorization: Bearer <service API key>
```

The main Clearead backend sends already chunked reading text in one request. The wrapper validates the request, submits valid chunks concurrently to vLLM, applies response guarding, and returns ordered per-block results.

## Selected Model

```text
Base model: unsloth/Llama-3.2-3B-Instruct-bnb-4bit
Adapter: phase2_r32_a64_lr1p5e4_epoch_4
Public model name: clearread-llama32-3b-qlora-phase2-r32-a64-lr1p5e4-epoch4
Serving backend: vLLM
GPU class: NVIDIA L4
```

## Runtime Limits

| Setting | Value |
| --- | ---: |
| `MAX_BLOCKS` | 32 |
| `MAX_CHARS_PER_BLOCK` | 11,000 |
| `REQUEST_BODY_LIMIT_BYTES` | 2,097,152 |
| `VLLM_MAX_CONCURRENCY` | 32 |
| `VLLM_MAX_TOKENS` | 260 |
| `VLLM_TIMEOUT_SECONDS` | 90 |
| `VLLM_MAX_MODEL_LEN` | 8,192 |

## Package Structure

```text
3B/
  configs/       Final service and model configuration records
  deploy/        Docker Compose, Dockerfile, nginx, and environment templates
  docs/          Architecture, API contract, operations, and handoff documents
  manifests/     Adapter manifest and deployment hash records
  reports/       Testing, validation, deployment, security, and privacy reports
  scripts/       Deployment, smoke-test, load-test, and operations scripts
  service/       FastAPI wrapper service source and tests
```

## Primary Documents

- [docs/production_handoff.md](docs/production_handoff.md)
- [docs/api_contract.md](docs/api_contract.md)
- [docs/architecture.md](docs/architecture.md)
- [docs/vm_operations.md](docs/vm_operations.md)
- [reports/testing_validation_report.md](reports/testing_validation_report.md)
- [reports/security_privacy_report.md](reports/security_privacy_report.md)
- [reports/deployment_audit_report.md](reports/deployment_audit_report.md)

## Local Service Checks

From this package:

```powershell
cd service
pip install -r requirements.txt
python -m pytest tests
```

Production-style runtime uses the Docker and vLLM templates under `deploy/`, with secrets supplied through environment files outside Git.

## Operations

Standard VM check command:

```bash
~/check-clearread-ai.sh
```

Standard recovery command:

```bash
~/restart-clearread-ai.sh
```
