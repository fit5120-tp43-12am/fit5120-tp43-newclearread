#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import os
import pathlib
import sys
import time
from urllib import error, request


DEFAULT_BASE_URL = "http://34.21.166.229:8010"
DEFAULT_TEST_JSONL = (
    r"C:\Users\Aufb\Desktop\fit5120\iteration1\training\data\splits\test.jsonl"
)
DEFAULT_OUTPUT_DIR = (
    r"C:\Users\Aufb\Desktop\fit5120\iteration3\3B-deploy\logs\tests\runtime"
)


def extract_user_text(record: dict) -> str:
    messages = record.get("messages")
    if isinstance(messages, list):
        user_parts = [
            str(item.get("content", "")).strip()
            for item in messages
            if item.get("role") == "user" and item.get("content")
        ]
        if user_parts:
            return "\n\n".join(user_parts)

    for key in ("text", "input", "prompt", "content"):
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    raise ValueError("Could not find user text in JSONL record")


def read_jsonl_batch(path: pathlib.Path, limit: int) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if len(rows) >= limit:
                break
            if not line.strip():
                continue
            record = json.loads(line)
            text = extract_user_text(record)
            rows.append(
                {
                    "id": f"test-{line_no:03d}",
                    "text": text,
                    "sourceLine": line_no,
                    "charCount": len(text),
                }
            )
    return rows


def get_json(base_url: str, path: str, timeout: int) -> tuple[int, dict]:
    with request.urlopen(f"{base_url}{path}", timeout=timeout) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def post_json(base_url: str, path: str, api_key: str, payload: dict, timeout: int) -> tuple[int, dict]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        f"{base_url}{path}",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        try:
            data = json.loads(exc.read().decode("utf-8"))
        except Exception:
            data = {"error": str(exc)}
        return exc.code, data


def write_result(output_dir: pathlib.Path, result: dict) -> pathlib.Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = output_dir / f"remote_test_split_16_{stamp}.json"
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Call the remote ClearRead summary API with the first N records from test.jsonl."
    )
    parser.add_argument("--base-url", default=os.environ.get("CLEARREAD_AI_SUMMARY_API_URL", DEFAULT_BASE_URL))
    parser.add_argument("--api-key", default=os.environ.get("CLEARREAD_AI_SUMMARY_API_KEY", ""))
    parser.add_argument("--test-jsonl", default=DEFAULT_TEST_JSONL)
    parser.add_argument("--limit", type=int, default=16)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--request-id", default="local-test-split-016")
    parser.add_argument(
        "--include-input-text",
        action="store_true",
        help="Store raw input text in the local artifact. Off by default for privacy.",
    )
    args = parser.parse_args()

    if not args.api_key:
        print(
            "Missing API key. Set CLEARREAD_AI_SUMMARY_API_KEY or pass --api-key.",
            file=sys.stderr,
        )
        return 2

    base_url = args.base_url.rstrip("/")
    test_jsonl = pathlib.Path(args.test_jsonl)
    output_dir = pathlib.Path(args.output_dir)

    items = read_jsonl_batch(test_jsonl, args.limit)
    if len(items) != args.limit:
        print(f"Expected {args.limit} records, found {len(items)}.", file=sys.stderr)
        return 2

    payload = {
        "requestId": args.request_id,
        "texts": [{"id": item["id"], "text": item["text"]} for item in items],
        "options": {"includeDebug": False},
    }

    run_started = dt.datetime.now(dt.timezone.utc).isoformat()
    health_status, health = get_json(base_url, "/health", args.timeout)
    ready_status, ready = get_json(base_url, "/ready", args.timeout)

    started = time.perf_counter()
    http_status, response_data = post_json(
        base_url,
        "/v1/clearread/summarize",
        args.api_key,
        payload,
        args.timeout,
    )
    elapsed = time.perf_counter() - started

    results = response_data.get("results", [])
    summary = {
        "runStartedUtc": run_started,
        "baseUrl": base_url,
        "sourceFile": str(test_jsonl),
        "requestId": args.request_id,
        "inputCount": len(items),
        "inputCharCounts": [item["charCount"] for item in items],
        "healthStatus": health_status,
        "health": health,
        "readyStatus": ready_status,
        "ready": ready,
        "summarizeHttpStatus": http_status,
        "topStatus": response_data.get("status"),
        "resultCount": len(results),
        "resultIds": [item.get("id") for item in results],
        "resultStatuses": [item.get("status") for item in results],
        "keyPointCounts": [len(item.get("keyPoints", [])) for item in results],
        "elapsedSeconds": round(elapsed, 3),
        "meta": response_data.get("meta"),
    }

    artifact_inputs = items
    if not args.include_input_text:
        artifact_inputs = [
            {
                "id": item["id"],
                "sourceLine": item["sourceLine"],
                "charCount": item["charCount"],
            }
            for item in items
        ]

    artifact = write_result(
        output_dir,
        {
            "summary": summary,
            "inputs": artifact_inputs,
            "response": response_data,
        },
    )

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"Saved result artifact: {artifact}")

    if http_status != 200 or response_data.get("status") != "ok":
        return 1
    if len(results) != len(items):
        return 1
    if any(item.get("status") != "ok" for item in results):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
