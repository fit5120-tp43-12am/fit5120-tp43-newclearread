# Frontend Work Log — ClearRead
**Branch:** `frontend`  
**Developer:** aubreywang1025

---

## 2026-04-04

### Project Initialisation
- Initial project scaffolded with Vite + Vue 3 (`frontend/` directory)
- Established folder structure: `src/views/`, `src/components/`, `src/router/`, `src/assets/`
- Base dependencies installed (`vue-router`, etc.)

---

## 2026-04-11

### Home Page — Initial Build (`a00dca5`)
- Created `src/views/HomePage.vue`
- Implemented fixed navbar with scroll-aware glass effect (`backdrop-filter: blur`)
- Built full-viewport hero section with:
  - Radial gradient background (blue-purple → warm peach)
  - Soft colour blob overlays for depth
  - Animated badge pill, large display heading, subtitle
  - Two CTA buttons: "Start Reading" and "Learn About Dyslexia"
- Configured `src/router/index.js` with `/` route

### Dyslexia Page — Structure (`0e05aac`, `d47a868`)
- Created `src/views/DyslexiaPage.vue`
- Set up page skeleton with seven placeholder sections:
  1. Hero
  2. Key Stats (placeholder numbers)
  3. What is Dyslexia + video block
  4. Signs & Symptoms grid
  5. Video section
  6. Reading Strategies list
  7. CTA
- Added `/dyslexia` route to router
- Shared navbar component replicated with active-link indicator for Dyslexia page

---

## 2026-04-12

### Dyslexia Page — Full Content Build (`bf4b118`)
- Replaced all placeholder content with real Australian dyslexia data (sourced from `frontend/Design/design.md`):
  - **Stats strip:** 10% official prevalence · 1 in 5 potential · 80–90% of learning-support students · 40% inheritance risk
  - **What is Dyslexia:** three concise paragraphs covering phonological processing, common misconceptions, and legal recognition under the *Disability Discrimination Act 1992*
  - **Signs & Symptoms:** 6-card grid — slow reading, inconsistent spelling, sound processing difficulty, weak working memory, poor fluency, avoidance
  - **Mental Health Impact:** 2× anxiety/depression risk, 46% higher suicide attempt rate, SA phonics check data (43% → 68%)
  - **Reading Strategies:** 6 numbered evidence-based tips
- Embedded YouTube video (`https://www.youtube.com/embed/zafiGBrFkRM`) in the "What is Dyslexia" two-column layout
- Applied sticky video aside (scrolls with reading context)
- CTA section: dark blue gradient (`#1e3a8a → #312e81`)
- Fixed all navbar links: `/reading` and `/dyslexia` properly routed

### Dyslexia Page — Text Simplification (`87600562`)
- Reduced copy throughout all sections for dyslexia-friendly readability:
  - Hero subtitle: 3 sentences → 1 sentence
  - "What is Dyslexia" paragraphs: shortened to 1–2 sentences each
  - Signs & Symptoms cards: each reduced to a single key sentence
  - Mental Health section: data-first, no filler
  - Reading Strategies: each item trimmed to 2 sentences maximum
  - All section intro subtitles shortened to one line

### Reading Page — Initial Build (`4f3396a`)
- Created `src/views/ReadingPage.vue`
- Added `/reading` route to router
- **Layout:** Fixed navbar + secondary toolbar + two-column workspace (input panel left, results panel right)
- **Input Panel:**
  - Large textarea with `0 / 5,000` character counter
  - `Simplify →` button (blue, pill-shaped)
  - Panel width animates from 46% (idle) → 30% (after submit) using CSS `flex` transition
- **Results Panel — three sections:**
  1. **AI Summary** — blue left-border card with bullet points and read-time badge
  2. **Simplified Version** — plain text with word count and read-time metadata
  3. **Key Points** — bulleted list
- **Backend stub (`handleSimplify`)** — clearly commented with endpoint, payload shape, and expected response; placeholder `setTimeout` for UI demonstration
- **Web Speech API (fully functional, no backend required):**
  - `playSpeech()`, `pauseSpeech()`, `stopSpeech()`, `toggleSpeech()`
  - Language set to `en-AU`
  - Speed options: 0.75× / 1.0× / 1.25× / 1.5×
  - Reads simplified text in Simplified view; switches to original in Original view
  - Auto-stops on component unmount
- **Toolbar controls (all wired up):**
  - Start Reading / Pause / Resume button
  - Speed selector
  - Simplified / Original view toggle
  - Font size A− / A+ (14px–28px range)
  - Line spacing: Compact / Normal / Relaxed
  - Background theme: White / Cream / Sky
- **States:** idle (empty prompt) → loading (shimmer skeleton) → result (content)
- Empty state and loading skeleton implemented

### Home Page — Feature Sections & Footer (`50123ff`)
- Added three new sections below the hero:
  - **Features grid (3 cards):** Simplify Text · Read Aloud · Customise Display — each with numbered label and description
  - **How it Works (3 steps):** Paste → Simplify → Read comfortably, connected with arrow dividers
  - **CTA section:** dark blue gradient with "Start Reading" button
- Added **Footer:**
  - Left: ClearRead wordmark + tagline "Built for minds that think differently."
  - Centre: navigation links (Reading · Dyslexia · About)
  - Right: © 2026 ClearRead. All rights reserved.
  - Dark background (`#0d1117`)
- All "Start Reading" / "Get Started" CTAs wired to `/reading`
- Removed Stats section (data already covered on Dyslexia page)
- Navbar "Get Started" button set to `disabled` (feature not yet available)

---

## Uncommitted Refinements (2026-04-12, current session)

### Reading Page — Layout & UX Polish
- Constrained workspace with `max-width: 1200px; margin: 0 auto` to prevent over-stretching on large monitors
- Input panel width uses percentage flex (`46%` idle / `30%` collapsed) instead of fixed pixels — scales with viewport
- Results layout revised from two-column card grid back to **single-column** with separator lines — more comfortable for dyslexic readers
- Fixed font/spacing toolbar: all result text elements now use `font-size: inherit; line-height: inherit` so toolbar adjustments apply correctly
- Separated computed styles: `panelBgStyle` (background/colour) applied to panel wrapper; `textStyle` (font/spacing) applied to content — ensures background tint covers full panel area
- Loading skeleton refined with shimmer animation
- Responsive breakpoint at 860px: stacks to vertical layout, input panel becomes fixed-height strip

### Dyslexia Page — Navigation Fixes
- Fixed navbar "Reading" link: `#` → `/reading`
- Fixed navbar "Dyslexia" link on Home Page: `#` → `/dyslexia`
- Fixed hero "Learn About Dyslexia" button: `#` → `/dyslexia`

---

## File Summary

| File | Status | Description |
|------|--------|-------------|
| `src/views/HomePage.vue` | Complete | Hero · Features · How it Works · CTA · Footer |
| `src/views/DyslexiaPage.vue` | Complete | 7-section informational page with real AU data + YouTube embed |
| `src/views/ReadingPage.vue` | Complete (backend stubs pending) | Full reading tool with TTS, display settings, and API hooks |
| `src/router/index.js` | Complete | Routes: `/` · `/dyslexia` · `/reading` |

---

## Pending (Backend Integration)

| Hook | File | Line | Description |
|------|------|------|-------------|
| `handleSimplify()` | `ReadingPage.vue` | ~54 | `POST /api/text/simplify` → `{ summary, simplified, keyPoints }` |
| Read Aloud | `ReadingPage.vue` | ~112 | Fully implemented via Web Speech API — no backend needed |
