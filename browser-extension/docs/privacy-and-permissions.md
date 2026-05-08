# Privacy And Permissions

## Current Data Collection

Phase 1 does not collect personal data, browsing data, page content, analytics, or account information.

The only user-provided data handled by the current foundation is text that the user manually pastes into the Clearead side panel.

## Does Pasted Text Leave The Browser?

No. In Phase 1, pasted text is processed only by local JavaScript in the side panel page.

The current code counts words and shows a placeholder preview message. It does not send pasted text to a backend, AI service, dictionary service, analytics service, or third-party API.

## Current Permission

### `sidePanel`

Clearead requests `sidePanel` so it can use Chrome's side panel API.

This permission is needed because Phase 1 implements the extension as a side panel experience instead of a popup or injected webpage UI.

The background service worker uses this permission to make the side panel open when the user clicks the extension action.

## Permissions Not Requested Yet

Clearead does not currently request:

- `host_permissions`: not needed because Phase 1 does not read or change webpages.
- `<all_urls>`: not needed and too broad for the current foundation.
- `scripting`: not needed because no scripts are injected into webpages.
- `tabs`: not needed because the extension does not inspect browser tabs.
- `storage`: not needed because Phase 1 does not save user preferences or history.
- `contextMenus`: not needed because dictionary lookup is not implemented.

## Possible Future Permissions

Future features may need extra permissions, but they should be added only when the feature is implemented and justified:

- Readable font or reading ruler features may need `activeTab`, `scripting`, or narrow host permissions if they modify the current webpage.
- Context menu dictionary lookup may need `contextMenus`.
- Saved user preferences may need `storage`.
- Backend or AI calls may need documented network endpoints, privacy policy updates, and user consent rules.

Any future permission should be reviewed against the Chrome Web Store single-purpose and minimum-permission expectations before being added.
