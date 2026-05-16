from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import platform
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

os.environ.setdefault("VLLM_USE_FLASHINFER_SAMPLER", "0")

from transformers import AutoTokenizer

from vllm_benchmark_common import (
    ADAPTER_PATH,
    BASE_MODEL_ID,
    BENCH_DIR,
    GPU_MEMORY_UTILIZATION,
    ITERATION_ROOT,
    LORA_NAME,
    MAX_MODEL_LEN,
    MAX_NEW_TOKENS,
    SYSTEM_PROMPT,
    PeakPoller,
    build_prompt,
    gpu_memory_used_mib,
    guarded_output,
    load_blocks,
    process_rss_mib,
    redact_log_line,
    stats,
    summarize_guards,
    token_lengths,
    word_count,
    write_csv,
    write_json,
)


API_KEY = os.environ.get("CLEARREAD_VLLM_BENCHMARK_API_KEY", "local-vllm-benchmark-token")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8012)
    parser.add_argument("--direct-batch-sizes", default="1,3,8,16")
    parser.add_argument("--wrapper-batch-sizes", default="1,3,4,6,8,10,16")
    parser.add_argument("--startup-timeout-seconds", type=float, default=240.0)
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


def request_json(method: str, url: str, payload: dict[str, Any] | None = None, auth: bool = True, timeout: float = 120.0) -> tuple[int, dict[str, Any] | str]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"} if payload is not None else {}
    if auth:
        headers["Authorization"] = f"Bearer {API_KEY}"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            text = response.read().decode("utf-8", errors="replace")
            try:
                return response.status, json.loads(text) if text else {}
            except json.JSONDecodeError:
                return response.status, text[:200]
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(text) if text else {}
        except json.JSONDecodeError:
            return exc.code, text[:200]
    except Exception as exc:
        return 0, {"error": type(exc).__name__, "message": str(exc)}


def chat_payload(block: dict[str, Any]) -> dict[str, Any]:
    return {
        "model": LORA_NAME,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": block["text"]},
        ],
        "max_tokens": MAX_NEW_TOKENS,
        "temperature": 0,
    }


def extract_content(response: dict[str, Any] | str) -> str:
    if not isinstance(response, dict):
        return ""
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0]
    if not isinstance(first, dict):
        return ""
    message = first.get("message")
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    return content if isinstance(content, str) else ""


