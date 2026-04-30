"""
Benchmark metrics for summarization outputs (assistant_val.jsonl).

This script computes a set of lightweight, dependency-minimal metrics such as:
- Readability (Flesch Reading Ease, FRE)
- Sentence length proxies
- Heuristic syntax complexity
- Word frequency (rarity) score based on user/source corpus

It also supports Method C (recommended): semantic similarity via embeddings:
- Summary-vs-source cosine similarity (`--semantic-sim`)
- QA-based semantic coverage using pre-generated QA (`--qa-semantic` + `--qa-jsonl`)

Outputs:
- JSONL to stdout or `--out`
- Or a single structured JSON file via `--out-json`.
"""

import argparse
import json
import math
import re
from typing import Dict, Iterable, List, Optional, Tuple


# =========================================================
# Shared utilities / regexes
# =========================================================
_SENTENCE_END_RE = re.compile(r"[.!?]+")
_WORD_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")
_VOWEL_GROUP_RE = re.compile(r"[aeiouy]+", re.IGNORECASE)
_PUNCT_COMPLEX_RE = re.compile(r"[,;:()\[\]—–-]")


def _safe_div(n: float, d: float) -> float:
    return n / d if d else 0.0


def _r2(x: float) -> float:
    """Round to 2 decimals for output."""
    return round(float(x), 2)


def _norm_ws(s: str) -> str:
    """Normalize whitespace for similarity comparisons."""
    return re.sub(r"\s+", " ", (s or "").strip())


def iter_jsonl(path: str) -> Iterable[dict]:
    """Iterate a JSONL file (one JSON object per non-empty line)."""
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


# =========================================================
# Parsing helpers (assistant_val.jsonl payload)
# =========================================================
def split_sentences(text: str) -> List[str]:
    """
    Non-strict sentence splitter using `. ! ?` as sentence boundaries.

    Intended for English text (this benchmark's `assistant_val.jsonl` is English JSON).
    """
    t = (text or "").strip()
    if not t:
        return []

    # Split then filter empties.
    parts = _SENTENCE_END_RE.split(t)
    sentences = [p.strip() for p in parts if p and p.strip()]
    return sentences


def tokenize_words(text: str) -> List[str]:
    """
    Lightweight tokenizer for metrics (sentence length, word frequency, etc.).

    Keeps only contiguous A–Z word tokens (including apostrophes), ignoring punctuation and digits.
    """
    if not text:
        return []
    return [m.group(0) for m in _WORD_RE.finditer(text)]


def estimate_syllables_in_word(word: str) -> int:
    """
    Heuristic syllable estimator for English (for Flesch Reading Ease).

    Goal: stable, dependency-free, and consistent enough for general English text.
    """
    w = (word or "").lower()
    if not w:
        return 0

    # Very short words fallback.
    if len(w) <= 3:
        return 1

    # Keep letters only (safety).
    w = re.sub(r"[^a-z]", "", w)
    if not w:
        return 0

    # Count vowel groups.
    groups = _VOWEL_GROUP_RE.findall(w)
    syllables = len(groups)

    # Handle silent -e (make / name / rate ...).
    if w.endswith("e") and not w.endswith(("le", "ye")) and syllables > 1:
        syllables -= 1

    # Handle -le endings (table / little).
    if w.endswith("le") and len(w) > 2 and w[-3] not in "aeiouy":
        syllables += 1

    return max(1, syllables)


def count_syllables(words: Iterable[str]) -> int:
    return sum(estimate_syllables_in_word(w) for w in words)


