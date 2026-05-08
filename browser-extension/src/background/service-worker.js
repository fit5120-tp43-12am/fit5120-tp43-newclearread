const MAX_LOOKUP_TERM_CHARS = 80;
const LOCAL_DICTIONARY_GUIDANCE_NOTE =
  "Local guidance only. This is not a full dictionary service.";
const LOCAL_DICTIONARY_FALLBACK_MEANING =
  "This looks like a word or phrase that may need context. Try reading the sentence around it and replacing it with a simpler phrase.";
const LOCAL_DICTIONARY_GLOSSARY = new Map([
  [
    "dyslexia",
    {
      meaning:
        "A learning difference that can make reading, spelling, and word recognition harder.",
      parts: ["dys-: difficult", "lexia: words or reading"],
    },
  ],
  [
    "accessibility",
    {
      meaning:
        "The practice of designing information, tools, and spaces so more people can use them.",
      parts: ["access: ability to use or enter", "-ibility: condition or quality"],
    },
  ],
  [
    "cognition",
    {
      meaning:
        "The mental process of learning, understanding, remembering, and using information.",
      parts: ["cognit: know or learn", "-ion: action or process"],
    },
  ],
  [
    "cognitive",
    {
      meaning: "Related to thinking, learning, memory, attention, or understanding.",
      parts: ["cognit: know or learn", "-ive: related to"],
    },
  ],
  [
    "comprehension",
    {
      meaning: "Understanding the meaning of what you read, hear, or see.",
      parts: ["com-: together", "prehend: grasp", "-ion: action or process"],
    },
  ],
  [
    "intervention",
    {
      meaning:
        "A planned action used to help improve a situation or support a person's needs.",
      parts: ["inter-: between", "vene: come", "-tion: action or process"],
    },
  ],
  [
    "significant",
    {
      meaning: "Important enough to notice, measure, or affect the result.",
      parts: ["sign: mark or meaning", "-ficant: making or causing"],
    },
  ],
  [
    "methodology",
    {
      meaning:
        "The planned methods and rules used to study a question or complete research.",
      parts: ["method: planned way", "-ology: study of"],
    },
  ],
  [
    "misinterpretation",
    {
      meaning: "An incorrect understanding of a word, message, result, or situation.",
      parts: ["mis-: wrong", "interpret: explain meaning", "-ation: action or result"],
    },
  ],
]);

function normaliseLookupTerm(term) {
  return String(term || "")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, MAX_LOOKUP_TERM_CHARS);
}

function explainLocalTerm(term) {
  const normalizedTerm = normaliseLookupTerm(term);
  const glossaryEntry = LOCAL_DICTIONARY_GLOSSARY.get(normalizedTerm.toLowerCase());

  if (!normalizedTerm) {
    return {
      ok: false,
      term: "",
      message: "Select one word or a short phrase on the page, then try again.",
      note: LOCAL_DICTIONARY_GUIDANCE_NOTE,
    };
  }

  return {
    ok: true,
    term: normalizedTerm,
    meaning: glossaryEntry?.meaning || LOCAL_DICTIONARY_FALLBACK_MEANING,
    parts: glossaryEntry?.parts || [],
    matchedLocalGlossary: Boolean(glossaryEntry),
    note: LOCAL_DICTIONARY_GUIDANCE_NOTE,
  };
}

chrome.sidePanel
  .setPanelBehavior({ openPanelOnActionClick: false })
  .catch((error) => {
    console.error("Clearead could not configure action-click side panel behavior.", error);
  });

const PAGE_TOOL_REQUEST_TYPE = "clearead:page-tool";
const PAGE_TOOL_COMMAND_TYPE = "clearead:page-tool-command-v6";
const OPEN_SIDE_PANEL_REQUEST_TYPE = "clearead:open-side-panel";
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
const PAGE_TOOL_ACTIONS = new Set([
  "get-page-tool-state",
  "set-readable-font",
  "set-reading-ruler",
  "apply-readable-font",
  "reset-readable-font",
  "toggle-reading-ruler",
]);

let isDictionaryEnabled = false;

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
        // The page may not have the packaged script yet. Fall through to inject it.
      }
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
