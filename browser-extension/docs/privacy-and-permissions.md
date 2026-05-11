# Privacy And Permissions

This document explains the Clearead browser extension data flow and permission use.

## Data Handled By The Extension

The extension handles data for user-triggered reading support features:

- Pasted text entered manually into the side panel for Summary.
- One English word entered in the side panel Word box or selected through the opt-in right-click Dictionary menu.
- Active-page DOM access used locally for visible page tools such as readable fonts, Highlight, Lens, and Line guide.
- Session state for the right-click lookup toggle, recent page activation metadata, and short dictionary error notices.

Page tools may inspect or clone the active page DOM locally inside the current tab. Lens uses a local non-interactive clone so it can show magnified content under the pointer.

## Summary Request

Summary runs after the user clicks Summary or presses Enter in the side panel text box.

- Endpoint: `POST https://clear-read-a3c2gyajcjf5agfd.australiaeast-01.azurewebsites.net/api/plugin/summary`
- Request body: `{ "text": string }`
- Text source: text manually pasted into the side panel
- Purpose: return a concise reading-support summary
- Rendered response field: `overallSummary.text`

## Dictionary Lookup

Dictionary lookup runs after the user requests one word explanation through the side panel Word box or the enabled right-click menu.

- Endpoint: `POST https://clear-read-a3c2gyajcjf5agfd.australiaeast-01.azurewebsites.net/api/dictionary`
- Request body: `{ "word": string }`
- Text source: one typed or selected English word
- Purpose: return a simple meaning and word-part explanation

The right-click menu starts disabled. When enabled, Chrome provides `info.selectionText` after the user clicks "Explain with Clearead". The service worker trims the selected text, caps it at 50 characters, validates it as one English word, and then sends the lookup request. Phrase and sentence selections receive local guidance.

The side panel Word box uses the same validation and backend route after the user clicks Explain or presses Enter.

## Page Tools

Page tools run after the user opens Clearead for the current page and chooses a tool in the side panel.

- Readable fonts inject one Clearead-owned style tag.
- Highlight and Line guide inject one Clearead-owned overlay.
- Lens injects one Clearead-owned local magnifier overlay.
- Original font and No ruler remove the Clearead-owned page changes.

Lens is intended for text pages. It removes scripts, inline event handlers, form actions, and embedded media sources from its local clone. When a page is too large or changes too rapidly, Lens stops and guides the user to Highlight or Line guide.

For direct PDF, DOCX, DOC, or TXT file URLs, the side panel guides users to the full Clearead website upload flow.

For browser-restricted pages such as `chrome://`, `edge://`, `about:`, extension pages, Chrome Web Store pages, and some browser PDF viewers, the side panel shows an unsupported-page message.

For fresh active-tab access needs on ordinary webpages, the side panel says: "Need page access. In Chrome, click Extensions (puzzle icon) > Clearead > Open Clearead for this page."

## Backend Processing

The extension sends Summary text and Dictionary words to the shared Clearead backend origin listed above. The website frontend and the extension both use the shared backend services for these user-triggered requests.

The backend may use Clearead-configured server-side model providers, including OpenAI, to generate summaries and word explanations. API keys and model credentials belong on the backend side.

The deployed backend origin is currently the Azure backend URL found in workflow config. The deployed website origin is currently `https://clearead.azurewebsites.net/`. Before release, the team should confirm production backend origin, backend retention behavior, public privacy policy wording, and Chrome Web Store data disclosure.

## Website Link

Open website links in the popup and side panel point to `https://clearead.azurewebsites.net/`. The link opens as a normal user-clicked browser tab.

## Storage

The extension uses `chrome.storage.session` for:

- The right-click Dictionary enabled boolean.
- Recent tab/window/time metadata for page-tool state sync.
- Short dictionary error notices after right-click lookup failures.

Chrome clears session storage when the extension is disabled, reloaded, updated, or when the browser restarts.

## Packaged Code And Assets

All extension UI, scripts, icons, and OpenDyslexic WOFF2 files are packaged locally. The OpenDyslexic font files are declared as web-accessible resources so injected page CSS can load them on normal webpages.

## Current Permissions

### `sidePanel`

Clearead uses Chrome's side panel API for the reading support panel.

### `activeTab`

Clearead uses temporary current-tab access after user action for page reading tools.

### `scripting`

Clearead uses programmatic injection for the local packaged page-tool script after user action.

### `contextMenus`

Clearead uses one opt-in selected-text right-click item: Explain with Clearead.

### `storage`

Clearead uses `chrome.storage.session` for the current-session feature state listed above.

### `host_permissions: ["https://clear-read-a3c2gyajcjf5agfd.australiaeast-01.azurewebsites.net/*"]`

Clearead uses this backend host permission for Summary and Dictionary requests.

## Permission Scope

The current manifest permission set is limited to the side panel UI, temporary active-tab page tools, local script injection, one opt-in context menu, current-session feature state, packaged font loading, and the deployed Clearead backend.
