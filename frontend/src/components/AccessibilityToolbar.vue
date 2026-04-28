<script setup>
import { ref, onMounted } from 'vue'
import { useAccessibility, applyToDom } from '../composables/useAccessibility.js'

// Pull shared state and config from the singleton composable
const { settings, THEMES, FONT_SIZES, LINE_HEIGHTS, resetSettings } = useAccessibility()

// Controls whether the settings panel is open or closed
const panelOpen = ref(false)

function togglePanel() { panelOpen.value = !panelOpen.value }
function closePanel()  { panelOpen.value = false }

// Apply saved settings to the DOM once the component is mounted
onMounted(() => applyToDom())
</script>


<template>
  <!--
    Wrapper — positioned in the top-right corner of the viewport (inside the navbar area).
    z-index: 200 keeps it above the navbar (z-index: 50) and page content.
  -->
  <div class="a11y-wrapper" @keydown.esc="closePanel">

    <!--
      Global colour overlay div.
      For light themes: uses mix-blend-mode:multiply so the tint colours the white
      background while keeping dark text fully readable (black × any colour = black).
      For Dark Calm: the overlay is transparent; the CSS filter on <body> handles it.
      pointer-events:none ensures it never blocks clicks.
    -->
    <div class="a11y-overlay" aria-hidden="true"></div>

    <!-- Toggle button — always visible in the top-right corner -->
    <button
      class="a11y-toggle"
      :class="{ 'a11y-toggle--open': panelOpen }"
      @click="togglePanel"
      :aria-expanded="panelOpen"
      aria-label="Accessibility settings"
      title="Accessibility settings"
    >
      <!-- Accessibility icon (person with arms raised) -->
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
        <circle cx="8" cy="3" r="1.6" fill="currentColor"/>
        <path d="M4.5 6.5C5.5 6 6.5 5.8 8 5.8C9.5 5.8 10.5 6 11.5 6.5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
        <path d="M8 5.8V10.5M8 10.5L5.5 13.5M8 10.5L10.5 13.5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      <span class="a11y-toggle-label">Aa</span>
    </button>

    <!-- Settings panel — drops down when toggle is clicked -->
    <Transition name="panel">
      <div v-if="panelOpen" class="a11y-panel" role="dialog" aria-label="Accessibility settings panel">

        <!-- Panel header -->
        <div class="panel-header">
          <span class="panel-title">Accessibility</span>
          <button class="panel-close" @click="closePanel" aria-label="Close panel">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
              <path d="M2 2l8 8M10 2l-8 8" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
            </svg>
          </button>
        </div>

        <!-- ── Section: Colour Theme ── -->
        <div class="panel-section">
          <div class="section-label">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
              <circle cx="6" cy="6" r="5" stroke="currentColor" stroke-width="1.2"/>
              <path d="M6 1v2M6 9v2M1 6h2M9 6h2" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/>
            </svg>
            Colour Theme
          </div>

          <!--
            Six dyslexia-friendly colour overlays.
            Light themes use mix-blend-mode multiply overlay on the page.
            Dark Calm uses CSS filter invert on the body.
          -->
          <div class="theme-grid">
            <button
              v-for="(cfg, key) in THEMES"
              :key="key"
              class="theme-swatch"
              :class="{ 'theme-swatch--active': settings.theme === key }"
              :style="{ background: cfg.swatch }"
              :title="cfg.label"
              :aria-label="cfg.label + (settings.theme === key ? ' (selected)' : '')"
              @click="settings.theme = key"
            >
              <!-- Check mark on the active theme -->
              <svg
                v-if="settings.theme === key"
                class="swatch-check"
                width="10" height="10" viewBox="0 0 10 10" fill="none"
              >
                <path d="M2 5l2.5 2.5 3.5-4" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </button>
          </div>

          <!-- Active theme label -->
          <p class="theme-active-label">{{ THEMES[settings.theme].label }}</p>
        </div>

        <div class="panel-divider"></div>

        <!-- ── Section: Font Size ── -->
        <div class="panel-section">
          <div class="section-label">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
              <path d="M2 10L5.5 2L9 10M3.5 7.5h5" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            Text Size
            <span class="section-note">Based on 14 pt reference</span>
          </div>

          <div class="option-row">
            <button
              v-for="(cfg, key) in FONT_SIZES"
              :key="key"
              class="option-btn"
              :class="{ 'option-btn--active': settings.fontSize === key }"
              @click="settings.fontSize = key"
            >
              {{ cfg.label }}
              <span class="option-hint">{{ cfg.display }}</span>
            </button>
          </div>
        </div>

        <div class="panel-divider"></div>

        <!-- ── Section: Line Height ── -->
        <div class="panel-section">
          <div class="section-label">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
              <path d="M4 2h6M4 6h6M4 10h6M2 2v8" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/>
            </svg>
            Line Height
            <span class="section-note">+0.26 em per step</span>
          </div>

          <div class="option-row">
            <button
              v-for="(cfg, key) in LINE_HEIGHTS"
              :key="key"
              class="option-btn"
              :class="{ 'option-btn--active': settings.lineHeight === key }"
              @click="settings.lineHeight = key"
            >
              {{ cfg.label }}
              <span class="option-hint">× {{ cfg.value }}</span>
            </button>
          </div>
        </div>

        <div class="panel-divider"></div>

        <!-- Reset button — restores all settings to defaults -->
        <div class="panel-footer">
          <button class="btn-reset" @click="resetSettings">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
              <path d="M10 6A4 4 0 1 1 6 2M10 2v4H6" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            Reset to defaults
          </button>
        </div>

      </div>
    </Transition>

    <!-- Click-outside backdrop to close panel -->
    <div v-if="panelOpen" class="a11y-backdrop" @click="closePanel" aria-hidden="true"></div>
  </div>
