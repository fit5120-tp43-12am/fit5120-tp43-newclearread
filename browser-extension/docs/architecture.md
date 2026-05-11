# Clearead Extension Architecture

## Main Folders

- `manifest.json`: Chrome extension registration file. It declares Manifest V3, packaged icons, the toolbar popup, side panel, background service worker, `sidePanel`, `activeTab`, `scripting`, `contextMenus`, `storage`, and the narrow deployed backend host permission.
- `src/background/`: background service worker code. It disables direct action-click side panel opening, handles popup side-panel open fallback requests, handles page-tool requests from the side panel, and owns the opt-in right-click dictionary context menu.
- `src/sidepanel/`: plain HTML, CSS, and JavaScript for the pasted-text summary workflow, page-tool controls, right-click dictionary button, one-line dictionary word input, and the full website link.
- `src/content/page-tools.js`: local packaged script that is programmatically injected into the active tab only after the user clicks a page-tool control or the Clearead dictionary context menu item.
- `src/shared/config.js`: shared extension constants, including `MAX_TEXT_CHARS`, the backend base URL, website URL, and endpoint paths.
- `src/services/backend-api.js`: backend API adapter for the summary request and side panel dictionary request.
- `src/services/local-dictionary.js`: one-word dictionary input validation helpers shared by the side panel dictionary flow.
- `src/popup/`: small toolbar popup that activates Clearead for the current page before opening the side panel and also links to the full Clearead website.
- `src/styles/`: reserved for shared styling.
- `public/icons/`: packaged extension icon PNG assets for 16, 32, 48, and 128 pixel contexts.
- `public/fonts/`: packaged OpenDyslexic WOFF2 font files and the SIL Open Font License text used by the OpenDyslexic font mode.
- `docs/`: project documentation for architecture, privacy, permissions, and store checks.
- `scripts/`: local validation scripts for extension checks.

## Manifest V3 Pieces

The extension uses these Manifest V3 pieces:

- `manifest_version: 3`: required for the current Chrome extension platform.
- `icons`: points to local packaged PNG files at 16, 32, 48, and 128 pixels.
- `action.default_title`: gives the toolbar action a clear title.
- `action.default_popup`: points to the small activation popup.
- `action.default_icon`: points the toolbar action to the same local packaged icon set.
- `background.service_worker`: points to the extension service worker. It uses classic-worker syntax for stable Chrome reload behavior.
- `side_panel.default_path`: points Chrome to the side panel HTML file.
- `permissions: ["sidePanel", "activeTab", "scripting", "contextMenus", "storage"]`: allows the side panel API, temporary active-tab access after user action, programmatic injection of local page-tool code, an opt-in right-click selected-text dictionary menu item, and session-only state for the Right-click lookup button plus recent page activation tracking.
- `host_permissions: ["https://clear-read-a3c2gyajcjf5agfd.australiaeast-01.azurewebsites.net/*"]`: allows the extension to call the shared Clearead backend for Summary and explicit one-word Dictionary lookup.
- `web_accessible_resources`: exposes only the packaged OpenDyslexic WOFF2 files to normal `http` and `https` pages so injected readable-font CSS can load the local font files.

The manifest surface is limited to the popup, side panel, classic service worker, local programmatic page-tool injection, packaged assets, session state, the opt-in context menu, and the deployed Clearead backend host permission.

Opening `https://clearead.azurewebsites.net/` uses a normal user-clicked external link from extension UI. The website tab remains a regular Chrome tab outside extension inspection.

## Summary Flow

1. Chrome loads the extension from `manifest.json`.
2. The background service worker calls `chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: false })`.
3. When the user clicks the Clearead extension action, Chrome opens `src/popup/popup.html`.
4. When the user clicks Open Clearead for this page, the popup opens `src/sidepanel/sidepanel.html` and closes.
5. The side panel loads local CSS and JavaScript modules.
6. The user manually pastes text into the textarea.
7. The side panel counts words and characters locally.
8. Empty input and text over 50,000 characters are rejected before any backend request.
9. When the user runs Summary, `src/services/backend-api.js` sends `POST https://clear-read-a3c2gyajcjf5agfd.australiaeast-01.azurewebsites.net/api/plugin/summary` with `{ "text": string }`.
10. The result panel renders the returned `overallSummary.text` above the Page tools section.
11. Backend validation and network failures are shown in the side panel as error states.

