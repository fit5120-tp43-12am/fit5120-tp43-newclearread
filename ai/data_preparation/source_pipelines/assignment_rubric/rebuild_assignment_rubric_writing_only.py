#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from huggingface_hub import hf_hub_download
import pyarrow.parquet as pq


HERE = Path(__file__).resolve().parent
OUTPUT_SAMPLES = HERE / "assignment_rubric_150_samples_writing_only.jsonl"
OUTPUT_META = HERE / "assignment_rubric_150_samples_writing_only.meta.json"

DATASET_REPO = "sojuL/RubricHub_v1"
DATASET_FILE = "RuRL/rurbichub_v1_Writing.parquet"

TOTAL_TARGET = 150
BUCKET_SPECS = {
    "short": (250, 499),
    "medium": (500, 800),
    "long": (801, 1200),
}

POSITIVE_PATTERN = re.compile(
    r"\b("
    r"essay|research paper|paper|technical paper|review paper|literature review|"
    r"report|lab report|experimental report|reflection paper|reflection report|"
    r"book review|critical review|executive summary|analytical summary|abstract|"
    r"presentation|seminar presentation|project|assignment|thesis|dissertation|"
    r"proposal|case study|white paper"
    r")\b",
    re.IGNORECASE,
)

ACADEMIC_CONTEXT_PATTERN = re.compile(
    r"\b("
    r"academic|college|university|graduate|undergraduate|scholarly|citation|citations|"
    r"reference|references|apa|mla|harvard|thesis|methodology|argument|critique|"
    r"introduction|conclusion|analysis|seminar|research|journal|conference|student|"
    r"literary|history|science|engineering|law|health|medical|environmental"
    r")\b",
    re.IGNORECASE,
)

ACTION_PATTERN = re.compile(
    r"\b("
    r"write|draft|prepare|create|develop|propose|devise|generate|construct|"
    r"outline|help me write|help me draft|please help me write|please help me draft|"
    r"is needed|is required"
    r")\b",
    re.IGNORECASE,
)

NEGATIVE_PATTERN = re.compile(
    r"\b("
    r"seo|meta description|table of contents|travel guide|newsletter|content writer|blog|"
    r"story|chapter|plot|fictional|manga|screenplay|poem|song|one-shot|"
    r"translate|translation|translate into|polish the writing|rewrite the whole sentence|"
    r"course outline|course plan|learning outcomes|syllabus|lesson plan|"
    r"book title|book on |book about|article on |write an article|ghostwriter|"
    r"marketing|sales|customer|tattoo|weather patterns unit|"
    r"submission date|acronym|working names|facebook post|report card comment|"
    r"school board|candidate|furniture company|community awareness flyer|"
    r"company website|market entry report|personal statement|family law attorneys|"
    r"rewrite:|re write|edit:|history of paper|strategies can writers use|"
    r"generate ai event|best family law attorneys|dear doctor|hi doctor|"
    r"medical report|inguinal hernia|semen analysis|"
    r"act like me|i will send a passage|teacher\b|homework assignment|"
    r"dissertation defense presentation template|doctoral dissertation defense presentation|"
    r"product development proposal|premium health and wellness platform|executive wellness|"
    r"commercial real estate|real estate investment|business proposal|"
    r"workshop presentation script|school administrators|educational partners|"
    r"pitch presentation|launch targeting|theoretical and practical significance|"
    r"telehealth solutions.*website|market research findings|corporate clients|"
    r"\[role\]|write only in paragraphs to explain following points|"
    r"part 5 of your essay|find the answers for the following assignment|"
    r"act as a historian|csv files|learning objectives|"
    r"conference presentation outline|prepare a 10-minute talk|"
    r"polish every paragraph|methodology section|opening speech|"
    r"personal essays|evergreen technologies|commercial real estate|"
    r"we submitted a paper to icml|smart tourism|"
    r"profitability analysis report"
    r")\b",
    re.IGNORECASE,
)


def normalize_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def word_count(text: str) -> int:
    return len(text.split()) if text else 0


def latin_ratio(text: str) -> float:
    alpha_chars = [ch for ch in text if ch.isalpha()]
    if not alpha_chars:
        return 0.0
    latin = sum(1 for ch in alpha_chars if ("A" <= ch <= "Z") or ("a" <= ch <= "z"))
    return latin / len(alpha_chars)


def cjk_count(text: str) -> int:
    return sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")


def extract_prompt_text(row: dict[str, Any]) -> str:
    parts: list[str] = []
    for message in row.get("prompt", []) or []:
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            parts.append(content.strip())
    return normalize_whitespace("\n\n".join(parts))


