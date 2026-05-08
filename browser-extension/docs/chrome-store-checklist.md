# Chrome Web Store Checklist

This checklist tracks review concerns for the Clearead extension. Phase 6 is not a claim of Chrome Web Store readiness.

## Permission Minimisation

- [x] Uses the `sidePanel` permission for the side panel UI.
- [x] Uses the `activeTab` permission for temporary access to the active page after user action.
- [x] Uses the `scripting` permission for programmatic injection of local packaged page-tool code.
- [x] Uses the `contextMenus` permission for one opt-in selected-text right-click dictionary item.
- [x] Uses the `storage` permission only for one `chrome.storage.session` boolean that tracks whether the user enabled the dictionary menu during the current browser session.
- [x] Uses only `https://clear-read-a3c2gyajcjf5agfd.australiaeast-01.azurewebsites.net/*` as a narrow deployed backend host permission.
- [x] Opens `https://clearead.azurewebsites.net/` as a user-clicked website link without adding it to `host_permissions`.
- [x] Does not request `<all_urls>`.
- [x] Does not request broad host permissions.
- [x] Does not request `tabs` or clipboard permissions.
- [x] Does not register static content scripts.
- [x] Validation rejects broad host permissions, wildcard host permissions, static content scripts, unexpected popup paths, and unexpected extension permissions.
- [ ] Re-check permissions before every new feature is added.
- [ ] Confirm the final production backend host permission before any production store package if the backend origin changes.

## Remote Code

- [x] Uses local HTML, CSS, and JavaScript only.
- [x] Uses JavaScript modules and page-tool code packaged with the extension.
- [x] Injects only local packaged code into the active tab after a user clicks a page-tool control.
- [x] Does not load scripts from a CDN.
- [x] Does not use `eval` or dynamic remote executable code.
- [x] Does not include API keys, secrets, or tokens.
- [ ] Re-check packaged files before release.

## Privacy And Data Flow

- [x] Pasted text is sent only after the user clicks Summary.
- [x] Pasted text is sent to `POST https://clear-read-a3c2gyajcjf5agfd.australiaeast-01.azurewebsites.net/api/process-text`.
- [x] Text is not sent automatically while typing.
- [x] Webpage content is not read automatically.
- [x] Page tools do not send webpage content to the backend.
- [x] Page tools run only after the user activates Clearead from the toolbar popup and clicks a side panel page-tool control.
- [x] Right-click dictionary is off by default and appears only after the user enables it in the side panel.
- [x] Selected-word lookup reads only Chrome-provided selected text after the user clicks the Clearead right-click menu item.
- [x] Selected-word lookup is processed locally and is not sent to the Clearead backend.
- [x] Selected-word lookup is not stored.
- [x] Dictionary toggle state is stored only as a `chrome.storage.session` boolean and does not include selected text.
- [x] No surrounding page content is read for selected-word lookup.
- [x] Pasted text is not saved by the extension.
- [x] Page-tool state is not persisted across page reloads.
- [x] No analytics are included.
- [x] The extension itself does not perform AI processing or call OpenAI, third-party AI APIs, analytics services, or remote dictionary services.
- [x] The website frontend and extension both use the shared Clearead backend processing route.
- [x] Website links open only after user click and are not used for background data transfer.
- [x] API keys and secrets for any server-side model services must stay on the backend side and must not be stored in the extension.
- [x] The disabled Simplify action does not send data.
- [ ] Create user-facing privacy policy before store submission.
- [ ] Confirm and disclose any Clearead-configured backend summarisation or model services used to generate summaries and key points.
- [ ] Confirm final production backend origin before store submission.
- [ ] Confirm production backend retention and logging behavior before store submission.
- [ ] Prepare final Chrome Web Store privacy and data-use disclosures before submission.

## Feature Accuracy

- [x] Summary is implemented against the existing Clearead backend endpoint.
- [x] Readable font support is implemented for user-triggered active-page use.
- [x] Reading ruler support is implemented for user-triggered active-page use.
- [x] Selected-word lookup is implemented as local glossary and fallback guidance only.
- [x] Simplify remains disabled because no stable public simplify endpoint is exposed.
- [x] Text-to-speech, file upload, remote dictionary service, automatic page scanning, and static content scripts are not claimed as implemented extension features.
- [ ] Add final extension icons in required Chrome Web Store sizes.
- [ ] Prepare accurate Chrome Web Store listing text.

## Packaging And Review

- [ ] Test loading as an unpacked extension in Chrome.
- [ ] Test extension action click opens the popup instead of the side panel.
- [ ] Test popup button opens the side panel and closes the popup.
- [ ] Test Summary against the deployed backend.
- [ ] Test a development build with an unavailable backend to verify the error state.
- [ ] Test Apply readable font, Reset page font, and Toggle reading ruler on normal webpages.
- [ ] Test right-click dictionary default-off behavior, side panel enablement, known and unknown selections, and disabling again on normal webpages.
- [ ] Test Open website links from the popup and side panel.
- [ ] Test restricted pages such as `chrome://extensions` for the message: "Chrome does not allow extensions to modify this page. Try a normal webpage."
- [ ] Test the active-tab access recovery path on a normal webpage, where possible, for the message asking the user to open the target webpage, click the Clearead toolbar icon, and try again.
- [ ] Run `npm run validate` before packaging.
- [ ] Confirm `manifest.json` includes only implemented features.
- [ ] Package only required production files.
