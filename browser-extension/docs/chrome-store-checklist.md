# Chrome Web Store Checklist

This checklist tracks review concerns for the Clearead extension. Phase 3 is not a claim of Chrome Web Store readiness.

## Permission Minimisation

- [x] Uses the `sidePanel` permission for the side panel UI.
- [x] Uses only `https://clear-read-a3c2gyajcjf5agfd.australiaeast-01.azurewebsites.net/*` as a narrow deployed backend host permission.
- [x] Does not request `<all_urls>`.
- [x] Does not request broad host permissions.
- [x] Does not request `tabs`, `scripting`, `storage`, `contextMenus`, or clipboard permissions.
- [x] Does not register content scripts.
- [x] Validation rejects broad host permissions and unexpected extension permissions.
- [ ] Re-check permissions before every new feature is added.
- [ ] Confirm the final production backend host permission before any production store package if the backend origin changes.

## Remote Code

- [x] Uses local HTML, CSS, and JavaScript only.
- [x] Uses JavaScript modules packaged with the extension.
- [x] Does not load scripts from a CDN.
- [x] Does not use `eval` or dynamic remote executable code.
- [x] Does not include API keys, secrets, or tokens.
- [ ] Re-check packaged files before release.

## Privacy And Data Flow

- [x] Pasted text is sent only after the user clicks Summary.
- [x] Pasted text is sent to `POST https://clear-read-a3c2gyajcjf5agfd.australiaeast-01.azurewebsites.net/api/process-text`.
- [x] Text is not sent automatically while typing.
- [x] Webpage content is not read automatically.
- [x] Pasted text is not saved by the extension.
- [x] No analytics are included.
- [x] The extension itself does not perform AI processing or call OpenAI, third-party AI APIs, analytics services, or dictionary services.
- [x] The website frontend and extension both use the shared Clearead backend processing route.
- [x] API keys and secrets for any server-side model services must stay on the backend side and must not be stored in the extension.
- [x] The disabled Simplify action does not send data.
- [ ] Create user-facing privacy policy before store submission.
- [ ] Confirm and disclose any Clearead-configured backend summarisation or model services used to generate summaries and key points.
- [ ] Confirm final production backend origin before store submission.
- [ ] Confirm production backend retention and logging behavior before store submission.
- [ ] Prepare final Chrome Web Store privacy and data-use disclosures before submission.

## Feature Accuracy

- [x] Summary is implemented against the existing Clearead backend endpoint.
- [x] Simplify remains disabled because no stable public simplify endpoint is exposed.
- [x] Text-to-speech, file upload, dictionary, readable font, reading ruler, webpage reading, and page modification are not claimed as implemented extension features.
- [ ] Add final extension icons in required Chrome Web Store sizes.
- [ ] Prepare accurate Chrome Web Store listing text.

## Packaging And Review

- [ ] Test loading as an unpacked extension in Chrome.
- [ ] Test extension action click opens the side panel.
- [ ] Test Summary against the deployed backend.
- [ ] Test a development build with an unavailable backend to verify the error state.
- [ ] Run `npm run validate` before packaging.
- [ ] Confirm `manifest.json` includes only implemented features.
- [ ] Package only required production files.
