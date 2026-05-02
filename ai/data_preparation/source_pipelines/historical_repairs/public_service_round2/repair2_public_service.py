#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any


MODEL = "gpt-4o-mini"
API_URL = "https://api.openai.com/v1/responses"
ROW_INDEX = 137
STRICT_INDEX = 197

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

SOURCE_FIELDS = (
    "bucket",
    "word_count",
    "wikihow_id",
    "title",
    "category",
    "source_url",
    "text",
)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def compact_json(obj: dict[str, Any]) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def validate_output(obj: dict[str, Any]) -> None:
    if set(obj.keys()) != {"main_idea", "key_points"}:
        raise ValueError(f"Unexpected output keys: {sorted(obj.keys())}")
    if not isinstance(obj["main_idea"], str) or not obj["main_idea"].strip():
        raise ValueError("main_idea must be a non-empty string.")
    if not isinstance(obj["key_points"], list) or not obj["key_points"]:
        raise ValueError("key_points must be a non-empty list.")
    if not all(isinstance(item, str) and item.strip() for item in obj["key_points"]):
        raise ValueError("Every key_points item must be a non-empty string.")


def build_request_payload(source_text: str) -> dict[str, Any]:
    return {
        "model": MODEL,
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


def call_openai(api_key: str, source_text: str, timeout_seconds: int = 120, max_retries: int = 4) -> dict[str, Any]:
    payload = build_request_payload(source_text)
    data = json.dumps(payload).encode("utf-8")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        request = urllib.request.Request(API_URL, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                body = response.read().decode("utf-8")
            return parse_response_json(json.loads(body))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            last_error = RuntimeError(f"HTTP {exc.code}: {body}")
        except Exception as exc:  # noqa: BLE001
            last_error = exc

        if attempt < max_retries:
            time.sleep(min(2**attempt, 15))

    raise RuntimeError(f"OpenAI request failed after {max_retries} attempts: {last_error}")


def build_raw_record(sample: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    return {
        "sample_index": sample["sample_index"],
        "bucket": sample.get("bucket"),
        "word_count": sample.get("word_count"),
        "wikihow_id": sample.get("wikihow_id", ""),
        "title": sample.get("title", ""),
        "category": sample.get("category", ""),
        "source_url": sample.get("source_url", ""),
        "generator": {"mode": "openai", "model": MODEL, "api": "responses", "schema": OUTPUT_SCHEMA},
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


def find_dataset_dir(data_root: Path) -> Path:
    matches = list(data_root.rglob("public_service_200_samples_reviewed.jsonl"))
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected exactly one public_service reviewed samples file under {data_root}, found {len(matches)}."
        )
    return matches[0].parent


def source_changed(before: dict[str, Any], after: dict[str, Any]) -> bool:
    return any(before.get(field) != after.get(field) for field in SOURCE_FIELDS)


def validate_alignment(
    samples: list[dict[str, Any]],
    outputs: list[dict[str, Any]],
    sft_rows: list[dict[str, Any]],
) -> None:
    if not (len(samples) == len(outputs) == len(sft_rows) == 200):
        raise RuntimeError("Expected samples, outputs, and SFT rows to each contain exactly 200 rows.")

    for index, (sample, output, sft_row) in enumerate(zip(samples, outputs, sft_rows, strict=True), start=1):
        if int(sample["sample_index"]) != index:
            raise RuntimeError(f"Sample row {index} has unexpected sample_index {sample['sample_index']}.")
        if int(output["sample_index"]) != index:
            raise RuntimeError(f"Output row {index} has unexpected sample_index {output['sample_index']}.")
        if output["input_text"] != sample["text"]:
            raise RuntimeError(f"Output/input mismatch at row {index}.")
        if output.get("bucket") != sample.get("bucket"):
            raise RuntimeError(f"Bucket mismatch at row {index}.")
        if output.get("word_count") != sample.get("word_count"):
            raise RuntimeError(f"Word-count mismatch at row {index}.")
        if output.get("title") != sample.get("title"):
            raise RuntimeError(f"Title mismatch at row {index}.")
        if not isinstance(sft_row.get("messages"), list) or len(sft_row["messages"]) != 3:
            raise RuntimeError(f"SFT row {index} has invalid messages structure.")
        user_content = sft_row["messages"][1]["content"]
        assistant_content = sft_row["messages"][2]["content"]
        if user_content != sample["text"]:
            raise RuntimeError(f"SFT user/source mismatch at row {index}.")
        parsed_assistant = json.loads(assistant_content)
        validate_output(parsed_assistant)
        if parsed_assistant != output["target"]:
            raise RuntimeError(f"SFT assistant/output mismatch at row {index}.")


def main() -> int:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Missing OPENAI_API_KEY environment variable.", file=sys.stderr)
        return 2

    worker_dir = Path(__file__).resolve().parent
    run_dir = worker_dir.parents[1]
    data_root = run_dir.parent
    dataset_dir = find_dataset_dir(data_root)

    samples_path = dataset_dir / "public_service_200_samples_reviewed.jsonl"
    outputs_path = dataset_dir / "public_service_200_outputs_reviewed.jsonl"
    sft_path = dataset_dir / "public_service_200_sft_reviewed.jsonl"
    meta_path = dataset_dir / "public_service_200_sft_reviewed.meta.json"
    review_map_path = dataset_dir / "public_service_200_review_map.json"
    strict_samples_path = dataset_dir / "public_service_200_samples_strict.jsonl"
    validator_path = dataset_dir / "validate_sft_jsonl.py"

    ledger_path = worker_dir / "ROUND2_REPAIR_LEDGER_public_service.jsonl"
    summary_path = worker_dir / "SUMMARY.md"

    samples = load_jsonl(samples_path)
    outputs = load_jsonl(outputs_path)
    sft_rows = load_jsonl(sft_path)
    strict_samples = load_jsonl(strict_samples_path)
    review_map = json.loads(review_map_path.read_text(encoding="utf-8"))
    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    original_samples = [dict(row) for row in samples]
    original_outputs = [dict(row) for row in outputs]
    before_bucket_counts = dict(Counter(row["bucket"] for row in samples))

    strict_by_index = {int(row["sample_index"]): row for row in strict_samples}
    replacement = strict_by_index[STRICT_INDEX]
    current = samples[ROW_INDEX - 1]

    if current["bucket"] != replacement["bucket"]:
        raise RuntimeError(
            f"Bucket mismatch for replacement row {ROW_INDEX}: current={current['bucket']} strict={replacement['bucket']}"
        )

    replacement_title = replacement["title"].strip().casefold()
    duplicate_titles = [
        row["sample_index"]
        for row in samples
        if row["sample_index"] != ROW_INDEX and row["title"].strip().casefold() == replacement_title
    ]
    if duplicate_titles:
        raise RuntimeError(f"Replacement title already exists in live dataset at rows {duplicate_titles}.")

    samples[ROW_INDEX - 1] = {
        **current,
        "sample_index": ROW_INDEX,
        "bucket": replacement["bucket"],
        "word_count": replacement["word_count"],
        "wikihow_id": replacement.get("wikihow_id", ""),
        "title": replacement.get("title", ""),
        "category": replacement.get("category", ""),
        "source_url": replacement.get("source_url", ""),
        "text": replacement["text"],
    }

    review_map[ROW_INDEX - 1] = {
        "sample_index": ROW_INDEX,
        "action": "replaced",
        "bucket": replacement["bucket"],
        "original_title": review_map[ROW_INDEX - 1]["original_title"],
        "final_title": replacement["title"],
        "replacement_from_strict_index": STRICT_INDEX,
    }

    target = call_openai(api_key=api_key, source_text=samples[ROW_INDEX - 1]["text"])
    outputs[ROW_INDEX - 1] = build_raw_record(samples[ROW_INDEX - 1], target)
    sft_rows[ROW_INDEX - 1] = build_sft_record(samples[ROW_INDEX - 1], target)

    replacement_rows = sorted({int(value) for value in meta.get("replacement_rows", [])} | {ROW_INDEX})
    replacement_sources = {str(key): value for key, value in meta.get("replacement_sources", {}).items()}
    replacement_sources[str(ROW_INDEX)] = STRICT_INDEX
    output_only_rows = [int(value) for value in meta.get("output_only_rows", []) if int(value) != ROW_INDEX]
    after_bucket_counts = dict(Counter(row["bucket"] for row in samples))

    meta.update(
        {
            "mode": "repair_openai_mixed_round2",
            "model": MODEL,
            "generated_now": len(replacement_rows) + len(meta.get("reextract_rows", [])) + len(output_only_rows),
            "reused_existing": len(samples) - (len(replacement_rows) + len(meta.get("reextract_rows", [])) + len(output_only_rows)),
            "replacement_rows": replacement_rows,
            "replacement_sources": replacement_sources,
            "output_only_rows": output_only_rows,
            "bucket_counts": after_bucket_counts,
            "round2_last_action": {
                "row_index": ROW_INDEX,
                "action_taken": "replace_same_dataset",
                "replacement_from_strict_index": STRICT_INDEX,
                "replacement_title": replacement["title"],
            },
        }
    )

    write_jsonl(samples_path, samples)
    write_jsonl(outputs_path, outputs)
    write_jsonl(sft_path, sft_rows)
    review_map_path.write_text(json.dumps(review_map, ensure_ascii=False, indent=2), encoding="utf-8")
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    validate_alignment(samples, outputs, sft_rows)

    validator_result = subprocess.run(
        [sys.executable, str(validator_path), "--path", str(sft_path), "--expected-lines", str(len(samples))],
        check=True,
        capture_output=True,
        text=True,
    )

    changed_source_rows = [
        index
        for index, (before, after) in enumerate(zip(original_samples, samples, strict=True), start=1)
        if source_changed(before, after)
    ]
    changed_output_rows = [
        index
        for index, (before, after) in enumerate(zip(original_outputs, outputs, strict=True), start=1)
        if before != after
    ]

    ledger_row = {
        "dataset": "public_service",
        "row_index": ROW_INDEX,
        "action_taken": "replace_same_dataset",
        "source_changed": True,
        "output_regenerated": True,
        "final_provenance_status": "source_first_rebuilt",
        "note": (
            "replaced off-domain marriage-fraud strategy row with same-dataset strict asset "
            f"{STRICT_INDEX} ({replacement['title']}) and regenerated the assistant output"
        ),
    }
    write_jsonl(ledger_path, [ledger_row])

    summary_lines = [
        "# Public Service Round-2 Repair Summary",
        "",
        "## Action Completed",
        "",
        "- Dataset: `public_service`",
        f"- Planned round-2 repairs executed: `1`",
        f"- Replaced row `{ROW_INDEX}` with strict-pool row `{STRICT_INDEX}`: `{replacement['title']}`.",
        f"- Regenerated row `{ROW_INDEX}` assistant output with `gpt-4o-mini` via the OpenAI Responses API.",
        "",
        "## Verification",
        "",
        f"- Reviewed samples rows: `{len(samples)}`",
        f"- Reviewed raw outputs rows: `{len(outputs)}`",
        f"- Reviewed SFT rows: `{len(sft_rows)}`",
        "- Full-dataset sample/output/SFT alignment: `pass`",
        f"- Validator result: `{validator_result.stdout.strip()}`",
        f"- Source-changed rows in this round-2 worker scope: `{changed_source_rows}`",
        f"- Output-changed rows in this round-2 worker scope: `{changed_output_rows}`",
        f"- Title uniqueness after repair: `{len({row['title'] for row in samples})}` unique titles",
        f"- Bucket counts before round-2 repair: `{before_bucket_counts}`",
        f"- Bucket counts after round-2 repair: `{after_bucket_counts}`",
        f"- Bucket counts changed: `{'yes' if before_bucket_counts != after_bucket_counts else 'no'}`",
        "",
        "## Outputs Written",
        "",
        f"- `{samples_path}`",
        f"- `{outputs_path}`",
        f"- `{sft_path}`",
        f"- `{meta_path}`",
        f"- `{review_map_path}`",
        f"- `{ledger_path}`",
    ]
    summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    print(f"Updated reviewed samples: {samples_path}")
    print(f"Updated reviewed outputs: {outputs_path}")
    print(f"Updated reviewed SFT: {sft_path}")
    print(f"Updated reviewed meta: {meta_path}")
    print(f"Updated review map: {review_map_path}")
    print(f"Wrote round-2 ledger: {ledger_path}")
    print(f"Wrote summary: {summary_path}")
    print(f"Validator output: {validator_result.stdout.strip()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
