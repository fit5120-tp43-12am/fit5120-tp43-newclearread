<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

// ── Navbar scroll ──
const scrolled = ref(false)
const menuOpen = ref(false)

function onScroll() { scrolled.value = window.scrollY > 10 }

onMounted(() => { window.addEventListener('scroll', onScroll) })
onUnmounted(() => { window.removeEventListener('scroll', onScroll) })
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
          <li><RouterLink to="/"         class="nav-link">Home</RouterLink></li>
          <li><RouterLink to="/reading"  class="nav-link nav-link--active">Reading Support</RouterLink></li>
          <li><RouterLink to="/dyslexia" class="nav-link">Dyslexia</RouterLink></li>
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
        <li><RouterLink to="/dyslexia" class="mobile-nav-link" @click="menuOpen = false">Dyslexia</RouterLink></li>
      </ul>
    </div>

    <!-- ── Page content goes here ── -->

  </div>
</template>

<style scoped>
/* ── Shell ── */
.page {
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
  background: #fff;
}

/* ── Navbar ── */
.navbar {
  flex-shrink: 0;
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
  z-index: 50;
}
.navbar--scrolled {
  box-shadow: 0 1px 8px rgba(0, 0, 0, 0.06);
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
  display: flex;
  align-items: center;
  gap: 9px;
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

/* ── Hamburger ── */
.nav-hamburger {
  display: none;
  background: none;
  border: none;
  cursor: pointer;
  color: #0d1117;
  padding: 4px;
  margin-left: 12px;
  align-items: center;
  justify-content: center;
}

/* ── Mobile nav drawer ── */
.mobile-nav { display: none; }

/* ── Responsive ── */
@media (max-width: 860px) {
  .nav-links { display: none; }
  .nav-hamburger { display: flex; }
  .nav-inner { padding: 0 16px; }

  .mobile-nav {
    display: block;
    position: fixed;
    top: 64px;
    left: 0;
    right: 0;
    background: rgba(255, 255, 255, 0.98);
    backdrop-filter: blur(18px);
    -webkit-backdrop-filter: blur(18px);
    border-bottom: 1px solid #e5e7eb;
    z-index: 99;
  }
  .mobile-nav-links { list-style: none; margin: 0; padding: 0; }
  .mobile-nav-link {
    display: block;
    padding: 16px 24px;
    font-size: 16px;
    font-weight: 500;
    color: #374151;
    text-decoration: none;
    border-bottom: 1px solid #f3f4f6;
    transition: background 0.15s;
  }
  .mobile-nav-link:hover { background: #f9fafb; color: #0d1117; }
}
</style>
