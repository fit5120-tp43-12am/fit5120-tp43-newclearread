# Clearead Extension Architecture

## Main Folders

- `manifest.json`: Chrome extension registration file. It declares Manifest V3, packaged icons, the toolbar popup, side panel, background service worker, `sidePanel`, `activeTab`, `scripting`, `contextMenus`, `storage`, and the narrow deployed backend host permission.
- `src/background/`: background service worker code. It disables direct action-click side panel opening, handles popup side-panel open fallback requests, handles page-tool requests from the side panel, and owns the opt-in right-click dictionary context menu.
- `src/sidepanel/`: plain HTML, CSS, and JavaScript for the pasted-text summary workflow, page-tool controls, right-click dictionary toggle and guidance, and the full website link.
- `src/content/page-tools.js`: local packaged script that is programmatically injected into the active tab only after the user clicks a page-tool control or the Clearead dictionary context menu item.
- `src/shared/config.js`: shared extension constants, including `MAX_TEXT_CHARS`, the backend base URL, website URL, and endpoint paths.
- `src/services/backend-api.js`: backend API adapter for the summary request.
- `src/services/local-dictionary.js`: local glossary and fallback guidance reference for selected-word lookup. The runtime lookup logic is packaged locally and does not make network requests.
- `src/popup/`: small toolbar popup that activates Clearead for the current page before opening the side panel and also links to the full Clearead website.
- `src/styles/`: reserved for shared styling.
- `public/icons/`: packaged extension icon PNG assets for 16, 32, 48, and 128 pixel contexts.
- `docs/`: project documentation for architecture, privacy, permissions, and store checks.
- `scripts/`: local validation scripts for extension checks.

## Manifest V3 Pieces

Phase 7 uses these Manifest V3 pieces:

- `manifest_version: 3`: required for the current Chrome extension platform.
- `icons`: points to local packaged PNG files at 16, 32, 48, and 128 pixels.
- `action.default_title`: gives the toolbar action a clear title.
- `action.default_popup`: points to the small activation popup.
- `action.default_icon`: points the toolbar action to the same local packaged icon set.
- `background.service_worker`: points to the extension service worker. It is kept as a classic worker so Chrome reloads do not depend on service-worker module parsing.
- `side_panel.default_path`: points Chrome to the side panel HTML file.
- `permissions: ["sidePanel", "activeTab", "scripting", "contextMenus", "storage"]`: allows the side panel API, temporary active-tab access after user action, programmatic injection of local page-tool code, an opt-in right-click selected-text dictionary menu item, and a session-only boolean for the dictionary toggle.
- `host_permissions: ["https://clear-read-a3c2gyajcjf5agfd.australiaeast-01.azurewebsites.net/*"]`: allows the side panel extension page to call the shared Clearead backend for Summary only.

No static `content_scripts`, `tabs`, clipboard permissions, broad host permissions, or remote executable code are used in this phase.

Opening `https://clearead.azurewebsites.net/` is a normal external link from extension UI. It does not require a website host permission and does not let the extension inspect that website tab.

## Summary Flow

1. Chrome loads the extension from `manifest.json`.
2. The background service worker calls `chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: false })`.
3. When the user clicks the Clearead extension action, Chrome opens `src/popup/popup.html`.
4. When the user clicks Open Clearead for this page, the popup opens `src/sidepanel/sidepanel.html` and closes.
5. The side panel loads local CSS and JavaScript modules.
6. The user manually pastes text into the textarea.
7. The side panel counts words and characters locally.
8. Empty input and text over 50,000 characters are rejected before any backend request.
9. When the user clicks Summary, `src/services/backend-api.js` sends `POST https://clear-read-a3c2gyajcjf5agfd.australiaeast-01.azurewebsites.net/api/process-text` with `{ "text": string }`.
10. The result panel renders only summary text and key points above the Page tools section.
11. Backend validation and network failures are shown in the side panel as error states.

Text is not sent automatically while typing, and page content is not read automatically.

## Website Link Flow

1. The popup and side panel show an Open website link.
2. The link target comes from `CLEAREAD_WEBSITE_URL` in `src/shared/config.js`.
3. The current website URL is `https://clearead.azurewebsites.net/`, verified from the frontend Azure Web App workflow.
4. The browser opens the website as a normal tab after the user clicks the link.
5. The extension does not inject scripts into that tab unless the user separately activates Clearead on that page and clicks a page tool.

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

The page-tool script is not registered in `manifest.json` as a static content script. It is packaged locally and runs only after clear user actions: activating Clearead from the popup, then opening the side panel for that page or clicking a side panel page-tool control. It does not send page text to the backend, persist settings, or scan pages automatically. Lens mode builds a local non-interactive clone of the current page DOM inside the same tab so it can render a magnified view; scripts and media sources are removed from that clone.

## Right-Click Dictionary Flow

