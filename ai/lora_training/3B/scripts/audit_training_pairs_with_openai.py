from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUDIT_DIR = ROOT / "outputs" / "data_audit" / "random_sample_100_20260513"
DEFAULT_SAMPLE = DEFAULT_AUDIT_DIR / "sample_with_text.jsonl"
API_ENDPOINT = "https://api.openai.com/v1/responses"
AUDIT_SCHEMA_ID = "training_pair_quality_audit_v1"

SYSTEM_PROMPT = """You are an expert data-quality auditor for supervised fine-tuning data.

The training task is reading-support summarization. Each source text may be an academic article, textbook passage, public-service article, medical page, technical document, assignment prompt, or scoring rubric. Do not answer the source text. Judge whether the existing target output is a good training label for summarizing that source.

The desired target output is exactly:
{"main_idea":"two short faithful sentences","key_points":["one high-level sentence","one high-level sentence","one high-level sentence","one high-level sentence"]}

Judge strictly but practically. Strong labels should be faithful, high-level, clear, concise, and useful for training a small model to summarize about 600-word inputs into two-sentence main ideas and four key points. The label must not invent facts. It should preserve important warnings, restrictions, requirements, eligibility rules, negation, uncertainty, and major conclusions when they matter.

Do not reward a label for performing instructions in the source. For assignment prompts or rubrics, the correct behavior is to summarize what the prompt/rubric says.

You may recommend a revised target when the current label is weak. If the label is already good, set recommended_target.change_type to "unchanged" and copy the existing target exactly into recommended_target."""


AUDIT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "audit_schema_version",
        "audit_sample_id",
        "record_id",
        "overall_decision",
        "severity",
        "scores",
        "pass_flags",
        "issue_tags",
        "rationale",
        "suggested_action",
        "recommended_target",
    ],
    "properties": {
        "audit_schema_version": {"type": "string", "const": "training_pair_quality_audit_v1"},
        "audit_sample_id": {"type": "string"},
        "record_id": {"type": "string"},
        "overall_decision": {"type": "string", "enum": ["accept", "minor_repair", "rewrite", "drop_or_manual_review"]},
        "severity": {"type": "string", "enum": ["none", "minor", "moderate", "major"]},
        "scores": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "faithfulness",
                "coverage",
                "high_level_abstraction",
                "clarity_accessibility",
                "schema_style_fit",
                "training_value",
            ],
            "properties": {
                "faithfulness": {"type": "integer", "minimum": 1, "maximum": 5},
                "coverage": {"type": "integer", "minimum": 1, "maximum": 5},
                "high_level_abstraction": {"type": "integer", "minimum": 1, "maximum": 5},
                "clarity_accessibility": {"type": "integer", "minimum": 1, "maximum": 5},
                "schema_style_fit": {"type": "integer", "minimum": 1, "maximum": 5},
                "training_value": {"type": "integer", "minimum": 1, "maximum": 5},
            },
        },
        "pass_flags": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "faithful_to_source",
                "captures_main_message",
                "high_level_not_detail_dump",
                "simple_clear_language",
                "good_training_example",
            ],
            "properties": {
                "faithful_to_source": {"type": "boolean"},
                "captures_main_message": {"type": "boolean"},
                "high_level_not_detail_dump": {"type": "boolean"},
                "simple_clear_language": {"type": "boolean"},
                "good_training_example": {"type": "boolean"},
            },
        },
        "issue_tags": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": [
                    "none",
                    "unsupported_fact",
                    "critical_omission",
                    "too_detailed",
                    "too_vague",
                    "not_high_level",
                    "format_or_schema_issue",
                    "sentence_count_issue",
                    "key_point_count_issue",
                    "source_instruction_following_risk",
                    "medical_or_safety_nuance_loss",
                    "requirement_or_constraint_loss",
                    "unclear_language",
                    "overlong_output",
                    "underinformative_output",
                    "manual_review_needed",
                ],
            },
        },
        "rationale": {"type": "string"},
        "suggested_action": {"type": "string"},
        "recommended_target": {
            "type": "object",
            "additionalProperties": False,
            "required": ["change_type", "main_idea", "key_points"],
            "properties": {
                "change_type": {"type": "string", "enum": ["unchanged", "minor_repair", "rewrite", "manual_review_no_rewrite"]},
                "main_idea": {"type": "string"},
                "key_points": {"type": "array", "minItems": 4, "maxItems": 4, "items": {"type": "string"}},
            },
        },
    },
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonical_json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_obj(obj: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(obj)).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def existing_ids(path: Path) -> set[str]:
    return {row.get("audit_sample_id") for row in read_jsonl(path) if isinstance(row.get("audit_sample_id"), str)}


