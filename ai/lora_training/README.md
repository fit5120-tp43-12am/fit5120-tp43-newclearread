# ClearRead LoRA Training Packages

This folder contains the model-training evidence packages for the ClearRead AI work.

It is organised by model scale:

```text
ai/lora_training/
  8B/   Original Llama 3.1 8B Candidate A training package
  3B/   Later 3B-scale replacement experiment package
```

## 8B Package

The `8B/` folder documents the original successful training cycle:

```text
Llama 3.1 8B Instruct + SFT + QLoRA
Selected adapter: Candidate A
```

This package includes the cleaned training reports, scripts, configuration examples, manifests, and stage history that explain how Candidate A was trained and selected.

## 3B Package

The `3B/` folder documents the later experiment that tested whether a smaller model could replace the 8B baseline for the ClearRead summarisation task.

Final practical recommendation:

```text
Llama 3.2 3B Instruct + SFT + QLoRA
Selected adapter checkpoint: phase2_r32_a64_lr1p5e4_epoch_4
```

The 3B package is designed to be read together with its final report:

```text
3B/reports/final/school_final_3b_experiment_report_en.md
```

## Large Artifacts

This Git package intentionally excludes large generated artifacts, including:

- base model files
- LoRA adapter weight files
- Hugging Face caches
- optimizer checkpoints
- raw datasets
- full raw API response dumps
- large generated output folders

Those artifacts are represented by reports, summary files, manifests, hashes, parse-failure records, and benchmark score summaries.

