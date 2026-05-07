import argparse
import hashlib
import json
import os
import random
import re
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

from datasets import load_dataset
from huggingface_hub import HfApi


HERE = os.path.dirname(os.path.abspath(__file__))


SYSTEM_PROMPT = (
    "You are a reading support assistant for students with dyslexia.\n"
    "Your task is to produce a quick summary of dense academic or public-information text.\n"
    "Return only valid JSON with this schema:\n"
    "{\n"
    '  "main_idea": "2 to 3 short sentences",\n'
    '  "key_points": ["point 1", "point 2", "point 3"]\n'
    "}\n"
    "Keep the language clear, simple, and short.\n"
    "Do not add information that is not supported by the source text."
)


def _norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


def _word_count(s: str) -> int:
    s = _norm_ws(s)
    return 0 if not s else len(s.split())


def _bucket(wc: int) -> Optional[str]:
    # Non-overlapping buckets
    if 250 <= wc <= 499:
        return "short"
    if 500 <= wc <= 800:
        return "medium"
    if 801 <= wc <= 1200:
        return "long"
    return None


def _safe_get(row: Dict[str, Any], keys: List[str]) -> Optional[Any]:
    for k in keys:
        if k in row and row[k] not in (None, ""):
            return row[k]
    return None


def _sha1_text(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def _dataset_card_min(repo_id: str) -> Dict[str, Any]:
    api = HfApi()
    info = api.dataset_info(repo_id=repo_id)
    card = getattr(info, "cardData", None) or {}
    try:
        card = dict(card)
    except Exception:
        card = card if isinstance(card, dict) else {}
    return {
        "repo_id": repo_id,
        "sha": getattr(info, "sha", None),
        "last_modified": (
            getattr(info, "lastModified", None).isoformat()
            if hasattr(getattr(info, "lastModified", None), "isoformat")
            else getattr(info, "lastModified", None)
        ),
        "license": card.get("license") or card.get("licenses") or None,
        "homepage": card.get("homepage") or None,
        "source": card.get("source") or card.get("sources") or None,
    }


def _section_text(section: Dict[str, Any]) -> str:
    title = section.get("title")
    para = section.get("paragraph")
    parts: List[str] = []
    if isinstance(title, str) and title.strip():
        parts.append(title.strip())
    if isinstance(para, str) and para.strip():
        parts.append(para.strip())
    elif isinstance(para, list):
        parts.extend([p.strip() for p in para if isinstance(p, str) and p.strip()])
    return "\n\n".join(parts).strip()


CNX_URL_RE = re.compile(r"https?://cnx\.org/content/(col\d+/\d+\.\d+)", re.I)


def _pick_window_words(words: List[str], target_len: int, rng: random.Random) -> str:
    if len(words) <= target_len:
        return " ".join(words)
    start_max = max(0, len(words) - target_len)
    start = rng.randint(0, start_max)
    return " ".join(words[start : start + target_len])


def _looks_like_exercises(text: str) -> bool:
    t = text.lower()
    if "review questions" in t or "problems & exercises" in t or "problems and exercises" in t:
        return True
    if "about the authors" in t or "senior contributing authors" in t:
        return True
    if "table of contents" in t:
        return True
    # many MCQ option markers
    if len(re.findall(r"\b[a-d]\.\s", text)) >= 6:
        return True
    if text.count("?") >= 4:
        return True
    # front-matter / rights lines that harm summarization quality
    head = t[:400]
    if "preface" in head:
        return True
    if "regents of" in head or "all rights reserved" in head:
        return True
    return False


def iter_openstax_text_sections(stream_ds, repo_id: str, split: str, progress_rows_every: int = 0) -> Iterable[Dict[str, Any]]:
    """
    Build section/module-level articles from crumb/openstax-text streaming rows.
    We detect boundaries by CNX module URL:
      http(s)://cnx.org/content/colXXXXXX/X.Y
    Output unit is ONE module/section (single-source), never crosses module URL boundaries.
    """
    current_module: Optional[str] = None
    current_lines: List[str] = []
    start_row: Optional[int] = None
    end_row: Optional[int] = None

    def flush_chapter():
        nonlocal current_module, current_lines, start_row, end_row
        if not current_module:
            current_module = None
            current_lines = []
            start_row = None
            end_row = None
            return
        text_raw = "\n".join([ln for ln in current_lines if ln.strip()])
        text = _norm_ws(text_raw)
        if text and not _looks_like_exercises(text):
            yield {
                "source_dataset": repo_id,
                "source_split": split,
                "source_row_idx": start_row,
                "source_row_idx_end": end_row,
                "article_id": f"{repo_id}|split={split}|module={current_module}|rows={start_row}-{end_row}",
                "title": None,
                "book": None,
                "chapter": None,
                "section": None,
                "url": None,
                "text": text,
            }
        current_module = None
        current_lines = []
        start_row = None
        end_row = None

    for row_idx, row in enumerate(stream_ds):
        if progress_rows_every and row_idx > 0 and (row_idx % progress_rows_every == 0):
            print(f"[scan] rows={row_idx} in_module={bool(current_module)}", flush=True)
        line = row.get("text")
        if not isinstance(line, str):
            continue
        s = line.strip()
        if not s:
            continue

        # Module boundary by CNX URL
        m = CNX_URL_RE.search(s)
        if m:
            module = m.group(1).lower()
            for item in flush_chapter():
                yield item
            current_module = module
            current_lines = [s]
            start_row = row_idx
            end_row = row_idx
            continue

        if current_module:
            current_lines.append(s)
            end_row = row_idx

    for item in flush_chapter():
        yield item


class Reservoir:
    def __init__(self, k: int, rng: random.Random):
        self.k = k
        self.rng = rng
        self.items: List[Dict[str, Any]] = []
        self.n_seen = 0

    def consider(self, item: Dict[str, Any]):
        self.n_seen += 1
        if len(self.items) < self.k:
            self.items.append(item)
            return
        j = self.rng.randint(1, self.n_seen)
        if j <= self.k:
            self.items[j - 1] = item


def iter_rows(ds) -> Iterable[Tuple[int, Dict[str, Any]]]:
    # Supports standard (non-streaming) datasets.
    for i in range(len(ds)):
        yield i, ds[i]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-total", type=int, default=250)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--max-chapters", type=int, default=20000, help="Max modules to scan from openstax-text")
    ap.add_argument("--min-chapters", type=int, default=6000, help="Don't early-stop before this many modules")
    ap.add_argument("--progress-every", type=int, default=500, help="Print progress every N modules")
    ap.add_argument("--progress-rows-every", type=int, default=200000, help="Print progress every N raw rows scanned")
    args = ap.parse_args()

    n_total = args.n_total
    quotas = {
        "short": int(round(n_total * 0.20)),
        "medium": int(round(n_total * 0.70)),
        "long": n_total - int(round(n_total * 0.20)) - int(round(n_total * 0.70)),
    }
    assert sum(quotas.values()) == n_total

    rng = random.Random(args.seed)

    # We build chapter-level "articles" from crumb/openstax-text (CC BY 4.0 on dataset page).
    sources = ["crumb/openstax-text"]

    cards = []
    for repo_id in sources:
        try:
            cards.append(_dataset_card_min(repo_id))
        except Exception as e:
            cards.append({"repo_id": repo_id, "error": repr(e)})

    reservoirs = {b: Reservoir(quotas[b], rng) for b in quotas}
    availability = {b: 0 for b in quotas}
    scanned_rows = []
    seen_text_hashes = set()

    for repo_id in sources:
        # Use streaming for the 3.35M rows dataset
        ds_stream = load_dataset(repo_id, split="train", streaming=True)
        split = "train"
        scan_n = args.max_chapters

        n_chapters_seen = 0
        last_row_report = 0
        for chap in iter_openstax_text_sections(
            ds_stream, repo_id=repo_id, split=split, progress_rows_every=args.progress_rows_every
        ):
            n_chapters_seen += 1
            if scan_n and n_chapters_seen > scan_n:
                break
            if args.progress_every and (n_chapters_seen % args.progress_every == 0):
                have = {b: len(reservoirs[b].items) for b in quotas}
                print(f"[progress] chapters={n_chapters_seen} selected={have} availability={availability}", flush=True)

            full_text = chap["text"]
            full_words = full_text.split()
            full_wc = len(full_words)
            if full_wc < 250:
                continue

            # For each bucket, we can take a window of a target length (still within the same chapter)
            for b, (lo, hi, target) in {
                "short": (250, 499, 350),
                "medium": (500, 800, 700),
                "long": (801, 1200, 1000),
            }.items():
                if full_wc < lo:
                    continue
                window_len = min(hi, max(lo, target), full_wc)
                text_win = _pick_window_words(full_words, window_len, rng)
                wc = len(text_win.split())
                if wc < lo or wc > hi:
                    continue

                th = _sha1_text(text_win)
                if th in seen_text_hashes:
                    continue

                availability[b] += 1
                item = {
                    "source_dataset": repo_id,
                    "source_split": split,
                    "source_row_idx": chap.get("source_row_idx"),
                    "source_row_idx_end": chap.get("source_row_idx_end"),
                    "article_id": chap.get("article_id"),
                    "title": chap.get("title"),
                    "book": chap.get("book"),
                    "chapter": chap.get("chapter"),
                    "section": None,
                    "url": chap.get("url"),
                    "word_count": wc,
                    "bucket": b,
                    "text": _norm_ws(text_win),
                    "text_sha1": th,
                }
                reservoirs[b].consider(item)

            # Early stop once quotas are filled and we've scanned enough for randomness
            if n_chapters_seen >= args.min_chapters and all(len(reservoirs[b].items) >= quotas[b] for b in quotas):
                print(f"[early-stop] chapters={n_chapters_seen} filled_quotas={quotas}", flush=True)
                break

        scanned_rows.append(
            {
                "repo_id": repo_id,
                "split": split,
                "note": "streaming; scan_n refers to chapters processed if set",
                "chapters_seen": n_chapters_seen,
            }
        )

    # Ensure quotas met
    missing = {b: max(0, quotas[b] - len(reservoirs[b].items)) for b in quotas}
    if any(v > 0 for v in missing.values()):
        raise SystemExit(
            "Not enough eligible single-source items to satisfy quotas.\n"
            f"Quotas: {quotas}\n"
            f"Selected: {{b: len(r.items) for b,r in reservoirs.items()}}\n"
            f"Missing: {missing}\n"
            f"Availability (scanned): {availability}\n"
            "Try increasing --max-scan-per-split to 0 (full scan) or add more sources with clear licenses."
        )

    samples: List[Dict[str, Any]] = []
    for b in ["medium", "short", "long"]:
        samples.extend(reservoirs[b].items)
    rng.shuffle(samples)

    out_samples_path = os.path.join(HERE, "academic_book_250_samples.jsonl")
    with open(out_samples_path, "w", encoding="utf-8") as f:
        for s in samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    meta = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "n_total": n_total,
        "seed": args.seed,
        "quotas": quotas,
        "availability_scanned": availability,
        "selected_counts": {b: len(reservoirs[b].items) for b in quotas},
        "scanned": scanned_rows,
        "sources": cards,
        "bucket_definition": {
            "short": "250-499",
            "medium": "500-800",
            "long": "801-1200",
        },
        "single_source_rule": "Each sample is a contiguous word-window from ONE OpenStax chapter; never crosses chapter/book boundaries.",
    }
    out_meta_path = os.path.join(HERE, "academic_book_250_samples.meta.json")
    with open(out_meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"Wrote: {out_samples_path}")
    print(f"Wrote: {out_meta_path}")


if __name__ == "__main__":
    main()