def start_server(port: int, log_path: Path) -> subprocess.Popen[str]:
    command = [
        sys.executable,
        "-m",
        "vllm.entrypoints.openai.api_server",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--model",
        BASE_MODEL_ID,
        "--trust-remote-code",
        "--dtype",
        "bfloat16",
        "--max-model-len",
        str(MAX_MODEL_LEN),
        "--gpu-memory-utilization",
        str(GPU_MEMORY_UTILIZATION),
        "--enforce-eager",
        "--enable-lora",
        "--max-lora-rank",
        "16",
        "--max-loras",
        "1",
        "--lora-modules",
        f"{LORA_NAME}={ADAPTER_PATH}",
        "--served-model-name",
        LORA_NAME,
        "--disable-log-requests",
        "--disable-log-stats",
        "--disable-uvicorn-access-log",
        "--disable-fastapi-docs",
        "--api-key",
        API_KEY,
    ]
    env = os.environ.copy()
    env["VLLM_USE_FLASHINFER_SAMPLER"] = "0"
    process = subprocess.Popen(
        command,
        cwd=str(BENCH_DIR),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    def reader() -> None:
        assert process.stdout is not None
        with log_path.open("w", encoding="utf-8") as handle:
            for line in process.stdout:
                handle.write(redact_log_line(line, api_key=API_KEY))

    threading.Thread(target=reader, daemon=True).start()
    return process


def wait_ready(port: int, timeout_seconds: float) -> tuple[float, int]:
    start = time.perf_counter()
    last_status = 0
    while time.perf_counter() - start < timeout_seconds:
        status, _ = request_json("GET", f"http://127.0.0.1:{port}/v1/models", timeout=2.0)
        last_status = status
        if status == 200:
            return time.perf_counter() - start, status
        time.sleep(1.0)
    return time.perf_counter() - start, last_status


def call_one(port: int, block: dict[str, Any]) -> dict[str, Any]:
    start = time.perf_counter()
    status, body = request_json("POST", f"http://127.0.0.1:{port}/v1/chat/completions", chat_payload(block), timeout=180.0)
    latency = time.perf_counter() - start
    guard = guarded_output(extract_content(body)) if status == 200 else {"status": "error", "schema_guard_action": "http_error", "errors": [f"http_{status}"], "output": None}
    return {"id": block["id"], "http_status": status, "latency_seconds": latency, "guard": guard}


def run_direct_batch(port: int, blocks: list[dict[str, Any]], token_lengths_for_blocks: list[int], batch_size: int) -> dict[str, Any]:
    selected = blocks[:batch_size]
    selected_words = [word_count(block["text"]) for block in selected]
    selected_tokens = token_lengths_for_blocks[:batch_size]
    start = time.perf_counter()
    with PeakPoller() as poller:
        with concurrent.futures.ThreadPoolExecutor(max_workers=batch_size) as executor:
            futures = [executor.submit(call_one, port, block) for block in selected]
            items = [future.result() for future in futures]
    latency = time.perf_counter() - start
    guards = [item["guard"] for item in items]
    guard_summary = summarize_guards(guards)
    return {
        "route": "vllm_server_concurrent_http",
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
        "http_statuses": [item["http_status"] for item in items],
        "max_single_http_latency_seconds": round(max(item["latency_seconds"] for item in items), 3),
        "gpu_after_run_mib": gpu_memory_used_mib(),
        "gpu_peak_during_run_mib": poller.peak_gpu_mib,
        "rss_after_run_mib": process_rss_mib(),
        "rss_peak_during_run_mib": poller.peak_rss_mib,
        "max_new_tokens": MAX_NEW_TOKENS,
        "payload_packaging_overhead_material": False,
        "logs_expose_request_text": False,
        "raw_outputs_saved": False,
    }


def run_wrapper_batch(port: int, blocks: list[dict[str, Any]], token_lengths_for_blocks: list[int], batch_size: int) -> dict[str, Any]:
    selected = blocks[:batch_size]
    selected_words = [word_count(block["text"]) for block in selected]
    selected_tokens = token_lengths_for_blocks[:batch_size]
    public_request = {
        "requestId": f"vllm-sla-{batch_size}",
        "texts": [{"id": block["id"], "text": block["text"]} for block in selected],
        "options": {"includeDebug": False},
    }
    payload_bytes = len(json.dumps(public_request).encode("utf-8"))

    total_start = time.perf_counter()
    with PeakPoller() as poller:
        dispatch_start = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=batch_size) as executor:
            futures = [executor.submit(call_one, port, block) for block in selected]
            items = [future.result() for future in futures]
        dispatch_latency = time.perf_counter() - dispatch_start

    packaging_start = time.perf_counter()
    results: list[dict[str, Any]] = []
    for block, item in zip(selected, items):
        guard = item["guard"]
        output = guard.get("output") if isinstance(guard, dict) else None
        if item["http_status"] == 200 and isinstance(output, dict):
            results.append(
                {
                    "id": block["id"],
                    "status": "ok",
                    "summary": output["main_idea"],
                    "keyPoints": output["key_points"],
                    "schemaGuardAction": guard["schema_guard_action"],
                }
            )
        else:
            results.append(
                {
                    "id": block["id"],
                    "status": "error",
                    "summary": "",
                    "keyPoints": [],
                    "schemaGuardAction": guard.get("schema_guard_action", "return_error_object"),
                    "error": {"code": "model_schema_error", "message": "The model output could not be converted into a valid summary.", "retryable": False},
                }
            )
    public_response = {
        "requestId": public_request["requestId"],
        "status": "ok" if all(result["status"] == "ok" for result in results) else ("partial_error" if any(result["status"] == "ok" for result in results) else "error"),
        "results": results,
        "errors": [],
        "meta": {"service": "clearread-ai-summary", "version": "v1", "model": "clearread-llama31-8b-qlora-candidate-a"},
    }
    response_bytes = len(json.dumps(public_response).encode("utf-8"))
    packaging_latency = time.perf_counter() - packaging_start
    total_latency = time.perf_counter() - total_start

    guards = [item["guard"] for item in items]
    guard_summary = summarize_guards(guards)
    ordered = [result["id"] for result in results] == [block["id"] for block in selected]
    return {
        "route": "clearread_wrapper_around_vllm",
        "batch_size": batch_size,
        "word_count_min": min(selected_words),
        "word_count_max": max(selected_words),
        "word_count_avg": round(sum(selected_words) / len(selected_words), 1),
        "input_tokens_min": min(selected_tokens),
        "input_tokens_max": max(selected_tokens),
        "input_tokens_avg": round(sum(selected_tokens) / len(selected_tokens), 1),
        "total_end_to_end_latency_seconds": round(total_latency, 3),
        "vllm_dispatch_latency_seconds": round(dispatch_latency, 3),
        "packaging_latency_seconds": round(packaging_latency, 6),
        "under_30_seconds": total_latency <= 30.0,
        **guard_summary,
        "http_statuses": [item["http_status"] for item in items],
        "input_order_preserved": ordered,
        "request_payload_bytes": payload_bytes,
        "response_payload_bytes": response_bytes,
        "packaging_overhead_material": packaging_latency > 0.5,
        "gpu_after_run_mib": gpu_memory_used_mib(),
        "gpu_peak_during_run_mib": poller.peak_gpu_mib,
        "rss_after_run_mib": process_rss_mib(),
        "rss_peak_during_run_mib": poller.peak_rss_mib,
        "max_new_tokens": MAX_NEW_TOKENS,
        "logs_expose_request_text": False,
        "raw_outputs_saved": False,
    }


