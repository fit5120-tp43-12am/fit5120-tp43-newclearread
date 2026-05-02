<script setup>
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'

// Backend base URL from .env; falls back to localhost for local development
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '')


// ── Navbar state ──────────────────────────────────────────────────────────────

const scrolled = ref(false)   // true when user scrolls past 10px — adds navbar shadow
const menuOpen = ref(false)   // controls mobile hamburger menu
function onScroll() { scrolled.value = window.scrollY > 10 }


// ── Input state ───────────────────────────────────────────────────────────────

const inputText        = ref('')  // text the user has typed or pasted
const uploadedFileText = ref('')  // extracted file text kept out of the visible textarea
const uploadedFileName = ref('')
const charLimit   = 50000         // max characters allowed
const processingText = computed(() => uploadedFileText.value || inputText.value)
const charCount   = computed(() => processingText.value.length)
const overLimit   = computed(() => charCount.value > charLimit)
const textareaRef = ref(null)     // ref to the textarea DOM element for auto-resize


// ── Page mode ─────────────────────────────────────────────────────────────────

// The page can be in one of three states at any time
const mode = ref('idle')   // 'idle' | 'loading' | 'result'

// Holds the processed result returned by the backend
// Expected shape:
// {
//   blocks: [
//     { id: 1, originalText: '...', summary: '...', keyPoints: ['...', '...'] },
//     ...
//   ],
//   notice: '...' (optional)
// }
const result = ref(null)


// Helper: count words in a string
function wordCount(t) { return t.trim().split(/\s+/).filter(Boolean).length }


// ── Original-text panel visibility ───────────────────────────────────────────

// Collapsed by default so the user sees only the clean summary on first load.
// Clicking the left-column toggle or any collapsed block strip sets this to true.
const showOriginal = ref(false)

// ── Block expand / collapse (left column) ────────────────────────────────────

// Tracks which blocks have been manually expanded by the user
const expandedBlocks = ref(new Set())

function isExpanded(id) { return expandedBlocks.value.has(id) }

function toggleBlock(id) {
  const next = new Set(expandedBlocks.value)
  next.has(id) ? next.delete(id) : next.add(id)
  expandedBlocks.value = next
}

// Detect whether a text element is being visually clamped (overflowing its container).
// We store a reactive map of blockId → isClamped so the template can show/hide the button.
const clampedBlocks = ref({})

// Called after each block card renders — checks if the paragraph is overflowing
function checkClamp(el, id) {
  if (!el) return
  // scrollHeight > clientHeight means the text is taller than the visible area
  clampedBlocks.value = {
    ...clampedBlocks.value,
    [id]: el.scrollHeight > el.clientHeight + 2,   // +2px to avoid sub-pixel false positives
  }
}


// ── TTS / Audio state ─────────────────────────────────────────────────────────

// ID of the block currently being read aloud (null = nothing active)
const activeBlockId   = ref(null)

// Which side is playing: 'original' (left card) | 'summary' (right card)
const activeBlockType = ref('original')

// Playback state machine
const playbackState   = ref('idle')   // 'idle' | 'playing' | 'paused'

// User-adjustable audio settings
const playbackSpeed  = ref(1.0)      // multiplier: 0.75 / 1.0 / 1.25 / 1.5 / 2.0
const selectedVoice  = ref('default-female')
const volume         = ref(70)       // 0–100

// Speed options shown in the toolbar dropdown
const SPEED_OPTIONS  = [0.75, 1.0, 1.25, 1.5, 2.0]

// Voice options — labels are UI-facing; the backend maps these keys to actual TTS voice IDs
// (e.g. gemini-2.5-flash-tts voice names: Aoede, Kore, Puck, Fenrir, Charon …)
const VOICE_OPTIONS  = [
  { value: 'default-female', label: 'Default Female' },
  { value: 'default-male',   label: 'Default Male'   },
  { value: 'calm-female',    label: 'Calm Female'    },
  { value: 'clear-male',     label: 'Clear Male'     },
]

// ─────────────────────────────────────────────────────────────────────────────
// BACKEND INTERFACE — TTS API
// ─────────────────────────────────────────────────────────────────────────────
//
// Endpoint : POST /api/tts
// Request  : { text: string, voice: string, speed: number, volume: number }
//             voice  → one of the VOICE_OPTIONS values above
//             speed  → playback rate multiplier (0.75–2.0)
//             volume → 0.0–1.0 float (volume.value / 100)
//
// Response : audio/mpeg binary stream
//            (or JSON { audioUrl: string } if the backend returns a hosted URL)
//
// The frontend will:
//   1. Create a Blob URL from the stream:   URL.createObjectURL(blob)
//   2. Pass it to:                          new Audio(url)
//   3. Set:                                 audio.playbackRate = speed
//                                           audio.volume       = volume / 100
//   4. Call:                                audio.play()
//
// Currently using Web Speech API as a placeholder until this endpoint is live.
// Replace the body of requestTTS() below when the backend is ready.
// ─────────────────────────────────────────────────────────────────────────────

// Internal reference to the current Audio object (used with real backend audio)
let currentAudio = null

/**
 * requestTTS — sends text to the TTS backend and returns a playable audio URL.
 *
 * PLACEHOLDER: Uses the browser's built-in Web Speech API.
 * Replace the entire function body with the fetch block below once the backend is ready.
 */
async function requestTTS(text) {
  // ── TODO (Backend): Replace everything inside this function with: ──────────
  //
  //   const res = await fetch(`${API_BASE_URL}/api/tts`, {
  //     method:  'POST',
  //     headers: { 'Content-Type': 'application/json' },
  //     body: JSON.stringify({
  //       text,
  //       voice:  selectedVoice.value,          // e.g. 'default-female'
  //       speed:  playbackSpeed.value,           // e.g. 1.25
  //       volume: volume.value / 100,            // e.g. 0.70
  //     }),
  //   })
  //   if (!res.ok) throw new Error('TTS request failed')
  //   const blob = await res.blob()
  //   return URL.createObjectURL(blob)           // pass this URL to new Audio(url).play()
  //
  // ─────────────────────────────────────────────────────────────────────────

  // Web Speech API fallback — works in Chrome/Edge/Safari without a backend
  return new Promise((resolve, reject) => {
    if (!('speechSynthesis' in window)) {
      reject(new Error('Text-to-speech is not supported in this browser.'))
      return
    }
    window.speechSynthesis.cancel()   // clear any previous utterance
    const utterance     = new SpeechSynthesisUtterance(text)
    utterance.rate      = playbackSpeed.value
    utterance.volume    = volume.value / 100
    utterance.onend     = () => resolve('done')
    utterance.onerror   = (e) => reject(e)
    window.speechSynthesis.speak(utterance)
    resolve('speaking')   // resolve immediately so UI updates right away
  })
}

/**
 * Start playing a block's text aloud.
 * @param {number} blockId   - The block to play
 * @param {string} textType  - 'original' (left card) or 'summary' (right card)
 */
async function playBlock(blockId, textType = 'original') {
  const block = result.value?.blocks?.find(b => b.id === blockId)
  if (!block) return

  const isSameCard = activeBlockId.value === blockId && activeBlockType.value === textType

  // Clicking the currently playing card → pause
  if (isSameCard && playbackState.value === 'playing') {
    pauseAudio(); return
  }
  // Clicking the currently paused card → resume
  if (isSameCard && playbackState.value === 'paused') {
    resumeAudio(); return
  }

  // Switch to a new block or side — stop current first
  stopAudio()
  activeBlockId.value   = blockId
  activeBlockType.value = textType
  playbackState.value   = 'playing'

  // Build the text to speak depending on which side was clicked
  let textToSpeak = ''
  if (textType === 'original') {
    textToSpeak = block.originalText
  } else {
    // Right card: read summary then key points as a flowing sentence
    const kp = block.keyPoints?.length
      ? 'Key points: ' + block.keyPoints.join('. ')
      : ''
    textToSpeak = [block.summary, kp].filter(Boolean).join('. ')
  }

  try {
    await requestTTS(textToSpeak)
    if (activeBlockId.value === blockId) stopAudio()
  } catch (err) {
    console.error('[TTS] Playback error:', err)
    stopAudio()
  }
}

/** Pause the current playback. */
function pauseAudio() {
  if ('speechSynthesis' in window) window.speechSynthesis.pause()
  // TODO (Backend): currentAudio?.pause()
  playbackState.value = 'paused'
}

