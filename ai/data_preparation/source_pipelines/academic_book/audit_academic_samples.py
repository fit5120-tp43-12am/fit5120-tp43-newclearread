import argparse
import json
import re
from collections import Counter, defaultdict


FLAG_PATTERNS = {
    "toc": re.compile(r"\btable of contents\b", re.I),
    "preface": re.compile(r"\bpreface\b", re.I),
    "review_questions": re.compile(r"\breview questions\b", re.I),
    "mcq_options": re.compile(r"\b[a-d]\.\s"),
    "many_numbers": re.compile(r"\b\d{1,4}\b"),
    "copyright": re.compile(r"\bcopyright\b|©|\xa9", re.I),
    "authors": re.compile(r"\bcontributing authors\b|\bauthors\b", re.I),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", type=str, default="academic_book_250_samples.jsonl")
    args = ap.parse_args()

    path = args.path
    by_flag = Counter()
    bucket_counts = Counter()
    book_counts = Counter()
    examples = defaultdict(list)

    n = 0
    for line_no, line in enumerate(open(path, "r", encoding="utf-8"), start=1):
        if not line.strip():
            continue
        n += 1
        o = json.loads(line)
        text = o["text"]
        bucket_counts[o["bucket"]] += 1
        book_counts[o.get("book") or ""] += 1

        flags = []
        for name, pat in FLAG_PATTERNS.items():
            if name == "mcq_options":
                hits = len(pat.findall(text))
                if hits >= 6:
                    flags.append((name, hits))
            elif name == "many_numbers":
                hits = len(pat.findall(text))
                if hits >= 60:
                    flags.append((name, hits))
            else:
                if pat.search(text):
                    flags.append((name, 1))

        # additional heuristic: many question marks suggests exercise-heavy
        qmarks = text.count("?")
        if qmarks >= 4:
            flags.append(("many_questions", qmarks))

        for name, val in flags:
            by_flag[name] += 1
            if len(examples[name]) < 5:
                examples[name].append(
                    {
                        "line_no": line_no,
                        "bucket": o["bucket"],
                        "word_count": o["word_count"],
                        "article_id": o.get("article_id"),
                        "book": o.get("book"),
                        "title": o.get("title"),
                        "value": val,
                        "preview": text[:240].replace("\n", " "),
                    }
                )

    print("rows", n)
    print("bucket_counts", dict(bucket_counts))
    print("top_books", book_counts.most_common(10))
    print("flag_counts", dict(by_flag))
    for k in sorted(examples.keys()):
        print("\n==", k, "examples ==")
        for ex in examples[k]:
            safe = json.dumps(ex, ensure_ascii=True)
            print(safe)


if __name__ == "__main__":
    main()
