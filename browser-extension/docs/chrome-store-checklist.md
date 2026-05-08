# Chrome Web Store Checklist

This checklist tracks review concerns for the Clearead extension. Phase 1 is a foundation and should not be described as full Chrome Web Store readiness yet.

## Permission Minimisation

- [x] Uses only the `sidePanel` permission in Phase 1.
- [x] Does not request `host_permissions`.
- [x] Does not request `<all_urls>`.
- [x] Does not request `tabs`, `scripting`, `storage`, `contextMenus`, or clipboard permissions.
- [x] Does not register content scripts.
- [ ] Re-check permissions before every new feature is added.
- [ ] Add a clear justification for any future permission.

## Remote Code

- [x] Uses local HTML, CSS, and JavaScript only.
- [x] Does not load scripts from a CDN.
- [x] Does not use `eval` or dynamic remote executable code.
- [x] Does not include API keys, secrets, tokens, or private URLs.
- [ ] Re-check packaged files before release.

## Privacy And Data Flow

- [x] Pasted text stays local in Phase 1.
- [x] No backend requests are made.
- [x] No AI service requests are made.
- [x] No dictionary service requests are made.
- [x] No webpage content is read automatically.
- [ ] Create user-facing privacy policy before store submission.
- [ ] Document any future server-side processing before implementation.

## Packaging And Review

- [ ] Add final extension icons in required Chrome Web Store sizes.
- [ ] Test loading as an unpacked extension in Chrome.
- [ ] Test extension action click opens the side panel.
- [ ] Run `npm run validate` before packaging.
- [ ] Confirm `manifest.json` includes only implemented features.
- [ ] Package only required production files.
- [ ] Prepare accurate Chrome Web Store listing text.
- [ ] Do not claim AI, dictionary, page modification, readable font, or reading ruler features until implemented.
