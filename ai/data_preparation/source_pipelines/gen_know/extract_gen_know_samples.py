#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import time
from collections import Counter
from pathlib import Path
from typing import Any, Optional

from datasets import load_dataset
from tqdm import tqdm


BUCKET_RANGES = {
    "short": (250, 499),
    "medium": (500, 800),
    "long": (801, 1200),
}

TARGET_WORDS = {
    "short": 360,
    "medium": 650,
    "long": 950,
}

EXACT_TITLE_REJECTS = {
    "baldric",
    "camelbeach waterpark",
    "kevin a. ring",
    "ken linseman",
    "mark dutiaume",
    "paul kollsman",
    "solstice cyclists",
    "sports periodization",
    "susanna rahkamo",
}

TITLE_REJECT_RE = re.compile(
    r"^(?:"
    r"List of|Lists of|Index of|Timeline of|Outline of|Glossary of|"
    r"Neighbourhoods of|Neighborhoods of|"
    r".+ in fiction|"
    r"Meanings of minor planet names:|National Register of Historic Places listings|"
    r"Portal:|Category:|Template:|File:|Draft:|Help:|Wikipedia:|"
    r"Module:|Book:|User:|Talk:"
    r")",
    re.IGNORECASE,
)
DISAMBIG_RE = re.compile(r"\bmay refer to\b|\bcan refer to\b", re.IGNORECASE)
MONTH_DAY_TITLE_RE = re.compile(
    r"^(January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}$"
)
TIMELINE_RE = re.compile(r"\bPre-1600\b|\b1601[-\u2013\u2014]1900\b|\b1901[-\u2013\u2014]present\b")
YEAR_SEASON_TITLE_RE = re.compile(r"^\d{4}[-\u2013\u2014]\d{2,4}\s+in\b", re.IGNORECASE)
TITLE_CONTEXT_NEGATIVE_RE = re.compile(
    r"\((?:board game|short story|roller coaster|Dungeons & Dragons|nightclub)\)|"
    r"\bon television\b|\bSuper Bowl\b|\bDivision Series\b",
    re.IGNORECASE,
)

