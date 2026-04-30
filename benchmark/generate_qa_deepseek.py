"""
Generate QA annotations from `user_val.jsonl` using the DeepSeek API (OpenAI-compatible).

Default input:  test_data/user_val.jsonl
Default output: test_data/qa_val_deepseek.jsonl

Each output line is a JSON object:
{
  "pair_id": "...",
  "pair_index": 0,
  "questions": [...],
  "reference_answers": [...]
}

The output can be used directly as `--qa-jsonl` for the benchmark script.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import requests
from tqdm import tqdm


SYSTEM_PROMPT = "You are a strict QA generation assistant for comprehension evaluation."

# If you really want a code-level fallback, put a key here.
# IMPORTANT: do NOT commit API keys to a public repo or submission bundle.
# Prefer using the DEEPSEEK_API_KEY environment variable or --api-key.
DEFAULT_DEEPSEEK_API_KEY = "Your DeepSeek API Key"

# Prompt template (kept in English to reduce model drift).
USER_PROMPT_TEMPLATE = """Task:
Generate high-quality question-answer pairs from the given source text.

Requirements:

1. Generate 5–8 questions.
2. Each question MUST be answerable strictly from the source text.
3. Each answer MUST be short (1–5 words or a short phrase).
4. Questions must cover:

   * main idea (at least 1)
   * key facts (at least 2)
   * cause or method (at least 1 if applicable)
5. Do NOT generate yes/no questions.
6. Do NOT use external knowledge.
7. Ensure diversity and avoid redundant questions.
8. Answers must be concise and directly grounded in the text.
9. Maintain strict alignment:

   * questions[i] must match reference_answers[i]

Output format (STRICT JSON):
{{
"questions": [
"...",
"..."
],
"reference_answers": [
"...",
"..."
]
}}

Rules:

* Only output valid JSON
* Do NOT include explanations
* Do NOT include extra fields
* Ensure both lists have the same length

