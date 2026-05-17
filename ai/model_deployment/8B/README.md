# Clearead 8B Model Deployment Package

This folder collects the deployment work for the Llama 3.1 8B Candidate A summary model. It documents the path from selected LoRA adapter to API service, including contract tests, local runtime checks, vLLM serving experiments, cloud pressure testing, and integration notes for the main Clearead backend.

## What This Package Contains

| Folder | Purpose |
| --- | --- |
| `service/` | Standalone FastAPI AI summary service, runtime adapters, requirements, and API tests. |
| `benchmarks/` | Local sizing, vLLM SLA, Google Cloud pressure, and L4 diagnosis scripts. |
| `docs/` | API contract, deployment process, backend integration guide, and restart runbook. |
| `reports/` | Testing, security, serving research, cloud pressure, and QA summaries. |
| `integration/` | Notes connecting the deployment service back to the main backend. |
| `manifests/` | Machine-readable included-file and external-artifact manifests. |

## Service Route

```text
Base model: unsloth/Llama-3.1-8B-Instruct-unsloth-bnb-4bit
Fine-tuning method: SFT + QLoRA
Selected adapter: full_candidate_a_3epoch
Public service name: clearread-ai-summary
Main endpoint: POST /v1/clearread/summarize
```

The wrapper exposes only the ClearRead contract and keeps raw vLLM routes, prompts, local paths, model artifacts, and raw model output behind the service boundary.

## Deployment Findings

The Google Cloud L4 testing route found the following MVP operating envelope:

| Setting | Result |
| --- | --- |
| Stable tested cap | 28 representative text blocks per request |
| Conservative product cap | 24 representative text blocks per request |
| 30-second target pressure point | 32 representative text blocks exceeded the stable target in repeated tests |
| Max characters per text block | 11,000 |
| Request body limit | 2 MiB |

These results are preserved because they explain the baseline deployment constraints used when evaluating the later 3B route.

## Local Contract Check

Mock mode validates the API contract without model artifacts:

```powershell
cd ai/model_deployment/8B/service
$env:CLEARREAD_AI_RUNTIME="mock"
$env:CLEARREAD_AI_SERVICE_API_KEY="replace-with-local-dev-key"
python -m uvicorn ai_summary_service.main:app --host 127.0.0.1 --port 8010
```

Then call:

```bash
curl -s http://127.0.0.1:8010/health
curl -s http://127.0.0.1:8010/ready
```

## Key Documents

- [docs/end_to_end_deployment_process.md](docs/end_to_end_deployment_process.md)
- [docs/api_contract.md](docs/api_contract.md)
- [reports/model_serving_and_benchmark_summary.md](reports/model_serving_and_benchmark_summary.md)
- [reports/gcp_l4_pressure_test_report.md](reports/gcp_l4_pressure_test_report.md)
- [reports/security_and_privacy_summary.md](reports/security_and_privacy_summary.md)

## Verification Commands

From the repository root:

```powershell
python -m compileall -q ai\model_deployment\8B\service\ai_summary_service ai\model_deployment\8B\service\tests ai\model_deployment\8B\benchmarks
cd ai\model_deployment\8B\service
python -m pytest tests\ai_summary_service
```

Large model artifacts, adapter files, raw benchmark outputs, logs, temporary VM details, API keys, and local machine paths are represented through manifests and reports rather than stored in Git.