STOP_SECTION_TITLES = [
    "See also",
    "References",
    "External links",
    "Notes",
    "Further reading",
    "Sources",
    "Bibliography",
    "Filmography",
    "Discography",
    "Works",
    "Selected works",
    "Career statistics",
    "Current roster",
    "Roster",
    "Honours",
    "Honors",
    "Events",
    "Births",
    "Deaths",
    "Classification",
    "Phylogeny",
    "Taxonomy",
    "Systematics",
    "Typical forum structures",
    "Equivalent spaces in other cultures",
    "Extreme points",
    "Abbots",
    "Burials",
    "Selected bibliography",
    "Publications",
    "Selected publications",
    "Track listing",
    "Cast",
    "Personnel",
    "In popular culture",
    "Popular culture",
    "In fiction",
]
STOP_SECTION_RE = re.compile(
    r"\n(?:" + "|".join(re.escape(title) for title in STOP_SECTION_TITLES) + r")\s*\n",
    re.IGNORECASE,
)
BAD_SECTION_RE = re.compile(
    r"\b(Current roster|Honours|Honors|Career statistics|Selected works|Discography|Filmography|"
    r"Classification|Phylogeny|Taxonomy|Systematics|Extreme points|Abbots|Burials|"
    r"Typical forum structures|Equivalent spaces in other cultures|Track listing|Cast|Personnel)\b",
    re.IGNORECASE,
)
TOPIC_NEGATIVE_RE = re.compile(
    r"\b("
    r"television series|television program|animated series|sitcom|soap opera|"
    r"film|movie|novel|comics?|comic strip|fictional character|video game|"
    r"song|album|band|rapper|drummer|guitarist|singer|actor|actress|musical|"
    r"football club|soccer club|sports club|baseball team|sports team|rugby union club|"
    r"basketball player|baseball player|footballer|athlete|olympian|ice dancer|"
    r"skier|coach|curler|sportscaster|ice hockey|hockey player|wrestler|discus thrower|"
    r"shot putter|snowboarder|ski racer|roller derby|shoot 'em up|casino|karaoke bar|"
    r"city-building game|condo-hotel|footrace|"
    r"country fair|cricketer|triathlete|racehorse|ski area|radio station|television station|"
    r"high school|secondary school|supporters group|betting|wagering|bookmaker|"
    r"board wargame|role-playing game|fantasy novels?|science fiction author|variety show|"
    r"clothing-optional|bodypainting|naked cyclists"
    r")\b",
    re.IGNORECASE,
)
LEAD_NEGATIVE_RE = re.compile(
    r"\b("
    r"murderer|serial killer|cult leader|television show|television channel|news channel|"
    r"episode|professional football player|football coach|linebacker|defensive back|"
    r"defensive coordinator|major league baseball|canadian football league|olympic medalist|"
    r"skeleton bobsleigh athlete|mogul skier|ice dancer|soccer representative|variety show|"
    r"daytime show|noon-time show|intercollegiate athletics|varsity sports|athletic teams|"
    r"agricultural society|fairgrounds|gaming devices|playstation|ringname|"
    r"real-time strategy elements|ski resort|las vegas strip|contract killer|super bowl|"
    r"division series|playoffs|express bus line|shuttle bus service|traveling amusement|"
    r"traveling carnival|carnival company|satellite television|magazine|"
    r"(?:first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth) book|"
    r"fantasy novels?"
    r")\b",
    re.IGNORECASE,
)
POSITIVE_LEAD_RE = re.compile(
    r"\b("
    r"country|state|province|district|city|town|village|municipality|archipelago|island|bay|river|sea|"
    r"mountain|plateau|park|airport|railway station|route|highway|castle|palace|temple|abbey|church|"
    r"cathedral|mosque|lighthouse|bridge|dam|fort|historic site|historic house|museum|"
    r"religion|festival|language|alphabet|script|sacred text|biblical figure|philosopher|theologian|"
    r"bishop|archbishop|rabbi|monk|saint|"
    r"theory|method|algorithm|law|court case|legal case|election|politics|government|relations|economy|"
    r"bank|institute|university|college|school|faculty|society|association|"
    r"public health|medicine|medical|disease|therapy|syndrome|gene|protein|chemical|compound|element|"
    r"memory|software|computer|mathematics|physics|chemistry|biology|linguistics|polyhedron|"
    r"mathematician|physicist|chemist|biologist|physician|surgeon|historian|linguist|scientist|engineer|"
    r"educator|politician|statesman|explorer|general|admiral|military officer|"
    r"battle|war|revolution|dynasty|empire|treaty|accident|hijacking|tribe|ethnic group|"
    r"howitzer|missile|aircraft|pump|earthmover"
    r")\b",
    re.IGNORECASE,
)
SUSPICIOUS_ENCODING_RE = re.compile(r"\uFFFD")
CJK_CHAR_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
LISTY_KEYWORD_RE = re.compile(
    r"\b(Classification|Phylogeny|Taxonomy|Systematics|Subfamily|Genus|Species|"
    r"Abbots?|Burials?|Extreme points|Typical forum structures|Equivalent spaces in other cultures|"
    r"Track listing|Personnel|Cast)\b",
    re.IGNORECASE,
)

STOP_HEADINGS = {title.lower() for title in STOP_SECTION_TITLES}
STOP_HEADINGS.update(
    {
        "gallery",
        "awards",
        "publications",
        "selected publications",
        "selected bibliography",
    }
)


def normalize_ws(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text).strip()


