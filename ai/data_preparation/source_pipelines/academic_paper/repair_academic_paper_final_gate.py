#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any

from datasets import load_dataset

import build_academic_paper_sft_outputs as gen
import extract_academic_paper_samples as base


REEXTRACT_ROWS = {
    25: 0,
    33: 2,
    119: 0,
    120: 0,
    139: 2,
    184: 2,
    202: 3,
    217: 0,
    242: 8,
    251: 0,
    258: 2,
    261: 2,
    262: 0,
    269: 3,
    334: 0,
    344: 2,
    355: 1,
    362: 1,
    409: 1,
    425: 2,
    428: 1,
    440: 0,
    441: 0,
    443: 3,
    445: 3,
    480: 0,
    487: 1,
}

OUTPUT_ONLY_ROWS = {397}
TARGET_ROWS = sorted(set(REEXTRACT_ROWS) | OUTPUT_ONLY_ROWS)
EXPECTED_ROW_COUNT = 500

REJECT_CONTAINS = [
    re.compile(r"<EMAIL_ADDRESS>", re.IGNORECASE),
    re.compile(r"\bISSN\b", re.IGNORECASE),
    re.compile(r"\bOpen Access\b", re.IGNORECASE),
    re.compile(r"\bcopyright\b", re.IGNORECASE),
    re.compile(r"not certified by peer review", re.IGNORECASE),
    re.compile(r"\blicense\b", re.IGNORECASE),
    re.compile(r"Click for updates", re.IGNORECASE),
    re.compile(r"www\.", re.IGNORECASE),
    re.compile(r"https?://", re.IGNORECASE),
    re.compile(r"(?<!\w)@"),
]

REJECT_LINE_START = [
    re.compile(r"^Table\b", re.IGNORECASE),
    re.compile(r"^Figure\b", re.IGNORECASE),
    re.compile(r"^Scheme\b", re.IGNORECASE),
    re.compile(r"^Appendix\b", re.IGNORECASE),
    re.compile(r"^EPJ Web of Conferences\b", re.IGNORECASE),
]

REJECT_LINE_END = [
    re.compile(r"\b(?:p|pp|Rp)\.$"),
]


def parse_args() -> argparse.Namespace:
    base_dir = Path(__file__).resolve().parent
    worker_dir = (
        base_dir.parent
        / "final_gate_2026-04-20"
        / "step_05_repair_workers"
        / "repair_academic_paper"
    )
    parser = argparse.ArgumentParser(description="Final-gate repair worker for the academic_paper dataset.")
    parser.add_argument("--samples", type=Path, default=base_dir / "academic_paper_500_repaired_samples.jsonl")
    parser.add_argument("--outputs", type=Path, default=base_dir / "academic_paper_500_repaired_outputs.jsonl")
    parser.add_argument("--sft", type=Path, default=base_dir / "academic_paper_500_repaired_sft.jsonl")
    parser.add_argument("--samples-meta", type=Path, default=base_dir / "academic_paper_500_repaired_samples.meta.json")
    parser.add_argument("--sft-meta", type=Path, default=base_dir / "academic_paper_500_repaired_sft.meta.json")
    parser.add_argument("--ledger", type=Path, default=worker_dir / "REPAIR_LEDGER_academic_paper.jsonl")
    parser.add_argument("--summary", type=Path, default=worker_dir / "SUMMARY.md")
    parser.add_argument("--model", default=gen.DEFAULT_MODEL)
    parser.add_argument("--timeout-seconds", type=int, default=120)
    parser.add_argument("--max-retries", type=int, default=4)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: dict[str, Any]) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def compact_preview(text: str, limit: int = 120) -> str:
    return re.sub(r"\s+", " ", text).strip()[:limit]


def sentence_ok(sentence: str) -> bool:
    text = sentence.strip()
    if len(text.split()) < 6:
        return False
    if text[-1] not in {".", "!", "?", '"', "'", ")", "]"}:
        return False
    if any(pattern.search(text) for pattern in REJECT_CONTAINS):
        return False
    if any(pattern.search(text) for pattern in REJECT_LINE_START):
        return False
    if any(pattern.search(text) for pattern in REJECT_LINE_END):
        return False
    return True


def paragraph_sentences(paragraph: str) -> list[str]:
    return [sentence for sentence in base.split_sentences(paragraph) if sentence_ok(sentence)]


