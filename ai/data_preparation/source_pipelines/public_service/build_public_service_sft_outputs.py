#!/usr/bin/env python3
"""
Generate dyslexia-friendly structured summaries for the sampled public-service texts
and export SFT-ready JSONL in the "messages" format.

Input:
  - public_service_200_samples.jsonl (from extract_wikihow_public_service_samples.py)

Output:
  1) public_service_200_outputs.jsonl  (raw targets + metadata per sample)
  2) public_service_200_sft.jsonl      (messages[system,user,assistant])
  3) public_service_200_sft.meta.json  (run metadata)

Two modes:
  - openai  : use OpenAI Responses API with Structured Outputs (JSON Schema)
  - offline : create a simple, deterministic summary without network/API

Usage:
  set OPENAI_API_KEY=...
  py -3 build_public_service_sft_outputs.py --mode openai --model gpt-4o-mini

  py -3 build_public_service_sft_outputs.py --mode offline
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


API_URL = "https://api.openai.com/v1/responses"
DEFAULT_MODEL = "gpt-4o-mini"


SFT_SYSTEM_PROMPT = """You are a reading support assistant for students with dyslexia.
Your task is to produce a quick summary of dense academic or public-information text.
Return only valid JSON with this schema:
{
  "main_idea": "2 to 3 short sentences",
  "key_points": ["short point 1", "short point 2", "..."]
}
Keep the language clear, simple, and short.
Use a short list of key points.
Do not add information that is not supported by the source text."""


GENERATION_SYSTEM_PROMPT = """You are a reading support assistant for students with dyslexia.
Your task is to produce a quick summary of dense public-information or process text.

STRICT RULES:
1) Return ONLY valid JSON (no markdown, no extra text).
2) The JSON must contain exactly:
   - "main_idea": 2 to 3 short sentences in plain English.
   - "key_points": a list of short bullet points (strings).
