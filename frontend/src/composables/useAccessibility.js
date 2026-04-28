/**
 * useAccessibility.js
 * -------------------
 * Singleton composable that manages global accessibility settings:
 * colour theme, font size, and line height.
 *
 * Settings are persisted to localStorage so they survive page refreshes.
 * Changes are applied to the DOM immediately via CSS custom properties.
 *
 * Based on dyslexia-accessibility research:
 *   - Font size reference: 14 pt base → 16/18/20 px for Normal/Large/XL
 *   - Letter spacing: +70/1000 em (not exposed here; handled per-page)
 *   - Word spacing:   +270/1000 em (not exposed here; handled per-page)
 *   - Line height: 1.5 (normal) → 1.8 → 2.1 (spacious)
 *   - Colour overlays: mimic physical acetate sheets used in dyslexia therapy
 */

import { reactive, watch } from 'vue'

// ── Storage ───────────────────────────────────────────────────────────────────
const STORAGE_KEY = 'clearead-a11y'

// ── Config maps ───────────────────────────────────────────────────────────────

/**
 * Font size is implemented via CSS `zoom` on <html>.
 * Unlike font-size (which only affects rem units), zoom scales
 * everything — px, em, rem, images, layout — so all pages respond
 * regardless of whether they use rem or hardcoded px values.
 *
 * Zoom levels are proportional to a 16 px base (14 pt reference):
 *   normal  = 1.00 → 16 px baseline
 *   large   = 1.13 → ~18 px equivalent
 *   xlarge  = 1.25 → ~20 px equivalent
 */
export const FONT_SIZES = {
  normal: { label: 'Normal', zoom: '1',    display: '16 px' },
  large:  { label: 'Large',  zoom: '1.13', display: '~18 px' },
  xlarge: { label: 'XL',     zoom: '1.25', display: '~20 px' },
}

// Line height steps (unitless, cascades to all text via :root)
export const LINE_HEIGHTS = {
  normal:   { label: 'Normal',   value: '1.5' },
  relaxed:  { label: 'Relaxed',  value: '1.8' },
  spacious: { label: 'Spacious', value: '2.1' },
}

/**
 * Colour themes designed for users with dyslexia / visual stress.
 *
 * Light themes use mix-blend-mode:multiply overlay so the tint
 * colours white backgrounds while keeping dark text fully readable.
 *
 * Dark Calm uses a CSS filter invert approach (avoids pure black)
 * to reduce glare for users with light sensitivity.
 */
export const THEMES = {
  default: {
    label:   'Default',
    swatch:  '#2563eb',       // brand blue indicator
    overlay: 'transparent',
    dark:    false,
  },
  warm: {
    label:   'Warm Cream',
    swatch:  '#f9d97e',       // warm amber swatch
    overlay: 'rgba(255, 210, 100, 0.14)',
    dark:    false,
  },
  yellow: {
    label:   'Soft Yellow',
    swatch:  '#fef08a',       // soft yellow — most cited dyslexia overlay colour
    overlay: 'rgba(255, 248, 80, 0.16)',
    dark:    false,
  },
  blue: {
    label:   'Sky Blue',
    swatch:  '#7dd3fc',       // calming sky blue
    overlay: 'rgba(80, 190, 255, 0.14)',
    dark:    false,
  },
  dark: {
    label:   'Dark Calm',
    swatch:  '#1e1e2e',       // dark navy — avoids pure black halation effect
    overlay: 'transparent',   // overlay not used; CSS filter handles this instead
    dark:    true,
  },
}

// ── Singleton state ───────────────────────────────────────────────────────────
// reactive() so the entire object is tracked as one unit

const settings = reactive({
  theme:      'default',
  fontSize:   'normal',
  lineHeight: 'normal',
})

// ── Persistence helpers ───────────────────────────────────────────────────────

function loadFromStorage() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}')
    if (saved.theme      && saved.theme      in THEMES)       settings.theme      = saved.theme
    if (saved.fontSize   && saved.fontSize   in FONT_SIZES)   settings.fontSize   = saved.fontSize
    if (saved.lineHeight && saved.lineHeight in LINE_HEIGHTS)  settings.lineHeight = saved.lineHeight
  } catch { /* ignore corrupt storage data */ }
}

function saveToStorage() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...settings }))
  } catch { /* ignore storage errors */ }
}

// ── DOM application ───────────────────────────────────────────────────────────

/**
 * Pushes current settings onto the document.
 * Called automatically by the watcher below; also exported so
 * the toolbar component can call it on mount to restore saved settings.
 */
export function applyToDom() {
  const root = document.documentElement

  /**
   * Font size — applied as CSS `zoom` on <html>.
   * zoom scales everything proportionally (px, em, rem, images, layout),
   * so all pages respond even if they use hardcoded px values in scoped CSS.
   */
  root.style.zoom = FONT_SIZES[settings.fontSize]?.zoom || '1'

  /**
   * Line height — set on :root so it cascades down to all text via inheritance.
   * Elements that don't override line-height will pick this up automatically.
   */
  root.style.lineHeight = LINE_HEIGHTS[settings.lineHeight]?.value || '1.5'

  const theme = THEMES[settings.theme]

  if (theme?.dark) {
    // Dark Calm: invert the entire page (not pure 1.0 to avoid harsh pure-black)
    // hue-rotate(190deg) keeps most colours looking natural after inversion
    document.body.style.filter = 'invert(0.88) hue-rotate(190deg)'
    root.style.setProperty('--a11y-overlay', 'transparent')
  } else {
    // Light themes: clear any previous dark filter, apply colour overlay tint
    document.body.style.filter = ''
    root.style.setProperty('--a11y-overlay', theme?.overlay || 'transparent')
  }

  // Store current theme key as a data attribute for CSS targeting
  root.setAttribute('data-theme', settings.theme)
}

// ── Reset to defaults ─────────────────────────────────────────────────────────

export function resetSettings() {
  settings.theme      = 'default'
  settings.fontSize   = 'normal'
  settings.lineHeight = 'normal'
}

// ── Init ─────────────────────────────────────────────────────────────────────

// Restore saved preferences immediately on module load
loadFromStorage()

// Watch for any setting change → apply to DOM + persist
watch(settings, () => {
  applyToDom()
  saveToStorage()
}, { immediate: true })

// ── Export ────────────────────────────────────────────────────────────────────

export function useAccessibility() {
  return {
    settings,
    THEMES,
    FONT_SIZES,
    LINE_HEIGHTS,
    resetSettings,
    applyToDom,
  }
}
