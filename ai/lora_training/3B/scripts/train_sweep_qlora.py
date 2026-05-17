from __future__ import annotations

import argparse
import json
import math
import os
import random
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from transformers import Trainer, TrainerCallback, TrainingArguments, set_seed

from sweep_utils import ROOT, file_sha256, read_json, utc_now, write_json, write_text
from training_data_utils import (
    SupervisedDataCollator,
    build_features_for_records,
    load_manifest_metadata,
    read_jsonl,
)


@dataclass
class ListDataset:
    features: list[dict[str, list[int]]]

    def __len__(self) -> int:
        return len(self.features)

    def __getitem__(self, index: int) -> dict[str, list[int]]:
        return self.features[index]


class EpochAdapterSnapshotCallback(TrainerCallback):
    def __init__(self, *, adapter_root: Path, tokenizer: Any, run_id: str, expected_epochs: int) -> None:
        self.adapter_root = adapter_root
        self.tokenizer = tokenizer
        self.run_id = run_id
        self.expected_epochs = expected_epochs
        self.saved_epochs: set[int] = set()
        self.saved_snapshots: list[dict[str, Any]] = []

    def on_epoch_end(self, args, state, control, model=None, **kwargs):  # type: ignore[override]
        epoch_float = getattr(state, "epoch", None)
        if model is None or epoch_float is None:
            return
        epoch = int(round(float(epoch_float)))
        if epoch < 1 or epoch > self.expected_epochs or epoch in self.saved_epochs:
            return
        if abs(float(epoch_float) - epoch) > 0.08:
            return

        snapshot_dir = self.adapter_root / f"{self.run_id}_epoch_{epoch}"
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        model.save_pretrained(str(snapshot_dir))
        self.tokenizer.save_pretrained(str(snapshot_dir))
        files = []
        for path in sorted(item for item in snapshot_dir.iterdir() if item.is_file()):
            files.append({"name": path.name, "size_bytes": path.stat().st_size, "sha256": file_sha256(path)})
        manifest = {
            "run_id": self.run_id,
            "epoch": epoch,
            "trainer_epoch": float(epoch_float),
            "global_step": int(getattr(state, "global_step", 0)),
            "saved_at_utc": utc_now(),
            "snapshot_dir": str(snapshot_dir),
            "files": files,
        }
        write_json(snapshot_dir / "snapshot_manifest.json", manifest)
        self.saved_epochs.add(epoch)
        self.saved_snapshots.append(manifest)
        print(json.dumps({"status": "epoch_adapter_snapshot_saved", "epoch": epoch, "snapshot_dir": str(snapshot_dir)}), flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generic 3-4B QLoRA sweep trainer.")
    parser.add_argument("--candidate-key", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--epochs", type=float, default=None)
    parser.add_argument("--learning-rate", type=float, default=None)
    parser.add_argument("--lora-r", type=int, default=None)
    parser.add_argument("--lora-alpha", type=int, default=None)
    parser.add_argument("--lora-dropout", type=float, default=None)
    parser.add_argument("--per-device-train-batch-size", type=int, default=None)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=None)
    parser.add_argument("--max-steps", type=int, default=None)
    parser.add_argument("--skip-final-eval", action="store_true")
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--model-preflight-only", action="store_true")
    parser.add_argument("--seed", type=int, default=None)
    return parser.parse_args()


def candidate_lookup(config: dict[str, Any], key: str) -> dict[str, Any]:
    for item in config["candidates"]:
        if item["key"] == key:
            return item
    raise KeyError(f"Unknown candidate key: {key}")


def resolve_run_config(args: argparse.Namespace) -> dict[str, Any]:
    sweep = read_json(ROOT / "configs" / "sweep_candidates.json")
    defaults = sweep["stage1_anchor_defaults"]
    candidate = candidate_lookup(sweep, args.candidate_key)
    run = {
        "created_at_utc": utc_now(),
        "candidate": candidate,
        "run_id": args.run_id,
        "data": sweep["data"],
        "excluded_module_name_fragments": sweep["excluded_module_name_fragments"],
        "preferred_lora_targets": sweep["preferred_lora_targets"],
        "training": {
            "epochs": float(args.epochs if args.epochs is not None else defaults["epochs"]),
            "learning_rate": float(args.learning_rate if args.learning_rate is not None else defaults["learning_rate"]),
            "lora_r": int(args.lora_r if args.lora_r is not None else defaults["lora_r"]),
            "lora_alpha": int(args.lora_alpha if args.lora_alpha is not None else defaults["lora_alpha"]),
            "lora_dropout": float(args.lora_dropout if args.lora_dropout is not None else defaults["lora_dropout"]),
            "per_device_train_batch_size": int(
                args.per_device_train_batch_size
                if args.per_device_train_batch_size is not None
                else defaults["per_device_train_batch_size"]
            ),
            "gradient_accumulation_steps": int(
                args.gradient_accumulation_steps
                if args.gradient_accumulation_steps is not None
                else defaults["gradient_accumulation_steps"]
            ),
            "warmup_ratio": float(defaults["warmup_ratio"]),
            "weight_decay": float(defaults["weight_decay"]),
            "max_grad_norm": float(defaults["max_grad_norm"]),
            "max_steps": int(args.max_steps if args.max_steps is not None else -1),
            "skip_final_eval": bool(args.skip_final_eval),
            "seed": int(args.seed if args.seed is not None else 5120),
        },
        "paths": {
            "workspace": f"model_workspaces/{candidate['key']}",
            "output_dir": f"model_workspaces/{candidate['key']}/outputs/training/{args.run_id}",
            "adapter_root": f"model_workspaces/{candidate['key']}/models/adapters",
            "final_adapter_dir": f"model_workspaces/{candidate['key']}/models/adapters/{args.run_id}_final",
            "training_log": f"model_workspaces/{candidate['key']}/logs/tests/{args.run_id}_training.md",
            "result_json": f"model_workspaces/{candidate['key']}/outputs/training/{args.run_id}_training_result.json",
            "run_config": f"model_workspaces/{candidate['key']}/configs/{args.run_id}_config.json",
        },
    }
    return run


def load_tokenizer_or_processor(candidate: dict[str, Any], cache_dir: Path) -> tuple[Any, Any]:
    from transformers import AutoProcessor, AutoTokenizer

    model_id = candidate["model_id"]
    trust_remote_code = bool(candidate.get("trust_remote_code", True))
    if candidate.get("loader") == "image_text_to_text":
        processor = AutoProcessor.from_pretrained(model_id, cache_dir=str(cache_dir), trust_remote_code=trust_remote_code)
        tokenizer = getattr(processor, "tokenizer", processor)
    else:
        tokenizer = AutoTokenizer.from_pretrained(model_id, cache_dir=str(cache_dir), trust_remote_code=trust_remote_code)
        processor = tokenizer
    if getattr(tokenizer, "pad_token_id", None) is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"
    return processor, tokenizer


def load_model(candidate: dict[str, Any], cache_dir: Path):
    import torch
    from transformers import AutoModelForCausalLM, BitsAndBytesConfig

    quantization_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,
    )
    kwargs = {
        "cache_dir": str(cache_dir),
        "trust_remote_code": bool(candidate.get("trust_remote_code", True)),
        "quantization_config": quantization_config,
        "device_map": "auto",
        "torch_dtype": torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,
    }
    if candidate.get("loader") == "image_text_to_text":
        from transformers import AutoModelForImageTextToText

        return AutoModelForImageTextToText.from_pretrained(candidate["model_id"], **kwargs)
    try:
        return AutoModelForCausalLM.from_pretrained(candidate["model_id"], **kwargs)
    except ImportError as exc:
        if not kwargs["trust_remote_code"]:
            raise
        retry_kwargs = dict(kwargs)
        retry_kwargs["trust_remote_code"] = False
        model = AutoModelForCausalLM.from_pretrained(candidate["model_id"], **retry_kwargs)
        setattr(model, "_sweep_loader_fallback", f"trust_remote_code_false_after_import_error: {exc}")
        return model