/** Resume a paused playback. */
function resumeAudio() {
  if ('speechSynthesis' in window) window.speechSynthesis.resume()
  // TODO (Backend): currentAudio?.play()
  playbackState.value = 'playing'
}

/** Replay the currently active block (same side) from the beginning. */
function replayBlock() {
  if (activeBlockId.value !== null) playBlock(activeBlockId.value, activeBlockType.value)
}

/** Stop all playback and reset to idle. */
function stopAudio() {
  if ('speechSynthesis' in window) window.speechSynthesis.cancel()
  // TODO (Backend): currentAudio?.pause(); currentAudio = null
  activeBlockId.value   = null
  activeBlockType.value = 'original'
  playbackState.value   = 'idle'
}


// ── Mock data (demo only) ─────────────────────────────────────────────────────

// Sample blocks that simulate what the backend would return.
// Used by the "Try Demo" button so the UI can be previewed without a real API call.
const MOCK_RESULT = {
  notice: 'Demo mode — this is sample data, not a real backend response.',
  blocks: [
    {
      id: 1,
      originalText:
        'Dyslexia is a learning difference that primarily affects reading and writing skills. It is neurological in origin, meaning it is related to how the brain processes written language. People with dyslexia may have difficulty recognising letters, decoding words, and spelling accurately. Despite these challenges, dyslexia does not affect general intelligence — many people with dyslexia are highly creative and excel in problem-solving, art, and entrepreneurship.',
      summary:
        'Dyslexia is a brain-based learning difference that makes reading and writing harder, but it does not affect overall intelligence or creativity.',
      keyPoints: [
        'Dyslexia is neurological — it stems from how the brain processes language.',
        'Common difficulties include letter recognition, word decoding, and spelling.',
        'It does not reduce general intelligence or creative ability.',
      ],
    },
    {
      id: 2,
      originalText:
        'Early identification of dyslexia is crucial for providing the right support. Signs often appear in early childhood and can include delayed speech development, difficulty rhyming, trouble learning the alphabet, and slow reading progress compared to peers. Teachers and parents play a vital role in noticing these signs and seeking professional assessment. With early intervention and appropriate teaching strategies, children with dyslexia can make significant progress and build confidence in their literacy skills.',
      summary:
        'Spotting dyslexia early — through signs like delayed speech or slow reading — allows timely support that can greatly improve a child\'s literacy and self-confidence.',
      keyPoints: [
        'Early signs include delayed speech, difficulty rhyming, and slow reading progress.',
        'Teachers and parents are key to recognising early warning signs.',
        'Early intervention leads to better literacy outcomes and greater confidence.',
      ],
    },
    {
      id: 3,
      originalText:
        'There are many effective strategies and tools that support people with dyslexia in everyday reading and writing tasks. These include the use of dyslexia-friendly fonts such as OpenDyslexic, adjusting text size and line spacing, using coloured overlays to reduce visual stress, and text-to-speech software that reads content aloud. Technology has made a significant difference — screen readers, speech-to-text apps, and reading support platforms like Clearead help users engage with written content more comfortably and independently.',
      summary:
        'A range of tools — from dyslexia-friendly fonts and colour overlays to text-to-speech software — help people with dyslexia read and write more comfortably.',
      keyPoints: [
        'Dyslexia-friendly fonts (e.g. OpenDyslexic) and adjusted spacing reduce reading friction.',
        'Coloured overlays can ease visual stress associated with reading.',
        'Text-to-speech and reading support apps like Clearead promote independent reading.',
      ],
    },
  ],
}

// Load mock data directly — skips the API call and jumps straight to result mode
function loadDemo() {
  // Clear the input box so it stays compact while the user views demo results
  inputText.value        = ''
  uploadedFileText.value = ''
  uploadedFileName.value = ''
  nextTick(autoResize)

  expandedBlocks.value  = new Set()
  clampedBlocks.value   = {}
  result.value          = MOCK_RESULT
  mode.value            = 'result'
  stopAudio()   // ensure clean audio state on demo load
}


// ── Feedback strip ────────────────────────────────────────────────────────────

// { type: 'loading' | 'uploading' | 'success' | 'error', message: string }
const feedback = ref(null)
let feedbackTimer = null

// Show a status message; set autoDismiss = 0 to keep it until manually dismissed
function showFeedback(type, message, autoDismiss = 3000) {
  clearTimeout(feedbackTimer)
  feedback.value = { type, message }
  if (autoDismiss) feedbackTimer = setTimeout(() => { feedback.value = null }, autoDismiss)
}


// ── File upload ───────────────────────────────────────────────────────────────

const fileInputRef  = ref(null)
const isDragging    = ref(false)
const SUPPORTED_EXT = ['.txt', '.pdf', '.docx']


// ── Auto-resize textarea ──────────────────────────────────────────────────────

function autoResize() {
  const el = textareaRef.value
  if (!el) return
  el.style.height = 'auto'                                   // reset first so it can shrink
  el.style.height = Math.min(el.scrollHeight, 180) + 'px'   // cap at 180px
}
watch(inputText, () => nextTick(autoResize))


// ── Submit / process text ─────────────────────────────────────────────────────

async function handleSubmit() {
  const textToProcess = processingText.value.trim()
  if (!textToProcess || overLimit.value || mode.value === 'loading') return

  // Clear the input box immediately after capturing the text —
  // this resets the textarea back to its compact single-line size
  // so it does not take up space while the user reads the results.
  inputText.value        = ''
  uploadedFileText.value = ''
  uploadedFileName.value = ''
  nextTick(autoResize)

  showFeedback('loading', 'Processing your text…', 0)
  stopAudio()                        // stop any playing audio before new submission
  mode.value           = 'loading'
  expandedBlocks.value = new Set()
  clampedBlocks.value  = {}

  try {
    // Send text to the backend and wait for the paragraph-breakdown response
    const res = await fetch(`${API_BASE_URL}/api/process-text`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ text: textToProcess }),
    })
    const data = await res.json()

    if (!res.ok) throw new Error(data.detail || 'Processing failed.')

    // Store the result — the template will render blocks dynamically from data.blocks
    result.value = data
    mode.value   = 'result'
    showFeedback('success', 'Text processed successfully.')

    if (data.notice) {
      // If the backend sent an informational notice (e.g. fallback used), show it too
      showFeedback('success', data.notice, 6000)
    }
  } catch (err) {
    mode.value = 'idle'
    showFeedback('error', err.message || 'Something went wrong. Please try again.', 6000)
  }
}

// Go back to the input screen without clearing the text
function handleBackToInput() {
  stopAudio()                        // stop TTS before leaving result view
  mode.value           = 'idle'
  result.value         = null
  feedback.value       = null
  expandedBlocks.value = new Set()
  clampedBlocks.value  = {}
}


// ── Clear input ───────────────────────────────────────────────────────────────

function handleClear() {
  inputText.value        = ''
  uploadedFileText.value = ''
  uploadedFileName.value = ''
  feedback.value         = null
  clearTimeout(feedbackTimer)
  nextTick(autoResize)
}

function handleTextInput() {
  if (!uploadedFileText.value) return
  uploadedFileText.value = ''
  uploadedFileName.value = ''
  feedback.value = null
}


// ── File read helpers ─────────────────────────────────────────────────────────

// Reads supported uploads as base64 so the backend handles all text extraction consistently
function readAsBase64(file) {
  return new Promise((res, rej) => {
    const r = new FileReader()
    r.onload = e => {
      const s = typeof e.target.result === 'string' ? e.target.result : ''
      res(s.includes(',') ? s.split(',')[1] : s)   // strip the data-URL prefix
    }
    r.onerror = () => rej(new Error('Could not read file.'))
    r.readAsDataURL(file)
  })
}

async function processFile(file) {
  const ext = '.' + file.name.split('.').pop().toLowerCase()

  if (!SUPPORTED_EXT.includes(ext)) {
    showFeedback('error', `"${file.name}" is not supported. Use TXT, PDF, or DOCX.`, 5000)
    return
  }
  if (file.size > 5 * 1024 * 1024) {
    showFeedback('error', 'File is too large (max 5 MB).', 5000)
    return
  }

  showFeedback('uploading', `Uploading "${file.name}"…`, 0)

  try {
    const base64 = await readAsBase64(file)
    const res = await fetch(`${API_BASE_URL}/api/extract-text`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ filename: file.name, contentBase64: base64 }),
    })
    const data = await res.json()
    if (!res.ok)            throw new Error(data.detail || 'Could not extract text.')
    if (!data.text?.trim()) throw new Error('No readable text found.')
    inputText.value = ''
    uploadedFileText.value = data.text
    uploadedFileName.value = file.name
    showFeedback('success', `"${file.name}" ready — click Process Text to continue`, 0)
    nextTick(autoResize)
  } catch (err) {
    showFeedback('error', err.message || 'Upload failed. Please try again.', 6000)
  }
}

