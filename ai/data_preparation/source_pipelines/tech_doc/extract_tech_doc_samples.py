import argparse
import hashlib
import json
import random
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

from datasets import load_dataset
from tqdm import tqdm


def normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def word_count(text: str) -> int:
    return len(text.split())


def sha1_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()


def choose_bucket(n_words: int) -> Optional[str]:
    if 250 <= n_words <= 499:
        return "short"
    if 500 <= n_words <= 800:
        return "medium"
    if 801 <= n_words <= 1200:
        return "long"
    return None


BUCKET_RANGES = {
    "short": (250, 499),
    "medium": (500, 800),
    "long": (801, 1200),
}


def _trim_to_sentence_boundary(text: str) -> str:
    tail = text[-400:]
    m = re.search(r"([.!?])\s+[A-Z0-9]", tail)
    if m:
        cut = len(text) - len(tail) + m.start(1) + 1
        return text[:cut].strip()
    return text.strip()


def excerpt_from_text(text: str, min_words: int, max_words: int, target_words: int) -> Optional[str]:
    """
    Build a coherent excerpt from a single page.
    Strategy: take early contiguous content; cut at word limit; try to end on sentence boundary.
    """
    raw = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    paras = [p.strip() for p in re.split(r"\n{2,}", raw) if p.strip()]
    if not paras:
        return None

    cleaned: List[str] = []
    for p in paras:
        if len(p) < 40:
            continue
        if re.search(r"\b(table of contents|contents)\b", p, re.I) and len(p.split()) < 120:
            continue
        cleaned.append(p)
    if not cleaned:
        cleaned = paras

    parts: List[str] = []
    cur_words = 0
    for p in cleaned:
        p_norm = normalize_ws(p)
        if not p_norm:
            continue
        p_words = p_norm.split()
        if cur_words + len(p_words) > max_words:
            remaining = max_words - cur_words
            if remaining <= 0:
                break
            parts.append(" ".join(p_words[:remaining]))
            cur_words += remaining
            break
        parts.append(p_norm)
        cur_words += len(p_words)
        if cur_words >= target_words:
            break

    excerpt = normalize_ws(" ".join(parts))
    n = word_count(excerpt)
    if n < min_words:
        all_words = normalize_ws(raw).split()
        if len(all_words) < min_words:
            return None
        excerpt = " ".join(all_words[: min(max_words, len(all_words))])
        excerpt = _trim_to_sentence_boundary(excerpt)
        excerpt = normalize_ws(excerpt)
        if word_count(excerpt) < min_words:
            return None

    if word_count(excerpt) > max_words:
        excerpt = " ".join(excerpt.split()[:max_words])
        excerpt = _trim_to_sentence_boundary(excerpt)
        excerpt = normalize_ws(excerpt)

    n2 = word_count(excerpt)
    if not (min_words <= n2 <= max_words):
        return None
    return excerpt


def excerpt_for_bucket(text: str, bucket: str) -> Optional[str]:
    mn, mx = BUCKET_RANGES[bucket]
    target = 650 if bucket == "medium" else (360 if bucket == "short" else 950)
    return excerpt_from_text(text, mn, mx, target)


TECH_POSITIVE = re.compile(
    r"\b("
    r"install|installation|configure|configuration|setup|getting started|quickstart|"
    r"getting_started|quick_start|"
    r"usage|commands?|cli|flags?|options?|arguments?|environment variables?|"
    r"command line|command-line|syntax|examples?|parameters?|"
    r"functions?|libraries?|packages?|modules?|preprocessor|variables?|operators?|"
    r"api reference|reference|tutorial|guide|manual|troubleshoot|"
    r"build|compile|run|deploy|docker|kubernetes|linux|windows|macos|"
    r"python|node|npm|pip|conda|git|github|http|json|yaml|toml|"
    r"database|sql|postgres|mysql|redis|"
    r"authentication|authorization|oauth|token|"
    r"endpoint|request|response"
    r")\b",
    re.IGNORECASE,
)

