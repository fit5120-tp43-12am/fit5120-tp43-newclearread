from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_API_URL = "http://127.0.0.1:8010"
DEFAULT_SEED = 20020
DEFAULT_BLOCK_COUNTS = "8,9,10,11,12"
ADAPTER_HASH = "ef220721c78e72f41c3b14749f25a09ef39f6aaf351266b276cee41ec724cf92"


def parse_args() -> argparse.Namespace:
    default_dataset = Path(
        os.environ.get(
            "CLEARREAD_BENCHMARK_DATASET",
            "data/final_lora_data/outputs/accepted/all_v1.jsonl",
        )
    )
    default_results_dir = Path(__file__).resolve().parent

    parser = argparse.ArgumentParser(
        description=(
            "Run safe ClearRead GCP pressure tests with training-style user text. "
            "The script records metadata only; it does not save raw inputs or model outputs."
        )
    )
    parser.add_argument("--dataset", type=Path, default=default_dataset)
    parser.add_argument("--results-dir", type=Path, default=default_results_dir)
    parser.add_argument(
        "--api-url",
        default=os.environ.get("CLEARREAD_AI_SUMMARY_API_URL", DEFAULT_API_URL),
    )
    parser.add_argument("--block-counts", default=DEFAULT_BLOCK_COUNTS)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--timeout-seconds", type=float, default=180.0)
    parser.add_argument("--sleep-between-seconds", type=float, default=2.0)
    parser.add_argument(
        "--output-stem",
        default=None,
        help="Optional output stem. Defaults to pressure_results_<UTC timestamp>.",
    )
    return parser.parse_args()


def parse_block_counts(raw: str) -> list[int]:
    counts: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        value = int(part)
        if value <= 0:
            raise ValueError("block counts must be positive")
        counts.append(value)
    if not counts:
        raise ValueError("at least one block count is required")
    return counts


def load_user_texts(dataset: Path) -> list[str]:
    texts: list[str] = []
    with dataset.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSON on line {line_number}: {exc}") from exc

            messages = record.get("messages")
            if not isinstance(messages, list):
                continue
            for message in messages:
                if not isinstance(message, dict):
                    continue
                if message.get("role") != "user":
                    continue
                content = message.get("content")
                if isinstance(content, str) and content.strip():
                    texts.append(content)
                break

    if not texts:
        raise ValueError(f"no role=user texts found in {dataset}")
    return texts


def percentile(values: list[int], q: float) -> int | None:
    if not values:
        return None
    sorted_values = sorted(values)
    index = max(0, min(len(sorted_values) - 1, math.ceil(q * len(sorted_values)) - 1))
    return sorted_values[index]


def char_stats(texts: list[str]) -> dict[str, int | None]:
    lengths = [len(text) for text in texts]
    return {
        "min": min(lengths) if lengths else None,
        "p50": percentile(lengths, 0.50),
        "p90": percentile(lengths, 0.90),
        "max": max(lengths) if lengths else None,
    }


def build_payload(selected_texts: list[str], request_id: str) -> dict[str, Any]:
    return {
        "requestId": request_id,
        "texts": [
            {"id": f"block-{index:03d}", "text": text}
            for index, text in enumerate(selected_texts, start=1)
        ],
        "options": {"includeDebug": False},
    }


def request_json(
    api_url: str,
    api_key: str,
    payload: dict[str, Any],
    timeout_seconds: float,
) -> tuple[int, str, dict[str, Any] | None, str | None]:
    url = api_url.rstrip("/") + "/v1/clearread/summarize"
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = None
            return response.status, raw, parsed, None
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = None
        return exc.code, raw, parsed, None
    except Exception as exc:
        return 0, "", None, f"{type(exc).__name__}: {exc}"


def forbidden_markers(
    raw_response: str,
    selected_texts: list[str],
    api_key: str,
) -> dict[str, bool]:
    return {
        "wrapper_main_idea": "main_idea" in raw_response,
        "wrapper_key_points": "key_points" in raw_response,
        "raw_vllm_choices": '"choices"' in raw_response,
        "raw_vllm_completion": "raw_completion" in raw_response
        or "rawCompletion" in raw_response,
        "full_source_text": any(text and text in raw_response for text in selected_texts),
        "private_vm_path": "/home/" in raw_response,
        "private_windows_path": ("C:" + "\\Users") in raw_response
        or ("/mnt/c/" + "Users") in raw_response,
        "adapter_hash": ADAPTER_HASH in raw_response,
        "api_key": bool(api_key) and api_key in raw_response,
    }


