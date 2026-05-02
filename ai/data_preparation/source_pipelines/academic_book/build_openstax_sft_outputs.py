import argparse
import json
import os
import random
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv


HERE = os.path.dirname(os.path.abspath(__file__))


SYSTEM_PROMPT = (
    "You are a reading support assistant for students with dyslexia.\n"
    "Your task is to produce a quick summary of dense academic or public-information text.\n"
    "Return only valid JSON with this schema:\n"
    "{\n"
    '  \"main_idea\": \"2 to 3 short sentences\",\n'
    '  \"key_points\": [\"short point 1\", \"short point 2\", \"...\"]\n'
    "}\n"
    "Keep the language clear, simple, and short.\n"
    "Use a short list of key points.\n"
    "Do not add information that is not supported by the source text."
)


def offline_summarize(text: str, rng: random.Random) -> Dict[str, Any]:
    # Simple offline baseline: pick a few short sentences from the beginning.
    # This is only a fallback; quality is not guaranteed.
    words = text.split()
    main = " ".join(words[:40]).strip()
    if len(main) < 20:
        main = (text[:200] or "").strip()
    main_idea = (main[:350] + ("..." if len(main) > 350 else "")).strip()
    key_points = [
        "Focus on the main topic and definitions.",
        "Note the steps, causes, or mechanisms described.",
        "Pay attention to examples and key terms.",
    ]
    rng.shuffle(key_points)
    return {"main_idea": main_idea, "key_points": key_points[:3]}


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
                "minItems": 1,
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

    out_text = resp.output_text
    obj = json.loads(out_text)
    kps = obj.get("key_points")
    if isinstance(kps, list):
        obj["key_points"] = [point for point in kps if isinstance(point, str) and point.strip()]
    return obj


def openai_summarize_with_retry(text: str, model: str, max_retries: int = 6) -> Dict[str, Any]:
    last_err: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        try:
            return openai_summarize(text=text, model=model)
        except Exception as e:
            last_err = e
            # Exponential backoff with cap
            sleep_s = min(30.0, (2.0 ** attempt))
            time.sleep(sleep_s)
    raise last_err  # type: ignore[misc]


def main():
    load_dotenv()

    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["openai", "offline"], default="offline")
    ap.add_argument("--model", type=str, default="gpt-4.1-mini")
    ap.add_argument("--input", type=str, default=os.path.join(HERE, "academic_book_250_samples.jsonl"))
    ap.add_argument("--outputs-path", type=str, default=os.path.join(HERE, "academic_book_250_outputs.jsonl"))
    ap.add_argument("--sft-path", type=str, default=os.path.join(HERE, "academic_book_250_sft.jsonl"))
    ap.add_argument("--meta-path", type=str, default=os.path.join(HERE, "academic_book_250_sft.meta.json"))
    ap.add_argument("--limit", type=int, default=0, help="0 means no limit")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--progress-every", type=int, default=10, help="Print progress every N samples")
    args = ap.parse_args()

    input_path = args.input
    out_outputs_path = args.outputs_path
    out_sft_path = args.sft_path
    out_meta_path = args.meta_path

    rng = random.Random(args.seed)

    n_in = 0
    n_out = 0

    # Stream write so you can see progress and resume manually if interrupted.
    with open(input_path, "r", encoding="utf-8") as fin, open(out_outputs_path, "w", encoding="utf-8") as fout, open(
        out_sft_path, "w", encoding="utf-8"
    ) as fsft:
        for line in fin:
            if not line.strip():
                continue
            n_in += 1
            if args.limit and n_in > args.limit:
                break
            item = json.loads(line)
            text = item["text"]

            if args.mode == "openai":
                summary = openai_summarize_with_retry(text=text, model=args.model)
            else:
                summary = offline_summarize(text=text, rng=rng)

            out_item = {
                "article_id": item.get("article_id"),
                "source_dataset": item.get("source_dataset"),
                "source_split": item.get("source_split"),
                "source_row_idx": item.get("source_row_idx"),
                "word_count": item.get("word_count"),
                "bucket": item.get("bucket"),
                "summary": summary,
            }
            fout.write(json.dumps(out_item, ensure_ascii=False) + "\n")

            sft_row = {
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                    {"role": "assistant", "content": json.dumps(summary, ensure_ascii=False)},
                ]
            }
            fsft.write(json.dumps(sft_row, ensure_ascii=False) + "\n")
            n_out += 1

            if args.progress_every and (n_out % args.progress_every == 0):
                print(f"[progress] wrote {n_out} samples", flush=True)

    meta = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "mode": args.mode,
        "model": args.model if args.mode == "openai" else None,
        "input_path": os.path.abspath(input_path),
        "n_input_read": n_in,
        "n_outputs_written": n_out,
        "output_paths": {
            "outputs_jsonl": os.path.abspath(out_outputs_path),
            "sft_jsonl": os.path.abspath(out_sft_path),
            "meta_json": os.path.abspath(out_meta_path),
        },
        "note": "Assistant content is a JSON string with keys: main_idea, key_points.",
    }
    with open(out_meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"Wrote: {os.path.abspath(out_outputs_path)}")
    print(f"Wrote: {os.path.abspath(out_sft_path)}")
    print(f"Wrote: {os.path.abspath(out_meta_path)}")


if __name__ == "__main__":
    main()
