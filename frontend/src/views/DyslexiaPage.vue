<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

/* ── Nav ─────────────────────────────────────────────────────────────── */
const scrolled = ref(false)   // true when the user scrolled down, so we can style the navbar
const menuOpen = ref(false)   // true when the mobile menu is open
function onScroll() { scrolled.value = window.scrollY > 10 }
onMounted(() => window.addEventListener('scroll', onScroll))
onUnmounted(() => window.removeEventListener('scroll', onScroll))

/* ── Chart Pagination ─────────────────────────────────────────────────── */
// we have 2 charts on this page — the user can switch between them using tabs or prev/next buttons
const chartIdx = ref(0)   // index of the currently shown chart (0 = bar chart, 1 = donut)
const CHARTS = 2          // total number of charts

// jump to a specific chart by index
function goTo(i) { chartIdx.value = i }
// go to the previous chart (does nothing if already on the first one)
function prevChart() { if (chartIdx.value > 0) chartIdx.value-- }
// go to the next chart (does nothing if already on the last one)
function nextChart() { if (chartIdx.value < CHARTS - 1) chartIdx.value++ }

/* ── Chart 1: Horizontal Bar Chart ───────────────────────────────────── */
// data for each disability group — m = male %, f = female %
// source: ABS SDAC 2022, ages 0–24
const barGroups = [
  { lines: ['Learning and', 'understanding'], m: 8.3, f: 4.9 },
  { lines: ['Psychosocial'],                  m: 6.4, f: 5.1 },
  { lines: ['Sensory and speech'],            m: 4.4, f: 3.0 },
  { lines: ['Physical'],                      m: 4.3, f: 3.9 },
  { lines: ['Other'],                         m: 3.0, f: 3.4 },
  { lines: ['Head injury / ABI'],             m: 1.3, f: 0.3 },
]

const sexFlt = ref('both')  // filter: 'both' | 'm' | 'f' — controls which bars are highlighted
const bTip   = ref(null)    // tooltip data: { x, y, text } — null means no tooltip

/* SVG bar-chart layout constants — these define the chart's coordinate system */
const BAR_W     = 600        // total SVG width
const BAR_H_SVG = 295        // total SVG height
const ML  = 185, MR = 15, MT = 44, MB = 38   // margins: left, right, top, bottom
const CW  = BAR_W - ML - MR          // chart drawing width = 400px
const CH  = BAR_H_SVG - MT - MB      // chart drawing height = 213px
const MAX_V = 9.5                     // max x-axis value (percentage)
const SX  = CW / MAX_V               // pixels per 1% on the x-axis (≈ 42.1)
const GH  = CH / barGroups.length    // height per group row (≈ 35.5)
const BH  = 13, BG = 4               // individual bar height, gap between male/female bars
const AXISY = BAR_H_SVG - MB         // y position of the x-axis line = 257
const DYLX  = ML + 4.9 * SX         // x position of the dyslexia reference line (≈ 391)

// y-position helpers for each row's male bar, female bar, and centre
function mY(i) { return MT + i * GH }
function fY(i) { return MT + i * GH + BH + BG }
function cY(i) { return MT + i * GH + (BH * 2 + BG) / 2 }

// return 1 (full opacity) if the bar matches the current filter, 0.15 (faded) otherwise
function barAlpha(sex) {
  return sexFlt.value === 'both' || sexFlt.value === sex ? 1 : 0.15
}

// show a tooltip when the user hovers a bar — flip position if it would go off screen
function showTip(i, sex, val) {
  const bx = ML + val * SX
  let tx = bx + 10
  if (tx + 122 > BAR_W) tx = bx - 130
  bTip.value = {
    x: tx,
    y: (sex === 'm' ? mY(i) : fY(i)) + BH / 2,
    text: `${sex === 'm' ? 'Males' : 'Females'}: ${val}%`,
  }
}

/* ── Chart 2: Donut Chart ────────────────────────────────────────────── */
// breakdown of the "psychological development" disability category
// dyslexia falls under this category in ABS data
const donutRaw = [
  { label: 'ASD',      v: 18.5, color: '#2563eb', note: 'Autism Spectrum Disorder' },
  { label: 'Dyslexia', v:  4.9, color: '#ef4444', note: 'Reading & learning difficulty' },
  { label: 'Others',   v:  0.5, color: '#9ca3af', note: 'Other conditions (derived)' },
]
const PSYCH  = 23.9       // total % of people with a psychological development condition
const hovSeg = ref(-1)    // index of the segment being hovered (-1 means none)

/* SVG donut constants — viewBox is 560×380, donut centred at (280, 190) */
const DCX = 280, DCY = 190   // centre of the donut
const DRO = 155, DRI = 92    // outer and inner radius

// convert polar coordinates (angle in degrees) to an SVG [x, y] point
function pol(cx, cy, r, deg) {
  const rad = (deg - 90) * Math.PI / 180
  return [+(cx + r * Math.cos(rad)).toFixed(2), +(cy + r * Math.sin(rad)).toFixed(2)]
}

// build the SVG path string for one donut segment
// if expand is true, the segment pops outward a bit (used on hover)
function makeSectorPath(cx, cy, ro, ri, a0, a1, expand) {
  const off = expand ? 8 : 0
  const mid = (a0 + a1) / 2
  // offset the centre point slightly outward to create the pop-out effect
  const ox = off * Math.cos((mid - 90) * Math.PI / 180)
  const oy = off * Math.sin((mid - 90) * Math.PI / 180)
  const ccx = cx + ox, ccy = cy + oy
  const [x1, y1] = pol(ccx, ccy, ro, a0)
  const [x2, y2] = pol(ccx, ccy, ro, a1)
  const [x3, y3] = pol(ccx, ccy, ri, a1)
  const [x4, y4] = pol(ccx, ccy, ri, a0)
  const lg = (a1 - a0 > 180) ? 1 : 0   // large-arc flag required by SVG arc command
  return `M${x1} ${y1} A${ro} ${ro} 0 ${lg} 1 ${x2} ${y2} L${x3} ${y3} A${ri} ${ri} 0 ${lg} 0 ${x4} ${y4}Z`
}

