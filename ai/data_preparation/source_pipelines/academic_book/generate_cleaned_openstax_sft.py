import json
import random
import argparse
import os
import sys
from datetime import datetime, timezone

from build_openstax_sft_outputs import HERE, SYSTEM_PROMPT, offline_summarize, openai_summarize_with_retry


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["openai", "offline"], default="openai")
    ap.add_argument("--model", type=str, default="gpt-4.1-mini")
    ap.add_argument("--input", type=str, default=os.path.join(HERE, "cleaned_samples.jsonl"))
    ap.add_argument("--outputs-path", type=str, default=os.path.join(HERE, "cleaned_outputs.jsonl"))
    ap.add_argument("--sft-path", type=str, default=os.path.join(HERE, "cleaned_sft.jsonl"))
    ap.add_argument("--meta-path", type=str, default=os.path.join(HERE, "cleaned_sft.meta.json"))
    ap.add_argument("--limit", type=int, default=0, help="0 means no limit")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--progress-every", type=int, default=10)
    args = ap.parse_args()

    input_path = os.path.abspath(args.input)
    outputs_path = os.path.abspath(args.outputs_path)
    sft_path = os.path.abspath(args.sft_path)
    meta_path = os.path.abspath(args.meta_path)

    if not os.path.exists(input_path):
        raise SystemExit(f"Missing input file: {input_path}")

    if args.mode == "openai" and not os.getenv("OPENAI_API_KEY"):
        raise SystemExit(
            "OPENAI_API_KEY is not set in this shell. "
            "Set it first, then rerun this command."
        )

    rng = random.Random(args.seed)
    n_in = 0
    n_out = 0

    with open(input_path, "r", encoding="utf-8") as fin, open(outputs_path, "w", encoding="utf-8") as fout, open(
        sft_path, "w", encoding="utf-8"
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

            fout.write(
                json.dumps(
                    {
                        "article_id": item.get("article_id"),
                        "source_dataset": item.get("source_dataset"),
                        "source_split": item.get("source_split"),
                        "source_row_idx": item.get("source_row_idx"),
                        "word_count": item.get("word_count"),
                        "bucket": item.get("bucket"),
                        "summary": summary,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

            fsft.write(
                json.dumps(
                    {
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": text},
                            {"role": "assistant", "content": json.dumps(summary, ensure_ascii=False)},
                        ]
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            n_out += 1
            if args.progress_every and (n_out % args.progress_every == 0):
                print(f"[progress] wrote {n_out} samples", flush=True)

    meta = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": args.mode,
        "model": args.model if args.mode == "openai" else None,
        "input_path": input_path,
        "n_input_read": n_in,
        "n_outputs_written": n_out,
        "output_paths": {
            "outputs_jsonl": outputs_path,
            "sft_jsonl": sft_path,
            "meta_json": meta_path,
        },
        "note": "Assistant content is a JSON string with keys: main_idea, key_points.",
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"Wrote: {outputs_path}")
    print(f"Wrote: {sft_path}")
    print(f"Wrote: {meta_path}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
