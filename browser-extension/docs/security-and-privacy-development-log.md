# Security And Privacy Development Log

Last updated: 2026-05-17

This development log supports review, presentation, and Chrome Web Store release maintenance. The public privacy policy text is maintained in `docs/privacy-policy.md`.

## Official Chrome References Checked

- Chrome Web Store Program Policies: https://developer.chrome.com/docs/webstore/program-policies/
- Declare permissions: https://developer.chrome.com/docs/extensions/develop/concepts/declare-permissions
- Chrome Web Store privacy fields: https://developer.chrome.com/docs/webstore/cws-dashboard-privacy
- Remote hosted code guidance: https://developer.chrome.com/docs/extensions/develop/migrate/remote-hosted-code

## Store-Readiness Principles We Are Applying

- Keep the extension Manifest V3.
- Request only permissions that match implemented features.
- Keep webpage host access narrow.
- Use programmatic page-tool injection after user action.
- Use active user actions before touching the current webpage.
- Package all executable JavaScript with the extension.
- Keep executable code local to the extension package.
- Keep API keys, tokens, private URLs, and secrets on the backend side.
- Be explicit about what user text leaves the browser and why.
- Surface clear messages for browser-restricted pages.

## Permission Decisions

- `sidePanel`: required for the Clearead reading support side panel.
- `activeTab`: grants temporary access to the current page after the user activates Clearead.
- `scripting`: injects the packaged page-tool script only for the active page after user action.
- `contextMenus`: creates one opt-in selected-text right-click dictionary item.
- `storage`: uses `chrome.storage.session` only for session state: one dictionary enabled boolean and a recent page activation tab/window/time record.
- `host_permissions`: limited to `https://clear-read-a3c2gyajcjf5agfd.australiaeast-01.azurewebsites.net/*` so the extension can submit pasted Summary text and explicit one-word dictionary lookups to the Clearead backend.

Permissions outside the current implementation:

- `<all_urls>`
- broad wildcard host permissions
- `tabs`
- clipboard permissions
- static `content_scripts`

## Data Flow Decisions

Pasted summary text:

- The user manually pastes text into the side panel.
- Text stays local while the user types.
- Text is sent only after the user runs Summary.
- The request goes to `POST /api/plugin/summary` on the deployed Clearead backend.
- The side panel renders only the returned full-document summary text.
- The side panel displays the returned extension summary text.
- Extension network requests go to the shared Clearead backend for Summary and Dictionary.

Backend processing:

- The extension and the website are two frontend clients for the same backend processing route.
- Backend-side model calls, GPT fallback, algorithm fallback, API keys, logging, and retention are handled by the Clearead backend.
- Privacy policy wording is maintained in `docs/privacy-policy.md`.

Page tools:

- Page tools run only after toolbar popup activation and side panel user action.
- Font tools inject a local style element.
- Highlight and Line guide create local overlay elements.
- Lens creates a local, non-interactive clone of the current page DOM inside the same tab for magnification.
- Lens refreshes that local clone after ordinary webpage DOM changes, such as dropdown menus, while Lens is active.
- Lens removes scripts, inline event handlers, form actions, and embedded media sources from the clone.
- Lens is presented as a text-page reading aid. If a media-heavy or animation-heavy page changes too frequently while Lens is active, the content script turns Lens off and shows: "Lens stopped on this dynamic page. Try Highlight or Line guide."
- Page content stays local to the active tab during page-tool use.
- Page-tool state is synchronized by querying the active page.

Right-click dictionary:

- The menu is off by default.
- The user must enable the Right-click lookup button in the side panel before the context menu item appears.
- It appears only for selected text on normal `http` and `https` webpages.
- Chrome provides `info.selectionText` only after the user clicks the Clearead menu item.
- The selected text is normalized, checked against the 50-character lookup limit, and validated as one English word before any backend request.
- Valid selected-word lookups call the deployed Clearead backend dictionary route and render Simple meaning, Word parts, and Meaning from parts.
- The current dictionary card omits Save.
- The one-line side panel dictionary word input uses the same one-word validation and backend dictionary route only after Explain or Enter.
- Phrase and sentence selections are rejected locally before a dictionary request.
- Selected words are sent only after explicit lookup.
- `chrome.storage.session` stores only whether the menu is enabled in the current browser session and a recent page activation tab/window/time record for page-tool state sync.

Website link:

- The popup and side panel can open `https://clearead.azurewebsites.net/` as a normal user-clicked link.
- The website link uses normal user-clicked tab opening.
- The website tab remains outside extension inspection.

## Development Timeline Notes

- Phase 1 created the Manifest V3 foundation with minimum permissions and compliance docs.
- Phase 3 connected the side panel summary flow to the deployed Clearead backend after endpoint verification.
- Phase 4 added readable page tools with `activeTab`, `scripting`, narrow host access, and clearer restricted-page errors.
- Phase 4c restored a popup activation step so page tools follow explicit user activation.
- Phase 5 added dictionary lookup, then changed it to right-click use, then added a side-panel opt-in control.
- Phase 5 follow-up used `chrome.storage.session` for the dictionary enabled boolean because Manifest V3 service workers can sleep.
- Phase 6 added normal website links as user-clicked external links.
- Phase 7 added packaged PNG icons and validation for icon dimensions.
- Visual polish aligned the extension with the Clearead website palette using the existing permission set.
- Recent Lens work returned to a local magnifier model and now documents the local DOM clone behavior honestly.
- Recent state-sync work added a `get-page-tool-state` command so side panel buttons reflect the actual active page state after reopening.
- Lens safety work added concise text-page guidance, clearer active-tab reconnection instructions, and a high-change safety cutoff for complex animated or media-heavy pages.

## Release Review Status

- Chrome Web Store privacy disclosure text exists in `docs/chrome-store-submission.md`.
- User-facing privacy policy text exists in `docs/privacy-policy.md`.
- Backend processing and provider disclosure are documented in the privacy materials.
- The current package uses the deployed backend origin documented in the manifest.
- Lens behavior has manual smoke-test coverage from the release review pass and includes a clear fallback message for dynamic pages.
- The package script stages only production files for the generated ZIP.

## Future Change Rules

- Any new permission must have a concrete implemented feature and matching documentation update.
- Any new network request must document endpoint, trigger, request body, response fields used, and data purpose.
- Any new storage use must document key, value, lifetime, and the reason for its storage scope.
- Any page-content feature must state whether it reads, clones, stores, or sends page content.
