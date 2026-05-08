# Clearead Extension Architecture

## Main Folders

- `manifest.json`: Chrome extension registration file. It declares the extension name, Manifest V3 version, side panel, background service worker, and permissions.
- `src/background/`: background service worker code. In Phase 1 it only enables opening the side panel when the extension action is clicked.
- `src/sidepanel/`: the current user interface. It contains plain HTML, CSS, and JavaScript for local pasted text placeholder behavior.
- `src/content/`: reserved for future content scripts. No content scripts are registered in Phase 1.
- `src/popup/`: reserved for a future popup if the product needs one. No popup is registered in Phase 1.
- `src/shared/`: reserved for shared constants and helpers.
- `src/services/`: reserved for future service adapters, such as AI, backend, or dictionary clients.
- `src/styles/`: reserved for shared styling.
- `public/icons/`: reserved for extension icon assets.
- `docs/`: project documentation for architecture, privacy, permissions, and store readiness.
- `scripts/`: local validation scripts for extension checks.

## Manifest V3 Pieces

Phase 1 uses these Manifest V3 pieces:

- `manifest_version: 3`: required for the current Chrome extension platform.
- `action.default_title`: gives the toolbar action a clear title.
- `background.service_worker`: points to the extension service worker.
- `side_panel.default_path`: points Chrome to the side panel HTML file.
- `permissions: ["sidePanel"]`: allows use of the side panel API.

No `host_permissions`, `content_scripts`, `default_popup`, or remote code are used in Phase 1.

## Current Side Panel Flow

1. Chrome loads the extension from `manifest.json`.
2. The background service worker calls `chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true })`.
3. When the user clicks the Clearead extension action, Chrome opens `src/sidepanel/sidepanel.html`.
4. The side panel loads local CSS and JavaScript.
5. The user can paste text into the textarea.
6. JavaScript counts words locally and shows a placeholder result message.

The pasted text stays inside the side panel page in this foundation.

## Planned Future Flow

Future side panel text tools may:

- Let the user choose simplify, summary, or reading support modes.
- Send user-approved text to a backend or AI service only after privacy and consent rules are implemented.
- Display returned simplified or summarized text in the side panel.

Future readable font work may:

- Use a content script only after a clear user action.
- Apply readable font styles to selected pages or text areas.
- Require narrower host permissions or `activeTab` depending on the chosen interaction model.

Future reading ruler work may:

- Use a content script to inject a visual ruler overlay into the current page.
- Keep page modification temporary and user-controlled.
- Avoid broad host access unless the final feature truly needs it.

Future dictionary work may:

- Add a context menu or side panel lookup flow.
- Use selected text only after user action.
- Request the minimum permission needed for that selected-text workflow.