def is_linear_like(module: Any) -> bool:
    name = module.__class__.__name__.lower()
    return name in {"linear", "linear4bit", "linear8bitlt"}


def discover_lora_targets(model: Any, preferred: list[str], excluded_fragments: list[str]) -> list[str]:
    available: set[str] = set()
    full_target_names: list[str] = []
    for module_name, module in model.named_modules():
        lower_name = module_name.lower()
        if any(fragment.lower() in lower_name for fragment in excluded_fragments):
            continue
        if "lm_head" in lower_name:
            continue
        if not is_linear_like(module):
            continue
        suffix = module_name.split(".")[-1]
        available.add(suffix)
        parts = module_name.split(".")
        for preferred_name in preferred:
            if suffix == preferred_name or (preferred_name in parts[:-1] and suffix in {"linear", "base_layer"}):
                full_target_names.append(module_name)
                break
    if not full_target_names:
        raise RuntimeError(f"No preferred LoRA target modules found. Available linear suffixes: {sorted(available)[:80]}")
    return sorted(set(full_target_names))


def prepare_datasets(run_config: dict[str, Any], tokenizer: Any) -> tuple[ListDataset, ListDataset, dict[str, Any]]:
    data = run_config["data"]
    train_path = ROOT / data["train_path"]
    val_path = ROOT / data["val_path"]
    manifest_path = ROOT / data["split_manifest_path"]
    train_records = read_jsonl(train_path)
    val_records = read_jsonl(val_path)
    if len(train_records) != int(data["expected_train_records"]):
        raise ValueError(f"Unexpected train count: {len(train_records)}")
    if len(val_records) != int(data["expected_val_records"]):
        raise ValueError(f"Unexpected val count: {len(val_records)}")
    manifest_lookup = load_manifest_metadata(manifest_path)
    max_seq_length = int(data["max_seq_length"])
    train_features, train_summaries = build_features_for_records(
        tokenizer, train_records, max_seq_length=max_seq_length, manifest_lookup=manifest_lookup
    )
    val_features, val_summaries = build_features_for_records(
        tokenizer, val_records, max_seq_length=max_seq_length, manifest_lookup=manifest_lookup
    )
    train_truncated = sum(1 for item in train_summaries if item.was_truncated)
    val_truncated = sum(1 for item in val_summaries if item.was_truncated)
    metadata = {
        "train_path": str(train_path),
        "val_path": str(val_path),
        "manifest_path": str(manifest_path),
        "train_sha256": file_sha256(train_path),
        "val_sha256": file_sha256(val_path),
        "manifest_sha256": file_sha256(manifest_path),
        "train_records": len(train_records),
        "val_records": len(val_records),
        "train_truncated": train_truncated,
        "val_truncated": val_truncated,
        "train_max_tokens": max(item.input_token_count for item in train_summaries),
        "val_max_tokens": max(item.input_token_count for item in val_summaries),
        "train_total_trainable_tokens": sum(item.trainable_token_count for item in train_summaries),
        "val_total_trainable_tokens": sum(item.trainable_token_count for item in val_summaries),
    }
    return ListDataset(train_features), ListDataset(val_features), metadata


