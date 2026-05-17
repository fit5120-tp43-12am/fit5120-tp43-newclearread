#!/usr/bin/env python
"""Run frozen benchmark inference for one selected sweep adapter."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from peft import PeftModel

from sweep_utils import ROOT, file_sha256, parse_candidate_output, read_json, read_jsonl, summarize_parse_results, write_json
from train_sweep_qlora import candidate_lookup, load_model, load_tokenizer_or_processor


PREPARED_INPUTS_PATH = (
    ROOT
    / "data"
    / "source_snapshot"
    / "benchmark_prepared_inputs"
    / "dyslexia_benchmark_handoff__03_project_workspace__09_run_config__worker_20_dataset_manifest_and_freeze_inputs__prepared_inputs.jsonl"
)
EXPECTED_PREPARED_ROW_COUNT = 145


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def system_prompt() -> str:
    train_path = ROOT / "data" / "source_snapshot" / "training3b_splits" / "train.jsonl"
    record = read_jsonl(train_path)[0]
    return str(record["messages"][0]["content"])


def apply_chat_template(tokenizer: Any, source_text: str) -> str:
    messages = [
        {"role": "system", "content": system_prompt()},
        {"role": "user", "content": source_text},
    ]
    if hasattr(tokenizer, "apply_chat_template"):
        try:
            return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        except TypeError:
            return tokenizer.apply_chat_template(messages, tokenize=False)
    return "\n\n".join(f"{item['role'].upper()}:\n{item['content']}" for item in messages) + "\n\nASSISTANT:\n"


def tensor_device(model: Any):
    for param in model.parameters():
        return param.device
    return "cuda"


def generate_one(model: Any, tokenizer: Any, source_text: str, max_new_tokens: int) -> tuple[str, dict[str, Any]]:
    import torch

    prompt = apply_chat_template(tokenizer, source_text)
    device = tensor_device(model)
    encoded = tokenizer(prompt, return_tensors="pt")
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
            pad_token_id=getattr(tokenizer, "pad_token_id", None),
            eos_token_id=getattr(tokenizer, "eos_token_id", None),
        )
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    output_ids = generated[0][input_len:]
    raw = tokenizer.decode(output_ids, skip_special_tokens=True).strip()
    return raw, {"input_tokens": input_len, "output_tokens": int(output_ids.shape[-1]), "latency_ms": elapsed_ms}


def build_record_run_id(run_id: str, system_id: str, input_id: str) -> str:
    return f"{run_id}__{system_id}__{input_id}__{sha256_text(run_id + '|' + system_id + '|' + input_id)[:12]}"


def resolve_adapter_dir(args: argparse.Namespace) -> Path:
    if args.adapter_dir:
        path = Path(args.adapter_dir)
        return path if path.is_absolute() else ROOT / path
    if args.train_run_id is None or args.epoch is None:
        raise SystemExit("Provide either --adapter-dir or both --train-run-id and --epoch.")
    return ROOT / "model_workspaces" / args.candidate_key / "models" / "adapters" / f"{args.train_run_id}_epoch_{args.epoch}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run frozen benchmark inference for one finalist adapter.")
    parser.add_argument("--candidate-key", required=True)
    parser.add_argument("--system-id", required=True)
    parser.add_argument("--benchmark-run-id", required=True)
    parser.add_argument("--adapter-dir", default=None)
    parser.add_argument("--train-run-id", default=None)
    parser.add_argument("--epoch", type=int, default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--max-new-tokens", type=int, default=320)
    parser.add_argument("--allow-overwrite", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    os.environ.setdefault("HF_HOME", str(ROOT / "cache" / "huggingface"))
    sweep = read_json(ROOT / "configs" / "sweep_candidates.json")
    candidate = candidate_lookup(sweep, args.candidate_key)
    adapter_dir = resolve_adapter_dir(args)
    if not adapter_dir.exists():
        raise FileNotFoundError(adapter_dir)

    run_root = ROOT / "benchmark_workspace" / "runs" / args.benchmark_run_id
    raw_dir = run_root / "model_raw_outputs" / args.system_id
    parsed_dir = run_root / "parsed_outputs" / args.system_id
    manifest_dir = run_root / "manifests_logs"
    if run_root.exists() and any((raw_dir, parsed_dir, manifest_dir)) and not args.allow_overwrite:
        existing = [str(path) for path in (raw_dir, parsed_dir, manifest_dir) if path.exists()]
        if existing:
            raise SystemExit(f"Refusing to overwrite existing benchmark artifacts: {existing}")
    raw_dir.mkdir(parents=True, exist_ok=True)
    parsed_dir.mkdir(parents=True, exist_ok=True)
    manifest_dir.mkdir(parents=True, exist_ok=True)

    prepared = read_jsonl(PREPARED_INPUTS_PATH)
    if len(prepared) != EXPECTED_PREPARED_ROW_COUNT:
        raise ValueError(f"Expected {EXPECTED_PREPARED_ROW_COUNT} prepared inputs, found {len(prepared)}")
    if args.limit:
        prepared = prepared[: args.limit]

    _, tokenizer = load_tokenizer_or_processor(candidate, ROOT / "cache" / "huggingface")
    model = load_model(candidate, ROOT / "cache" / "huggingface")
    model = PeftModel.from_pretrained(model, str(adapter_dir), is_trainable=False)
    model.eval()

    import torch

    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
    started = time.time()
    created_at = utc_now()
    raw_rows: list[dict[str, Any]] = []
    parsed_rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for index, record in enumerate(prepared, start=1):
        raw, generation = generate_one(model, tokenizer, str(record["source_chunk_text"]), args.max_new_tokens)
        input_id = str(record["input_id"])
        base = {
            "record_run_id": build_record_run_id(args.benchmark_run_id, args.system_id, input_id),
            "run_id": args.benchmark_run_id,
            "system_id": args.system_id,
            "input_id": input_id,
            "source_dataset_path": record.get("source_dataset_path"),
            "source_row_index": record.get("source_row_index"),
            "source_row_sha256": record.get("source_row_sha256"),
            "source_chunk_sha256": record.get("source_chunk_sha256"),
            "prepared_input_sha256": hashlib.sha256(json.dumps(record, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest(),
            "raw_output_sha256": sha256_text(raw),
            "created_at_utc": created_at,
        }
        raw_item = {**base, "raw_output_text": raw, "generation": generation}
        raw_rows.append(raw_item)
        parsed, parse_error = parse_candidate_output(raw)
        if parsed is None:
            failures.append({**base, "raw_output_text": raw, "parse_error": parse_error})
        else:
            parsed_rows.append(
                {
                    **base,
                    "raw_output_text": raw,
                    "raw_output": raw,
                    "parsed": parsed,
                    "main_idea": parsed["main_idea"],
                    "key_points": parsed["key_points"],
                }
            )
        print(json.dumps({"system_id": args.system_id, "i": index, "n": len(prepared), "parsed": parsed is not None}), flush=True)

    raw_path = raw_dir / "raw_outputs.jsonl"
    parsed_path = parsed_dir / "parsed_outputs.jsonl"
    failure_path = parsed_dir / "parse_failures.jsonl"
    write_jsonl(raw_path, raw_rows)
    write_jsonl(parsed_path, parsed_rows)
    write_jsonl(failure_path, failures)
    runtime = round(time.time() - started, 2)
    peak_allocated = round(torch.cuda.max_memory_allocated() / 1024 / 1024, 2) if torch.cuda.is_available() else None
    metrics = summarize_parse_results(len(raw_rows), parsed_rows, failures)
    manifest = {
        "created_at_utc": utc_now(),
        "benchmark_run_id": args.benchmark_run_id,
        "candidate_key": args.candidate_key,
        "system_id": args.system_id,
        "base_model_id": candidate["model_id"],
        "adapter_dir": str(adapter_dir),
        "adapter_manifest_sha256": file_sha256(adapter_dir / "adapter_config.json") if (adapter_dir / "adapter_config.json").exists() else None,
        "prepared_inputs_path": str(PREPARED_INPUTS_PATH),
        "prepared_inputs_sha256": file_sha256(PREPARED_INPUTS_PATH),
        "prepared_input_count": len(prepared),
        "raw_output_path": str(raw_path),
        "parsed_output_path": str(parsed_path),
        "parse_failure_path": str(failure_path),
        "metrics": metrics,
        "runtime_seconds": runtime,
        "peak_vram_allocated_mib": peak_allocated,
        "decode": {"do_sample": False, "max_new_tokens": args.max_new_tokens},
    }
    manifest_path = manifest_dir / f"model_inference_{args.system_id}.json"
    write_json(manifest_path, manifest)
    print(json.dumps({"status": "completed", "manifest": str(manifest_path), "parsed": len(parsed_rows), "total": len(raw_rows)}, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
