# Content Scripts

This folder contains page-level support code for Clearead page tools.

`page-tools.js` is packaged as local page-level support code. The background service worker injects it programmatically into the active tab only after the user activates Clearead from the toolbar popup and clicks a page-tool control in the side panel, or after the user clicks the Clearead selected-text context menu item.

The script owns page-level behavior for readable font support, the reading ruler overlay, and the small Clearead dictionary popover. Page-tool behavior stays local to the active tab, and dictionary backend requests are made by the background service worker after the user clicks the opt-in context menu item.
