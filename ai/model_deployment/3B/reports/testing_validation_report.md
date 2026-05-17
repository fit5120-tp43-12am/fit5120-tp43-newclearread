# Testing and Validation Report

Date: 2026-05-16

## Executive Summary

This report summarises the validation work completed for the ClearRead 3B summary model service. The validation confirmed that the service can receive a batch of text blocks from the project backend, process the blocks concurrently through the wrapper API and vLLM backend, and return structured JSON responses containing a summary and key points for each block.

The final deployment passed the VM environment checks, adapter integrity checks, container startup checks, local API checks, batch request checks, reboot recovery checks, and project-environment comparison checks. The service is ready for backend integration and project demonstration.

## Purpose

The deployment goal was to provide a production-style model service for the latest 3B ClearRead model. The backend server can call the model service through an HTTP API, pass all text chunks in a single request, and receive one combined JSON response. This design supports the project requirement for fast batch summarisation while keeping model serving separate from the main backend application.

The validation focused on four questions:

- whether the VM can run the model service with the selected NVIDIA L4 GPU;
- whether the uploaded LoRA adapter is the intended final 3B adapter;
- whether the API contract supports batch text-block input and structured output;
- whether the service remains usable after VM restart and backend-style calls.

## Deployment Environment

| Item | Value |
|---|---|
| Cloud provider | Google Cloud Platform |
| Project | `clearead-junwei` |
| VM instance | `instance-20260516-075135` |
| Zone | `asia-southeast1-c` |
| VM shape | `g2-standard-4`, 4 vCPU, 16 GB RAM |
| GPU | 1 x NVIDIA L4 |
| Disk | 100 GB persistent disk |
| Operating system | Ubuntu 22.04 LTS Deep Learning VM |
| Model serving backend | vLLM |
| Public wrapper port | TCP 8010 |
| Internal vLLM port | TCP 8000 inside Docker network |
| Deployed adapter | `phase2_r32_a64_lr1p5e4_epoch_4` |
| Public model name | `clearread-llama32-3b-qlora-phase2-r32-a64-lr1p5e4-epoch4` |

## Work Completed

The validation process started with a clean GPU VM and confirmed the operating system, disk space, CPU, memory, CUDA driver, PyTorch GPU visibility, and NVIDIA L4 availability. Docker and NVIDIA Container Toolkit were then configured so the vLLM container could access the GPU from inside Docker.

The final LoRA adapter was uploaded to the VM under `/opt/clearread-ai-summary/models/adapters/phase2_r32_a64_lr1p5e4_epoch_4`. The adapter files were checked with SHA-256 hashes after upload. The hash verification confirmed that the VM copy matched the intended local adapter artifact.

The deployment package was started with Docker Compose. The wrapper API container and the vLLM container were brought up together on an internal Docker network. The wrapper API exposes the backend-facing endpoint, while vLLM performs model inference with the base 3B model and the deployed LoRA adapter.

After startup, the service was tested through health, readiness, single-block, multi-block, real test-split, and post-reboot calls. The tests used the same API shape expected by the project backend: one request containing multiple text blocks and one response containing per-block results.

## Validation Results

| Validation area | Evidence collected | Result |
|---|---|---|
| VM baseline | Ubuntu 22.04 LTS, 100 GB disk, 4 vCPU, 16 GB RAM, NVIDIA L4 visible | Passed |
| GPU runtime | `nvidia-smi` worked on host and inside Docker runtime | Passed |
| Adapter integrity | SHA-256 hashes matched for adapter config, weights, tokenizer, template, and manifest files | Passed |
| vLLM startup | Base model and LoRA adapter loaded; server exposed `/v1/models` and chat completion routes | Passed |
| Wrapper API health | `/health` returned service status `ok` | Passed |
| Wrapper readiness | `/ready` returned model status `ready` after vLLM warm-up | Passed |
| One-block smoke test | Response contained one `ok` result with summary and key points | Passed |
| Four-block batch test | 4/4 blocks returned `ok` in about 2.818 seconds | Passed |
| Eight-block batch test | 8/8 blocks returned `ok` in about 2.891 seconds | Passed |
| Real test split | 16/16 blocks returned `ok` for 87,191 input characters in about 11.897 seconds | Passed |
| VM reboot recovery | Containers restarted, vLLM loaded the adapter, and a 2-block smoke test completed in about 2.940 seconds | Passed |

