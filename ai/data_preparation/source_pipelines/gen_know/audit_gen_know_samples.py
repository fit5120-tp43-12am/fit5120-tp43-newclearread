#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


MONTH_DAY_TITLE_RE = re.compile(
    r"^(January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}$"
)
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
TIMELINE_RE = re.compile(r"\bPre-1600\b|\b1601[-\u2013\u2014]1900\b|\b1901[-\u2013\u2014]present\b")
TITLE_REJECT_RE = re.compile(
    r"^(?:Neighbourhoods of|Neighborhoods of|.+ in fiction|Meanings of minor planet names:|National Register of Historic Places listings)",
    re.IGNORECASE,
)
YEAR_SEASON_TITLE_RE = re.compile(r"^\d{4}[-\u2013\u2014]\d{2,4}\s+in\b", re.IGNORECASE)
TITLE_CONTEXT_NEGATIVE_RE = re.compile(
    r"\((?:board game|short story|roller coaster|Dungeons & Dragons|nightclub)\)|"
    r"\bon television\b|\bSuper Bowl\b|\bDivision Series\b",
    re.IGNORECASE,
)
LIST_SECTION_RE = re.compile(
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


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_no} of {path}: {exc}") from exc
    return rows


def normalize_ws(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text).strip()


def word_count(text: str) -> int:
    return len(text.split())


def sentence_count(text: str) -> int:
    return len(re.findall(r"[.!?](?=\s|$)", text))


def split_paragraphs(text: str) -> list[str]:
    raw = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    raw = re.sub(r"\n{3,}", "\n\n", raw)
    paras = [p.strip() for p in re.split(r"\n{2,}", raw) if p.strip()]
    return paras or [raw]


def has_suspicious_encoding(text: str) -> bool:
    return bool(SUSPICIOUS_ENCODING_RE.search(text) or CJK_CHAR_RE.search(text))


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


def flags_for_row(row: dict[str, Any], duplicate_titles: set[str]) -> list[str]:
    flags: list[str] = []
    title = str(row.get("source_title") or "")
    text = str(row.get("text") or "")
    title_key = title.casefold().strip()
    tail = text[-1500:]
    tail_paragraphs = split_paragraphs(tail)
    last_para = tail_paragraphs[-1] if tail_paragraphs else tail

    if MONTH_DAY_TITLE_RE.fullmatch(title):
        flags.append("month_day_title")
    if title_key in EXACT_TITLE_REJECTS:
        flags.append("manual_reject_title")
    if TITLE_REJECT_RE.search(title):
        flags.append("reference_like_title")
    if YEAR_SEASON_TITLE_RE.search(title):
        flags.append("season_title")
    if TITLE_CONTEXT_NEGATIVE_RE.search(title):
        flags.append("off_domain_title")
    if title.lower().endswith("(surname)"):
        flags.append("reference_like_title")
    if title_key in duplicate_titles:
        flags.append("duplicate_title")
    if TIMELINE_RE.search(text[:2500]):
        flags.append("timeline_page")
    if LIST_SECTION_RE.search(tail):
        flags.append("list_like_section")
    if has_suspicious_encoding(title) or has_suspicious_encoding(text[:4000]):
        flags.append("suspicious_encoding")
    if TOPIC_NEGATIVE_RE.search(title) or TOPIC_NEGATIVE_RE.search(text[:1200]):
        flags.append("off_domain_topic")
    if LEAD_NEGATIVE_RE.search(title) or LEAD_NEGATIVE_RE.search(text[:1200]):
        flags.append("off_domain_lead")
    if not POSITIVE_LEAD_RE.search(text[:1600]):
        flags.append("missing_positive_signal")
    if LISTY_KEYWORD_RE.search(last_para):
        flags.append("listy_tail")
    if is_list_like(last_para):
        flags.append("listy_tail")
    if not re.search(r"[.!?]['\")\]]?\s*$", text.strip()):
        flags.append("non_sentence_ending")
    return sorted(set(flags))


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit gen_know base samples for content-quality risks.")
    parser.add_argument("--samples", type=Path, required=True)
    parser.add_argument("--show-flagged", action="store_true")
    args = parser.parse_args()

    rows = load_jsonl(args.samples)
    title_counts = Counter(str(row.get("source_title") or "").casefold().strip() for row in rows)
    duplicate_titles = {title for title, count in title_counts.items() if title and count > 1}

    flag_counts = Counter()
    flagged_rows: list[dict[str, Any]] = []

    for row in rows:
        flags = flags_for_row(row, duplicate_titles)
        if flags:
            for flag in flags:
                flag_counts[flag] += 1
            flagged_rows.append(
                {
                    "sample_index": row.get("sample_index"),
                    "bucket": row.get("bucket"),
                    "source_title": row.get("source_title"),
                    "flags": flags,
                }
            )

    print(
        json.dumps(
            {
                "rows": len(rows),
                "duplicate_titles": len(duplicate_titles),
                "flag_counts": dict(flag_counts),
                "flagged_rows": len(flagged_rows),
            },
            ensure_ascii=True,
            indent=2,
        )
    )
    if args.show_flagged and flagged_rows:
        print(json.dumps(flagged_rows, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
