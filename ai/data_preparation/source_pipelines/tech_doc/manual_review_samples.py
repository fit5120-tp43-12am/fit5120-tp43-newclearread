import argparse
import json
import random
import re
from typing import Any, Dict, List, Tuple


def load_jsonl(path: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def head_tail(text: str, head_chars: int = 320, tail_chars: int = 220) -> Tuple[str, str]:
    t = norm_ws(text)
    head = t[:head_chars]
    tail = t[-tail_chars:] if len(t) > tail_chars else t
    return head, tail


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", default="tech_doc_100_samples.jsonl")
    ap.add_argument("--sft", default="tech_doc_100_sft.jsonl")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--k", type=int, default=12, help="random rows to review")
    ap.add_argument("--per-bucket", type=int, default=3, help="extra rows per bucket")
    args = ap.parse_args()

    samples = load_jsonl(args.samples)
    sft = load_jsonl(args.sft)
    assert len(samples) == len(sft)

    idxs = set()
    random.seed(args.seed)
    while len(idxs) < min(args.k, len(samples)):
        idxs.add(random.randrange(0, len(samples)))

    # Ensure bucket coverage
    by_bucket: Dict[str, List[int]] = {"short": [], "medium": [], "long": []}
    for i, r in enumerate(samples):
        b = r.get("bucket")
        if b in by_bucket:
            by_bucket[b].append(i)

    for b, lst in by_bucket.items():
        random.shuffle(lst)
        for i in lst[: args.per_bucket]:
            idxs.add(i)

    # Also include first/last few rows
    for i in [0, 1, 2, len(samples) - 1, len(samples) - 2]:
        if 0 <= i < len(samples):
            idxs.add(i)

    idx_list = sorted(idxs)
    out: List[Dict[str, Any]] = []
    for i in idx_list:
        sm = samples[i]
        row = sft[i]
        user_text = row["messages"][1]["content"]
        assistant_text = row["messages"][2]["content"]
        assistant_obj = json.loads(assistant_text)
        head, tail = head_tail(user_text)
        out.append(
            {
                "row_index": i,
                "bucket": sm.get("bucket"),
                "word_count": sm.get("word_count"),
                "source_title": sm.get("source_title"),
                "source_url": sm.get("source_url"),
                "user_head": head,
                "user_tail": tail,
                "assistant": assistant_obj,
            }
        )

    # Windows consoles may default to GBK. Ensure we can always write the JSON.
    # Write to file to avoid console encoding issues.
    report = {"n_total": len(samples), "n_review": len(out), "rows": out}
    with open("manual_review_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("Wrote: manual_review_report.json")


if __name__ == "__main__":
    main()