3) Be faithful: do not add facts not in the source.
4) Keep language simple and short."""


OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "main_idea": {"type": "string"},
        "key_points": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["main_idea", "key_points"],
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_no} of {path}: {exc}") from exc
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def compact_json(obj: dict[str, Any]) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def validate_output(obj: dict[str, Any]) -> None:
    if not isinstance(obj, dict):
        raise ValueError("Output is not a JSON object.")
    if set(obj.keys()) != {"main_idea", "key_points"}:
        raise ValueError(f"Unexpected output keys: {sorted(obj.keys())}")
    if not isinstance(obj["main_idea"], str) or not obj["main_idea"].strip():
        raise ValueError("main_idea must be a non-empty string.")
    if not isinstance(obj["key_points"], list) or not obj["key_points"]:
        raise ValueError("key_points must be a non-empty list.")
    if not all(isinstance(x, str) and x.strip() for x in obj["key_points"]):
        raise ValueError("Every key_points item must be a non-empty string.")


def build_request_payload(model: str, source_text: str) -> dict[str, Any]:
    return {
        "model": model,
        "input": [
            {"role": "system", "content": GENERATION_SYSTEM_PROMPT},
            {"role": "user", "content": source_text},
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "dyslexia_summary",
                "strict": True,
                "schema": OUTPUT_SCHEMA,
            }
        },
    }


def parse_response_json(response_obj: dict[str, Any]) -> dict[str, Any]:
    if response_obj.get("status") == "incomplete":
        raise RuntimeError("Response was incomplete.")

    for item in response_obj.get("output", []) or []:
        if item.get("type") != "message":
            continue
        for content in item.get("content", []) or []:
            refusal = content.get("refusal")
            if refusal:
                raise RuntimeError(f"Model refusal: {refusal}")
            text = content.get("text")
            if text:
                parsed = json.loads(text)
                validate_output(parsed)
                return parsed

    if response_obj.get("output_text"):
        parsed = json.loads(response_obj["output_text"])
        validate_output(parsed)
        return parsed

    raise RuntimeError("Could not find structured JSON text in API response.")


def call_openai(
    api_key: str,
    model: str,
    source_text: str,
    timeout_seconds: int,
    max_retries: int,
) -> dict[str, Any]:
    payload = build_request_payload(model, source_text)
    data = json.dumps(payload).encode("utf-8")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        req = urllib.request.Request(API_URL, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
                body = resp.read().decode("utf-8")
            return parse_response_json(json.loads(body))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            try:
                err_obj = json.loads(body)
            except Exception:  # noqa: BLE001
                err_obj = None
            code = None
            message = None
            if isinstance(err_obj, dict) and isinstance(err_obj.get("error"), dict):
                code = err_obj["error"].get("code")
                message = err_obj["error"].get("message")
            if exc.code == 429 and code == "insufficient_quota":
                raise RuntimeError(
                    "OpenAI API returned insufficient_quota (billing/credits not available). "
                    f"Details: {message or body}"
                ) from exc
            last_error = RuntimeError(f"HTTP {exc.code}: {body}")
        except Exception as exc:  # noqa: BLE001
            last_error = exc

        if attempt < max_retries:
            time.sleep(min(2**attempt, 15))

    raise RuntimeError(f"OpenAI request failed after {max_retries} attempts: {last_error}")


def offline_summarize(source_text: str, max_points: int = 8) -> dict[str, Any]:
    """
    Deterministic, no-dependency fallback. Produces a faithful but simple output by
    extracting the first 2–3 sentences and a few short key lines.
    """
    text = re.sub(r"\s+", " ", (source_text or "")).strip()
    if not text:
        return {"main_idea": "This text is empty.", "key_points": ["No details were provided."]}

    # Sentence split (lightweight)
    sents = re.split(r"(?<=[.!?])\s+", text)
    main = " ".join([s for s in sents[:3] if s][:3]).strip()
    if not main:
        main = text[:240].strip()

    # Key points: pick short-ish clauses that look like instructions or requirements
    candidates: list[str] = []
    for s in sents:
        s = s.strip()
        if not s:
            continue
        if len(s.split()) > 28:
            continue
        if any(w in s.lower() for w in ["must", "need to", "required", "require", "apply", "eligib", "fee", "submit"]):
            candidates.append(s)
        if len(candidates) >= max_points:
            break

    if not candidates:
        candidates = [s.strip() for s in sents[1: max_points + 1] if s.strip()]
        candidates = [c for c in candidates if 3 <= len(c.split()) <= 28][:max_points]

    if not candidates:
        candidates = [text[:120].strip()]

    out = {"main_idea": main, "key_points": candidates[:max_points]}
    validate_output(out)
    return out


def build_raw_record(sample: dict[str, Any], target: dict[str, Any], generator: dict[str, Any]) -> dict[str, Any]:
    return {
        "sample_index": sample["sample_index"],
        "bucket": sample.get("bucket"),
        "word_count": sample.get("word_count"),
        "wikihow_id": sample.get("wikihow_id", ""),
        "title": sample.get("title", ""),
        "category": sample.get("category", ""),
        "source_url": sample.get("source_url", ""),
        "generator": generator,
        "input_text": sample["text"],
        "target": target,
    }


def build_sft_record(sample: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    return {
        "messages": [
            {"role": "system", "content": SFT_SYSTEM_PROMPT},
            {"role": "user", "content": sample["text"]},
            {"role": "assistant", "content": compact_json(target)},
        ]
    }


def load_existing_by_index(path: Path) -> dict[int, dict[str, Any]]:
    if not path.exists():
        return {}
    rows = load_jsonl(path)
    by_idx: dict[int, dict[str, Any]] = {}
    for r in rows:
        by_idx[int(r["sample_index"])] = r
    return by_idx


def parse_args() -> argparse.Namespace:
    base_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=base_dir / "public_service_200_samples.jsonl",
        help="Input samples JSONL.",
    )
    parser.add_argument(
        "--raw-output",
        type=Path,
        default=base_dir / "public_service_200_outputs.jsonl",
        help="Raw outputs JSONL (targets + metadata).",
    )
    parser.add_argument(
        "--sft-output",
        type=Path,
        default=base_dir / "public_service_200_sft.jsonl",
        help="Final SFT JSONL (messages).",
    )
    parser.add_argument(
        "--meta-output",
        type=Path,
        default=base_dir / "public_service_200_sft.meta.json",
        help="Run metadata JSON.",
    )
    parser.add_argument("--mode", choices=["openai", "offline"], default="openai")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="OpenAI model name (mode=openai).")
    parser.add_argument("--limit", type=int, default=0, help="Only process first N samples.")
    parser.add_argument("--timeout-seconds", type=int, default=120)
    parser.add_argument("--max-retries", type=int, default=4)
    parser.add_argument("--overwrite", action="store_true", help="Regenerate even if raw output exists.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.input.is_file():
        print(f"Input file not found: {args.input}", file=sys.stderr)
        return 1

    samples = load_jsonl(args.input)
    if args.limit and args.limit > 0:
        samples = samples[: args.limit]

    existing = {} if args.overwrite else load_existing_by_index(args.raw_output)
    raw_records: list[dict[str, Any]] = []
    generated = 0
    reused = 0

    api_key = os.environ.get("OPENAI_API_KEY") if args.mode == "openai" else None
    if args.mode == "openai" and not api_key:
        print("Missing OPENAI_API_KEY environment variable (mode=openai).", file=sys.stderr)
        return 2

    for i, sample in enumerate(samples, start=1):
        sample_index = int(sample["sample_index"])
        if sample_index in existing:
            raw_records.append(existing[sample_index])
            reused += 1
            print(f"[{i}/{len(samples)}] reused sample {sample_index}")
            continue

        print(f"[{i}/{len(samples)}] generating sample {sample_index}: {sample.get('title', '')}")
        if args.mode == "offline":
            target = offline_summarize(sample["text"])
            generator = {"mode": "offline", "name": "heuristic_v1"}
        else:
            target = call_openai(
                api_key=api_key or "",
                model=args.model,
                source_text=sample["text"],
                timeout_seconds=args.timeout_seconds,
                max_retries=args.max_retries,
            )
            generator = {"mode": "openai", "model": args.model, "api": "responses", "schema": OUTPUT_SCHEMA}

        record = build_raw_record(sample, target, generator)
        raw_records.append(record)
        generated += 1

        # Save incrementally so long runs can resume safely
        merged = {int(r["sample_index"]): r for r in raw_records}
        for idx, row in existing.items():
            merged.setdefault(idx, row)
        ordered = [merged[int(s["sample_index"])] for s in samples if int(s["sample_index"]) in merged]
        write_jsonl(args.raw_output, ordered)

    merged_by_index = {int(r["sample_index"]): r for r in raw_records}
    for idx, row in existing.items():
        merged_by_index.setdefault(idx, row)

    final_raw = [merged_by_index[int(s["sample_index"])] for s in samples]
    write_jsonl(args.raw_output, final_raw)

    sft_rows = [build_sft_record(s, merged_by_index[int(s["sample_index"])]["target"]) for s in samples]
    write_jsonl(args.sft_output, sft_rows)

    meta = {
        "input_file": str(args.input.resolve()),
        "raw_output_file": str(args.raw_output.resolve()),
        "sft_output_file": str(args.sft_output.resolve()),
        "mode": args.mode,
        "model": args.model if args.mode == "openai" else None,
        "total_samples": len(samples),
        "generated_now": generated,
        "reused_existing": reused,
        "schema": OUTPUT_SCHEMA,
    }
    args.meta_output.parent.mkdir(parents=True, exist_ok=True)
    args.meta_output.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote raw outputs to {args.raw_output}")
    print(f"Wrote SFT dataset to {args.sft_output}")
    print(f"Wrote metadata to {args.meta_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
