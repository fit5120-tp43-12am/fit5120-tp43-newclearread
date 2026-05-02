#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from huggingface_hub import hf_hub_download
import pyarrow.parquet as pq


DATASET_REPO = "sojuL/RubricHub_v1"
DATASET_FILES = [
    "RuRL/rurbichub_v1_Writing.parquet",
    "RuRL/rurbichub_v1_Science.parquet",
    "RuRL/rurbichub_v1_Chat.parquet",
    "RuRL/rurbichub_v1_Instruction_Following.parquet",
    "RuRL/rurbichub_v1_Medical.parquet",
]
DATASET_URL = "https://huggingface.co/datasets/sojuL/RubricHub_v1"
SOURCE_REAL_ORIGIN = "RubricHub_v1 prompt-rubric pairs (curated across multiple subsets)"
SOURCE_SCOPE = "single_prompt_single_rubric_set"
SOURCE_LICENSE = "Apache-2.0"

REQUESTED_BUCKET_TARGETS = {
    "short": 30,
    "medium": 105,
    "long": 15,
}

BUCKET_SPECS = {
    "short": {"min_words": 250, "max_words": 499, "target_words": 360},
    "medium": {"min_words": 500, "max_words": 800, "target_words": 620},
    "long": {"min_words": 801, "max_words": 1200, "target_words": 960},
}

POSITIVE_PATTERN = re.compile(
    r"\b("
    r"essay|research paper|paper|technical paper|review paper|literature review|"
    r"report|lab report|reflection report|reflection paper|book review|critical review|"
    r"executive summary|analytical summary|abstract|introduction|conclusion|"
    r"presentation|seminar presentation|poster presentation|assignment|thesis|dissertation|"
    r"proposal|research proposal|case study|annotated bibliography|position paper"
    r")\b",
    re.IGNORECASE,
)

ACTION_PATTERN = re.compile(
    r"\b("
    r"write|draft|prepare|create|develop|propose|construct|outline|summarize|"
    r"help me write|help me draft|please help me write|please help me draft|"
    r"is needed|is required|craft"
    r")\b",
    re.IGNORECASE,
)

ACADEMIC_CONTEXT_PATTERN = re.compile(
    r"\b("
    r"academic|college|university|undergraduate|graduate|student|students|scholarly|"
    r"citation|citations|reference|references|apa|mla|harvard|journal|conference|"
    r"seminar|thesis|research|argument|analysis|literature|methodology|critical|"
    r"course|curriculum|peer review|bibliography"
    r")\b",
    re.IGNORECASE,
)

STUDENT_SIGNAL_PATTERN = re.compile(
    r"\b("
    r"student|college|university|undergraduate|graduate|course|semester|assignment|"
    r"class|seminar|professor|citation|references|essay|paper|report|thesis|presentation"
    r")\b",
    re.IGNORECASE,
)

NEGATIVE_PATTERN = re.compile(
    r"\b("
    r"translate|translation|translated|translator|bilingual|mandarin|chinese|"
    r"rewrite|re-write|polish the writing|paraphrase|proofread|grammar check|"
    r"seo|meta description|newsletter|blog|social media|facebook post|marketing|sales|"
    r"product launch|company website|website copy|landing page|brand|customer|corporate clients|"
    r"competitive analysis report|product development proposal|\bkpi\b|market research findings|"
    r"market performance|strategic positioning|industry data from recent reports|"
    r"commercial real estate|investment analysis report|"
    r"nodejs|node\.js|react|frontend|backend|mvc application|json file|csv files|vue project|"
    r"story|chapter|fiction|fictional|poem|song|screenplay|manga|novel chapter|"
    r"teacher\b|lesson plan|course outline|course plan|learning outcomes|syllabus|"
    r"roleplay|act as|act like me|ignore all previous instructions|prompt injection|"
    r"medical report|mri report|semen analysis|doctor|patient|diagnosis|treatment plan|"
    r"personal statement|cover letter|resume|job application|"
    r"travel guide|weather patterns unit|"
    r"report card comment|school board|campaign speech|"
    r"write an article|ghostwriter|"
    r"working names|acronym|extract the dollar amounts|"
    r"i will send|i will give|continue previous|"
    r"how to say in a research paper|opening speech|"
    r"what strategies can|answerable question based on the context|"
    r"answer ->|sentence a\b|template\b|personal essays|"
    r"thesis statement\b"
    r")\b",
    re.IGNORECASE,
)

