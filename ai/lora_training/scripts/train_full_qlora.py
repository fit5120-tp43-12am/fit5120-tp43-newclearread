from __future__ import annotations

import argparse
import importlib.metadata as importlib_metadata
import json
import math
import os
import platform
import random
import subprocess
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import unsloth  # noqa: F401  Must be imported before transformers/peft/trl.
from unsloth import FastLanguageModel

from training_data_utils import (
    SupervisedDataCollator,
    append_text,
    build_features_for_records,
    dataset_summary,
    ensure_tokenizer_padding,
    eta_status,
    file_sha256,
    format_duration,
    load_manifest_metadata,
    load_yaml_config,
    local_timestamp,
    markdown_table,
    metadata_for_record,
    read_jsonl,
    resolve_project_path,
    write_text,
)

from transformers import AutoTokenizer, Trainer, TrainerCallback, TrainingArguments, set_seed


@dataclass
class SplitBundle:
    name: str
    path: Path
    expected_records: int
    records: list[dict[str, Any]]
    features: list[dict[str, list[int]]]
    summaries: list[Any]
    metadata: list[Any]
    sha256: str


class ListDataset:
    def __init__(self, features: list[dict[str, list[int]]]) -> None:
        self.features = features

    def __len__(self) -> int:
        return len(self.features)

    def __getitem__(self, index: int) -> dict[str, list[int]]:
        return self.features[index]


class ETAProgressCallback(TrainerCallback):
    def __init__(self, total_steps: int, print_every_steps: int = 5) -> None:
        self.total_steps = max(1, total_steps)
        self.print_every_steps = max(1, print_every_steps)
        self.start_time: float | None = None
        self.last_printed_step = -1
        self.records: list[dict[str, Any]] = []

    def on_train_begin(self, args, state, control, **kwargs):  # type: ignore[override]
        self.start_time = time.time()
        if getattr(state, "max_steps", 0):
            self.total_steps = int(state.max_steps)

    def on_step_end(self, args, state, control, **kwargs):  # type: ignore[override]
        if self.start_time is None:
            self.start_time = time.time()
        step = int(state.global_step)
        should_print = (
            step > 0
            and step != self.last_printed_step
            and (step % self.print_every_steps == 0 or step == self.total_steps)
        )
        if not should_print:
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
    parser = argparse.ArgumentParser(description="Run or dry-run ClearRead full Candidate A QLoRA training.")
    parser.add_argument("--config", default="configs/train_llama31_8b_qlora_candidate_a.example.yaml")
    parser.add_argument("--dry-run", action="store_true", help="Validate train/val tokenization without training.")
    parser.add_argument("--model-id", default=None, help="Override configured base model id.")
    return parser.parse_args()


def configured_model_ids(config: dict[str, Any], override: str | None) -> list[str]:
    if override:
        return [override]
    model = config["model"]
    return [model["base_model_id"], *model.get("fallback_model_ids", [])]


def load_tokenizer_only(model_ids: Sequence[str], trust_remote_code: bool):
    last_error: Exception | None = None
    for model_id in model_ids:
        try:
            tokenizer = AutoTokenizer.from_pretrained(
                model_id,
                use_fast=True,
                trust_remote_code=trust_remote_code,
            )
            ensure_tokenizer_padding(tokenizer)
            return model_id, tokenizer
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            print(f"Tokenizer load failed for {model_id}: {exc}", flush=True)
    raise RuntimeError(f"All configured tokenizer loads failed. Last error: {last_error}") from last_error


def load_unsloth_model_and_tokenizer(model_ids: Sequence[str], config: dict[str, Any], max_seq_length: int):
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


def torch_precision_flags(config: dict[str, Any]) -> tuple[bool, bool]:
    import torch

    bf16_config = config["training"].get("bf16", "auto")
    fp16_config = config["training"].get("fp16", "auto")
    bf16_supported = bool(torch.cuda.is_available() and torch.cuda.is_bf16_supported())
    if bf16_config == "auto":
        bf16 = bf16_supported
    else:
        bf16 = bool(bf16_config)
    if fp16_config == "auto":
        fp16 = bool(torch.cuda.is_available() and not bf16)
    else:
        fp16 = bool(fp16_config)
    return bf16, fp16


