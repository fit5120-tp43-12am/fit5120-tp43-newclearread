#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any


MODEL = "gpt-4o-mini"
API_URL = "https://api.openai.com/v1/responses"

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

REPLACEMENT_MAP = {
    3: 127,
    5: 24,
    32: 116,
    90: 190,
    146: 196,
    160: 192,
    161: 110,
    178: 187,
    182: 149,
    199: 189,
}

REEXTRACT_RULES = {
    24: {
        "cut_before": "for example , on a",
        "note": "trimmed the same-source window before the garbled worked-example formula tail",
    },
    176: {
        "cut_before": "generally , you can set aside a tax sale for only the following reasons",
        "note": "trimmed the same-source window before the flattened invalidation-grounds list tail",
    },
}

OUTPUT_ONLY_ROWS = [
    1,
    2,
    8,
    10,
    26,
    36,
    40,
    43,
    48,
    50,
    57,
    58,
    68,
    72,
    75,
    80,
    82,
    83,
    86,
    88,
    89,
    94,
    96,
    97,
    102,
    109,
    110,
    121,
    123,
    129,
    134,
    137,
    145,
    147,
    152,
    153,
    156,
    158,
    167,
    171,
    172,
    173,
    177,
    180,
    188,
    189,
    196,
    197,
    200,
]


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


def classify_bucket(word_count: int) -> str:
    if 250 <= word_count <= 499:
        return "short"
    if 500 <= word_count <= 800:
        return "medium"
    if 801 <= word_count <= 1200:
        return "long"
    raise ValueError(f"Word count {word_count} is outside the expected public_service bucket ranges.")


def validate_output(obj: dict[str, Any]) -> None:
    if set(obj.keys()) != {"main_idea", "key_points"}:
        raise ValueError(f"Unexpected output keys: {sorted(obj.keys())}")
    if not isinstance(obj["main_idea"], str) or not obj["main_idea"].strip():
        raise ValueError("main_idea must be a non-empty string.")
    if not isinstance(obj["key_points"], list) or not obj["key_points"]:
        raise ValueError("key_points must be a non-empty list.")
    if not all(isinstance(item, str) and item.strip() for item in obj["key_points"]):
        raise ValueError("Every key point must be a non-empty string.")


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
        raise RuntimeError(f"Expected exactly one public_service reviewed samples file under {data_root}, found {len(matches)}.")
    return matches[0].parent


