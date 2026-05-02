from __future__ import annotations

import argparse
import json
import os
import platform
import time
from pathlib import Path

os.environ.setdefault("VLLM_USE_FLASHINFER_SAMPLER", "0")

from transformers import AutoTokenizer
from vllm import LLM, SamplingParams
from vllm.lora.request import LoRARequest

from vllm_benchmark_common import (
    ADAPTER_PATH,
    BASE_MODEL_ID,
    BENCH_DIR,
    GPU_MEMORY_UTILIZATION,
    LORA_NAME,
    MAX_MODEL_LEN,
    MAX_NEW_TOKENS,
    PeakPoller,
    build_prompt,
    gpu_memory_used_mib,
    load_blocks,
    process_rss_mib,
    stats,
    summarize_guards,
    token_lengths,
    guarded_output,
    word_count,
    write_csv,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-sizes", default="1,3,4,6,8,10,16")
    return parser.parse_args()


def version_info() -> dict[str, object]:
    import bitsandbytes
    import torch
    import transformers
    import vllm

    return {
        "python": platform.python_version(),
        "vllm": vllm.__version__,
        "torch": torch.__version__,
        "torch_cuda": torch.version.cuda,
        "transformers": transformers.__version__,
        "bitsandbytes": bitsandbytes.__version__,
        "cuda_available": torch.cuda.is_available(),
        "vllm_use_flashinfer_sampler": os.environ.get("VLLM_USE_FLASHINFER_SAMPLER"),
    }


def main() -> int:
    args = parse_args()
    batch_sizes = [int(part.strip()) for part in args.batch_sizes.split(",") if part.strip()]
    blocks = load_blocks()

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_ID, trust_remote_code=True)
    prompts_all = [build_prompt(tokenizer, block["text"]) for block in blocks]
    token_lengths_all = token_lengths(tokenizer, prompts_all)

    environment = {
        "route": "offline",
        "versions": version_info(),
        "base_model_id": BASE_MODEL_ID,
        "adapter": "full_candidate_a_3epoch",
        "max_model_len": MAX_MODEL_LEN,
        "gpu_memory_utilization": GPU_MEMORY_UTILIZATION,
        "max_new_tokens": MAX_NEW_TOKENS,
        "gpu_before_load_mib": gpu_memory_used_mib(),
    }

    load_start = time.perf_counter()
    with PeakPoller() as load_poller:
        llm = LLM(
            model=BASE_MODEL_ID,
            trust_remote_code=True,
            dtype="bfloat16",
            max_model_len=MAX_MODEL_LEN,
            gpu_memory_utilization=GPU_MEMORY_UTILIZATION,
            enforce_eager=True,
            enable_lora=True,
            max_loras=1,
            max_lora_rank=16,
        )
    environment["load_latency_seconds"] = round(time.perf_counter() - load_start, 3)
    environment["gpu_after_load_mib"] = gpu_memory_used_mib()
    environment["gpu_peak_during_load_mib"] = load_poller.peak_gpu_mib
    environment["rss_after_load_mib"] = process_rss_mib()
    environment["rss_peak_during_load_mib"] = load_poller.peak_rss_mib

    sampling_params = SamplingParams(
        max_tokens=MAX_NEW_TOKENS,
        temperature=0.0,
        top_p=1.0,
    )

    rows: list[dict[str, object]] = []
    detailed: list[dict[str, object]] = []

    for batch_size in batch_sizes:
        selected_blocks = blocks[:batch_size]
        selected_prompts = prompts_all[:batch_size]
        selected_tokens = token_lengths_all[:batch_size]
        selected_words = [word_count(block["text"]) for block in selected_blocks]

        start = time.perf_counter()
        with PeakPoller() as poller:
            outputs = llm.generate(
                selected_prompts,
                sampling_params,
                lora_request=LoRARequest(LORA_NAME, 1, ADAPTER_PATH),
            )
        latency = time.perf_counter() - start
        guards = [guarded_output(output.outputs[0].text if output.outputs else "") for output in outputs]
        guard_summary = summarize_guards(guards)

        row: dict[str, object] = {
            "route": "offline_batched_inference",
            "batch_size": batch_size,
            "word_count_min": min(selected_words),
            "word_count_max": max(selected_words),
            "word_count_avg": round(sum(selected_words) / len(selected_words), 1),
            "input_tokens_min": min(selected_tokens),
            "input_tokens_max": max(selected_tokens),
            "input_tokens_avg": round(sum(selected_tokens) / len(selected_tokens), 1),
            "total_latency_seconds": round(latency, 3),
            "under_30_seconds": latency <= 30.0,
            **guard_summary,
            "gpu_after_load_mib": environment["gpu_after_load_mib"],
            "gpu_after_run_mib": gpu_memory_used_mib(),
            "gpu_peak_during_run_mib": poller.peak_gpu_mib,
            "rss_after_run_mib": process_rss_mib(),
            "rss_peak_during_run_mib": poller.peak_rss_mib,
            "max_new_tokens": MAX_NEW_TOKENS,
            "payload_packaging_overhead_material": False,
            "logs_expose_request_text": False,
            "raw_outputs_saved": False,
        }
        rows.append(row)
        detailed.append({**row, "item_statuses": [{"id": block["id"], "status": guard["status"], "schema_guard_action": guard["schema_guard_action"]} for block, guard in zip(selected_blocks, guards)]})
        print(json.dumps(row, sort_keys=True))

    payload = {"environment": environment, "results": detailed}
    write_json(BENCH_DIR / "offline_vllm_results.json", payload)
    write_csv(BENCH_DIR / "offline_vllm_results.csv", rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
