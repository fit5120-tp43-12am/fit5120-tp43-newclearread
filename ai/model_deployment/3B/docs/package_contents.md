# Package Contents

This package contains the deployable wrapper service, deployment templates, operational scripts, model identity records, and formal validation reports for the ClearRead 3B model service.

## Included

- FastAPI wrapper source under `service/`.
- Docker Compose and vLLM image template under `deploy/`.
- Runtime environment templates under `deploy/env/`.
- Final model and API configuration records under `configs/`.
- Adapter manifest and file hashes under `manifests/`.
- Selected operations scripts under `scripts/`.
- Final deployment, testing, and security reports under `docs/` and `reports/`.

## Artifact Policy

Large model weights are tracked by manifest and hash. The deployed VM stores the adapter files at:

```text
/opt/clearread-ai-summary/models/adapters/phase2_r32_a64_lr1p5e4_epoch_4
```

Service keys, tokens, local `.env` files, raw user text, and runtime caches are excluded from the package.