def apply_reextract_rule(text: str, cut_before: str) -> str:
    pos = text.find(cut_before)
    if pos == -1:
        raise ValueError(f"Could not find trim marker: {cut_before}")
    return text[:pos].strip()


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

    ledger_path = worker_dir / "REPAIR_LEDGER_public_service.jsonl"
    summary_path = worker_dir / "SUMMARY.md"

    samples = load_jsonl(samples_path)
    outputs = load_jsonl(outputs_path)
    review_map = json.loads(review_map_path.read_text(encoding="utf-8"))
    strict_samples = load_jsonl(strict_samples_path)

    if not (len(samples) == len(outputs) == len(review_map) == 200):
        raise RuntimeError("Expected reviewed samples, outputs, and review map to each contain 200 rows.")

    strict_by_index = {int(row["sample_index"]): row for row in strict_samples}

    touched_rows = sorted(set(REPLACEMENT_MAP) | set(REEXTRACT_RULES) | set(OUTPUT_ONLY_ROWS))
    if len(touched_rows) != 61:
        raise RuntimeError(f"Expected 61 touched rows, found {len(touched_rows)}.")

    original_samples = [dict(row) for row in samples]

    for row_index, strict_index in REPLACEMENT_MAP.items():
        strict_row = strict_by_index[strict_index]
        current_row = samples[row_index - 1]
        if current_row["bucket"] != strict_row["bucket"]:
            raise RuntimeError(
                f"Bucket mismatch for replacement row {row_index}: current={current_row['bucket']} strict={strict_row['bucket']}"
            )
        samples[row_index - 1] = {
            **current_row,
            "sample_index": row_index,
            "bucket": strict_row["bucket"],
            "word_count": strict_row["word_count"],
            "wikihow_id": strict_row.get("wikihow_id", ""),
            "title": strict_row.get("title", ""),
            "category": strict_row.get("category", ""),
            "source_url": strict_row.get("source_url", ""),
            "text": strict_row["text"],
        }
        review_map[row_index - 1] = {
            "sample_index": row_index,
            "action": "replaced",
            "bucket": strict_row["bucket"],
            "original_title": review_map[row_index - 1]["original_title"],
            "final_title": strict_row["title"],
            "replacement_from_strict_index": strict_index,
        }

    for row_index, rule in REEXTRACT_RULES.items():
        current_row = samples[row_index - 1]
        rebuilt_text = apply_reextract_rule(current_row["text"], rule["cut_before"])
        rebuilt_word_count = len(rebuilt_text.split())
        samples[row_index - 1] = {
            **current_row,
            "bucket": classify_bucket(rebuilt_word_count),
            "word_count": rebuilt_word_count,
            "text": rebuilt_text,
        }

    write_jsonl(samples_path, samples)
    review_map_path.write_text(json.dumps(review_map, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Updated reviewed samples: {samples_path}")
    print(f"Updated review map: {review_map_path}")

    outputs_by_index = {int(row["sample_index"]): row for row in outputs}
    ledger_rows: list[dict[str, Any]] = []

    for ordinal, row_index in enumerate(touched_rows, start=1):
        sample = samples[row_index - 1]
        original_sample = original_samples[row_index - 1]
        action_taken = (
            "replace_same_dataset"
            if row_index in REPLACEMENT_MAP
            else "reextract_same_source"
            if row_index in REEXTRACT_RULES
            else "regenerate_output_only"
        )
        print(f"[{ordinal}/{len(touched_rows)}] regenerating row {row_index}: {sample['title']}")
        target = call_openai(api_key=api_key, source_text=sample["text"])
        outputs_by_index[row_index] = build_raw_record(sample, target)

        source_changed = action_taken != "regenerate_output_only"
        if action_taken == "replace_same_dataset":
            strict_index = REPLACEMENT_MAP[row_index]
            strict_title = strict_by_index[strict_index]["title"]
            note = f"replaced with same-dataset strict asset {strict_index} ({strict_title}) and regenerated output"
            final_provenance_status = "source_first_rebuilt"
        elif action_taken == "reextract_same_source":
            note = f"{REEXTRACT_RULES[row_index]['note']} and regenerated output"
            final_provenance_status = "source_first_rebuilt"
        else:
            note = "kept the current reviewed source and regenerated the assistant output through the OpenAI path"
            final_provenance_status = "output_only_regenerated"

        ledger_rows.append(
            {
                "dataset": "public_service",
                "row_index": row_index,
                "action_taken": action_taken,
                "source_changed": source_changed,
                "output_regenerated": True,
                "final_provenance_status": final_provenance_status,
                "note": note,
            }
        )

        ordered_outputs = [outputs_by_index[index] for index in range(1, len(samples) + 1)]
        write_jsonl(outputs_path, ordered_outputs)

    final_outputs = [outputs_by_index[index] for index in range(1, len(samples) + 1)]
    write_jsonl(outputs_path, final_outputs)

    sft_rows = [build_sft_record(sample, final_outputs[index - 1]["target"]) for index, sample in enumerate(samples, start=1)]
    write_jsonl(sft_path, sft_rows)

    bucket_counts = Counter(row["bucket"] for row in samples)
    meta = {
        "input_file": str(samples_path.resolve()),
        "raw_output_file": str(outputs_path.resolve()),
        "sft_output_file": str(sft_path.resolve()),
        "mode": "repair_openai_mixed",
        "model": MODEL,
        "total_samples": len(samples),
        "generated_now": len(touched_rows),
        "reused_existing": len(samples) - len(touched_rows),
        "replacement_rows": sorted(REPLACEMENT_MAP),
        "replacement_sources": REPLACEMENT_MAP,
        "reextract_rows": sorted(REEXTRACT_RULES),
        "output_only_rows": OUTPUT_ONLY_ROWS,
        "bucket_counts": dict(bucket_counts),
        "schema": OUTPUT_SCHEMA,
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    write_jsonl(ledger_path, ledger_rows)

    summary_lines = [
        "# Public Service Repair Summary",
        "",
        "## Actions Completed",
        "",
        "- Dataset: `public_service`",
        "- Total planned repairs executed: `61`",
        "- `replace_same_dataset`: `10`",
        "- `reextract_same_source`: `2`",
        "- `regenerate_output_only`: `49`",
        "- All `61` touched rows had assistant outputs regenerated with `gpt-4o-mini` via the OpenAI Responses API.",
        "",
        "## Source Updates",
        "",
        "- Replacement rows updated from unused strict-pool assets: `3, 5, 32, 90, 146, 160, 161, 178, 182, 199`.",
        "- Same-source re-extractions applied to rows `24` and `176` by trimming before the known garbled tails.",
        "- Output-only rows kept their current reviewed source text unchanged.",
        "",
        "## Validation Notes",
        "",
        f"- Reviewed samples rows: `{len(samples)}`",
        f"- Reviewed raw outputs rows: `{len(final_outputs)}`",
        f"- Reviewed SFT rows: `{len(sft_rows)}`",
        f"- Title uniqueness after repair: `{len({row['title'] for row in samples})}` unique titles",
        f"- Bucket counts after repair: `{dict(bucket_counts)}`",
        "- Row `176` moved from `medium` to `short` because the clean same-source window ends before the flattened invalidation list; this kept the source-first repair path without inventing new text.",
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

    print(f"Wrote reviewed outputs: {outputs_path}")
    print(f"Wrote reviewed SFT: {sft_path}")
    print(f"Wrote repair ledger: {ledger_path}")
    print(f"Wrote summary: {summary_path}")
    print(f"Validator available at: {validator_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
