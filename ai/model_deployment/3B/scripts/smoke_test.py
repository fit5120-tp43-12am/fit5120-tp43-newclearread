#!/usr/bin/env python3
import json
import os
import sys
import time
from urllib import request, error


BASE_URL = os.environ.get("CLEARREAD_AI_SUMMARY_API_URL", "http://127.0.0.1:8010").rstrip("/")
API_KEY = os.environ.get("CLEARREAD_AI_SUMMARY_API_KEY", "")


def get_json(path: str) -> dict:
    with request.urlopen(f"{BASE_URL}{path}", timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def post_json(path: str, payload: dict) -> tuple[int, dict]:
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        f"{BASE_URL}{path}",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=120) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def main() -> int:
    started = time.perf_counter()
    print("BASE_URL", BASE_URL)
    print("health", json.dumps(get_json("/health"), indent=2))
    print("ready", json.dumps(get_json("/ready"), indent=2))

    status, data = post_json(
        "/v1/clearread/summarize",
        {
            "requestId": "smoke-test-001",
            "texts": [
                {
                    "id": "block-1",
                    "text": "Photosynthesis lets plants use sunlight, water, and carbon dioxide to make glucose and oxygen."
                }
            ],
            "options": {"includeDebug": False},
        },
    )
    print("summarize_status", status)
    print(json.dumps(data, indent=2))
    elapsed = time.perf_counter() - started
    print("elapsed_seconds", round(elapsed, 3))

    if status != 200:
        return 1
    if data.get("status") != "ok":
        return 1
    result = data.get("results", [{}])[0]
    if result.get("status") != "ok" or not result.get("summary") or not result.get("keyPoints"):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
