# Security And Privacy Development Log

Last updated: 2026-05-09

This is a development log for the Clearead browser extension. It supports review, presentation, and later Chrome Web Store preparation. It is not the final public privacy policy.

## Official Chrome References Checked

- Chrome Web Store Program Policies: https://developer.chrome.com/docs/webstore/program-policies/
- Declare permissions: https://developer.chrome.com/docs/extensions/develop/concepts/declare-permissions
- Chrome Web Store privacy fields: https://developer.chrome.com/docs/webstore/cws-dashboard-privacy
- Remote hosted code guidance: https://developer.chrome.com/docs/extensions/develop/migrate/remote-hosted-code

## Store-Readiness Principles We Are Applying

- Keep the extension Manifest V3.
- Request only permissions that match implemented features.
- Avoid broad webpage host permissions such as `<all_urls>`.
- Do not register static content scripts for every page.
- Use active user actions before touching the current webpage.
- Package all executable JavaScript with the extension.
- Do not load remote executable code, remote scripts, or dynamic code.
- Do not include API keys, tokens, private URLs, or secrets in the extension.
- Be explicit about what user text leaves the browser and why.
- Keep unsupported browser-restricted pages honest instead of hiding failures.

## Permission Decisions

- `sidePanel`: required for the Clearead reading support side panel.
- `activeTab`: grants temporary access to the current page after the user activates Clearead.
- `scripting`: injects the packaged page-tool script only for the active page after user action.
- `contextMenus`: creates one opt-in selected-text right-click dictionary item.
- `storage`: uses `chrome.storage.session` only for one dictionary enabled boolean.
- `host_permissions`: limited to `https://clear-read-a3c2gyajcjf5agfd.australiaeast-01.azurewebsites.net/*` so the side panel can submit pasted text to the Clearead backend.

Permissions intentionally not requested:

- `<all_urls>`
- broad wildcard host permissions
- `tabs`
- clipboard permissions
- static `content_scripts`

## Data Flow Decisions

Pasted summary text:

- The user manually pastes text into the side panel.
- Nothing is sent while the user types.
- Text is sent only after the user clicks Summary.
- The request goes to `POST /api/process-text` on the deployed Clearead backend.
- The side panel renders only summary and key points.
- Extra backend fields such as original text or fallback details are not displayed.
- The extension itself does not call OpenAI, third-party AI services, analytics, or remote dictionary services.

Backend processing:

- The extension and the website are two frontend clients for the same backend processing route.
- Backend-side model calls, GPT fallback, algorithm fallback, API keys, logging, and retention must remain backend-side concerns.
- Before release, backend retention/logging and the final privacy policy wording still need explicit confirmation.

Page tools:

- Page tools run only after toolbar popup activation and side panel user action.
- Font tools inject a local style element.
- Highlight and Line guide create local overlay elements.
- Lens creates a local, non-interactive clone of the current page DOM inside the same tab for magnification.
- Lens removes scripts and media sources from the clone.
- Page content is not sent to the backend, not sent to third parties, and not stored.
- Page-tool state is synchronized by querying the active page, not by storing page content or preferences.

Right-click dictionary:

- The menu is off by default.
- The user must enable it in the side panel before the context menu item appears.
- It appears only for selected text on normal `http` and `https` webpages.
- Chrome provides `info.selectionText` only after the user clicks the Clearead menu item.
- The selected text is normalized, capped at 80 characters, and processed locally.
- Selected text is not sent to the backend and is not stored.
- `chrome.storage.session` stores only whether the menu is enabled in the current browser session.

Website link:

- The popup and side panel can open `https://clearead.azurewebsites.net/` as a normal user-clicked link.
- No host permission is requested for the website link.
- Opening the website does not allow the extension to inspect that website tab.

## Development Timeline Notes

- Phase 1 created the Manifest V3 foundation with minimum permissions and compliance docs.
- Phase 3 connected the side panel Summary flow to the deployed Clearead backend after endpoint verification.
- Phase 4 added readable page tools with `activeTab` and `scripting`, no broad host permissions, and clearer restricted-page errors.
- Phase 4c restored a popup activation step so page tools follow explicit user activation.
- Phase 5 added dictionary lookup, then changed it to right-click use, then added a side-panel opt-in toggle.
- Phase 5 follow-up used `chrome.storage.session` for the dictionary enabled boolean because Manifest V3 service workers can sleep.
- Phase 6 added normal website links without adding website host permissions.
- Phase 7 added packaged PNG icons and validation for icon dimensions.
- Visual polish aligned the extension with the Clearead website palette without adding permissions.
- Recent Lens work returned to a local magnifier model and now documents the local DOM clone behavior honestly.
- Recent state-sync work added a `get-page-tool-state` command so side panel buttons reflect the actual active page state after reopening.

## Open Release Risks

- Final Chrome Web Store privacy disclosure is not complete.
- Final user-facing privacy policy is not complete.
- Backend data retention, logging, and subprocessors still need confirmation.
- Final production backend origin may change before release.
- Lens behavior still needs manual usability testing on several normal websites.
- The extension has not yet gone through a final package contents audit.

## Future Change Rules

- Any new permission must have a concrete implemented feature and matching documentation update.
- Any new network request must document endpoint, trigger, request body, response fields used, and data purpose.
- Any new storage use must document key, value, lifetime, and why session-only storage is not enough.
- Any page-content feature must state whether it reads, clones, stores, or sends page content.
- Worker chats must not edit `.codex-local/clearead-extension-memory.md`; only Central Brain may update it.
