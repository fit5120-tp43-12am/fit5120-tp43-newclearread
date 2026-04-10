<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const scrolled = ref(false)
function onScroll() { scrolled.value = window.scrollY > 10 }
onMounted(() => window.addEventListener('scroll', onScroll))
onUnmounted(() => window.removeEventListener('scroll', onScroll))
</script>

<template>
  <div class="page">

    <!-- Navbar -->
    <nav :class="['navbar', { 'navbar--scrolled': scrolled }]">
      <div class="nav-inner">
        <a href="/" class="nav-logo">ClearRead</a>
        <ul class="nav-links">
          <li><a href="/" class="nav-link">Home</a></li>
          <li><a href="#" class="nav-link">Reading</a></li>
          <li><a href="/dyslexia" class="nav-link nav-link--active">Dyslexia</a></li>
          <li><a href="#" class="nav-link">About</a></li>
        </ul>
        <a href="#" class="btn-nav">Get Started</a>
      </div>
    </nav>

    <main>

      <!-- ① Hero -->
      <section class="section-hero">
        <div class="container">
          <p class="eyebrow">Understanding Dyslexia</p>
          <h1 class="hero-title">
            Dyslexia is a difference,<br/>not a deficit.
          </h1>
          <p class="hero-sub">
            Around 1 in 5 people have dyslexia. It affects how the brain processes
            written language — not intelligence. Here's what the research actually says.
          </p>
        </div>
      </section>

      <!-- ② Key Stats — placeholder numbers, you'll replace -->
      <section class="section-stats">
        <div class="container">
          <div class="stats-row">
            <div class="stat-item">
              <span class="stat-num">—%</span>
              <p class="stat-label">Placeholder stat label. Replace with real data.</p>
            </div>
            <div class="stat-divider"></div>
            <div class="stat-item">
              <span class="stat-num">—%</span>
              <p class="stat-label">Placeholder stat label. Replace with real data.</p>
            </div>
            <div class="stat-divider"></div>
            <div class="stat-item">
              <span class="stat-num">1 in —</span>
              <p class="stat-label">Placeholder stat label. Replace with real data.</p>
            </div>
            <div class="stat-divider"></div>
            <div class="stat-item">
              <span class="stat-num">—%</span>
              <p class="stat-label">Placeholder stat label. Replace with real data.</p>
            </div>
          </div>
        </div>
      </section>

      <!-- ③ What is Dyslexia -->
      <section class="section-content">
        <div class="container">
          <div class="content-block">
            <div class="content-text">
              <p class="eyebrow">What is it?</p>
              <h2>How dyslexia affects reading</h2>
              <p>
                Placeholder — add your paragraph here about what dyslexia is,
                how it works neurologically, and what it means for day-to-day reading.
              </p>
              <p>
                Placeholder — second paragraph. Can include common misconceptions,
                e.g. it is not about seeing letters backwards.
              </p>
            </div>
            <div class="content-aside">
              <!-- Video placeholder -->
              <div class="video-placeholder">
                <p class="video-placeholder__label">Video goes here</p>
                <p class="video-placeholder__sub">Drop in the embed URL when ready</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- ④ Signs & Symptoms -->
      <section class="section-list section-list--alt">
        <div class="container">
          <p class="eyebrow">Signs &amp; Symptoms</p>
          <h2>What to look out for</h2>
          <div class="list-grid">
            <div class="list-card">
              <h3>Placeholder heading</h3>
              <p>Replace with a real sign or symptom of dyslexia. Keep it concise — 1–2 sentences.</p>
            </div>
            <div class="list-card">
              <h3>Placeholder heading</h3>
              <p>Replace with a real sign or symptom of dyslexia. Keep it concise — 1–2 sentences.</p>
            </div>
            <div class="list-card">
              <h3>Placeholder heading</h3>
              <p>Replace with a real sign or symptom of dyslexia. Keep it concise — 1–2 sentences.</p>
            </div>
            <div class="list-card">
              <h3>Placeholder heading</h3>
              <p>Replace with a real sign or symptom of dyslexia. Keep it concise — 1–2 sentences.</p>
            </div>
            <div class="list-card">
              <h3>Placeholder heading</h3>
              <p>Replace with a real sign or symptom of dyslexia. Keep it concise — 1–2 sentences.</p>
            </div>
            <div class="list-card">
              <h3>Placeholder heading</h3>
              <p>Replace with a real sign or symptom of dyslexia. Keep it concise — 1–2 sentences.</p>
            </div>
          </div>
        </div>
      </section>

      <!-- ⑤ Video Section — second video placeholder -->
      <section class="section-video">
        <div class="container">
          <p class="eyebrow">Watch &amp; Learn</p>
          <h2>Placeholder video section title</h2>
          <p class="section-sub">
            Short description about what the video covers. Replace this text when you have the video link.
          </p>
          <div class="video-placeholder video-placeholder--large">
            <p class="video-placeholder__label">Video goes here</p>
            <p class="video-placeholder__sub">Drop in the embed URL when ready</p>
          </div>
        </div>
      </section>

      <!-- ⑥ Reading Strategies -->
      <section class="section-list">
        <div class="container">
          <p class="eyebrow">Reading Strategies</p>
          <h2>What actually helps</h2>
          <p class="section-sub">
            Placeholder — brief intro sentence about why these strategies matter.
          </p>
          <div class="strategy-list">
            <div class="strategy-item">
              <span class="strategy-num">01</span>
              <div>
                <h3>Placeholder strategy title</h3>
                <p>Replace with a practical, evidence-based reading tip for dyslexic students.</p>
              </div>
            </div>
            <div class="strategy-item">
              <span class="strategy-num">02</span>
              <div>
                <h3>Placeholder strategy title</h3>
                <p>Replace with a practical, evidence-based reading tip for dyslexic students.</p>
              </div>
            </div>
            <div class="strategy-item">
              <span class="strategy-num">03</span>
              <div>
                <h3>Placeholder strategy title</h3>
                <p>Replace with a practical, evidence-based reading tip for dyslexic students.</p>
              </div>
            </div>
            <div class="strategy-item">
              <span class="strategy-num">04</span>
              <div>
                <h3>Placeholder strategy title</h3>
                <p>Replace with a practical, evidence-based reading tip for dyslexic students.</p>
              </div>
            </div>
            <div class="strategy-item">
              <span class="strategy-num">05</span>
              <div>
                <h3>Placeholder strategy title</h3>
                <p>Replace with a practical, evidence-based reading tip for dyslexic students.</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- ⑦ CTA -->
      <section class="section-cta">
        <div class="container">
          <h2>Ready to read more comfortably?</h2>
          <p>Try ClearRead's reading tool — built for minds that think differently.</p>
          <a href="#" class="btn-cta">Start Reading</a>
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

