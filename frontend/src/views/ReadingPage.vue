<script setup>
// Vue core utilities we need for this page
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'

// Read the backend URL from the .env file; fall back to localhost if not set
// The .replace removes any trailing slash to keep URLs clean
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '')


// ── Navbar state ──────────────────────────────────────────────────────────────

// Track whether the user has scrolled down (used to add a shadow to the navbar)
const scrolled = ref(false)
// Track whether the mobile hamburger menu is open
const menuOpen = ref(false)
// Add a shadow when the user scrolls more than 10px from the top
function onScroll() { scrolled.value = window.scrollY > 10 }


// ── Input state ───────────────────────────────────────────────────────────────

// The text the user has typed or pasted into the input box
const inputText = ref('')
// Maximum number of characters we allow
const charLimit = 5000
// Live character count based on current input
const charCount = computed(() => inputText.value.length)
// True if the user has exceeded the character limit
const overLimit = computed(() => charCount.value > charLimit)
// Reference to the <textarea> DOM element so we can resize it programmatically
const textareaRef = ref(null)


// ── Page mode ─────────────────────────────────────────────────────────────────

// The page has three states: idle (waiting), loading (processing), result (done)
const mode = ref('idle')
// The text that was last submitted and is now shown in the reading area
const loadedText = ref('')

// Helper: count words in a string
const wordCount = (t) => t.trim().split(/\s+/).filter(Boolean).length


// ── Feedback strip ────────────────────────────────────────────────────────────

// Stores the current feedback message shown above the input bar
// Shape: { type: 'loading' | 'uploading' | 'success' | 'error', message: string }
const feedback = ref(null)
let feedbackTimer = null

// Show a feedback message; auto-dismiss after `autoDismiss` ms (0 = keep until manually cleared)
function showFeedback(type, message, autoDismiss = 3000) {
  clearTimeout(feedbackTimer)
  feedback.value = { type, message }
  if (autoDismiss) feedbackTimer = setTimeout(() => { feedback.value = null }, autoDismiss)
}


// ── File upload state ─────────────────────────────────────────────────────────

// Reference to the hidden <input type="file"> element
const fileInputRef = ref(null)
// True while the user is dragging a file over the page
const isDragging = ref(false)
// File extensions we accept from users
const SUPPORTED_EXT = ['.txt', '.md', '.markdown', '.csv', '.rtf', '.log', '.pdf', '.docx']


// ── Auto-resize textarea ──────────────────────────────────────────────────────

// Resize the textarea to fit its content (up to a max height of 180px)
function autoResize() {
  const el = textareaRef.value
  if (!el) return
  el.style.height = 'auto'                                  // reset first so shrinking works
  el.style.height = Math.min(el.scrollHeight, 180) + 'px'  // then set to content height
}
// Re-run autoResize whenever the input text changes
watch(inputText, () => nextTick(autoResize))


// ── Submit handler ────────────────────────────────────────────────────────────

// Called when the user clicks "Load Text" or presses Ctrl+Enter
async function handleSubmit() {
  // Do nothing if the input is empty, over the limit, or already loading
  if (!inputText.value.trim() || overLimit.value || mode.value === 'loading') return

  showFeedback('loading', 'Loading your text…', 0)
  mode.value = 'loading'

  // Small delay so the loading state is visible to the user
  await new Promise(r => setTimeout(r, 380))

  // Move the input text to the reading area and switch to result mode
  loadedText.value = inputText.value
  mode.value = 'result'
  showFeedback('success', 'Text loaded — scroll up to read')
}


// ── Clear handler ─────────────────────────────────────────────────────────────

// Reset the input box and remove any active feedback
function handleClear() {
  inputText.value = ''
  feedback.value = null
  clearTimeout(feedbackTimer)
  nextTick(autoResize) // shrink textarea back to its minimum height
}


// ── File read helpers ─────────────────────────────────────────────────────────

// Read a file and return its content as a plain text string
function readAsText(file) {
  return new Promise((res, rej) => {
    const r = new FileReader()
    r.onload  = e => res(e.target.result)
    r.onerror = () => rej(new Error('Could not read file.'))
    r.readAsText(file)
  })
}

