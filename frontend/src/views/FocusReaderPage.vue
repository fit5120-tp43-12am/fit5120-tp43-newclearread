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

const STORAGE_KEY = 'focus-reader-v2-sessions'
const TOTAL_ROUNDS = 16

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
  message:      'Press Start, then tap the circle that matches the word shown above.',
  timePct:      0,       // 0-100, drives the timer progress bar width
  secondsLeft:  0,
  roundNum:     0,
  flashClass:   '',      // '' | 'flash-correct' | 'flash-wrong'
  score:        0,
  accuracy:     '--',
  reaction:     '--',
  level:        1,
  showOverlay:  true,
  overlayTitle: 'Find the Right Circle',
  overlayBody:  'Each round shows you a word or letter. Tap the moving circle that matches it — watch out for ones that look similar!',
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
  flashAlpha: 0,
  flashColor: null,
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
    // Lv 1-2: target keeps its distinct teal colour (beginner scaffolding)
    // Lv 3-4: all chips use random colours — must read to find the target
    // Lv 5-6: all chips are plain white — maximum reading focus, zero colour cue
    hue: G.level >= 5
      ? 'plain'
      : (isTarget && G.level <= 2 ? 'target' : pick(['blue', 'yellow', 'rose', 'plain'])),
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

// ── Audio feedback ────────────────────────────────────────────────────────────
function playBeep(type) {
  try {
    const ac = new (window.AudioContext || window.webkitAudioContext)()
    const osc = ac.createOscillator()
    const gain = ac.createGain()
    osc.connect(gain); gain.connect(ac.destination)
    if (type === 'correct') {
      osc.frequency.value = 880; osc.type = 'sine'
      gain.gain.setValueAtTime(0.25, ac.currentTime)
      gain.gain.exponentialRampToValueAtTime(0.001, ac.currentTime + 0.35)
      osc.start(ac.currentTime); osc.stop(ac.currentTime + 0.35)
    } else {
      osc.frequency.value = 200; osc.type = 'sawtooth'
      gain.gain.setValueAtTime(0.18, ac.currentTime)
      gain.gain.exponentialRampToValueAtTime(0.001, ac.currentTime + 0.45)
      osc.start(ac.currentTime); osc.stop(ac.currentTime + 0.45)
    }
  } catch(e) { /* silently ignore if audio context unavailable */ }
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
  utt.lang = 'en-US'; utt.rate = 0.68; utt.pitch = 1.05
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
    G.level++
    G.recent = []
    if (G.level === 3) {
      ui.message += ' — Level up! Colour hints removed — read carefully!'
    } else if (G.level === 5) {
      ui.message += ' — Level up! All circles are now the same colour. Pure reading!'
    } else {
      ui.message += ' — Level up!'
    }
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
    ui.message = `Great! You got "${chip.label}" in ${Math.round(rt)} ms.`
    playBeep('correct')
    G.flashColor = 'rgba(34,197,94,0.28)'; G.flashAlpha = 0.6
    ui.flashClass = 'flash-correct'; setTimeout(() => { ui.flashClass = '' }, 500)
  } else {
    G.wrong++; G.streak = 0
    G.score = Math.max(0, G.score - 30)
    G.recent.push({ ok: false, rt })
    ui.message = `Not quite — "${chip.label}" looks similar but the answer was "${G.target}". Try again!`
    playBeep('wrong')
    G.flashColor = 'rgba(239,68,68,0.25)'; G.flashAlpha = 0.6
    ui.flashClass = 'flash-wrong'; setTimeout(() => { ui.flashClass = '' }, 500)
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
  ui.message = `Time's up! The answer was "${G.target}". Keep going!`
  adaptDifficulty()
  syncUiStats()
  setTimeout(nextRound, 900)
}

