<script setup>
/**
 * FocusReaderPage.vue
 * -------------------
 * Interactive reading-training game for users with dyslexia.
 * Ported from the standalone Focus Reader prototype into Vue 3
 * and restyled to match the Clearead design system.
 *
 * Game mechanics:
 *   - Moving circular "chips" bounce around a canvas arena.
 *   - Each round the user receives a cue (visual label or spoken audio).
 *   - The user taps the chip whose label matches the cue.
 *   - Distractors are deliberately chosen to be visually/phonetically
 *     similar to the target (e.g. b/d/p/q, sh/ch/th) — the same
 *     confusions that are common in dyslexic readers.
 *   - Difficulty adapts automatically: level rises when accuracy ≥ 82 %
 *     and average reaction time < 2.5 s; falls when accuracy ≤ 45 %.
 *   - Sessions are saved to localStorage and can be exported as JSON.
 */

import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'

// ── Navbar scroll shadow ──────────────────────────────────────────────────────
const scrolled = ref(false)
const menuOpen = ref(false)
function onScroll() { scrolled.value = window.scrollY > 10 }

// ── Word / letter pools ───────────────────────────────────────────────────────
/**
 * Three pools cover different aspects of reading decoding:
 *   letters — single visually confusable characters (b/d/p/q problem)
 *   chunks  — common digraphs and vowel teams (phoneme awareness)
 *   words   — real short words mixed with phonetically plausible nonsense
 *             words (pseudoword reading = the gold standard for decoding skill)
 */
const POOLS = {
  letters: ['b', 'd', 'p', 'q', 'm', 'n', 'u', 'v', 'w', 'a', 'e', 'g'],
  chunks:  ['sh', 'ch', 'th', 'ph', 'wh', 'ck', 'ee', 'ea', 'oo', 'ai', 'oa', 'igh'],
  words:   ['ship', 'chip', 'thin', 'then', 'shop', 'chop', 'rush', 'much',
            'bead', 'deed', 'road', 'toad', 'shup', 'chib', 'thop', 'prail'],
}

/**
 * Confusable distractors for each target item.
 * Selecting semantically/visually close distractors (rather than random ones)
 * forces the learner to discriminate carefully — a key skill in phonics training.
 */
const CONFUSABLES = {
  b: ['d', 'p', 'q'],    d: ['b', 'p', 'q'],    p: ['q', 'b', 'd'],   q: ['p', 'd', 'b'],
  m: ['n', 'w'],         n: ['m', 'u'],          u: ['n', 'v'],        v: ['u', 'w'],
  w: ['m', 'v'],
  sh: ['ch', 'th', 'ph'], ch: ['sh', 'ck', 'th'], th: ['sh', 'ch', 'ph'],
  ph: ['th', 'sh', 'wh'], wh: ['ph', 'sh', 'ch'],
  ee: ['ea', 'oo'],  ea: ['ee', 'ai'],  oo: ['oa', 'ee'],
  ai: ['ea', 'oa'],  oa: ['oo', 'ai'],  igh: ['ai', 'ee'],
  ship: ['chip', 'shop', 'shup'], chip: ['ship', 'chop', 'chib'],
  thin: ['then', 'thop', 'ship'], then: ['thin', 'chop', 'thop'],
  shop: ['ship', 'chop', 'shup'], chop: ['shop', 'chip', 'chib'],
  rush: ['much', 'ship', 'shup'], much: ['rush', 'chop', 'chip'],
  bead: ['deed', 'road', 'toad'], deed: ['bead', 'road', 'thin'],
  road: ['toad', 'bead', 'oa'],   toad: ['road', 'deed', 'oa'],
  shup: ['ship', 'shop', 'chib'], chib: ['chip', 'chop', 'shup'],
  thop: ['thin', 'then', 'shop'], prail: ['trail', 'plain', 'prail'],
}

const STORAGE_KEY = 'focus-reader-sessions'

// ── Chip colour palette ───────────────────────────────────────────────────────
// Target chips are always teal so the learner can distinguish colours if needed,
// but the task still requires reading the label to pick the correct one.
const CHIP_COLORS = {
  target: ['#0f766e', '#ffffff', '#07413e'],
  blue:   ['#2f6fbb', '#ffffff', '#18395f'],
  yellow: ['#f9d56e', '#1f2937', '#8b6215'],
  rose:   ['#e76f73', '#ffffff', '#82373a'],
  plain:  ['#ffffff', '#20242a', '#aab6c1'],
}

// ── Settings (reactive — drives both UI controls and game behaviour) ──────────
const settings = reactive({
  sound: true,   // whether to use Web Speech API for audio-cue rounds
  calm:  false,  // slower chip speed and longer round time (reduces anxiety)
  mode:  'mixed',
})

// ── UI state (reactive — everything the template reads) ──────────────────────
const ui = reactive({
  cueLabel:     'Ready',
  message:      'Press Start, then tap the chip that matches the cue.',
  timePct:      0,       // 0-100, drives the timer progress bar width
  score:        0,
  accuracy:     '--',
  reaction:     '--',
  level:        1,
  showOverlay:  true,
  overlayTitle: 'Catch the Target Chip',
  overlayBody:  'Each round gives you a cue — visual text or a spoken word. Tap the chip that matches it. Avoid look-alike distractors.',
  sessions:     [],      // recent session history for the sidebar
  cueIsAudio:   false,   // controls whether the ♪ Replay button is shown
})