# =========================================================
# Flesch Reading Ease
# =========================================================
def flesch_reading_ease(text: str) -> float:
    """
    Flesch Reading Ease (FRE)

    Standard formula:
      206.835 - 1.015*(words/sentences) - 84.6*(syllables/words)

    Note:
    - While some specs describe it as "based on word length and sentence length",
      FRE typically uses syllables/word. We approximate syllables heuristically.
    """
    sentences = split_sentences(text)
    words = tokenize_words(text)

    s = len(sentences)
    w = len(words)
    if s == 0 or w == 0:
        return 0.0

    syll = count_syllables(words)
    fre = 206.835 - 1.015 * _safe_div(w, s) - 84.6 * _safe_div(syll, w)
    # Light clamp to avoid extreme values for pathological inputs.
    if math.isnan(fre) or math.isinf(fre):
        return 0.0
    return float(max(-200.0, min(200.0, fre)))


def fre(text: str) -> float:
    """Alias for Flesch Reading Ease."""
    return flesch_reading_ease(text)


# =========================================================
# Sentence Length
# =========================================================
def sentence_length_metrics_main_idea(text: str) -> float:
    """
    Sentence length proxy for `main_idea`.

    - Split `main_idea` into sentences using `. ! ?`.
    - Token count uses `tokenize_words`.
    - avg = total_words / number_of_sentences

    If no sentence boundary is found but words exist, treat the whole text as 1 sentence.
    """
    t = (text or "").strip()
    words = tokenize_words(t)
    total = len(words)
    if total == 0:
        return 0.0

    sentences = split_sentences(t)
    if not sentences:
        return float(total)

    n = len(sentences)
    return float(_safe_div(total, n))


def sentence_length_metrics_key_points(key_points: List[str]) -> float:
    """
    Sentence length proxy for `key_points`.

    - Each key point is treated as one sentence (no further splitting).
    - avg = arithmetic mean of token counts across key points.
    """
    counts: List[int] = []
    for kp in key_points:
        if isinstance(kp, str) and kp.strip():
            counts.append(len(tokenize_words(kp.strip())))
    if not counts:
        return 0.0
    return float(sum(counts) / len(counts))


# =========================================================
# Syntax Complexity
# =========================================================
def syntax_complexity(text: str) -> float:
    """
    Heuristic syntax complexity score in ~[0, 100]. Higher means more complex.

    This is a parser-free proxy based on:
    - Sentence length
    - Density of subordinate/relative/coordinating markers
    - Punctuation patterns (lightweight)

    Designed for English text.
    """
    t = (text or "").strip()
    if not t:
        return 0.0

    sentences = split_sentences(t)
    words = tokenize_words(t)
    s = len(sentences)
    w = len(words)
    if s == 0 or w == 0:
        return 0.0

    avg_sent_len = w / s
    punct = len(_PUNCT_COMPLEX_RE.findall(t))

    low_words = [x.lower() for x in words]
    # Subordinators / concessives / conditionals (rough list).
    subordinators = {
        "because",
        "although",
        "though",
        "while",
        "whereas",
        "since",
        "unless",
        "until",
        "when",
        "whenever",
        "before",
        "after",
        "if",
        "whether",
        "therefore",
        "however",
        "moreover",
        "nevertheless",
    }
    relatives = {"that", "which", "who", "whom", "whose"}
    coordinators = {"and", "or", "but", "nor", "yet", "so"}

    sub_cnt = sum(1 for x in low_words if x in subordinators)
    rel_cnt = sum(1 for x in low_words if x in relatives)
    coord_cnt = sum(1 for x in low_words if x in coordinators)

    # Normalize to 0..1 then weight (heuristic).
    def clamp01(x: float) -> float:
        return 0.0 if x < 0 else 1.0 if x > 1 else x

    f_len = clamp01(avg_sent_len / 30.0)  # 30+ words/sentence saturates.
    f_sub = clamp01(((sub_cnt + rel_cnt) / w) * 25.0)  # density scaled up
    f_punct = clamp01((punct / w) * 40.0)
    f_coord = clamp01((coord_cnt / w) * 15.0)

    score01 = 0.45 * f_len + 0.30 * f_sub + 0.15 * f_punct + 0.10 * f_coord
    return float(max(0.0, min(100.0, score01 * 100.0)))


