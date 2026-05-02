import argparse
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Sequence, Tuple

from datasets import load_dataset

from extract_cleaned_openstax_samples import (
    BUCKET_CONFIG,
    _best_window_for_bucket,
    _clean_sentences,
    _math_symbol_count,
    _module_looks_bad,
    _sha1_text,
    _split_sentences,
    iter_openstax_modules,
)


HERE = os.path.dirname(os.path.abspath(__file__))


def read_jsonl(path: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: str, rows: Sequence[Dict[str, Any]]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def parse_rows(spec: str) -> List[int]:
    rows = sorted({int(x.strip()) for x in spec.split(",") if x.strip()})
    if not rows:
        raise SystemExit("No rows were provided.")
    if any(r <= 0 for r in rows):
        raise SystemExit("Rows must be 1-based positive integers.")
    return rows


def quality_key(text: str, wc: int, bucket: str) -> Tuple[int, int, int, int]:
    target = BUCKET_CONFIG[bucket][2]
    sent_count = len(_split_sentences(text))
    return (
        sum(ch.isdigit() for ch in text),
        _math_symbol_count(text),
        abs(wc - target),
        -sent_count,
    )


def build_sample(module: Dict[str, Any], text: str, wc: int, bucket: str) -> Dict[str, Any]:
    text_hash = _sha1_text(text)
    return {
        "source_dataset": "crumb/openstax-text",
        "source_split": "train",
        "source_row_idx": module["source_row_idx"],
        "source_row_idx_end": module["source_row_idx_end"],
        "article_id": (
            f"crumb/openstax-text|split=train|module={module['module']}|"
            f"rows={module['source_row_idx']}-{module['source_row_idx_end']}"
        ),
        "title": None,
        "book": None,
        "chapter": None,
        "section": None,
        "url": None,
        "word_count": wc,
        "bucket": bucket,
        "text": text,
        "text_sha1": text_hash,
    }


def replace_samples(
    current_rows: List[Dict[str, Any]],
    replace_rows: Sequence[int],
    max_modules: int,
    progress_every: int,
    progress_rows_every: int,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    replace_set = set(replace_rows)
    retained_hashes = {
        row.get("text_sha1")
        for idx, row in enumerate(current_rows, start=1)
        if idx not in replace_set and row.get("text_sha1")
    }
    replace_hashes = {
        row.get("text_sha1")
        for idx, row in enumerate(current_rows, start=1)
        if idx in replace_set and row.get("text_sha1")
    }
    retained_article_ids = {
        row.get("article_id")
        for idx, row in enumerate(current_rows, start=1)
        if idx not in replace_set and row.get("article_id")
    }
    replace_article_ids = {
        row.get("article_id")
        for idx, row in enumerate(current_rows, start=1)
        if idx in replace_set and row.get("article_id")
    }

    need_by_bucket = {"short": 0, "medium": 0, "long": 0}
    for row_no in replace_rows:
        bucket = current_rows[row_no - 1]["bucket"]
        need_by_bucket[bucket] += 1

    pool_target = {bucket: (need + 8) if need else 0 for bucket, need in need_by_bucket.items()}
    candidate_pools: Dict[str, List[Tuple[Tuple[int, int, int, int], Dict[str, Any]]]] = {
        "short": [],
        "medium": [],
        "long": [],
    }
    # Exclude both retained rows and the rows being replaced so a "repair" cannot silently
    # select the same bad text again.
    candidate_hashes = set(retained_hashes) | set(replace_hashes)
    candidate_article_ids = set(retained_article_ids) | set(replace_article_ids)
    scanned_modules = 0

    ds = load_dataset("crumb/openstax-text", split="train", streaming=True)
    for module in iter_openstax_modules(ds, progress_rows_every=progress_rows_every):
        scanned_modules += 1
        if max_modules and scanned_modules > max_modules:
            break
        if progress_every and scanned_modules % progress_every == 0:
            sizes = {bucket: len(candidate_pools[bucket]) for bucket in candidate_pools}
            print(f"[repair-progress] modules={scanned_modules} candidate_pools={sizes}", flush=True)

        if _module_looks_bad(module["lines"]):
            continue
        sentences = _clean_sentences(module["lines"])
        if not sentences:
            continue

        for bucket, need in need_by_bucket.items():
            if need == 0 or len(candidate_pools[bucket]) >= pool_target[bucket]:
                continue
            candidate = _best_window_for_bucket(sentences, bucket)
            if not candidate:
                continue
            text, wc = candidate
            text_hash = _sha1_text(text)
            if text_hash in candidate_hashes:
                continue
            sample = build_sample(module, text, wc, bucket)
            if sample["article_id"] in candidate_article_ids:
                continue
            candidate_pools[bucket].append((quality_key(text, wc, bucket), sample))
            candidate_hashes.add(text_hash)
            candidate_article_ids.add(sample["article_id"])

        if all(
            len(candidate_pools[bucket]) >= pool_target[bucket]
            for bucket, need in need_by_bucket.items()
            if need > 0
        ):
            break

    for bucket, need in need_by_bucket.items():
        if len(candidate_pools[bucket]) < need:
            raise SystemExit(
                f"Not enough replacement candidates for bucket '{bucket}'. "
                f"Need {need}, found {len(candidate_pools[bucket])}."
            )
        candidate_pools[bucket].sort(key=lambda item: item[0])

    next_index = {"short": 0, "medium": 0, "long": 0}
    new_rows = [dict(row) for row in current_rows]
    selected_hashes = set()
    selected_article_ids = set()
    replacements: List[Dict[str, Any]] = []

    for row_no in replace_rows:
        idx = row_no - 1
        bucket = current_rows[idx]["bucket"]
        pool = candidate_pools[bucket]
        while next_index[bucket] < len(pool) and (
            pool[next_index[bucket]][1]["text_sha1"] in selected_hashes
            or pool[next_index[bucket]][1]["article_id"] in selected_article_ids
        ):
            next_index[bucket] += 1
        if next_index[bucket] >= len(pool):
            raise SystemExit(f"Ran out of replacement candidates for bucket '{bucket}'.")
        replacement = dict(pool[next_index[bucket]][1])
        next_index[bucket] += 1
        selected_hashes.add(replacement["text_sha1"])
        selected_article_ids.add(replacement["article_id"])
        new_rows[idx] = replacement
        replacements.append(
            {
                "row": row_no,
                "bucket": bucket,
                "word_count": replacement["word_count"],
                "article_id": replacement["article_id"],
            }
        )

    seen_hashes = set()
    bucket_counts = {"short": 0, "medium": 0, "long": 0}
    for row in new_rows:
        bucket_counts[row["bucket"]] += 1
        text_hash = row["text_sha1"]
        if text_hash in seen_hashes:
            raise SystemExit(f"Duplicate text detected after repair: {text_hash}")
        seen_hashes.add(text_hash)

    meta_updates = {
        "repaired_at": datetime.utcnow().isoformat() + "Z",
        "repair_generator": os.path.basename(__file__),
        "repair_rows": list(replace_rows),
        "repair_counts_by_bucket": need_by_bucket,
        "candidate_pool_sizes": {bucket: len(candidate_pools[bucket]) for bucket in candidate_pools},
        "scanned_modules_for_repair": scanned_modules,
        "selected_counts": bucket_counts,
        "replacements": replacements,
    }
    return new_rows, meta_updates


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--replace-rows", required=True, help="Comma-separated 1-based row numbers to replace.")
    ap.add_argument("--input-samples", default=os.path.join(HERE, "cleaned_samples.jsonl"))
    ap.add_argument("--meta-path", default=os.path.join(HERE, "cleaned_samples.meta.json"))
    ap.add_argument("--max-modules", type=int, default=40000)
    ap.add_argument("--progress-every", type=int, default=500)
    ap.add_argument("--progress-rows-every", type=int, default=200000)
    args = ap.parse_args()

    replace_rows = parse_rows(args.replace_rows)
    samples = read_jsonl(args.input_samples)
    if len(samples) != 250:
        raise SystemExit(f"Expected 250 rows in {args.input_samples}, found {len(samples)}.")
    if max(replace_rows) > len(samples):
        raise SystemExit("A requested row is outside the input file length.")

    repaired_rows, meta_updates = replace_samples(
        current_rows=samples,
        replace_rows=replace_rows,
        max_modules=args.max_modules,
        progress_every=args.progress_every,
        progress_rows_every=args.progress_rows_every,
    )

    tmp_samples = args.input_samples + ".tmp"
    write_jsonl(tmp_samples, repaired_rows)
    os.replace(tmp_samples, args.input_samples)

    if os.path.exists(args.meta_path):
        with open(args.meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
    else:
        meta = {}
    repair_history = list(meta.get("repair_history") or [])
    repair_history.append(meta_updates)
    meta.update(meta_updates)
    meta["repair_history"] = repair_history
    meta.setdefault("outputs", {})
    meta["outputs"]["samples_jsonl"] = os.path.abspath(args.input_samples)
    meta["outputs"]["meta_json"] = os.path.abspath(args.meta_path)
    meta["outputs"]["cleaned_outputs_jsonl"] = None
    meta["outputs"]["cleaned_sft_jsonl"] = None
    meta["outputs"]["cleaned_sft_meta_json"] = None
    meta["generation_status"] = "samples_repaired_api_regeneration_required"

    tmp_meta = args.meta_path + ".tmp"
    with open(tmp_meta, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    os.replace(tmp_meta, args.meta_path)

    print(f"Repaired rows: {replace_rows}")
    print(f"Wrote: {os.path.abspath(args.input_samples)}")
    print(f"Wrote: {os.path.abspath(args.meta_path)}")


if __name__ == "__main__":
    main()
