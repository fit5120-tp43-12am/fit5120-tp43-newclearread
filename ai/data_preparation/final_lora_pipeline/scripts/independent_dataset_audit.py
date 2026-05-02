from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs" / "pipeline_config.json"
DEFAULT_FINAL_DIR = ROOT / "outputs" / "final_dataset_v1"

ABBREVIATIONS = {
    ".gov",
    "a.m.",
    "apr.",
    "aug.",
    "c.",
    "dec.",
    "dept.",
    "dr.",
    "e.g.",
    "etc.",
    "feb.",
    "fig.",
    "gov.",
    "i.e.",
    "inc.",
    "jan.",
    "jul.",
    "jun.",
    "ltd.",
    "mar.",
    "mr.",
    "mrs.",
    "ms.",
    "no.",
    "nov.",
    "oct.",
    "p.m.",
    "prof.",
    "sep.",
    "sept.",
    "st.",
    "u.k.",
    "u.s.",
    "vs.",
    "www.",
}

TITLE_ABBREVIATIONS = {"dr.", "fig.", "mr.", "mrs.", "ms.", "no.", "prof.", "st.", "vs."}
NEVER_BOUNDARY_ABBREVIATIONS = {"a.m.", "e.g.", "i.e.", "p.m.", "www."}
COUNTRY_ABBREVIATION_CONTINUATIONS = {
    "agency",
    "agencies",
    "business",
    "businesses",
    "citizen",
    "citizens",
    "company",
    "companies",
    "department",
    "departments",
    "embassy",
    "embassies",
    "government",
    "governments",
    "law",
    "laws",
    "resident",
    "residents",
    "state",
    "states",
    "territories",
    "territory",
    "visa",
    "visas",
    "worker",
    "workers",
}
LIKELY_SENTENCE_STARTERS = {"a", "an", "it", "the", "these", "they", "this", "those"}

MOJIBAKE_PATTERNS = [
    "\ufffd",
    "\u9225",
    "\u8305",
    "\u00c3",
    "\u00c2",
    "\u00e2\u20ac",
    "\u934f",
    "\u5d85",
    "\u59df",
    "\u6f12",
    "\u6dd0",
]

BAD_ASSISTANT_PATTERNS = [
    r"```",
    r"^\s*here (is|are)\b",
    r"\bas an ai\b",
    r"\bi cannot\b",
    r"\bi can('|no)t\b",
    r"\bsorry\b",
    r"\bmarkdown\b",
    r"\bjson\s*:\s*\{",
    r"\bI will\b",
]

CJK_RE = re.compile(r"[\u4e00-\u9fff]")
WORD_RE = re.compile(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)?")
WEB_SUFFIXES = {"com", "edu", "gov", "mil", "net", "org"}


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def extract_role_content(record: dict[str, Any], role: str) -> str | None:
    messages = record.get("messages")
    if not isinstance(messages, list):
        return None
    for message in messages:
        if isinstance(message, dict) and message.get("role") == role:
            content = message.get("content")
            return content if isinstance(content, str) else None
    return None


def words(text: str) -> list[str]:
    return WORD_RE.findall(text.lower())


def word_count(text: str) -> int:
    return len(words(text))


def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    k = (len(ordered) - 1) * p / 100
    floor = math.floor(k)
    ceil = math.ceil(k)
    if floor == ceil:
        return ordered[int(k)]
    return ordered[floor] * (ceil - k) + ordered[ceil] * (k - floor)


def summary_stats(values: list[float]) -> dict[str, Any]:
    if not values:
        return {}
    return {
        "min": round(min(values), 4),
        "p05": round(percentile(values, 5), 4),
        "median": round(percentile(values, 50), 4),
        "mean": round(sum(values) / len(values), 4),
        "p95": round(percentile(values, 95), 4),
        "max": round(max(values), 4),
    }


