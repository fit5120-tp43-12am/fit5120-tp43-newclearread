# Clearead Backend

The backend is a FastAPI application that serves the Clearead web app and Chrome extension. It handles text extraction, reading segmentation, block summaries, full-document summaries, dictionary lookup, and text-to-speech.

## API Surface

| Endpoint | Method | Purpose |
| --- | --- | --- |
| `/` | `GET` | Basic health response for the FastAPI app. |
| `/api/process-text` | `POST` | Cleans, segments, and summarises reading text for the web reading page. |
| `/api/extract-text` | `POST` | Extracts text from uploaded TXT, PDF, or DOCX files. |
| `/api/plugin/summary` | `POST` | Returns a full-document summary for the browser extension side panel. |
| `/api/dictionary` | `POST` | Returns a learner-friendly word meaning and word-part breakdown. |
| `/api/tts` | `POST` | Returns WAV speech audio for submitted text. |

OpenAPI documentation is available at `/docs` when the service is running.

## Directory Structure

```text
backend/
  main.py                 FastAPI app and route registration
  config.py               Minimal backend configuration module
  requirements.txt        Python dependencies for local and Azure deployment
  sample_article.txt      Local sample text for manual testing
  models/
    schemas.py            Pydantic request and response models
  routes/
    text.py               Reading and file-extraction endpoints
    plugin.py             Extension summary endpoint
    dictionary.py         Dictionary endpoint
    tts.py                Text-to-speech endpoint
  services/
    file_service.py       TXT/PDF/DOCX extraction
    reading_service.py    Main reading-processing orchestration
    text_preprocessor.py  Cleaning, segmentation, and section-card enrichment
    text_service.py       Block summary fallback and OpenAI summary helper
    overall_summary_service.py
    word_dictionary.py
    tts_service.py
```

`core/`, `repositories/`, and their `__init__.py` files mark the boundary for persistence and shared infrastructure modules. The application code in this repository is service-oriented and stores no project database state.

## Local Development

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

## Environment Variables

Create `backend/.env` for local development. The backend loads this file from service modules.

```env
OPENAI_API_KEY=replace-with-your-key
OPENAI_MODEL=gpt-5.4-mini
OPENAI_TTS_MODEL=gpt-4o-mini-tts

# Optional ClearRead internal summary model service
CLEARREAD_AI_SUMMARY_ENABLED=true
CLEARREAD_AI_SUMMARY_API_URL=http://127.0.0.1:8010
CLEARREAD_AI_SUMMARY_API_KEY=replace-with-service-key
CLEARREAD_AI_SUMMARY_TIMEOUT_SECONDS=35
CLEARREAD_AI_SUMMARY_MAX_BLOCKS=100
CLEARREAD_AI_SUMMARY_MAX_CHARS_PER_BLOCK=11000
```

The reading workflow remains usable when selected external model calls are unavailable. The backend uses local fallback segmentation and summary logic where practical, and response fields expose fallback status for debugging.

## Request Limits

| Limit | Value |
| --- | ---: |
| Maximum reading text length | 50,000 characters |
| Maximum TTS text length | 12,000 characters |
| Supported upload types | TXT, PDF, DOCX |
| Extracted file text cap | 50,000 characters |

## Integration Points

- The web frontend calls this backend through `VITE_API_BASE_URL`.
- The Chrome extension production build calls the deployed Azure backend origin configured in `browser-extension/src/shared/config.js`.
- The backend can call the internal 3B summary service documented in [../ai/model_deployment/3B/](../ai/model_deployment/3B/README.md).
