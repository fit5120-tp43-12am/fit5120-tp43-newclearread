import {
  CLEAREAD_WEBSITE_URL,
  MAX_TEXT_CHARS,
} from "../shared/config.js";
import { requestSummary } from "../services/backend-api.js";
import { explainLocalTerm, normaliseLookupTerm } from "../services/local-dictionary.js";

const sourceText = document.querySelector("#source-text");
const wordCount = document.querySelector("#word-count");
const charCount = document.querySelector("#char-count");
const validationMessage = document.querySelector("#validation-message");
const summaryButton = document.querySelector("#summary-text");
const clearButton = document.querySelector("#clear-text");
const statusRegion = document.querySelector("#status-region");
const resultPanel = document.querySelector(".result-panel");
const resultEmpty = document.querySelector("#result-empty");
const resultContent = document.querySelector("#result-content");
const fontModeButtons = Array.from(document.querySelectorAll("[data-font-mode]"));
const rulerModeButtons = Array.from(document.querySelectorAll("[data-ruler-mode]"));
const pageToolsStatus = document.querySelector("#page-tools-status");
const lensHint = document.querySelector("#lens-hint");
const dictionaryToggleButton = document.querySelector("#dictionary-toggle");
const dictionaryTermInput = document.querySelector("#dictionary-term");
const dictionaryExplainButton = document.querySelector("#dictionary-explain");
const dictionaryStatus = document.querySelector("#dictionary-status");
const dictionaryResult = document.querySelector("#dictionary-result");
const openWebsiteLink = document.querySelector("#open-clearead-website");
const SIDE_PANEL_FONT_CLASSES = [
  "font-mode-original",
  "font-mode-verdana",
  "font-mode-opendyslexic",
  "font-mode-calibri",
];
const PAGE_TOOL_STATE_MAYBE_CHANGED_TYPE = "clearead:page-tool-state-maybe-changed";
const PAGE_TOOL_STATE_SYNC_DEBOUNCE_MS = 180;
const PAGE_TOOL_STATE_WATCH_INTERVAL_MS = 2000;
const FONT_MODE_LABELS = Object.freeze({
  original: "Original",
  verdana: "Verdana",
  opendyslexic: "OpenDyslexic",
  calibri: "Calibri",
});
const RULER_MODE_LABELS = Object.freeze({
  none: "No ruler",
  highlight: "Highlight",
  lens: "Lens",
  line: "Line guide",
});

let isLoading = false;
let isPageToolLoading = false;
let isPageToolStateSyncing = false;
let isDictionaryToggleLoading = false;
let activeFontMode = "original";
let activeRulerMode = "none";
let isDictionaryEnabled = false;
let pageToolStateSyncTimer = null;
let pageToolStateWatchTimer = null;

function countWords(text) {
  const words = text.trim().match(/\S+/g);
  return words ? words.length : 0;
}

function formatNumber(value) {
  return new Intl.NumberFormat("en").format(value);
}

function hideStatus() {
  statusRegion.hidden = true;
  statusRegion.textContent = "";
  statusRegion.setAttribute("role", "status");
}

function setStatus(type, message) {
  statusRegion.hidden = false;
  statusRegion.className = `status-region status-${type}`;
  statusRegion.textContent = message;
  statusRegion.setAttribute("role", type === "error" ? "alert" : "status");
}

function setPageToolsStatus(type, message) {
  pageToolsStatus.className = `page-tools-status status-${type}`;
  pageToolsStatus.textContent = message;
  pageToolsStatus.setAttribute("role", type === "error" ? "alert" : "status");
}

function setDictionaryStatus(type, message) {
  dictionaryStatus.className = `dictionary-status status-${type}`;
  dictionaryStatus.textContent = message;
  dictionaryStatus.setAttribute("role", type === "error" ? "alert" : "status");
}

function describePageToolState(fontMode = activeFontMode, rulerMode = activeRulerMode) {
  const fontLabel = FONT_MODE_LABELS[fontMode] || FONT_MODE_LABELS.original;
  const rulerLabel = RULER_MODE_LABELS[rulerMode] || RULER_MODE_LABELS.none;

  return `Font: ${fontLabel}. Ruler: ${rulerLabel}.`;
}

function getPageToolStateStatusType() {
  return activeFontMode === "original" && activeRulerMode === "none" ? "neutral" : "success";
}

function setCurrentPageToolStatus() {
  setPageToolsStatus(getPageToolStateStatusType(), describePageToolState());
}

function keepPageToolNoticeIfNeeded(response) {
  if (!response?.noticeType) {
    return false;
  }

  setPageToolsStatus(response.noticeType, response.message || describePageToolState());
  return true;
}

