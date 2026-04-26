<script setup>
import { ref } from 'vue'
import { useAccessibility } from '../composables/useAccessibility.js'

const open = ref(false)

const {
  fontSizeIdx,
  currentTheme,
  FONT_SIZES,
  THEMES,
  canIncrease,
  canDecrease,
  currentFontSize,
  increaseFontSize,
  decreaseFontSize,
  setTheme,
  resetAll,
} = useAccessibility()
</script>

<template>
  <!-- Floating accessibility widget -->
  <div class="a11y-widget" :class="{ 'a11y-widget--open': open }">

    <!-- Panel -->
    <Transition name="panel">
      <div v-if="open" class="a11y-panel" role="dialog" aria-label="Accessibility settings">
        <div class="a11y-panel-header">
          <span class="a11y-panel-title">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <circle cx="8" cy="3.5" r="1.5" fill="currentColor"/>
              <path d="M5 6.5h6M8 6.5v6M6 9.5l-2 3M10 9.5l2 3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
            </svg>
            Accessibility
          </span>
          <button class="a11y-reset" @click="resetAll" title="Reset to defaults">Reset</button>
        </div>

        <!-- Font size -->
        <div class="a11y-section">
          <p class="a11y-section-label">Text Size</p>
          <div class="a11y-font-row">
            <button
              class="a11y-font-btn"
              :disabled="!canDecrease"
              @click="decreaseFontSize"
              aria-label="Decrease font size"
            >
              <span style="font-size:12px;font-weight:700">A</span>
            </button>

            <div class="a11y-font-track">
              <button
                v-for="(size, idx) in FONT_SIZES"
                :key="size.id"
                class="a11y-font-dot"
                :class="{ 'a11y-font-dot--active': fontSizeIdx === idx }"
                @click="fontSizeIdx === idx ? null : (idx > fontSizeIdx ? increaseFontSize() : decreaseFontSize())"
                :aria-label="`Font size ${size.label}`"
              ></button>
            </div>

            <button
              class="a11y-font-btn"
              :disabled="!canIncrease"
              @click="increaseFontSize"
              aria-label="Increase font size"
            >
              <span style="font-size:17px;font-weight:700">A</span>
            </button>
          </div>
          <p class="a11y-font-label">{{ currentFontSize.label }} ({{ currentFontSize.px }}px)</p>
        </div>

        <!-- Theme -->
        <div class="a11y-section">
          <p class="a11y-section-label">Theme</p>
          <div class="a11y-themes">
            <button
              v-for="theme in THEMES"
              :key="theme.id"
              class="a11y-theme-btn"
              :class="{ 'a11y-theme-btn--active': currentTheme === theme.id }"
              :style="{ background: theme.bg, color: theme.fg, borderColor: currentTheme === theme.id ? theme.fg : 'rgba(0,0,0,0.12)' }"
              @click="setTheme(theme.id)"
              :aria-label="`${theme.label} theme`"
              :aria-pressed="currentTheme === theme.id"
            >
              {{ theme.label }}
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Toggle button -->
    <button
      class="a11y-toggle"
      @click="open = !open"
      :aria-expanded="open"
      :aria-label="open ? 'Close accessibility settings' : 'Open accessibility settings'"
      :title="open ? 'Close accessibility settings' : 'Open accessibility settings'"
    >
      <svg v-if="!open" width="22" height="22" viewBox="0 0 22 22" fill="none" aria-hidden="true">
        <circle cx="11" cy="5" r="2" fill="currentColor"/>
        <path d="M7 9h8M11 9v8M9 13l-2.5 4M13 13l2.5 4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
      </svg>
      <svg v-else width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
        <path d="M3 3l10 10M13 3L3 13" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      </svg>
    </button>

  </div>
</template>

<style scoped>
.a11y-widget {
  position: fixed;
  bottom: 28px;
  right: 28px;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 10px;
  font-family: 'Inter', system-ui, sans-serif;
}

