# Clearead LoRA Training

This directory contains the model-training evidence packages for Clearead's summarisation model work. It is organised by model scale so reviewers can understand the original 8B baseline, the 3B comparative experiment, and the selected training checkpoint used by the deployment package.

## Directory Map

| Path | Purpose |
| --- | --- |
| [8B/](8B/README.md) | Llama 3.1 8B Candidate A training package and evaluation evidence. |
| [3B/](3B/README.md) | 3B-scale model comparison and final selected Llama 3.2 3B checkpoint evidence. |

## Model Packages

| Package | Base model | Method | Result |
| --- | --- | --- | --- |
| `8B/` | `unsloth/Llama-3.1-8B-Instruct-unsloth-bnb-4bit` | SFT + QLoRA | Candidate A selected after validation and held-out testing. |
| `3B/` | `unsloth/Llama-3.2-3B-Instruct-bnb-4bit` | SFT + QLoRA | `phase2_r32_a64_lr1p5e4_epoch_4` selected as the deployment recommendation. |

The 8B package provides the original strong baseline. The 3B package documents the smaller-model evaluation and the checkpoint selected for the production deployment route in [../model_deployment/3B/](../model_deployment/3B/README.md).

## What Is Included

- Training and inference scripts.
- Evaluation, validation, and audit scripts.
- Configuration examples.
- Compact benchmark summaries.
- Technical reports and review evidence.
- Manifests, hashes, and evidence inventories.
- Sanitised run history where needed for traceability.

## Artifact Policy

The Git package excludes large generated artifacts:

- base model files;
- LoRA adapter weight files;
- Hugging Face and Unsloth caches;
- optimizer checkpoints;
- raw datasets;
- full prediction JSONL outputs;
- raw API response dumps.

These artifacts are represented through reports, score summaries, manifests, hashes, and configuration records.
