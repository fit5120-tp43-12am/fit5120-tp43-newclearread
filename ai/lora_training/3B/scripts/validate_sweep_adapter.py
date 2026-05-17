from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

from sweep_utils import ROOT, parse_candidate_output, read_json, read_jsonl, summarize_parse_results, utc_now, write_json
from train_sweep_qlora import candidate_lookup, load_model, load_tokenizer_or_processor


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a sweep adapter on the 145-item validation split.")
    parser.add_argument("--candidate-key", required=True)
    parser.add_argument("--train-run-id", required=True)
    parser.add_argument("--epoch", type=int, required=True)
    parser.add_argument("--validation-run-id", default=None)
    parser.add_argument("--prompt-mode", choices=["record_messages", "gentle_schema_guard"], default="record_messages")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--allow-overwrite", action="store_true")
    return parser.parse_args()


def apply_chat_template(tokenizer: Any, messages: list[dict[str, str]]) -> str:
    if hasattr(tokenizer, "apply_chat_template"):
        try:
            return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        except TypeError:
            return tokenizer.apply_chat_template(messages, tokenize=False)
    return "\n\n".join(f"{item['role'].upper()}:\n{item['content']}" for item in messages) + "\n\nASSISTANT:\n"


def messages_for_record(record: dict[str, Any], prompt_mode: str) -> list[dict[str, str]]:
    messages = record["messages"][:2]
    if prompt_mode == "gentle_schema_guard":
        guard = (
            "\n\nReturn only one JSON object with exactly these keys in this order: "
            '{"main_idea":"...","key_points":["...","...","...","..."]}. '
            "The main_idea must be exactly two sentences. Each key point must be one sentence."
        )
        messages = [dict(item) for item in messages]
        messages[-1]["content"] = messages[-1]["content"].rstrip() + guard
    return messages


def tensor_device(model: Any):
    for param in model.parameters():
        return param.device
    return "cuda"


def generate_one(model: Any, processor_or_tokenizer: Any, prompt_text: str, max_new_tokens: int = 320) -> tuple[str, dict[str, Any]]:
    import torch

    device = tensor_device(model)
    encoded = processor_or_tokenizer(prompt_text, return_tensors="pt")
    inputs = {key: value.to(device) if hasattr(value, "to") else value for key, value in encoded.items()}
    input_len = int(inputs["input_ids"].shape[-1])
    started = time.perf_counter()
    with torch.no_grad():
        generation_config = getattr(model, "generation_config", None)
        if generation_config is not None and getattr(generation_config, "max_length", None) is not None:
            generation_config.max_length = None
        generated = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            temperature=None,
            top_p=None,
            pad_token_id=getattr(processor_or_tokenizer, "pad_token_id", None)
            or getattr(getattr(processor_or_tokenizer, "tokenizer", None), "pad_token_id", None),
        )
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    output_ids = generated[0][input_len:]
    tokenizer = getattr(processor_or_tokenizer, "tokenizer", processor_or_tokenizer)
    raw = tokenizer.decode(output_ids, skip_special_tokens=True).strip()
    return raw, {"input_tokens": input_len, "output_tokens": int(output_ids.shape[-1]), "latency_ms": elapsed_ms}


