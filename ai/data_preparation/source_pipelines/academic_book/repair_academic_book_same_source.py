import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from datasets import load_dataset

import extract_cleaned_openstax_samples as extractor


HERE = os.path.dirname(os.path.abspath(__file__))
FINAL_GATE_ROOT = os.path.abspath(os.path.join(HERE, "..", "final_gate_2026-04-20"))
WORKER_DIR = os.path.join(FINAL_GATE_ROOT, "step_05_repair_workers", "repair_academic_book")

SAMPLES_PATH = os.path.join(HERE, "cleaned_samples.jsonl")
OUTPUTS_PATH = os.path.join(HERE, "cleaned_outputs.jsonl")
SFT_PATH = os.path.join(HERE, "cleaned_sft.jsonl")
SAMPLES_META_PATH = os.path.join(HERE, "cleaned_samples.meta.json")
SFT_META_PATH = os.path.join(HERE, "cleaned_sft.meta.json")
LEDGER_PATH = os.path.join(WORKER_DIR, "REPAIR_LEDGER_academic_book.jsonl")
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


# Sentence spans are 0-based and inclusive. Buckets may change when that is needed to
# produce a clean same-source window from the exact live upstream slice.
REPAIRS: Dict[int, Dict[str, Any]] = {
    1: {
        "bucket": "medium",
        "sentence_span": (23, 51),
        "note": "same-source re-extraction shifted from a mixed long visual-pathway window to a cleaner thalamus/cortical-processing passage",
    },
    6: {
        "bucket": "medium",
        "sentence_span": (13, 35),
        "note": "same-source re-extraction removed exercise residue and the broken standing-balance tail",
    },
    17: {
        "bucket": "short",
        "sentence_span": (17, 36),
        "note": "same-source re-extraction narrowed the mixed civil-rights/incivility slice to a cleaner standalone passage",
    },
    18: {
        "bucket": "short",
        "sentence_span": (8, 24),
        "note": "same-source re-extraction removed header residue before the solar-layer explanation",
    },
    24: {
        "bucket": "short",
        "sentence_span": (18, 26),
        "note": "same-source re-extraction replaced the broken article-tail slice with a clean employer-coverage passage",
    },
    26: {
        "bucket": "short",
        "sentence_span": (7, 26),
        "note": "same-source re-extraction removed numbered-list residue and rebuilt a coherent bond-accounting window",
    },
    30: {
        "bucket": "short",
        "sentence_span": (9, 23),
        "note": "same-source re-extraction replaced the mid-context opening with a clean cardiac conduction passage",
    },
    45: {
        "bucket": "short",
        "sentence_span": (1, 13),
        "note": "same-source re-extraction removed the unresolved opening and kept a cleaner legal-system overview",
    },
    61: {
        "bucket": "medium",
        "sentence_span": (11, 39),
        "note": "same-source re-extraction removed the inherited donation-example opening and rebuilt around internal-control requirements",
    },
    63: {
        "bucket": "medium",
        "sentence_span": (1, 32),
        "note": "same-source re-extraction removed bullet residue before the EPO discussion",
    },
    69: {
        "bucket": "medium",
        "sentence_span": (0, 34),
        "note": "same-source re-extraction rebuilt the anatomy window without repaired-looking source noise",
    },
    71: {
        "bucket": "medium",
        "sentence_span": (2, 26),
        "note": "same-source re-extraction rebuilt the muscle-contraction window from a cleaner sentence boundary",
    },
    98: {
        "bucket": "medium",
        "sentence_span": (8, 35),
        "note": "same-source re-extraction removed the truncated citation tail",
    },
    101: {
        "bucket": "medium",
        "sentence_span": (2, 32),
        "note": "same-source re-extraction removed the transition/header residue before the motivation content",
    },
    134: {
        "bucket": "medium",
        "sentence_span": (2, 29),
        "note": "same-source re-extraction removed local source trimming from the membrane-transport passage",
    },
    154: {
        "bucket": "medium",
        "sentence_span": (4, 39),
        "note": "same-source re-extraction replaced the repaired-looking cranial-fossa opening with a clean section start",
    },
    157: {
        "bucket": "medium",
        "sentence_span": (10, 27),
        "note": "same-source re-extraction replaced the unresolved MI opening with a clean infarction/treatment passage",
    },
    173: {
        "bucket": "short",
        "sentence_span": (4, 20),
        "note": "same-source re-extraction avoided the broken figure carryover and page-tail artifact",
    },
    183: {
        "bucket": "short",
        "sentence_span": (6, 25),
        "note": "same-source re-extraction narrowed the mixed cash-flow/ergonomics slice to a coherent payment-methods passage",
    },
    207: {
        "bucket": "short",
        "sentence_span": (1, 23),
        "note": "same-source re-extraction removed the garbled calculus tail before the formula-heavy ending",
    },
    210: {
        "bucket": "medium",
        "sentence_span": (3, 31),
        "note": "same-source re-extraction removed direct-patch provenance from the smooth-muscle window",
    },
    211: {
        "bucket": "long",
        "sentence_span": (3, 40),
        "note": "same-source re-extraction removed direct-patch provenance from the vessel-wall window",
    },
    217: {
        "bucket": "medium",
        "sentence_span": (21, 53),
        "note": "same-source re-extraction removed the dangling parenthetical opening before the field discussion",
    },
    235: {
        "bucket": "short",
        "sentence_span": (15, 33),
        "note": "same-source re-extraction replaced the sacrum-coccyx drift with a coherent intervertebral-disc passage",
    },
    243: {
        "bucket": "medium",
        "sentence_span": (16, 39),
        "note": "same-source re-extraction removed source noise and rebuilt around animal communication signals",
    },
    249: {
        "bucket": "medium",
        "sentence_span": (5, 38),
        "note": "same-source re-extraction replaced the mid-thought hormones opening with a clean endocrine overview",
    },
}

