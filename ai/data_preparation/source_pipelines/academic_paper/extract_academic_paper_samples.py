#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from datasets import load_dataset


DATASET_NAME = "common-pile/peS2o_filtered"
DATASET_SPLIT = "train"
DATASET_REAL_ORIGIN = "common-pile/peS2o_filtered -> peS2o -> S2ORC"
LICENSE_NOTE = (
    "Only keep documents whose oa_license is one of: CCBY, CCBYSA, CC0, pd, public-domain."
)
ALLOWED_LICENSES = {"CCBY", "CCBYSA", "CC0", "pd", "public-domain"}

DOMAIN_LABELS = {
    "cse": "Computer Science, AI & Engineering",
    "bfe": "Business, Finance & Economics",
    "ssh": "Social Sciences & Humanities",
    "lsph": "Life Sciences & Public Health",
}

DOMAIN_FIELDS = {
    "cse": {"computer science", "engineering", "materials science"},
    "bfe": {"business", "economics"},
    "ssh": {
        "psychology",
        "political science",
        "sociology",
        "geography",
        "history",
        "philosophy",
        "art",
        "linguistics",
        "anthropology",
        "education",
    },
    "lsph": {
        "medicine",
        "biology",
        "environmental science",
        "public health",
        "epidemiology",
        "health sciences",
        "nursing",
    },
}

DOMAIN_BUCKET_TARGETS = {
    "cse": {"short": 25, "medium": 88, "long": 12},
    "bfe": {"short": 25, "medium": 87, "long": 13},
    "ssh": {"short": 25, "medium": 87, "long": 13},
    "lsph": {"short": 25, "medium": 88, "long": 12},
}

BUCKET_SPECS = {
    "short": {"min_words": 250, "max_words": 499, "target_words": 360},
    "medium": {"min_words": 500, "max_words": 800, "target_words": 620},
    "long": {"min_words": 801, "max_words": 1200, "target_words": 960},
}

STOP_SECTION_HEADERS = {
    "references",
    "reference",
    "acknowledgments",
    "acknowledgements",
    "bibliography",
    "author contributions",
    "funding",
    "appendix",
    "appendices",
    "supplementary material",
    "supplementary materials",
}

REJECT_TITLE_PATTERNS = [
    re.compile(r"\bcomment\b", re.IGNORECASE),
    re.compile(r"\breply\b", re.IGNORECASE),
    re.compile(r"\bresponse\b", re.IGNORECASE),
    re.compile(r"\bletter to the editor\b", re.IGNORECASE),
    re.compile(r"\bshort communication\b", re.IGNORECASE),
    re.compile(r"\beditorial\b", re.IGNORECASE),
    re.compile(r"\bcorrigendum\b", re.IGNORECASE),
    re.compile(r"\berratum\b", re.IGNORECASE),
    re.compile(r"\bretraction\b", re.IGNORECASE),
    re.compile(r"\bexpression of concern\b", re.IGNORECASE),
]

REJECT_OPENING_PREFIXES = (
    "supplementary ",
    "supporting information",
    "supporting file",
    "additional file",
    "appendix",
)

REJECT_OPENING_PATTERNS = [
    re.compile(r"^sir\b", re.IGNORECASE),
    re.compile(r"^dear editor\b", re.IGNORECASE),
]

REJECT_EXCERPT_PATTERNS = [
    re.compile(r"(?im)^references\b"),
    re.compile(r"(?im)^acknowledg"),
]

SUSPICIOUS_TOKEN_PATTERN = re.compile(r"\b([A-Za-z]\d{5,})\b")


@dataclass
class ExcerptCandidate:
    bucket: str
    text: str
    word_count: int


