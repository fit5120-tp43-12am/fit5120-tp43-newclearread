# Backend Integration Guide

This guide describes how the main ClearRead backend should call the AI Summary service.

## Expected Call Path

```text
Browser frontend -> ClearRead backend -> ClearRead AI Summary service
```

The browser frontend should never call the AI Summary service directly. The backend owns authentication, fallback behaviour, request shaping, and timeout handling.

## Backend Environment Variables

```text
CLEARREAD_AI_SUMMARY_ENABLED=true
CLEARREAD_AI_SUMMARY_API_URL=http://127.0.0.1:8010
CLEARREAD_AI_SUMMARY_API_KEY=<secret>
CLEARREAD_AI_SUMMARY_TIMEOUT_SECONDS=130
CLEARREAD_AI_SUMMARY_MAX_BLOCKS=28
CLEARREAD_AI_SUMMARY_MAX_CHARS_PER_BLOCK=11000
```

For a more conservative product setting, use:

```text
CLEARREAD_AI_SUMMARY_MAX_BLOCKS=24
```

## Request Construction

The backend should send one already-segmented reading block per item:

```json
{
  "requestId": "reading-123",
  "texts": [
    {
      "id": "block-1",
      "text": "Prepared reading block text..."
    }
  ],
  "options": {
    "includeDebug": false
  }
}
```

Use stable block IDs so partial failures can be mapped back to the original reading blocks.

## Response Handling

The backend should:

- Preserve item order when mapping returned summaries to reading blocks.
- Treat `status: "ok"` items as usable AI summaries.
- Use the existing fallback summarizer for any item with `status: "error"`.
- Use fallback for all blocks when the whole request returns `401`, `413`, `422`, `429`, `503`, `504`, or a network timeout.
- Log request ID, item IDs, item count, error codes, and latency.
- Avoid logging full source text or raw model output.

## Timeout Setting

The AI service currently has a 120-second service-side timeout. The backend timeout should be slightly higher, around 125 to 130 seconds, so the service has a chance to return a structured `504` first.

For the measured L4 MVP setup, normal 24 to 28 block requests are expected to target about 30 seconds, but the longer service timeout protects against slow startup, cold runtime behaviour, or unusually token-heavy blocks.

## Input Limit Alignment

The backend should enforce limits before calling the AI service:

| Limit | Recommended backend value |
|---|---:|
| Max blocks per request | 28 current MVP, or 24 conservative |
| Max characters per block | 11000 |
| Request timeout | 130 seconds |

If the backend sends more than the service cap, the service returns a whole-request `422`.
