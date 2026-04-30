## `benchmark_check.py` – Metrics & Semantic Similarity Evaluation

This document explains how to use `benchmark_check.py` to evaluate the generated summaries in `assistant_val.jsonl`.

It supports:
- **Text-quality metrics**: Flesch Reading Ease, sentence length, syntax complexity, and word-frequency (rarity).
- **Semantic similarity**: embedding cosine similarity used by the semantic QA coverage metrics.
- **QA Accuracy (recommended)**: **QA-based semantic coverage** using your pre-generated QA file (`qa_val_deepseek.jsonl`).

---

## Inputs

### Assistant outputs
- **File**: `test_data/assistant_val.jsonl`
- **Expected field**: each line has `text` which is a JSON string:

```json
{"main_idea":"...","key_points":["...","..."]}
```

### Source/user texts (reference corpus)
- **File**: `test_data/user_val.jsonl`
- **Used for**:
  - Building the **word-frequency table** (to avoid leakage from assistant outputs).
  - Optional: computing **summary-vs-source semantic similarity** when `--semantic-sim` is enabled.

### Pre-generated QA (for QA Accuracy)
- **File**: `test_data/qa_val_deepseek.jsonl`
- **Expected fields** (per line):
  - `pair_id`, `pair_index`
  - `questions`: list of questions
  - `reference_answers`: list of short answers (aligned with `questions`)

---

## Outputs

You can choose one of two output formats:

### Option A: JSONL (streaming)
- **Default**: prints JSON objects to stdout
- Or write to file via `--out`

Each processed sample emits one JSON object (one line). At the end, a **summary** object is emitted.

### Option B: Single JSON file (recommended)
- Use `--out-json` to write one JSON file:

```json
{
  "rows": [ ... per-sample objects ... ],
  "summary": { ... averages ... }
}
```

---

## Metrics (by section)

## Metric Overview Table (all output fields)

The script emits one row per sample (in `rows`) and an aggregate `summary` containing averages (suffix `_avg`).

| Category | Fields | Measures | Computation | Range | Better when | Notes |
|:--|:--|:--|:--|:--|:--|:--|
| **Flesch Reading Ease** | `fre_m`, `fre_k`, `fre_a` | Readability / ease | FRE formula using sentences, tokens, and heuristic syllables | Usually \([-50, 120]\); clamped to \([-200, 200]\) | Higher | Sensitive to sentence splitting (`.!?`) and short fragments. |
| **Sentence Length** | `slen_m`, `slen_k` | Length / conciseness proxy | `slen_m`: avg tokens per sentence; `slen_k`: avg tokens per key point | \([0, +\infty)\) | Depends | Higher may mean more detail **or** verbosity. Interpret with QA/semantic scores. |
| **Syntax Complexity** | `syn_m` | Heuristic syntactic complexity | Proxy from sentence length, marker-word density, and punctuation density | \([0, 100]\) | Depends | Parser-free heuristic; best for relative comparisons. |
| **Word Frequency (rarity)** | `wf_m`, `wf_k`, `wf_a` | Lexical rarity | Mean \(-\log p(w)\) using unigram counts from `user_val.jsonl` (smoothed) | \([0, +\infty)\) | Lower (simpler vocab) | Corpus-dependent. Higher = rarer words on average. |
| **Semantic Similarity** | `sem_m`, `sem_k` | Optional summary-to-source alignment | Embedding cosine similarity with sentence-transformers | \([-1, 1]\), typically \([0, 1]\) | Higher | Enabled by `--semantic-sim`. Uses the same embedding similarity mechanism as QA semantic coverage, but compares summaries directly with source text from `user_val.jsonl`. |
| **QA Accuracy (semantic coverage)** | `qa_sem_m`, `qa_sem_k` | Coverage of QA reference answers | For each `reference_answer`: semantic similarity vs candidates -> take max -> average | \([-1, 1]\), typically \([0, 1]\) | Higher | Enabled by `--qa-semantic`. Recommended task-aligned metric; uses semantic similarity internally. |

### Flesch Reading Ease (FRE)
- **Fields**:
  - `fre_m`: FRE of `main_idea`
  - `fre_k`: FRE of merged `key_points`
  - `fre_a`: FRE of (main_idea + key_points merged)