def analyze_response(
    block_count: int,
    seed: int,
    selected_texts: list[str],
    http_status: int,
    latency_seconds: float,
    raw_response: str,
    parsed: dict[str, Any] | None,
    exception: str | None,
    api_key: str,
) -> dict[str, Any]:
    expected_ids = [f"block-{index:03d}" for index in range(1, block_count + 1)]
    results = parsed.get("results") if isinstance(parsed, dict) else None
    if not isinstance(results, list):
        results = []

    ids = [item.get("id") if isinstance(item, dict) else None for item in results]
    item_statuses = [
        item.get("status") if isinstance(item, dict) else None for item in results
    ]
    ok_count = sum(1 for status in item_statuses if status == "ok")
    error_codes: Counter[str] = Counter()
    key_point_counts: list[int | None] = []

    for item in results:
        if not isinstance(item, dict):
            key_point_counts.append(None)
            continue
        key_points = item.get("keyPoints")
        key_point_counts.append(len(key_points) if isinstance(key_points, list) else None)
        if item.get("status") == "error":
            error = item.get("error")
            if isinstance(error, dict) and isinstance(error.get("code"), str):
                error_codes[error["code"]] += 1
            else:
                error_codes["missing_error_code"] += 1

    markers = forbidden_markers(raw_response, selected_texts, api_key)
    forbidden_any = any(markers.values())
    successful_key_points_all_four = all(
        count == 4
        for status, count in zip(item_statuses, key_point_counts)
        if status == "ok"
    )
    all_items_ok = ok_count == block_count and len(results) == block_count
    order_preserved = ids == expected_ids
    top_status = parsed.get("status") if isinstance(parsed, dict) else None
    pass_under_30 = (
        http_status == 200
        and top_status == "ok"
        and all_items_ok
        and order_preserved
        and successful_key_points_all_four
        and not forbidden_any
        and latency_seconds <= 30.0
    )

    return {
        "block_count": block_count,
        "seed": seed,
        "http_status": http_status,
        "latency_seconds": round(latency_seconds, 3),
        "under_30_seconds": latency_seconds <= 30.0,
        "top_status": top_status,
        "result_count": len(results),
        "ok_item_count": ok_count,
        "error_item_count": len(results) - ok_count if results else 0,
        "error_codes": dict(sorted(error_codes.items())),
        "order_preserved": order_preserved,
        "key_point_counts": key_point_counts,
        "successful_key_points_all_four": successful_key_points_all_four,
        "input_character_lengths": char_stats(selected_texts),
        "forbidden_public_response_markers": markers,
        "forbidden_public_response_marker_present": forbidden_any,
        "passed_all_success_under_30_seconds": pass_under_30,
        "exception": exception,
        "raw_inputs_saved": False,
        "raw_model_outputs_saved": False,
    }


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def write_csv(path: Path, runs: list[dict[str, Any]]) -> None:
    if not runs:
        path.write_text("", encoding="utf-8")
        return

    fieldnames: list[str] = []
    for row in runs:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in runs:
            writer.writerow(
                {
                    key: json.dumps(value, sort_keys=True)
                    if isinstance(value, (dict, list))
                    else value
                    for key, value in row.items()
                }
            )


def print_table(runs: list[dict[str, Any]]) -> None:
    header = (
        "blocks  http  latency_s  top_status     ok/result  order  kp4  "
        "forbidden  pass_under_30"
    )
    print(header)
    print("-" * len(header))
    for row in runs:
        print(
            f"{row['block_count']:>6}  "
            f"{row['http_status']:>4}  "
            f"{row['latency_seconds']:>9.3f}  "
            f"{str(row['top_status']):<12}  "
            f"{row['ok_item_count']:>2}/{row['result_count']:<6}  "
            f"{str(row['order_preserved']):<5}  "
            f"{str(row['successful_key_points_all_four']):<4}  "
            f"{str(row['forbidden_public_response_marker_present']):<9}  "
            f"{str(row['passed_all_success_under_30_seconds'])}"
        )


def main() -> int:
    args = parse_args()
    api_key = os.environ.get("CLEARREAD_AI_SERVICE_API_KEY")
    if not api_key:
        print("ERROR: CLEARREAD_AI_SERVICE_API_KEY is not set in the local environment.", file=sys.stderr)
        return 2

    block_counts = parse_block_counts(args.block_counts)
    user_texts = load_user_texts(args.dataset)
    if max(block_counts) > len(user_texts):
        raise ValueError(
            f"largest block count {max(block_counts)} exceeds available texts {len(user_texts)}"
        )

    rng = random.Random(args.seed)
    shuffled = list(user_texts)
    rng.shuffle(shuffled)

    args.results_dir.mkdir(parents=True, exist_ok=True)
    started_at = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_stem = args.output_stem or f"pressure_results_{started_at}"

    runs: list[dict[str, Any]] = []
    for block_count in block_counts:
        selected = shuffled[:block_count]
        request_id = f"gcp-pressure-{block_count}-{args.seed}"
        payload = build_payload(selected, request_id)

        started = time.perf_counter()
        http_status, raw_response, parsed, exception = request_json(
            args.api_url,
            api_key,
            payload,
            args.timeout_seconds,
        )
        latency = time.perf_counter() - started

        run = analyze_response(
            block_count=block_count,
            seed=args.seed,
            selected_texts=selected,
            http_status=http_status,
            latency_seconds=latency,
            raw_response=raw_response,
            parsed=parsed,
            exception=exception,
            api_key=api_key,
        )
        runs.append(run)
        print_table([run])

        if block_count != block_counts[-1] and args.sleep_between_seconds > 0:
            time.sleep(args.sleep_between_seconds)

    artifact = {
        "created_at_utc": started_at,
        "api_url": args.api_url,
        "dataset_path": str(args.dataset),
        "dataset_record_count": len(user_texts),
        "block_counts": block_counts,
        "seed": args.seed,
        "timeout_seconds": args.timeout_seconds,
        "raw_inputs_saved": False,
        "raw_model_outputs_saved": False,
        "runs": runs,
    }

    json_path = args.results_dir / f"{output_stem}.json"
    csv_path = args.results_dir / f"{output_stem}.csv"
    latest_json_path = args.results_dir / "pressure_results_latest.json"
    latest_csv_path = args.results_dir / "pressure_results_latest.csv"
    write_json(json_path, artifact)
    write_json(latest_json_path, artifact)
    write_csv(csv_path, runs)
    write_csv(latest_csv_path, runs)

    print()
    print_table(runs)
    print(f"json_path={json_path}")
    print(f"csv_path={csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
