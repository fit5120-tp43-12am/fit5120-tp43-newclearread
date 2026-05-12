<template>
  <div class="page">

    <!-- ── Navbar ── -->
    <nav class="navbar">
      <div class="nav-inner">
        <RouterLink to="/" class="nav-logo">
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
            <rect width="28" height="28" rx="8" fill="#2563eb"/>
            <path d="M7 8.5C7 7.67 7.67 7 8.5 7H13.5V21H8.5C7.67 21 7 20.33 7 19.5V8.5Z" fill="white" opacity="0.9"/>
            <path d="M21 8.5C21 7.67 20.33 7 19.5 7H14.5V21H19.5C20.33 21 21 20.33 21 19.5V8.5Z" fill="white" opacity="0.55"/>
          </svg>
          Clearead
        </RouterLink>
        <ul class="nav-links">
          <li><RouterLink to="/"           class="nav-link">Home</RouterLink></li>
          <li><RouterLink to="/reading"    class="nav-link">Reading Support</RouterLink></li>
          <li><RouterLink to="/training"   class="nav-link">Training</RouterLink></li>
          <li><RouterLink to="/dictionary" class="nav-link">Dictionary</RouterLink></li>
          <li><RouterLink to="/dyslexia"   class="nav-link">Understand Dyslexia</RouterLink></li>
          <li><RouterLink to="/extension"  class="nav-link nav-link--ext nav-link--active">Extension</RouterLink></li>
        </ul>
      </div>
    </nav>

    <!-- ── Hero ── -->
    <section class="hero">
      <div class="hero-blob hero-blob--purple"></div>
      <div class="hero-blob hero-blob--blue"></div>

      <div class="hero-inner container">

        <!-- Left: text + CTA -->
        <div class="hero-text">
          <div class="badge">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <circle cx="7" cy="7" r="6" fill="#4ade80" opacity="0.3"/>
              <circle cx="7" cy="7" r="3" fill="#16a34a"/>
            </svg>
            Now available on Chrome Web Store
          </div>

          <h1 class="hero-title">
            Clearead<br/>
            <span class="hero-title--accent">in your browser</span>
          </h1>
          <p class="hero-desc">
            Get reading support on <strong>any webpage</strong> you visit.
            Summarise articles, look up words with a right-click, and apply
            dyslexia-friendly reading tools — all from a side panel in Chrome.
          </p>

          <a
            href="https://chromewebstore.google.com/detail/clearead/jlohhhioeodjkkeahcoelbbnkaigflkn"
            target="_blank"
            rel="noopener noreferrer"
            class="btn-install"
          >
            <!-- Chrome icon -->
            <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
              <circle cx="11" cy="11" r="10" fill="white" opacity="0.15"/>
              <circle cx="11" cy="11" r="4.2" fill="white"/>
              <path d="M11 6.8h8.6A10 10 0 0 0 2.7 8.6L6.9 15.6A4.2 4.2 0 0 1 11 6.8Z" fill="#EA4335" opacity="0.9"/>
              <path d="M19.6 6.8H11A4.2 4.2 0 0 1 15.1 15.6L11 22A10 10 0 0 0 19.6 6.8Z" fill="#FBBC05" opacity="0.9"/>
              <path d="M6.9 15.6A4.2 4.2 0 0 0 15.1 15.6L11 22A10 10 0 0 1 2.7 8.6Z" fill="#34A853" opacity="0.9"/>
            </svg>
            Add to Chrome — it's free
          </a>

          <p class="hero-note">Chrome 116+ · No account required</p>
        </div>

        <!-- Right: browser + side panel mockup -->
        <div class="hero-visual" aria-hidden="true">
          <div class="browser-mock">
            <!-- Browser chrome -->
            <div class="browser-bar">
              <div class="browser-dots">
                <span class="dot dot--red"></span>
                <span class="dot dot--yellow"></span>
                <span class="dot dot--green"></span>
              </div>
              <div class="browser-url">
                <svg width="11" height="11" viewBox="0 0 12 12" fill="none">
                  <path d="M6 1a5 5 0 1 0 0 10A5 5 0 0 0 6 1Zm0 1.5a.5.5 0 1 1 0 1 .5.5 0 0 1 0-1Zm.5 6.5h-1V5.5h1V9Z" fill="#9ca3af"/>
                </svg>
                your-study-article.com
              </div>
              <!-- Extension icon in toolbar -->
              <div class="browser-ext-icon">
                <svg width="14" height="14" viewBox="0 0 28 28" fill="none">
                  <rect width="28" height="28" rx="6" fill="#2563eb"/>
                  <path d="M7 8.5C7 7.67 7.67 7 8.5 7H13.5V21H8.5C7.67 21 7 20.33 7 19.5V8.5Z" fill="white" opacity="0.9"/>
                  <path d="M21 8.5C21 7.67 20.33 7 19.5 7H14.5V21H19.5C20.33 21 21 20.33 21 19.5V8.5Z" fill="white" opacity="0.55"/>
                </svg>
              </div>
            </div>

            <!-- Page + side panel -->
            <div class="browser-body">
              <!-- Webpage content area -->
              <div class="webpage-area">
                <div class="webpage-line webpage-line--title"></div>
                <div class="webpage-line" style="width:88%"></div>
                <div class="webpage-line" style="width:74%"></div>
                <div class="webpage-line" style="width:92%"></div>
                <div class="webpage-line" style="width:66%"></div>
                <div class="webpage-line" style="width:80%; margin-top:10px"></div>
                <div class="webpage-line" style="width:70%"></div>
                <div class="webpage-line webpage-line--highlighted" style="width:85%"></div>
                <div class="webpage-line webpage-line--highlighted" style="width:60%"></div>
                <div class="webpage-line" style="width:78%"></div>
              </div>

              <!-- Side panel -->
              <div class="sidepanel">
                <div class="sp-header">
                  <svg width="14" height="14" viewBox="0 0 28 28" fill="none">
                    <rect width="28" height="28" rx="6" fill="#2563eb"/>
                    <path d="M7 8.5C7 7.67 7.67 7 8.5 7H13.5V21H8.5C7.67 21 7 20.33 7 19.5V8.5Z" fill="white" opacity="0.9"/>
                    <path d="M21 8.5C21 7.67 20.33 7 19.5 7H14.5V21H19.5C20.33 21 21 20.33 21 19.5V8.5Z" fill="white" opacity="0.55"/>
                  </svg>
                  <span class="sp-title">Clearead</span>
                </div>

                <!-- Summary result -->
                <div class="sp-section">
                  <div class="sp-label">Summary</div>
                  <div class="sp-summary-lines">
                    <div class="sp-line" style="width:95%"></div>
                    <div class="sp-line" style="width:80%"></div>
                    <div class="sp-line" style="width:88%"></div>
                  </div>
                </div>

                <!-- Tools row -->
                <div class="sp-section">
                  <div class="sp-label">Page Tools</div>
                  <div class="sp-tools">
                    <div class="sp-tool sp-tool--active">
                      <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
                        <path d="M3 4h10M3 8h10M3 12h6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
                      </svg>
                      Font
                    </div>
                    <div class="sp-tool">
                      <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
                        <rect x="2" y="5" width="12" height="3" rx="1.5" fill="currentColor" opacity="0.4"/>
                        <rect x="2" y="10" width="8" height="3" rx="1.5" fill="currentColor" opacity="0.4"/>
                      </svg>
                      Highlight
                    </div>
                    <div class="sp-tool">
                      <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
                        <circle cx="8" cy="8" r="5" stroke="currentColor" stroke-width="1.6"/>
                        <circle cx="8" cy="8" r="2" fill="currentColor" opacity="0.5"/>
                      </svg>
                      Lens
                    </div>
                  </div>
                </div>

                <!-- Word box -->
                <div class="sp-section sp-section--last">
                  <div class="sp-label">Word Lookup</div>
                  <div class="sp-word-box">
                    <span class="sp-word-text">dyslexia</span>
                    <span class="sp-word-explain">Explain</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

      </div>
    </section>

    <!-- ── Features ── -->
    <section class="section-features">
      <div class="container">
        <p class="eyebrow">What you get</p>
        <h2 class="section-title">Four tools, one side panel</h2>
        <div class="features-grid">

          <div class="feature-card">
            <div class="feature-icon feature-icon--blue">
              <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
                <path d="M4 5h14M4 9h10M4 13h12M4 17h8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
              </svg>
            </div>
            <h3>Text Summary</h3>
            <p>Paste any article, lecture note, or reading. Clearead returns a plain-English summary so you know what matters before reading in depth.</p>
          </div>

          <div class="feature-card">
            <div class="feature-icon feature-icon--violet">
              <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
                <circle cx="10" cy="10" r="6.5" stroke="currentColor" stroke-width="1.8"/>
                <path d="M15 15l4 4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
              </svg>
            </div>
            <h3>Word Lookup</h3>
            <p>Type a word in the side panel or right-click any word on the page. Get a simple meaning and a breakdown of its prefix, root, and suffix.</p>
          </div>

          <div class="feature-card">
            <div class="feature-icon feature-icon--green">
              <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
                <path d="M4 7h14M4 11h14M4 15h10" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
                <rect x="14" y="13" width="5" height="5" rx="1" fill="currentColor" opacity="0.3"/>
              </svg>
            </div>
            <h3>Readable Fonts</h3>
            <p>Switch the whole page to OpenDyslexic or another dyslexia-friendly font with one click. Works on almost any website.</p>
          </div>

          <div class="feature-card">
            <div class="feature-icon feature-icon--amber">
              <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
                <rect x="2" y="9" width="18" height="4" rx="2" fill="currentColor" opacity="0.25"/>
                <path d="M2 11h18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                <circle cx="11" cy="11" r="4" stroke="currentColor" stroke-width="1.8"/>
              </svg>
            </div>
            <h3>Highlight &amp; Line Guide</h3>
            <p>Highlight the line you're reading and add a visual ruler so your eyes don't drift. Great for dense text-heavy pages.</p>
          </div>

        </div>
      </div>
    </section>

    <!-- ── How to use ── -->
    <section class="section-howto">
      <div class="container">
        <p class="eyebrow">Getting started</p>
        <h2 class="section-title">Up and running in 3 steps</h2>

        <div class="steps">

          <div class="step">
            <div class="step-num">1</div>
            <div class="step-body">
              <div class="step-visual step-visual--install">
                <div class="chrome-store-card">
                  <div class="csc-icon">
                    <svg width="32" height="32" viewBox="0 0 28 28" fill="none">
                      <rect width="28" height="28" rx="7" fill="#2563eb"/>
                      <path d="M7 8.5C7 7.67 7.67 7 8.5 7H13.5V21H8.5C7.67 21 7 20.33 7 19.5V8.5Z" fill="white" opacity="0.9"/>
                      <path d="M21 8.5C21 7.67 20.33 7 19.5 7H14.5V21H19.5C20.33 21 21 20.33 21 19.5V8.5Z" fill="white" opacity="0.55"/>
                    </svg>
                  </div>
                  <div class="csc-info">
                    <div class="csc-name">Clearead</div>
                    <div class="csc-meta">4.9 ★ · Reading support</div>
                  </div>
                  <div class="csc-btn">Add</div>
                </div>
              </div>
              <div class="step-text">
                <h3>Install from Chrome Web Store</h3>
                <p>Click <strong>"Add to Chrome"</strong> on the store page. Chrome will ask for permission — click <em>Add extension</em> to confirm. Takes under 10 seconds.</p>
                <a
                  href="https://chromewebstore.google.com/detail/clearead/jlohhhioeodjkkeahcoelbbnkaigflkn"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="btn-step-install"
                >
                  Go to Chrome Web Store →
                </a>
              </div>
            </div>
          </div>

          <div class="step-divider"></div>

          <div class="step">
            <div class="step-num">2</div>
            <div class="step-body">
              <div class="step-visual step-visual--open">
                <div class="toolbar-mock">
                  <div class="toolbar-puzzle">
                    <svg width="16" height="16" viewBox="0 0 20 20" fill="none">
                      <path d="M12 2a2 2 0 0 1 2 2h1a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1h-1a2 2 0 0 1-4 0H8v1a2 2 0 0 1-2 2v1a1 1 0 0 0 1 1h3a2 2 0 0 1 4 0h1a1 1 0 0 0 1-1v-3" stroke="#6b7280" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                  </div>
                  <div class="toolbar-ext-item toolbar-ext-item--active">
                    <svg width="14" height="14" viewBox="0 0 28 28" fill="none">
                      <rect width="28" height="28" rx="6" fill="#2563eb"/>
                      <path d="M7 8.5C7 7.67 7.67 7 8.5 7H13.5V21H8.5C7.67 21 7 20.33 7 19.5V8.5Z" fill="white" opacity="0.9"/>
                      <path d="M21 8.5C21 7.67 20.33 7 19.5 7H14.5V21H19.5C20.33 21 21 20.33 21 19.5V8.5Z" fill="white" opacity="0.55"/>
                    </svg>
                    <span>Clearead</span>
                    <div class="toolbar-arrow">↑</div>
                  </div>
                </div>
              </div>
              <div class="step-text">
                <h3>Open the side panel</h3>
                <p>On any webpage, click the <strong>puzzle piece icon</strong> in Chrome's toolbar, then click <strong>Clearead</strong>. The reading support panel will open on the right side of your browser.</p>
                <p class="step-tip">💡 Tip: Pin Clearead to your toolbar so it's always one click away.</p>
              </div>
            </div>
          </div>

          <div class="step-divider"></div>

          <div class="step">
            <div class="step-num">3</div>
            <div class="step-body">
              <div class="step-visual step-visual--use">
                <div class="use-tabs">
                  <div class="use-tab use-tab--active">Summary</div>
                  <div class="use-tab">Word</div>
                  <div class="use-tab">Tools</div>
                </div>
                <div class="use-content">
                  <div class="use-textarea">Paste your text here…</div>
                  <div class="use-submit">Summarise</div>
                </div>
              </div>
              <div class="step-text">
                <h3>Choose your reading tool</h3>
                <p>The panel has three sections:</p>
                <ul class="step-list">
                  <li><strong>Summary</strong> — paste text, get a plain-English summary</li>
                  <li><strong>Word</strong> — type or right-click a word to look it up</li>
                  <li><strong>Tools</strong> — apply readable fonts, highlight, lens, or line guide to the page</li>
                </ul>
              </div>
            </div>
          </div>

        </div>
      </div>
    </section>

    <!-- ── CTA Banner ── -->
    <section class="section-cta">
      <div class="container">
        <div class="cta-panel">
          <div class="cta-text">
            <h2>Ready to try it?</h2>
            <p>Install Clearead in seconds and get reading support on every page you visit.</p>
          </div>
          <a
            href="https://chromewebstore.google.com/detail/clearead/jlohhhioeodjkkeahcoelbbnkaigflkn"
            target="_blank"
            rel="noopener noreferrer"
            class="btn-install btn-install--cta"
          >
            <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
              <circle cx="11" cy="11" r="10" fill="white" opacity="0.15"/>
              <circle cx="11" cy="11" r="4.2" fill="white"/>
              <path d="M11 6.8h8.6A10 10 0 0 0 2.7 8.6L6.9 15.6A4.2 4.2 0 0 1 11 6.8Z" fill="#EA4335" opacity="0.9"/>
              <path d="M19.6 6.8H11A4.2 4.2 0 0 1 15.1 15.6L11 22A10 10 0 0 0 19.6 6.8Z" fill="#FBBC05" opacity="0.9"/>
              <path d="M6.9 15.6A4.2 4.2 0 0 0 15.1 15.6L11 22A10 10 0 0 1 2.7 8.6Z" fill="#34A853" opacity="0.9"/>
            </svg>
            Add to Chrome — it's free
          </a>
        </div>
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
          <RouterLink to="/privacy-policy" class="footer-link">Privacy Policy</RouterLink>
        </nav>
        <p class="footer-copy">© 2026 Clearead. All rights reserved.</p>
      </div>
    </footer>

  </div>