// Read a file and return its content as a base64-encoded string
// This is needed when sending binary files (PDF, DOCX) to the backend as JSON
function readAsBase64(file) {
  return new Promise((res, rej) => {
    const r = new FileReader()
    r.onload = e => {
      const s = typeof e.target.result === 'string' ? e.target.result : ''
      // Strip the "data:...;base64," prefix — we only need the raw base64 part
      res(s.includes(',') ? s.split(',')[1] : s)
    }
    r.onerror = () => rej(new Error('Could not read file.'))
    r.readAsDataURL(file)
  })
}

// Main function to handle any uploaded or dropped file
async function processFile(file) {
  // Get the file extension (e.g. ".pdf")
  const ext = '.' + file.name.split('.').pop().toLowerCase()

  // Reject unsupported file types
  if (!SUPPORTED_EXT.includes(ext)) {
    showFeedback('error', `"${file.name}" is not supported. Use TXT, PDF, or DOCX.`, 5000)
    return
  }

  // Reject files larger than 5 MB
  if (file.size > 5 * 1024 * 1024) {
    showFeedback('error', 'File is too large (max 5 MB).', 5000)
    return
  }

  showFeedback('uploading', `Uploading "${file.name}"…`, 0)

  try {
    // Plain-text files can be read directly in the browser — no backend call needed
    if (['.txt', '.md', '.markdown', '.csv', '.rtf', '.log'].includes(ext)) {
      const text = await readAsText(file)
      if (!text.trim()) throw new Error('No readable text found in this file.')
      inputText.value = text
      showFeedback('success', `"${file.name}" ready — click Load Text to continue`)
      return
    }

    // For PDF and DOCX, send the file to the backend for text extraction
    const base64 = await readAsBase64(file)
    const res = await fetch(`${API_BASE_URL}/api/extract-text`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filename: file.name, contentBase64: base64 }),
    })
    const data = await res.json()
    if (!res.ok)            throw new Error(data.detail || 'Could not extract text.')
    if (!data.text?.trim()) throw new Error('No readable text found in this file.')
    inputText.value = data.text
    showFeedback('success', `"${file.name}" ready — click Load Text to continue`)
  } catch (err) {
    showFeedback('error', err.message || 'Upload failed. Please try again.', 6000)
  }
}

// Open the hidden file picker when the "Upload file" button is clicked
function triggerFileInput() { fileInputRef.value?.click() }

// Handle the file chosen from the file picker dialog
async function handleFileChange(e) {
  const file = e.target.files[0]
  e.target.value = '' // reset so the same file can be re-selected if needed
  if (file) await processFile(file)
}


// ── Drag and drop ─────────────────────────────────────────────────────────────

// We use a counter to handle nested drag events correctly
// (dragging over a child element fires dragenter/dragleave on the parent)
let dragCounter = 0

function onDragEnter(e) {
  e.preventDefault()
  dragCounter++
  isDragging.value = true
}

function onDragOver(e) { e.preventDefault() } // must prevent default to allow drop

function onDragLeave() {
  dragCounter--
  // Only hide the overlay once we have fully left the page
  if (dragCounter <= 0) { dragCounter = 0; isDragging.value = false }
}

async function onDrop(e) {
  e.preventDefault()
  dragCounter = 0
  isDragging.value = false
  const file = e.dataTransfer?.files[0] // grab the first dropped file
  if (file) await processFile(file)
}


// ── Keyboard shortcut ─────────────────────────────────────────────────────────

// Allow Ctrl+Enter (or Cmd+Enter on Mac) to submit without clicking the button
function onKeydown(e) {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') handleSubmit()
}


// ── Lifecycle hooks ───────────────────────────────────────────────────────────

onMounted(() => {
  window.addEventListener('scroll', onScroll)
  nextTick(autoResize) // set initial textarea height
})

onUnmounted(() => {
  window.removeEventListener('scroll', onScroll)
  clearTimeout(feedbackTimer) // clean up any pending timers
})
</script>

