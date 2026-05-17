from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_DIR = ROOT / "outputs" / "local_inference_resource_probe" / "20260513"
DEFAULT_SUMMARY = DEFAULT_INPUT_DIR / "summary.json"
DEFAULT_REPORT = ROOT / "reports" / "deployment_feasibility" / "local_inference_resource_probe_20260513.md"
DEFAULT_DECISION = ROOT / "logs" / "decisions" / "local_inference_resource_probe_20260513.md"


ORDER = [
    "llama31_8b_candidate_a",
    "llama32_3b_instruct",
    "ministral3_3b_instruct",
    "granite41_3b",
    "phi4_mini_instruct",
    "qwen35_4b",
    "gemma4_e2b_it",
    "gemma4_e4b_it",
]


DISPLAY = {
    "llama31_8b_candidate_a": "Llama 3.1 8B Candidate A",
    "llama32_3b_instruct": "Llama 3.2 3B Instruct",
    "ministral3_3b_instruct": "Ministral 3 3B Instruct",
    "granite41_3b": "Granite 4.1 3B",
    "phi4_mini_instruct": "Phi-4-mini-instruct",
    "qwen35_4b": "Qwen 3.5 4B",
    "gemma4_e2b_it": "Gemma 4 E2B IT",
    "gemma4_e4b_it": "Gemma 4 E4B IT",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def mem_used(entry: dict[str, Any] | None) -> int | None:
    if not isinstance(entry, dict):
        return None
    value = entry.get("memory_used_mib")
    return int(value) if isinstance(value, (int, float)) else None


def run_by_count(record: dict[str, Any], block_count: int) -> dict[str, Any] | None:
    for run in record.get("runs") or []:
        if run.get("block_count") == block_count:
            return run
    return None


def row_from_record(record: dict[str, Any]) -> dict[str, Any]:
    key = record.get("model_key")
    run1 = run_by_count(record, 1)
    run3 = run_by_count(record, 3)
    run3_tokens = []
    if run3 is not None:
        run3_tokens = [
            int(item.get("generated_tokens"))
            for item in run3.get("items", [])
            if isinstance(item.get("generated_tokens"), (int, float))
        ]
    run3_total_tokens = sum(run3_tokens)
    run3_total_seconds = None if run3 is None else run3.get("total_latency_seconds")
    run3_tokens_per_second = None
    if isinstance(run3_total_seconds, (int, float)) and run3_total_seconds > 0 and run3_total_tokens:
        run3_tokens_per_second = round(run3_total_tokens / run3_total_seconds, 3)
    after_load = mem_used(record.get("gpu_after_load"))
    run_mems = [mem_used((run or {}).get("gpu_after_run")) for run in [run1, run3]]
    run_mems = [value for value in run_mems if value is not None]
    peak_gpu = max([after_load] + run_mems) if after_load is not None else (max(run_mems) if run_mems else None)
    return {
        "model_key": key,
        "display_name": DISPLAY.get(str(key), str(key)),
        "model_id": (record.get("candidate") or {}).get("model_id"),
        "status": record.get("status"),
        "load_seconds": record.get("load_seconds"),
        "gpu_after_load_mib": after_load,
        "peak_gpu_used_mib_after_load_or_run": peak_gpu,
        "one_block_seconds": None if run1 is None else run1.get("total_latency_seconds"),
        "one_block_parse": None if run1 is None else f"{run1.get('parse_success')}/{run1.get('parse_total')}",
        "three_block_total_seconds": run3_total_seconds,
        "three_block_mean_seconds": None if run3 is None else run3.get("mean_latency_seconds"),
        "three_block_avg_generated_tokens": round(run3_total_tokens / len(run3_tokens), 1) if run3_tokens else None,
        "three_block_generated_tokens_per_second": run3_tokens_per_second,
        "three_block_parse": None if run3 is None else f"{run3.get('parse_success')}/{run3.get('parse_total')}",
        "actual_route": record.get("actual_route"),
        "error": record.get("error"),
    }


def format_value(value: Any, suffix: str = "") -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.3f}{suffix}"
    return f"{value}{suffix}"