1. The right-click dictionary menu is off by default.
2. The user opens the side panel and turns on Enable right-click dictionary.
3. `src/sidepanel/sidepanel.js` sends `clearead:set-dictionary-enabled` to `src/background/service-worker.js`.
4. The service worker stores only the enabled boolean in `chrome.storage.session` and creates the selected-text context menu item for normal `http` and `https` webpages.
5. The user selects one word or a short phrase on a normal webpage.
6. The user right-clicks the selection and clicks Explain with Clearead.
7. The service worker reads only `info.selectionText`, normalizes whitespace, caps it at 80 characters, and explains it with packaged local dictionary logic.
8. The helper returns a built-in glossary meaning for demo terms or conservative fallback guidance for unknown words.
9. The service worker injects `src/content/page-tools.js` into the clicked tab if needed.
10. The service worker sends a `show-dictionary-popover` command with the local explanation.
11. The content script renders a small Clearead-owned popover near the current selection, or in a safe viewport position if no selection rectangle is available.
12. When the user turns the side panel toggle off, the service worker removes the Clearead context menu item.

Selected text is processed locally in the extension only after the user clicks the Clearead menu item. It is not sent to the Clearead backend, not stored, and not expanded into surrounding page content. The context menu is limited with `documentUrlPatterns` for normal webpages and is not backed by static content scripts or broad host permissions. The only dictionary state saved is the enabled boolean in `chrome.storage.session`, so the menu can survive Manifest V3 service worker sleep but is cleared when the extension is disabled, reloaded, updated, or when the browser restarts.

## Page Tool Behaviors

Readable font adds one removable style tag with id `clearead-readable-style`. The style targets common text containers such as `body`, `main`, `article`, `section`, paragraphs, list items, headings, labels, tables, links, inline spans, and form controls. The side panel offers Original, Verdana, OpenDyslexic, and Calibri. Choosing a readable font also increases line height, word spacing, and letter spacing so the change is visible and easier to scan. Choosing Original removes only this Clearead-owned style tag.

Reading ruler adds one overlay element with id `clearead-reading-ruler-v2` and removes older `clearead-reading-ruler` overlays if found. The side panel offers No ruler, Highlight, Lens, and Line guide. The active ruler is fixed-position, pointer-following, visually dims the rest of the page, and uses `pointer-events: none` so page clicks can pass through. Lens follows the pointer horizontally and vertically, showing a local magnified clone of the page area under the pointer. Choosing No ruler removes the overlay and listeners. The active font and ruler are not persisted across page reloads, but the side panel can query the current active page to keep its buttons aligned with the actual page state.

## Unsupported Pages

Some browser-controlled pages cannot be scripted by extensions. Clearead rejects or gracefully reports failure for `chrome://`, `edge://`, `about:`, Chrome Web Store pages, extension pages, some PDF viewers, and other restricted contexts. The expected side panel message is: "Chrome does not allow extensions to modify this page. Try a normal webpage."

Normal webpages can also fail if Chrome has not granted Clearead temporary `activeTab` access for the current page. In that case, the expected side panel message is: "Clearead needs access to the current tab before page tools can run. Open the target webpage, click the Clearead toolbar icon, then try the page tool again."

For unexpected page-tool failures, the fallback message is: "Clearead page tools could not run on this page. Try a normal webpage and reopen Clearead from the toolbar icon."

## Backend Contract

The deployed backend origin is currently `https://clear-read-a3c2gyajcjf5agfd.australiaeast-01.azurewebsites.net`, the Azure backend URL found in workflow config. The expected summary route is:

- Method: `POST`
- Path: `/api/process-text`
- Request body: `{ "text": string }`
- Backend limit: `MAX_TEXT_CHARS = 50000`

The response shape is defined by `TextResponse` in `backend/models/schemas.py`:

```text
{
  notice: string,
  usedFallback: boolean,
  fallbackReason: string,
  segmentation: object,
  blocks: [
    {
      id: number,
      originalText: string,
      summary: string,
      keyPoints: string[]
    }
  ]
}
```

After the extension request reaches the Clearead backend, the backend performs the existing processing pipeline: segmentation or chunking, configured model service processing, GPT/API fallback if configured, and backend algorithm fallback if needed. Any API keys or secrets for those services belong on the backend side and must not be stored in extension files. Selected-word lookup does not use this backend route. Before Chrome Web Store release, the team must confirm the final production backend origin and privacy disclosures.

## Website Origin

The deployed frontend website origin is currently:

- `https://clearead.azurewebsites.net/`

This is separate from the deployed backend API origin. It is used only for user-clicked website links in the extension UI.

## Simplify Status

The backend contains internal simplification logic in service code, but no stable public simplify route or clear extension-facing simplify contract is currently mounted. The extension therefore keeps Simplify disabled and documents it as a future feature instead of inventing a route.
