# Morpheme Segmenter (Minimal)

A character-level BiLSTM morpheme segmenter (prefix / root / suffix), backed by
**ONNX Runtime** for inference. CPU only; no PyTorch required. The whole folder
is self-contained and can be handed to a teammate as-is.

## Layout

```
morpheme_segmenter_minimal/
├── README.md
├── requirements.txt
├── data/
│   └── morphemes.json          # morpheme dictionary (colingoldberg/morphemes, MIT)
├── models/
│   ├── morpheme_bilstm.onnx    # trained BiLSTM boundary tagger (~830 KB)
│   └── char_vocab.json         # character vocabulary
└── src/
    ├── __init__.py
    ├── morpheme_utils.py       # CharVocab / boundaries / role classifier / meaning lookup
    └── morpheme_analyzer.py    # MorphemeSegmenter + CLI (optional WordsAPI)
```

## Install

```powershell
# Recommended: create a virtual environment first
python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

Dependencies (see `requirements.txt`):

- `onnxruntime` — CPU inference for the `.onnx` model
- `numpy` — input/output tensor handling
- `requests` — optional whole-word definition via WordsAPI

## Usage

Run from this directory so the relative imports inside `src/` resolve:

```powershell
# CLI — one JSON object per word
python -m src.morpheme_analyzer misinterpretation
python -m src.morpheme_analyzer misinterpretation unpredictability counterproductive

# Optional: override bundled artifacts or threshold
python -m src.morpheme_analyzer misinterpretation --threshold 0.5 --onnx models/morpheme_bilstm.onnx --vocab models/char_vocab.json
```

> Note: use `python -m src.morpheme_analyzer` (no `.py` suffix). The module
> uses package-relative imports, so `python src/morpheme_analyzer.py ...`
> will not work.

Output (one JSON object per word):

```json
{
  "word": "misinterpretation",
  "simple_meaning": "putting the wrong interpretation on",
  "parts": [
    { "text": "mis", "display": "mis-", "type": "Prefix",
      "meaning": ["badly", "wrongly", "astray"] },
    { "text": "interpretation", "display": "interpretation", "type": "Root",
      "meaning": null }
  ],
  "found": true
}
```

If the model cannot produce a meaningful segmentation (only a single piece AND
the morpheme dictionary has no hit), only `word` and `simple_meaning` are
returned, e.g.:

```json
{
  "word": "cat",
  "simple_meaning": "feline mammal usually having thick soft fur and no ability to roar..."
}
```

## Use from Python

```python
import json
from src.morpheme_analyzer import MorphemeSegmenter

seg = MorphemeSegmenter()  # loads bundled .onnx + vocab + dictionary
print(json.dumps(seg.analyze("unpredictability"), ensure_ascii=False, indent=2))
```

Run your script from this directory (the repo root) so `import src.morpheme_analyzer` resolves.

## About `simple_meaning` (optional whole-word definition)

- It comes from [WordsAPI](https://rapidapi.com/dpventures/api/wordsapi/).
- Set a RapidAPI key as an environment variable to enable real requests:

  ```powershell
  $env:RAPIDAPI_KEY = "your RapidAPI key"
  # or
  $env:WORDSAPI_KEY = "your RapidAPI key"
  ```

- When the key is missing, the network is unavailable, or the request fails,
  the call **silently falls back** to `simple_meaning: null`. The morpheme
  segmentation itself is unaffected.
- To disable outbound requests entirely, set the following in
  `src/morpheme_analyzer.py`:

  ```python
  USE_WORDSAPI = False
  ```

## Output schema

| Field | Description |
|---|---|
| `word` | The original input word |
| `simple_meaning` | Whole-word definition from WordsAPI; may be `null` |
| `parts[].text` | A morpheme segment |
| `parts[].display` | Hyphenated display form (`-` after prefixes, `-` before suffixes) |
| `parts[].type` | `Prefix` / `Root` / `Suffix` |
| `parts[].meaning` | Up to 3 dictionary glosses for the segment; may be `null` |
| `parts[].matched` | The actual key matched in the dictionary (only when it differs from `text`) |
| `found` | `true` when segmentation succeeded; the field is omitted in the "not found" short form |