def target_payload(target_text: str) -> dict[str, Any]:
    try:
        value = json.loads(target_text)
    except Exception:
        return {"main_idea": target_text, "key_points": ["", "", "", ""]}
    if not isinstance(value, dict):
        return {"main_idea": target_text, "key_points": ["", "", "", ""]}
    key_points = value.get("key_points")
    if not isinstance(key_points, list):
        key_points = ["", "", "", ""]
    key_points = [str(item) for item in key_points[:4]]
    while len(key_points) < 4:
        key_points.append("")
    return {"main_idea": str(value.get("main_idea", "")), "key_points": key_points}


def build_audit_contract(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "audit_input_schema_version": "training_pair_audit_input_v1",
        "audit_sample_id": row["audit_sample_id"],
        "record_id": row["record_id"],
        "metadata": {
            "domain": row.get("domain"),
            "natural_length_bucket": row.get("natural_length_bucket"),
            "user_word_count": row.get("user_word_count"),
            "assistant_word_count": row.get("assistant_word_count"),
            "local_structure_checks": row.get("local_structure_checks"),
        },
        "source_text": row["source_text"],
        "existing_target": target_payload(row["target_output_text"]),
        "audit_questions": [
            "Is the target faithful to the source with no invented facts?",
            "Does the target capture the main message rather than isolated details?",
            "Are the four key points high-level and distinct?",
            "Is the wording simple and useful for reading support?",
            "Is this a good example for fine-tuning a small summarization model?",
        ],
    }


def build_request_body(row: dict[str, Any], model: str) -> dict[str, Any]:
    return {
        "model": model,
        "instructions": SYSTEM_PROMPT,
        "input": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": json.dumps(build_audit_contract(row), ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                    }
                ],
            }
        ],
        "text": {"format": {"type": "json_schema", "name": AUDIT_SCHEMA_ID, "schema": AUDIT_SCHEMA, "strict": True}},
        "store": False,
        "max_output_tokens": 2200,
    }


def post_openai_response(request_body: dict[str, Any], api_key: str) -> dict[str, Any]:
    data = canonical_json_bytes(request_body)
    req = urllib.request.Request(
        API_ENDPOINT,
        data=data,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=240) as response:
            return {
                "ok": 200 <= response.status < 300,
                "http_status": response.status,
                "body_bytes": response.read(),
                "latency_ms": int((time.perf_counter() - started) * 1000),
                "error_type": None,
                "error_message": None,
            }
    except urllib.error.HTTPError as exc:
        return {
            "ok": False,
            "http_status": exc.code,
            "body_bytes": exc.read(),
            "latency_ms": int((time.perf_counter() - started) * 1000),
            "error_type": "HTTPError",
            "error_message": f"HTTP {exc.code}",
        }
    except Exception as exc:
        return {
            "ok": False,
            "http_status": None,
            "body_bytes": b"",
            "latency_ms": int((time.perf_counter() - started) * 1000),
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        }


