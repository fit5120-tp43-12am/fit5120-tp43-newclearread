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
    ap.add_argument("--sft", default="tech_doc_100_sft.jsonl")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--k", type=int, default=20)
    ap.add_argument("--out", default="manual_review_sft_report.json")
    args = ap.parse_args()

    sft = load_jsonl(args.sft)
    n = len(sft)
    random.seed(args.seed)
    idxs = set()
    while len(idxs) < min(args.k, n):
        idxs.add(random.randrange(0, n))
    for i in [0, 1, 2, n - 1, n - 2]:
        if 0 <= i < n:
            idxs.add(i)
    idx_list = sorted(idxs)

    out_rows: List[Dict[str, Any]] = []
    for i in idx_list:
        row = sft[i]
        user_text = row["messages"][1]["content"]
        assistant_text = row["messages"][2]["content"]
        assistant_obj = json.loads(assistant_text)
        h, t = head_tail(user_text)
        out_rows.append(
            {
                "row_index": i,
                "user_head": h,
                "user_tail": t,
                "assistant": assistant_obj,
            }
        )

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"n_total": n, "n_review": len(out_rows), "rows": out_rows}, f, ensure_ascii=False, indent=2)
    print(f"Wrote: {args.out}")


if __name__ == "__main__":
    main()