def package_version(name: str) -> str:
    try:
        return importlib_metadata.version(name)
    except importlib_metadata.PackageNotFoundError:
        return "not_installed"


def environment_summary() -> dict[str, Any]:
    import torch

    gpu_name = "no_cuda"
    gpu_vram = "0 MiB"
    bf16 = False
    if torch.cuda.is_available():
        props = torch.cuda.get_device_properties(0)
        gpu_name = props.name
        gpu_vram = f"{round(props.total_memory / 1024 / 1024)} MiB"
        bf16 = bool(torch.cuda.is_bf16_supported())
    packages = {
        "torch": getattr(torch, "__version__", "unknown"),
        "transformers": package_version("transformers"),
        "datasets": package_version("datasets"),
        "accelerate": package_version("accelerate"),
        "peft": package_version("peft"),
        "trl": package_version("trl"),
        "bitsandbytes": package_version("bitsandbytes"),
        "unsloth": package_version("unsloth"),
        "huggingface_hub": package_version("huggingface_hub"),
        "safetensors": package_version("safetensors"),
        "sentencepiece": package_version("sentencepiece"),
    }
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "conda_env": os.environ.get("CONDA_DEFAULT_ENV", "unknown"),
        "gpu_name": gpu_name,
        "gpu_vram": gpu_vram,
        "bf16_supported": bf16,
        "packages": packages,
    }


