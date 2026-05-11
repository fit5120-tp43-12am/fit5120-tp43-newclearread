const MAX_LOOKUP_TERM_CHARS = 50;
const BACKEND_API_BASE_URL =
  "https://clear-read-a3c2gyajcjf5agfd.australiaeast-01.azurewebsites.net";
const DICTIONARY_ENDPOINT = "/api/dictionary";
const DICTIONARY_REQUEST_TIMEOUT_MS = 30000;
const SINGLE_LOOKUP_WORD_PATTERN = /^[a-z]+(?:['-][a-z]+)*$/i;

function normaliseLookupTerm(term) {
  return String(term || "")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, MAX_LOOKUP_TERM_CHARS);
}

function stripEdgePunctuation(term) {
  return term.replace(/^[^a-zA-Z]+|[^a-zA-Z]+$/g, "");
}

function normaliseLookupWord(term) {
  return stripEdgePunctuation(normaliseLookupTerm(term)).toLowerCase();
}

function validateLookupWord(term) {
  const word = normaliseLookupWord(term);

  if (!word) {
    return {
      ok: false,
      word: "",
      message: "Select one English word first.",
    };
  }

  if (word.length > MAX_LOOKUP_TERM_CHARS || !SINGLE_LOOKUP_WORD_PATTERN.test(word)) {
    return {
      ok: false,
      word,
      message: "Select one English word only, not a sentence.",
    };
  }

  return { ok: true, word };
}

function buildBackendUrl(path) {
  return `${BACKEND_API_BASE_URL.replace(/\/$/, "")}${path}`;
}

function getErrorDetail(data) {
  if (!data) {
    return "";
  }

  if (typeof data.detail === "string") {
    return data.detail;
  }

  if (Array.isArray(data.detail)) {
    return data.detail
      .map((item) => item?.msg || item?.message || JSON.stringify(item))
      .filter(Boolean)
      .join(" ");
  }

  return "";
}

async function readJsonResponse(response) {
  const bodyText = await response.text();

  if (!bodyText) {
    return {};
  }

  try {
    return JSON.parse(bodyText);
  } catch (error) {
    throw new Error("Dictionary returned an unreadable response.", {
      cause: error,
    });
  }
}

function normalizeDictionaryPart(part) {
  return {
    part: String(part?.form || part?.part || "").trim(),
    meaning: String(part?.meaning || "").trim(),
    type: String(part?.type || "Part").trim() || "Part",
  };
}

function normalizeDictionaryResponse(data, fallbackWord) {
  const word = String(data?.word || fallbackWord || "").trim();
  const wordParts = Array.isArray(data?.wordParts)
    ? data.wordParts
        .map(normalizeDictionaryPart)
        .filter((part) => part.part || part.meaning)
    : [];
  const simpleMeaning = String(data?.simpleMeaning || "").trim();
  const meaningFromParts = String(data?.meaningFromParts || "").trim();
  const processingStats =
    data?.processingStats && typeof data.processingStats === "object"
      ? data.processingStats
      : null;
  const backendSource = String(processingStats?.source || "").toLowerCase();
  const isNonResultFallback = backendSource === "fallback" || backendSource === "invalid_input";
  const hasResult =
    Boolean(simpleMeaning || wordParts.length > 0 || meaningFromParts) &&
    !isNonResultFallback;

  return {
    ok: true,
    term: word,
    simpleMeaning,
    wordParts,
    meaningFromParts,
    hasResult,
    noResultMessage:
      isNonResultFallback && simpleMeaning
        ? simpleMeaning
        : "No dictionary result was returned for this word. Try another word or use the full Clearead website.",
    processingStats,
    source: "backend-dictionary",
  };
}

function createDictionaryErrorExplanation(term, message) {
  return {
    ok: false,
    term: term || "Selected word",
    message,
  };
}

function createDictionaryLoadingExplanation(term) {
  return {
    ok: false,
    loading: true,
    term,
    message: "Looking up...",
  };
}

async function requestDictionary(word) {
  let response;
  const controller = new AbortController();
  const timeoutId = globalThis.setTimeout(() => {
    controller.abort();
  }, DICTIONARY_REQUEST_TIMEOUT_MS);

  try {
    response = await fetch(buildBackendUrl(DICTIONARY_ENDPOINT), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ word }),
      signal: controller.signal,
    });
  } catch (error) {
    if (error?.name === "AbortError") {
      throw new Error(
        "Dictionary is taking too long. Try again or use the full Clearead website."
      );
    }

    throw new Error(
      "Dictionary is unavailable. Check your connection and try again."
    );
  } finally {
    globalThis.clearTimeout(timeoutId);
  }

  const data = await readJsonResponse(response);

  if (!response.ok) {
    const detail = getErrorDetail(data);
    throw new Error(detail || "Dictionary is unavailable. Try again later.");
  }

  return normalizeDictionaryResponse(data, word);
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
const DICTIONARY_NOTICE_TYPE = "clearead:dictionary-notice";
const PAGE_TOOL_STATE_MAYBE_CHANGED_TYPE = "clearead:page-tool-state-maybe-changed";
const PAGE_TOOL_SCRIPT = "src/content/page-tools.js";
const DICTIONARY_CONTEXT_MENU_ID = "clearead-explain-selection";
const DICTIONARY_ENABLED_STORAGE_KEY = "cleareadDictionaryEnabled";
const DICTIONARY_NOTICE_STORAGE_KEY = "cleareadDictionaryNotice";
const PAGE_TOOL_ACTIVATION_STORAGE_KEY = "cleareadPageToolActivation";
const NORMAL_PAGE_URL_PATTERNS = ["http://*/*", "https://*/*"];
const BROWSER_RESTRICTED_PAGE_MESSAGE =
  "Chrome blocks tools on this page. Try another webpage.";
