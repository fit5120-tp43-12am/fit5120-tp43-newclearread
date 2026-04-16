<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '')

// ── Navbar scroll ──
const scrolled  = ref(false)
const menuOpen  = ref(false)
function onScroll() { scrolled.value = window.scrollY > 10 }

// ── Input ──
const rawText    = ref('')
const charLimit  = 5000
const charCount  = computed(() => rawText.value.length)
const overLimit  = computed(() => charCount.value > charLimit)
const atLimit    = computed(() => charCount.value >= charLimit)
const inputWordCount = computed(() => wordCount(rawText.value))

// ── App state ──
const mode      = ref('idle')     // 'idle' | 'loading' | 'result'
const viewMode  = ref('simplified') // 'simplified' | 'original'

// ── Result data (populated by backend stub) ──
const result = ref(null)
// Shape: { summary, simplified, keyPoints, usedFallback, fallbackReason, notice }

// ── Display settings ──
const fontSize    = ref(18)
const lineSpacing = ref('normal')
const bgTheme     = ref('white')

const spacingMap = { compact: 1.55, normal: 1.8, relaxed: 2.15 }

const bgThemes = [
  { value: 'white', bg: '#ffffff', swatch: '#ffffff', text: '#0d1117' },
  { value: 'cream', bg: '#fdf8ed', swatch: '#fdf8ed', text: '#1c1309' },
  { value: 'sky',   bg: '#eef4ff', swatch: '#eef4ff', text: '#0d1940' },
]
const theme = computed(() => bgThemes.find(t => t.value === bgTheme.value) || bgThemes[0])

const readingStyle = computed(() => ({
  fontSize:   `${fontSize.value}px`,
  lineHeight: spacingMap[lineSpacing.value],
  background: theme.value.bg,
  color:      theme.value.text,
}))

// panel bg only (covers full panel area incl. padding)
const panelBgStyle = computed(() => ({
  background: theme.value.bg,
  color:      theme.value.text,
}))

// text style only (font/spacing, no bg)
const textStyle = computed(() => ({
  fontSize:   `${fontSize.value}px`,
  lineHeight: spacingMap[lineSpacing.value],
}))

// input panel flex width — percentage-based so it scales with viewport
const inputFlexStyle = computed(() => ({
  flex: mode.value === 'idle' ? '0 0 46%' : '0 0 30%',
}))

// ── What text to read aloud ──
const activeText = computed(() => {
  if (mode.value === 'result' && result.value) {
    return viewMode.value === 'simplified'
      ? result.value.simplified
      : rawText.value
  }
  return rawText.value
})

function fallbackNotice(resultData) {
  if (!resultData?.usedFallback) return ''

  if (resultData.notice) return resultData.notice

  const notices = {
    temporary_ai_unavailable: 'AI service is busy right now. Showing a basic result.',
    config_error: 'AI is not configured right now. Showing a basic result.',
    invalid_ai_response: 'AI response could not be processed. Showing a basic result.',
    unknown_error: 'AI is unavailable right now. Showing a basic result.',
  }

  return notices[resultData.fallbackReason] || notices.unknown_error
}

// ── Simplify (backend stub) ──────────────────────────────────────────────────
async function handleSimplify() {
  if (!rawText.value.trim() || overLimit.value) return
  mode.value    = 'loading'
  viewMode.value = 'simplified'

  try {
    // The backend may return either an AI result or a fallback result.
    const response = await fetch(`${API_BASE_URL}/api/process-text`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        text: rawText.value,
      }),
    })

    const data = await response.json()

    console.log("Returned by the backend:", data)

    // Store the full payload so the template can show status details.
    result.value = data

    mode.value = 'result'

  } catch (error) {
    console.error(error)
    mode.value = 'idle'
  }
}

  // ╔══════════════════════════════════════════════════════════╗
  // ║  BACKEND STUB — teammate connects here                   ║
  // ║                                                          ║
  // ║  POST /api/text/simplify                                 ║
  // ║  Body:   { text: rawText.value }                         ║
  // ║  Expect: {                                               ║
  // ║    summary:     string[],   // 2–4 bullet sentences      ║
  // ║    simplified:  string,     // plain-English version     ║
  // ║    keyPoints:   string[]    // 3–6 short key points      ║
  // ║  }                                                       ║
  // ║                                                          ║
  // ║  On success:  result.value = data; mode.value = 'result' ║
  // ║  On error:    mode.value = 'idle'; show error toast      ║
  // ╚══════════════════════════════════════════════════════════╝

  // Placeholder — remove when API is connected:
//   setTimeout(() => {
//     result.value = {
//       summary: [
//         'Core concept: The text introduces a central idea about the subject matter.',
//         'Key mechanism: It explains how the key processes or arguments are structured.',
//         'Conclusion: The main takeaway connects theory to real-world application.',
//       ],
//       simplified:
//         'This is a placeholder for the simplified version of your text. Once connected to the backend, this section will show a plain-English rewrite that is shorter, clearer, and easier to read for people with dyslexia.',
//       keyPoints: [
//         'Main idea from the text',
//         'Important supporting concept',
//         'Key term or definition',
//         'Practical implication',
//       ],
//     }
//     mode.value = 'result'
//   }, 900)
// }

// ── Speech ───────────────────
const isPlaying  = ref(false)
const isPaused   = ref(false)
const speechRate = ref(1.0)
let   utterance  = null