# Stronger "this is tech/tool documentation" signals.
TECH_STRONG = re.compile(
    r"\b("
    r"install|installation|uninstall|configure|configuration|setup|quickstart|getting started|"
    r"usage|examples?|command line|command-line|cli|flags?|options?|arguments?|parameters?|"
    r"api|api reference|endpoint|request|response|http|https|"
    r"environment variables?|env var|"
    r"docker|kubernetes|"
    r"pip|npm|conda|venv|virtualenv|"
    r"git|github|"
    r"sql|postgres|mysql|sqlite|"
    r"windows|linux|macos"
    r")\b",
    re.IGNORECASE,
)

# Titles that are usually not "tech doc / tool instruction" for this dataset.
NON_TECH_TITLE = re.compile(
    r"^(?:"
    r"general biology|biology|botany|biochemistry|organic chemistry|chemistry|"
    r"world history|history|united states government|government|"
    r"abstract algebra|algebra|calculus|mathematics|physics"
    r")",
    re.IGNORECASE,
)

TECH_ALLOW_IN_TITLE_URL = re.compile(
    r"(^|[^A-Za-z0-9])("
    r"computer|programming|software|operating system|"
    r"linux|windows|macos|"
    r"internet|web|world wide web|network|networking|"
    r"database|sql|postgres|mysql|sqlite|"
    r"git|github|docker|kubernetes|"
    r"api|json|yaml|"
    r"c programming|c\\+\\+|java|javascript|python|typescript|rust|golang"
    r")([^A-Za-z0-9]|$)",
    re.IGNORECASE,
)

TECH_OPERATIONAL = re.compile(
    r"\b("
    r"install|uninstall|configure|configuration|setup|quickstart|getting started|"
    r"usage|command line|command-line|cli|flags?|options?|arguments?|parameters?|"
    r"api reference|api|endpoint|request|response"
    r")\b",
    re.IGNORECASE,
)

TECH_NEGATIVE = re.compile(
    r"\b("
    r"recipe|cookbook|poem|lyrics|novel|fiction|fantasy|romance|"
    r"game walkthrough|walkthrough|cheats"
    r"horoscope|astrology|"
    r"home remedy|"
    r"biology of|history of"
    r"|spanish|french|german|grammar|vocabulary|lesson|dialogue"
    r")\b",
    re.IGNORECASE,
)

EN_STOP = {
    "the",
    "and",
    "to",
    "of",
    "in",
    "is",
    "that",
    "for",
    "on",
    "with",
    "as",
    "are",
    "be",
    "by",
    "this",
    "from",
    "or",
    "an",
    "at",
    "not",
    "can",
    "will",
    "you",
    "your",
}


def english_score(text: str, max_tokens: int = 220) -> float:
    toks = re.findall(r"[A-Za-z']+", text.lower())
    toks = toks[:max_tokens]
    if not toks:
        return 0.0
    hits = sum(1 for t in toks if t in EN_STOP)
    return hits / len(toks)


def has_url(text: str) -> bool:
    return bool(re.search(r"https?://", text))


def url_count(text: str) -> int:
    return len(re.findall(r"https?://", text))


def looks_like_discussion_title(title: str) -> bool:
    t = (title or "").lower()
    return t.startswith(("user:", "user talk:", "talk:", "help talk:", "cookbook talk:"))


def looks_like_discussion_body(text: str) -> bool:
    # Common wiki talk signatures / timestamps.
    if re.search(r"\b\(\s*talk\s*\)\b", text, re.I):
        return True
    if re.search(r"\b\d{1,2}:\d{2},\s*\d{1,2}\s+\w+\s+\d{4}\b", text):
        return True
    if re.search(r"\bUTC\)", text):
        return True
    return False


def get_namespace(row: Dict[str, Any]) -> str:
    md = row.get("metadata")
    if isinstance(md, dict):
        ns = md.get("namespace")
        if isinstance(ns, str):
            return ns.strip()
        if isinstance(ns, int):
            return str(ns)
    return ""