const FILE_PAGE_MESSAGE =
  "File pages may not support page tools. Click Open website to upload the file.";
const ACTIVE_TAB_ACCESS_MESSAGE =
  "Need page access. In Chrome, click Extensions (puzzle icon) > Clearead > Open Clearead for this page.";
const GENERIC_PAGE_TOOL_MESSAGE =
  "Clearead tools are unavailable on this page. Try a text page or click Clearead again.";
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

function isValidPageToolActivationRecord(record) {
  return Boolean(
    record &&
      Number.isInteger(record.tabId) &&
      Number.isFinite(record.activatedAt)
  );
}

function createPageToolActivationRecord(message) {
  if (!Number.isInteger(message?.tabId)) {
    return null;
  }

  return {
    tabId: message.tabId,
    windowId: Number.isInteger(message.windowId) ? message.windowId : null,
    activatedAt: Date.now(),
  };
}

async function writePageToolActivation(record) {
  lastPageToolActivation = record;
  await chrome.storage.session.set({
    [PAGE_TOOL_ACTIVATION_STORAGE_KEY]: record,
  });
}

async function readPageToolActivation() {
  try {
    const storedValues = await chrome.storage.session.get(
      PAGE_TOOL_ACTIVATION_STORAGE_KEY
    );
    const storedRecord = storedValues[PAGE_TOOL_ACTIVATION_STORAGE_KEY];

    if (isValidPageToolActivationRecord(storedRecord)) {
      lastPageToolActivation = storedRecord;
      return storedRecord;
    }
  } catch {
    // The in-memory copy is enough for the current service worker lifetime.
  }

  return lastPageToolActivation;
}

