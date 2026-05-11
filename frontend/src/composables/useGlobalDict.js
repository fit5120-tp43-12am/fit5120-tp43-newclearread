/**
 * useGlobalDict.js
 * ─────────────────────────────────────────────────────────────────
 * Singleton composable: shared dictionary-popup state + saved-words logic.
 *
 * Because all refs are defined at *module* level they are shared across
 * every component that imports this file — one popup, one saved list,
 * everywhere on the site.
 *
 * Usage
 * ──────
 *   import { useGlobalDict } from '../composables/useGlobalDict'
 *   const { dictPopup, isSaved, toggleSave, savedWords, ... } = useGlobalDict()
 */

import { ref, computed } from 'vue'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '')

// ── Popup state ───────────────────────────────────────────────────────────────
const dictPopup = ref(null)   // null | { word, data, x, y, loading, error }

// ── Saved words (localStorage) ────────────────────────────────────────────────
const SAVED_KEY = 'clearead-dict-saved'

function loadSavedWords() {
  try { return JSON.parse(localStorage.getItem(SAVED_KEY) || '[]') }
  catch { return [] }
}

const savedWords = ref(loadSavedWords())

/** Is the word currently shown in the popup already saved? */
const isSaved = computed(() =>
  dictPopup.value?.data
    ? savedWords.value.some(w => w.word === dictPopup.value.data.word)
    : false
)

/** Save or unsave the word currently shown in the popup. */
function toggleSave() {
  if (!dictPopup.value?.data) return
  const entry = dictPopup.value.data
  if (isSaved.value) {
    savedWords.value = savedWords.value.filter(w => w.word !== entry.word)
  } else {
    savedWords.value = [
      { ...entry, savedAt: new Date().toISOString() },
      ...savedWords.value,
    ]
  }
  localStorage.setItem(SAVED_KEY, JSON.stringify(savedWords.value))
}

/** Remove one entry from the saved list by word string. */
function removeSaved(word) {
  savedWords.value = savedWords.value.filter(w => w.word !== word)
  localStorage.setItem(SAVED_KEY, JSON.stringify(savedWords.value))
}

/** Clear every saved word. */
function clearAllSaved() {
  savedWords.value = []
  localStorage.removeItem(SAVED_KEY)
}

/** Load a saved entry into the popup (used from Dictionary page). */
function loadSavedIntoPopup(entry) {
  dictPopup.value = {
    word: entry.word,
    data: entry,
    x: window.innerWidth / 2 - 170,
    y: 120,
    loading: false,
    error: null,
  }
}

/** Human-readable relative date label. */
function relativeDate(iso) {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1)  return 'Just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24)  return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  if (days < 7)  return `${days}d ago`
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function cleanWord(str) {
  return str.replace(/[^a-zA-Z'-]/g, '').toLowerCase().trim()
}

/**
 * Global dblclick handler — registered on document in App.vue.
 * Skips interactive elements so buttons/links still work normally.
 */
async function handleWordDblClick(e) {
  if (e.target.closest('button, a, input, textarea, select, [role="button"]')) return

  const raw  = window.getSelection()?.toString() || ''
  const word = cleanWord(raw)
  if (!word || word.length < 2) return

  const POPUP_W = 340
  const x = Math.min(e.clientX - 12, window.innerWidth - POPUP_W - 16)
  const y = e.clientY + 18

  dictPopup.value = { word, data: null, x, y, loading: true, error: null }

  try {
    const res  = await fetch(`${API_BASE_URL}/api/dictionary`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ word }),
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || 'Word not found.')
    dictPopup.value = { ...dictPopup.value, data, loading: false }
  } catch {
    dictPopup.value = {
      ...dictPopup.value,
      loading: false,
      error:   null,
      data: {
        word,
        simpleMeaning:   `Could not find "${word}". Check your connection and try again.`,
        wordParts:        [],
        meaningFromParts: '',
      },
    }
  }
}

function speakDictWord(rate = 1) {
  if (!dictPopup.value?.data) return
  const text = [dictPopup.value.data.word, dictPopup.value.data.simpleMeaning]
    .filter(Boolean).join('. ')
  window.speechSynthesis?.cancel()
  const utt = new SpeechSynthesisUtterance(text)
  utt.lang = 'en-US'
  utt.rate = rate
  window.speechSynthesis?.speak(utt)
}

function closeDictPopup() {
  dictPopup.value = null
  window.speechSynthesis?.cancel()
}

// ── Export ────────────────────────────────────────────────────────────────────
export function useGlobalDict() {
  return {
    // Popup
    dictPopup,
    handleWordDblClick,
    speakDictWord,
    closeDictPopup,
    // Saved words
    savedWords,
    isSaved,
    toggleSave,
    removeSaved,
    clearAllSaved,
    loadSavedIntoPopup,
    relativeDate,
  }
}
