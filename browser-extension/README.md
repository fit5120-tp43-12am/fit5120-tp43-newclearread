# Clearead Browser Extension

This folder contains the Manifest V3 Clearead Chrome extension. Phase 4 keeps the pasted-text summary workflow and adds user-triggered readable page tools for ordinary webpages.

## Current Workflow

- Starts from a small toolbar popup, then opens as a Chrome side panel.
- Lets the user paste text manually.
- Shows live word and character counts.
- Enforces the backend limit of 50,000 characters.
- Sends text to `POST https://clear-read-a3c2gyajcjf5agfd.australiaeast-01.azurewebsites.net/api/process-text` only when the user clicks Summary.
- Displays the returned notice, fallback status, summary blocks, key points, and collapsed original text.
- Shows clear loading, success, empty-input, over-limit, backend-unavailable, and backend-validation states.
- Keeps Simplify visible but disabled because no stable public simplify endpoint is currently exposed by the backend.
- Lets the user apply readable font styles to the active webpage after clicking Apply readable font.
- Lets the user remove only Clearead-added readable font styles after clicking Reset page font.
- Lets the user toggle a local reading ruler overlay on the active webpage after clicking Toggle reading ruler.

## How To Load In Chrome

1. Open Chrome.
2. Go to `chrome://extensions`.
3. Turn on Developer mode.
4. Click Load unpacked.
5. Select this folder: `browser-extension/`.
6. Click the Clearead extension action icon.
7. In the popup, click Open Clearead for this page to open the side panel.

## How To Test The Summary Flow

1. Confirm the shared backend is available at `https://clear-read-a3c2gyajcjf5agfd.australiaeast-01.azurewebsites.net`.
2. Load the unpacked extension from `browser-extension/`.
3. Click the Clearead toolbar icon, then click Open Clearead for this page.
4. Paste text into the textarea.
5. Click Summary.
6. Confirm result blocks, summaries, key points, and collapsed original text render.
7. Temporarily block network access or point a development build at an unavailable backend to confirm the side panel shows a useful backend-unavailable error.

Developers may point a local-only test build at `http://localhost:8000`, but the normal demo path uses the deployed backend origin above.

## How To Test Page Tools

1. Reload the unpacked extension from `browser-extension/`.
2. Open a normal webpage.
3. Click the Clearead toolbar icon and confirm the popup opens instead of the side panel opening immediately.
4. Click Open Clearead for this page and confirm the side panel opens.
5. Click Apply readable font and confirm common text containers use a clearer local system font and modestly larger line height.
6. Click Reset page font and confirm the Clearead-added font styles are removed.
7. Click Toggle reading ruler and confirm the horizontal ruler appears and follows the pointer without blocking clicks.
8. Click Toggle reading ruler again and confirm the ruler disappears.
9. Try a restricted page such as `chrome://extensions` and confirm Clearead says Chrome does not allow extensions to modify that page.
10. If a normal webpage was opened before Clearead had current-tab access, confirm Clearead asks the user to open the target webpage, click the toolbar icon, and try the page tool again.

## Permissions

The extension requests:

- `sidePanel`: allows Clearead to use Chrome's side panel API.
- `activeTab`: gives temporary access to the current tab after a user action so page tools can run on that active page.
- `scripting`: allows Clearead to inject its local packaged page-tool script only after the user clicks a page-tool button.
- `host_permissions: ["https://clear-read-a3c2gyajcjf5agfd.australiaeast-01.azurewebsites.net/*"]`: allows the extension side panel to send user-submitted text to the shared Clearead backend for Summary only.

The extension does not request `<all_urls>`, `tabs`, `storage`, `contextMenus`, clipboard permissions, broad host permissions, or static `content_scripts`.

## Data Flow

Pasted text is not sent while the user types. When the user clicks Summary, the side panel sends this request body to the backend:

```json
{ "text": "the pasted text" }
```

The website frontend and the extension are separate frontend clients for the same Clearead backend processing route. The backend response is displayed in the side panel. The extension itself does not save pasted text, call OpenAI or other third-party AI APIs, call analytics or dictionary services, include API keys, read webpage content automatically, or load remote executable code.

Page tools do not send page content to the backend. The toolbar popup is an explicit activation step for the current page. After the user clicks Open Clearead for this page, the side panel opens. When the user then clicks a page-tool button, the service worker checks the active tab, rejects known restricted browser pages, and injects `src/content/page-tools.js` from the packaged extension into that active tab. The injected script adds or removes Clearead-owned style and overlay elements only. It does not collect page text, send page text, persist state, or run automatically on every page.

After a summary request reaches the Clearead backend, the backend performs the existing processing pipeline: segmentation or chunking, configured model service processing, GPT/API fallback if configured, and backend algorithm fallback if needed. Any API keys or secrets for those services must stay on the backend side and must not be stored in the extension.

The deployed backend origin is currently the Azure backend URL found in workflow config. The final production backend origin, user-facing privacy policy wording, and final Chrome Web Store data disclosure still need review before release.

## Unsupported Pages

Chrome blocks extension scripting on some pages by design. Clearead page tools are expected not to run on pages such as `chrome://`, `edge://`, `about:`, Chrome Web Store pages, extension pages, some browser PDF viewers, and other restricted contexts. The side panel reports a friendly unsupported-page message instead of claiming the tools worked.

Clearead also distinguishes temporary `activeTab` access problems from browser-restricted pages. If Chrome reports that the extension does not currently have access to an otherwise normal webpage, the side panel asks the user to open the target webpage, click the Clearead toolbar icon, and try the page tool again.

## What Is Not Implemented Yet

- No public simplify endpoint is wired into the extension.
- No text-to-speech.
- No file upload.
- No dictionary service.
- No selected-word lookup.
- No automatic webpage scanning.
- No registered static content scripts.
- No final Chrome Web Store icon artwork.

## Validation

Run this from the `browser-extension/` folder:

```bash
npm run validate
```

The validation script checks Manifest V3 setup, required local files, the side panel, background, the known popup activation file, page-tool file, absence of static content scripts, and that permissions stay narrow. It rejects broad host permissions such as `<all_urls>`, wildcard host permissions, unexpected popup paths, and unexpected extension permissions.

This phase should not be described as Chrome Web Store ready.
