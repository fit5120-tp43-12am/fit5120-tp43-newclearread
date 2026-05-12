<script setup>
// ── HomePage.vue ──────────────────────────────────────────────────────────────
// The landing page. Shows the hero section, feature overview, training game promo,
// how-it-works steps, a CTA banner, and the footer.
// The script only handles two UI behaviours: navbar scroll shadow and mobile menu toggle.
import { ref, onMounted, onUnmounted } from 'vue'

// scrolled drives the .navbar--scrolled CSS class.
// The navbar starts transparent; once the user scrolls 10px it becomes frosted-glass.
const scrolled  = ref(false)
// menuOpen controls whether the mobile slide-down nav drawer is visible.
const menuOpen  = ref(false)

// Simple scroll handler — called ~60× per second during scrolling.
function onScroll() { scrolled.value = window.scrollY > 10 }

// onMounted / onUnmounted are Vue lifecycle hooks.
// We attach the scroll listener after the component is in the DOM, and REMOVE it when
// the user navigates away — failing to remove it would cause a memory leak because the
// callback would keep running on a component that no longer exists.
onMounted(() => window.addEventListener('scroll', onScroll))
onUnmounted(() => window.removeEventListener('scroll', onScroll))
</script>

<template>
  <div class="page">

    <!-- ── Navbar ── -->
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
          <li><RouterLink to="/"         class="nav-link nav-link--active">Home</RouterLink></li>
          <li><RouterLink to="/reading"  class="nav-link">Reading Support</RouterLink></li>
          <li><RouterLink to="/dyslexia" class="nav-link">Understand Dyslexia</RouterLink></li>
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

    <!-- ── Hero ── -->
    <section class="hero">
      <div class="blob blob--blue"></div>
      <div class="blob blob--peach"></div>

      <div class="hero-content">
        <div class="badge">
          For university students with dyslexia · Australia
        </div>
        <h1 class="hero-title">
          Study Smarter.<br/>
          Read with <span class="highlight">Confidence.</span>
        </h1>
        <p class="hero-sub">
          Hard to get through your study materials?<br/>
          Clearead makes them shorter, simpler, and easier to follow.
        </p>
        <div class="hero-actions">
          <RouterLink to="/reading" class="btn-start">
            Start Here
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M3 8H13M13 8L9 4M13 8L9 12" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </RouterLink>
          <RouterLink to="/dyslexia" class="btn-ghost">
            Learn About Dyslexia
          </RouterLink>
          <RouterLink to="/training" class="btn-ghost">
            Try Training Game
          </RouterLink>
        </div>
      </div>
    </section>

    <!-- ── Features ── -->
    <section class="section-features">
      <div class="container">
        <p class="eyebrow">What Clearead does</p>
        <h2 class="section-title">Three ways Clearead helps</h2>

        <div class="features-grid">
          <div class="feature-card">
            <div class="feature-num">01</div>
            <h3>Simplify Text</h3>
            <p>Paste your text. Get a simpler version, key points, and a short summary.</p>
          </div>
          <div class="feature-card">
            <div class="feature-num">02</div>
            <h3>Listen Along</h3>
            <p>Listen to your text read aloud. Choose a speed that feels right for you.</p>
          </div>
          <div class="feature-card">
            <div class="feature-num">03</div>
            <h3>Adjust the Display</h3>
            <p>Change font size, spacing, and background colour. Find what works for you.</p>
          </div>
        </div>

        <div class="features-cta">
          <RouterLink to="/reading" class="btn-features-start">
            Start Here
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M3 8H13M13 8L9 4M13 8L9 12" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </RouterLink>
        </div>
      </div>
    </section>

    <!-- ── Training game promo ── -->
    <section class="section-training">
      <div class="container">
      <div class="training-panel">
      <div class="training-inner">
        <!-- Left: text content -->
        <div class="training-text">
          <p class="eyebrow">New — Reading Training</p>
          <h2 class="section-title">Build reading skills with Focus Reader</h2>
          <p class="training-desc">
            A short, game-based exercise that trains you to tell apart easily confused
            letters and sounds — like b/d/p/q and sh/ch/th. Tap the right moving chip
            before time runs out. Difficulty adapts to your pace.
          </p>
          <ul class="training-bullets">
            <li>
              <span class="bullet-icon" aria-hidden="true">
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                  <circle cx="7" cy="7" r="6" fill="#eef2ff"/>
                  <path d="M4 7l2 2 4-4" stroke="#2563eb" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </span>
              Confusable letters, phoneme chunks, and short words
            </li>
            <li>
              <span class="bullet-icon" aria-hidden="true">
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                  <circle cx="7" cy="7" r="6" fill="#eef2ff"/>
                  <path d="M4 7l2 2 4-4" stroke="#2563eb" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </span>
              Visual and audio cues — trains both reading pathways
            </li>
            <li>
              <span class="bullet-icon" aria-hidden="true">
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                  <circle cx="7" cy="7" r="6" fill="#eef2ff"/>
                  <path d="M4 7l2 2 4-4" stroke="#2563eb" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </span>
              Adapts difficulty automatically as you improve
            </li>
          </ul>
          <RouterLink to="/training" class="btn-training">
            Try Focus Reader
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M3 8H13M13 8L9 4M13 8L9 12" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </RouterLink>
        </div>
        <!-- Right: visual preview of the game chips -->
        <div class="training-visual" aria-hidden="true">
          <div class="chip-preview">
            <div class="chip chip--target">b</div>
            <div class="chip chip--distractor chip--blue">d</div>
            <div class="chip chip--distractor chip--rose">p</div>
            <div class="chip chip--distractor chip--yellow">q</div>
            <div class="chip chip--distractor chip--plain">sh</div>
            <div class="chip chip--distractor chip--blue">ch</div>
          </div>
          <p class="preview-caption">Tap the chip that matches the cue</p>
        </div>
      </div><!-- training-inner -->
      </div><!-- training-panel -->
      </div><!-- container -->
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
          <RouterLink to="/dyslexia" class="footer-link">Understand Dyslexia</RouterLink>
        </nav>
        <p class="footer-copy">© 2026 Clearead. All rights reserved.</p>
      </div>
    </footer>

  </div>
