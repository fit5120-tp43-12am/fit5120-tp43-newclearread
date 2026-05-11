<script setup>
/**
 * GlobalDictPopup.vue
 * ─────────────────────────────────────────────────────────────────
 * Floating dictionary popup rendered once at the App root level.
 * Shown when the user double-clicks any word anywhere on the site.
 * State is shared via useGlobalDict() composable (singleton refs).
 */
import { ref } from 'vue'
import { useGlobalDict } from '../composables/useGlobalDict'

const { dictPopup, speakDictWord, closeDictPopup, isSaved, toggleSave } = useGlobalDict()

// ── Drag logic ────────────────────────────────────────────────────────────────
const dragging = ref(false)
let dragOffsetX = 0
let dragOffsetY = 0

function onDragStart(e) {
  if (!dictPopup.value) return
  dragging.value = true
  dragOffsetX = e.clientX - dictPopup.value.x
  dragOffsetY = e.clientY - dictPopup.value.y
  window.addEventListener('mousemove', onDragMove)
  window.addEventListener('mouseup', onDragEnd)
}

function onDragMove(e) {
  if (!dragging.value || !dictPopup.value) return
  const CARD_W = 340
  const CARD_H = 80  // minimum visible strip
  const newX = Math.max(0, Math.min(e.clientX - dragOffsetX, window.innerWidth  - CARD_W))
  const newY = Math.max(0, Math.min(e.clientY - dragOffsetY, window.innerHeight - CARD_H))
  dictPopup.value = { ...dictPopup.value, x: newX, y: newY }
}

function onDragEnd() {
  dragging.value = false
  window.removeEventListener('mousemove', onDragMove)
  window.removeEventListener('mouseup', onDragEnd)
}
</script>

<template>
  <Transition name="dict-pop">
    <div
      v-if="dictPopup"
      class="dict-backdrop"
      @click.self="!dragging && closeDictPopup()"
    >
      <div
        class="dict-card"
        :style="{ left: dictPopup.x + 'px', top: dictPopup.y + 'px' }"
        @click.stop
      >

        <!-- Header: word + TTS + close (drag handle) -->
        <div class="dict-header" @mousedown.prevent="onDragStart" :class="{ 'dict-header--dragging': dragging }">
          <h3 class="dict-word">{{ dictPopup.word }}</h3>
          <div class="dict-header-actions">
            <button class="dict-tts-btn" title="Listen" @click="speakDictWord()">
              <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
                <path d="M2 5H4.5L7.5 2.5v10L4.5 10H2V5z" fill="currentColor"/>
                <path d="M10 4a5 5 0 0 1 0 7" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
                <path d="M11.5 6a2.5 2.5 0 0 1 0 3" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
              </svg>
            </button>
            <!-- Save / unsave button — only shown when result data is loaded -->
            <button
              v-if="dictPopup.data && !dictPopup.loading"
              :class="['dict-save-btn', { 'dict-save-btn--saved': isSaved }]"
              :title="isSaved ? 'Remove from saved' : 'Save word'"
              @click="toggleSave"
            >
              <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
                <path
                  d="M6.5 1.5l1.5 3 3.3.5-2.4 2.3.6 3.2L6.5 9 3 10.5l.6-3.2L1.2 5l3.3-.5z"
                  :fill="isSaved ? 'currentColor' : 'none'"
                  stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"
                />
              </svg>
            </button>
            <button class="dict-close-btn" title="Close" @click="closeDictPopup">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                <path d="M1.5 1.5l9 9M10.5 1.5l-9 9" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
              </svg>
            </button>
          </div>
        </div>

        <!-- Loading -->
        <div v-if="dictPopup.loading" class="dict-loading">
          <svg class="spin" width="18" height="18" viewBox="0 0 18 18" fill="none">
            <circle cx="9" cy="9" r="7" stroke="#c7d2fe" stroke-width="2.5" stroke-dasharray="28 14" stroke-linecap="round"/>
          </svg>
          <span>Looking up…</span>
        </div>

        <!-- Error -->
        <div v-else-if="dictPopup.error" class="dict-error">
          {{ dictPopup.error }}
        </div>

        <!-- Result -->
        <div v-else-if="dictPopup.data" class="dict-body">

          <div v-if="dictPopup.data.simpleMeaning" class="dict-section">
            <div class="dict-section-label">Simple meaning</div>
            <p class="dict-simple-meaning">{{ dictPopup.data.simpleMeaning }}</p>
          </div>

          <div v-if="dictPopup.data.wordParts?.length" class="dict-section">
            <div class="dict-section-label">Word parts</div>
            <div class="dict-parts">
              <div
                v-for="part in dictPopup.data.wordParts"
                :key="part.form + part.type"
                :class="['dict-part-row', `dict-part-row--${part.type?.toLowerCase()}`]"
              >
                <span class="dict-part-form">{{ part.form }}</span>
                <span class="dict-part-meaning">{{ part.meaning }}</span>
                <span :class="['dict-part-badge', `dict-part-badge--${part.type?.toLowerCase()}`]">
                  {{ part.type }}
                </span>
              </div>
            </div>
          </div>

          <div v-if="dictPopup.data.meaningFromParts" class="dict-section dict-section--last">
            <div class="dict-section-label">Meaning from parts</div>
            <p class="dict-parts-meaning">{{ dictPopup.data.meaningFromParts }}</p>
          </div>

        </div>

      </div>
    </div>
  </Transition>
</template>