def build_training_args(run_config: dict[str, Any], output_dir: Path) -> TrainingArguments:
    import torch

    training = run_config["training"]
    bf16 = bool(torch.cuda.is_available() and torch.cuda.is_bf16_supported())
    fp16 = bool(torch.cuda.is_available() and not bf16)
    return TrainingArguments(
        output_dir=str(output_dir),
        per_device_train_batch_size=int(training["per_device_train_batch_size"]),
        per_device_eval_batch_size=1,
        gradient_accumulation_steps=int(training["gradient_accumulation_steps"]),
        num_train_epochs=float(training["epochs"]),
        learning_rate=float(training["learning_rate"]),
        warmup_ratio=float(training["warmup_ratio"]),
        weight_decay=float(training["weight_decay"]),
        max_grad_norm=float(training["max_grad_norm"]),
        max_steps=int(training.get("max_steps", -1)),
        lr_scheduler_type="linear",
        optim="adamw_8bit",
        logging_steps=1,
        save_strategy="no",
        eval_strategy="no",
        report_to=[],
        bf16=bf16,
        fp16=fp16,
        remove_unused_columns=False,
        seed=int(training["seed"]),
    )


def render_training_log(run_config: dict[str, Any], payload: dict[str, Any]) -> str:
    lines = [
        f"# Sweep Training Run: {run_config['candidate']['key']} / {run_config['run_id']}",
        "",
        f"- Created UTC: `{utc_now()}`",
        f"- Model: `{run_config['candidate']['model_id']}`",
        f"- Loader: `{run_config['candidate']['loader']}`",
        f"- LoRA r/alpha/dropout: `{run_config['training']['lora_r']}/{run_config['training']['lora_alpha']}/{run_config['training']['lora_dropout']}`",
        f"- Learning rate: `{run_config['training']['learning_rate']}`",
        f"- Epochs: `{run_config['training']['epochs']}`",
        f"- Batch/grad accumulation: `{run_config['training']['per_device_train_batch_size']}/{run_config['training']['gradient_accumulation_steps']}`",
        "",
        "## Result",
        "",
        f"- Status: `{payload['status']}`",
        f"- OOM: `{payload.get('oom')}`",
        f"- LoRA targets: `{','.join(payload.get('lora_targets') or [])}`",
        f"- Peak VRAM allocated MiB: `{payload.get('peak_vram_allocated_mib')}`",
        f"- Runtime seconds: `{payload.get('runtime_seconds')}`",
        f"- Train loss: `{(payload.get('train_metrics') or {}).get('train_loss')}`",
        f"- Eval loss: `{(payload.get('eval_metrics') or {}).get('eval_loss')}`",
        "",
        "## Data",
        "",
        "```json",
        json.dumps(payload.get("data_metadata", {}), indent=2, sort_keys=True),
        "```",
        "",
        "## Epoch Snapshots",
        "",
        "```json",
        json.dumps(payload.get("epoch_snapshots", []), indent=2, sort_keys=True),
        "```",
    ]
    if payload.get("error_text_tail"):
        lines.extend(["", "## Error Tail", "", "```text", payload["error_text_tail"], "```"])
    return "\n".join(lines) + "\n"