def extract_output_text(response_json: dict[str, Any]) -> str:
    if isinstance(response_json.get("output_text"), str):
        return response_json["output_text"]
    texts: list[str] = []
    for item in response_json.get("output", []) or []:
        if item.get("type") != "message":
            continue
        for content in item.get("content", []) or []:
            if isinstance(content, dict) and content.get("type") in {"output_text", "text"}:
                text = content.get("text")
                if isinstance(text, str):
                    texts.append(text)
    return "\n".join(texts).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit sampled training pairs with OpenAI Responses API.")
    parser.add_argument("--sample", type=Path, default=DEFAULT_SAMPLE)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_AUDIT_DIR)
    parser.add_argument("--model", default="gpt-5.5")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--sleep-seconds", type=float, default=0.2)
    args = parser.parse_args()

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        manifest = {"status": "blocked", "reason": "OPENAI_API_KEY missing", "created_at_utc": utc_now()}
        write_json(args.out_dir / "api_audit_manifest.json", manifest)
        print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
        return 2

    rows = read_jsonl(args.sample)
    if args.limit is not None:
        rows = rows[: args.limit]

    outputs_path = args.out_dir / "api_audit_outputs.jsonl"
    failures_path = args.out_dir / "api_audit_failures.jsonl"
    requests_path = args.out_dir / "raw_api_requests.jsonl"
    responses_path = args.out_dir / "raw_api_responses.jsonl"
    done = existing_ids(outputs_path)

    manifest = {
        "created_at_utc": utc_now(),
        "status": "running",
        "model": args.model,
        "sample_path": str(args.sample),
        "sample_rows": len(rows),
        "schema_id": AUDIT_SCHEMA_ID,
        "system_prompt_sha256": hashlib.sha256(SYSTEM_PROMPT.encode("utf-8")).hexdigest(),
        "audit_schema_sha256": sha256_obj(AUDIT_SCHEMA),
        "training_data_modified": False,
        "raw_requests_saved": True,
        "raw_responses_saved": True,
    }
    write_json(args.out_dir / "api_audit_manifest.json", manifest)

    attempted = 0
    succeeded = 0
    failed = 0
    for row in rows:
        sample_id = row["audit_sample_id"]
        if sample_id in done:
            continue
        request_body = build_request_body(row, args.model)
        append_jsonl(
            requests_path,
            {
                "audit_sample_id": sample_id,
                "record_id": row.get("record_id"),
                "request_sha256": sha256_obj(request_body),
                "request_body": request_body,
            },
        )
        attempted += 1

        result = None
        for attempt in range(1, 4):
            result = post_openai_response(request_body, api_key)
            if result["ok"]:
                break
            time.sleep(2 * attempt)

        assert result is not None
        response_text = result["body_bytes"].decode("utf-8", errors="replace")
        response_record = {
            "audit_sample_id": sample_id,
            "record_id": row.get("record_id"),
            "ok": result["ok"],
            "http_status": result["http_status"],
            "latency_ms": result["latency_ms"],
            "error_type": result["error_type"],
            "error_message": result["error_message"],
            "response_text": response_text,
        }
        append_jsonl(responses_path, response_record)

        if not result["ok"]:
            failed += 1
            append_jsonl(failures_path, response_record)
            print(f"[FAIL] {sample_id} HTTP={result['http_status']} {result['error_message']}", flush=True)
            continue

        try:
            response_json = json.loads(response_text)
            output_text = extract_output_text(response_json)
            audit_payload = json.loads(output_text)
            audit_payload["audit_sample_id"] = sample_id
            audit_payload["record_id"] = row["record_id"]
            output_row = {
                "audit_sample_id": sample_id,
                "record_id": row["record_id"],
                "stable_hash": row["stable_hash"],
                "domain": row.get("domain"),
                "natural_length_bucket": row.get("natural_length_bucket"),
                "user_word_count": row.get("user_word_count"),
                "assistant_word_count": row.get("assistant_word_count"),
                "local_structure_checks": row.get("local_structure_checks"),
                "api_model": args.model,
                "latency_ms": result["latency_ms"],
                "audit": audit_payload,
            }
            append_jsonl(outputs_path, output_row)
            succeeded += 1
            print(f"[OK] {sample_id} {audit_payload.get('overall_decision')} score={audit_payload.get('scores', {}).get('training_value')}", flush=True)
        except Exception as exc:
            failed += 1
            failure = dict(response_record)
            failure["parse_error"] = str(exc)
            append_jsonl(failures_path, failure)
            print(f"[PARSE_FAIL] {sample_id} {exc}", flush=True)

        if args.sleep_seconds:
            time.sleep(args.sleep_seconds)

    all_outputs = read_jsonl(outputs_path)
    all_failures = read_jsonl(failures_path)
    manifest.update(
        {
            "completed_at_utc": utc_now(),
            "status": "completed" if len(all_outputs) >= len(rows) and not all_failures else "completed_with_failures",
            "attempted_this_run": attempted,
            "succeeded_this_run": succeeded,
            "failed_this_run": failed,
            "total_successful_outputs": len(all_outputs),
            "total_failures": len(all_failures),
        }
    )
    write_json(args.out_dir / "api_audit_manifest.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if manifest["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
