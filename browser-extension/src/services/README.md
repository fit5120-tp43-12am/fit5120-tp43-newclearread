# Services

This folder contains service adapters and local helper modules for the extension.

Current modules:

- `backend-api.js`: sends pasted text to the deployed Clearead backend only after the user clicks Summary.
- `local-dictionary.js`: provides a small built-in selected-word glossary and fallback guidance for the right-click dictionary flow. It does not fetch data, store selected text, or call a remote dictionary service.