function triggerFileInput() { fileInputRef.value?.click() }

async function handleFileChange(e) {
  const file = e.target.files[0]
  e.target.value = ''   // reset so the same file can be re-selected
  if (file) await processFile(file)
}


// ── Drag and drop ─────────────────────────────────────────────────────────────

// Use a counter instead of a boolean to handle nested drag events correctly
let dragCounter = 0

function onDragEnter(e) { e.preventDefault(); dragCounter++; isDragging.value = true }
function onDragOver(e)  { e.preventDefault() }
function onDragLeave()  {
  dragCounter--
  if (dragCounter <= 0) { dragCounter = 0; isDragging.value = false }
}
async function onDrop(e) {
  e.preventDefault()
  dragCounter = 0
  isDragging.value = false
  const file = e.dataTransfer?.files[0]
  if (file) await processFile(file)
}


// ── Keyboard shortcut ─────────────────────────────────────────────────────────

// Ctrl+Enter (or Cmd+Enter on Mac) submits without clicking the button
function onKeydown(e) {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') handleSubmit()
}


// ── Lifecycle ─────────────────────────────────────────────────────────────────

onMounted(() => {
  window.addEventListener('scroll', onScroll)
  nextTick(autoResize)
})
onUnmounted(() => {
  window.removeEventListener('scroll', onScroll)
  clearTimeout(feedbackTimer)
})
</script>


