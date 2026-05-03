#!/usr/bin/env python3
"""
Extract a stratified random sample of "public service / policy / process guide" style texts
from a public WikiHow-derived dataset (via HuggingFace datasets) and export JSONL for downstream SFT generation.

Constraints:
  - English only (WikiHow is English in practice)
  - Single-source per example (one article per row; never concatenated across rows)
  - Word-count buckets (non-overlapping, by whitespace token count after cleaning):
      short:  250–499
      medium: 500–800
      long:   801–1200
  - Default sampling ratios: 20% / 70% / 10% of N (N default 200)

Notes:
  - The canonical HF dataset id 'wikihow' is currently returning 403 (disabled/gated) in many environments.
    This script defaults to a public alternative: 'gursi26/wikihow-cleaned' (columns: title, text, summary).

Usage:
  py -3 extract_wikihow_public_service_samples.py
  py -3 extract_wikihow_public_service_samples.py --n-total 200 --seed 42
  py -3 extract_wikihow_public_service_samples.py --keywords visa tax permit license
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


OUTPUT_BASENAME = "public_service_200_samples"
DEFAULT_DATASET = "gursi26/wikihow-cleaned"


DEFAULT_KEYWORDS = [
    # eligibility / requirements / process
    "eligibility",
    "eligible",
    "requirement",
    "requirements",
    "apply",
    "application",
    "submit",
    "documents",
    "forms",
    "fee",
    "deadline",
    "appointment",
    "renew",
    "renewal",
    "register",
    "registration",
    "verify",
    # public service & government-like topics
    "government",
    "public service",
    "policy",
    "permit",
    "license",
    "passport",
    "visa",
    "immigration",
    "tax",
    "refund",
    "rebate",
    "benefit",
    "benefits",
    "claim",
    "insurance",
    "social security",
    "citizenship",
    "residency",
    "id card",
]

# Stricter filters to approximate "public service / policy / eligibility / official process" domain.
# The old DEFAULT_KEYWORDS list is intentionally broad; these are used by default instead.
DEFAULT_GOV_KEYWORDS = [
    "government",
    "legal",
    "court",
    "tax",
    "refund",
    "rebate",
    "social security",
    "citizenship",
    "immigration",
    "visa",
    "passport",
    "birth certificate",
    "certificate",
    "id card",
    "driver",
    "license",
    "permit",
    "registration",
    "vote",
    "voter",
    "unemployment",
    "welfare",
    "tenant",
    "landlord",
    "fine",
    "ticket",
    "citation",
    "open container",
    "notary",
    "power of attorney",
    "authorization",
    "appeal",
    "complaint",
]

DEFAULT_PROCESS_KEYWORDS = [
    "apply",
    "application",
    "application form",
    "requirements",
    "requirement",
    "eligible",
    "eligibility",
    "documents",
    "fee",
    "deadline",
    "submit",
    "fill out",
    "steps",
    "process",
    "procedure",
    "register",
    "registration",
    "renew",
    "renewal",
    "notarize",
    "notarized",
]

DEFAULT_EXCLUDE_KEYWORDS = [
    # High-volume lifestyle domains that frequently match generic process words.
    "hair",
    "skin",
    "makeup",
    "halloween",
    "kitten",
    "cat",
    "dog",
    "horse",
    "hockey",
    "skate",
    "diet",
    "weight loss",
    "workout",
    "recipe",
    "cook",
    "bake",
    "artist",
    "presentation",
    "school",
]

# Manual exclusions discovered during full content review.
# These topics are structurally valid how-to articles, but are off-domain for the
# target dataset ("public service / policy / official process explanations") or are
# high-risk because they mix in weapons, entertainment, hobby, tech-admin, vendor-
# selection, private legal tactics, or personal-advice content.
DEFAULT_TITLE_EXCLUDE_PHRASES = [
    "grow legal cannabis",
    "contact your uber driver",
    "tip a cab driver",
    "install an ssl certificate",
    "license content from associated press",
    "license music",
    "paint fine art miniatures",
    "write legal briefs with openoffice",
    "cite legal research",
    "choose who to vote for",
    "encourage others to vote",
    "support the national immigration project",
    "retain self esteem during unemployment",
    "overcome unemployment",
    "deal with an ex who seems fine after your breakup",
    "buy tax free bonds",
    "calculate after tax yield",
    "visa or mastercard with no credit history",
    "safely remove fine scratches",
    "advertise for a tenant",
    "be a good landlord",
    "be a great driver",
    "be a safe teenage driver",
    "make money as an uber driver",
    "personal seat license",
    "gaming license",
    "fishing license",
    "personalized license plate",
    "gun dealers license",
    "gun dealer's license",
    "federal firearms license",
    "class 3 firearms license",
    "concealed carry permit",
    "gun license",
    "ffl license",
    "legal malpractice suit",
    "evidence thrown out in court",
    "assaulted by a retail worker",
    "deal with legal matters on a budget",
    "reduce legal fees",
    "represent yourself in family court",
    "reach a divorce settlement outside of court",
    "dispute a visa charge",
    "visa credit card",
    "certificate of authenticity",
    "government foreclosures",
    "government surplus land",
    "book an airline ticket",
    "legal nurse consultant",
    "check a veterinarian license",
    "read fine print",
    "be a taxi driver",
    "join the american federation of government employees",
    "choose a designated driver",
    "receive a refund on prepaid credit cards",
    "learn tax accounting",
    "lottery ticket",
    "activate a visa credit card",
    "used car dealers license",
    "verizon wireless",
    "refund for late packages",
    "accompany a learner driver",
    "certificate of amendment for a corporation",
    "legal consent to avoid rape charges",
    "avoid a traffic ticket",
    "add curb appeal",
    "court lumina on harvest moon ds",
    "hire a tax resolution company",
    "co-tenant of your property",
    "fight a cell phone ticket",
    "get your boating license",
    "babysitting license",
    "welfare state as a recipient",
    "be a smart teen driver",
    "write a bank authorization letter",
    "avoid capital gains tax",
    "collect a court ordered judgment",
    "evict a tenant",
    "evict a commercial tenant",
    "settle landlord tenant disputes out of court",
    "take legal action against price fixing",
    "get a court order",
    "take legal action against cyber threats",
    "license plate number",
    "complaint to human resources",
    "visa gift card balance",
    "maximize your irs tax deductions",
    "reduce the chance of being audited on your tax returns",
    "avoid going to court when filing for bankruptcy",
    "plan when to apply for social security when you are married",
    "obtain a visa for the world cup",
    "avoid tax problems",
    "convert chicago style to mla citation",
    "reduce legal risks when posting company news online",
    "cash gifting is legal",
    "swing a driver",
    "vote against unionization",
    "hoa management company",
    "victim of violence at a bar",
    "contest a parking ticket",
    "check available license plates",
    "dwa license",
    "make money fast without a social security card",
    "select a property tax attorney",
    "avoid inheritance tax",
    "find affordable irs tax attorneys",
    "spiral knights",
    "be a court reporter",
    "get paid as an uber driver",
    "fight visa chargebacks",
    "tax time financial peace of mind",
]


def normalize_ws(text: str) -> str:
    text = re.sub(r"\s+", " ", (text or "")).strip()
    return text


def normalize_match_text(text: str) -> str:
    text = (text or "").lower()
    # Normalize common unicode punctuation variants so manual phrase filters
    # keep working even when upstream titles use unusual dashes or quotes.
    text = (
        text.replace("\u2010", "-")
        .replace("\u2011", "-")
        .replace("\u2012", "-")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2015", "-")
        .replace("\u2212", "-")
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u00a0", " ")
    )
    return normalize_ws(text)


def word_count(text: str) -> int:
    return len(text.split()) if text else 0


def to_plain_text(example: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """
    Best-effort conversion of a WikiHow dataset row into a single plain-text article body.
    This function is defensive because column names can vary depending on dataset config.
    Returns (plain_text, extracted_metadata).
    """
    meta: dict[str, Any] = {}

    def pick_first(keys: Iterable[str]) -> Any | None:
        for k in keys:
            if k in example and example[k] not in (None, "", [], {}):
                return example[k]
        return None

    title = pick_first(["title", "headline", "name"])
    if isinstance(title, str):
        meta["title"] = normalize_ws(title)

    url = pick_first(["url", "source_url", "link"])
    if isinstance(url, str):
        meta["source_url"] = url.strip()

    category = pick_first(["category", "categories", "section", "domain"])
    if isinstance(category, str):
        meta["category"] = normalize_ws(category)
    elif isinstance(category, list):
        meta["category"] = ", ".join([normalize_ws(str(x)) for x in category if str(x).strip()])

    wikihow_id = pick_first(["id", "wikihow_id", "article_id"])
    if wikihow_id is not None:
        meta["wikihow_id"] = str(wikihow_id)

    # Body candidates (string)
    body = pick_first(["text", "article", "content", "body"])
    if isinstance(body, str) and normalize_ws(body):
        return normalize_ws(body), meta

    # Some variants store structured steps/sections
    steps = pick_first(["steps", "method", "methods", "sections"])
    chunks: list[str] = []

    def add_chunk(x: Any) -> None:
        if not x:
            return
        if isinstance(x, str):
            t = normalize_ws(x)
            if t:
                chunks.append(t)
        elif isinstance(x, list):
            for it in x:
                add_chunk(it)
        elif isinstance(x, dict):
            # common keys seen across how-to datasets
            for k in ["summary", "text", "title", "name", "body", "step", "headline", "description"]:
                if k in x:
                    add_chunk(x[k])

    add_chunk(meta.get("title"))
    add_chunk(steps)

    plain = normalize_ws(" ".join(chunks))
    return plain, meta


def classify_bucket(w: int) -> str | None:
    if 250 <= w <= 499:
        return "short"
    if 500 <= w <= 800:
        return "medium"
    if 801 <= w <= 1200:
        return "long"
    return None


@dataclass
class Row:
    plain_text: str
    words: int
    meta: dict[str, Any]


def load_wikihow_split(
    split: str,
    dataset_name: str,
) -> Any:
    from datasets import load_dataset

    # Public dataset; do not require tokens or remote code execution.
    return load_dataset(dataset_name, split=split)


def _kw_to_regex(kw: str) -> re.Pattern[str] | None:
    kw = (kw or "").strip()
    if not kw:
        return None
    # Normalize internal whitespace in phrases.
    parts = re.split(r"\s+", kw)
    escaped = r"\s+".join(re.escape(p) for p in parts if p)
    if not escaped:
        return None
    # Use word boundaries for alphabetic/number keywords to avoid substring noise:
    # e.g., "law" should not match "allow".
    return re.compile(rf"\b{escaped}\b", re.IGNORECASE)


def keyword_match(text: str, keywords: list[str]) -> bool:
    t = text or ""
    for kw in keywords:
        rx = _kw_to_regex(kw)
        if rx and rx.search(t):
            return True
    return False


def keyword_match_all(text: str, keywords: list[str]) -> bool:
    t = text or ""
    for kw in keywords:
        rx = _kw_to_regex(kw)
        if not rx or not rx.search(t):
            return False
    return True


def is_manually_excluded(title: str, text: str) -> bool:
    title_l = normalize_match_text(title)
    text_l = normalize_match_text(text)

    if any(phrase in title_l for phrase in DEFAULT_TITLE_EXCLUDE_PHRASES):
        return True

    # Specific bad variants found during review.
    if "how to get a federal tax id usa" in title_l and ("form ss-5" in text_l or "social security number" in text_l):
        return True
    if "how to avoid violating your b1 business visa" in title_l and ("h-1b" in text_l or "i-129" in text_l):
        return True
    if "how to absentee vote" in title_l and (
        "elections canada" in text_l or "overseas voter" in text_l or "australian embassy" in text_l
    ):
        return True
    if "how to vote online" in title_l:
        return True

    return False


def iter_candidate_rows(
    ds: Any,
    gov_keywords: list[str],
    process_keywords: list[str],
    exclude_keywords: list[str],
) -> list[Row]:
    rows: list[Row] = []
    for ex in ds:
        plain, meta = to_plain_text(ex)
        if not plain:
            continue
        wc = word_count(plain)
        b = classify_bucket(wc)
        if not b:
            continue
        title = str(meta.get("title", "")).strip()
        title_hay = title
        full_hay = f"{title}\n{plain}"
        if is_manually_excluded(title, plain):
            continue
        # Exclude obvious out-of-domain articles early.
        if exclude_keywords and keyword_match(full_hay, exclude_keywords):
            continue
        # Require BOTH:
        # - at least one "gov/policy/public-service" signal in the TITLE (higher precision than body text)
        # - at least one "process/requirements" signal in title or body
        if gov_keywords and not keyword_match(title_hay, gov_keywords):
            continue
        if process_keywords and not keyword_match(full_hay, process_keywords):
            continue
        rows.append(Row(plain_text=plain, words=wc, meta=meta))
    return rows


def stratified_sample(
    rows: list[Row],
    n_short: int,
    n_medium: int,
    n_long: int,
    seed: int,
) -> tuple[list[Row], dict[str, Any]]:
    buckets: dict[str, list[Row]] = {"short": [], "medium": [], "long": []}
    for r in rows:
        b = classify_bucket(r.words)
        if b:
            buckets[b].append(r)

    report: dict[str, Any] = {
        "available": {k: len(v) for k, v in buckets.items()},
        "requested": {"short": n_short, "medium": n_medium, "long": n_long},
    }

    rng = random.Random(seed)

    def take(bucket: str, n: int) -> list[Row]:
        pool = buckets[bucket]
        if len(pool) < n:
            raise ValueError(
                f"Not enough items in bucket '{bucket}': need {n}, have {len(pool)}. "
                "Try adjusting keywords, using a different wikihow config, or relaxing quotas."
            )
        return rng.sample(pool, n)

    chosen = take("short", n_short) + take("medium", n_medium) + take("long", n_long)
    rng.shuffle(chosen)
    return chosen, report


def row_to_record(idx: int, r: Row) -> dict[str, Any]:
    return {
        "sample_index": idx,
        "bucket": classify_bucket(r.words),
        "word_count": r.words,
        "source_dataset": "WikiHow (HuggingFace datasets)",
        "source_field": "article (single row)",
        "wikihow_id": r.meta.get("wikihow_id", ""),
        "title": r.meta.get("title", ""),
        "category": r.meta.get("category", ""),
        "source_url": r.meta.get("source_url", ""),
        "text": r.plain_text,
    }


def main() -> int:
    base_dir = Path(__file__).resolve().parent
    default_out = base_dir / f"{OUTPUT_BASENAME}.jsonl"

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, default=default_out, help="Output JSONL path")
    p.add_argument("--seed", type=int, default=42, help="RNG seed for reproducibility")
    p.add_argument("--n-total", type=int, default=200, help="Total samples (default 200)")
    p.add_argument(
        "--dataset",
        default=DEFAULT_DATASET,
        help="HuggingFace dataset id to load (default: gursi26/wikihow-cleaned).",
    )
    p.add_argument("--split", default="train", help="Dataset split to sample from (default train)")
    p.add_argument(
        "--gov-keywords",
        nargs="*",
        default=DEFAULT_GOV_KEYWORDS,
        help="At least one of these must match (public service / policy domain signals).",
    )
    p.add_argument(
        "--process-keywords",
        nargs="*",
        default=DEFAULT_PROCESS_KEYWORDS,
        help="At least one of these must match (process/eligibility/requirements signals).",
    )
    p.add_argument(
        "--exclude-keywords",
        nargs="*",
        default=DEFAULT_EXCLUDE_KEYWORDS,
        help="If any of these match, the row is excluded (common lifestyle noise terms).",
    )
    p.add_argument(
        "--max-scan",
        type=int,
        default=0,
        help="If >0, only scan first N rows for faster experimentation.",
    )
    p.add_argument(
        "--analyze-only",
        action="store_true",
        help="Only compute availability by bucket and exit (no sampling/output).",
    )
    args = p.parse_args()

    n_total = args.n_total
    if n_total <= 0 or n_total % 10 != 0:
        print("n-total should be positive; for 20/70/10 ratios use a multiple of 10.", file=sys.stderr)
        return 2

    n_short = n_total * 20 // 100
    n_medium = n_total * 70 // 100
    n_long = n_total * 10 // 100
    if n_short + n_medium + n_long != n_total:
        n_medium += n_total - (n_short + n_medium + n_long)

    try:
        ds = load_wikihow_split(
            split=args.split,
            dataset_name=args.dataset,
        )
    except Exception as e:  # noqa: BLE001
        print(
            "Failed to load dataset from HuggingFace.\n"
            "Try checking your network, or switching datasets with --dataset.\n"
            f"Error: {e}",
            file=sys.stderr,
        )
        return 1

    if args.max_scan and args.max_scan > 0:
        ds = ds.select(range(min(args.max_scan, len(ds))))

    print(f"Loaded dataset split: {args.split} (rows={len(ds)})")
    print(
        "Filtering by domain/process keywords and length buckets ...\n"
        f"  gov_keywords={len(args.gov_keywords)}  process_keywords={len(args.process_keywords)}  exclude_keywords={len(args.exclude_keywords)}"
    )
    rows = iter_candidate_rows(ds, args.gov_keywords, args.process_keywords, args.exclude_keywords)
    print(f"Candidates in target length ranges after keyword filter: {len(rows)}")

    availability = {"short": 0, "medium": 0, "long": 0}
    for r in rows:
        b = classify_bucket(r.words)
        if b:
            availability[b] += 1
    print(f"Availability by bucket: {availability}")

    if args.analyze_only:
        return 0

    try:
        chosen, report = stratified_sample(rows, n_short, n_medium, n_long, args.seed)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        print(
            f"Availability report: {{'available': {availability}, 'requested': {{'short': {n_short}, 'medium': {n_medium}, 'long': {n_long}}}}}",
            file=sys.stderr,
        )
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as f:
        for i, row in enumerate(chosen, start=1):
            f.write(json.dumps(row_to_record(i, row), ensure_ascii=False) + "\n")

    meta_path = args.output.with_suffix(".meta.json")
    meta = {
        "output_file": str(args.output.resolve()),
        "seed": args.seed,
        "dataset": {"name": args.dataset, "split": args.split},
        "filters": {
            "gov_keywords": args.gov_keywords,
            "process_keywords": args.process_keywords,
            "exclude_keywords": args.exclude_keywords,
        },
        "totals": {"short": n_short, "medium": n_medium, "long": n_long, "total": n_total},
        "bucket_word_ranges": {
            "short": "250–499 inclusive",
            "medium": "500–800 inclusive",
            "long": "801–1200 inclusive",
        },
        "sampling_report": report,
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote {len(chosen)} records to {args.output}")
    print(f"Wrote run metadata to {meta_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
