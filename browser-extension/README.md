# Clearead Browser Extension

This folder contains the Manifest V3 Chrome extension for Clearead. The extension provides a side-panel reading workflow, page-level reading tools, and opt-in dictionary lookup for ordinary web pages.

## Main Features

- Toolbar popup that opens the Clearead side panel for the active tab.
- Side-panel text summary workflow using the deployed Clearead backend.
- Link from the popup and side panel to the full Clearead website at `https://clearead.azurewebsites.net/`.
- Page font controls for Original, Verdana, OpenDyslexic, and Calibri.
- Reading ruler modes: No ruler, Highlight, Lens, and Line guide.
- Opt-in right-click dictionary lookup for one selected English word.
- Side-panel one-word dictionary input using the same backend dictionary route.
- Packaged extension icons and local OpenDyslexic font files.

## Project Structure

```text
browser-extension/
  manifest.json              Manifest V3 extension definition
  package.json               Validation and package scripts
  src/
    background/              Service worker for side panel, page tools, and context menu
    sidepanel/               Side-panel HTML, CSS, and JavaScript
    popup/                   Toolbar popup activation UI
    content/                 Page-tool script injected after user action
    services/                Backend API adapter and dictionary validation
    shared/                  Shared backend URL, website URL, endpoints, and limits
    styles/                  Reserved location for shared extension styles
  public/
    icons/                   PNG icons for Chrome contexts
    fonts/                   Packaged OpenDyslexic font files
  docs/                      Store, privacy, testing, architecture, and release documents
  scripts/                   Validation and packaging scripts
```

## Backend Integration

The extension uses the deployed backend origin configured in `src/shared/config.js`:

```text
https://clear-read-a3c2gyajcjf5agfd.australiaeast-01.azurewebsites.net
```

API calls:

- `POST /api/plugin/summary` sends pasted text after the user clicks Summary.
- `POST /api/dictionary` sends one validated English word after the user clicks Explain or chooses the right-click menu item.

API keys and model credentials stay on the backend. Page font and ruler tools run locally in the active tab after user activation.

## Chrome Permissions

| Permission | Purpose |
| --- | --- |
| `sidePanel` | Opens the Clearead side panel. |
| `activeTab` | Grants temporary active-tab access after a user action. |
| `scripting` | Injects the packaged page-tool script after a tool or dictionary action. |
| `contextMenus` | Provides the opt-in selected-word dictionary menu item. |
| `storage` | Stores current-session feature state in `chrome.storage.session`. |
| Host permission | Allows Summary and Dictionary requests to the deployed Clearead backend. |

Session storage is limited to feature state, recent page activation metadata, and short dictionary notices.

## Install

The released extension is available on the Chrome Web Store:

```text
https://chromewebstore.google.com/detail/clearead/jlohhhioeodjkkeahcoelbbnkaigflkn
```

Use Add to Chrome on the store page, then open Clearead from the browser toolbar.

## Local Development

For source-level development and validation, load this folder as an unpacked extension:

1. Open `chrome://extensions`.
2. Enable Developer mode.
3. Click Load unpacked.
4. Select `browser-extension/`.
5. Click the Clearead toolbar icon.
6. Click Open Clearead for this page to open the side panel.

## Validation

Run this from the extension folder:

```powershell
cd browser-extension
npm run validate
```

The validation script checks Manifest V3 setup, required local files, icon dimensions, side-panel and popup files, page-tool files, narrow permissions, session-only storage, and common unsafe extension patterns such as `eval`, remote JavaScript URLs, and HTML string injection APIs.

## Manual Review Checklist

- Summary accepts pasted text, shows loading state, and renders the returned overview.
- Empty, over-limit, backend-timeout, backend-unavailable, and validation-error states show useful messages.
- Font tools apply and remove readable font styling on ordinary web pages.
- Ruler tools apply Highlight, Lens, and Line guide modes on ordinary text pages.
- Restricted browser pages show unsupported-page guidance.
- Right-click dictionary remains disabled until enabled in the side panel.
- Selected-word lookup rejects phrases before a backend request.
- Dictionary cards show simple meaning, word parts, pronunciation, and close controls.

## Supporting Documents

- [docs/architecture.md](docs/architecture.md)
- [docs/privacy-and-permissions.md](docs/privacy-and-permissions.md)
- [docs/privacy-policy.md](docs/privacy-policy.md)
- [docs/chrome-store-checklist.md](docs/chrome-store-checklist.md)
- [docs/chrome-store-submission.md](docs/chrome-store-submission.md)
- [docs/release-runbook.md](docs/release-runbook.md)
- [docs/testing-development-log.md](docs/testing-development-log.md)
- [docs/security-and-privacy-development-log.md](docs/security-and-privacy-development-log.md)

## Package Scope

The extension package is focused on pasted-text Summary, page tools, side-panel dictionary lookup, opt-in selected-word right-click lookup, and website navigation. File upload and full reading-workspace workflows belong to the web application.
