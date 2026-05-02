import json
import os
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from datasets import load_dataset

import extract_cleaned_openstax_samples as extractor


HERE = os.path.dirname(os.path.abspath(__file__))
FINAL_GATE_ROOT = os.path.abspath(os.path.join(HERE, "..", "final_gate_2026-04-20"))
WORKER_DIR = os.path.join(FINAL_GATE_ROOT, "step_08_round2_repair_workers", "repair2_academic_book")

SAMPLES_PATH = os.path.join(HERE, "cleaned_samples.jsonl")
OUTPUTS_PATH = os.path.join(HERE, "cleaned_outputs.jsonl")
SFT_PATH = os.path.join(HERE, "cleaned_sft.jsonl")
SAMPLES_META_PATH = os.path.join(HERE, "cleaned_samples.meta.json")
SFT_META_PATH = os.path.join(HERE, "cleaned_sft.meta.json")
LEDGER_PATH = os.path.join(WORKER_DIR, "ROUND2_REPAIR_LEDGER_academic_book.jsonl")
SUMMARY_PATH = os.path.join(WORKER_DIR, "SUMMARY.md")

SYSTEM_PROMPT = (
    "You are a reading support assistant for students with dyslexia.\n"
    "Your task is to produce a quick summary of dense academic or public-information text.\n"
    "Return only valid JSON with this schema:\n"
    "{\n"
    '  "main_idea": "2 to 3 short sentences",\n'
    '  "key_points": ["short point 1", "short point 2", "..."]\n'
    "}\n"
    "Keep the language clear, simple, and short.\n"
    "Use a short list of key points.\n"
    "Do not add information that is not supported by the source text."
)

CITATION_RE = re.compile(r"\[\d+\]")
DISALLOWED_TEXT_FRAGMENTS = [
    "Read the GAO",
    "E X P A",
    "E T H I C A",
    "Seek additional content",
    "Comparison of Tunics in Arteries and Veins",
]

# Sentence spans are 0-based and inclusive within the cleaned sentence list built from
# the row's exact live upstream slice.
REPAIRS: Dict[int, Dict[str, Any]] = {
    2: {"bucket": "medium", "sentence_span": (13, 38)},
    6: {"bucket": "medium", "sentence_span": (0, 21)},
    8: {"bucket": "short", "sentence_span": (3, 18)},
    12: {"bucket": "short", "sentence_span": (12, 23)},
    14: {"bucket": "short", "sentence_span": (17, 34)},
    19: {"bucket": "short", "sentence_span": (3, 12)},
    27: {"bucket": "medium", "sentence_span": (1, 34)},
    41: {"bucket": "short", "sentence_span": (10, 24)},
    47: {"bucket": "short", "sentence_span": (0, 14)},
    61: {"bucket": "medium", "sentence_span": (18, 43)},
    63: {"bucket": "medium", "sentence_span": (2, 33)},
    69: {"bucket": "medium", "sentence_span": (0, 33)},
    72: {"bucket": "medium", "sentence_span": (0, 29)},
    79: {"bucket": "short", "sentence_span": (6, 19)},
    87: {"bucket": "medium", "sentence_span": (3, 40)},
    98: {"bucket": "medium", "sentence_span": (8, 34)},
    100: {"bucket": "medium", "sentence_span": (0, 26)},
    101: {"bucket": "short", "sentence_span": (7, 21)},
    112: {"bucket": "short", "sentence_span": (0, 15)},
    131: {"bucket": "medium", "sentence_span": (1, 31)},
    132: {"bucket": "short", "sentence_span": (10, 29)},
    137: {"bucket": "medium", "sentence_span": (8, 35)},
    138: {"bucket": "medium", "sentence_span": (1, 38)},
    154: {"bucket": "medium", "sentence_span": (2, 36)},
    168: {"bucket": "medium", "sentence_span": (6, 29)},
    175: {"bucket": "short", "sentence_span": (9, 20)},
    198: {"bucket": "short", "sentence_span": (22, 35)},
    199: {"bucket": "medium", "sentence_span": (0, 33)},
    211: {"bucket": "medium", "sentence_span": (5, 29)},
    229: {"bucket": "medium", "sentence_span": (11, 41)},
    231: {"bucket": "short", "sentence_span": (12, 25)},
    242: {"bucket": "short", "sentence_span": (1, 15)},
    248: {"bucket": "medium", "sentence_span": (4, 33)},
    249: {"bucket": "medium", "sentence_span": (6, 40)},
}


