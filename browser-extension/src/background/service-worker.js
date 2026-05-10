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
      message: "Select one word or short phrase first.",
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
const PAGE_TOOL_STATE_MAYBE_CHANGED_TYPE = "clearead:page-tool-state-maybe-changed";
const PAGE_TOOL_SCRIPT = "src/content/page-tools.js";
const DICTIONARY_CONTEXT_MENU_ID = "clearead-explain-selection";
const DICTIONARY_ENABLED_STORAGE_KEY = "cleareadDictionaryEnabled";
const NORMAL_PAGE_URL_PATTERNS = ["http://*/*", "https://*/*"];
const BROWSER_RESTRICTED_PAGE_MESSAGE =
  "Chrome blocks tools on this page. Try another webpage.";
const FILE_PAGE_MESSAGE =
  "File pages may not support page tools. Click Open website to upload the file.";
const ACTIVE_TAB_ACCESS_MESSAGE =
  "Need page access. In Chrome, click Extensions (puzzle icon) > Clearead > Open Clearead for this page.";
const GENERIC_PAGE_TOOL_MESSAGE =
  "This page is not supported. Try a text page or click Clearead again.";
const PAGE_TOOL_RECONNECT_MESSAGE =
  "Not connected. In Chrome, click Extensions (puzzle icon) > Clearead > Open Clearead for this page.";