Source Text:
{source_text}
"""


# =============================================================================
# JSONL utilities
# =============================================================================
def iter_jsonl(path: str) -> Any:
    """Yield JSON objects from a JSONL file (one JSON object per non-empty line)."""
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def load_completed_pair_ids(out_path: str) -> Tuple[set, set, int]:
    """
    Read an existing JSONL output file and return:
    - completed_pair_ids: pair_ids that were generated successfully (questions/reference_answers present, no error)
    - seen_pair_ids: pair_ids that appeared in the output (success or failure), used to avoid duplicate error rows
    - n_lines: total number of non-empty lines (for logging/debug)
    """
    completed: set = set()
    seen: set = set()
    n = 0
    if not out_path or not os.path.exists(out_path):
        return completed, seen, 0
    try:
        with open(out_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                n += 1
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if not isinstance(obj, dict):
                    continue
                pid = obj.get("pair_id") or obj.get("record_id")
                if not isinstance(pid, str) or not pid:
                    continue
                seen.add(pid)
                if obj.get("error"):
                    continue
                qs = obj.get("questions")
                rs = obj.get("reference_answers")
                if isinstance(qs, list) and isinstance(rs, list) and qs and rs and len(qs) == len(rs):
                    completed.add(pid)
    except Exception:
        # If reading fails, assume no resume checkpoint.
        return set(), set(), 0
    return completed, seen, n


# =============================================================================
# Model-output parsing and validation
# =============================================================================
def _extract_first_json_object(text: str) -> Optional[dict]:
    """
    Try to extract the first JSON object from model output.
    DeepSeek sometimes wraps output with ```json ...``` or adds a small amount of extra text.
    """
    if not text:
        return None
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*\s*", "", t).strip()
        t = re.sub(r"\s*```$", "", t).strip()
    try:
        obj = json.loads(t)
        return obj if isinstance(obj, dict) else None
    except Exception:
        pass

    # Fallback: find the first {...} fragment that can be parsed as a JSON object.
    start = t.find("{")
    if start < 0:
        return None
    for end in range(len(t), start + 1, -1):
        if t[end - 1] != "}":
            continue
        frag = t[start:end]
        try:
            obj = json.loads(frag)
            return obj if isinstance(obj, dict) else None
        except Exception:
            continue
    return None


def _ensure_list_str(x: Any) -> List[str]:
    """Best-effort normalization: coerce a list-like object to list[str]."""
    if not isinstance(x, list):
        return []
    out: List[str] = []
    for v in x:
        s = str(v).strip()
        if s:
            out.append(s)
    return out


def _count_words_simple(ans: str) -> int:
    # Approximate word count: split on whitespace and ignore repeated spaces.
    return len([w for w in re.split(r"\s+", (ans or "").strip()) if w])


def truncate_answers_words(obj: dict, *, max_words: int) -> dict:
    """
    Fallback: if answers are only slightly too long, truncate to the first `max_words` words,
    keeping the overall JSON structure intact.

    Note: this is only used in repair mode to avoid repeatedly emitting errors.
    """
    qs = _ensure_list_str(obj.get("questions"))
    rs = _ensure_list_str(obj.get("reference_answers"))
    out_rs: List[str] = []
    for a in rs:
        words = [w for w in re.split(r"\s+", (a or "").strip()) if w]
        out_rs.append(" ".join(words[: int(max_words)]).strip())
    return {"questions": qs, "reference_answers": out_rs}


def validate_qa(obj: dict, *, max_answer_words: int = 8) -> Tuple[bool, str, Optional[dict]]:
    """
    Validate and normalize the model output:
    - questions/reference_answers exist and have the same length
    - number of items is in [5, 8]
    - each answer is short enough (default <= 8 words; set to 5 for a strict 1–5 words requirement)
    """
    if not isinstance(obj, dict):
        return False, "not a json object", None

    qs = _ensure_list_str(obj.get("questions"))
    rs = _ensure_list_str(obj.get("reference_answers"))
    if not qs or not rs:
        return False, "missing questions/reference_answers", None
    if len(qs) != len(rs):
        return False, "length mismatch", None
    if not (5 <= len(qs) <= 8):
        return False, "question count not in [5,8]", None
    for a in rs:
        if _count_words_simple(a) > int(max_answer_words):
            return False, "answer too long", None

    norm = {"questions": qs, "reference_answers": rs}
    return True, "ok", norm


# =============================================================================
# DeepSeek API client (OpenAI-compatible)
# =============================================================================
def deepseek_chat_completion(
    *,
    api_key: str,
    base_url: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int,
    timeout_s: int,
) -> str:
    url = base_url.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "temperature": temperature,
        "max_tokens": int(max_tokens),
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    r = requests.post(url, headers=headers, json=payload, timeout=timeout_s)
    r.raise_for_status()
    data = r.json()
    return (
        data.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
    )


# =============================================================================
# Output file helpers (used by repair mode)
# =============================================================================
def load_latest_rows_by_pair_id(out_path: str) -> Tuple[Dict[str, dict], List[str]]:
    """
    Read `out_path` (JSONL) and return:
    - latest: pair_id -> the last record (success or error) for that pair_id
    - order: pair_ids in the order of first appearance, used to keep stable ordering when rewriting
    """
    latest: Dict[str, dict] = {}
    order: List[str] = []
    if not out_path or not os.path.exists(out_path):
        return latest, order
    with open(out_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if not isinstance(obj, dict):
                continue
            pid = obj.get("pair_id") or obj.get("record_id")
            if not isinstance(pid, str) or not pid:
                continue
            if pid not in latest:
                order.append(pid)
            latest[pid] = obj
    return latest, order


# =============================================================================
# Prompt builders for repair/shorten flows
# =============================================================================
def build_repair_prompt(source_text: str) -> str:
    """
    Repair prompt for the "answer too long" case: enforce answers to be 1–5 words.
    """
    return (
        USER_PROMPT_TEMPLATE.format(source_text=source_text)
        + "\n\n"
        + "Extra strict constraints:\n"
        + "- Generate exactly 5 questions.\n"
        + "- Every reference_answers item MUST be 1–5 words (maximum 5 words).\n"
        + "- Prefer 1–3 words when possible.\n"
        + "- If an answer would be longer, rewrite it to a shorter noun phrase strictly grounded in the text.\n"
        + "- Prefer named entities, numbers, dates, short terms.\n"
        + "- Do NOT use punctuation-heavy answers.\n"
    )


def build_shorten_prompt(*, source_text: str, qa_obj: dict) -> str:
    """
    If the model output is valid JSON but answers are too long, do a second request to
    shorten ONLY the answers to avoid question drift.
    """
    qs = _ensure_list_str(qa_obj.get("questions"))
    rs = _ensure_list_str(qa_obj.get("reference_answers"))
    payload = json.dumps({"questions": qs, "reference_answers": rs}, ensure_ascii=False)
    return (
        "Task:\n"
        "You will be given a source text and an existing QA JSON.\n"
        "Shorten ONLY the reference_answers so that EVERY answer is 1–5 words.\n"
        "Do NOT change the questions.\n"
        "Do NOT add or remove items.\n"
        "Do NOT use external knowledge. Answers must remain strictly grounded in the source text.\n"
        "\n"
        "Output format (STRICT JSON):\n"
        '{\n  "questions": [...],\n  "reference_answers": [...]\n}\n'
        "\n"
        "Source Text:\n"
        f"{source_text}\n"
        "\n"
        "Existing QA JSON:\n"
        f"{payload}\n"
    )


# =============================================================================
# Main pipeline
# =============================================================================
def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--in", dest="in_path", default=str(r"test_data\user_val.jsonl"))
    p.add_argument("--out", dest="out_path", default=str(r"test_data\qa_val_deepseek.jsonl"))
    p.add_argument("--limit", type=int, default=0, help="Only generate the first N records (0 = all)")
    p.add_argument("--start", type=int, default=0, help="Skip the first N records (by line order)")
    p.add_argument("--model", type=str, default="deepseek-chat")
    p.add_argument("--base-url", type=str, default=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"))
    p.add_argument("--api-key", type=str, default=os.environ.get("DEEPSEEK_API_KEY", ""))
    p.add_argument("--temperature", type=float, default=0.2)
    p.add_argument("--max-tokens", type=int, default=800, help="Max output tokens per request (prevents verbose replies)")
    p.add_argument(
        "--max-answer-words",
        type=int,
        default=8,
        help="Max words per answer for validate_qa (default 8; set to 5 to enforce strict 1–5 words)",
    )
    p.add_argument("--max-retries", type=int, default=5)
    p.add_argument("--timeout-s", type=int, default=90)
    p.add_argument("--sleep-s", type=float, default=0.0, help="Extra sleep seconds after each request (rate limiting)")
    p.add_argument(
        "--resume",
        action="store_true",
        help="Resume mode: if output exists, skip already-completed pair_ids and append new rows",
    )
    p.add_argument(
        "--no-resume",
        action="store_true",
        help="Disable resume: always overwrite the output and regenerate from scratch",
    )
    p.add_argument(
        "--repair-answer-too-long",
        action="store_true",
        help=(
            "Repair mode: only rerun rows in the output where error == 'answer too long'; "
            "leave successful rows untouched; rewrite output to remove duplicate pair_id lines"
        ),
    )
    args = p.parse_args(argv)

    # API key resolution: prefer explicit/env; only then fall back to the code-level default.
    if not args.api_key:
        args.api_key = DEFAULT_DEEPSEEK_API_KEY
    if not args.api_key:
        raise SystemExit("Missing DEEPSEEK_API_KEY. Set the environment variable or pass --api-key.")

    # Load input into memory for stable ordering and for resume/repair bookkeeping.
    rows = list(iter_jsonl(args.in_path))
    if args.start:
        rows = rows[args.start :]
    if args.limit:
        rows = rows[: args.limit]

    # Ensure output directory exists (e.g., test_data/).
    os.makedirs(os.path.dirname(args.out_path) or ".", exist_ok=True)

    # Repair mode: only rerun rows marked as "answer too long" and rewrite the output (no append).
    if args.repair_answer_too_long:
        latest_out, out_order = load_latest_rows_by_pair_id(args.out_path)
        in_by_pid: Dict[str, dict] = {}
        in_order: List[str] = []
        for rec in rows:
            pid = rec.get("pair_id") or rec.get("record_id")
            if isinstance(pid, str) and pid and pid not in in_by_pid:
                in_by_pid[pid] = rec
                in_order.append(pid)

        repair_targets: List[str] = []
        for pid, obj in latest_out.items():
            if obj.get("error") == "answer too long":
                if pid in in_by_pid:
                    repair_targets.append(pid)

        # We intentionally only repair explicitly marked rows (error == "answer too long").
        max_answer_words = 5  # strict requirement: 1–5 words
        rewritten: Dict[str, dict] = dict(latest_out)

        for pid in tqdm(repair_targets, desc="Repairing answer-too-long"):
            rec = in_by_pid[pid]
            pair_index = rec.get("pair_index")
            source_text = rec.get("text", "")
            if not isinstance(source_text, str) or not source_text.strip():
                continue

            user_prompt = build_repair_prompt(source_text)
            last_err = ""
            qa_obj: Optional[dict] = None

            # Repair strategy (in order):
            # 1) Re-generate with extra-strict constraints.
            # 2) If only answers are too long, ask the model to shorten answers without changing questions.
            # 3) As a last resort, truncate answers locally to guarantee progress.
            for attempt in range(int(args.max_retries)):
                try:
                    content = deepseek_chat_completion(
                        api_key=args.api_key,
                        base_url=args.base_url,
                        model=args.model,
                        system_prompt=SYSTEM_PROMPT,
                        user_prompt=user_prompt,
                        temperature=float(min(float(args.temperature), 0.1)),
                        max_tokens=int(min(int(args.max_tokens), 600)),
                        timeout_s=int(args.timeout_s),
                    )
                    parsed = _extract_first_json_object(content)
                    if parsed is None:
                        last_err = "cannot parse json"
                        raise ValueError(last_err)
                    ok, reason, norm = validate_qa(parsed, max_answer_words=max_answer_words)
                    if not ok or norm is None:
                        # If only answers are too long, try shortening answers to avoid question drift.
                        if reason == "answer too long":
                            shorten_prompt = build_shorten_prompt(source_text=source_text, qa_obj=parsed)
                            content2 = deepseek_chat_completion(
                                api_key=args.api_key,
                                base_url=args.base_url,
                                model=args.model,
                                system_prompt=SYSTEM_PROMPT,
                                user_prompt=shorten_prompt,
                                temperature=0.0,
                                max_tokens=400,
                                timeout_s=int(args.timeout_s),
                            )
                            parsed2 = _extract_first_json_object(content2)
                            if parsed2 is not None:
                                ok2, reason2, norm2 = validate_qa(parsed2, max_answer_words=max_answer_words)
                                if ok2 and norm2 is not None:
                                    qa_obj = norm2
                                    break
                            # Last resort: truncate answers locally to 5 words to avoid repeated failures.
                            truncated = truncate_answers_words(parsed, max_words=max_answer_words)
                            ok3, reason3, norm3 = validate_qa(truncated, max_answer_words=max_answer_words)
                            if ok3 and norm3 is not None:
                                qa_obj = norm3
                                break
                            last_err = reason
                            raise ValueError(reason)
                        last_err = reason
                        raise ValueError(reason)
                    qa_obj = norm
                    break
                except Exception as e:  # noqa: BLE001
                    last_err = str(e)
                    backoff = min(30.0, (2**attempt) + random.random())
                    time.sleep(backoff)

            if qa_obj is None:
                rewritten[pid] = {
                    "pair_id": pid,
                    "pair_index": pair_index,
                    "error": last_err or "answer too long",
                }
                continue

            rewritten[pid] = {
                "pair_id": pid,
                "pair_index": pair_index,
                "questions": qa_obj["questions"],
                "reference_answers": qa_obj["reference_answers"],
            }

        # Rewrite output: prioritize the input order; append any remaining existing rows at the end.
        final_order: List[str] = []
        seen: set = set()
        for pid in in_order:
            if pid in rewritten:
                final_order.append(pid)
                seen.add(pid)
        for pid in out_order:
            if pid not in seen and pid in rewritten:
                final_order.append(pid)
                seen.add(pid)

        tmp_path = args.out_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as out_f:
            for pid in final_order:
                out_f.write(json.dumps(rewritten[pid], ensure_ascii=False) + "\n")
        os.replace(tmp_path, args.out_path)
        return 0

    # Enable resume by default (better for batch API calls); use --no-resume to force overwrite.
    if not args.resume and not args.no_resume:
        args.resume = True

    completed_pair_ids: set = set()
    seen_pair_ids: set = set()
    if args.resume and not args.no_resume:
        # completed_pair_ids: skip work on resume
        # seen_pair_ids: avoid re-appending the same error row for a given pair_id
        completed_pair_ids, seen_pair_ids, _ = load_completed_pair_ids(args.out_path)

    out_mode = "a" if (args.resume and not args.no_resume and os.path.exists(args.out_path)) else "w"

    with open(args.out_path, out_mode, encoding="utf-8") as out_f:
        for rec in tqdm(rows, desc="Generating QA"):
            pair_id = rec.get("pair_id") or rec.get("record_id")
            pair_index = rec.get("pair_index")
            source_text = rec.get("text", "")
            if not isinstance(source_text, str) or not source_text.strip():
                continue
            if args.resume and not args.no_resume and isinstance(pair_id, str) and pair_id in completed_pair_ids:
                continue

            user_prompt = USER_PROMPT_TEMPLATE.format(source_text=source_text)

            last_err = ""
            qa_obj: Optional[dict] = None
            for attempt in range(args.max_retries):
                try:
                    content = deepseek_chat_completion(
                        api_key=args.api_key,
                        base_url=args.base_url,
                        model=args.model,
                        system_prompt=SYSTEM_PROMPT,
                        user_prompt=user_prompt,
                        temperature=float(args.temperature),
                        max_tokens=int(args.max_tokens),
                        timeout_s=int(args.timeout_s),
                    )
                    parsed = _extract_first_json_object(content)
                    if parsed is None:
                        last_err = "cannot parse json"
                        raise ValueError(last_err)
                    ok, reason, norm = validate_qa(parsed, max_answer_words=int(args.max_answer_words))
                    if not ok or norm is None:
                        last_err = reason
                        raise ValueError(reason)
                    qa_obj = norm
                    break
                except Exception as e:  # noqa: BLE001
                    last_err = str(e)
                    # Exponential backoff with jitter.
                    backoff = min(30.0, (2**attempt) + random.random())
                    time.sleep(backoff)

            if qa_obj is None:
                # Emit an error row to help identify pairs that need manual inspection.
                # In resume mode, avoid repeatedly appending the same error for a given pair_id.
                if args.resume and not args.no_resume and isinstance(pair_id, str) and pair_id in seen_pair_ids:
                    continue
                out_f.write(
                    json.dumps(
                        {
                            "pair_id": pair_id,
                            "pair_index": pair_index,
                            "error": last_err,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                out_f.flush()
                if isinstance(pair_id, str) and pair_id:
                    seen_pair_ids.add(pair_id)
                continue

            out_row = {
                "pair_id": pair_id,
                "pair_index": pair_index,
                "questions": qa_obj["questions"],
                "reference_answers": qa_obj["reference_answers"],
            }
            out_f.write(json.dumps(out_row, ensure_ascii=False) + "\n")
            out_f.flush()
            if args.resume and not args.no_resume and isinstance(pair_id, str) and pair_id:
                completed_pair_ids.add(pair_id)
                seen_pair_ids.add(pair_id)
            if args.sleep_s:
                time.sleep(float(args.sleep_s))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

