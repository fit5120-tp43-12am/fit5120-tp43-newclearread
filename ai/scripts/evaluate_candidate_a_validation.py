from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import math
import re
import time
from pathlib import Path
from typing import Any, Iterable, Sequence

import unsloth  # noqa: F401  Keep Unsloth before transformers/peft imports.
from unsloth import FastLanguageModel

from training_data_utils import (
    ensure_tokenizer_padding,
    eta_status,
    file_sha256,
    format_duration,
    load_manifest_metadata,
    load_yaml_config,
    local_timestamp,
    markdown_table,
    metadata_for_record,
    preview_text,
    read_jsonl,
    resolve_project_path,
    validate_role_order,
    write_text,
)

from peft import PeftModel


EXPECTED_KEYS = ["main_idea", "key_points"]
EXPECTED_VALIDATION_COUNT = 145
WORD_RE = re.compile(r"[A-Za-z0-9]+(?:['-][A-Za-z0-9]+)*")
SENTENCE_END_RE = re.compile(r"[.!?]+(?=(?:\s|$|[\"')\]]))")
MARKDOWN_RE = re.compile(r"(^|\n)\s*(#{1,6}\s+|[-*]\s+|\d+\.\s+)")

MOJIBAKE_PATTERNS = [
    # Required work-order patterns, represented as escapes so the detector is
    # not itself vulnerable to editor/console mojibake.
    "\ufffd",
    "\u8252",
    "\u9225",
    "\u00c3",
    "\u00c2",
    "\u00e2\u20ac\u2122",
    "\u00e2\u20ac\u0153",
    "\u00e2\u20ac\u009d",
    # Additional variants seen in earlier project notes or common UTF-8/CP1252
    # corruption paths.
    "\u951f",
    "\u9479",
    "\u95b3",
    "\u8119",
    "\u8117",
    "\u8292\u9227\ue0fd\u5289",
    "\u8292\u9227\ue0e0?",
    "\u8292\u9227\ue0dd?",
    "\u9225\u6a9a",
    "\u57be",
    "\u59be\u6b5a",
]

REFUSAL_OR_META_PATTERNS = [
    r"\bas an ai\b",
    r"\bi cannot\b",
    r"\bi can't\b",
    r"\bi am unable\b",
    r"\bi'm unable\b",
    r"\bsorry\b",
    r"\bcannot assist\b",
    r"\bcan't assist\b",
    r"\bnot able to\b",
    r"\bi do not have\b",
    r"\bi don't have\b",
    r"^\s*here\s+is\b",
    r"^\s*here's\b",
    r"^\s*the json\b",
    r"^\s*json object\b",
    r"^\s*the summary is\b",
]

