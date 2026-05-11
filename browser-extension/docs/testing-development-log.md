# Testing Development Log

Last updated: 2026-05-11

This development testing log records validation commands, manual checks, known gaps, and regression items for the Clearead browser extension.

## Standard Local Checks

Run from `browser-extension/` unless noted otherwise.

```bash
node scripts/validate-extension.js
node --check src/background/service-worker.js
node --check src/content/page-tools.js
node --check src/sidepanel/sidepanel.js
node --check src/popup/popup.js
```

Run from the repository root:

```bash
git diff --check -- browser-extension
rg -n "<all_urls>|\\*://\\*/\\*|content_scripts|chrome\\.storage\\.local|chrome\\.storage\\.sync|localStorage|https?://.*\\.js|script src=.*https?://|clipboard" browser-extension
```

Notes:

- `npm run validate` is defined. The equivalent `node scripts/validate-extension.js` command is useful in PowerShell environments where `npm` is outside PATH.
- `git diff --check` may show Windows line-ending warnings. Treat those warnings as line-ending noise after confirming there are no whitespace error lines.

## Validator Coverage

The validation script currently checks:

- Manifest V3.
- Minimum Chrome version.
- Side panel path.
- Popup path.
- Background service worker path.
- Required packaged icons and PNG dimensions.
- Allowed extension permissions only.
- Narrow deployed backend host permission only.
- Static `content_scripts` absence.
- Required local source files.
- Classic background service worker syntax.
- Common unsafe source patterns, including HTML string injection APIs, `eval`, `new Function`, remote JavaScript URLs, non-session extension storage, localStorage, and credential-like names.

## Manual Chrome Checks Performed

Foundation:

- Loaded `browser-extension/` as an unpacked extension.
- Confirmed side panel could open.
- Confirmed Phase 1 initial workflow loaded.

Text processing workflow:

- Tested pasted text summary against deployed Azure backend.
- Confirmed Summary ready status.
- Confirmed deployed `/api/plugin/summary` returns `overallSummary.heading` and `overallSummary.text` without returning block summaries.
- Confirmed result displays only the full-document `overallSummary.text` value.
- Confirmed pasted text is sent only after Summary is run.
- Confirm Summary runs from the text box with Enter, and Ctrl+Enter or Shift+Enter inserts a line break instead.
- Later UI change confirmed the status strip and Result panel are hidden before Summary is used.

Popup activation and page access:

- Confirmed toolbar click opens a popup activation step.
- Confirmed Open Clearead for this page opens the side panel.
- Confirmed page tools work after popup activation on normal webpages.
- Confirmed restricted page errors are separated from ordinary active-tab access errors.

Readable page tools:

- Tested readable font application and reset on normal webpages.
- Added Font chooser states for Original, Verdana, OpenDyslexic, and Calibri.
- Added Reading ruler chooser states for No ruler, Highlight, Lens, and Line guide.
- Confirmed page tools use user-triggered programmatic injection, not static content scripts.

Dictionary:

- Confirmed right-click dictionary is default-off.
- Confirmed enabling the side panel Right-click lookup button creates the selected-text context menu item.
- Confirmed disabling removes the context menu item.
- Confirm Right-click lookup button state is loaded from the real background/session state, and failed updates keep the button aligned with background state.
- Confirm the one-line dictionary word input accepts one English word, rejects phrases or sentences before a backend request, and shows a backend dictionary card after Explain or Enter.
- Confirm the side panel dictionary Explain flow sends only the validated word to the deployed Clearead dictionary backend.
- Confirmed selected text is capped, validated as one English word, and only then sent to the deployed Clearead dictionary backend after the user clicks the context menu item.
- Recent dictionary UI target: selected text opens a large card with Simple meaning, Word parts, Meaning from parts, pronunciation, and close controls.
- Confirm that the dictionary card omits Save.
- Confirm dictionary card stays compact, uses a speech-bubble tail near the selected word, supports two or more word-part rows, and closes when clicking outside the card.
- Confirm the right-click dictionary card shows a Looking up state before the backend result replaces it.