<template>
  <!-- The whole page listens for drag events so users can drop files anywhere -->
  <div
    class="page"
    @dragenter="onDragEnter"
    @dragover.prevent="onDragOver"
    @dragleave="onDragLeave"
    @drop="onDrop"
  >

    <!-- ── Navbar ── -->
    <nav :class="['navbar', { 'navbar--scrolled': scrolled }]">
      <div class="nav-inner">

        <!-- Brand logo — links back to home -->
        <RouterLink to="/" class="nav-logo">
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
            <rect width="28" height="28" rx="8" fill="#2563eb"/>
            <path d="M7 8.5C7 7.67 7.67 7 8.5 7H13.5V21H8.5C7.67 21 7 20.33 7 19.5V8.5Z" fill="white" opacity="0.9"/>
            <path d="M21 8.5C21 7.67 20.33 7 19.5 7H14.5V21H19.5C20.33 21 21 20.33 21 19.5V8.5Z" fill="white" opacity="0.55"/>
            <rect x="9" y="10" width="3" height="1.5" rx="0.75" fill="#2563eb" opacity="0.7"/>
            <rect x="9" y="13" width="3" height="1.5" rx="0.75" fill="#2563eb" opacity="0.7"/>
            <rect x="9" y="16" width="2" height="1.5" rx="0.75" fill="#2563eb" opacity="0.7"/>
          </svg>
          Clearead
        </RouterLink>

        <!-- Desktop nav links -->
        <ul class="nav-links">
          <li><RouterLink to="/"         class="nav-link">Home</RouterLink></li>
          <li><RouterLink to="/reading"  class="nav-link nav-link--active">Reading Support</RouterLink></li>
          <li><RouterLink to="/dyslexia" class="nav-link">Dyslexia</RouterLink></li>
          <li><RouterLink to="/training" class="nav-link">Training</RouterLink></li>
        </ul>

        <!-- Hamburger icon — only visible on small screens -->
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

    <!-- Mobile navigation drawer -->
    <div v-if="menuOpen" class="mobile-nav">
      <ul class="mobile-nav-links">
        <li><RouterLink to="/"         class="mobile-nav-link" @click="menuOpen = false">Home</RouterLink></li>
        <li><RouterLink to="/reading"  class="mobile-nav-link" @click="menuOpen = false">Reading Support</RouterLink></li>
        <li><RouterLink to="/dyslexia" class="mobile-nav-link" @click="menuOpen = false">Dyslexia</RouterLink></li>
        <li><RouterLink to="/training" class="mobile-nav-link" @click="menuOpen = false">Training</RouterLink></li>
      </ul>
    </div>


    <!-- ── Main reading area ── -->
    <main class="reading-area">
      <div :class="['reading-inner', { 'reading-inner--wide': mode === 'result' }]">

        <!-- ── STATE: idle — welcome / how-to screen ── -->
        <div v-if="mode === 'idle'" class="empty-state">

          <h2 class="empty-title">Reading Support</h2>
          <p class="empty-sub">
            Paste or upload your text — Clearead will break it into sections
            and write a plain-English summary for each one.
          </p>

          <!-- Three-step flow — horizontal cards with arrows showing the process -->
          <div class="how-flow">

            <div class="how-card how-card--1">
              <span class="how-step-num">1</span>
              <strong class="how-card-title">Add your text</strong>
              <p class="how-card-desc">Paste, type, or upload a TXT, PDF, or DOCX file into the box below.</p>
            </div>

            <!-- Arrow connector -->
            <div class="how-arrow" aria-hidden="true">
              <svg width="28" height="16" viewBox="0 0 28 16" fill="none">
                <path d="M0 8h24M18 2l6 6-6 6" stroke="#c7d2fe" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </div>

            <div class="how-card how-card--2">
              <span class="how-step-num">2</span>
              <strong class="how-card-title">Process</strong>
              <p class="how-card-desc">Click Process Text — Clearead breaks it into paragraphs and writes a clear summary for each.</p>
            </div>

            <!-- Arrow connector -->
            <div class="how-arrow" aria-hidden="true">
              <svg width="28" height="16" viewBox="0 0 28 16" fill="none">
                <path d="M0 8h24M18 2l6 6-6 6" stroke="#c7d2fe" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </div>

            <div class="how-card how-card--3">
              <span class="how-step-num">3</span>
              <strong class="how-card-title">Read or listen</strong>
              <p class="how-card-desc">Read the summaries, or press Play on any block to hear it read aloud.</p>
            </div>

          </div>

          <p class="empty-shortcut">
            <kbd>Ctrl</kbd> + <kbd>Enter</kbd>
            <span>to submit quickly</span>
          </p>

          <!-- Demo button: loads sample data so the result UI can be previewed instantly -->
          <button class="btn-demo" @click="loadDemo">Try Demo</button>
        </div>


        <!-- ── STATE: loading — animated skeleton ── -->
        <div v-else-if="mode === 'loading'" class="loading-state">
          <!-- Skeleton mimics the two-column result layout -->
          <div class="skeleton-header">
            <div class="skeleton skeleton--col-title"></div>
            <div class="skeleton skeleton--col-title"></div>
          </div>
          <div v-for="i in 3" :key="i" class="skeleton-row">
            <!-- Left: original text placeholder -->
            <div class="skeleton-block">
              <div class="skeleton skeleton--badge"></div>
              <div class="skeleton skeleton--line" style="width:100%"></div>
              <div class="skeleton skeleton--line" style="width:88%"></div>
              <div class="skeleton skeleton--line" style="width:75%"></div>
            </div>
            <!-- Right: summary placeholder -->
            <div class="skeleton-block skeleton-block--right">
              <div class="skeleton skeleton--badge"></div>
              <div class="skeleton skeleton--sm" style="width:60%"></div>
              <div class="skeleton skeleton--line" style="width:95%"></div>
              <div class="skeleton skeleton--line" style="width:80%"></div>
              <div class="skeleton skeleton--sm" style="width:50%; margin-top:8px"></div>
              <div class="skeleton skeleton--line" style="width:85%"></div>
              <div class="skeleton skeleton--line" style="width:70%"></div>
            </div>
          </div>
        </div>


        <!-- ── STATE: result — two-column block display ── -->
        <div v-else-if="mode === 'result' && result" class="result-state">

          <!-- Top status bar: success notice + back button -->
          <div class="result-topbar">
            <div class="result-notice">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <circle cx="7" cy="7" r="6" fill="#dcfce7" stroke="#16a34a" stroke-width="1"/>
                <path d="M4 7l2.2 2.2 3.8-4.4" stroke="#16a34a" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              <!-- Show a custom backend notice if provided, otherwise a default message -->
              {{ result.notice || 'Text processed successfully.' }}
            </div>
            <button class="btn-back" @click="handleBackToInput">
              <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
                <path d="M11 6.5H2M2 6.5L6 2.5M2 6.5L6 10.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              Back to Input
            </button>
          </div>

          <!--
            ── Audio Control Toolbar ──────────────────────────────────────────
            Appears when any block is playing or paused.
            Controls: pause/resume, replay, playback speed, voice, volume, stop.

            BACKEND NOTE:
              Voice selector values map to TTS voice IDs on the backend.
              Speed and volume are forwarded as-is in the /api/tts request body.
              See requestTTS() in the script section for the full API contract.
          -->
          <Transition name="audio-bar">
            <div v-if="playbackState !== 'idle'" class="audio-toolbar">

              <!-- Left: icon + title + now-playing label -->
              <div class="at-info">
                <div class="at-icon">
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                    <path d="M2 5.5h2.5l3-3v11l-3-3H2V5.5z" fill="#2563eb"/>
                    <path d="M11 4.5a5 5 0 0 1 0 7M13 2.5a8 8 0 0 1 0 11" stroke="#2563eb" stroke-width="1.4" stroke-linecap="round"/>
                  </svg>
                </div>
                <div>
                  <div class="at-title">Audio Control Panel</div>
                  <div class="at-status">
                    Now Playing: Block {{ activeBlockId }}
                    ({{ activeBlockType === 'summary' ? 'Summary &amp; Key Points' : 'Original Text' }})
                    <span v-if="playbackState === 'paused'" class="at-paused-tag">· Paused</span>
                  </div>
                </div>
              </div>

              <!-- Centre: playback action buttons -->
              <div class="at-actions">
                <!-- Pause / Resume -->
                <button
                  class="at-btn"
                  :class="{ 'at-btn--primary': playbackState === 'playing' }"
                  @click="playbackState === 'playing' ? pauseAudio() : resumeAudio()"
                >
                  <svg v-if="playbackState === 'playing'" width="14" height="14" viewBox="0 0 14 14" fill="none">
                    <rect x="3" y="2" width="3" height="10" rx="1" fill="currentColor"/>
                    <rect x="8" y="2" width="3" height="10" rx="1" fill="currentColor"/>
                  </svg>
                  <svg v-else width="14" height="14" viewBox="0 0 14 14" fill="none">
                    <path d="M4 2.5l8 4.5-8 4.5V2.5z" fill="currentColor"/>
                  </svg>
                  {{ playbackState === 'playing' ? 'Pause' : 'Resume' }}
                </button>

                <!-- Replay -->
                <button class="at-btn" @click="replayBlock">
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                    <path d="M11 7A4 4 0 1 1 7 3M11 3v4H7" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                  Replay
                </button>
              </div>

              <!-- Speed selector -->
              <div class="at-control">
                <label class="at-label">Speed</label>
                <select v-model="playbackSpeed" class="at-select">
                  <option v-for="s in SPEED_OPTIONS" :key="s" :value="s">{{ s }}x</option>
                </select>
              </div>

              <!-- Voice selector -->
              <div class="at-control">
                <label class="at-label">Voice</label>
                <select v-model="selectedVoice" class="at-select">
                  <option v-for="v in VOICE_OPTIONS" :key="v.value" :value="v.value">{{ v.label }}</option>
                </select>
              </div>

              <!-- Volume slider -->
              <div class="at-control at-volume">
                <label class="at-label">Volume</label>
                <input
                  type="range"
                  v-model="volume"
                  min="0" max="100" step="1"
                  class="at-slider"
                  :aria-label="`Volume: ${volume}%`"
                />
                <span class="at-vol-num">{{ volume }}%</span>
              </div>

              <!-- Stop button -->
              <button class="at-btn-stop" @click="stopAudio" title="Stop playback">
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                  <rect x="2" y="2" width="8" height="8" rx="1.5" fill="currentColor"/>
                </svg>
                Stop
              </button>

            </div>
          </Transition>

          <!--
            Two-column layout.
            Structure: one sticky header row + one grid row per block.
            Left and right cards share the same row, so they always align in height.
          -->
          <!-- result-grid--orig-hidden collapses the left column to a 44px strip -->
          <div :class="['result-grid', { 'result-grid--orig-hidden': !showOriginal }]">

            <!-- ── Sticky column headers ── -->
            <div class="result-grid-header">

              <!-- Left header: acts as a toggle button to show/hide the original-text column -->
              <button
                class="col-header col-orig-toggle"
                @click="showOriginal = !showOriginal"
                :title="showOriginal ? 'Hide original text' : 'Show original text'"
                :aria-label="showOriginal ? 'Hide original text' : 'Show original text'"
              >
                <!-- Expanded state: label + collapse-left chevron (no decorative icon) -->
                <template v-if="showOriginal">
                  Original Text
                  <!-- Left-pointing chevron = "click to collapse" -->
                  <svg class="col-toggle-arrow" width="13" height="13" viewBox="0 0 13 13" fill="none">
                    <path d="M8.5 2.5L4 6.5l4.5 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                </template>
                <!-- Collapsed state: right-pointing chevron + rotated label -->
                <template v-else>
                  <svg class="col-toggle-arrow" width="13" height="13" viewBox="0 0 13 13" fill="none">
                    <path d="M4.5 2.5L9 6.5l-4.5 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                  <span class="col-orig-label-vert">Original</span>
                </template>
              </button>

              <!-- Right column header — no decorative icon -->
              <div class="col-header">
                Summary &amp; Key Points
              </div>
            </div>

            <!--
              One row per block — left card (2fr) + right card (3fr) sit in the same grid row,
              so align-items: stretch makes both cards equal height automatically.
            -->
            <div
              v-for="block in result.blocks"
              :key="block.id"
              class="block-row"
            >

              <!-- ── Left card: original text (collapsible) ── -->
              <!--
                When showOriginal is false this card is a narrow strip.
                Clicking the strip sets showOriginal = true to reveal the full column.
                When showOriginal is true the card behaves like the original layout.
              -->
              <div :class="['block-card', 'block-card--left', { 'block-card--active': activeBlockId === block.id }]">

                <!-- Collapsed strip — shown only when the original-text panel is hidden -->
                <div v-if="!showOriginal" class="orig-strip-hint" @click="showOriginal = true">
                  <!-- Right-pointing expand icon -->
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                    <path d="M4.5 2L9 6l-4.5 4" stroke="#9ca3af" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                  <!-- Rotated block label so it reads bottom-to-top in the strip -->
                  <span class="orig-strip-label">B{{ block.id }}</span>
                </div>

                <!-- Expanded — full original-text card content -->
                <template v-else>

                  <!-- Card header: block label on the left, play button on the right -->
                  <div class="block-card-header">
                    <div class="block-label">Block {{ block.id }}</div>

                    <!-- Play / Pause button for this specific block -->
                    <button class="btn-play" @click="playBlock(block.id)" :aria-label="`Play Block ${block.id}`">
                      <!-- Animated waveform bars when this block is playing -->
                      <span v-if="activeBlockId === block.id && playbackState === 'playing'" class="play-badge play-badge--playing">
                        <span class="wave-bar"></span>
                        <span class="wave-bar"></span>
                        <span class="wave-bar"></span>
                        Now Playing…
                      </span>
                      <!-- Paused state indicator -->
                      <span v-else-if="activeBlockId === block.id && playbackState === 'paused'" class="play-badge play-badge--paused">
                        <svg width="11" height="11" viewBox="0 0 11 11" fill="none">
                          <rect x="2" y="1.5" width="2.5" height="8" rx="0.8" fill="currentColor"/>
                          <rect x="6.5" y="1.5" width="2.5" height="8" rx="0.8" fill="currentColor"/>
                        </svg>
                        Paused
                      </span>
                      <!-- Default: play icon + label -->
                      <span v-else class="play-badge play-badge--idle">
                        <svg width="11" height="11" viewBox="0 0 11 11" fill="none">
                          <path d="M2.5 1.5l7 4-7 4V1.5z" fill="currentColor"/>
                        </svg>
                        Play
                      </span>
                    </button>
                  </div>

                  <!-- Original text — clamped by default, expandable via Read more -->
                  <p
                    :ref="el => checkClamp(el, block.id)"
                    :class="['block-text', 'block-text--small', { 'block-text--clamped': !isExpanded(block.id) }]"
                  >
                    {{ block.originalText }}
                  </p>

                  <!-- Read more / Show less toggle — only when text actually overflows -->
                  <button
                    v-if="clampedBlocks[block.id] || isExpanded(block.id)"
                    class="btn-toggle"
                    @click="toggleBlock(block.id)"
                  >
                    {{ isExpanded(block.id) ? 'Show less ↑' : 'Read more ↓' }}
                  </button>

                </template>
              </div>

              <!-- ── Right card: summary + key points ── -->
              <div :class="['block-card', 'block-card--right', { 'block-card--active': activeBlockId === block.id && activeBlockType === 'summary' }]">

                <!-- Card header: block label + play button (plays summary + key points) -->
                <div class="block-card-header">
                  <div class="block-label">Block {{ block.id }}</div>

                  <button class="btn-play" @click="playBlock(block.id, 'summary')" :aria-label="`Play summary of Block ${block.id}`">
                    <span v-if="activeBlockId === block.id && activeBlockType === 'summary' && playbackState === 'playing'" class="play-badge play-badge--playing">
                      <span class="wave-bar"></span>
                      <span class="wave-bar"></span>
                      <span class="wave-bar"></span>
                      Now Playing…
                    </span>
                    <span v-else-if="activeBlockId === block.id && activeBlockType === 'summary' && playbackState === 'paused'" class="play-badge play-badge--paused">
                      <svg width="11" height="11" viewBox="0 0 11 11" fill="none">
                        <rect x="2" y="1.5" width="2.5" height="8" rx="0.8" fill="currentColor"/>
                        <rect x="6.5" y="1.5" width="2.5" height="8" rx="0.8" fill="currentColor"/>
                      </svg>
                      Paused
                    </span>
                    <span v-else class="play-badge play-badge--idle">
                      <svg width="11" height="11" viewBox="0 0 11 11" fill="none">
                        <path d="M2.5 1.5l7 4-7 4V1.5z" fill="currentColor"/>
                      </svg>
                      Play
                    </span>
                  </button>
                </div>

                <div class="summary-section">
                  <!-- Section label — no icon, plain text -->
                  <div class="section-title">Summary</div>
                  <p class="summary-text">
                    {{ block.summary || 'Summary is not available.' }}
                  </p>
                </div>

                <div class="keypoints-section">
                  <!-- Section label — no icon, plain text -->
                  <div class="section-title">Key Points</div>
                  <p v-if="!block.keyPoints || block.keyPoints.length === 0" class="fallback-text">
                    No key points available.
                  </p>
                  <ul v-else class="keypoints-list">
                    <li v-for="(pt, i) in block.keyPoints" :key="i">{{ pt }}</li>
                  </ul>
                </div>
              </div>

            </div>
          </div>
        </div>

      </div>
    </main>


    <!-- ── Full-page drag-and-drop overlay ── -->
    <!-- Shown when the user drags a file anywhere over the window -->
    <Transition name="drag-fade">
      <div v-if="isDragging" class="drag-overlay">
        <div class="drag-card">
          <div class="drag-icon">
            <svg width="36" height="36" viewBox="0 0 36 36" fill="none">
              <path d="M18 5v20M18 5L11 12M18 5l7 7" stroke="#2563eb" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M5 28h26" stroke="#2563eb" stroke-width="2.2" stroke-linecap="round"/>
            </svg>
          </div>
          <p class="drag-title">Drop your file here</p>
          <p class="drag-sub">TXT · PDF · DOCX</p>
        </div>
      </div>
    </Transition>


    <!-- ── Fixed bottom input bar ── -->
    <!-- Always visible at the bottom; contains the textarea and action buttons -->
    <div class="bottom-bar">
      <div class="bottom-bar-inner">

        <!-- Feedback strip: shows loading / success / error messages -->
        <Transition name="feedback">
          <div v-if="feedback" :class="['feedback-strip', `feedback--${feedback.type}`]">
            <div class="feedback-icon">
              <!-- Spinner for loading / uploading -->
              <svg v-if="feedback.type === 'loading' || feedback.type === 'uploading'"
                class="spin" width="14" height="14" viewBox="0 0 14 14" fill="none">
                <circle cx="7" cy="7" r="5.5" stroke="currentColor" stroke-width="1.8" stroke-dasharray="22 10" stroke-linecap="round"/>
              </svg>
              <!-- Check for success -->
              <svg v-else-if="feedback.type === 'success'" width="14" height="14" viewBox="0 0 14 14" fill="none">
                <circle cx="7" cy="7" r="6" fill="#dcfce7"/>
                <path d="M4 7l2.2 2.2 3.8-4.4" stroke="#16a34a" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              <!-- X for error -->
              <svg v-else-if="feedback.type === 'error'" width="14" height="14" viewBox="0 0 14 14" fill="none">
                <circle cx="7" cy="7" r="6" fill="#fee2e2"/>
                <path d="M4.5 4.5l5 5M9.5 4.5l-5 5" stroke="#ef4444" stroke-width="1.4" stroke-linecap="round"/>
              </svg>
            </div>
            <span class="feedback-msg">{{ feedback.message }}</span>
            <button class="feedback-close" @click="feedback = null" aria-label="Dismiss">
              <svg width="11" height="11" viewBox="0 0 11 11" fill="none">
                <path d="M2 2l7 7M9 2l-7 7" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
              </svg>
            </button>
          </div>
        </Transition>

        <!-- Input card: textarea + action buttons -->
        <div class="input-card">

          <!-- Auto-resizing textarea for text input -->
          <textarea
            ref="textareaRef"
            v-model="inputText"
            class="input-textarea"
            :class="{ 'input-textarea--over': overLimit }"
            placeholder="Type or paste your text here…"
            rows="1"
            spellcheck="false"
            @input="handleTextInput"
            @keydown="onKeydown"
          ></textarea>

          <div class="input-divider"></div>

          <!-- Action buttons row -->
          <div class="input-actions">

            <!-- Left: upload button + character counter -->
            <div class="actions-left">
              <!-- Hidden native file picker triggered by the button below -->
              <input
                ref="fileInputRef"
                type="file"
                accept=".txt,.pdf,.docx"
                style="display:none"
                @change="handleFileChange"
              />
              <button class="btn-upload" @click="triggerFileInput" title="Upload TXT, PDF or DOCX">
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                  <path d="M7 9.5V2M7 2L4 5M7 2l3 3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                  <path d="M2 10.5v1a.5.5 0 00.5.5h9a.5.5 0 00.5-.5v-1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                </svg>
                <span>Upload file</span>
              </button>

              <!-- Live character counter — turns red when over the limit -->
              <div :class="['char-count', { 'char-count--over': overLimit }]">
                <span class="char-current">{{ charCount.toLocaleString() }}</span>
                <span class="char-sep">/</span>
                <span class="char-limit">{{ charLimit.toLocaleString() }}</span>
              </div>
            </div>

            <!-- Right: clear + submit -->
            <div class="actions-right">
              <!-- Clear button only appears when there is text to clear -->
              <Transition name="fade-btn">
                <button v-if="inputText || uploadedFileText" class="btn-clear" @click="handleClear" title="Clear input">
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                    <path d="M2 2l8 8M10 2L2 10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                  </svg>
                  Clear
                </button>
              </Transition>

              <!-- Primary submit button — disabled when input is empty or over limit -->
              <button
                class="btn-submit"
                :disabled="!processingText.trim() || overLimit || mode === 'loading'"
                @click="handleSubmit"
              >
                <span v-if="mode === 'loading'" class="btn-spinner"></span>
                <template v-else>
                  Process Text
                  <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
                    <path d="M2 6.5H11M11 6.5L7 2.5M11 6.5L7 10.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                </template>
              </button>
            </div>

          </div>
        </div>

        <!-- Keyboard shortcut and drag hint -->
        <p class="bar-hint">
          <kbd>Ctrl</kbd> + <kbd>Enter</kbd> to submit
          <span class="hint-dot">·</span>
          Drag &amp; drop a file anywhere on this page
        </p>

      </div>
    </div>

  </div>