function applyPageToolResponseState(response, fallback = {}) {
  applySidePanelFontMode(response.fontMode || fallback.fontMode || activeFontMode);
  activeRulerMode = response.rulerMode || fallback.rulerMode || activeRulerMode;
  updatePageToolButtonStates();
}

function updateLensHint() {
  lensHint.hidden = activeRulerMode !== "lens";
}

function setChoiceButtonState(buttons, dataKey, activeValue) {
  buttons.forEach((button) => {
    const isActive = button.dataset[dataKey] === activeValue;
    button.classList.toggle("tool-choice-button-active", isActive);
    button.setAttribute("aria-pressed", String(isActive));

    const check = button.querySelector(".selection-check");
    if (check) {
      check.hidden = !isActive;
    }
  });
}

function updatePageToolButtonStates() {
  setChoiceButtonState(fontModeButtons, "fontMode", activeFontMode);
  setChoiceButtonState(rulerModeButtons, "rulerMode", activeRulerMode);
  updateLensHint();
  updatePageToolStateWatcher();
}

function updateDictionaryButtonState(enabled) {
  isDictionaryEnabled = Boolean(enabled);
  dictionaryToggleButton.classList.toggle("tool-choice-button-active", isDictionaryEnabled);
  dictionaryToggleButton.setAttribute("aria-pressed", String(isDictionaryEnabled));

  const check = dictionaryToggleButton.querySelector(".selection-check");
  if (check) {
    check.hidden = !isDictionaryEnabled;
  }
}

function applySidePanelFontMode(fontMode) {
  activeFontMode = fontMode;
  document.body.classList.remove(...SIDE_PANEL_FONT_CLASSES);
  document.body.classList.add(`font-mode-${fontMode}`);
}

function setLoading(nextLoading) {
  isLoading = nextLoading;
  sourceText.disabled = nextLoading;
  clearButton.disabled = nextLoading;
  summaryButton.disabled = nextLoading || sourceText.value.length > MAX_TEXT_CHARS;
  summaryButton.textContent = nextLoading ? "Summarizing..." : "Summary";
}

function setPageToolLoading(nextLoading) {
  isPageToolLoading = nextLoading;
  fontModeButtons.forEach((button) => {
    button.disabled = nextLoading;
  });
  rulerModeButtons.forEach((button) => {
    button.disabled = nextLoading;
  });
}

function hasActivePageToolState() {
  return activeFontMode !== "original" || activeRulerMode !== "none";
}

function updatePageToolStateWatcher() {
  if (hasActivePageToolState()) {
    if (!pageToolStateWatchTimer) {
      pageToolStateWatchTimer = window.setInterval(() => {
        schedulePageToolStateSync();
      }, PAGE_TOOL_STATE_WATCH_INTERVAL_MS);
    }

    return;
  }

  if (pageToolStateWatchTimer) {
    window.clearInterval(pageToolStateWatchTimer);
    pageToolStateWatchTimer = null;
  }
}

function resetPageToolState(type, message) {
  applySidePanelFontMode("original");
  activeRulerMode = "none";
  updatePageToolButtonStates();
  setPageToolsStatus(type, message);
}

function schedulePageToolStateSync(delay = PAGE_TOOL_STATE_SYNC_DEBOUNCE_MS) {
  if (pageToolStateSyncTimer) {
    window.clearTimeout(pageToolStateSyncTimer);
  }

  pageToolStateSyncTimer = window.setTimeout(() => {
    pageToolStateSyncTimer = null;
    syncPageToolState();
  }, delay);
}

function setDictionaryToggleLoading(nextLoading) {
  isDictionaryToggleLoading = nextLoading;
  dictionaryToggleButton.disabled = nextLoading;
}

function updateCountsAndValidation() {
  const text = sourceText.value;
  const words = countWords(text);
  const chars = text.length;
  const overLimit = chars > MAX_TEXT_CHARS;

  wordCount.textContent = `${formatNumber(words)} ${words === 1 ? "word" : "words"}`;
  charCount.textContent = `${formatNumber(chars)} / ${formatNumber(MAX_TEXT_CHARS)} chars`;
  charCount.classList.toggle("count-error", overLimit);
  sourceText.classList.toggle("text-input-error", overLimit);

  if (overLimit) {
    validationMessage.textContent = `Too long by ${formatNumber(
      chars - MAX_TEXT_CHARS
    )} characters. Limit: 50,000.`;
    validationMessage.className = "validation-message validation-error";
  } else {
    validationMessage.textContent = "Up to 50,000 characters.";
    validationMessage.className = "validation-message";
  }

  if (!isLoading) {
    summaryButton.disabled = overLimit;
  }

  if (!isLoading && !text.trim() && statusRegion.textContent) {
    hideStatus();
  }
}

