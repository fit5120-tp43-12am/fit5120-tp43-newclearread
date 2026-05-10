<script setup>
import { ref, computed } from 'vue'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '')

// ── Navbar ────────────────────────────────────────────────────────────────────
const menuOpen = ref(false)

// ── Search state ─────────────────────────────────────────────────────────────
const query       = ref('')          // text in the search input
const result      = ref(null)        // { word, simpleMeaning, wordParts, meaningFromParts }
const loading     = ref(false)
const errorMsg    = ref('')
const searched    = ref(false)       // true after first search attempt

// ── TTS ───────────────────────────────────────────────────────────────────────
const ttsPlaying  = ref(false)

function speakWord() {
  if (!result.value) return
  window.speechSynthesis?.cancel()
  const text = [result.value.word, result.value.simpleMeaning].filter(Boolean).join('. ')
  const utt = new SpeechSynthesisUtterance(text)
  utt.lang = 'en-US'
  ttsPlaying.value = true
  utt.onend = utt.onerror = () => { ttsPlaying.value = false }
  window.speechSynthesis?.speak(utt)
}

// ── Lookup ────────────────────────────────────────────────────────────────────
function cleanWord(str) {
  return str.replace(/[^a-zA-Z'-]/g, '').toLowerCase().trim()
}

async function handleSearch() {
  const word = cleanWord(query.value)
  if (!word || word.length < 2) return

  loading.value  = true
  errorMsg.value = ''
  result.value   = null
  searched.value = true
  window.speechSynthesis?.cancel()
  ttsPlaying.value = false

  try {
    const res = await fetch(`${API_BASE_URL}/api/dictionary`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ word }),
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || 'Word not found.')
    result.value = data
  } catch (err) {
    errorMsg.value = err.message || 'Something went wrong. Please try again.'
  } finally {
    loading.value = false
  }
}

function handleKeydown(e) {
  if (e.key === 'Enter') handleSearch()
}

const hasWordParts        = computed(() => result.value?.wordParts?.length > 0)
const hasMeaningFromParts = computed(() => !!result.value?.meaningFromParts)


// ── Saved words (localStorage) ────────────────────────────────────────────────
// Each entry: { word, simpleMeaning, wordParts, meaningFromParts, savedAt }
const SAVED_KEY  = 'clearead-dict-saved'

function loadSavedWords() {
  try { return JSON.parse(localStorage.getItem(SAVED_KEY) || '[]') }
  catch { return [] }
}

const savedWords = ref(loadSavedWords())

/** Is the current result already in the saved list? */
const isSaved = computed(() =>
  result.value ? savedWords.value.some(w => w.word === result.value.word) : false
)

/** Save or unsave the current result word. */
function toggleSave() {
  if (!result.value) return
  if (isSaved.value) {
    savedWords.value = savedWords.value.filter(w => w.word !== result.value.word)
  } else {
    savedWords.value = [
      { ...result.value, savedAt: new Date().toISOString() },
      ...savedWords.value,
    ]
  }
  localStorage.setItem(SAVED_KEY, JSON.stringify(savedWords.value))
}

/** Remove one entry from the saved list. */
function removeSaved(word) {
  savedWords.value = savedWords.value.filter(w => w.word !== word)
  localStorage.setItem(SAVED_KEY, JSON.stringify(savedWords.value))
}

/** Clear every saved word. */
function clearAllSaved() {
  savedWords.value = []
  localStorage.removeItem(SAVED_KEY)
}

/** Load a saved entry back into the result card. */
function loadSaved(entry) {
  result.value   = entry
  query.value    = entry.word
  searched.value = true
  errorMsg.value = ''
  ttsPlaying.value = false
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

/** Human-readable relative date label. */
function relativeDate(iso) {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1)   return 'Just now'
  if (mins < 60)  return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24)   return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  if (days < 7)   return `${days}d ago`
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}
</script>


