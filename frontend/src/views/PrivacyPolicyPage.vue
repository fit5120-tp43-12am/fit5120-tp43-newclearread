<template>
  <div class="page">

    <!-- Navbar -->
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
        </ul>
      </div>
    </nav>

    <!-- Content -->
    <main class="main">
      <div class="container">

        <div class="back-link">
          <RouterLink to="/" class="back-btn">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M13 8H3M3 8L7 4M3 8L7 12" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            Back to Home
          </RouterLink>
        </div>

        <div class="policy-card">
          <div class="policy-header">
            <h1 class="policy-title">Privacy Policy</h1>
            <p class="policy-meta">Clearead · Last updated: May 2026</p>
          </div>

          <div class="policy-body">

            <section class="policy-section">
              <h2>1. Overview</h2>
              <p>
                Clearead is a web application and browser extension designed to support
                university students with dyslexia. We are committed to protecting your
                privacy. This policy explains what information we collect, how we use it,
                and your rights.
              </p>
            </section>

            <section class="policy-section">
              <h2>2. Information We Collect</h2>
              <p>Clearead collects only the minimum information necessary to provide its services:</p>
              <ul>
                <li>
                  <strong>Text you submit</strong> — When you use the Reading Support feature,
                  the text you paste or upload is sent to our backend for processing (simplification,
                  summarisation, and key-point extraction). This text is processed in real time and
                  is <strong>not stored</strong> on our servers after the response is returned.
                </li>
                <li>
                  <strong>Words you look up</strong> — When you use the Dictionary feature,
                  the word you search is sent to our backend. It is not linked to any personal
                  identifier and is not retained.
                </li>
                <li>
                  <strong>Saved words</strong> — Words you choose to save are stored locally
                  in your browser's <code>localStorage</code>. They never leave your device.
                </li>
                <li>
                  <strong>Accessibility preferences</strong> — Font, colour, and spacing
                  settings are stored in your browser's <code>localStorage</code> and are
                  never transmitted to our servers.
                </li>
              </ul>
            </section>

            <section class="policy-section">
              <h2>3. Information We Do Not Collect</h2>
              <ul>
                <li>We do not require you to create an account or log in.</li>
                <li>We do not collect your name, email address, or any contact information.</li>
                <li>We do not use cookies for tracking or advertising.</li>
                <li>We do not sell or share your data with third parties for marketing purposes.</li>
              </ul>
            </section>

            <section class="policy-section">
              <h2>4. Third-Party Services</h2>
              <p>Clearead uses the following third-party services to deliver its features:</p>
              <ul>
                <li>
                  <strong>OpenAI / AI language model</strong> — Used to simplify and summarise
                  text. Text you submit is sent to the AI API. Please refer to the provider's
                  own privacy policy for details on data handling.
                </li>
                <li>
                  <strong>RapidAPI / WordsAPI</strong> — Used to fetch plain-English word
                  definitions. Only the word itself (no personal data) is sent.
                </li>
              </ul>
            </section>

            <section class="policy-section">
              <h2>5. Data Security</h2>
              <p>
                All communication between your browser and our servers uses HTTPS encryption.
                We do not store personal data on our servers. Data held in your browser's
                <code>localStorage</code> is under your control and can be cleared at any time
                through your browser settings.
              </p>
            </section>

            <section class="policy-section">
              <h2>6. Children's Privacy</h2>
              <p>
                Clearead is intended for use by university students (18 years and older).
                We do not knowingly collect any information from children under 13.
              </p>
            </section>

            <section class="policy-section">
              <h2>7. Changes to This Policy</h2>
              <p>
                We may update this Privacy Policy from time to time. Any changes will be
                reflected on this page with an updated date. Continued use of Clearead
                after changes are posted constitutes acceptance of the updated policy.
              </p>
            </section>

            <section class="policy-section policy-section--last">
              <h2>8. Contact</h2>
              <p>
                If you have any questions about this Privacy Policy, please contact the
                Clearead development team via the project repository on GitHub.
              </p>
            </section>

          </div>
        </div>

      </div>
    </main>

    <!-- Footer -->
    <footer class="footer">
      <div class="container footer-inner">
        <div class="footer-left">
          <span class="footer-logo">Clearead</span>
          <p class="footer-tagline">Built for minds that think differently.</p>
        </div>
        <p class="footer-copy">© 2026 Clearead. All rights reserved.</p>
      </div>
    </footer>

  </div>
