import json
import random
import re
from collections import Counter, defaultdict


def compile_patterns():
    return {
        "index": re.compile(r"(^|\n)\s*(https?://\S+\s+)?index\b", re.I),
        "glossary": re.compile(r"(^|\n)\s*(https?://\S+\s+)?glossary\b", re.I),
        "references": re.compile(r"(^|\n)\s*(https?://\S+\s+)?references\b", re.I),
        "bibliography": re.compile(r"\bbibliography\b", re.I),
        "table_of_contents": re.compile(r"\btable of contents\b", re.I),
        "answer_key": re.compile(r"\banswer key\b|\banswers to\b", re.I),
        "review_questions": re.compile(r"\breview questions\b", re.I),
        "problems_exercises": re.compile(r"\bproblems\s*&\s*exercises\b|\bproblems and exercises\b", re.I),
        "end_of_chapter": re.compile(r"\bend-of-chapter\b|\bend of chapter\b", re.I),
        "about_authors": re.compile(r"\babout the authors\b|\bcontributing authors\b", re.I),
        "copyrightish": re.compile(r"\ball rights reserved\b|©|\bcopyright\b", re.I),
    }


def is_mcq_heavy(text: str) -> bool:
    return len(re.findall(r"\b[a-d]\.\s", text)) >= 6


def is_list_like(text: str) -> bool:
    commas = text.count(",")
    nums = len(re.findall(r"\b\d{2,4}\b", text))
    # heuristic: index-like pages have tons of comma-separated entries and page numbers
    return commas >= 120 and nums >= 120


def is_question_heavy(text: str) -> bool:
    return text.count("?") >= 4


def main():
    path = "academic_book_250_sft.jsonl"
    pats = compile_patterns()
    n = 0
    flags = Counter()
    examples = defaultdict(list)

    user_texts = []
    with open(path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            if not line.strip():
                continue
            obj = json.loads(line)
            user = obj["messages"][1]["content"]
            n += 1
            user_texts.append((line_no, user))

            def add(name: str, extra: int | None = None):
                flags[name] += 1
                if len(examples[name]) < 5:
                    ex = {
                        "line_no": line_no,
                        "preview": user[:240].replace("\n", " "),
                    }
                    if extra is not None:
                        ex["value"] = extra
                    examples[name].append(ex)

            for name, pat in pats.items():
                if pat.search(user):
                    add(name)

            if is_mcq_heavy(user):
                add("mcq_heavy", extra=len(re.findall(r"\b[a-d]\.\s", user)))
            if is_question_heavy(user):
                add("question_heavy", extra=user.count("?"))
            if is_list_like(user):
                add("list_like", extra=user.count(","))

    print(json.dumps({"rows": n, "flag_counts": dict(flags)}, ensure_ascii=True))
    for k in sorted(examples.keys()):
        print("\n==", k, "examples ==")
        for ex in examples[k]:
            print(json.dumps(ex, ensure_ascii=True))

    # Random human spot-check previews
    rng = random.Random(42)
    picks = rng.sample(user_texts, k=min(20, len(user_texts)))
    print("\n== random_20_previews ==")
    for line_no, user in sorted(picks, key=lambda x: x[0]):
        safe = user[:180].replace("\n", " ")
        print(json.dumps({"line_no": line_no, "preview": safe}, ensure_ascii=True))


if __name__ == "__main__":
    main()