<style scoped>
/* Transparent full-screen layer — catches outside clicks to close popup */
.dict-backdrop {
  position: fixed; inset: 0;
  z-index: 9000;
  pointer-events: all;    /* catches clicks outside the card */
  cursor: default;
}
.dict-card {
  pointer-events: all;
  position: fixed;
  width: 340px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 18px;
  box-shadow:
    0 4px 6px rgba(0,0,0,0.04),
    0 12px 40px rgba(0,0,0,0.12),
    0 2px 0 rgba(255,255,255,0.8) inset;
  overflow: hidden;
}

/* Header — doubles as drag handle */
.dict-header {
  display: flex; align-items: center;
  padding: 18px 18px 14px 20px;
  border-bottom: 1px solid #f1f5f9;
  gap: 8px;
  cursor: grab;
  user-select: none;
}
.dict-header--dragging { cursor: grabbing; }
.dict-header:active { cursor: grabbing; }
.dict-word {
  flex: 1;
  font-size: 22px; font-weight: 800;
  color: #0f172a; letter-spacing: -0.03em; margin: 0;
}
.dict-header-actions { display: flex; align-items: center; gap: 6px; }

/* TTS button */
.dict-tts-btn {
  display: flex; align-items: center; justify-content: center;
  width: 32px; height: 32px; border-radius: 50%;
  background: none; border: none; cursor: pointer;
  color: #6366f1;
  transition: background 0.15s, color 0.15s;
}
.dict-tts-btn:hover { background: #e0e7ff; color: #4f46e5; }

/* Save button */
.dict-save-btn {
  display: flex; align-items: center; justify-content: center;
  width: 32px; height: 32px; border-radius: 50%;
  background: none; border: none; cursor: pointer;
  color: #94a3b8;
  transition: background 0.15s, color 0.15s;
}
.dict-save-btn:hover { background: #fef9c3; color: #ca8a04; }
.dict-save-btn--saved { color: #f59e0b; }
.dict-save-btn--saved:hover { background: #fee2e2; color: #ef4444; }

/* Close button */
.dict-close-btn {
  display: flex; align-items: center; justify-content: center;
  width: 28px; height: 28px; border-radius: 50%;
  background: none; border: none; cursor: pointer;
  color: #94a3b8;
  transition: background 0.15s, color 0.15s;
}
.dict-close-btn:hover { background: #fee2e2; color: #ef4444; }

/* Loading */
.dict-loading {
  display: flex; align-items: center; gap: 10px;
  padding: 20px; color: #94a3b8; font-size: 13px; font-weight: 500;
}

/* Error */
.dict-error {
  padding: 16px 20px;
  font-size: 13px; color: #ef4444;
}

/* Body */
.dict-body {
  display: flex; flex-direction: column;
  max-height: 60vh; overflow-y: auto;
}

/* Section block */
.dict-section {
  padding: 14px 20px;
  border-bottom: 1px solid #f8fafc;
}
.dict-section--last { border-bottom: none; }
.dict-section-label {
  font-size: 10.5px; font-weight: 800;
  letter-spacing: 0.1em; text-transform: uppercase;
  color: #94a3b8; margin-bottom: 8px;
}

/* Simple meaning */
.dict-simple-meaning {
  font-size: 14.5px; line-height: 1.7;
  color: #1e293b; margin: 0;
}

/* Word parts */
.dict-parts { display: flex; flex-direction: column; gap: 8px; }
.dict-part-row {
  display: flex; align-items: center; gap: 10px;
  padding: 9px 12px; border-radius: 10px;
  border-left: 3px solid transparent;
}
.dict-part-row--prefix  { background: #fff1f2; border-left-color: #fda4af; }
.dict-part-row--root    { background: #eff6ff; border-left-color: #93c5fd; }
.dict-part-row--suffix  { background: #f0fdf4; border-left-color: #86efac; }
.dict-part-row--infix   { background: #faf5ff; border-left-color: #d8b4fe; }

.dict-part-form    { font-size: 13px; font-weight: 800; color: #0f172a; min-width: 46px; flex-shrink: 0; }
.dict-part-meaning { flex: 1; font-size: 13px; line-height: 1.5; color: #475569; }

/* Type badge */
.dict-part-badge {
  font-size: 10.5px; font-weight: 800;
  padding: 3px 9px; border-radius: 999px;
  letter-spacing: 0.06em; text-transform: uppercase;
  white-space: nowrap; flex-shrink: 0;
}
.dict-part-badge--prefix { background: #ffe4e6; color: #e11d48; }
.dict-part-badge--root   { background: #dbeafe; color: #1d4ed8; }
.dict-part-badge--suffix { background: #dcfce7; color: #15803d; }
.dict-part-badge--infix  { background: #ede9fe; color: #7c3aed; }

/* Meaning from parts */
.dict-parts-meaning {
  font-size: 13.5px; line-height: 1.7;
  color: #334155; margin: 0; font-style: italic;
}

/* Pop-in transition */
.dict-pop-enter-active { transition: opacity 0.18s ease; }
.dict-pop-leave-active { transition: opacity 0.14s ease; }
.dict-pop-enter-from,
.dict-pop-leave-to { opacity: 0; }
.dict-pop-enter-active .dict-card {
  animation: dict-card-in 0.22s cubic-bezier(0.34, 1.4, 0.64, 1);
}
@keyframes dict-card-in {
  from { transform: scale(0.88) translateY(8px); opacity: 0; }
  to   { transform: scale(1) translateY(0);      opacity: 1; }
}

/* Spin utility */
.spin { animation: spin 0.9s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
