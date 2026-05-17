# Google Cloud L4 Restart Runbook

This runbook records the restart shape used for the tested Google Cloud L4 deployment without storing VM names, public IPs, private usernames, or secrets.

## Assumed Runtime Shape

```text
ClearRead API wrapper on port 8010
Internal vLLM server on port 8014
NVIDIA L4 GPU
Selected LoRA adapter mounted outside Git
```

The wrapper should be the only service reachable by the ClearRead backend. The internal vLLM server should remain bound to `127.0.0.1` or a private interface.

## Required Environment Variables

```text
CLEARREAD_AI_RUNTIME=vllm_http
CLEARREAD_AI_SERVICE_API_KEY=<secret>
CLEARREAD_AI_SERVICE_HOST=0.0.0.0
CLEARREAD_AI_SERVICE_PORT=8010
CLEARREAD_AI_MODEL_LABEL=clearread-llama31-8b-qlora-candidate-a
CLEARREAD_AI_MAX_TEXTS_PER_REQUEST=28
CLEARREAD_AI_MAX_CHARACTERS_PER_TEXT=11000
CLEARREAD_AI_MAX_REQUEST_BODY_BYTES=2097152
CLEARREAD_AI_REQUEST_TIMEOUT_SECONDS=120
CLEARREAD_AI_VLLM_BASE_URL=http://127.0.0.1:8014
CLEARREAD_AI_VLLM_API_KEY=<internal-secret>
CLEARREAD_AI_VLLM_MODEL=clearread
CLEARREAD_AI_VLLM_INTERNAL_CONCURRENCY=28
CLEARREAD_AI_VLLM_REQUEST_TIMEOUT_SECONDS=30
CLEARREAD_AI_VLLM_SCHEMA_RETRY_ATTEMPTS=0
CLEARREAD_AI_VLLM_MAX_TOKENS=256
```

The vLLM process should be started with settings equivalent to:

```text
max sequences: 28
maximum output tokens: 256
eager mode: disabled
LoRA adapter: selected ClearRead adapter
```

## Restart Checklist

1. Confirm the GPU is visible.

```bash
nvidia-smi
```

2. Stop old API and vLLM processes through the configured process manager.

3. Start the internal vLLM server first.

4. Wait until the vLLM server answers a local model/readiness probe.

5. Start the ClearRead AI Summary API wrapper.

6. Check wrapper liveness and readiness.

```bash
curl -s http://127.0.0.1:8010/health
curl -s http://127.0.0.1:8010/ready
```

7. Run an authenticated one-block smoke test through the wrapper.

8. Run a small multi-block smoke test, such as 3 or 8 blocks.

9. Confirm `/docs` and `/openapi.json` are not exposed by the wrapper.

10. Confirm the raw vLLM port is not externally reachable.

## Expected Post-Restart State

| Check | Expected result |
|---|---|
| `/health` | HTTP 200 |
| `/ready` | HTTP 200 after model/runtime readiness |
| Unauthenticated summarize call | HTTP 401 |
| Authenticated one-block summarize call | HTTP 200 with one result |
| Public result fields | `summary`, `keyPoints`, `schemaGuardAction` |
| Raw vLLM fields in wrapper response | absent |

## Rollback

If the 28-block setting fails after restart:

1. Lower `CLEARREAD_AI_MAX_TEXTS_PER_REQUEST` to `24`.
2. Lower `CLEARREAD_AI_VLLM_INTERNAL_CONCURRENCY` to `24`.
3. Restart vLLM and the wrapper.
4. Re-run 8, 16, 24-block pressure checks.

If the wrapper cannot reach vLLM, keep the endpoint out of backend traffic and fall back to the existing non-AI summarizer until the runtime is healthy.
