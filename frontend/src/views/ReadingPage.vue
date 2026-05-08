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

// Holds the processed result returned by the backend.
//
// ── Expected shape (iteration3 updated API) ──────────────────────────────────
// {
//   title: '...'                   (optional) article title shown as tree root node
//   overallSummary: {              (NEW in iteration3 — backend must provide this)
//     heading: '...',              large heading shown in Stage 1 card
//     text:    '...'               paragraph text shown in Stage 1 card
//   },
//   blocks: [                      array of sections/paragraphs
//     {
//       id:           1,           section number
//       title:        '...',       (NEW) section name shown as tree node label
//       subtitle:     '...',       (NEW) one-line description shown under node label
//       originalText: '...',       original text from the article (kept for backward compat)
//       summary:      '...',       plain-English summary shown in the detail modal
//       keyPoints:    ['...', '...'] bullet points shown in the detail modal
//     },
//     ...
//   ],
//   notice: '...' (optional)
// }
//
// Backward-compatibility notes:
//   - If overallSummary is missing, we fall back to the first block's summary.
//   - If block.title is missing, we show "Section {id}" as the node label.
// ─────────────────────────────────────────────────────────────────────────────
const result = ref(null)


// ── Overall summary (computed from backend response) ──────────────────────────
// Backend should provide result.overallSummary directly (iteration3 API).
// Falls back to the first block's data for compatibility with older responses.
const overallSummary = computed(() => {
  if (!result.value) return null
  if (result.value.overallSummary) return result.value.overallSummary
  const first = result.value.blocks?.[0]
  return first
    ? { heading: first.title || 'Summary', text: first.summary || '' }
    : null
})


// ── Section detail modal ──────────────────────────────────────────────────────
// activeSection holds the block the user clicked in the tree.
// null = modal closed; a block object = modal open showing that section.
const activeSection = ref(null)

/** Opens the section detail modal for the given block. Stops TTS first. */
function openSection(block) {
  stopAudio()
  activeSection.value = block
}

/** Closes the section detail modal and stops any playing TTS. */
function closeSection() {
  stopAudio()
  activeSection.value = null
}


// ── Demo data ─────────────────────────────────────────────────────────────────
// Sample data that matches the exact shape the backend will return.
// Used by loadDemo() so the new UI can be previewed without a real API call.
// When the backend is updated to return overallSummary + block titles,
// the real data will flow through exactly the same code paths.
const DEMO_RESULT = {
  title: 'Clearead – Iteration 1 Analysis and Design Plan',
  overallSummary: {
    heading: 'Making academic reading easier for students with dyslexia.',
    text: 'This report presents the analysis and design plan for Iteration 1 of Clearead. It aims to help Australian university students with dyslexia by turning dense academic texts into clearer, more structured, and more accessible formats.',
  },
  blocks: [
    {
      id: 1, title: 'Introduction', subtitle: 'Background and context',
      originalText: 'Clearead was designed to help students with dyslexia navigate university-level reading.',
      summary: 'Clearead was designed to help university students with dyslexia who struggle with dense academic texts. The project grew out of research showing that 1 in 5 Australians has dyslexia, yet most academic platforms offer no reading support.',
      keyPoints: ['1 in 5 Australians are affected by dyslexia.', 'Academic platforms rarely offer reading accessibility tools.', 'Clearead aims to bridge this gap for university students.'],
    },
    {
      id: 2, title: 'Problem Definition', subtitle: 'Understanding the challenge',
      originalText: 'Dense academic text is a significant barrier for students with dyslexia.',
      summary: 'Dense academic text is a significant barrier for students with dyslexia. Complex sentence structures, unfamiliar vocabulary, and lack of structure make it difficult to understand and engage with the content.',
      keyPoints: ['Academic texts are written for a general audience, not students with dyslexia.', 'Long sentences and complex words increase cognitive load.', 'Students may spend more time reading but retain less.', 'There is a lack of accessible tools for university academic reading.'],
    },
    {
      id: 3, title: 'Target Audience', subtitle: 'Who we are designing for',
      originalText: 'The primary users are Australian university students aged 18 to 22.',
      summary: 'The primary users are Australian university students aged 18 to 22 who have been diagnosed with dyslexia or experience reading difficulties.',
      keyPoints: ['Age range: 18–22 years old.', 'Enrolled in Australian universities.', 'Diagnosed with dyslexia or experiencing reading difficulties.', 'Regular users of digital academic content.'],
    },
    {
      id: 4, title: 'Design Goals', subtitle: 'What we aim to achieve',
      originalText: 'Clearead aims to reduce cognitive load and improve reading comprehension.',
      summary: 'Clearead aims to reduce cognitive load, improve reading comprehension, and provide a calm, structured reading experience that adapts to the needs of dyslexic users.',
      keyPoints: ['Reduce cognitive load through chunked, summarised content.', 'Provide multiple reading modes: visual and audio.', 'Use dyslexia-friendly typography and colour schemes.', 'Enable users to control reading speed and text size.'],
    },
    {
      id: 5, title: 'Approach & Solution', subtitle: 'How we will solve it',
      originalText: 'The solution involves an AI-powered text processing pipeline.',
      summary: 'The solution involves an AI-powered text processing pipeline that breaks long documents into manageable sections, generates plain-English summaries, and provides audio playback for each section.',
      keyPoints: ['AI pipeline segments text into logical blocks.', 'Each block receives a plain-English summary.', 'Text-to-speech is available for every section.', 'Users can adjust font, size, and colour for accessibility.'],
    },
    {
      id: 6, title: 'Evaluation Plan', subtitle: 'How we will test and improve',
      originalText: 'The evaluation plan includes user testing with dyslexic university students.',
      summary: 'The evaluation plan includes user testing with dyslexic university students, measuring reading comprehension scores, and gathering qualitative feedback on the usability of the tool.',
      keyPoints: ['User testing with 5–8 participants with dyslexia.', 'Pre/post comprehension tests to measure improvement.', 'Qualitative interviews to gather usability feedback.', 'Iterative improvements based on test results.'],
    },
    {
      id: 7, title: 'Risks & Considerations', subtitle: 'Potential risks and limitations',
      originalText: 'Key risks include AI summarisation inaccuracies and browser compatibility issues.',
      summary: 'Key risks include AI summarisation inaccuracies, browser compatibility issues with text-to-speech, and the challenge of designing for the broad spectrum of dyslexia experiences.',
      keyPoints: ['AI may occasionally produce inaccurate summaries.', 'Text-to-speech support varies across browsers.', 'Dyslexia affects individuals differently — no one-size-fits-all solution.', 'Privacy considerations for uploaded document content.'],
    },
    {
      id: 8, title: 'Next Steps', subtitle: 'What happens next',
      originalText: 'The next iteration will focus on refining the AI summarisation model.',
      summary: 'The next iteration will focus on refining the AI summarisation model, expanding accessibility settings, and conducting a second round of user testing with a larger participant group.',
      keyPoints: ['Refine AI model based on evaluation feedback.', 'Add more accessibility customisation options.', 'Conduct second round of user testing.', 'Prepare for public beta release.'],
    },
  ],
}

