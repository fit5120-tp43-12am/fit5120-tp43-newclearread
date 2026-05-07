import argparse
import hashlib
import json
import os
import random
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from datasets import load_dataset


HERE = os.path.dirname(os.path.abspath(__file__))


SYSTEM_PROMPT = (
    "You are a reading support assistant for students with dyslexia.\n"
    "Your task is to produce a quick summary of dense academic or public-information text.\n"
    "Return only valid JSON with this schema:\n"
    "{\n"
    '  \"main_idea\": \"2 to 3 short sentences\",\n'
    '  \"key_points\": [\"point 1\", \"point 2\", \"point 3\"]\n'
    "}\n"
    "Keep the language clear, simple, and short.\n"
    "Do not add information that is not supported by the source text."
)


CNX_URL_RE = re.compile(r"https?://cnx\.org/content/(col\d+/\d+\.\d+)", re.I)


def norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


def sha1_text(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def bucket_for_wc(wc: int) -> Optional[str]:
    if 250 <= wc <= 499:
        return "short"
    if 500 <= wc <= 800:
        return "medium"
    if 801 <= wc <= 1200:
        return "long"
    return None


def looks_bad(text: str) -> bool:
    t = text.lower()
    if "index " in t[:50] or t.strip().startswith("index"):
        return True
    if " table of contents" in t or "table of contents" in t[:200]:
        return True
    if "review questions" in t or "problems & exercises" in t or "problems and exercises" in t:
        return True
    if "about the authors" in t or "contributing authors" in t:
        return True
    # MCQ / question heavy
    if len(re.findall(r"\b[a-d]\.\s", text)) >= 6:
        return True
    if text.count("?") >= 4:
        return True
    # index/list-like heuristic
    commas = text.count(",")
    nums = len(re.findall(r"\b\d{2,4}\b", text))
    if commas >= 120 and nums >= 120:
        return True
    return False


def pick_window(words: List[str], target_len: int, rng: random.Random) -> str:
    if len(words) <= target_len:
        return " ".join(words)
    start = rng.randint(0, max(0, len(words) - target_len))
    return " ".join(words[start : start + target_len])


def iter_modules(stream_ds):
    current_module = None
    current_lines: List[str] = []
    start_row = None
    end_row = None

    def flush():
        nonlocal current_module, current_lines, start_row, end_row
        if not current_module:
            current_module = None
            current_lines = []
            start_row = None
            end_row = None
            return None
        raw = "\n".join(current_lines)
        current = {
            "module": current_module,
            "source_row_idx": start_row,
            "source_row_idx_end": end_row,
            "text": norm_ws(raw),
        }
        current_module = None
        current_lines = []
        start_row = None
        end_row = None
        return current

    for row_idx, row in enumerate(stream_ds):
        line = row.get("text")
        if not isinstance(line, str):
            continue
        s = line.strip()
        if not s:
            continue
        m = CNX_URL_RE.search(s)
        if m:
            out = flush()
            if out:
                yield out
            current_module = m.group(1).lower()
            current_lines = [s]
            start_row = row_idx
            end_row = row_idx
            continue
        if current_module:
            current_lines.append(s)
            end_row = row_idx

    out = flush()
    if out:
        yield out


def openai_summarize(text: str, model: str) -> Dict[str, Any]:
    from openai import OpenAI

    client = OpenAI()
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "main_idea": {"type": "string"},
            "key_points": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 3,
                "maxItems": 3,
            },
        },
        "required": ["main_idea", "key_points"],
    }
    resp = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "dyslexia_summary",
                "strict": True,
                "schema": schema,
            }
        },
    )
    obj = json.loads(resp.output_text)
    obj["key_points"] = obj["key_points"][:3]
    return obj


def openai_summarize_with_retry(text: str, model: str, max_retries: int = 6) -> Dict[str, Any]:
    last: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        try:
            return openai_summarize(text=text, model=model)
        except Exception as e:
            last = e
            time.sleep(min(30.0, 2.0**attempt))
    raise last  # type: ignore[misc]


