# Chrome Web Store Submission

This document collects Chrome Web Store dashboard text for the Clearead extension release.

Official references checked on May 11, 2026:

- Chrome Web Store Program Policies: https://developer.chrome.com/docs/webstore/program-policies/policies
- Privacy practices fields: https://developer.chrome.com/docs/webstore/cws-dashboard-privacy
- Listing requirements: https://developer.chrome.com/docs/webstore/program-policies/listing-requirements
- Listing image guidance: https://developer.chrome.com/docs/webstore/best-listing

## Store Listing

### Item Name

Clearead

### Short Summary

Reading support for pasted text, page fonts, reading rulers, and one-word dictionary help.

### Detailed Description

Clearead helps readers work with dense text in a calmer, more accessible way.

Use the side panel to paste text and request a concise reading-support summary. On ordinary webpages, apply readable fonts or reading rulers after opening Clearead for the current page. You can also look up one English word using the side panel word box or an opt-in right-click menu.

Main features:

- Summarise pasted text only when you run Summary.
- Apply readable page fonts: Original, Verdana, OpenDyslexic, or Calibri.
- Use reading rulers: Highlight, Lens, or Line guide.
- Look up one English word with a clear meaning and word-part explanation.
- Open the full Clearead website for broader tools.

Privacy-conscious design:

- Host access is limited to the Clearead backend used for Summary and Dictionary.
- Page tools run locally in the active tab after user action.
- Summary and Dictionary requests are sent to the Clearead backend after explicit user action.
- Extension files, fonts, and icons are packaged locally.
- Session state is limited to the right-click lookup toggle, page-tool activation metadata, and short error notices.

### Suggested Category

Accessibility

### Language

English

## Privacy Practices Tab

### Single Purpose

Clearead provides reading support by summarising user-submitted text, applying local page reading tools, and explaining one selected English word after explicit user action.

### Permission Justifications

`sidePanel`

Used to show the Clearead reading support interface in Chrome's side panel.

`activeTab`

Used so a user action can grant temporary access to the current tab for page reading tools.

`scripting`

Used to inject the local packaged page-tool script into the active tab only after the user opens Clearead for that page or clicks a page-tool/dictionary action.

`contextMenus`

Used to create one opt-in selected-text right-click item, "Explain with Clearead". The menu starts disabled and is limited to normal http and https webpages.

`storage`

Used for `chrome.storage.session`: the current right-click dictionary enabled boolean, recent tab/window/time metadata for page-tool state sync, and a short dictionary error notice.

`host_permissions`

`https://clear-read-a3c2gyajcjf5agfd.australiaeast-01.azurewebsites.net/*`

Used only to send explicit user-submitted Summary text and explicit one-word Dictionary lookups to the Clearead backend.

### Remote Code Declaration

Dashboard answer: No.

All extension HTML, CSS, JavaScript, icons, and OpenDyslexic font files are packaged locally. The extension performs HTTPS data requests to the Clearead backend for Summary and Dictionary features. Executable extension code comes from the packaged files.

### Data Collection Disclosure

Recommended dashboard selection:

- Website content: Yes.
- Personally identifiable information: select only if the final team policy treats user-submitted text as personal information.
- Health information: select only if the final team policy treats user-submitted text as health information.
- Financial and payment information: not selected for the current extension features.
- Authentication information: not selected for the current extension features.
- Personal communications: select only if the final team policy treats pasted text as personal communications.
- Location: not selected for the current extension features.
- Web history: not selected for the current extension features.
- User activity: not selected for the current extension features.

Explanation:

The extension handles user-submitted text for Summary, one user-submitted or selected English word for Dictionary, and local active-page DOM access for visible page tools. Page-tool DOM access stays inside the current tab. Summary and Dictionary requests are transmitted after explicit user action.

### Limited Use Certification

Use the dashboard certification only if the final build still matches this statement:

- Data is used only for user-facing Summary, Dictionary, and page reading support features.
- Data stays within the user-facing Summary, Dictionary, and page reading support purposes.
- Data transfer is limited to providing or improving the user-facing feature, complying with law, or protecting users.
- The extension complies with the Chrome Web Store User Data Policy, including Limited Use requirements.

### Privacy Policy URL

Use the public project privacy policy URL that publishes the text from `docs/privacy-policy.md`.

## Listing Assets

Release asset set:

- Store icon: 128x128 PNG. Current packaged file: `public/icons/icon-128.png`.
- Screenshots: at least one, preferably up to five. Use 1280x800 or 640x400. Show actual extension UI.
- Small promotional tile: 440x280.

Recommended screenshots:

- Side panel Summary with pasted text and returned summary.
- Page tools showing Font and Reading ruler controls.
- Lens or Highlight active on a normal text webpage.
- Dictionary word box result.
- Right-click dictionary card on a webpage.

Asset guidance:

- Use clear, current UI screenshots.
- Keep screenshots full bleed with square corners and no padding.
- Avoid heavy text overlays.
- Keep screenshots aligned with the current extension build.

## Test Instructions For Reviewers

The extension works without login or paid account setup.

Suggested text:

1. Load the extension and click the Clearead toolbar icon.
2. Click "Open Clearead for this page" to open the side panel.
3. Paste a short paragraph into the text box and click Summary.
4. On a normal webpage, try Verdana, OpenDyslexic, Highlight, Lens, Line guide, and No ruler.
5. Turn on Right-click lookup, select one English word on a normal webpage, right-click it, and choose "Explain with Clearead".
6. Try typing one English word into the side panel Word box and click Explain.
7. Restricted browser pages such as `chrome://extensions` are expected to show a friendly unsupported-page message.

## Final Copy Checks

- Use measured wording and supported feature claims.
- Describe page tools as user-triggered active-tab tools.
- Keep file upload, account sync, saved history, and automatic page scanning outside the extension listing.
- Keep the listing consistent with the privacy policy and actual manifest permissions.
