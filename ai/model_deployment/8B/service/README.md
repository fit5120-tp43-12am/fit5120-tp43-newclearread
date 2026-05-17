# ClearRead AI Summary Service

This package is a standalone internal FastAPI service for ClearRead block summaries.
It exposes only the service contract endpoints:

- `GET /health`
- `GET /ready`
- `POST /v1/clearread/summarize`

The ClearRead backend should call this service as an internal API. The service hides
model paths, prompts, runtime details, and wrapper-native output.

## Runtime Modes

Use the mock runtime for tests and contract checks:

```powershell
$env:CLEARREAD_AI_RUNTIME="mock"
$env:CLEARREAD_AI_SERVICE_API_KEY="replace-with-local-dev-key"
python -m uvicorn ai_summary_service.main:app --host 127.0.0.1 --port 8010
```

Use the Transformers/Unsloth runtime for the real local model service:

```bash
export CLEARREAD_AI_RUNTIME=transformers
export CLEARREAD_AI_SERVICE_API_KEY="<secret-from-local-env>"
export CLEARREAD_AI_MODEL_LABEL="clearread-llama31-8b-qlora-candidate-a"
export CLEARREAD_AI_BASE_MODEL_ID="unsloth/Llama-3.1-8B-Instruct-unsloth-bnb-4bit"
export CLEARREAD_AI_WRAPPER_PATH="/path/to/infer_clearread_candidate_a.py"
export CLEARREAD_AI_INFERENCE_CONFIG="/path/to/final_candidate_a_inference.yaml"
export CLEARREAD_AI_ADAPTER_DIR="/path/to/full_candidate_a_3epoch"
export CLEARREAD_AI_MAX_CHARACTERS_PER_TEXT=11000
export CLEARREAD_AI_MAX_REQUEST_BODY_BYTES=2097152
export CLEARREAD_AI_MAX_CONCURRENT_REQUESTS=1
python -m uvicorn ai_summary_service.main:app --host 127.0.0.1 --port 8010
```

Use the vLLM HTTP runtime when a local or private vLLM OpenAI-compatible server
is already running behind the ClearRead service:

```bash
export CLEARREAD_AI_RUNTIME=vllm_http
export CLEARREAD_AI_SERVICE_API_KEY="<secret-from-local-env>"
export CLEARREAD_AI_VLLM_BASE_URL="http://127.0.0.1:8014"
export CLEARREAD_AI_VLLM_API_KEY="<internal-vllm-key>"
export CLEARREAD_AI_VLLM_MODEL="clearread"
export CLEARREAD_AI_VLLM_INTERNAL_CONCURRENCY=8
export CLEARREAD_AI_VLLM_REQUEST_TIMEOUT_SECONDS=30
export CLEARREAD_AI_VLLM_SCHEMA_RETRY_ATTEMPTS=0
export CLEARREAD_AI_MAX_CHARACTERS_PER_TEXT=11000
export CLEARREAD_AI_MAX_REQUEST_BODY_BYTES=2097152
python -m uvicorn ai_summary_service.main:app --host 127.0.0.1 --port 8010
```

Do not put real secrets, private local paths, model weights, adapters, caches, or
generated prediction files in Git. The real runtime dynamically imports the final
wrapper and keeps the model loaded in the long-running service process. The
vLLM runtime keeps vLLM internal and still returns only the ClearRead public
schema.

## Input Limits

The default per-block character cap is `11000`, and the default request body cap
is `2097152` bytes (2 MiB). The character cap is based on the accepted training
input distribution: the largest observed `role=user` text was `8756` characters,
and `11000` gives about 1.2x headroom.

Character limits and token limits are separate deployment concerns. Cloud pressure
testing results for context length, latency, schema success, and GPU memory are
recorded in the deployment reports before a larger cap is treated as
deployment-validated.

## Example Request

```bash
curl -s http://127.0.0.1:8010/v1/clearread/summarize \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $CLEARREAD_AI_SERVICE_API_KEY" \
  -d '{
    "requestId": "local-smoke-001",
    "texts": [
      {
        "id": "block-1",
        "text": "Photosynthesis lets plants use sunlight, water, and carbon dioxide to make glucose and oxygen."
      }
    ],
    "options": {
      "includeDebug": false
    }
  }'
```

Successful public results contain `summary` and exactly four `keyPoints`. Normal
responses omit raw source text and raw model output.