function playSpeech() {
  if (!('speechSynthesis' in window) || !activeText.value.trim()) return
  if (isPaused.value) {
    window.speechSynthesis.resume()
    isPlaying.value = true
    isPaused.value  = false
    return
  }
  stopSpeech()
  utterance      = new SpeechSynthesisUtterance(activeText.value)
  utterance.rate = speechRate.value
  utterance.lang = 'en-AU'
  utterance.onend   = () => { isPlaying.value = false; isPaused.value = false }
  utterance.onerror = () => { isPlaying.value = false; isPaused.value = false }
  window.speechSynthesis.speak(utterance)
  isPlaying.value = true
}

function pauseSpeech() {
  window.speechSynthesis.pause()
  isPlaying.value = false
  isPaused.value  = true
}

function stopSpeech() {
  if ('speechSynthesis' in window) window.speechSynthesis.cancel()
  isPlaying.value = false
  isPaused.value  = false
}

function toggleSpeech() {
  if (isPlaying.value) pauseSpeech()
  else playSpeech()
}

function setRate(r) {
  speechRate.value = r
  if (isPlaying.value) { stopSpeech(); playSpeech() }
}

const rateOptions = [0.75, 1.0, 1.25, 1.5]

// ── Read time estimate ──
function readTime(text) {
  const words = text.trim().split(/\s+/).filter(Boolean).length
  const mins  = Math.ceil(words / 200)
  const secs  = Math.round((words / 200) * 60)
  return secs < 60 ? `~${secs} sec read` : `~${mins} min read`
}

function wordCount(text) {
  return text.trim().split(/\s+/).filter(Boolean).length
}

// ── File Upload ──────────────────────────────────────────────────────────────
const fileInputRef = ref(null)
const fileError    = ref('')

// Directly readable as plain text
const UPLOAD_EXT  = ['.txt', '.md', '.markdown', '.csv', '.rtf', '.log', '.text', '.pdf', '.docx']
// Accepted but need backend to extract (placeholder inserted)
// Rejected — not text
const IMAGE_EXT   = ['.jpg','.jpeg','.png','.gif','.webp','.svg','.bmp','.tiff','.ico','.heic']
const MEDIA_EXT   = ['.mp4','.mov','.avi','.mkv','.webm','.mp3','.wav','.aac','.flac','.ogg']

function triggerFileInput() {
  fileError.value = ''
  fileInputRef.value?.click()
}

function readFileAsBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      const result = typeof reader.result === 'string' ? reader.result : ''
      const base64 = result.includes(',') ? result.split(',')[1] : result
      resolve(base64)
    }
    reader.onerror = () => reject(new Error('Could not read the file. Please try again.'))
    reader.readAsDataURL(file)
  })
}

async function uploadFileForExtraction(file) {
  const contentBase64 = await readFileAsBase64(file)
  const response = await fetch(`${API_BASE_URL}/api/extract-text`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      filename: file.name,
      contentBase64,
    }),
  })

  const data = await response.json()
  if (!response.ok) {
    throw new Error(data.detail || 'Could not extract text from this file.')
  }

  return data
}

async function handleFileUpload(event) {
  const file = event.target.files[0]
  event.target.value = ''
  if (!file) return

  const ext = '.' + file.name.split('.').pop().toLowerCase()

  // Hard reject — images & media
  if (IMAGE_EXT.includes(ext)) {
    fileError.value = 'Image files cannot be uploaded. Please paste your text directly.'
    return
  }
  if (MEDIA_EXT.includes(ext)) {
    fileError.value = 'Audio and video files are not supported. Please paste your text directly.'
    return
  }

  // Reject unrecognised formats
  if (!UPLOAD_EXT.includes(ext)) {
    fileError.value = `"${file.name}" is not a supported format. Accepted: TXT, MD, CSV, RTF, LOG, PDF, DOCX.`
    return
  }

  if (file.size > 5 * 1024 * 1024) {
    fileError.value = 'File is too large (max 5 MB). Please use a shorter document.'
    return
  }

  fileError.value = ''

  // Binary formats — placeholder text; teammate connects backend extraction
  try {
    const extracted = await uploadFileForExtraction(file)
    if (!extracted.text?.trim()) {
      fileError.value = extracted.notice || 'No readable text was found in this file.'
      return
    }

    rawText.value = extracted.text
    if (extracted.notice) {
      fileError.value = extracted.notice
    }
  } catch (error) {
    fileError.value = error instanceof Error ? error.message : 'Could not extract text from this file.'
  }

  // Plain-text formats — read directly
}

// ── Tutorial ──────────────────────────────────────────────────────────────────
const showTutorial = ref(false)
const tutorialStep = ref(0)

const TUTORIAL_STEPS = [
  {
    title: 'Welcome to ClearRead',
    desc:  'This quick guide walks you through the tool in 3 simple steps. You can skip any time.',
    highlight: null,
    cardPos: 'center',
  },
  {
    title: 'Step 1 — Add your text',
    desc:  'Paste any lecture notes, academic article, or PDF content into the box on the left. You can also click "Upload file" to import a document directly.',
    highlight: 'input',
    cardPos: 'right-top',
  },
  {
    title: 'Step 2 — Simplify',
    desc:  'Click the Simplify button. ClearRead will rewrite the text in plain English, pull out the key points, and generate a short summary.',
    highlight: 'simplify',
    cardPos: 'right-bottom',
  },
  {
    title: 'Step 3 — Adjust your settings',
    desc:  'Use the toolbar to change font size, line spacing, and background colour. Small changes can make a big difference to how comfortable it feels to read.',
    highlight: 'toolbar',
    cardPos: 'toolbar',
  },
]