/**
 * Loads demo data so the redesigned UI can be previewed without a backend call.
 * Mirrors the exact shape POST /api/process-text will return in iteration3.
 */
function loadDemo() {
  stopAudio()
  result.value      = DEMO_RESULT
  mode.value        = 'result'
  activeSection.value = null
}


// ── Overall Summary playback ──────────────────────────────────────────────────
// We use block ID 0 as a virtual sentinel for the overall summary card.
// Real block IDs from the backend start at 1, so 0 is safe.
const OVERALL_SUMMARY_ID = 0

/**
 * Plays (or pauses / resumes) the overall summary using TTS.
 * Reuses the same playback state machine as individual block playback.
 */
async function playOverallSummary() {
  if (!overallSummary.value) return

  // Build the text: heading + body paragraph joined as a sentence
  const text = [overallSummary.value.heading, overallSummary.value.text]
    .filter(Boolean).join('. ')

  const isSame = activeBlockId.value === OVERALL_SUMMARY_ID

  // Toggle play/pause if already active
  if (isSame && playbackState.value === 'playing') { pauseAudio();  return }
  if (isSame && playbackState.value === 'paused')  { resumeAudio(); return }

  // Stop whatever is currently playing and start fresh
  stopAudio()
  activeBlockId.value   = OVERALL_SUMMARY_ID
  activeBlockType.value = 'summary'
  playbackState.value   = 'playing'

  try {
    await requestTTS(text)
    if (activeBlockId.value === OVERALL_SUMMARY_ID) stopAudio()
  } catch (err) {
    console.error('[TTS] Overall summary playback error:', err)
    stopAudio()
  }
}


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
  const isClamped = el.scrollHeight > el.clientHeight + 2  // +2px to avoid sub-pixel false positives
  // Only update if the value actually changed — prevents an infinite render loop
  // where assigning clampedBlocks.value triggers a re-render which calls checkClamp again.
  if (clampedBlocks.value[id] === isClamped) return
  clampedBlocks.value = {
    ...clampedBlocks.value,
    [id]: isClamped,
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

// Voice preference keys shown in the toolbar dropdown.
// These are mapped to actual browser SpeechSynthesisVoice objects by getSelectedVoice().
const VOICE_OPTIONS  = [
  { value: 'default-female', label: 'Default Female' },
  { value: 'default-male',   label: 'Default Male'   },
  { value: 'calm-female',    label: 'Calm Female'    },
  { value: 'clear-male',     label: 'Clear Male'     },
]

// Browser voices loaded asynchronously via the Web Speech API
const availableVoices = ref([])

function loadVoices() {
  if (!('speechSynthesis' in window)) return
  availableVoices.value = window.speechSynthesis.getVoices()
}

/**
 * Returns the best matching SpeechSynthesisVoice for the user's preference.
 * Searches English voices by common name patterns for male / female voices.
 */
function getSelectedVoice() {
  // Only look at English voices
  const en = availableVoices.value.filter(v => v.lang.startsWith('en'))
  if (!en.length) return null

  const pref = selectedVoice.value

  if (pref === 'default-female' || pref === 'calm-female') {
    // Common female voice name keywords across Windows / macOS / Chrome
    return (
      en.find(v => /zira|victoria|samantha|karen|moira|fiona|female|woman/i.test(v.name)) ||
      en[0]
    )
  }

  if (pref === 'default-male' || pref === 'clear-male') {
    // Common male voice name keywords
    return (
      en.find(v => /david|mark|daniel|alex|james|george|male|man/i.test(v.name)) ||
      en[0]
    )
  }

  return en[0]
}

// ── TTS via Browser Web Speech API ───────────────────────────────────────────
//
// Uses the browser's built-in SpeechSynthesis — no backend required.
// Works in Chrome, Edge, and Safari. Firefox support is partial.
//
// The Promise resolves ONLY when speech actually ends (onend).
// Resolving early (before onend) would cause playBlock() to immediately
// call stopAudio(), cancelling the speech before it finishes — the
// original bug that made TTS appear broken.

/**
 * Speak text using the Web Speech API.
 * Returns a Promise that resolves when the utterance naturally finishes,
 * or when it is cancelled programmatically (treated as a clean stop).
 */
function requestTTS(text) {
  return new Promise((resolve, reject) => {
    if (!('speechSynthesis' in window)) {
      reject(new Error('Text-to-speech is not supported in this browser.'))
      return
    }

    const synth     = window.speechSynthesis
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.lang   = 'en-US'
    utterance.rate   = playbackSpeed.value
    utterance.volume = volume.value / 100

    // Apply the selected browser voice (mapped from user preference to real voice object)
    const voice = getSelectedVoice()
    if (voice) utterance.voice = voice

    // Resolve when speech ends naturally
    utterance.onend = () => resolve('done')

    // 'interrupted' / 'canceled' fire when stopAudio() calls speechSynthesis.cancel().
    // Treat them as a normal clean stop, not an error.
    utterance.onerror = (e) => {
      if (e.error === 'interrupted' || e.error === 'canceled') {
        resolve('cancelled')
      } else {
        console.warn('[TTS] Speech error:', e.error)
        reject(new Error(e.error))
      }
    }

    // ⚠️ Chrome bug: calling cancel() + speak() in the same synchronous block
    // causes the new utterance to immediately receive an 'interrupted' error.
    // stopAudio() already called cancel() before we get here, so we must NOT
    // call cancel() again. We also defer speak() by 50 ms so Chrome has time
    // to flush the previous cancellation before queuing the new utterance.
    setTimeout(() => synth.speak(utterance), 50)
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

  // New block / different side — stop anything currently playing first
  stopAudio()
  activeBlockId.value   = blockId
  activeBlockType.value = textType
  playbackState.value   = 'playing'

  // Build the text to speak depending on which card was clicked
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
    // Await speech completion — state resets to idle only after speech ends
    await requestTTS(textToSpeak)
    // Only reset if this block is still the active one (user may have moved on)
    if (activeBlockId.value === blockId) stopAudio()
  } catch (err) {
    console.error('[TTS] Playback error:', err)
    stopAudio()
  }
}

/** Pause the current playback. */
function pauseAudio() {
  if ('speechSynthesis' in window) window.speechSynthesis.pause()
  playbackState.value = 'paused'
}

/** Resume a paused playback. */
function resumeAudio() {
  if ('speechSynthesis' in window) window.speechSynthesis.resume()
  playbackState.value = 'playing'
}

/** Replay the currently active block (same side) from the beginning. */
function replayBlock() {
  if (activeBlockId.value !== null) playBlock(activeBlockId.value, activeBlockType.value)
}

/** Stop all playback and reset to idle. */
function stopAudio() {
  if ('speechSynthesis' in window) window.speechSynthesis.cancel()
  activeBlockId.value   = null
  activeBlockType.value = 'original'
  playbackState.value   = 'idle'
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

  // Clear the input box immediately after capturing the text.
  // We also directly reset the textarea DOM height so it collapses
  // right away — reactive updates alone can lag on larger content.
  inputText.value        = ''
  uploadedFileText.value = ''
  uploadedFileName.value = ''
  if (textareaRef.value) {
    textareaRef.value.value = ''         // force-clear the native element
    textareaRef.value.style.height = 'auto'  // collapse immediately
  }
  await nextTick()
  autoResize()   // recalculate to the correct min height

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

  // Load browser voices — they populate asynchronously after page load.
  // voiceschanged fires once the list is ready (required in Chrome).
  loadVoices()
  if ('speechSynthesis' in window) {
    window.speechSynthesis.onvoiceschanged = loadVoices
  }
})
onUnmounted(() => {
  window.removeEventListener('scroll', onScroll)
  clearTimeout(feedbackTimer)
  if ('speechSynthesis' in window) {
    window.speechSynthesis.onvoiceschanged = null
    window.speechSynthesis.cancel()
  }
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
          <li><RouterLink to="/dyslexia" class="nav-link">Understand Dyslexia</RouterLink></li>
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
        <li><RouterLink to="/dyslexia" class="mobile-nav-link" @click="menuOpen = false">Understand Dyslexia</RouterLink></li>
        <li><RouterLink to="/training" class="mobile-nav-link" @click="menuOpen = false">Training</RouterLink></li>
      </ul>
    </div>


    <!-- ── Main reading area ── -->
    <main :class="['reading-area', { 'reading-area--no-bar': mode === 'result' }]">
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

          <!-- Demo CTA: lets users preview the full UI without real content -->
          <div class="demo-cta">
            <span class="demo-cta-text">Want to see how it looks?</span>
            <button class="btn-demo" @click="loadDemo">Try Demo →</button>
          </div>

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


        <!-- ── STATE: result — 3-stage guided reading flow ── -->
        <!--
          Stage 1: Overall Summary Card  — green, centered, with TTS play button
          Stage 2: Section Tree          — root node → trunk → clickable section cards
          Stage 3: Section Detail Modal  — opens when a tree card is clicked
        -->
        <div v-else-if="mode === 'result' && result" class="result-state">

          <!-- Top status bar: success notice + back button -->
          <div class="result-topbar">
            <div class="result-notice">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <circle cx="7" cy="7" r="6" fill="#dcfce7" stroke="#16a34a" stroke-width="1"/>
                <path d="M4 7l2.2 2.2 3.8-4.4" stroke="#16a34a" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              Text processed successfully.
            </div>
            <button class="btn-back" @click="handleBackToInput">
              <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
                <path d="M11 6.5H2M2 6.5L6 2.5M2 6.5L6 10.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              Back to Input
            </button>
          </div>

          <!-- ══════════════════════════════════════════════════════════════
               STAGE 1 · Overall Summary
               Fills the full viewport. Reader sees ONLY this section on load.
               A bouncing arrow at the bottom prompts scrolling to Stage 2.
          ══════════════════════════════════════════════════════════════ -->
          <div class="stage-summary">

            <!-- Small pill label at the top -->
            <div class="stage-header">
              <span class="stage-pill stage-pill--green">
                <!-- Green dot -->
                <svg width="7" height="7" viewBox="0 0 7 7" fill="none">
                  <circle cx="3.5" cy="3.5" r="3.5" fill="currentColor"/>
                </svg>
                Overview
              </span>
            </div>

            <!--
              Main card: white background with green left-accent border.
              Play button is part of the card flow (below the body text),
              not absolutely positioned, so it reads naturally.
            -->
            <div class="overall-card">

              <!-- Large document-level heading -->
              <h2 class="overall-heading">{{ overallSummary?.heading }}</h2>

              <!-- Supporting body paragraph -->
              <p class="overall-body">{{ overallSummary?.text }}</p>

              <!-- Audio row: play/pause/resume + inline speed when active -->
              <div class="overall-audio-row">
                <button
                  class="overall-play-btn"
                  :class="{
                    'overall-play-btn--playing': activeBlockId === OVERALL_SUMMARY_ID && playbackState === 'playing',
                    'overall-play-btn--paused':  activeBlockId === OVERALL_SUMMARY_ID && playbackState === 'paused',
                  }"
                  :aria-label="activeBlockId === OVERALL_SUMMARY_ID && playbackState === 'playing' ? 'Pause overview' : 'Play overview'"
                  @click="playOverallSummary"
                >
                  <!-- Waveform when playing -->
                  <template v-if="activeBlockId === OVERALL_SUMMARY_ID && playbackState === 'playing'">
                    <span class="wave-bar wave-bar--white"></span>
                    <span class="wave-bar wave-bar--white"></span>
                    <span class="wave-bar wave-bar--white"></span>
                    Pause
                  </template>
                  <!-- Resume when paused -->
                  <template v-else-if="activeBlockId === OVERALL_SUMMARY_ID && playbackState === 'paused'">
                    <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
                      <path d="M3 1.5l9 5-9 5V1.5z" fill="currentColor"/>
                    </svg>
                    Resume
                  </template>
                  <!-- Default: play icon -->
                  <template v-else>
                    <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
                      <path d="M3 1.5l9 5-9 5V1.5z" fill="currentColor"/>
                    </svg>
                    Listen to Overview
                  </template>
                </button>

                <!-- Speed selector: only visible when actively playing/paused -->
                <div
                  v-if="activeBlockId === OVERALL_SUMMARY_ID && playbackState !== 'idle'"
                  class="overall-speed"
                >
                  <select v-model="playbackSpeed" class="overall-speed-select">
                    <option v-for="s in SPEED_OPTIONS" :key="s" :value="s">{{ s }}x</option>
                  </select>
                  <button class="overall-stop-btn" @click="stopAudio">■ Stop</button>
                </div>
              </div>

            </div><!-- /overall-card -->

          </div><!-- /stage-summary -->


          <!-- ══════════════════════════════════════════════════════════════
               STAGE 2 · Section Grid
               A bridge label connects the overview to the section cards.
               Clicking a card opens the Stage 3 detail modal.
          ══════════════════════════════════════════════════════════════ -->
          <div class="stage-tree">

            <!-- Bridge: thin rule + "N Sections" label + thin rule -->
            <div class="sections-bridge" aria-hidden="true">
              <div class="sections-bridge-line"></div>
              <span class="sections-bridge-label">
                {{ result.blocks?.length || 0 }} Sections
              </span>
              <div class="sections-bridge-line"></div>
            </div>

            <!--
              Sections container: a single bordered box that groups ALL cards.
              This makes clear that every card is a parallel sibling — no hierarchy implied.
              Inside, cards are laid out in a simple grid with no branch lines.
            -->
            <div class="tree-container">
            <div class="tree-nodes">
              <div
                v-for="block in result.blocks"
                :key="block.id"
                class="tree-node"
                role="button"
                tabindex="0"
                :aria-label="`Open section ${block.id}: ${block.title || ''}`"
                @click="openSection(block)"
                @keydown.enter.space.prevent="openSection(block)"
              >
                <!-- Section number circle badge -->
                <div class="tree-node-num">{{ block.id }}</div>

                <!-- Section title and subtitle -->
                <div class="tree-node-content">
                  <div class="tree-node-title">{{ block.title || `Section ${block.id}` }}</div>
                  <div v-if="block.subtitle" class="tree-node-subtitle">{{ block.subtitle }}</div>
                </div>

                <!-- Right-arrow: visual cue that the card is clickable -->
                <svg class="tree-node-arrow" width="14" height="14" viewBox="0 0 14 14" fill="none">
                  <path d="M3 7h8M7 3.5l3.5 3.5L7 10.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </div>
            </div><!-- /tree-nodes -->
            </div><!-- /tree-container -->

          </div><!-- /stage-tree -->

        </div><!-- /result-state -->

      </div><!-- /reading-inner -->
    </main>


    <!-- ══════════════════════════════════════════════════════════════════════
         STAGE 3 · Section Detail Modal
         Opens when the user clicks a section card in the tree.
         Contains: section title/subtitle, 2-column body (summary + key points),
         and compact TTS audio controls.
         Clicking the semi-transparent backdrop closes the modal.
    ══════════════════════════════════════════════════════════════════════ -->
    <Transition name="modal-fade">
      <div
        v-if="activeSection"
        class="modal-backdrop"
        role="dialog"
        :aria-label="`Section ${activeSection.id} – ${activeSection.title || 'detail'}`"
        @click.self="closeSection"
      >
        <div class="modal-panel">

          <!-- ── Modal header ── -->
          <div class="modal-header">

            <!-- Circular section number badge -->
            <div class="modal-section-num">{{ activeSection.id }}</div>

            <!-- Title + subtitle -->
            <div class="modal-title-group">
              <h3 class="modal-title">{{ activeSection.title || `Section ${activeSection.id}` }}</h3>
              <p v-if="activeSection.subtitle" class="modal-subtitle">{{ activeSection.subtitle }}</p>
            </div>

            <!-- Close button (×) -->
            <button class="modal-close-btn" @click="closeSection" aria-label="Close section detail">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <path d="M2 2l10 10M12 2L2 12" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
              </svg>
            </button>
          </div>

          <!-- ── Modal body: Summary (left) + Key Points (right) ── -->
          <div class="modal-body">

            <!-- Left column: plain-English paragraph summary -->
            <div class="modal-col">
              <div class="modal-col-label">Summary</div>
              <p class="modal-summary-text">{{ activeSection.summary || 'Summary not available.' }}</p>
            </div>

            <!-- Thin vertical divider between the two columns -->
            <div class="modal-divider" aria-hidden="true"></div>

            <!-- Right column: bullet-point key ideas -->
            <div class="modal-col">
              <div class="modal-col-label">Key Points</div>
              <p v-if="!activeSection.keyPoints?.length" class="modal-fallback">
                No key points available.
              </p>
              <ul v-else class="modal-keypoints">
                <li v-for="(pt, i) in activeSection.keyPoints" :key="i">{{ pt }}</li>
              </ul>
            </div>

          </div><!-- /modal-body -->

          <!-- ── Modal audio bar ── -->
          <!-- Compact TTS controls scoped to this section only -->
          <div class="modal-audio">

            <!-- Playback status: waveform when active, speaker icon when idle -->
            <div class="modal-audio-status">
              <template v-if="activeBlockId === activeSection.id && playbackState !== 'idle'">
                <span class="wave-bar"></span>
                <span class="wave-bar"></span>
                <span class="wave-bar"></span>
                <span class="modal-audio-label">
                  {{ playbackState === 'playing' ? 'Playing…' : 'Paused' }}
                </span>
              </template>
              <template v-else>
                <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
                  <path d="M1.5 4H4l3-2.5v9L4 8H1.5V4z" fill="#2563eb"/>
                  <path d="M9 3.5a4 4 0 0 1 0 6" stroke="#2563eb" stroke-width="1.2" stroke-linecap="round"/>
                </svg>
                <span class="modal-audio-label">Audio</span>
              </template>
            </div>

            <!-- Button group: Play/Pause/Resume · Stop · Speed -->
            <div class="modal-audio-btns">

              <!-- Play / Pause / Resume toggle -->
              <button
                class="modal-audio-btn modal-audio-btn--primary"
                @click="
                  activeBlockId === activeSection.id && playbackState === 'playing'
                    ? pauseAudio()
                    : activeBlockId === activeSection.id && playbackState === 'paused'
                      ? resumeAudio()
                      : playBlock(activeSection.id, 'summary')
                "
              >
                <!-- Pause icon when playing -->
                <template v-if="activeBlockId === activeSection.id && playbackState === 'playing'">
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                    <rect x="2" y="1.5" width="2.5" height="9" rx="0.8" fill="currentColor"/>
                    <rect x="7.5" y="1.5" width="2.5" height="9" rx="0.8" fill="currentColor"/>
                  </svg>
                  Pause
                </template>
                <!-- Play icon when paused -->
                <template v-else-if="activeBlockId === activeSection.id && playbackState === 'paused'">
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                    <path d="M2.5 1.5l8 4.5-8 4.5V1.5z" fill="currentColor"/>
                  </svg>
                  Resume
                </template>
                <!-- Default: play icon -->
                <template v-else>
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                    <path d="M2.5 1.5l8 4.5-8 4.5V1.5z" fill="currentColor"/>
                  </svg>
                  Play
                </template>
              </button>

              <!-- Stop button — only active when this section is playing/paused -->
              <button
                class="modal-audio-btn"
                :disabled="activeBlockId !== activeSection.id || playbackState === 'idle'"
                @click="stopAudio"
              >
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                  <rect x="2" y="2" width="8" height="8" rx="1.5" fill="currentColor"/>
                </svg>
                Stop
              </button>

              <!-- Speed selector -->
              <div class="modal-audio-speed">
                <label class="modal-audio-speed-label">Speed</label>
                <select v-model="playbackSpeed" class="modal-speed-select">
                  <option v-for="s in SPEED_OPTIONS" :key="s" :value="s">{{ s }}x</option>
                </select>
              </div>

            </div><!-- /modal-audio-btns -->
          </div><!-- /modal-audio -->

        </div><!-- /modal-panel -->
      </div><!-- /modal-backdrop -->
    </Transition><!-- /modal-fade -->


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
    <!-- Hidden in result mode so the reading area has full focus -->
    <div v-if="mode !== 'result'" class="bottom-bar">
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
/* In result mode the bottom bar is hidden — remove the bottom clearance */
.reading-area--no-bar { padding-bottom: 40px; }

/* Narrow width for idle/loading; full-width for results */
.reading-inner {
  max-width: 760px;
  margin: 0 auto;
  padding: 0 24px;
  transition: max-width 0.3s ease;
}
.reading-inner--wide {
  max-width: 1100px;  /* wider in result mode to give the 4-column tree room */
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
   Result state — gap is now 0; each stage
   manages its own spacing internally.
   (Overridden again in the NEW STYLES block below.)
───────────────────────────────────────── */
.result-state { display: flex; flex-direction: column; gap: 0; }

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
   a 72px clickable strip and the right (summary) column fills the rest.
───────────────────────────────────────── */

/* Narrow the left column for both the header and all block rows.
   72px is wide enough to read the strip labels without taking space from summary. */
.result-grid--orig-hidden .result-grid-header,
.result-grid--orig-hidden .block-row {
  grid-template-columns: 72px 1fr;
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
  align-items: center; gap: 4px;
  padding: 3px 10px;
  font-size: 11.5px; font-weight: 700;
  color: #2563eb;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 999px;
  align-self: flex-start;
}

/* Collapse variant — resets button defaults, keeps badge look, adds pointer */
.block-label--collapse {
  cursor: pointer;
  font-family: inherit;
  transition: background 0.15s, border-color 0.15s;
}
.block-label--collapse:hover {
  background: #dbeafe;
  border-color: #93c5fd;
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


/* ═══════════════════════════════════════════════════════════════════
   ITERATION 3 — 3-stage guided reading flow
   Premium, calm design for dyslexia-friendly reading.
   ═══════════════════════════════════════════════════════════════════ */

/* ─────────────────────────────────────────
   Demo CTA banner in idle state
───────────────────────────────────────── */
.demo-cta {
  display: flex; align-items: center; gap: 14px;
  margin-top: 24px; padding: 14px 20px;
  background: linear-gradient(135deg, #eff6ff 0%, #f0fdf4 100%);
  border: 1px solid #bfdbfe; border-radius: 12px;
  max-width: 520px; width: 100%;
}
.demo-cta-text { font-size: 13.5px; color: #4b5563; flex: 1; }
.btn-demo {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 8px 18px; font-size: 13px; font-weight: 700; color: #2563eb;
  background: #fff; border: 1.5px solid #bfdbfe; border-radius: 999px;
  cursor: pointer; transition: all 0.18s; white-space: nowrap; font-family: inherit;
}
.btn-demo:hover {
  background: #eff6ff; border-color: #93c5fd;
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.14); transform: translateY(-1px);
}


/* ─────────────────────────────────────────
   Result state — no gap; stages are full-page
───────────────────────────────────────── */
.result-state { display: flex; flex-direction: column; gap: 0; }


/* ─────────────────────────────────────────
   Stage pill labels (OVERVIEW / SECTIONS)
───────────────────────────────────────── */
.stage-header { display: flex; align-items: center; gap: 10px; margin-bottom: 20px; }
.stage-pill {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 5px 14px;
  font-size: 10.5px; font-weight: 700;
  letter-spacing: 0.08em; text-transform: uppercase;
  border-radius: 999px;
}
.stage-pill--green { color: #15803d; background: #f0fdf4; border: 1px solid #bbf7d0; }
.stage-pill--blue  { color: #4338ca; background: #eef2ff; border: 1px solid #c7d2fe; }
.stage-pill-count  { font-size: 12px; color: #9ca3af; font-weight: 500; }


/* ─────────────────────────────────────────
   STAGE 1 — Overall Summary hero card
   Natural height — flows directly into the section grid below.
───────────────────────────────────────── */
.stage-summary {
  display: flex;
  flex-direction: column;
  gap: 0;
  max-width: 740px;
  margin: 0 auto;
  width: 100%;
  padding: 48px 0 0;
}

/*
  Main card: white background, green left accent border.
  No coloured fill — white feels cleaner and more premium.
  Three layers of shadow for natural depth.
*/
.overall-card {
  background: #ffffff;
  border: 1px solid #e8f5e9;
  border-left: 4px solid #22c55e;
  border-radius: 20px;
  padding: 40px 44px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  box-shadow:
    0 0 0 1px rgba(22, 163, 74, 0.04),
    0 4px 16px rgba(0, 0, 0, 0.05),
    0 20px 56px rgba(0, 0, 0, 0.05);
}

/* Large, impactful heading */
.overall-heading {
  font-size: 28px;
  font-weight: 800;
  color: #0a0a0a;
  letter-spacing: -0.03em;
  line-height: 1.35;
  margin: 0;
}

/* Comfortable body text */
.overall-body {
  font-size: 16px;
  line-height: 1.8;
  color: #4b5563;
  margin: 0;
}

/*
  Audio control row: thin top separator, then play button + optional speed.
  The play button is part of the card flow — below the body text —
  so the reading hierarchy feels natural.
*/
.overall-audio-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-top: 16px;
  border-top: 1px solid #f0fdf4;
  flex-wrap: wrap;
}

/* Primary play/pause/resume button: filled green pill */
.overall-play-btn {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 11px 24px;
  font-size: 14px; font-weight: 700; color: #fff;
  background: #16a34a;
  border: none; border-radius: 999px;
  cursor: pointer; font-family: inherit;
  box-shadow: 0 4px 14px rgba(22, 163, 74, 0.30);
  transition: background 0.18s, box-shadow 0.18s, transform 0.12s;
}
.overall-play-btn:hover {
  background: #15803d;
  box-shadow: 0 6px 22px rgba(22, 163, 74, 0.38);
  transform: translateY(-1px);
}
.overall-play-btn--playing { background: #15803d; }
.overall-play-btn--paused {
  background: #d97706;
  box-shadow: 0 4px 14px rgba(217, 119, 6, 0.30);
}
.overall-play-btn--paused:hover { background: #b45309; }

/* White waveform bars on the green button */
.wave-bar--white {
  display: inline-block;
  width: 3px; height: 11px;
  background: #fff; border-radius: 2px;
  animation: wave 0.9s ease-in-out infinite;
}
.wave-bar--white:nth-child(2) { animation-delay: 0.15s; }
.wave-bar--white:nth-child(3) { animation-delay: 0.30s; }

/* Speed selector + stop button (only when playing/paused) */
.overall-speed { display: flex; align-items: center; gap: 8px; }
.overall-speed-select {
  padding: 6px 10px; font-size: 12.5px; font-weight: 600; color: #374151;
  background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px;
  cursor: pointer; outline: none; font-family: inherit;
}
.overall-speed-select:focus { border-color: #86efac; }
.overall-stop-btn {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 6px 12px; font-size: 12px; font-weight: 700;
  color: #6b7280; background: #f3f4f6; border: none; border-radius: 8px;
  cursor: pointer; font-family: inherit; transition: all 0.15s;
}
.overall-stop-btn:hover { background: #e5e7eb; color: #374151; }


/* ─────────────────────────────────────────
   STAGE 2 — Section Grid
   Flows naturally below the overview card.
   The bridge label visually connects the two.
───────────────────────────────────────── */
.stage-tree {
  display: flex;
  flex-direction: column;
  gap: 0;
  padding: 0 0 64px;
  max-width: 1100px;
  margin: 0 auto;
  width: 100%;
}

/* ─────────────────────────────────────────
   Bridge: "N Sections" label with horizontal
   rules on each side, connecting overview ↔ grid
───────────────────────────────────────── */
.sections-bridge {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 36px 0 28px;
}
.sections-bridge-line {
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, transparent, #e0e7ff 40%, #e0e7ff 60%, transparent);
}
.sections-bridge-label {
  flex-shrink: 0;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #a5b4fc;
  white-space: nowrap;
}

/*
  Container box — wraps ALL section cards in one visual unit.
  This makes it unmistakably clear that every card is a peer,
  NOT a child of another card.
  A soft background + border draws the eye to the group as a whole.
*/
.tree-container {
  border: 1.5px solid #e0e7ff;
  border-radius: 20px;
  padding: 20px;
  background: linear-gradient(160deg, #fafbff 0%, #f5f4ff 100%);
  box-shadow: 0 2px 16px rgba(99, 102, 241, 0.06);
}

/* Grid of section cards inside the container */
.tree-nodes {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  /* No position: relative or padding-top needed — branch lines are gone */
}

/* No crossbar pseudo-element */
.tree-nodes::before { display: none; }

/* Individual section card */
.tree-node {
  display: flex; flex-direction: column; gap: 10px;
  padding: 18px 18px 16px 20px;
  background: #fff;
  border: 1px solid #eef0f8;
  border-left: 3px solid #e0e7ff;
  border-radius: 14px;
  cursor: pointer;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
  transition: border-left-color 0.2s ease, box-shadow 0.2s ease, transform 0.15s ease;
}
.tree-node:hover {
  border-left-color: #6366f1;
  box-shadow: 0 8px 28px rgba(99, 102, 241, 0.13);
  transform: translateY(-3px);
}
.tree-node:focus-visible { outline: 2px solid #6366f1; outline-offset: 2px; }

/* No branch-line pseudo-element per card */
.tree-node::before { display: none; }

/* Number badge */
.tree-node-num {
  display: flex; align-items: center; justify-content: center;
  width: 28px; height: 28px; flex-shrink: 0;
  border-radius: 50%;
  font-size: 12px; font-weight: 800; color: #4338ca;
  background: #eef2ff;
  align-self: flex-start;
}
.tree-node-content { flex: 1; }
.tree-node-title {
  font-size: 13.5px; font-weight: 700; color: #0f172a;
  line-height: 1.3; margin-bottom: 4px;
}
.tree-node-subtitle { font-size: 12px; color: #64748b; line-height: 1.45; }

/* Right arrow: click hint */
.tree-node-arrow {
  color: #cbd5e1;
  transition: color 0.15s, transform 0.15s;
  align-self: flex-end; margin-top: auto;
}
.tree-node:hover .tree-node-arrow { color: #6366f1; transform: translateX(4px); }

/* Responsive grid */
@media (max-width: 1000px) {
  .tree-nodes { grid-template-columns: repeat(3, 1fr); }
}
@media (max-width: 700px) {
  .tree-nodes { grid-template-columns: repeat(2, 1fr); }
  .stage-tree { padding: 0 0 40px; }
  .tree-container { padding: 14px; }
}
@media (max-width: 440px) {
  .tree-nodes { grid-template-columns: 1fr; }
}


/* ─────────────────────────────────────────
   STAGE 3 — Section Detail Modal
   Full-screen backdrop + centred panel card.
───────────────────────────────────────── */

/* Dim backdrop with blur */
.modal-backdrop {
  position: fixed; inset: 0;
  background: rgba(8, 10, 18, 0.52);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  z-index: 300;
  display: flex; align-items: center; justify-content: center;
  padding: 24px;
}

/* Panel card */
.modal-panel {
  background: #fff;
  border-radius: 22px;
  box-shadow:
    0 0 0 1px rgba(0,0,0,0.04),
    0 24px 80px rgba(0, 0, 0, 0.24);
  max-width: 880px; width: 100%;
  max-height: 88vh;
  display: flex; flex-direction: column;
  overflow: hidden;
}

/* Modal header */
.modal-header {
  display: flex; align-items: flex-start; gap: 16px;
  padding: 26px 30px 22px;
  border-bottom: 1px solid #f1f5f9;
  flex-shrink: 0;
}

/* Circular section number */
.modal-section-num {
  display: flex; align-items: center; justify-content: center;
  width: 44px; height: 44px; flex-shrink: 0; border-radius: 50%;
  font-size: 17px; font-weight: 800; color: #4338ca;
  background: #eef2ff; border: 2px solid #c7d2fe;
}

.modal-title-group { flex: 1; min-width: 0; }
.modal-title {
  font-size: 21px; font-weight: 800; color: #0f172a;
  letter-spacing: -0.025em; margin: 0 0 5px; line-height: 1.3;
}
.modal-subtitle { font-size: 13.5px; color: #64748b; margin: 0; line-height: 1.45; }

/* Close button */
.modal-close-btn {
  display: flex; align-items: center; justify-content: center;
  width: 36px; height: 36px; flex-shrink: 0;
  background: #f8fafc; border: none; border-radius: 999px;
  color: #94a3b8; cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.modal-close-btn:hover { background: #f1f5f9; color: #0f172a; }

/* Modal body: 2-column */
.modal-body {
  display: flex; gap: 0;
  flex: 1; overflow-y: auto;
  padding: 28px 30px;
}
.modal-col { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 14px; }

/* Column label */
.modal-col-label {
  font-size: 10.5px; font-weight: 700;
  letter-spacing: 0.09em; text-transform: uppercase; color: #94a3b8;
}

/* Vertical divider */
.modal-divider { width: 1px; background: #f1f5f9; margin: 0 26px; flex-shrink: 0; }

/* Summary text */
.modal-summary-text { font-size: 15px; line-height: 1.8; color: #1e293b; margin: 0; }

/* Key points list */
.modal-keypoints { margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 9px; }
.modal-keypoints li {
  font-size: 14px; line-height: 1.65; color: #334155;
  padding-left: 16px; position: relative;
}
.modal-keypoints li::before { content: '●'; position: absolute; left: 0; color: #818cf8; font-size: 8px; top: 6px; }

.modal-fallback { font-size: 13px; color: #94a3b8; font-style: italic; margin: 0; }

/* Audio bar */
.modal-audio {
  display: flex; align-items: center; gap: 14px;
  padding: 16px 30px;
  background: #fafafa; border-top: 1px solid #f1f5f9;
  flex-shrink: 0; flex-wrap: wrap;
}
.modal-audio-status {
  display: flex; align-items: center; gap: 7px;
  font-size: 12.5px; color: #64748b; font-weight: 600;
  flex: 1; min-width: 80px;
}
.modal-audio-label { font-size: 12.5px; color: #64748b; }

.modal-audio-btns { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }

.modal-audio-btn {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 7px 16px;
  font-size: 13px; font-weight: 700;
  background: #fff; color: #374151;
  border: 1px solid #e2e8f0; border-radius: 10px;
  cursor: pointer; font-family: inherit;
  transition: all 0.15s;
}
.modal-audio-btn:hover:not(:disabled) { background: #f8fafc; border-color: #cbd5e1; color: #0f172a; }
.modal-audio-btn:disabled { opacity: 0.38; cursor: not-allowed; }
.modal-audio-btn--primary { background: #4f46e5; border-color: #4f46e5; color: #fff; box-shadow: 0 3px 10px rgba(79,70,229,0.28); }
.modal-audio-btn--primary:hover:not(:disabled) { background: #4338ca; border-color: #4338ca; }

.modal-audio-speed { display: flex; align-items: center; gap: 6px; }
.modal-audio-speed-label { font-size: 10.5px; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.06em; }
.modal-speed-select {
  padding: 5px 8px; font-size: 12px; font-weight: 600; color: #374151;
  background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
  cursor: pointer; outline: none; font-family: inherit;
}
.modal-speed-select:focus { border-color: #818cf8; }

/* Mobile modal */
@media (max-width: 680px) {
  .modal-body { flex-direction: column; padding: 20px; }
  .modal-divider { width: auto; height: 1px; margin: 16px 0; }
  .modal-panel { border-radius: 18px; max-height: 93vh; }
  .modal-header { padding: 20px 22px 16px; }
  .modal-audio { padding: 14px 22px; }
  .overall-card { padding: 24px 20px; }
  .overall-heading { font-size: 22px; }
  .stage-summary { padding: 28px 0 0; }
}


/* ─────────────────────────────────────────
   Modal fade + scale-in transition
───────────────────────────────────────── */
.modal-fade-enter-active { transition: opacity 0.22s ease; }
.modal-fade-leave-active { transition: opacity 0.18s ease; }
.modal-fade-enter-from, .modal-fade-leave-to { opacity: 0; }

.modal-fade-enter-active .modal-panel {
  animation: modal-pop 0.24s cubic-bezier(0.34, 1.38, 0.64, 1);
}
@keyframes modal-pop {
  from { transform: scale(0.93) translateY(12px); }
  to   { transform: scale(1) translateY(0); }
}
</style>
