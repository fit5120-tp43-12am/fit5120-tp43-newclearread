#!/usr/bin/env python3
"""
Generate target outputs for MedlinePlus input samples and export SFT-ready JSONL.

Input:
  - One JSON object per line from medlineplus_250_english_samples.jsonl

Output:
  1. A raw targets JSONL with the model-produced structured summary for each sample
  2. An SFT JSONL where each row has:
       {"messages": [{"role": "system", ...}, {"role": "user", ...}, {"role": "assistant", ...}]}

This script uses the OpenAI Responses API with Structured Outputs (JSON Schema)
so each model response is constrained to:
  {"main_idea": "...", "key_points": ["...", "..."]}

Usage:
  set OPENAI_API_KEY=...
  py build_medlineplus_sft_outputs.py

  py build_medlineplus_sft_outputs.py --model gpt-4o-mini --limit 10
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


API_URL = "https://api.openai.com/v1/responses"
DEFAULT_MODEL = "gpt-4o-mini"

GENERATION_SYSTEM_PROMPT = """You are an expert text simplification assistant specializing in adapting complex public information into highly accessible, dyslexia-friendly summaries.

Your task is to read the provided source text and extract its core message and essential details.

STRICT RULES:
1. OUTPUT FORMAT: You must output ONLY a valid JSON object. Do not include markdown formatting like ```json or any conversational filler.
2. JSON STRUCTURE: The JSON must contain exactly two keys:
   - "main_idea": A short, single paragraph (1-3 sentences) written in very simple, plain language that captures the primary concept of the text.
   - "key_points": A list of strings (bullet points). Extract only the most crucial actionable or factual points. Keep sentences extremely short and direct.
3. Use simple and easy understand word.
4. FAITHFULNESS: Do not invent, hallucinate, or add any facts not explicitly stated in the source text.
5. COMPRESSION: The output MUST be significantly shorter than the original text. Strip away academic jargon, redundant examples, and complex sentence structures.

If the source text is long, focus only on its most important ideas and the most useful facts for a reader who needs clear support."""

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

OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "main_idea": {
            "type": "string",
            "description": "A short plain-language explanation of the main idea in 1 to 3 sentences.",
        },
        "key_points": {
            "type": "array",
            "description": "A short list of crucial facts or actions from the text.",
            "items": {"type": "string"},
        },
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

    output_items = response_obj.get("output", [])
    for item in output_items:
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            refusal = content.get("refusal")
            if refusal:
                raise RuntimeError(f"Model refusal: {refusal}")
            text = content.get("text")
            if text:
                parsed = json.loads(text)
                validate_output(parsed)
                return parsed

    if "output_text" in response_obj and response_obj["output_text"]:
        parsed = json.loads(response_obj["output_text"])
        validate_output(parsed)
        return parsed

    raise RuntimeError("Could not find structured JSON text in API response.")


def validate_output(obj: dict[str, Any]) -> None:
    if not isinstance(obj, dict):
        raise ValueError("Model output is not a JSON object.")
    if set(obj.keys()) != {"main_idea", "key_points"}:
        raise ValueError(f"Unexpected output keys: {sorted(obj.keys())}")
    if not isinstance(obj["main_idea"], str) or not obj["main_idea"].strip():
        raise ValueError("main_idea must be a non-empty string.")
    if not isinstance(obj["key_points"], list) or not obj["key_points"]:
        raise ValueError("key_points must be a non-empty list.")
    if not all(isinstance(x, str) and x.strip() for x in obj["key_points"]):
        raise ValueError("Every key_points item must be a non-empty string.")


def call_openai(
    api_key: str,
    model: str,
    source_text: str,
    timeout_seconds: int,
    max_retries: int,
) -> dict[str, Any]:
    payload = build_request_payload(model, source_text)
    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        request = urllib.request.Request(API_URL, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as resp:
                body = resp.read().decode("utf-8")
            response_obj = json.loads(body)
            return parse_response_json(response_obj)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            # Try to parse OpenAI error payload for clearer handling.
            try:
                err_obj = json.loads(body)
            except Exception:  # noqa: BLE001
                err_obj = None

            code = None
            message = None
            if isinstance(err_obj, dict):
                err = err_obj.get("error")
                if isinstance(err, dict):
                    code = err.get("code")
                    message = err.get("message")

            # Quota/billing errors will never succeed by retrying.
            if exc.code == 429 and code == "insufficient_quota":
                raise RuntimeError(
                    "OpenAI API returned insufficient_quota (billing/credits not available for this key/project). "
                    "Fix billing/credits and rerun; this is not a rate-limit and retries won't help. "
                    f"Details: {message or body}"
                ) from exc

            last_error = RuntimeError(f"HTTP {exc.code}: {body}")
        except Exception as exc:  # noqa: BLE001
            last_error = exc

        if attempt < max_retries:
            time.sleep(min(2**attempt, 15))

    raise RuntimeError(f"OpenAI request failed after {max_retries} attempts: {last_error}")


def build_raw_record(sample: dict[str, Any], target: dict[str, Any], model: str) -> dict[str, Any]:
    return {
        "sample_index": sample["sample_index"],
        "bucket": sample["bucket"],
        "word_count": sample["word_count"],
        "medlineplus_topic_id": sample["medlineplus_topic_id"],
        "title": sample["title"],
        "source_url": sample["source_url"],
        "generator_model": model,
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
    return {int(row["sample_index"]): row for row in rows}


def parse_args() -> argparse.Namespace:
    base_dir = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=base_dir / "data" / "medlineplus_250_english_samples.jsonl",
        help="Path to input JSONL created by the extraction script.",
    )
    parser.add_argument(
        "--raw-output",
        type=Path,
        default=base_dir / "data" / "medlineplus_250_english_outputs.jsonl",
        help="Path for per-sample raw target outputs.",
    )
    parser.add_argument(
        "--sft-output",
        type=Path,
        default=base_dir / "data" / "medlineplus_250_english_sft.jsonl",
        help="Path for final SFT JSONL.",
    )
    parser.add_argument(
        "--meta-output",
        type=Path,
        default=base_dir / "data" / "medlineplus_250_english_sft.meta.json",
        help="Path for metadata about this run.",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help="OpenAI model name.")
    parser.add_argument("--limit", type=int, default=0, help="Only process the first N samples.")
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=120,
        help="HTTP timeout for each API call.",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=4,
        help="Retry count per sample when the API fails.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Ignore existing raw outputs and regenerate all rows.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Missing OPENAI_API_KEY environment variable.", file=sys.stderr)
        return 2

    if not args.input.is_file():
        print(f"Input file not found: {args.input}", file=sys.stderr)
        return 1

    samples = load_jsonl(args.input)
    if args.limit > 0:
        samples = samples[: args.limit]

    existing = {} if args.overwrite else load_existing_by_index(args.raw_output)
    raw_records: list[dict[str, Any]] = []
    generated = 0
    reused = 0

    for i, sample in enumerate(samples, start=1):
        sample_index = int(sample["sample_index"])
        if sample_index in existing:
            raw_records.append(existing[sample_index])
            reused += 1
            print(f"[{i}/{len(samples)}] reused sample {sample_index}")
            continue

        print(f"[{i}/{len(samples)}] generating sample {sample_index}: {sample.get('title', '')}")
        target = call_openai(
            api_key=api_key,
            model=args.model,
            source_text=sample["text"],
            timeout_seconds=args.timeout_seconds,
            max_retries=args.max_retries,
        )
        record = build_raw_record(sample, target, args.model)
        raw_records.append(record)
        generated += 1

        # Save incrementally so long runs can resume safely.
        ordered = sorted(raw_records + [row for idx, row in existing.items() if idx not in {r["sample_index"] for r in raw_records}], key=lambda x: int(x["sample_index"]))
        write_jsonl(args.raw_output, ordered)

    merged_by_index = {int(row["sample_index"]): row for row in raw_records}
    for idx, row in existing.items():
        merged_by_index.setdefault(idx, row)

    final_raw = [merged_by_index[int(sample["sample_index"])] for sample in samples]
    write_jsonl(args.raw_output, final_raw)

    sft_rows = [build_sft_record(sample, merged_by_index[int(sample["sample_index"])]["target"]) for sample in samples]
    write_jsonl(args.sft_output, sft_rows)

    meta = {
        "input_file": str(args.input.resolve()),
        "raw_output_file": str(args.raw_output.resolve()),
        "sft_output_file": str(args.sft_output.resolve()),
        "model": args.model,
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