function clearElement(element) {
  while (element.firstChild) {
    element.removeChild(element.firstChild);
  }
}

function appendTextElement(parent, tagName, className, text) {
  const element = document.createElement(tagName);
  element.className = className;
  element.textContent = text;
  parent.appendChild(element);
  return element;
}

function getDictionaryPartTheme(type) {
  const normalizedType = String(type || "").toLowerCase();

  if (normalizedType.includes("prefix")) {
    return {
      background: "#fee2e2",
      color: "#9f1239",
    };
  }

  if (normalizedType.includes("root")) {
    return {
      background: "#dbeafe",
      color: "#1d4ed8",
    };
  }

  if (normalizedType.includes("suffix")) {
    return {
      background: "#dcfce7",
      color: "#15803d",
    };
  }

  return {
    background: "#e2e8f0",
    color: "#334155",
  };
}

function speakDictionaryTerm(term) {
  const speech = window.speechSynthesis;

  if (!speech || !term) {
    return;
  }

  speech.cancel();
  const utterance = new SpeechSynthesisUtterance(term);
  utterance.rate = 0.86;
  utterance.pitch = 1;
  speech.speak(utterance);
}

function appendDictionarySection(parent, heading, bodyText) {
  const section = document.createElement("section");
  section.className = "dictionary-card-section";
  appendTextElement(section, "h4", "dictionary-section-title", heading);

  if (bodyText) {
    appendTextElement(section, "p", "dictionary-section-body", bodyText);
  }

  parent.appendChild(section);
  return section;
}

function appendDictionaryWordParts(parent, wordParts) {
  const section = appendDictionarySection(parent, "Word parts");
  const table = document.createElement("div");
  table.className = "dictionary-parts-table";

  wordParts.forEach((wordPart) => {
    const theme = getDictionaryPartTheme(wordPart.type);
    const row = document.createElement("div");
    row.className = "dictionary-part-row";

    const partLabel = appendTextElement(row, "span", "dictionary-part", wordPart.part);
    partLabel.style.background = theme.background;

    appendTextElement(row, "span", "dictionary-part-meaning", wordPart.meaning);

    const typeBadge = appendTextElement(row, "span", "dictionary-part-type", wordPart.type);
    typeBadge.style.background = theme.background;
    typeBadge.style.color = theme.color;

    table.appendChild(row);
  });

  section.appendChild(table);
}

function renderDictionaryCard(explanation) {
  clearElement(dictionaryResult);

  const card = document.createElement("article");
  card.className = "dictionary-card";

  const header = document.createElement("div");
  header.className = "dictionary-card-header";
  appendTextElement(header, "h3", "dictionary-term", explanation.term || "Selected word");

  const speakButton = document.createElement("button");
  speakButton.type = "button";
  speakButton.className = "dictionary-speak-button";
  speakButton.setAttribute("aria-label", `Hear ${explanation.term || "selected word"}`);
  speakButton.textContent = "\uD83D\uDD0A";
  speakButton.addEventListener("click", () => {
    speakDictionaryTerm(explanation.term || "");
  });
  header.appendChild(speakButton);
  card.appendChild(header);

  appendDictionarySection(card, "Simple meaning", explanation.simpleMeaning || "demo demo demo");
  appendDictionaryWordParts(card, Array.isArray(explanation.wordParts) ? explanation.wordParts : []);

  const divider = document.createElement("div");
  divider.className = "dictionary-divider";
  card.appendChild(divider);

  appendDictionarySection(card, "Meaning from parts", explanation.meaningFromParts || "demo demo demo");

  dictionaryResult.appendChild(card);
  dictionaryResult.hidden = false;
}

function hideDictionaryResult() {
  clearElement(dictionaryResult);
  dictionaryResult.hidden = true;
}

function showEmptyResult(message = "Summary will appear here.") {
  clearElement(resultContent);
  resultPanel.hidden = false;
  resultContent.hidden = true;
  resultEmpty.hidden = false;
  resultEmpty.textContent = message;
}

function hideResult() {
  clearElement(resultContent);
  resultPanel.hidden = true;
  resultContent.hidden = true;
  resultEmpty.hidden = false;
  resultEmpty.textContent = "Summary will appear here.";
}