## Runtime Limits Confirmed

The deployed wrapper service applies request limits to keep calls predictable for the backend integration.

| Setting | Value | Purpose |
|---|---:|---|
| `MAX_BLOCKS` | 32 | Maximum text blocks per request |
| `MAX_CHARS_PER_BLOCK` | 11,000 | Maximum input characters per text block |
| `REQUEST_BODY_LIMIT_BYTES` | 2,097,152 | Maximum HTTP request body size |
| `VLLM_MAX_CONCURRENCY` | 32 | Maximum concurrent model calls from the wrapper |
| `VLLM_MAX_TOKENS` | 260 | Maximum generated tokens per block |
| `VLLM_TIMEOUT_SECONDS` | 90 | Per-block inference timeout |
| `VLLM_MAX_MODEL_LEN` | 8,192 | vLLM model context length |

The 260-token output limit is appropriate for this service because each block needs a concise summary and key points. In practical English output, 260 tokens usually corresponds to about 190 to 220 words, depending on punctuation and wording.

## Batch Processing Behaviour

The wrapper creates one asynchronous task for each valid text block in the request. The service uses a concurrency limit of 32, so a request with 20 blocks is submitted concurrently by the wrapper and scheduled by vLLM on the GPU. This matches the intended project use case, where the backend sends all text chunks together and receives one combined response.

This design keeps the backend integration simple and allows vLLM to perform efficient GPU batching internally. The tests showed that increasing the number of blocks from 4 to 8 added very little end-to-end time for short inputs, which indicates that the concurrent batch path is working as intended.

## Project Environment Comparison

A teammate tested both the 8B and 3B services through the real project environment using the same input document. The document contained about 48,000 characters and was processed as 16 text blocks. Both services used one NVIDIA L4 GPU.

| Model service | VM shape | GPU | Total seconds | Model seconds | Blocks | Fallback blocks |
|---|---|---|---:|---:|---:|---:|
| 8B service | `g2-standard-8`, 8 vCPU, 32 GB RAM | 1 x NVIDIA L4 | 23.19 | 20.72 | 16 | 0 |
| 3B service | `g2-standard-4`, 4 vCPU, 16 GB RAM | 1 x NVIDIA L4 | 12.44 | 8.37 | 16 | 0 |

Measured on model-processing time, the 3B service completed the request about 2.47 times faster than the 8B service. Measured on full project processing time, the 3B service completed the request about 1.86 times faster. The comparison is significant because the 3B service used a smaller CPU and memory configuration while running on the same GPU class.

## Observations and Resolutions

During deployment, the VM directory ownership required adjustment before files could be uploaded cleanly into `/opt/clearread-ai-summary`. Ownership was assigned to the deployment user, and the service files, deployment files, and adapter files were uploaded successfully.

The first vLLM command included a logging flag that was incompatible with the installed vLLM version. The command was updated, the containers were restarted, and vLLM then started successfully with the selected LoRA adapter.

After VM reboot, Docker restarted both containers automatically. vLLM needed several minutes for model loading, CUDA graph capture, and adapter activation before the readiness endpoint reported `ready`. Restart and check scripts were created so the VM can be recovered with a short operational procedure.

The readiness endpoint is the most reliable signal for backend use. The health endpoint confirms that the wrapper API process is running, while the readiness endpoint confirms that the model backend is ready for inference.

## Conclusion

The ClearRead 3B model service met the validation goals. It processes multiple text blocks in one request, returns structured JSON for each block, protects the backend-facing endpoint with API-key authentication, and recovers after VM restart. The project-environment comparison also showed a clear latency improvement over the earlier 8B deployment on the same GPU class.