const tutorialCardStyle = computed(() => {
  const pos = TUTORIAL_STEPS[tutorialStep.value]?.cardPos
  // On narrow screens always centre the card
  if (typeof window !== 'undefined' && window.innerWidth <= 600) {
    return { top: '50%', left: '50%', transform: 'translate(-50%, -50%)', width: 'calc(100vw - 48px)' }
  }
  if (pos === 'center')       return { top: '50%', left: '50%', transform: 'translate(-50%, -50%)' }
  if (pos === 'right-top')    return { top: '160px', right: '24px' }
  if (pos === 'right-bottom') return { bottom: '100px', right: '24px' }
  if (pos === 'toolbar')      return { top: '145px', right: '24px' }
  return { top: '50%', left: '50%', transform: 'translate(-50%, -50%)' }
})

function startTutorial() {
  tutorialStep.value = 0
  showTutorial.value = true
}
function nextStep() {
  if (tutorialStep.value < TUTORIAL_STEPS.length - 1) tutorialStep.value++
  else closeTutorial()
}
function prevStep() {
  if (tutorialStep.value > 0) tutorialStep.value--
}
function closeTutorial() {
  showTutorial.value = false
  localStorage.setItem('cr_tutorial_done', '1')
}

onMounted(() => {
  window.addEventListener('scroll', onScroll)
  if (!localStorage.getItem('cr_tutorial_done')) {
    showTutorial.value = true
  }
})
onUnmounted(() => { window.removeEventListener('scroll', onScroll); stopSpeech() })
</script>

