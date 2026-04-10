<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const scrolled = ref(false)

function onScroll() {
  scrolled.value = window.scrollY > 10
}

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
          <li><a href="/" class="nav-link nav-link--active">Home</a></li>
          <li><a href="#" class="nav-link">Reading</a></li>
          <li><a href="#" class="nav-link">Dyslexia</a></li>
          <li><a href="#" class="nav-link">About</a></li>
        </ul>

        <a href="#" class="btn-nav">Get Started</a>
      </div>
    </nav>

    <!-- Hero -->
    <section class="hero">
      <!-- Gradient background blobs -->
      <div class="blob blob--blue"></div>
      <div class="blob blob--peach"></div>

      <!-- Side decorative circles -->
      <button class="side-btn side-btn--left" aria-label="Previous">
        <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
          <path d="M11 13L7 9L11 5" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>
      <button class="side-btn side-btn--right" aria-label="Next">
        <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
          <path d="M7 5L11 9L7 13" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>

      <div class="hero-content">
        <!-- Badge -->
        <div class="badge">
          <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
            <path d="M6.5 1L8 5H12L8.8 7.5L10 11.5L6.5 9L3 11.5L4.2 7.5L1 5H5L6.5 1Z" fill="#4f6ef7"/>
          </svg>
          Reading support for minds that think differently.
        </div>

        <!-- Heading -->
        <h1 class="hero-title">
          Read with Clarity.<br/>
          Learn with <span class="highlight">Confidence.</span>
        </h1>

        <!-- Subtitle -->
        <p class="hero-sub">
          ClearRead turns complex text into clear summaries,<br/>
          custom reading settings, and natural audio&thinsp;&mdash;&thinsp;so you can<br/>
          focus on understanding.
        </p>

        <!-- Buttons -->
        <div class="hero-actions">
          <a href="#" class="btn-start">
            Start Reading
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M3 8H13M13 8L9 4M13 8L9 12" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </a>
          <a href="#" class="btn-learn">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <rect x="2" y="3" width="12" height="10" rx="1.5" stroke="currentColor" stroke-width="1.5"/>
              <path d="M5 7h6M5 9.5h3.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
            </svg>
            Learn About Dyslexia
          </a>
        </div>
      </div>
    </section>

  </div>
</template>

<style scoped>
/* ── Page ── */
.page {
  min-height: 100vh;
  overflow: hidden;
}

/* ── Navbar ── */
.navbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 100;
  transition: background 0.3s, box-shadow 0.3s;
}

.navbar--scrolled {
  background: rgba(255, 255, 255, 0.85);
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
  gap: 0;
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

.nav-link:hover {
  color: #0d1117;
  background: rgba(0, 0, 0, 0.04);
}

.nav-link--active {
  color: #0d1117;
}

/* Active underline dot */
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
  transition: background 0.2s, transform 0.15s, box-shadow 0.2s;
  box-shadow: 0 4px 14px rgba(37, 99, 235, 0.3);
  flex-shrink: 0;
}

.btn-nav:hover {
  background: #1d4ed8;
  transform: translateY(-1px);
  box-shadow: 0 8px 20px rgba(37, 99, 235, 0.35);
}

/* ── Hero ── */
.hero {
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  /* Gradient matching the design: blue-purple left → warm peach right */
  background:
    radial-gradient(ellipse 55% 80% at 15% 55%, rgba(147, 167, 255, 0.45) 0%, transparent 65%),
    radial-gradient(ellipse 45% 65% at 85% 40%, rgba(255, 200, 150, 0.4) 0%, transparent 60%),
    radial-gradient(ellipse 30% 40% at 50% 80%, rgba(255, 220, 180, 0.25) 0%, transparent 55%),
    #f8f9ff;
}

/* Soft colour blobs for extra depth */
.blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(90px);
  pointer-events: none;
  z-index: 0;
}

.blob--blue {
  width: 520px;
  height: 520px;
  background: rgba(99, 120, 255, 0.18);
  top: -60px;
  left: -80px;
}

.blob--peach {
  width: 420px;
  height: 420px;
  background: rgba(255, 165, 100, 0.15);
  bottom: -60px;
  right: -60px;
}

/* Side arrow buttons */
.side-btn {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: 1.5px solid rgba(0, 0, 0, 0.1);
  background: rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(8px);
  color: #6b7280;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 2;
  transition: background 0.2s, border-color 0.2s, box-shadow 0.2s;
}

.side-btn:hover {
  background: rgba(255, 255, 255, 0.9);
  border-color: rgba(0, 0, 0, 0.15);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.side-btn--left  { left: 28px; }
.side-btn--right { right: 28px; }

/* Hero content */
.hero-content {
  position: relative;
  z-index: 1;
  text-align: center;
  padding: 0 24px;
  max-width: 700px;
}

/* Badge pill */
.badge {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 6px 16px;
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(79, 110, 247, 0.2);
  border-radius: 999px;
  font-size: 13px;
  font-weight: 500;
  color: #374151;
  margin-bottom: 28px;
  backdrop-filter: blur(10px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

/* Heading */
.hero-title {
  font-size: clamp(44px, 7.5vw, 72px);
  font-weight: 800;
  letter-spacing: -0.045em;
  line-height: 1.08;
  color: #0d1117;
  margin-bottom: 22px;
}

.highlight {
  background: linear-gradient(120deg, #2563eb 20%, #5b8af5 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* Subtitle */
.hero-sub {
  font-size: 16px;
  line-height: 1.72;
  color: #4b5563;
  margin-bottom: 38px;
}

/* Action buttons */
.hero-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
  flex-wrap: wrap;
}

.btn-start {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  padding: 13px 26px;
  background: #2563eb;
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  border-radius: 999px;
  text-decoration: none;
  transition: background 0.2s, transform 0.15s, box-shadow 0.2s;
  box-shadow: 0 6px 20px rgba(37, 99, 235, 0.3);
}

.btn-start:hover {
  background: #1d4ed8;
  transform: translateY(-2px);
  box-shadow: 0 12px 28px rgba(37, 99, 235, 0.35);
}

.btn-learn {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  padding: 13px 24px;
  background: rgba(255, 255, 255, 0.75);
  color: #374151;
  font-size: 15px;
  font-weight: 600;
  border-radius: 999px;
  border: 1px solid rgba(0, 0, 0, 0.1);
  text-decoration: none;
  backdrop-filter: blur(10px);
  transition: background 0.2s, transform 0.15s, box-shadow 0.2s;
}

.btn-learn:hover {
  background: rgba(255, 255, 255, 0.95);
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.08);
}
</style>
