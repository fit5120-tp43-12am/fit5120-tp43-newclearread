# Clearead Browser Extension

This folder contains the Manifest V3 Clearead Chrome extension. It includes the pasted-text Summary workflow, user-triggered readable page tools, a backend-backed right-click dictionary flow for ordinary webpages, a direct link back to the Clearead website, and packaged extension icons.

## Current Workflow

- Starts from a small toolbar popup, then opens as a Chrome side panel.
- Lets the user open the full Clearead website at `https://clearead.azurewebsites.net/` from the popup or side panel.
- Includes packaged extension icons for toolbar, extension management, and install contexts.
- Lets the user paste text manually.
- Shows live word and character counts.
- Enforces the backend limit of 50,000 characters.
- Sends text to `POST https://clear-read-a3c2gyajcjf5agfd.australiaeast-01.azurewebsites.net/api/plugin/summary` only when the user runs Summary.
- Displays only returned full-document summary text in the result panel.
- Shows clear loading, success, empty-input, over-limit, backend-timeout, backend-unavailable, and backend-validation states.
- Uses the shared Clearead backend processing route for Summary.
- Lets the user choose Original, Verdana, OpenDyslexic, or Calibri page font styling from the side panel. OpenDyslexic WOFF2 font files are packaged locally with the extension.
- Applies wider line height, word spacing, and letter spacing with the chosen readable font.
- Lets the user choose No ruler, Highlight, Lens, or Line guide reading ruler styles from the side panel. Reading rulers are intended for text pages. Lens is a local pointer-following magnifier that clones the current page DOM into a non-interactive overlay and enlarges the area under the pointer. If a dynamic page changes too rapidly, Lens stops and tells the user to try Highlight or Line guide.
- Lets the user opt in from the side panel dictionary button, then select one English word on a normal webpage, right-click it, and choose Explain with Clearead to show a dictionary card on the page. The side panel also includes a one-line word input with an Explain button that uses the same deployed Clearead dictionary backend. Sentence or phrase selections are rejected before any backend request.

## How To Load In Chrome

1. Open Chrome.
2. Go to `chrome://extensions`.
3. Turn on Developer mode.
4. Click Load unpacked.
5. Select this folder: `browser-extension/`.
6. Click the Clearead extension action icon.
7. In the popup, click Open Clearead for this page to open the side panel.
8. In the popup or side panel, click Open website to confirm the full Clearead website opens in a normal tab.

## How To Test The Summary Flow

1. Confirm the shared backend is available at `https://clear-read-a3c2gyajcjf5agfd.australiaeast-01.azurewebsites.net`.
2. Load the unpacked extension from `browser-extension/`.
3. Click the Clearead toolbar icon, then click Open Clearead for this page.
4. Paste text into the textarea.
5. Click Summary or press Enter from the text box.
6. Confirm the result appears above Page tools and renders only the full-document summary text.
7. Temporarily block network access or point a development build at an unavailable backend to confirm the side panel shows a useful backend-unavailable error.

Developers may point a local-only test build at `http://localhost:8000`, but the normal demo path uses the deployed backend origin above. Because the background service worker is kept as a classic worker, update both `src/shared/config.js` and the backend constants in `src/background/service-worker.js` for local backend testing.

## How To Test Page Tools

1. Reload the unpacked extension from `browser-extension/`.
2. Open a normal webpage.
3. Click the Clearead toolbar icon and confirm the popup opens instead of the side panel opening immediately.
4. Click Open Clearead for this page and confirm the side panel opens.
5. In Font, click Verdana, OpenDyslexic, and Calibri and confirm common text containers visibly change font and spacing.
6. Click Original and confirm the Clearead-added font styles are removed.
7. In Reading ruler, confirm the guidance says: "Best on text pages. If Lens looks blank, try Highlight or Line guide." When Lens is selected, confirm a separate Lens tip appears below the current Font/Ruler status.
8. Click No ruler and confirm the ruler disappears.
9. Try a restricted page such as `chrome://extensions` and confirm Clearead says: "Chrome blocks tools on this page. Try another webpage."
10. Try a direct PDF, DOCX, DOC, or TXT file URL and confirm Clearead says: "File pages may not support page tools. Click Open website to upload the file."
11. If a normal webpage was opened before Clearead had current-tab access, confirm Clearead says: "Need page access. In Chrome, click Extensions (puzzle icon) > Clearead > Open Clearead for this page."