def preflight_only(run_config: dict[str, Any], model_preflight: bool) -> int:
    cache_dir = ROOT / "cache" / "huggingface"
    _, tokenizer = load_tokenizer_or_processor(run_config["candidate"], cache_dir)
    train_dataset, val_dataset, data_metadata = prepare_datasets(run_config, tokenizer)
    payload: dict[str, Any] = {
        "status": "preflight_ok",
        "created_at_utc": utc_now(),
        "candidate": run_config["candidate"],
        "run_id": run_config["run_id"],
        "train_features": len(train_dataset),
        "val_features": len(val_dataset),
        "data_metadata": data_metadata,
    }
    if model_preflight:
        try:
            from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

            model = load_model(run_config["candidate"], cache_dir)
            targets = discover_lora_targets(
                model, list(run_config["preferred_lora_targets"]), list(run_config["excluded_module_name_fragments"])
            )
            payload["lora_targets"] = targets
            model.config.use_cache = False
            model = prepare_model_for_kbit_training(model)
            peft_model = get_peft_model(
                model,
                LoraConfig(
                    r=int(run_config["training"]["lora_r"]),
                    lora_alpha=int(run_config["training"]["lora_alpha"]),
                    lora_dropout=float(run_config["training"]["lora_dropout"]),
                    bias="none",
                    task_type="CAUSAL_LM",
                    target_modules=targets,
                ),
            )
            trainable_parameters = 0
            total_parameters = 0
            for _, param in peft_model.named_parameters():
                total_parameters += param.numel()
                if param.requires_grad:
                    trainable_parameters += param.numel()
            payload["peft_injection_ok"] = True
            payload["trainable_parameters"] = trainable_parameters
            payload["total_parameters"] = total_parameters
            payload["model_class"] = model.__class__.__name__
            if hasattr(model, "_sweep_loader_fallback"):
                payload["loader_fallback"] = getattr(model, "_sweep_loader_fallback")
            del peft_model
            del model
        except Exception as exc:  # noqa: BLE001
            payload["status"] = "model_preflight_failed"
            payload["error"] = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))[-5000:]
            preflight_path = ROOT / "outputs" / "stage0_preflight" / f"{run_config['candidate']['key']}_{run_config['run_id']}.json"
            write_json(preflight_path, payload)
            print(json.dumps({"status": payload["status"], "preflight": str(preflight_path)}, indent=2), flush=True)
            return 1
    preflight_path = ROOT / "outputs" / "stage0_preflight" / f"{run_config['candidate']['key']}_{run_config['run_id']}.json"
    write_json(preflight_path, payload)
    print(json.dumps({"status": payload["status"], "preflight": str(preflight_path)}, indent=2), flush=True)
    return 0