</template>

<style scoped>
/* ═══════════════════════════════════════════════════════
   PAGE — seamless gradient canvas, no fixed attachment
   Use a tall linear base + radial blobs so there is NO
   hard edge anywhere as the user scrolls.
   ═══════════════════════════════════════════════════════ */
.page {
  min-height: 100vh;
  background:
    /* top-left lavender */
    radial-gradient(ellipse 80% 40% at 0%   0%,   rgba(147,167,255,0.50) 0%, transparent 55%),
    /* top-right peach */
    radial-gradient(ellipse 70% 35% at 100% 0%,   rgba(255,200,150,0.42) 0%, transparent 52%),
    /* mid-left soft violet */
    radial-gradient(ellipse 60% 30% at 0%   50%,  rgba(147,167,255,0.25) 0%, transparent 55%),
    /* mid-right warm peach */
    radial-gradient(ellipse 55% 28% at 100% 50%,  rgba(255,218,180,0.28) 0%, transparent 52%),
    /* bottom-left lavender */
    radial-gradient(ellipse 65% 30% at 0%   100%, rgba(147,167,255,0.30) 0%, transparent 55%),
    /* bottom-right peach */
    radial-gradient(ellipse 60% 28% at 100% 100%, rgba(255,200,150,0.30) 0%, transparent 52%),
    /* base */
    #f4f5ff;
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
  background: rgba(244,245,255,0.82);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  box-shadow: 0 1px 0 rgba(99,120,255,0.1);
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
  content: '';
  position: absolute;
  bottom: -2px; left: 50%; transform: translateX(-50%);
  width: 4px; height: 4px;
  border-radius: 50%; background: #2563eb;
}

/* ── Hero — transparent so page gradient shows ── */
.hero {
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  overflow: hidden;
}
/* subtle animated blobs add depth without blocking the fixed gradient */
.blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(100px);
  pointer-events: none;
  z-index: 0;
}
.blob--blue  { width: 500px; height: 500px; background: rgba(99,120,255,0.14); top: -80px; left: -100px; }
.blob--peach { width: 400px; height: 400px; background: rgba(255,165,100,0.12); bottom: -80px; right: -80px; }

.hero-content {
  position: relative;
  z-index: 1;
  text-align: center;
  padding: 0 24px;
  max-width: 700px;
}
.badge {
  display: inline-flex; align-items: center; gap: 7px;
  padding: 6px 16px;
  background: rgba(255,255,255,0.65);
  border: 1px solid rgba(79,110,247,0.18);
  border-radius: 999px;
  font-size: 13px; font-weight: 500; color: #374151;
  margin-bottom: 28px;
  backdrop-filter: blur(12px);
  box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}