def read_jsonl(path: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: str, rows: List[Dict[str, Any]]) -> None:
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    os.replace(tmp_path, path)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def count_by_bucket(rows: List[Dict[str, Any]]) -> Dict[str, int]:
    counts = {"short": 0, "medium": 0, "long": 0}
    for row in rows:
        counts[row["bucket"]] += 1
    return counts


def openai_summarize(text: str, model: str) -> Dict[str, Any]:
    from openai import OpenAI

    client = OpenAI()
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "main_idea": {"type": "string"},
            "key_points": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
            },
        },
        "required": ["main_idea", "key_points"],
    }
    response = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "dyslexia_summary",
                "strict": True,
                "schema": schema,
            }
        },
    )
    summary = json.loads(response.output_text)
    key_points = summary.get("key_points")
    cleaned_points: List[str] = []
    if isinstance(key_points, list):
        cleaned_points = [point.strip() for point in key_points if isinstance(point, str) and point.strip()]
    cleaned_points = cleaned_points[:3]
    while len(cleaned_points) < 3:
        fallback = summary.get("main_idea", "").strip() or text.split(".")[0].strip()
        cleaned_points.append(fallback)
    summary["key_points"] = cleaned_points
    return summary


def openai_summarize_with_retry(text: str, model: str, max_retries: int = 6) -> Dict[str, Any]:
    last_error: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        try:
            return openai_summarize(text=text, model=model)
        except Exception as exc:  # pragma: no cover - network retry path
            last_error = exc
            time.sleep(min(30.0, 2.0**attempt))
    assert last_error is not None
    raise last_error


def load_exact_source_lines(repairs: Dict[int, Dict[str, Any]], sample_rows: List[Dict[str, Any]]) -> Dict[int, List[str]]:
    targets = {
        row_index: (sample_rows[row_index - 1]["source_row_idx"], sample_rows[row_index - 1]["source_row_idx_end"])
        for row_index in repairs
    }
    starts: Dict[int, List[int]] = {}
    for row_index, (start, _) in targets.items():
        starts.setdefault(start, []).append(row_index)
    max_end = max(end for _, end in targets.values())
    active: List[Tuple[int, int, int, List[str]]] = []
    collected: Dict[int, List[str]] = {}

    stream = load_dataset("crumb/openstax-text", split="train", streaming=True)
    for row_idx, row in enumerate(stream):
        for repair_row in starts.get(row_idx, []):
            start, end = targets[repair_row]
            active.append((repair_row, start, end, []))

        for active_index, (repair_row, start, end, lines) in enumerate(active):
            if start <= row_idx <= end:
                text = row.get("text")
                if isinstance(text, str):
                    lines.append(text)
                active[active_index] = (repair_row, start, end, lines)

        finished: List[int] = []
        for active_index, (repair_row, _, end, lines) in enumerate(active):
            if row_idx >= end:
                collected[repair_row] = lines
                finished.append(active_index)
        for active_index in reversed(finished):
            del active[active_index]

        if row_idx > max_end and not active:
            break

    missing = sorted(set(repairs) - set(collected))
    if missing:
        raise SystemExit(f"Failed to load exact source lines for rows: {missing}")
    return collected