// compute all the segment paths and label positions based on the raw data
const segs = computed(() => {
  const tot = donutRaw.reduce((s, d) => s + d.v, 0)
  let a = 0
  return donutRaw.map((d, i) => {
    const sweep = (d.v / tot) * 360    // degrees this segment takes up
    const a1   = a + sweep
    const hov  = hovSeg.value === i    // true if this segment is being hovered
    const path = makeSectorPath(DCX, DCY, DRO, DRI, a, a1, hov)
    const mid  = a + sweep / 2         // midpoint angle (used to position the label)
    const [lx1, ly1] = pol(DCX, DCY, DRO + 6,  mid)   // start of the label line
    const [lx,  ly ] = pol(DCX, DCY, DRO + 26, mid)   // end of the label line / text anchor
    const anc  = lx > DCX ? 'start' : 'end'            // left or right text alignment
    const pct  = (d.v / PSYCH * 100).toFixed(1)        // % within the psychological category
    const seg  = { ...d, path, a0: a, a1, mid, lx1, ly1, lx, ly, anc, pct, sweep }
    a = a1
    return seg
  })
})

// the text shown in the centre of the donut
// defaults to the category total, but updates when a segment is hovered
const ctxt = computed(() => {
  if (hovSeg.value >= 0) {
    const s = donutRaw[hovSeg.value]
    return { top: s.label, mid: `${s.v}%`, bot: `${(s.v / PSYCH * 100).toFixed(1)}% within` }
  }
  return { top: 'Psychological', mid: 'development', bot: `${PSYCH}% of all` }
})
</script>

