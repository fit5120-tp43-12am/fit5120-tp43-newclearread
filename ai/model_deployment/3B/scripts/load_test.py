#!/usr/bin/env python3
import argparse
import json
import os
import time
from urllib import request


BASE_URL = os.environ.get("CLEARREAD_AI_SUMMARY_API_URL", "http://127.0.0.1:8010").rstrip("/")
API_KEY = os.environ.get("CLEARREAD_AI_SUMMARY_API_KEY", "")

SAMPLE_TEXT = (
    "A rubric explains how marks are awarded for structure, evidence, clarity, and referencing. "
    "It helps students understand what a strong answer includes before they submit work. "
    "Teachers can use the same rubric to give consistent feedback and make expectations clearer."
)


def post_batch(block_count: int) -> tuple[float, int, dict]:
    payload = {
        "requestId": f"load-test-{block_count}",
        "texts": [
            {"id": f"block-{idx + 1}", "text": f"{SAMPLE_TEXT} Block number {idx + 1}."}
            for idx in range(block_count)
        ],
        "options": {"includeDebug": False},
    }
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        f"{BASE_URL}/v1/clearread/summarize",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
        },
        method="POST",
    )
    started = time.perf_counter()
    with request.urlopen(req, timeout=240) as response:
        data = json.loads(response.read().decode("utf-8"))
        elapsed = time.perf_counter() - started
        return elapsed, response.status, data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--blocks", nargs="+", type=int, default=[1, 4, 8, 16, 32])
    args = parser.parse_args()

    rows = []
    for count in args.blocks:
        elapsed, status, data = post_batch(count)
        results = data.get("results", [])
        ok_count = sum(1 for item in results if item.get("status") == "ok")
        rows.append(
            {
                "blocks": count,
                "httpStatus": status,
                "topStatus": data.get("status"),
                "okCount": ok_count,
                "errorCount": len(results) - ok_count,
                "elapsedSeconds": round(elapsed, 3),
            }
        )
        print(json.dumps(rows[-1], indent=2))

    print(json.dumps({"baseUrl": BASE_URL, "runs": rows}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