.hero-title {
  font-size: clamp(44px, 7.5vw, 72px);
  font-weight: 800; letter-spacing: -0.045em;
  line-height: 1.08; color: #0d1117;
  margin-bottom: 22px;
}
.highlight {
  background: linear-gradient(120deg, #2563eb 20%, #5b8af5 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.hero-sub {
  font-size: 16px; line-height: 1.72;
  color: #4b5563; margin-bottom: 38px;
}
.hero-actions {
  display: flex; align-items: center;
  justify-content: center; gap: 14px; flex-wrap: wrap;
}
.btn-start {
  display: inline-flex; align-items: center; gap: 9px;
  padding: 13px 26px;
  background: #2563eb; color: #fff;
  font-size: 15px; font-weight: 600;
  border-radius: 999px; text-decoration: none;
  box-shadow: 0 6px 20px rgba(37,99,235,0.3);
  transition: background 0.2s, transform 0.15s, box-shadow 0.2s;
}
.btn-start:hover { background: #1d4ed8; transform: translateY(-2px); box-shadow: 0 12px 28px rgba(37,99,235,0.35); }
.btn-ghost {
  display: inline-flex; align-items: center; gap: 9px;
  padding: 13px 24px;
  background: rgba(255,255,255,0.65); color: #374151;
  font-size: 15px; font-weight: 600;
  border-radius: 999px; border: 1px solid rgba(255,255,255,0.8);
  text-decoration: none; backdrop-filter: blur(12px);
  transition: background 0.2s, transform 0.15s;
}
.btn-ghost:hover { background: rgba(255,255,255,0.9); transform: translateY(-2px); box-shadow: 0 8px 20px rgba(0,0,0,0.08); }

/* ── Shared layout ── */
.container {
  max-width: 1040px;
  margin: 0 auto;
  padding: 0 36px;
}
.eyebrow {
  font-size: 12px; font-weight: 700;
  letter-spacing: 0.1em; text-transform: uppercase;
  color: #2563eb; margin: 0 0 14px;
}
.section-title {
  font-size: clamp(26px, 3.5vw, 40px);
  font-weight: 800; letter-spacing: -0.03em;
  margin: 0 0 14px; line-height: 1.2;
}

/* ═══════════════════════════════════════════════════════
   FEATURES — transparent section, glass cards
   ═══════════════════════════════════════════════════════ */
.section-features {
  padding: 96px 0;
  /* no background, no border — seamless with page gradient */
}
.features-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  margin-top: 8px;
}
/* Glass card — lets gradient show through */
.feature-card {
  padding: 32px 28px;
  border-radius: 20px;
  background: rgba(255,255,255,0.55);
  border: 1px solid rgba(255,255,255,0.85);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  box-shadow: 0 4px 24px rgba(99,120,255,0.07);
  transition: box-shadow 0.2s, transform 0.2s;
}
.feature-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 16px 40px rgba(99,120,255,0.13);
}
.feature-num {
  font-size: 12px; font-weight: 700;
  letter-spacing: 0.08em; color: #2563eb;
  margin-bottom: 16px;
}
.feature-card h3 {
  font-size: 18px; font-weight: 700;
  letter-spacing: -0.02em; margin: 0 0 12px;
}
.feature-card p {
  font-size: 14.5px; color: #6b7280;
  line-height: 1.7; margin: 0;
}
.features-cta {
  margin-top: 44px;
  display: flex;
  justify-content: center;
}
.btn-features-start {
  display: inline-flex; align-items: center; gap: 9px;
  padding: 13px 28px;
  background: #2563eb; color: #fff;
  font-size: 15px; font-weight: 600;
  border-radius: 999px; text-decoration: none;
  box-shadow: 0 6px 20px rgba(37,99,235,0.3);
  transition: background 0.2s, transform 0.15s, box-shadow 0.2s;
}
.btn-features-start:hover {
  background: #1d4ed8;
  transform: translateY(-2px);
  box-shadow: 0 12px 28px rgba(37,99,235,0.35);
}

/* ═══════════════════════════════════════════════════════
   TRAINING — glass panel, no section divider
   ═══════════════════════════════════════════════════════ */
