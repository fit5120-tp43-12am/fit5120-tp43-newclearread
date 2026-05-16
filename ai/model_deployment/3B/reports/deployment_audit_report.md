# Deployment Audit Report

Date: 2026-05-16

## Scope

The VM was reviewed after deployment and reboot validation. The audit checked runtime directories, Docker containers, Docker images, port exposure, file permissions, helper scripts, and GPU usage.

## Findings

- Runtime files are concentrated under `/opt/clearread-ai-summary`.
- The wrapper container is running and publishes TCP port 8010.
- The vLLM container is running on the private Docker network.
- Both containers use `restart=unless-stopped`.
- The deployed vLLM service loaded the selected LoRA adapter.
- NVIDIA L4 is visible and used by `VLLM::EngineCore`.
- Runtime environment files use restricted permissions.
- Temporary deployment files were removed.
- Docker images retained after cleanup:
  - `clearread-vllm-openai-bnb:3b`
  - `clearread-ai-summary-api:3b-v1`

## Runtime Size

Approximate VM runtime sizes:

```text
/opt/clearread-ai-summary: 2.4 GB
adapter files: 203 MB
Hugging Face cache: 2.2 GB
```

## Result

The VM state is consistent with the intended 3B service deployment.