def extract_rubric_lines(row: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    rubrics = row.get("Rubrics") or row.get("reward_model", {}).get("rubrics", []) or []
    for idx, item in enumerate(rubrics, start=1):
        if not isinstance(item, dict):
            continue
        criterion = str(item.get("criterion") or "").strip()
        if not criterion:
            continue
        points = item.get("points")
        if isinstance(points, (int, float)):
            score = int(points) if float(points).is_integer() else points
            lines.append(f"{idx}. [{score} pts] {criterion}")
        else:
            lines.append(f"{idx}. {criterion}")
    return lines


def build_text(prompt_text: str, rubric_lines: list[str]) -> str:
    return normalize_whitespace(
        "Assignment Brief:\n"
        f"{prompt_text}\n\n"
        "Scoring Rubric:\n"
        + "\n".join(rubric_lines)
    )


def bucket_for(count: int) -> str | None:
    for bucket, (minimum, maximum) in BUCKET_SPECS.items():
        if minimum <= count <= maximum:
            return bucket
    return None


def score(candidate: dict[str, Any]) -> tuple[Any, ...]:
    academic_hits = len(
        re.findall(
            r"\b(research|academic|journal|conference|literature review|essay|report|paper|thesis|proposal|presentation|reference|citation)\b",
            candidate["prompt_text"],
            re.IGNORECASE,
        )
    )
    return (
        -academic_hits,
        -candidate["rubric_count"],
        abs(candidate["word_count"] - {"short": 360, "medium": 620, "long": 960}[candidate["bucket"]]),
        candidate["row_index"],
    )


def main() -> int:
    parquet_path = hf_hub_download(DATASET_REPO, DATASET_FILE, repo_type="dataset")
    parquet_file = pq.ParquetFile(parquet_path)

    candidates = []
    row_index = 0
    for batch in parquet_file.iter_batches(batch_size=512):
        for row in batch.to_pylist():
            row_index += 1
            prompt_text = extract_prompt_text(row)
            if not prompt_text:
                continue
            if not POSITIVE_PATTERN.search(prompt_text):
                continue
            if not ACADEMIC_CONTEXT_PATTERN.search(prompt_text):
                continue
            if not ACTION_PATTERN.search(prompt_text):
                continue
            if NEGATIVE_PATTERN.search(prompt_text):
                continue

            rubric_lines = extract_rubric_lines(row)
            if len(rubric_lines) < 8:
                continue

            text = build_text(prompt_text, rubric_lines)
            if cjk_count(text) != 0:
                continue
            if latin_ratio(text) < 0.97:
                continue

            bucket = bucket_for(word_count(text))
            if bucket is None:
                continue

            title = normalize_whitespace(prompt_text.splitlines()[0])[:180]
            candidates.append(
                {
                    "row_index": row_index,
                    "bucket": bucket,
                    "word_count": word_count(text),
                    "rubric_count": len(rubric_lines),
                    "task_title": title,
                    "prompt_text": prompt_text,
                    "text": text,
                }
            )

    candidates.sort(key=score)

    short = [x for x in candidates if x["bucket"] == "short"]
    medium = [x for x in candidates if x["bucket"] == "medium"]
    long = [x for x in candidates if x["bucket"] == "long"]

    selected = short + medium
    remaining = TOTAL_TARGET - len(selected)
    if remaining < 0:
        selected = selected[:TOTAL_TARGET]
    else:
        selected.extend(long[:remaining])

    if len(selected) < TOTAL_TARGET:
        raise RuntimeError(f"Only found {len(selected)} writing-only candidates, needed {TOTAL_TARGET}.")

    output_rows = []
    for idx, item in enumerate(selected, start=1):
        output_rows.append(
            {
                "sample_index": idx,
                "bucket": item["bucket"],
                "word_count": item["word_count"],
                "task_type": "writing_only_assignment_like",
                "task_title": item["task_title"],
                "quality_tier": 0,
                "translation_like": False,
                "cjk_count": 0,
                "latin_ratio": round(latin_ratio(item["text"]), 4),
                "rubric_count": item["rubric_count"],
                "source_dataset": DATASET_REPO,
                "source_dataset_file": DATASET_FILE,
                "source_dataset_url": "https://huggingface.co/datasets/sojuL/RubricHub_v1",
                "source_dataset_real_origin": "RubricHub_v1 RuRL Writing subset",
                "source_license": "Apache-2.0",
                "source_scope": "single_prompt_single_rubric_set",
                "source_row_index": item["row_index"],
                "text": item["text"],
            }
        )

    with OUTPUT_SAMPLES.open("w", encoding="utf-8", newline="\n") as handle:
        for row in output_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    OUTPUT_META.write_text(
        json.dumps(
            {
                "dataset_repo": DATASET_REPO,
                "dataset_file": DATASET_FILE,
                "total_rows": len(output_rows),
                "bucket_counts": dict(Counter(row["bucket"] for row in output_rows)),
                "selection_note": "Writing-only strict rebuild prioritizing English-only and assignment/rubric coherence over target length distribution.",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Wrote {OUTPUT_SAMPLES}")
    print(f"Counts: {Counter(row['bucket'] for row in output_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