function renderSummaryResult(data) {
  clearElement(resultContent);
  resultPanel.hidden = false;

  const blocks = Array.isArray(data.blocks) ? data.blocks : [];

  if (blocks.length === 0) {
    appendTextElement(
      resultContent,
      "p",
      "empty-state",
      "No summary was returned."
    );
  }

  blocks.forEach((block) => {
    const card = document.createElement("article");
    card.className = "block-card";

    appendTextElement(card, "h3", "block-heading", "Summary");
    appendTextElement(
      card,
      "p",
      "summary-text",
      block.summary || "No summary was returned."
    );

    resultContent.appendChild(card);
  });

  resultEmpty.hidden = true;
  resultContent.hidden = false;
}

function validateTextForSummary() {
  const text = sourceText.value.trim();

  if (!text) {
    setStatus("error", "Paste text first.");
    validationMessage.textContent = "Paste text to summarize.";
    validationMessage.className = "validation-message validation-error";
    sourceText.focus();
    return null;
  }

  if (sourceText.value.length > MAX_TEXT_CHARS) {
    setStatus("error", "Text is over 50,000 characters.");
    sourceText.focus();
    return null;
  }

  return text;
}

async function summarizeText() {
  if (isLoading) {
    return;
  }

  const text = validateTextForSummary();
  if (!text) {
    hideResult();
    return;
  }

  setLoading(true);
  showEmptyResult("Summarizing...");
  setStatus("loading", "Summarizing...");

  try {
    const data = await requestSummary(text);
    renderSummaryResult(data);
    setStatus("success", "Summary ready.");
  } catch (error) {
    showEmptyResult("No summary yet.");
    setStatus("error", error.message || "Summary failed. Try again.");
  } finally {
    setLoading(false);
    updateCountsAndValidation();
  }
}

function clearText() {
  sourceText.value = "";
  updateCountsAndValidation();
  hideResult();
  hideStatus();
  sourceText.focus();
}

function sendRuntimeMessage(message) {
  return new Promise((resolve, reject) => {
    chrome.runtime.sendMessage(message, (response) => {
      const runtimeError = chrome.runtime.lastError;

      if (runtimeError) {
        reject(new Error(runtimeError.message));
        return;
      }

      resolve(response);
    });
  });
}

async function runPageTool(action, loadingMessage, payload = {}) {
  if (isPageToolLoading) {
    return null;
  }

  setPageToolLoading(true);
  setPageToolsStatus("loading", loadingMessage);

  try {
    const response = await sendRuntimeMessage({
      type: "clearead:page-tool",
      action,
      ...payload,
    });

    if (!response?.ok) {
      throw new Error(response?.message || "Tool is not available here.");
    }

    setPageToolsStatus(response.noticeType || "success", response.message || "Done.");
    return response;
  } catch (error) {
    setPageToolsStatus(
      "error",
      error.message ||
        "This page is not supported. Try a text page or click Clearead again."
    );
    return null;
  } finally {
    setPageToolLoading(false);
  }
}

async function setReadableFontMode(fontMode) {
  const response = await runPageTool(
    "set-readable-font",
    fontMode === "original" ? "Restoring font..." : "Applying font...",
    { fontMode }
  );

  if (response?.ok) {
    applyPageToolResponseState(response, { fontMode });
    if (!keepPageToolNoticeIfNeeded(response)) {
      setCurrentPageToolStatus();
    }
  }
}

async function setReadingRulerMode(rulerMode) {
  const response = await runPageTool(
    "set-reading-ruler",
    rulerMode === "none" ? "Turning ruler off..." : "Applying ruler...",
    { rulerMode }
  );

  if (response?.ok) {
    applyPageToolResponseState(response, { rulerMode });
    if (!keepPageToolNoticeIfNeeded(response)) {
      setCurrentPageToolStatus();
    }
  }
}

async function syncPageToolState() {
  if (isPageToolLoading || isPageToolStateSyncing) {
    return;
  }

  isPageToolStateSyncing = true;

  try {
    const response = await sendRuntimeMessage({
      type: "clearead:page-tool",
      action: "get-page-tool-state",
    });

    if (!response?.ok) {
      throw new Error(response?.message || "Page tools are not available here.");
    }

    if (response.syncUnavailable) {
      resetPageToolState(
        "neutral",
        response.message ||
          "In Chrome, click Extensions (puzzle icon) > Clearead > Open Clearead for this page."
      );
      return;
    }

    applySidePanelFontMode(response.fontMode || "original");
    activeRulerMode = response.rulerMode || "none";
    updatePageToolButtonStates();
    setPageToolsStatus(
      response.noticeType || getPageToolStateStatusType(),
      response.message || describePageToolState()
    );
  } catch (error) {
    resetPageToolState(
      "neutral",
      error.message ||
        "Ready. If needed, in Chrome click Extensions (puzzle icon) > Clearead > Open Clearead for this page."
    );
  } finally {
    isPageToolStateSyncing = false;
  }
}

