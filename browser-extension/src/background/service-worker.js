const MAX_LOOKUP_TERM_CHARS = 80;
const DICTIONARY_DEMO_TEXT = "demo demo demo";

function normaliseLookupTerm(term) {
  return String(term || "")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, MAX_LOOKUP_TERM_CHARS);
}

function createDemoWordParts() {
  return [
    {
      part: "demo",
      meaning: DICTIONARY_DEMO_TEXT,
      type: "Prefix",
    },
    {
      part: "demo",
      meaning: DICTIONARY_DEMO_TEXT,
      type: "Root",
    },
    {
      part: "demo",
      meaning: DICTIONARY_DEMO_TEXT,
      type: "Suffix",
    },
  ];
}

function explainLocalTerm(term) {
  const normalizedTerm = normaliseLookupTerm(term);

  if (!normalizedTerm) {
    return {
      ok: false,
      term: "",
      message: "Select one word or a short phrase on the page, then try again.",
    };
  }

  return {
    ok: true,
    term: normalizedTerm,
    simpleMeaning: DICTIONARY_DEMO_TEXT,
    wordParts: createDemoWordParts(),
    meaningFromParts: DICTIONARY_DEMO_TEXT,
    source: "demo-placeholder",
  };
}

chrome.sidePanel
  .setPanelBehavior({ openPanelOnActionClick: false })
  .catch((error) => {
    console.error("Clearead could not configure action-click side panel behavior.", error);
  });

const PAGE_TOOL_REQUEST_TYPE = "clearead:page-tool";
const PAGE_TOOL_COMMAND_TYPE = "clearead:page-tool-command-v7";
const OPEN_SIDE_PANEL_REQUEST_TYPE = "clearead:open-side-panel";
const MARK_PAGE_ACTIVATION_REQUEST_TYPE = "clearead:mark-page-activation";
const SET_DICTIONARY_ENABLED_REQUEST_TYPE = "clearead:set-dictionary-enabled";
const GET_DICTIONARY_ENABLED_REQUEST_TYPE = "clearead:get-dictionary-enabled";
const PAGE_TOOL_SCRIPT = "src/content/page-tools.js";
const DICTIONARY_CONTEXT_MENU_ID = "clearead-explain-selection";
const DICTIONARY_ENABLED_STORAGE_KEY = "cleareadDictionaryEnabled";
const NORMAL_PAGE_URL_PATTERNS = ["http://*/*", "https://*/*"];
const BROWSER_RESTRICTED_PAGE_MESSAGE =
  "Chrome does not allow extensions to modify this page. Try a normal webpage.";
const ACTIVE_TAB_ACCESS_MESSAGE =
  "Clearead needs access to the current tab before page tools can run. Open the target webpage, click the Clearead toolbar icon, then try the page tool again.";
const GENERIC_PAGE_TOOL_MESSAGE =
  "Clearead page tools could not run on this page. Try a normal webpage and reopen Clearead from the toolbar icon.";
const PAGE_TOOL_RECONNECT_MESSAGE =
  "Page tools are not connected to this page yet. Click the Clearead toolbar icon on the target webpage and open Clearead for this page.";
const RECENT_PAGE_ACTIVATION_MS = 120000;
const PAGE_TOOL_ACTIONS = new Set([
  "get-page-tool-state",
  "set-readable-font",
  "set-reading-ruler",
  "apply-readable-font",
  "reset-readable-font",
  "toggle-reading-ruler",
]);

let isDictionaryEnabled = false;
let lastPageToolActivation = {
  tabId: null,
  windowId: null,
  activatedAt: 0,
};

function markPageToolActivation(message) {
  if (!Number.isInteger(message?.tabId)) {
    return {
      ok: false,
      message: "Clearead could not identify the current tab for page tools.",
    };
  }

  lastPageToolActivation = {
    tabId: message.tabId,
    windowId: Number.isInteger(message.windowId) ? message.windowId : null,
    activatedAt: Date.now(),
  };

  return {
    ok: true,
  };
}

function hasRecentPageToolActivation(tab) {
  if (!tab?.id || lastPageToolActivation.tabId !== tab.id) {
    return false;
  }

  if (
    Number.isInteger(lastPageToolActivation.windowId) &&
    Number.isInteger(tab.windowId) &&
    lastPageToolActivation.windowId !== tab.windowId
  ) {
    return false;
  }

  return Date.now() - lastPageToolActivation.activatedAt <= RECENT_PAGE_ACTIVATION_MS;
}

async function readDictionaryEnabled() {
  const storedValues = await chrome.storage.session.get(DICTIONARY_ENABLED_STORAGE_KEY);
  return Boolean(storedValues[DICTIONARY_ENABLED_STORAGE_KEY]);
}

async function writeDictionaryEnabled(enabled) {
  await chrome.storage.session.set({
    [DICTIONARY_ENABLED_STORAGE_KEY]: Boolean(enabled),
  });
}

function removeDictionaryContextMenu() {
  return new Promise((resolve) => {
    chrome.contextMenus.remove(DICTIONARY_CONTEXT_MENU_ID, () => {
      chrome.runtime.lastError;
      resolve();
    });
  });
}

async function registerDictionaryContextMenu() {
  await removeDictionaryContextMenu();

  return new Promise((resolve, reject) => {
    chrome.contextMenus.create({
      id: DICTIONARY_CONTEXT_MENU_ID,
      title: 'Explain "%s" with Clearead',
      contexts: ["selection"],
      documentUrlPatterns: NORMAL_PAGE_URL_PATTERNS,
    }, () => {
      const runtimeError = chrome.runtime.lastError;

      if (runtimeError) {
        reject(new Error(runtimeError.message));
        return;
      }

      resolve();
    });
  });
}

