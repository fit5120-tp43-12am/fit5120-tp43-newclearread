# Clearead Extension Architecture

## Main Folders

- `manifest.json`: Chrome extension registration file. It declares Manifest V3, the side panel, background service worker, `sidePanel`, and the narrow deployed backend host permission.
- `src/background/`: background service worker code. It enables opening the side panel when the extension action is clicked.
- `src/sidepanel/`: plain HTML, CSS, and JavaScript for the pasted-text summary workflow.
- `src/shared/config.js`: shared extension constants, including `MAX_TEXT_CHARS`, the backend base URL, and endpoint paths.
- `src/services/backend-api.js`: backend API adapter for the summary request.
- `src/content/`: reserved for future content scripts. No content scripts are registered.
- `src/popup/`: reserved for a future popup if the product needs one. No popup is registered.
- `src/styles/`: reserved for shared styling.
- `public/icons/`: reserved for extension icon assets.
- `docs/`: project documentation for architecture, privacy, permissions, and store checks.
- `scripts/`: local validation scripts for extension checks.

## Manifest V3 Pieces

Phase 3 uses these Manifest V3 pieces:

- `manifest_version: 3`: required for the current Chrome extension platform.
- `action.default_title`: gives the toolbar action a clear title.
- `background.service_worker`: points to the extension service worker.
- `side_panel.default_path`: points Chrome to the side panel HTML file.
- `permissions: ["sidePanel"]`: allows use of the Chrome side panel API.
- `host_permissions: ["https://clear-read-a3c2gyajcjf5agfd.australiaeast-01.azurewebsites.net/*"]`: allows the side panel extension page to call the shared Clearead backend.

No `content_scripts`, `default_popup`, `tabs`, `scripting`, `storage`, `contextMenus`, clipboard permissions, or remote executable code are used in this phase.

## Current Side Panel Flow

1. Chrome loads the extension from `manifest.json`.
2. The background service worker calls `chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true })`.
3. When the user clicks the Clearead extension action, Chrome opens `src/sidepanel/sidepanel.html`.
4. The side panel loads local CSS and JavaScript modules.
5. The user manually pastes text into the textarea.
6. The side panel counts words and characters locally.
7. Empty input and text over 50,000 characters are rejected before any backend request.
8. When the user clicks Summary, `src/services/backend-api.js` sends `POST https://clear-read-a3c2gyajcjf5agfd.australiaeast-01.azurewebsites.net/api/process-text` with `{ "text": string }`.
9. The response is rendered as notice text, fallback status, summary blocks, key points, and collapsed original text.
10. Backend validation and network failures are shown in the side panel as error states.

Text is not sent automatically while typing, and page content is not read automatically.

The extension is another frontend client for the shared Clearead backend. The website frontend and extension both send user-submitted text to the same backend processing route. The extension calls only the Clearead backend endpoint for summary generation. It does not call OpenAI, third-party AI APIs, analytics services, or dictionary services directly.

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
