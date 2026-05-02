import argparse
import json
import os
from typing import Any, Dict, List, Tuple


def _fail(msg: str) -> None:
    raise SystemExit(msg)


def validate_sft_line(obj: Dict[str, Any], line_no: int) -> None:
    if "messages" not in obj or not isinstance(obj["messages"], list):
        _fail(f"Line {line_no}: missing/invalid 'messages' list")
    msgs = obj["messages"]
    if len(msgs) != 3:
        _fail(f"Line {line_no}: messages length != 3 (got {len(msgs)})")
    roles = [m.get("role") for m in msgs]
    if roles != ["system", "user", "assistant"]:
        _fail(f"Line {line_no}: roles must be ['system','user','assistant'] (got {roles})")
    for i, m in enumerate(msgs):
        if "content" not in m or not isinstance(m["content"], str):
            _fail(f"Line {line_no}: messages[{i}].content must be string")

    # Assistant content must be JSON with exact keys
    try:
        a = json.loads(msgs[2]["content"])
    except Exception as e:
        _fail(f"Line {line_no}: assistant content not valid JSON: {e!r}")
    if not isinstance(a, dict):
        _fail(f"Line {line_no}: assistant JSON must be object")
    if set(a.keys()) != {"main_idea", "key_points"}:
        _fail(f"Line {line_no}: assistant JSON keys must be exactly {{main_idea,key_points}} (got {set(a.keys())})")
    if not isinstance(a["main_idea"], str) or not a["main_idea"].strip():
        _fail(f"Line {line_no}: main_idea must be non-empty string")
    if not isinstance(a["key_points"], list) or len(a["key_points"]) != 3:
        _fail(f"Line {line_no}: key_points must be list with exactly 3 items")
    if any((not isinstance(x, str) or not x.strip()) for x in a["key_points"]):
        _fail(f"Line {line_no}: key_points items must be non-empty strings")


def validate_file(path: str, expected_lines: int = 0) -> Tuple[int, int]:
    n = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            n += 1
            try:
                obj = json.loads(line)
            except Exception as e:
                _fail(f"Line {n}: not valid JSONL: {e!r}")
            validate_sft_line(obj, n)

    if expected_lines and n != expected_lines:
        _fail(f"Expected {expected_lines} lines, got {n}")
    return n, 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", required=True, type=str)
    ap.add_argument("--expected-lines", type=int, default=0)
    args = ap.parse_args()

    path = args.path
    if not os.path.exists(path):
        _fail(f"File not found: {path}")

    n, _ = validate_file(path, expected_lines=args.expected_lines)
    print(f"OK: {n} rows valid: {path}")


if __name__ == "__main__":
    main()
