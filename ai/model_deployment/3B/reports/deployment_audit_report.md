# Deployment Audit Report

Date: 2026-05-16

## Executive Summary

This report records the final deployment state of the ClearRead 3B model service after installation, validation, cleanup, and reboot testing. The audit confirms that the VM contains a focused production deployment workspace, the required Docker services are running, the final LoRA adapter is present and verified, and the operational scripts are available for restart and health checks.

The deployment is organised as a maintainable service package with separate service code, Docker Compose configuration, runtime scripts, manifests, and documentation.

## Purpose

The audit was completed to provide evidence that the VM and repository package match the intended final 3B deployment. The review focused on:

- deployment directory structure;
- Docker services and restart behaviour;
- model and adapter files;
- exposed ports and internal networking;
- runtime file permissions;
- cleanup of temporary deployment materials;
- operational scripts for future handoff.

## Deployment Workspace

The VM deployment workspace is:

```text
/opt/clearread-ai-summary
```

The workspace contains the service code, Docker Compose files, model adapter directory, Hugging Face cache, and deployment support files. The repository handoff package is organised under:

```text
ai/model_deployment/3B
```

This package contains the files needed to understand, reproduce, operate, and validate the 3B deployment.

## Final Runtime State

| Runtime item | Final state |
|---|---|
| Wrapper API container | Running as `deploy-clearread-summary-api-1` |
| vLLM container | Running as `deploy-vllm-1` |
| Wrapper image | `clearread-ai-summary-api:3b-v1` |
| vLLM image | `clearread-vllm-openai-bnb:3b` |
| Public API port | TCP `8010` |
| Internal vLLM port | TCP `8000` on Docker network |
| Restart policy | `unless-stopped` |
| GPU process | `VLLM::EngineCore` on NVIDIA L4 |
| Model backend | vLLM |
| LoRA adapter | `phase2_r32_a64_lr1p5e4_epoch_4` |

The wrapper API serves the project-facing `/v1/clearread/summarize` endpoint. vLLM provides OpenAI-compatible model routes inside the deployment network.

## Work Completed

The deployment started with a new Google Cloud GPU VM using the Deep Learning VM image. Docker, Docker Compose, and NVIDIA Container Toolkit were configured so containers could access the NVIDIA L4 GPU.

The local deployment package and final 3B LoRA adapter were uploaded to the VM. The adapter upload was verified by checking SHA-256 hashes for the adapter configuration, adapter weights, tokenizer files, chat template, and snapshot manifest.

The service was launched through Docker Compose. vLLM loaded the 3B base model with 4-bit quantisation and mounted the final LoRA adapter. The wrapper API started on port 8010 and connected to vLLM through the internal Docker network.

Validation checks confirmed health, readiness, batch summarisation, real test-split performance, and post-reboot recovery. The final handoff scripts were added so the service can be restarted and checked consistently.

## Audit Checks

| Audit area | Evidence | Result |
|---|---|---|
| Directory structure | Runtime files concentrated under `/opt/clearread-ai-summary` | Confirmed |
| Adapter presence | Adapter directory present under `models/adapters/phase2_r32_a64_lr1p5e4_epoch_4` | Confirmed |
| Adapter integrity | SHA-256 verification completed after upload | Confirmed |
| Docker services | Wrapper and vLLM containers running after start and reboot | Confirmed |
| GPU usage | `nvidia-smi` showed `VLLM::EngineCore` using NVIDIA L4 memory | Confirmed |
| Port exposure | Wrapper API published TCP 8010; vLLM kept on Docker network | Confirmed |
| Restart behaviour | Containers configured with `restart=unless-stopped` | Confirmed |
| Runtime cleanup | Temporary deployment files and one-off CUDA test image removed | Confirmed |
| Operations scripts | `restart-clearread-ai.sh` and `check-clearread-ai.sh` available in the VM home directory | Confirmed |

## Runtime Size

The final VM storage footprint was reviewed to confirm that the deployment stayed within the 100 GB disk allocation.

```text
/opt/clearread-ai-summary: about 2.4 GB
adapter files: about 203 MB
Hugging Face cache: about 2.2 GB
Docker build cache: reviewed during deployment
```

The 100 GB disk allocation provides sufficient space for the deployed service, adapter files, Docker images, and model cache used in this release.

## Operational Procedure

After VM restart, the service can be checked with:

```bash
nvidia-smi
~/restart-clearread-ai.sh
~/check-clearread-ai.sh
```

The restart script starts or recovers the Docker Compose services. The check script reports container status, local health, local readiness, vLLM logs, and GPU usage. The readiness endpoint should be used as the main signal before backend traffic is sent to the service.

## Observations and Resolutions

The deployment required directory ownership alignment under `/opt/clearread-ai-summary` before local files could be uploaded smoothly. The directory was assigned to the deployment user, and upload operations completed cleanly afterward.

The vLLM command was adjusted for the installed vLLM version. After the compatibility adjustment, the model server loaded the base model and LoRA adapter successfully.

After restart, GPU memory usage appears once vLLM has loaded the model. This is expected because Docker automatically restarts the service and vLLM occupies GPU memory during warm-up and serving.

The service requires several minutes after reboot before it reaches full readiness. This startup time comes from model loading, quantised weight loading, CUDA graph capture, and adapter activation. The operational scripts make this behaviour visible and repeatable for handoff.

## Result

The VM state is consistent with the intended ClearRead 3B model service deployment. The service workspace is organised, Docker services recover after restart, the final adapter is verified, and the documented scripts support future operation by teammates.
