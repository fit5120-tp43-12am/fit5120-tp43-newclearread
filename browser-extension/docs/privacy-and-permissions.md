# Privacy And Permissions

## Current Data Collection

The extension handles text that the user manually pastes into the Clearead side panel for summary and selected text that the user explicitly asks Clearead to look up from the opt-in right-click menu.

The page tools can modify the currently active webpage after the user activates Clearead from the toolbar popup and clicks a side panel control. The dictionary context menu is off by default. After the user enables it in the side panel, it can read only the selected text supplied by Chrome after the user clicks the Clearead right-click menu item.

The popup and side panel can open the full Clearead website at `https://clearead.azurewebsites.net/` when the user clicks Open website. This is a normal browser link, not a background data transfer.

The extension does not collect browsing history, analytics, account information, cookies, files, screenshots, or telemetry. Page tools may inspect or clone the active page DOM locally inside the current tab only to apply visible reading support tools. That page content is not sent to the Clearead backend, not sent to third parties, and not stored.

## Does Pasted Text Leave The Browser?

Yes, but only after a clear user action.

Pasted text is sent when the user clicks Summary. It is not sent automatically while the user types, and the extension does not read webpage content automatically.

## Summary Request

When Summary is clicked, the side panel sends:

- Endpoint: `POST https://clear-read-a3c2gyajcjf5agfd.australiaeast-01.azurewebsites.net/api/process-text`
- Request body: `{ "text": string }`
- Text source: the text manually pasted into the side panel
- Purpose: ask the Clearead backend to segment and summarize the pasted text

The side panel displays only:

- `blocks[].summary`

The backend response can include extra fields such as key points, notice, fallback status, and original text, but those extra fields are not rendered in the result panel.

## Selected-Word Lookup

The right-click dictionary menu is off by default. The side panel includes a Right-click lookup button that turns blue with a check only when the background service worker confirms the menu is enabled. When the user turns it on, the service worker creates the selected-text menu item for normal `http` and `https` webpages. When the user turns it off, the service worker removes that menu item.

When the enabled user right-clicks a webpage selection and clicks the Clearead dictionary menu item, Chrome passes the selected text to the service worker as `info.selectionText`. The service worker normalizes whitespace, trims it, and caps it at 80 characters.

The selected text is then used locally to build a demo dictionary response with Simple meaning, Word parts, and Meaning from parts fields. These fields currently contain placeholder demo content until a stable backend dictionary function exists. The service worker injects the local packaged page-tool script only when needed so it can render the dictionary card on the clicked page.

Selected text is not sent to the Clearead backend, not sent to any third party, not stored, and not used to read surrounding page content. No lookup runs automatically while the user selects text. The side panel also has a one-line word input; when the user clicks Explain or presses Enter, the current build uses that word locally to build the same demo dictionary response shape. The pasted word is not sent to the backend and is not stored. The dictionary card has a local pronunciation button and no Save action. The only dictionary state saved is the enabled boolean in `chrome.storage.session`, which keeps the menu stable while the browser session is active and is cleared when the extension is disabled, reloaded, updated, or when the browser restarts.

## Page Tools

Page tools run only after the user opens the toolbar popup and clicks Open Clearead for this page. The side panel may query the active page to sync button state, and user clicks on page-tool controls can apply or remove visible tools.

For the Font chooser and Reading ruler chooser, the extension service worker queries the active tab, rejects known restricted browser pages, and uses `chrome.scripting.executeScript` to inject the local packaged file `src/content/page-tools.js` into the active tab. The script adds or removes Clearead-owned style and overlay elements.

Readable font and reading ruler tools do not call the backend, do not send page content anywhere, do not read selected text, do not persist settings, and do not run automatically on every page. The reading ruler is local to the current page and disappears when toggled off or when the page reloads. Lens mode clones the current page DOM into a local, non-interactive overlay in the same tab, removes scripts and media sources from that clone, and enlarges the area under the pointer. The cloned content stays in the current page DOM only, is not stored, and is not sent anywhere.

Unsupported pages are expected. Chrome blocks extension scripting on `chrome://`, `edge://`, `about:`, Chrome Web Store pages, extension pages, some PDF viewers, and other restricted contexts. The side panel shows a friendly unsupported-page error for these cases where possible.

If a normal webpage fails because Clearead does not currently have temporary `activeTab` access, the side panel shows a separate message asking the user to open the target webpage, click the Clearead toolbar icon, and try the page tool again. This keeps the explanation accurate without adding broader permissions.

## Backend-Side Processing

The extension sends pasted text only to the shared Clearead backend endpoint. The website frontend and extension both use the same backend processing route. The extension itself does not perform AI processing or call OpenAI, third-party AI APIs, analytics services, or remote dictionary services.

After the request reaches the Clearead backend, the backend performs the existing processing pipeline: segmentation or chunking, configured model service processing, GPT/API fallback if configured, and backend algorithm fallback if needed. API keys and secrets for those services, if any, belong on the backend side and must not be stored in the extension.

The deployed backend origin is currently the Azure backend URL found in workflow config. The deployed website origin is currently `https://clearead.azurewebsites.net/`. Before release, the final production backend origin, website origin, backend retention and logging behavior, user-facing privacy policy wording, and Chrome Web Store data disclosure still need review.

## Website Link

Open website links in the popup and side panel point to `https://clearead.azurewebsites.net/`. The extension does not request host permission for this website because opening a user-clicked link does not require permission to read or change that website.

## Storage

The extension does not save pasted text or selected text. It uses `chrome.storage.session` only for one right-click dictionary enabled boolean. It does not use `chrome.storage.local`, `chrome.storage.sync`, localStorage, indexedDB, cookies, or a custom cache for pasted content, selected text, or page-tool state. Page-tool button state is synchronized by querying the current active page, not by storing page content or preferences.

## Secrets And Remote Code

The extension does not include API keys, access tokens, secrets, analytics IDs, or private credentials.

All side panel and page-tool code is packaged locally with the extension. The extension does not load remote executable JavaScript, use `eval`, or inject remote scripts into webpages.

## Current Permissions

### `sidePanel`

Clearead requests `sidePanel` so it can use Chrome's side panel API and open the reading support panel when the user clicks the popup activation button.

### `activeTab`

Clearead requests `activeTab` so a user action can grant temporary access to the current tab for page tools. This avoids requesting access to every website.

### `scripting`

Clearead requests `scripting` so it can programmatically inject the local packaged page-tool script into the active tab only after the user opens Clearead for the page and uses or syncs page tools.

### `contextMenus`

Clearead requests `contextMenus` so it can add one opt-in selected-text right-click menu item: Explain with Clearead. The item is created only after the user enables the side panel Right-click lookup button, and it is limited to selection context on normal `http` and `https` webpages. Selected text is read only when the user clicks that Clearead menu item.

### `storage`

Clearead requests `storage` so it can use `chrome.storage.session` for one boolean: whether the user enabled the right-click dictionary menu in the current browser session. Pasted text, selected text, page content, summaries, and page-tool state are not stored.

### `host_permissions: ["https://clear-read-a3c2gyajcjf5agfd.australiaeast-01.azurewebsites.net/*"]`

Clearead requests this narrow host permission so the extension side panel can send user-submitted pasted text to the shared Clearead backend for Summary.

This permission is limited to the deployed backend origin currently used for the shared Clearead service. It is not a permission to read webpages.

## Permissions Not Requested

Clearead does not request:

- `<all_urls>`
- broad host permissions
- `tabs`
- clipboard permissions
- static `content_scripts`

Future permissions should be added only if an implemented feature has a clear need and matching documentation.
