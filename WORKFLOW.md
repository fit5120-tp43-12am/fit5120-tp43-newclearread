# Clearead Development Workflow

> Branch: `dev`
> Last updated: 2026-05-17

## Purpose

This document summarises the current project workflow across the Clearead website, FastAPI backend, Chrome extension, and AI model evidence packages. It is intended as a review-oriented map for understanding how the implemented parts of the project work together.

## Project Areas

| Area | Main location | Role |
| --- | --- | --- |
| Web frontend | `frontend/` | Vue 3 and Vite application for the reading workspace, dictionary, focus reader, public pages, privacy page, and extension page. |
| Backend API | `backend/` | FastAPI service for extraction, reading summaries, dictionary lookup, extension summaries, and text-to-speech. |
| Browser extension | `browser-extension/` | Manifest V3 Chrome extension with side-panel reading support, page tools, dictionary lookup, and Chrome Web Store release materials. |
| AI work | `ai/` | Dataset preparation, LoRA training, model selection, deployment packages, reports, and review evidence. |
| Deployment | `.github/workflows/` | Azure deployment workflows for the backend and frontend from `dev`. |

## Implemented User Workflows

### Website Reading Workflow

1. The user enters text or uploads a TXT, PDF, or DOCX file on the reading page.
2. The frontend calls `/api/process-text` for reading segmentation, section summaries, key points, and overall summary content.
3. The backend calls the Clearead AI summary model service through the configured service URL and API key.
4. The reading page renders an overall summary, section cards, original text access, key points, and backend-generated TTS playback.

### Dictionary Workflow

1. The user submits one English word from the website dictionary page, global dictionary popup, or extension dictionary UI.
2. The frontend or extension calls `/api/dictionary`.
3. The backend returns a learner-friendly meaning, word-part breakdown, and examples.
4. Website dictionary views can request pronunciation through the backend TTS helper.

### Text-To-Speech Workflow

1. Website reading, dictionary, and focus-reader views call the shared `useBackendTts.js` helper.
2. The helper posts to `/api/tts` with text and voice settings.
3. The backend calls OpenAI TTS through `services/tts_service.py`, caches generated WAV files, and returns `audio/wav`.
4. Playback rate and volume are handled by the browser audio element for responsive controls.

### Browser Extension Workflow

1. Users install Clearead from the Chrome Web Store listing:

   ```text
   https://chromewebstore.google.com/detail/clearead/jlohhhioeodjkkeahcoelbbnkaigflkn
   ```

2. The toolbar popup opens the side panel for the current page.
3. The side panel supports pasted-text Summary, readable page fonts, Highlight, Lens, Line guide, website links, and one-word Dictionary lookup.
4. Extension Summary and Dictionary requests use the deployed Clearead backend origin configured in `browser-extension/src/shared/config.js`.
5. Local unpacked loading is used for source development and release QA.

## Backend API Contract

| Endpoint | Method | Purpose |
| --- | --- | --- |
| `/` | `GET` | Basic health response. |
| `/api/test` | `GET` | Simple backend test response. |
| `/api/process-text` | `POST` | Cleans, segments, and summarises reading text for the web reading page. |
| `/api/extract-text` | `POST` | Extracts text from TXT, PDF, and DOCX uploads. |
| `/api/plugin/summary` | `POST` | Returns a full-document summary for the Chrome extension side panel. |
| `/api/dictionary` | `POST` | Returns a simple meaning and word-part explanation for one English word. |
| `/api/tts` | `POST` | Returns WAV speech audio for submitted text. |

## Local Development Commands

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

### Backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### Browser Extension Validation

```powershell
cd browser-extension
npm run validate
```

In environments where `npm` is unavailable but Node.js is available:

```powershell
node scripts\validate-extension.js
```

## Environment Variables

### Frontend

```env
VITE_API_BASE_URL=http://localhost:8000
```

### Backend

```env
OPENAI_API_KEY=replace-with-your-key
OPENAI_MODEL=gpt-5.4-mini
OPENAI_TTS_MODEL=gpt-4o-mini-tts

# Core Clearead AI summary model service
CLEARREAD_AI_SUMMARY_ENABLED=true
CLEARREAD_AI_SUMMARY_API_URL=http://127.0.0.1:8010
CLEARREAD_AI_SUMMARY_API_KEY=replace-with-service-key
```

## Review Sign-In

```text
Username: tp43_goodjob
Password: tp43_clearead
```

## Supporting Documentation

- [README.md](README.md) gives the high-level project overview.
- [frontend/README.md](frontend/README.md) documents the website structure and routes.
- [backend/README.md](backend/README.md) documents the FastAPI service.
- [browser-extension/README.md](browser-extension/README.md) documents the Chrome extension and release entry point.
- [ai/README.md](ai/README.md) maps the AI data, training, and deployment evidence.