Text leaves the browser only when the user runs Summary. Page-tool behavior starts only after explicit user activation.

## Website Link Flow

1. The popup and side panel show an Open website link.
2. The link target comes from `CLEAREAD_WEBSITE_URL` in `src/shared/config.js`.
3. The current website URL is `https://clearead.azurewebsites.net/`, verified from the frontend Azure Web App workflow.
4. The browser opens the website as a normal tab after the user clicks the link.
5. Page-tool injection on the website follows the same separate Clearead activation and page-tool click flow as any other normal webpage.

## Page Tools Flow

1. The user opens a normal webpage, clicks the Clearead toolbar icon, and clicks Open Clearead for this page in the popup.
2. The user chooses a Font option or Reading ruler option in the side panel.
3. `src/sidepanel/sidepanel.js` sends a page-tool message to the extension service worker.
4. `src/background/service-worker.js` queries the active tab ID without requesting the `tabs` permission.
5. The service worker rejects known restricted URLs such as `chrome://`, `edge://`, `about:`, Chrome Web Store URLs, and extension pages.
6. For allowed pages, the service worker injects `src/content/page-tools.js` with `chrome.scripting.executeScript`.
7. The service worker sends the requested command to the injected script.
8. The injected script applies or removes Clearead-owned page elements and returns a status message to the side panel.
9. If Chrome rejects scripting, the service worker classifies the error as a browser-restricted page, a temporary active-tab access problem, or a generic page-tool failure before sending the message back to the side panel.

The page-tool script is packaged locally and injected programmatically after clear user actions: activating Clearead from the popup, then opening the side panel for that page or clicking a side panel page-tool control. Page-tool work stays local to the active page. Lens mode builds a local non-interactive clone of the current page DOM inside the same tab so it can render a magnified view; that local clone is refreshed after page DOM changes such as dropdown menus, and scripts, inline event handlers, form actions, and embedded media sources are removed from the clone. Lens is scoped to text-page support. If a page changes too frequently while Lens is active, the content script turns Lens off and returns: "Lens stopped on this dynamic page. Try Highlight or Line guide."

## Right-Click Dictionary Flow

1. The right-click dictionary menu is off by default.
2. The user opens the side panel and turns on the Right-click lookup button.
3. `src/sidepanel/sidepanel.js` sends `clearead:set-dictionary-enabled` to `src/background/service-worker.js`.
4. The service worker stores only the enabled boolean in `chrome.storage.session` and creates the selected-text context menu item for normal `http` and `https` webpages.
5. The user selects one English word on a normal webpage.
6. The user right-clicks the selection and clicks Explain with Clearead.
7. The service worker reads only `info.selectionText`, normalizes whitespace, caps it at 50 characters, and confirms it is one English word.
8. If the selection is a phrase, sentence, or unsupported token, the content script shows a dictionary card message asking the user to select one English word.
9. The service worker injects `src/content/page-tools.js` into the clicked tab if needed.
10. For valid words, the service worker first sends a `show-dictionary-popover` command with a loading explanation so the page card says Looking up.
11. The service worker sends `POST /api/dictionary` to the deployed Clearead backend with `{ "word": string }`.
12. The service worker adapts the backend response fields into the extension card shape and sends another `show-dictionary-popover` command with the final explanation.
13. The content script renders a Clearead-owned dictionary card near the current selection, or in a safe viewport position if no selection rectangle is available.
14. When the user turns the side panel Right-click lookup button off, the service worker removes the Clearead context menu item.

Selected text is sent to the Clearead backend only after the user clicks the Clearead menu item and only if the selected text validates as one English word. The lookup uses only the selected word supplied by Chrome. The side panel word input is one line; clicking Explain or pressing Enter uses the same one-word validation and `POST /api/dictionary` route, then renders the returned dictionary card inside the panel. The current card includes a local pronunciation button and omits Save. The context menu is limited with `documentUrlPatterns` for normal webpages and uses programmatic injection after user action. The dictionary enabled boolean is saved in `chrome.storage.session`, so the menu can survive Manifest V3 service worker sleep and resets when the extension is disabled, reloaded, updated, or when the browser restarts. A recent page activation tab/window/time record is also saved in `chrome.storage.session` so page-tool state sync can recover after service worker sleep while page content remains local to the tab.