def normalize_block(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def word_count(text: str) -> int:
    return len(text.split())


def sentence_count(text: str) -> int:
    return len(re.findall(r"[.!?](?=\s|$)", text))


def sha1_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()


def normalize_title_key(title: str) -> str:
    return normalize_ws(title).casefold()


def trim_to_sentence_boundary(text: str, min_words: int) -> str:
    text = normalize_ws(text)
    if word_count(text) <= min_words:
        return text
    matches = list(re.finditer(r"[.!?](?=\s|$)", text))
    for match in reversed(matches):
        candidate = text[: match.end()].strip()
        if word_count(candidate) >= min_words:
            return candidate
    return text


def shorten_paragraph(paragraph: str, max_words: int, min_words: int) -> str:
    words = paragraph.split()
    if len(words) <= max_words:
        return paragraph
    cut = " ".join(words[:max_words])
    cut = trim_to_sentence_boundary(cut, min_words=min_words)
    return normalize_ws(cut)


def is_heading_like(paragraph: str) -> bool:
    p = normalize_ws(paragraph)
    lower = p.lower()
    if lower in STOP_HEADINGS:
        return True
    if len(p.split()) <= 10 and not re.search(r"[.!?]['\")\]]?$", p):
        if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 ,()'/:&\-]{0,120}", p):
            return True
    return False


def is_list_like(paragraph: str) -> bool:
    raw = paragraph.strip()
    p = normalize_ws(raw)
    if not raw or not p:
        return True

    lines = [normalize_ws(line) for line in raw.splitlines() if normalize_ws(line)]
    if len(lines) >= 4:
        avg_line_words = sum(word_count(line) for line in lines) / len(lines)
        punct_ended = sum(bool(re.search(r"[.!?]['\")\]]?$", line)) for line in lines)
        if avg_line_words <= 8 and punct_ended <= 1:
            return True
        if punct_ended <= 1 and max((word_count(line) for line in lines), default=0) <= 14:
            return True

    if re.match(r"^(?:\*|-|\u2022|\d+\.)\s", p):
        return True
    if p.count(";") >= 5 and word_count(p) < 180:
        return True
    if len(re.findall(r"\b[A-Z][a-z]+,", p)) >= 10 and word_count(p) < 220:
        return True
    if LISTY_KEYWORD_RE.search(p) and sentence_count(p) <= 2 and word_count(p) < 240:
        return True
    if len(re.findall(r"\b(?:Genus|Family|Subfamily|Species)\b", p)) >= 3 and word_count(p) < 240:
        return True
    return False


def split_paragraphs(text: str) -> list[str]:
    raw = normalize_block(text)
    paras = [normalize_ws(p) for p in re.split(r"\n{2,}", raw) if normalize_ws(p)]
    if len(paras) > 1:
        return paras

    sentence_chunks = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", normalize_ws(raw))
    merged: list[str] = []
    cur: list[str] = []
    cur_words = 0
    for sent in sentence_chunks:
        sent = normalize_ws(sent)
        if not sent:
            continue
        cur.append(sent)
        cur_words += word_count(sent)
        if cur_words >= 90:
            merged.append(" ".join(cur))
            cur = []
            cur_words = 0
    if cur:
        merged.append(" ".join(cur))
    return merged or [normalize_ws(raw)]


def truncate_at_stop_section(text: str) -> str:
    raw = normalize_block(text)
    match = STOP_SECTION_RE.search(raw)
    if match:
        raw = raw[: match.start()].strip()
    return raw


def has_suspicious_encoding(text: str) -> bool:
    return bool(SUSPICIOUS_ENCODING_RE.search(text) or CJK_CHAR_RE.search(text))


def has_bad_tail(text: str) -> bool:
    tail = text[-1500:]
    tail_paragraphs = split_paragraphs(tail)
    last_para = tail_paragraphs[-1] if tail_paragraphs else tail
    if BAD_SECTION_RE.search(tail):
        return True
    if LISTY_KEYWORD_RE.search(last_para):
        return True
    if is_list_like(last_para):
        return True
    if not re.search(r"[.!?]['\")\]]?\s*$", text.strip()):
        return True
    return False


def reject_article(title: str, text: str) -> bool:
    clean_title = normalize_ws(title)
    if not clean_title:
        return True
    if normalize_title_key(clean_title) in EXACT_TITLE_REJECTS:
        return True
    if TITLE_REJECT_RE.search(clean_title):
        return True
    if MONTH_DAY_TITLE_RE.fullmatch(clean_title):
        return True
    if YEAR_SEASON_TITLE_RE.search(clean_title):
        return True
    if TITLE_CONTEXT_NEGATIVE_RE.search(clean_title):
        return True
    if clean_title.lower().endswith("(surname)"):
        return True
    if "(disambiguation)" in clean_title.lower():
        return True
    if re.fullmatch(r"\d{3,4}", clean_title):
        return True

    lead = normalize_ws(text[:2500]).lower()
    if DISAMBIG_RE.search(lead):
        return True
    if TIMELINE_RE.search(text[:2500]):
        return True
    if BAD_SECTION_RE.search(text[:4000]):
        return True
    if TOPIC_NEGATIVE_RE.search(clean_title) or TOPIC_NEGATIVE_RE.search(text[:1200]):
        return True
    if LEAD_NEGATIVE_RE.search(clean_title) or LEAD_NEGATIVE_RE.search(text[:1200]):
        return True
    if not POSITIVE_LEAD_RE.search(text[:1600]):
        return True
    if has_suspicious_encoding(clean_title) or has_suspicious_encoding(text[:4000]):
        return True
    if word_count(normalize_ws(text)) < 220:
        return True
    return False


def extract_excerpt(title: str, text: str, bucket: str) -> Optional[str]:
    min_words, max_words = BUCKET_RANGES[bucket]
    target_words = TARGET_WORDS[bucket]

    clean_title = normalize_ws(title)
    if reject_article(clean_title, text):
        return None

    text = truncate_at_stop_section(text)
    paragraphs = split_paragraphs(text)
    if not paragraphs:
        return None

    parts: list[str] = []
    current_words = word_count(clean_title)
    title_lower = clean_title.lower()

    for paragraph in paragraphs:
        p = normalize_ws(paragraph)
        if not p:
            continue
        if p.lower() == title_lower:
            continue
        if is_heading_like(p):
            if parts:
                break
            continue
        if is_list_like(paragraph):
            continue

        p_words = word_count(p)
        if current_words + p_words > max_words:
            remaining = max_words - current_words
            if remaining >= 60:
                shortened = shorten_paragraph(
                    p,
                    max_words=remaining,
                    min_words=max(40, remaining // 2),
                )
                if shortened:
                    parts.append(shortened)
                    current_words += word_count(shortened)
            break

        parts.append(p)
        current_words += p_words
        if current_words >= target_words:
            break

    if not parts:
        return None

    body = "\n\n".join(parts).strip()
    excerpt = f"{clean_title}\n\n{body}".strip()
    excerpt = normalize_block(excerpt)
    excerpt = trim_to_sentence_boundary(excerpt, min_words=min_words)
    wc = word_count(excerpt)
    if not (min_words <= wc <= max_words):
        return None
    if DISAMBIG_RE.search(excerpt[:1200]):
        return None
    if has_suspicious_encoding(excerpt[:4000]):
        return None
    if has_bad_tail(excerpt):
        return None
    return excerpt


def make_sample(row: dict[str, Any], bucket: str, excerpt: str) -> dict[str, Any]:
    return {
        "sample_index": None,
        "bucket": bucket,
        "word_count": word_count(excerpt),
        "source_dataset": "wikimedia/wikipedia",
        "source_config": row.get("_source_config"),
        "source_split": row.get("_source_split"),
        "source_real_origin": "Wikipedia articles from Wikimedia dumps, accessed via Hugging Face dataset wikimedia/wikipedia.",
        "source_license": "Wikipedia/Wikimedia open text (CC BY-SA + GFDL obligations apply; keep attribution metadata).",
        "source_article_id": row.get("id"),
        "source_title": row.get("title"),
        "source_url": row.get("url"),
        "excerpt_strategy": "title_plus_lead_excerpt",
        "text_sha1": sha1_text(excerpt),
        "text": excerpt,
    }


def parse_args() -> argparse.Namespace:
    base_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Extract encyclopedia samples from wikimedia/wikipedia.")
    parser.add_argument("--dataset", default="wikimedia/wikipedia")
    parser.add_argument("--config", default="20231101.en")
    parser.add_argument("--split", default="train")
    parser.add_argument("--total", type=int, default=150)
    parser.add_argument("--max-scan", type=int, default=20000)
    parser.add_argument("--min-scan-before-stop", type=int, default=20000)
    parser.add_argument("--pool-multiplier", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--log-every", type=int, default=5000)
    parser.add_argument("--analyze-only", action="store_true")
    parser.add_argument("--out", type=Path, default=base_dir / "gen_know_150_samples.jsonl")
    parser.add_argument("--meta-out", type=Path, default=base_dir / "gen_know_150_samples.meta.json")
    return parser.parse_args()


def target_buckets_for_total(total: int) -> dict[str, int]:
    medium = round(total * 0.70)
    short = round(total * 0.20)
    long = total - medium - short
    return {"short": short, "medium": medium, "long": long}


def reservoir_add(
    pools: dict[str, list[dict[str, Any]]],
    seen_counts: dict[str, int],
    bucket: str,
    item: dict[str, Any],
    cap: int,
    rng: random.Random,
) -> None:
    seen_counts[bucket] += 1
    pool = pools[bucket]
    if len(pool) < cap:
        pool.append(item)
        return
    idx = rng.randint(0, seen_counts[bucket] - 1)
    if idx < cap:
        pool[idx] = item


def select_final_samples(
    pools: dict[str, list[dict[str, Any]]],
    targets: dict[str, int],
    rng: random.Random,
) -> list[dict[str, Any]]:
    selected: dict[str, list[dict[str, Any]]] = {"short": [], "medium": [], "long": []}
    used_articles: set[str] = set()
    used_titles: set[str] = set()

    for bucket in ["long", "medium", "short"]:
        pool = list(pools[bucket])
        rng.shuffle(pool)
        for item in pool:
            article_id = str(item.get("source_article_id") or "")
            title_key = normalize_title_key(str(item.get("source_title") or ""))
            if not article_id or article_id in used_articles:
                continue
            if not title_key or title_key in used_titles:
                continue
            selected[bucket].append(item)
            used_articles.add(article_id)
            used_titles.add(title_key)
            if len(selected[bucket]) >= targets[bucket]:
                break
        if len(selected[bucket]) < targets[bucket]:
            raise RuntimeError(
                f"Not enough unique candidates for bucket '{bucket}'. "
                f"Needed {targets[bucket]}, got {len(selected[bucket])}. "
                "Increase --max-scan or --pool-multiplier."
            )

    merged: list[dict[str, Any]] = []
    for bucket in ["short", "medium", "long"]:
        merged.extend(selected[bucket][: targets[bucket]])
    rng.shuffle(merged)
    for idx, row in enumerate(merged, start=1):
        row["sample_index"] = idx
    return merged


def main() -> int:
    args = parse_args()
    rng = random.Random(args.seed)
    targets = target_buckets_for_total(args.total)
    pool_caps = {bucket: max(targets[bucket] * args.pool_multiplier, targets[bucket]) for bucket in targets}

    ds = load_dataset(args.dataset, args.config, split=args.split, streaming=True)

    pools: dict[str, list[dict[str, Any]]] = {"short": [], "medium": [], "long": []}
    eligible_counts = Counter()
    seen_counts = {"short": 0, "medium": 0, "long": 0}
    seen_article_ids: set[str] = set()
    seen_titles: set[str] = set()
    scanned = 0
    kept_any = 0
    start = time.time()

    pbar = tqdm(total=args.max_scan, desc="scan", unit="row")
    try:
        for row in ds:
            scanned += 1
            if scanned > args.max_scan:
                break
            pbar.update(1)
            if args.log_every and scanned % args.log_every == 0:
                elapsed = max(time.time() - start, 0.001)
                print(
                    f"[scan] scanned={scanned} kept={kept_any} "
                    f"eligible={dict(eligible_counts)} rate={int(scanned / elapsed)}/sec"
                )

            title = str(row.get("title") or "")
            text = str(row.get("text") or "")
            url = str(row.get("url") or "")
            article_id = str(row.get("id") or "")
            if not title or not text or not url or not article_id:
                continue

            title_key = normalize_title_key(title)
            if article_id in seen_article_ids or title_key in seen_titles:
                continue
            seen_article_ids.add(article_id)
            seen_titles.add(title_key)

            row_for_sample = {
                "id": article_id,
                "title": title,
                "url": url,
                "_source_config": args.config,
                "_source_split": args.split,
            }

            row_eligible = False
            for bucket in ["short", "medium", "long"]:
                excerpt = extract_excerpt(title, text, bucket)
                if excerpt is None:
                    continue
                row_eligible = True
                eligible_counts[bucket] += 1
                sample = make_sample(row_for_sample, bucket, excerpt)
                reservoir_add(
                    pools=pools,
                    seen_counts=seen_counts,
                    bucket=bucket,
                    item=sample,
                    cap=pool_caps[bucket],
                    rng=rng,
                )

            if row_eligible:
                kept_any += 1

            if args.analyze_only:
                continue

            if (
                scanned >= args.min_scan_before_stop
                and all(len(pools[bucket]) >= pool_caps[bucket] for bucket in pools)
            ):
                break
    finally:
        pbar.close()

    elapsed = round(time.time() - start, 2)

    if args.analyze_only:
        report = {
            "mode": "analyze-only",
            "dataset": args.dataset,
            "config": args.config,
            "split": args.split,
            "targets": targets,
            "eligible_bucket_counts": dict(eligible_counts),
            "pool_caps": pool_caps,
            "scanned_rows": scanned,
            "rows_with_any_eligible_excerpt": kept_any,
            "elapsed_sec": elapsed,
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    final_rows = select_final_samples(pools, targets, rng)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="\n") as handle:
        for row in final_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    bucket_counts = Counter(row["bucket"] for row in final_rows)
    wc_values = [int(row["word_count"]) for row in final_rows]
    meta = {
        "dataset": args.dataset,
        "config": args.config,
        "split": args.split,
        "target_total": args.total,
        "target_bucket_counts": targets,
        "actual_total": len(final_rows),
        "actual_bucket_counts": dict(bucket_counts),
        "word_count_range": [min(wc_values), max(wc_values)],
        "max_scan": args.max_scan,
        "min_scan_before_stop": args.min_scan_before_stop,
        "pool_multiplier": args.pool_multiplier,
        "scanned_rows": scanned,
        "rows_with_any_eligible_excerpt": kept_any,
        "eligible_bucket_counts": dict(eligible_counts),
        "elapsed_sec": elapsed,
        "selection_note": "Samples were drawn from unique Wikipedia articles and converted into title-plus-lead excerpts.",
        "source_note": "Recommended source for this task is wikimedia/wikipedia, not Salesforce/wikitext.",
    }
    args.meta_out.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote: {args.out}")
    print(f"Wrote: {args.meta_out}")
    print(f"bucket_counts: {dict(bucket_counts)}")
    print(f"word_count_range: {(min(wc_values), max(wc_values))}")
    print(f"scanned_rows: {scanned}")
    print(f"eligible_bucket_counts: {dict(eligible_counts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
