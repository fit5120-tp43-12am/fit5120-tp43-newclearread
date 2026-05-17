# Cloud Server Research Summary

Date: 2026-05-02

## Initial Direction

The first deployment research focused on a 16 GB GPU because the persistent Transformers route used under 8 GiB VRAM locally after readiness and inference. A 16 GB T4-style VM looked reasonable for a first smoke deployment.

That recommendation changed after the 30-second multi-block target became important. vLLM was much faster, but local vLLM readiness used most of a 16 GB-class GPU. This made 24 GB GPU options a more credible target for the model-serving route.

## Provider Findings

| Provider or class | Finding |
|---|---|
| Azure T4 16 GB | Good initial fit for persistent Transformers smoke, not preferred for vLLM SLA route. |
| Google Cloud T4 16 GB | Possible fallback for simple serving, but high risk for vLLM capacity. |
| Google Cloud L4 24 GB | Accepted for MVP pressure testing. |
| A10/A10G 24 GB class | Plausible next target if L4 is unavailable. |
| A100 40 GB class | More expensive option if stricter capacity or concurrency is required. |
| GPU marketplaces | Useful for experiments, less clean for stable team handoff and network controls. |

## Final Research Outcome

The project moved from "minimum GPU that can load the model" to "GPU and runtime that can return document-level batches within the target latency."

That led to the tested L4 route:

- 1 x NVIDIA L4 GPU;
- ClearRead wrapper over internal vLLM;
- current stable MVP cap of 28 representative blocks;
- conservative product cap of 24 representative blocks.

## Remaining Cloud Risks

- Results are tied to the tested VM shape and configuration.
- Real documents may be more token-heavy than benchmark samples.
- Endpoint hardening, process supervision, secret rotation, and backend network restrictions need to be handled in the hosting environment.
- If production needs more than 28 representative blocks under the same target, the team should test faster GPUs, shorter block limits, guided JSON decoding, or multi-request batching.
