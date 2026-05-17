# Clearead 8B LoRA Training Package

This folder documents the Clearead Llama 3.1 8B training cycle. It explains how Candidate A was prepared, trained, evaluated, and packaged, with scripts, configuration files, reports, history notes, and metadata needed for review.

## Selected Model

```text
Base model: unsloth/Llama-3.1-8B-Instruct-unsloth-bnb-4bit
Training method: SFT + QLoRA
Selected adapter: Candidate A, 3 epochs
```

Candidate A completed training within available GPU memory, passed validation strongly, and performed well on the final held-out test set.

## Key Results

| Area | Result |
| --- | --- |
| Source records | 1,452 accepted records |
| Split | 1,162 train, 145 validation, 145 test |
| Full training | 3 epochs, 438 optimizer steps |
| Final train loss | 0.4797596574748216 |
| Validation loss | 0.9654271602630615 |
| Validation schema pass | 145/145 |
| Final test JSON parse | 145/145 |
| Final test schema pass | 144/145 |
| Final decision | Candidate A selected with schema guard for deployment |

The final-test schema issue was one academic-paper example with seven key points rather than the expected four. The inference wrapper handles this class of issue with schema guarding while the held-out evaluation result is preserved in the reports.

## Review Path

Read these files in order:

1. [docs/end_to_end_training_process.md](docs/end_to_end_training_process.md): full path from accepted data to final model selection.
2. [docs/experiment_history.md](docs/experiment_history.md): main iterations, retries, checks, and decisions.
3. [reports/qa_summary.md](reports/qa_summary.md): compact evidence table for data, training, validation, and final test quality.
4. [reports/CLEARREAD_LORA_TRAINING_TECHNICAL_REPORT.md](reports/CLEARREAD_LORA_TRAINING_TECHNICAL_REPORT.md): detailed technical report.
5. [docs/local_inference_runbook.md](docs/local_inference_runbook.md): local inference and schema-guard instructions.

## Package Structure

```text
8B/
  configs/            Example training, smoke-test, inference, and environment configs
  scripts/            Training, split, evaluation, inference, and environment-check scripts
  docs/               Process documentation and runbooks
  reports/            Training, validation, final-test, and QA reports
  manifests/          Metadata-only manifests and artifact metadata
  artifact_metadata/  Metadata pointer for the selected local adapter
  history/            Sanitised stage reviews and run logs
```

## Reproducibility Notes

Scripts assume this package root as the working directory:

```bash
cd ai/lora_training/8B
```

Raw accepted training data should be supplied through the project data handoff channel and passed to scripts through command-line options or a local `data/` directory.

## Artifact Policy

Large generated artifacts are represented by reports, counts, hashes, and metadata:

- raw and derived `.jsonl` datasets;
- adapter weight files such as `.safetensors`;
- base model files, tokenizer artifacts, checkpoints, and optimizer states;
- generated prediction JSONL files;
- Hugging Face cache, Unsloth compiled cache, and local runtime logs.

This package covers model training. Deployment evidence is documented in [../../model_deployment/8B/](../../model_deployment/8B/README.md).
