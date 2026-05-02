# ClearRead Llama LoRA Training Package

This folder is the Git-safe, teacher-facing package for the ClearRead local model training work. It documents how the final Candidate A LoRA adapter was prepared, trained, evaluated, and packaged, without committing raw JSONL data, model weights, checkpoints, cache files, or local machine paths.

## Final Result

The selected model for this training cycle is:

```text
Llama-3.1-8B-Instruct + SFT + QLoRA
Base model: unsloth/Llama-3.1-8B-Instruct-unsloth-bnb-4bit
Selected adapter: Candidate A, 3 epochs
```

Candidate A was selected because it completed training without OOM, passed validation strongly, and performed well on the final held-out test set.

Key results:

| Area | Result |
| --- | --- |
| Source records | 1452 accepted records |
| Split | 1162 train, 145 validation, 145 test |
| Training route | Supervised fine-tuning with QLoRA |
| Full training | 3 epochs, 438 optimizer steps |
| Final train loss | 0.4797596574748216 |
| Validation loss | 0.9654271602630615 |
| Validation schema pass | 145/145 |
| Final test JSON parse | 145/145 |
| Final test schema pass | 144/145 |
| Final decision | Candidate A selected with schema guard for deployment |

The only final-test schema failure was one academic-paper example where the model produced seven key points instead of exactly four. The inference wrapper handles this class of issue with a schema guard; the held-out result itself is kept unchanged.

## Where To Start

Read these files in order:

1. `docs/end_to_end_training_process.md` - the full path from accepted data to final model selection.
2. `docs/experiment_history.md` - the main iterations, retries, checks, and decisions.
3. `reports/qa_summary.md` - compact evidence table for data, training, validation, and final test quality.
4. `reports/CLEARREAD_LORA_TRAINING_TECHNICAL_REPORT.md` - detailed technical report.
5. `docs/local_inference_runbook.md` - clean local inference and schema-guard instructions.

## Package Structure

```text
ai/lora_training/
  configs/            Example training, smoke-test, inference, and environment configs
  scripts/            Training, split, evaluation, inference, and environment-check scripts
  docs/               Teacher-facing process docs and runbooks
  reports/            Training, validation, final-test, and QA reports
  manifests/          Metadata-only manifests and artifact metadata
  artifact_metadata/  Metadata pointer for the selected local adapter
  history/            Sanitized work orders, decision reviews, and run logs
```

## What Is Excluded

The following files are deliberately excluded from Git:

- raw and derived `.jsonl` datasets
- model adapter weights such as `.safetensors`
- base model files, tokenizer large artifacts, checkpoints, optimizer states
- generated prediction JSONL files
- Hugging Face cache, Unsloth compiled cache, and local runtime logs

The excluded artifacts are represented by hashes, counts, reports, and metadata manifests where useful.

## Reproducibility Notes

The scripts assume they are run from this package root:

```bash
cd ai/lora_training
```

Raw accepted training data should be supplied outside Git, then passed to scripts with command-line options or placed under an ignored local `data/` directory. The package-level `.gitignore` protects these generated and private artifacts.

## Relationship To Other AI Work

This package covers model training only. The later API service and application deployment layer belongs to the separate `ai-model-deployment` work and is intentionally not reorganized here.
