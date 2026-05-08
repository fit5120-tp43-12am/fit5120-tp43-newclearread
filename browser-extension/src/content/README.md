# Content Scripts

This folder contains page-level support code for Clearead page tools.

`page-tools.js` is not registered as a static `content_scripts` entry in `manifest.json`. The background service worker injects it programmatically into the active tab only after the user activates Clearead from the toolbar popup and clicks a page-tool control in the side panel.

The script owns page-level behavior for readable font support and the reading ruler overlay. It does not scan webpages automatically, collect page text, send page content to the backend, or persist state across reloads.
