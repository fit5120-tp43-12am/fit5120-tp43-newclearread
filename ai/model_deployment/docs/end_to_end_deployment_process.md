# End-To-End Deployment Process

Date: 2026-05-02

## 1. Starting Point

The training work produced a selected LoRA adapter and a final inference wrapper. Deployment work started from the question: how can ClearRead use this model through a stable backend API without exposing model internals to the frontend or to the main application code?

The target service shape was:

```text
ClearRead backend -> AI Summary API -> model runtime
```

The browser frontend was not allowed to call the AI model service directly because that would expose the model API key.

## 2. First Contract

The first stable output was an API contract for a standalone service named `clearread-ai-summary`.

The service contract settled on:

- `GET /health` for process liveness.
- `GET /ready` for model/runtime readiness.
- `POST /v1/clearread/summarize` for batched text-block summary.
- Bearer API key authentication on the summarize endpoint.
- One result per input block, preserving order.
- Public field names `summary` and `keyPoints`.
- Safe item-level errors when a model output fails schema checks.

The contract separated the public ClearRead response from the wrapper-native model output:

| Wrapper-native field | Public API field |
|---|---|
| `main_idea` | `summary` |
| `key_points` | `keyPoints` |

## 3. First Service Implementation

The first implementation was a standalone FastAPI package with three runtime modes:

| Runtime | Purpose |
|---|---|
| `mock` | Contract and unit tests without model artifacts. |
| `transformers` | Persistent Unsloth/Transformers service using the final wrapper. |
| `vllm_http` | ClearRead wrapper in front of an internal vLLM OpenAI-compatible server. |

The service includes request validation, authentication, body-size limits, text-size limits, safe logging, partial-success responses, timeout handling, and schema guard mapping.

## 4. Initial Real-Model Smoke Test

The first real-model path reused the final training inference wrapper through the `transformers` runtime. This was the safest first route because it reused the already-tested wrapper and schema guard.

Important correction during this phase:

- The package initially made real smoke tests harder because importing `ai_summary_service` eagerly loaded the FastAPI app and runtime.
- The import path was adjusted so `create_app` is imported lazily.
- This allowed lightweight tests and smoke checks to import configuration and helpers without immediately loading the real model.

After this correction, the service could be tested in mock mode and then smoke-tested with real model artifacts in a separate environment.

## 5. Machine-Sizing Benchmark

The persistent Transformers route worked functionally but processed blocks sequentially. It was useful for proving the service could load and call the selected model, but it did not meet the desired 30-second multi-block target.

Observed local results:

| Batch size | Latency |
|---:|---:|
| 1 block | 4.911s |
| 3 blocks | 13.548s |
| 8 blocks | 36.536s |
| 16 blocks | 74.887s |
| 32 blocks | timed out near 120s |

This stage changed the deployment direction: a sequential Transformers service was acceptable for a simple smoke demo, but not for the desired document-level batch latency.

## 6. vLLM Retry And Compatibility Work

The next route tested vLLM because it can batch and schedule generation more efficiently.

This required a separate isolated environment because vLLM is sensitive to CUDA, PyTorch, and vLLM binary compatibility. The working local path used:

| Component | Validated version |
|---|---|
| vLLM | 0.10.1.1 |
| Torch | 2.7.1+cu118 |
| Transformers | 4.55.4 |
| BitsAndBytes | 0.49.2 |
| Workaround | `VLLM_USE_FLASHINFER_SAMPLER=0` |

The direct vLLM server was not accepted as the public API because it exposes many general model-server routes. The decision was to keep vLLM internal and put the ClearRead FastAPI wrapper in front of it.

## 7. Wrapper Over vLLM

The `vllm_http` runtime added a controlled wrapper around the internal vLLM server:

- It exposes only the ClearRead API.
- It authenticates ClearRead backend requests.
- It sends one internal chat-completion request per block.
- It preserves input order.
- It converts valid model JSON into `summary` and `keyPoints`.
- It converts invalid model output into safe item-level errors.
- It avoids returning raw vLLM response fields to the caller.

Local vLLM latency was promising, but larger local batches still showed schema reliability issues. This meant the deployment needed both performance testing and schema-success checking.

## 8. Cloud Pressure Testing

The deployment then moved to a temporary Google Cloud VM with an NVIDIA L4 GPU.

The first cloud configuration still had a low wrapper-to-vLLM internal concurrency setting. That made 8 blocks pass but 9 or more blocks exceed the target. This was treated as a configuration bottleneck, not the final system limit.

After diagnosis, the settings were adjusted:

| Setting | Earlier value | Improved value |
|---|---:|---:|
| Wrapper internal concurrency | 8 | 16, then 28 for final MVP |
| vLLM max sequences | 16 | 16, then 28 for final MVP |
| Max output tokens | 320 | 256 |
| vLLM eager mode | enabled | disabled |

The capacity search then tested higher limits. Some larger single runs passed once, but stability testing showed that 32 blocks repeatedly exceeded the target.

Final accepted MVP result:

| Candidate | Result |
|---:|---|
| 24 blocks | Conservative product setting. |
| 28 blocks | Highest stable observed setting under about 30 seconds. |
| 32 blocks | Not stable for the current target. |

## 9. Final Current Shape

The final current deployment shape is:

```text
ClearRead backend
  -> ClearRead AI Summary API wrapper
    -> internal vLLM server
      -> Llama-3.1 8B base model + selected QLoRA adapter
```

The wrapper is the part included in this package. The model adapter and runtime artifacts remain external.

## 10. Main Rework Decisions

| Problem found | Change made |
|---|---|
| Direct model loading per request would be too slow | Use a persistent service process. |
| Eager package import made smoke tests brittle | Use lazy app import in `ai_summary_service.__init__`. |
| Sequential Transformers route missed 30-second multi-block target | Test vLLM serving. |
| Raw vLLM exposed too many routes | Put ClearRead wrapper in front of vLLM. |
| Initial cloud result only supported 8 blocks | Diagnose and raise wrapper/vLLM internal concurrency. |
| 32 blocks passed once but failed repeats | Set MVP live cap to 28, with 24 as safer product cap. |
| Benchmark and cloud records included environment-specific details | Keep code and summaries, exclude raw logs, secrets, endpoint IPs, and local paths. |
