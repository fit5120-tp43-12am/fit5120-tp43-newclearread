# Chrome Web Store Checklist

This checklist tracks review concerns for the Clearead extension and supports final Chrome Web Store preparation.

## Permission Minimisation

- [x] Uses the `sidePanel` permission for the side panel UI.
- [x] Uses the `activeTab` permission for temporary access to the active page after user action.
- [x] Uses the `scripting` permission for programmatic injection of local packaged page-tool code.
- [x] Uses the `contextMenus` permission for one opt-in selected-text right-click dictionary item.
- [x] Uses the `storage` permission only for session state: the right-click dictionary enabled boolean and a recent page activation tab/window/time record.
- [x] Uses only `https://clear-read-a3c2gyajcjf5agfd.australiaeast-01.azurewebsites.net/*` as a narrow deployed backend host permission.
- [x] Opens `https://clearead.azurewebsites.net/` as a user-clicked website link without adding it to `host_permissions`.
- [x] Declares only packaged OpenDyslexic WOFF2 font files as web-accessible resources for normal webpages.
- [x] Keeps `<all_urls>` outside the manifest.
- [x] Keeps broad host permissions outside the manifest.
- [x] Keeps `tabs` and clipboard permissions outside the manifest.
- [x] Uses programmatic page-tool injection after user action.
- [x] Validation rejects broad host permissions, wildcard host permissions, static content scripts, unexpected popup paths, unexpected extension permissions, and common unsafe source patterns.
- [x] Validation checks the packaged icon files and declared PNG dimensions.
- [x] Validation recursively scans packaged source HTML, CSS, and JavaScript for common unsafe source patterns.
- [x] Validation checks duplicated extension constants such as backend URL and text length limits.
- [ ] Re-check permissions before every new feature is added.
- [ ] Confirm the final production backend host permission before any production store package if the backend origin changes.

## Remote Code

- [x] Uses local HTML, CSS, and JavaScript only.
- [x] Uses only JavaScript and page-tool code packaged with the extension.
- [x] Uses packaged local OpenDyslexic font files.
- [x] Injects only local packaged code into the active tab after a user clicks a page-tool control.
- [x] Keeps CDN scripts outside the package.
- [x] Keeps `eval` and dynamic remote executable code outside the package.
- [x] Keeps API keys, secrets, and tokens outside the package.
- [x] Packaging script stages only `manifest.json`, `public/`, and `src/` for the Chrome Web Store ZIP.
- [ ] Re-check packaged files before release.

## Privacy And Data Flow

- [x] Pasted text is sent only after the user runs Summary.
- [x] Pasted text is sent to `POST https://clear-read-a3c2gyajcjf5agfd.australiaeast-01.azurewebsites.net/api/plugin/summary`.
- [x] Text stays local while the user types.
- [x] Webpage content is touched only after user activation for page tools.
- [x] Page tools keep webpage content local to the active tab.
- [x] Lens magnification uses a local non-interactive page clone only inside the current tab, refreshes it after ordinary webpage DOM changes, removes scripts, inline event handlers, form actions, and embedded media sources from the clone, and turns itself off with a concise message if the page changes too rapidly.
- [x] Page tools run only after the user activates Clearead from the toolbar popup and opens the side panel for that page or clicks a side panel page-tool control.
- [x] Right-click dictionary is off by default and appears only after the user enables it with the side panel Right-click lookup button.
- [x] Selected-word lookup reads only Chrome-provided selected text after the user clicks the Clearead right-click menu item.
- [x] Selected-word lookup is validated as one English word before being sent to the Clearead backend dictionary route.
- [x] Selected-word lookup has request-only lifetime.
- [x] Right-click lookup button state is stored only as a `chrome.storage.session` boolean.
- [x] Recent page activation state is stored only as tab/window/time metadata in `chrome.storage.session`.
- [x] Selected-word lookup uses only Chrome-provided selected text.
- [x] Pasted text has request-only lifetime in the extension.
- [x] Page-tool state is page-local and reload-scoped.
- [x] Analytics services are absent from the extension.
- [x] Summary and Dictionary network requests go through the shared Clearead backend.
- [x] The website frontend and extension both use the shared Clearead backend for Summary and Dictionary requests.
- [x] Website links open only after user click.
- [x] API keys and secrets for any server-side model services stay on the backend side.
- [x] User-facing privacy policy text exists at `docs/privacy-policy.md`.
- [ ] Confirm and disclose any Clearead-configured backend summarisation or model services used to generate summaries.
- [ ] Confirm final production backend origin before store submission.
- [ ] Confirm production backend retention and logging behavior before store submission.
- [x] Chrome Web Store privacy and data-use disclosure text exists at `docs/chrome-store-submission.md`.
- [ ] Publish the final privacy policy at a public URL before store submission.
- [ ] Review final Chrome Web Store privacy fields against the published privacy policy before submission.