async function markPageToolActivation(message) {
  const activationRecord = createPageToolActivationRecord(message);

  if (!activationRecord) {
    return {
      ok: false,
      message: "No active page found.",
    };
  }

  try {
    await writePageToolActivation(activationRecord);
  } catch {
    lastPageToolActivation = activationRecord;
  }

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

function isRecentPageToolActivationForTab(tab, activationRecord) {
  if (!tab?.id || activationRecord.tabId !== tab.id) {
    return false;
  }

  if (
    Number.isInteger(activationRecord.windowId) &&
    Number.isInteger(tab.windowId) &&
    activationRecord.windowId !== tab.windowId
  ) {
    return false;
  }

  return Date.now() - activationRecord.activatedAt <= RECENT_PAGE_ACTIVATION_MS;
}

async function hasRecentPageToolActivation(tab) {
  const activationRecord = await readPageToolActivation();
  return isRecentPageToolActivationForTab(tab, activationRecord);
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

function notifyDictionaryNotice(notice) {
  chrome.runtime.sendMessage(
    {
      type: DICTIONARY_NOTICE_TYPE,
      notice,
    },
    () => {
      chrome.runtime.lastError;
    }
  );
}

function ignoreChromeActionResult(possiblePromise) {
  possiblePromise?.catch?.(() => {});
}

function showDictionaryFailureBadge() {
  ignoreChromeActionResult(chrome.action.setBadgeBackgroundColor({ color: "#dc2626" }));
  ignoreChromeActionResult(chrome.action.setBadgeText({ text: "!" }));
  ignoreChromeActionResult(chrome.action.setTitle({ title: "Clearead dictionary needs attention" }));

  globalThis.setTimeout(() => {
    ignoreChromeActionResult(chrome.action.setBadgeText({ text: "" }));
    ignoreChromeActionResult(chrome.action.setTitle({ title: "Open Clearead" }));
  }, 6000);
}

async function writeDictionaryNotice(type, message) {
  const notice = {
    type: type || "error",
    message,
    createdAt: Date.now(),
  };

  await chrome.storage.session.set({
    [DICTIONARY_NOTICE_STORAGE_KEY]: notice,
  });
  notifyDictionaryNotice(notice);

  if (notice.type === "error") {
    showDictionaryFailureBadge();
  }
}

async function readAndClearDictionaryNotice() {
  const storedValues = await chrome.storage.session.get(DICTIONARY_NOTICE_STORAGE_KEY);
  const notice = storedValues[DICTIONARY_NOTICE_STORAGE_KEY];
  await chrome.storage.session.remove(DICTIONARY_NOTICE_STORAGE_KEY);

  if (!notice?.message) {
    return null;
  }

  return {
    type: notice.type || "error",
    message: notice.message,
  };
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
    (normalizedMessage.includes("receiving end") &&
      normalizedMessage.includes("exist")) ||
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

      if (await hasRecentPageToolActivation(tab)) {
        await injectPageTools(tab.id);

        const injectedResponse = await sendPageToolCommand(tab.id, message);

        if (injectedResponse?.ok) {
          return injectedResponse;
        }

        throw new Error(
          injectedResponse?.message || "Page tools are unavailable here."
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

      throw new Error(existingResponse?.message || "Page tools are unavailable here.");
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
      throw new Error(response?.message || "Page tools are unavailable here.");
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

  const validation = validateLookupWord(selectedText);
  const term = validation.word || normaliseLookupTerm(selectedText) || "Selected word";

  try {
    await injectPageTools(tab.id);

    if (!validation.ok) {
      await chrome.tabs.sendMessage(tab.id, {
        type: PAGE_TOOL_COMMAND_TYPE,
        action: "show-dictionary-popover",
        explanation: createDictionaryErrorExplanation(term, validation.message),
      });
      return;
    }

    await chrome.tabs.sendMessage(tab.id, {
      type: PAGE_TOOL_COMMAND_TYPE,
      action: "show-dictionary-popover",
      explanation: createDictionaryLoadingExplanation(term),
    });

    let explanation;
    try {
      explanation = await requestDictionary(validation.word);
    } catch (error) {
      explanation = createDictionaryErrorExplanation(
        term,
        error.message || "Dictionary is unavailable. Try again."
      );
    }

    const response = await chrome.tabs.sendMessage(tab.id, {
      type: PAGE_TOOL_COMMAND_TYPE,
      action: "show-dictionary-popover",
      explanation,
    });

    if (!response?.ok) {
      throw new Error(response?.message || "Dictionary is unavailable here.");
    }
  } catch (error) {
    throw new Error(normalisePageToolError(error, tab));
  }
}

async function handleOpenSidePanelRequest(message) {
  const activationResponse = await markPageToolActivation(message);

  if (!activationResponse.ok) {
    throw new Error(activationResponse.message);
  }

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
    markPageToolActivation(message)
      .then((response) => sendResponse(response))
      .catch((error) => {
        sendResponse({
          ok: false,
          message: error.message || "No active page found.",
        });
      });

    return true;
  }

  if (message?.type === GET_DICTIONARY_ENABLED_REQUEST_TYPE) {
    syncDictionaryContextMenuFromSession()
      .then(async (enabled) => {
        const notice = await readAndClearDictionaryNotice();
        sendResponse({
          ok: true,
          enabled,
          ...(notice ? { notice } : {}),
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

function getDictionaryContextMenuFailureMessage(error) {
  const message = String(error?.message || "").trim();

  if (message && message !== GENERIC_PAGE_TOOL_MESSAGE) {
    return message;
  }

  return "Dictionary did not work on this page. Try one English word on a normal webpage, or use the Word box in Clearead.";
}

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
    writeDictionaryNotice(
      "error",
      getDictionaryContextMenuFailureMessage(error)
    ).catch(() => {});
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
