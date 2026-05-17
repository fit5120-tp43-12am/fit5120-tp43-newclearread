# Clearead Web Frontend

The frontend is a Vue 3 and Vite application for the Clearead reading-support website. It provides the public product pages, protected coursework-review entry point, reading workspace, dictionary page, focus reader, privacy page, and browser-extension information page.

## Main Routes

| Route | Component | Purpose |
| --- | --- | --- |
| `/` | `src/views/HomePage.vue` | Main website landing and navigation. |
| `/reading` | `src/views/ReadingPage.vue` | Pasted/file text processing, summaries, section cards, key points, and TTS playback. |
| `/dictionary` | `src/views/DictionaryPage.vue` | One-word dictionary lookup with simple meaning, word parts, and pronunciation. |
| `/training` | `src/views/FocusReaderPage.vue` | Letter-confusion focus reader and practice workflow. |
| `/dyslexia` | `src/views/DyslexiaPage.vue` | Dyslexia information and visual explanation page. |
| `/extension` | `src/views/ExtensionPage.vue` | Browser-extension overview and install guidance. |
| `/privacy-policy` | `src/views/PrivacyPolicyPage.vue` | Web app and extension privacy information. |

## Project Structure

```text
frontend/
  index.html
  package.json
  vite.config.js
  public/fonts/          Local OpenDyslexic font files
  src/
    App.vue              Session sign-in gate and global UI mounting
    main.js              Vue app entry point
    style.css            Global CSS variables, fonts, and base styles
    router/              Vue Router route table
    views/               Page-level application screens
    components/          Shared UI components
    composables/         Shared state and backend helpers
    assets/              Website image and SVG assets
  Design/                Design reference material
```

## Backend Integration

The frontend reads the backend origin from `VITE_API_BASE_URL`, defaulting to `http://localhost:8000`.

Main API calls:

- `POST /api/process-text` for segmented reading results.
- `POST /api/extract-text` for TXT, PDF, and DOCX extraction.
- `POST /api/plugin/summary` for full-document overview generation.
- `POST /api/dictionary` for word breakdowns.
- `POST /api/tts` for backend-generated speech audio.

## Local Development

```powershell
cd frontend
npm install
npm run dev
```

Optional local environment:

```env
VITE_API_BASE_URL=http://localhost:8000
```

The local app runs at `http://localhost:5173`.

## Build

```powershell
npm run build
npm run preview
```

Deployment builds set `VITE_BASE_PATH` so the same frontend can be served at `/`, `/underdevelopment/`, `/version1/`, and `/version2/` in the Azure static-server package.

## Review Sign-In

The coursework review build uses a simple session sign-in gate defined in `src/App.vue`:

```text
Username: tp43_goodjob
Password: tp43_clearead
```

This gate provides a lightweight coursework review entry point for the submitted build.
