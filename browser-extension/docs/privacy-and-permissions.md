# Privacy And Permissions

## Current Data Collection

The extension handles only text that the user manually pastes into the Clearead side panel.

It does not collect browsing history, page content, analytics, account information, cookies, files, screenshots, selected text from webpages, or telemetry.

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

## Backend-Side Processing

The extension sends pasted text only to the shared Clearead backend endpoint. The website frontend and extension both use the same backend processing route. The extension itself does not perform AI processing or call OpenAI, third-party AI APIs, analytics services, or dictionary services.

After the request reaches the Clearead backend, the backend performs the existing processing pipeline: segmentation or chunking, configured model service processing, GPT/API fallback if configured, and backend algorithm fallback if needed. API keys and secrets for those services, if any, belong on the backend side and must not be stored in the extension.

The deployed backend origin is currently the Azure backend URL found in workflow config. Before release, the final production backend origin, backend retention and logging behavior, user-facing privacy policy wording, and Chrome Web Store data disclosure still need review.

## Storage

The extension does not save pasted text. It does not use Chrome storage, localStorage, indexedDB, cookies, or a custom cache for the pasted content.

## Secrets And Remote Code

The extension does not include API keys, access tokens, secrets, analytics IDs, or private credentials.

All side panel code is packaged locally with the extension. The extension does not load remote executable JavaScript, use `eval`, or inject scripts into webpages.

## Current Permissions

### `sidePanel`

Clearead requests `sidePanel` so it can use Chrome's side panel API and open the reading support panel when the user clicks the extension action.

### `host_permissions: ["https://clear-read-a3c2gyajcjf5agfd.australiaeast-01.azurewebsites.net/*"]`

Clearead requests this narrow host permission so the extension side panel can send user-submitted pasted text to the shared Clearead backend.

This permission is limited to the deployed backend origin currently used for the shared Clearead service. It is not a permission to read webpages.

## Permissions Not Requested

Clearead does not request:

- `<all_urls>`
- broad host permissions
- `tabs`
- `scripting`
- `storage`
- `contextMenus`
- clipboard permissions
- content scripts

These permissions should be added only if a future implemented feature has a clear need and matching documentation.