// ── Internal game state (plain object — not reactive, canvas reads directly) ──
// Using a plain object avoids Vue tracking overhead inside the animation loop.
const G = {
  running: false, paused: false, roundActive: false,
  level: 1, score: 0, hits: 0, misses: 0, wrong: 0, streak: 0,
  roundIndex: 0, roundStartedAt: 0, roundDuration: 6500,
  target: '', cueMode: 'visual',
  chips: [], recent: [], reactionTimes: [],
  animId: 0, lastFrame: 0,
}

// ── Reactive flags that drive button visibility ───────────────────────────────
const isRunning = ref(false)
const isPaused  = ref(false)

// ── Canvas ref ────────────────────────────────────────────────────────────────
const canvasEl = ref(null)
let ctx = null  // 2D context, assigned in onMounted

// ── Computed ──────────────────────────────────────────────────────────────────
// Timer bar colour shifts from blue → amber → red as time runs out
const timerColor = computed(() => {
  if (ui.timePct > 50) return '#2563eb'
  if (ui.timePct > 25) return '#f59e0b'
  return '#ef4444'
})

// ── Utility helpers ───────────────────────────────────────────────────────────
function pick(arr)   { return arr[Math.floor(Math.random() * arr.length)] }
function shuffle(arr) {
  const a = [...arr]
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]]
  }
  return a
}
function canvasW() { return canvasEl.value?.getBoundingClientRect().width  || 600 }
function canvasH() { return canvasEl.value?.getBoundingClientRect().height || 420 }

function formatDate(iso) {
  return new Intl.DateTimeFormat('en-AU', {
    month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit',
  }).format(new Date(iso))
}

// ── Pool selection ────────────────────────────────────────────────────────────
function getPool() {
  if (settings.mode === 'mixed') return pick([POOLS.letters, POOLS.chunks, POOLS.words])
  return POOLS[settings.mode] || POOLS.letters
}

/**
 * Builds the label array for a round.
 * Guarantees the target appears once, fills remaining slots first with
 * confusable items, then random pool items.
 */
function buildLabels(target, count) {
  const pool  = [...new Set([...POOLS.letters, ...POOLS.chunks, ...POOLS.words])]
  const close = CONFUSABLES[target] || []
  const labels = [target, ...shuffle(close).slice(0, Math.min(3, close.length))]
  while (labels.length < count) {
    const c = pick(pool)
    if (!labels.includes(c)) labels.push(c)
  }
  return shuffle(labels)
}

// ── Chip factory ──────────────────────────────────────────────────────────────
function makeChip(label, isTarget, index, total) {
  const radius = Math.max(30, 42 - G.level * 2)
  const margin = radius + 12
  const angle  = (Math.PI * 2 * index / total) + Math.random() * 0.8
  const base   = settings.calm ? 34 : 48
  const speed  = base + G.level * (settings.calm ? 7 : 13) + Math.random() * 18
  return {
    label, isTarget, radius,
    x:  margin + Math.random() * Math.max(20, canvasW() - margin * 2),
    y:  margin + Math.random() * Math.max(20, canvasH() - margin * 2),
    vx: Math.cos(angle) * speed,
    vy: Math.sin(angle) * speed,
    spin:   (Math.random() - 0.5) * 0.9,
    wobble: Math.random() * Math.PI * 2,
    hue: isTarget ? 'target' : pick(['blue', 'yellow', 'rose', 'plain']),
  }
}

// ── Canvas drawing ────────────────────────────────────────────────────────────
function drawBackground() {
  const w = canvasW(), h = canvasH()
  ctx.clearRect(0, 0, w, h)
  ctx.fillStyle = '#edf6f4'
  ctx.fillRect(0, 0, w, h)
  // Subtle grid — helps with visual tracking without being distracting
  ctx.strokeStyle = 'rgba(32,36,42,0.07)'
  ctx.lineWidth = 1
  for (let x = 0; x < w; x += 56) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke() }
  for (let y = 0; y < h; y += 56) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke() }
}

function drawChip(chip) {
  const [fill, text, stroke] = CHIP_COLORS[chip.hue]
  ctx.save()
  ctx.translate(chip.x, chip.y)
  ctx.rotate(Math.sin(chip.wobble) * chip.spin * 0.14)
  ctx.beginPath()
  ctx.arc(0, 0, chip.radius, 0, Math.PI * 2)
  ctx.fillStyle = fill; ctx.fill()
  ctx.lineWidth = chip.isTarget ? 4 : 2; ctx.strokeStyle = stroke; ctx.stroke()
  ctx.fillStyle = text
  const fontSize = Math.max(19, chip.radius * (chip.label.length > 3 ? 0.45 : 0.58))
  ctx.font = `900 ${fontSize}px "Segoe UI", Arial`
  ctx.textAlign = 'center'; ctx.textBaseline = 'middle'
  ctx.fillText(chip.label, 0, 1)
  ctx.restore()
}

function drawEmpty() {
  drawBackground()
  ctx.save()
  ctx.fillStyle = '#687581'
  ctx.font = '800 22px "Segoe UI", Arial'
  ctx.textAlign = 'center'
  ctx.fillText('Ready', canvasW() / 2, canvasH() / 2)
  ctx.restore()
}