def parse_args() -> argparse.Namespace:
    base_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Extract 500 academic-paper excerpts.")
    parser.add_argument("--dataset-name", default=DATASET_NAME)
    parser.add_argument("--dataset-split", default=DATASET_SPLIT)
    parser.add_argument(
        "--output",
        type=Path,
        default=base_dir / "academic_paper_500_samples.jsonl",
    )
    parser.add_argument(
        "--meta-output",
        type=Path,
        default=base_dir / "academic_paper_500_samples.meta.json",
    )
    parser.add_argument("--max-scan", type=int, default=250000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--analyze-only", action="store_true")
    parser.add_argument("--progress-every", type=int, default=5000)
    return parser.parse_args()


def normalize_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_inline_text(text: str) -> str:
    text = re.sub(r"\[[0-9,\-; ]+\]", " ", text)
    text = re.sub(r"\((?:Fig|Table|Eq|Ref)s?\.?[^\)]*\)", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    return text.strip()


def word_count(text: str) -> int:
    return len(text.split()) if text else 0


def alpha_ratio(text: str) -> float:
    chars = [c for c in text if not c.isspace()]
    if not chars:
        return 0.0
    return sum(1 for c in chars if c.isalpha()) / len(chars)


def normalize_field_names(values: Iterable[str] | None) -> set[str]:
    return {str(v).strip().lower() for v in (values or []) if str(v).strip()}


def normalize_for_dedup(text: str) -> str:
    lowered = text.lower()
    lowered = re.sub(r"[^a-z0-9 ]+", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def looks_like_heading(paragraph: str) -> bool:
    compact = paragraph.strip()
    if not compact:
        return True
    words = compact.split()
    if len(words) > 12:
        return False
    if re.fullmatch(r"(?:[IVXLCM]+\.?|[0-9]+\.?)", compact):
        return True
    return bool(re.fullmatch(r"(?:[IVXLCM]+\.?\s+)?[A-Z0-9][A-Z0-9 \-:/,&()]+", compact))


def normalize_header(paragraph: str) -> str:
    compact = re.sub(r"^(?:[IVXLCM]+\.?|[0-9]+\.?)\s*", "", paragraph.strip(), flags=re.IGNORECASE)
    compact = compact.lower()
    compact = re.sub(r"[^a-z ]+", " ", compact)
    return re.sub(r"\s+", " ", compact).strip()


def is_stop_header(paragraph: str) -> bool:
    return normalize_header(paragraph) in STOP_SECTION_HEADERS


def is_noise_paragraph(paragraph: str) -> bool:
    compact = paragraph.strip()
    if not compact or len(compact) < 40:
        return True
    if compact.lower().startswith("http://") or compact.lower().startswith("https://"):
        return True
    if compact.count("@") >= 2:
        return True
    if alpha_ratio(compact) < 0.65:
        return True
    if sum(ch.isdigit() for ch in compact) > max(20, len(compact) * 0.2):
        return True
    return False


def is_rejected_title(title: str) -> bool:
    compact = title.strip()
    if not compact:
        return True
    return any(pattern.search(compact) for pattern in REJECT_TITLE_PATTERNS)


def is_rejected_opening(paragraph: str) -> bool:
    compact = paragraph.strip()
    normalized = normalize_header(compact)
    if any(normalized.startswith(prefix) for prefix in REJECT_OPENING_PREFIXES):
        return True
    return any(pattern.search(compact) for pattern in REJECT_OPENING_PATTERNS)


def excerpt_has_quality_issue(text: str) -> bool:
    if text.lower().count("http") >= 2:
        return True
    if any(pattern.search(text) for pattern in REJECT_EXCERPT_PATTERNS):
        return True
    suspicious_counts = Counter(SUSPICIOUS_TOKEN_PATTERN.findall(text))
    if any(count >= 3 for count in suspicious_counts.values()):
        return True
    return False


def split_sentences(paragraph: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])", paragraph.strip())
    cleaned = [clean_inline_text(p) for p in parts]
    return [p for p in cleaned if word_count(p) >= 6]


def prepare_document(raw_text: str) -> tuple[str, list[str], str | None]:
    text = normalize_whitespace(raw_text)
    paragraphs = [clean_inline_text(p) for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paragraphs:
        return "", [], "no_paragraphs"

    title = ""
    start_idx = 0
    if 2 <= word_count(paragraphs[0]) <= 24 and alpha_ratio(paragraphs[0]) >= 0.75:
        title = paragraphs[0].strip()
        start_idx = 1
    if is_rejected_title(title):
        return title, [], "rejected_title"

    body: list[str] = []
    body_words = 0
    last_key = ""
    for paragraph in paragraphs[start_idx:]:
        if is_stop_header(paragraph):
            break
        if looks_like_heading(paragraph) or is_noise_paragraph(paragraph):
            continue
        if not body and is_rejected_opening(paragraph):
            return title, [], "rejected_opening"
        dedup_key = normalize_for_dedup(paragraph)
        if dedup_key and dedup_key == last_key:
            continue
        body.append(paragraph)
        last_key = dedup_key
        body_words += word_count(paragraph)
        if body_words >= 2200:
            break
    if not body:
        return title, [], "empty_body"
    return title, body, None


def join_excerpt(title: str, pieces: list[str]) -> str:
    if title:
        return f"{title}\n\n" + "\n\n".join(pieces)
    return "\n\n".join(pieces)


def build_bucket_candidate(title: str, body: list[str], bucket: str, start_offset: int) -> ExcerptCandidate | None:
    spec = BUCKET_SPECS[bucket]
    title_words = word_count(title) if title else 0
    selected: list[str] = []
    best_text = ""
    best_wc = 0
    best_score: tuple[int, int] | None = None

    for paragraph in body[start_offset:]:
        proposed_wc = title_words + sum(word_count(x) for x in selected + [paragraph])
        if proposed_wc <= spec["max_words"]:
            selected.append(paragraph)
            if proposed_wc >= spec["min_words"]:
                score = (abs(proposed_wc - spec["target_words"]), len(selected))
                if best_score is None or score < best_score:
                    best_score = score
                    best_text = join_excerpt(title, selected)
                    best_wc = proposed_wc
            continue

        temp = list(selected)
        for sentence in split_sentences(paragraph):
            sentence_wc = title_words + sum(word_count(x) for x in temp) + word_count(sentence)
            if sentence_wc > spec["max_words"]:
                break
            temp.append(sentence)
            if sentence_wc >= spec["min_words"]:
                score = (abs(sentence_wc - spec["target_words"]), len(temp))
                if best_score is None or score < best_score:
                    best_score = score
                    best_text = join_excerpt(title, temp)
                    best_wc = sentence_wc
        break

    if not best_text:
        return None
    best_text = normalize_whitespace(best_text)
    if alpha_ratio(best_text) < 0.72:
        return None
    if excerpt_has_quality_issue(best_text):
        return None
    return ExcerptCandidate(bucket=bucket, text=best_text, word_count=best_wc)


def build_candidates(title: str, body: list[str]) -> dict[str, ExcerptCandidate]:
    results: dict[str, ExcerptCandidate] = {}
    for bucket in ("short", "medium", "long"):
        best: ExcerptCandidate | None = None
        for start_offset in (0, 1, 2):
            if start_offset >= len(body):
                continue
            current = build_bucket_candidate(title, body, bucket, start_offset)
            if current is None:
                continue
            if best is None:
                best = current
                continue
            if abs(current.word_count - BUCKET_SPECS[bucket]["target_words"]) < abs(
                best.word_count - BUCKET_SPECS[bucket]["target_words"]
            ):
                best = current
        if best is not None:
            results[bucket] = best
    return results


def classify_domain(metadata: dict[str, Any]) -> tuple[str | None, list[str]]:
    fields = normalize_field_names(metadata.get("extfieldsofstudy")) | normalize_field_names(
        metadata.get("s2fieldsofstudy")
    )
    ordered = sorted(fields)
    scores = {domain: len(fields & DOMAIN_FIELDS[domain]) for domain in DOMAIN_FIELDS}
    best_score = max(scores.values(), default=0)
    if best_score <= 0:
        return None, ordered
    tied = [domain for domain, score in scores.items() if score == best_score]
    for domain in ("bfe", "ssh", "cse", "lsph"):
        if domain in tied:
            return domain, ordered
    return None, ordered


def choose_bucket(
    candidates: dict[str, ExcerptCandidate],
    remaining: dict[str, int],
    targets: dict[str, int],
    rng: random.Random,
) -> str | None:
    options = [b for b in ("short", "medium", "long") if remaining[b] > 0 and b in candidates]
    if not options:
        return None

    def score(bucket: str) -> tuple[float, int, float]:
        fraction_left = remaining[bucket] / targets[bucket]
        priority = {"long": 3, "short": 2, "medium": 1}[bucket]
        return (fraction_left, priority, rng.random())

    return max(options, key=score)


def build_record(
    sample_index: int,
    domain: str,
    chosen: ExcerptCandidate,
    row: dict[str, Any],
    title: str,
    all_fields: list[str],
) -> dict[str, Any]:
    metadata = row.get("metadata") or {}
    return {
        "sample_index": sample_index,
        "domain_key": domain,
        "domain_label": DOMAIN_LABELS[domain],
        "bucket": chosen.bucket,
        "word_count": chosen.word_count,
        "paper_id": row.get("id"),
        "title": title,
        "year": metadata.get("year"),
        "fields_of_study": all_fields,
        "source_dataset": DATASET_NAME,
        "source_dataset_real_origin": DATASET_REAL_ORIGIN,
        "source": row.get("source"),
        "source_url": metadata.get("oa_url"),
        "source_license": metadata.get("oa_license"),
        "source_license_status": metadata.get("oa_status"),
        "source_scope": "single_article_excerpt",
        "excerpt_strategy": "title_plus_early_contiguous_paragraphs_from_one_article",
        "text": chosen.text,
    }


def quotas_complete(remaining_by_domain: dict[str, dict[str, int]]) -> bool:
    return all(value == 0 for quotas in remaining_by_domain.values() for value in quotas.values())


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    args = parse_args()
    rng = random.Random(args.seed)
    targets = {domain: quotas.copy() for domain, quotas in DOMAIN_BUCKET_TARGETS.items()}
    remaining = {domain: quotas.copy() for domain, quotas in DOMAIN_BUCKET_TARGETS.items()}

    dataset = load_dataset(args.dataset_name, split=args.dataset_split, streaming=True)
    selected_rows: list[dict[str, Any]] = []
    seen_paper_ids: set[str] = set()
    skipped_reasons: Counter[str] = Counter()
    domain_seen_counts: Counter[str] = Counter()
    domain_candidate_support: dict[str, Counter[str]] = defaultdict(Counter)
    scan_count = 0

    for row in dataset:
        scan_count += 1
        if scan_count % args.progress_every == 0:
            print(f"[scan={scan_count}] selected={len(selected_rows)}")

        metadata = row.get("metadata") or {}
        license_name = str(metadata.get("oa_license") or "")
        if license_name not in ALLOWED_LICENSES:
            skipped_reasons["license"] += 1
            if scan_count >= args.max_scan:
                break
            continue

        paper_id = str(row.get("id") or "").strip()
        if not paper_id:
            skipped_reasons["missing_id"] += 1
            if scan_count >= args.max_scan:
                break
            continue
        if paper_id in seen_paper_ids:
            skipped_reasons["duplicate_paper"] += 1
            if scan_count >= args.max_scan:
                break
            continue

        domain, all_fields = classify_domain(metadata)
        if domain is None:
            skipped_reasons["domain_unmatched"] += 1
            if scan_count >= args.max_scan:
                break
            continue

        title, body, prep_reason = prepare_document(str(row.get("text") or ""))
        if not body:
            skipped_reasons[prep_reason or "empty_after_cleaning"] += 1
            if scan_count >= args.max_scan:
                break
            continue

        candidates = build_candidates(title, body)
        if not candidates:
            skipped_reasons["no_bucket_candidate"] += 1
            if scan_count >= args.max_scan:
                break
            continue

        domain_seen_counts[domain] += 1
        for bucket in candidates:
            domain_candidate_support[domain][bucket] += 1

        if args.analyze_only:
            if scan_count >= args.max_scan:
                break
            continue

        bucket = choose_bucket(candidates, remaining[domain], targets[domain], rng)
        if bucket is None:
            skipped_reasons["quota_full_for_domain_or_bucket"] += 1
            if scan_count >= args.max_scan:
                break
            continue

        chosen = candidates[bucket]
        selected_rows.append(
            build_record(
                sample_index=len(selected_rows) + 1,
                domain=domain,
                chosen=chosen,
                row=row,
                title=title,
                all_fields=all_fields,
            )
        )
        seen_paper_ids.add(paper_id)
        remaining[domain][bucket] -= 1
        print(
            f"[pick {len(selected_rows):03d}/500] {DOMAIN_LABELS[domain]} | {bucket} | "
            f"{chosen.word_count} words | {title[:80]}"
        )

        if quotas_complete(remaining) or scan_count >= args.max_scan:
            break

    if args.analyze_only:
        report = {
            "dataset_name": args.dataset_name,
            "dataset_split": args.dataset_split,
            "dataset_real_origin": DATASET_REAL_ORIGIN,
            "license_note": LICENSE_NOTE,
            "allowed_licenses": sorted(ALLOWED_LICENSES),
            "scan_count": scan_count,
            "domain_seen_counts": dict(domain_seen_counts),
            "domain_candidate_support": {k: dict(v) for k, v in domain_candidate_support.items()},
            "skipped_reasons": dict(skipped_reasons),
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    if not quotas_complete(remaining):
        print(
            "Failed to satisfy all quotas. Increase --max-scan and rerun.\n"
            f"Remaining: {json.dumps(remaining, ensure_ascii=False)}",
            file=sys.stderr,
        )
        return 1

    write_jsonl(args.output, selected_rows)
    meta = {
        "dataset_name": args.dataset_name,
        "dataset_split": args.dataset_split,
        "dataset_real_origin": DATASET_REAL_ORIGIN,
        "license_note": LICENSE_NOTE,
        "allowed_licenses": sorted(ALLOWED_LICENSES),
        "output_file": str(args.output.resolve()),
        "scan_count": scan_count,
        "seed": args.seed,
        "targets_by_domain": DOMAIN_BUCKET_TARGETS,
        "selected_domain_counts": dict(Counter(row["domain_key"] for row in selected_rows)),
        "selected_bucket_counts": dict(Counter(row["bucket"] for row in selected_rows)),
        "remaining_after_run": remaining,
        "domain_candidate_support": {k: dict(v) for k, v in domain_candidate_support.items()},
        "skipped_reasons": dict(skipped_reasons),
    }
    args.meta_output.parent.mkdir(parents=True, exist_ok=True)
    args.meta_output.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote {len(selected_rows)} samples to {args.output}")
    print(f"Wrote metadata to {args.meta_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