## Feature Accuracy

- [x] Summary is implemented against the existing Clearead backend endpoint.
- [x] Readable font support is implemented for user-triggered active-page use.
- [x] Reading ruler support is implemented for user-triggered active-page use.
- [x] Selected-word lookup is implemented against the existing Clearead backend dictionary route for validated one-word requests.
- [x] Summary uses the shared `/api/plugin/summary` route and renders the returned full-document summary text.
- [x] Listing copy claims the implemented extension features: Summary, readable fonts, reading rulers, one-word Dictionary lookup, and website link.
- [x] Add extension icons in 16, 32, 48, and 128 pixel sizes.
- [x] Package OpenDyslexic WOFF2 files and the SIL Open Font License text for the OpenDyslexic font mode.
- [ ] Complete final brand review for icon artwork before store submission.
- [x] Prepare accurate Chrome Web Store listing text in `docs/chrome-store-submission.md`.
- [ ] Capture final Chrome Web Store screenshots and promotional image.

## Packaging And Review

- [ ] Test loading as an unpacked extension in Chrome.
- [ ] Test extension action click opens the popup first.
- [ ] Test popup button opens the side panel and closes the popup.
- [ ] Test Summary against the deployed backend.
- [ ] Test a development build with an unavailable backend to verify the error state.
- [ ] Test Original, Verdana, OpenDyslexic, Calibri, No ruler, Highlight, local Lens magnification, and Line guide on normal webpages.
- [ ] Test that the Reading ruler section says: "Best on text pages. If Lens looks blank, try Highlight or Line guide."
- [ ] Test that selecting Lens keeps the current Font/Ruler state visible and shows a separate Lens tip below it.
- [ ] Test Lens on one complex media-heavy webpage and confirm it either remains usable or says: "Lens stopped on this dynamic page. Try Highlight or Line guide."
- [ ] Test that closing and reopening the side panel syncs Font and Reading ruler button state with the actual active page.
- [ ] Test right-click dictionary default-off behavior, side panel Right-click lookup button state, one-line word input Explain flow, backend dictionary card fields, one-word validation, pronunciation button, omitted Save action, and disabling again on normal webpages.
- [ ] Test Open website links from the popup and side panel.
- [ ] Test restricted pages such as `chrome://extensions` for the message: "Chrome blocks tools on this page. Try another webpage."
- [ ] Test direct PDF, DOCX, DOC, or TXT file URLs for the message: "File pages may not support page tools. Click Open website to upload the file."
- [ ] Test the active-tab access recovery path on a normal webpage, where possible, for the message: "Need page access. In Chrome, click Extensions (puzzle icon) > Clearead > Open Clearead for this page."
- [ ] Run `npm run validate` before packaging.
- [ ] Confirm `manifest.json` includes only implemented features.
- [x] Add repeatable packaging script for only required production files.
- [ ] Run `npm run package` and audit the produced ZIP before upload.