def markdown_table(rows: list[dict[str, Any]]) -> str:
    lines = [
        "| Model | Load s | Peak GPU MiB | 1 block s | 3 blocks total s | Mean s/block | Avg gen tokens | Gen tok/s | Parse 3/3 | Status |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    row["display_name"],
                    format_value(row["load_seconds"]),
                    format_value(row["peak_gpu_used_mib_after_load_or_run"]),
                    format_value(row["one_block_seconds"]),
                    format_value(row["three_block_total_seconds"]),
                    format_value(row["three_block_mean_seconds"]),
                    format_value(row["three_block_avg_generated_tokens"]),
                    format_value(row["three_block_generated_tokens_per_second"]),
                    str(row["three_block_parse"] or "n/a"),
                    str(row["status"] or "n/a"),
                ]
            )
            + " |"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize local inference resource probe JSON files.")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--decision", type=Path, default=DEFAULT_DECISION)
    args = parser.parse_args()

    records: dict[str, dict[str, Any]] = {}
    for path in sorted(args.input_dir.glob("*.json")):
        if path.name == "summary.json":
            continue
        value = json.loads(path.read_text(encoding="utf-8"))
        key = value.get("model_key")
        if isinstance(key, str):
            records[key] = value

    rows = [row_from_record(records[key]) for key in ORDER if key in records]
    rows.extend(row_from_record(record) for key, record in sorted(records.items()) if key not in ORDER)

    summary = {
        "created_at_utc": utc_now(),
        "input_dir": str(args.input_dir),
        "measurement_scope": "Same-machine local sequential inference resource probe. This is not a vLLM throughput benchmark.",
        "models_count": len(rows),
        "rows": rows,
    }
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report = f"""# Local Inference Resource Probe - 2026-05-13

## Purpose

This probe reruns the old Llama 3.1 8B Candidate A and the newer 3-4B candidate models on the same local machine, using the same script, same dataset sample, same prompt, same 4-bit loading policy where applicable, and the same sequential generation route.

This answers the deployment-feasibility question only: inference time and GPU memory on this machine. It does not replace the fine-tuning validation or full benchmark.

## Test Setup

- Machine GPU: NVIDIA GeForce RTX 4070 Ti SUPER, 16376 MiB reported by nvidia-smi.
- Environment: WSL conda environment `clearread-llama-lora`.
- Route: local single-process sequential inference, Transformers or Unsloth depending on model compatibility, not vLLM.
- Dataset source: `C:\\Users\\Aufb\\Desktop\\fit5120\\iteration1\\data\\final_lora_data\\outputs\\accepted\\all_v1.jsonl`.
- Sample seed: `20021`.
- Block counts: `1` and `3`.
- Max input tokens: `3072`.
- Max new tokens: `256`.
- Raw inputs and raw outputs were not saved in this probe.
- No files outside `fine_tune_sweep` were written by the probe.

## Results

{markdown_table(rows)}

## Reading The Results

The old Llama 3.1 8B Candidate A is faster than all tested 3-4B base candidates in this sequential local route, mainly because it generates shorter schema-compliant outputs after fine-tuning. Smaller parameter count does reduce model memory for several candidates, but it does not automatically reduce end-to-end latency when the model emits more tokens or uses a heavier architecture/runtime path.

Gemma 4 E4B and E2B are especially poor fits for the original goal of replacing the 8B deployment with a smaller and faster model: both use more local GPU memory than most 3B candidates and are much slower in this probe.

## Limitations

- This is a small resource probe, not a full quality benchmark.
- It uses sequential local inference, not the old cloud vLLM deployment stack.
- Base models are not fine-tuned except the old Llama 3.1 8B Candidate A adapter.
- Parse success is recorded only as a sanity signal; the main target here is time and memory.
"""
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")

    decision = f"""# Decision Note - Local Inference Resource Probe 2026-05-13

The same-machine probe has now been run for all listed candidates and for the old Llama 3.1 8B Candidate A. The old 8B candidate remains the fastest local sequential option in this measurement, while several smaller base models use less GPU memory but take longer because their outputs are longer or their runtime path is heavier.

Immediate implication: do not prioritize Gemma 4 E4B as the main replacement candidate unless a separate optimized deployment route proves a major speed improvement. For the smaller-model search, focus should stay on candidates that are both trainable and deployment-light, especially Llama 3.2 3B, Ministral 3B, Granite 3B, and Phi mini, with quality measured after fine-tuning.

Report: `{args.report}`
Summary JSON: `{args.summary}`
"""
    args.decision.parent.mkdir(parents=True, exist_ok=True)
    args.decision.write_text(decision, encoding="utf-8")

    print(markdown_table(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