def looks_like_technical_doc(title: str, text: str) -> bool:
    t = f"{title}\n{text}"
    # Hard reject broad non-tech textbook topics for this dataset.
    if NON_TECH_TITLE.search((title or "").strip()):
        return False
    if not TECH_POSITIVE.search(t):
        return False
    if TECH_NEGATIVE.search(t):
        return False
    if not TECH_STRONG.search(t):
        return False
    return True


def get_first_str(row: Dict[str, Any], candidates: List[str]) -> str:
    for k in candidates:
        v = row.get(k)
        if isinstance(v, str) and v.strip():
            return v
    return ""


def get_project(row: Dict[str, Any]) -> str:
    for k in ["project", "wiki", "source_project", "site", "dataset", "namespace"]:
        v = row.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    md = row.get("metadata")
    if isinstance(md, dict):
        w = md.get("wiki")
        if isinstance(w, str) and w.strip():
            return w.strip()
    return ""


def get_language(row: Dict[str, Any]) -> str:
    for k in ["language", "lang", "locale"]:
        v = row.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    md = row.get("metadata")
    if isinstance(md, dict):
        # some dumps encode language as part of the wiki host (e.g., en.wikibooks.org)
        w = md.get("wiki")
        if isinstance(w, str) and w.strip():
            if w.startswith("en."):
                return "en"
    return ""


def get_url(row: Dict[str, Any]) -> str:
    for k in ["url", "source_url", "canonical_url"]:
        v = row.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    md = row.get("metadata")
    if isinstance(md, dict):
        u = md.get("url")
        if isinstance(u, str) and u.strip():
            return u.strip()
    return ""


@dataclass
class Quotas:
    short: int
    medium: int
    long: int

    @classmethod
    def for_total(cls, total: int) -> "Quotas":
        # Required distribution:
        # 70% medium (500-800), 20% short (250-499), 10% long (801-1200)
        medium = round(total * 0.70)
        short = round(total * 0.20)
        long = total - medium - short
        return cls(short=short, medium=medium, long=long)

    def as_dict(self) -> Dict[str, int]:
        return {"short": self.short, "medium": self.medium, "long": self.long}


def iter_rows(ds: Iterable[Dict[str, Any]]) -> Iterable[Tuple[int, Dict[str, Any]]]:
    idx = 0
    for row in ds:
        yield idx, row
        idx += 1


def extract_text_from_row(row: Dict[str, Any]) -> Tuple[str, str]:
    title = get_first_str(row, ["title", "page_title", "name", "heading"])
    text = get_first_str(row, ["text", "content", "page_text", "body"])
    if not title:
        md = row.get("metadata")
        if isinstance(md, dict):
            t = md.get("title")
            if isinstance(t, str) and t.strip():
                title = t.strip()
    return title, text


