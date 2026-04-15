<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const scrolled  = ref(false)
const menuOpen  = ref(false)
function onScroll() { scrolled.value = window.scrollY > 10 }
onMounted(() => window.addEventListener('scroll', onScroll))
onUnmounted(() => window.removeEventListener('scroll', onScroll))
</script>

<template>
  <div class="page">

    <!-- ── Navbar ── -->
    <nav :class="['navbar', { 'navbar--scrolled': scrolled }]">
      <div class="nav-inner">
        <a href="/" class="nav-logo">
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect width="28" height="28" rx="8" fill="#2563eb"/>
            <path d="M7 8.5C7 7.67 7.67 7 8.5 7H13.5V21H8.5C7.67 21 7 20.33 7 19.5V8.5Z" fill="white" opacity="0.9"/>
            <path d="M21 8.5C21 7.67 20.33 7 19.5 7H14.5V21H19.5C20.33 21 21 20.33 21 19.5V8.5Z" fill="white" opacity="0.55"/>
            <rect x="9" y="10" width="3" height="1.5" rx="0.75" fill="#2563eb" opacity="0.7"/>
            <rect x="9" y="13" width="3" height="1.5" rx="0.75" fill="#2563eb" opacity="0.7"/>
            <rect x="9" y="16" width="2" height="1.5" rx="0.75" fill="#2563eb" opacity="0.7"/>
          </svg>
          ClearRead
        </a>
        <ul class="nav-links">
          <li><a href="/"         class="nav-link nav-link--active">Home</a></li>
          <li><a href="/reading"  class="nav-link">Reading Support</a></li>
          <li><a href="/dyslexia" class="nav-link">Dyslexia</a></li>
          <li><a href="#"         class="nav-link">About</a></li>
        </ul>
        <button class="btn-nav btn-nav--disabled" disabled>Get Started</button>
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
        <li><a href="/"         class="mobile-nav-link" @click="menuOpen = false">Home</a></li>
        <li><a href="/reading"  class="mobile-nav-link" @click="menuOpen = false">Reading Support</a></li>
        <li><a href="/dyslexia" class="mobile-nav-link" @click="menuOpen = false">Dyslexia</a></li>
        <li><a href="#"         class="mobile-nav-link" @click="menuOpen = false">About</a></li>
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
          ClearRead makes them shorter, simpler, and easier to follow.
        </p>
        <div class="hero-actions">
          <a href="/reading" class="btn-start">
            Start Here
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M3 8H13M13 8L9 4M13 8L9 12" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </a>
          <a href="/dyslexia" class="btn-ghost">
            Learn About Dyslexia
          </a>
        </div>
      </div>
    </section>

    <!-- ── Features ── -->
    <section class="section-features">
      <div class="container">
        <p class="eyebrow">What ClearRead does</p>
        <h2 class="section-title">Three ways ClearRead helps</h2>

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
      </div>
    </section>

    <!-- ── How it works ── -->
    <section class="section-steps">
      <div class="container">
        <p class="eyebrow">How it works</p>
        <h2 class="section-title">Three steps</h2>

        <div class="steps-row">
          <div class="step">
            <span class="step-num">1</span>
            <div class="step-body">
              <h3>Paste your text</h3>
              <p>Paste any text or upload a file.</p>
            </div>
          </div>
          <div class="step-arrow">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path d="M4 10H16M16 10L11 5M16 10L11 15" stroke="#d1d5db" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
          <div class="step">
            <span class="step-num">2</span>
            <div class="step-body">
              <h3>Simplify</h3>
              <p>Click Simplify. Get a plain English version and key points.</p>
            </div>
          </div>
          <div class="step-arrow">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path d="M4 10H16M16 10L11 5M16 10L11 15" stroke="#d1d5db" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
          <div class="step">
            <span class="step-num">3</span>
            <div class="step-body">
              <h3>Read or listen</h3>
              <p>Read or listen at your own pace.</p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ── CTA ── -->
    <section class="section-cta">
      <div class="container">
        <h2>Give it a try.</h2>
        <p>It only takes a minute to get started.</p>
        <a href="/reading" class="btn-cta">
          Start Here
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M3 8H13M13 8L9 4M13 8L9 12" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </a>
      </div>
    </section>

    <!-- ── Footer ── -->
    <footer class="footer">
      <div class="container footer-inner">
        <div class="footer-left">
          <span class="footer-logo">ClearRead</span>
          <p class="footer-tagline">Built for minds that think differently.</p>
        </div>
        <nav class="footer-links">
          <a href="/reading"  class="footer-link">Reading Support</a>
          <a href="/dyslexia" class="footer-link">Dyslexia</a>
          <a href="#"         class="footer-link">About</a>
        </nav>
        <p class="footer-copy">© 2026 ClearRead. All rights reserved.</p>
      </div>
    </footer>

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
.btn-nav {
  display: inline-flex; align-items: center;
  padding: 8px 18px;
  background: #2563eb; color: #fff;
  font-size: 13.5px; font-weight: 600;
  border-radius: 999px; text-decoration: none; flex-shrink: 0;
  box-shadow: 0 4px 14px rgba(37,99,235,0.3);
  transition: background 0.2s, transform 0.15s;
}
.btn-nav:hover:not(:disabled) { background: #1d4ed8; transform: translateY(-1px); }
.btn-nav--disabled {
  opacity: 0.45;
  cursor: not-allowed;
  box-shadow: none;
}

/* ── Hero ── */
.hero {
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background:
    radial-gradient(ellipse 55% 80% at 15% 55%, rgba(147,167,255,0.45) 0%, transparent 65%),
    radial-gradient(ellipse 45% 65% at 85% 40%, rgba(255,200,150,0.4) 0%, transparent 60%),
    radial-gradient(ellipse 30% 40% at 50% 80%, rgba(255,220,180,0.25) 0%, transparent 55%),
    #f8f9ff;
  overflow: hidden;
}
.blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(90px);
  pointer-events: none;
  z-index: 0;
}
.blob--blue  { width: 520px; height: 520px; background: rgba(99,120,255,0.18); top: -60px; left: -80px; }
.blob--peach { width: 420px; height: 420px; background: rgba(255,165,100,0.15); bottom: -60px; right: -60px; }

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
  background: rgba(255,255,255,0.7);
  border: 1px solid rgba(79,110,247,0.2);
  border-radius: 999px;
  font-size: 13px; font-weight: 500; color: #374151;
  margin-bottom: 28px;
  backdrop-filter: blur(10px);
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
  background: rgba(255,255,255,0.75); color: #374151;
  font-size: 15px; font-weight: 600;
  border-radius: 999px; border: 1px solid rgba(0,0,0,0.1);
  text-decoration: none; backdrop-filter: blur(10px);
  transition: background 0.2s, transform 0.15s;
}
.btn-ghost:hover { background: rgba(255,255,255,0.95); transform: translateY(-2px); box-shadow: 0 8px 20px rgba(0,0,0,0.08); }

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
.section-sub {
  font-size: 16px; color: #6b7280;
  line-height: 1.65; margin: 0 0 52px;
  max-width: 520px;
}

