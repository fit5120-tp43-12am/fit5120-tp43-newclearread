# Clearead

Clearead is a reading-support platform for students and other readers who benefit from clearer text structure, accessible visual settings, dictionary support, and audio playback. The project combines a Vue web application, a FastAPI backend, a Chrome extension, and documented AI model-training and deployment packages.

The repository is organised so a reviewer can start at this root README, then move into the application, extension, and AI evidence folders through the linked README files.

## What The System Provides

- Web reading workspace for pasted text and uploaded TXT, PDF, or DOCX files.
- Text segmentation, plain-English summaries, key points, and full-document summaries.
- Learner-friendly dictionary lookup with word-part explanations.
- Text-to-speech playback through the backend.
- Dyslexia-oriented visual controls, including font, size, line height, colour overlay, and reading support pages.
- Chrome extension with a side-panel summary workflow, page font/ruler tools, and opt-in right-click dictionary lookup.
- AI evidence packages for dataset preparation, LoRA training, model selection, and deployment.

## Repository Map

| Path | Purpose |
| --- | --- |
| [frontend/](frontend/README.md) | Vue 3 and Vite web application. |
| [backend/](backend/README.md) | FastAPI application API used by the web app and extension. |
| [browser-extension/](browser-extension/README.md) | Manifest V3 Chrome extension package. |
| [ai/](ai/README.md) | Data preparation, LoRA training, and AI model deployment evidence. |
| [.github/workflows/](.github/workflows) | GitHub Actions workflows for Azure deployment. |
| [server.js](server.js) | Static server used by the Azure frontend deployment package. |
| [requirements.txt](requirements.txt) | Root Python dependency entry that points to backend requirements. |

## Architecture

```text
User
  |
  |-- Web app: Vue 3 + Vite
  |       |
  |       |-- /api/process-text
  |       |-- /api/extract-text
  |       |-- /api/dictionary
  |       |-- /api/tts
  |
  |-- Chrome extension: Manifest V3 side panel
          |
          |-- /api/plugin/summary
          |-- /api/dictionary

FastAPI backend
  |
  |-- Core Clearead AI summary model service for structured block summaries
  |-- OpenAI-backed dictionary, overall summary, and TTS services
  |-- Local fallback logic for resilience when service dependencies are unavailable
```

The AI service package under [ai/model_deployment/3B/](ai/model_deployment/3B/README.md) documents the core Clearead model-serving component for block-level reading summaries. This dedicated service represents the main project AI contribution and the production summarisation path. The backend also includes fallback behaviour so the reading workflow remains testable when a service dependency is unavailable; that fallback is a resilience layer rather than the preferred summary path.

## Local Setup

Use two terminals for normal development: one for the backend and one for the frontend.

### Backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Create `backend/.env` for local model-backed features:

```env
OPENAI_API_KEY=replace-with-your-key

# Optional internal ClearRead summary service
CLEARREAD_AI_SUMMARY_API_URL=http://127.0.0.1:8010
CLEARREAD_AI_SUMMARY_API_KEY=replace-with-service-key
```

Backend API docs are available at:

```text
http://127.0.0.1:8000/docs
```

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

The frontend runs at:

```text
http://localhost:5173
```

The demo sign-in used by the coursework review build is:

```text
Username: tp43_goodjob
Password: tp43_clearead
```

### Browser Extension

```powershell
cd browser-extension
npm run validate
```

Load the extension in Chrome through `chrome://extensions`, enable Developer mode, and choose `browser-extension/` as an unpacked extension.

## Deployment Notes

The GitHub Actions workflows deploy:

- the Python backend to Azure App Service from `dev`;
- the built frontend to an Azure Node static server package with route prefixes for current and release builds.

Runtime secrets, environment files, generated datasets, model weights, adapter binaries, logs, and caches are excluded from Git. AI artifacts are represented through manifests, reports, hashes, configuration examples, and reproducible scripts.

## Documentation Approach

This repository follows GitHub's README conventions: the root README explains what the project does, why it is useful, how to get started, and where to find deeper documentation. Subdirectory README files provide local context and use relative links so they work both on GitHub and in a cloned repository.
