from __future__ import annotations

import argparse
import os
import platform
import random
import time
from pathlib import Path
from typing import Any

import unsloth  # noqa: F401  Must be imported before transformers/peft/trl.
from unsloth import FastLanguageModel

from training_data_utils import (
    SupervisedDataCollator,
    append_text,
    build_features_for_records,
    ensure_tokenizer_padding,
    eta_status,
    file_sha256,
    load_manifest_metadata,
    load_yaml_config,
    local_timestamp,
    markdown_table,
    metadata_for_record,
    read_jsonl,
    resolve_project_path,
    verify_feature_summaries,
)

from transformers import AutoTokenizer, Trainer, TrainerCallback, TrainingArguments, set_seed


class ListDataset:
    def __init__(self, features: list[dict[str, list[int]]]) -> None:
        self.features = features

    def __len__(self) -> int:
        return len(self.features)

    def __getitem__(self, index: int) -> dict[str, list[int]]:
        return self.features[index]


class ETAProgressCallback(TrainerCallback):
    def __init__(self, total_steps: int, print_every_steps: int = 1) -> None:
        self.total_steps = total_steps
        self.print_every_steps = max(1, print_every_steps)
        self.start_time: float | None = None
        self.last_printed_step = -1
        self.records: list[dict[str, Any]] = []

    def on_train_begin(self, args, state, control, **kwargs):  # type: ignore[override]
        self.start_time = time.time()

    def on_step_end(self, args, state, control, **kwargs):  # type: ignore[override]
        if self.start_time is None:
            self.start_time = time.time()
        step = int(state.global_step)
        if step <= 0 or step == self.last_printed_step or step % self.print_every_steps != 0:
            return
        status = eta_status(self.start_time, step, self.total_steps, time.time())
        self.records.append(status)
        self.last_printed_step = step
        print(
            "progress "
            f"step={status['current_step']}/{status['total_steps']} "
            f"elapsed={status['elapsed']} "
            f"avg_s_per_step={status['average_seconds_per_step']} "
            f"remaining={status['estimated_remaining']} "
            f"eta={status['estimated_completion_time']}",
            flush=True,
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run or dry-run ClearRead smoke QLoRA training.")
    parser.add_argument("--config", default="configs/smoke_llama31_8b_qlora.example.yaml")
    parser.add_argument("--dry-run", action="store_true", help="Validate config/data/tokenization without training.")
    parser.add_argument("--model-id", default=None, help="Override configured base model id.")
    return parser.parse_args()


def configured_model_ids(config: dict[str, Any], override: str | None) -> list[str]:
    if override:
        return [override]
    model = config["model"]
    return [model["base_model_id"], *model.get("fallback_model_ids", [])]


def load_tokenizer_only(model_id: str, trust_remote_code: bool):
    tokenizer = AutoTokenizer.from_pretrained(
        model_id,
        use_fast=True,
        trust_remote_code=trust_remote_code,
    )
    ensure_tokenizer_padding(tokenizer)
    return tokenizer


def load_unsloth_model_and_tokenizer(model_ids: list[str], config: dict[str, Any], max_seq_length: int):
    last_error: Exception | None = None
    for model_id in model_ids:
        try:
            model, tokenizer = FastLanguageModel.from_pretrained(
                model_name=model_id,
                max_seq_length=max_seq_length,
                dtype=None,
                load_in_4bit=bool(config["model"].get("load_in_4bit", True)),
                trust_remote_code=bool(config["model"].get("trust_remote_code", True)),
            )
            ensure_tokenizer_padding(tokenizer)
            return model_id, model, tokenizer
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            print(f"Model load failed for {model_id}: {exc}", flush=True)
    raise RuntimeError(f"All configured model loads failed. Last error: {last_error}") from last_error


def apply_lora(model, config: dict[str, Any]):
    lora = config["lora"]
    return FastLanguageModel.get_peft_model(
        model,
        r=int(lora["r"]),
        target_modules=list(lora["target_modules"]),
        lora_alpha=int(lora["alpha"]),
        lora_dropout=float(lora["dropout"]),
        bias=str(lora.get("bias", "none")),
        use_gradient_checkpointing=lora.get("use_gradient_checkpointing", "unsloth"),
        random_state=int(lora.get("random_state", config["training"].get("seed", 5120))),
        max_seq_length=int(config["data"]["max_seq_length"]),
        use_rslora=bool(lora.get("use_rslora", False)),
        loftq_config=lora.get("loftq_config") or {},
    )


def prepare_features(root: Path, config: dict[str, Any], tokenizer) -> tuple[list[dict[str, list[int]]], list[Any], Path, Path]:
    data_path = resolve_project_path(root, config["data"]["smoke_path"])
    manifest_path = resolve_project_path(root, config["data"]["split_manifest_path"])
    records = read_jsonl(data_path)
    manifest_lookup = load_manifest_metadata(manifest_path)
    features, summaries = build_features_for_records(
        tokenizer,
        records,
        max_seq_length=int(config["data"]["max_seq_length"]),
        manifest_lookup=manifest_lookup,
    )
    ok, errors = verify_feature_summaries(summaries)
    if not ok:
        raise ValueError("Assistant-only label mask verification failed: " + "; ".join(errors))
    if len(records) != 10:
        raise ValueError(f"Smoke training must use exactly 10 records, found {len(records)}")
    return features, summaries, data_path, manifest_path


def run_dry_run(root: Path, config_path: Path, config: dict[str, Any], model_ids: list[str]) -> int:
    tokenizer = load_tokenizer_only(model_ids[0], bool(config["model"].get("trust_remote_code", True)))
    features, summaries, data_path, manifest_path = prepare_features(root, config, tokenizer)
    manifest_lookup = load_manifest_metadata(manifest_path)
    metadata = [
        metadata_for_record(record, index, manifest_lookup)
        for index, record in enumerate(read_jsonl(data_path))
    ]
    print(
        {
            "status": "dry_run_ok",
            "config": str(config_path),
            "model_tokenizer": model_ids[0],
            "records": len(features),
            "data_sha256": file_sha256(data_path),
            "manifest": str(manifest_path),
            "domains": sorted({item.domain for item in metadata if item.domain}),
            "max_input_tokens": max(summary.input_token_count for summary in summaries),
            "max_trainable_tokens": max(summary.trainable_token_count for summary in summaries),
            "truncated_records": sum(1 for summary in summaries if summary.was_truncated),
        }
    )
    return 0


def torch_precision_flags() -> tuple[bool, bool]:
    import torch

    bf16 = bool(torch.cuda.is_available() and torch.cuda.is_bf16_supported())
    fp16 = bool(torch.cuda.is_available() and not bf16)
    return bf16, fp16


def append_smoke_log(
    *,
    log_path: Path,
    config_path: Path,
    data_path: Path,
    manifest_path: Path,
    model_id: str,
    config: dict[str, Any],
    summaries,
    progress_records: list[dict[str, Any]],
    result: str,
    elapsed_seconds: float,
) -> None:
    progress_rows = [
        [
            item["current_step"],
            item["total_steps"],
            item["elapsed"],
            item["average_seconds_per_step"],
            item["estimated_remaining"],
            item["estimated_completion_time"],
        ]
        for item in progress_records[-10:]
    ]
    if not progress_rows:
        progress_rows = [["n/a", "n/a", "n/a", "n/a", "n/a", "n/a"]]

    text = "\n".join(
        [
            "",
            "# Smoke Test 001",
            "",
            f"Date/time: {local_timestamp()}",
            "",
            "## Command",
            "",
            f"`python scripts/train_smoke_qlora.py --config {config_path.as_posix()}`",
            "",
            "## Environment",
            "",
            f"- Python: `{platform.python_version()}`",
            f"- Platform: `{platform.platform()}`",
            f"- Conda env: `{os.environ.get('CONDA_DEFAULT_ENV', 'unknown')}`",
            "",
            "## Inputs",
            "",
            f"- Model id: `{model_id}`",
            f"- Data: `{data_path.as_posix()}`",
            f"- Data SHA256: `{file_sha256(data_path)}`",
            f"- Split manifest: `{manifest_path.as_posix()}`",
            f"- Split manifest SHA256: `{file_sha256(manifest_path)}`",
            "",
            "## Config",
            "",
            f"- Max sequence length: `{config['data']['max_seq_length']}`",
            f"- Per-device train batch size: `{config['training']['per_device_train_batch_size']}`",
            f"- Gradient accumulation steps: `{config['training']['gradient_accumulation_steps']}`",
            f"- Max steps: `{config['training']['max_steps']}`",
            f"- Learning rate: `{config['training']['learning_rate']}`",
            f"- LoRA r/alpha/dropout: `{config['lora']['r']}` / `{config['lora']['alpha']}` / `{config['lora']['dropout']}`",
            f"- Target modules: `{','.join(config['lora']['target_modules'])}`",
            "",
            "## Label Mask Summary",
            "",
            f"- Records: `{len(summaries)}`",
            f"- Max input tokens: `{max(summary.input_token_count for summary in summaries)}`",
            f"- Total trainable assistant tokens: `{sum(summary.trainable_token_count for summary in summaries)}`",
            "",
            "## Progress Samples",
            "",
            markdown_table(
                ["Step", "Total", "Elapsed", "Avg Sec/Step", "Remaining", "ETA"],
                progress_rows,
            ),
            "",
            "## Result",
            "",
            f"- Status: `{result}`",
            f"- Elapsed runtime: `{elapsed_seconds:.2f}` seconds",
            "",
        ]
    )
    append_text(log_path, text)


def run_training(root: Path, config_path: Path, config: dict[str, Any], model_ids: list[str]) -> int:
    import torch

    seed = int(config["training"].get("seed", 5120))
    random.seed(seed)
    set_seed(seed)

    max_seq_length = int(config["data"]["max_seq_length"])
    model_id, model, tokenizer = load_unsloth_model_and_tokenizer(model_ids, config, max_seq_length)
    model = apply_lora(model, config)
    features, summaries, data_path, manifest_path = prepare_features(root, config, tokenizer)

    output_dir = resolve_project_path(root, config["outputs"]["output_dir"])
    adapter_dir = resolve_project_path(root, config["outputs"]["adapter_dir"])
    log_path = resolve_project_path(root, config["outputs"]["smoke_log_path"])
    output_dir.mkdir(parents=True, exist_ok=True)
    adapter_dir.parent.mkdir(parents=True, exist_ok=True)

    bf16, fp16 = torch_precision_flags()
    training = config["training"]
    progress = config.get("progress", {})
    total_steps = int(training["max_steps"])
    progress_callback = ETAProgressCallback(
        total_steps=total_steps,
        print_every_steps=int(progress.get("print_every_steps", 1)),
    )

    args = TrainingArguments(
        output_dir=str(output_dir),
        per_device_train_batch_size=int(training["per_device_train_batch_size"]),
        gradient_accumulation_steps=int(training["gradient_accumulation_steps"]),
        max_steps=total_steps,
        learning_rate=float(training["learning_rate"]),
        warmup_steps=int(training.get("warmup_steps", 0)),
        weight_decay=float(training.get("weight_decay", 0.0)),
        lr_scheduler_type=str(training.get("lr_scheduler_type", "linear")),
        optim=str(training.get("optim", "adamw_8bit")),
        logging_steps=int(training.get("logging_steps", 1)),
        save_strategy=str(training.get("save_strategy", "no")),
        report_to=list(training.get("report_to", [])),
        bf16=bf16,
        fp16=fp16,
        remove_unused_columns=False,
        seed=seed,
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=ListDataset(features),
        data_collator=SupervisedDataCollator(tokenizer),
        callbacks=[progress_callback],
    )

    start = time.time()
    result = "success"
    try:
        trainer.train()
        model.save_pretrained(str(adapter_dir))
        tokenizer.save_pretrained(str(adapter_dir))
    except Exception:
        result = "failure"
        raise
    finally:
        elapsed = time.time() - start
        append_smoke_log(
            log_path=log_path,
            config_path=config_path,
            data_path=data_path,
            manifest_path=manifest_path,
            model_id=model_id,
            config=config,
            summaries=summaries,
            progress_records=progress_callback.records,
            result=result,
            elapsed_seconds=elapsed,
        )

    print({"status": result, "adapter_dir": str(adapter_dir), "smoke_log": str(log_path)})
    return 0


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    config_path = resolve_project_path(root, args.config)
    config = load_yaml_config(config_path)
    model_ids = configured_model_ids(config, args.model_id)

    if args.dry_run:
        return run_dry_run(root, config_path, config, model_ids)
    return run_training(root, config_path, config, model_ids)


if __name__ == "__main__":
    raise SystemExit(main())