<template>
  <div class="page">

    <!-- ── Navbar ── -->
    <nav :class="['navbar', { 'navbar--scrolled': scrolled }]">
      <div class="nav-inner">
        <a href="/" class="nav-logo">
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect width="28" height="28" rx="8" fill="#2563eb"/>
            <path d="M7 8.5C7 7.67 7.67 7 8.5 7H13.5V21H8.5C7.67 21 7 20.33 7 19.5V8.5Z" fill="white" opacity="0.9"/>
            <path d="M21 8.5C21 7.67 20.33 7 19.5 7H14.5V21H19.5C20.33 21 21 20.33 21 19.5V8.5Z" fill="white" opacity="0.55"/>
            <rect x="9" y="10" width="3" height="1.5" rx="0.75" fill="#2563eb" opacity="0.7"/>
            <rect x="9" y="13" width="3" height="1.5" rx="0.75" fill="#2563eb" opacity="0.7"/>
            <rect x="9" y="16" width="2" height="1.5" rx="0.75" fill="#2563eb" opacity="0.7"/>
          </svg>
          ClearRead
        </a>
        <ul class="nav-links">
          <li><a href="/"         class="nav-link">Home</a></li>
          <li><a href="/reading"  class="nav-link nav-link--active">Reading Support</a></li>
          <li><a href="/dyslexia" class="nav-link">Dyslexia</a></li>
        </ul>
        <button class="nav-hamburger" @click="menuOpen = !menuOpen" :aria-label="menuOpen ? 'Close menu' : 'Open menu'">
          <svg v-if="!menuOpen" width="22" height="22" viewBox="0 0 22 22" fill="none">
            <path d="M3 6h16M3 11h16M3 16h16" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          </svg>
          <svg v-else width="22" height="22" viewBox="0 0 22 22" fill="none">
            <path d="M5 5l12 12M17 5L5 17" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          </svg>
        </button>
      </div>
    </nav>

    <!-- Mobile nav -->
    <div v-if="menuOpen" class="mobile-nav">
      <ul class="mobile-nav-links">
        <li><a href="/"         class="mobile-nav-link" @click="menuOpen = false">Home</a></li>
        <li><a href="/reading"  class="mobile-nav-link" @click="menuOpen = false">Reading Support</a></li>
        <li><a href="/dyslexia" class="mobile-nav-link" @click="menuOpen = false">Dyslexia</a></li>
      </ul>
    </div>

    <!-- ── Toolbar ── -->
    <div :class="['toolbar', { 'tutorial-highlight--toolbar': showTutorial && TUTORIAL_STEPS[tutorialStep].highlight === 'toolbar' }]">
      <div class="toolbar-inner">

        <!-- Left controls -->
        <div class="toolbar-left">
          <!-- Play / Pause -->
          <button
            class="btn-read"
            :class="{ 'btn-read--active': isPlaying }"
            :disabled="!rawText.trim() && mode !== 'result'"
            @click="toggleSpeech"
          >
            <svg v-if="isPlaying" width="13" height="13" viewBox="0 0 13 13" fill="none">
              <rect x="1.5" y="1" width="4" height="11" rx="1.5" fill="currentColor"/>
              <rect x="7.5" y="1" width="4" height="11" rx="1.5" fill="currentColor"/>
            </svg>
            <svg v-else width="13" height="13" viewBox="0 0 13 13" fill="none">
              <path d="M2 1.5L11.5 6.5L2 11.5V1.5Z" fill="currentColor"/>
            </svg>
            {{ isPlaying ? 'Pause' : isPaused ? 'Resume' : 'Start Reading' }}
          </button>

          <!-- Speed -->
          <div class="speed-group">
            <button
              v-for="r in rateOptions"
              :key="r"
              :class="['speed-pill', { 'speed-pill--active': speechRate === r }]"
              @click="setRate(r)"
            >{{ r }}×</button>
          </div>

          <div class="toolbar-sep"></div>

          <!-- View toggle -->
          <div v-if="mode === 'result'" class="view-toggle">
            <button
              :class="['view-btn', { 'view-btn--active': viewMode === 'simplified' }]"
              @click="viewMode = 'simplified'"
            >Simplified</button>
            <button
              :class="['view-btn', { 'view-btn--active': viewMode === 'original' }]"
              @click="viewMode = 'original'"
            >Original</button>
          </div>
        </div>

        <!-- Right controls -->
        <div class="toolbar-right">
          <!-- Font size -->
          <div class="font-group">
            <button class="font-btn" @click="fontSize = Math.max(14, fontSize - 2)">A−</button>
            <span class="font-val">{{ fontSize }}</span>
            <button class="font-btn" @click="fontSize = Math.min(28, fontSize + 2)">A+</button>
          </div>

          <div class="toolbar-sep"></div>

          <!-- Spacing -->
          <div class="seg-group">
            <button
              v-for="s in ['compact','normal','relaxed']"
              :key="s"
              :class="['seg-btn', { 'seg-btn--active': lineSpacing === s }]"
              @click="lineSpacing = s"
            >{{ s.charAt(0).toUpperCase() + s.slice(1) }}</button>
          </div>

          <div class="toolbar-sep"></div>

          <!-- BG -->
          <div class="bg-group">
            <span class="bg-label">BG</span>
            <button
              v-for="t in bgThemes"
              :key="t.value"
              :class="['bg-swatch', { 'bg-swatch--active': bgTheme === t.value }]"
              :style="{ background: t.swatch }"
              @click="bgTheme = t.value"
            ></button>
          </div>
        </div>

      </div>
    </div>

    <!-- ── Main content ── -->
    <div class="content">

      <!-- Left: input panel -->
      <div :class="['input-panel', { 'tutorial-highlight--input': showTutorial && TUTORIAL_STEPS[tutorialStep].highlight === 'input' }]" :style="inputFlexStyle">
        <p class="input-panel-label">Paste or upload your text</p>

        <!-- Hidden file input -->
        <input
          ref="fileInputRef"
          type="file"
          accept=".txt,.md,.markdown,.csv,.rtf,.log,.text,.pdf,.docx"
          style="display:none"
          @change="handleFileUpload"
        />

        <textarea
          v-model="rawText"
          class="input-textarea"
          :class="{ 'input-textarea--over': overLimit }"
          placeholder="Paste your text here — an article, essay, or any passage you'd like to simplify and read more easily."
          spellcheck="false"
          :maxlength="charLimit"
        ></textarea>

        <!-- File error message -->
        <div v-if="fileError" class="file-error">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" style="flex-shrink:0">
            <circle cx="7" cy="7" r="6" stroke="#ef4444" stroke-width="1.5"/>
            <path d="M7 4v3.5M7 9.5v.5" stroke="#ef4444" stroke-width="1.5" stroke-linecap="round"/>
          </svg>
          {{ fileError }}
        </div>

        <div class="input-footer">
          <!-- Upload button -->
          <button class="btn-upload" @click="triggerFileInput" title="Upload a TXT, PDF, or DOCX file">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path d="M7 9.5V2M7 2L4 5M7 2L10 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M2 10.5v1a.5.5 0 00.5.5h9a.5.5 0 00.5-.5v-1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
            </svg>
            Upload file
          </button>

          <div class="input-limit">
            <span class="word-count" :class="{ 'word-count--over': atLimit }">
              {{ inputWordCount.toLocaleString() }} words
            </span>
            <span v-if="atLimit" class="limit-hint limit-hint--over">
              Maximum input length applies
            </span>
          </div>

          <button
            :class="['btn-simplify', { 'tutorial-highlight--simplify': showTutorial && TUTORIAL_STEPS[tutorialStep].highlight === 'simplify' }]"
            :disabled="!rawText.trim() || overLimit || mode === 'loading'"
            @click="handleSimplify"
          >
            <span v-if="mode === 'loading'" class="spinner"></span>
            <span v-else>Simplify</span>
            <svg v-if="mode !== 'loading'" width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path d="M2 7H12M12 7L8 3M12 7L8 11" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </button>
        </div>
      </div>

      <!-- Right: results panel -->
      <div class="results-panel" :style="panelBgStyle">

        <!-- Empty state -->
        <div v-if="mode === 'idle'" class="empty-state">
          <div class="empty-icon">
            <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
              <rect x="8" y="6" width="24" height="28" rx="4" stroke="#c7d2fe" stroke-width="2"/>
              <path d="M14 14h12M14 20h12M14 26h7" stroke="#c7d2fe" stroke-width="2" stroke-linecap="round"/>
            </svg>
          </div>
          <p class="empty-title">Your results will appear here</p>
          <p class="empty-sub">Paste text on the left and click <strong>Simplify</strong> to get started.</p>
        </div>

        <!-- Loading skeleton -->
        <div v-else-if="mode === 'loading'" class="loading-state">
          <div class="skeleton skeleton--card"></div>
          <div class="skeleton skeleton--line" style="width: 100%; margin-top: 32px;"></div>
          <div class="skeleton skeleton--line" style="width: 88%;"></div>
          <div class="skeleton skeleton--line" style="width: 72%;"></div>
          <div class="skeleton skeleton--sm" style="width: 50%; margin-top: 32px;"></div>
          <div class="skeleton skeleton--line" style="width: 90%; margin-top: 12px;"></div>
          <div class="skeleton skeleton--line" style="width: 80%;"></div>
          <div class="skeleton skeleton--line" style="width: 60%;"></div>
        </div>

        <!-- Results -->
        <div v-else-if="mode === 'result' && result" class="results-content" :style="textStyle">

          <!-- View: Simplified -->
          <template v-if="viewMode === 'simplified'">

            <div v-if="result.usedFallback" class="fallback-notice">
              {{ fallbackNotice(result) }}
            </div>

            <!-- AI Summary -->
            <div class="summary-card">
              <div class="summary-card-header">
                <span class="summary-title">AI Summary</span>
                <span class="summary-badge">{{ readTime(result.simplified) }}</span>
              </div>
              <div class="summary-list">
                <p>{{ result.summary }}</p>
              </div>
            </div>

            <!-- Simplified version -->
            <div class="result-section">
              <p class="section-label">Simplified Version</p>
              <p class="section-text">{{ result.simplified }}</p>
              <p class="section-meta">{{ wordCount(result.simplified) }} words · {{ readTime(result.simplified) }}</p>
            </div>

            <!-- Key points -->
            <div class="result-section result-section--last">
              <p class="section-label">Key Points</p>
              <ul class="key-points">
                <li v-for="(pt, i) in result.keyPoints" :key="i">{{ pt }}</li>
              </ul>
              <p class="section-meta section-meta--blue">Simplified to {{ wordCount(result.simplified) }} words</p>
            </div>

          </template>

          <!-- View: Original -->
          <template v-else>
            <div class="result-section result-section--last">
              <p class="section-label">Original Text</p>
              <p class="section-text" style="white-space: pre-wrap;">{{ rawText }}</p>
              <p class="section-meta">{{ wordCount(rawText) }} words · {{ readTime(rawText) }}</p>
            </div>
          </template>

        </div>
      </div>

    </div>

    <!-- ── Floating Guide button ── -->
    <button class="btn-guide-fab" @click="startTutorial" title="Show guide">
      <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
        <circle cx="7.5" cy="7.5" r="6.5" stroke="currentColor" stroke-width="1.5"/>
        <path d="M5.8 5.8a1.7 1.7 0 013.2.85c0 1.1-1.5 1.4-1.5 2.55" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        <circle cx="7.5" cy="11.5" r=".7" fill="currentColor"/>
      </svg>
      Guide
    </button>

    <!-- ── Tutorial overlay ── -->
    <Transition name="tutorial-fade">
      <div v-if="showTutorial" class="tutorial-overlay" @click.self="closeTutorial">

        <!-- Card -->
        <div class="tutorial-card" :style="tutorialCardStyle">

          <!-- Step dots -->
          <div class="tutorial-dots">
            <span
              v-for="(_, i) in TUTORIAL_STEPS"
              :key="i"
              :class="['tutorial-dot', { 'tutorial-dot--active': i === tutorialStep }]"
            ></span>
          </div>

          <!-- Content -->
          <h3 class="tutorial-title">{{ TUTORIAL_STEPS[tutorialStep].title }}</h3>
          <p class="tutorial-desc">{{ TUTORIAL_STEPS[tutorialStep].desc }}</p>

          <!-- Actions -->
          <div class="tutorial-actions">
            <button v-if="tutorialStep > 0" class="tutorial-btn-prev" @click="prevStep">Back</button>
            <button class="tutorial-btn-skip" @click="closeTutorial">Skip</button>
            <button class="tutorial-btn-next" @click="nextStep">
              {{ tutorialStep < TUTORIAL_STEPS.length - 1 ? 'Next' : 'Get started' }}
              <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
                <path d="M2 6.5H11M11 6.5L7 2.5M11 6.5L7 10.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </button>
          </div>
        </div>

      </div>
    </Transition>

  </div>
