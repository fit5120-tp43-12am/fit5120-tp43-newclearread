# Clearead Extension Architecture

## Main Folders

- `manifest.json`: Chrome extension registration file. It declares Manifest V3, the toolbar popup, side panel, background service worker, `sidePanel`, `activeTab`, `scripting`, and the narrow deployed backend host permission.
- `src/background/`: background service worker code. It disables direct action-click side panel opening, handles popup side-panel open fallback requests, and handles page-tool requests from the side panel.
- `src/sidepanel/`: plain HTML, CSS, and JavaScript for the pasted-text summary workflow and page-tool controls.
- `src/content/page-tools.js`: local packaged script that is programmatically injected into the active tab only after the user clicks a page-tool control.
- `src/shared/config.js`: shared extension constants, including `MAX_TEXT_CHARS`, the backend base URL, and endpoint paths.
- `src/services/backend-api.js`: backend API adapter for the summary request.
- `src/popup/`: small toolbar popup that activates Clearead for the current page before opening the side panel.
- `src/styles/`: reserved for shared styling.
- `public/icons/`: reserved for extension icon assets.
- `docs/`: project documentation for architecture, privacy, permissions, and store checks.
- `scripts/`: local validation scripts for extension checks.

## Manifest V3 Pieces

Phase 4 uses these Manifest V3 pieces:

- `manifest_version: 3`: required for the current Chrome extension platform.
- `action.default_title`: gives the toolbar action a clear title.
- `action.default_popup`: points to the small activation popup.
- `background.service_worker`: points to the extension service worker.
- `side_panel.default_path`: points Chrome to the side panel HTML file.
- `permissions: ["sidePanel", "activeTab", "scripting"]`: allows the side panel API, temporary active-tab access after user action, and programmatic injection of local page-tool code.
- `host_permissions: ["https://clear-read-a3c2gyajcjf5agfd.australiaeast-01.azurewebsites.net/*"]`: allows the side panel extension page to call the shared Clearead backend for Summary only.

No static `content_scripts`, `tabs`, `storage`, `contextMenus`, clipboard permissions, broad host permissions, or remote executable code are used in this phase.

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
10. The response is rendered as notice text, fallback status, summary blocks, key points, and collapsed original text.
11. Backend validation and network failures are shown in the side panel as error states.

Text is not sent automatically while typing, and page content is not read automatically.

## Page Tools Flow

1. The user opens a normal webpage, clicks the Clearead toolbar icon, and clicks Open Clearead for this page in the popup.
2. The user clicks Apply readable font, Reset page font, or Toggle reading ruler.
3. `src/sidepanel/sidepanel.js` sends a page-tool message to the extension service worker.
4. `src/background/service-worker.js` queries the active tab ID without requesting the `tabs` permission.
5. The service worker rejects known restricted URLs such as `chrome://`, `edge://`, `about:`, Chrome Web Store URLs, and extension pages.
6. For allowed pages, the service worker injects `src/content/page-tools.js` with `chrome.scripting.executeScript`.
7. The service worker sends the requested command to the injected script.
8. The injected script applies or removes Clearead-owned page elements and returns a status message to the side panel.
9. If Chrome rejects scripting, the service worker classifies the error as a browser-restricted page, a temporary active-tab access problem, or a generic page-tool failure before sending the message back to the side panel.

The page-tool script is not registered in `manifest.json` as a static content script. It is packaged locally and runs only after clear user actions: activating Clearead from the popup, then clicking a side panel page-tool control. It does not collect page text, send page text to the backend, persist settings, or scan pages automatically.

## Page Tool Behaviors

Readable font adds one removable style tag with id `clearead-readable-style`. The style targets common text containers such as `body`, `main`, `article`, `section`, paragraphs, list items, headings, labels, tables, and form controls. It uses local system fonts (`Arial`, `Verdana`, `Tahoma`) and a modest line-height increase. Reset removes only this Clearead-owned style tag.

Reading ruler adds one overlay element with id `clearead-reading-ruler`. It is fixed-position, horizontal, pointer-following, and uses `pointer-events: none` so page clicks can pass through. Toggling it off removes the overlay and listener. It is not persisted across reloads.

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

After the extension request reaches the Clearead backend, the backend performs the existing processing pipeline: segmentation or chunking, configured model service processing, GPT/API fallback if configured, and backend algorithm fallback if needed. Any API keys or secrets for those services belong on the backend side and must not be stored in extension files. Before Chrome Web Store release, the team must confirm the final production backend origin and privacy disclosures.

## Simplify Status

The backend contains internal simplification logic in service code, but no stable public simplify route or clear extension-facing simplify contract is currently mounted. The extension therefore keeps Simplify disabled and documents it as a future feature instead of inventing a route.
