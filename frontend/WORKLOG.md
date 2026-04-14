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

## 2026-04-13

### Reading Page — File Upload & Toolbar Expansion
- Expanded accepted file types for upload:
  - **Text (read directly):** `.txt`, `.md`, `.markdown`, `.csv`, `.rtf`, `.log`, `.text`
  - **Binary (backend stub placeholder):** `.pdf`, `.doc`, `.docx`, `.odt`, `.pages`, `.epub`, `.ppt`, `.pptx`
  - **Rejected with specific error:** images (`.jpg`, `.png`, `.gif`, `.webp`, etc.) and media (`.mp4`, `.mp3`, etc.)
- Updated `accept` attribute on hidden file `<input>` to include all binary formats
- Binary uploads insert a clear placeholder message pointing to `POST /api/text/extract` stub

### Reading Page — Toolbar Height & Button Size
- Toolbar height: `52px → 64px`, inner gap: `12px → 16px`
- `btn-read` padding: `7px 16px → 9px 20px`; font-size: `13px → 13.5px`; shadow upgraded
- Speed pills: padding `4px 9px → 6px 11px`; font-size `12px → 12.5px`
- View toggle buttons: padding `5px 12px → 6px 14px`; font-size `12.5px → 13px`
- Font A−/A+ buttons: padding `5px 9px → 7px 11px`; font-size `13px → 13.5px`
- Toolbar separator height: `20px → 24px`

### Reading Page — Toolbar Colour
- Changed toolbar background from plain white to a blue-purple horizontal gradient:
  `linear-gradient(105deg, rgba(232,239,255,0.9), rgba(240,236,255,0.9))`
- All toolbar button borders updated to blue-toned `rgba(199,210,254,0.6)`
- Speed pills, spacing buttons, font buttons: semi-transparent white backgrounds (`rgba(255,255,255,0.45–0.9)`)
- Separator line changed to `rgba(199,210,254,0.7)`; BG label and font value text updated to blue-toned colours
- Active states remain `#2563eb`; hover states brighten to `rgba(255,255,255,0.75–0.85)`

### Reading Page — Background Alignment
- Input panel background changed from warm `#faf9f7` → `#fafbff` to match cool blue-white tone of other pages
- Removed left/right border from `.content` container (was creating a "boxed" look)

### Global Navbar — ClearRead Logo
- Added blue SVG logo icon to `nav-logo` across all three pages (HomePage, DyslexiaPage, ReadingPage)
- Logo: 28×28 rounded square (`rx="8"`) in `#2563eb` with white open-book shape and text-line details
- `.nav-logo` updated to `display: flex; align-items: center; gap: 9px` on all three pages

### Global — Font Consistency Fix
- Reading page had `font-family: 'Arial', 'Helvetica Neue', sans-serif` on `.page`, overriding the global Inter font
- Removed the override — all three pages now uniformly use **Inter** from `style.css`

### Navigation — Start Reading Button Audit
- **DyslexiaPage CTA section:** `href="#"` → `href="/reading"` (was broken, not navigating)
- **DyslexiaPage navbar:** `Get Started` converted from `<a href="#">` to `<button disabled>` with `.btn-nav--disabled` styling, consistent with HomePage
- Added `.btn-nav--disabled` and `:not(:disabled)` hover guard to DyslexiaPage CSS
- HomePage and ReadingPage buttons verified correct — no changes needed

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
| `handleSimplify()` | `ReadingPage.vue` | ~71 | `POST /api/text/simplify` → `{ summary, simplified, keyPoints }` |
| `handleFileUpload()` binary branch | `ReadingPage.vue` | ~220 | `POST /api/text/extract` for PDF/DOCX/EPUB etc. — placeholder text shown until connected |
| Read Aloud | `ReadingPage.vue` | ~118 | Fully implemented via Web Speech API (`en-AU`, 0.75×–1.5×) — no backend needed |