Icons and branding:

- Generated PNG icons at 16, 32, 48, and 128 pixels.
- Validator confirmed icon dimensions.
- Popup and side panel were visually aligned with Clearead website colors.

## Recent Regression Tests To Run

Side panel state sync:

- Open a normal webpage.
- Open Clearead from the toolbar popup.
- Apply Verdana, OpenDyslexic, or Calibri.
- Close the side panel.
- Reopen the side panel.
- Confirm the selected Font button matches the actual page font.
- Turn on Highlight, Lens, or Line guide.
- Close and reopen the side panel.
- Confirm the selected Reading ruler button matches the actual page ruler.
- With Lens active, navigate within the same tab, such as from Unit to Grades on a learning site, and confirm the side panel changes back to No ruler if the page removed the Lens overlay.
- Click No ruler and confirm the overlay disappears and the button state changes.
- Confirm Highlight and Line guide keep the whole ruler rectangle transparent, use blue top/bottom borders with blue glow fading outward, and dim the page outside the ruler slightly.
- On a dark-background webpage, confirm Highlight and Line guide remain visible and Lens preserves the page's dark surface.
- Reload the extension while a page tool is visible, then reopen Clearead from the toolbar popup and confirm state sync recovers from the existing page DOM.
- Open the side panel without a current page connection and confirm it says: "In Chrome, click Extensions (puzzle icon) > Clearead > Open Clearead for this page."
- Open a direct PDF, DOCX, DOC, or TXT file URL and confirm it says: "File pages may not support page tools. Click Open website to upload the file."

Lens regression:

- Reload the extension and refresh the target webpage before testing.
- Select Lens.
- Confirm the magnifier follows the pointer horizontally and vertically.
- Confirm the magnifier shows a single local magnified page view.
- Confirm Lens remains readable on dark-background webpages.
- Confirm ordinary webpage dropdown menus remain visible inside Lens after the menu opens.
- Confirm page clicks pass through the overlay because it uses `pointer-events: none`.
- Confirm disabling the ruler removes the lens overlay.
- Test after scrolling halfway down a long page.
- Confirm the Reading ruler section says: "Best on text pages. If Lens looks blank, try Highlight or Line guide."
- Select Lens and confirm the status still shows the current Font/Ruler state while a separate Lens tip appears below it.
- On a media-heavy or animation-heavy page, confirm Lens either remains usable or says: "Lens stopped on this dynamic page. Try Highlight or Line guide."

Background service worker regression:

- Open `chrome://extensions`.
- Clear extension errors.
- Reload the extension.
- Confirm no new `Cannot use import statement outside a module` error appears.
- Confirm `service-worker.js` starts with classic worker syntax.

Chrome Store readiness regression:

- Confirm host permissions stay narrow.
- Confirm executable code is packaged locally.
- Confirm page-tool injection remains programmatic.
- Confirm storage contains only session state.
- Confirm pasted text network calls only go to the deployed Clearead backend after Summary is run.
- Confirm dictionary network calls send only a validated one-word `{ "word": string }` request to the deployed Clearead backend after Explain, Enter, or the right-click menu item.

## Known Current Gaps

- Chrome Web Store listing and privacy field text exists in `docs/chrome-store-submission.md`; final dashboard copy/paste review is still pending.
- Public privacy policy text exists in `docs/privacy-policy.md`; public hosting URL is still pending.
- Backend retention/logging behavior still needs confirmation.
- Lens has manual smoke-test coverage from the release review pass; broader cross-site regression testing is still recommended.
- Automated browser test coverage for the unpacked extension UI remains future work.
- Final packaged ZIP audit remains pending.

## Test Evidence Locations

- Extension source, docs, and validation scripts live under `browser-extension/`.
