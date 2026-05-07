# Model Serving And Benchmark Summary

Date: 2026-05-02

## Serving Routes Considered

| Route | Result |
|---|---|
| Per-request model load | Rejected because startup cost would be too high. |
| Persistent Transformers/Unsloth service | Functional and memory-efficient, but too slow for larger multi-block batches. |
| Raw vLLM server | Fast, but too broad and unsafe as the public ClearRead API. |
| ClearRead wrapper over internal vLLM | Accepted current deployment route. |

## Persistent Transformers Route

The persistent Transformers service proved that the selected model and adapter could be served through the final wrapper. Local smoke measurements were:

| Measurement | Result |
|---|---:|
| Startup to ready | about 30.254s |
| One-block HTTP latency | about 3.429s |
| Three-block HTTP latency | about 8.591s |
| GPU after readiness | about 7.341 GiB |
| GPU after inference | about 7.731 GiB |

This route was useful for correctness and memory sizing. It was not sufficient for the desired multi-block latency because blocks were processed sequentially.

Sequential benchmark result:

| Blocks | Latency |
|---:|---:|
| 1 | 4.911s |
| 3 | 13.548s |
| 8 | 36.536s |
| 16 | 74.887s |
| 32 | timeout near 120s |

## vLLM Route

vLLM was tested to improve multi-block throughput. The working local stack used pinned versions because the latest/default install path was not the validated route on the local environment.

Local vLLM wrapper benchmark:

| Blocks | Wrapper latency | Schema-valid successes |
|---:|---:|---:|
| 1 | 5.043s | 1/1 |
| 3 | 8.071s | 3/3 |
| 4 | 8.335s | 4/4 |
| 6 | 8.457s | 6/6 |
| 8 | 8.148s | 8/8 |
| 10 | 9.598s | 7/10 |
| 16 | 10.499s | 11/16 |
| 32 | 9.000s | 28/32 |

The key finding was that latency and all-item schema success are separate. vLLM made the request fast enough locally, but larger batches still needed schema-error handling and fallback.

## Final Deployment Direction

The accepted route is:

```text
ClearRead backend
  -> ClearRead AI Summary wrapper
    -> internal vLLM server
```

This preserves the ClearRead API contract while allowing vLLM to handle faster model serving internally.