async function setDictionaryEnabled(nextEnabled) {
  const enabled = Boolean(nextEnabled);

  if (enabled) {
    await registerDictionaryContextMenu();
    await writeDictionaryEnabled(true);
  } else {
    await removeDictionaryContextMenu();
    await writeDictionaryEnabled(false);
  }

  isDictionaryEnabled = enabled;

  return {
    ok: true,
    enabled: isDictionaryEnabled,
  };
}

async function syncDictionaryContextMenuFromSession() {
  const enabled = await readDictionaryEnabled();

  if (enabled) {
    await registerDictionaryContextMenu();
  } else {
    await removeDictionaryContextMenu();
  }

  isDictionaryEnabled = enabled;
  return enabled;
}

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

async function injectPageTools(tabId) {
  await chrome.scripting.executeScript({
    target: { tabId },
    files: [PAGE_TOOL_SCRIPT],
  });
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
    if (message.action === "get-page-tool-state") {
      try {
        const existingResponse = await chrome.tabs.sendMessage(tab.id, {
          type: PAGE_TOOL_COMMAND_TYPE,
          action: message.action,
        });

        if (existingResponse?.ok) {
          return existingResponse;
        }
      } catch {
        // Startup state sync should not request fresh activeTab access.
      }

      if (hasRecentPageToolActivation(tab)) {
        await injectPageTools(tab.id);

        const injectedResponse = await chrome.tabs.sendMessage(tab.id, {
          type: PAGE_TOOL_COMMAND_TYPE,
          action: message.action,
        });

        if (injectedResponse?.ok) {
          return injectedResponse;
        }

        throw new Error(
          injectedResponse?.message || "Clearead page tools could not read this page."
        );
      }

      return {
        ok: true,
        syncUnavailable: true,
        message: PAGE_TOOL_RECONNECT_MESSAGE,
      };
    }

    await injectPageTools(tab.id);

    const response = await chrome.tabs.sendMessage(tab.id, {
      type: PAGE_TOOL_COMMAND_TYPE,
      action: message.action,
      fontMode: message.fontMode,
      rulerMode: message.rulerMode,
    });

    if (!response?.ok) {
      throw new Error(response?.message || "Clearead page tools could not update this page.");
    }

    return response;
  } catch (error) {
    throw new Error(normalisePageToolError(error, tab.url));
  }
}

async function showDictionaryPopover(tab, selectedText) {
  if (!tab?.id) {
    throw new Error("Clearead could not identify the tab for dictionary lookup.");
  }

  if (isBrowserRestrictedPageUrl(tab.url)) {
    throw new Error(BROWSER_RESTRICTED_PAGE_MESSAGE);
  }

  const term = normaliseLookupTerm(selectedText);
  const explanation = explainLocalTerm(term);

  try {
    await injectPageTools(tab.id);

    const response = await chrome.tabs.sendMessage(tab.id, {
      type: PAGE_TOOL_COMMAND_TYPE,
      action: "show-dictionary-popover",
      explanation,
    });

    if (!response?.ok) {
      throw new Error(response?.message || "Clearead could not show the dictionary popover.");
    }
  } catch (error) {
    throw new Error(normalisePageToolError(error, tab.url));
  }
}

async function handleOpenSidePanelRequest(message) {
  markPageToolActivation(message);

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
  if (message?.type === MARK_PAGE_ACTIVATION_REQUEST_TYPE) {
    sendResponse(markPageToolActivation(message));
    return false;
  }

  if (message?.type === GET_DICTIONARY_ENABLED_REQUEST_TYPE) {
    syncDictionaryContextMenuFromSession()
      .then((enabled) => {
        sendResponse({
          ok: true,
          enabled,
        });
      })
      .catch((error) => {
        sendResponse({
          ok: false,
          enabled: false,
          message: error.message || "Clearead could not read the dictionary setting.",
        });
      });

    return true;
  }

  if (message?.type === SET_DICTIONARY_ENABLED_REQUEST_TYPE) {
    setDictionaryEnabled(message.enabled)
      .then((response) => sendResponse(response))
      .catch((error) => {
        sendResponse({
          ok: false,
          enabled: isDictionaryEnabled,
          message: error.message || "Clearead could not update the dictionary menu.",
        });
      });

    return true;
  }

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

chrome.runtime.onInstalled.addListener(() => {
  setDictionaryEnabled(false).catch((error) => {
    console.error("Clearead could not reset the dictionary context menu.", error);
  });
});

chrome.runtime.onStartup.addListener(() => {
  syncDictionaryContextMenuFromSession().catch((error) => {
    console.error("Clearead could not sync the dictionary context menu on startup.", error);
  });
});

async function handleDictionaryContextMenuClick(info, tab) {
  if (info.menuItemId !== DICTIONARY_CONTEXT_MENU_ID) {
    return;
  }

  const enabled = await readDictionaryEnabled();
  isDictionaryEnabled = enabled;

  if (!enabled) {
    await removeDictionaryContextMenu();
    return;
  }

  await showDictionaryPopover(tab, info.selectionText);
}

chrome.contextMenus.onClicked.addListener((info, tab) => {
  handleDictionaryContextMenuClick(info, tab).catch((error) => {
    console.error("Clearead could not show the dictionary popover.", error);
  });
});

syncDictionaryContextMenuFromSession().catch((error) => {
  console.error("Clearead could not sync the dictionary context menu.", error);
});