RATE_KEYS = [
    "json_parse_ok",
    "schema_pass",
    "exact_key_order",
    "main_idea_string",
    "key_points_list",
    "exactly_4_key_points",
    "all_key_points_strings",
    "main_idea_two_sentences",
    "each_key_point_one_sentence",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate Candidate A on the validation split only.")
    parser.add_argument("--config", default="configs/train_llama31_8b_qlora_candidate_a.yaml")
    parser.add_argument("--adapter-path", default=None)
    parser.add_argument("--data-path", default=None)
    parser.add_argument("--manifest-path", default=None)
    parser.add_argument("--output-dir", default="outputs/evaluation/candidate_a_validation")
    parser.add_argument("--expected-count", type=int, default=EXPECTED_VALIDATION_COUNT)
    parser.add_argument("--reuse-predictions", action="store_true", help="Rebuild metrics/report from an existing prediction JSONL.")
    return parser.parse_args()


def percent(numerator: int | float, denominator: int | float) -> float:
    if denominator == 0:
        return 0.0
    return round(float(numerator) * 100.0 / float(denominator), 2)


def mean_or_none(values: Iterable[int | float | None]) -> float | None:
    numeric = [float(value) for value in values if value is not None]
    if not numeric:
        return None
    return round(sum(numeric) / len(numeric), 2)


def word_count(text: str) -> int:
    return len(WORD_RE.findall(text or ""))


def sentence_count(text: str) -> int:
    stripped = " ".join((text or "").strip().split())
    if not stripped:
        return 0
    protected = stripped
    for source, target in (
        ("e.g.", "eg<DOT>"),
        ("i.e.", "ie<DOT>"),
        ("U.S.", "US<DOT>"),
        ("U.K.", "UK<DOT>"),
    ):
        protected = protected.replace(source, target).replace(source.upper(), target)
    matches = list(SENTENCE_END_RE.finditer(protected))
    if not matches:
        return 1
    tail = protected[matches[-1].end() :].strip()
    if tail:
        return len(matches) + 1
    return len(matches)


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def json_dumps_ascii(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True)


def clean_table_cell(value: Any, limit: int | None = None) -> str:
    text = str(value)
    text = text.replace("\n", " ").replace("|", "\\|")
    text = " ".join(text.split())
    if limit is not None and len(text) > limit:
        text = text[: max(0, limit - 3)] + "..."
    return text


def find_mojibake(text: str) -> list[str]:
    hits = [pattern for pattern in MOJIBAKE_PATTERNS if pattern and pattern in (text or "")]
    return sorted(set(hits))


def has_markdown_leakage(text: str) -> bool:
    stripped = text or ""
    return "```" in stripped or bool(MARKDOWN_RE.search(stripped))


def has_refusal_or_meta(text: str) -> bool:
    lowered = (text or "").lower()
    return any(re.search(pattern, lowered) for pattern in REFUSAL_OR_META_PATTERNS)


def parse_generated_json(text: str) -> dict[str, Any]:
    stripped = (text or "").strip()
    result: dict[str, Any] = {
        "parsed_json": None,
        "json_parse_ok": False,
        "json_parse_method": "failed",
        "json_error": None,
        "extra_text_outside_json": False,
    }
    if not stripped:
        result["json_error"] = "empty_output"
        return result

    try:
        value = json.loads(stripped)
    except json.JSONDecodeError as exc:
        result["json_error"] = str(exc)
    else:
        if isinstance(value, dict):
            result["parsed_json"] = value
            result["json_parse_ok"] = True
            result["json_parse_method"] = "exact"
            return result
        result["json_error"] = f"json_value_not_object:{type(value).__name__}"
        return result

    start = stripped.find("{")
    if start < 0:
        return result

    decoder = json.JSONDecoder()
    try:
        value, end = decoder.raw_decode(stripped[start:])
    except json.JSONDecodeError:
        return result
    if not isinstance(value, dict):
        return result

    prefix = stripped[:start].strip()
    suffix = stripped[start + end :].strip()
    result["parsed_json"] = value
    result["json_parse_method"] = "extracted"
    result["extra_text_outside_json"] = bool(prefix or suffix)
    return result


def schema_errors(parsed_json: dict[str, Any] | None, parse_info: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not parse_info["json_parse_ok"]:
        errors.append("full_output_not_exact_json_object")
    if parse_info["extra_text_outside_json"]:
        errors.append("extra_text_outside_json")
    if parsed_json is None:
        errors.append("no_parseable_json_object")
        return errors
    if list(parsed_json.keys()) != EXPECTED_KEYS:
        errors.append(f"wrong_key_order_or_keys:{list(parsed_json.keys())}")
    main_idea = parsed_json.get("main_idea")
    if not isinstance(main_idea, str):
        errors.append("main_idea_not_string")
    key_points = parsed_json.get("key_points")
    if not isinstance(key_points, list):
        errors.append("key_points_not_list")
    else:
        if len(key_points) != 4:
            errors.append(f"key_points_len_{len(key_points)}")
        if not all(isinstance(item, str) for item in key_points):
            errors.append("key_points_item_not_string")
    return errors


def combined_summary_text(parsed_json: dict[str, Any] | None, fallback_text: str) -> str:
    if not isinstance(parsed_json, dict):
        return fallback_text or ""
    parts: list[str] = []
    main_idea = parsed_json.get("main_idea")
    if isinstance(main_idea, str):
        parts.append(main_idea)
    key_points = parsed_json.get("key_points")
    if isinstance(key_points, list):
        parts.extend(item for item in key_points if isinstance(item, str))
    return " ".join(parts) if parts else (fallback_text or "")


def deterministic_flags(
    generated_text: str,
    parsed_json: dict[str, Any] | None,
    parse_info: dict[str, Any],
    gold_assistant_text: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    errors = schema_errors(parsed_json, parse_info)
    main_idea = parsed_json.get("main_idea") if isinstance(parsed_json, dict) else None
    key_points = parsed_json.get("key_points") if isinstance(parsed_json, dict) else None
    key_point_strings = key_points if isinstance(key_points, list) and all(isinstance(item, str) for item in key_points) else []

    main_idea_word_count = word_count(main_idea) if isinstance(main_idea, str) else None
    key_point_word_counts = [word_count(item) for item in key_point_strings]
    summary_text = combined_summary_text(parsed_json, generated_text)
    summary_word_count = word_count(summary_text)

    has_empty_string = not (generated_text or "").strip()
    if isinstance(main_idea, str) and not main_idea.strip():
        has_empty_string = True
    if isinstance(key_points, list):
        for item in key_points:
            if isinstance(item, str) and not item.strip():
                has_empty_string = True

    prediction_mojibake_hits = find_mojibake(generated_text)
    gold_mojibake_hits = find_mojibake(gold_assistant_text)
    output_too_short = summary_word_count < 35
    output_too_long = summary_word_count > 180

    flags = {
        "json_parse_ok": bool(parse_info["json_parse_ok"]),
        "json_object_extractable": parsed_json is not None,
        "schema_pass": len(errors) == 0,
        "exact_key_order": isinstance(parsed_json, dict) and list(parsed_json.keys()) == EXPECTED_KEYS,
        "main_idea_string": isinstance(main_idea, str),
        "key_points_list": isinstance(key_points, list),
        "exactly_4_key_points": isinstance(key_points, list) and len(key_points) == 4,
        "all_key_points_strings": isinstance(key_points, list) and all(isinstance(item, str) for item in key_points),
        "main_idea_two_sentences": isinstance(main_idea, str) and sentence_count(main_idea) == 2,
        "each_key_point_one_sentence": bool(key_point_strings) and len(key_point_strings) == 4 and all(sentence_count(item) == 1 for item in key_point_strings),
        "has_empty_string": has_empty_string,
        "output_too_short": output_too_short,
        "output_too_long": output_too_long,
        "code_fence_or_markdown_leakage": has_markdown_leakage(generated_text),
        "extra_text_outside_json": bool(parse_info["extra_text_outside_json"]),
        "refusal_or_meta_response": has_refusal_or_meta(generated_text),
        "prediction_mojibake": bool(prediction_mojibake_hits),
        "gold_mojibake": bool(gold_mojibake_hits),
    }
    counts = {
        "schema_errors": errors,
        "main_idea_sentence_count": sentence_count(main_idea) if isinstance(main_idea, str) else None,
        "key_point_sentence_counts": [sentence_count(item) for item in key_point_strings],
        "main_idea_word_count": main_idea_word_count,
        "key_point_word_counts": key_point_word_counts,
        "summary_word_count": summary_word_count,
        "prediction_mojibake_patterns": prediction_mojibake_hits,
        "gold_mojibake_patterns": gold_mojibake_hits,
    }
    return flags, counts


def load_model_with_adapter(config: dict[str, Any], adapter_path: Path):
    model_id = config["model"]["base_model_id"]
    max_seq_length = int(config["data"]["max_seq_length"])
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_id,
        max_seq_length=max_seq_length,
        dtype=None,
        load_in_4bit=bool(config["model"].get("load_in_4bit", True)),
        trust_remote_code=bool(config["model"].get("trust_remote_code", True)),
    )
    ensure_tokenizer_padding(tokenizer)
    model = PeftModel.from_pretrained(model, str(adapter_path))
    FastLanguageModel.for_inference(model)
    model.eval()
    return model, tokenizer


def generate_candidate_a_text(
    model: Any,
    tokenizer: Any,
    record: dict[str, Any],
    *,
    index: int,
    max_new_tokens: int,
) -> str:
    import torch

    messages = validate_role_order(record, index)
    prompt = tokenizer.apply_chat_template(messages[:2], tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    generate_kwargs = {
        "max_new_tokens": max_new_tokens,
        "do_sample": False,
        "pad_token_id": tokenizer.pad_token_id,
        "eos_token_id": tokenizer.eos_token_id,
    }
    with torch.inference_mode():
        output_ids = model.generate(**inputs, **generate_kwargs)
    if torch.cuda.is_available():
        torch.cuda.synchronize()
    new_tokens = output_ids[0][inputs["input_ids"].shape[-1] :]
    return tokenizer.decode(new_tokens, skip_special_tokens=True).strip()


def build_prediction_row(
    record: dict[str, Any],
    index: int,
    generated_text: str,
    manifest_lookup: dict[str, Any],
) -> dict[str, Any]:
    messages = validate_role_order(record, index)
    gold_assistant_text = messages[2]["content"]
    metadata = metadata_for_record(record, index, manifest_lookup)
    parse_info = parse_generated_json(generated_text)
    parsed_json = parse_info["parsed_json"]
    gold_parse_info = parse_generated_json(gold_assistant_text)
    flags, counts = deterministic_flags(generated_text, parsed_json, parse_info, gold_assistant_text)

    return {
        "row_index": index + 1,
        "record_id": metadata.record_id,
        "stable_hash": metadata.stable_hash,
        "domain": metadata.domain,
        "natural_length_bucket": metadata.natural_length_bucket,
        "source_file": metadata.source_file,
        "source_line": metadata.source_line,
        "generated_text": generated_text,
        "parsed_json": parsed_json,
        "json_parse_method": parse_info["json_parse_method"],
        "json_error": parse_info["json_error"],
        "schema_status": "pass" if flags["schema_pass"] else "fail",
        "schema_errors": counts["schema_errors"],
        "gold_assistant_json": gold_parse_info["parsed_json"],
        "gold_assistant_parse_method": gold_parse_info["json_parse_method"],
        "deterministic_flags": flags,
        "deterministic_counts": counts,
    }


def summarize_rows(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)

    def count_flag(name: str) -> int:
        return sum(1 for row in rows if row["deterministic_flags"].get(name))

    summary: dict[str, Any] = {
        "count": total,
        "rates": {},
        "counts": {
            "empty_string_count": count_flag("has_empty_string"),
            "output_too_short_count": count_flag("output_too_short"),
            "output_too_long_count": count_flag("output_too_long"),
            "code_fence_or_markdown_leakage_count": count_flag("code_fence_or_markdown_leakage"),
            "extra_text_outside_json_count": count_flag("extra_text_outside_json"),
            "refusal_or_meta_response_count": count_flag("refusal_or_meta_response"),
            "prediction_mojibake_count": count_flag("prediction_mojibake"),
            "gold_mojibake_count": count_flag("gold_mojibake"),
        },
        "averages": {
            "main_idea_word_count": mean_or_none(
                row["deterministic_counts"].get("main_idea_word_count") for row in rows
            ),
            "key_point_word_count": mean_or_none(
                count
                for row in rows
                for count in row["deterministic_counts"].get("key_point_word_counts", [])
            ),
            "summary_word_count": mean_or_none(
                row["deterministic_counts"].get("summary_word_count") for row in rows
            ),
        },
    }
    for key in RATE_KEYS:
        count = count_flag(key)
        summary["rates"][key] = {
            "count": count,
            "percent": percent(count, total),
        }
    return summary


def group_breakdowns(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    by_domain: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    by_bucket: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    by_domain_bucket: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for row in rows:
        domain = str(row.get("domain") or "unknown")
        bucket = str(row.get("natural_length_bucket") or "unknown")
        by_domain[domain].append(row)
        by_bucket[bucket].append(row)
        by_domain_bucket[f"{domain} / {bucket}"].append(row)
    return {
        "by_domain": {key: summarize_rows(value) for key, value in sorted(by_domain.items())},
        "by_natural_length_bucket": {key: summarize_rows(value) for key, value in sorted(by_bucket.items())},
        "by_domain_x_natural_length_bucket": {
            key: summarize_rows(value) for key, value in sorted(by_domain_bucket.items())
        },
    }


def collect_mojibake_patterns(rows: Sequence[dict[str, Any]], field: str) -> dict[str, int]:
    counts: collections.Counter[str] = collections.Counter()
    for row in rows:
        patterns = row["deterministic_counts"].get(f"{field}_mojibake_patterns", [])
        counts.update(patterns)
    return dict(sorted(counts.items()))


def build_metrics(
    *,
    rows: Sequence[dict[str, Any]],
    config_path: Path,
    adapter_path: Path,
    data_path: Path,
    manifest_path: Path,
    output_dir: Path,
    expected_count: int,
    generation_started_at: str | None,
    generation_finished_at: str | None,
    generation_elapsed_seconds: float | None,
) -> dict[str, Any]:
    overall = summarize_rows(rows)
    return {
        "created_at": local_timestamp(),
        "scope": "Candidate A validation split only; no test-set use; no training.",
        "config_path": str(config_path),
        "adapter_path": str(adapter_path),
        "data_path": str(data_path),
        "split_manifest_path": str(manifest_path),
        "output_dir": str(output_dir),
        "validation_count": len(rows),
        "expected_validation_count": expected_count,
        "validation_count_matches_expected": len(rows) == expected_count,
        "validation_sha256": file_sha256(data_path),
        "split_manifest_sha256": file_sha256(manifest_path),
        "generation_started_at": generation_started_at,
        "generation_finished_at": generation_finished_at,
        "generation_elapsed_seconds": round(generation_elapsed_seconds, 2) if generation_elapsed_seconds is not None else None,
        "generation_elapsed": format_duration(generation_elapsed_seconds or 0.0) if generation_elapsed_seconds is not None else None,
        "generation_average_seconds_per_example": round(generation_elapsed_seconds / len(rows), 3)
        if generation_elapsed_seconds and rows
        else None,
        "mojibake_patterns_scanned": MOJIBAKE_PATTERNS,
        "deterministic_metrics": overall,
        "breakdowns": group_breakdowns(rows),
        "mojibake_pattern_counts": {
            "predictions": collect_mojibake_patterns(rows, "prediction"),
            "gold_assistant_targets": collect_mojibake_patterns(rows, "gold"),
        },
        "metric_definitions": {
            "json_parse_ok": "The stripped full model output parses as a JSON object with json.loads.",
            "schema_pass": "Full output is an exact JSON object with key order main_idea, key_points; main_idea is a string; key_points is a list of exactly four strings.",
            "main_idea_two_sentences": "Approximate punctuation-based sentence count equals two.",
            "each_key_point_one_sentence": "All four key points have approximate punctuation-based sentence count equal to one.",
            "output_too_short": "Combined parsed summary text is under 35 regex words.",
            "output_too_long": "Combined parsed summary text is over 180 regex words.",
        },
    }


def metric_table_rows(summary: dict[str, Any]) -> list[list[Any]]:
    rates = summary["rates"]
    counts = summary["counts"]
    averages = summary["averages"]
    return [
        ["count", summary["count"]],
        ["JSON parse rate", f'{rates["json_parse_ok"]["count"]}/{summary["count"]} ({rates["json_parse_ok"]["percent"]:.2f}%)'],
        ["schema pass rate", f'{rates["schema_pass"]["count"]}/{summary["count"]} ({rates["schema_pass"]["percent"]:.2f}%)'],
        ["exact key order rate", f'{rates["exact_key_order"]["count"]}/{summary["count"]} ({rates["exact_key_order"]["percent"]:.2f}%)'],
        ["main_idea string rate", f'{rates["main_idea_string"]["count"]}/{summary["count"]} ({rates["main_idea_string"]["percent"]:.2f}%)'],
        ["key_points list rate", f'{rates["key_points_list"]["count"]}/{summary["count"]} ({rates["key_points_list"]["percent"]:.2f}%)'],
        ["exactly 4 key points rate", f'{rates["exactly_4_key_points"]["count"]}/{summary["count"]} ({rates["exactly_4_key_points"]["percent"]:.2f}%)'],
        ["all key points strings rate", f'{rates["all_key_points_strings"]["count"]}/{summary["count"]} ({rates["all_key_points_strings"]["percent"]:.2f}%)'],
        ["main_idea two-sentence rate", f'{rates["main_idea_two_sentences"]["count"]}/{summary["count"]} ({rates["main_idea_two_sentences"]["percent"]:.2f}%)'],
        ["each key point one-sentence rate", f'{rates["each_key_point_one_sentence"]["count"]}/{summary["count"]} ({rates["each_key_point_one_sentence"]["percent"]:.2f}%)'],
        ["empty-string rows", counts["empty_string_count"]],
        ["output too short / too long", f'{counts["output_too_short_count"]} / {counts["output_too_long_count"]}'],
        ["avg main_idea words", averages["main_idea_word_count"]],
        ["avg key-point words", averages["key_point_word_count"]],
        ["markdown/code-fence leakage", counts["code_fence_or_markdown_leakage_count"]],
        ["extra text outside JSON", counts["extra_text_outside_json_count"]],
        ["refusal/meta-response phrases", counts["refusal_or_meta_response_count"]],
        ["prediction mojibake rows", counts["prediction_mojibake_count"]],
        ["gold mojibake rows", counts["gold_mojibake_count"]],
    ]


def breakdown_table_rows(breakdown: dict[str, Any], include_name: str) -> list[list[Any]]:
    rows: list[list[Any]] = []
    for name, summary in breakdown.items():
        rates = summary["rates"]
        counts = summary["counts"]
        rows.append(
            [
                name,
                summary["count"],
                f'{rates["json_parse_ok"]["percent"]:.2f}%',
                f'{rates["schema_pass"]["percent"]:.2f}%',
                f'{rates["main_idea_two_sentences"]["percent"]:.2f}%',
                f'{rates["each_key_point_one_sentence"]["percent"]:.2f}%',
                counts["prediction_mojibake_count"],
                counts["gold_mojibake_count"],
                counts["output_too_short_count"],
                counts["output_too_long_count"],
            ]
        )
    if include_name:
        return rows
    return rows


def select_manual_review_candidates(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    selected_hashes: set[str] = set()
    by_domain: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for row in rows:
        by_domain[str(row.get("domain") or "unknown")].append(row)

    bucket_priority = ["long", "short", "medium"]
    for domain in sorted(by_domain):
        domain_rows = by_domain[domain]
        picked: list[dict[str, Any]] = []
        for bucket in bucket_priority:
            candidates = [row for row in domain_rows if row.get("natural_length_bucket") == bucket]
            if candidates:
                picked.append(candidates[0])
            if len(picked) == 2:
                break
        if len(picked) < 2:
            for row in domain_rows:
                if row not in picked:
                    picked.append(row)
                if len(picked) == 2:
                    break
        for row in picked[:2]:
            selected.append(row)
            selected_hashes.add(row["stable_hash"])

    needs = [
        ("academic_paper", "long"),
        ("academic_book", "long"),
        ("medlineplus", None),
        ("public_service", None),
        ("assignment_rubric", None),
    ]
    for domain, bucket in needs:
        if any(row.get("domain") == domain and (bucket is None or row.get("natural_length_bucket") == bucket) for row in selected):
            continue
        for row in rows:
            if row["stable_hash"] in selected_hashes:
                continue
            if row.get("domain") == domain and (bucket is None or row.get("natural_length_bucket") == bucket):
                selected.append(row)
                selected_hashes.add(row["stable_hash"])
                break

    return selected[: max(14, len(selected))]


def build_report(metrics: dict[str, Any], rows: Sequence[dict[str, Any]]) -> str:
    overall = metrics["deterministic_metrics"]
    domain_rows = breakdown_table_rows(metrics["breakdowns"]["by_domain"], "domain")
    bucket_rows = breakdown_table_rows(metrics["breakdowns"]["by_natural_length_bucket"], "bucket")
    domain_bucket_rows = breakdown_table_rows(metrics["breakdowns"]["by_domain_x_natural_length_bucket"], "domain_bucket")
    candidates = select_manual_review_candidates(rows)
    candidate_rows = [
        [
            row["row_index"],
            row.get("domain"),
            row.get("natural_length_bucket"),
            row.get("record_id"),
            row.get("source_file"),
            row.get("source_line"),
            row.get("schema_status"),
            clean_table_cell(preview_text(row.get("generated_text") or "", 120)),
        ]
        for row in candidates
    ]

    lines = [
        "# Candidate A Validation Quality Report",
        "",
        f"Date/time: {metrics['created_at']}",
        "",
        "## Scope",
        "",
        "- Evaluated Candidate A on `data/splits/val.jsonl` only.",
        "- Did not use `data/splits/test.jsonl`.",
        "- Did not run training.",
        "- Prediction JSONL and metrics JSON are local artifacts and should not be committed without central-brain approval.",
        "",
        "## Inputs And Local Artifacts",
        "",
        f"- Config: `{metrics['config_path']}`",
        f"- Adapter: `{metrics['adapter_path']}`",
        f"- Validation data: `{metrics['data_path']}`",
        f"- Validation SHA256: `{metrics['validation_sha256']}`",
        f"- Split manifest SHA256: `{metrics['split_manifest_sha256']}`",
        f"- Validation records: `{metrics['validation_count']}` expected `{metrics['expected_validation_count']}`",
        f"- Predictions: `{Path(metrics['output_dir']) / 'validation_predictions.jsonl'}`",
        f"- Metrics: `{Path(metrics['output_dir']) / 'validation_metrics.json'}`",
        "",
        "## Generation Timing",
        "",
        f"- Started: `{metrics['generation_started_at']}`",
        f"- Finished: `{metrics['generation_finished_at']}`",
        f"- Elapsed: `{metrics['generation_elapsed']}`",
        f"- Average seconds/example: `{metrics['generation_average_seconds_per_example']}`",
        "",
        "## Deterministic Metrics",
        "",
        markdown_table(["Metric", "Value"], metric_table_rows(overall)),
        "",
        "Metric notes: sentence counts are approximate punctuation-based checks. Output too short means under 35 regex words across the parsed summary; too long means over 180 regex words.",
        "",
        "## Domain Breakdown",
        "",
        markdown_table(
            [
                "Domain",
                "N",
                "JSON Parse",
                "Schema",
                "Main 2 Sent",
                "KPs 1 Sent",
                "Pred Mojibake",
                "Gold Mojibake",
                "Too Short",
                "Too Long",
            ],
            domain_rows,
        ),
        "",
        "## Natural Length Bucket Breakdown",
        "",
        markdown_table(
            [
                "Bucket",
                "N",
                "JSON Parse",
                "Schema",
                "Main 2 Sent",
                "KPs 1 Sent",
                "Pred Mojibake",
                "Gold Mojibake",
                "Too Short",
                "Too Long",
            ],
            bucket_rows,
        ),
        "",
        "## Domain X Natural Length Bucket Breakdown",
        "",
        markdown_table(
            [
                "Domain / Bucket",
                "N",
                "JSON Parse",
                "Schema",
                "Main 2 Sent",
                "KPs 1 Sent",
                "Pred Mojibake",
                "Gold Mojibake",
                "Too Short",
                "Too Long",
            ],
            domain_bucket_rows,
        ),
        "",
        "## Encoding And Mojibake Audit",
        "",
        f"- Patterns scanned (Unicode escaped): `{json.dumps(MOJIBAKE_PATTERNS, ensure_ascii=True)}`",
        f"- Prediction mojibake rows: `{overall['counts']['prediction_mojibake_count']}`",
        f"- Gold assistant mojibake rows: `{overall['counts']['gold_mojibake_count']}`",
        f"- Prediction pattern counts: `{json_dumps_ascii(metrics['mojibake_pattern_counts']['predictions'])}`",
        f"- Gold pattern counts: `{json_dumps_ascii(metrics['mojibake_pattern_counts']['gold_assistant_targets'])}`",
        "",
        "## Script-Selected Manual Review Candidates",
        "",
        "The table below is the stratified candidate set selected by the script. The worker should replace or extend this section with completed manual labels before final submission.",
        "",
        markdown_table(
            ["Row", "Domain", "Bucket", "Record ID", "Source File", "Source Line", "Schema", "Prediction Preview"],
            candidate_rows,
        ),
        "",
        "## Manual Review",
        "",
        "Pending worker manual review.",
        "",
        "## Recommendation",
        "",
        "Pending manual review. Deterministic format metrics should be combined with stratified quality review before model-choice recommendation.",
        "",
    ]
    return "\n".join(lines)


def build_run_log(metrics: dict[str, Any]) -> str:
    overall = metrics["deterministic_metrics"]
    return "\n".join(
        [
            "# Candidate A Validation Quality Audit Log",
            "",
            f"Date/time: {metrics['created_at']}",
            "",
            "## Scope",
            "",
            "- Validation split only.",
            "- No test-set use.",
            "- No training.",
            "",
            "## Inputs",
            "",
            f"- Config: `{metrics['config_path']}`",
            f"- Adapter: `{metrics['adapter_path']}`",
            f"- Data: `{metrics['data_path']}`",
            f"- Split manifest: `{metrics['split_manifest_path']}`",
            "",
            "## Outputs",
            "",
            f"- Predictions JSONL: `{Path(metrics['output_dir']) / 'validation_predictions.jsonl'}`",
            f"- Metrics JSON: `{Path(metrics['output_dir']) / 'validation_metrics.json'}`",
            f"- Report: `reports/CANDIDATE_A_VALIDATION_QUALITY_REPORT.md`",
            "",
            "## Result Summary",
            "",
            f"- Validation records: `{metrics['validation_count']}` expected `{metrics['expected_validation_count']}`",
            f"- Validation SHA256: `{metrics['validation_sha256']}`",
            f"- Split manifest SHA256: `{metrics['split_manifest_sha256']}`",
            f"- Generation elapsed: `{metrics['generation_elapsed']}`",
            f"- Average seconds/example: `{metrics['generation_average_seconds_per_example']}`",
            f"- JSON parse: `{overall['rates']['json_parse_ok']['count']}/{overall['count']}`",
            f"- Schema pass: `{overall['rates']['schema_pass']['count']}/{overall['count']}`",
            f"- Main idea two sentences: `{overall['rates']['main_idea_two_sentences']['count']}/{overall['count']}`",
            f"- Each key point one sentence: `{overall['rates']['each_key_point_one_sentence']['count']}/{overall['count']}`",
            f"- Prediction mojibake rows: `{overall['counts']['prediction_mojibake_count']}`",
            f"- Gold mojibake rows: `{overall['counts']['gold_mojibake_count']}`",
            "",
        ]
    )


def read_prediction_rows(prediction_path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with prediction_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            value = json.loads(stripped)
            if not isinstance(value, dict):
                raise ValueError(f"Prediction row must be an object at {prediction_path}:{line_number}")
            rows.append(value)
    return rows


def refresh_prediction_rows(rows: list[dict[str, Any]], prediction_path: Path) -> list[dict[str, Any]]:
    refreshed: list[dict[str, Any]] = []
    for row in rows:
        generated_text = str(row.get("generated_text") or "")
        gold_assistant_json = row.get("gold_assistant_json")
        gold_assistant_text = json.dumps(gold_assistant_json, ensure_ascii=False) if gold_assistant_json is not None else ""
        parse_info = parse_generated_json(generated_text)
        parsed_json = parse_info["parsed_json"]
        flags, counts = deterministic_flags(generated_text, parsed_json, parse_info, gold_assistant_text)
        row["parsed_json"] = parsed_json
        row["json_parse_method"] = parse_info["json_parse_method"]
        row["json_error"] = parse_info["json_error"]
        row["schema_status"] = "pass" if flags["schema_pass"] else "fail"
        row["schema_errors"] = counts["schema_errors"]
        row["deterministic_flags"] = flags
        row["deterministic_counts"] = counts
        refreshed.append(row)

    with prediction_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in refreshed:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return refreshed


def write_prediction_rows(
    *,
    config: dict[str, Any],
    adapter_path: Path,
    data_path: Path,
    manifest_path: Path,
    output_path: Path,
    expected_count: int,
) -> tuple[list[dict[str, Any]], str, str, float]:
    records = read_jsonl(data_path)
    if len(records) != expected_count:
        print(f"WARNING: validation count {len(records)} does not match expected {expected_count}", flush=True)

    manifest_lookup = load_manifest_metadata(manifest_path)
    max_new_tokens = int(config.get("inference", {}).get("max_new_tokens", 320))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    model, tokenizer = load_model_with_adapter(config, adapter_path)

    rows: list[dict[str, Any]] = []
    start_time = time.time()
    started_at = local_timestamp()
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for index, record in enumerate(records):
            generated_text = generate_candidate_a_text(
                model,
                tokenizer,
                record,
                index=index,
                max_new_tokens=max_new_tokens,
            )
            row = build_prediction_row(record, index, generated_text, manifest_lookup)
            rows.append(row)
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            handle.flush()

            status = eta_status(start_time, index + 1, len(records), time.time())
            print(
                "[{current:03d}/{total:03d}] elapsed={elapsed} avg={avg} "
                "remaining={remaining} eta={eta} domain={domain} bucket={bucket} schema={schema}".format(
                    current=index + 1,
                    total=len(records),
                    elapsed=status["elapsed"],
                    avg=status["average_seconds_per_step"],
                    remaining=status["estimated_remaining"],
                    eta=status["estimated_completion_time"],
                    domain=row.get("domain") or "unknown",
                    bucket=row.get("natural_length_bucket") or "unknown",
                    schema=row.get("schema_status"),
                ),
                flush=True,
            )

    finished_at = local_timestamp()
    elapsed = time.time() - start_time
    return rows, started_at, finished_at, elapsed


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    config_path = resolve_project_path(root, args.config)
    config = load_yaml_config(config_path)
    adapter_path = resolve_project_path(root, args.adapter_path or config["outputs"]["adapter_dir"])
    data_path = resolve_project_path(root, args.data_path or config["data"]["val_path"])
    manifest_path = resolve_project_path(root, args.manifest_path or config["data"]["split_manifest_path"])
    output_dir = resolve_project_path(root, args.output_dir)
    prediction_path = output_dir / "validation_predictions.jsonl"
    metrics_path = output_dir / "validation_metrics.json"
    report_path = root / "reports" / "CANDIDATE_A_VALIDATION_QUALITY_REPORT.md"
    log_path = root / "logs" / "candidate_a_validation_quality_audit.md"

    if not adapter_path.exists():
        raise FileNotFoundError(f"Adapter path does not exist: {adapter_path}")
    if data_path.name == "test.jsonl":
        raise ValueError("Refusing to evaluate test.jsonl in the validation audit.")

    previous_metrics: dict[str, Any] | None = None
    if args.reuse_predictions and metrics_path.exists():
        previous_metrics = json.loads(metrics_path.read_text(encoding="utf-8"))

    if args.reuse_predictions:
        rows = refresh_prediction_rows(read_prediction_rows(prediction_path), prediction_path)
        started_at = None
        finished_at = None
        elapsed = None
    else:
        rows, started_at, finished_at, elapsed = write_prediction_rows(
            config=config,
            adapter_path=adapter_path,
            data_path=data_path,
            manifest_path=manifest_path,
            output_path=prediction_path,
            expected_count=args.expected_count,
        )

    metrics = build_metrics(
        rows=rows,
        config_path=config_path,
        adapter_path=adapter_path,
        data_path=data_path,
        manifest_path=manifest_path,
        output_dir=output_dir,
        expected_count=args.expected_count,
        generation_started_at=started_at,
        generation_finished_at=finished_at,
        generation_elapsed_seconds=elapsed,
    )
    if previous_metrics is not None and elapsed is None:
        for key in (
            "generation_started_at",
            "generation_finished_at",
            "generation_elapsed_seconds",
            "generation_elapsed",
            "generation_average_seconds_per_example",
        ):
            if previous_metrics.get(key) is not None:
                metrics[key] = previous_metrics[key]
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_text(report_path, build_report(metrics, rows))
    write_text(log_path, build_run_log(metrics))

    print(
        json.dumps(
            {
                "status": "ok",
                "validation_count": metrics["validation_count"],
                "predictions": str(prediction_path),
                "metrics": str(metrics_path),
                "report": str(report_path),
                "log": str(log_path),
                "schema_pass": metrics["deterministic_metrics"]["rates"]["schema_pass"]["count"],
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
