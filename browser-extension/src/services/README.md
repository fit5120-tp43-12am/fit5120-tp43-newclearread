# Services

This folder contains service adapters and local helper modules for the extension.

Current modules:

- `backend-api.js`: sends pasted text to the deployed Clearead backend only after the user clicks Summary.
- `local-dictionary.js`: provides the current demo placeholder selected-word response shape for the right-click dictionary flow. It returns `simpleMeaning`, `wordParts`, and `meaningFromParts` fields locally. It does not fetch data, store selected text, or call a remote dictionary service.
