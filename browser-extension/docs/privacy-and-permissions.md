# Privacy And Permissions

## Current Data Collection

The extension handles only text that the user manually pastes into the Clearead side panel for summary.

The page tools can modify the currently active webpage after the user activates Clearead from the toolbar popup and clicks a side panel control, but they do not collect, copy, send, or store webpage text.

The extension does not collect browsing history, page content, analytics, account information, cookies, files, screenshots, selected text from webpages, or telemetry.

## Does Pasted Text Leave The Browser?

Yes, but only after a clear user action.

Pasted text is sent when the user clicks Summary. It is not sent automatically while the user types, and the extension does not read webpage content automatically.

## Summary Request

When Summary is clicked, the side panel sends:

- Endpoint: `POST https://clear-read-a3c2gyajcjf5agfd.australiaeast-01.azurewebsites.net/api/process-text`
- Request body: `{ "text": string }`
- Text source: the text manually pasted into the side panel
- Purpose: ask the Clearead backend to segment and summarize the pasted text

The response displayed in the side panel may include:

- `notice`
- `usedFallback`
- `fallbackReason`
- `blocks[].summary`
- `blocks[].keyPoints`
- `blocks[].originalText`

The original text is shown in a collapsed section so the generated summary remains readable.

## Page Tools

Page tools run only after the user opens the toolbar popup, clicks Open Clearead for this page, and then clicks a side panel page-tool control.

For Apply readable font, Reset page font, and Toggle reading ruler, the extension service worker queries the active tab, rejects known restricted browser pages, and uses `chrome.scripting.executeScript` to inject the local packaged file `src/content/page-tools.js` into the active tab. The script adds or removes Clearead-owned style and overlay elements.

Page tools do not call the backend, do not send page content anywhere, do not read selected text, do not persist settings, and do not run automatically on every page. The reading ruler is local to the current page and disappears when toggled off or when the page reloads.

Unsupported pages are expected. Chrome blocks extension scripting on `chrome://`, `edge://`, `about:`, Chrome Web Store pages, extension pages, some PDF viewers, and other restricted contexts. The side panel shows a friendly unsupported-page error for these cases where possible.

If a normal webpage fails because Clearead does not currently have temporary `activeTab` access, the side panel shows a separate message asking the user to open the target webpage, click the Clearead toolbar icon, and try the page tool again. This keeps the explanation accurate without adding broader permissions.

## Backend-Side Processing

The extension sends pasted text only to the shared Clearead backend endpoint. The website frontend and extension both use the same backend processing route. The extension itself does not perform AI processing or call OpenAI, third-party AI APIs, analytics services, or dictionary services.

After the request reaches the Clearead backend, the backend performs the existing processing pipeline: segmentation or chunking, configured model service processing, GPT/API fallback if configured, and backend algorithm fallback if needed. API keys and secrets for those services, if any, belong on the backend side and must not be stored in the extension.

The deployed backend origin is currently the Azure backend URL found in workflow config. Before release, the final production backend origin, backend retention and logging behavior, user-facing privacy policy wording, and Chrome Web Store data disclosure still need review.

## Storage

The extension does not save pasted text. It does not use Chrome storage, localStorage, indexedDB, cookies, or a custom cache for pasted content or page-tool state.

## Secrets And Remote Code

The extension does not include API keys, access tokens, secrets, analytics IDs, or private credentials.

All side panel and page-tool code is packaged locally with the extension. The extension does not load remote executable JavaScript, use `eval`, or inject remote scripts into webpages.

## Current Permissions

### `sidePanel`

Clearead requests `sidePanel` so it can use Chrome's side panel API and open the reading support panel when the user clicks the popup activation button.

### `activeTab`

Clearead requests `activeTab` so a user action can grant temporary access to the current tab for page tools. This avoids requesting access to every website.

### `scripting`

Clearead requests `scripting` so it can programmatically inject the local packaged page-tool script into the active tab only after the user clicks a page-tool button.

### `host_permissions: ["https://clear-read-a3c2gyajcjf5agfd.australiaeast-01.azurewebsites.net/*"]`

Clearead requests this narrow host permission so the extension side panel can send user-submitted pasted text to the shared Clearead backend for Summary.

This permission is limited to the deployed backend origin currently used for the shared Clearead service. It is not a permission to read webpages.

## Permissions Not Requested

Clearead does not request:

- `<all_urls>`
- broad host permissions
- `tabs`
- `storage`
- `contextMenus`
- clipboard permissions
- static `content_scripts`

These permissions should be added only if a future implemented feature has a clear need and matching documentation.
