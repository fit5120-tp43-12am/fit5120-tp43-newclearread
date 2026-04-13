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
          <li><a href="/" class="nav-link">Home</a></li>
          <li><a href="/reading" class="nav-link">Read Easier</a></li>
          <li><a href="/dyslexia" class="nav-link nav-link--active">Dyslexia</a></li>
          <li><a href="#" class="nav-link">About</a></li>
        </ul>
        <button class="btn-nav btn-nav--disabled" disabled>Get Started</button>
      </div>
    </nav>

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
            1 in 5 Australians may have dyslexia. It affects how the brain reads —
            not how smart someone is.
          </p>
          <div class="hero-actions">
            <a href="#what-is" class="btn-primary">Learn More</a>
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

      <!-- ③ What is Dyslexia + Video -->
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
              <h3>Slow or effortful reading</h3>
              <p>Reading takes much longer than expected and causes fatigue.</p>
            </div>
            <div class="sign-card">
              <h3>Inconsistent spelling</h3>
              <p>The same word may be spelled differently within a single piece of writing.</p>
            </div>
            <div class="sign-card">
              <h3>Sound processing difficulty</h3>
              <p>Trouble breaking words into sounds and blending them back together.</p>
            </div>
            <div class="sign-card">
              <h3>Weak working memory</h3>
              <p>Forgetting words just read, or losing track of a sentence mid-way through.</p>
            </div>
            <div class="sign-card">
              <h3>Poor reading fluency</h3>
              <p>Losing place on a page, skipping lines, or reading word-by-word.</p>
            </div>
            <div class="sign-card">
              <h3>Avoidance of reading</h3>
              <p>Reluctance to read aloud — masking the difficulty, not disinterest.</p>
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
              <h2>The broader impact on wellbeing</h2>
              <p>
                Adults with dyslexia are <strong>twice as likely</strong> to experience
                anxiety or depression, and <strong>46% more likely</strong> to have
                attempted suicide.
              </p>
              <p>
                Many are not diagnosed until adulthood — some not until their fifties.
                Years of unrecognised struggle take a real toll.
              </p>
              <p>
                Early support changes outcomes. SA's phonics check lifted Year 1 literacy
                from <strong>43% (2018) to 68% (2022)</strong>.
              </p>
            </div>
            <div class="impact-quote">
              <blockquote>
                "Many children with dyslexia are bright, creative, and highly capable.
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
          <h2>Ready to read more comfortably?</h2>
          <p>Try ClearRead's Read Easier tool — built for minds that think differently.</p>
          <a href="/reading" class="btn-cta">Read Easier</a>
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
  box-shadow: 0 4px 14px rgba(37, 99, 235, 0.28);
  transition: background 0.2s, transform 0.15s;
}
.btn-nav:hover:not(:disabled) { background: #1d4ed8; transform: translateY(-1px); }
.btn-nav--disabled { opacity: 0.45; cursor: not-allowed; box-shadow: none; }

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

/* ── Responsive ── */
@media (max-width: 1024px) {
  .signs-grid { grid-template-columns: repeat(2, 1fr); }
  .content-block,
  .impact-block { grid-template-columns: 1fr; gap: 40px; }
  .content-aside { position: static; }
}
@media (max-width: 768px) {
  .stats-row { flex-direction: column; gap: 36px; }
  .stat-divider { display: none; }
  .stat-item { padding: 0; }
  .signs-grid { grid-template-columns: 1fr; }
  .nav-links, .btn-nav { display: none; }
  .section-hero { padding: 110px 0 72px; }
}
</style>
