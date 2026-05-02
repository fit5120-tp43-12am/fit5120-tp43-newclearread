import argparse
import json
import re
from collections import Counter
from typing import Any, Dict, List, Tuple


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


def load_jsonl(path: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception as e:
                raise ValueError(f"Invalid JSON on line {i}: {e}") from e
    return rows


def norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def wc(s: str) -> int:
    return len(norm_ws(s).split())


def english_score(text: str, max_tokens: int = 200) -> float:
    toks = re.findall(r"[A-Za-z']+", text.lower())
    toks = toks[:max_tokens]
    if not toks:
        return 0.0
    hits = sum(1 for t in toks if t in EN_STOP)
    return hits / len(toks)


def is_probably_english(text: str) -> bool:
    # Cheap heuristic: enough common English function words.
    return english_score(text) >= 0.03


def looks_like_discussion(title: str, text: str) -> bool:
    t = (title or "").lower()
    if t.startswith(("user:", "user talk:", "talk:", "cookbook talk:")):
        return True
    # Talk-like signatures/timestamps
    if re.search(r"\b\(\s*talk\s*\)\b", text, re.I):
        return True
    if re.search(r"\b\d{1,2}:\d{2},\s*\d{1,2}\s+\w+\s+\d{4}\b", text):
        return True
    return False


def has_urls(text: str) -> bool:
    return bool(re.search(r"https?://", text))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", default="tech_doc_100_samples.jsonl")
    ap.add_argument("--sft", default=None, help="Optional SFT JSONL to audit outputs too")
    ap.add_argument("--max-print", type=int, default=8)
    args = ap.parse_args()

    samples = load_jsonl(args.samples)
    sft = load_jsonl(args.sft) if args.sft else None
    if sft is not None and len(samples) != len(sft):
        raise SystemExit(f"Line count mismatch: samples={len(samples)} sft={len(sft)}")

    flags: Counter[str] = Counter()
    bad: List[Tuple[int, List[str]]] = []

    for i in range(len(samples)):
        sm = samples[i]
        text = sm.get("text", "")
        if not isinstance(text, str):
            text = ""
        title = sm.get("source_title") or ""
        reasons: List[str] = []

        if not is_probably_english(text):
            reasons.append("non_english_or_low_english_score")
        if looks_like_discussion(title, text):
            reasons.append("discussion_or_user_talk_like")
        if has_urls(text):
            reasons.append("contains_urls")

        # bucket / word count consistency
        w = wc(text)
        if not (250 <= w <= 1200):
            reasons.append(f"wc_out_of_range:{w}")

        if sft is not None:
            row = sft[i]
            # Ensure assistant JSON has exactly 3 key points
            try:
                assistant_obj = json.loads(row["messages"][2]["content"])
                kps = assistant_obj.get("key_points", None)
                if not isinstance(kps, list) or len(kps) != 3:
                    reasons.append("assistant_key_points_not_3")
            except Exception:
                reasons.append("assistant_not_json")

        if reasons:
            bad.append((i, reasons))
            for r in reasons:
                flags[r] += 1

    print(json.dumps({"n": len(samples), "flag_counts": dict(flags), "bad_rows": len(bad)}, indent=2))

    to_show = bad[: args.max_print]
    for idx, reasons in to_show:
        sm = samples[idx]
        print("\n---")
        print("row_index:", idx)
        print("reasons:", reasons)
        print("source_title:", sm.get("source_title"))
        print("source_url:", sm.get("source_url"))
        print("bucket:", sm.get("bucket"), "word_count:", sm.get("word_count"))
        user = sm.get("text", "")
        head = "text_head: " + norm_ws(str(user)[:260])
        print(head.encode("ascii", "backslashreplace").decode("ascii"))
        if sft is not None:
            row = sft[idx]
            print("assistant:", row["messages"][2]["content"][:260])


if __name__ == "__main__":
    main()