</template>

<style scoped>
/* ── Reset / shell ── */
.page {
  height: 100dvh;   /* dynamic viewport — accounts for mobile browser chrome */
  height: 100vh;    /* fallback for browsers without dvh support */
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #fff;
}
@supports (height: 100dvh) {
  .page { height: 100dvh; }
}

/* ── Navbar ── */
.navbar {
  flex-shrink: 0;
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
  z-index: 50;
}
.navbar--scrolled {
  box-shadow: 0 1px 8px rgba(0,0,0,0.06);
}
.nav-inner {
  max-width: 1160px;
  margin: 0 auto;
  padding: 0 36px;
  height: 64px;
  display: flex;
  align-items: center;
}
.nav-logo {
  display: flex; align-items: center; gap: 9px;
  font-size: 17px; font-weight: 700;
  color: #0d1117; letter-spacing: -0.4px;
  text-decoration: none; flex-shrink: 0;
}
.nav-links {
  display: flex; list-style: none;
  margin: 0 auto; padding: 0; gap: 2px;
}
.nav-link {
  display: block; padding: 6px 14px;
  font-size: 14px; font-weight: 500;
  color: #4b5563; text-decoration: none;
  border-radius: 999px;
  transition: color 0.2s, background 0.2s;
  position: relative;
}
.nav-link:hover { color: #0d1117; background: rgba(0,0,0,0.04); }
.nav-link--active { color: #0d1117; }
.nav-link--active::after {
  content: ''; position: absolute;
  bottom: -2px; left: 50%; transform: translateX(-50%);
  width: 4px; height: 4px;
  border-radius: 50%; background: #2563eb;
}

/* ── Toolbar ── */
.toolbar {
  flex-shrink: 0;
  background: linear-gradient(105deg, rgba(232,239,255,0.9) 0%, rgba(240,236,255,0.9) 100%);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  border-bottom: 1px solid rgba(199,210,254,0.55);
  z-index: 40;
  position: relative;
}
.toolbar-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  max-width: 1160px;
  margin: 0 auto;
  padding: 0 36px;
  height: 64px;
  gap: 16px;
  width: 100%;
}
.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
.toolbar-sep {
  width: 1px; height: 24px;
  background: rgba(199,210,254,0.7);
  flex-shrink: 0;
}

/* Play button */
.btn-read {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 9px 20px;
  background: #2563eb; color: #fff;
  font-size: 13.5px; font-weight: 600;
  border: none; border-radius: 999px; cursor: pointer;
  box-shadow: 0 4px 14px rgba(37,99,235,0.28);
  transition: background 0.2s, transform 0.15s;
  white-space: nowrap;
}
.btn-read:hover:not(:disabled) { background: #1d4ed8; transform: translateY(-1px); }
.btn-read:disabled { opacity: 0.4; cursor: not-allowed; }
.btn-read--active { background: #1d4ed8; }

/* Speed pills */
.speed-group { display: flex; gap: 4px; }
.speed-pill {
  padding: 6px 11px;
  font-size: 12.5px; font-weight: 600;
  border: 1.5px solid rgba(199,210,254,0.6); border-radius: 6px;
  background: rgba(255,255,255,0.45); color: #4b5a8a; cursor: pointer;
  transition: all 0.15s;
}
.speed-pill:hover { background: rgba(255,255,255,0.75); color: #0d1117; }
.speed-pill--active { background: rgba(255,255,255,0.9); color: #2563eb; border-color: #a5b4fc; }

/* View toggle */
.view-toggle { display: flex; background: rgba(199,210,254,0.3); border-radius: 8px; padding: 3px; gap: 2px; }
.view-btn {
  padding: 6px 14px;
  font-size: 13px; font-weight: 600;
  border: none; border-radius: 6px;
  background: transparent; color: #4b5a8a; cursor: pointer;
  transition: all 0.15s;
}
.view-btn--active { background: rgba(255,255,255,0.9); color: #0d1117; box-shadow: 0 1px 4px rgba(99,120,255,0.12); }

/* Font controls */
.font-group {
  display: flex; align-items: center; gap: 6px;
}
.font-btn {
  padding: 7px 11px;
  font-size: 13.5px; font-weight: 700;
  border: 1.5px solid rgba(199,210,254,0.6); border-radius: 6px;
  background: rgba(255,255,255,0.55); color: #374151; cursor: pointer;
  transition: background 0.15s;
}
.font-btn:hover { background: rgba(255,255,255,0.85); }
.font-val {
  font-size: 13px; font-weight: 600;
  color: #1e3a8a; min-width: 26px; text-align: center;
}

/* Segmented spacing */
.seg-group { display: flex; gap: 2px; }
.seg-btn {
  padding: 5px 10px;
  font-size: 12.5px; font-weight: 600;
  border: 1.5px solid rgba(199,210,254,0.6); border-radius: 6px;
  background: rgba(255,255,255,0.45); color: #4b5a8a; cursor: pointer;
  transition: all 0.15s;
}
.seg-btn:hover { background: rgba(255,255,255,0.75); }
.seg-btn--active { background: rgba(255,255,255,0.9); color: #2563eb; border-color: #a5b4fc; }

/* BG swatches */
.bg-group { display: flex; align-items: center; gap: 6px; }
.bg-label { font-size: 11px; font-weight: 600; color: #7a8fc4; }
.bg-swatch {
  width: 22px; height: 22px;
  border-radius: 6px;
  border: 2px solid rgba(199,210,254,0.7);
  cursor: pointer;
  transition: transform 0.15s;
  box-shadow: 0 1px 3px rgba(99,120,255,0.12);
}
.bg-swatch:hover { transform: scale(1.15); }
.bg-swatch--active { border-color: #2563eb; box-shadow: 0 0 0 3px rgba(37,99,235,0.2); }

/* ── Main content ── */
.content {
  flex: 1;
  display: flex;
  overflow: hidden;
  min-height: 0;
  max-width: 1160px;
  margin: 0 auto;
  width: 100%;
}

/* ── Left input panel ── */
.input-panel {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: #fafbff;
  border-right: 1px solid #e5e7eb;
  padding: 24px 20px 16px 28px;
  gap: 12px;
  overflow: hidden;
  transition: flex 0.45s cubic-bezier(0.4, 0, 0.2, 1);
}
.input-panel-label {
  font-size: 13px; font-weight: 700;
  color: #0d1117;
  margin: 0;
  letter-spacing: -0.01em;
}
.input-textarea {
  flex: 1;
  resize: none;
  border: 1.5px solid #e8e4dc;
  border-radius: 12px;
  padding: 16px;
  font-size: 14px;
  line-height: 1.7;
  font-family: inherit;
  color: #374151;
  background: #fff;
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.input-textarea::placeholder { color: #c4c4c4; line-height: 1.8; }
.input-textarea:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37,99,235,0.1);
}
.input-textarea--over { border-color: #ef4444; }
.input-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}
.input-limit {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 10px;
}
.word-count {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  background: #f3f5fb;
  color: #34415f;
  font-size: 13px;
  font-weight: 700;
}
.word-count--over {
  background: #fef2f2;
  color: #dc2626;
}
.limit-hint {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  background: #f6f7fb;
  color: #7b86a2;
  font-size: 12px;
  font-weight: 600;
}
.limit-hint--over {
  background: #fef2f2;
  color: #dc2626;
}

/* File upload button */
.btn-upload {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 7px 12px;
  background: #fff; color: #4b5563;
  font-size: 12.5px; font-weight: 600;
  border: 1.5px solid #e5e7eb; border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s, color 0.15s;
  white-space: nowrap;
}
.btn-upload:hover {
  background: #f3f4f6; color: #0d1117;
  border-color: #d1d5db;
}

/* File error */
.file-error {
  display: flex; align-items: center; gap: 6px;
  font-size: 12.5px; color: #ef4444; font-weight: 500;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 8px;
  padding: 8px 12px;
  margin: 0;
  line-height: 1.4;
}

.btn-simplify {
  display: inline-flex; align-items: center; gap: 7px;
  padding: 9px 20px;
  background: #2563eb; color: #fff;
  font-size: 13.5px; font-weight: 700;
  border: none; border-radius: 999px; cursor: pointer;
  box-shadow: 0 4px 14px rgba(37,99,235,0.3);
  transition: background 0.2s, transform 0.15s;
}
.btn-simplify:hover:not(:disabled) { background: #1d4ed8; transform: translateY(-1px); }
.btn-simplify:disabled { opacity: 0.4; cursor: not-allowed; }

.spinner {
  width: 14px; height: 14px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  display: inline-block;
}
@keyframes spin { to { transform: rotate(360deg); } }


/* Empty state */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 12px;
  padding: 40px;
  text-align: center;
}
.empty-icon { opacity: 0.5; }
.empty-title {
  font-size: 17px; font-weight: 700;
  color: #374151; margin: 0;
}
.empty-sub {
  font-size: 14px; color: #9ca3af;
  margin: 0; line-height: 1.6;
}

/* Loading skeleton */
.loading-state {
  padding: 32px 48px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.skeleton {
  background: linear-gradient(90deg, #f0f0f0 25%, #e8e8e8 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: shimmer 1.2s infinite;
  border-radius: 8px;
}
.skeleton--card { height: 120px; border-radius: 14px; }
.skeleton--line { height: 16px; }
.skeleton--sm   { height: 13px; }
@keyframes shimmer {
  0%   { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* ── Results panel ── */
.results-panel {
  flex: 1;
  overflow-y: auto;
  min-width: 0;
  transition: background 0.3s, color 0.3s;
}

/* Results content — single column, padded */
.results-content {
  padding: 36px 44px;
  display: flex;
  flex-direction: column;
  gap: 0;
  transition: font-size 0.2s, line-height 0.2s;
}

/* AI Summary card */
.summary-card {
  background: #eef4ff;
  border: 1px solid #c7d9f5;
  border-left: 4px solid #2563eb;
  border-radius: 14px;
  padding: 18px 22px;
  margin-bottom: 28px;
}
.fallback-notice {
  margin-bottom: 20px;
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid #f5d38a;
  background: #fff7e6;
  color: #8a5a00;
  font-size: 14px;
  font-weight: 600;
}
.summary-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.summary-title {
  font-size: 11px; font-weight: 700;
  letter-spacing: 0.08em; text-transform: uppercase;
  color: #1e3a8a;
}
.summary-badge {
  font-size: 11px; font-weight: 600;
  color: #3b82f6;
  background: rgba(37,99,235,0.1);
  padding: 2px 9px; border-radius: 999px;
}
.summary-list {
  margin: 0; padding: 0;
  list-style: none;
  display: flex; flex-direction: column; gap: 8px;
}
.summary-list li {
  font-size: inherit;
  color: #1e3a8a;
  line-height: inherit;
  padding-left: 14px;
  position: relative;
}
.summary-list li::before {
  content: '·';
  position: absolute; left: 0;
  color: #2563eb; font-weight: 700;
}

/* Content sections */
.result-section {
  padding: 24px 0;
  border-top: 1px solid rgba(0,0,0,0.07);
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.result-section--last { border-bottom: 1px solid rgba(0,0,0,0.07); }

.section-label {
  font-size: 11px; font-weight: 700;
  letter-spacing: 0.08em; text-transform: uppercase;
  color: #9ca3af; margin: 0;
}
.section-text {
  font-size: inherit;
  line-height: inherit;
  color: inherit;
  margin: 0;
}
.section-meta {
  font-size: 12px; color: #9ca3af; margin: 0;
}
.section-meta--blue { color: #3b82f6; }

.key-points {
  margin: 0; padding: 0;
  list-style: none;
  display: flex; flex-direction: column; gap: 8px;
}
.key-points li {
  font-size: inherit;
  line-height: inherit;
  color: inherit;
  padding-left: 16px;
  position: relative;
}
.key-points li::before {
  content: '•';
  position: absolute; left: 0;
  color: #2563eb; font-weight: 700;
}

/* ── Hamburger ── */
.nav-hamburger {
  display: none;
  background: none; border: none; cursor: pointer;
  color: #0d1117; padding: 4px; margin-left: 12px;
  align-items: center; justify-content: center;
}

/* ── Mobile nav drawer ── */
.mobile-nav { display: none; }

/* ── Responsive ── */
@media (max-width: 860px) {
  .nav-links { display: none; }
  .nav-hamburger { display: flex; }

  .mobile-nav {
    display: block;
    position: fixed;
    top: 64px; left: 0; right: 0;
    background: rgba(255,255,255,0.98);
    backdrop-filter: blur(18px);
    -webkit-backdrop-filter: blur(18px);
    border-bottom: 1px solid #e5e7eb;
    z-index: 99;
  }
  .mobile-nav-links { list-style: none; margin: 0; padding: 0; }
  .mobile-nav-link {
    display: block; padding: 16px 24px;
    font-size: 16px; font-weight: 500; color: #374151;
    text-decoration: none;
    border-bottom: 1px solid #f3f4f6;
    transition: background 0.15s;
  }
  .mobile-nav-link:hover { background: #f9fafb; color: #0d1117; }

  /* Layout */
  .content { flex-direction: column; max-width: 100%; }
  .input-panel { flex: 0 0 auto !important; height: 36vh; border-right: none; border-bottom: 1px solid #e5e7eb; }
  .results-content { padding: 20px 16px; }
  .loading-state { padding: 24px 16px; }
  .nav-inner { padding: 0 16px; }

  /* Toolbar — scroll horizontally so all controls remain accessible */
  .toolbar-inner {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    justify-content: flex-start;
    padding: 0 16px;
    gap: 12px;
    scrollbar-width: none;
  }
  .toolbar-inner::-webkit-scrollbar { display: none; }
  .toolbar-left, .toolbar-right { flex-shrink: 0; }
}

/* ── Floating Guide button ── */
.btn-guide-fab {
  position: fixed;
  bottom: 28px; right: 28px;
  z-index: 150;
  display: inline-flex; align-items: center; gap: 7px;
  padding: 10px 18px;
  background: #fff; color: #2563eb;
  font-size: 13px; font-weight: 700;
  border: 1.5px solid #c7d2fe; border-radius: 999px;
  box-shadow: 0 4px 18px rgba(37,99,235,0.18), 0 1px 4px rgba(0,0,0,0.08);
  cursor: pointer;
  transition: background 0.15s, box-shadow 0.15s, transform 0.15s;
}
.btn-guide-fab:hover {
  background: #eef2ff;
  box-shadow: 0 6px 24px rgba(37,99,235,0.26);
  transform: translateY(-2px);
}
@media (max-width: 860px) {
  .btn-guide-fab { bottom: 16px; right: 16px; padding: 9px 14px; font-size: 12.5px; }
}

/* ── Tutorial highlight states ── */
.tutorial-highlight--toolbar {
  box-shadow: 0 0 0 3px #2563eb, 0 0 0 7px rgba(37,99,235,0.18);
  z-index: 210;
  position: relative;
  border-radius: 0;
}
.tutorial-highlight--input {
  box-shadow: 0 0 0 3px #2563eb, 0 0 0 7px rgba(37,99,235,0.18);
  z-index: 210;
  position: relative;
}
.tutorial-highlight--simplify {
  box-shadow: 0 0 0 3px #2563eb, 0 0 20px rgba(37,99,235,0.45) !important;
  transform: scale(1.05);
  z-index: 210;
  position: relative;
}

/* ── Tutorial overlay ── */
.tutorial-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  z-index: 200;
  backdrop-filter: blur(2px);
  -webkit-backdrop-filter: blur(2px);
}

/* ── Tutorial card ── */
.tutorial-card {
  position: fixed;
  width: 300px;
  background: #fff;
  border-radius: 18px;
  padding: 26px 24px 20px;
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.22), 0 4px 16px rgba(0, 0, 0, 0.1);
  z-index: 211;
}

.tutorial-dots {
  display: flex; gap: 6px; margin-bottom: 18px;
}
.tutorial-dot {
  width: 7px; height: 7px;
  border-radius: 50%;
  background: #e5e7eb;
  transition: background 0.2s, width 0.2s;
}
.tutorial-dot--active {
  width: 20px;
  border-radius: 999px;
  background: #2563eb;
}

.tutorial-title {
  font-size: 16px; font-weight: 700;
  letter-spacing: -0.02em;
  color: #0d1117; margin: 0 0 10px;
}
.tutorial-desc {
  font-size: 13.5px; line-height: 1.68;
  color: #4b5563; margin: 0 0 22px;
}

.tutorial-actions {
  display: flex; align-items: center; gap: 8px;
}
.tutorial-btn-prev {
  font-size: 13px; font-weight: 600;
  color: #6b7280; background: none;
  border: none; cursor: pointer; padding: 6px 2px;
  transition: color 0.15s;
}
.tutorial-btn-prev:hover { color: #0d1117; }
.tutorial-btn-skip {
  font-size: 13px; font-weight: 500;
  color: #9ca3af; background: none;
  border: none; cursor: pointer; padding: 6px 4px;
  margin-right: auto;
  transition: color 0.15s;
}
.tutorial-btn-skip:hover { color: #6b7280; }
.tutorial-btn-next {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 9px 18px;
  background: #2563eb; color: #fff;
  font-size: 13px; font-weight: 700;
  border: none; border-radius: 999px; cursor: pointer;
  box-shadow: 0 4px 12px rgba(37,99,235,0.3);
  transition: background 0.2s, transform 0.15s;
}
.tutorial-btn-next:hover { background: #1d4ed8; transform: translateY(-1px); }

/* ── Tutorial card — mobile override ── */
@media (max-width: 600px) {
  .tutorial-card {
    position: fixed !important;
    top: 50% !important; left: 50% !important;
    right: auto !important; bottom: auto !important;
    transform: translate(-50%, -50%) !important;
    width: calc(100vw - 48px);
    max-width: 340px;
  }
}

/* ── Transition ── */
.tutorial-fade-enter-active,
.tutorial-fade-leave-active { transition: opacity 0.22s ease; }
.tutorial-fade-enter-from,
.tutorial-fade-leave-to    { opacity: 0; }
</style>