## How To Test Right-Click Dictionary

1. Reload the unpacked extension from `browser-extension/`.
2. Open a normal webpage.
3. Select text and right-click before enabling Dictionary; confirm the Clearead dictionary item does not appear.
4. Click the Clearead toolbar icon, then click Open Clearead for this page.
5. In the side panel Dictionary section, click the Right-click lookup button and confirm it turns blue with a check.
6. Select a word such as `misinterpretation`.
7. Right-click the selected word and confirm the Clearead dictionary menu item appears.
8. Click it and confirm a dictionary card appears near the selection, shows a Looking up state, then displays Simple meaning, Word parts, and Meaning from parts sections.
9. Confirm the card has a pronunciation button and close button, but no Save action.
10. Click the Right-click lookup button again and confirm it turns off.
11. Select text and right-click again; confirm the Clearead dictionary item no longer appears.
12. Confirm Summary, the font choices, No ruler, Highlight, local Lens magnification, Line guide, and the Right-click lookup button still work.
13. Try a restricted page such as `chrome://extensions` and confirm Clearead does not offer or cannot run page tools on that page.
14. Select a phrase or sentence and confirm Clearead asks for one English word instead of calling the dictionary backend.

## How To Test Website Links

1. Reload the unpacked extension from `browser-extension/`.
2. Click the Clearead toolbar icon.
3. Click Open website in the popup and confirm `https://clearead.azurewebsites.net/` opens in a normal tab.
4. Open the side panel and click Open website in the header.
5. Confirm the website link does not request extra extension page permissions.

## Permissions

The extension requests:

- `sidePanel`: allows Clearead to use Chrome's side panel API.
- `activeTab`: gives temporary access to the current tab after a user action so page tools can run on that active page.
- `scripting`: allows Clearead to inject its local packaged page-tool script only after the user clicks a page-tool button.
- `contextMenus`: lets Clearead add an opt-in right-click menu item that appears only after the user enables it in the side panel and selects text on normal `http` and `https` webpages.
- `storage`: keeps session-only extension state: whether the user enabled the right-click dictionary, plus the recent page activation tab/window/time used to keep side panel state sync stable across Manifest V3 service worker sleep. It does not store pasted text, selected text, page content, summaries, or dictionary results.
- `host_permissions: ["https://clear-read-a3c2gyajcjf5agfd.australiaeast-01.azurewebsites.net/*"]`: allows the extension to send user-submitted Summary text and explicit one-word dictionary lookups to the shared Clearead backend.

The extension does not request `<all_urls>`, `tabs`, clipboard permissions, broad host permissions, or static `content_scripts`.

The Clearead website link does not require a host permission. It opens `https://clearead.azurewebsites.net/` as a normal external webpage tab.

The manifest declares local PNG icons at 16, 32, 48, and 128 pixels. These files are packaged with the extension and are not loaded from a remote URL.

The manifest also declares the packaged OpenDyslexic WOFF2 files as web-accessible font resources for normal `http` and `https` webpages so the injected readable-font CSS can load the local font files. No executable code is exposed this way.

## Data Flow

Pasted text is not sent while the user types. When the user runs Summary, the side panel sends this request body to the backend:

```json
{ "text": "the pasted text" }
```

The website frontend and the extension are separate frontend clients for the same Clearead backend. The side panel calls the plugin summary route and renders the returned `overallSummary.text` value. It does not display the returned `overallSummary.heading`. The extension itself does not save pasted text, call OpenAI or other third-party AI APIs, call analytics services, include API keys, read webpage content automatically, or load remote executable code.

The website entry point is separate from the backend API origin. `https://clearead.azurewebsites.net/` is opened only when the user clicks Open website. It is not used as a host permission and the extension does not inspect that website tab.

