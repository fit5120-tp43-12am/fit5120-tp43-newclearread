from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
API_ENDPOINT = "https://api.openai.com/v1/responses"
JUDGE_SCHEMA_ID = "judge_accessibility_v1_1_draft"
PROMPT_TEMPLATE_ID = "clearread_base_model_shootout_prompt_v1"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonical_json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha256_obj(obj: Any) -> str:
    return sha256_bytes(canonical_json_bytes(obj))


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists() or path.stat().st_size == 0:
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


def extract_markdown_section(text: str, heading: str) -> str:
    start = text.find(heading)
    if start < 0:
        raise RuntimeError(f"Missing markdown section: {heading}")
    body_start = text.find("\n", start)
    if body_start < 0:
        return ""
    body_start += 1
    next_match = re.search(r"\n## ", text[body_start:])
    end = body_start + next_match.start() if next_match else len(text)
    return text[body_start:end].strip()


def first_code_block_or_text(section: str) -> str:
    match = re.search(r"```[A-Za-z0-9_-]*\s*\n(.*?)\n```", section, re.S)
    return match.group(1).strip() if match else section.strip()


def load_prompt_and_schema(schema_path: Path) -> tuple[str, dict[str, Any], str]:
    text = schema_path.read_text(encoding="utf-8")
    prompt_section = extract_markdown_section(text, "## Proposed Judge Prompt")
    schema_section = extract_markdown_section(text, "## Proposed Judge Output JSON Schema")
    prompt = first_code_block_or_text(prompt_section)
    schema = json.loads(first_code_block_or_text(schema_section))
    return prompt, schema, sha256_bytes(schema_path.read_bytes())


def type_matches(value: Any, expected_type: Any) -> bool:
    if isinstance(expected_type, list):
        return any(type_matches(value, item) for item in expected_type)
    if expected_type == "object":
        return isinstance(value, dict)
    if expected_type == "array":
        return isinstance(value, list)
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected_type == "boolean":
        return isinstance(value, bool)
    if expected_type == "null":
        return value is None
    return True


def resolve_ref(ref: str, root_schema: dict[str, Any]) -> dict[str, Any]:
    prefix = "#/$defs/"
    if not ref.startswith(prefix):
        raise RuntimeError(f"Unsupported schema ref: {ref}")
    return root_schema["$defs"][ref[len(prefix) :]]


def validate_schema(instance: Any, schema: dict[str, Any], root_schema: dict[str, Any] | None = None, path: str = "$") -> list[str]:
    if root_schema is None:
        root_schema = schema
    if "$ref" in schema:
        return validate_schema(instance, resolve_ref(str(schema["$ref"]), root_schema), root_schema, path)
    errors: list[str] = []
    if "const" in schema and instance != schema["const"]:
        errors.append(f"{path}: expected const {schema['const']!r}")
    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: value not in enum")
    if "type" in schema and not type_matches(instance, schema["type"]):
        errors.append(f"{path}: expected type {schema['type']}")
        return errors
    if schema.get("type") == "object" and isinstance(instance, dict):
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in instance:
                errors.append(f"{path}.{key}: missing required property")
        if schema.get("additionalProperties") is False:
            extra = sorted(set(instance) - set(props))
            if extra:
                errors.append(f"{path}: unexpected properties {extra}")
        for key, prop_schema in props.items():
            if key in instance:
                errors.extend(validate_schema(instance[key], prop_schema, root_schema, f"{path}.{key}"))
    if schema.get("type") == "array" and isinstance(instance, list) and "items" in schema:
        for index, item in enumerate(instance):
            errors.extend(validate_schema(item, schema["items"], root_schema, f"{path}[{index}]"))
    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append(f"{path}: below minimum")
        if "maximum" in schema and instance > schema["maximum"]:
            errors.append(f"{path}: above maximum")
    return errors


