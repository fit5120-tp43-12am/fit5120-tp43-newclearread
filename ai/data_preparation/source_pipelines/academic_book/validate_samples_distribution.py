import argparse
import json
from collections import Counter


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", type=str, default="academic_book_250_samples.jsonl")
    ap.add_argument("--expected-lines", type=int, default=0)
    ap.add_argument("--expected-short", type=int, default=0)
    ap.add_argument("--expected-medium", type=int, default=0)
    ap.add_argument("--expected-long", type=int, default=0)
    args = ap.parse_args()

    path = args.path
    c = Counter()
    wmin = 10**9
    wmax = 0
    n = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            o = json.loads(line)
            n += 1
            wc = int(o["word_count"])
            wmin = min(wmin, wc)
            wmax = max(wmax, wc)
            c[o["bucket"]] += 1
    report = {"n": n, "bucket_counts": dict(c), "word_count_min": wmin, "word_count_max": wmax}
    if args.expected_lines and n != args.expected_lines:
        raise SystemExit(f"Expected {args.expected_lines} rows, got {n}")
    expected = {
        "short": args.expected_short,
        "medium": args.expected_medium,
        "long": args.expected_long,
    }
    for bucket, want in expected.items():
        if want and c.get(bucket, 0) != want:
            raise SystemExit(f"Expected {want} rows in bucket '{bucket}', got {c.get(bucket, 0)}")
    print(report)


if __name__ == "__main__":
    main()