## Page Tool Behaviors

Readable font adds one removable style tag with id `clearead-readable-style`. The style targets common text containers such as `body`, `main`, `article`, `section`, paragraphs, list items, headings, labels, tables, links, inline spans, and form controls. The side panel offers Original, Verdana, OpenDyslexic, and Calibri. OpenDyslexic loads from packaged local WOFF2 font files. Choosing a readable font also increases line height, word spacing, and letter spacing so the change is visible and easier to scan. Choosing Original removes only this Clearead-owned style tag.

Reading ruler adds one overlay element with id `clearead-reading-ruler-v2` and removes older `clearead-reading-ruler` overlays if found. The side panel offers No ruler, Highlight, Lens, and Line guide. The active ruler is fixed-position, pointer-following, visually dims the rest of the page, and uses `pointer-events: none` so page clicks can pass through. Lens follows the pointer horizontally and vertically, showing a local magnified clone of the page area under the pointer. While Lens is active, a local mutation observer marks the clone for throttled refresh when ordinary webpage DOM changes. A safety threshold turns Lens off on pages that trigger too many DOM changes in a short window, such as some animated or media-heavy pages. The side panel also warns: "Best on text pages. If Lens looks blank, try Highlight or Line guide." Choosing No ruler removes the overlay and listeners. The active font and ruler are page-local state, and the side panel can query the current active page to keep its buttons aligned with the actual page state.

## Unsupported Pages

Some browser-controlled pages cannot be scripted by extensions. Clearead rejects or gracefully reports failure for `chrome://`, `edge://`, `about:`, Chrome Web Store pages, extension pages, some PDF viewers, and other restricted contexts. The expected side panel message is: "Chrome blocks tools on this page. Try another webpage."

For direct PDF, DOCX, DOC, or TXT file URLs, the expected side panel message is: "File pages may not support page tools. Click Open website to upload the file." This guides users to the full Clearead website upload flow without adding broad file or host permissions.

Normal webpages can also fail if Chrome has not granted Clearead temporary `activeTab` access for the current page. In that case, the expected side panel message is: "Need page access. In Chrome, click Extensions (puzzle icon) > Clearead > Open Clearead for this page."

For unexpected page-tool failures, the fallback message is: "Clearead tools are unavailable on this page. Try a text page or click Clearead again."

## Backend Contract

The deployed backend origin is currently `https://clear-read-a3c2gyajcjf5agfd.australiaeast-01.azurewebsites.net`, the Azure backend URL found in workflow config. The expected extension summary route is:

- Method: `POST`
- Path: `/api/plugin/summary`
- Request body: `{ "text": string }`
- Backend limit: `MAX_TEXT_CHARS = 50000`

The response shape returned by the plugin summary route is:

```text
{
  overallSummary: {
    heading: string,
    text: string
  },
  processingStats: object
}
```

The extension displays only `overallSummary.text` from this response in the side panel Result section.

After the extension Summary request reaches the Clearead backend, the plugin summary route performs the full-document summary flow for the extension. Dictionary requests use the existing backend dictionary route and word-breakdown flow. API keys or secrets for those services belong on the backend side. Before Chrome Web Store release, the team must confirm the final production backend origin and privacy disclosures.

Because the background service worker is intentionally kept as a classic worker, the backend dictionary URL is duplicated in `src/background/service-worker.js` while side panel API calls use `src/shared/config.js`. If the backend origin changes, update both places and rerun the extension validator.

## Website Origin

The deployed frontend website origin is currently:

- `https://clearead.azurewebsites.net/`

This is separate from the deployed backend API origin. It is used only for user-clicked website links in the extension UI.

## Summary Status

Summary uses the deployed Clearead plugin summary route: `POST /api/plugin/summary`. The side panel sends `{ "text": string }` to the shared backend only after the user runs Summary, then renders the returned full-document `overallSummary.text`.

Dictionary uses the deployed Clearead dictionary route: `POST /api/dictionary`. The extension sends `{ "word": string }` only after the side panel input or right-click selected text validates as one English word. The returned `word`, `simpleMeaning`, `wordParts`, and `meaningFromParts` fields are adapted into the extension dictionary card shape.
