# FIT5120 TP43 — Clearead / NewClearRead · Frontend Workflow

> Branch: `iteration2-frontend`  
> Last updated: 2026-04-28

---

## Project Overview

Clearead is a reading-support web app for university students with dyslexia.  
Built with **Vue 3 (Composition API) + Vite**. Backend: **FastAPI** at `http://localhost:8000`.

---

## Directory Structure

```
frontend/src/
├── assets/                 Static assets (images, icons)
├── components/
│   └── AccessibilityToolbar.vue   Global a11y toolbar (theme / font / spacing)
├── composables/
│   └── useAccessibility.js        Singleton state for accessibility settings
├── router/
│   └── index.js                   Vue Router config (/, /reading, /dyslexia)
├── views/
│   ├── HomePage.vue               Landing page
│   ├── DyslexiaPage.vue           Dyslexia info + data viz page
│   └── ReadingPage.vue            Core reading support tool (Iteration 2 focus)
├── App.vue                        Auth gate + global toolbar mount
├── main.js                        App entry point
└── style.css                      Global CSS variables + base resets
```

---

## Iteration 2 — Frontend Checklist

### ✅ Completed

| Feature | File(s) | Notes |
|---|---|---|
| Fixed bottom input bar | `ReadingPage.vue` | Textarea + upload + submit, auto-resize, Ctrl+Enter shortcut |
| File upload (TXT / PDF / DOCX) | `ReadingPage.vue` | FileReader for text; base64 → backend for binary |
| Drag & drop anywhere | `ReadingPage.vue` | dragCounter trick prevents nested-element false-leave events |
| Two-column result display | `ReadingPage.vue` | 2fr/3fr grid, one row per block, align-items:stretch for height sync |
| Dynamic block rendering | `ReadingPage.vue` | `v-for` on `result.blocks` — count driven by backend response |
| Original text expand (left) | `ReadingPage.vue` | `-webkit-line-clamp:7`; Read more/Show less when overflowing |
| Fallback text | `ReadingPage.vue` | "Summary not available" / "No key points" when backend omits data |
| Skeleton loading state | `ReadingPage.vue` | Shimmer skeleton mirrors two-column layout |
| Feedback strip | `ReadingPage.vue` | loading / uploading / success / error states with auto-dismiss |
| Demo mode | `ReadingPage.vue` | "Try Demo" button loads mock blocks without backend |
| Global accessibility toolbar | `AccessibilityToolbar.vue` + `useAccessibility.js` | Theme / font size / line height; applied to all pages including /reading |
| Colour themes (dyslexia) | `AccessibilityToolbar.vue` | 5 themes: Default, Warm Cream, Soft Yellow, Sky Blue, Dark Calm |
| Font size adjustment | `useAccessibility.js` | 16px / 18px / 20px applied to :root |
| Line height adjustment | `useAccessibility.js` | 1.5 / 1.8 / 2.1 applied to :root |
| Settings persistence | `useAccessibility.js` | Saved to localStorage; survives refresh |

| TTS audio control toolbar | `ReadingPage.vue` | Pause/Resume/Replay, speed, voice, volume, stop; backend interface clearly marked |
| Per-block Play button | `ReadingPage.vue` | Animated waveform when playing; active block blue border highlight |

### 🔲 Pending — Iteration 2

| Feature | Priority | Notes |
|---|---|---|
| Reading Page — typography settings bar | High | Per-page font/spacing controls for the result view |
| Reading Page — TTS backend integration | Medium | Replace requestTTS() placeholder with POST /api/tts fetch when backend is ready |
| Global toolbar — letter spacing option | Medium | +70/1000 em step based on research |
| Global toolbar — word spacing option | Medium | +270/1000 em (must be 3-4× letter spacing) |
| Dyslexia-friendly font option (OpenDyslexic) | Medium | Already loaded via CDN in style.css |

---

## Accessibility Research Reference

> Based on survey data collected for this project (14 pt reference font):

| Setting | Default | Step 1 | Step 2 | Implementation |
|---|---|---|---|---|
| Font size | 16 px (zoom 1.00) | ~18 px (zoom 1.13) | ~20 px (zoom 1.25) | `zoom` on `<html>` — scales all units (px/em/rem) |
| Line height | 1.5 | 1.8 | 2.1 | `line-height` on `:root` |
| Letter spacing | 0 | +0.05 em | +0.1 em | ≈ +70/1000 em from research |
| Word spacing | 0 | +0.16 em | +0.25 em | must be 3–4× letter spacing |

### Colour Overlay Themes

| Theme | Overlay Colour | Target Condition |
|---|---|---|
| Default | None | General use |
| Warm Cream | rgba(255,210,100,0.14) | Glare reduction |
| Soft Yellow | rgba(255,248,80,0.16) | Most cited dyslexia overlay |
| Sky Blue | rgba(80,190,255,0.14) | Reduces letter-movement sensation |
| Soft Green | rgba(60,210,130,0.12) | Blue-light sensitivity |
| Dark Calm | CSS filter invert(0.88) | Light sensitivity / halation |

---

## Backend API Reference

| Endpoint | Method | Payload | Response |
|---|---|---|---|
| `/api/process-text` | POST | `{ text: string }` | `{ blocks: [{ id, originalText, summary, keyPoints[] }], notice? }` |
| `/api/extract-text` | POST | `{ filename, contentBase64 }` | `{ text: string }` |
| `/api/tts` | POST | `{ text: string, voice: string, speed: number, volume: number }` | `audio/mpeg` binary stream |

### TTS Voice Key Mapping (frontend → backend)

| Frontend key | Suggested gemini-2.5-flash-tts voice |
|---|---|
| `default-female` | `Aoede` or `Kore` |
| `default-male`   | `Puck` or `Charon` |
| `calm-female`    | `Kore` |
| `clear-male`     | `Fenrir` |

> Backend can freely remap these keys to any available TTS voice IDs.

---

## Key Design Decisions

1. **Two-column result layout**: Each block is one grid row (`2fr 3fr`), so left and right cards share height via `align-items: stretch`. This keeps the layout visually ordered and tabular.

2. **Colour overlay with `mix-blend-mode: multiply`**: Applied as a fixed `<div>` above page content. Multiply blend makes white → tinted while black text stays fully readable. No existing page CSS needs to be changed.

3. **Dark Calm via CSS filter**: `invert(0.88) hue-rotate(190deg)` on `<body>` avoids pure-black halation. The toolbar counter-inverts itself so it always appears normal.

4. **Drag-and-drop counter trick**: Uses an integer counter instead of boolean to correctly track `dragenter`/`dragleave` on nested elements — prevents the overlay from flickering.

5. **Singleton composable pattern**: `useAccessibility.js` uses module-level reactive state + `watch`, so settings sync across all components without a Vuex/Pinia store.

---

## Running the Project

```bash
# Frontend
cd frontend
npm install
npm run dev          # http://localhost:5173

# Backend (separate terminal)
cd backend
pip install -r requirements.txt
uvicorn main:app --reload   # http://localhost:8000
```

Login credentials (demo): `tp43_goodjob` / `tp43_clearead`

---

## Environment Variables

```env
# frontend/.env
VITE_API_BASE_URL=http://localhost:8000
```