def independent_sentences(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text.strip())
    if not normalized:
        return []

    units: list[str] = []
    start = 0
    index = 0
    while index < len(normalized):
        char = normalized[index]
        if char in ".!?":
            prev_char = normalized[index - 1] if index > 0 else ""
            next_char = normalized[index + 1] if index + 1 < len(normalized) else ""

            if char == "." and prev_char.isdigit() and next_char.isdigit():
                index += 1
                continue
            if char == "." and normalized[index + 1 : index + 4].lower() in WEB_SUFFIXES:
                after_suffix = normalized[index + 4] if index + 4 < len(normalized) else ""
                if not after_suffix.isalpha():
                    index += 1
                    continue
            if char == "." and prev_char.isalpha() and next_char.isalpha():
                index += 1
                continue

            chunk = normalized[start : index + 1].strip()
            parts = chunk.lower().split()
            tail_token = parts[-1] if parts else ""
            next_word_match = re.match(r"\s+([A-Za-z][A-Za-z-]*)", normalized[index + 1 :])
            next_word = next_word_match.group(1) if next_word_match else ""

            if char == ".":
                next_word_lower = next_word.lower()
                if tail_token in NEVER_BOUNDARY_ABBREVIATIONS or tail_token in TITLE_ABBREVIATIONS:
                    index += 1
                    continue
                if tail_token == "c." and next_word and next_word[:1].islower():
                    index += 1
                    continue
                if tail_token in {"u.k.", "u.s."}:
                    if (
                        not next_word
                        or next_word[:1].islower()
                        or next_word_lower in COUNTRY_ABBREVIATION_CONTINUATIONS
                        or (next_word.isupper() and len(next_word) <= 6)
                    ):
                        index += 1
                        continue
                    if next_word_lower not in LIKELY_SENTENCE_STARTERS:
                        index += 1
                        continue
                if tail_token in {".gov", "gov."}:
                    if not next_word or next_word[:1].islower():
                        index += 1
                        continue
                if tail_token in ABBREVIATIONS:
                    if next_word and next_word[:1].islower():
                        index += 1
                        continue
                if re.search(r"\b\w+\.(com|edu|gov|mil|net|org)\.?$", chunk.lower()):
                    index += 1
                    continue

            units.append(chunk)
            start = index + 1
        index += 1

    tail = normalized[start:].strip()
    if tail:
        units.append(tail)
    return [unit for unit in units if unit]


def jaccard_similarity(left: str, right: str) -> float:
    left_words = set(words(left))
    right_words = set(words(right))
    if not left_words and not right_words:
        return 1.0
    if not left_words or not right_words:
        return 0.0
    return len(left_words & right_words) / len(left_words | right_words)


def add_issue(issues: list[dict[str, Any]], severity: str, code: str, detail: dict[str, Any]) -> None:
    issues.append({"severity": severity, "code": code, "detail": detail})


def compact_record_for_report(item: dict[str, Any]) -> dict[str, Any]:
    kept = {key: value for key, value in item.items() if key != "assistant"}
    if "assistant" in item:
        kept["assistant"] = item["assistant"][:260]
    return kept


def build_source_index(config: dict[str, Any]) -> tuple[dict[tuple[str, str], dict[str, Any]], Counter[str], list[Any]]:
    source_index: dict[tuple[str, str], dict[str, Any]] = {}
    source_counts: Counter[str] = Counter()
    duplicates: list[Any] = []

    for dataset in config["datasets"]:
        slug = dataset["slug"]
        source_path = Path(dataset["source_path"])
        with source_path.open("r", encoding="utf-8") as fh:
            for line_number, line in enumerate(fh, 1):
                record = json.loads(line)
                user_text = extract_role_content(record, "user")
                source_hash = sha256_text(user_text or "")
                key = (slug, source_hash)
                if key in source_index:
                    duplicates.append({"slug": slug, "line_number": line_number, "first_line": source_index[key]["line_number"]})
                source_index[key] = {
                    "slug": slug,
                    "line_number": line_number,
                    "source_path": str(source_path),
                    "user_text": user_text,
                }
                source_counts[slug] += 1

    return source_index, source_counts, duplicates


