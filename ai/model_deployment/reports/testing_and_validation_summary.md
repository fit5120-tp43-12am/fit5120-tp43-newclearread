# Testing And Validation Summary

Date: 2026-05-02

## Summary

The deployment was validated in layers: API contract tests first, then real model smoke tests, then performance and cloud pressure tests.

## Validation Stages

| Stage | Purpose | Result |
|---|---|---|
| Mock API tests | Validate request/response contract without model artifacts. | Passed. |
| Authentication tests | Confirm missing or invalid bearer key returns `401`. | Passed. |
| Input validation tests | Confirm duplicate IDs, oversized text, oversized body, and empty text behave safely. | Passed. |
| Privacy tests | Confirm normal responses do not echo full source text or raw model output. | Passed. |
| vLLM wrapper tests | Confirm wrapper maps vLLM output to ClearRead schema and handles schema/runtime failures safely. | Passed with fake vLLM server. |
| Real Transformers smoke | Confirm selected adapter can be loaded through the final wrapper. | Passed in the validated local model environment. |
| Machine sizing | Measure sequential Transformers route. | Functional but too slow for the 30-second multi-block target. |
| Local vLLM benchmark | Measure vLLM latency and wrapper feasibility. | Latency passed locally; larger batches needed schema-error fallback. |
| Google Cloud L4 pressure test | Measure current cloud MVP capacity. | 28 representative blocks passed repeated under-target checks; 32 did not. |

## Test Coverage In The Package

The included tests cover:

- `GET /health`
- `GET /ready`
- `POST /v1/clearread/summarize`
- bearer authentication
- max text count
- max text characters
- max request-body bytes
- duplicate IDs
- empty text
- partial success
- response ordering
- disabled docs/openapi routes
- safe metadata logging
- vLLM HTTP runtime success and failure mapping

## Commands

```powershell
cd ai/model_deployment/service
python -m pytest tests/ai_summary_service
```

The benchmark scripts require additional model runtime dependencies and external model artifacts. They are included for reproducibility of the deployment method, not as lightweight unit tests.