<template>
  <div class="page">

    <!-- ── Navbar ── -->
    <nav class="navbar">
      <div class="nav-inner">
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

        <ul class="nav-links">
          <li><RouterLink to="/"           class="nav-link">Home</RouterLink></li>
          <li><RouterLink to="/reading"    class="nav-link">Reading Support</RouterLink></li>
          <li><RouterLink to="/training"   class="nav-link">Training</RouterLink></li>
          <li><RouterLink to="/dictionary" class="nav-link nav-link--active">Dictionary</RouterLink></li>
          <li><RouterLink to="/dyslexia"   class="nav-link">Understand Dyslexia</RouterLink></li>
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
        <li><RouterLink to="/"           class="mobile-nav-link" @click="menuOpen = false">Home</RouterLink></li>
        <li><RouterLink to="/reading"    class="mobile-nav-link" @click="menuOpen = false">Reading Support</RouterLink></li>
        <li><RouterLink to="/training"   class="mobile-nav-link" @click="menuOpen = false">Training</RouterLink></li>
        <li><RouterLink to="/dictionary" class="mobile-nav-link" @click="menuOpen = false">Dictionary</RouterLink></li>
        <li><RouterLink to="/dyslexia"   class="mobile-nav-link" @click="menuOpen = false">Understand Dyslexia</RouterLink></li>
      </ul>
    </div>


    <!-- ── Main ── -->
    <main class="main">
      <div class="inner">

        <!-- Page header -->
        <div class="page-header">
          <div class="page-header-icon">
            <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
              <rect x="3" y="2" width="22" height="24" rx="3" stroke="currentColor" stroke-width="1.8" fill="none"/>
              <path d="M8 9h12M8 13h12M8 17h7" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
            </svg>
          </div>
          <div>
            <h1 class="page-title">Dictionary</h1>
            <p class="page-sub">Search any word to see its meaning and how it breaks down into parts.</p>
          </div>
        </div>

        <!-- Search bar -->
        <div class="search-card">
          <div class="search-row">
            <div class="search-input-wrap">
              <svg class="search-icon" width="18" height="18" viewBox="0 0 18 18" fill="none">
                <circle cx="8" cy="8" r="5.5" stroke="currentColor" stroke-width="1.6"/>
                <path d="M12.5 12.5l3 3" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
              </svg>
              <input
                v-model="query"
                class="search-input"
                type="text"
                placeholder="Type a word and press Enter…"
                spellcheck="false"
                autocomplete="off"
                @keydown="handleKeydown"
              />
              <button v-if="query" class="search-clear" @click="query = ''; result = null; searched = false; errorMsg = ''" aria-label="Clear">
                <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
                  <path d="M2 2l9 9M11 2l-9 9" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
                </svg>
              </button>
            </div>
            <button class="search-btn" :disabled="!query.trim() || loading" @click="handleSearch">
              <svg v-if="loading" class="spin" width="15" height="15" viewBox="0 0 15 15" fill="none">
                <circle cx="7.5" cy="7.5" r="5.5" stroke="rgba(255,255,255,0.4)" stroke-width="2"/>
                <path d="M7.5 2a5.5 5.5 0 0 1 5.5 5.5" stroke="white" stroke-width="2" stroke-linecap="round"/>
              </svg>
              <template v-else>
                Look up
                <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
                  <path d="M2 6.5H11M11 6.5L7 2.5M11 6.5L7 10.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </template>
            </button>
          </div>
          <p class="search-hint">
            <kbd>Enter</kbd> to search · double-click any word on the <RouterLink to="/reading" class="search-hint-link">Reading page</RouterLink> for a quick lookup
          </p>
        </div>


        <!-- ── Results ── -->

        <!-- Loading -->
        <div v-if="loading" class="state-loading">
          <svg class="spin" width="28" height="28" viewBox="0 0 28 28" fill="none">
            <circle cx="14" cy="14" r="11" stroke="#e0e7ff" stroke-width="3"/>
            <path d="M14 3a11 11 0 0 1 11 11" stroke="#4f46e5" stroke-width="3" stroke-linecap="round"/>
          </svg>
          <span>Looking up…</span>
        </div>

        <!-- Error -->
        <div v-else-if="errorMsg" class="state-error">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <circle cx="10" cy="10" r="9" stroke="#ef4444" stroke-width="1.5"/>
            <path d="M10 6v5M10 13.5v.5" stroke="#ef4444" stroke-width="1.8" stroke-linecap="round"/>
          </svg>
          <span>{{ errorMsg }}</span>
        </div>

        <!-- Empty state before first search -->
        <div v-else-if="!searched" class="state-empty">
          <div class="empty-illustration">
            <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
              <rect x="8" y="6" width="48" height="52" rx="6" fill="#eef2ff" stroke="#c7d2fe" stroke-width="1.5"/>
              <path d="M18 20h28M18 28h28M18 36h18" stroke="#a5b4fc" stroke-width="2" stroke-linecap="round"/>
              <circle cx="46" cy="46" r="12" fill="#4f46e5"/>
              <circle cx="46" cy="43" r="4" stroke="white" stroke-width="1.5" fill="none"/>
              <path d="M49 47l3.5 3.5" stroke="white" stroke-width="1.5" stroke-linecap="round"/>
            </svg>
          </div>
          <p class="empty-title">Search a word to get started</p>
          <p class="empty-sub">You'll see a simple definition, how the word breaks into parts, and what each part means.</p>
        </div>

        <!-- Result card -->
        <div v-else-if="result" class="result-card">

          <!-- Card header: word + TTS + Save -->
          <div class="result-header">
            <div class="result-header-left">
              <h2 class="result-word">{{ result.word }}</h2>
            </div>
            <div class="result-header-actions">
              <!-- Listen button -->
              <button class="result-tts-btn" :class="{ 'result-tts-btn--active': ttsPlaying }" @click="speakWord" title="Listen to pronunciation">
                <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
                  <path d="M3 6.5H6L9.5 3.5v11L6 11.5H3V6.5z" fill="currentColor"/>
                  <path d="M12 5a6 6 0 0 1 0 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" fill="none"/>
                  <path d="M13.5 7.5a3 3 0 0 1 0 3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" fill="none"/>
                </svg>
                {{ ttsPlaying ? 'Playing…' : 'Listen' }}
              </button>

              <!-- Save / Saved toggle -->
              <button
                class="result-save-btn"
                :class="{ 'result-save-btn--saved': isSaved }"
                @click="toggleSave"
                :title="isSaved ? 'Remove from saved words' : 'Save for later study'"
              >
                <!-- Bookmark icon: filled when saved, outline when not -->
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <path
                    v-if="isSaved"
                    d="M3 2h10a1 1 0 0 1 1 1v11l-6-3-6 3V3a1 1 0 0 1 1-1z"
                    fill="currentColor"
                  />
                  <path
                    v-else
                    d="M3 2h10a1 1 0 0 1 1 1v11l-6-3-6 3V3a1 1 0 0 1 1-1z"
                    stroke="currentColor" stroke-width="1.5"
                    stroke-linejoin="round" fill="none"
                  />
                </svg>
                {{ isSaved ? 'Saved' : 'Save' }}
              </button>
            </div>
          </div>

          <!-- Simple meaning -->
          <div v-if="result.simpleMeaning" class="result-section">
            <div class="result-section-label">Simple meaning</div>
            <p class="result-simple-meaning">{{ result.simpleMeaning }}</p>
          </div>

          <!-- Word parts -->
          <div v-if="hasWordParts" class="result-section">
            <div class="result-section-label">Word parts</div>
            <div class="result-parts">
              <div
                v-for="part in result.wordParts"
                :key="part.form + part.type"
                :class="['result-part-row', `result-part-row--${part.type?.toLowerCase()}`]"
              >
                <span class="result-part-form">{{ part.form }}</span>
                <span class="result-part-meaning">{{ part.meaning }}</span>
                <span :class="['result-part-badge', `result-part-badge--${part.type?.toLowerCase()}`]">
                  {{ part.type }}
                </span>
              </div>
            </div>
          </div>

          <!-- Meaning from parts -->
          <div v-if="hasMeaningFromParts" class="result-section result-section--last">
            <div class="result-section-label">Meaning from parts</div>
            <p class="result-parts-meaning">{{ result.meaningFromParts }}</p>
          </div>

        </div>

        <!-- ── Saved Words panel ── -->
        <!-- Always visible when there are saved words -->
        <div v-if="savedWords.length" class="saved-panel">

          <!-- Panel header -->
          <div class="saved-panel-header">
            <div class="saved-panel-title">
              <!-- Bookmark icon -->
              <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
                <path d="M2.5 2h10a1 1 0 0 1 1 1v10l-5.5-2.75L2.5 13V3a1 1 0 0 1 1-1z"
                  fill="#4f46e5" stroke="#4f46e5" stroke-width="0.5" stroke-linejoin="round"/>
              </svg>
              Saved Words
              <span class="saved-panel-count">{{ savedWords.length }}</span>
            </div>
            <button class="saved-clear-btn" @click="clearAllSaved" title="Remove all saved words">
              Clear all
            </button>
          </div>

          <!-- Word rows -->
          <ul class="saved-list">
            <li
              v-for="entry in savedWords"
              :key="entry.word"
              class="saved-item"
            >
              <!-- Clickable area: loads the word back -->
              <button class="saved-item-btn" @click="loadSaved(entry)">
                <span class="saved-item-word">{{ entry.word }}</span>
                <span v-if="entry.simpleMeaning" class="saved-item-meaning">
                  {{ entry.simpleMeaning.length > 60 ? entry.simpleMeaning.slice(0, 60) + '…' : entry.simpleMeaning }}
                </span>
              </button>

              <!-- Right: date + remove -->
              <div class="saved-item-meta">
                <span class="saved-item-date">{{ relativeDate(entry.savedAt) }}</span>
                <button class="saved-remove-btn" @click.stop="removeSaved(entry.word)" :title="`Remove '${entry.word}'`">
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                    <path d="M2 2l8 8M10 2l-8 8" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
                  </svg>
                </button>
              </div>
            </li>
          </ul>

        </div>

      </div>
    </main>

  </div>