</template>

<style scoped>
.page {
  min-height: 100vh;
  background:
    radial-gradient(ellipse 80% 40% at 0% 0%,   rgba(147,167,255,0.45) 0%, transparent 55%),
    radial-gradient(ellipse 65% 35% at 100% 0%,  rgba(120,180,255,0.30) 0%, transparent 52%),
    radial-gradient(ellipse 60% 30% at 0% 100%,  rgba(147,167,255,0.25) 0%, transparent 55%),
    radial-gradient(ellipse 55% 28% at 100% 100%,rgba(200,180,255,0.22) 0%, transparent 52%),
    #f4f5ff;
  color: #0d1117;
}

/* ── Navbar ── */
.navbar {
  position: sticky; top: 0; z-index: 100;
  background: rgba(244,245,255,0.90);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  box-shadow: 0 1px 0 rgba(99,120,255,0.10);
}
.nav-inner {
  max-width: 1100px; margin: 0 auto;
  padding: 0 36px; height: 64px;
  display: flex; align-items: center; gap: 32px;
}
.nav-logo {
  display: flex; align-items: center; gap: 9px;
  font-size: 17px; font-weight: 700;
  color: #0d1117; text-decoration: none; flex-shrink: 0;
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
}
.nav-link:hover { color: #0d1117; background: rgba(0,0,0,0.04); }
.nav-link--ext { color: #2563eb; border: 1px solid rgba(37,99,235,0.22); padding: 5px 13px; }
.nav-link--ext:hover { background: rgba(37,99,235,0.07); color: #1d4ed8; }
.nav-link--active { color: #2563eb; background: rgba(37,99,235,0.08); }

/* ── Shared layout ── */
.container { max-width: 1040px; margin: 0 auto; padding: 0 36px; }
.eyebrow {
  font-size: 12px; font-weight: 700;
  letter-spacing: 0.1em; text-transform: uppercase;
  color: #2563eb; margin: 0 0 14px;
}
.section-title {
  font-size: clamp(26px, 3.5vw, 40px);
  font-weight: 800; letter-spacing: -0.03em;
  margin: 0 0 14px; line-height: 1.2; color: #0f172a;
}

/* ══════════════════════════════════════════
   HERO
   ══════════════════════════════════════════ */
.hero {
  position: relative;
  padding: 100px 0 80px;
  overflow: hidden;
}
.hero-blob {
  position: absolute; border-radius: 50%;
  filter: blur(110px); pointer-events: none; z-index: 0;
}
.hero-blob--purple { width: 480px; height: 480px; background: rgba(124,58,237,0.12); top: -60px; right: -80px; }
.hero-blob--blue   { width: 360px; height: 360px; background: rgba(37,99,235,0.10);  bottom: 0;  left: -60px; }

.hero-inner {
  position: relative; z-index: 1;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 64px;
  align-items: center;
}

/* Badge */
.badge {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 6px 16px;
  background: rgba(255,255,255,0.70);
  border: 1px solid rgba(79,110,247,0.18);
  border-radius: 999px;
  font-size: 13px; font-weight: 500; color: #374151;
  margin-bottom: 24px;
  backdrop-filter: blur(12px);
}

.hero-title {
  font-size: clamp(36px, 5vw, 58px);
  font-weight: 800; letter-spacing: -0.04em;
  line-height: 1.08; color: #0d1117;
  margin: 0 0 20px;
}
.hero-title--accent {
  background: linear-gradient(120deg, #2563eb 10%, #7c3aed 90%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  background-clip: text;
}
.hero-desc {
  font-size: 16px; line-height: 1.78;
  color: #4b5563; margin: 0 0 32px;
}
.hero-desc strong { color: #1e293b; }

/* Install button */
.btn-install {
  display: inline-flex; align-items: center; gap: 10px;
  padding: 14px 28px;
  background: linear-gradient(135deg, #2563eb 0%, #7c3aed 100%);
  color: #fff; font-size: 16px; font-weight: 700;
  border-radius: 999px; text-decoration: none;
  box-shadow: 0 8px 28px rgba(37,99,235,0.32);
  transition: opacity 0.2s, transform 0.15s, box-shadow 0.2s;
}
.btn-install:hover {
  opacity: 0.92; transform: translateY(-2px);
  box-shadow: 0 14px 36px rgba(37,99,235,0.38);
}
.btn-install--cta { font-size: 15px; padding: 13px 26px; }

.hero-note {
  margin: 14px 0 0;
  font-size: 12.5px; color: #9ca3af;
}

/* ── Browser mockup ── */
.hero-visual { display: flex; justify-content: center; align-items: flex-start; }

.browser-mock {
  width: 100%;
  max-width: 440px;
  border-radius: 16px;
  overflow: hidden;
  background: #fff;
  box-shadow: 0 4px 8px rgba(0,0,0,0.06), 0 24px 64px rgba(99,102,241,0.16);
  border: 1px solid rgba(226,232,240,0.8);
}

/* Browser chrome bar */
.browser-bar {
  height: 36px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  padding: 0 12px;
  gap: 10px;
}
.browser-dots { display: flex; gap: 5px; }
.dot { width: 10px; height: 10px; border-radius: 50%; }
.dot--red    { background: #ff5f57; }
.dot--yellow { background: #ffbd2e; }
.dot--green  { background: #28c840; }
.browser-url {
  flex: 1; height: 22px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  display: flex; align-items: center; gap: 5px;
  padding: 0 8px;
  font-size: 11px; color: #9ca3af;
}
.browser-ext-icon {
  width: 22px; height: 22px;
  background: #eef2ff;
  border-radius: 5px;
  display: flex; align-items: center; justify-content: center;
}

/* Page + side panel split */
.browser-body {
  display: flex;
  height: 280px;
}
.webpage-area {
  flex: 1;
  padding: 16px 14px;
  display: flex;
  flex-direction: column;
  gap: 7px;
}
.webpage-line {
  height: 9px;
  background: #e2e8f0;
  border-radius: 4px;
}
.webpage-line--title {
  width: 55%; height: 14px;
  background: #cbd5e1;
  margin-bottom: 6px;
}
.webpage-line--highlighted {
  background: rgba(255,248,80,0.55);
  border-radius: 4px;
}

/* Side panel */
.sidepanel {
  width: 160px;
  border-left: 1px solid #e2e8f0;
  background: #fff;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.sp-header {
  display: flex; align-items: center; gap: 6px;
  padding: 10px 10px 8px;
  border-bottom: 1px solid #f1f5f9;
  background: #f8fafc;
}
.sp-title { font-size: 11px; font-weight: 700; color: #0f172a; }
.sp-section {
  padding: 8px 10px;
  border-bottom: 1px solid #f8fafc;
}
.sp-section--last { border-bottom: none; }
.sp-label {
  font-size: 8.5px; font-weight: 700;
  letter-spacing: 0.08em; text-transform: uppercase;
  color: #94a3b8; margin-bottom: 6px;
}
.sp-summary-lines { display: flex; flex-direction: column; gap: 4px; }
.sp-line { height: 7px; background: #e2e8f0; border-radius: 3px; }
.sp-tools { display: flex; flex-direction: column; gap: 4px; }
.sp-tool {
  display: flex; align-items: center; gap: 5px;
  padding: 4px 6px;
  border-radius: 6px;
  font-size: 9.5px; color: #6b7280;
  background: #f8fafc;
}
.sp-tool--active {
  background: #eef2ff; color: #4f46e5;
  font-weight: 600;
}
.sp-word-box {
  display: flex; align-items: center; justify-content: space-between;
  padding: 5px 7px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
}
.sp-word-text { font-size: 10px; color: #4f46e5; font-weight: 600; }
.sp-word-explain { font-size: 9px; color: #2563eb; font-weight: 700; }

/* ══════════════════════════════════════════
   FEATURES
   ══════════════════════════════════════════ */
.section-features { padding: 96px 0; }

.features-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 18px;
  margin-top: 8px;
}
.feature-card {
  padding: 28px 22px;
  border-radius: 20px;
  background: rgba(255,255,255,0.60);
  border: 1px solid rgba(255,255,255,0.88);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  box-shadow: 0 4px 24px rgba(99,120,255,0.07);
  transition: box-shadow 0.2s, transform 0.2s;
  display: flex; flex-direction: column; gap: 12px;
}
.feature-card:hover { transform: translateY(-4px); box-shadow: 0 16px 40px rgba(99,120,255,0.12); }
.feature-icon {
  width: 44px; height: 44px; border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.feature-icon--blue   { background: #eff6ff; color: #2563eb; }
.feature-icon--violet { background: #f5f3ff; color: #7c3aed; }
.feature-icon--green  { background: #f0fdf4; color: #16a34a; }
.feature-icon--amber  { background: #fffbeb; color: #d97706; }
.feature-card h3 { font-size: 16px; font-weight: 700; color: #0f172a; margin: 0; }
.feature-card p  { font-size: 13.5px; color: #6b7280; line-height: 1.68; margin: 0; }

/* ══════════════════════════════════════════
   HOW TO USE
   ══════════════════════════════════════════ */
.section-howto { padding: 0 0 96px; }

.steps { display: flex; flex-direction: column; gap: 0; margin-top: 8px; }

.step {
  background: rgba(255,255,255,0.58);
  border: 1px solid rgba(255,255,255,0.88);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border-radius: 24px;
  padding: 40px 44px;
  box-shadow: 0 4px 24px rgba(99,120,255,0.06);
}

.step-divider { height: 16px; }

.step-num {
  width: 40px; height: 40px; border-radius: 50%;
  background: linear-gradient(135deg, #2563eb, #7c3aed);
  color: #fff; font-size: 17px; font-weight: 800;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 4px 14px rgba(37,99,235,0.28);
  margin-bottom: 24px;
}

.step-body {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 48px;
  align-items: center;
}

/* step visual areas */
.step-visual {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 140px;
}

/* Step 1 — Chrome store card mock */
.chrome-store-card {
  display: flex; align-items: center; gap: 14px;
  padding: 16px 20px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.08);
  width: 280px;
}
.csc-icon { flex-shrink: 0; }
.csc-info { flex: 1; }
.csc-name { font-size: 15px; font-weight: 700; color: #0f172a; margin-bottom: 3px; }
.csc-meta { font-size: 12px; color: #9ca3af; }
.csc-btn {
  padding: 7px 18px;
  background: #1a73e8;
  color: #fff;
  font-size: 13px; font-weight: 700;
  border-radius: 8px;
}

/* Step 2 — Toolbar mock */
.toolbar-mock {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 12px 16px;
  display: flex;
  align-items: center;
  gap: 10px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.06);
}
.toolbar-puzzle {
  width: 28px; height: 28px;
  background: #fff; border: 1px solid #e2e8f0; border-radius: 6px;
  display: flex; align-items: center; justify-content: center;
}
.toolbar-ext-item {
  display: flex; align-items: center; gap: 6px;
  padding: 6px 10px;
  border-radius: 8px;
  font-size: 12px; color: #374151; font-weight: 500;
  position: relative;
}
.toolbar-ext-item--active {
  background: #eef2ff;
  color: #4f46e5;
  border: 1px solid #c7d2fe;
}
.toolbar-arrow {
  position: absolute;
  top: -18px; left: 50%;
  transform: translateX(-50%);
  font-size: 14px; color: #4f46e5;
  animation: arrow-bounce 1.5s ease-in-out infinite;
}
@keyframes arrow-bounce {
  0%, 100% { transform: translateX(-50%) translateY(0); }
  50%       { transform: translateX(-50%) translateY(-4px); }
}

/* Step 3 — Use mock */
.use-tabs {
  display: flex; gap: 4px; margin-bottom: 10px;
}
.use-tab {
  padding: 5px 12px;
  border-radius: 999px;
  font-size: 12px; font-weight: 600; color: #6b7280;
  background: #f1f5f9;
}
.use-tab--active {
  background: #eef2ff; color: #4f46e5;
}
.use-content {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 4px 16px rgba(0,0,0,0.06);
}
.use-textarea {
  padding: 14px 14px 20px;
  font-size: 12px; color: #94a3b8;
  min-height: 60px;
  border-bottom: 1px solid #f1f5f9;
}
.use-submit {
  padding: 10px 14px;
  font-size: 12px; font-weight: 700;
  color: #2563eb;
  background: #f8fafc;
  text-align: right;
}

/* Step text */
.step-text { display: flex; flex-direction: column; gap: 14px; }
.step-text h3 { font-size: 22px; font-weight: 800; color: #0f172a; margin: 0; letter-spacing: -0.02em; }
.step-text p  { font-size: 15px; color: #4b5563; line-height: 1.75; margin: 0; }
.step-tip {
  font-size: 13.5px !important;
  color: #6b7280 !important;
  background: #fefce8;
  border: 1px solid #fde68a;
  border-radius: 10px;
  padding: 10px 14px !important;
}
.step-list {
  list-style: none; padding: 0; margin: 0;
  display: flex; flex-direction: column; gap: 8px;
}
.step-list li {
  font-size: 14.5px; color: #4b5563;
  padding-left: 18px; position: relative; line-height: 1.6;
}
.step-list li::before {
  content: '·';
  position: absolute; left: 4px; color: #7c3aed; font-weight: 900;
}
.btn-step-install {
  display: inline-flex; align-items: center;
  font-size: 14px; font-weight: 600; color: #2563eb;
  text-decoration: none;
  transition: color 0.15s;
}
.btn-step-install:hover { color: #4f46e5; }

/* ══════════════════════════════════════════
   CTA BANNER
   ══════════════════════════════════════════ */
.section-cta { padding: 32px 0 80px; }
.cta-panel {
  background: linear-gradient(135deg, #1e3a8a 0%, #4c1d95 100%);
  border-radius: 28px;
  padding: 52px 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 32px;
  box-shadow: 0 20px 60px rgba(37,99,235,0.25);
}
.cta-text h2 {
  font-size: 30px; font-weight: 800; letter-spacing: -0.03em;
  color: #fff; margin: 0 0 10px;
}
.cta-text p { font-size: 16px; color: rgba(255,255,255,0.65); margin: 0; }

/* ══════════════════════════════════════════
   FOOTER
   ══════════════════════════════════════════ */
.footer {
  background: linear-gradient(135deg, #1e3a8a 0%, #312e81 100%);
  padding: 40px 0;
}
.footer-inner {
  display: flex; align-items: center;
  justify-content: space-between;
  flex-wrap: wrap; gap: 16px;
}
.footer-left { display: flex; flex-direction: column; gap: 4px; }
.footer-logo { font-size: 15px; font-weight: 700; color: #fff; }
.footer-tagline { font-size: 13px; color: rgba(255,255,255,0.45); margin: 0; }
.footer-links { display: flex; gap: 24px; }
.footer-link {
  font-size: 13px; font-weight: 500;
  color: rgba(255,255,255,0.55);
  text-decoration: none;
  transition: color 0.2s;
}
.footer-link:hover { color: #fff; }
.footer-copy { font-size: 13px; color: rgba(255,255,255,0.35); margin: 0; }

/* ══════════════════════════════════════════
   RESPONSIVE
   ══════════════════════════════════════════ */
@media (max-width: 900px) {
  .hero-inner { grid-template-columns: 1fr; gap: 48px; }
  .hero-visual { order: -1; }
  .browser-mock { max-width: 380px; }
  .features-grid { grid-template-columns: repeat(2, 1fr); }
  .step-body { grid-template-columns: 1fr; gap: 28px; }
  .step-visual { order: -1; }
  .cta-panel { flex-direction: column; align-items: flex-start; padding: 36px 28px; }
}
@media (max-width: 600px) {
  .nav-links { display: none; }
  .features-grid { grid-template-columns: 1fr; }
  .step { padding: 28px 20px; }
  .container { padding: 0 20px; }
  .hero { padding: 80px 0 60px; }
}
</style>
