#!/usr/bin/env python3
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

GENERATION_SYSTEM_PROMPT = """You are an expert reading-support assistant for students with dyslexia.

Your task is to read one academic-paper excerpt and produce a short, faithful summary in simple English.

STRICT RULES:
1. Return ONLY a valid JSON object.
2. The JSON must contain exactly:
   - "main_idea": 2 to 3 short sentences
   - "key_points": an array of 3 short strings
3. Keep the language clear, simple, and short.
4. Do not add information that is not supported by the source text.
5. If the paper is dense, focus on the main finding, method, or claim, and the most important supporting details.
6. Do not mention citations, table numbers, figure numbers, or section numbers unless they are necessary to the meaning."""

SFT_SYSTEM_PROMPT = """You are a reading support assistant for students with dyslexia.
Your task is to produce a quick summary of dense academic or public-information text.
Return only valid JSON with this schema:
{
  "main_idea": "2 to 3 short sentences",
  "key_points": ["point 1", "point 2", "point 3"]
}
Keep the language clear, simple, and short.
Do not add information that is not supported by the source text."""

OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "main_idea": {
            "type": "string",
            "description": "A short plain-language explanation of the main idea in 2 to 3 short sentences.",
        },
        "key_points": {
            "type": "array",
            "description": "Three short key facts or takeaways from the text.",
            "items": {"type": "string"},
            "minItems": 3,
            "maxItems": 3,
        },
    },
    "required": ["main_idea", "key_points"],
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
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
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


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


def validate_output(obj: dict[str, Any]) -> None:
    if not isinstance(obj, dict):
        raise ValueError("Model output is not a JSON object.")
    if set(obj.keys()) != {"main_idea", "key_points"}:
        raise ValueError(f"Unexpected output keys: {sorted(obj.keys())}")
    if not isinstance(obj["main_idea"], str) or not obj["main_idea"].strip():
        raise ValueError("main_idea must be a non-empty string.")
    if not isinstance(obj["key_points"], list) or len(obj["key_points"]) != 3:
        raise ValueError("key_points must be a list of exactly 3 strings.")
    if not all(isinstance(x, str) and x.strip() for x in obj["key_points"]):
        raise ValueError("Every key_points item must be a non-empty string.")


def parse_response_json(response_obj: dict[str, Any]) -> dict[str, Any]:
    if response_obj.get("status") == "incomplete":
        raise RuntimeError("Response was incomplete.")

    for item in response_obj.get("output", []):
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

    output_text = response_obj.get("output_text")
    if output_text:
        parsed = json.loads(output_text)
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
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        request = urllib.request.Request(API_URL, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                body = response.read().decode("utf-8")
            return parse_response_json(json.loads(body))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            try:
                error_obj = json.loads(body)
            except Exception:
                error_obj = None

            code = None
            message = None
            if isinstance(error_obj, dict):
                error_data = error_obj.get("error")
                if isinstance(error_data, dict):
                    code = error_data.get("code")
                    message = error_data.get("message")

            if exc.code == 429 and code == "insufficient_quota":
                raise RuntimeError(
                    "OpenAI API returned insufficient_quota. "
                    f"Fix billing/credits and rerun. Details: {message or body}"
                ) from exc

            last_error = RuntimeError(f"HTTP {exc.code}: {body}")
        except Exception as exc:
            last_error = exc

        if attempt < max_retries:
            time.sleep(min(2**attempt, 15))

    raise RuntimeError(f"OpenAI request failed after {max_retries} attempts: {last_error}")


def build_raw_record(sample: dict[str, Any], target: dict[str, Any], model: str) -> dict[str, Any]:
    return {
        "sample_index": sample["sample_index"],
        "domain_key": sample["domain_key"],
        "domain_label": sample["domain_label"],
        "bucket": sample["bucket"],
        "word_count": sample["word_count"],
        "paper_id": sample["paper_id"],
        "title": sample["title"],
        "source_url": sample["source_url"],
        "source_license": sample["source_license"],
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
    base_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Generate SFT outputs for academic-paper samples.")
    parser.add_argument("--input", type=Path, default=base_dir / "academic_paper_500_samples.jsonl")
    parser.add_argument("--raw-output", type=Path, default=base_dir / "academic_paper_500_outputs.jsonl")
    parser.add_argument("--sft-output", type=Path, default=base_dir / "academic_paper_500_sft.jsonl")
    parser.add_argument("--meta-output", type=Path, default=base_dir / "academic_paper_500_sft.meta.json")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--timeout-seconds", type=int, default=120)
    parser.add_argument("--max-retries", type=int, default=4)
    parser.add_argument("--overwrite", action="store_true")
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
    generated_now = 0
    reused_existing = 0

    for idx, sample in enumerate(samples, start=1):
        sample_index = int(sample["sample_index"])
        if sample_index in existing:
            raw_records.append(existing[sample_index])
            reused_existing += 1
            print(f"[{idx}/{len(samples)}] reused sample {sample_index}")
            continue

        print(f"[{idx}/{len(samples)}] generating sample {sample_index}: {sample.get('title', '')}")
        target = call_openai(
            api_key=api_key,
            model=args.model,
            source_text=sample["text"],
            timeout_seconds=args.timeout_seconds,
            max_retries=args.max_retries,
        )
        raw_records.append(build_raw_record(sample, target, args.model))
        generated_now += 1

        merged = {int(row["sample_index"]): row for row in raw_records}
        for old_index, old_row in existing.items():
            merged.setdefault(old_index, old_row)
        ordered = [merged[int(s["sample_index"])] for s in samples if int(s["sample_index"]) in merged]
        write_jsonl(args.raw_output, ordered)

    merged = {int(row["sample_index"]): row for row in raw_records}
    for old_index, old_row in existing.items():
        merged.setdefault(old_index, old_row)

    final_raw = [merged[int(sample["sample_index"])] for sample in samples]
    write_jsonl(args.raw_output, final_raw)

    sft_rows = [build_sft_record(sample, merged[int(sample["sample_index"])]["target"]) for sample in samples]
    write_jsonl(args.sft_output, sft_rows)

    meta = {
        "input_file": str(args.input.resolve()),
        "raw_output_file": str(args.raw_output.resolve()),
        "sft_output_file": str(args.sft_output.resolve()),
        "model": args.model,
        "total_samples": len(samples),
        "generated_now": generated_now,
        "reused_existing": reused_existing,
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