Page tools do not send page content to the backend. The toolbar popup is an explicit activation step for the current page. After the user clicks Open Clearead for this page, the side panel opens. The service worker can then query the active page to sync the side panel button state, and page-tool buttons can apply the selected tool. In both cases the service worker checks the active tab, rejects known restricted browser pages, and injects `src/content/page-tools.js` from the packaged extension only for that active tab when needed. The injected script adds or removes Clearead-owned style and overlay elements only. Lens mode clones the current page DOM locally inside the same tab for magnification, refreshes that local clone after page DOM changes such as dropdown menus, removes scripts, inline event handlers, form actions, and embedded media sources from the clone, and keeps it non-interactive. Lens is intended for text pages; if a dynamic page changes too rapidly, Lens stops and tells the user to try Highlight or Line guide. Page tools do not send page text, persist page-tool state, or run automatically on every page.

Right-click dictionary lookup uses Chrome's selection context menu only after the user turns on the Right-click lookup button in the side panel. The menu is off by default. The extension stores that on/off flag in `chrome.storage.session`, which is memory-backed and cleared when the extension is disabled, reloaded, updated, or when the browser restarts. When enabled, the menu item appears only when the user has selected text on a normal `http` or `https` webpage. After the user clicks the Clearead menu item, the service worker uses only `info.selectionText`, trims and normalizes whitespace, limits it to 80 characters, and confirms it is one English word before any backend request. Valid lookups are sent to `POST /api/dictionary` on the deployed Clearead backend with `{ "word": string }`. The service worker then injects the local packaged page-tool script if needed and asks it to render an on-page dictionary card. The selected word is not stored, no surrounding page content is read, and sentence or phrase selections are rejected locally. The one-line side panel word input uses the same backend dictionary route after the user clicks Explain or presses Enter. The dictionary card has no Save action. The extension also stores a recent page activation tab/window/time record in `chrome.storage.session` so page-tool state sync remains stable across Manifest V3 service worker sleep; this record does not contain page text or selected text.

After a Summary request reaches the Clearead backend, the plugin summary route performs only the backend full-document summary flow and returns `overallSummary`. It does not need the website block segmentation or block-level summary result for the extension. Any API keys or secrets for those services must stay on the backend side and must not be stored in the extension.

The deployed backend origin is currently the Azure backend URL found in workflow config. The website origin is currently `https://clearead.azurewebsites.net/`. The final production backend origin, website origin, user-facing privacy policy wording, and final Chrome Web Store data disclosure still need review before release.

## Unsupported Pages

Chrome blocks extension scripting on some pages by design. Clearead page tools are expected not to run on pages such as `chrome://`, `edge://`, `about:`, Chrome Web Store pages, extension pages, some browser PDF viewers, and other restricted contexts. The side panel reports a friendly unsupported-page message instead of claiming the tools worked.

For direct PDF, DOCX, DOC, or TXT file URLs, Clearead points users to the full website upload flow instead of promising page tools on browser-controlled file viewers.

Clearead also distinguishes temporary `activeTab` access problems from browser-restricted pages. If Chrome reports that the extension does not currently have access to an otherwise normal webpage, the side panel says: "Need page access. In Chrome, click Extensions (puzzle icon) > Clearead > Open Clearead for this page."

## Current Extension Scope

- Summary uses the shared deployed Clearead backend plugin summary route.
- Dictionary uses the shared deployed Clearead backend dictionary route for explicit one-word lookups.
- Page tools run on normal webpages after user activation.
- File upload, sentence-level dictionary lookup, automatic webpage scanning, static content scripts, and final Chrome Web Store listing text are outside this extension build.

## Validation

Run this from the `browser-extension/` folder:

```bash
npm run validate
```

The validation script checks Manifest V3 setup, required local files, local icon files and PNG dimensions, the side panel, background, the known popup activation file, page-tool file, absence of static content scripts, narrow permissions, and common unsafe source patterns such as HTML string injection, `eval`, remote JavaScript URLs, non-session extension storage, and credential-like names.

This build should not be described as Chrome Web Store ready until the final manual review, privacy policy, production backend confirmation, and store listing work are complete.