.section-training {
  padding: 80px 0 96px;
}
.training-panel {
  /* Wider glass panel wrapping the whole training block */
  background: rgba(255,255,255,0.52);
  border: 1px solid rgba(255,255,255,0.82);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
  border-radius: 28px;
  box-shadow: 0 8px 40px rgba(99,120,255,0.09);
  padding: 56px 64px;
}
.training-inner {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 64px;
  align-items: center;
}
.training-text { max-width: 520px; }
.training-desc {
  font-size: 15.5px; color: #4b5563;
  line-height: 1.72; margin: 0 0 28px;
}
.training-bullets {
  list-style: none; padding: 0; margin: 0 0 32px;
  display: flex; flex-direction: column; gap: 12px;
}
.training-bullets li {
  display: flex; align-items: center; gap: 10px;
  font-size: 14.5px; color: #374151; line-height: 1.5;
}
.bullet-icon { flex-shrink: 0; display: flex; }
.btn-training {
  display: inline-flex; align-items: center; gap: 9px;
  padding: 13px 26px;
  background: linear-gradient(135deg, #2563eb 0%, #7c3aed 100%);
  color: #fff;
  font-size: 15px; font-weight: 600;
  border-radius: 999px; text-decoration: none;
  box-shadow: 0 6px 20px rgba(37,99,235,0.3);
  transition: opacity 0.2s, transform 0.15s;
}
.btn-training:hover { opacity: 0.92; transform: translateY(-2px); }

/* Chip preview */
.training-visual {
  display: flex; flex-direction: column;
  align-items: center; gap: 20px;
}
.chip-preview {
  display: grid;
  grid-template-columns: repeat(3, 80px);
  grid-template-rows: repeat(2, 80px);
  gap: 16px;
  justify-items: center; align-items: center;
}
.chip {
  width: 76px; height: 76px;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 22px; font-weight: 900;
  letter-spacing: -0.02em;
  box-shadow: 0 4px 14px rgba(0,0,0,0.1);
  transition: transform 0.2s;
}
.chip:hover { transform: scale(1.08); }
.chip--target    { background: #0f766e; color: #fff; border: 3px solid #07413e; }
.chip--blue      { background: #2f6fbb; color: #fff; border: 2px solid #18395f; }
.chip--yellow    { background: #f9d56e; color: #1f2937; border: 2px solid #8b6215; }
.chip--rose      { background: #e76f73; color: #fff; border: 2px solid #82373a; }
.chip--plain     { background: rgba(255,255,255,0.9); color: #20242a; border: 2px solid #aab6c1; }
.chip--distractor { opacity: 0.88; }
.preview-caption {
  font-size: 12.5px; color: #9ca3af;
  font-weight: 500; margin: 0;
}

/* ═══════════════════════════════════════════════════════
   FOOTER — deep blue, clearly separated from page body
   ═══════════════════════════════════════════════════════ */
.footer {
  background: linear-gradient(135deg, #1e3a8a 0%, #312e81 100%);
  padding: 52px 0;
}
.footer-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 24px;
}
.footer-left {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.footer-logo {
  font-size: 16px; font-weight: 700;
  color: #fff; letter-spacing: -0.3px;
}
.footer-tagline {
  font-size: 13px; color: rgba(255,255,255,0.45);
  margin: 0;
}
.footer-links {
  display: flex; gap: 28px;
}
.footer-link {
  font-size: 14px; font-weight: 500;
  color: rgba(255,255,255,0.6);
  text-decoration: none;
  transition: color 0.2s;
}
.footer-link:hover { color: #fff; }
.footer-copy {
  font-size: 13px; color: rgba(255,255,255,0.35);
  margin: 0;
}

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
  .features-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 768px) {
  .nav-links { display: none; }
  .nav-hamburger { display: flex; }

  .mobile-nav {
    display: block;
    position: fixed;
    top: 64px; left: 0; right: 0;
    background: rgba(244,245,255,0.96);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border-bottom: 1px solid rgba(99,120,255,0.1);
    z-index: 99;
  }
  .mobile-nav-links { list-style: none; margin: 0; padding: 0; }
  .mobile-nav-link {
    display: block; padding: 16px 28px;
    font-size: 16px; font-weight: 500; color: #374151;
    text-decoration: none;
    border-bottom: 1px solid rgba(0,0,0,0.05);
    transition: background 0.15s;
  }
  .mobile-nav-link:hover { background: rgba(255,255,255,0.6); color: #0d1117; }

  .features-grid { grid-template-columns: 1fr; }
  .footer-inner { flex-direction: column; align-items: flex-start; }
  .container { padding: 0 20px; }
  .section-features, .section-training { padding: 64px 0; }
  .training-panel { padding: 36px 24px; border-radius: 20px; }
  .training-inner { grid-template-columns: 1fr; gap: 40px; }
  .training-visual { order: -1; }
  .chip-preview { grid-template-columns: repeat(3, 68px); grid-template-rows: repeat(2, 68px); }
  .chip { width: 64px; height: 64px; font-size: 18px; }
}
</style>