def main() -> int:
    args = parse_args()
    os.environ.setdefault("HF_HOME", str(ROOT / "cache" / "huggingface"))
    sweep = read_json(ROOT / "configs" / "sweep_candidates.json")
    candidate = candidate_lookup(sweep, args.candidate_key)
    validation_run_id = args.validation_run_id or f"{args.train_run_id}_epoch_{args.epoch}_{args.prompt_mode}"
    out_dir = ROOT / "model_workspaces" / args.candidate_key / "outputs" / "validation" / validation_run_id
    if out_dir.exists() and any(out_dir.iterdir()) and not args.allow_overwrite:
        raise SystemExit(f"Refusing to overwrite existing validation dir: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)

    adapter_dir = ROOT / "model_workspaces" / args.candidate_key / "models" / "adapters" / f"{args.train_run_id}_epoch_{args.epoch}"
    if not adapter_dir.exists():
        raise FileNotFoundError(f"Adapter snapshot not found: {adapter_dir}")

    from peft import PeftModel

    _, tokenizer = load_tokenizer_or_processor(candidate, ROOT / "cache" / "huggingface")
    model = load_model(candidate, ROOT / "cache" / "huggingface")
    model = PeftModel.from_pretrained(model, str(adapter_dir))
    model.eval()

    records = read_jsonl(ROOT / sweep["data"]["val_path"])
    if args.limit:
        records = records[: args.limit]

    raw_rows: list[dict[str, Any]] = []
    parsed_rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    latency: list[int] = []
    output_tokens: list[int] = []
    input_tokens: list[int] = []

    raw_path = out_dir / "raw_outputs.jsonl"
    parsed_path = out_dir / "parsed_outputs.jsonl"
    failure_path = out_dir / "parse_failures.jsonl"
    with raw_path.open("w", encoding="utf-8", newline="\n") as raw_handle, parsed_path.open(
        "w", encoding="utf-8", newline="\n"
    ) as parsed_handle, failure_path.open("w", encoding="utf-8", newline="\n") as failure_handle:
        for index, record in enumerate(records):
            prompt_text = apply_chat_template(tokenizer, messages_for_record(record, args.prompt_mode))
            raw, gen_meta = generate_one(model, tokenizer, prompt_text)
            parsed, parse_error = parse_candidate_output(raw)
            raw_item = {
                "index": index,
                "record_id": record.get("id") or record.get("record_id") or f"val_{index:03d}",
                "raw_output": raw,
                "generation": gen_meta,
            }
            raw_rows.append(raw_item)
            raw_handle.write(json.dumps(raw_item, ensure_ascii=False) + "\n")
            latency.append(int(gen_meta["latency_ms"]))
            input_tokens.append(int(gen_meta["input_tokens"]))
            output_tokens.append(int(gen_meta["output_tokens"]))
            if parsed is None:
                failure_item = {**raw_item, "parse_error": parse_error}
                failures.append(failure_item)
                failure_handle.write(json.dumps(failure_item, ensure_ascii=False) + "\n")
            else:
                parsed_item = {**raw_item, "parsed": parsed}
                parsed_rows.append(parsed_item)
                parsed_handle.write(json.dumps(parsed_item, ensure_ascii=False) + "\n")
            print(json.dumps({"model": args.candidate_key, "run": validation_run_id, "i": index + 1, "n": len(records), "parsed": parsed is not None}), flush=True)

    metrics = summarize_parse_results(len(raw_rows), parsed_rows, failures)
    metrics["latency_ms_mean"] = round(sum(latency) / len(latency), 3) if latency else None
    metrics["input_tokens_mean"] = round(sum(input_tokens) / len(input_tokens), 3) if input_tokens else None
    metrics["output_tokens_mean"] = round(sum(output_tokens) / len(output_tokens), 3) if output_tokens else None
    write_json(out_dir / "metrics.json", metrics)
    write_json(
        out_dir / "manifest.json",
        {
            "created_at_utc": utc_now(),
            "candidate": candidate,
            "train_run_id": args.train_run_id,
            "epoch": args.epoch,
            "validation_run_id": validation_run_id,
            "adapter_dir": str(adapter_dir),
            "prompt_mode": args.prompt_mode,
            "raw_outputs": str(raw_path),
            "parsed_outputs": str(parsed_path),
            "parse_failures": str(failure_path),
            "metrics": str(out_dir / "metrics.json"),
            "status": "completed",
        },
    )
    print(json.dumps({"status": "completed", "validation_dir": str(out_dir), "parsed": len(parsed_rows), "total": len(raw_rows)}, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