<template>
  <!--
    The whole page listens for drag events so users can drop a file
    anywhere on the screen, not just on a specific drop zone.
  -->
  <div
    class="page"
    @dragenter="onDragEnter"
    @dragover.prevent="onDragOver"
    @dragleave="onDragLeave"
    @drop="onDrop"
  >

    <!-- ── Navbar ── -->
    <!-- The navbar sticks to the top and gets a shadow when the user scrolls -->
    <nav :class="['navbar', { 'navbar--scrolled': scrolled }]">
      <div class="nav-inner">

        <!-- Logo / brand link — always navigates back to home -->
        <RouterLink to="/" class="nav-logo">
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect width="28" height="28" rx="8" fill="#2563eb"/>
            <path d="M7 8.5C7 7.67 7.67 7 8.5 7H13.5V21H8.5C7.67 21 7 20.33 7 19.5V8.5Z" fill="white" opacity="0.9"/>
            <path d="M21 8.5C21 7.67 20.33 7 19.5 7H14.5V21H19.5C20.33 21 21 20.33 21 19.5V8.5Z" fill="white" opacity="0.55"/>
            <rect x="9" y="10" width="3" height="1.5" rx="0.75" fill="#2563eb" opacity="0.7"/>
            <rect x="9" y="13" width="3" height="1.5" rx="0.75" fill="#2563eb" opacity="0.7"/>
            <rect x="9" y="16" width="2" height="1.5" rx="0.75" fill="#2563eb" opacity="0.7"/>
          </svg>
          Clearead
        </RouterLink>

        <!-- Desktop navigation links -->
        <ul class="nav-links">
          <li><RouterLink to="/"         class="nav-link">Home</RouterLink></li>
          <li><RouterLink to="/reading"  class="nav-link nav-link--active">Reading Support</RouterLink></li>
          <li><RouterLink to="/dyslexia" class="nav-link">Dyslexia</RouterLink></li>
        </ul>

        <!-- Hamburger button — only visible on small screens -->
        <button class="nav-hamburger" @click="menuOpen = !menuOpen" :aria-label="menuOpen ? 'Close menu' : 'Open menu'">
          <!-- Show X icon when menu is open, bars icon when closed -->
          <svg v-if="!menuOpen" width="22" height="22" viewBox="0 0 22 22" fill="none">
            <path d="M3 6h16M3 11h16M3 16h16" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          </svg>
          <svg v-else width="22" height="22" viewBox="0 0 22 22" fill="none">
            <path d="M5 5l12 12M17 5L5 17" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          </svg>
        </button>

      </div>
    </nav>

    <!-- Mobile nav drawer — slides down when the hamburger is clicked -->
    <div v-if="menuOpen" class="mobile-nav">
      <ul class="mobile-nav-links">
        <li><RouterLink to="/"         class="mobile-nav-link" @click="menuOpen = false">Home</RouterLink></li>
        <li><RouterLink to="/reading"  class="mobile-nav-link" @click="menuOpen = false">Reading Support</RouterLink></li>
        <li><RouterLink to="/dyslexia" class="mobile-nav-link" @click="menuOpen = false">Dyslexia</RouterLink></li>
      </ul>
    </div>


    <!-- ── Main reading area ── -->
    <!--
      This scrollable area sits between the navbar and the fixed bottom bar.
      It shows one of three states depending on `mode`: idle, loading, or result.
    -->
    <main class="reading-area">
      <div class="reading-inner">

        <!-- State 1: Idle — nothing loaded yet, show a welcome prompt -->
        <div v-if="mode === 'idle'" class="empty-state">
          <div class="empty-icon">
            <svg width="52" height="52" viewBox="0 0 52 52" fill="none">
              <rect x="9" y="6" width="34" height="40" rx="6" fill="#eef2ff" stroke="#c7d2fe" stroke-width="1.5"/>
              <path d="M17 20h18M17 27h18M17 34h11" stroke="#a5b4fc" stroke-width="2" stroke-linecap="round"/>
              <circle cx="40" cy="40" r="9" fill="#2563eb"/>
              <path d="M40 36v8M36 40h8" stroke="white" stroke-width="1.8" stroke-linecap="round"/>
            </svg>
          </div>
          <h2 class="empty-title">Ready to support your reading</h2>
          <p class="empty-sub">
            Paste your text or drop a file into the bar below.<br>
            Clearead will help you read it more comfortably.
          </p>
          <!-- Feature pills: quick summary of what the user can do -->
          <div class="empty-features">
            <div class="feature-pill">
              <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
                <path d="M2 6.5h9M7.5 3l3.5 3.5L7.5 10" stroke="#2563eb" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              Paste text
            </div>
            <div class="feature-pill">
              <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
                <path d="M6.5 9V2.5M6.5 2.5L4 5M6.5 2.5L9 5" stroke="#2563eb" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M2 10h9" stroke="#2563eb" stroke-width="1.5" stroke-linecap="round"/>
              </svg>
              Upload TXT / PDF / DOCX
            </div>
            <div class="feature-pill">
              <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
                <rect x="1.5" y="4" width="4" height="5" rx="1" fill="#2563eb" opacity="0.3"/>
                <path d="M7 4.5l4 2-4 2" stroke="#2563eb" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              Drag &amp; drop anywhere
            </div>
          </div>
          <!-- Keyboard shortcut hint -->
          <p class="empty-shortcut">
            <kbd>Ctrl</kbd> + <kbd>Enter</kbd>
            <span>to submit quickly</span>
          </p>
        </div>

        <!-- State 2: Loading — show animated skeleton while waiting -->
        <div v-else-if="mode === 'loading'" class="loading-state">
          <!-- Each skeleton block represents a line of text that is being loaded -->
          <div class="skeleton skeleton--heading"></div>
          <div class="skeleton skeleton--line" style="width:96%"></div>
          <div class="skeleton skeleton--line" style="width:89%"></div>
          <div class="skeleton skeleton--line" style="width:93%"></div>
          <div class="skeleton skeleton--line" style="width:78%"></div>
          <div class="skeleton skeleton--spacer"></div>
          <div class="skeleton skeleton--line" style="width:91%"></div>
          <div class="skeleton skeleton--line" style="width:84%"></div>
          <div class="skeleton skeleton--line" style="width:67%"></div>
          <div class="skeleton skeleton--spacer"></div>
          <div class="skeleton skeleton--line" style="width:88%"></div>
          <div class="skeleton skeleton--line" style="width:72%"></div>
        </div>

        <!-- State 3: Result — display the loaded text and word count -->
        <div v-else-if="mode === 'result'" class="result-state">
          <div class="result-header">
            <!-- Green badge to confirm the text was loaded successfully -->
            <div class="result-badge">
              <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
                <circle cx="6.5" cy="6.5" r="6" fill="#dcfce7" stroke="#16a34a" stroke-width="1"/>
                <path d="M4 6.5l1.8 1.8 3.2-3.6" stroke="#16a34a" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              Text loaded
            </div>
            <span class="result-meta">{{ wordCount(loadedText).toLocaleString() }} words</span>
          </div>
          <!-- Display the loaded text, preserving line breaks from the original -->
          <div class="result-text">{{ loadedText }}</div>
        </div>

      </div>
    </main>


    <!-- ── Drag-and-drop overlay ── -->
    <!--
      This full-screen overlay appears when the user drags a file over the page.
      It guides them to drop the file to upload it.
    -->
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
          <p class="drag-sub">TXT · PDF · DOCX · MD</p>
        </div>
      </div>
    </Transition>


    <!-- ── Fixed bottom input bar ── -->
    <!--
      This bar is always visible at the bottom of the screen.
      It contains the textarea for input, file upload, and the submit button.
    -->
    <div class="bottom-bar">
      <div class="bottom-bar-inner">

        <!-- Feedback strip: shows status messages (loading, success, error) above the input -->
        <Transition name="feedback">
          <div v-if="feedback" :class="['feedback-strip', `feedback--${feedback.type}`]">
            <div class="feedback-icon">
              <!-- Animated spinner for loading and uploading states -->
              <svg v-if="feedback.type === 'loading' || feedback.type === 'uploading'"
                class="spin" width="14" height="14" viewBox="0 0 14 14" fill="none">
                <circle cx="7" cy="7" r="5.5" stroke="currentColor" stroke-width="1.8"
                  stroke-dasharray="22 10" stroke-linecap="round"/>
              </svg>
              <!-- Green check for success -->
              <svg v-else-if="feedback.type === 'success'" width="14" height="14" viewBox="0 0 14 14" fill="none">
                <circle cx="7" cy="7" r="6" fill="#dcfce7"/>
                <path d="M4 7l2.2 2.2 3.8-4.4" stroke="#16a34a" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              <!-- Red X for errors -->
              <svg v-else-if="feedback.type === 'error'" width="14" height="14" viewBox="0 0 14 14" fill="none">
                <circle cx="7" cy="7" r="6" fill="#fee2e2"/>
                <path d="M4.5 4.5l5 5M9.5 4.5l-5 5" stroke="#ef4444" stroke-width="1.4" stroke-linecap="round"/>
              </svg>
            </div>
            <span class="feedback-msg">{{ feedback.message }}</span>
            <!-- Allow the user to manually dismiss the feedback -->
            <button class="feedback-close" @click="feedback = null" aria-label="Dismiss">
              <svg width="11" height="11" viewBox="0 0 11 11" fill="none">
                <path d="M2 2l7 7M9 2l-7 7" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
              </svg>
            </button>
          </div>
        </Transition>

        <!-- Input card: the main text entry area -->
        <div class="input-card">

          <!-- Multi-line textarea that auto-resizes as the user types -->
          <textarea
            ref="textareaRef"
            v-model="inputText"
            class="input-textarea"
            :class="{ 'input-textarea--over': overLimit }"
            placeholder="Type or paste your text here…"
            rows="1"
            spellcheck="false"
            @keydown="onKeydown"
          ></textarea>

          <!-- Visual divider between textarea and action buttons -->
          <div class="input-divider"></div>

          <!-- Action buttons row -->
          <div class="input-actions">

            <!-- Left side: file upload and character count -->
            <div class="actions-left">
              <!-- Hidden native file input — triggered by the "Upload file" button below -->
              <input
                ref="fileInputRef"
                type="file"
                accept=".txt,.md,.markdown,.csv,.rtf,.log,.pdf,.docx"
                style="display:none"
                @change="handleFileChange"
              />
              <!-- Visible upload button that opens the file picker -->
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

            <!-- Right side: clear and submit buttons -->
            <div class="actions-right">
              <!-- Clear button only appears when there is text to clear -->
              <Transition name="fade-btn">
                <button v-if="inputText" class="btn-clear" @click="handleClear" title="Clear input">
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                    <path d="M2 2l8 8M10 2L2 10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                  </svg>
                  Clear
                </button>
              </Transition>

              <!-- Submit button — disabled when input is empty, over limit, or already loading -->
              <button
                class="btn-submit"
                :disabled="!inputText.trim() || overLimit || mode === 'loading'"
                @click="handleSubmit"
              >
                <!-- Show spinner while loading, otherwise show the button label -->
                <span v-if="mode === 'loading'" class="btn-spinner"></span>
                <template v-else>
                  Load Text
                  <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
                    <path d="M2 6.5H11M11 6.5L7 2.5M11 6.5L7 10.5"
                      stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                </template>
              </button>
            </div>

          </div>
        </div>

        <!-- Small hint text at the bottom of the bar -->
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
   The page uses flexbox column layout so the
   reading area fills the space between navbar and bottom bar.
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
  /* Slightly transparent with blur so content scrolls behind it nicely */
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid #e5e7eb;
  z-index: 50;
  transition: box-shadow 0.2s;
}
/* Add a deeper shadow when the user has scrolled down */
.navbar--scrolled { box-shadow: 0 1px 12px rgba(0, 0, 0, 0.07); }

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
.nav-link:hover { color: #0d1117; background: rgba(0, 0, 0, 0.04); }
.nav-link--active { color: #0d1117; }
/* Blue dot indicator under the active page link */
.nav-link--active::after {
  content: ''; position: absolute;
  bottom: -2px; left: 50%; transform: translateX(-50%);
  width: 4px; height: 4px;
  border-radius: 50%; background: #2563eb;
}
/* Hamburger is hidden on desktop, shown only on mobile */
.nav-hamburger {
  display: none;
  background: none; border: none; cursor: pointer;
  color: #0d1117; padding: 4px; margin-left: 12px;
  align-items: center; justify-content: center;
}
/* Mobile nav is hidden by default */
.mobile-nav { display: none; }


/* ─────────────────────────────────────────
   Reading area
   Fills the vertical space between navbar and bottom bar.
   Bottom padding prevents the fixed bar from covering content.
───────────────────────────────────────── */
.reading-area {
  flex: 1;
  padding: 40px 0 220px; /* 220px bottom padding to clear the fixed input bar */
  overflow-y: auto;
}
.reading-inner {
  max-width: 720px;
  margin: 0 auto;
  padding: 0 28px;
}


/* ─── Empty state ─── */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 48px 0 0;
}
.empty-icon { margin-bottom: 24px; }
.empty-title {
  font-size: 22px; font-weight: 700;
  color: #0d1117; letter-spacing: -0.03em;
  margin: 0 0 10px;
}
.empty-sub {
  font-size: 15px; line-height: 1.65;
  color: #6b7280; margin: 0 0 28px;
}
/* Small pill badges listing supported input methods */
.empty-features {
  display: flex; flex-wrap: wrap;
  justify-content: center; gap: 8px;
  margin-bottom: 24px;
}
.feature-pill {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 6px 14px;
  font-size: 13px; font-weight: 500; color: #374151;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 999px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}
.empty-shortcut {
  display: flex; align-items: center; gap: 6px;
  font-size: 13px; color: #9ca3af; margin: 0;
}
/* Keyboard key styling used in hints throughout the page */
kbd {
  display: inline-flex; align-items: center; justify-content: center;
  padding: 2px 7px;
  font-size: 11.5px; font-weight: 600; font-family: inherit;
  color: #374151;
  background: #f3f4f6;
  border: 1px solid #d1d5db;
  border-bottom-width: 2px; /* slightly thicker bottom border looks like a real key */
  border-radius: 5px;
}


/* ─── Skeleton loading ─── */
/* Animated placeholder bars shown while the page is processing the input */
.loading-state {
  display: flex; flex-direction: column; gap: 10px;
  padding-top: 8px;
}
.skeleton {
  border-radius: 8px;
  /* Gradient animates left-to-right to create a shimmer effect */
  background: linear-gradient(90deg, #eff1f5 25%, #e8eaf0 50%, #eff1f5 75%);
  background-size: 300% 100%;
  animation: shimmer 1.4s infinite;
}
.skeleton--heading { height: 22px; width: 52%; margin-bottom: 8px; }
.skeleton--line    { height: 15px; }
.skeleton--spacer  { height: 22px; background: transparent; } /* invisible gap between paragraphs */
@keyframes shimmer {
  0%   { background-position: 100% 0; }
  100% { background-position: -100% 0; }
}


/* ─── Result state ─── */
.result-state { padding-top: 8px; }
.result-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 20px;
}
/* Green pill badge shown after text is successfully loaded */
.result-badge {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 4px 12px;
  font-size: 12px; font-weight: 700;
  color: #16a34a;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 999px;
}
.result-meta {
  font-size: 12.5px; font-weight: 600; color: #9ca3af;
}
/* The actual loaded text — pre-wrap preserves line breaks from the original */
.result-text {
  font-size: 16px; line-height: 1.85;
  color: #1f2937;
  white-space: pre-wrap;
  font-family: inherit;
}


/* ─────────────────────────────────────────
   Drag-and-drop overlay
   Covers the whole page when the user drags a file in
───────────────────────────────────────── */
.drag-overlay {
  position: fixed; inset: 0;
  background: rgba(37, 99, 235, 0.08); /* light blue tint */
  backdrop-filter: blur(3px);
  -webkit-backdrop-filter: blur(3px);
  z-index: 200;
  display: flex; align-items: center; justify-content: center;
}
.drag-card {
  display: flex; flex-direction: column; align-items: center; gap: 12px;
  padding: 48px 64px;
  background: #fff;
  border: 2px dashed #93c5fd; /* dashed blue border to indicate drop zone */
  border-radius: 20px;
  box-shadow: 0 24px 64px rgba(37, 99, 235, 0.14);
}
.drag-icon {
  width: 72px; height: 72px;
  display: flex; align-items: center; justify-content: center;
  background: #eff6ff;
  border-radius: 50%;
}
.drag-title {
  font-size: 20px; font-weight: 700;
  color: #0d1117; margin: 0; letter-spacing: -0.02em;
}
.drag-sub {
  font-size: 13.5px; color: #6b7280; margin: 0; font-weight: 500;
  letter-spacing: 0.05em;
}


/* ─────────────────────────────────────────
   Fixed bottom input bar
   Always visible at the bottom of the viewport
───────────────────────────────────────── */
.bottom-bar {
  position: fixed;
  bottom: 0; left: 0; right: 0;
  /* Frosted-glass effect using semi-transparent background + blur */
  background: rgba(248, 249, 252, 0.96);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border-top: 1px solid #e5e7eb;
  box-shadow: 0 -4px 30px rgba(0, 0, 0, 0.07);
  z-index: 100;
  padding: 12px 0 14px;
}
.bottom-bar-inner {
  max-width: 720px; /* match the reading area width */
  margin: 0 auto;
  padding: 0 28px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}


/* ─── Feedback strip ─── */
/* A small notification bar that appears above the input card */
.feedback-strip {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 12px;
  border-radius: 10px;
  font-size: 13px; font-weight: 500;
  line-height: 1.4;
}
/* Blue style for loading and uploading states */
.feedback--loading,
.feedback--uploading {
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  color: #1d4ed8;
}
/* Green style for success */
.feedback--success {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  color: #15803d;
}
/* Red style for errors */
.feedback--error {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #b91c1c;
}
.feedback-icon { flex-shrink: 0; display: flex; }
.feedback-msg  { flex: 1; }
.feedback-close {
  flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  width: 22px; height: 22px;
  background: none; border: none; cursor: pointer;
  color: inherit; opacity: 0.55; border-radius: 4px;
  transition: opacity 0.15s;
}
.feedback-close:hover { opacity: 1; }


/* ─── Input card ─── */
/* The white rounded card that contains the textarea and action buttons */
.input-card {
  background: #fff;
  border: 1.5px solid #e5e7eb;
  border-radius: 14px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  transition: border-color 0.2s, box-shadow 0.2s;
  overflow: hidden;
}
/* Highlight with a blue ring when any element inside is focused */
.input-card:focus-within {
  border-color: #93c5fd;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05), 0 0 0 3px rgba(37, 99, 235, 0.1);
}

/* Textarea styling — no visible border since the card provides the border */
.input-textarea {
  display: block;
  width: 100%;
  min-height: 46px;
  max-height: 180px;  /* prevent it from growing too tall */
  padding: 14px 16px 8px;
  font-size: 14.5px; line-height: 1.65;
  font-family: inherit; color: #1f2937;
  background: transparent;
  border: none; outline: none; resize: none;
  box-sizing: border-box;
  overflow-y: auto;
}
.input-textarea::placeholder { color: #b8bfd0; }
/* Turn text red if the user has typed more than the allowed limit */
.input-textarea--over { color: #ef4444; }

/* Thin horizontal line between textarea and action buttons */
.input-divider {
  height: 1px;
  background: #f3f4f6;
  margin: 0 12px;
}

/* Row containing left (upload/count) and right (clear/submit) button groups */
.input-actions {
  display: flex; align-items: center;
  justify-content: space-between;
  padding: 8px 10px 10px;
  gap: 8px;
}
.actions-left,
.actions-right { display: flex; align-items: center; gap: 8px; }


/* Upload file button */
.btn-upload {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 6px 12px;
  font-size: 12.5px; font-weight: 600;
  color: #4b5563;
  background: #f3f4f6;
  border: 1px solid #e5e7eb;
  border-radius: 8px; cursor: pointer;
  transition: background 0.15s, border-color 0.15s, color 0.15s;
  white-space: nowrap;
}
.btn-upload:hover { background: #e9eaf0; color: #111827; border-color: #d1d5db; }


/* Character counter (shows current / max) */
.char-count { display: flex; align-items: center; gap: 2px; font-size: 12px; font-weight: 600; }
.char-current { color: #9ca3af; }
.char-sep     { color: #d1d5db; }
.char-limit   { color: #d1d5db; }
/* Turn the current count red when over the limit */
.char-count--over .char-current { color: #ef4444; }


/* Clear button — only rendered when there is text in the input */
.btn-clear {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 6px 12px;
  font-size: 12.5px; font-weight: 600;
  color: #6b7280;
  background: transparent;
  border: 1px solid #e5e7eb;
  border-radius: 8px; cursor: pointer;
  transition: all 0.15s;
}
.btn-clear:hover { background: #fef2f2; color: #ef4444; border-color: #fecaca; }


/* Submit / Load Text button — the primary action */
.btn-submit {
  display: inline-flex; align-items: center; gap: 7px;
  padding: 8px 22px;
  font-size: 13.5px; font-weight: 700;
  color: #fff;
  background: #2563eb;
  border: none; border-radius: 999px; cursor: pointer;
  box-shadow: 0 4px 14px rgba(37, 99, 235, 0.32);
  transition: background 0.2s, transform 0.15s, box-shadow 0.15s;
  white-space: nowrap;
}
.btn-submit:hover:not(:disabled) {
  background: #1d4ed8; transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(37, 99, 235, 0.40);
}
.btn-submit:disabled { opacity: 0.42; cursor: not-allowed; transform: none; box-shadow: none; }


/* Spinning loading indicator inside the submit button */
.btn-spinner {
  display: inline-block;
  width: 14px; height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.35);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.65s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* Spinning animation used on the feedback strip icons */
.spin { animation: spin 0.9s linear infinite; transform-origin: center; }


/* Small hint text at the very bottom of the bar */
.bar-hint {
  display: flex; align-items: center; justify-content: center; gap: 6px;
  font-size: 11.5px; color: #b0b8cc;
  margin: 0; flex-wrap: wrap;
}
.bar-hint kbd { font-size: 10.5px; padding: 1px 5px; color: #9ca3af; background: #f3f4f6; border-color: #e5e7eb; }
.hint-dot { color: #d1d5db; }


/* ─────────────────────────────────────────
   Vue <Transition> animations
───────────────────────────────────────── */

/* Drag overlay fades in/out */
.drag-fade-enter-active,
.drag-fade-leave-active { transition: opacity 0.2s ease; }
.drag-fade-enter-from,
.drag-fade-leave-to    { opacity: 0; }

/* Feedback strip slides up when appearing, fades when leaving */
.feedback-enter-active { transition: all 0.22s ease; }
.feedback-leave-active { transition: all 0.18s ease; }
.feedback-enter-from   { opacity: 0; transform: translateY(6px); }
.feedback-leave-to     { opacity: 0; transform: translateY(4px); }

/* Clear button pops in/out with a quick scale animation */
.fade-btn-enter-active { transition: all 0.18s ease; }
.fade-btn-leave-active { transition: all 0.14s ease; }
.fade-btn-enter-from   { opacity: 0; transform: scale(0.9); }
.fade-btn-leave-to     { opacity: 0; transform: scale(0.9); }


/* ─────────────────────────────────────────
   Responsive styles
───────────────────────────────────────── */

/* Tablet and below: switch to hamburger menu */
@media (max-width: 860px) {
  .nav-links     { display: none; }
  .nav-hamburger { display: flex; }
  .nav-inner     { padding: 0 16px; }

  /* Mobile nav drawer drops down from the navbar */
  .mobile-nav {
    display: block;
    position: fixed; top: 64px; left: 0; right: 0;
    background: rgba(255, 255, 255, 0.98);
    backdrop-filter: blur(18px);
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
}

/* Mobile: stack the action buttons vertically so they're not crowded */
@media (max-width: 600px) {
  .reading-area { padding-bottom: 260px; } /* extra bottom padding for taller stacked bar */
  .empty-title  { font-size: 18px; }
  .empty-features { gap: 6px; }

  .input-actions {
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
  }
  .actions-left  { justify-content: space-between; }
  .actions-right { justify-content: flex-end; }
  .btn-submit    { flex: 1; justify-content: center; }

  /* Hide hint row on small screens to save space */
  .bar-hint  { display: none; }
  .drag-card { padding: 36px 28px; }
}
</style>