def build_reextracted_text(
    row_index: int,
    start_paragraph: int,
    raw_text: str,
    bucket: str,
    live_word_count: int,
) -> tuple[str, str, int]:
    title, body, prep_reason = base.prepare_document(raw_text)
    if prep_reason or not body:
        raise ValueError(f"Failed to prepare raw paper for row {row_index}: {prep_reason}")

    if start_paragraph >= len(body):
        raise ValueError(f"Start paragraph {start_paragraph} out of range for row {row_index}")

    spec = base.BUCKET_SPECS[bucket]
    selected_paragraphs: list[str] = []
    current_wc = base.word_count(title) if title else 0
    best: tuple[float, str, int] | None = None

    for paragraph in body[start_paragraph:]:
        sentences = paragraph_sentences(paragraph)
        if not sentences:
            continue

        paragraph_text = " ".join(sentences)
        paragraph_wc = base.word_count(paragraph_text)

        if current_wc + paragraph_wc <= spec["max_words"]:
            selected_paragraphs.append(paragraph_text)
            current_wc += paragraph_wc
            if current_wc >= spec["min_words"]:
                text = base.join_excerpt(title, selected_paragraphs)
                score = abs(current_wc - live_word_count)
                if best is None or score < best[0]:
                    best = (score, text, current_wc)
            continue

        temp_paragraphs = list(selected_paragraphs)
        temp_wc = current_wc
        partial_sentences: list[str] = []
        for sentence in sentences:
            sentence_wc = base.word_count(sentence)
            if temp_wc + sentence_wc > spec["max_words"]:
                break
            partial_sentences.append(sentence)
            temp_wc += sentence_wc
            if temp_wc >= spec["min_words"]:
                text = base.join_excerpt(title, temp_paragraphs + [" ".join(partial_sentences)])
                score = abs(temp_wc - live_word_count)
                if best is None or score < best[0]:
                    best = (score, text, temp_wc)
        break

    if best is None:
        raise ValueError(f"Could not build a valid {bucket} candidate for row {row_index}")

    _, text, word_count = best
    return title, base.normalize_whitespace(text), word_count