QA_OR_INSTRUCTION_PATTERN = re.compile(
    r"("
    r"choose one letter from the given options|"
    r"###answer:|###explanation:|"
    r"json object with two fields|"
    r"\bverdict\b|\bevidence\b|"
    r"include a palindrome|"
    r"entire response should be in|"
    r"\[role\]|\[task\]|\[demonstration\]|"
    r"reviewer.*increase their score|"
    r"can we convince this reviewer|"
    r"can you summarize following words"
    r")",
    re.IGNORECASE,
)

BUSINESS_OR_PRODUCT_PATTERN = re.compile(
    r"("
    r"data analytics manager|"
    r"investment analysts?|"
    r"profitability analysis|"
    r"financial performance|"
    r"quarterly earnings|"
    r"employee turnover|"
    r"employee wellness survey|"
    r"micro and small cap|small cap stocks?|portfolio diversification|"
    r"business report|"
    r"market abuse|import businesses|"
    r"executive relocation|white-glove concierge|"
    r"corporate sustainability announcement|"
    r"business analysis briefing|"
    r"pricing tiers|platform launch|"
    r"product description|smartwatch|"
    r"wellness platform|corporate executive clients|"
    r"chief information security officer|ciso|"
    r"potential investor|strategic partnership|"
    r"keynote introduction|"
    r"professional article|"
    r"cal newport|"
    r"white paper|"
    r"gastroscope|"
    r"biologics company|"
    r"spiral dynamics|integral leadership|"
    r"\baws\b|amazon\b|tesla\b|evergreen technologies"
    r")",
    re.IGNORECASE,
)

COURSE_DESIGN_PATTERN = re.compile(
    r"("
    r"learning objectives|"
    r"create a comprehensive and cohesive lesson|"
    r"design a comprehensive .* course|"
    r"course outline|"
    r"encourage enrollment|"
    r"record to report|"
    r"first day lesson"
    r")",
    re.IGNORECASE,
)

META_FRAGMENT_PATTERN = re.compile(
    r"("
    r"part 5 of your essay|"
    r"annual report introduction|"
    r"dr\. miranda chen|"
    r"proposal presentation|"
    r"pitch presentation|"
    r"with these companies as an audience|"
    r"the best of both worlds|"
    r"why is it important to develop case definitions"
    r")",
    re.IGNORECASE,
)

LANGUAGE_MISMATCH_PATTERN = re.compile(
    r"("
    r"chinese characters|"
    r"response should be in hebrew|"
    r"response should be in bengali"
    r")",
    re.IGNORECASE,
)

MOJIBAKE_PATTERN = re.compile(
    r"(?:Ã.|Â.|â[\x80-\xbf]?|鈥|鈧|锟|�|憁|€|™|œ|ž)"
)

PROMPT_INJECTION_PATTERN = re.compile(
    r"\b("
    r"start and end your response|first word of your response|last word of each sentence|"
    r"all lowercase words|all capital letters|letter [a-z] should appear less than|"
    r"no word should be repeated|repeat the request word for word|"
    r"enclose every word|postscript starting with|markdown divider|square brackets"
    r")\b",
    re.IGNORECASE,
)

META_ASSISTANT_PATTERN = re.compile(
    r"\b("
    r"assistant explicitly states|asks the user|requests the user|before proceeding|"
    r"clarifying questions?|if the outline is missing, the presenter explicitly states"
    r")\b",
    re.IGNORECASE,
)