def build_judge_input_contract(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "judge_input_schema_version": "judge_input_v1_draft",
        "benchmark_item_id": row["judge_input_id"],
        "run_id": row["run_id"],
        "system_id": row["system_id"],
        "source_chunk_id": row["input_id"],
        "source_chunk": row["source_chunk_text"],
        "parsed_model_output": row["candidate_output"],
        "strict_parse_status": "parsed_ok",
        "parser_schema_version": row["parser_version"],
        "prompt_template_id": PROMPT_TEMPLATE_ID,
        "generation_metadata": {
            "model_or_system_label": row["system_id"],
            "decode_config_id": row["judge_run_id"],
            "raw_output_sha256": row["raw_output_sha256"],
        },
    }


def build_request_body(row: dict[str, Any], judge_prompt: str, judge_schema: dict[str, Any], judge_model: str) -> dict[str, Any]:
    return {
        "model": judge_model,
        "instructions": judge_prompt,
        "input": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": json.dumps(build_judge_input_contract(row), ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                    }
                ],
            }
        ],
        "text": {"format": {"type": "json_schema", "name": JUDGE_SCHEMA_ID, "schema": judge_schema, "strict": True}},
        "store": False,
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
            body = response.read()
            return {"ok": 200 <= response.status < 300, "http_status": response.status, "body_bytes": body, "latency_ms": int((time.perf_counter() - started) * 1000), "error_type": None, "error_message": None}
    except urllib.error.HTTPError as exc:
        return {"ok": False, "http_status": exc.code, "body_bytes": exc.read(), "latency_ms": int((time.perf_counter() - started) * 1000), "error_type": "HTTPError", "error_message": f"HTTP {exc.code}"}
    except Exception as exc:
        return {"ok": False, "http_status": None, "body_bytes": b"", "latency_ms": int((time.perf_counter() - started) * 1000), "error_type": type(exc).__name__, "error_message": str(exc)}


def extract_output_text(response_json: dict[str, Any]) -> str:
    if isinstance(response_json.get("output_text"), str):
        return response_json["output_text"]
    texts: list[str] = []
    for item in response_json.get("output", []) or []:
        if item.get("type") != "message":
            continue
        for content in item.get("content", []) or []:
            if content.get("type") == "output_text" and isinstance(content.get("text"), str):
                texts.append(content["text"])
    return "".join(texts)


def usage_from_response(response_json: dict[str, Any]) -> dict[str, Any]:
    usage = response_json.get("usage") or {}
    details = usage.get("input_tokens_details") if isinstance(usage.get("input_tokens_details"), dict) else {}
    return {"input_tokens": usage.get("input_tokens"), "output_tokens": usage.get("output_tokens"), "total_tokens": usage.get("total_tokens"), "cached_input_tokens": details.get("cached_tokens")}


