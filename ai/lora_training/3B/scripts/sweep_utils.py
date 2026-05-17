from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: str | Path, payload: Any) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: str | Path, text: str) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8", newline="\n")


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            value = json.loads(stripped)
            if not isinstance(value, dict):
                raise ValueError(f"JSONL row must be an object at {path}:{line_number}")
            rows.append(value)
    return rows


def first_json_object(text: str) -> str | None:
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return None


def sentence_count(text: str) -> int:
    return len(re.findall(r"[.!?](?:\s|$)", text.strip()))


def parse_candidate_output(raw: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    obj_text = first_json_object(raw)
    if not obj_text:
        return None, {"reason": "no_json_object"}
    try:
        parsed = json.loads(obj_text)
    except json.JSONDecodeError as exc:
        return None, {"reason": "invalid_json", "detail": str(exc)}
    if not isinstance(parsed, dict):
        return None, {"reason": "json_not_object"}
    if list(parsed.keys()) != ["main_idea", "key_points"]:
        return None, {"reason": "key_order_or_keys_invalid", "keys": list(parsed.keys())}
    main_idea = parsed.get("main_idea")
    key_points = parsed.get("key_points")
    if not isinstance(main_idea, str):
        return None, {"reason": "main_idea_not_string"}
    if sentence_count(main_idea) != 2:
        return None, {"reason": "main_idea_not_two_sentences", "sentence_count": sentence_count(main_idea)}
    if not isinstance(key_points, list) or len(key_points) != 4 or not all(isinstance(item, str) for item in key_points):
        return None, {"reason": "key_points_not_four_string_items"}
    bad_kp = [i for i, item in enumerate(key_points) if sentence_count(item) > 1]
    if bad_kp:
        return None, {"reason": "key_point_not_one_sentence", "indices": bad_kp}
    return parsed, None


def summarize_parse_results(raw_count: int, parsed_rows: list[dict[str, Any]], failures: list[dict[str, Any]]) -> dict[str, Any]:
    failure_reasons: dict[str, int] = {}
    for item in failures:
        reason = str((item.get("parse_error") or {}).get("reason", "unknown"))
        failure_reasons[reason] = failure_reasons.get(reason, 0) + 1
    parsed_ok = len(parsed_rows)
    return {
        "parser_version": "sweep_json_main2_kp4_v1",
        "counts": {
            "raw_output_count": raw_count,
            "parsed_ok_count": parsed_ok,
            "parse_failure_count": len(failures),
            "no_markdown_fence_count": sum(1 for item in parsed_rows if "```" not in item.get("raw_output", "")),
            "no_refusal_or_meta_count": sum(
                1
                for item in parsed_rows
                if not re.search(r"\b(as an ai|cannot|can't|i am unable|sorry)\b", item.get("raw_output", ""), re.I)
            ),
            "no_mojibake_count": sum(1 for item in parsed_rows if "�" not in item.get("raw_output", "")),
        },
        "rates": {
            "parsed_ok_rate": round(parsed_ok / raw_count, 6) if raw_count else 0.0,
            "parse_failure_rate": round(len(failures) / raw_count, 6) if raw_count else 0.0,
        },
        "failure_reasons": failure_reasons,
    }


def path_manifest(paths: list[Path], root: Path) -> dict[str, Any]:
    entries = []
    for path in sorted(paths):
        if not path.exists() or not path.is_file():
            continue
        entries.append(
            {
                "path": str(path),
                "relative_path": path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path),
                "size_bytes": path.stat().st_size,
                "sha256": file_sha256(path),
                "modified_utc": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
                .replace(microsecond=0)
                .isoformat()
                .replace("+00:00", "Z"),
            }
        )
    return {"created_at_utc": utc_now(), "root": str(root), "entries": entries}
