import {
  CLEAREAD_WEBSITE_URL,
  MAX_TEXT_CHARS,
} from "../shared/config.js";
import { requestDictionary, requestSummary } from "../services/backend-api.js";
import { normaliseLookupTerm, validateLookupWord } from "../services/local-dictionary.js";

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
const DICTIONARY_NOTICE_TYPE = "clearead:dictionary-notice";
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
let isDictionaryLookupLoading = false;
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

function setDictionaryLookupLoading(nextLoading) {
  isDictionaryLookupLoading = nextLoading;
  dictionaryTermInput.disabled = nextLoading;
  dictionaryExplainButton.disabled = nextLoading;
  dictionaryExplainButton.textContent = nextLoading ? "Looking up..." : "Explain";
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

function appendSvgNode(parent, tagName, attributes) {
  const node = document.createElementNS("http://www.w3.org/2000/svg", tagName);

  Object.entries(attributes).forEach(([name, value]) => {
    node.setAttribute(name, value);
  });

  parent.appendChild(node);
  return node;
}

function appendDictionarySpeakerIcon(parent) {
  const svg = appendSvgNode(parent, "svg", {
    width: "15",
    height: "15",
    viewBox: "0 0 15 15",
    fill: "none",
    "aria-hidden": "true",
  });
  appendSvgNode(svg, "path", {
    d: "M2 5H4.5L7.5 2.5v10L4.5 10H2V5z",
    fill: "currentColor",
  });
  appendSvgNode(svg, "path", {
    d: "M10 4a5 5 0 0 1 0 7",
    stroke: "currentColor",
    "stroke-width": "1.4",
    "stroke-linecap": "round",
  });
  appendSvgNode(svg, "path", {
    d: "M11.5 6a2.5 2.5 0 0 1 0 3",
    stroke: "currentColor",
    "stroke-width": "1.4",
    "stroke-linecap": "round",
  });
}

function getDictionaryPartClass(type) {
  const normalizedType = String(type || "").toLowerCase();

  if (normalizedType.includes("prefix")) {
    return "prefix";
  }

  if (normalizedType.includes("root")) {
    return "root";
  }

  if (normalizedType.includes("suffix")) {
    return "suffix";
  }

  if (normalizedType.includes("infix")) {
    return "infix";
  }

  if (
    normalizedType.includes("base-word") ||
    (normalizedType.includes("base") && normalizedType.includes("word"))
  ) {
    return "base-word";
  }

  if (
    normalizedType.includes("combining-form") ||
    (normalizedType.includes("combining") && normalizedType.includes("form"))
  ) {
    return "combining-form";
  }

  return "";
}

function formatDictionaryPartType(type) {
  return String(type || "part")
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .map((word) => `${word.charAt(0).toUpperCase()}${word.slice(1)}`)
    .join(" ") || "Part";
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
    const typeClass = getDictionaryPartClass(wordPart.type);
    const row = document.createElement("div");
    row.className = typeClass
      ? `dictionary-part-row dictionary-part-row--${typeClass}`
      : "dictionary-part-row";

    appendTextElement(row, "span", "dictionary-part", wordPart.part);
    appendTextElement(
      row,
      "span",
      "dictionary-part-meaning",
      wordPart.meaning || "No meaning returned."
    );

    const typeBadge = appendTextElement(
      row,
      "span",
      typeClass ? `dictionary-part-type dictionary-part-type--${typeClass}` : "dictionary-part-type",
      formatDictionaryPartType(wordPart.type)
    );
    typeBadge.setAttribute("aria-label", `Word part type: ${formatDictionaryPartType(wordPart.type)}`);

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
  appendDictionarySpeakerIcon(speakButton);
  speakButton.addEventListener("click", () => {
    speakDictionaryTerm(explanation.term || "");
  });
  header.appendChild(speakButton);
  card.appendChild(header);

  if (explanation.hasResult === false) {
    appendDictionarySection(
      card,
      "Result",
      explanation.noResultMessage ||
        "No dictionary result was returned for this word. Try another word or use the full Clearead website."
    );
    dictionaryResult.appendChild(card);
    dictionaryResult.hidden = false;
    return;
  }

  appendDictionarySection(
    card,
    "Simple meaning",
    explanation.simpleMeaning || "No simple meaning was returned."
  );

  const wordParts = Array.isArray(explanation.wordParts) ? explanation.wordParts : [];

  if (wordParts.length > 0) {
    appendDictionaryWordParts(card, wordParts);
  } else {
    appendDictionarySection(card, "Word parts", "No word parts were returned.");
  }

  appendDictionarySection(
    card,
    "Meaning from parts",
    explanation.meaningFromParts || "No word-part explanation was returned."
  );

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

function getOverallSummaryText(data) {
  const overallSummary = data?.overallSummary;

  if (overallSummary && typeof overallSummary === "object") {
    const text = String(overallSummary.text || "").trim();

    if (text) {
      return text;
    }
  }

  const blocks = Array.isArray(data?.blocks) ? data.blocks : [];
  const fallbackBlock = blocks.find((block) => String(block?.summary || "").trim());

  if (fallbackBlock) {
    return String(fallbackBlock.summary || "").trim();
  }

  return "";
}

function renderSummaryResult(data) {
  clearElement(resultContent);
  resultPanel.hidden = false;

  const summaryText = getOverallSummaryText(data);

  if (!summaryText) {
    appendTextElement(
      resultContent,
      "p",
      "empty-state",
      "No summary was returned."
    );
  } else {
    const card = document.createElement("article");
    card.className = "block-card overall-summary-card";

    appendTextElement(card, "p", "summary-text", summaryText);
    resultContent.appendChild(card);
  }

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
      throw new Error(response?.message || "Tool is unavailable here.");
    }

    setPageToolsStatus(response.noticeType || "success", response.message || "Done.");
    return response;
  } catch (error) {
    setPageToolsStatus(
      "error",
      error.message ||
        "Clearead tools are unavailable on this page. Try a text page or click Clearead again."
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
      throw new Error(response?.message || "Page tools are unavailable here.");
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

    if (response.notice?.message) {
      setDictionaryStatus(response.notice.type || "error", response.notice.message);
    } else {
      setDictionaryStatus(
        response.enabled ? "success" : "neutral",
        response.enabled ? "On for selected words." : "Off for right-clicks."
      );
    }
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
      response.enabled ? "On for selected words." : "Off for right-clicks."
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

async function explainDictionaryTerm() {
  if (isDictionaryLookupLoading) {
    return;
  }

  const validation = validateLookupWord(dictionaryTermInput.value);

  if (!validation.ok) {
    hideDictionaryResult();
    setDictionaryStatus("error", validation.message || "Paste one English word first.");
    dictionaryTermInput.focus();
    return;
  }

  dictionaryTermInput.value = validation.word;
  setDictionaryLookupLoading(true);
  hideDictionaryResult();
  setDictionaryStatus("loading", "Looking up...");

  try {
    const explanation = await requestDictionary(validation.word);
    renderDictionaryCard(explanation);
    setDictionaryStatus(
      explanation.hasResult === false ? "neutral" : "success",
      explanation.hasResult === false ? "No dictionary result found." : "Explanation shown."
    );
  } catch (error) {
    hideDictionaryResult();
    setDictionaryStatus("error", error.message || "Dictionary is unavailable. Try again.");
  } finally {
    setDictionaryLookupLoading(false);
  }
}

function isComposingText(event) {
  return event.isComposing || event.keyCode === 229;
}

function insertSourceTextLineBreak() {
  const selectionStart = sourceText.selectionStart ?? sourceText.value.length;
  const selectionEnd = sourceText.selectionEnd ?? selectionStart;
  const selectedLength = Math.max(selectionEnd - selectionStart, 0);
  const nextLength = sourceText.value.length - selectedLength + 1;

  if (nextLength > MAX_TEXT_CHARS) {
    updateCountsAndValidation();
    return;
  }

  if (typeof sourceText.setRangeText === "function") {
    sourceText.setRangeText("\n", selectionStart, selectionEnd, "end");
  } else {
    sourceText.value = `${sourceText.value.slice(0, selectionStart)}\n${sourceText.value.slice(selectionEnd)}`;
    sourceText.selectionStart = selectionStart + 1;
    sourceText.selectionEnd = selectionStart + 1;
  }

  sourceText.dispatchEvent(new Event("input", { bubbles: true }));
}

function handleSummaryTextKeydown(event) {
  if (event.key !== "Enter" || isComposingText(event)) {
    return;
  }

  if (event.ctrlKey || event.shiftKey || event.altKey || event.metaKey) {
    event.preventDefault();
    insertSourceTextLineBreak();
    return;
  }

  event.preventDefault();
  summarizeText();
}

function handleDictionaryTermKeydown(event) {
  if (event.key !== "Enter" || isComposingText(event)) {
    return;
  }

  event.preventDefault();
  explainDictionaryTerm();
}

sourceText.addEventListener("input", updateCountsAndValidation);
sourceText.addEventListener("keydown", handleSummaryTextKeydown);
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
dictionaryTermInput.addEventListener("keydown", handleDictionaryTermKeydown);
dictionaryExplainButton.addEventListener("click", explainDictionaryTerm);
openWebsiteLink.href = CLEAREAD_WEBSITE_URL;
chrome.runtime.onMessage.addListener((message) => {
  if (message?.type === PAGE_TOOL_STATE_MAYBE_CHANGED_TYPE) {
    schedulePageToolStateSync();
  }

  if (message?.type === DICTIONARY_NOTICE_TYPE && message.notice?.message) {
    setDictionaryStatus(message.notice.type || "error", message.notice.message);
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