def audit_accepted_dataset(
    config: dict[str, Any],
    final_dir: Path,
    source_index: dict[tuple[str, str], dict[str, Any]],
    prompt: str,
) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    accepted_keys: set[tuple[str, str]] = set()
    assistant_hashes: defaultdict[str, list[tuple[str, str, str, str]]] = defaultdict(list)
    lengths: list[dict[str, Any]] = []
    mojibake_user: list[dict[str, Any]] = []
    mojibake_assistant: list[dict[str, Any]] = []
    non_ascii_assistant: list[dict[str, Any]] = []
    cjk_assistant: list[dict[str, Any]] = []

    for dataset in config["datasets"]:
        slug = dataset["slug"]
        accepted_path = final_dir / "accepted" / dataset["accepted_filename"]
        with accepted_path.open("r", encoding="utf-8") as fh:
            for line_index, line in enumerate(fh, 1):
                loc = f"accepted/{dataset['accepted_filename']}:{line_index}"
                raw_line = line.rstrip("\n")
                try:
                    record = json.loads(raw_line)
                except json.JSONDecodeError as exc:
                    add_issue(issues, "critical", "outer_json_invalid", {"loc": loc, "error": str(exc)})
                    continue

                messages = record.get("messages")
                if not isinstance(messages, list) or len(messages) != 3:
                    add_issue(
                        issues,
                        "critical",
                        "bad_messages_shape",
                        {"loc": loc, "type": type(messages).__name__, "length": len(messages) if isinstance(messages, list) else None},
                    )
                    continue

                roles = [message.get("role") if isinstance(message, dict) else None for message in messages]
                if roles != ["system", "user", "assistant"]:
                    add_issue(issues, "critical", "bad_roles", {"loc": loc, "roles": roles})

                if messages[0].get("content") != prompt:
                    add_issue(issues, "major", "system_prompt_drift", {"loc": loc})

                user_text = messages[1].get("content")
                assistant_text = messages[2].get("content")
                if not isinstance(user_text, str) or not user_text.strip():
                    add_issue(issues, "critical", "empty_user", {"loc": loc})
                    continue
                if not isinstance(assistant_text, str) or not assistant_text.strip():
                    add_issue(issues, "critical", "empty_assistant", {"loc": loc})
                    continue

                source_hash = sha256_text(user_text)
                key = (slug, source_hash)
                if key not in source_index:
                    add_issue(issues, "critical", "accepted_not_in_source", {"loc": loc, "slug": slug, "sha": source_hash[:12]})
                if key in accepted_keys:
                    add_issue(issues, "critical", "duplicate_accepted_source", {"loc": loc, "slug": slug, "sha": source_hash[:12]})
                accepted_keys.add(key)

                for pattern in MOJIBAKE_PATTERNS:
                    if pattern in user_text:
                        mojibake_user.append({"loc": loc, "slug": slug, "pattern": repr(pattern)})
                        break
                for pattern in MOJIBAKE_PATTERNS:
                    if pattern in assistant_text:
                        mojibake_assistant.append({"loc": loc, "pattern": repr(pattern), "assistant": assistant_text[:220]})
                        break
                if any(ord(char) > 127 for char in assistant_text):
                    non_ascii_assistant.append({"loc": loc, "assistant": assistant_text[:220]})
                if CJK_RE.search(assistant_text):
                    cjk_assistant.append({"loc": loc, "assistant": assistant_text[:220]})

                if not assistant_text.lstrip().startswith("{") or not assistant_text.rstrip().endswith("}"):
                    add_issue(
                        issues,
                        "critical",
                        "assistant_not_single_json_object_text",
                        {"loc": loc, "assistant_start": assistant_text[:80]},
                    )

                try:
                    assistant = json.loads(assistant_text)
                except json.JSONDecodeError as exc:
                    add_issue(
                        issues,
                        "critical",
                        "assistant_json_invalid",
                        {"loc": loc, "error": str(exc), "assistant": assistant_text[:220]},
                    )
                    continue

                if list(assistant.keys()) != ["main_idea", "key_points"]:
                    add_issue(issues, "critical", "assistant_key_order_or_keys_bad", {"loc": loc, "keys": list(assistant.keys())})

                main_idea = assistant.get("main_idea")
                key_points = assistant.get("key_points")
                if not isinstance(main_idea, str):
                    add_issue(issues, "critical", "main_idea_not_string", {"loc": loc})
                    continue
                if not isinstance(key_points, list):
                    add_issue(issues, "critical", "key_points_not_list", {"loc": loc})
                    continue

                main_sentences = independent_sentences(main_idea)
                if len(main_sentences) != 2:
                    add_issue(
                        issues,
                        "major",
                        "independent_main_sentence_count",
                        {"loc": loc, "count": len(main_sentences), "main_idea": main_idea},
                    )
                if len(main_idea) < 30:
                    add_issue(issues, "minor", "main_idea_very_short", {"loc": loc, "chars": len(main_idea), "main_idea": main_idea})
                if len(main_idea) > 360:
                    add_issue(issues, "minor", "main_idea_very_long", {"loc": loc, "chars": len(main_idea), "main_idea": main_idea[:220]})

                if len(key_points) != 4:
                    add_issue(issues, "critical", "key_points_count", {"loc": loc, "count": len(key_points)})

                for point_index, point in enumerate(key_points, 1):
                    if not isinstance(point, str):
                        add_issue(issues, "critical", "key_point_not_string", {"loc": loc, "index": point_index})
                        continue
                    point_sentences = independent_sentences(point)
                    if len(point_sentences) != 1:
                        add_issue(
                            issues,
                            "major",
                            "independent_key_point_sentence_count",
                            {"loc": loc, "index": point_index, "count": len(point_sentences), "text": point},
                        )
                    if len(point) < 18:
                        add_issue(issues, "minor", "key_point_very_short", {"loc": loc, "index": point_index, "chars": len(point), "text": point})
                    if len(point) > 260:
                        add_issue(issues, "minor", "key_point_very_long", {"loc": loc, "index": point_index, "chars": len(point), "text": point[:220]})
                    if not point.strip().endswith((".", "!", "?")):
                        add_issue(issues, "minor", "key_point_no_terminal_punctuation", {"loc": loc, "index": point_index, "text": point})

                if len(key_points) == 4 and all(isinstance(point, str) for point in key_points):
                    for left_index in range(4):
                        for right_index in range(left_index + 1, 4):
                            similarity = jaccard_similarity(key_points[left_index], key_points[right_index])
                            if similarity >= 0.72:
                                add_issue(
                                    issues,
                                    "major",
                                    "similar_key_points",
                                    {
                                        "loc": loc,
                                        "i": left_index + 1,
                                        "j": right_index + 1,
                                        "jaccard": round(similarity, 3),
                                        "a": key_points[left_index],
                                        "b": key_points[right_index],
                                    },
                                )

                if len(main_sentences) == 2:
                    main_similarity = jaccard_similarity(main_sentences[0], main_sentences[1])
                    if main_similarity >= 0.75:
                        add_issue(
                            issues,
                            "major",
                            "similar_main_sentences",
                            {"loc": loc, "jaccard": round(main_similarity, 3), "main_idea": main_idea},
                        )

                for pattern in BAD_ASSISTANT_PATTERNS:
                    if re.search(pattern, assistant_text, flags=re.IGNORECASE | re.MULTILINE):
                        add_issue(
                            issues,
                            "major",
                            "assistant_artifact_or_refusal_pattern",
                            {"loc": loc, "pattern": pattern, "assistant": assistant_text[:220]},
                        )

                assistant_words = word_count(main_idea + " " + " ".join(str(point) for point in key_points))
                user_words = word_count(user_text)
                ratio = assistant_words / user_words if user_words else 0.0
                lengths.append(
                    {
                        "loc": loc,
                        "slug": slug,
                        "user_words": user_words,
                        "assistant_words": assistant_words,
                        "ratio": ratio,
                        "assistant": assistant_text,
                    }
                )
                if assistant_words < 35:
                    add_issue(
                        issues,
                        "major",
                        "assistant_too_short",
                        {"loc": loc, "assistant_words": assistant_words, "assistant": assistant_text},
                    )
                if assistant_words > 155:
                    add_issue(
                        issues,
                        "minor",
                        "assistant_long",
                        {"loc": loc, "assistant_words": assistant_words, "assistant": assistant_text[:260]},
                    )
                if user_words >= 250 and ratio > 0.30:
                    add_issue(
                        issues,
                        "minor",
                        "summary_ratio_high",
                        {"loc": loc, "user_words": user_words, "assistant_words": assistant_words, "ratio": round(ratio, 3)},
                    )

                assistant_hashes[sha256_text(assistant_text)].append((loc, slug, source_hash[:12], assistant_text))

    duplicate_assistant_groups = []
    for _assistant_hash, items in assistant_hashes.items():
        source_set = {(item[1], item[2]) for item in items}
        if len(source_set) > 1:
            duplicate_assistant_groups.append({"count": len(items), "examples": items[:5]})

    user_words = [item["user_words"] for item in lengths]
    assistant_words = [item["assistant_words"] for item in lengths]
    ratios = [item["ratio"] for item in lengths]
    by_dataset: defaultdict[str, dict[str, Any]] = defaultdict(lambda: {"accepted": 0, "user_words": [], "assistant_words": [], "ratio": []})
    for item in lengths:
        dataset_summary = by_dataset[item["slug"]]
        dataset_summary["accepted"] += 1
        dataset_summary["user_words"].append(item["user_words"])
        dataset_summary["assistant_words"].append(item["assistant_words"])
        dataset_summary["ratio"].append(item["ratio"])

    by_dataset_summary = {}
    for slug, item in by_dataset.items():
        by_dataset_summary[slug] = {
            "accepted": item["accepted"],
            "user_words_median": round(percentile(item["user_words"], 50), 1),
            "assistant_words_median": round(percentile(item["assistant_words"], 50), 1),
            "ratio_median": round(percentile(item["ratio"], 50), 4),
        }

    return {
        "accepted_keys": accepted_keys,
        "issues": issues,
        "issue_severity_counts": dict(Counter(issue["severity"] for issue in issues)),
        "issue_code_counts": dict(Counter(issue["code"] for issue in issues).most_common()),
        "issue_examples": issues[:80],
        "stats": {
            "user_words": summary_stats(user_words),
            "assistant_words": summary_stats(assistant_words),
            "summary_ratio": summary_stats(ratios),
        },
        "by_dataset": by_dataset_summary,
        "duplicate_assistant_label_groups": len(duplicate_assistant_groups),
        "duplicate_assistant_examples": duplicate_assistant_groups[:10],
        "mojibake_user_count": len(mojibake_user),
        "mojibake_user_examples": mojibake_user[:20],
        "mojibake_assistant_count": len(mojibake_assistant),
        "mojibake_assistant_examples": mojibake_assistant[:20],
        "non_ascii_assistant_count": len(non_ascii_assistant),
        "non_ascii_assistant_examples": non_ascii_assistant[:20],
        "cjk_assistant_count": len(cjk_assistant),
        "cjk_assistant_examples": cjk_assistant[:20],
        "shortest_assistant_examples": [compact_record_for_report(item) for item in sorted(lengths, key=lambda item: item["assistant_words"])[:10]],
        "longest_assistant_examples": [compact_record_for_report(item) for item in sorted(lengths, key=lambda item: item["assistant_words"], reverse=True)[:10]],
        "highest_ratio_examples": [compact_record_for_report(item) for item in sorted(lengths, key=lambda item: item["ratio"], reverse=True)[:10]],
    }