/* Toggle button */
.a11y-toggle {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: #2563eb;
  color: #fff;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 16px rgba(37, 99, 235, 0.4), 0 2px 6px rgba(0,0,0,0.15);
  transition: background 0.2s, transform 0.15s, box-shadow 0.2s;
  flex-shrink: 0;
}
.a11y-toggle:hover {
  background: #1d4ed8;
  transform: scale(1.08);
  box-shadow: 0 6px 20px rgba(37, 99, 235, 0.5), 0 2px 8px rgba(0,0,0,0.18);
}
.a11y-toggle:focus-visible {
  outline: 3px solid #93c5fd;
  outline-offset: 2px;
}

/* Panel */
.a11y-panel {
  background: #fff;
  border: 1px solid rgba(0,0,0,0.08);
  border-radius: 16px;
  box-shadow: 0 16px 48px rgba(0,0,0,0.12), 0 4px 16px rgba(0,0,0,0.07);
  padding: 0;
  width: 280px;
  overflow: hidden;
}

.a11y-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px 12px;
  border-bottom: 1px solid rgba(0,0,0,0.07);
  background: #f8faff;
}
.a11y-panel-title {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 13px;
  font-weight: 700;
  color: #0d1117;
  letter-spacing: -0.01em;
}
.a11y-reset {
  font-size: 11px;
  font-weight: 600;
  color: #6b7280;
  background: none;
  border: 1px solid rgba(0,0,0,0.1);
  border-radius: 6px;
  padding: 3px 9px;
  cursor: pointer;
  transition: color 0.15s, background 0.15s;
  font-family: inherit;
}
.a11y-reset:hover {
  color: #2563eb;
  background: #eef2ff;
  border-color: #c7d7fe;
}

.a11y-section {
  padding: 14px 16px;
  border-bottom: 1px solid rgba(0,0,0,0.06);
}
.a11y-section:last-child { border-bottom: none; }

.a11y-section-label {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #9ca3af;
  margin: 0 0 10px;
}

/* Font size controls */
.a11y-font-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.a11y-font-btn {
  width: 34px;
  height: 34px;
  border-radius: 8px;
  border: 1px solid rgba(0,0,0,0.1);
  background: #f9fafb;
  color: #374151;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s, border-color 0.15s;
  flex-shrink: 0;
  font-family: inherit;
}
.a11y-font-btn:hover:not(:disabled) {
  background: #eef2ff;
  border-color: #c7d7fe;
  color: #2563eb;
}
.a11y-font-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}
.a11y-font-track {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 4px;
  padding: 0 2px;
}
.a11y-font-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  border: 2px solid #d1d5db;
  background: transparent;
  cursor: pointer;
  padding: 0;
  transition: border-color 0.15s, background 0.15s, transform 0.15s;
}
.a11y-font-dot--active {
  background: #2563eb;
  border-color: #2563eb;
  transform: scale(1.3);
}
.a11y-font-dot:hover:not(.a11y-font-dot--active) {
  border-color: #93c5fd;
  background: #dbeafe;
}
.a11y-font-label {
  font-size: 11px;
  color: #9ca3af;
  margin: 7px 0 0;
  text-align: center;
}

/* Theme buttons */
.a11y-themes {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 7px;
}
.a11y-theme-btn {
  padding: 7px 6px;
  border-radius: 8px;
  border: 2px solid transparent;
  font-size: 11.5px;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.12s, box-shadow 0.12s;
  font-family: inherit;
  letter-spacing: -0.01em;
}
.a11y-theme-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 3px 10px rgba(0,0,0,0.15);
}
.a11y-theme-btn--active {
  box-shadow: 0 0 0 2px rgba(37,99,235,0.35), 0 3px 10px rgba(0,0,0,0.15);
  transform: translateY(-1px);
}

/* Panel transition */
.panel-enter-active,
.panel-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.panel-enter-from,
.panel-leave-to {
  opacity: 0;
  transform: translateY(8px) scale(0.97);
}

/* Mobile: smaller offset */
@media (max-width: 480px) {
  .a11y-widget {
    bottom: 16px;
    right: 16px;
  }
  .a11y-panel {
    width: calc(100vw - 32px);
    max-width: 280px;
  }
}
</style>