def scan_raw_rows(paper_ids: set[str]) -> dict[str, dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    dataset = load_dataset(base.DATASET_NAME, split=base.DATASET_SPLIT, streaming=True)
    for row in dataset:
        paper_id = str(row.get("id") or "").strip()
        if paper_id in paper_ids and paper_id not in found:
            found[paper_id] = row
            if len(found) == len(paper_ids):
                break
    missing = sorted(paper_ids - set(found))
    if missing:
        raise ValueError(f"Failed to recover raw rows for paper_ids={missing}")
    return found


def rebuild_samples(samples: list[dict[str, Any]], raw_by_paper_id: dict[str, dict[str, Any]]) -> dict[int, dict[str, Any]]:
    updated_rows: dict[int, dict[str, Any]] = {}
    for row_index in TARGET_ROWS:
        live = dict(samples[row_index - 1])
        if row_index in OUTPUT_ONLY_ROWS:
            updated_rows[row_index] = live
            continue

        paper_id = str(live["paper_id"])
        raw_row = raw_by_paper_id[paper_id]
        title, text, word_count = build_reextracted_text(
            row_index=row_index,
            start_paragraph=REEXTRACT_ROWS[row_index],
            raw_text=str(raw_row.get("text") or ""),
            bucket=str(live["bucket"]),
            live_word_count=int(live["word_count"]),
        )
        if text == str(live["text"]):
            raise ValueError(f"Row {row_index} did not change after planned same-source re-extraction")

        live["title"] = title
        live["text"] = text
        live["word_count"] = word_count
        updated_rows[row_index] = live
    return updated_rows


def regenerate_targets(
    rows_to_generate: list[dict[str, Any]],
    api_key: str,
    model: str,
    timeout_seconds: int,
    max_retries: int,
) -> dict[int, dict[str, Any]]:
    generated: dict[int, dict[str, Any]] = {}
    for position, sample in enumerate(rows_to_generate, start=1):
        sample_index = int(sample["sample_index"])
        print(f"[{position}/{len(rows_to_generate)}] generating row {sample_index}: {sample.get('title', '')}")
        target = gen.call_openai(
            api_key=api_key,
            model=model,
            source_text=str(sample["text"]),
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )
        generated[sample_index] = target
    return generated


def write_summary(
    path: Path,
    model: str,
    samples_path: Path,
    outputs_path: Path,
    sft_path: Path,
    changed_word_counts: dict[int, tuple[int, int]],
) -> None:
    lines = [
        "# academic_paper repair summary",
        "",
        "- Planned repairs executed: `28/28`",
        "- Same-source re-extractions executed: `27`",
        "- Output-only regenerations executed: `1`",
        f"- Regenerated outputs: `{len(TARGET_ROWS)}` using `{model}`",
        f"- Updated samples file: `{samples_path}`",
        f"- Updated outputs file: `{outputs_path}`",
        f"- Updated SFT file: `{sft_path}`",
        "",
        "## Changed rows",
        "",
        "| Row | Action | Word count change |",
        "| --- | --- | --- |",
    ]
    for row_index in TARGET_ROWS:
        if row_index in OUTPUT_ONLY_ROWS:
            lines.append(f"| {row_index} | regenerate_output_only | unchanged |")
            continue
        before, after = changed_word_counts[row_index]
        lines.append(f"| {row_index} | reextract_same_source | {before} -> {after} |")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("Missing OPENAI_API_KEY environment variable.")

    samples = gen.load_jsonl(args.samples)
    outputs = gen.load_jsonl(args.outputs)
    sft_rows = gen.load_jsonl(args.sft)
    if len(samples) != EXPECTED_ROW_COUNT or len(outputs) != EXPECTED_ROW_COUNT or len(sft_rows) != EXPECTED_ROW_COUNT:
        raise SystemExit("Unexpected row count in live academic_paper files.")

    paper_ids = {str(samples[row_index - 1]["paper_id"]) for row_index in TARGET_ROWS}
    raw_by_paper_id = scan_raw_rows(paper_ids)
    rebuilt_samples = rebuild_samples(samples, raw_by_paper_id)

    changed_word_counts: dict[int, tuple[int, int]] = {}
    rows_to_generate: list[dict[str, Any]] = []
    for row_index in TARGET_ROWS:
        original = samples[row_index - 1]
        updated = rebuilt_samples[row_index]
        rows_to_generate.append(updated)
        if row_index not in OUTPUT_ONLY_ROWS:
            changed_word_counts[row_index] = (int(original["word_count"]), int(updated["word_count"]))

    generated_targets = regenerate_targets(
        rows_to_generate=rows_to_generate,
        api_key=api_key,
        model=args.model,
        timeout_seconds=args.timeout_seconds,
        max_retries=args.max_retries,
    )

    updated_samples = list(samples)
    updated_outputs = list(outputs)
    updated_sft_rows = list(sft_rows)
    ledger_rows: list[dict[str, Any]] = []

    for row_index in TARGET_ROWS:
        sample = rebuilt_samples[row_index]
        sample_index = int(sample["sample_index"])
        target = generated_targets[sample_index]

        if row_index in REEXTRACT_ROWS:
            updated_samples[row_index - 1] = sample
            provenance_status = "source_first_rebuilt"
            action_taken = "reextract_same_source"
            source_changed = True
            note = (
                f"Rebuilt from the same raw paper using paragraph anchor {REEXTRACT_ROWS[row_index]} "
                "and regenerated the assistant output."
            )
        else:
            provenance_status = "output_only_regenerated"
            action_taken = "regenerate_output_only"
            source_changed = False
            note = "Kept the live source/sample text unchanged and regenerated the assistant output."

        updated_outputs[row_index - 1] = gen.build_raw_record(sample, target, args.model)
        updated_sft_rows[row_index - 1] = gen.build_sft_record(sample, target)
        ledger_rows.append(
            {
                "dataset": "academic_paper",
                "row_index": row_index,
                "action_taken": action_taken,
                "source_changed": source_changed,
                "output_regenerated": True,
                "final_provenance_status": provenance_status,
                "note": note,
            }
        )

    gen.write_jsonl(args.samples, updated_samples)
    gen.write_jsonl(args.outputs, updated_outputs)
    gen.write_jsonl(args.sft, updated_sft_rows)
    gen.write_jsonl(args.ledger, ledger_rows)

    samples_meta = load_json(args.samples_meta)
    samples_meta["final_gate_repair_2026_04_20"] = {
        "repaired_dataset": "academic_paper",
        "changed_rows": TARGET_ROWS,
        "reextract_same_source_rows": sorted(REEXTRACT_ROWS),
        "regenerate_output_only_rows": sorted(OUTPUT_ONLY_ROWS),
        "worker_ledger": str(args.ledger),
        "worker_summary": str(args.summary),
    }
    write_json(args.samples_meta, samples_meta)

    sft_meta = load_json(args.sft_meta)
    sft_meta["final_gate_repair_2026_04_20"] = {
        "repaired_dataset": "academic_paper",
        "changed_rows": TARGET_ROWS,
        "reextract_same_source_rows": sorted(REEXTRACT_ROWS),
        "regenerate_output_only_rows": sorted(OUTPUT_ONLY_ROWS),
        "generated_now": len(TARGET_ROWS),
        "model": args.model,
        "worker_ledger": str(args.ledger),
        "worker_summary": str(args.summary),
    }
    write_json(args.sft_meta, sft_meta)

    write_summary(
        path=args.summary,
        model=args.model,
        samples_path=args.samples,
        outputs_path=args.outputs,
        sft_path=args.sft,
        changed_word_counts=changed_word_counts,
    )

    print(f"Wrote updated samples to {args.samples}")
    print(f"Wrote updated outputs to {args.outputs}")
    print(f"Wrote updated SFT rows to {args.sft}")
    print(f"Wrote repair ledger to {args.ledger}")
    print(f"Wrote repair summary to {args.summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