def validate_rebuilt_text(row_index: int, text: str, bucket: str, original_text: str) -> None:
    if text == original_text:
        raise SystemExit(f"Row {row_index} re-extraction matched the current live text; expected a fresh same-source window.")
    word_count = len(text.split())
    expected_bucket = extractor._bucket(word_count)
    if expected_bucket != bucket:
        raise SystemExit(
            f"Row {row_index} bucket mismatch for rebuilt text: expected {bucket}, got {expected_bucket}, wc={word_count}"
        )
    if CITATION_RE.search(text):
        raise SystemExit(f"Row {row_index} rebuilt text still contains inline citation residue.")
    for fragment in DISALLOWED_TEXT_FRAGMENTS:
        if fragment in text:
            raise SystemExit(f"Row {row_index} rebuilt text still contains blocked residue: {fragment!r}")


def build_replacements(sample_rows: List[Dict[str, Any]]) -> Tuple[Dict[int, Dict[str, Any]], List[Dict[str, Any]]]:
    source_lines = load_exact_source_lines(REPAIRS, sample_rows)
    retained_hashes = {
        row["text_sha1"]
        for index, row in enumerate(sample_rows, start=1)
        if index not in REPAIRS and row.get("text_sha1")
    }

    replacements: Dict[int, Dict[str, Any]] = {}
    ledger_rows: List[Dict[str, Any]] = []

    for row_index in sorted(REPAIRS):
        config = REPAIRS[row_index]
        start_sent, end_sent = config["sentence_span"]
        original = sample_rows[row_index - 1]
        sentences = extractor._clean_sentences(source_lines[row_index])
        if end_sent >= len(sentences):
            raise SystemExit(
                f"Row {row_index} sentence span {start_sent}-{end_sent} exceeds cleaned sentence count {len(sentences)}"
            )
        text = " ".join(sentences[start_sent : end_sent + 1]).strip()
        validate_rebuilt_text(row_index=row_index, text=text, bucket=config["bucket"], original_text=original["text"])
        text_sha1 = extractor._sha1_text(text)
        if text_sha1 in retained_hashes:
            raise SystemExit(f"Row {row_index} replacement would duplicate an untouched row: {text_sha1}")
        if text_sha1 in {item["text_sha1"] for item in replacements.values()}:
            raise SystemExit(f"Row {row_index} replacement duplicates another rebuilt row: {text_sha1}")

        new_row = dict(original)
        new_row["bucket"] = config["bucket"]
        new_row["word_count"] = len(text.split())
        new_row["text"] = text
        new_row["text_sha1"] = text_sha1
        replacements[row_index] = new_row

        ledger_rows.append(
            {
                "dataset": "academic_book",
                "row_index": row_index,
                "action_taken": "reextract_same_source",
                "source_changed": True,
                "output_regenerated": True,
                "final_provenance_status": "source_first_rebuilt",
                "note": (
                    f"same-source re-extraction replaced the noisy live window with cleaned sentence span "
                    f"{start_sent}-{end_sent}; bucket {original['bucket']}->{config['bucket']}"
                ),
            }
        )

    return replacements, ledger_rows