def build_sample(
    *,
    source_dataset: str,
    row_idx: int,
    title: str,
    text: str,
    bucket: str,
    n_words: int,
    project: str,
    language: str,
    url: str,
) -> Dict[str, Any]:
    norm = normalize_ws(text)
    return {
        "sample_index": None,
        "bucket": bucket,
        "word_count": n_words,
        "source_dataset": source_dataset,
        "source_real_origin": "Wikimedia database dumps (CC BY-SA). Via Hugging Face dataset common-pile/wikimedia.",
        "source_license": "CC BY-SA (Wikimedia projects; attribution required).",
        "source_row_idx": row_idx,
        "source_project": project or None,
        "source_language": language or None,
        "source_title": title or None,
        "source_url": url or None,
        "text_sha1": sha1_text(norm),
        "text": norm,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="common-pile/wikimedia")
    ap.add_argument("--split", default="train")
    ap.add_argument("--streaming", action="store_true", default=True)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--max-scan", type=int, default=2_000_000)
    ap.add_argument("--min-chars", type=int, default=800)
    ap.add_argument("--require-english", action="store_true", default=True)
    ap.add_argument("--min-english-score", type=float, default=0.03)
    ap.add_argument("--reject-urls", action="store_true", default=False)
    ap.add_argument("--max-urls", type=int, default=2)
    ap.add_argument("--reject-discussions", action="store_true", default=True)
    ap.add_argument("--require-main-namespace", action="store_true", default=True)
    ap.add_argument(
        "--prefer-projects",
        default="wikibooks.com,en.wikibooks.org,wikiversity.org,en.wikiversity.org",
    )
    ap.add_argument("--out", default="tech_doc_100_samples.jsonl")
    ap.add_argument("--meta-out", default="tech_doc_100_samples.meta.json")
    ap.add_argument("--total", type=int, default=100)
    ap.add_argument("--analyze-only", action="store_true", default=False)
    ap.add_argument("--log-every", type=int, default=50000)
    args = ap.parse_args()

    random.seed(args.seed)
    quotas = Quotas.for_total(args.total)
    target = quotas.as_dict()
    got = {"short": 0, "medium": 0, "long": 0}
    samples: Dict[str, List[Dict[str, Any]]] = {"short": [], "medium": [], "long": []}
    seen_sha1: set[str] = set()

    preferred = {p.strip().lower() for p in args.prefer_projects.split(",") if p.strip()}
    source_dataset = args.dataset

    ds = load_dataset(args.dataset, split=args.split, streaming=args.streaming)

    scanned = 0
    kept = 0
    start = time.time()

    pbar = tqdm(total=args.total, desc="collecting", unit="sample")
    try:
        for row_idx, row in iter_rows(ds):
            scanned += 1
            if scanned > args.max_scan and sum(got.values()) < args.total:
                break
            if args.log_every and scanned % args.log_every == 0:
                elapsed = max(0.001, time.time() - start)
                rate = int(scanned / elapsed)
                print(
                    f"[scan] scanned={scanned} kept={kept} got={got} rate={rate}/sec"
                )

            title, text = extract_text_from_row(row)
            if not text:
                continue
            if len(text) < args.min_chars:
                continue

            # Hard filters for content type (avoid talk/user/help namespaces).
            ns = get_namespace(row)
            if args.require_main_namespace and ns and ns != "0":
                continue

            if args.reject_discussions:
                if looks_like_discussion_title(title) or looks_like_discussion_body(text):
                    continue

            project = get_project(row).lower()
            if preferred and project and project not in preferred:
                # still allow if strong technical signal in title+text
                if not looks_like_technical_doc(title, text):
                    continue

            lang = get_language(row).lower()
            if args.require_english:
                # If explicit language exists, require it to be English; if absent, we allow and rely on heuristics.
                if lang and lang not in {"en", "eng", "english"}:
                    continue
                # Heuristic English filter (important because many rows have no language metadata).
                if english_score(text) < args.min_english_score:
                    continue

            if args.reject_urls and has_url(text):
                continue
            if args.max_urls is not None and url_count(text) > args.max_urls:
                continue

            url = get_url(row)
            title_url_norm = ((title or "") + " " + (url or "")).replace("_", " ").replace("/", " ")
            if not TECH_ALLOW_IN_TITLE_URL.search(title_url_norm):
                continue

            if not looks_like_technical_doc(title, text):
                continue

            # Use a single-page excerpt so very long docs can still fit 250–1200 words.
            candidate_buckets = ["medium", "short", "long"] if not args.analyze_only else ["short", "medium", "long"]
            chosen_bucket = None
            chosen_excerpt = None
            for b in candidate_buckets:
                if not args.analyze_only and got[b] >= target[b]:
                    continue
                ex = excerpt_for_bucket(text, b)
                if ex is None:
                    continue
                chosen_bucket = b
                chosen_excerpt = ex
                break

            if chosen_bucket is None or chosen_excerpt is None:
                continue

            n_words = word_count(chosen_excerpt)

            if args.analyze_only:
                kept += 1
                got[chosen_bucket] += 1
                continue

            s_sha1 = sha1_text(chosen_excerpt)
            if s_sha1 in seen_sha1:
                continue
            seen_sha1.add(s_sha1)

            url = get_url(row)
            sample = build_sample(
                source_dataset=source_dataset,
                row_idx=row_idx,
                title=title,
                text=chosen_excerpt,
                bucket=chosen_bucket,
                n_words=n_words,
                project=project,
                language=lang,
                url=url,
            )
            samples[chosen_bucket].append(sample)
            got[chosen_bucket] += 1
            kept += 1
            pbar.update(1)

            if sum(got.values()) >= args.total and all(got[b] >= target[b] for b in target):
                break
    finally:
        pbar.close()

    if args.analyze_only:
        # In analyze-only mode, got[] is "eligible counts by bucket" (not quota-filled).
        meta = {
            "created_at_unix": int(time.time()),
            "mode": "analyze-only",
            "source_dataset": args.dataset,
            "source_split": args.split,
            "streaming": bool(args.streaming),
            "seed": args.seed,
            "max_scan": args.max_scan,
            "min_chars": args.min_chars,
            "require_english": bool(args.require_english),
            "prefer_projects": sorted(list(preferred)),
            "eligible_bucket_counts": got,
            "scanned_rows": scanned,
            "elapsed_sec": round(time.time() - start, 2),
        }
        print(json.dumps(meta, ensure_ascii=False, indent=2))
        return

    # If quotas could not be fully satisfied, do a controlled relaxation:
    # - allow any bucket to fill remaining slots using already-eligible samples from other buckets only by extending max-scan
    # Here we keep it simple: we proceed with what we have and report missing.
    picked: List[Dict[str, Any]] = []
    for b in ["short", "medium", "long"]:
        picked.extend(samples[b][: target[b]])

    # If still short, just take extras from any bucket (already eligible) to reach total.
    if len(picked) < args.total:
        extras: List[Dict[str, Any]] = []
        for b in ["medium", "short", "long"]:
            extras.extend(samples[b][target[b] :])
        random.shuffle(extras)
        need = args.total - len(picked)
        picked.extend(extras[:need])

    random.shuffle(picked)
    for i, s in enumerate(picked):
        s["sample_index"] = i

    with open(args.out, "w", encoding="utf-8") as f:
        for row in picked:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    dist = {"short": 0, "medium": 0, "long": 0}
    wc_min = None
    wc_max = None
    for row in picked:
        dist[row["bucket"]] += 1
        wc = int(row["word_count"])
        wc_min = wc if wc_min is None else min(wc_min, wc)
        wc_max = wc if wc_max is None else max(wc_max, wc)

    meta = {
        "created_at_unix": int(time.time()),
        "source_dataset": args.dataset,
        "source_split": args.split,
        "streaming": bool(args.streaming),
        "seed": args.seed,
        "max_scan": args.max_scan,
        "min_chars": args.min_chars,
        "require_english": bool(args.require_english),
        "prefer_projects": sorted(list(preferred)),
        "target_total": args.total,
        "target_bucket_counts": target,
        "actual_total": len(picked),
        "actual_bucket_counts": dist,
        "word_count_range": [wc_min, wc_max],
        "scanned_rows": scanned,
        "kept_candidates": kept,
        "elapsed_sec": round(time.time() - start, 2),
        "license_note": "Text from Wikimedia projects is CC BY-SA; attribution required. Each row includes title/project/url when available.",
        "stack_edu_note": "HuggingFaceTB/stack-edu only contains SWH blob IDs; downloading contents requires Software Heritage S3. It is heavier than needed for this 100-row doc dataset.",
    }
    with open(args.meta_out, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print("Wrote:", args.out)
    print("Wrote:", args.meta_out)
    print("bucket_counts:", dist)
    print("word_count_range:", (wc_min, wc_max))
    print("scanned_rows:", scanned, "kept_candidates:", kept)


if __name__ == "__main__":
    main()