</template>


<style scoped>

/* ─────────────────────────────────────────
   Wrapper — anchors the toggle + panel
   Fixed top-right; sits above navbar content.
───────────────────────────────────────── */
.a11y-wrapper {
  position: fixed;
  top: 14px;
  right: 20px;
  z-index: 200;
  font-family: 'Inter', system-ui, sans-serif;  /* always use Inter regardless of user font setting */
}

/* ─────────────────────────────────────────
   Global colour overlay
   mix-blend-mode:multiply tints white backgrounds
   while leaving dark text unaffected.
   The --a11y-overlay CSS variable is set by
   the composable whenever the theme changes.
───────────────────────────────────────── */
.a11y-overlay {
  position: fixed;
  inset: 0;
  background: var(--a11y-overlay, transparent);
  mix-blend-mode: multiply;
  pointer-events: none;
  z-index: 9990;
}

/* ─────────────────────────────────────────
   Toggle button
───────────────────────────────────────── */
.a11y-toggle {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 7px 13px;
  background: rgba(255, 255, 255, 0.92);
  border: 1.5px solid #e5e7eb;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 700;
  color: #374151;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  transition: background 0.2s, border-color 0.2s, box-shadow 0.2s;
  position: relative;
  z-index: 201;
}

.a11y-toggle:hover {
  background: #fff;
  border-color: #2563eb;
  box-shadow: 0 2px 12px rgba(37, 99, 235, 0.15);
  color: #2563eb;
}

/* Slightly highlighted when panel is open */
.a11y-toggle--open {
  background: #eff6ff;
  border-color: #93c5fd;
  color: #2563eb;
}

.a11y-toggle-label { font-size: 12.5px; letter-spacing: 0.02em; }


/* ─────────────────────────────────────────
   Settings panel
───────────────────────────────────────── */
.a11y-panel {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  width: 256px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 16px;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.12), 0 4px 12px rgba(0, 0, 0, 0.06);
  overflow: hidden;
  z-index: 201;
}