/* ── Navbar (same as Home) ── */
.navbar {
  position: fixed;
  top: 0; left: 0; right: 0;
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
  max-width: 1160px;
  margin: 0 auto;
  padding: 0 36px;
  height: 64px;
  display: flex;
  align-items: center;
}
.nav-logo {
  font-size: 17px;
  font-weight: 700;
  color: #0d1117;
  letter-spacing: -0.4px;
  text-decoration: none;
  flex-shrink: 0;
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
.nav-link:hover { color: #0d1117; background: rgba(0,0,0,0.04); }
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
.btn-nav {
  display: inline-flex;
  align-items: center;
  padding: 8px 18px;
  background: #2563eb;
  color: #fff;
  font-size: 13.5px;
  font-weight: 600;
  border-radius: 999px;
  text-decoration: none;
  flex-shrink: 0;
  box-shadow: 0 4px 14px rgba(37,99,235,0.28);
  transition: background 0.2s, transform 0.15s;
}
.btn-nav:hover { background: #1d4ed8; transform: translateY(-1px); }

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

/* ── ① Hero ── */
.section-hero {
  padding: 140px 0 80px;
  background: linear-gradient(160deg, #eef2ff 0%, #f5f3ff 40%, #fafbff 100%);
  border-bottom: 1px solid #e5e7eb;
}
.hero-title {
  font-size: clamp(36px, 6vw, 60px);
  font-weight: 800;
  letter-spacing: -0.04em;
  line-height: 1.1;
  margin: 0 0 20px;
  color: #0d1117;
}
.hero-sub {
  font-size: 17px;
  line-height: 1.72;
  color: #4b5563;
  max-width: 560px;
  margin: 0;
}

/* ── ② Stats ── */
.section-stats {
  padding: 64px 0;
  border-bottom: 1px solid #e5e7eb;
}
.stats-row {
  display: flex;
  align-items: flex-start;
  gap: 0;
}
.stat-item {
  flex: 1;
  padding: 0 40px;
}
.stat-item:first-child { padding-left: 0; }
.stat-item:last-child  { padding-right: 0; }
.stat-num {
  display: block;
  font-size: 48px;
  font-weight: 800;
  letter-spacing: -0.05em;
  color: #2563eb;
  margin-bottom: 10px;
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
  padding: 80px 0;
  border-bottom: 1px solid #e5e7eb;
}
.content-block {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 64px;
  align-items: center;
}
.content-text h2 {
  font-size: clamp(24px, 3vw, 36px);
  font-weight: 800;
  letter-spacing: -0.03em;
  margin: 0 0 20px;
}
.content-text p {
  font-size: 16px;
  line-height: 1.75;
  color: #4b5563;
  margin: 0 0 14px;
}

/* ── Video placeholder ── */
.video-placeholder {
  width: 100%;
  aspect-ratio: 16 / 9;
  background: #f3f4f6;
  border: 2px dashed #d1d5db;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
}
.video-placeholder--large {
  max-width: 720px;
  margin: 32px auto 0;
}
.video-placeholder__label {
  font-size: 15px;
  font-weight: 600;
  color: #9ca3af;
  margin: 0;
}
.video-placeholder__sub {
  font-size: 13px;
  color: #d1d5db;
  margin: 0;
}

/* ── ④ List grid ── */
.section-list {
  padding: 80px 0;
  border-bottom: 1px solid #e5e7eb;
}
.section-list--alt {
  background: #fafbff;
}
.section-list h2 {
  font-size: clamp(24px, 3vw, 36px);
  font-weight: 800;
  letter-spacing: -0.03em;
  margin: 0 0 36px;
}
.list-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}
.list-card {
  padding: 24px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #fff;
  transition: box-shadow 0.2s, transform 0.2s;
}
.list-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 24px rgba(0,0,0,0.07);
}
.list-card h3 {
  font-size: 15px;
  font-weight: 700;
  margin: 0 0 8px;
  letter-spacing: -0.02em;
}
.list-card p {
  font-size: 14px;
  color: #6b7280;
  line-height: 1.6;
  margin: 0;
}

/* ── ⑤ Video section ── */
.section-video {
  padding: 80px 0;
  border-bottom: 1px solid #e5e7eb;
}
.section-video h2 {
  font-size: clamp(24px, 3vw, 36px);
  font-weight: 800;
  letter-spacing: -0.03em;
  margin: 0 0 12px;
}
.section-sub {
  font-size: 16px;
  color: #6b7280;
  line-height: 1.65;
  margin: 0;
}

/* ── ⑥ Strategy list ── */
.section-list h2 { margin-bottom: 12px; }
.strategy-list {
  margin-top: 36px;
  display: flex;
  flex-direction: column;
  gap: 0;
}
.strategy-item {
  display: flex;
  gap: 28px;
  align-items: flex-start;
  padding: 24px 0;
  border-bottom: 1px solid #e5e7eb;
}
.strategy-item:first-child { border-top: 1px solid #e5e7eb; }
.strategy-num {
  font-size: 13px;
  font-weight: 700;
  color: #2563eb;
  letter-spacing: 0.05em;
  flex-shrink: 0;
  padding-top: 3px;
  width: 28px;
}
.strategy-item h3 {
  font-size: 16px;
  font-weight: 700;
  margin: 0 0 6px;
  letter-spacing: -0.02em;
}
.strategy-item p {
  font-size: 14.5px;
  color: #6b7280;
  line-height: 1.65;
  margin: 0;
}

/* ── ⑦ CTA ── */
.section-cta {
  padding: 80px 0;
  background: linear-gradient(135deg, #1e3a8a 0%, #312e81 100%);
  text-align: center;
}
.section-cta h2 {
  font-size: clamp(26px, 4vw, 42px);
  font-weight: 800;
  color: #fff;
  letter-spacing: -0.04em;
  margin: 0 0 12px;
}
.section-cta p {
  font-size: 16px;
  color: rgba(255,255,255,0.68);
  margin: 0 0 32px;
}
.btn-cta {
  display: inline-flex;
  align-items: center;
  padding: 13px 30px;
  background: #fff;
  color: #2563eb;
  font-size: 15px;
  font-weight: 600;
  border-radius: 999px;
  text-decoration: none;
  transition: background 0.2s, transform 0.15s;
  box-shadow: 0 8px 24px rgba(0,0,0,0.18);
}
.btn-cta:hover {
  background: #f0f4ff;
  transform: translateY(-2px);
}

/* ── Responsive ── */
@media (max-width: 1024px) {
  .list-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 768px) {
  .stats-row { flex-direction: column; gap: 32px; }
  .stat-divider { display: none; }
  .stat-item { padding: 0; }
  .content-block { grid-template-columns: 1fr; gap: 36px; }
  .list-grid { grid-template-columns: 1fr; }
  .nav-links, .btn-nav { display: none; }
}
</style>