def git_info(config: dict[str, Any]) -> dict[str, str]:
    repo_path = config.get("git", {}).get("team_repo_path")
    if not repo_path:
        return {"repo": "not_configured", "branch": "unknown", "commit": "unknown"}
    repo = Path(repo_path)
    if not repo.exists():
        return {"repo": str(repo), "branch": "missing", "commit": "missing"}

    def run_git(args: list[str]) -> str:
        completed = subprocess.run(
            ["git", *args],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout.strip()

    try:
        return {
            "repo": str(repo),
            "branch": run_git(["rev-parse", "--abbrev-ref", "HEAD"]),
            "commit": run_git(["rev-parse", "HEAD"]),
        }
    except Exception as exc:  # noqa: BLE001
        return {"repo": str(repo), "branch": "git_error", "commit": str(exc)}


def expected_total_steps(records: int, config: dict[str, Any]) -> int:
    training = config["training"]
    per_device = int(training["per_device_train_batch_size"])
    accumulation = int(training["gradient_accumulation_steps"])
    epochs = float(training["num_train_epochs"])
    steps_per_epoch = math.ceil(records / max(1, per_device * accumulation))
    return int(math.ceil(steps_per_epoch * epochs))


def split_paths(root: Path, config: dict[str, Any]) -> tuple[Path, Path, Path]:
    data = config["data"]
    return (
        resolve_project_path(root, data["train_path"]),
        resolve_project_path(root, data["val_path"]),
        resolve_project_path(root, data["split_manifest_path"]),
    )


def prepare_split(
    *,
    name: str,
    path: Path,
    expected_records: int,
    tokenizer,
    max_seq_length: int,
    manifest_lookup: dict[str, Any],
) -> SplitBundle:
    records = read_jsonl(path)
    metadata = [metadata_for_record(record, index, manifest_lookup) for index, record in enumerate(records)]
    features, summaries = build_features_for_records(
        tokenizer,
        records,
        max_seq_length=max_seq_length,
        manifest_lookup=manifest_lookup,
    )
    return SplitBundle(
        name=name,
        path=path,
        expected_records=expected_records,
        records=records,
        features=features,
        summaries=summaries,
        metadata=metadata,
        sha256=file_sha256(path),
    )


def split_stats(bundle: SplitBundle) -> dict[str, Any]:
    errors: list[str] = []
    for summary in bundle.summaries:
        prefix = f"{summary.record_id}"
        if summary.trainable_token_count <= 0:
            errors.append(f"{prefix}: no trainable assistant tokens")
        if summary.prompt_token_count <= 0:
            errors.append(f"{prefix}: no masked prompt tokens")
        if not summary.assistant_json_ok:
            errors.append(f"{prefix}: source assistant text is not valid JSON")
        if not summary.decoded_trainable_json_ok:
            errors.append(f"{prefix}: decoded trainable text is not valid JSON")
    ok = not errors
    metadata_summary = dataset_summary(bundle.records, bundle.metadata)
    zero_trainable = [summary for summary in bundle.summaries if summary.trainable_token_count <= 0]
    truncated_pairs = [
        (summary, metadata)
        for summary, metadata in zip(bundle.summaries, bundle.metadata)
        if summary.was_truncated
    ]
    truncated_by_domain: dict[str, int] = {}
    truncated_by_bucket: dict[str, int] = {}
    for _, metadata in truncated_pairs:
        domain = metadata.domain or "unknown"
        bucket = metadata.natural_length_bucket or "unknown"
        truncated_by_domain[domain] = truncated_by_domain.get(domain, 0) + 1
        truncated_by_bucket[bucket] = truncated_by_bucket.get(bucket, 0) + 1
    decoded_ok = sum(1 for summary in bundle.summaries if summary.decoded_trainable_json_ok)
    decoded_matches = sum(1 for summary in bundle.summaries if summary.decoded_matches_assistant_json)
    truncated_count = len(truncated_pairs)
    truncation_pct = (truncated_count / len(bundle.summaries) * 100.0) if bundle.summaries else 0.0
    return {
        "ok": ok,
        "errors": errors,
        "record_count": len(bundle.records),
        "expected_records": bundle.expected_records,
        "sha256": bundle.sha256,
        "max_input_tokens": max(summary.input_token_count for summary in bundle.summaries),
        "max_trainable_tokens": max(summary.trainable_token_count for summary in bundle.summaries),
        "total_trainable_tokens": sum(summary.trainable_token_count for summary in bundle.summaries),
        "non_empty_trainable": len(bundle.summaries) - len(zero_trainable),
        "zero_trainable": len(zero_trainable),
        "decoded_json_ok": decoded_ok,
        "decoded_matches_assistant_json": decoded_matches,
        "truncated_records": truncated_count,
        "truncation_pct": truncation_pct,
        "truncated_by_domain": dict(sorted(truncated_by_domain.items())),
        "truncated_by_bucket": dict(sorted(truncated_by_bucket.items())),
        "domains": metadata_summary["domains"],
        "natural_length_buckets": metadata_summary["natural_length_buckets"],
    }


def preflight_gate(
    train_stats: dict[str, Any],
    val_stats: dict[str, Any],
    threshold_percent: float,
) -> tuple[bool, list[str]]:
    blockers: list[str] = []
    for name, stats in [("train", train_stats), ("validation", val_stats)]:
        if stats["record_count"] != stats["expected_records"]:
            blockers.append(
                f"{name}: expected {stats['expected_records']} records, found {stats['record_count']}"
            )
        if stats["zero_trainable"] > 0:
            blockers.append(f"{name}: {stats['zero_trainable']} records have zero trainable assistant tokens")
        if stats["truncation_pct"] > threshold_percent:
            blockers.append(
                f"{name}: truncation {stats['truncated_records']}/{stats['record_count']} "
                f"({stats['truncation_pct']:.2f}%) exceeds {threshold_percent:.2f}%"
            )
        if stats["decoded_json_ok"] != stats["record_count"]:
            blockers.append(
                f"{name}: decoded trainable labels parse as JSON for "
                f"{stats['decoded_json_ok']}/{stats['record_count']} records"
            )
        for error in stats["errors"][:10]:
            blockers.append(f"{name}: {error}")
    return not blockers, blockers


def preflight_bundle(root: Path, config: dict[str, Any], tokenizer) -> tuple[SplitBundle, SplitBundle, Path]:
    train_path, val_path, manifest_path = split_paths(root, config)
    manifest_lookup = load_manifest_metadata(manifest_path)
    train_bundle = prepare_split(
        name="train",
        path=train_path,
        expected_records=int(config["data"]["expected_train_records"]),
        tokenizer=tokenizer,
        max_seq_length=int(config["data"]["max_seq_length"]),
        manifest_lookup=manifest_lookup,
    )
    val_bundle = prepare_split(
        name="validation",
        path=val_path,
        expected_records=int(config["data"]["expected_val_records"]),
        tokenizer=tokenizer,
        max_seq_length=int(config["data"]["max_seq_length"]),
        manifest_lookup=manifest_lookup,
    )
    return train_bundle, val_bundle, manifest_path


def sample_rows(bundle: SplitBundle, sample_size: int) -> list[list[Any]]:
    rows = []
    for summary in bundle.summaries[:sample_size]:
        rows.append(
            [
                summary.index + 1,
                summary.record_id,
                summary.stable_hash[:12],
                summary.input_token_count,
                summary.trainable_token_count,
                summary.was_truncated,
                summary.decoded_trainable_json_ok,
                summary.decoded_matches_assistant_json,
                summary.decoded_trainable_preview.replace("|", "\\|"),
            ]
        )
    return rows


def render_preflight_section(
    *,
    config_path: Path,
    model_id: str,
    train_bundle: SplitBundle,
    val_bundle: SplitBundle,
    manifest_path: Path,
    train_stats: dict[str, Any],
    val_stats: dict[str, Any],
    gate_ok: bool,
    blockers: list[str],
    sample_size: int,
) -> str:
    summary_rows = [
        [
            "train",
            train_stats["record_count"],
            train_stats["expected_records"],
            train_stats["sha256"],
            train_stats["max_input_tokens"],
            train_stats["max_trainable_tokens"],
            train_stats["total_trainable_tokens"],
            train_stats["truncated_records"],
            f"{train_stats['truncation_pct']:.2f}%",
            train_stats["non_empty_trainable"],
            train_stats["decoded_json_ok"],
            train_stats["decoded_matches_assistant_json"],
        ],
        [
            "validation",
            val_stats["record_count"],
            val_stats["expected_records"],
            val_stats["sha256"],
            val_stats["max_input_tokens"],
            val_stats["max_trainable_tokens"],
            val_stats["total_trainable_tokens"],
            val_stats["truncated_records"],
            f"{val_stats['truncation_pct']:.2f}%",
            val_stats["non_empty_trainable"],
            val_stats["decoded_json_ok"],
            val_stats["decoded_matches_assistant_json"],
        ],
    ]
    blocker_lines = ["- None"] if not blockers else [f"- {item}" for item in blockers]
    return "\n".join(
        [
            "## Preflight Tokenization Gate",
            "",
            f"- Config: `{config_path.as_posix()}`",
            f"- Tokenizer model id: `{model_id}`",
            f"- Train data: `{train_bundle.path.as_posix()}`",
            f"- Validation data: `{val_bundle.path.as_posix()}`",
            f"- Split manifest: `{manifest_path.as_posix()}`",
            f"- Split manifest SHA256: `{file_sha256(manifest_path)}`",
            "",
            markdown_table(
                [
                    "Split",
                    "Records",
                    "Expected",
                    "SHA256",
                    "Max Input Tokens",
                    "Max Assistant Tokens",
                    "Total Assistant Tokens",
                    "Truncated",
                    "Trunc %",
                    "Non-Empty Labels",
                    "JSON OK",
                    "Matches Gold JSON",
                ],
                summary_rows,
            ),
            "",
            "### Train Decoded Label Samples",
            "",
            markdown_table(
                [
                    "#",
                    "Record ID",
                    "Stable Hash",
                    "Input Tokens",
                    "Assistant Tokens",
                    "Truncated",
                    "JSON OK",
                    "Matches Gold",
                    "Preview",
                ],
                sample_rows(train_bundle, sample_size),
            ),
            "",
            "### Validation Decoded Label Samples",
            "",
            markdown_table(
                [
                    "#",
                    "Record ID",
                    "Stable Hash",
                    "Input Tokens",
                    "Assistant Tokens",
                    "Truncated",
                    "JSON OK",
                    "Matches Gold",
                    "Preview",
                ],
                sample_rows(val_bundle, sample_size),
            ),
            "",
            "### Truncation Detail",
            "",
            f"- Train truncated by domain: `{json.dumps(train_stats['truncated_by_domain'], sort_keys=True)}`",
            f"- Train truncated by length bucket: `{json.dumps(train_stats['truncated_by_bucket'], sort_keys=True)}`",
            f"- Validation truncated by domain: `{json.dumps(val_stats['truncated_by_domain'], sort_keys=True)}`",
            f"- Validation truncated by length bucket: `{json.dumps(val_stats['truncated_by_bucket'], sort_keys=True)}`",
            "",
            "### Gate Result",
            "",
            f"- Gate passed: `{gate_ok}`",
            "- Blockers:",
            *blocker_lines,
            "",
        ]
    )


def render_environment_section(config: dict[str, Any]) -> str:
    env = environment_summary()
    package_rows = [[name, version] for name, version in env["packages"].items()]
    git = git_info(config)
    return "\n".join(
        [
            "## Environment",
            "",
            f"- Git repo: `{git['repo']}`",
            f"- Git branch before run: `{git['branch']}`",
            f"- Git commit before run: `{git['commit']}`",
            f"- Python: `{env['python']}`",
            f"- Platform: `{env['platform']}`",
            f"- Conda env: `{env['conda_env']}`",
            f"- GPU: `{env['gpu_name']}`",
            f"- VRAM: `{env['gpu_vram']}`",
            f"- BF16 supported: `{env['bf16_supported']}`",
            "",
            markdown_table(["Package", "Version"], package_rows),
            "",
        ]
    )


def render_config_section(config: dict[str, Any], command: str) -> str:
    training = config["training"]
    lora = config["lora"]
    return "\n".join(
        [
            "## Commands And Config",
            "",
            f"- Command: `{command}`",
            f"- Max sequence length: `{config['data']['max_seq_length']}`",
            f"- QLoRA: `4-bit NF4`",
            f"- LoRA r/alpha/dropout: `{lora['r']} / {lora['alpha']} / {lora['dropout']}`",
            f"- Target modules: `{','.join(lora['target_modules'])}`",
            f"- Per-device train batch size: `{training['per_device_train_batch_size']}`",
            f"- Gradient accumulation steps: `{training['gradient_accumulation_steps']}`",
            f"- Effective train batch size: `{training['effective_batch_size']}`",
            f"- Epochs: `{training['num_train_epochs']}`",
            f"- Learning rate: `{training['learning_rate']}`",
            f"- Warmup ratio: `{training.get('warmup_ratio', 'n/a')}`",
            f"- Optimizer: `{training['optim']}`",
            f"- Scheduler: `{training['lr_scheduler_type']}`",
            f"- Seed: `{training['seed']}`",
            f"- Assistant-only loss masking: `enabled`",
            f"- Save strategy: `{training.get('save_strategy', 'no')}`",
            f"- Validation loss: `computed once after training with trainer.evaluate(eval_dataset=validation)`",
            "",
        ]
    )


def resolve_adapter_dir(root: Path, config: dict[str, Any]) -> Path:
    base_dir = resolve_project_path(root, config["outputs"]["adapter_dir"])
    if base_dir.exists() and any(base_dir.iterdir()):
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        return base_dir.with_name(f"{base_dir.name}_{timestamp}")
    return base_dir


def adapter_rows(adapter_dir: Path) -> list[list[Any]]:
    rows = []
    if not adapter_dir.exists():
        return [["missing", 0, "missing"]]
    for path in sorted(item for item in adapter_dir.iterdir() if item.is_file()):
        size = path.stat().st_size
        digest = file_sha256(path) if size <= 2 * 1024 * 1024 else "not recorded (large local artifact)"
        rows.append([path.name, size, digest])
    return rows


def loss_rows(log_history: Sequence[dict[str, Any]]) -> list[list[Any]]:
    rows = []
    for item in log_history:
        if "loss" in item:
            rows.append(
                [
                    item.get("step", "n/a"),
                    item.get("epoch", "n/a"),
                    item.get("loss", "n/a"),
                    item.get("learning_rate", "n/a"),
                ]
            )
    if len(rows) <= 12:
        return rows or [["n/a", "n/a", "n/a", "n/a"]]
    return [*rows[:3], ["...", "...", "...", "..."], *rows[-8:]]


def progress_rows(records: Sequence[dict[str, Any]]) -> list[list[Any]]:
    rows = [
        [
            item["current_step"],
            item["total_steps"],
            item["elapsed"],
            item["average_seconds_per_step"],
            item["estimated_remaining"],
            item["estimated_completion_time"],
        ]
        for item in records[-15:]
    ]
    return rows or [["n/a", "n/a", "n/a", "n/a", "n/a", "n/a"]]


def render_training_result_section(
    *,
    result_status: str,
    model_id: str,
    adapter_dir: Path,
    output_dir: Path,
    start_time: str,
    end_time: str,
    elapsed_seconds: float,
    progress_records: Sequence[dict[str, Any]],
    train_metrics: dict[str, Any],
    eval_metrics: dict[str, Any],
    log_history: Sequence[dict[str, Any]],
    oom: bool,
    error_text: str | None = None,
) -> str:
    avg_seconds = progress_records[-1]["average_seconds_per_step"] if progress_records else "n/a"
    final_loss = train_metrics.get("train_loss", "n/a")
    validation_loss = eval_metrics.get("eval_loss", "n/a")
    lines = [
        "## Training Result",
        "",
        f"- Status: `{result_status}`",
        f"- Model id actually used: `{model_id}`",
        f"- Start time: `{start_time}`",
        f"- End time: `{end_time}`",
        f"- Elapsed runtime: `{format_duration(elapsed_seconds)}` ({elapsed_seconds:.2f} seconds)",
        f"- Output/checkpoint path: `{output_dir.as_posix()}`",
        f"- Adapter output path: `{adapter_dir.as_posix()}`",
        f"- OOM: `{'yes' if oom else 'no'}`",
        f"- Final train loss: `{final_loss}`",
        f"- Validation loss: `{validation_loss}`",
        f"- Average seconds per step at final progress sample: `{avg_seconds}`",
        "",
        "### Progress Samples",
        "",
        markdown_table(
            ["Step", "Total", "Elapsed", "Avg Sec/Step", "Remaining", "ETA"],
            progress_rows(progress_records),
        ),
        "",
        "### Train Loss Trend",
        "",
        markdown_table(["Step", "Epoch", "Loss", "Learning Rate"], loss_rows(log_history)),
        "",
        "### Trainer Metrics",
        "",
        "```json",
        json.dumps({"train": train_metrics, "validation": eval_metrics}, indent=2, sort_keys=True),
        "```",
        "",
        "### Adapter Files",
        "",
        markdown_table(["File", "Size bytes", "SHA256"], adapter_rows(adapter_dir)),
        "",
        "### ETA Accuracy Note",
        "",
        "The ETA callback used average observed seconds per completed optimizer step. Early estimates included warmup/cache effects and stabilized after several progress samples.",
        "",
    ]
    if error_text:
        lines.extend(["### Error", "", "```text", error_text[-4000:], "```", ""])
    return "\n".join(lines)


def write_preflight_log(
    *,
    root: Path,
    config_path: Path,
    config: dict[str, Any],
    model_id: str,
    train_bundle: SplitBundle,
    val_bundle: SplitBundle,
    manifest_path: Path,
    train_stats: dict[str, Any],
    val_stats: dict[str, Any],
    gate_ok: bool,
    blockers: list[str],
    command: str,
) -> None:
    log_path = resolve_project_path(root, config["outputs"]["training_log_path"])
    sample_size = int(config.get("preflight", {}).get("decoded_json_sample_size", 5))
    text = "\n".join(
        [
            "# Full Training Candidate A 3 Epoch",
            "",
            f"Date/time: {local_timestamp()}",
            "Stage id: `Stage 006`",
            "",
            render_environment_section(config),
            render_config_section(config, command),
            render_preflight_section(
                config_path=config_path,
                model_id=model_id,
                train_bundle=train_bundle,
                val_bundle=val_bundle,
                manifest_path=manifest_path,
                train_stats=train_stats,
                val_stats=val_stats,
                gate_ok=gate_ok,
                blockers=blockers,
                sample_size=sample_size,
            ),
            "## Decision",
            "",
            "- Dry-run preflight completed. Training may proceed only if the gate passed.",
            "",
        ]
    )
    write_text(log_path, text)


def training_command(config_path: Path, dry_run: bool) -> str:
    suffix = " --dry-run" if dry_run else ""
    return f"python scripts/train_full_qlora.py --config {config_path.as_posix()}{suffix}"


def run_preflight(root: Path, config_path: Path, config: dict[str, Any], model_ids: list[str], dry_run: bool) -> tuple[bool, dict[str, Any]]:
    model_id, tokenizer = load_tokenizer_only(model_ids, bool(config["model"].get("trust_remote_code", True)))
    train_bundle, val_bundle, manifest_path = preflight_bundle(root, config, tokenizer)
    train_stats = split_stats(train_bundle)
    val_stats = split_stats(val_bundle)
    gate_ok, blockers = preflight_gate(
        train_stats,
        val_stats,
        float(config.get("preflight", {}).get("truncation_stop_threshold_percent", 2.0)),
    )
    write_preflight_log(
        root=root,
        config_path=config_path,
        config=config,
        model_id=model_id,
        train_bundle=train_bundle,
        val_bundle=val_bundle,
        manifest_path=manifest_path,
        train_stats=train_stats,
        val_stats=val_stats,
        gate_ok=gate_ok,
        blockers=blockers,
        command=training_command(config_path, dry_run=dry_run),
    )
    print(
        {
            "status": "preflight_ok" if gate_ok else "preflight_blocked",
            "config": str(config_path),
            "model_tokenizer": model_id,
            "train_records": train_stats["record_count"],
            "val_records": val_stats["record_count"],
            "split_manifest_sha256": file_sha256(manifest_path),
            "train_sha256": train_stats["sha256"],
            "val_sha256": val_stats["sha256"],
            "train_max_input_tokens": train_stats["max_input_tokens"],
            "val_max_input_tokens": val_stats["max_input_tokens"],
            "train_truncated_records": train_stats["truncated_records"],
            "val_truncated_records": val_stats["truncated_records"],
            "total_trainable_assistant_tokens": train_stats["total_trainable_tokens"] + val_stats["total_trainable_tokens"],
            "blockers": blockers,
        }
    )
    return gate_ok, {
        "model_id": model_id,
        "train_bundle": train_bundle,
        "val_bundle": val_bundle,
        "manifest_path": manifest_path,
        "train_stats": train_stats,
        "val_stats": val_stats,
        "blockers": blockers,
    }


def build_training_args(root: Path, config: dict[str, Any], output_dir: Path) -> TrainingArguments:
    training = config["training"]
    bf16, fp16 = torch_precision_flags(config)
    kwargs: dict[str, Any] = {
        "output_dir": str(output_dir),
        "per_device_train_batch_size": int(training["per_device_train_batch_size"]),
        "gradient_accumulation_steps": int(training["gradient_accumulation_steps"]),
        "num_train_epochs": float(training["num_train_epochs"]),
        "learning_rate": float(training["learning_rate"]),
        "weight_decay": float(training.get("weight_decay", 0.0)),
        "lr_scheduler_type": str(training.get("lr_scheduler_type", "linear")),
        "optim": str(training.get("optim", "adamw_8bit")),
        "logging_steps": int(training.get("logging_steps", 1)),
        "save_strategy": str(training.get("save_strategy", "no")),
        "eval_strategy": str(training.get("eval_strategy", "no")),
        "report_to": list(training.get("report_to", [])),
        "bf16": bf16,
        "fp16": fp16,
        "remove_unused_columns": False,
        "seed": int(training.get("seed", 5120)),
    }
    if "warmup_ratio" in training:
        kwargs["warmup_ratio"] = float(training["warmup_ratio"])
    else:
        kwargs["warmup_steps"] = int(training.get("warmup_steps", 0))
    return TrainingArguments(**kwargs)


def run_dry_run(root: Path, config_path: Path, config: dict[str, Any], model_ids: list[str]) -> int:
    gate_ok, _ = run_preflight(root, config_path, config, model_ids, dry_run=True)
    return 0 if gate_ok else 2


def run_training(root: Path, config_path: Path, config: dict[str, Any], model_ids: list[str]) -> int:
    import torch

    seed = int(config["training"].get("seed", 5120))
    random.seed(seed)
    set_seed(seed)

    max_seq_length = int(config["data"]["max_seq_length"])
    model_id, model, tokenizer = load_unsloth_model_and_tokenizer(model_ids, config, max_seq_length)
    train_bundle, val_bundle, manifest_path = preflight_bundle(root, config, tokenizer)
    train_stats = split_stats(train_bundle)
    val_stats = split_stats(val_bundle)
    gate_ok, blockers = preflight_gate(
        train_stats,
        val_stats,
        float(config.get("preflight", {}).get("truncation_stop_threshold_percent", 2.0)),
    )
    if not gate_ok:
        write_preflight_log(
            root=root,
            config_path=config_path,
            config=config,
            model_id=model_id,
            train_bundle=train_bundle,
            val_bundle=val_bundle,
            manifest_path=manifest_path,
            train_stats=train_stats,
            val_stats=val_stats,
            gate_ok=gate_ok,
            blockers=blockers,
            command=training_command(config_path, dry_run=False),
        )
        print({"status": "training_blocked_by_preflight", "blockers": blockers})
        return 2

    model = apply_lora(model, config)
    output_dir = resolve_project_path(root, config["outputs"]["output_dir"])
    adapter_dir = resolve_adapter_dir(root, config)
    log_path = resolve_project_path(root, config["outputs"]["training_log_path"])
    output_dir.mkdir(parents=True, exist_ok=True)
    adapter_dir.parent.mkdir(parents=True, exist_ok=True)

    progress_callback = ETAProgressCallback(
        total_steps=expected_total_steps(len(train_bundle.records), config),
        print_every_steps=int(config.get("progress", {}).get("print_every_steps", 5)),
    )
    args = build_training_args(root, config, output_dir)
    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=ListDataset(train_bundle.features),
        eval_dataset=ListDataset(val_bundle.features),
        data_collator=SupervisedDataCollator(tokenizer),
        callbacks=[progress_callback],
    )

    start_timestamp = local_timestamp()
    start = time.time()
    train_metrics: dict[str, Any] = {}
    eval_metrics: dict[str, Any] = {}
    result_status = "success"
    oom = False
    error_text: str | None = None
    try:
        train_result = trainer.train()
        train_metrics = dict(train_result.metrics)
        if bool(config["training"].get("eval_after_training", True)):
            eval_metrics = dict(trainer.evaluate(eval_dataset=ListDataset(val_bundle.features)))
        model.save_pretrained(str(adapter_dir))
        tokenizer.save_pretrained(str(adapter_dir))
    except Exception as exc:  # noqa: BLE001
        result_status = "failure"
        error_text = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        oom = isinstance(exc, torch.cuda.OutOfMemoryError) or "out of memory" in str(exc).lower()
        raise
    finally:
        end_timestamp = local_timestamp()
        elapsed = time.time() - start
        sample_size = int(config.get("preflight", {}).get("decoded_json_sample_size", 5))
        text = "\n".join(
            [
                "# Full Training Candidate A 3 Epoch",
                "",
                f"Date/time: {local_timestamp()}",
                "Stage id: `Stage 006`",
                "",
                render_environment_section(config),
                render_config_section(config, training_command(config_path, dry_run=False)),
                render_preflight_section(
                    config_path=config_path,
                    model_id=model_id,
                    train_bundle=train_bundle,
                    val_bundle=val_bundle,
                    manifest_path=manifest_path,
                    train_stats=train_stats,
                    val_stats=val_stats,
                    gate_ok=gate_ok,
                    blockers=blockers,
                    sample_size=sample_size,
                ),
                render_training_result_section(
                    result_status=result_status,
                    model_id=model_id,
                    adapter_dir=adapter_dir,
                    output_dir=output_dir,
                    start_time=start_timestamp,
                    end_time=end_timestamp,
                    elapsed_seconds=elapsed,
                    progress_records=progress_callback.records,
                    train_metrics=train_metrics,
                    eval_metrics=eval_metrics,
                    log_history=trainer.state.log_history,
                    oom=oom,
                    error_text=error_text,
                ),
                "## Validation Inference",
                "",
                "Pending. Run `python scripts/run_inference_check.py --config configs/train_llama31_8b_qlora_candidate_a.example.yaml --adapter-path "
                f"{adapter_dir.as_posix()} --data-path data/splits/val.jsonl --num-examples 10`.",
                "",
                "## Decision",
                "",
                "- Candidate A training completed and requires validation inference sanity checks before model-selection review."
                if result_status == "success"
                else "- Candidate A training failed; see error details above.",
                "",
            ]
        )
        write_text(log_path, text)

    print(
        {
            "status": result_status,
            "adapter_dir": str(adapter_dir),
            "training_log": str(log_path),
            "train_loss": train_metrics.get("train_loss"),
            "eval_loss": eval_metrics.get("eval_loss"),
        }
    )
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
