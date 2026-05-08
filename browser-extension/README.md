# Clearead Browser Extension

This folder contains the Manifest V3 Clearead Chrome extension. Phase 3 replaces the placeholder side panel with a real pasted-text summary workflow backed by the shared deployed Clearead backend used by the website.

## Current Workflow

- Opens as a Chrome side panel.
- Lets the user paste text manually.
- Shows live word and character counts.
- Enforces the backend limit of 50,000 characters.
- Sends text to `POST https://clear-read-a3c2gyajcjf5agfd.australiaeast-01.azurewebsites.net/api/process-text` only when the user clicks Summary.
- Displays the returned notice, fallback status, summary blocks, key points, and collapsed original text.
- Shows clear loading, success, empty-input, over-limit, backend-unavailable, and backend-validation states.
- Keeps Simplify visible but disabled because no stable public simplify endpoint is currently exposed by the backend.

## How To Load In Chrome

1. Open Chrome.
2. Go to `chrome://extensions`.
3. Turn on Developer mode.
4. Click Load unpacked.
5. Select this folder: `browser-extension/`.
6. Click the Clearead extension action icon to open the side panel.

## How To Test The Summary Flow

1. Confirm the shared backend is available at `https://clear-read-a3c2gyajcjf5agfd.australiaeast-01.azurewebsites.net`.
2. Load the unpacked extension from `browser-extension/`.
3. Open the Clearead side panel.
4. Paste text into the textarea.
5. Click Summary.
6. Confirm result blocks, summaries, key points, and collapsed original text render.
7. Temporarily block network access or point a development build at an unavailable backend to confirm the side panel shows a useful backend-unavailable error.

Developers may point a local-only test build at `http://localhost:8000`, but the normal demo path uses the deployed backend origin above.

## Permissions

The extension requests:

- `sidePanel`: allows Clearead to use Chrome's side panel API.
- `host_permissions: ["https://clear-read-a3c2gyajcjf5agfd.australiaeast-01.azurewebsites.net/*"]`: allows the extension side panel to send user-submitted text to the shared Clearead backend.

The extension does not request `<all_urls>`, `tabs`, `scripting`, `storage`, `contextMenus`, clipboard permissions, or content scripts.

## Data Flow

Pasted text is not sent while the user types. When the user clicks Summary, the side panel sends this request body to the backend:

```json
{ "text": "the pasted text" }
```

The website frontend and the extension are separate frontend clients for the same Clearead backend processing route. The backend response is displayed in the side panel. The extension itself does not save pasted text, call OpenAI or other third-party AI APIs, call analytics or dictionary services, include API keys, read webpage content automatically, or load remote executable code.

After the request reaches the Clearead backend, the backend performs the existing processing pipeline: segmentation or chunking, configured model service processing, GPT/API fallback if configured, and backend algorithm fallback if needed. Any API keys or secrets for those services must stay on the backend side and must not be stored in the extension.

The deployed backend origin is currently the Azure backend URL found in workflow config. The final production backend origin, user-facing privacy policy wording, and final Chrome Web Store data disclosure still need review before release.

## What Is Not Implemented Yet

- No public simplify endpoint is wired into the extension.
- No text-to-speech.
- No file upload.
- No dictionary service.
- No readable font feature.
- No reading ruler feature.
- No webpage reading or modification.
- No registered content scripts.
- No browser action popup.
- No final Chrome Web Store icon artwork.

## Validation

Run this from the `browser-extension/` folder:

```bash
npm run validate
```

The validation script checks Manifest V3 setup, required local files, the side panel and background files, the absence of content scripts and popup UI, and that permissions stay narrow. It rejects broad host permissions such as `<all_urls>` and allows only the deployed backend host permission used by this phase.

This phase should not be described as Chrome Web Store ready.