// ── Statistics helper ─────────────────────────────────────────────────────────
function syncUiStats() {
  const attempts = G.hits + G.misses + G.wrong
  ui.score    = G.score
  ui.accuracy = attempts ? `${Math.round(G.hits / attempts * 100)}%` : '--'
  const lastHit = [...G.recent].reverse().find(r => r.ok)
  ui.reaction = lastHit ? `${Math.round(lastHit.rt)} ms` : '--'
  ui.level    = G.level
}

// ── Speech synthesis ──────────────────────────────────────────────────────────
function speakTarget() {
  if (!settings.sound || !('speechSynthesis' in window)) {
    // Fallback: show text when speech is unavailable
    ui.cueLabel  = G.target
    ui.cueIsAudio = false
    return
  }
  window.speechSynthesis.cancel()
  const utt = new SpeechSynthesisUtterance(G.target)
  utt.lang = 'en-US'; utt.rate = 0.82; utt.pitch = 1.05
  window.speechSynthesis.speak(utt)
}

// ── Difficulty adaptation ─────────────────────────────────────────────────────
/**
 * Adjusts level after each resolved round.
 * Uses the last 4–6 rounds to smooth out lucky/unlucky streaks.
 * Thresholds are set conservatively so the learner experiences
 * success before the difficulty rises.
 */
function adaptDifficulty() {
  if (G.recent.length < 4) return
  const successRate = G.recent.filter(r => r.ok).length / G.recent.length
  const goodTimes   = G.recent.filter(r => r.ok).map(r => r.rt)
  const avgRt = goodTimes.length
    ? goodTimes.reduce((s, v) => s + v, 0) / goodTimes.length
    : Infinity

  if (successRate >= 0.82 && avgRt < 2500 && G.level < 6) {
    G.level++; G.recent = []; ui.message += ' — Level up!'
  } else if (successRate <= 0.45 && G.level > 1) {
    G.level--; G.recent = []; ui.message += ' — Slowing down.'
  }
}

// ── Round resolution ──────────────────────────────────────────────────────────
function resolveChoice(chip) {
  if (!G.roundActive) return
  const rt = performance.now() - G.roundStartedAt
  G.roundActive = false

  if (chip.isTarget) {
    G.hits++; G.streak++
    const speedBonus = Math.max(0, Math.round((G.roundDuration - rt) / 120))
    G.score += 80 + G.level * 12 + speedBonus
    G.recent.push({ ok: true, rt })
    G.reactionTimes.push(rt)
    ui.message = `Hit! "${chip.label}" — ${Math.round(rt)} ms.`
  } else {
    G.wrong++; G.streak = 0
    G.score = Math.max(0, G.score - 30)
    G.recent.push({ ok: false, rt })
    ui.message = `That was a distractor: "${chip.label}". The target was "${G.target}".`
  }

  G.recent = G.recent.slice(-6)
  adaptDifficulty()
  syncUiStats()
  setTimeout(nextRound, chip.isTarget ? 650 : 1100)
}

function missRound() {
  if (!G.roundActive) return
  G.roundActive = false
  G.misses++; G.streak = 0
  G.recent.push({ ok: false, rt: G.roundDuration })
  G.recent = G.recent.slice(-6)
  ui.message = `Time's up. The target was "${G.target}".`
  adaptDifficulty()
  syncUiStats()
  setTimeout(nextRound, 900)
}

// ── Round start ───────────────────────────────────────────────────────────────
function nextRound() {
  if (!G.running || G.paused) return
  G.roundIndex++
  if (G.roundIndex > 16) { finishSession(true); return }

  const pool = getPool()
  G.target   = pick(pool)
  // Every 3rd round uses audio cue (if sound is enabled) to train auditory-visual mapping
  G.cueMode  = settings.sound && G.roundIndex % 3 === 0 ? 'audio' : 'visual'
  G.roundDuration = Math.max(3800, 7200 - G.level * 520 + (settings.calm ? 1200 : 0))
  G.roundStartedAt = performance.now()
  G.roundActive    = true

  const count  = Math.min(11, 4 + G.level + Math.floor(G.roundIndex / 5))
  const labels = buildLabels(G.target, count + 1)
  G.chips = labels.map((lbl, i) => makeChip(lbl, lbl === G.target, i, labels.length))

  if (G.cueMode === 'audio') {
    ui.cueLabel  = '♪ Listen'
    ui.cueIsAudio = true
    ui.message   = 'Listen to the audio cue, then tap the matching chip.'
    speakTarget()
  } else {
    ui.cueLabel  = G.target
    ui.cueIsAudio = false
    ui.message   = 'Find the chip that matches the visual cue above.'
  }
  syncUiStats()
}

// ── Animation loop ────────────────────────────────────────────────────────────
function loop(now) {
  if (!G.running || G.paused) return
  const dt = Math.min(0.04, (now - G.lastFrame) / 1000 || 0)
  G.lastFrame = now

  // Update chip positions and handle wall bouncing
  const w = canvasW(), h = canvasH()
  for (const chip of G.chips) {
    chip.x += chip.vx * dt; chip.y += chip.vy * dt; chip.wobble += dt * 3
    if (chip.x < chip.radius || chip.x > w - chip.radius) {
      chip.vx *= -1; chip.x = Math.min(Math.max(chip.x, chip.radius), w - chip.radius)
    }
    if (chip.y < chip.radius || chip.y > h - chip.radius) {
      chip.vy *= -1; chip.y = Math.min(Math.max(chip.y, chip.radius), h - chip.radius)
    }
  }

  // Update countdown timer bar
  if (G.roundActive) {
    const elapsed = now - G.roundStartedAt
    ui.timePct = Math.max(0, (1 - elapsed / G.roundDuration) * 100)
    if (elapsed >= G.roundDuration) missRound()
  }

  drawBackground()
  G.chips.forEach(drawChip)
  G.animId = requestAnimationFrame(loop)
}