<template>
  <div class="page">

    <!-- Navbar -->
    <nav :class="['navbar', { 'navbar--scrolled': scrolled }]">
      <div class="nav-inner">
        <RouterLink to="/" class="nav-logo">
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
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
          <li><RouterLink to="/" class="nav-link">Home</RouterLink></li>
          <li><RouterLink to="/reading" class="nav-link">Reading Support</RouterLink></li>
          <li><RouterLink to="/dyslexia" class="nav-link nav-link--active">Understand Dyslexia</RouterLink></li>
          <li><RouterLink to="/training" class="nav-link">Training</RouterLink></li>
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
        <li><RouterLink to="/"         class="mobile-nav-link" @click="menuOpen = false">Home</RouterLink></li>
        <li><RouterLink to="/reading"  class="mobile-nav-link" @click="menuOpen = false">Reading Support</RouterLink></li>
        <li><RouterLink to="/dyslexia" class="mobile-nav-link" @click="menuOpen = false">Understand Dyslexia</RouterLink></li>
        <li><RouterLink to="/training" class="mobile-nav-link" @click="menuOpen = false">Training</RouterLink></li>
      </ul>
    </div>

    <main>

      <!-- ① Hero -->
      <section class="section-hero">
        <div class="hero-bg-blob blob-left"></div>
        <div class="hero-bg-blob blob-right"></div>
        <div class="container hero-container">
          <p class="eyebrow">Understanding Dyslexia in Australia</p>
          <h1 class="hero-title">
            Dyslexia is a difference,<br/>
            not a <span class="text-gradient">deficit.</span>
          </h1>
          <p class="hero-sub">
            Many university students experience dyslexia. It affects how the brain
            processes text — not how capable or intelligent you are.<br/><br/>
            <span class="hero-sub-question">Would you like some support?</span>
          </p>
          <div class="hero-actions">
            <RouterLink to="/reading" class="btn-primary">Start Here</RouterLink>
            <a href="#strategies" class="btn-ghost">Reading Strategies</a>
          </div>
        </div>
      </section>

      <!-- ② Key Stats -->
      <section class="section-stats">
        <div class="container">
          <div class="stats-row">
            <div class="stat-item">
              <span class="stat-num">10%</span>
              <p class="stat-label">Official estimated prevalence of dyslexia across the Australian population</p>
            </div>
            <div class="stat-divider"></div>
            <div class="stat-item">
              <span class="stat-num">1 in 5</span>
              <p class="stat-label">Potential rate if measured by UK or US standards — up to 2.5 million Australians</p>
            </div>
            <div class="stat-divider"></div>
            <div class="stat-item">
              <span class="stat-num">80–90%</span>
              <p class="stat-label">Of students receiving learning support in school are affected by dyslexia</p>
            </div>
            <div class="stat-divider"></div>
            <div class="stat-item">
              <span class="stat-num">40%</span>
              <p class="stat-label">Inheritance risk if a first-degree family member has dyslexia</p>
            </div>
          </div>
        </div>
      </section>

      <!-- ③ Data Insights — interactive charts -->
      <section id="data-insights" class="section-viz">
        <div class="container">
          <p class="eyebrow">Data &amp; Research</p>
          <h2 class="viz-h2">Dyslexia by the Numbers</h2>
          <p class="section-sub">Australian data, ages 0–24. Hover to explore.</p>

          <!-- Tab buttons -->
          <div class="viz-tabs" role="tablist">
            <button
              role="tab"
              :aria-selected="chartIdx === 0"
              :class="['viz-tab', { active: chartIdx === 0 }]"
              @click="goTo(0)"
            >
              <svg width="15" height="15" viewBox="0 0 15 15" fill="none" class="tab-icon">
                <rect x="1" y="4" width="13" height="3" rx="1" fill="currentColor" opacity="0.7"/>
                <rect x="1" y="9" width="9" height="3" rx="1" fill="currentColor"/>
              </svg>
              Disability Groups by Sex
            </button>
            <button
              role="tab"
              :aria-selected="chartIdx === 1"
              :class="['viz-tab', { active: chartIdx === 1 }]"
              @click="goTo(1)"
            >
              <svg width="15" height="15" viewBox="0 0 15 15" fill="none" class="tab-icon">
                <circle cx="7.5" cy="7.5" r="6" stroke="currentColor" stroke-width="2" fill="none"/>
                <circle cx="7.5" cy="7.5" r="3" fill="currentColor" opacity="0.3"/>
              </svg>
              Psychological Development
            </button>
          </div>

          <!-- Chart panel -->
          <div class="viz-panel">
            <Transition name="chart-fade" mode="out-in">

              <!-- ─ Chart 0: Horizontal Bar Chart ─ -->
              <div v-if="chartIdx === 0" key="bar" class="chart-view">

                <!-- Sex filter toggle -->
                <div class="bar-controls">
                  <span class="ctrl-label">Show:</span>
                  <div class="toggle-group" role="group">
                    <button :class="['tog-btn', { active: sexFlt === 'both' }]" @click="sexFlt = 'both'">Both</button>
                    <button :class="['tog-btn', { active: sexFlt === 'm' }]"    @click="sexFlt = 'm'">Males</button>
                    <button :class="['tog-btn', { active: sexFlt === 'f' }]"    @click="sexFlt = 'f'">Females</button>
                  </div>
                </div>

                <!-- SVG -->
                <div class="svg-wrap">
                  <svg
                    :viewBox="`0 0 ${BAR_W} ${BAR_H_SVG}`"
                    class="chart-svg"
                    role="img"
                    aria-label="Horizontal bar chart: disability group proportions by sex, ages 0–24"
                    @mouseleave="bTip = null"
                  >
                    <!-- Grid & x-axis ticks -->
                    <g v-for="v in [0, 2, 4, 6, 8]" :key="v">
                      <line
                        :x1="ML + v * SX" :y1="MT - 6"
                        :x2="ML + v * SX" :y2="AXISY"
                        stroke="#e5e7eb" stroke-width="1"
                      />
                      <text
                        :x="ML + v * SX" :y="AXISY + 14"
                        font-size="10" fill="#9ca3af" text-anchor="middle" font-family="Inter, sans-serif"
                      >{{ v }}%</text>
                    </g>

                    <!-- Axis line -->
                    <line :x1="ML" :y1="AXISY" :x2="BAR_W - MR" :y2="AXISY" stroke="#d1d5db" stroke-width="1"/>

                    <!-- Dyslexia reference line -->
                    <line
                      :x1="DYLX" :y1="MT - 6"
                      :x2="DYLX" :y2="AXISY"
                      stroke="#ef4444" stroke-width="1.5" stroke-dasharray="5 3" opacity="0.75"
                    />
                    <text
                      :x="DYLX" :y="MT - 10"
                      font-size="9" fill="#ef4444" text-anchor="middle" font-family="Inter, sans-serif"
                    >Dyslexia 4.9%</text>

                    <!-- Legend -->
                    <rect :x="ML" y="6" width="11" height="11" rx="2" fill="#2563eb"/>
                    <text :x="ML + 14" y="16" font-size="11" fill="#374151" font-family="Inter, sans-serif">Males</text>
                    <rect :x="ML + 64" y="6" width="11" height="11" rx="2" fill="#f59e0b"/>
                    <text :x="ML + 78" y="16" font-size="11" fill="#374151" font-family="Inter, sans-serif">Females</text>

                    <!-- Bars & labels -->
                    <g v-for="(d, i) in barGroups" :key="i">
                      <!-- Male bar -->
                      <rect
                        :x="ML" :y="mY(i)"
                        :width="d.m * SX" :height="BH"
                        rx="2" fill="#2563eb"
                        :opacity="barAlpha('m')"
                        class="bar-rect"
                        @mouseenter="showTip(i, 'm', d.m)"
                        @mouseleave="bTip = null"
                      />
                      <!-- Female bar -->
                      <rect
                        :x="ML" :y="fY(i)"
                        :width="d.f * SX" :height="BH"
                        rx="2" fill="#f59e0b"
                        :opacity="barAlpha('f')"
                        class="bar-rect"
                        @mouseenter="showTip(i, 'f', d.f)"
                        @mouseleave="bTip = null"
                      />
                      <!-- Label (1 or 2 lines) -->
                      <text
                        v-if="d.lines.length === 1"
                        :x="ML - 8" :y="cY(i) + 4.5"
                        font-size="11" fill="#374151" text-anchor="end" font-family="Inter, sans-serif"
                      >{{ d.lines[0] }}</text>
                      <text v-else font-size="11" fill="#374151" text-anchor="end" font-family="Inter, sans-serif">
                        <tspan :x="ML - 8" :y="cY(i) - 5">{{ d.lines[0] }}</tspan>
                        <tspan :x="ML - 8" :y="cY(i) + 9">{{ d.lines[1] }}</tspan>
                      </text>
                    </g>

                    <!-- Tooltip -->
                    <g v-if="bTip">
                      <rect
                        :x="bTip.x" :y="bTip.y - 11"
                        width="122" height="20" rx="5"
                        fill="#1e293b" opacity="0.93"
                      />
                      <text :x="bTip.x + 9" :y="bTip.y + 3" font-size="11" fill="white" font-family="Inter, sans-serif">
                        {{ bTip.text }}
                      </text>
                    </g>
                  </svg>
                </div>

                <!-- Chart summary -->
                <div class="chart-summary">
                  <p>Boys are more likely than girls to have learning difficulties. The <strong>red line shows where dyslexia sits</strong> — at 4.9%.</p>
                  <p class="chart-source">Source: ABS SDAC 2022 · Ages 0–24</p>
                </div>
              </div>

              <!-- ─ Chart 1: Donut Chart ─ -->
              <div v-else-if="chartIdx === 1" key="donut" class="chart-view">

                <!-- SVG — full width, centred -->
                <div class="donut-svg-wrap">
                  <svg
                    viewBox="0 0 560 380"
                    class="chart-svg donut-svg"
                    role="img"
                    aria-label="Donut chart: breakdown of psychological development conditions"
                  >
                    <!-- Segments -->
                    <path
                      v-for="(s, i) in segs" :key="i"
                      :d="s.path"
                      :fill="s.color"
                      class="donut-seg"
                      @mouseenter="hovSeg = i"
                      @mouseleave="hovSeg = -1"
                    />

                    <!-- Center text (updates on hover) -->
                    <text :x="DCX" :y="DCY - 18" font-size="15" font-weight="700" fill="#0d1117" text-anchor="middle" font-family="Inter, sans-serif">{{ ctxt.top }}</text>
                    <text :x="DCX" :y="DCY + 4"  font-size="15" font-weight="700" fill="#0d1117" text-anchor="middle" font-family="Inter, sans-serif">{{ ctxt.mid }}</text>
                    <text :x="DCX" :y="DCY + 24" font-size="11" fill="#6b7280"   text-anchor="middle" font-family="Inter, sans-serif">{{ ctxt.bot }}</text>

                    <!-- Segment labels (skip tiny segments < 10°) -->
                    <g v-for="(s, i) in segs" :key="'lbl' + i">
                      <template v-if="s.sweep > 10">
                        <line :x1="s.lx1" :y1="s.ly1" :x2="s.lx" :y2="s.ly" stroke="#d1d5db" stroke-width="1.2"/>
                        <text
                          :x="s.lx + (s.anc === 'start' ? 6 : -6)" :y="s.ly + 1"
                          font-size="14" font-weight="700" :fill="s.color" :text-anchor="s.anc"
                          font-family="Inter, sans-serif"
                        >{{ s.label }}</text>
                        <text
                          :x="s.lx + (s.anc === 'start' ? 6 : -6)" :y="s.ly + 18"
                          font-size="12" fill="#6b7280" :text-anchor="s.anc"
                          font-family="Inter, sans-serif"
                        >{{ s.pct }}%</text>
                      </template>
                    </g>
                  </svg>
                </div>

                <!-- Legend — horizontal row below chart -->
                <div class="donut-legend">
                  <div
                    v-for="(s, i) in segs" :key="i"
                    :class="['leg-item', { hovered: hovSeg === i }]"
                    @mouseenter="hovSeg = i"
                    @mouseleave="hovSeg = -1"
                  >
                    <span class="leg-dot" :style="{ background: s.color }"/>
                    <div class="leg-info">
                      <div class="leg-row">
                        <span class="leg-name">{{ s.label }}</span>
                        <span class="leg-val" :style="{ color: s.color }">{{ s.v }}%</span>
                      </div>
                      <div class="leg-note">{{ s.note }}</div>
                    </div>
                  </div>
                </div>

                <!-- Chart summary -->
                <div class="chart-summary">
                  <p><strong>Dyslexia is the 2nd most common</strong> condition in this group. ASD is the most common. Hover each section to see more.</p>
                  <p class="chart-source">Source: ABS SDAC 2022 · Ages 0–24</p>
                </div>
              </div>

            </Transition>
          </div>

          <!-- Pagination navigation -->
          <div class="viz-nav">
            <button class="page-btn" @click="prevChart" :disabled="chartIdx === 0">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M10 4L6 8L10 12" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              Previous
            </button>
            <div class="page-dots">
              <button
                v-for="i in CHARTS" :key="i"
                :class="['page-dot', { active: chartIdx === i - 1 }]"
                @click="goTo(i - 1)"
                :aria-label="`Chart ${i}`"
              />
            </div>
            <button class="page-btn" @click="nextChart" :disabled="chartIdx === CHARTS - 1">
              Next
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M6 4L10 8L6 12" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </button>
          </div>

        </div>
      </section>

      <!-- ④ What is Dyslexia + Video -->
      <section id="what-is" class="section-content">
        <div class="container">
          <div class="content-block">
            <div class="content-text">
              <p class="eyebrow">What is it?</p>
              <h2>How dyslexia affects reading</h2>
              <p>
                Dyslexia affects how the brain processes the sounds that make up words —
                not vision or intelligence.
              </p>
              <p>
                It is not about seeing letters backwards. It makes decoding written text
                effortful, while verbal skills and creativity are often unaffected.
              </p>
              <p>
                In Australia, dyslexia is protected under the
                <em>Disability Discrimination Act 1992</em> — people are entitled to
                reasonable adjustments at school and work.
              </p>
            </div>
            <div class="content-aside">
              <div class="video-wrap">
                <iframe
                  src="https://www.youtube.com/embed/zafiGBrFkRM"
                  title="Understanding Dyslexia"
                  frameborder="0"
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                  allowfullscreen
                ></iframe>
              </div>
              <p class="video-caption">What it feels like to have dyslexia</p>
            </div>
          </div>
        </div>
      </section>

      <!-- ④ Signs & Symptoms -->
      <section class="section-signs">
        <div class="container">
          <p class="eyebrow">Signs &amp; Symptoms</p>
          <h2>What to look out for</h2>
          <p class="section-sub">
            Signs vary between people, but these patterns are commonly observed.
          </p>
          <div class="signs-grid">
            <div class="sign-card">
              <h3>Reading takes more effort</h3>
              <p>Reading may take longer than expected, and can feel tiring after a while.</p>
            </div>
            <div class="sign-card">
              <h3>Spelling feels inconsistent</h3>
              <p>The same word might be spelled differently across a piece of writing.</p>
            </div>
            <div class="sign-card">
              <h3>Breaking words into sounds</h3>
              <p>It can be hard to split words into sounds or blend them back together.</p>
            </div>
            <div class="sign-card">
              <h3>Difficulty holding information</h3>
              <p>It is easy to lose track of a sentence or forget a word mid-way through.</p>
            </div>
            <div class="sign-card">
              <h3>Losing your place while reading</h3>
              <p>Skipping lines or re-reading the same line is a common experience.</p>
            </div>
            <div class="sign-card">
              <h3>Feeling hesitant to read aloud</h3>
              <p>This is a natural response — not a sign of disinterest or ability.</p>
            </div>
          </div>
        </div>
      </section>

      <!-- ⑤ Mental Health Impact -->
      <section class="section-impact">
        <div class="container">
          <div class="impact-block">
            <div class="impact-text">
              <p class="eyebrow">Beyond the Page</p>
              <h2>It can affect how you feel, too</h2>
              <p>
                University students with dyslexia sometimes find academic workloads more
                draining. Feeling behind or overwhelmed is common — and understandable.
              </p>
              <p>
                Many students do not realise they have dyslexia until they are at
                university. Getting support earlier makes a real difference.
              </p>
              <p>
                With the right tools and adjustments, students with dyslexia can — and
                do — thrive at university.
              </p>
            </div>
            <div class="impact-quote">
              <blockquote>
                "Students with dyslexia are bright, creative, and highly capable.
                They just need the right support to show it."
              </blockquote>
              <p class="quote-attr">— Dyslexia Australia (ADA)</p>
            </div>
          </div>
        </div>
      </section>

      <!-- ⑥ Reading Strategies -->
      <section id="strategies" class="section-strategies">
        <div class="container">
          <p class="eyebrow">Reading Strategies</p>
          <h2>What actually helps</h2>
          <p class="section-sub">
            Simple, evidence-based techniques that make a real difference.
          </p>
          <div class="strategy-list">
            <div class="strategy-item">
              <span class="strategy-num">01</span>
              <div>
                <h3>Use dyslexia-friendly fonts</h3>
                <p>OpenDyslexic, Arial, or Verdana with wider letter spacing reduce visual crowding and make characters easier to tell apart.</p>
              </div>
            </div>
            <div class="strategy-item">
              <span class="strategy-num">02</span>
              <div>
                <h3>Listen while you read</h3>
                <p>Text-to-speech lets you focus on meaning instead of decoding. It directly targets the phonological skill that dyslexia affects.</p>
              </div>
            </div>
            <div class="strategy-item">
              <span class="strategy-num">03</span>
              <div>
                <h3>Read in short chunks</h3>
                <p>Break long text into small sections with pauses. It lowers memory pressure and helps information sink in.</p>
              </div>
            </div>
            <div class="strategy-item">
              <span class="strategy-num">04</span>
              <div>
                <h3>Try a coloured background</h3>
                <p>Pale yellow, cream, or light blue can reduce visual stress and stop text appearing to move on the page.</p>
              </div>
            </div>
            <div class="strategy-item">
              <span class="strategy-num">05</span>
              <div>
                <h3>Read the summary first</h3>
                <p>A short overview before the full text gives your brain a frame to hang details on — making the whole piece easier to follow.</p>
              </div>
            </div>
            <div class="strategy-item">
              <span class="strategy-num">06</span>
              <div>
                <h3>Highlight as you go</h3>
                <p>Marking key sentences keeps you active and gives you quick reference points to return to.</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- ⑦ CTA -->
      <section class="section-cta">
        <div class="container">
          <h2>Would you like some help?</h2>
          <p>Clearead can simplify your study materials and make them easier to work through.</p>
          <RouterLink to="/reading" class="btn-cta">
            Start Here
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M3 8H13M13 8L9 4M13 8L9 12" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </RouterLink>
        </div>
      </section>

    </main>
  </div>
