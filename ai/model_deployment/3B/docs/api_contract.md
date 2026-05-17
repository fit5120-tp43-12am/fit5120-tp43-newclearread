# API Contract

Base URL:

```text
http://34.21.166.229:8010
```

## Health

```http
GET /health
```

Expected response:

```json
{
  "status": "ok",
  "service": "clearread-ai-summary"
}
```

## Readiness

```http
GET /ready
```

Expected response after vLLM is loaded:

```json
{
  "status": "ready",
  "service": "clearread-ai-summary",
  "model": "clearread-llama32-3b-qlora-phase2-r32-a64-lr1p5e4-epoch4",
  "version": "v1"
}
```

## Summarize

```http
POST /v1/clearread/summarize
Content-Type: application/json
Authorization: Bearer <CLEARREAD_AI_SERVICE_API_KEY>
```

Request:

```json
{
  "requestId": "reading-001",
  "texts": [
    {
      "id": "block-1",
      "text": "Source text block..."
    }
  ],
  "options": {
    "includeDebug": false
  }
}
```

Success response:

```json
{
  "requestId": "reading-001",
  "status": "ok",
  "results": [
    {
      "id": "block-1",
      "status": "ok",
      "summary": "A concise summary.",
      "keyPoints": [
        "A useful point.",
        "Another useful point."
      ],
      "schemaGuardAction": "none",
      "error": null
    }
  ],
  "errors": [],
  "meta": {
    "service": "clearread-ai-summary",
    "version": "v1",
    "model": "clearread-llama32-3b-qlora-phase2-r32-a64-lr1p5e4-epoch4",
    "modelBackend": "vllm"
  }
}
```

## Limits

```text
MAX_BLOCKS=32
MAX_CHARS_PER_BLOCK=11000
REQUEST_BODY_LIMIT_BYTES=2097152
VLLM_MAX_CONCURRENCY=32
VLLM_MAX_TOKENS=260
VLLM_TIMEOUT_SECONDS=90
VLLM_MAX_MODEL_LEN=8192
```

The `keyPoints` array is dynamic. Backend and frontend code should render the returned array as provided.
