# Clearead Browser Extension

This folder contains the Manifest V3 Clearead Chrome extension. Phase 7 keeps the pasted-text summary workflow, user-triggered readable page tools, a local right-click dictionary flow for ordinary webpages, a direct link back to the Clearead website, and packaged extension icons.

## Current Workflow

- Starts from a small toolbar popup, then opens as a Chrome side panel.
- Lets the user open the full Clearead website at `https://clearead.azurewebsites.net/` from the popup or side panel.
- Includes packaged extension icons for toolbar, extension management, and install contexts.
- Lets the user paste text manually.
- Shows live word and character counts.
- Enforces the backend limit of 50,000 characters.
- Sends text to `POST https://clear-read-a3c2gyajcjf5agfd.australiaeast-01.azurewebsites.net/api/process-text` only when the user clicks Summary.
- Displays only returned summary text in the result panel.
- Shows clear loading, success, empty-input, over-limit, backend-unavailable, and backend-validation states.
- Keeps Simplify visible but disabled because no stable public simplify endpoint is currently exposed by the backend.
- Lets the user choose Original, Verdana, OpenDyslexic, or Calibri page font styling from the side panel.
- Applies wider line height, word spacing, and letter spacing with the chosen readable font.
- Lets the user choose No ruler, Highlight, Lens, or Line guide reading ruler styles from the side panel. Lens is a local pointer-following magnifier that clones the current page DOM into a non-interactive overlay and enlarges the area under the pointer.
- Lets the user opt in from the side panel dictionary button, then select one word or a short phrase on a normal webpage, right-click it, and choose Explain with Clearead to show a dictionary card on the page. The side panel also includes a one-line word input with an Explain button that shows the same demo dictionary card shape inside the panel. The current dictionary content is local demo placeholder data until a stable backend dictionary function exists.

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
5. Click Summary.
6. Confirm the result appears above Page tools and renders only summaries.
7. Temporarily block network access or point a development build at an unavailable backend to confirm the side panel shows a useful backend-unavailable error.

Developers may point a local-only test build at `http://localhost:8000`, but the normal demo path uses the deployed backend origin above.

## How To Test Page Tools

1. Reload the unpacked extension from `browser-extension/`.
2. Open a normal webpage.
3. Click the Clearead toolbar icon and confirm the popup opens instead of the side panel opening immediately.
4. Click Open Clearead for this page and confirm the side panel opens.
5. In Font, click Verdana, OpenDyslexic, and Calibri and confirm common text containers visibly change font and spacing.
6. Click Original and confirm the Clearead-added font styles are removed.
7. In Reading ruler, click Highlight, Lens, and Line guide and confirm each pointer-following ruler style appears without blocking clicks.
8. Click No ruler and confirm the ruler disappears.
9. Try a restricted page such as `chrome://extensions` and confirm Clearead says Chrome does not allow extensions to modify that page.
10. If a normal webpage was opened before Clearead had current-tab access, confirm Clearead asks the user to open the target webpage, click the toolbar icon, and try the page tool again.

## How To Test Right-Click Dictionary

1. Reload the unpacked extension from `browser-extension/`.
2. Open a normal webpage.
3. Select text and right-click before enabling Dictionary; confirm the Clearead dictionary item does not appear.
4. Click the Clearead toolbar icon, then click Open Clearead for this page.
5. In the side panel Dictionary section, click the Right-click lookup button and confirm it turns blue with a check.
6. Select a word such as `misinterpretation`.
7. Right-click the selected word and confirm the Clearead dictionary menu item appears.
8. Click it and confirm a dictionary card appears near the selection with Simple meaning, Word parts, and Meaning from parts sections.
9. Confirm the card has a pronunciation button and close button, but no Save action.
10. Click the Right-click lookup button again and confirm it turns off.
11. Select text and right-click again; confirm the Clearead dictionary item no longer appears.
12. Confirm Summary, the font choices, No ruler, Highlight, local Lens magnification, Line guide, and the Right-click lookup button still work.
13. Try a restricted page such as `chrome://extensions` and confirm Clearead does not offer or cannot run page tools on that page.

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
- `storage`: keeps one session-only boolean for whether the user enabled the right-click dictionary, so the menu survives Manifest V3 service worker sleep without storing text.
- `host_permissions: ["https://clear-read-a3c2gyajcjf5agfd.australiaeast-01.azurewebsites.net/*"]`: allows the extension side panel to send user-submitted text to the shared Clearead backend for Summary only.