- Higher FRE generally indicates easier text.

**Definition**
- FRE is a classical readability score:

\[
206.835 - 1.015 \cdot \frac{\text{words}}{\text{sentences}} - 84.6 \cdot \frac{\text{syllables}}{\text{words}}
\]

**Implementation notes (this repo)**
- Sentence splitting uses `. ! ?` only.
- “Words” are counted using a simple regex tokenizer (A–Z tokens, plus apostrophes).
- Syllables are estimated with a heuristic (no external dictionary).
- Output is lightly clamped to \([-200, 200]\) to avoid extreme values on pathological inputs.

### Sentence Length
- **Fields**:
  - `slen_m`: average tokens per sentence in `main_idea`
  - `slen_k`: average tokens per key point item

**Interpretation**
- `slen_m` is computed after splitting `main_idea` into sentences. If no sentence boundary exists but tokens exist, the whole text is treated as one sentence.
- `slen_k` treats each key point as one “sentence” (no further splitting).
- Higher values tend to indicate more verbosity or more packed information; use together with QA/semantic metrics to judge whether the extra length is informative.

### Syntax Complexity (heuristic)
- **Field**: `syn_m`
- A lightweight proxy score in ~[0, 100] using sentence length, subordinator markers, punctuation density, etc.

**What it captures**
- Longer sentences
- More subordinate / relative clause cues (e.g., *because*, *although*, *which*, *that*)
- More complex punctuation patterns

**Caveat**
- This is **not** a true syntactic parse. It is a stable proxy intended for benchmarking and comparisons.

### Word Frequency (rarity)
- **Fields**:
  - `wf_m`, `wf_k`, `wf_a`
- Higher means **rarer words on average** based on `user_val.jsonl` unigram counts.

**Definition**
- Builds unigram counts from `user_val.jsonl`.
- Scores a text as mean rarity:

\[
\text{WF}(t) = \frac{1}{|t|} \sum_{w \in t} -\log\left(\frac{c(w)+1}{N+V}\right)
\]

Where:
- \(c(w)\) is the unigram count in the reference corpus
- \(N\) is total token count, \(V\) is vocabulary size
- `+1` is smoothing (avoids zero-probability for OOV words)

**Interpretation**
- Higher `wf_*` means the model used rarer words (potentially less accessible).

### Semantic Similarity (embedding cosine)
Enabled by `--semantic-sim`.

- **Fields**:
  - `sem_m`: cosine similarity between `main_idea` and **source text**
  - `sem_k`: cosine similarity between merged `key_points` and **source text**

**Definition**
- Uses a sentence-transformers model to embed two texts and computes cosine similarity.
- With normalized embeddings, cosine similarity equals dot product.

**Notes**
- This is the same embedding similarity mechanism used by QA Accuracy (`qa_sem_*`).
- This measures semantic alignment to the source, but it may still be high even if specific facts are missing.
- For more task-aligned evaluation, prefer QA-based coverage (`qa_sem_*`).

### QA Accuracy (QA-based semantic coverage)
Enabled by `--qa-semantic`. Uses **your existing** `qa_val_deepseek.jsonl`.

This computes how well `main_idea` and `key_points` semantically cover the QA reference answers:
- For each `reference_answer`:
  - compute embedding cosine similarity to the candidate texts
  - take **max similarity** across candidates
- then average over all answers

- **Fields**:
  - `qa_sem_m`: coverage of `main_idea` (candidate = `[main_idea]`)
  - `qa_sem_k`: coverage of `key_points` (candidates = key points list)

**Why it helps**
- This connects summary quality to “answerable facts” extracted from the source.
- `qa_sem_k` is usually higher than `qa_sem_m` because multiple key points can cover more answers.

**Caveats**
- Coverage is semantic, not exact-match. Paraphrases can score well.
- If the QA generation is noisy, the coverage score inherits that noise.

---

## How to run

### 1) QA-based evaluation (recommended)

```bash
python benchmark_check.py --qa-semantic --out-json test_data/benchmark_check_out.json
```

### 2) QA coverage + summary-vs-source semantic similarity

```bash
python benchmark_check.py --qa-semantic --semantic-sim --out-json test_data/benchmark_check_out.json
```

