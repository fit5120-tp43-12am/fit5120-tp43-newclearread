#!/usr/bin/env python3
"""
Validate an SFT JSONL file with the expected "messages" structure and
assistant JSON schema: {"main_idea": str, "key_points": [str,...]}.

Usage:
  py -3 validate_sft_jsonl.py --path public_service_200_sft.jsonl --expected-lines 200
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def iter_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_no}: {exc}") from exc
    return rows


def validate_assistant_content_json(s: str) -> None:
    try:
        obj = json.loads(s)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Assistant content is not valid JSON: {exc}") from exc
    if not isinstance(obj, dict):
        raise ValueError("Assistant JSON is not an object.")
    if set(obj.keys()) != {"main_idea", "key_points"}:
        raise ValueError(f"Assistant JSON keys must be exactly main_idea,key_points. Got: {sorted(obj.keys())}")
    if not isinstance(obj["main_idea"], str) or not obj["main_idea"].strip():
        raise ValueError("main_idea must be a non-empty string.")
    if not isinstance(obj["key_points"], list) or not obj["key_points"]:
        raise ValueError("key_points must be a non-empty list.")
    if not all(isinstance(x, str) and x.strip() for x in obj["key_points"]):
        raise ValueError("Each key_points item must be a non-empty string.")


def validate_row(row: dict[str, Any]) -> None:
    msgs = row.get("messages")
    if not isinstance(msgs, list) or len(msgs) != 3:
        raise ValueError("messages must be a list of length 3.")
    roles = [m.get("role") for m in msgs]
    if roles != ["system", "user", "assistant"]:
        raise ValueError(f"roles must be [system,user,assistant]. Got: {roles}")
    for m in msgs:
        if not isinstance(m.get("content"), str):
            raise ValueError("Each message content must be a string.")
    validate_assistant_content_json(msgs[2]["content"])


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--path", type=Path, required=True)
    p.add_argument("--expected-lines", type=int, default=0)
    args = p.parse_args()

    if not args.path.is_file():
        print(f"File not found: {args.path}", file=sys.stderr)
        return 1

    rows = iter_jsonl(args.path)
    if args.expected_lines and len(rows) != args.expected_lines:
        print(f"Line count mismatch: got {len(rows)}, expected {args.expected_lines}", file=sys.stderr)
        return 2

    for i, row in enumerate(rows, start=1):
        try:
            validate_row(row)
        except Exception as exc:  # noqa: BLE001
            print(f"Validation failed at row {i}: {exc}", file=sys.stderr)
            return 3

    print(f"OK: {len(rows)} rows valid: {args.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