The extension does not request `<all_urls>`, `tabs`, clipboard permissions, broad host permissions, or static `content_scripts`.

The Clearead website link does not require a host permission. It opens `https://clearead.azurewebsites.net/` as a normal external webpage tab.

The manifest declares local PNG icons at 16, 32, 48, and 128 pixels. These files are packaged with the extension and are not loaded from a remote URL.

## Data Flow

Pasted text is not sent while the user types. When the user clicks Summary, the side panel sends this request body to the backend:

```json
{ "text": "the pasted text" }
```

The website frontend and the extension are separate frontend clients for the same Clearead backend processing route. The side panel renders only the backend summary text. The extension itself does not save pasted text, call OpenAI or other third-party AI APIs, call analytics or dictionary services, include API keys, read webpage content automatically, or load remote executable code.

The website entry point is separate from the backend API origin. `https://clearead.azurewebsites.net/` is opened only when the user clicks Open website. It is not used as a host permission and the extension does not inspect that website tab.

Page tools do not send page content to the backend. The toolbar popup is an explicit activation step for the current page. After the user clicks Open Clearead for this page, the side panel opens. The service worker can then query the active page to sync the side panel button state, and page-tool buttons can apply the selected tool. In both cases the service worker checks the active tab, rejects known restricted browser pages, and injects `src/content/page-tools.js` from the packaged extension only for that active tab when needed. The injected script adds or removes Clearead-owned style and overlay elements only. Lens mode clones the current page DOM locally inside the same tab for magnification, removes scripts and media sources from that clone, and keeps it non-interactive. Page tools do not send page text, persist page-tool state, or run automatically on every page.

Right-click dictionary lookup uses Chrome's selection context menu only after the user turns on the Right-click lookup button in the side panel. The menu is off by default. The extension stores only that on/off flag in `chrome.storage.session`, which is memory-backed and cleared when the extension is disabled, reloaded, updated, or when the browser restarts. When enabled, the menu item appears only when the user has selected text on a normal `http` or `https` webpage. After the user clicks the Clearead menu item, the service worker uses only `info.selectionText`, trims and normalizes whitespace, limits it to 80 characters, and builds a demo dictionary response with Simple meaning, Word parts, and Meaning from parts fields. The service worker then injects the local packaged page-tool script if needed and asks it to render an on-page dictionary card. The selected text is processed locally, is not sent to the Clearead backend, is not stored, and no surrounding page content is read. The one-line side panel word input uses the same local demo dictionary response after the user clicks Explain or presses Enter; it is not sent to the backend and is not stored. The card has no Save action.

After a summary request reaches the Clearead backend, the backend performs the existing processing pipeline: segmentation or chunking, configured model service processing, GPT/API fallback if configured, and backend algorithm fallback if needed. Any API keys or secrets for those services must stay on the backend side and must not be stored in the extension.

The deployed backend origin is currently the Azure backend URL found in workflow config. The website origin is currently `https://clearead.azurewebsites.net/`. The final production backend origin, website origin, user-facing privacy policy wording, and final Chrome Web Store data disclosure still need review before release.

## Unsupported Pages

Chrome blocks extension scripting on some pages by design. Clearead page tools are expected not to run on pages such as `chrome://`, `edge://`, `about:`, Chrome Web Store pages, extension pages, some browser PDF viewers, and other restricted contexts. The side panel reports a friendly unsupported-page message instead of claiming the tools worked.

Clearead also distinguishes temporary `activeTab` access problems from browser-restricted pages. If Chrome reports that the extension does not currently have access to an otherwise normal webpage, the side panel asks the user to open the target webpage, click the Clearead toolbar icon, and try the page tool again.

## What Is Not Implemented Yet

- No public simplify endpoint is wired into the extension.
- No backend dictionary endpoint is wired into the extension; dictionary content is local placeholder data.
- No file upload.
- No remote dictionary service.
- No automatic webpage scanning.
- No registered static content scripts.
- No final Chrome Web Store listing text.

## Validation

Run this from the `browser-extension/` folder:

```bash
npm run validate
```

The validation script checks Manifest V3 setup, required local files, local icon files and PNG dimensions, the side panel, background, the known popup activation file, page-tool file, absence of static content scripts, and that permissions stay narrow. It rejects broad host permissions such as `<all_urls>`, wildcard host permissions, unexpected popup paths, and unexpected extension permissions.

This phase should not be described as Chrome Web Store ready.
