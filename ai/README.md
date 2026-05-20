# Clearead AI Evidence

This directory contains the AI data, training, and deployment evidence used by the Clearead reading-support system. It is separate from the application runtime code so reviewers can evaluate the model work without searching through the web app or backend folders.

## Directory Map

| Path | Purpose |
| --- | --- |
| [data_preparation/](data_preparation/README.md) | Source collection, cleaning, label regeneration, QA, and final dataset manifests. |
| [lora_training/](lora_training/README.md) | LoRA and QLoRA training evidence for the 8B baseline and selected 3B package. |
| [model_deployment/](model_deployment/README.md) | API service wrappers, deployment configuration, benchmark evidence, and operational reports. |

## Review Path

1. Read [data_preparation/README.md](data_preparation/README.md) to understand the final `1452` accepted-record dataset and the `2 + 4` assistant-label contract.
2. Read [lora_training/README.md](lora_training/README.md) to see how model candidates were trained and compared.
3. Read [model_deployment/README.md](model_deployment/README.md) to see how the selected model is served behind the Clearead summary API contract.

## Artifact Policy

Large or sensitive runtime artifacts are represented through reports, manifests, hashes, configuration examples, and source scripts. The Git package excludes generated JSONL datasets, raw source archives, SQLite checkpoints, model weights, LoRA adapter binaries, GPU caches, private local paths, API logs, and secrets.

This structure keeps the repository lightweight while preserving enough evidence to review the data pipeline, training decisions, deployment contract, and operational constraints.
