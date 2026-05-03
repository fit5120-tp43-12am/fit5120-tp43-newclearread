import argparse
import json
import os
import time
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv


SYSTEM_PROMPT = (
    "You are a reading support assistant for students with dyslexia.\n"
    "Your task is to produce a quick summary of dense academic or public-information text.\n"
    "Return only valid JSON with this schema:\n"
    "{\n"
    "  \"main_idea\": \"2 to 3 short sentences\",\n"
    "  \"key_points\": [\"point 1\", \"point 2\", \"point 3\"]\n"
    "}\n"
    "Keep the language clear, simple, and short.\n"
    "Do not add information that is not supported by the source text."
)


def load_jsonl(path: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def write_jsonl(path: str, rows: List[Dict[str, Any]]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def summarize_openai(text: str, model: str) -> Dict[str, Any]:
    # Imported lazily so the script can still be used in offline mode without the SDK.
    from openai import OpenAI  # type: ignore

    client = OpenAI()
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "main_idea": {"type": "string", "minLength": 10},
            "key_points": {
                "type": "array",
                "minItems": 3,
                "maxItems": 3,
                "items": {"type": "string", "minLength": 5},
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
                "schema": schema,
                "strict": True,
            }
        },
    )

    out_text = resp.output_text
    obj = json.loads(out_text)
    obj["key_points"] = obj["key_points"][:3]
    return obj


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", required=True)
    ap.add_argument("--mode", choices=["openai", "offline"], default="offline")
    ap.add_argument("--model", default="gpt-4o-mini")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--outputs-out", default="tech_doc_100_outputs.jsonl")
    ap.add_argument("--sft-out", default="tech_doc_100_sft.jsonl")
    ap.add_argument("--meta-out", default="tech_doc_100_sft.meta.json")
    args = ap.parse_args()

    load_dotenv()

    samples = load_jsonl(args.samples)
    if args.limit is not None:
        samples = samples[: args.limit]

    raw_outputs: List[Dict[str, Any]] = []
    sft_rows: List[Dict[str, Any]] = []

    for i, row in enumerate(samples):
        src_text = row["text"]

        if args.mode == "offline":
            # Placeholder to let you validate plumbing without consuming API calls.
            target = {
                "main_idea": "PLACEHOLDER (run with --mode openai to generate).",
                "key_points": [
                    "PLACEHOLDER point 1.",
                    "PLACEHOLDER point 2.",
                    "PLACEHOLDER point 3.",
                ],
            }
        else:
            if not os.environ.get("OPENAI_API_KEY"):
                raise RuntimeError(
                    "OPENAI_API_KEY is not set. In PowerShell: $env:OPENAI_API_KEY=\"...\""
                )
            target = summarize_openai(src_text, model=args.model)

        raw = {
            "sample_index": row.get("sample_index", i),
            "source_dataset": row.get("source_dataset"),
            "source_row_idx": row.get("source_row_idx"),
            "bucket": row.get("bucket"),
            "word_count": row.get("word_count"),
            "text_sha1": row.get("text_sha1"),
            "target": target,
        }
        raw_outputs.append(raw)

        sft_rows.append(
            {
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": src_text},
                    {"role": "assistant", "content": json.dumps(target, ensure_ascii=False)},
                ]
            }
        )

        if (i + 1) % 10 == 0:
            print(f"[progress] processed {i+1}/{len(samples)}")

    write_jsonl(args.outputs_out, raw_outputs)
    write_jsonl(args.sft_out, sft_rows)

    meta = {
        "created_at_unix": int(time.time()),
        "mode": args.mode,
        "model": args.model if args.mode == "openai" else None,
        "samples_in": args.samples,
        "n": len(samples),
        "outputs_out": args.outputs_out,
        "sft_out": args.sft_out,
        "system_prompt": SYSTEM_PROMPT,
    }
    with open(args.meta_out, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print("Wrote:", args.outputs_out)
    print("Wrote:", args.sft_out)
    print("Wrote:", args.meta_out)


if __name__ == "__main__":
    main()