// ── Round start ───────────────────────────────────────────────────────────────
function nextRound() {
  if (!G.running || G.paused) return
  G.roundIndex++
  if (G.roundIndex > TOTAL_ROUNDS) { finishSession(true); return }

  const pool = getPool()
  G.target   = pick(pool)
  // Every 3rd round uses audio cue (if sound is enabled) to train auditory-visual mapping
  G.cueMode  = settings.sound && G.roundIndex % 3 === 0 ? 'audio' : 'visual'
  G.roundDuration = Math.max(3800, 7200 - G.level * 520 + (settings.calm ? 1200 : 0))
  G.roundStartedAt = performance.now()
  G.roundActive    = true
  ui.roundNum = G.roundIndex

  const count  = Math.min(11, 4 + G.level + Math.floor(G.roundIndex / 5))
  const labels = buildLabels(G.target, count + 1)
  G.chips = labels.map((lbl, i) => makeChip(lbl, lbl === G.target, i, labels.length))

  if (G.cueMode === 'audio') {
    ui.cueLabel   = '♪ Listen'
    ui.cueIsAudio = true
    ui.message    = 'Listen to the word, then tap the circle that shows it.'
    speakTarget()
  } else {
    ui.cueLabel   = G.target
    ui.cueIsAudio = false
    ui.message    = 'Tap the circle that matches the word shown above.'
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
    ui.secondsLeft = Math.ceil(Math.max(0, G.roundDuration - (now - G.roundStartedAt)) / 1000)
    if (elapsed >= G.roundDuration) missRound()
  }

  drawBackground()
  G.chips.forEach(drawChip)

  if (G.flashAlpha > 0) {
    ctx.save()
    ctx.globalAlpha = G.flashAlpha
    ctx.fillStyle = G.flashColor
    ctx.fillRect(0, 0, canvasW(), canvasH())
    ctx.restore()
    G.flashAlpha = Math.max(0, G.flashAlpha - 0.06)
  }

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
  ui.secondsLeft  = 0
  ui.roundNum     = 0
  ui.showOverlay  = true
  ui.overlayTitle = completed ? 'Well done!' : 'Game Reset'
  ui.overlayBody  = completed
    ? `You got ${accuracy}% correct and reached level ${G.level}. Short, regular practice makes a real difference!`
    : 'Your results have been saved. Press Start whenever you are ready.'
  ui.message = completed
    ? `Finished! ${accuracy}% correct, highest level ${G.level}.`
    : 'Results saved. Press Start to play again.'
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

// ── Guide modal (multi-step carousel) ────────────────────────────────────────
const GUIDE_SEEN_KEY = 'clearead-training-guide-seen'
const showGuide  = ref(false)
const guideStep  = ref(0)
const guideDir   = ref(1)   // 1 = forward, -1 = backward (drives slide direction)
const TOTAL_GUIDE_STEPS = 5

function openGuide() {
  if (G.running && !G.paused) pauseGame()
  guideStep.value = 0
  showGuide.value = true
}
function closeGuide() {
  showGuide.value = false
  localStorage.setItem(GUIDE_SEEN_KEY, '1')
}
function nextStep() {
  if (guideStep.value < TOTAL_GUIDE_STEPS - 1) {
    guideDir.value = 1; guideStep.value++
  } else { closeGuide() }
}
function prevStep() {
  if (guideStep.value > 0) { guideDir.value = -1; guideStep.value-- }
}
function goToStep(i) {
  guideDir.value = i >= guideStep.value ? 1 : -1
  guideStep.value = i
}

// ── Guide step content ────────────────────────────────────────────────────────
const GUIDE_STEPS = [
  {
    title: 'Look at the target',
    desc: "A word or letter appears at the top of the screen — that's your target. Read it carefully before you start looking.",
  },
  {
    title: 'Find the matching circle',
    desc: 'Tap the moving circle whose label matches the target. The distractors look similar on purpose — look closely!',
  },
  {
    title: 'Beat the clock',
    desc: 'Each round has a countdown timer. Tap before time runs out. The faster you respond, the more bonus points you earn.',
  },
  {
    title: 'Listen for audio cues',
    desc: "Some rounds play a spoken word instead of showing it. Press Replay if you need to hear it again, then find the circle.",
  },
  {
    title: 'Difficulty adapts to you',
    desc: 'Do well and the game adds more circles and speeds up. Struggle and it eases off. Just keep playing at your own pace!',
  },
]

// ── Keyboard shortcuts ────────────────────────────────────────────────────────
function handleKey(e) {
  const key = e.key.toLowerCase()
  if (key === 'escape') { closeGuide() }
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

  // Auto-open guide on first visit — only once, never again after closing
  if (!localStorage.getItem(GUIDE_SEEN_KEY)) {
    setTimeout(() => { showGuide.value = true }, 600)
  }
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
          <li></li>
          <li><RouterLink to="/training"   class="nav-link nav-link--active">Training</RouterLink></li>
          <li><RouterLink to="/dictionary" class="nav-link">Dictionary</RouterLink></li>
          <li></li>
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
        <li></li>
        <li><RouterLink to="/training"   class="mobile-nav-link" @click="menuOpen = false">Training</RouterLink></li>
        <li><RouterLink to="/dictionary" class="mobile-nav-link" @click="menuOpen = false">Dictionary</RouterLink></li>
        <li></li>
      </ul>
    </div>

    <!-- ── Game wrapper ── -->
    <main class="game-main">
      <div class="game-card">

        <!-- ① Top status strip -->
        <div class="status-strip">
          <div class="status-pill">
            <svg width="13" height="13" viewBox="0 0 13 13" fill="none" aria-hidden="true">
              <circle cx="6.5" cy="6.5" r="5.5" stroke="currentColor" stroke-width="1.3"/>
              <path d="M6.5 4v3l1.5 1.5" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>
            </svg>
            Round <strong>{{ isRunning ? ui.roundNum : '—' }}</strong> / {{ TOTAL_ROUNDS }}
          </div>
          <div class="status-pill status-pill--score">
            Score <strong>{{ ui.score }}</strong>
          </div>
          <div class="status-pill">
            Level <strong>{{ ui.level }}</strong>/6
          </div>
          <div class="status-pill status-pill--accuracy" v-if="ui.accuracy !== '--'">
            Accuracy <strong>{{ ui.accuracy }}</strong>
          </div>
        </div>

        <!-- ② Cue display -->
        <div class="cue-area">
          <p class="cue-eyebrow">Find this</p>
          <div class="cue-word" :class="{ 'cue-word--audio': ui.cueIsAudio }">
            {{ ui.cueLabel }}
          </div>
          <button
            v-if="ui.cueIsAudio && isRunning && !isPaused"
            class="btn-replay"
            @click="speakTarget"
            aria-label="Replay audio cue"
          >
            <svg width="13" height="13" viewBox="0 0 13 13" fill="none" aria-hidden="true">
              <path d="M2 3.5l9 3-9 3V3.5z" fill="currentColor"/>
            </svg>
            Replay
          </button>
        </div>

        <!-- ③ Timer row -->
        <div class="timer-row" v-if="isRunning && !isPaused">
          <div class="timer-track" aria-label="Time remaining">
            <div class="timer-fill" :style="{ width: ui.timePct + '%', background: timerColor }"></div>
          </div>
          <span class="timer-seconds" :style="{ color: timerColor }">{{ ui.secondsLeft }}s</span>
        </div>

        <!-- ④ Canvas arena -->
        <div class="arena-wrap" :class="ui.flashClass">
          <canvas
            ref="canvasEl"
            class="game-canvas"
            @pointerdown="handleCanvasPointer"
            aria-label="Game arena — tap the chip that matches the cue"
          ></canvas>
          <Transition name="overlay">
            <div v-if="ui.showOverlay" class="arena-overlay">
              <div class="overlay-icon" aria-hidden="true">
                <svg width="44" height="44" viewBox="0 0 44 44" fill="none">
                  <circle cx="22" cy="22" r="20" fill="#eef2ff" stroke="#2563eb" stroke-width="2"/>
                  <path d="M15 22l5 5 9-9" stroke="#2563eb" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </div>
              <h2>{{ ui.overlayTitle }}</h2>
              <p>{{ ui.overlayBody }}</p>
            </div>
          </Transition>
        </div>

        <!-- ⑤ Feedback message -->
        <p class="feedback-msg" role="status" aria-live="polite">{{ ui.message }}</p>

        <!-- ⑥ Controls -->
        <div class="controls-row">
          <button
            v-if="!isRunning || isPaused"
            class="btn-start"
            @click="startGame"
          >
            {{ isPaused ? '▶ Resume' : (isRunning ? '↺ Restart' : '▶ Start') }}
          </button>
          <button
            v-if="isRunning && !isPaused"
            class="btn-pause"
            @click="pauseGame"
          >⏸ Pause</button>
          <button class="btn-reset" @click="resetGame">Reset</button>
          <button class="btn-guide" @click="openGuide" aria-label="How to play">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <circle cx="8" cy="8" r="7" stroke="currentColor" stroke-width="1.5"/>
              <path d="M8 11v-1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
              <path d="M8 9c0-2 3-2 3-4a3 3 0 1 0-6 0" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
            </svg>
            Guide
          </button>
        </div>

        <!-- ── Guide modal ── -->
        <Transition name="guide-fade">
          <div v-if="showGuide" class="guide-backdrop" @click.self="closeGuide">
            <div class="guide-modal" role="dialog" aria-label="How to play">
              <div class="guide-header">
                <h2 class="guide-title">How to Play</h2>
                <button class="guide-close" @click="closeGuide" aria-label="Close guide">
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                    <path d="M2 2l10 10M12 2L2 12" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
                  </svg>
                </button>
              </div>

              <!-- ── Carousel ── -->
              <div class="guide-carousel">

                <!-- Illustration slide -->
                <div class="guide-illus-wrap">
                  <Transition :name="guideDir === 1 ? 'guide-slide-fwd' : 'guide-slide-bwd'" mode="out-in">
                    <div class="guide-illus" :key="'illus-' + guideStep">

                      <!-- Step 0: Look at the target -->
                      <svg v-if="guideStep===0" width="200" height="164" viewBox="0 0 200 164" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <circle cx="100" cy="98" r="60" fill="#eef2ff"/>
                        <circle cx="100" cy="98" r="44" fill="white" stroke="#0f766e" stroke-width="3.5"/>
                        <text x="100" y="122" text-anchor="middle" font-size="60" font-weight="900" fill="#0d1117" font-family="Arial, sans-serif">b</text>
                        <rect x="48" y="8" width="104" height="28" rx="14" fill="#2563eb"/>
                        <text x="100" y="27" text-anchor="middle" font-size="11" font-weight="700" fill="white" font-family="Arial, sans-serif" letter-spacing="1.5">FIND THIS</text>
                        <line x1="100" y1="36" x2="100" y2="50" stroke="#2563eb" stroke-width="2.5" stroke-linecap="round" stroke-dasharray="3 2.5"/>
                        <path d="M93 50l7 8 7-8" stroke="#2563eb" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
                      </svg>

                      <!-- Step 1: Find the matching circle -->
                      <svg v-else-if="guideStep===1" width="200" height="164" viewBox="0 0 200 164" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <rect x="12" y="12" width="176" height="140" rx="18" fill="#f0fdf4"/>
                        <!-- Target chip (teal) -->
                        <circle cx="78" cy="80" r="34" fill="white" stroke="#0f766e" stroke-width="4"/>
                        <text x="78" y="91" text-anchor="middle" font-size="28" font-weight="900" fill="#0d1117" font-family="Arial, sans-serif">b</text>
                        <!-- Checkmark badge -->
                        <circle cx="102" cy="57" r="13" fill="#22c55e"/>
                        <path d="M95 57l6 6 9-8" stroke="white" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
                        <!-- Distractor 1 (blue) -->
                        <circle cx="148" cy="62" r="24" fill="white" stroke="#2f6fbb" stroke-width="2.5"/>
                        <text x="148" y="70" text-anchor="middle" font-size="18" font-weight="900" fill="#0d1117" font-family="Arial, sans-serif">d</text>
                        <!-- Distractor 2 (yellow/rose) -->
                        <circle cx="148" cy="118" r="22" fill="white" stroke="#c89a18" stroke-width="2.5"/>
                        <text x="148" y="126" text-anchor="middle" font-size="16" font-weight="900" fill="#0d1117" font-family="Arial, sans-serif">p</text>
                        <!-- Tap cursor -->
                        <path d="M38 112c0-1.2 0.6-2.3 1.7-2.8l14-6c1.4-0.6 3 0.3 3 1.8v13c0 1.2-0.9 2.2-2 2.4l-3.5 0.6 2.5 5.4c0.5 1-0.1 2.2-1.2 2.6l-2.3 0.8c-1 0.4-2.2-0.2-2.6-1.2l-2.5-5.5-2.3 2.5c-0.8 0.9-2.3 0.4-2.3-0.8v-13.6z" fill="#374151"/>
                      </svg>

                      <!-- Step 2: Beat the clock -->
                      <svg v-else-if="guideStep===2" width="200" height="164" viewBox="0 0 200 164" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <rect x="16" y="44" width="168" height="90" rx="18" fill="#fff7ed"/>
                        <!-- Clock icon -->
                        <circle cx="100" cy="32" r="22" fill="white" stroke="#f59e0b" stroke-width="2.5"/>
                        <line x1="100" y1="18" x2="100" y2="32" stroke="#374151" stroke-width="2.2" stroke-linecap="round"/>
                        <line x1="100" y1="32" x2="110" y2="38" stroke="#374151" stroke-width="2.2" stroke-linecap="round"/>
                        <!-- Timer bar track -->
                        <rect x="30" y="72" width="120" height="18" rx="9" fill="#fde8d4"/>
                        <!-- Timer fill (20% — red, almost empty) -->
                        <rect x="30" y="72" width="24" height="18" rx="9" fill="#ef4444"/>
                        <!-- 2s countdown label -->
                        <text x="165" y="85" text-anchor="middle" font-size="15" font-weight="800" fill="#ef4444" font-family="Arial, sans-serif">2s</text>
                        <!-- Labels -->
                        <text x="100" y="112" text-anchor="middle" font-size="13" font-weight="700" fill="#ef4444" font-family="Arial, sans-serif">HURRY!</text>
                        <text x="100" y="130" text-anchor="middle" font-size="10.5" fill="#9ca3af" font-family="Arial, sans-serif">Faster = more points</text>
                      </svg>

                      <!-- Step 3: Listen for audio cues -->
                      <svg v-else-if="guideStep===3" width="200" height="164" viewBox="0 0 200 164" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <circle cx="82" cy="82" r="60" fill="#eff6ff"/>
                        <!-- Speaker body -->
                        <path d="M44 67 L44 97 L56 97 L74 114 L74 50 L56 67 Z" fill="#2563eb"/>
                        <!-- Sound waves -->
                        <path d="M82 64 Q98 82 82 100" stroke="#2563eb" stroke-width="3.5" stroke-linecap="round" fill="none" opacity="0.7"/>
                        <path d="M92 55 Q114 82 92 109" stroke="#2563eb" stroke-width="2.8" stroke-linecap="round" fill="none" opacity="0.45"/>
                        <path d="M102 46 Q130 82 102 118" stroke="#2563eb" stroke-width="2" stroke-linecap="round" fill="none" opacity="0.25"/>
                        <!-- Musical note -->
                        <text x="148" y="58" font-size="30" fill="#f59e0b" font-family="Arial, sans-serif">♪</text>
                        <!-- Replay pill -->
                        <rect x="112" y="100" width="68" height="26" rx="13" fill="#2563eb"/>
                        <text x="146" y="117" text-anchor="middle" font-size="11" font-weight="700" fill="white" font-family="Arial, sans-serif">▶ Replay</text>
                      </svg>

                      <!-- Step 4: Difficulty adapts -->
                      <svg v-else-if="guideStep===4" width="200" height="164" viewBox="0 0 200 164" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <rect x="12" y="14" width="176" height="136" rx="18" fill="#f0fdf4"/>
                        <!-- "Lv 1" label + 3 small circles -->
                        <text x="48" y="42" text-anchor="middle" font-size="10" font-weight="700" fill="#9ca3af" font-family="Arial, sans-serif">Lv 1</text>
                        <circle cx="32" cy="64" r="11" fill="#d1d5db"/>
                        <circle cx="56" cy="64" r="11" fill="#d1d5db"/>
                        <circle cx="44" cy="88" r="11" fill="#d1d5db"/>
                        <!-- Arrow right -->
                        <path d="M76 76 L94 76" stroke="#9ca3af" stroke-width="2.2" stroke-linecap="round"/>
                        <path d="M90 70 L96 76 L90 82" stroke="#9ca3af" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
                        <!-- "Lv 3" label + 5 circles (faster/harder) -->
                        <text x="148" y="42" text-anchor="middle" font-size="10" font-weight="700" fill="#16a34a" font-family="Arial, sans-serif">Lv 3</text>
                        <circle cx="118" cy="60" r="10" fill="#86efac"/>
                        <circle cx="136" cy="52" r="10" fill="#86efac"/>
                        <circle cx="158" cy="60" r="10" fill="#86efac"/>
                        <circle cx="122" cy="83" r="10" fill="#86efac"/>
                        <circle cx="148" cy="80" r="10" fill="#86efac"/>
                        <!-- Trend line -->
                        <path d="M28 130 Q100 108 168 74" stroke="#22c55e" stroke-width="2.5" stroke-linecap="round" fill="none" stroke-dasharray="5 3"/>
                        <text x="100" y="150" text-anchor="middle" font-size="10.5" fill="#6b7280" font-family="Arial, sans-serif">Adapts to your skill level</text>
                      </svg>

                    </div>
                  </Transition>
                </div>

                <!-- Text slide -->
                <Transition :name="guideDir === 1 ? 'guide-slide-fwd' : 'guide-slide-bwd'" mode="out-in">
                  <div class="guide-text" :key="'text-' + guideStep">
                    <p class="guide-step-counter">{{ guideStep + 1 }} / {{ TOTAL_GUIDE_STEPS }}</p>
                    <h3 class="guide-step-title">{{ GUIDE_STEPS[guideStep].title }}</h3>
                    <p class="guide-step-desc">{{ GUIDE_STEPS[guideStep].desc }}</p>
                  </div>
                </Transition>

                <!-- Dot indicators -->
                <div class="guide-dots">
                  <button
                    v-for="(_, i) in GUIDE_STEPS"
                    :key="i"
                    :class="['guide-dot', { 'guide-dot--active': guideStep === i }]"
                    @click="goToStep(i)"
                    :aria-label="`Go to step ${i + 1}`"
                  />
                </div>

                <!-- Navigation -->
                <div class="guide-nav">
                  <button class="guide-nav-btn guide-nav-prev" @click="prevStep" :disabled="guideStep === 0">
                    ← Back
                  </button>
                  <button class="guide-nav-btn guide-nav-next" @click="nextStep">
                    {{ guideStep === TOTAL_GUIDE_STEPS - 1 ? "Let's play!" : 'Next →' }}
                  </button>
                </div>

              </div>
            </div>
          </div>
        </Transition>

        <!-- ⑦ Settings row -->
        <div class="settings-row">
          <select v-model="settings.mode" class="mode-select" :disabled="isRunning && !isPaused">
            <option value="mixed">Mix — Letters, Sounds &amp; Words</option>
            <option value="letters">Tricky Letters (b, d, p, q)</option>
            <option value="chunks">Sound Groups (sh, ch, th)</option>
            <option value="words">Short Words &amp; Made-up Words</option>
          </select>

          <label class="toggle-row">
            <span class="toggle-wrap">
              <input type="checkbox" class="sr-only" v-model="settings.sound" />
              <span class="toggle-track" :class="{ 'toggle-track--on': settings.sound }">
                <span class="toggle-thumb"></span>
              </span>
            </span>
            <span class="toggle-label">🔊 Sound</span>
          </label>

          <label class="toggle-row">
            <span class="toggle-wrap">
              <input type="checkbox" class="sr-only" v-model="settings.calm" />
              <span class="toggle-track" :class="{ 'toggle-track--on': settings.calm }">
                <span class="toggle-thumb"></span>
              </span>
            </span>
            <span class="toggle-label">🐢 Slow</span>
          </label>
        </div>

        <!-- ⑧ History (compact, collapsible) -->
        <details class="history-details">
          <summary class="history-summary">
            <span class="history-summary-label">
              <svg width="15" height="15" viewBox="0 0 15 15" fill="none" aria-hidden="true">
                <path d="M2 4.5h11M2 7.5h7M2 10.5h5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
              </svg>
              Your recent games
            </span>
            <svg class="history-chevron" width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
              <path d="M3 5l4 4 4-4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </summary>
          <ol class="history-list">
            <li v-if="!ui.sessions.length" class="history-empty">No games yet</li>
            <li v-for="(s, i) in ui.sessions" :key="i" class="history-item">
              <span class="history-time">{{ formatDate(s.date) }}</span>
              <span class="history-stats">{{ s.accuracy }}% · {{ s.score }} pts · Lv {{ s.level }}</span>
            </li>
          </ol>
        </details>

        <p class="disclaimer">Practice game only — not a medical test.</p>

      </div>
    </main>

    <!-- ── Footer ── -->
    <footer class="footer">
      <div class="container footer-inner">
        <div class="footer-left">
          <span class="footer-logo">Clearead</span>
          <p class="footer-tagline">Built for minds that think differently.</p>
        </div>
        <nav class="footer-links">
          <RouterLink to="/privacy-policy" class="footer-link">Privacy Policy</RouterLink>
        </nav>
        <p class="footer-copy">© 2026 Clearead. All rights reserved.</p>
      </div>
    </footer>

  </div>
</template>


<style scoped>
/* ── Page ── */
.page {
  min-height: 100vh;
  background:
    radial-gradient(ellipse 80% 40% at 0%   0%,   rgba(147,167,255,0.50) 0%, transparent 55%),
    radial-gradient(ellipse 70% 35% at 100% 0%,   rgba(255,200,150,0.42) 0%, transparent 52%),
    radial-gradient(ellipse 60% 30% at 0%   50%,  rgba(147,167,255,0.25) 0%, transparent 55%),
    radial-gradient(ellipse 55% 28% at 100% 50%,  rgba(255,218,180,0.28) 0%, transparent 52%),
    radial-gradient(ellipse 65% 30% at 0%   100%, rgba(147,167,255,0.30) 0%, transparent 55%),
    radial-gradient(ellipse 60% 28% at 100% 100%, rgba(255,200,150,0.30) 0%, transparent 52%),
    #f4f5ff;
  color: #0d1117;
}

/* ── Navbar ── */
.navbar {
  position: fixed; top: 0; left: 0; right: 0;
  z-index: 100;
  transition: background 0.3s, box-shadow 0.3s;
}
.navbar--scrolled {
  background: rgba(244,245,255,0.82);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  box-shadow: 0 1px 0 rgba(99,120,255,0.1);
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
.mobile-nav { display: none; }

/* ── Main centred layout ── */
.game-main {
  min-height: 100vh;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 88px 20px 60px;
}

/* The single game card */
.game-card {
  width: 100%;
  max-width: 780px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

/* ── ① Status strip ── */
.status-strip {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.status-pill {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 8px 18px;
  background: rgba(255,255,255,0.65);
  border: 1px solid rgba(255,255,255,0.9);
  backdrop-filter: blur(12px);
  border-radius: 999px;
  font-size: 15px; font-weight: 500; color: #4b5563;
}
.status-pill strong { color: #0d1117; font-weight: 700; }
.status-pill--score strong { color: #2563eb; }
.status-pill--accuracy strong { color: #16a34a; }

/* ── ② Cue area ── */
.cue-area {
  background: rgba(255,255,255,0.65);
  border: 1px solid rgba(255,255,255,0.9);
  backdrop-filter: blur(16px);
  border-radius: 20px;
  padding: 24px 32px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}
.cue-eyebrow {
  font-size: 11px; font-weight: 700;
  letter-spacing: 0.1em; text-transform: uppercase;
  color: #6b7280; margin: 0;
}
.cue-word {
  font-size: clamp(48px, 8vw, 80px);
  font-weight: 900; letter-spacing: -0.03em;
  color: #0d1117; line-height: 1;
}
.cue-word--audio {
  font-size: 32px; color: #2563eb;
}
.btn-replay {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 6px 16px; font-size: 13px; font-weight: 600;
  color: #2563eb; background: #eef2ff;
  border: 1px solid #bfdbfe; border-radius: 999px; cursor: pointer;
  transition: background 0.15s;
}
.btn-replay:hover { background: #dbeafe; }

/* ── ③ Timer ── */
.timer-row {
  display: flex; align-items: center; gap: 10px;
}
.timer-track {
  flex: 1; height: 10px;
  background: rgba(255,255,255,0.5);
  border-radius: 999px; overflow: hidden;
  border: 1px solid rgba(255,255,255,0.8);
}
.timer-fill {
  height: 100%; border-radius: 999px;
  transition: width 0.1s linear, background 0.4s ease;
}
.timer-seconds {
  font-size: 16px; font-weight: 800;
  letter-spacing: -0.02em;
  min-width: 32px; text-align: right;
  transition: color 0.4s;
}

/* ── ④ Arena ── */
.arena-wrap {
  position: relative;
  border-radius: 20px; overflow: hidden;
  border: 1px solid rgba(255,255,255,0.85);
  box-shadow: 0 8px 32px rgba(99,120,255,0.1);
  aspect-ratio: 16/9;
  min-height: 320px;
  transition: box-shadow 0.2s;
}
.arena-wrap.flash-correct {
  box-shadow: 0 0 0 3px #22c55e, 0 8px 32px rgba(34,197,94,0.25);
}
.arena-wrap.flash-wrong {
  box-shadow: 0 0 0 3px #ef4444, 0 8px 32px rgba(239,68,68,0.2);
}
.game-canvas {
  width: 100%; height: 100%;
  display: block; cursor: crosshair;
  touch-action: none;
}
.arena-overlay {
  position: absolute; inset: 0;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  text-align: center; padding: 32px;
  background: rgba(237,246,244,0.88);
  backdrop-filter: blur(6px);
}
.overlay-icon { margin-bottom: 16px; }
.arena-overlay h2 {
  font-size: 22px; font-weight: 800;
  letter-spacing: -0.02em; color: #0d1117; margin: 0 0 12px;
}
.arena-overlay p {
  font-size: 14.5px; color: #4b5563;
  line-height: 1.65; max-width: 380px; margin: 0;
}
.overlay-enter-active { transition: opacity 0.25s ease; }
.overlay-leave-active { transition: opacity 0.2s ease; }
.overlay-enter-from, .overlay-leave-to { opacity: 0; }

/* ── ⑤ Feedback message ── */
.feedback-msg {
  min-height: 22px;
  font-size: 14px; color: #4b5563;
  text-align: center; margin: 0;
  line-height: 1.5;
}

/* ── ⑥ Controls ── */
.controls-row {
  display: flex; gap: 10px; justify-content: center;
}
.btn-start {
  padding: 13px 40px;
  background: #2563eb; color: #fff;
  font-size: 16px; font-weight: 700;
  border-radius: 999px; border: none; cursor: pointer;
  box-shadow: 0 6px 20px rgba(37,99,235,0.3);
  transition: background 0.2s, transform 0.15s;
  letter-spacing: -0.01em;
}
.btn-start:hover { background: #1d4ed8; transform: translateY(-2px); }
.btn-pause {
  padding: 13px 24px;
  background: rgba(255,255,255,0.7); color: #374151;
  font-size: 15px; font-weight: 600;
  border-radius: 999px; border: 1px solid rgba(255,255,255,0.9);
  backdrop-filter: blur(10px); cursor: pointer;
  transition: background 0.15s, transform 0.15s;
}
.btn-pause:hover { background: rgba(255,255,255,0.95); transform: translateY(-1px); }
.btn-reset {
  padding: 13px 20px;
  background: none; color: #9ca3af;
  font-size: 14px; font-weight: 500;
  border-radius: 999px; border: 1px solid rgba(0,0,0,0.08); cursor: pointer;
  transition: color 0.15s, background 0.15s;
}
.btn-reset:hover { color: #ef4444; background: rgba(239,68,68,0.06); border-color: #fecaca; }

/* ── Guide button ── */
.btn-guide {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 13px 20px;
  background: none; color: #6b7280;
  font-size: 15px; font-weight: 500;
  border-radius: 999px; border: 1px solid rgba(0,0,0,0.1); cursor: pointer;
  transition: color 0.15s, background 0.15s, border-color 0.15s;
}
.btn-guide:hover {
  color: #2563eb; background: #eef2ff; border-color: #bfdbfe;
}

/* ── Guide modal ── */
.guide-backdrop {
  position: fixed; inset: 0; z-index: 300;
  background: rgba(15,20,40,0.45);
  backdrop-filter: blur(6px);
  display: flex; align-items: center; justify-content: center;
  padding: 20px;
}
.guide-modal {
  background: #fff;
  border-radius: 24px;
  padding: 32px;
  max-width: 520px; width: 100%;
  box-shadow: 0 24px 64px rgba(0,0,0,0.18);
  display: flex; flex-direction: column; gap: 24px;
}
.guide-header {
  display: flex; align-items: center; justify-content: space-between;
}
.guide-title {
  font-size: 22px; font-weight: 800;
  letter-spacing: -0.03em; color: #0d1117; margin: 0;
}
.guide-close {
  display: flex; align-items: center; justify-content: center;
  width: 32px; height: 32px;
  background: #f3f4f6; border: none; border-radius: 8px; cursor: pointer;
  color: #6b7280; transition: background 0.15s, color 0.15s;
}
.guide-close:hover { background: #e5e7eb; color: #0d1117; }

/* ── Guide carousel ── */
.guide-carousel {
  display: flex; flex-direction: column; gap: 20px;
}

/* Fixed-height illustration area so layout doesn't jump between slides */
.guide-illus-wrap {
  position: relative;
  height: 172px;
  display: flex; align-items: center; justify-content: center;
  overflow: hidden;
}
.guide-illus {
  display: flex; align-items: center; justify-content: center;
  width: 100%;
}

/* Text block */
.guide-text {
  text-align: center; padding: 0 8px;
}
.guide-step-counter {
  font-size: 11px; font-weight: 700;
  letter-spacing: 0.1em; text-transform: uppercase;
  color: #2563eb; margin: 0 0 6px;
}
.guide-step-title {
  font-size: 20px; font-weight: 800;
  letter-spacing: -0.02em; color: #0d1117;
  margin: 0 0 8px;
}
.guide-step-desc {
  font-size: 14px; color: #4b5563;
  line-height: 1.68; margin: 0;
}

/* Dot indicators */
.guide-dots {
  display: flex; gap: 8px; justify-content: center;
}
.guide-dot {
  height: 8px; width: 8px;
  border-radius: 999px; background: #e5e7eb;
  border: none; cursor: pointer; padding: 0;
  transition: background 0.2s, width 0.25s;
}
.guide-dot--active {
  background: #2563eb; width: 22px;
}

/* Nav buttons */
.guide-nav {
  display: flex; gap: 10px;
}
.guide-nav-btn {
  padding: 13px 24px;
  font-size: 15px; font-weight: 600;
  border-radius: 12px; cursor: pointer;
  transition: all 0.15s; font-family: inherit;
}
.guide-nav-prev {
  background: #f3f4f6; color: #4b5563;
  border: 1px solid #e5e7eb;
}
.guide-nav-prev:hover:not(:disabled) { background: #e5e7eb; }
.guide-nav-prev:disabled { opacity: 0.32; cursor: not-allowed; }
.guide-nav-next {
  flex: 1;
  background: #2563eb; color: #fff;
  border: none;
  box-shadow: 0 4px 14px rgba(37,99,235,0.25);
}
.guide-nav-next:hover { background: #1d4ed8; transform: translateY(-1px); }

/* Carousel slide transitions — forward */
.guide-slide-fwd-enter-active { transition: all 0.28s ease; }
.guide-slide-fwd-leave-active { transition: all 0.22s ease; }
.guide-slide-fwd-enter-from   { transform: translateX(48px); opacity: 0; }
.guide-slide-fwd-leave-to     { transform: translateX(-48px); opacity: 0; }
/* Carousel slide transitions — backward */
.guide-slide-bwd-enter-active { transition: all 0.28s ease; }
.guide-slide-bwd-leave-active { transition: all 0.22s ease; }
.guide-slide-bwd-enter-from   { transform: translateX(-48px); opacity: 0; }
.guide-slide-bwd-leave-to     { transform: translateX(48px); opacity: 0; }

/* Modal transition */
.guide-fade-enter-active { transition: opacity 0.2s ease, transform 0.2s ease; }
.guide-fade-leave-active { transition: opacity 0.18s ease, transform 0.15s ease; }
.guide-fade-enter-from   { opacity: 0; transform: scale(0.96); }
.guide-fade-leave-to     { opacity: 0; transform: scale(0.97); }

/* ── ⑦ Settings ── */
.settings-row {
  display: flex; align-items: center; gap: 16px; flex-wrap: wrap;
  background: rgba(255,255,255,0.55);
  border: 1px solid rgba(255,255,255,0.85);
  backdrop-filter: blur(12px);
  border-radius: 16px; padding: 16px 24px;
}
.mode-select {
  flex: 1; min-width: 180px;
  padding: 10px 38px 10px 14px; font-size: 15px;
  color: #0d1117; background: rgba(255,255,255,0.7);
  border: 1px solid rgba(0,0,0,0.1); border-radius: 10px;
  appearance: none; cursor: pointer; font-family: inherit;
  transition: border-color 0.15s;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12' fill='none'%3E%3Cpath d='M2 4l4 4 4-4' stroke='%236b7280' stroke-width='1.6' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 13px center;
}
.mode-select:focus { outline: none; border-color: #93c5fd; }
.mode-select:disabled { opacity: 0.6; cursor: not-allowed; }
.toggle-row {
  display: flex; align-items: center; gap: 10px; cursor: pointer; flex-shrink: 0;
}
.toggle-wrap { flex-shrink: 0; }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0,0,0,0); }
.toggle-track {
  display: flex; align-items: center;
  width: 40px; height: 22px;
  border-radius: 999px; background: #d1d5db;
  padding: 2px; cursor: pointer;
  transition: background 0.2s;
}
.toggle-track--on { background: #2563eb; }
.toggle-thumb {
  width: 18px; height: 18px;
  border-radius: 50%; background: #fff;
  box-shadow: 0 1px 3px rgba(0,0,0,0.2);
  transition: transform 0.2s;
}
.toggle-track--on .toggle-thumb { transform: translateX(18px); }
.toggle-label { font-size: 15px; font-weight: 500; color: #374151; }

/* ── ⑧ History ── */
.history-details {
  background: rgba(255,255,255,0.45);
  border: 1px solid rgba(255,255,255,0.8);
  backdrop-filter: blur(10px);
  border-radius: 14px; overflow: hidden;
}
.history-summary {
  padding: 14px 22px;
  font-size: 15px; font-weight: 600; color: #6b7280;
  cursor: pointer; list-style: none; user-select: none;
  display: flex; align-items: center; justify-content: space-between;
  border-radius: 14px;
  transition: color 0.2s, background 0.18s;
}
.history-summary:hover { color: #374151; background: rgba(255,255,255,0.5); }
.history-summary-label {
  display: flex; align-items: center; gap: 8px;
}
.history-chevron {
  flex-shrink: 0;
  transition: transform 0.28s cubic-bezier(0.4, 0, 0.2, 1);
}
.history-details[open] .history-chevron {
  transform: rotate(180deg);
}
.history-details[open] .history-summary {
  color: #374151;
  border-bottom: 1px solid rgba(0,0,0,0.06);
  border-radius: 14px 14px 0 0;
}
.history-list {
  list-style: none; padding: 0 22px 14px; margin: 0;
  display: flex; flex-direction: column; gap: 8px;
}
.history-empty { font-size: 14px; color: #9ca3af; padding: 4px 0; }
.history-item {
  display: flex; justify-content: space-between; align-items: center;
  padding: 10px 14px;
  background: rgba(255,255,255,0.6); border-radius: 10px;
  font-size: 14px;
}
.history-time { color: #6b7280; }
.history-stats { font-weight: 600; color: #374151; }

/* ── Disclaimer ── */
.disclaimer {
  font-size: 13px; color: #9ca3af;
  text-align: center; margin: 0;
}

/* ── Footer ── */
.footer {
  background: linear-gradient(135deg, #1e3a8a 0%, #312e81 100%);
  padding: 52px 0;
}
.footer-inner {
  display: flex; align-items: center;
  justify-content: space-between; flex-wrap: wrap; gap: 24px;
}
.footer-left { display: flex; flex-direction: column; gap: 4px; }
.footer-logo { font-size: 16px; font-weight: 700; color: #fff; letter-spacing: -0.3px; }
.footer-tagline { font-size: 13px; color: rgba(255,255,255,0.45); margin: 0; }
.footer-links { display: flex; gap: 28px; }
.footer-link {
  font-size: 14px; font-weight: 500;
  color: rgba(255,255,255,0.6); text-decoration: none;
  transition: color 0.2s;
}
.footer-link:hover { color: #fff; }
.footer-copy { font-size: 13px; color: rgba(255,255,255,0.35); margin: 0; }

.container { max-width: 1160px; margin: 0 auto; padding: 0 36px; }

/* ── Responsive ── */
@media (max-width: 768px) {
  .nav-links { display: none; }
  .nav-hamburger { display: flex; }
  .mobile-nav {
    display: block; position: fixed;
    top: 64px; left: 0; right: 0;
    background: rgba(244,245,255,0.96);
    backdrop-filter: blur(20px);
    border-bottom: 1px solid rgba(99,120,255,0.1);
    z-index: 99;
  }
  .mobile-nav-links { list-style: none; margin: 0; padding: 0; }
  .mobile-nav-link {
    display: block; padding: 16px 28px;
    font-size: 16px; font-weight: 500; color: #374151;
    text-decoration: none; border-bottom: 1px solid rgba(0,0,0,0.05);
    transition: background 0.15s;
  }
  .mobile-nav-link:hover { background: rgba(255,255,255,0.6); color: #0d1117; }
  .game-main { padding: 80px 12px 48px; }
  .cue-area { padding: 18px 20px; }
  .controls-row { flex-wrap: wrap; }
  .btn-start { width: 100%; justify-content: center; }
  .container { padding: 0 20px; }
  .footer-inner { flex-direction: column; align-items: flex-start; }
}
</style>
