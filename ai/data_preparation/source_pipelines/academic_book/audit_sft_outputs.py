import argparse
import json
import re
from collections import Counter, defaultdict


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", type=str, default="academic_book_250_sft.jsonl")
    args = ap.parse_args()

    path = args.path
    n = 0
    flags = Counter()
    examples = defaultdict(list)

    idx_re = re.compile(r"^\s*(http[s]?://\S+\s+)?index\b", re.I)
    toc_re = re.compile(r"\btable of contents\b", re.I)
    review_re = re.compile(r"\breview questions\b|\bproblems\s*&\s*exercises\b|\bsolutions manual\b", re.I)
    authors_re = re.compile(r"\babout the authors\b|\bcontributing authors\b", re.I)
    # List-like: many commas + many page numbers
    many_commas = re.compile(r",")
    page_nums = re.compile(r"\b\d{2,4}\b")

    with open(path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            if not line.strip():
                continue
            n += 1
            obj = json.loads(line)
            user = obj["messages"][1]["content"]

            def add(name: str, val: int = 1):
                flags[name] += 1
                if len(examples[name]) < 5:
                    examples[name].append(
                        {
                            "line_no": line_no,
                            "preview": user[:220].replace("\n", " "),
                            "value": val,
                        }
                    )

            if idx_re.search(user):
                add("index")
            if toc_re.search(user):
                add("toc")
            if review_re.search(user):
                add("review_or_exercises")
            if authors_re.search(user):
                add("authors")

            commas = len(many_commas.findall(user))
            nums = len(page_nums.findall(user))
            if commas >= 80 and nums >= 80:
                add("heavy_list_like", val=commas)

    print({"rows": n, "flag_counts": dict(flags)})
    for k in sorted(examples.keys()):
        print("\n==", k, "examples ==")
        for ex in examples[k]:
            print(json.dumps(ex, ensure_ascii=True))


if __name__ == "__main__":
    main()