def train(run_config: dict[str, Any]) -> int:
    import torch
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

    random.seed(int(run_config["training"]["seed"]))
    set_seed(int(run_config["training"]["seed"]))
    cache_dir = ROOT / "cache" / "huggingface"
    output_dir = ROOT / run_config["paths"]["output_dir"]
    adapter_root = ROOT / run_config["paths"]["adapter_root"]
    final_adapter_dir = ROOT / run_config["paths"]["final_adapter_dir"]
    output_dir.mkdir(parents=True, exist_ok=True)
    adapter_root.mkdir(parents=True, exist_ok=True)
    final_adapter_dir.parent.mkdir(parents=True, exist_ok=True)

    _, tokenizer = load_tokenizer_or_processor(run_config["candidate"], cache_dir)
    train_dataset, val_dataset, data_metadata = prepare_datasets(run_config, tokenizer)
    model = load_model(run_config["candidate"], cache_dir)
    model.config.use_cache = False
    if hasattr(model, "gradient_checkpointing_enable"):
        model.gradient_checkpointing_enable()
    model = prepare_model_for_kbit_training(model)
    lora_targets = discover_lora_targets(
        model, list(run_config["preferred_lora_targets"]), list(run_config["excluded_module_name_fragments"])
    )
    lora_config = LoraConfig(
        r=int(run_config["training"]["lora_r"]),
        lora_alpha=int(run_config["training"]["lora_alpha"]),
        lora_dropout=float(run_config["training"]["lora_dropout"]),
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=lora_targets,
    )
    model = get_peft_model(model, lora_config)
    try:
        model.print_trainable_parameters()
    except Exception:
        pass

    snapshot_callback = EpochAdapterSnapshotCallback(
        adapter_root=adapter_root,
        tokenizer=tokenizer,
        run_id=run_config["run_id"],
        expected_epochs=int(math.ceil(float(run_config["training"]["epochs"]))),
    )
    args = build_training_args(run_config, output_dir)
    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        data_collator=SupervisedDataCollator(tokenizer),
        callbacks=[snapshot_callback],
    )

    started = time.time()
    status = "success"
    error_text: str | None = None
    oom = False
    train_metrics: dict[str, Any] = {}
    eval_metrics: dict[str, Any] = {}
    try:
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()
        train_result = trainer.train()
        train_metrics = dict(train_result.metrics)
        if run_config["training"].get("skip_final_eval"):
            eval_metrics = {"skipped": True, "reason": "skip_final_eval"}
        else:
            eval_metrics = dict(trainer.evaluate(eval_dataset=val_dataset))
        model.save_pretrained(str(final_adapter_dir))
        tokenizer.save_pretrained(str(final_adapter_dir))
    except Exception as exc:  # noqa: BLE001
        status = "failure"
        error_text = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        oom = "out of memory" in error_text.lower() or exc.__class__.__name__ == "OutOfMemoryError"
    runtime = round(time.time() - started, 2)
    peak_allocated = None
    peak_reserved = None
    if torch.cuda.is_available():
        peak_allocated = round(torch.cuda.max_memory_allocated() / 1024 / 1024, 2)
        peak_reserved = round(torch.cuda.max_memory_reserved() / 1024 / 1024, 2)
    payload = {
        "status": status,
        "created_at_utc": utc_now(),
        "candidate": run_config["candidate"],
        "run_id": run_config["run_id"],
        "run_config": run_config,
        "data_metadata": data_metadata,
        "lora_targets": lora_targets,
        "epoch_snapshots": snapshot_callback.saved_snapshots,
        "final_adapter_dir": str(final_adapter_dir),
        "output_dir": str(output_dir),
        "train_metrics": train_metrics,
        "eval_metrics": eval_metrics,
        "runtime_seconds": runtime,
        "peak_vram_allocated_mib": peak_allocated,
        "peak_vram_reserved_mib": peak_reserved,
        "oom": oom,
        "error_text_tail": error_text[-5000:] if error_text else None,
    }
    result_path = ROOT / run_config["paths"]["result_json"]
    log_path = ROOT / run_config["paths"]["training_log"]
    write_json(result_path, payload)
    write_text(log_path, render_training_log(run_config, payload))
    print(json.dumps({"status": status, "result": str(result_path), "log": str(log_path), "oom": oom}, indent=2), flush=True)
    return 0 if status == "success" else (88 if oom else 1)


def main() -> int:
    args = parse_args()
    os.environ.setdefault("HF_HOME", str(ROOT / "cache" / "huggingface"))
    run_config = resolve_run_config(args)
    write_json(ROOT / run_config["paths"]["run_config"], run_config)
    if args.preflight_only or args.model_preflight_only:
        return preflight_only(run_config, model_preflight=args.model_preflight_only)
    return train(run_config)


if __name__ == "__main__":
    raise SystemExit(main())