PRE_REPAIR_BUCKET_COUNTS = {"short": 50, "medium": 175, "long": 25}

PRE_REPAIR_ROW_BUCKETS = {
    1: "long",
    6: "medium",
    17: "long",
    18: "short",
    24: "medium",
    26: "short",
    30: "short",
    45: "short",
    61: "medium",
    63: "medium",
    69: "medium",
    71: "medium",
    98: "medium",
    101: "medium",
    134: "medium",
    154: "medium",
    157: "medium",
    173: "medium",
    183: "medium",
    207: "medium",
    210: "medium",
    211: "long",
    217: "medium",
    235: "medium",
    243: "medium",
    249: "medium",
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
        bucket = row["bucket"]
        counts[bucket] += 1
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
    cleaned_points = []
    if isinstance(key_points, list):
        cleaned_points = [point.strip() for point in key_points if isinstance(point, str) and point.strip()]
    cleaned_points = cleaned_points[:3]
    while len(cleaned_points) < 3:
        fallback = summary.get("main_idea", "").strip() or text.split(".")[0].strip()
        cleaned_points.append(fallback)
    summary["key_points"] = cleaned_points
    return summary


def openai_summarize_with_retry(text: str, model: str, max_retries: int = 6) -> Dict[str, Any]:
    last_error: Exception | None = None
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
    starts = {start: row_index for row_index, (start, _) in targets.items()}
    max_end = max(end for _, end in targets.values())
    active: List[Tuple[int, int, int, List[str]]] = []
    collected: Dict[int, List[str]] = {}

    stream = load_dataset("crumb/openstax-text", split="train", streaming=True)
    for row_idx, row in enumerate(stream):
        if row_idx in starts:
            repair_row = starts[row_idx]
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


def validate_bucket(text: str, bucket: str) -> None:
    word_count = len(text.split())
    expected = extractor._bucket(word_count)
    if expected != bucket:
        raise SystemExit(
            f"Bucket mismatch for rebuilt text: expected {bucket}, got {expected}, wc={word_count}"
        )


def build_replacements(sample_rows: List[Dict[str, Any]]) -> Tuple[Dict[int, Dict[str, Any]], List[Dict[str, Any]]]:
    source_lines = load_exact_source_lines(REPAIRS, sample_rows)
    retained_hashes = {
        row["text_sha1"]
        for index, row in enumerate(sample_rows, start=1)
        if index not in REPAIRS and row.get("text_sha1")
    }

    replacements: Dict[int, Dict[str, Any]] = {}
    ledger_preview: List[Dict[str, Any]] = []

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
        validate_bucket(text, config["bucket"])
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

        ledger_preview.append(
            {
                "dataset": "academic_book",
                "row_index": row_index,
                "action_taken": "reextract_same_source",
                "source_changed": original["text"] != text,
                "output_regenerated": True,
                "final_provenance_status": "source_first_rebuilt",
                "note": (
                    f"{config['note']}; source sentence span {start_sent}-{end_sent}; "
                    f"bucket {original['bucket']}->{config['bucket']}"
                ),
            }
        )

    return replacements, ledger_preview


def apply_repairs(model: str = "gpt-4.1-mini") -> None:
    os.makedirs(WORKER_DIR, exist_ok=True)

    sample_rows = read_jsonl(SAMPLES_PATH)
    output_rows = read_jsonl(OUTPUTS_PATH)
    sft_rows = read_jsonl(SFT_PATH)
    if not (len(sample_rows) == len(output_rows) == len(sft_rows) == 250):
        raise SystemExit("Expected cleaned_samples/outputs/sft to each contain 250 rows.")

    original_bucket_counts = dict(PRE_REPAIR_BUCKET_COUNTS)
    original_buckets = dict(PRE_REPAIR_ROW_BUCKETS)
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

    seen_hashes: set[str] = set()
    for index, row in enumerate(sample_rows, start=1):
        text_sha1 = row["text_sha1"]
        if text_sha1 in seen_hashes:
            raise SystemExit(f"Duplicate sample text hash after repair at row {index}: {text_sha1}")
        seen_hashes.add(text_sha1)

    for row_index in REPAIRS:
        if sft_rows[row_index - 1]["messages"][1]["content"] != sample_rows[row_index - 1]["text"]:
            raise SystemExit(f"Row {row_index} SFT user content is misaligned with repaired sample text.")
        json.loads(sft_rows[row_index - 1]["messages"][2]["content"])

    write_jsonl(SAMPLES_PATH, sample_rows)
    write_jsonl(OUTPUTS_PATH, output_rows)
    write_jsonl(SFT_PATH, sft_rows)

    repaired_at = utc_now()
    final_bucket_counts = count_by_bucket(sample_rows)
    changed_bucket_rows = [
        f"{row_index} ({original_buckets[row_index]}->{sample_rows[row_index - 1]['bucket']})"
        for row_index in sorted(REPAIRS)
        if original_buckets[row_index] != sample_rows[row_index - 1]["bucket"]
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
                "note": config["note"],
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
        "generation_status": "final_gate_same_source_rows_rebuilt_outputs_regenerated_reaudit_required",
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
            "rows_regenerated": sorted(REPAIRS),
            "row_count": len(REPAIRS),
            "status": "repair_completed_reaudit_required",
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
        "# academic_book Repair Summary",
        "",
        f"- Dataset: `academic_book`",
        f"- Repair action: `reextract_same_source` for all `{len(REPAIRS)}` assigned rows",
        f"- Rows rebuilt: `{changed_rows}`",
        f"- Outputs regenerated: `{len(REPAIRS)}` rows in `cleaned_outputs.jsonl` and `cleaned_sft.jsonl`",
        "",
        "## Bucket Counts",
        "",
        f"- Before repair: {original_counts_line}",
        f"- After repair: {final_counts_line}",
        "",
        "## Notes",
        "",
        (
            "- Bucket changes: "
            + (", ".join(changed_bucket_rows) if changed_bucket_rows else "none")
        ),
        "- `cleaned_samples.meta.json` and `cleaned_sft.meta.json` were updated to reflect this repair pass and to avoid declaring package readiness.",
        "- This worker output does not declare the package ready; changed rows still require fresh re-audit under the run workflow.",
    ]
    with open(SUMMARY_PATH, "w", encoding="utf-8") as handle:
        handle.write("\n".join(summary_lines) + "\n")


if __name__ == "__main__":
    apply_repairs()