UNICODE_REPLACEMENTS = {
    "\u00a0": " ",
    "\u2002": " ",
    "\u2003": " ",
    "\u2009": " ",
    "\u200b": "",
    "\u2010": "-",
    "\u2011": "-",
    "\u2012": "-",
    "\u2013": "-",
    "\u2014": "-",
    "\u2015": "-",
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u2022": "-",
    "\u2026": "...",
    "\u2212": "-",
    "\u00d7": "x",
    "\u00b1": "+/-",
    "\u00b0": " degrees ",
    "\u03b1": " alpha ",
    "\u03b2": " beta ",
    "\u03b3": " gamma ",
    "\u03bc": " micro ",
    "\u03c0": " pi ",
    "\u2082": "2",
    "\u2083": "3",
    "\u00b2": "2",
    "\u00b3": "3",
}

FILE_RANK = {
    "RuRL/rurbichub_v1_Writing.parquet": 0,
    "RuRL/rurbichub_v1_Science.parquet": 1,
    "RuRL/rurbichub_v1_Chat.parquet": 2,
    "RuRL/rurbichub_v1_Instruction_Following.parquet": 3,
    "RuRL/rurbichub_v1_Medical.parquet": 4,
}

TITLE_STOPWORDS = {
    "a",
    "an",
    "and",
    "about",
    "academic",
    "active",
    "all",
    "analysis",
    "analytical",
    "analyze",
    "approximately",
    "authoritative",
    "body",
    "can",
    "coherent",
    "comprehensive",
    "complex",
    "complete",
    "create",
    "critical",
    "detailed",
    "draft",
    "essay",
    "for",
    "formal",
    "full",
    "help",
    "highly",
    "in",
    "include",
    "including",
    "informative",
    "introduction",
    "language",
    "literary",
    "me",
    "methodology",
    "of",
    "on",
    "organized",
    "paper",
    "please",
    "polished",
    "prepare",
    "presentation",
    "proposal",
    "provide",
    "references",
    "report",
    "research",
    "section",
    "sentence",
    "sentences",
    "single",
    "structures",
    "support",
    "the",
    "thesis",
    "tone",
    "transition",
    "using",
    "verbatim",
    "with",
    "words",
    "write",
    "writing",
}


def parse_args() -> argparse.Namespace:
    base_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description="Build a clean English-only assignment/rubric dataset from RubricHub."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=base_dir / "assignment_rubric_150_samples_final.jsonl",
    )
    parser.add_argument(
        "--meta-output",
        type=Path,
        default=base_dir / "assignment_rubric_150_samples_final.meta.json",
    )
    parser.add_argument("--analyze-only", action="store_true")
    return parser.parse_args()


