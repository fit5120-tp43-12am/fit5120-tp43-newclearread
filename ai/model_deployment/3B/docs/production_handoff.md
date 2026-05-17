# Production Handoff

## Service Summary

The ClearRead 3B model service is deployed as a production API for backend integration. The backend submits all prepared text chunks for a reading request in one API call and receives one ordered batch response.

```text
Base URL: http://34.21.166.229:8010
Endpoint: POST /v1/clearread/summarize
Authentication: Authorization: Bearer <service API key>
```

## Backend Integration

The backend request body should include a stable request ID and a `texts` array:

```json
{
  "requestId": "reading-001",
  "texts": [
    {
      "id": "block-1",
      "text": "Prepared source text block..."
    }
  ],
  "options": {
    "includeDebug": false
  }
}
```

Each result item contains:

- `id`: original block ID.
- `status`: `ok` or `error`.
- `summary`: returned summary text.
- `keyPoints`: returned key point array.
- `schemaGuardAction`: response validation action.
- `error`: per-block error details when present.

## Parallel Processing

For a request with 20 blocks, the wrapper submits the valid blocks concurrently. The current concurrency limit is 32, so 20 blocks are eligible for concurrent vLLM requests. vLLM then schedules the requests on the GPU.

## Current Access Control

GCP firewall rules allow the approved backend source IP ranges to reach TCP port 8010. The wrapper requires the Bearer service key for the summarize endpoint.

## Operational Check

The standard VM check command is:

```bash
~/check-clearread-ai.sh
```

The recovery command is:

```bash
~/restart-clearread-ai.sh
```

## Evidence

Final validation evidence is summarized in:

```text
reports/testing_validation_report.md
reports/security_privacy_report.md
reports/deployment_audit_report.md
```