# =========================================================
# Word Frequency (rarity)
# =========================================================
def build_unigram_counts_from_user_jsonl(path: str) -> Tuple[Dict[str, int], int]:
    """
    Build a unigram frequency table from user/source texts (to avoid leakage from assistant outputs).

    Returns (counts, total_tokens).
    """
    counts: Dict[str, int] = {}
    total = 0
    for rec in iter_jsonl(path):
        text = rec.get("text", "")
        if not isinstance(text, str) or not text.strip():
            continue
        for w in tokenize_words(text):
            lw = w.lower()
            counts[lw] = counts.get(lw, 0) + 1
            total += 1
    return counts, total


def word_frequency_score(text: str, counts: Dict[str, int], total_tokens: int) -> float:
    """
    Word frequency metric using a reference corpus frequency table.

    We output "average rarity" (higher = rarer words, potentially harder):
      score = mean( -log( (c(w)+1) / (N+V) ) )

    - +1 smoothing avoids OOV=0
    - N: total tokens in reference corpus, V: vocabulary size
    """
    t = (text or "").strip()
    if not t:
        return 0.0
    toks = [w.lower() for w in tokenize_words(t)]
    if not toks:
        return 0.0

    N = max(0, int(total_tokens))
    V = max(1, len(counts))
    denom = N + V
    acc = 0.0
    for w in toks:
        c = counts.get(w, 0) + 1
        p = c / denom
        acc += -math.log(p)
    return acc / len(toks)


# =========================================================
# Assistant output parsing
# =========================================================
def _parse_assistant_text_payload(record: dict) -> Tuple[str, List[str], str]:
    """
    Parse `assistant_val.jsonl` record where `text` is a JSON string:
      {"main_idea": "...", "key_points": ["...", ...]}

    Returns:
    - main_idea_text
    - key_points_list
    - merged_text (main_idea + key_points joined into a paragraph)
    """
    raw = record.get("text", "")
    if not isinstance(raw, str):
        return "", [], ""

    raw = raw.strip()
    if not raw:
        return "", [], ""

    try:
        obj = json.loads(raw)
    except Exception:
        # If not a JSON string, treat it as raw merged_text.
        return "", [], raw

    if not isinstance(obj, dict):
        return "", [], raw

    main_idea = obj.get("main_idea", "")
    key_points = obj.get("key_points", [])
    main_idea_text = main_idea.strip() if isinstance(main_idea, str) else ""
    key_points_list: List[str] = []
    if isinstance(key_points, list):
        for kp in key_points:
            if isinstance(kp, str) and kp.strip():
                key_points_list.append(kp.strip())

    parts: List[str] = []
    if main_idea_text:
        parts.append(main_idea_text)
    parts.extend(key_points_list)
    merged_text = ". ".join(parts)
    return main_idea_text, key_points_list, merged_text


def _merge_key_points(key_points: List[str]) -> str:
    # Merge into one paragraph for stability with very short bullet points.
    return ". ".join([kp for kp in key_points if kp])


# =========================================================
# Semantic similarity (embeddings)
# =========================================================
def cosine_similarity_embedding(text_a: str, text_b: str, *, model_name: str) -> float:
    """
    cosine similarity via sentence-transformers embeddings.

    Returns a value roughly in [-1, 1] (in practice usually [0, 1]).
    """
    a = (text_a or "").strip()
    b = (text_b or "").strip()
    if not a or not b:
        return 0.0

    try:
        from sentence_transformers import SentenceTransformer  # type: ignore
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(
            "Missing dependency: sentence-transformers. Install with: pip install -U sentence-transformers"
        ) from e

    # Singleton cache to avoid re-loading the model for each record.
    if not hasattr(cosine_similarity_embedding, "_model"):
        cosine_similarity_embedding._model = SentenceTransformer(model_name)  # type: ignore[attr-defined]
        cosine_similarity_embedding._model_name = model_name  # type: ignore[attr-defined]
    else:
        if getattr(cosine_similarity_embedding, "_model_name", None) != model_name:
            cosine_similarity_embedding._model = SentenceTransformer(model_name)  # type: ignore[attr-defined]
            cosine_similarity_embedding._model_name = model_name  # type: ignore[attr-defined]

    model = cosine_similarity_embedding._model  # type: ignore[attr-defined]
    emb = model.encode([a, b], normalize_embeddings=True)
    # With normalize_embeddings=True, cosine similarity equals dot product.
    return float(emb[0] @ emb[1])