</template>


<style scoped>

/* ── Page shell ── */
.page {
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
  background: #f8f9fc;
}

/* ── Navbar ── */
.navbar {
  flex-shrink: 0;
  position: sticky; top: 0;
  background: rgba(255,255,255,0.95);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid #e5e7eb;
  z-index: 50;
}
.nav-inner {
  max-width: 1200px; margin: 0 auto;
  padding: 0 36px; height: 64px;
  display: flex; align-items: center;
}
.nav-logo {
  display: flex; align-items: center; gap: 9px;
  font-size: 17px; font-weight: 700; color: #0d1117;
  letter-spacing: -0.4px; text-decoration: none; flex-shrink: 0;
}
.nav-links {
  display: flex; list-style: none;
  margin: 0 auto; padding: 0; gap: 2px;
}
.nav-link {
  display: block; padding: 6px 14px;
  font-size: 14px; font-weight: 500; color: #4b5563;
  text-decoration: none; border-radius: 999px;
  transition: color 0.2s, background 0.2s; position: relative;
}
.nav-link:hover { color: #0d1117; background: rgba(0,0,0,0.04); }
.nav-link--active { color: #0d1117; }
.nav-link--active::after {
  content: ''; position: absolute;
  bottom: -2px; left: 50%; transform: translateX(-50%);
  width: 4px; height: 4px; border-radius: 50%; background: #4f46e5;
}
.nav-hamburger {
  display: none; background: none; border: none; cursor: pointer;
  color: #0d1117; padding: 4px; margin-left: 12px;
  align-items: center; justify-content: center;
}
.mobile-nav { display: none; }

@media (max-width: 860px) {
  .nav-links     { display: none; }
  .nav-hamburger { display: flex; }
  .nav-inner     { padding: 0 16px; }
  .mobile-nav {
    display: block; position: fixed; top: 64px; left: 0; right: 0;
    background: rgba(255,255,255,0.98); backdrop-filter: blur(18px);
    border-bottom: 1px solid #e5e7eb; z-index: 99;
  }
  .mobile-nav-links { list-style: none; margin: 0; padding: 0; }
  .mobile-nav-link {
    display: block; padding: 16px 24px;
    font-size: 16px; font-weight: 500; color: #374151;
    text-decoration: none; border-bottom: 1px solid #f3f4f6;
    transition: background 0.15s;
  }
  .mobile-nav-link:hover { background: #f9fafb; color: #0d1117; }
}

/* ── Main content ── */
.main {
  flex: 1;
  padding: 48px 24px 80px;
}
.inner {
  max-width: 680px;
  margin: 0 auto;
  display: flex; flex-direction: column; gap: 28px;
}

/* ── Page header ── */
.page-header {
  display: flex; align-items: flex-start; gap: 18px;
}
.page-header-icon {
  flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  width: 54px; height: 54px;
  background: #eef2ff; border: 1.5px solid #c7d2fe;
  border-radius: 16px; color: #4f46e5;
}
.page-title {
  font-size: 30px; font-weight: 800; color: #0f172a;
  letter-spacing: -0.03em; margin: 0 0 6px; line-height: 1.2;
}
.page-sub {
  font-size: 15px; color: #64748b; margin: 0; line-height: 1.6;
}

/* ── Search card ── */
.search-card {
  background: #fff;
  border: 1.5px solid #e2e8f0;
  border-radius: 18px;
  padding: 20px 20px 14px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.05);
}
.search-row {
  display: flex; gap: 10px;
}
.search-input-wrap {
  flex: 1; position: relative;
  display: flex; align-items: center;
}
.search-icon {
  position: absolute; left: 14px;
  color: #94a3b8; flex-shrink: 0; pointer-events: none;
}
.search-input {
  width: 100%; height: 48px;
  padding: 0 40px 0 42px;
  font-size: 16px; font-weight: 500; color: #0f172a;
  font-family: inherit;
  background: #f8fafc; border: 1.5px solid #e2e8f0;
  border-radius: 12px; outline: none;
  transition: border-color 0.18s, box-shadow 0.18s;
}
.search-input:focus {
  border-color: #818cf8;
  box-shadow: 0 0 0 3px rgba(99,102,241,0.12);
  background: #fff;
}
.search-input::placeholder { color: #b0b8cc; }
.search-clear {
  position: absolute; right: 12px;
  display: flex; align-items: center; justify-content: center;
  width: 26px; height: 26px; border-radius: 50%;
  background: none; border: none; cursor: pointer;
  color: #94a3b8; transition: background 0.15s, color 0.15s;
}
.search-clear:hover { background: #f1f5f9; color: #475569; }

.search-btn {
  display: inline-flex; align-items: center; gap: 7px;
  padding: 0 22px; height: 48px;
  font-size: 14px; font-weight: 700; color: #fff;
  background: #4f46e5; border: none; border-radius: 12px;
  cursor: pointer; font-family: inherit; white-space: nowrap;
  box-shadow: 0 4px 14px rgba(79,70,229,0.28);
  transition: background 0.18s, transform 0.12s, box-shadow 0.18s;
}
.search-btn:hover:not(:disabled) {
  background: #4338ca;
  box-shadow: 0 6px 20px rgba(79,70,229,0.38);
  transform: translateY(-1px);
}
.search-btn:active:not(:disabled) { transform: translateY(0); }
.search-btn:disabled { opacity: 0.45; cursor: not-allowed; transform: none; box-shadow: none; }

.search-hint {
  margin: 12px 0 0;
  font-size: 12px; color: #94a3b8;
  display: flex; align-items: center; gap: 5px; flex-wrap: wrap;
}
.search-hint kbd {
  display: inline-flex; align-items: center;
  padding: 1px 6px; font-size: 11px; font-weight: 600;
  font-family: inherit; color: #64748b;
  background: #f1f5f9; border: 1px solid #e2e8f0;
  border-bottom-width: 2px; border-radius: 4px;
}
.search-hint-link {
  color: #4f46e5; text-decoration: none; font-weight: 600;
}
.search-hint-link:hover { text-decoration: underline; }

/* ── State: loading ── */
.state-loading {
  display: flex; align-items: center; justify-content: center; gap: 12px;
  padding: 48px 0;
  font-size: 15px; color: #64748b; font-weight: 500;
}

/* ── State: error ── */
.state-error {
  display: flex; align-items: center; gap: 10px;
  padding: 18px 20px;
  background: #fef2f2; border: 1px solid #fecaca; border-radius: 14px;
  font-size: 14px; color: #b91c1c; font-weight: 500;
}

/* ── State: empty ── */
.state-empty {
  display: flex; flex-direction: column; align-items: center;
  gap: 14px; padding: 56px 24px; text-align: center;
}
.empty-illustration { opacity: 0.85; }
.empty-title {
  font-size: 18px; font-weight: 700; color: #0f172a; margin: 0;
}
.empty-sub {
  font-size: 14px; color: #64748b; margin: 0; max-width: 400px; line-height: 1.65;
}

/* ── Result card ── */
.result-card {
  background: #fff;
  border: 1.5px solid #e2e8f0;
  border-radius: 20px;
  overflow: hidden;
  box-shadow:
    0 0 0 1px rgba(99,102,241,0.05),
    0 8px 32px rgba(0,0,0,0.08);
}

/* Header row: word title + TTS */
.result-header {
  display: flex; align-items: center; gap: 14px;
  padding: 26px 28px 20px;
  border-bottom: 1px solid #f1f5f9;
}
.result-header-left { flex: 1; min-width: 0; }
.result-word {
  font-size: 34px; font-weight: 900;
  color: #0f172a; letter-spacing: -0.04em; margin: 0;
  line-height: 1.1;
}

/* Header actions group */
.result-header-actions {
  display: flex; align-items: center; gap: 8px; flex-shrink: 0;
}

/* TTS button */
.result-tts-btn {
  display: inline-flex; align-items: center; gap: 7px;
  padding: 9px 18px;
  font-size: 13px; font-weight: 700;
  color: #4f46e5; background: #eef2ff;
  border: 1.5px solid #c7d2fe; border-radius: 999px;
  cursor: pointer; font-family: inherit; flex-shrink: 0;
  transition: background 0.15s, border-color 0.15s, color 0.15s;
}
.result-tts-btn:hover { background: #e0e7ff; border-color: #a5b4fc; }
.result-tts-btn--active { background: #4f46e5; color: #fff; border-color: #4f46e5; }

/* Save / Saved button */
.result-save-btn {
  display: inline-flex; align-items: center; gap: 7px;
  padding: 9px 18px;
  font-size: 13px; font-weight: 700;
  color: #64748b; background: #f8fafc;
  border: 1.5px solid #e2e8f0; border-radius: 999px;
  cursor: pointer; font-family: inherit; flex-shrink: 0;
  transition: background 0.15s, border-color 0.15s, color 0.15s, transform 0.1s;
}
.result-save-btn:hover { background: #f0fdf4; border-color: #86efac; color: #15803d; }
.result-save-btn:active { transform: scale(0.96); }
/* Saved state: green fill */
.result-save-btn--saved {
  background: #f0fdf4; border-color: #86efac; color: #15803d;
}
.result-save-btn--saved:hover { background: #fef2f2; border-color: #fca5a5; color: #dc2626; }

/* Content sections */
.result-section {
  padding: 20px 28px;
  border-bottom: 1px solid #f8fafc;
}
.result-section--last { border-bottom: none; }

.result-section-label {
  font-size: 10.5px; font-weight: 800;
  letter-spacing: 0.1em; text-transform: uppercase;
  color: #4f46e5; margin-bottom: 10px;
}

/* Simple meaning */
.result-simple-meaning {
  font-size: 16px; line-height: 1.75; color: #1e293b; margin: 0;
}

/* Word parts */
.result-parts {
  display: flex; flex-direction: column; gap: 10px;
}
.result-part-row {
  display: flex; align-items: center; gap: 12px;
  padding: 11px 14px;
  border-radius: 12px;
  border-left: 3px solid transparent;
}
.result-part-row--prefix { background: #fff1f2; border-left-color: #fda4af; }
.result-part-row--root   { background: #eff6ff; border-left-color: #93c5fd; }
.result-part-row--suffix { background: #f0fdf4; border-left-color: #86efac; }
.result-part-row--infix  { background: #faf5ff; border-left-color: #d8b4fe; }

.result-part-form {
  font-size: 14px; font-weight: 800;
  color: #0f172a; min-width: 54px; flex-shrink: 0;
}
.result-part-meaning {
  flex: 1; font-size: 14px; line-height: 1.5; color: #475569;
}
.result-part-badge {
  font-size: 11px; font-weight: 800;
  padding: 4px 11px; border-radius: 999px;
  letter-spacing: 0.04em; white-space: nowrap; flex-shrink: 0;
}
.result-part-badge--prefix { background: #ffe4e6; color: #e11d48; }
.result-part-badge--root   { background: #dbeafe; color: #1d4ed8; }
.result-part-badge--suffix { background: #dcfce7; color: #15803d; }
.result-part-badge--infix  { background: #ede9fe; color: #7c3aed; }

/* Meaning from parts */
.result-parts-meaning {
  font-size: 15px; line-height: 1.75;
  color: #334155; margin: 0; font-style: italic;
}

/* ── Saved Words panel ── */
.saved-panel {
  background: #fff;
  border: 1.5px solid #e2e8f0;
  border-radius: 20px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0,0,0,0.05);
}

.saved-panel-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 22px;
  border-bottom: 1px solid #f1f5f9;
}
.saved-panel-title {
  display: flex; align-items: center; gap: 8px;
  font-size: 13.5px; font-weight: 800; color: #0f172a;
}
.saved-panel-count {
  display: inline-flex; align-items: center; justify-content: center;
  min-width: 20px; height: 20px; padding: 0 6px;
  background: #eef2ff; color: #4f46e5;
  font-size: 11px; font-weight: 800; border-radius: 999px;
}
.saved-clear-btn {
  font-size: 12px; font-weight: 600; color: #94a3b8;
  background: none; border: none; cursor: pointer; font-family: inherit;
  padding: 4px 8px; border-radius: 6px;
  transition: background 0.15s, color 0.15s;
}
.saved-clear-btn:hover { background: #fef2f2; color: #dc2626; }

/* Word list */
.saved-list {
  list-style: none; margin: 0; padding: 0;
}
.saved-item {
  display: flex; align-items: center; gap: 12px;
  padding: 0 12px 0 0;
  border-bottom: 1px solid #f8fafc;
  transition: background 0.12s;
}
.saved-item:last-child { border-bottom: none; }
.saved-item:hover { background: #fafbff; }

/* Clickable left part */
.saved-item-btn {
  flex: 1; min-width: 0;
  display: flex; flex-direction: column; align-items: flex-start; gap: 2px;
  padding: 14px 8px 14px 22px;
  background: none; border: none; cursor: pointer; font-family: inherit;
  text-align: left;
}
.saved-item-word {
  font-size: 15px; font-weight: 800; color: #0f172a;
  letter-spacing: -0.02em;
}
.saved-item-meaning {
  font-size: 12.5px; color: #64748b; line-height: 1.4;
}
.saved-item-btn:hover .saved-item-word { color: #4f46e5; }

/* Right meta: date + remove */
.saved-item-meta {
  display: flex; align-items: center; gap: 8px; flex-shrink: 0;
}
.saved-item-date {
  font-size: 11.5px; color: #94a3b8; white-space: nowrap;
}
.saved-remove-btn {
  display: flex; align-items: center; justify-content: center;
  width: 26px; height: 26px; border-radius: 50%;
  background: none; border: none; cursor: pointer;
  color: #cbd5e1; transition: background 0.15s, color 0.15s;
}
.saved-remove-btn:hover { background: #fee2e2; color: #ef4444; }

/* Spin utility */
.spin { animation: spin 0.9s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* Mobile */
@media (max-width: 600px) {
  .main { padding: 32px 16px 60px; }
  .page-header { flex-direction: column; gap: 12px; }
  .page-header-icon { width: 44px; height: 44px; }
  .page-title { font-size: 24px; }
  .search-row { flex-direction: column; }
  .search-btn { width: 100%; justify-content: center; height: 44px; }
  .result-word { font-size: 26px; }
  .result-header { padding: 20px 20px 16px; }
  .result-section { padding: 16px 20px; }
  .result-header { flex-wrap: wrap; }
}
</style>
