# Gemma E4 versus Llama 8B deployment-feasibility check

Date: 2026-05-13

## Status

- Background automation `monitor-fine-tune-sweep-long-run` is paused.
- The broader 3-4B fine-tune sweep is paused.
- No live `fine_tune_sweep` training process was detected before this check.
- This check is not a model-quality benchmark and does not resume Stage 2/Stage 3.

## Question

Does `google/gemma-4-E4B-it` have enough deployment value to justify more training experiments, compared with the already deployed Llama 3.1 8B Candidate A route?

The comparison prioritises inference speed and GPU memory.

## Llama 8B real deployment baseline

Source: `<external-local-raw-iteration1-deployment-workspace-not-in-git>/docs/GCP_L4_PRESSURE_TEST_REPORT.md`

Actual deployment route:

- Model: Llama 3.1 8B Instruct + QLoRA Candidate A adapter
- Runtime: vLLM behind the ClearRead API wrapper
- VM: Google Cloud `g2-standard-8`
- GPU: 1 x NVIDIA L4
- GPU memory: about 23 GB
- Current MVP config: `max text blocks=28`, wrapper concurrency `28`, vLLM max sequences `28`, max output tokens `256`, eager mode disabled

Measured capacity:

| Case | Result |
|---|---:|
| Stable 28-block wrapper runs | `26.438s`, `22.669s`, `25.037s`, all `28/28 ok` |
| Direct internal vLLM, 28 blocks | `23.879s`, `28/28 schema-valid` |
| Wrapper 28 blocks | `26.438s`, `28/28 valid public results` |
| 32-block repeated runs | `34.484s`, `31.619s`, `34.330s`, over target |
| Active GPU memory near 28/32 tests | about `17,976 MiB / 23,034 MiB` |
| Idle GPU memory after final 28-block config | about `17,016 MiB / 23,034 MiB` |

Interpretation:

The real Llama 8B deployment can process 28 representative text blocks under about 30 seconds on one L4 GPU. It is already a working high-throughput baseline, although it uses much of the L4 memory.

## Older local Llama 8B sequential route

Source: `<external-local-raw-iteration1-deployment-workspace-not-in-git>/benchmarks/011_machine_sizing/benchmark_results.json`

This is not the final deployment route, but it is useful as a local single-GPU reference.

| Case | Latency | GPU memory after run |
|---|---:|---:|
| Readiness after load | `31.635s` startup | `7,911 MiB` |
| 1 block | `4.911s` | `8,301 MiB` |
| 3 blocks | `13.548s` | `8,525 MiB` |
| 8 blocks | `36.536s` | `8,525 MiB` |

Interpretation:

The old sequential route was much slower than vLLM for multi-block use, which is why the project moved to vLLM. Even there, Llama 8B single-block latency was much lower than the Gemma local smoke result below.

## Gemma E4 local deployment-style smoke

Source: `<external-local-raw-3b-search-workspace-not-in-git>/outputs/deployment_feasibility/gemma_e4_local_transformers_smoke.json`

Route tested:

- Model: `google/gemma-4-E4B-it`
- Runtime: local Transformers sequential generation
- GPU: local RTX 4070 Ti SUPER, 16 GB
- Quantization: 4-bit bitsandbytes
- Data source: same deployment-style `all_v1.jsonl` source used by previous pressure-test tooling
- Seed: `20021`
- Raw inputs and raw outputs: not saved
- Max input tokens: `3072`
- Max new tokens: `256`

Measured result:

| Case | Latency | GPU memory |
|---|---:|---:|
| Load | `100.271s` | after load `10,175 MiB / 16,376 MiB` |
| 1 block | `19.909s`, `1/1 parse ok` | after run `10,479 MiB / 16,376 MiB` |
| 3 blocks | `37.395s`, `3/3 parse ok` | after run `10,728 MiB / 16,376 MiB` |
| Torch peak allocated | n/a | `9,406.76 MiB` |
| Torch peak reserved | n/a | `9,544.0 MiB` |

Local vLLM status:

- `vLLM` is not currently importable in either checked local conda environment.
- Therefore this quick local run does not prove whether Gemma E4 can or cannot achieve much better speed through vLLM.

## Comparison

| Question | Llama 8B Candidate A | Gemma E4 current evidence |
|---|---:|---:|
| Real deployed route exists | yes | no |
| Real deployed GPU | L4 23 GB | not tested |
| Real vLLM throughput | 28 blocks in about `22.7-26.4s` stable | not tested |
| Current local single-block latency | old route `4.911s` | `19.909s` |
| Current local 3-block latency | old route `13.548s` | `37.395s` |
| Local route memory after load | old route about `7,911 MiB` | `10,175 MiB` |
| Schema/readiness signal | strong after fine-tune/deployment | strong prompt-only format, but not yet deployed |

## Decision

Gemma E4 should not block the main search and should not receive full fine-tuning budget before a deployment-runtime proof.

Current evidence does not prove Gemma E4 is impossible to deploy efficiently, because training cost and local Transformers latency are not the same as optimized vLLM serving. However, it also does not support the original goal of finding a clearly smaller, cheaper, faster replacement for the existing Llama 8B route.

The existing Llama 8B route already has a real L4 deployment that handles 28 representative blocks under about 30 seconds. Gemma E4, in the local sequential smoke, took about 20 seconds for one block and 37 seconds for three blocks.

## Recommended next gate

Only continue Gemma if a short rented-GPU deployment smoke is acceptable.

Minimum useful Gemma deployment smoke:

1. Use the same or comparable L4/A10/A100 class GPU.
2. Test whether Gemma E4 can load under vLLM or another optimized serving runtime.
3. Run the same deployment-style sample seed and block ladder: `1`, `3`, `8`, then optionally `16` and `28`.
4. Stop Gemma if it cannot load in optimized serving, or if `8` blocks cannot approach the existing Llama 8B L4 latency envelope.
5. Only train Gemma if this deployment smoke shows a real speed/memory path that could beat or closely match the old 8B deployment.

For now, Gemma has only limited experimental value as a bounded side test, not as the main replacement candidate.
