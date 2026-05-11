# Clearead Browser Extension Privacy Policy

Last updated: May 11, 2026

This policy describes how the Clearead browser extension handles data. It is intended for publication with the Chrome Web Store submission after the project owner confirms the public contact address and production backend retention settings.

## What Clearead Does

Clearead is a reading support extension. It lets users:

- Paste text into the side panel and request a summary.
- Apply local page reading tools, including readable fonts, Highlight, Lens, and Line guide.
- Look up one English word using either the side panel word box or an opt-in right-click menu.
- Open the full Clearead website from a user-clicked link.

## Information The Extension Handles

Clearead handles only the information needed for these user-facing features:

- Pasted text: text that the user manually enters into the side panel and submits by clicking Summary or pressing Enter.
- Dictionary word: one English word that the user types into the side panel word box, or one selected word passed by Chrome after the user clicks the Clearead right-click menu item.
- Page content used locally for page tools: the active page DOM may be inspected or cloned inside the current tab to apply visible reading tools. Lens uses a local, non-interactive clone inside the same tab so it can show magnified content under the pointer.
- Session state: `chrome.storage.session` stores whether the opt-in right-click dictionary menu is enabled, plus recent tab/window/time metadata used to keep page-tool state in sync after the service worker sleeps.

Clearead handles the categories listed above for its reading support features.

## When Data Leaves The Browser

Pasted text leaves the browser only when the user runs Summary. The extension sends the submitted text to the Clearead backend:

- `POST https://clear-read-a3c2gyajcjf5agfd.australiaeast-01.azurewebsites.net/api/plugin/summary`

Dictionary words leave the browser only when the user explicitly requests a lookup. The extension sends the validated one-word lookup to the Clearead backend:

- `POST https://clear-read-a3c2gyajcjf5agfd.australiaeast-01.azurewebsites.net/api/dictionary`

Page-tool content stays in the browser. Readable fonts, Highlight, Lens, and Line guide run locally in the active tab.

## How Data Is Used

Clearead uses submitted text only to provide the requested reading support result:

- Summary text is used to generate and return a concise reading-support summary.
- Dictionary words are used to generate and return a simple meaning and word-part explanation.
- Page DOM access is used locally to apply visible reading tools in the active tab.
- Session state is used only to remember the current right-click dictionary toggle and keep page-tool button state accurate during the browser session.

Clearead uses handled data for the requested Summary, Dictionary, and page reading support features.

## Sharing And Service Providers

The extension sends Summary and Dictionary requests to the Clearead backend origin listed above. The backend may use Clearead-configured server-side model providers, including OpenAI, to generate requested summaries and word explanations. API keys and model credentials stay on the backend.

## Storage And Retention

The extension uses `chrome.storage.session` only for:

- The current right-click dictionary enabled boolean.
- Recent tab/window/time metadata used for page-tool state sync.
- A short dictionary error notice if a right-click lookup fails before the side panel can display the message.

Session storage is cleared by Chrome when the extension is disabled, reloaded, updated, or when the browser restarts.

Production backend request logging and retention settings should be confirmed by the project owner before this policy is published.

## Security

The extension uses HTTPS for backend requests. Executable extension code is packaged locally, and API keys stay on the backend.

The OpenDyslexic fonts used by the readable-font option are packaged locally with the extension.

## Chrome Web Store Limited Use

The use of information received from Google APIs will adhere to the Chrome Web Store User Data Policy, including the Limited Use requirements.

## User Choices

Users can:

- Choose when to submit text for Summary.
- Turn the right-click dictionary menu on or off from the side panel.
- Avoid right-click lookup and use only the side panel word box.
- Turn page tools off by choosing Original font and No ruler.
- Remove the extension from Chrome at any time.

## Contact

For privacy questions, use the contact details provided by the project owner in the Chrome Web Store listing and the published Clearead website.