</template>


<style scoped>

/* ─────────────────────────────────────────
   Page shell
   Flexbox column so reading area stretches
   between the navbar and the fixed bottom bar.
───────────────────────────────────────── */
.page {
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
  background: #f8f9fc;
}


/* ─────────────────────────────────────────
   Navbar
───────────────────────────────────────── */
.navbar {
  flex-shrink: 0;
  position: sticky;
  top: 0;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid #e5e7eb;
  z-index: 50;
  transition: box-shadow 0.2s;
}
.navbar--scrolled { box-shadow: 0 1px 12px rgba(0, 0, 0, 0.07); }

.nav-inner {
  max-width: 1200px;
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
.nav-link:hover { color: #0d1117; background: rgba(0, 0, 0, 0.04); }
.nav-link--active { color: #0d1117; }
/* Blue dot under the active page link */
.nav-link--active::after {
  content: ''; position: absolute;
  bottom: -2px; left: 50%; transform: translateX(-50%);
  width: 4px; height: 4px;
  border-radius: 50%; background: #2563eb;
}
.nav-hamburger {
  display: none;
  background: none; border: none; cursor: pointer;
  color: #0d1117; padding: 4px; margin-left: 12px;
  align-items: center; justify-content: center;
}
.mobile-nav { display: none; }


/* ─────────────────────────────────────────
   Reading area
   Fills all space between navbar and bottom bar.
   padding-bottom clears the fixed input bar.
───────────────────────────────────────── */
.reading-area {
  flex: 1;
  padding: 32px 0 210px;
  overflow-y: auto;
}

/* Narrow width for idle/loading; full-width for results */
.reading-inner {
  max-width: 760px;
  margin: 0 auto;
  padding: 0 24px;
  transition: max-width 0.3s ease;
}
.reading-inner--wide {
  max-width: 1200px;  /* expand to full width when showing two-column result */
}


/* ─────────────────────────────────────────
   Idle / empty state
───────────────────────────────────────── */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 56px 0 0;
}
.empty-title {
  font-size: 28px; font-weight: 700;
  color: #0d1117; letter-spacing: -0.03em;
  margin: 0 0 12px;
}
.empty-sub {
  font-size: 16px; line-height: 1.7;
  color: #4b5563; margin: 0 0 40px;
  max-width: 520px;
}

/* ── Three-step process flow ── */
/* Horizontal cards with arrow connectors between them. */
.how-flow {
  display: flex;
  align-items: center;
  gap: 0;
  width: 100%;
  max-width: 680px;
  margin-bottom: 32px;
}

/* Arrow between cards */
.how-arrow {
  flex-shrink: 0;
  padding: 0 4px;
  display: flex; align-items: center; justify-content: center;
}

/* Each step card */
.how-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
  padding: 20px 18px;
  border-radius: 14px;
  border: 1.5px solid transparent;
  text-align: left;
}

/* Subtle distinct tint per step so they feel like a sequence */
.how-card--1 { background: #eff6ff; border-color: #dbeafe; }
.how-card--2 { background: #f0fdf4; border-color: #bbf7d0; }
.how-card--3 { background: #fefce8; border-color: #fef08a; }

/* Large step number badge at the top of each card */
.how-step-num {
  display: flex; align-items: center; justify-content: center;
  width: 30px; height: 30px;
  border-radius: 50%;
  font-size: 14px; font-weight: 800;
}
.how-card--1 .how-step-num { background: #2563eb; color: #fff; }
.how-card--2 .how-step-num { background: #16a34a; color: #fff; }
.how-card--3 .how-step-num { background: #ca8a04; color: #fff; }

.how-card-title {
  font-size: 15px; font-weight: 700;
  color: #0d1117; line-height: 1.3;
}
.how-card-desc {
  font-size: 13px; line-height: 1.65;
  color: #4b5563; margin: 0;
}

/* On narrow screens: stack cards vertically, hide arrows */
@media (max-width: 600px) {
  .how-flow   { flex-direction: column; max-width: 100%; }
  .how-arrow  { display: none; }
  .how-card   { width: 100%; }
}

.empty-shortcut {
  display: flex; align-items: center; gap: 6px;
  font-size: 13px; color: #9ca3af; margin: 0;
}

/* Demo button — sits below the shortcut hint */
.btn-demo {
  display: inline-flex; align-items: center; gap: 7px;
  margin-top: 20px;
  padding: 10px 28px;
  font-size: 14px; font-weight: 600;
  color: #2563eb;
  background: #eff6ff;
  border: 1.5px solid #bfdbfe;
  border-radius: 999px; cursor: pointer;
  transition: background 0.15s, border-color 0.15s, transform 0.15s;
}
.btn-demo:hover {
  background: #dbeafe; border-color: #93c5fd;
  transform: translateY(-1px);
}
kbd {
  display: inline-flex; align-items: center; justify-content: center;
  padding: 2px 7px;
  font-size: 11.5px; font-weight: 600; font-family: inherit;
  color: #374151;
  background: #f3f4f6;
  border: 1px solid #d1d5db;
  border-bottom-width: 2px;
  border-radius: 5px;
}


/* ─────────────────────────────────────────
   Loading skeleton
   Two-column skeleton that mirrors the result layout
───────────────────────────────────────── */
.loading-state {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.skeleton-header {
  display: grid;
  grid-template-columns: 2fr 3fr;
  gap: 16px;
}
.skeleton-row {
  display: grid;
  grid-template-columns: 2fr 3fr;
  gap: 16px;
}
.skeleton-block {
  display: flex; flex-direction: column; gap: 8px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 16px;
}
.skeleton-block--right { background: #fafbff; }

.skeleton {
  border-radius: 6px;
  background: linear-gradient(90deg, #eff1f5 25%, #e8eaf0 50%, #eff1f5 75%);
  background-size: 300% 100%;
  animation: shimmer 1.4s infinite;
}
.skeleton--col-title { height: 20px; width: 60%; }
.skeleton--badge     { height: 20px; width: 25%; border-radius: 999px; }
.skeleton--line      { height: 14px; }
.skeleton--sm        { height: 11px; }
@keyframes shimmer {
  0%   { background-position: 100% 0; }
  100% { background-position: -100% 0; }
}


/* ─────────────────────────────────────────
   Result state
───────────────────────────────────────── */
.result-state { display: flex; flex-direction: column; gap: 16px; }

/* Top bar: success badge + back-to-input button */
.result-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 10px;
}
.result-notice {
  display: flex; align-items: center; gap: 7px;
  font-size: 13px; font-weight: 600; color: #15803d;
}
.btn-back {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 6px 14px;
  font-size: 12.5px; font-weight: 600;
  color: #4b5563;
  background: #fff;
  border: 1px solid #d1d5db;
  border-radius: 8px; cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.btn-back:hover { background: #f3f4f6; color: #0d1117; }

/* ─────────────────────────────────────────
   Audio Control Toolbar
   Shown when any block is playing/paused.
   Slides in from the top with a transition.
───────────────────────────────────────── */
.audio-toolbar {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
  padding: 12px 16px;
  background: #fff;
  border: 1.5px solid #bfdbfe;
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(37, 99, 235, 0.08);
}

/* Slide-down enter/leave transition */
.audio-bar-enter-active { transition: opacity 0.25s ease, transform 0.25s ease; }
.audio-bar-leave-active { transition: opacity 0.18s ease, transform 0.18s ease; }
.audio-bar-enter-from   { opacity: 0; transform: translateY(-8px); }
.audio-bar-leave-to     { opacity: 0; transform: translateY(-4px); }

/* Info section: speaker icon + title + now-playing label */
.at-info {
  display: flex; align-items: center; gap: 10px;
  flex: 1; min-width: 160px;
}
.at-icon {
  width: 34px; height: 34px;
  display: flex; align-items: center; justify-content: center;
  background: #eff6ff; border-radius: 8px; flex-shrink: 0;
}
.at-title  { font-size: 12px; font-weight: 700; color: #1d4ed8; }
.at-status { font-size: 11.5px; color: #6b7280; margin-top: 1px; }
.at-paused-tag { color: #f59e0b; font-weight: 600; }

/* Action buttons (Pause/Resume, Replay) */
.at-actions { display: flex; gap: 6px; }
.at-btn {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 6px 12px;
  font-size: 12.5px; font-weight: 600; color: #4b5563;
  background: #f3f4f6; border: 1px solid #e5e7eb; border-radius: 8px;
  cursor: pointer; transition: background 0.15s, color 0.15s; white-space: nowrap;
}
.at-btn:hover { background: #e8eaf0; color: #0d1117; }
.at-btn--primary { background: #eff6ff; border-color: #93c5fd; color: #2563eb; }
.at-btn--primary:hover { background: #dbeafe; }

/* Speed / Voice selector controls */
.at-control { display: flex; flex-direction: column; gap: 3px; }
.at-label { font-size: 10.5px; font-weight: 700; color: #9ca3af; letter-spacing: 0.06em; text-transform: uppercase; }
.at-select {
  padding: 5px 8px; font-size: 12px; font-weight: 600; color: #374151;
  background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 7px;
  cursor: pointer; outline: none; transition: border-color 0.15s;
}
.at-select:focus { border-color: #93c5fd; }

/* Volume slider */
.at-volume { flex-direction: row; align-items: center; gap: 6px; flex-wrap: wrap; }
.at-slider { width: 80px; height: 4px; accent-color: #2563eb; cursor: pointer; }
.at-vol-num { font-size: 11.5px; font-weight: 600; color: #374151; min-width: 32px; }

/* Stop button — dark fill to clearly signal "stop" */
.at-btn-stop {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 6px 14px; font-size: 12.5px; font-weight: 700;
  color: #fff; background: #1f2937; border: none; border-radius: 8px;
  cursor: pointer; transition: background 0.15s; white-space: nowrap; margin-left: auto;
}
.at-btn-stop:hover { background: #111827; }


/* ─────────────────────────────────────────
   Block card header (label + play button)
───────────────────────────────────────── */
.block-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

/* Active block — blue border highlight when playing/paused */
.block-card--active {
  border-color: #93c5fd !important;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.08), 0 2px 12px rgba(0, 0, 0, 0.06) !important;
}

/* Play button with three states: idle / playing / paused */
.btn-play {
  background: none; border: none; cursor: pointer; padding: 0; line-height: 1;
}

/* Badge shared styles */
.play-badge {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 4px 10px; border-radius: 999px;
  font-size: 11.5px; font-weight: 700; white-space: nowrap;
  transition: background 0.15s, color 0.15s;
}
.play-badge--idle {
  color: #2563eb; background: #eff6ff; border: 1px solid #bfdbfe;
}
.play-badge--idle:hover { background: #dbeafe; }

.play-badge--playing {
  color: #2563eb; background: #dbeafe; border: 1px solid #93c5fd;
}
.play-badge--paused {
  color: #d97706; background: #fffbeb; border: 1px solid #fde68a;
}

/* Animated waveform bars (shown when playing) */
.wave-bar {
  display: inline-block;
  width: 3px; height: 10px;
  background: #2563eb; border-radius: 2px;
  animation: wave 0.9s ease-in-out infinite;
}
.wave-bar:nth-child(2) { animation-delay: 0.15s; }
.wave-bar:nth-child(3) { animation-delay: 0.30s; }
@keyframes wave {
  0%, 100% { transform: scaleY(0.4); }
  50%       { transform: scaleY(1.0); }
}


/* ── Result grid ── */
/*
  The outer grid defines the two-column proportion (2fr left, 3fr right).
  Both the header row and every block row share this same grid template,
  so the column widths stay perfectly consistent throughout.
*/
.result-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* Header row — two column titles side by side */
.result-grid-header {
  display: grid;
  grid-template-columns: 2fr 3fr;
  gap: 16px;
}

/*
  Each block row is also a 2fr / 3fr grid.
  align-items: stretch makes both cards grow to match the taller one,
  keeping left and right blocks visually aligned.
*/
.block-row {
  display: grid;
  grid-template-columns: 2fr 3fr;
  gap: 16px;
  align-items: stretch;
}

/* ─────────────────────────────────────────
   Collapsible original-text panel
   When .result-grid--orig-hidden is applied the left column narrows to
   a 44px clickable strip and the right (summary) column fills the rest.
───────────────────────────────────────── */

/* Narrow the left column for both the header and all block rows */
.result-grid--orig-hidden .result-grid-header,
.result-grid--orig-hidden .block-row {
  grid-template-columns: 44px 1fr;
}

/* ── Left column header toggle button ── */
/* Shares base styles with .col-header but resets browser button defaults */
.col-orig-toggle {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 13px;
  font-weight: 700;
  color: #374151;
  padding: 0 4px 8px;
  border: none;
  border-bottom: 2px solid #e5e7eb;
  background: none;
  cursor: pointer;
  font-family: inherit;
  text-align: left;
  transition: color 0.15s, border-color 0.15s;
  width: 100%;
}
.col-orig-toggle:hover {
  color: #2563eb;
  border-color: #93c5fd;
}

.col-toggle-arrow { flex-shrink: 0; }

/* In collapsed mode, stack icon + rotated label vertically */
.result-grid--orig-hidden .col-orig-toggle {
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  padding: 6px 0 8px;
  gap: 6px;
}

/* Rotated "Original" text shown in the collapsed header strip */
.col-orig-label-vert {
  writing-mode: vertical-rl;
  transform: rotate(180deg);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #9ca3af;
  white-space: nowrap;
}

/* ── Collapsed left block cards ── */
/* When collapsed, hide the normal content and show only the strip */
.result-grid--orig-hidden .block-card--left {
  padding: 10px 4px;
  cursor: pointer;
  align-items: center;
  justify-content: center;
  border-style: dashed; /* visual cue that the panel is collapsed/hidden */
  min-height: 80px;
}
.result-grid--orig-hidden .block-card--left:hover {
  border-color: #93c5fd;
  background: #f0f6ff;
}

/* Strip hint: icon + rotated block label, stacked vertically inside the narrow card */
.orig-strip-hint {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 100%;
  min-height: 60px;
  width: 100%;
}

/* Rotated "B1 / B2 / B3" label inside each collapsed block strip */
.orig-strip-label {
  writing-mode: vertical-rl;
  transform: rotate(180deg);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #b0b8cc;
}

/* ── Mobile: hide the strip entirely, just stack normally ── */
@media (max-width: 860px) {
  /* Revert narrow columns — mobile already stacks to 1fr */
  .result-grid--orig-hidden .result-grid-header,
  .result-grid--orig-hidden .block-row {
    grid-template-columns: 1fr;
  }
  /* Hide the collapsed left cards on mobile to avoid a confusing stub */
  .result-grid--orig-hidden .block-card--left {
    display: none;
  }
}

/* Column header label */
.col-header {
  display: flex; align-items: center; gap: 7px;
  font-size: 13px; font-weight: 700;
  color: #374151;
  padding: 0 4px 8px;
  border-bottom: 2px solid #e5e7eb;
}
.col-header-sub {
  font-size: 12px; font-weight: 500; color: #9ca3af;
}

/* ── Block cards ── */
.block-card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  transition: box-shadow 0.2s;
}
.block-card:hover { box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06); }
.block-card--right {
  background: #fafbff;
  border-color: #e0e8ff;
}

/* "Block X" label badge */
.block-label {
  display: inline-flex;
  padding: 3px 10px;
  font-size: 11.5px; font-weight: 700;
  color: #2563eb;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 999px;
  align-self: flex-start;
}

/* Original text — smaller font to de-emphasise vs the summary */
.block-text { font-size: 13.5px; line-height: 1.7; color: #374151; margin: 0; }
.block-text--small { font-size: 13px; color: #4b5563; }

/*
  Clamp the left-side text to 7 lines by default.
  If the text fits within 7 lines, it shows fully — no button appears.
  If it overflows, the JS checkClamp() detects it and shows the Read more button.
*/
.block-text--clamped {
  display: -webkit-box;
  -webkit-line-clamp: 7;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* Read more / Show less toggle */
.btn-toggle {
  align-self: flex-start;
  font-size: 12.5px; font-weight: 600;
  color: #2563eb;
  background: none; border: none; cursor: pointer; padding: 0;
  transition: color 0.15s;
}
.btn-toggle:hover { color: #1d4ed8; }

/* Summary and key points sections inside the right card */
.summary-section,
.keypoints-section { display: flex; flex-direction: column; gap: 6px; }

.keypoints-section { margin-top: 4px; }

/* Section label (e.g. "Summary", "Key Points") */
.section-title {
  display: flex; align-items: center; gap: 6px;
  font-size: 11.5px; font-weight: 700;
  letter-spacing: 0.06em; text-transform: uppercase;
  color: #6b7280;
}

.summary-text {
  font-size: 13.5px; line-height: 1.65;
  color: #1f2937; margin: 0;
}

/* Key points bullet list */
.keypoints-list {
  margin: 0; padding: 0;
  list-style: none;
  display: flex; flex-direction: column; gap: 5px;
}
.keypoints-list li {
  font-size: 13px; line-height: 1.6; color: #374151;
  padding-left: 14px; position: relative;
}
.keypoints-list li::before {
  content: '•';
  position: absolute; left: 0;
  color: #2563eb; font-weight: 700;
}

/* Fallback text for missing summary or key points */
.fallback-text {
  font-size: 13px; color: #9ca3af;
  font-style: italic; margin: 0;
}


/* ─────────────────────────────────────────
   Drag-and-drop overlay
───────────────────────────────────────── */
.drag-overlay {
  position: fixed; inset: 0;
  background: rgba(37, 99, 235, 0.08);
  backdrop-filter: blur(3px);
  -webkit-backdrop-filter: blur(3px);
  z-index: 200;
  display: flex; align-items: center; justify-content: center;
}
.drag-card {
  display: flex; flex-direction: column; align-items: center; gap: 12px;
  padding: 48px 64px;
  background: #fff;
  border: 2px dashed #93c5fd;
  border-radius: 20px;
  box-shadow: 0 24px 64px rgba(37, 99, 235, 0.14);
}
.drag-icon {
  width: 72px; height: 72px;
  display: flex; align-items: center; justify-content: center;
  background: #eff6ff; border-radius: 50%;
}
.drag-title { font-size: 20px; font-weight: 700; color: #0d1117; margin: 0; }
.drag-sub   { font-size: 13.5px; color: #6b7280; margin: 0; font-weight: 500; letter-spacing: 0.05em; }


/* ─────────────────────────────────────────
   Fixed bottom input bar
───────────────────────────────────────── */
.bottom-bar {
  position: fixed;
  bottom: 0; left: 0; right: 0;
  background: rgba(248, 249, 252, 0.96);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border-top: 1px solid #e5e7eb;
  box-shadow: 0 -4px 30px rgba(0, 0, 0, 0.07);
  z-index: 100;
  padding: 12px 0 14px;
}
.bottom-bar-inner {
  max-width: 760px;
  margin: 0 auto;
  padding: 0 24px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}


/* ─── Feedback strip ─── */
.feedback-strip {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 12px;
  border-radius: 10px;
  font-size: 13px; font-weight: 500;
  line-height: 1.4;
}
.feedback--loading,
.feedback--uploading { background: #eff6ff; border: 1px solid #bfdbfe; color: #1d4ed8; }
.feedback--success   { background: #f0fdf4; border: 1px solid #bbf7d0; color: #15803d; }
.feedback--error     { background: #fef2f2; border: 1px solid #fecaca; color: #b91c1c; }
.feedback-icon { flex-shrink: 0; display: flex; }
.feedback-msg  { flex: 1; }
.feedback-close {
  flex-shrink: 0; display: flex; align-items: center; justify-content: center;
  width: 22px; height: 22px;
  background: none; border: none; cursor: pointer;
  color: inherit; opacity: 0.55; border-radius: 4px; transition: opacity 0.15s;
}
.feedback-close:hover { opacity: 1; }


/* ─── Input card ─── */
.input-card {
  background: #fff;
  border: 1.5px solid #e5e7eb;
  border-radius: 14px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  transition: border-color 0.2s, box-shadow 0.2s;
  overflow: hidden;
}
/* Blue focus ring when anything inside the card is focused */
.input-card:focus-within {
  border-color: #93c5fd;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05), 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.input-textarea {
  display: block; width: 100%;
  min-height: 46px; max-height: 180px;
  padding: 14px 16px 8px;
  font-size: 14.5px; line-height: 1.65;
  font-family: inherit; color: #1f2937;
  background: transparent;
  border: none; outline: none; resize: none;
  box-sizing: border-box; overflow-y: auto;
}
.input-textarea::placeholder { color: #b8bfd0; }
.input-textarea--over        { color: #ef4444; } /* red text when over character limit */

.input-divider { height: 1px; background: #f3f4f6; margin: 0 12px; }

.input-actions {
  display: flex; align-items: center;
  justify-content: space-between;
  padding: 8px 10px 10px; gap: 8px;
}
.actions-left,
.actions-right { display: flex; align-items: center; gap: 8px; }

/* Upload button */
.btn-upload {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 6px 12px;
  font-size: 12.5px; font-weight: 600; color: #4b5563;
  background: #f3f4f6; border: 1px solid #e5e7eb;
  border-radius: 8px; cursor: pointer;
  transition: background 0.15s, color 0.15s; white-space: nowrap;
}
.btn-upload:hover { background: #e9eaf0; color: #111827; border-color: #d1d5db; }

/* Character counter */
.char-count { display: flex; align-items: center; gap: 2px; font-size: 12px; font-weight: 600; }
.char-current { color: #9ca3af; }
.char-sep, .char-limit { color: #d1d5db; }
.char-count--over .char-current { color: #ef4444; }

/* Clear button */
.btn-clear {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 6px 12px;
  font-size: 12.5px; font-weight: 600; color: #6b7280;
  background: transparent; border: 1px solid #e5e7eb;
  border-radius: 8px; cursor: pointer; transition: all 0.15s;
}
.btn-clear:hover { background: #fef2f2; color: #ef4444; border-color: #fecaca; }

/* Primary submit button */
.btn-submit {
  display: inline-flex; align-items: center; gap: 7px;
  padding: 8px 22px;
  font-size: 13.5px; font-weight: 700; color: #fff;
  background: #2563eb; border: none; border-radius: 999px; cursor: pointer;
  box-shadow: 0 4px 14px rgba(37, 99, 235, 0.32);
  transition: background 0.2s, transform 0.15s, box-shadow 0.15s;
  white-space: nowrap;
}
.btn-submit:hover:not(:disabled) {
  background: #1d4ed8; transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(37, 99, 235, 0.40);
}
.btn-submit:disabled { opacity: 0.42; cursor: not-allowed; transform: none; box-shadow: none; }

/* Spinner inside the submit button while loading */
.btn-spinner {
  display: inline-block;
  width: 14px; height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.35);
  border-top-color: #fff; border-radius: 50%;
  animation: spin 0.65s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* Spinning animation used on feedback icons */
.spin { animation: spin 0.9s linear infinite; transform-origin: center; }

/* Hint row below the input card */
.bar-hint {
  display: flex; align-items: center; justify-content: center; gap: 6px;
  font-size: 11.5px; color: #b0b8cc; margin: 0; flex-wrap: wrap;
}
.bar-hint kbd { font-size: 10.5px; padding: 1px 5px; color: #9ca3af; background: #f3f4f6; border-color: #e5e7eb; }
.hint-dot { color: #d1d5db; }


/* ─────────────────────────────────────────
   Transitions
───────────────────────────────────────── */
.drag-fade-enter-active,
.drag-fade-leave-active { transition: opacity 0.2s ease; }
.drag-fade-enter-from,
.drag-fade-leave-to    { opacity: 0; }

.feedback-enter-active { transition: all 0.22s ease; }
.feedback-leave-active { transition: all 0.18s ease; }
.feedback-enter-from   { opacity: 0; transform: translateY(6px); }
.feedback-leave-to     { opacity: 0; transform: translateY(4px); }

.fade-btn-enter-active { transition: all 0.18s ease; }
.fade-btn-leave-active { transition: all 0.14s ease; }
.fade-btn-enter-from   { opacity: 0; transform: scale(0.9); }
.fade-btn-leave-to     { opacity: 0; transform: scale(0.9); }


/* ─────────────────────────────────────────
   Responsive styles
───────────────────────────────────────── */

/* Tablet: switch to hamburger menu */
@media (max-width: 860px) {
  .nav-links     { display: none; }
  .nav-hamburger { display: flex; }
  .nav-inner     { padding: 0 16px; }

  .mobile-nav {
    display: block;
    position: fixed; top: 64px; left: 0; right: 0;
    background: rgba(255, 255, 255, 0.98);
    backdrop-filter: blur(18px);
    border-bottom: 1px solid #e5e7eb; z-index: 99;
  }
  .mobile-nav-links { list-style: none; margin: 0; padding: 0; }
  .mobile-nav-link {
    display: block; padding: 16px 24px;
    font-size: 16px; font-weight: 500; color: #374151;
    text-decoration: none; border-bottom: 1px solid #f3f4f6; transition: background 0.15s;
  }
  .mobile-nav-link:hover { background: #f9fafb; color: #0d1117; }

  /* Stack the two result columns on tablet */
  .result-grid-header,
  .block-row       { grid-template-columns: 1fr; }
  .skeleton-header,
  .skeleton-row    { grid-template-columns: 1fr; }
}

/* Mobile: further layout adjustments */
@media (max-width: 600px) {
  .reading-area { padding-bottom: 260px; }
  .empty-title  { font-size: 18px; }
  .empty-features { gap: 6px; }

  /* Stack input action buttons vertically */
  .input-actions { flex-direction: column; align-items: stretch; gap: 10px; }
  .actions-left  { justify-content: space-between; }
  .actions-right { justify-content: flex-end; }
  .btn-submit    { flex: 1; justify-content: center; }

  .bar-hint  { display: none; }  /* hide hint row to save space */
  .drag-card { padding: 36px 28px; }
}
</style>
