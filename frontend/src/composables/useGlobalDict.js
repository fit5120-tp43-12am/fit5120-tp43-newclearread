/**
 * useGlobalDict.js
 * ─────────────────────────────────────────────────────────────────
 * Singleton composable: shared dictionary-popup state + logic.
 *
 * Because the `ref` objects are defined at *module* level (outside the
 * exported function) they are shared across every component that imports
 * this file — meaning the popup opened on one page is the same object
 * rendered in App.vue.
 *
 * Usage
 * ──────
 *   import { useGlobalDict } from '@/composables/useGlobalDict'
 *   const { dictPopup, handleWordDblClick, speakDictWord, closeDictPopup } = useGlobalDict()
 */

import { ref } from 'vue'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '')

// ── Shared state (module-level = singleton) ───────────────────────────────────
const dictPopup  = ref(null)   // null | { word, data, x, y, loading, error }

// ── Helpers ───────────────────────────────────────────────────────────────────

function cleanWord(str) {
  return str.replace(/[^a-zA-Z'-]/g, '').toLowerCase().trim()
}

/**
 * Fire on every document dblclick.
 * Skips interactive targets (buttons, links, inputs) so normal UI still works.
 */
async function handleWordDblClick(e) {
  // Skip interactive elements
  if (e.target.closest('button, a, input, textarea, select, [role="button"]')) return

  const raw  = window.getSelection()?.toString() || ''
  const word = cleanWord(raw)
  if (!word || word.length < 2) return

  // Position popup near the click, keeping it inside the viewport
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
    // Show a placeholder so the UI is always responsive even without backend
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
  return { dictPopup, handleWordDblClick, speakDictWord, closeDictPopup }
}