// ── Session persistence ───────────────────────────────────────────────────────
function getSessions() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY)) || [] } catch { return [] }
}

function saveSession(session) {
  const all = getSessions()
  all.unshift(session)
  localStorage.setItem(STORAGE_KEY, JSON.stringify(all.slice(0, 30)))
}

function loadHistory() {
  ui.sessions = getSessions().slice(0, 5)
}

function exportHistory() {
  const blob = new Blob([JSON.stringify(getSessions(), null, 2)], { type: 'application/json' })
  const url  = URL.createObjectURL(blob)
  const a    = document.createElement('a')
  a.href = url
  a.download = `focus-reader-sessions-${new Date().toISOString().slice(0, 10)}.json`
  document.body.append(a); a.click(); a.remove()
  URL.revokeObjectURL(url)
}

// ── Session end ───────────────────────────────────────────────────────────────
function finishSession(completed) {
  cancelAnimationFrame(G.animId)
  if (!G.running) return

  const attempts  = G.hits + G.misses + G.wrong
  const accuracy  = attempts ? Math.round(G.hits / attempts * 100) : 0
  const avgRt     = G.reactionTimes.length
    ? Math.round(G.reactionTimes.reduce((s, v) => s + v, 0) / G.reactionTimes.length)
    : null

  if (completed || attempts > 0) {
    saveSession({ date: new Date().toISOString(), score: G.score, accuracy, level: G.level,
                  avgRt, hits: G.hits, wrong: G.wrong, misses: G.misses, completed })
  }

  G.running = false; G.paused = false; G.roundActive = false; G.chips = []
  isRunning.value = false; isPaused.value = false
  ui.cueLabel     = completed ? 'Complete!' : 'Reset'
  ui.cueIsAudio   = false
  ui.timePct      = 0
  ui.showOverlay  = true
  ui.overlayTitle = completed ? 'Session Complete' : 'Session Reset'
  ui.overlayBody  = completed
    ? `${accuracy}% accuracy · Peak level ${G.level}. Short, regular sessions build reading fluency over time.`
    : 'Session saved. Click Start to begin again.'
  ui.message = completed
    ? `Done! ${accuracy}% accuracy, peak level ${G.level}.`
    : 'Session saved. Click Start to train again.'
  syncUiStats()
  drawEmpty()
  loadHistory()
}

// ── Game controls ─────────────────────────────────────────────────────────────
function startGame() {
  if (G.running && G.paused) { resumeGame(); return }

  // Full reset for a fresh session
  Object.assign(G, {
    running: true, paused: false, level: 1, score: 0,
    hits: 0, misses: 0, wrong: 0, streak: 0,
    roundIndex: 0, recent: [], reactionTimes: [],
  })
  isRunning.value = true; isPaused.value = false
  ui.showOverlay  = false
  syncUiStats()
  nextRound()
  G.lastFrame = performance.now()
  loop(G.lastFrame)
}

function pauseGame() {
  if (!G.running || G.paused) return
  G.paused = true; isPaused.value = true
  cancelAnimationFrame(G.animId)
  ui.message = 'Paused. Press Resume to continue. (Shortcut: P)'
}

function resumeGame() {
  G.paused = false; isPaused.value = false
  ui.showOverlay = false
  G.roundStartedAt = performance.now()
  G.lastFrame      = performance.now()
  loop(G.lastFrame)
}

function resetGame() {
  finishSession(false)
}

// ── Canvas pointer handling ───────────────────────────────────────────────────
function handleCanvasPointer(event) {
  if (!G.running || G.paused || !G.roundActive) return
  const rect = canvasEl.value.getBoundingClientRect()
  const x = event.clientX - rect.left
  const y = event.clientY - rect.top
  // Iterate in reverse so topmost-rendered chip wins on overlap
  for (let i = G.chips.length - 1; i >= 0; i--) {
    const chip = G.chips[i]
    if (Math.hypot(chip.x - x, chip.y - y) <= chip.radius + 6) {
      resolveChoice(chip); return
    }
  }
}

// ── Canvas resize ─────────────────────────────────────────────────────────────
function resizeCanvas() {
  if (!canvasEl.value) return
  const rect = canvasEl.value.getBoundingClientRect()
  const dpr  = window.devicePixelRatio || 1
  canvasEl.value.width  = Math.max(320, Math.floor(rect.width  * dpr))
  canvasEl.value.height = Math.max(320, Math.floor(rect.height * dpr))
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
}

function onResize() {
  resizeCanvas()
  drawBackground()
  G.chips.forEach(drawChip)
}

// ── Keyboard shortcuts ────────────────────────────────────────────────────────
function handleKey(e) {
  const key = e.key.toLowerCase()
  if (key === 'p' && G.running) { e.preventDefault(); G.paused ? resumeGame() : pauseGame() }
  if (key === 'r' && G.cueMode === 'audio') { e.preventDefault(); speakTarget() }
}