def audit_quarantine_dataset(config: dict[str, Any], final_dir: Path, source_index: dict[tuple[str, str], dict[str, Any]]) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    quarantine_keys: set[tuple[str, str]] = set()
    reason_counts: Counter[str] = Counter()
    last_stage_counts: Counter[str] = Counter()

    for dataset in config["datasets"]:
        slug = dataset["slug"]
        path = final_dir / "quarantine" / f"{slug}_quarantine.jsonl"
        with path.open("r", encoding="utf-8") as fh:
            for line_index, line in enumerate(fh, 1):
                loc = f"quarantine/{slug}_quarantine.jsonl:{line_index}"
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    add_issue(issues, "critical", "quarantine_json_invalid", {"loc": loc, "error": str(exc)})
                    continue
                source_hash = record.get("source_sha256")
                key = (slug, source_hash)
                if key not in source_index:
                    add_issue(issues, "critical", "quarantine_not_in_source", {"loc": loc, "sha": str(source_hash)[:12]})
                if key in quarantine_keys:
                    add_issue(issues, "critical", "duplicate_quarantine_source", {"loc": loc, "sha": str(source_hash)[:12]})
                quarantine_keys.add(key)
                reason_counts[str(record.get("reason", ""))[:140]] += 1
                last_stage_counts[str(record.get("last_stage", ""))] += 1

    return {
        "quarantine_keys": quarantine_keys,
        "issues": issues,
        "issue_counts": dict(Counter(issue["code"] for issue in issues)),
        "last_stage_counts": dict(last_stage_counts),
        "reason_top20": reason_counts.most_common(20),
    }


