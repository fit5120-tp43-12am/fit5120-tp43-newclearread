# Clearead Browser Extension

This folder contains the Phase 1 production foundation for the Clearead Chrome extension.

## Current Foundation

- Uses Chrome Manifest V3.
- Provides a minimal Chrome side panel.
- Lets the user paste text locally into the side panel.
- Shows a local word count and placeholder preview message.
- Opens the side panel when the extension action is clicked.
- Includes documentation for architecture, privacy, permissions, and Chrome Web Store checks.

## How To Load In Chrome

1. Open Chrome.
2. Go to `chrome://extensions`.
3. Turn on Developer mode.
4. Click Load unpacked.
5. Select this folder: `browser-extension/`.
6. Click the Clearead extension action icon to open the side panel.

## What Is Not Implemented Yet

- No backend calls.
- No AI simplify or summary service.
- No dictionary service.
- No readable font feature.
- No reading ruler feature.
- No context menu dictionary feature.
- No webpage reading or modification.
- No registered content scripts.
- No browser action popup.
- No final Chrome Web Store icon artwork.

## Permissions

The extension currently requests only:

- `sidePanel`: allows Clearead to use Chrome's side panel API and open its side panel when the extension action is clicked.

The foundation does not request `host_permissions`, `<all_urls>`, tabs access, storage access, or scripting access.

## Validation

Run this from the `browser-extension/` folder:

```bash
npm run validate
```

The validation script checks that the Manifest V3 setup is present, the side panel and background files exist, and Phase 1 has not added broad webpage permissions or registered content scripts.
