# Clearead Model Deployment

This directory contains deployment evidence for the core Clearead AI summary model service. It documents how selected LoRA adapters are wrapped behind a stable API contract, tested, benchmarked, and prepared for operational use.

## Directory Map

| Path | Purpose |
| --- | --- |
| [3B/](3B/README.md) | Current production deployment package for the selected Llama 3.2 3B QLoRA checkpoint. |
| [8B/](8B/README.md) | Deployment exploration and baseline package for the Llama 3.1 8B Candidate A model. |

## Deployment Contract

Both packages centre on the Clearead summary service contract:

```text
GET  /health
GET  /ready
POST /v1/clearread/summarize
```

The application backend sends already chunked text blocks and receives ordered results containing:

- input block id;
- per-block status;
- summary string;
- dynamic `keyPoints` array;
- schema-guard action;
- item-level error details when needed.

## Package Policy

Deployment packages include service source code, Docker and configuration templates, operational scripts, API contracts, benchmark scripts, reports, and manifests. Runtime secrets, local environment files, private VM paths, model weights, adapter binaries, raw benchmark logs, and generated outputs are excluded from Git.