def validate_input_reference_echo(parsed: dict[str, Any], row: dict[str, Any]) -> str | None:
    ref = parsed.get("input_reference")
    if not isinstance(ref, dict):
        return "input_reference missing or not an object"
    expected = {
        "benchmark_item_id": row["judge_input_id"],
        "run_id": row["run_id"],
        "system_id": row["system_id"],
        "source_chunk_id": row["input_id"],
    }
    for key, value in expected.items():
        if ref.get(key) != value:
            return f"{key} echo mismatch"
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Run OpenAI judge calls for base-model shootout outputs.")
    parser.add_argument("--judge-run-id", required=True)
    parser.add_argument("--model-key", required=True)
    parser.add_argument("--max-new-calls", type=int, default=None)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--retry-failures", action="store_true")
    args = parser.parse_args()

    settings = read_json(ROOT / "configs" / "eval_settings.json")
    judge_model = settings["judge_policy"]["judge_model"]
    schema_path = ROOT / settings["judge_policy"]["judge_prompt_schema"]
    judge_root = ROOT / "outputs" / "judge" / args.judge_run_id
    judge_input_path = judge_root / "judge_inputs" / args.model_key / "judge_inputs.jsonl"
    output_root = judge_root / "judge_outputs" / judge_model.replace(".", "_").replace("-", "_")
    system_dir = output_root / args.model_key
    system_dir.mkdir(parents=True, exist_ok=True)
    for name in ["raw_api_requests.jsonl", "raw_api_responses.jsonl", "judge_outputs.jsonl", "judge_validation_failures.jsonl"]:
        (system_dir / name).touch(exist_ok=True)
    (output_root / "judge_call_log.jsonl").touch(exist_ok=True)

    rows = read_jsonl(judge_input_path)
    judge_prompt, judge_schema, prompt_hash = load_prompt_and_schema(schema_path)
    if args.validate_only:
        print(json.dumps({"status": "validated", "judge_inputs": len(rows), "prompt_schema_sha256": prompt_hash}, indent=2))
        return 0
    if not os.environ.get("OPENAI_API_KEY"):
        write_json(system_dir / "judge_output_manifest.json", {"status": "blocked", "reason": "OPENAI_API_KEY missing", "system_id": args.model_key, "judge_inputs": len(rows)})
        print("blocked: OPENAI_API_KEY missing")
        return 2

    parsed_existing = {row["judge_input_id"] for row in read_jsonl(system_dir / "judge_outputs.jsonl") if row.get("judge_input_id")}
    failed_existing = {row["judge_input_id"] for row in read_jsonl(system_dir / "judge_validation_failures.jsonl") if row.get("judge_input_id")}
    done = parsed_existing if args.retry_failures else parsed_existing | failed_existing
    pending = [row for row in rows if row["judge_input_id"] not in done]
    if args.max_new_calls is not None:
        pending = pending[: args.max_new_calls]

    api_key = os.environ["OPENAI_API_KEY"]
    attempted = 0
    for row in pending:
        attempted += 1
        request_body = build_request_body(row, judge_prompt, judge_schema, judge_model)
        request_sha = sha256_obj(request_body)
        append_jsonl(system_dir / "raw_api_requests.jsonl", {"created_at_utc": utc_now(), "judge_run_id": args.judge_run_id, "run_id": row["run_id"], "system_id": args.model_key, "judge_input_id": row["judge_input_id"], "input_id": row["input_id"], "record_run_id": row["record_run_id"], "judge_model": judge_model, "api_endpoint_or_client_method": "POST /v1/responses via urllib.request", "request_sha256": request_sha, "request_body": request_body})
        result = post_openai_response(request_body, api_key)
        response_sha = sha256_bytes(result["body_bytes"]) if result["body_bytes"] else None
        call_record = {"created_at_utc": utc_now(), "system_id": args.model_key, "judge_input_id": row["judge_input_id"], "request_sha256": request_sha, "response_sha256": response_sha, "model": judge_model, "api_endpoint_or_client_method": "POST /v1/responses via urllib.request", "attempt_number": 1, "status": "completed" if result["ok"] else "api_error", "http_status": result["http_status"], "latency_ms": result["latency_ms"], "error_type": result["error_type"]}
        if not result["ok"]:
            append_jsonl(output_root / "judge_call_log.jsonl", call_record)
            append_jsonl(system_dir / "judge_validation_failures.jsonl", {"created_at_utc": utc_now(), "judge_run_id": args.judge_run_id, "run_id": row["run_id"], "system_id": args.model_key, "judge_input_id": row["judge_input_id"], "input_id": row["input_id"], "record_run_id": row["record_run_id"], "judge_model": judge_model, "judge_schema_version": JUDGE_SCHEMA_ID, "request_sha256": request_sha, "raw_response_sha256": response_sha, "failure_stage": "api_error", "error_message": result["error_message"]})
            continue
        response_json = json.loads(result["body_bytes"].decode("utf-8"))
        append_jsonl(system_dir / "raw_api_responses.jsonl", {"created_at_utc": utc_now(), "judge_run_id": args.judge_run_id, "run_id": row["run_id"], "system_id": args.model_key, "judge_input_id": row["judge_input_id"], "request_sha256": request_sha, "raw_response_sha256": response_sha, "response_json": response_json})
        call_record.update(usage_from_response(response_json))
        append_jsonl(output_root / "judge_call_log.jsonl", call_record)
        output_text = extract_output_text(response_json)
        try:
            parsed = json.loads(output_text)
        except json.JSONDecodeError as exc:
            append_jsonl(system_dir / "judge_validation_failures.jsonl", {"created_at_utc": utc_now(), "judge_run_id": args.judge_run_id, "run_id": row["run_id"], "system_id": args.model_key, "judge_input_id": row["judge_input_id"], "input_id": row["input_id"], "record_run_id": row["record_run_id"], "judge_model": judge_model, "judge_schema_version": JUDGE_SCHEMA_ID, "request_sha256": request_sha, "raw_response_sha256": response_sha, "failure_stage": "json_parse_error", "error_message": str(exc)[:500]})
            continue
        schema_errors = validate_schema(parsed, judge_schema)
        echo_error = validate_input_reference_echo(parsed, row)
        if schema_errors or echo_error:
            append_jsonl(system_dir / "judge_validation_failures.jsonl", {"created_at_utc": utc_now(), "judge_run_id": args.judge_run_id, "run_id": row["run_id"], "system_id": args.model_key, "judge_input_id": row["judge_input_id"], "input_id": row["input_id"], "record_run_id": row["record_run_id"], "judge_model": judge_model, "judge_schema_version": JUDGE_SCHEMA_ID, "request_sha256": request_sha, "raw_response_sha256": response_sha, "parsed_judge_output_sha256": sha256_obj(parsed), "failure_stage": "schema_validation_error" if schema_errors else "input_reference_echo_error", "error_message": "; ".join(schema_errors)[:500] if schema_errors else echo_error})
            continue
        append_jsonl(system_dir / "judge_outputs.jsonl", {"created_at_utc": utc_now(), "judge_run_id": args.judge_run_id, "run_id": row["run_id"], "system_id": args.model_key, "record_run_id": row["record_run_id"], "input_id": row["input_id"], "judge_input_id": row["judge_input_id"], "judge_model": judge_model, "judge_schema_version": JUDGE_SCHEMA_ID, "request_sha256": request_sha, "raw_response_sha256": response_sha, "parsed_judge_output_sha256": sha256_obj(parsed), "parsed_judge_output": parsed, "validation_status": "schema_valid"})
        print(f"judged {attempted}/{len(pending)} system={args.model_key} jid={row['judge_input_id']}", flush=True)

    parsed_rows_after = read_jsonl(system_dir / "judge_outputs.jsonl")
    failure_rows_after = read_jsonl(system_dir / "judge_validation_failures.jsonl")
    parsed_ids_after = {row["judge_input_id"] for row in parsed_rows_after if row.get("judge_input_id")}
    unresolved_failure_ids_after = {row["judge_input_id"] for row in failure_rows_after if row.get("judge_input_id") and row.get("judge_input_id") not in parsed_ids_after}
    manifest = {
        "created_at_utc": utc_now(),
        "status": "completed" if len(parsed_ids_after) + len(unresolved_failure_ids_after) >= len(rows) else "partial",
        "judge_run_id": args.judge_run_id,
        "system_id": args.model_key,
        "intended_calls": len(rows),
        "attempted_new_calls": attempted,
        "schema_valid_outputs": len(parsed_rows_after),
        "validation_failures": len(unresolved_failure_ids_after),
        "historical_validation_failures": len(failure_rows_after),
        "pending_calls": max(0, len(rows) - len(parsed_ids_after) - len(unresolved_failure_ids_after)),
        "judge_prompt_schema_sha256": prompt_hash,
    }
    write_json(system_dir / "judge_output_manifest.json", manifest)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0 if manifest["pending_calls"] == 0 and manifest["validation_failures"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

