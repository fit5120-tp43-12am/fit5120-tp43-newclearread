from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import unsloth  # noqa: F401  Keep Unsloth before transformers/peft imports.
from unsloth import FastLanguageModel

from training_data_utils import (
    append_text,
    ensure_tokenizer_padding,
    load_yaml_config,
    local_timestamp,
    markdown_table,
    read_jsonl,
    resolve_project_path,
)

from peft import PeftModel


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run ClearRead smoke adapter inference checks.")
    parser.add_argument("--config", default="configs/smoke_llama31_8b_qlora.yaml")
    parser.add_argument("--adapter-path", default=None)
    parser.add_argument("--num-examples", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def exact_schema_status(text: str) -> tuple[bool, str]:
    try:
        value = json.loads(text.strip())
    except json.JSONDecodeError as exc:
        return False, f"json_parse_error: {exc}"
    if not isinstance(value, dict):
        return False, "not_object"
    if list(value.keys()) != ["main_idea", "key_points"]:
        return False, f"wrong_keys: {list(value.keys())}"
    if not isinstance(value.get("main_idea"), str):
        return False, "main_idea_not_string"
    key_points = value.get("key_points")
    if not isinstance(key_points, list):
        return False, "key_points_not_list"
    if len(key_points) != 4:
        return False, f"key_points_len_{len(key_points)}"
    if not all(isinstance(item, str) for item in key_points):
        return False, "key_points_item_not_string"
    return True, "ok"


def dry_run(root: Path, config_path: Path, config: dict[str, Any], adapter_path: Path) -> int:
    data_path = resolve_project_path(root, config["data"]["smoke_path"])
    records = read_jsonl(data_path)
    requested = int(config.get("inference", {}).get("default_num_examples", 3))
    gold_rows = []
    for index, record in enumerate(records[:requested], start=1):
        assistant = record["messages"][2]["content"]
        ok, reason = exact_schema_status(assistant)
        gold_rows.append([index, ok, reason])
    print(
        {
            "status": "dry_run_ok",
            "config": str(config_path),
            "adapter_path": str(adapter_path),
            "records_available": len(records),
            "gold_schema_checks": gold_rows,
            "note": "No model or adapter was loaded in dry-run mode.",
        }
    )
    return 0


def load_model_with_adapter(config: dict[str, Any], adapter_path: Path):
    model_id = config["model"]["base_model_id"]
    max_seq_length = int(config["data"]["max_seq_length"])
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_id,
        max_seq_length=max_seq_length,
        dtype=None,
        load_in_4bit=bool(config["model"].get("load_in_4bit", True)),
        trust_remote_code=bool(config["model"].get("trust_remote_code", True)),
    )
    ensure_tokenizer_padding(tokenizer)
    model = PeftModel.from_pretrained(model, str(adapter_path))
    FastLanguageModel.for_inference(model)
    return model, tokenizer


def run_inference(root: Path, config: dict[str, Any], adapter_path: Path, num_examples: int) -> int:
    import torch

    data_path = resolve_project_path(root, config["data"]["smoke_path"])
    log_path = resolve_project_path(root, config["outputs"]["smoke_log_path"])
    records = read_jsonl(data_path)
    model, tokenizer = load_model_with_adapter(config, adapter_path)
    inference = config.get("inference", {})
    rows = []

    for index, record in enumerate(records[:num_examples], start=1):
        messages = record["messages"][:2]
        prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        do_sample = bool(inference.get("do_sample", False))
        generate_kwargs = {
            "max_new_tokens": int(inference.get("max_new_tokens", 320)),
            "do_sample": do_sample,
            "pad_token_id": tokenizer.pad_token_id,
            "eos_token_id": tokenizer.eos_token_id,
        }
        if do_sample:
            generate_kwargs["temperature"] = float(inference.get("temperature", 0.7))
        with torch.no_grad():
            output_ids = model.generate(
                **inputs,
                **generate_kwargs,
            )
        new_tokens = output_ids[0][inputs["input_ids"].shape[-1] :]
        decoded = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
        ok, reason = exact_schema_status(decoded)
        rows.append([index, ok, reason, decoded[:160].replace("\n", " ").replace("|", "\\|")])

    pass_count = sum(1 for _, ok, _, _ in rows if ok)
    report = "\n".join(
        [
            "",
            "## Inference Sanity Check",
            "",
            f"Date/time: {local_timestamp()}",
            f"Adapter path: `{adapter_path.as_posix()}`",
            f"Examples checked: `{len(rows)}`",
            f"Schema pass count: `{pass_count}`",
            "",
            markdown_table(["#", "Schema OK", "Reason", "Output Preview"], rows),
            "",
        ]
    )
    append_text(log_path, report)
    print({"status": "ok", "checked": len(rows), "schema_pass": pass_count, "log": str(log_path)})
    return 0 if pass_count == len(rows) else 2


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    config_path = resolve_project_path(root, args.config)
    config = load_yaml_config(config_path)
    adapter_path = resolve_project_path(
        root,
        args.adapter_path or config["outputs"]["adapter_dir"],
    )
    num_examples = args.num_examples or int(config.get("inference", {}).get("default_num_examples", 3))

    if args.dry_run:
        return dry_run(root, config_path, config, adapter_path)
    if not adapter_path.exists():
        raise FileNotFoundError(f"Adapter path does not exist: {adapter_path}")
    return run_inference(root, config, adapter_path, num_examples)


if __name__ == "__main__":
    raise SystemExit(main())