async function loadDictionaryEnabledState() {
  setDictionaryToggleLoading(true);

  try {
    const response = await sendRuntimeMessage({
      type: "clearead:get-dictionary-enabled",
    });

    if (!response?.ok) {
      throw new Error(response?.message || "Dictionary setting is unavailable.");
    }

    updateDictionaryButtonState(response.enabled);
    setDictionaryStatus(
      response.enabled ? "success" : "neutral",
      response.enabled ? "On for selected text." : "Off for right-clicks."
    );
  } catch (error) {
    updateDictionaryButtonState(false);
    setDictionaryStatus(
      "error",
      error.message || "Dictionary setting is unavailable."
    );
  } finally {
    setDictionaryToggleLoading(false);
  }
}

async function updateDictionaryEnabledState() {
  if (isDictionaryToggleLoading) {
    return;
  }

  const previousEnabled = isDictionaryEnabled;
  const nextEnabled = !previousEnabled;
  setDictionaryToggleLoading(true);
  setDictionaryStatus(
    "loading",
    nextEnabled ? "Turning dictionary on..." : "Turning dictionary off..."
  );

  try {
    const response = await sendRuntimeMessage({
      type: "clearead:set-dictionary-enabled",
      enabled: nextEnabled,
    });

    if (!response?.ok) {
      throw new Error(response?.message || "Dictionary did not update.");
    }

    updateDictionaryButtonState(response.enabled);
    setDictionaryStatus(
      response.enabled ? "success" : "neutral",
      response.enabled ? "On for selected text." : "Off for right-clicks."
    );
  } catch (error) {
    updateDictionaryButtonState(previousEnabled);
    setDictionaryStatus(
      "error",
      error.message || "Dictionary did not update."
    );
  } finally {
    setDictionaryToggleLoading(false);
  }
}

function normalizeDictionaryTermInput() {
  const normalizedTerm = normaliseLookupTerm(dictionaryTermInput.value);

  if (dictionaryTermInput.value !== normalizedTerm) {
    dictionaryTermInput.value = normalizedTerm;
  }
}

function explainDictionaryTerm() {
  const term = normaliseLookupTerm(dictionaryTermInput.value);

  if (!term) {
    hideDictionaryResult();
    setDictionaryStatus("error", "Paste one word or short phrase first.");
    dictionaryTermInput.focus();
    return;
  }

  dictionaryTermInput.value = term;
  const explanation = explainLocalTerm(term);

  if (!explanation.ok) {
    hideDictionaryResult();
    setDictionaryStatus("error", explanation.message || "Could not explain this word.");
    return;
  }

  renderDictionaryCard(explanation);
  setDictionaryStatus(
    "success",
    explanation.source === "demo-placeholder"
      ? "Example explanation shown."
      : "Explanation shown."
  );
}

sourceText.addEventListener("input", updateCountsAndValidation);
summaryButton.addEventListener("click", summarizeText);
clearButton.addEventListener("click", clearText);
fontModeButtons.forEach((button) => {
  button.addEventListener("click", () => {
    setReadableFontMode(button.dataset.fontMode);
  });
});
rulerModeButtons.forEach((button) => {
  button.addEventListener("click", () => {
    setReadingRulerMode(button.dataset.rulerMode);
  });
});
dictionaryToggleButton.addEventListener("click", updateDictionaryEnabledState);
dictionaryTermInput.addEventListener("input", normalizeDictionaryTermInput);
dictionaryTermInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    explainDictionaryTerm();
  }
});
dictionaryExplainButton.addEventListener("click", explainDictionaryTerm);
openWebsiteLink.href = CLEAREAD_WEBSITE_URL;
chrome.runtime.onMessage.addListener((message) => {
  if (message?.type === PAGE_TOOL_STATE_MAYBE_CHANGED_TYPE) {
    schedulePageToolStateSync();
  }

  return false;
});
document.addEventListener("visibilitychange", () => {
  if (!document.hidden) {
    schedulePageToolStateSync();
  }
});
window.addEventListener("focus", () => {
  schedulePageToolStateSync();
});

updateCountsAndValidation();
hideResult();
hideStatus();
applySidePanelFontMode(activeFontMode);
updatePageToolButtonStates();
updateDictionaryButtonState(false);
hideDictionaryResult();
syncPageToolState();
loadDictionaryEnabledState();
