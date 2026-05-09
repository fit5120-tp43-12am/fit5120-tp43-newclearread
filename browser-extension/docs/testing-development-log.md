# Testing Development Log

Last updated: 2026-05-09

This is a development testing log for the Clearead browser extension. It records validation commands, manual checks, known gaps, and regression items. It is not a final QA sign-off.

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

- `npm run validate` is defined, but the local PowerShell environment previously did not have `npm` on PATH, so the equivalent `node scripts/validate-extension.js` command has been used.
- `git diff --check` may show Windows line-ending warnings. Those are not whitespace errors.

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
- No static `content_scripts`.
- Required local source files.
- Classic background service worker without static `import` or `export`.

## Manual Chrome Checks Performed

Foundation:

- Loaded `browser-extension/` as an unpacked extension.
- Confirmed side panel could open.
- Confirmed Phase 1 placeholder workflow loaded.

Summary workflow:

- Tested pasted text summary against deployed Azure backend.
- Confirmed Summary complete status.
- Confirmed result displays summary text only.
- Confirmed pasted text is sent only after Summary click.
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
- Confirm Right-click lookup button state is loaded from the real background/session state, and failed updates do not leave the button falsely active.
- Confirm the one-line dictionary word input accepts pasted words or short phrases, normalizes whitespace, and shows a local demo dictionary card after Explain or Enter.
- Confirm the side panel dictionary Explain flow does not send the pasted word to the backend or store it.
- Confirmed selected text is processed locally and capped.
- Recent dictionary UI target: selected text opens a large card with Simple meaning, Word parts, Meaning from parts, pronunciation, and close controls.
- Confirm that the dictionary card does not include a Save action.
- Confirm dictionary card stays compact, uses a speech-bubble tail near the selected word, supports two or more word-part rows, and closes when clicking outside the card.

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
- Click No ruler and confirm the overlay disappears and the button state changes.
- Confirm Highlight and Line guide keep the whole ruler rectangle transparent, use blue top/bottom borders with blue glow fading outward, and dim the page outside the ruler slightly.
- Reload the extension while a page tool is visible, then reopen Clearead from the toolbar popup and confirm state sync recovers from the existing page DOM.
- Open the side panel without a current page connection and confirm it asks for toolbar popup reconnection instead of showing a false synced state.

Lens regression:

- Reload the extension and refresh the target webpage before testing.
- Select Lens.
- Confirm the magnifier follows the pointer horizontally and vertically.
- Confirm the magnifier does not show extracted multi-line text or duplicated rows.
- Confirm it does not block page clicks because the overlay uses `pointer-events: none`.
- Confirm disabling the ruler removes the lens overlay.
- Test after scrolling halfway down a long page.

Background service worker regression:

- Open `chrome://extensions`.
- Clear extension errors.
- Reload the extension.
- Confirm no new `Cannot use import statement outside a module` error appears.
- Confirm `service-worker.js` starts as a classic worker without static imports.

Chrome Store readiness regression:

- Confirm no broad host permissions.
- Confirm no remote executable code.
- Confirm no static content scripts.
- Confirm no text, selected text, or page content is stored.
- Confirm pasted text network calls only go to the deployed Clearead backend after Summary click.

## Known Current Gaps

- Final Chrome Web Store listing text has not been written.
- Final public privacy policy has not been written.
- Backend retention/logging behavior still needs confirmation.
- Lens usability still needs more manual testing across different websites.
- No automated browser test suite exists for the unpacked extension UI.
- No final packaged ZIP audit has been completed.

## Test Evidence Locations

- Extension source, docs, and validation scripts live under `browser-extension/`.
