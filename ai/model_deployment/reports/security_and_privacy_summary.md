# Security And Privacy Summary

Date: 2026-05-02

## Main Security Decisions

| Area | Decision |
|---|---|
| Public route surface | Expose only ClearRead wrapper routes, not raw vLLM routes. |
| Authentication | Require bearer API key on `POST /v1/clearread/summarize`. |
| Frontend access | Frontend must not call the AI service directly. |
| Health probes | `/health` and `/ready` are unauthenticated but return only safe status metadata. |
| Debug responses | Disabled by default and opt-in only when service configuration allows. |
| Model artifacts | Stored outside Git. |
| Secrets | Read from environment variables or a secret manager. |

## Response Privacy

Normal successful responses include:

- input item IDs;
- public summary text;
- exactly four public key points;
- schema guard action;
- safe service metadata.

Normal responses do not include:

- full source text;
- raw model output;
- raw vLLM response fields;
- API keys;
- prompt text;
- adapter paths;
- local filesystem paths;
- cloud VM identifiers.

## Logging Privacy

Default service logs are designed to record operational metadata:

- request ID;
- item IDs;
- text lengths;
- status;
- latency;
- error codes.

They should not record full source text, raw model output, API keys, private endpoints, model paths, or adapter file paths.

## vLLM Exposure Control

Direct vLLM serving was tested but not accepted as the public API surface. vLLM exposes a broad model-server route set, while ClearRead needs only summary-specific routes. The accepted architecture keeps vLLM internal and makes the FastAPI wrapper the only application-facing service.

## Package Sanitisation

Before packaging, raw deployment materials were reviewed and reduced to code, reusable scripts, and clean summaries. The package excludes:

- raw temporary VM details;
- public endpoint IPs;
- local machine paths;
- raw logs;
- secrets;
- large model artifacts;
- internal planning records.