# =========================================================
# QA Accuracy (QA-based semantic coverage)
# =========================================================
def qa_semantic_coverage_score(
    *,
    reference_answers: List[str],
    candidate_texts: List[str],
    model_name: str,
) -> float:
    """
    QA-based semantic coverage of candidate texts (main_idea / key_points).

    For each reference answer, compute embedding cosine similarity against all candidate texts,
    take the max similarity, then average across all reference answers.

    - main_idea: candidate_texts=[main_idea_text]
    - key_points: candidate_texts=key_points_list
    """
    refs = [_norm_ws(a) for a in reference_answers if isinstance(a, str) and a.strip()]
    cands = [_norm_ws(t) for t in candidate_texts if isinstance(t, str) and t.strip()]
    if not refs or not cands:
        return 0.0

    scores: List[float] = []
    for a in refs:
        best = 0.0
        for t in cands:
            s = cosine_similarity_embedding(a, t, model_name=model_name)
            if s > best:
                best = s
        scores.append(best)
    return float(sum(scores) / len(scores)) if scores else 0.0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--assistant-jsonl",
        type=str,
        default=str(r"test_data\assistant_val.jsonl"),
        help="Path to assistant_val.jsonl (one JSON per line)",
    )
    parser.add_argument(
        "--user-jsonl",
        type=str,
        default=str(r"test_data\user_val.jsonl"),
        help="Path to user_val.jsonl used to build reference word frequencies",
    )
    parser.add_argument(
        "--out",
        type=str,
        default="",
        help="Write results to JSONL (defaults to stdout)",
    )
    parser.add_argument(
        "--out-json",
        type=str,
        default="",
        help="Write a single JSON file: {rows: [...], summary: {...}} (takes precedence over --out/stdout)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Only process the first N records (0 = all)",
    )
    parser.add_argument(
        "--semantic-sim",
        action="store_true",
        help="Semantic similarity between main_idea/key_points and source text (embedding cosine)",
    )
    parser.add_argument(
        "--embedding-model",
        type=str,
        default="sentence-transformers/all-MiniLM-L6-v2",
        help="sentence-transformers model name (used by Method C options)",
    )
    parser.add_argument(
        "--qa-jsonl",
        type=str,
        default=str(r"test_data\qa_val_deepseek.jsonl"),
        help="Path to pre-generated QA JSONL (questions/reference_answers) for QA-based evaluation",
    )
    parser.add_argument(
        "--qa-semantic",
        action="store_true",
        help="QA + semantic similarity coverage of main_idea/key_points using reference_answers (recommended)",
    )
    args = parser.parse_args(argv)

    out_f = open(args.out, "w", encoding="utf-8") if args.out and not args.out_json else None
    rows_for_json: List[dict] = [] if args.out_json else []
    summary_for_json: Optional[dict] = None

    def _emit(obj: dict) -> None:
        nonlocal summary_for_json
        line = json.dumps(obj, ensure_ascii=False)
        if args.out_json:
            # The last emitted object is typically the summary (n + *_avg fields).
            if "n" in obj and any(k.endswith("_avg") for k in obj.keys()):
                summary_for_json = obj
            else:
                rows_for_json.append(obj)
        elif out_f:
            out_f.write(line + "\n")
        else:
            print(line)

    scores_all: List[float] = []
    scores_main: List[float] = []
    scores_kp: List[float] = []
    slen_m_scores: List[float] = []
    slen_k_scores: List[float] = []
    syn_main_scores: List[float] = []
    wf_main_scores: List[float] = []
    wf_kp_scores: List[float] = []
    wf_all_scores: List[float] = []
    sem_main_scores: List[float] = []
    sem_kp_scores: List[float] = []
    qa_sem_m_scores: List[float] = []
    qa_sem_k_scores: List[float] = []

    wf_counts, wf_total = build_unigram_counts_from_user_jsonl(args.user_jsonl)

    # For summary-vs-source similarity, map pair_id -> source text from user_jsonl.
    user_text_by_pair_id: Dict[str, str] = {}
    if args.semantic_sim:
        for u in iter_jsonl(args.user_jsonl):
            pid = u.get("pair_id") or u.get("record_id")
            if not isinstance(pid, str) or not pid:
                continue
            txt = u.get("text", "")
            if isinstance(txt, str) and txt.strip():
                user_text_by_pair_id[pid] = txt.strip()

    qa_by_pair_id: Dict[str, dict] = {}
    if args.qa_semantic:
        for q in iter_jsonl(args.qa_jsonl):
            pid = q.get("pair_id") or q.get("record_id")
            if not isinstance(pid, str) or not pid:
                continue
            if q.get("error"):
                continue
            qs = q.get("questions")
            rs = q.get("reference_answers")
            if isinstance(qs, list) and isinstance(rs, list) and qs and rs and len(qs) == len(rs):
                qa_by_pair_id[pid] = q
    try:
        for i, rec in enumerate(iter_jsonl(args.assistant_jsonl)):
            if args.limit and i >= args.limit:
                break
            main_idea_text, key_points_list, merged_text = _parse_assistant_text_payload(rec)
            kp_text = _merge_key_points(key_points_list)

            score_main = fre(main_idea_text)
            score_kp = fre(kp_text)
            score_all = fre(merged_text)
            slen_m = sentence_length_metrics_main_idea(main_idea_text)
            slen_k = sentence_length_metrics_key_points(key_points_list)
            syn_m = syntax_complexity(main_idea_text)
            wf_m = word_frequency_score(main_idea_text, wf_counts, wf_total)
            wf_k = word_frequency_score(kp_text, wf_counts, wf_total)
            wf_a = word_frequency_score(merged_text, wf_counts, wf_total)

            sem_m = 0.0
            sem_k = 0.0
            if args.semantic_sim:
                pair_id0 = rec.get("pair_id") or rec.get("record_id")
                source_text = user_text_by_pair_id.get(pair_id0, "") if isinstance(pair_id0, str) else ""
                sem_m = cosine_similarity_embedding(
                    main_idea_text,
                    source_text,
                    model_name=str(args.embedding_model),
                )
                sem_k = cosine_similarity_embedding(
                    kp_text,
                    source_text,
                    model_name=str(args.embedding_model),
                )

            qa_sem_m = 0.0
            qa_sem_k = 0.0
            if args.qa_semantic:
                pair_id0 = rec.get("pair_id") or rec.get("record_id")
                qa_obj = qa_by_pair_id.get(pair_id0, {}) if isinstance(pair_id0, str) else {}
                ref_answers = qa_obj.get("reference_answers", []) if isinstance(qa_obj, dict) else []
                if isinstance(ref_answers, list) and ref_answers:
                    qa_sem_m = qa_semantic_coverage_score(
                        reference_answers=ref_answers,
                        candidate_texts=[main_idea_text],
                        model_name=str(args.embedding_model),
                    )
                    qa_sem_k = qa_semantic_coverage_score(
                        reference_answers=ref_answers,
                        candidate_texts=key_points_list,
                        model_name=str(args.embedding_model),
                    )

            scores_main.append(score_main)
            scores_kp.append(score_kp)
            scores_all.append(score_all)
            slen_m_scores.append(slen_m)
            slen_k_scores.append(slen_k)
            syn_main_scores.append(syn_m)
            wf_main_scores.append(wf_m)
            wf_kp_scores.append(wf_k)
            wf_all_scores.append(wf_a)
            if args.semantic_sim:
                sem_main_scores.append(sem_m)
                sem_kp_scores.append(sem_k)
            if args.qa_semantic:
                qa_sem_m_scores.append(qa_sem_m)
                qa_sem_k_scores.append(qa_sem_k)
            pair_id = rec.get("pair_id", rec.get("record_id", i))
            pair_index = rec.get("pair_index", i)

            # fre_*; slen_* are sentence-length proxies (tokens/sentence), see tokenize_words.
            row = {
                "pair_index": pair_index,
                "pair_id": pair_id,
                "fre_m": _r2(score_main),
                "fre_k": _r2(score_kp),
                "fre_a": _r2(score_all),
                "slen_m": _r2(slen_m),
                "slen_k": _r2(slen_k),
                "syn_m": _r2(syn_m),
                "wf_m": _r2(wf_m),
                "wf_k": _r2(wf_k),
                "wf_a": _r2(wf_a),
            }
            if args.semantic_sim:
                row.update({"sem_m": _r2(sem_m), "sem_k": _r2(sem_k)})
            if args.qa_semantic:
                row.update({"qa_sem_m": _r2(qa_sem_m), "qa_sem_k": _r2(qa_sem_k)})
            _emit(row)

        n = len(scores_all)
        if n:
            summary = {
                "n": n,
                "fre_m_avg": _r2(sum(scores_main) / n),
                "fre_k_avg": _r2(sum(scores_kp) / n),
                "fre_a_avg": _r2(sum(scores_all) / n),
                "slen_m_avg": _r2(sum(slen_m_scores) / n),
                "slen_k_avg": _r2(sum(slen_k_scores) / n),
                "syn_m_avg": _r2(sum(syn_main_scores) / n),
                "wf_m_avg": _r2(sum(wf_main_scores) / n),
                "wf_k_avg": _r2(sum(wf_kp_scores) / n),
                "wf_a_avg": _r2(sum(wf_all_scores) / n),
            }
            if args.semantic_sim and sem_main_scores:
                summary.update(
                    {
                        "sem_m_avg": _r2(sum(sem_main_scores) / len(sem_main_scores)),
                        "sem_k_avg": _r2(sum(sem_kp_scores) / len(sem_kp_scores)),
                    }
                )
            if args.qa_semantic and qa_sem_m_scores:
                summary.update(
                    {
                        "qa_sem_m_avg": _r2(sum(qa_sem_m_scores) / len(qa_sem_m_scores)),
                        "qa_sem_k_avg": _r2(sum(qa_sem_k_scores) / len(qa_sem_k_scores)),
                    }
                )
            _emit(summary)
        else:
            summary0 = {
                "n": 0,
                "fre_m_avg": 0.0,
                "fre_k_avg": 0.0,
                "fre_a_avg": 0.0,
                "slen_m_avg": 0.0,
                "slen_k_avg": 0.0,
                "syn_m_avg": 0.0,
                "wf_m_avg": 0.0,
                "wf_k_avg": 0.0,
                "wf_a_avg": 0.0,
            }
            if args.semantic_sim:
                summary0.update({"sem_m_avg": 0.0, "sem_k_avg": 0.0})
            if args.qa_semantic:
                summary0.update({"qa_sem_m_avg": 0.0, "qa_sem_k_avg": 0.0})
            _emit(summary0)
    finally:
        if out_f:
            out_f.close()
        if args.out_json:
            payload = {"rows": rows_for_json, "summary": summary_for_json or {"n": len(rows_for_json)}}
            with open(args.out_json, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