def normalize_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" ?\n ?", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_unicode(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    for old, new in UNICODE_REPLACEMENTS.items():
        text = text.replace(old, new)
    return normalize_whitespace(text)


def maybe_fix_mojibake(text: str) -> str:
    candidates = [text]
    for encoding in ("latin-1", "cp1252"):
        try:
            candidates.append(text.encode(encoding).decode("utf-8"))
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass

    def score(item: str) -> tuple[int, int]:
        suspicious = len(MOJIBAKE_PATTERN.findall(item))
        non_ascii = sum(1 for ch in item if ord(ch) > 127 and ch not in "\n\t")
        return suspicious, non_ascii

    return min(candidates, key=score)


def sanitize_text(text: str) -> str:
    return clean_unicode(maybe_fix_mojibake(text))


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


def suspicious_char_count(text: str) -> int:
    return len(MOJIBAKE_PATTERN.findall(text))


def extract_prompt_text(row: dict[str, Any]) -> str:
    parts: list[str] = []
    for message in row.get("prompt", []) or []:
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            parts.append(content.strip())
    return sanitize_text("\n\n".join(parts))


def extract_rubric_lines(row: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    rubrics = row.get("Rubrics") or row.get("reward_model", {}).get("rubrics", []) or []
    for idx, item in enumerate(rubrics, start=1):
        if not isinstance(item, dict):
            continue
        criterion = sanitize_text(str(item.get("criterion") or "").strip())
        if not criterion:
            continue
        points = item.get("points")
        if isinstance(points, (int, float)):
            score = int(points) if float(points).is_integer() else points
            lines.append(f"{idx}. [{score} pts] {criterion}")
        else:
            lines.append(f"{idx}. {criterion}")
    return lines


def build_sample_text(prompt_text: str, rubric_lines: list[str]) -> str:
    text = (
        "Assignment Brief:\n"
        f"{prompt_text}\n\n"
        "Scoring Rubric:\n"
        + "\n".join(rubric_lines)
    )
    return sanitize_text(text)


def bucket_for_word_count(count: int) -> str | None:
    for bucket, spec in BUCKET_SPECS.items():
        if spec["min_words"] <= count <= spec["max_words"]:
            return bucket
    return None


def classify_task_type(prompt_text: str) -> str:
    lowered = prompt_text.lower()
    if "literature review" in lowered:
        return "literature_review"
    if "research paper" in lowered or "thesis" in lowered or "dissertation" in lowered:
        return "research_paper"
    if "essay" in lowered:
        return "essay"
    if "report" in lowered:
        return "report"
    if "abstract" in lowered:
        return "abstract"
    if "presentation" in lowered:
        return "presentation"
    if "proposal" in lowered:
        return "proposal"
    if "annotated bibliography" in lowered:
        return "annotated_bibliography"
    return "other_assignment_like"


def derive_task_title(prompt_text: str) -> str:
    first_line = prompt_text.splitlines()[0].strip()
    title = re.sub(r"\s+", " ", first_line).strip(" -*#")
    if len(title) > 160:
        title = title[:157].rstrip() + "..."
    return title


def text_signature(prompt_text: str) -> str:
    collapsed = re.sub(r"[^a-z0-9]+", " ", prompt_text.lower())
    collapsed = re.sub(r"\s+", " ", collapsed).strip()
    return hashlib.sha1(collapsed.encode("utf-8")).hexdigest()


def title_topic_tokens(title: str) -> set[str]:
    tokens = {
        token
        for token in re.findall(r"[a-z0-9]+", title.lower())
        if len(token) > 2 and token not in TITLE_STOPWORDS
    }
    return tokens


def title_jaccard_similarity(left: str, right: str) -> float:
    left_tokens = title_topic_tokens(left)
    right_tokens = title_topic_tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    overlap = left_tokens & right_tokens
    union = left_tokens | right_tokens
    if len(overlap) < 3:
        return 0.0
    return len(overlap) / len(union)


def is_near_duplicate_title(candidate: dict[str, Any], selected: list[dict[str, Any]]) -> bool:
    for prior in selected:
        if candidate["task_type"] != prior["task_type"]:
            continue
        if title_jaccard_similarity(candidate["task_title"], prior["task_title"]) >= 0.8:
            return True
    return False


def is_clean_english(text: str) -> bool:
    if not text:
        return False
    if cjk_count(text) != 0:
        return False
    if suspicious_char_count(text) != 0:
        return False
    if latin_ratio(text) < 0.97:
        return False
    return True


def candidate_sort_key(candidate: dict[str, Any]) -> tuple[Any, ...]:
    target_words = BUCKET_SPECS[candidate["bucket"]]["target_words"]
    student_signal = 0 if candidate["student_signal"] else 1
    task_rank = {
        "literature_review": 0,
        "research_paper": 1,
        "essay": 2,
        "report": 3,
        "abstract": 4,
        "presentation": 5,
        "proposal": 6,
        "annotated_bibliography": 7,
        "other_assignment_like": 8,
    }.get(candidate["task_type"], 9)
    return (
        FILE_RANK.get(candidate["source_dataset_file"], 9),
        student_signal,
        task_rank,
        abs(candidate["word_count"] - target_words),
        -candidate["rubric_count"],
        candidate["source_row_index"],
    )


def load_candidates() -> tuple[dict[str, list[dict[str, Any]]], Counter]:
    candidates_by_bucket: dict[str, list[dict[str, Any]]] = defaultdict(list)
    stats = Counter()
    seen_signatures: set[str] = set()

    for dataset_file in DATASET_FILES:
        parquet_path = hf_hub_download(DATASET_REPO, dataset_file, repo_type="dataset")
        parquet_file = pq.ParquetFile(parquet_path)
        row_index = 0

        for batch in parquet_file.iter_batches(batch_size=512):
            for row in batch.to_pylist():
                row_index += 1
                stats[f"{dataset_file}_rows_scanned"] += 1
                if not isinstance(row, dict):
                    continue

                prompt_text = extract_prompt_text(row)
                if not prompt_text:
                    stats["skip_empty_prompt"] += 1
                    continue
                if NEGATIVE_PATTERN.search(prompt_text):
                    stats["skip_negative_pattern"] += 1
                    continue
                if PROMPT_INJECTION_PATTERN.search(prompt_text):
                    stats["skip_prompt_injection"] += 1
                    continue
                if not POSITIVE_PATTERN.search(prompt_text):
                    stats["skip_no_deliverable"] += 1
                    continue
                if not ACTION_PATTERN.search(prompt_text):
                    stats["skip_no_action"] += 1
                    continue
                if not ACADEMIC_CONTEXT_PATTERN.search(prompt_text):
                    stats["skip_no_academic_context"] += 1
                    continue
                if not is_clean_english(prompt_text):
                    stats["skip_prompt_not_clean_english"] += 1
                    continue

                rubric_lines = extract_rubric_lines(row)
                if len(rubric_lines) < 6:
                    stats["skip_too_few_rubrics"] += 1
                    continue
                rubric_text = "\n".join(rubric_lines)
                if META_ASSISTANT_PATTERN.search(rubric_text):
                    stats["skip_meta_assistant_rubric"] += 1
                    continue
                if not is_clean_english(rubric_text):
                    stats["skip_rubric_not_clean_english"] += 1
                    continue

                inspection_text = prompt_text + "\n" + rubric_text
                if QA_OR_INSTRUCTION_PATTERN.search(inspection_text):
                    stats["skip_qa_or_instruction"] += 1
                    continue
                if BUSINESS_OR_PRODUCT_PATTERN.search(inspection_text):
                    stats["skip_business_or_product"] += 1
                    continue
                if COURSE_DESIGN_PATTERN.search(inspection_text):
                    stats["skip_course_design"] += 1
                    continue
                if META_FRAGMENT_PATTERN.search(inspection_text):
                    stats["skip_meta_fragment"] += 1
                    continue
                if LANGUAGE_MISMATCH_PATTERN.search(inspection_text):
                    stats["skip_language_mismatch"] += 1
                    continue

                text = build_sample_text(prompt_text, rubric_lines)
                wc = word_count(text)
                bucket = bucket_for_word_count(wc)
                if bucket is None:
                    stats["skip_out_of_range"] += 1
                    continue

                signature = text_signature(prompt_text)
                if signature in seen_signatures:
                    stats["skip_duplicate_signature"] += 1
                    continue

                candidate = {
                    "bucket": bucket,
                    "word_count": wc,
                    "task_type": classify_task_type(prompt_text),
                    "task_title": derive_task_title(prompt_text),
                    "rubric_count": len(rubric_lines),
                    "student_signal": bool(STUDENT_SIGNAL_PATTERN.search(prompt_text)),
                    "source_dataset": DATASET_REPO,
                    "source_dataset_file": dataset_file,
                    "source_dataset_url": DATASET_URL,
                    "source_dataset_real_origin": SOURCE_REAL_ORIGIN,
                    "source_license": SOURCE_LICENSE,
                    "source_scope": SOURCE_SCOPE,
                    "source_row_index": row_index,
                    "cjk_count": 0,
                    "latin_ratio": round(latin_ratio(text), 4),
                    "translation_like": False,
                    "quality_tier": 0,
                    "text": text,
                }
                seen_signatures.add(signature)
                candidates_by_bucket[bucket].append(candidate)
                stats[f"candidate_{bucket}"] += 1

    for bucket in candidates_by_bucket:
        candidates_by_bucket[bucket].sort(key=candidate_sort_key)

    return candidates_by_bucket, stats


def allocate_actual_counts(candidates_by_bucket: dict[str, list[dict[str, Any]]]) -> dict[str, int]:
    actual = {
        bucket: min(REQUESTED_BUCKET_TARGETS[bucket], len(candidates_by_bucket.get(bucket, [])))
        for bucket in REQUESTED_BUCKET_TARGETS
    }
    deficit = sum(REQUESTED_BUCKET_TARGETS.values()) - sum(actual.values())
    for bucket in ("medium", "long", "short"):
        if deficit <= 0:
            break
        available_extra = len(candidates_by_bucket.get(bucket, [])) - actual[bucket]
        if available_extra <= 0:
            continue
        extra = min(available_extra, deficit)
        actual[bucket] += extra
        deficit -= extra
    return actual


def select_rows(candidates_by_bucket: dict[str, list[dict[str, Any]]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    actual_counts = allocate_actual_counts(candidates_by_bucket)
    selected: list[dict[str, Any]] = []
    used_source_keys: set[tuple[str, int]] = set()
    for bucket in ("short", "medium", "long"):
        pool = candidates_by_bucket.get(bucket, [])
        needed = actual_counts[bucket]
        chosen_for_bucket = []
        for item in pool:
            source_key = (item["source_dataset_file"], item["source_row_index"])
            if source_key in used_source_keys:
                continue
            if is_near_duplicate_title(item, selected):
                continue
            chosen_for_bucket.append(item)
            used_source_keys.add(source_key)
            if len(chosen_for_bucket) == needed:
                break
        actual_counts[bucket] = len(chosen_for_bucket)
        selected.extend(chosen_for_bucket)

    output_rows: list[dict[str, Any]] = []
    ordered = sorted(selected, key=lambda item: (("short", "medium", "long").index(item["bucket"]), candidate_sort_key(item)))
    for index, item in enumerate(ordered, start=1):
        row = dict(item)
        row["sample_index"] = index
        output_rows.append(row)
    return output_rows, actual_counts


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    args = parse_args()
    candidates_by_bucket, stats = load_candidates()

    availability = {
        bucket: len(rows)
        for bucket, rows in candidates_by_bucket.items()
    }

    if args.analyze_only:
        report = {
            "dataset_repo": DATASET_REPO,
            "dataset_files": DATASET_FILES,
            "requested_bucket_targets": REQUESTED_BUCKET_TARGETS,
            "availability": availability,
            "stats": dict(stats),
            "example_titles": {
                bucket: [row["task_title"] for row in rows[:15]]
                for bucket, rows in candidates_by_bucket.items()
            },
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    rows, actual_counts = select_rows(candidates_by_bucket)
    write_jsonl(args.output, rows)

    meta = {
        "dataset_repo": DATASET_REPO,
        "dataset_files": DATASET_FILES,
        "dataset_url": DATASET_URL,
        "dataset_real_origin": SOURCE_REAL_ORIGIN,
        "source_license": SOURCE_LICENSE,
        "selection_mode": "manual_qc_aligned_strict_clean",
        "requested_bucket_targets": REQUESTED_BUCKET_TARGETS,
        "actual_bucket_targets": actual_counts,
        "availability": availability,
        "stats": dict(stats),
        "output_path": str(args.output),
        "total_rows": len(rows),
    }
    args.meta_output.parent.mkdir(parents=True, exist_ok=True)
    args.meta_output.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote {len(rows)} rows to {args.output}")
    print(f"Bucket counts: {Counter(row['bucket'] for row in rows)}")
    print(f"Metadata: {args.meta_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
