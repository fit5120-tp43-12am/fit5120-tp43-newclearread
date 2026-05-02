# Package Contents

## Included

| Path | Reason |
|---|---|
| `service/ai_summary_service/` | Deployable FastAPI service code. |
| `service/tests/ai_summary_service/` | Contract, validation, vLLM-wrapper, and privacy tests. |
| `service/requirements.txt` | API service dependencies. |
| `benchmarks/machine_sizing/` | Script for local persistent Transformers service sizing. |
| `benchmarks/vllm_30s_sla/` | Scripts for local vLLM latency and wrapper SLA testing. |
| `benchmarks/gcp_pressure/` | Script for cloud pressure testing through the ClearRead wrapper. |
| `benchmarks/gcp_l4_diagnosis/` | Scripts for L4 diagnosis and payload construction. |
| `docs/` | Contract, process, integration, and restart documentation. |
| `reports/` | Clean summaries of test results, security decisions, and deployment findings. |
| `integration/` | Backend connection notes. |
| `manifests/` | Included-file and external-artifact manifests. |

## Excluded

| Excluded material | Reason |
|---|---|
| LoRA adapter zip and model weights | Too large for this repository and should be distributed as external artifacts. |
| Raw benchmark result JSON/CSV files | Some records contain local timing, endpoint, or dataset metadata. The important findings are summarised in reports. |
| Raw service logs | Logs can contain runtime environment details. |
| Temporary VM names, public endpoint IPs, and usernames | Not needed for review and should not be published. |
| API keys and local environment files | Secrets must be configured through environment variables or secret managers. |
| Internal planning and work-order records | Replaced by the cleaner process and validation summaries in this package. |
