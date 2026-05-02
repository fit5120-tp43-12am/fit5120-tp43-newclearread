# ClearRead AI Summary API Contract

Date: 2026-05-02

## Purpose

`clearread-ai-summary` is a standalone internal service for summarising text blocks that have already been prepared by the ClearRead application. It does not upload files, parse documents, segment text, train models, or serve the frontend.

The service hides model paths, prompts, runtime details, adapter details, and raw model output behind a stable HTTP contract.

## Endpoints

| Method | Path | Purpose | Authentication |
|---|---|---|---|
| `GET` | `/health` | Process liveness check | none |
| `GET` | `/ready` | Runtime readiness check | none |
| `POST` | `/v1/clearread/summarize` | Summarise one or more text blocks | bearer API key |

The summarize endpoint requires:

```http
Content-Type: application/json
Authorization: Bearer <CLEARREAD_AI_SERVICE_API_KEY>
```

## Request Shape

```json
{
  "requestId": "optional-client-request-id",
  "texts": [
    {
      "id": "block-1",
      "text": "Source block text..."
    }
  ],
  "options": {
    "includeDebug": false
  }
}
```

Rules:

- `texts` must contain 1 to `maxTextsPerRequest` items.
- Each `texts[].id` must be non-empty, unique inside the request, and at most 128 characters.
- Empty text is returned as an item-level error.
- Oversized text is returned as an item-level error.
- Duplicate IDs or an invalid request body return a whole-request error.

## Current Limits

| Limit | Default or current setting | Notes |
|---|---:|---|
| Code default `maxTextsPerRequest` | 32 | Service default and API contract maximum. |
| Current measured L4 MVP cap | 28 | Highest stable repeated setting under the current target. |
| Conservative product cap | 24 | Recommended if more latency margin is needed. |
| `maxCharactersPerText` | 11000 | Based on training-input distribution plus headroom. |
| `maxRequestBodyBytes` | 2097152 | 2 MiB request-body guard. |
| Service request timeout | 120s | Backend timeout should be slightly higher. |

## Successful Response Shape

```json
{
  "requestId": "optional-client-request-id",
  "status": "ok",
  "results": [
    {
      "id": "block-1",
      "status": "ok",
      "summary": "Two-sentence main idea.",
      "keyPoints": [
        "Point one.",
        "Point two.",
        "Point three.",
        "Point four."
      ],
      "schemaGuardAction": "none"
    }
  ],
  "errors": [],
  "meta": {
    "service": "clearread-ai-summary",
    "version": "v1",
    "model": "clearread-llama31-8b-qlora-candidate-a"
  }
}
```

The wrapper-native model output is mapped as follows:

| Wrapper output | Public API field |
|---|---|
| `main_idea` | `summary` |
| `key_points` | `keyPoints` |

## Error Behaviour

Whole-request errors use non-200 HTTP status codes when the service cannot safely process the batch. Item-level errors are returned inside `results` with HTTP `200` when the request itself is valid.

Common whole-request errors:

| HTTP | Code | Retryable |
|---:|---|---:|
| 400 | `malformed_json` | false |
| 401 | `unauthorized` | false |
| 413 | `request_body_too_large` | false |
| 415 | `unsupported_media_type` | false |
| 422 | `invalid_request` | false |
| 429 | `too_many_requests` | true |
| 503 | `service_not_ready` | true |
| 504 | `request_timeout` | true |
| 500 | `internal_error` | true |

Common item-level errors:

| Code | Retryable | Meaning |
|---|---:|---|
| `empty_text` | false | Text is empty or whitespace only. |
| `text_too_large` | false | Text exceeded the configured character cap. |
| `model_schema_error` | false | The model output could not be converted to the public schema. |
| `model_runtime_error` | true | The runtime failed for that item. |

## Security Rules

- API keys must come from environment variables or secret managers.
- The frontend must not call this service directly.
- Normal responses must not include raw source text, raw model output, API keys, local paths, prompts, or vLLM internals.
- Debug output is opt-in and disabled in production by default.
- The internal vLLM server should bind to localhost or a private interface and should not be exposed as the ClearRead API.