</template>

<style scoped>
.page {
  min-height: 100vh;
  background: #f4f5ff;
  display: flex;
  flex-direction: column;
}

/* ── Navbar ── */
.navbar {
  position: sticky;
  top: 0;
  z-index: 100;
  background: rgba(244,245,255,0.92);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  box-shadow: 0 1px 0 rgba(99,120,255,0.1);
}
.nav-inner {
  max-width: 1040px;
  margin: 0 auto;
  padding: 0 36px;
  height: 64px;
  display: flex;
  align-items: center;
  gap: 32px;
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

/* ── Main ── */
.main {
  flex: 1;
  padding: 60px 0 80px;
}
.container {
  max-width: 780px;
  margin: 0 auto;
  padding: 0 36px;
}

/* Back link */
.back-btn {
  display: inline-flex; align-items: center; gap: 7px;
  font-size: 14px; font-weight: 500; color: #6366f1;
  text-decoration: none;
  margin-bottom: 32px;
  transition: color 0.15s;
}
.back-btn:hover { color: #4338ca; }

/* Policy card */
.policy-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 20px;
  box-shadow: 0 4px 24px rgba(99,120,255,0.07);
  overflow: hidden;
}

.policy-header {
  padding: 40px 48px 32px;
  border-bottom: 1px solid #f1f5f9;
  background: linear-gradient(135deg, #f5f3ff 0%, #eff6ff 100%);
}
.policy-title {
  font-size: 32px; font-weight: 800;
  letter-spacing: -0.03em; color: #0f172a;
  margin: 0 0 8px;
}
.policy-meta {
  font-size: 13px; color: #94a3b8;
  margin: 0;
}

.policy-body {
  padding: 8px 48px 48px;
}

.policy-section {
  padding: 28px 0;
  border-bottom: 1px solid #f8fafc;
}
.policy-section--last { border-bottom: none; }

.policy-section h2 {
  font-size: 17px; font-weight: 700;
  color: #1e293b; margin: 0 0 12px;
  letter-spacing: -0.02em;
}
.policy-section p {
  font-size: 15px; line-height: 1.78;
  color: #475569; margin: 0 0 12px;
}
.policy-section p:last-child { margin-bottom: 0; }
.policy-section ul {
  margin: 8px 0 0; padding-left: 20px;
  display: flex; flex-direction: column; gap: 10px;
}
.policy-section li {
  font-size: 15px; line-height: 1.7; color: #475569;
}
.policy-section strong { color: #1e293b; }
.policy-section code {
  font-size: 13px; background: #f1f5f9;
  padding: 1px 6px; border-radius: 4px;
  color: #4f46e5; font-family: monospace;
}

/* ── Footer ── */
.footer {
  background: linear-gradient(135deg, #1e3a8a 0%, #312e81 100%);
  padding: 40px 0;
}
.footer-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 16px;
}
.footer-left { display: flex; flex-direction: column; gap: 4px; }
.footer-logo { font-size: 15px; font-weight: 700; color: #fff; }
.footer-tagline { font-size: 13px; color: rgba(255,255,255,0.45); margin: 0; }
.footer-copy { font-size: 13px; color: rgba(255,255,255,0.35); margin: 0; }

@media (max-width: 640px) {
  .nav-links { display: none; }
  .policy-header { padding: 28px 24px 24px; }
  .policy-body { padding: 8px 24px 36px; }
  .container { padding: 0 20px; }
}
</style>