// ── Lifecycle ─────────────────────────────────────────────────────────────────
onMounted(() => {
  ctx = canvasEl.value.getContext('2d')
  resizeCanvas()
  drawEmpty()
  loadHistory()
  window.addEventListener('scroll', onScroll)
  window.addEventListener('resize', onResize)
  document.addEventListener('keydown', handleKey)
})

onUnmounted(() => {
  cancelAnimationFrame(G.animId)
  window.speechSynthesis?.cancel()
  window.removeEventListener('scroll', onScroll)
  window.removeEventListener('resize', onResize)
  document.removeEventListener('keydown', handleKey)
})
</script>


<template>
  <div class="page">

    <!-- ── Navbar ── -->
    <nav :class="['navbar', { 'navbar--scrolled': scrolled }]">
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
          <li><RouterLink to="/"         class="nav-link">Home</RouterLink></li>
          <li><RouterLink to="/reading"  class="nav-link">Reading Support</RouterLink></li>
          <li><RouterLink to="/dyslexia" class="nav-link">Dyslexia</RouterLink></li>
          <li><RouterLink to="/training" class="nav-link nav-link--active">Training</RouterLink></li>
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

    <!-- Mobile nav drawer -->
    <div v-if="menuOpen" class="mobile-nav">
      <ul class="mobile-nav-links">
        <li><RouterLink to="/"         class="mobile-nav-link" @click="menuOpen = false">Home</RouterLink></li>
        <li><RouterLink to="/reading"  class="mobile-nav-link" @click="menuOpen = false">Reading Support</RouterLink></li>
        <li><RouterLink to="/dyslexia" class="mobile-nav-link" @click="menuOpen = false">Dyslexia</RouterLink></li>
        <li><RouterLink to="/training" class="mobile-nav-link" @click="menuOpen = false">Training</RouterLink></li>
      </ul>
    </div>

    <!-- ── Page header ── -->
    <section class="page-hero">
      <div class="container">
        <span class="eyebrow">Reading Training</span>
        <h1 class="page-title">Focus Reader</h1>
        <p class="page-sub">
          Build visual discrimination and phoneme awareness through short, targeted practice sessions.
          Designed for learners who struggle with letter reversals and sound–spelling connections.
        </p>
        <!-- Keyboard hint -->
        <div class="kbd-hints">
          <span class="kbd-hint"><kbd>P</kbd> Pause / Resume</span>
          <span class="kbd-hint"><kbd>R</kbd> Replay audio cue</span>
        </div>
      </div>
    </section>

    <!-- ── Game dashboard ── -->
    <section class="game-section">
      <div class="game-layout container">

        <!-- Left panel: cue card + stats + controls -->
        <aside class="game-panel">

          <!-- Current target cue -->
          <div class="cue-card">
            <span class="panel-eyebrow">Current Target</span>
            <div class="cue-display" :class="{ 'cue-display--audio': ui.cueIsAudio }">
              {{ ui.cueLabel }}
            </div>
            <!-- Replay button only shown for audio-cue rounds -->
            <button
              v-if="ui.cueIsAudio"
              class="btn-replay"
              @click="speakTarget"
              :disabled="!isRunning || isPaused"
              aria-label="Replay audio cue"
            >
              ♪ Replay
            </button>
          </div>

          <!-- Status message (hit / miss / pause feedback) -->
          <div class="message-box" role="status" aria-live="polite">
            {{ ui.message }}
          </div>

          <!-- Countdown timer bar -->
          <div class="timer-wrap">
            <span class="timer-label">Round time</span>
            <div class="timer-track" aria-label="Remaining time">
              <div
                class="timer-fill"
                :style="{ width: ui.timePct + '%', background: timerColor }"
              ></div>
            </div>
          </div>

          <!-- Stats grid -->
          <dl class="stats-grid">
            <div class="stat-cell">
              <dt>Score</dt><dd>{{ ui.score }}</dd>
            </div>
            <div class="stat-cell">
              <dt>Accuracy</dt><dd>{{ ui.accuracy }}</dd>
            </div>
            <div class="stat-cell">
              <dt>Reaction</dt><dd>{{ ui.reaction }}</dd>
            </div>
            <div class="stat-cell">
              <dt>Level</dt><dd>{{ ui.level }} / 6</dd>
            </div>
          </dl>

          <!-- Game controls -->
          <div class="controls">
            <button
              v-if="!isRunning || isPaused"
              class="btn-primary"
              @click="startGame"
            >
              {{ isPaused ? 'Resume' : (isRunning ? 'Restart' : 'Start') }}
            </button>
            <button
              v-if="isRunning && !isPaused"
              class="btn-secondary"
              @click="pauseGame"
            >
              Pause
            </button>
            <button class="btn-ghost-sm" @click="resetGame">Reset</button>
          </div>

        </aside>

        <!-- Canvas arena -->
        <div class="arena-wrap">
          <canvas
            ref="canvasEl"
            class="game-canvas"
            @pointerdown="handleCanvasPointer"
            aria-label="Game arena — tap the chip that matches the cue"
          ></canvas>
          <!-- Overlay shown before game starts and after session ends -->
          <Transition name="overlay">
            <div v-if="ui.showOverlay" class="arena-overlay">
              <div class="overlay-icon" aria-hidden="true">
                <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
                  <circle cx="20" cy="20" r="18" fill="#eef2ff" stroke="#2563eb" stroke-width="2"/>
                  <path d="M14 20l4.5 4.5 7.5-8" stroke="#2563eb" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </div>
              <h2>{{ ui.overlayTitle }}</h2>
              <p>{{ ui.overlayBody }}</p>
            </div>
          </Transition>
        </div>

        <!-- Right panel: settings + history -->
        <aside class="game-panel">

          <!-- Training mode selector -->
          <div class="settings-block">
            <span class="panel-eyebrow">Training Mode</span>
            <select v-model="settings.mode" class="mode-select" :disabled="isRunning && !isPaused">
              <option value="mixed">Mixed — Letters, Phonemes &amp; Words</option>
              <option value="letters">Confusable Letters (b/d/p/q)</option>
              <option value="chunks">Phoneme Chunks (sh/ch/th)</option>
              <option value="words">Short &amp; Nonsense Words</option>
            </select>
          </div>

          <!-- Toggle options -->
          <div class="toggles-block">
            <label class="toggle-row">
              <span class="toggle-wrap">
                <input type="checkbox" class="sr-only" v-model="settings.sound" />
                <span class="toggle-track" :class="{ 'toggle-track--on': settings.sound }">
                  <span class="toggle-thumb"></span>
                </span>
              </span>
              <span class="toggle-label">Audio Cues</span>
            </label>
            <label class="toggle-row">
              <span class="toggle-wrap">
                <input type="checkbox" class="sr-only" v-model="settings.calm" />
                <span class="toggle-track" :class="{ 'toggle-track--on': settings.calm }">
                  <span class="toggle-thumb"></span>
                </span>
              </span>
              <span class="toggle-label">Calm Speed</span>
            </label>
          </div>

          <!-- Session history -->
          <div class="history-block">
            <span class="panel-eyebrow">Recent Sessions</span>
            <ol class="history-list">
              <li v-if="!ui.sessions.length" class="history-empty">No sessions yet</li>
              <li v-for="(s, i) in ui.sessions" :key="i" class="history-item">
                <span class="history-time">{{ formatDate(s.date) }}</span>
                <span class="history-stats">{{ s.accuracy }}% · {{ s.score }} pts · Lv{{ s.level }}</span>
              </li>
            </ol>
            <button class="btn-export" @click="exportHistory">Export JSON</button>
          </div>

          <!-- Clinical disclaimer -->
          <p class="disclaimer">
            This is a practice aid, not a clinical tool. Use it alongside professional reading intervention and specialist advice.
          </p>

        </aside>
      </div>
    </section>

    <!-- ── Footer ── -->
    <footer class="footer">
      <div class="container footer-inner">
        <div class="footer-left">
          <span class="footer-logo">Clearead</span>
          <p class="footer-tagline">Built for minds that think differently.</p>
        </div>
        <nav class="footer-links">
          <RouterLink to="/reading"  class="footer-link">Reading Support</RouterLink>
          <RouterLink to="/dyslexia" class="footer-link">Dyslexia</RouterLink>
          <RouterLink to="/training" class="footer-link">Training</RouterLink>
        </nav>
        <p class="footer-copy">© 2026 Clearead. All rights reserved.</p>
      </div>
    </footer>

  </div>