### 3) JSONL output instead of JSON

```bash
python benchmark_check.py --qa-semantic --out test_data/benchmark_check_out.jsonl
```

### 4) Limit records for quick debugging

```bash
python benchmark_check.py --qa-semantic --limit 5 --out-json test_data/debug_out.json
```

---

## Dependencies (Semantic Similarity / QA Accuracy)

Embedding-based methods require:

```bash
pip install -U sentence-transformers
```

By default the script uses:
- `sentence-transformers/all-MiniLM-L6-v2`

To change the embedding model:

```bash
python benchmark_check.py --qa-semantic --embedding-model sentence-transformers/all-mpnet-base-v2 --out-json test_data/out.json
```

---

## Notes & Troubleshooting

- **First run may be slow**: the embedding model is downloaded and cached.
- You may see a HuggingFace warning about unauthenticated requests. It’s optional, but you can set `HF_TOKEN` to improve rate limits.
- `qa_sem_*` scores are **semantic** (embedding-based). They are not exact-string matches, so they can reward paraphrases.

---

## `generate_qa_deepseek.py` – QA Generation (DeepSeek API)

This document explains how to use `generate_qa_deepseek.py` to generate a QA annotation file from `user_val.jsonl`.

It is designed to:
- Generate **5–8** short-answer questions per source text.
- Keep outputs **strict JSON** for downstream parsing.
- Support **resume** (skip already completed samples) for large batch runs.
- Provide a **repair mode** for previously-failed rows where answers were too long.

---

## Inputs

### Source/user texts
- **File**: `test_data/user_val.jsonl`
- **Expected fields** (per line):
  - `pair_id` (or `record_id`)
  - `pair_index`
  - `text`: the source passage used to generate QA

---

## Outputs

### QA annotations (JSONL)
- **Default output**: `test_data/qa_val_deepseek.jsonl`
- **One JSON object per line**:

```json
{
  "pair_id": "...",
  "pair_index": 0,
  "questions": ["...", "..."],
  "reference_answers": ["...", "..."]
}
```

### Error rows (JSONL)
If generation fails after retries, the script writes an error row instead of silently skipping:

```json
{
  "pair_id": "...",
  "pair_index": 0,
  "error": "..."
}
```

This makes it easy to locate problematic samples and optionally repair them later.

---

## API key and endpoint

The script reads credentials in this order:
- `--api-key`
- environment variable `DEEPSEEK_API_KEY`

Optional:
- `DEEPSEEK_BASE_URL` (default `https://api.deepseek.com`)

Example (PowerShell):

```bash
setx DEEPSEEK_API_KEY "YOUR_KEY"
```

---

## How to run

### 1) Basic generation (recommended default)

```bash
python generate_qa_deepseek.py
```

### 2) Generate only the first N records

```bash
python generate_qa_deepseek.py --limit 50
```

### 3) Skip the first N records (by line order)

```bash
python generate_qa_deepseek.py --start 50
```

### 4) Resume mode (default behavior)

If the output file exists, the script will:
- skip any `pair_id` that already has a successful row (questions + answers, no error)
- avoid appending duplicate error rows for the same `pair_id`

You can also enable it explicitly:

```bash
python generate_qa_deepseek.py --resume
```

### 5) Force overwrite (disable resume)

```bash
python generate_qa_deepseek.py --no-resume
```

### 6) Repair only "answer too long" failures

This mode:
- reads the existing output file
- reruns only rows where `error == "answer too long"`
- rewrites the output file to remove duplicated `pair_id` entries

```bash
python generate_qa_deepseek.py --repair-answer-too-long
```

---

## Important options

- `--model`: DeepSeek model name (default `deepseek-chat`)
- `--temperature`: generation randomness (default `0.2`)
- `--max-tokens`: output token budget per request (default `800`)
- `--timeout-s`: HTTP request timeout in seconds (default `90`)
- `--max-retries`: retries per sample (default `5`)
- `--sleep-s`: sleep after each request (rate limiting / stability)
- `--max-answer-words`: maximum allowed words per answer during validation (default `8`)
  - If you need strict **1–5 words**, set `--max-answer-words 5`

---

## Dependencies

Install:

```bash
pip install -U requests tqdm
```