/* Panel slide-down transition */
.panel-enter-active { transition: opacity 0.2s ease, transform 0.2s ease; }
.panel-leave-active { transition: opacity 0.15s ease, transform 0.15s ease; }
.panel-enter-from   { opacity: 0; transform: translateY(-8px) scale(0.97); }
.panel-leave-to     { opacity: 0; transform: translateY(-4px) scale(0.98); }


/* Panel header */
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px 12px;
  border-bottom: 1px solid #f3f4f6;
}
.panel-title {
  font-size: 13px;
  font-weight: 700;
  color: #0d1117;
  letter-spacing: -0.01em;
}
.panel-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 6px;
  color: #9ca3af;
  background: none;
  border: none;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.panel-close:hover { background: #f3f4f6; color: #374151; }


/* Section block */
.panel-section { padding: 12px 16px; }

.section-label {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  color: #6b7280;
  margin-bottom: 10px;
}
.section-note {
  font-weight: 400;
  font-size: 10px;
  letter-spacing: 0;
  text-transform: none;
  color: #b0b8cc;
  margin-left: auto;
}

/* Divider between sections */
.panel-divider { height: 1px; background: #f3f4f6; margin: 0; }


/* ── Theme swatches ── */
.theme-grid {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.theme-swatch {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 2px solid transparent;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.15s, box-shadow 0.15s, border-color 0.15s;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.12);
  position: relative;
  overflow: hidden;
}
.theme-swatch:hover {
  transform: scale(1.12);
  box-shadow: 0 3px 10px rgba(0, 0, 0, 0.18);
}
.theme-swatch--active {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.22);
}

/* Check mark inside active swatch — ensure visibility on all backgrounds */
.swatch-check {
  filter: drop-shadow(0 0 1px rgba(0,0,0,0.4));
}

/* Active theme name below swatches */
.theme-active-label {
  font-size: 11.5px;
  color: #6b7280;
  font-weight: 500;
  margin-top: 8px;
  text-align: center;
}


/* ── Font size / Line height option buttons ── */
.option-row {
  display: flex;
  gap: 6px;
}

.option-btn {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 7px 4px;
  font-size: 12px;
  font-weight: 600;
  color: #4b5563;
  background: #f3f4f6;
  border: 1.5px solid transparent;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s, color 0.15s;
}
.option-btn:hover { background: #e8eaf0; color: #0d1117; }

.option-btn--active {
  background: #eff6ff;
  border-color: #93c5fd;
  color: #2563eb;
}

/* Small hint text (e.g. "16px" or "×1.5") */
.option-hint {
  font-size: 10px;
  font-weight: 400;
  color: #9ca3af;
  letter-spacing: 0;
}
.option-btn--active .option-hint { color: #60a5fa; }


/* Panel footer with reset button */
.panel-footer {
  padding: 10px 16px 14px;
  display: flex;
  justify-content: center;
}

.btn-reset {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: #9ca3af;
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  transition: color 0.15s, background 0.15s;
}
.btn-reset:hover { color: #ef4444; background: #fef2f2; }


/* ─────────────────────────────────────────
   Invisible backdrop to close panel on
   click-outside — below the panel (z 200)
   but above the page content (z 1).
───────────────────────────────────────── */
.a11y-backdrop {
  position: fixed;
  inset: 0;
  z-index: 199;
  cursor: default;
}


/* ─────────────────────────────────────────
   Dark Calm counter-invert
   When the body has filter:invert applied,
   the toolbar is also inverted. This rule
   re-inverts it so it always looks normal.
───────────────────────────────────────── */
:root[data-theme="dark"] .a11y-wrapper {
  filter: invert(0.88) hue-rotate(190deg);
}


/* ─────────────────────────────────────────
   Responsive — hide label on very small screens
───────────────────────────────────────── */
@media (max-width: 480px) {
  .a11y-wrapper { top: 10px; right: 12px; }
  .a11y-toggle  { padding: 7px 10px; }
  .a11y-toggle-label { display: none; }
}
</style>
