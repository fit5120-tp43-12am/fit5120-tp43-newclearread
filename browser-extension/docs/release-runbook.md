# Browser Extension Release Runbook

This runbook is for validating, packaging, and maintaining Clearead extension releases on the Chrome Web Store.

## 1. Confirm Release Scope

- Branch: `dev`
- Extension root: `browser-extension/`
- Public listing: `https://chromewebstore.google.com/detail/clearead/jlohhhioeodjkkeahcoelbbnkaigflkn`
- Production package contents: `manifest.json`, `src/`, `public/`
- Store ZIP contents are limited to production extension files.

## 2. Final Manual QA

Use Chrome with the unpacked `browser-extension/` folder.

- Popup opens from the toolbar action.
- Popup "Open Clearead for this page" opens the side panel.
- Summary works against the deployed backend.
- Empty Summary input shows a clear error.
- Over-limit Summary input cannot be submitted.
- Open website links work from popup and side panel.
- Original, Verdana, OpenDyslexic, and Calibri apply and restore correctly.
- No ruler, Highlight, Lens, and Line guide apply and restore correctly.
- Lens works on a normal text page.
- Lens either works or gives a clear fallback message on a complex page.
- Restricted pages such as `chrome://extensions` show a clear unsupported-page message.
- Direct PDF/DOC/DOCX/TXT URLs tell the user to use the full website upload flow.
- Right-click lookup is off by default.
- Right-click lookup can be enabled and disabled from the side panel.
- Right-click lookup rejects phrases before any backend dictionary request.
- Right-click lookup shows Loading, then a dictionary card or a clear error.
- Side panel Word box accepts one English word and rejects phrases.
- Dictionary cards omit Save.
- Extension storage contains only the session toggle, recent page activation metadata, and short error notices.

Record any final manual QA notes in `docs/testing-development-log.md`.

## 3. Validate

From `browser-extension/`:

```powershell
npm run validate
```

Alternative command for environments with Node.js available but no npm:

```powershell
node scripts\validate-extension.js
```

Expected output:

```text
Extension validation passed.
```

## 4. Package

From `browser-extension/`:

```powershell
npm run package
```

Alternative command for environments with Node.js available but no npm:

```powershell
node scripts\package-extension.js
```

Expected output:

```text
Extension validation passed.
Created ...\browser-extension\dist\clearead-extension-0.1.2.zip
Packaged entries: manifest.json, public/, src/
```

Upload the ZIP from:

```text
browser-extension/dist/clearead-extension-0.1.2.zip
```

## 5. Dashboard Materials

Use `docs/chrome-store-submission.md` for store listing maintenance:

- Store summary
- Detailed description
- Single purpose
- Permission justifications
- Remote code declaration
- Data collection disclosure
- Limited Use certification
- Reviewer test instructions

Publish `docs/privacy-policy.md` at a public URL and use that URL in the Developer Dashboard.

## 6. Release Submission Checks

Confirm these items before publishing a new or updated package:

- Confirm production backend URL is final.
- Confirm backend request logging and retention.
- Confirm server-side AI/model provider disclosures.
- Confirm privacy policy public URL works.
- Confirm store listing screenshots and promo image match the current extension UI.
- Confirm all dashboard privacy fields match the privacy policy and actual extension behavior.