/* ── Features ── */
.section-features {
  padding: 96px 0;
  border-bottom: 1px solid #e5e7eb;
}
.features-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
}
.feature-card {
  padding: 32px 28px;
  border: 1px solid #e5e7eb;
  border-radius: 16px;
  background: #fff;
  transition: box-shadow 0.2s, transform 0.2s;
}
.feature-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 32px rgba(0,0,0,0.07);
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

/* ── Steps ── */
.section-steps {
  padding: 96px 0;
  background: #fafbff;
  border-bottom: 1px solid #e5e7eb;
}
.steps-row {
  display: flex;
  align-items: center;
  gap: 0;
  margin-top: 52px;
}
.step {
  flex: 1;
  display: flex;
  gap: 20px;
  align-items: flex-start;
}
.step-num {
  width: 40px; height: 40px;
  flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  background: #eef2ff;
  color: #2563eb;
  font-size: 15px; font-weight: 800;
  border-radius: 12px;
}
.step-body h3 {
  font-size: 16px; font-weight: 700;
  margin: 0 0 8px; letter-spacing: -0.02em;
}
.step-body p {
  font-size: 14px; color: #6b7280;
  line-height: 1.65; margin: 0;
}
.step-arrow {
  flex-shrink: 0;
  padding: 0 28px;
  margin-top: 10px;
}

/* ── CTA ── */
.section-cta {
  padding: 96px 0;
  background: linear-gradient(135deg, #1e3a8a 0%, #312e81 100%);
  text-align: center;
}
.section-cta h2 {
  font-size: clamp(26px, 4vw, 42px);
  font-weight: 800; color: #fff;
  letter-spacing: -0.04em; margin: 0 0 14px;
}
.section-cta p {
  font-size: 16px; color: rgba(255,255,255,0.65);
  margin: 0 0 36px;
}
.btn-cta {
  display: inline-flex; align-items: center; gap: 10px;
  padding: 14px 32px;
  background: #fff; color: #2563eb;
  font-size: 15px; font-weight: 700;
  border-radius: 999px; text-decoration: none;
  box-shadow: 0 8px 28px rgba(0,0,0,0.2);
  transition: background 0.2s, transform 0.15s;
}
.btn-cta:hover { background: #eef2ff; transform: translateY(-2px); }

/* ── Footer ── */
.footer {
  background: #0d1117;
  padding: 48px 0;
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
  font-size: 13px; color: rgba(255,255,255,0.35);
  margin: 0;
}
.footer-links {
  display: flex; gap: 28px;
}
.footer-link {
  font-size: 14px; font-weight: 500;
  color: rgba(255,255,255,0.5);
  text-decoration: none;
  transition: color 0.2s;
}
.footer-link:hover { color: #fff; }
.footer-copy {
  font-size: 13px; color: rgba(255,255,255,0.3);
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
.mobile-nav {
  display: none;
}

/* ── Responsive ── */
@media (max-width: 1024px) {
  .features-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 768px) {
  .nav-links, .btn-nav { display: none; }
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

  .features-grid { grid-template-columns: 1fr; }
  .steps-row  { flex-direction: column; gap: 24px; }
  .step-arrow { display: none; }
  .footer-inner { flex-direction: column; align-items: flex-start; }
  .container { padding: 0 20px; }
  .section-features, .section-steps, .section-cta { padding: 64px 0; }
}
</style>
