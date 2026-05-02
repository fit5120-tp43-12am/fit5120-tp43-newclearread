import argparse
import json
from typing import Any, Dict, List, Optional, Tuple


def word_count(text: str) -> int:
    return len(text.split())


def bucket_for_wc(n: int) -> Optional[str]:
    if 250 <= n <= 499:
        return "short"
    if 500 <= n <= 800:
        return "medium"
    if 801 <= n <= 1200:
        return "long"
    return None


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


def validate_samples(rows: List[Dict[str, Any]]) -> Tuple[Dict[str, int], Tuple[int, int]]:
    dist = {"short": 0, "medium": 0, "long": 0}
    wc_min: Optional[int] = None
    wc_max: Optional[int] = None
    for i, r in enumerate(rows):
        if "text" not in r or not isinstance(r["text"], str) or not r["text"].strip():
            raise ValueError(f"Row {i} missing non-empty text")
        wc = word_count(r["text"])
        b = bucket_for_wc(wc)
        if b is None:
            raise ValueError(f"Row {i} word_count={wc} out of range 250-1200")
        dist[b] += 1
        wc_min = wc if wc_min is None else min(wc_min, wc)
        wc_max = wc if wc_max is None else max(wc_max, wc)
    assert wc_min is not None and wc_max is not None
    return dist, (wc_min, wc_max)


def validate_sft(rows: List[Dict[str, Any]]) -> None:
    for i, r in enumerate(rows):
        msgs = r.get("messages")
        if not isinstance(msgs, list) or len(msgs) != 3:
            raise ValueError(f"Row {i} messages must be a list of length 3")
        roles = [m.get("role") if isinstance(m, dict) else None for m in msgs]
        if roles != ["system", "user", "assistant"]:
            raise ValueError(f"Row {i} roles must be [system,user,assistant], got {roles}")
        user = msgs[1].get("content")
        assistant = msgs[2].get("content")
        if not isinstance(user, str) or not user.strip():
            raise ValueError(f"Row {i} user content empty")
        if not isinstance(assistant, str) or not assistant.strip():
            raise ValueError(f"Row {i} assistant content empty")
        try:
            obj = json.loads(assistant)
        except Exception as e:
            raise ValueError(f"Row {i} assistant content not JSON: {e}") from e
        if set(obj.keys()) != {"main_idea", "key_points"}:
            raise ValueError(f"Row {i} assistant JSON keys must be exactly main_idea/key_points")
        if not isinstance(obj["main_idea"], str) or not obj["main_idea"].strip():
            raise ValueError(f"Row {i} main_idea must be non-empty string")
        if not isinstance(obj["key_points"], list) or len(obj["key_points"]) < 3:
            raise ValueError(f"Row {i} key_points must be a list (>=3)")
        for j, kp in enumerate(obj["key_points"]):
            if not isinstance(kp, str) or not kp.strip():
                raise ValueError(f"Row {i} key_points[{j}] empty")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", help="Path to samples JSONL")
    ap.add_argument("--sft", help="Path to SFT JSONL")
    ap.add_argument("--expected-total", type=int, default=None)
    args = ap.parse_args()

    if not args.samples and not args.sft:
        raise SystemExit("Provide --samples or --sft")

    if args.samples:
        rows = load_jsonl(args.samples)
        if args.expected_total is not None and len(rows) != args.expected_total:
            raise ValueError(f"Expected {args.expected_total} rows, got {len(rows)}")
        dist, wc_range = validate_samples(rows)
        print(f"{args.samples}: OK")
        print("rows=", len(rows))
        print("bucket_counts=", dist)
        print("word_count_range=", wc_range)

    if args.sft:
        rows = load_jsonl(args.sft)
        if args.expected_total is not None and len(rows) != args.expected_total:
            raise ValueError(f"Expected {args.expected_total} rows, got {len(rows)}")
        validate_sft(rows)
        print(f"{args.sft}: OK")
        print("rows=", len(rows))


if __name__ == "__main__":
    main()
