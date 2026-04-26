import { ref, computed } from 'vue'

const FONT_SIZES = [
  { id: 'sm',  label: 'S',  px: 14 },
  { id: 'md',  label: 'M',  px: 16 },
  { id: 'lg',  label: 'L',  px: 18 },
  { id: 'xl',  label: 'XL', px: 20 },
  { id: 'xxl', label: 'XXL',px: 22 },
]

const THEMES = [
  { id: 'light',         label: 'Light',    bg: '#ffffff', fg: '#0d1117' },
  { id: 'dark',          label: 'Dark',     bg: '#0d1117', fg: '#e6edf3' },
  { id: 'high-contrast', label: 'Contrast', bg: '#000000', fg: '#ffffff' },
  { id: 'warm',          label: 'Warm',     bg: '#fdf5e6', fg: '#2c1810' },
  { id: 'sky',           label: 'Sky',      bg: '#eef4ff', fg: '#0d1940' },
]

// module-level singletons — shared across all component instances
const fontSizeIdx = ref(1)
const currentTheme = ref('light')

function applyToDOM() {
  const html = document.documentElement
  html.setAttribute('data-font-size', FONT_SIZES[fontSizeIdx.value].id)
  html.setAttribute('data-theme', currentTheme.value)
}

export function initAccessibility() {
  const savedFont  = localStorage.getItem('a11y-font')
  const savedTheme = localStorage.getItem('a11y-theme')

  if (savedFont !== null) {
    const idx = parseInt(savedFont, 10)
    if (idx >= 0 && idx < FONT_SIZES.length) fontSizeIdx.value = idx
  }
  if (savedTheme && THEMES.some(t => t.id === savedTheme)) {
    currentTheme.value = savedTheme
  }
  applyToDOM()
}

export function useAccessibility() {
  function increaseFontSize() {
    if (fontSizeIdx.value < FONT_SIZES.length - 1) {
      fontSizeIdx.value++
      localStorage.setItem('a11y-font', fontSizeIdx.value)
      applyToDOM()
    }
  }

  function decreaseFontSize() {
    if (fontSizeIdx.value > 0) {
      fontSizeIdx.value--
      localStorage.setItem('a11y-font', fontSizeIdx.value)
      applyToDOM()
    }
  }

  function setTheme(themeId) {
    currentTheme.value = themeId
    localStorage.setItem('a11y-theme', themeId)
    applyToDOM()
  }

  function resetAll() {
    fontSizeIdx.value  = 1
    currentTheme.value = 'light'
    localStorage.removeItem('a11y-font')
    localStorage.removeItem('a11y-theme')
    applyToDOM()
  }

  return {
    fontSizeIdx,
    currentTheme,
    FONT_SIZES,
    THEMES,
    canIncrease:     computed(() => fontSizeIdx.value < FONT_SIZES.length - 1),
    canDecrease:     computed(() => fontSizeIdx.value > 0),
    currentFontSize: computed(() => FONT_SIZES[fontSizeIdx.value]),
    increaseFontSize,
    decreaseFontSize,
    setTheme,
    resetAll,
  }
}