def read_jsonl(path: str) -> List[Dict[str, Any]]:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: str, rows: List[Dict[str, Any]]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bad-lines", type=str, required=True, help="Comma-separated 1-based line numbers, e.g. 191,201")
    ap.add_argument("--bucket", type=str, default="medium", choices=["short", "medium", "long"])
    ap.add_argument("--model", type=str, default="gpt-4.1-mini")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--max-modules-scan", type=int, default=20000)
    args = ap.parse_args()

    bad_lines = [int(x.strip()) for x in args.bad_lines.split(",") if x.strip()]
    bad_lines = sorted(set(bad_lines))

    samples_path = os.path.join(HERE, "academic_book_250_samples.jsonl")
    outputs_path = os.path.join(HERE, "academic_book_250_outputs.jsonl")
    sft_path = os.path.join(HERE, "academic_book_250_sft.jsonl")

    samples = read_jsonl(samples_path)
    outputs = read_jsonl(outputs_path)
    sft = read_jsonl(sft_path)
    if not (len(samples) == len(outputs) == len(sft) == 250):
        raise SystemExit("Expected all files to have 250 lines: samples/outputs/sft.")

    used_sha1 = {r.get("text_sha1") for r in samples if r.get("text_sha1")}
    rng = random.Random(args.seed)

    needed = len(bad_lines)
    replacements: List[Tuple[int, Dict[str, Any]]] = []

    ds = load_dataset("crumb/openstax-text", split="train", streaming=True)
    scanned = 0
    for mod in iter_modules(ds):
        scanned += 1
        if args.max_modules_scan and scanned > args.max_modules_scan:
            break
        text = mod["text"]
        if not text or looks_bad(text):
            continue
        words = text.split()
        # we only need medium replacements here
        if args.bucket == "medium":
            if len(words) < 500:
                continue
            win = pick_window(words, target_len=700, rng=rng)
        elif args.bucket == "short":
            if len(words) < 250:
                continue
            win = pick_window(words, target_len=350, rng=rng)
        else:
            if len(words) < 801:
                continue
            win = pick_window(words, target_len=1000, rng=rng)

        win = norm_ws(win)
        wc = len(win.split())
        if bucket_for_wc(wc) != args.bucket:
            continue
        th = sha1_text(win)
        if th in used_sha1:
            continue
        if looks_bad(win):
            continue

        sample_row = {
            "source_dataset": "crumb/openstax-text",
            "source_split": "train",
            "source_row_idx": mod["source_row_idx"],
            "source_row_idx_end": mod["source_row_idx_end"],
            "article_id": f"crumb/openstax-text|split=train|module={mod['module']}|rows={mod['source_row_idx']}-{mod['source_row_idx_end']}",
            "title": None,
            "book": None,
            "chapter": None,
            "section": None,
            "url": None,
            "word_count": wc,
            "bucket": args.bucket,
            "text": win,
            "text_sha1": th,
        }
        replacements.append((len(replacements), sample_row))
        used_sha1.add(th)
        if len(replacements) >= needed:
            break

    if len(replacements) < needed:
        raise SystemExit(f"Could not find enough replacements. Needed {needed}, found {len(replacements)}.")

    # Apply replacements: align by line number (1-based index)
    for i, line_no in enumerate(bad_lines):
        idx = line_no - 1
        new_sample = replacements[i][1]
        summary = openai_summarize_with_retry(new_sample["text"], model=args.model)

        samples[idx] = new_sample
        outputs[idx] = {
            "article_id": new_sample["article_id"],
            "source_dataset": new_sample["source_dataset"],
            "source_split": new_sample["source_split"],
            "source_row_idx": new_sample["source_row_idx"],
            "word_count": new_sample["word_count"],
            "bucket": new_sample["bucket"],
            "summary": summary,
        }
        sft[idx] = {
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": new_sample["text"]},
                {"role": "assistant", "content": json.dumps(summary, ensure_ascii=False)},
            ]
        }
        print(f"Replaced line {line_no} with {new_sample['article_id']}")

    write_jsonl(samples_path, samples)
    write_jsonl(outputs_path, outputs)
    write_jsonl(sft_path, sft)
    print("Done. Re-run: py -3 validate_sft_jsonl.py --path academic_book_250_sft.jsonl --expected-lines 250")
    print("And: py -3 audit_sft_outputs.py  (should show 0 index/list_like)")


if __name__ == "__main__":
    main()
