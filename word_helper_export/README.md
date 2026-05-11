# Word Helper Export

This folder contains a portable backend feature block for the dyslexia-friendly English Word Helper.

## Files

- `word_dictionary.py`
  - FastAPI router
  - Pydantic request/response models
  - input validation
  - local affix fallback dictionary
  - OpenAI Structured Outputs integration

## Required Python packages

Make sure your main project has these installed:

- `fastapi`
- `pydantic`
- `openai`

## Environment variables

Your main project should provide:

- `OPENAI_API_KEY`
- optional: `OPENAI_MODEL` (default: `gpt-4o-mini`)
- optional: `OPENAI_MAX_TOKENS` (default: `900`)

## How to integrate

1. Copy `word_dictionary.py` into your main project's backend codebase.
2. Import its router in your FastAPI app.
3. Include the router with your API prefix.

Example:

```python
from fastapi import FastAPI
from your_module.word_dictionary import router as word_helper_router

app = FastAPI()
app.include_router(word_helper_router, prefix="/api")
```

## Endpoint

`POST /api/word-breakdown`

Request body:

```json
{
  "word": "misinterpretation"
}
```

Response shape:

```json
{
  "word": "misinterpretation",
  "can_split": true,
  "simple_meaning": "a wrong explanation or understanding of something",
  "parts": [
    {
      "text": "mis",
      "display": "mis-",
      "type": "prefix",
      "meaning": "wrongly or badly"
    }
  ]
}
```

## Notes

- The module returns safe fallback JSON when input is invalid.
- The module also returns safe fallback JSON when the OpenAI call fails.
- All learner-facing output is English-only.
- It uses OpenAI native Structured Outputs via `client.beta.chat.completions.parse(...)`
  with a Pydantic response model, following the OpenAI Structured Outputs article.
