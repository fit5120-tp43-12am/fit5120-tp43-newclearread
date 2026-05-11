# Services

This folder contains service adapters and local helper modules for the extension.

Current modules:

- `backend-api.js`: sends pasted text to the deployed Clearead backend only after the user runs Summary, and sends one validated dictionary word only after the user clicks Explain or presses Enter.
- `local-dictionary.js`: validates dictionary input as one English word before lookup. It does not store selected text or dictionary results.