def write_reports(report: dict[str, Any], reports_dir: Path) -> tuple[Path, Path]:
    reports_dir.mkdir(parents=True, exist_ok=True)
    json_path = reports_dir / "independent_dataset_audit.json"
    md_path = reports_dir / "independent_dataset_audit.md"

    json_report = dict(report)
    json_report["accepted_keys"] = None
    json_report["quarantine_keys"] = None
    with json_path.open("w", encoding="utf-8", newline="\n") as fh:
        json.dump(json_report, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    coverage = report["coverage"]
    accepted = report["accepted"]
    quarantine = report["quarantine"]

    with md_path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write("# Independent Dataset Audit\n\n")
        fh.write("This audit is independent of the project pipeline structural gate. It re-parses source, accepted, and quarantine files directly.\n\n")
        fh.write("## Coverage\n\n")
        for key, value in coverage.items():
            fh.write(f"- {key}: `{value}`\n")
        fh.write("\n## Accepted Issue Counts\n\n")
        fh.write(f"- by severity: `{accepted['issue_severity_counts']}`\n")
        fh.write(f"- by code: `{accepted['issue_code_counts']}`\n")
        fh.write("\n## Length Statistics\n\n")
        fh.write(f"- user_words: `{accepted['stats']['user_words']}`\n")
        fh.write(f"- assistant_words: `{accepted['stats']['assistant_words']}`\n")
        fh.write(f"- summary_ratio: `{accepted['stats']['summary_ratio']}`\n")
        fh.write("\n## Encoding Signals\n\n")
        fh.write(f"- mojibake_user_count: `{accepted['mojibake_user_count']}`\n")
        fh.write(f"- mojibake_assistant_count: `{accepted['mojibake_assistant_count']}`\n")
        fh.write(f"- non_ascii_assistant_count: `{accepted['non_ascii_assistant_count']}`\n")
        fh.write(f"- cjk_assistant_count: `{accepted['cjk_assistant_count']}`\n")
        fh.write("\n## Quarantine\n\n")
        fh.write(f"- issue_counts: `{quarantine['issue_counts']}`\n")
        fh.write(f"- last_stage_counts: `{quarantine['last_stage_counts']}`\n")
        fh.write("\n## Notes\n\n")
        fh.write("- Critical accepted issues indicate records that should not be trained without repair or removal.\n")
        fh.write("- Major accepted issues indicate records that deserve manual review before high-confidence training.\n")
        fh.write("- Semantic truthfulness cannot be fully proven by deterministic checks; use a second independent judge for that layer.\n")

    return json_path, md_path


def run_audit(config_path: Path, final_dir: Path) -> dict[str, Any]:
    config = read_json(config_path)
    prompt = (ROOT / "prompts" / "generation_system.txt").read_text(encoding="utf-8").strip()
    source_index, source_counts, source_duplicates = build_source_index(config)
    accepted = audit_accepted_dataset(config, final_dir, source_index, prompt)
    quarantine = audit_quarantine_dataset(config, final_dir, source_index)

    accepted_keys = accepted.pop("accepted_keys")
    quarantine_keys = quarantine.pop("quarantine_keys")
    source_keys = set(source_index.keys())

    coverage = {
        "source_total": len(source_keys),
        "accepted_total": len(accepted_keys),
        "quarantine_total": len(quarantine_keys),
        "accepted_quarantine_overlap": len(accepted_keys & quarantine_keys),
        "missing_source_records": len(source_keys - accepted_keys - quarantine_keys),
        "unexpected_records": len((accepted_keys | quarantine_keys) - source_keys),
        "source_duplicate_count": len(source_duplicates),
        "source_counts": dict(source_counts),
    }

    return {
        "config_path": str(config_path),
        "final_dir": str(final_dir),
        "coverage": coverage,
        "accepted": accepted,
        "quarantine": quarantine,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run an independent offline audit of final LoRA JSONL outputs.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--final-dir", type=Path, default=DEFAULT_FINAL_DIR)
    args = parser.parse_args()

    report = run_audit(args.config, args.final_dir)
    json_path, md_path = write_reports(report, args.final_dir / "reports")
    print(json.dumps({"report_json": str(json_path), "report_md": str(md_path), "coverage": report["coverage"], "accepted_issue_counts": report["accepted"]["issue_code_counts"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