def apply_repairs(model: str = "gpt-4.1-mini") -> None:
    os.makedirs(WORKER_DIR, exist_ok=True)

    sample_rows = read_jsonl(SAMPLES_PATH)
    output_rows = read_jsonl(OUTPUTS_PATH)
    sft_rows = read_jsonl(SFT_PATH)
    if not (len(sample_rows) == len(output_rows) == len(sft_rows) == 250):
        raise SystemExit("Expected cleaned_samples/outputs/sft to each contain 250 rows.")

    original_bucket_counts = count_by_bucket(sample_rows)
    original_row_buckets = {row_index: sample_rows[row_index - 1]["bucket"] for row_index in REPAIRS}
    original_output_rows = {
        row_index: json.dumps(output_rows[row_index - 1], ensure_ascii=False, sort_keys=True)
        for row_index in REPAIRS
    }

    replacements, ledger_rows = build_replacements(sample_rows)

    for row_index, new_sample in replacements.items():
        sample_rows[row_index - 1] = new_sample
        summary = openai_summarize_with_retry(new_sample["text"], model=model)
        output_rows[row_index - 1] = {
            "article_id": new_sample.get("article_id"),
            "source_dataset": new_sample.get("source_dataset"),
            "source_split": new_sample.get("source_split"),
            "source_row_idx": new_sample.get("source_row_idx"),
            "word_count": new_sample.get("word_count"),
            "bucket": new_sample.get("bucket"),
            "summary": summary,
        }
        sft_rows[row_index - 1] = {
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": new_sample["text"]},
                {"role": "assistant", "content": json.dumps(summary, ensure_ascii=False)},
            ]
        }

    if not (len(sample_rows) == len(output_rows) == len(sft_rows) == 250):
        raise SystemExit("Row counts drifted while applying round-2 repairs.")

    seen_hashes: set[str] = set()
    for index, row in enumerate(sample_rows, start=1):
        text_sha1 = row["text_sha1"]
        if text_sha1 in seen_hashes:
            raise SystemExit(f"Duplicate sample text hash after repair at row {index}: {text_sha1}")
        seen_hashes.add(text_sha1)

    regenerated_changed_rows: List[int] = []
    for row_index in sorted(REPAIRS):
        if sft_rows[row_index - 1]["messages"][1]["content"] != sample_rows[row_index - 1]["text"]:
            raise SystemExit(f"Row {row_index} SFT user content is misaligned with repaired sample text.")
        json.loads(sft_rows[row_index - 1]["messages"][2]["content"])
        new_output_blob = json.dumps(output_rows[row_index - 1], ensure_ascii=False, sort_keys=True)
        if new_output_blob == original_output_rows[row_index]:
            raise SystemExit(f"Row {row_index} output row did not change after regeneration.")
        regenerated_changed_rows.append(row_index)

    write_jsonl(SAMPLES_PATH, sample_rows)
    write_jsonl(OUTPUTS_PATH, output_rows)
    write_jsonl(SFT_PATH, sft_rows)

    repaired_at = utc_now()
    final_bucket_counts = count_by_bucket(sample_rows)
    changed_bucket_rows = [
        f"{row_index} ({original_row_buckets[row_index]}->{sample_rows[row_index - 1]['bucket']})"
        for row_index in sorted(REPAIRS)
        if original_row_buckets[row_index] != sample_rows[row_index - 1]["bucket"]
    ]

    with open(SAMPLES_META_PATH, "r", encoding="utf-8") as handle:
        samples_meta = json.load(handle)
    replacement_rows = []
    for row_index in sorted(REPAIRS):
        config = REPAIRS[row_index]
        sample = sample_rows[row_index - 1]
        replacement_rows.append(
            {
                "row": row_index,
                "bucket": sample["bucket"],
                "word_count": sample["word_count"],
                "article_id": sample["article_id"],
                "sentence_span": list(config["sentence_span"]),
                "note": "round-2 same-source re-extraction selected a cleaner contiguous sentence window from the live upstream slice",
            }
        )
    meta_update = {
        "repaired_at": repaired_at,
        "repair_generator": os.path.basename(__file__),
        "repair_action": "reextract_same_source",
        "repair_rows": sorted(REPAIRS),
        "repair_counts_by_bucket": count_by_bucket([sample_rows[row_index - 1] for row_index in sorted(REPAIRS)]),
        "repair_bucket_changes": changed_bucket_rows,
        "selected_counts": final_bucket_counts,
        "replacements": replacement_rows,
        "generation_status": "final_gate_round2_same_source_rows_rebuilt_outputs_regenerated_reaudit_required",
    }
    history = list(samples_meta.get("repair_history") or [])
    history.append(meta_update)
    samples_meta.update(meta_update)
    samples_meta.pop("second_pass_release_gate", None)
    samples_meta["repair_history"] = history
    samples_meta.setdefault("outputs", {})
    samples_meta["outputs"]["samples_jsonl"] = os.path.abspath(SAMPLES_PATH)
    samples_meta["outputs"]["meta_json"] = os.path.abspath(SAMPLES_META_PATH)
    samples_meta["outputs"]["cleaned_outputs_jsonl"] = os.path.abspath(OUTPUTS_PATH)
    samples_meta["outputs"]["cleaned_sft_jsonl"] = os.path.abspath(SFT_PATH)
    samples_meta["outputs"]["cleaned_sft_meta_json"] = os.path.abspath(SFT_META_PATH)
    with open(SAMPLES_META_PATH + ".tmp", "w", encoding="utf-8") as handle:
        json.dump(samples_meta, handle, ensure_ascii=False, indent=2)
    os.replace(SAMPLES_META_PATH + ".tmp", SAMPLES_META_PATH)

    sft_meta = {
        "generated_at": repaired_at,
        "mode": "openai",
        "model": model,
        "input_path": os.path.abspath(SAMPLES_PATH),
        "n_input_read": len(sample_rows),
        "n_outputs_written": len(output_rows),
        "output_paths": {
            "outputs_jsonl": os.path.abspath(OUTPUTS_PATH),
            "sft_jsonl": os.path.abspath(SFT_PATH),
            "meta_json": os.path.abspath(SFT_META_PATH),
        },
        "note": "Assistant content is a JSON string with keys: main_idea, key_points.",
        "repair_run": {
            "dataset": "academic_book",
            "run_root": FINAL_GATE_ROOT,
            "required_action": "reextract_same_source",
            "rows_regenerated": regenerated_changed_rows,
            "row_count": len(REPAIRS),
            "status": "round2_repair_completed_reaudit_required",
        },
    }
    with open(SFT_META_PATH + ".tmp", "w", encoding="utf-8") as handle:
        json.dump(sft_meta, handle, ensure_ascii=False, indent=2)
    os.replace(SFT_META_PATH + ".tmp", SFT_META_PATH)

    write_jsonl(LEDGER_PATH, ledger_rows)

    original_counts_line = (
        f"`short`: {original_bucket_counts['short']}, "
        f"`medium`: {original_bucket_counts['medium']}, "
        f"`long`: {original_bucket_counts['long']}"
    )
    final_counts_line = (
        f"`short`: {final_bucket_counts['short']}, "
        f"`medium`: {final_bucket_counts['medium']}, "
        f"`long`: {final_bucket_counts['long']}"
    )
    changed_rows = ", ".join(str(row_index) for row_index in sorted(REPAIRS))
    summary_lines = [
        "# academic_book Round-2 Repair Summary",
        "",
        f"- Dataset: `academic_book`",
        f"- Repair action: `reextract_same_source` for all `{len(REPAIRS)}` assigned rows",
        f"- Rows rebuilt: `{changed_rows}`",
        f"- Outputs regenerated and changed: `{len(regenerated_changed_rows)}` / `{len(REPAIRS)}` repaired rows",
        f"- Row-count alignment after repair: `samples={len(sample_rows)}`, `outputs={len(output_rows)}`, `sft={len(sft_rows)}`",
        f"- Out-of-scope rows reopened: `none`",
        "",
        "## Bucket Counts",
        "",
        f"- Before round-2 repair: {original_counts_line}",
        f"- After round-2 repair: {final_counts_line}",
        "",
        "## Verification",
        "",
        "- All rebuilt rows received fresh output regeneration and their output rows changed from the pre-repair live state.",
        "- All rebuilt rows have SFT user content exactly aligned to the repaired sample text.",
        (
            "- Bucket drift introduced by round-2: "
            + (", ".join(changed_bucket_rows) if changed_bucket_rows else "none")
        ),
        "- This worker output does not declare the package ready; changed rows still require fresh re-audit under the run workflow.",
    ]
    with open(SUMMARY_PATH, "w", encoding="utf-8") as handle:
        handle.write("\n".join(summary_lines) + "\n")


if __name__ == "__main__":
    apply_repairs()