</template>

<style scoped>
/* ── Page ── */
.page {
  min-height: 100vh;
  background: #fff;
  color: #0d1117;
}

/* ── Navbar ── */
.navbar {
  position: fixed;
  top: 0; left: 0; right: 0;
  z-index: 100;
  transition: background 0.3s, box-shadow 0.3s;
}
.navbar--scrolled {
  background: rgba(255, 255, 255, 0.88);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
  box-shadow: 0 1px 0 rgba(0, 0, 0, 0.06);
}
.nav-inner {
  max-width: 1160px;
  margin: 0 auto;
  padding: 0 36px;
  height: 64px;
  display: flex;
  align-items: center;
}
.nav-logo {
  display: flex; align-items: center; gap: 9px;
  font-size: 17px; font-weight: 700;
  color: #0d1117; letter-spacing: -0.4px;
  text-decoration: none; flex-shrink: 0;
}
.nav-links {
  display: flex;
  list-style: none;
  margin: 0 auto;
  padding: 0;
  gap: 2px;
}
.nav-link {
  display: block;
  padding: 6px 14px;
  font-size: 14px;
  font-weight: 500;
  color: #4b5563;
  text-decoration: none;
  border-radius: 999px;
  transition: color 0.2s, background 0.2s;
  position: relative;
}
.nav-link:hover { color: #0d1117; background: rgba(0, 0, 0, 0.04); }
.nav-link--active { color: #0d1117; }
.nav-link--active::after {
  content: '';
  position: absolute;
  bottom: -2px;
  left: 50%;
  transform: translateX(-50%);
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: #2563eb;
}

/* ── Shared layout ── */
.container {
  max-width: 1040px;
  margin: 0 auto;
  padding: 0 36px;
}
.eyebrow {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #2563eb;
  margin: 0 0 14px;
}
.section-sub {
  font-size: 16px;
  color: #6b7280;
  line-height: 1.65;
  margin: 0 0 48px;
  max-width: 620px;
}

/* ── ① Hero ── */
.section-hero {
  position: relative;
  padding: 148px 0 96px;
  background:
    radial-gradient(ellipse 60% 80% at 10% 60%, rgba(147, 167, 255, 0.35) 0%, transparent 65%),
    radial-gradient(ellipse 45% 60% at 90% 35%, rgba(199, 210, 254, 0.3) 0%, transparent 60%),
    #f8f9ff;
  border-bottom: 1px solid #e5e7eb;
  overflow: hidden;
}
.hero-bg-blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(100px);
  pointer-events: none;
}
.blob-left {
  width: 560px;
  height: 560px;
  background: rgba(99, 120, 255, 0.14);
  top: -120px;
  left: -140px;
}
.blob-right {
  width: 400px;
  height: 400px;
  background: rgba(167, 139, 250, 0.13);
  bottom: -80px;
  right: -100px;
}
.hero-container {
  position: relative;
  z-index: 1;
}
.hero-title {
  font-size: clamp(38px, 6vw, 64px);
  font-weight: 800;
  letter-spacing: -0.045em;
  line-height: 1.08;
  color: #0d1117;
  margin: 0 0 22px;
}
.text-gradient {
  background: linear-gradient(120deg, #2563eb 20%, #7c3aed 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.hero-sub {
  font-size: 17px;
  line-height: 1.72;
  color: #4b5563;
  max-width: 580px;
  margin: 0 0 36px;
}
.hero-sub-question {
  display: inline-block;
  font-size: 18px;
  font-weight: 700;
  background: linear-gradient(120deg, #2563eb 20%, #7c3aed 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.hero-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.btn-primary {
  display: inline-flex;
  align-items: center;
  padding: 12px 26px;
  background: #2563eb;
  color: #fff;
  font-size: 14.5px;
  font-weight: 600;
  border-radius: 999px;
  text-decoration: none;
  box-shadow: 0 6px 20px rgba(37, 99, 235, 0.3);
  transition: background 0.2s, transform 0.15s;
}
.btn-primary:hover { background: #1d4ed8; transform: translateY(-2px); }
.btn-ghost {
  display: inline-flex;
  align-items: center;
  padding: 12px 24px;
  background: rgba(255, 255, 255, 0.75);
  color: #374151;
  font-size: 14.5px;
  font-weight: 600;
  border-radius: 999px;
  border: 1px solid rgba(0, 0, 0, 0.1);
  text-decoration: none;
  backdrop-filter: blur(10px);
  transition: background 0.2s, transform 0.15s;
}
.btn-ghost:hover { background: #fff; transform: translateY(-2px); box-shadow: 0 6px 18px rgba(0,0,0,0.08); }

/* ── ② Stats ── */
.section-stats {
  padding: 72px 0;
  border-bottom: 1px solid #e5e7eb;
}
.stats-row {
  display: flex;
  align-items: flex-start;
}
.stat-item {
  flex: 1;
  padding: 0 40px;
}
.stat-item:first-child { padding-left: 0; }
.stat-item:last-child  { padding-right: 0; }
.stat-num {
  display: block;
  font-size: 46px;
  font-weight: 800;
  letter-spacing: -0.05em;
  color: #2563eb;
  margin-bottom: 10px;
  line-height: 1;
}
.stat-label {
  font-size: 14px;
  color: #6b7280;
  line-height: 1.55;
  margin: 0;
}
.stat-divider {
  width: 1px;
  background: #e5e7eb;
  align-self: stretch;
  flex-shrink: 0;
}

/* ── ③ Content block ── */
.section-content {
  padding: 88px 0;
  border-bottom: 1px solid #e5e7eb;
}
.content-block {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 72px;
  align-items: start;
}
.content-text h2 {
  font-size: clamp(26px, 3vw, 38px);
  font-weight: 800;
  letter-spacing: -0.03em;
  margin: 0 0 22px;
  line-height: 1.2;
}
.content-text p {
  font-size: 16px;
  line-height: 1.78;
  color: #4b5563;
  margin: 0 0 16px;
}
.content-text p:last-child { margin-bottom: 0; }
.content-aside {
  position: sticky;
  top: 88px;
}
.video-wrap {
  width: 100%;
  aspect-ratio: 16 / 9;
  border-radius: 14px;
  overflow: hidden;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.12), 0 4px 12px rgba(0, 0, 0, 0.06);
}
.video-wrap iframe {
  width: 100%;
  height: 100%;
  display: block;
}
.video-caption {
  margin: 12px 0 0;
  font-size: 13px;
  color: #9ca3af;
  text-align: center;
}

/* ── ④ Signs ── */
.section-signs {
  padding: 88px 0;
  background: #fafbff;
  border-bottom: 1px solid #e5e7eb;
}
.section-signs h2 {
  font-size: clamp(26px, 3vw, 38px);
  font-weight: 800;
  letter-spacing: -0.03em;
  margin: 0 0 12px;
}
.signs-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-top: 48px;
}
.sign-card {
  padding: 28px;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  background: #fff;
  transition: box-shadow 0.2s, transform 0.2s;
}
.sign-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.07);
}
.sign-card h3 {
  font-size: 15px;
  font-weight: 700;
  margin: 0 0 10px;
  letter-spacing: -0.02em;
  color: #0d1117;
}
.sign-card p {
  font-size: 14px;
  color: #6b7280;
  line-height: 1.65;
  margin: 0;
}

/* ── ⑤ Impact ── */
.section-impact {
  padding: 88px 0;
  border-bottom: 1px solid #e5e7eb;
}
.impact-block {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 72px;
  align-items: center;
}
.impact-text h2 {
  font-size: clamp(26px, 3vw, 38px);
  font-weight: 800;
  letter-spacing: -0.03em;
  margin: 0 0 22px;
  line-height: 1.2;
}
.impact-text p {
  font-size: 16px;
  line-height: 1.78;
  color: #4b5563;
  margin: 0 0 16px;
}
.impact-text p:last-child { margin-bottom: 0; }
.impact-text strong { color: #0d1117; font-weight: 700; }
.impact-quote {
  background: linear-gradient(145deg, #eef2ff, #f5f3ff);
  border-left: 3px solid #2563eb;
  border-radius: 14px;
  padding: 36px 32px;
}
blockquote {
  margin: 0 0 16px;
  font-size: 17px;
  line-height: 1.7;
  color: #1e3a8a;
  font-weight: 500;
  font-style: italic;
}
.quote-attr {
  font-size: 13px;
  color: #6b7280;
  margin: 0;
  font-style: normal;
}

/* ── ⑥ Strategies ── */
.section-strategies {
  padding: 88px 0;
  border-bottom: 1px solid #e5e7eb;
}
.section-strategies h2 {
  font-size: clamp(26px, 3vw, 38px);
  font-weight: 800;
  letter-spacing: -0.03em;
  margin: 0 0 12px;
}
.strategy-list {
  margin-top: 48px;
  display: flex;
  flex-direction: column;
}
.strategy-item {
  display: flex;
  gap: 32px;
  align-items: flex-start;
  padding: 28px 0;
  border-bottom: 1px solid #e5e7eb;
}
.strategy-item:first-child { border-top: 1px solid #e5e7eb; }
.strategy-num {
  font-size: 12px;
  font-weight: 700;
  color: #2563eb;
  letter-spacing: 0.08em;
  flex-shrink: 0;
  padding-top: 4px;
  width: 28px;
  text-transform: uppercase;
}
.strategy-item h3 {
  font-size: 16px;
  font-weight: 700;
  margin: 0 0 8px;
  letter-spacing: -0.02em;
  color: #0d1117;
}
.strategy-item p {
  font-size: 14.5px;
  color: #6b7280;
  line-height: 1.68;
  margin: 0;
}

/* ── ⑦ CTA ── */
.section-cta {
  padding: 96px 0;
  background: linear-gradient(135deg, #1e3a8a 0%, #312e81 100%);
  text-align: center;
}
.section-cta h2 {
  font-size: clamp(28px, 4vw, 44px);
  font-weight: 800;
  color: #fff;
  letter-spacing: -0.04em;
  margin: 0 0 14px;
}
.section-cta p {
  font-size: 16px;
  color: rgba(255, 255, 255, 0.65);
  margin: 0 0 36px;
}
.btn-cta {
  display: inline-flex;
  align-items: center;
  padding: 14px 32px;
  background: #fff;
  color: #2563eb;
  font-size: 15px;
  font-weight: 700;
  border-radius: 999px;
  text-decoration: none;
  box-shadow: 0 8px 28px rgba(0, 0, 0, 0.2);
  transition: background 0.2s, transform 0.15s;
}
.btn-cta:hover { background: #eef2ff; transform: translateY(-2px); }

/* ── ③ Data Viz ───────────────────────────────────────────────────────── */
.section-viz {
  padding: 88px 0;
  background: #fafbff;
  border-bottom: 1px solid #e5e7eb;
}
.viz-h2 { font-size: clamp(26px, 3vw, 38px); font-weight: 800; letter-spacing: -0.03em; margin: 0 0 12px; line-height: 1.2; }

/* Tabs */
.viz-tabs {
  display: flex; gap: 6px; margin-bottom: 0;
  border-bottom: 2px solid #e5e7eb;
}
.viz-tab {
  display: inline-flex; align-items: center; gap: 7px;
  padding: 10px 20px; font-size: 14px; font-weight: 600;
  color: #6b7280; background: none; border: none; border-radius: 8px 8px 0 0;
  cursor: pointer; transition: color 0.2s, background 0.2s;
  position: relative; bottom: -2px;
  border-bottom: 2px solid transparent;
}
.viz-tab:hover { color: #374151; background: rgba(0,0,0,0.03); }
.viz-tab.active {
  color: #2563eb; background: #fff;
  border-bottom-color: #2563eb;
  box-shadow: 0 -2px 8px rgba(37,99,235,0.08);
}
.tab-icon { flex-shrink: 0; }

/* Panel */
.viz-panel {
  background: #fff;
  border-radius: 0 16px 16px 16px;
  border: 1px solid #e5e7eb;
  box-shadow: 0 4px 24px rgba(0,0,0,0.05);
  padding: 32px 32px 28px;
  min-height: 380px;
}

/* Transition */
.chart-fade-enter-active,
.chart-fade-leave-active { transition: opacity 0.22s ease, transform 0.22s ease; }
.chart-fade-enter-from { opacity: 0; transform: translateY(10px); }
.chart-fade-leave-to  { opacity: 0; transform: translateY(-6px); }

/* Bar controls */
.bar-controls { display: flex; align-items: center; gap: 10px; margin-bottom: 16px; }
.ctrl-label { font-size: 13px; color: #6b7280; font-weight: 500; }
.toggle-group { display: flex; background: #f3f4f6; border-radius: 999px; padding: 3px; gap: 2px; }
.tog-btn {
  padding: 4px 14px; font-size: 13px; font-weight: 500;
  border: none; border-radius: 999px; cursor: pointer;
  color: #6b7280; background: transparent;
  transition: background 0.15s, color 0.15s;
}
.tog-btn.active { background: #fff; color: #2563eb; font-weight: 600; box-shadow: 0 1px 4px rgba(0,0,0,0.1); }

/* SVG */
.svg-wrap { width: 100%; overflow: hidden; }
.chart-svg { width: 100%; height: auto; display: block; }
.bar-rect { transition: opacity 0.2s; cursor: pointer; }
.bar-rect:hover { filter: brightness(1.1); }

/* Donut — full-width centred SVG, legend row below */
.donut-svg-wrap { max-width: 520px; margin: 0 auto; }
.donut-svg { width: 100%; height: auto; }
.donut-seg { cursor: pointer; transition: filter 0.15s; }
.donut-seg:hover { filter: brightness(1.08); }

/* Legend — horizontal row */
.donut-legend { display: flex; gap: 12px; justify-content: center; flex-wrap: wrap; margin-top: 4px; }
.leg-item {
  display: flex; gap: 10px; align-items: center;
  padding: 10px 16px; border-radius: 10px;
  border: 1px solid transparent; cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}
.leg-item:hover,
.leg-item.hovered { background: #f8faff; border-color: #dbeafe; }
.leg-dot { width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0; }
.leg-info { }
.leg-row { display: flex; align-items: baseline; gap: 6px; }
.leg-name { font-size: 14px; font-weight: 700; color: #0d1117; }
.leg-val  { font-size: 13px; font-weight: 700; }
.leg-note { font-size: 12px; color: #9ca3af; margin-top: 2px; }

/* Chart summary */
.chart-summary {
  margin-top: 24px; padding-top: 20px;
  border-top: 1px solid #f3f4f6;
}
.chart-summary p { font-size: 14.5px; line-height: 1.7; color: #4b5563; margin: 0 0 8px; }
.chart-summary p:last-child { margin-bottom: 0; }
.chart-summary strong { color: #0d1117; font-weight: 700; }
.chart-source { font-size: 12px; color: #9ca3af; }

/* Pagination */
.viz-nav { display: flex; align-items: center; justify-content: center; gap: 24px; margin-top: 28px; }
.page-btn {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 8px 18px; font-size: 14px; font-weight: 600;
  color: #374151; background: #fff; border: 1px solid #e5e7eb;
  border-radius: 999px; cursor: pointer;
  transition: background 0.15s, color 0.15s, box-shadow 0.15s;
}
.page-btn:hover:not(:disabled) {
  background: #f8faff; color: #2563eb; border-color: #bfdbfe;
  box-shadow: 0 2px 8px rgba(37,99,235,0.1);
}
.page-btn:disabled { opacity: 0.35; cursor: not-allowed; }
.page-dots { display: flex; gap: 8px; align-items: center; }
.page-dot {
  width: 10px; height: 10px; border-radius: 50%;
  background: #d1d5db; border: none; cursor: pointer;
  transition: background 0.2s, transform 0.2s; padding: 0;
}
.page-dot.active { background: #2563eb; transform: scale(1.25); }
.page-dot:hover:not(.active) { background: #93c5fd; }

/* ── Hamburger ── */
.nav-hamburger {
  display: none;
  background: none; border: none; cursor: pointer;
  color: #0d1117; padding: 4px; margin-left: 12px;
  align-items: center; justify-content: center;
}

/* ── Mobile nav drawer ── */
.mobile-nav { display: none; }

/* ── Responsive ── */
@media (max-width: 1024px) {
  .signs-grid { grid-template-columns: repeat(2, 1fr); }
  .content-block,
  .impact-block { grid-template-columns: 1fr; gap: 40px; }
  .content-aside { position: static; }
  .donut-svg-wrap { max-width: 380px; }
}
@media (max-width: 768px) {
  .nav-links { display: none; }
  .nav-hamburger { display: flex; }

  .mobile-nav {
    display: block;
    position: fixed;
    top: 64px; left: 0; right: 0;
    background: rgba(255,255,255,0.98);
    backdrop-filter: blur(18px);
    -webkit-backdrop-filter: blur(18px);
    border-bottom: 1px solid #e5e7eb;
    z-index: 99;
  }
  .mobile-nav-links { list-style: none; margin: 0; padding: 0; }
  .mobile-nav-link {
    display: block; padding: 16px 28px;
    font-size: 16px; font-weight: 500; color: #374151;
    text-decoration: none;
    border-bottom: 1px solid #f3f4f6;
    transition: background 0.15s;
  }
  .mobile-nav-link:hover { background: #f9fafb; color: #0d1117; }

  .stats-row { flex-direction: column; gap: 36px; }
  .stat-divider { display: none; }
  .stat-item { padding: 0; }
  .signs-grid { grid-template-columns: 1fr; }
  .section-hero { padding: 110px 0 72px; }
  .container { padding: 0 20px; }
  .section-content, .section-signs, .section-impact,
  .section-strategies, .section-cta { padding: 64px 0; }
  .section-stats, .section-viz { padding: 48px 0; }
  .viz-panel { padding: 20px 16px; }
  .viz-tabs { gap: 4px; }
  .viz-tab { padding: 8px 12px; font-size: 13px; }
  .page-btn { padding: 7px 14px; font-size: 13px; }
  .bar-controls { flex-wrap: wrap; }
  .viz-nav { gap: 16px; }
}
</style>
