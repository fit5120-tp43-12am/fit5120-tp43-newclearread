chrome.sidePanel
  .setPanelBehavior({ openPanelOnActionClick: false })
  .catch((error) => {
    console.error("Clearead could not configure action-click side panel behavior.", error);
  });

const PAGE_TOOL_REQUEST_TYPE = "clearead:page-tool";
const PAGE_TOOL_COMMAND_TYPE = "clearead:page-tool-command";
const OPEN_SIDE_PANEL_REQUEST_TYPE = "clearead:open-side-panel";
const PAGE_TOOL_SCRIPT = "src/content/page-tools.js";
const BROWSER_RESTRICTED_PAGE_MESSAGE =
  "Chrome does not allow extensions to modify this page. Try a normal webpage.";
const ACTIVE_TAB_ACCESS_MESSAGE =
  "Clearead needs access to the current tab before page tools can run. Open the target webpage, click the Clearead toolbar icon, then try the page tool again.";
const GENERIC_PAGE_TOOL_MESSAGE =
  "Clearead page tools could not run on this page. Try a normal webpage and reopen Clearead from the toolbar icon.";
const PAGE_TOOL_ACTIONS = new Set([
  "apply-readable-font",
  "reset-readable-font",
  "toggle-reading-ruler",
]);

function isBrowserRestrictedPageUrl(url) {
  if (!url) {
    return false;
  }

  const normalizedUrl = url.toLowerCase();
  return (
    normalizedUrl.startsWith("chrome://") ||
    normalizedUrl.startsWith("edge://") ||
    normalizedUrl.startsWith("about:") ||
    normalizedUrl.startsWith("devtools://") ||
    normalizedUrl.startsWith("chrome-extension://") ||
    normalizedUrl.startsWith("edge-extension://") ||
    normalizedUrl.startsWith("moz-extension://") ||
    normalizedUrl.startsWith("https://chrome.google.com/webstore") ||
    normalizedUrl.startsWith("https://chromewebstore.google.com/")
  );
}

function isBrowserRestrictedPageError(message) {
  const normalizedMessage = message.toLowerCase();

  return (
    normalizedMessage.includes("extensions gallery cannot be scripted") ||
    normalizedMessage.includes("cannot access a chrome://") ||
    normalizedMessage.includes("cannot access a edge://") ||
    normalizedMessage.includes("cannot access a devtools://") ||
    normalizedMessage.includes("chrome://") ||
    normalizedMessage.includes("edge://") ||
    normalizedMessage.includes("about:") ||
    normalizedMessage.includes("devtools://") ||
    normalizedMessage.includes("chrome-extension://") ||
    normalizedMessage.includes("edge-extension://") ||
    normalizedMessage.includes("chromewebstore.google.com") ||
    normalizedMessage.includes("chrome.google.com/webstore")
  );
}

function isActiveTabAccessError(message) {
  const normalizedMessage = message.toLowerCase();

  return (
    normalizedMessage.includes("cannot access contents of url") ||
    normalizedMessage.includes("cannot access contents of the page") ||
    normalizedMessage.includes("manifest must request permission") ||
    normalizedMessage.includes("missing host permission") ||
    normalizedMessage.includes("requires host permission")
  );
}

function normalisePageToolError(error, tabUrl) {
  const message = error?.message || "";

  if (isBrowserRestrictedPageUrl(tabUrl) || isBrowserRestrictedPageError(message)) {
    return BROWSER_RESTRICTED_PAGE_MESSAGE;
  }

  if (isActiveTabAccessError(message)) {
    return ACTIVE_TAB_ACCESS_MESSAGE;
  }

  return GENERIC_PAGE_TOOL_MESSAGE;
}

async function getActiveTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

  if (!tab?.id) {
    throw new Error("Clearead could not find an active tab for page tools.");
  }

  return tab;
}

async function handlePageToolRequest(message) {
  if (!PAGE_TOOL_ACTIONS.has(message.action)) {
    throw new Error("Clearead does not recognise that page tool action.");
  }

  const tab = await getActiveTab();

  if (isBrowserRestrictedPageUrl(tab.url)) {
    throw new Error(BROWSER_RESTRICTED_PAGE_MESSAGE);
  }

  try {
    await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      files: [PAGE_TOOL_SCRIPT],
    });

    const response = await chrome.tabs.sendMessage(tab.id, {
      type: PAGE_TOOL_COMMAND_TYPE,
      action: message.action,
    });

    if (!response?.ok) {
      throw new Error(response?.message || "Clearead page tools could not update this page.");
    }

    return response;
  } catch (error) {
    throw new Error(normalisePageToolError(error, tab.url));
  }
}

async function handleOpenSidePanelRequest(message) {
  const openOptions = {};

  if (Number.isInteger(message.tabId)) {
    openOptions.tabId = message.tabId;
  } else if (Number.isInteger(message.windowId)) {
    openOptions.windowId = message.windowId;
  } else {
    throw new Error("Clearead could not identify where to open the side panel.");
  }

  await chrome.sidePanel.open(openOptions);

  return {
    ok: true,
  };
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type === OPEN_SIDE_PANEL_REQUEST_TYPE) {
    handleOpenSidePanelRequest(message)
      .then((response) => sendResponse(response))
      .catch((error) => {
        sendResponse({
          ok: false,
          message: error.message || "Clearead could not open the side panel.",
        });
      });

    return true;
  }

  if (message?.type !== PAGE_TOOL_REQUEST_TYPE) {
    return false;
  }

  handlePageToolRequest(message)
    .then((response) => sendResponse(response))
    .catch((error) => {
      sendResponse({
        ok: false,
        message: error.message || GENERIC_PAGE_TOOL_MESSAGE,
      });
    });

  return true;
});