const RECENT_PAGE_ACTIVATION_MS = 120000;
const PAGE_TOOL_ACTIONS = new Set([
  "get-page-tool-state",
  "set-readable-font",
  "set-reading-ruler",
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
      message: "No active page found.",
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

function notifyPageToolStateMaybeChanged(tabId) {
  chrome.runtime.sendMessage(
    {
      type: PAGE_TOOL_STATE_MAYBE_CHANGED_TYPE,
      tabId,
    },
    () => {
      chrome.runtime.lastError;
    }
  );
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

function decodeForFileDetection(value) {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}

function isLikelyUploadableFileUrl(tabOrUrl) {
  const url = typeof tabOrUrl === "string" ? tabOrUrl : tabOrUrl?.url;
  const title = typeof tabOrUrl === "string" ? "" : tabOrUrl?.title;

  if (!url && !title) {
    return false;
  }

  const urlText = decodeForFileDetection(url || "").toLowerCase();
  const titleText = decodeForFileDetection(title || "").toLowerCase();
  const uploadableFilePattern = /\.(pdf|doc|docx|txt)(?:$|[\s"'&#?])/;

  if (
    urlText.includes("application/pdf") ||
    urlText.includes("application/msword") ||
    urlText.includes(
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ) ||
    urlText.includes("text/plain")
  ) {
    return true;
  }

  if (uploadableFilePattern.test(urlText)) {
    return true;
  }

  if (/\.(pdf|doc|docx|txt)\s*$/.test(titleText)) {
    return true;
  }

  try {
    const parsedUrl = new URL(url);
    const pathname = decodeURIComponent(parsedUrl.pathname).toLowerCase();
    return /\.(pdf|doc|docx|txt)$/i.test(pathname);
  } catch {
    return /\.(pdf|doc|docx|txt)(?:$|[?#])/i.test(String(url).toLowerCase());
  }
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

function isMissingContentScriptError(error) {
  const normalizedMessage = String(error?.message || "").toLowerCase();

  return (
    normalizedMessage.includes("receiving end does not exist") ||
    normalizedMessage.includes("could not establish connection") ||
    normalizedMessage.includes("no receiving end")
  );
}

function normalisePageToolError(error, tabOrUrl) {
  const message = error?.message || "";
  const tabUrl = typeof tabOrUrl === "string" ? tabOrUrl : tabOrUrl?.url;

  if (isLikelyUploadableFileUrl(tabOrUrl)) {
    return FILE_PAGE_MESSAGE;
  }

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
    throw new Error("No active page found.");
  }

  return tab;
}

async function injectPageTools(tabId) {
  await chrome.scripting.executeScript({
    target: { tabId },
    files: [PAGE_TOOL_SCRIPT],
  });
}

async function sendPageToolCommand(tabId, message) {
  return chrome.tabs.sendMessage(tabId, {
    type: PAGE_TOOL_COMMAND_TYPE,
    action: message.action,
    fontMode: message.fontMode,
    rulerMode: message.rulerMode,
    explanation: message.explanation,
  });
}

async function clearPageToolsFromTab(tabId) {
  await Promise.allSettled([
    sendPageToolCommand(tabId, {
      action: "set-reading-ruler",
      rulerMode: "none",
    }),
    sendPageToolCommand(tabId, {
      action: "set-readable-font",
      fontMode: "original",
    }),
  ]);
}

function getPageToolUpdateFallback(message) {
  if (message.action === "set-reading-ruler" && message.rulerMode === "none") {
    return {
      ok: true,
      rulerMode: "none",
      message: "No ruler is active.",
    };
  }

  if (message.action === "set-readable-font" && message.fontMode === "original") {
    return {
      ok: true,
      fontMode: "original",
      message: "Original font restored.",
    };
  }

  return null;
}

async function handlePageToolRequest(message) {
  if (!PAGE_TOOL_ACTIONS.has(message.action)) {
    throw new Error("Unknown page tool.");
  }

  const tab = await getActiveTab();

  if (isLikelyUploadableFileUrl(tab)) {
    await clearPageToolsFromTab(tab.id);
    return {
      ok: true,
      fontMode: "original",
      rulerMode: "none",
      noticeType: "error",
      message: FILE_PAGE_MESSAGE,
    };
  }

  if (isBrowserRestrictedPageUrl(tab.url)) {
    throw new Error(BROWSER_RESTRICTED_PAGE_MESSAGE);
  }

  try {
    if (message.action === "get-page-tool-state") {
      try {
        const existingResponse = await sendPageToolCommand(tab.id, message);

        if (existingResponse?.ok) {
          return existingResponse;
        }
      } catch {
        // Startup state sync should not request fresh activeTab access.
      }

      if (hasRecentPageToolActivation(tab)) {
        await injectPageTools(tab.id);

        const injectedResponse = await sendPageToolCommand(tab.id, message);

        if (injectedResponse?.ok) {
          return injectedResponse;
        }

        throw new Error(
          injectedResponse?.message || "Page tools are not available here."
        );
      }

      return {
        ok: true,
        syncUnavailable: true,
        message: PAGE_TOOL_RECONNECT_MESSAGE,
      };
    }

    try {
      const existingResponse = await sendPageToolCommand(tab.id, message);

      if (existingResponse?.ok) {
        return existingResponse;
      }

      throw new Error(existingResponse?.message || "Page tools are not available here.");
    } catch (error) {
      if (!isMissingContentScriptError(error)) {
        throw error;
      }
    }

    try {
      await injectPageTools(tab.id);
    } catch (error) {
      const fallback = getPageToolUpdateFallback(message);

      if (fallback) {
        return fallback;
      }

      throw error;
    }

    const response = await sendPageToolCommand(tab.id, message);

    if (!response?.ok) {
      throw new Error(response?.message || "Page tools are not available here.");
    }

    return response;
  } catch (error) {
    throw new Error(normalisePageToolError(error, tab));
  }
}

async function showDictionaryPopover(tab, selectedText) {
  if (!tab?.id) {
    throw new Error("No active page found.");
  }

  if (isBrowserRestrictedPageUrl(tab.url)) {
    throw new Error(BROWSER_RESTRICTED_PAGE_MESSAGE);
  }

  if (isLikelyUploadableFileUrl(tab)) {
    throw new Error(FILE_PAGE_MESSAGE);
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
      throw new Error(response?.message || "Dictionary is not available here.");
    }
  } catch (error) {
    throw new Error(normalisePageToolError(error, tab));
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
    throw new Error("No active page found.");
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
          message: error.message || "Dictionary setting is unavailable.",
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
          message: error.message || "Dictionary setting did not update.",
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
          message: error.message || "Side panel did not open.",
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

chrome.tabs.onActivated.addListener((activeInfo) => {
  notifyPageToolStateMaybeChanged(activeInfo.tabId);
});

chrome.tabs.onUpdated.addListener((tabId, changeInfo) => {
  if (changeInfo.status === "loading" || changeInfo.status === "complete" || changeInfo.url) {
    notifyPageToolStateMaybeChanged(tabId);
  }
});

syncDictionaryContextMenuFromSession().catch((error) => {
  console.error("Clearead could not sync the dictionary context menu.", error);
});