def terminate_server(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=20)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=20)


def main() -> int:
    args = parse_args()
    direct_batch_sizes = [int(part.strip()) for part in args.direct_batch_sizes.split(",") if part.strip()]
    wrapper_batch_sizes = [int(part.strip()) for part in args.wrapper_batch_sizes.split(",") if part.strip()]
    blocks = load_blocks()
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_ID, trust_remote_code=True)
    prompts = [build_prompt(tokenizer, block["text"]) for block in blocks]
    input_token_lengths = token_lengths(tokenizer, prompts)

    sanitized_log = BENCH_DIR / "vllm_server_sanitized.log"
    environment: dict[str, Any] = {
        "route": "vllm_server_and_wrapper",
        "versions": version_info(),
        "base_model_id": BASE_MODEL_ID,
        "adapter": "full_candidate_a_3epoch",
        "host": "127.0.0.1",
        "port": args.port,
        "api_key_used": "dummy local-only token, redacted from log artifact",
        "max_model_len": MAX_MODEL_LEN,
        "gpu_memory_utilization": GPU_MEMORY_UTILIZATION,
        "max_new_tokens": MAX_NEW_TOKENS,
        "gpu_before_start_mib": gpu_memory_used_mib(),
        "request_logging_disabled": True,
        "stats_logging_disabled": True,
        "uvicorn_access_log_disabled": True,
        "fastapi_docs_disabled": True,
    }

    process = start_server(args.port, sanitized_log)
    try:
        startup_latency, ready_status = wait_ready(args.port, args.startup_timeout_seconds)
        environment["server_pid"] = process.pid
        environment["startup_to_ready_seconds"] = round(startup_latency, 3)
        environment["ready_status"] = ready_status
        environment["gpu_after_ready_mib"] = gpu_memory_used_mib()
        environment["rss_after_ready_mib"] = process_rss_mib(process.pid)
        if ready_status != 200:
            environment["server_exit_code"] = process.poll()
            write_json(BENCH_DIR / "server_wrapper_vllm_results.json", {"environment": environment, "direct_results": [], "wrapper_results": []})
            print(json.dumps(environment, sort_keys=True))
            return 2

        route_probes = {}
        for path, auth in [
            ("/v1/models", True),
            ("/v1/models", False),
            ("/v1/chat/completions", True),
            ("/docs", True),
            ("/openapi.json", True),
            ("/metrics", True),
            ("/health", True),
        ]:
            method = "GET"
            status, _ = request_json(method, f"http://127.0.0.1:{args.port}{path}", auth=auth, timeout=5.0)
            key = f"{method} {path} auth={auth}"
            route_probes[key] = status
        environment["route_probe_statuses"] = route_probes

        direct_rows: list[dict[str, Any]] = []
        for batch_size in direct_batch_sizes:
            row = run_direct_batch(args.port, blocks, input_token_lengths, batch_size)
            direct_rows.append(row)
            print(json.dumps(row, sort_keys=True))

        wrapper_rows: list[dict[str, Any]] = []
        for batch_size in wrapper_batch_sizes:
            row = run_wrapper_batch(args.port, blocks, input_token_lengths, batch_size)
            wrapper_rows.append(row)
            print(json.dumps(row, sort_keys=True))

        payload = {"environment": environment, "direct_results": direct_rows, "wrapper_results": wrapper_rows}
        write_json(BENCH_DIR / "server_wrapper_vllm_results.json", payload)
        write_csv(BENCH_DIR / "server_vllm_direct_results.csv", direct_rows)
        write_csv(BENCH_DIR / "wrapper_vllm_results.csv", wrapper_rows)
        return 0
    finally:
        terminate_server(process)


if __name__ == "__main__":
    raise SystemExit(main())