</template>


<style scoped>
/* ── Page shell ── */
.page {
  min-height: 100vh;
  background: var(--color-bg, #f9f7f4);
  color: #0d1117;
}

/* ── Navbar (mirrors HomePage) ── */
.navbar {
  position: fixed; top: 0; left: 0; right: 0;
  z-index: 100;
  transition: background 0.3s, box-shadow 0.3s;
}
.navbar--scrolled {
  background: rgba(255,255,255,0.88);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
  box-shadow: 0 1px 0 rgba(0,0,0,0.06);
}
.nav-inner {
  max-width: 1160px; margin: 0 auto;
  padding: 0 36px; height: 64px;
  display: flex; align-items: center;
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
.nav-link:hover { color: #0d1117; background: rgba(0,0,0,0.04); }
.nav-link--active { color: #0d1117; }
.nav-link--active::after {
  content: ''; position: absolute;
  bottom: -2px; left: 50%; transform: translateX(-50%);
  width: 4px; height: 4px;
  border-radius: 50%; background: #2563eb;
}
.nav-hamburger {
  display: none; background: none; border: none; cursor: pointer;
  color: #0d1117; padding: 4px; margin-left: 12px;
  align-items: center; justify-content: center;
}
.mobile-nav {
  display: none;
}

/* ── Page hero header ── */
.page-hero {
  padding: 120px 0 56px;
  background: linear-gradient(160deg, #eef2ff 0%, #f9f7f4 60%);
  border-bottom: 1px solid #e5e7eb;
}
.eyebrow {
  font-size: 12px; font-weight: 700;
  letter-spacing: 0.1em; text-transform: uppercase;
  color: #2563eb; display: block; margin-bottom: 14px;
}
.page-title {
  font-size: clamp(32px, 5vw, 52px);
  font-weight: 800; letter-spacing: -0.04em;
  margin: 0 0 16px;
}
.page-sub {
  font-size: 16px; color: #4b5563;
  line-height: 1.7; max-width: 600px; margin: 0 0 24px;
}
.kbd-hints {
  display: flex; gap: 20px; flex-wrap: wrap;
}
.kbd-hint {
  font-size: 13px; color: #6b7280;
  display: flex; align-items: center; gap: 7px;
}
kbd {
  display: inline-block;
  padding: 2px 7px; font-size: 11px; font-weight: 700;
  background: #fff; border: 1px solid #d1d5db;
  border-radius: 5px; box-shadow: 0 1px 2px rgba(0,0,0,0.1);
  font-family: inherit;
}

/* ── Game section ── */
.game-section {
  padding: 40px 0 80px;
}
.game-layout {
  display: grid;
  grid-template-columns: 240px 1fr 240px;
  gap: 20px;
  align-items: start;
}

/* ── Side panels ── */
.game-panel {
  display: flex; flex-direction: column; gap: 16px;
}

/* Cue card */
.cue-card {
  background: #fff; border: 1px solid #e5e7eb;
  border-radius: 16px; padding: 20px;
  text-align: center;
  box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}
.panel-eyebrow {
  display: block;
  font-size: 10px; font-weight: 700; letter-spacing: 0.1em;
  text-transform: uppercase; color: #9ca3af; margin-bottom: 10px;
}
.cue-display {
  font-size: 36px; font-weight: 900;
  letter-spacing: -0.02em; color: #0d1117;
  min-height: 52px; display: flex;
  align-items: center; justify-content: center;
  line-height: 1;
}
.cue-display--audio {
  font-size: 28px; color: #2563eb;
}
.btn-replay {
  margin-top: 12px;
  display: inline-flex; align-items: center; gap: 5px;
  padding: 6px 14px; font-size: 13px; font-weight: 600;
  color: #2563eb; background: #eef2ff;
  border: 1px solid #bfdbfe; border-radius: 999px; cursor: pointer;
  transition: background 0.15s;
}
.btn-replay:hover:not(:disabled) { background: #dbeafe; }
.btn-replay:disabled { opacity: 0.45; cursor: not-allowed; }

/* Message box */
.message-box {
  background: #f8fafc; border: 1px solid #e5e7eb;
  border-radius: 12px; padding: 14px 16px;
  font-size: 13px; color: #4b5563; line-height: 1.6;
  min-height: 56px;
}

/* Timer bar */
.timer-wrap {
  background: #fff; border: 1px solid #e5e7eb;
  border-radius: 12px; padding: 14px 16px;
}
.timer-label {
  display: block; font-size: 11px; font-weight: 600;
  color: #9ca3af; text-transform: uppercase;
  letter-spacing: 0.06em; margin-bottom: 8px;
}
.timer-track {
  height: 8px; background: #f3f4f6;
  border-radius: 999px; overflow: hidden;
}
.timer-fill {
  height: 100%; border-radius: 999px;
  transition: width 0.1s linear, background 0.5s ease;
}

/* Stats */
.stats-grid {
  display: grid; grid-template-columns: 1fr 1fr;
  gap: 10px; margin: 0;
  background: #fff; border: 1px solid #e5e7eb;
  border-radius: 16px; padding: 16px;
}
.stat-cell { display: flex; flex-direction: column; gap: 2px; }
.stat-cell dt {
  font-size: 10px; font-weight: 700; letter-spacing: 0.08em;
  text-transform: uppercase; color: #9ca3af;
}
.stat-cell dd {
  font-size: 20px; font-weight: 800;
  letter-spacing: -0.02em; color: #0d1117; margin: 0;
}

/* Controls */
.controls {
  display: flex; flex-direction: column; gap: 8px;
}
.btn-primary {
  width: 100%; padding: 12px;
  background: #2563eb; color: #fff;
  font-size: 15px; font-weight: 700;
  border-radius: 12px; border: none; cursor: pointer;
  box-shadow: 0 4px 14px rgba(37,99,235,0.28);
  transition: background 0.2s, transform 0.15s;
}
.btn-primary:hover { background: #1d4ed8; transform: translateY(-1px); }
.btn-secondary {
  width: 100%; padding: 11px;
  background: #f3f4f6; color: #374151;
  font-size: 14px; font-weight: 600;
  border-radius: 12px; border: 1px solid #e5e7eb; cursor: pointer;
  transition: background 0.15s;
}
.btn-secondary:hover { background: #e8eaf0; }
.btn-ghost-sm {
  width: 100%; padding: 9px;
  background: none; color: #9ca3af;
  font-size: 13px; font-weight: 500;
  border-radius: 10px; border: 1px solid #e5e7eb; cursor: pointer;
  transition: color 0.15s, background 0.15s;
}
.btn-ghost-sm:hover { color: #ef4444; background: #fef2f2; border-color: #fecaca; }

/* ── Canvas arena ── */
.arena-wrap {
  position: relative;
  border-radius: 20px; overflow: hidden;
  border: 1px solid #e5e7eb;
  box-shadow: 0 4px 20px rgba(0,0,0,0.06);
  aspect-ratio: 16 / 10;   /* keeps the arena proportional at any width */
  background: #edf6f4;
}
.game-canvas {
  width: 100%; height: 100%;
  display: block; cursor: crosshair;
  touch-action: none;   /* prevents scroll-jank on mobile during gameplay */
}
.arena-overlay {
  position: absolute; inset: 0;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  text-align: center; padding: 32px;
  background: rgba(237,246,244,0.92);
  backdrop-filter: blur(4px);
}
.overlay-icon { margin-bottom: 16px; }
.arena-overlay h2 {
  font-size: 22px; font-weight: 800;
  letter-spacing: -0.02em; color: #0d1117; margin: 0 0 12px;
}
.arena-overlay p {
  font-size: 14px; color: #4b5563;
  line-height: 1.65; max-width: 340px; margin: 0;
}
/* Fade in/out transition for the overlay */
.overlay-enter-active { transition: opacity 0.25s ease; }
.overlay-leave-active { transition: opacity 0.2s ease; }
.overlay-enter-from, .overlay-leave-to { opacity: 0; }

/* ── Right panel blocks ── */
.settings-block, .toggles-block, .history-block {
  background: #fff; border: 1px solid #e5e7eb;
  border-radius: 16px; padding: 18px;
}

.mode-select {
  width: 100%; margin-top: 10px;
  padding: 9px 12px; font-size: 13px;
  color: #0d1117; background: #f3f4f6;
  border: 1.5px solid transparent; border-radius: 10px;
  appearance: none; cursor: pointer;
  font-family: inherit;
  transition: border-color 0.15s;
}
.mode-select:focus  { outline: none; border-color: #93c5fd; }
.mode-select:disabled { opacity: 0.6; cursor: not-allowed; }

/* Toggle switch rows */
.toggles-block { display: flex; flex-direction: column; gap: 14px; }
.toggle-row {
  display: flex; align-items: center; gap: 12px;
  cursor: pointer;
}
.toggle-wrap { flex-shrink: 0; }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0,0,0,0); }
.toggle-track {
  display: flex; align-items: center;
  width: 36px; height: 20px;
  border-radius: 999px; background: #d1d5db;
  padding: 2px; cursor: pointer;
  transition: background 0.2s;
}
.toggle-track--on { background: #2563eb; }
.toggle-thumb {
  width: 16px; height: 16px;
  border-radius: 50%; background: #fff;
  box-shadow: 0 1px 3px rgba(0,0,0,0.2);
  transition: transform 0.2s;
}
.toggle-track--on .toggle-thumb { transform: translateX(16px); }
.toggle-label { font-size: 13px; font-weight: 500; color: #374151; }

/* History */
.history-list {
  list-style: none; padding: 0; margin: 10px 0 14px;
  display: flex; flex-direction: column; gap: 8px;
}
.history-empty { font-size: 13px; color: #9ca3af; text-align: center; padding: 8px 0; }
.history-item {
  display: flex; flex-direction: column; gap: 2px;
  padding: 10px 12px; background: #f8fafc;
  border-radius: 10px; border: 1px solid #f3f4f6;
}
.history-time { font-size: 11px; color: #9ca3af; font-weight: 500; }
.history-stats { font-size: 13px; color: #374151; font-weight: 600; }
.btn-export {
  width: 100%; padding: 9px;
  background: #f3f4f6; color: #4b5563;
  font-size: 13px; font-weight: 600;
  border-radius: 10px; border: 1px solid #e5e7eb; cursor: pointer;
  transition: background 0.15s;
}
.btn-export:hover { background: #e8eaf0; color: #0d1117; }

.disclaimer {
  font-size: 11.5px; color: #9ca3af;
  line-height: 1.6; margin: 0;
  background: #fff; border: 1px solid #e5e7eb;
  border-radius: 12px; padding: 14px;
}

/* ── Footer ── */
.footer { background: #0d1117; padding: 48px 0; }
.footer-inner {
  display: flex; align-items: center;
  justify-content: space-between; flex-wrap: wrap; gap: 24px;
}
.footer-left { display: flex; flex-direction: column; gap: 4px; }
.footer-logo  { font-size: 16px; font-weight: 700; color: #fff; letter-spacing: -0.3px; }
.footer-tagline { font-size: 13px; color: rgba(255,255,255,0.35); margin: 0; }
.footer-links { display: flex; gap: 28px; }
.footer-link {
  font-size: 14px; font-weight: 500;
  color: rgba(255,255,255,0.5); text-decoration: none;
  transition: color 0.2s;
}
.footer-link:hover { color: #fff; }
.footer-copy { font-size: 13px; color: rgba(255,255,255,0.3); margin: 0; }

/* ── Shared utility ── */
.container { max-width: 1160px; margin: 0 auto; padding: 0 36px; }

/* ── Responsive ── */
@media (max-width: 1024px) {
  .game-layout {
    grid-template-columns: 200px 1fr 200px;
  }
}

@media (max-width: 768px) {
  .nav-links     { display: none; }
  .nav-hamburger { display: flex; }
  .mobile-nav {
    display: block; position: fixed;
    top: 64px; left: 0; right: 0;
    background: rgba(255,255,255,0.98);
    backdrop-filter: blur(18px);
    border-bottom: 1px solid #e5e7eb;
    z-index: 99;
  }
  .mobile-nav-links { list-style: none; margin: 0; padding: 0; }
  .mobile-nav-link {
    display: block; padding: 16px 28px;
    font-size: 16px; font-weight: 500; color: #374151;
    text-decoration: none; border-bottom: 1px solid #f3f4f6;
    transition: background 0.15s;
  }
  .mobile-nav-link:hover { background: #f9fafb; color: #0d1117; }

  /* Stack the three-column layout vertically on mobile */
  .game-layout {
    grid-template-columns: 1fr;
    grid-template-rows: auto;
  }
  /* Re-order: controls first, then canvas, then history */
  .game-panel:first-child { order: 1; }
  .arena-wrap             { order: 2; aspect-ratio: 4 / 3; }
  .game-panel:last-child  { order: 3; }

  .page-hero { padding: 96px 0 40px; }
  .container { padding: 0 20px; }
  .footer-inner { flex-direction: column; align-items: flex-start; }
}
</style>
