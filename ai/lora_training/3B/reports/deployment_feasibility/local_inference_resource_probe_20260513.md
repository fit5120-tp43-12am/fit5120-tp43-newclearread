# Local Inference Resource Probe - 2026-05-13

## Purpose

This probe reruns the old Llama 3.1 8B Candidate A and the newer 3-4B candidate models on the same local machine, using the same script, same dataset sample, same prompt, same 4-bit loading policy where applicable, and the same sequential generation route.

This answers the deployment-feasibility question only: inference time and GPU memory on this machine. It does not replace the fine-tuning validation or full benchmark.

## Test Setup

- Machine GPU: NVIDIA GeForce RTX 4070 Ti SUPER, 16376 MiB reported by nvidia-smi.
- Environment: WSL conda environment `clearread-llama-lora`.
- Route: local single-process sequential inference, Transformers or Unsloth depending on model compatibility, not vLLM.
- Dataset source: `<external-local-raw-iteration1-data-workspace-not-in-git>/final_lora_data/outputs/accepted/all_v1.jsonl`.
- Sample seed: `20021`.
- Block counts: `1` and `3`.
- Max input tokens: `3072`.
- Max new tokens: `256`.
- Raw inputs and raw outputs were not saved in this probe.
- No files outside `fine_tune_sweep` were written by the probe.

## Results

| Model | Load s | Peak GPU MiB | 1 block s | 3 blocks total s | Mean s/block | Avg gen tokens | Gen tok/s | Parse 3/3 | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Llama 3.1 8B Candidate A | 154.969 | 7889 | 4.693 | 13.434 | 4.478 | 129.300 | 28.882 | 3/3 | completed |
| Llama 3.2 3B Instruct | 61.857 | 3688 | 6.640 | 15.852 | 5.284 | 185.300 | 35.074 | 0/3 | completed |
| Ministral 3 3B Instruct | 177.364 | 4135 | 5.907 | 18.815 | 6.272 | 212.000 | 33.803 | 1/3 | completed |
| Granite 4.1 3B | 126.135 | 3739 | 8.535 | 25.283 | 8.428 | 193.700 | 22.980 | 1/3 | completed |
| Phi-4-mini-instruct | 146.952 | 4547 | 7.737 | 20.971 | 6.990 | 250.300 | 35.811 | 2/3 | completed |
| Qwen 3.5 4B | 182.323 | 5065 | 8.854 | 28.255 | 9.418 | 171.300 | 18.191 | 0/3 | completed |
| Gemma 4 E2B IT | 193.821 | 8199 | 17.463 | 32.649 | 10.883 | 171.700 | 15.774 | 2/3 | completed |
| Gemma 4 E4B IT | 310.970 | 10951 | 20.559 | 46.776 | 15.592 | 211.300 | 13.554 | 3/3 | completed |

## Reading The Results

The old Llama 3.1 8B Candidate A is faster than all tested 3-4B base candidates in this sequential local route, mainly because it generates shorter schema-compliant outputs after fine-tuning. Smaller parameter count does reduce model memory for several candidates, but it does not automatically reduce end-to-end latency when the model emits more tokens or uses a heavier architecture/runtime path.

Gemma 4 E4B and E2B are especially poor fits for the original goal of replacing the 8B deployment with a smaller and faster model: both use more local GPU memory than most 3B candidates and are much slower in this probe.

## Limitations

- This is a small resource probe, not a full quality benchmark.
- It uses sequential local inference, not the old cloud vLLM deployment stack.
- Base models are not fine-tuned except the old Llama 3.1 8B Candidate A adapter.
- Parse success is recorded only as a sanity signal; the main target here is time and memory.
