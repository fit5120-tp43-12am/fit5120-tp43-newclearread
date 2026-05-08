import {
  MAX_TEXT_CHARS,
  SIMPLIFY_UNAVAILABLE_MESSAGE,
} from "../shared/config.js";
import { requestSummary } from "../services/backend-api.js";

const sourceText = document.querySelector("#source-text");
const wordCount = document.querySelector("#word-count");
const charCount = document.querySelector("#char-count");
const validationMessage = document.querySelector("#validation-message");
const summaryButton = document.querySelector("#summary-text");
const simplifyButton = document.querySelector("#simplify-text");
const clearButton = document.querySelector("#clear-text");
const statusRegion = document.querySelector("#status-region");
const resultEmpty = document.querySelector("#result-empty");
const resultContent = document.querySelector("#result-content");

let isLoading = false;

function countWords(text) {
  const words = text.trim().match(/\S+/g);
  return words ? words.length : 0;
}

function formatNumber(value) {
  return new Intl.NumberFormat("en").format(value);
}

function setStatus(type, message) {
  statusRegion.className = `status-region status-${type}`;
  statusRegion.textContent = message;
  statusRegion.setAttribute("role", type === "error" ? "alert" : "status");
}

function setLoading(nextLoading) {
  isLoading = nextLoading;
  sourceText.disabled = nextLoading;
  clearButton.disabled = nextLoading;
  summaryButton.disabled = nextLoading || sourceText.value.length > MAX_TEXT_CHARS;
  summaryButton.textContent = nextLoading ? "Summarizing..." : "Summary";
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
    validationMessage.textContent = `This text is ${formatNumber(
      chars - MAX_TEXT_CHARS
    )} characters over the 50,000 character backend limit.`;
    validationMessage.className = "validation-message validation-error";
  } else {
    validationMessage.textContent =
      "Paste up to 50,000 characters. Nothing is sent while you type.";
    validationMessage.className = "validation-message";
  }

  if (!isLoading) {
    summaryButton.disabled = overLimit;
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

function showEmptyResult(message = "Summary results will appear here after the backend responds.") {
  clearElement(resultContent);
  resultContent.hidden = true;
  resultEmpty.hidden = false;
  resultEmpty.textContent = message;
}

function renderSummaryResult(data) {
  clearElement(resultContent);

  const meta = document.createElement("div");
  meta.className = "result-meta";

  if (data.notice) {
    appendTextElement(meta, "p", "notice", data.notice);
  }

  if (typeof data.usedFallback === "boolean") {
    appendTextElement(
      meta,
      "p",
      data.usedFallback ? "fallback fallback-active" : "fallback",
      data.usedFallback
        ? `Fallback used: yes${data.fallbackReason ? ` (${data.fallbackReason})` : ""}`
        : "Fallback used: no"
    );
  }

  if (meta.childElementCount > 0) {
    resultContent.appendChild(meta);
  }

  const blocks = Array.isArray(data.blocks) ? data.blocks : [];

  if (blocks.length === 0) {
    appendTextElement(
      resultContent,
      "p",
      "empty-state",
      "The backend responded, but did not return any summary blocks."
    );
  }

  blocks.forEach((block, index) => {
    const card = document.createElement("article");
    card.className = "block-card";

    const blockNumber = block.id ?? index + 1;
    appendTextElement(card, "p", "block-label", `Block ${blockNumber}`);
    appendTextElement(card, "h3", "block-heading", "Summary");
    appendTextElement(
      card,
      "p",
      "summary-text",
      block.summary || "No summary was returned for this block."
    );

    const keyPoints = Array.isArray(block.keyPoints) ? block.keyPoints.filter(Boolean) : [];
    const keyPointHeading = appendTextElement(card, "h4", "keypoints-heading", "Key points");
    keyPointHeading.setAttribute("aria-label", `Key points for block ${blockNumber}`);

    if (keyPoints.length > 0) {
      const list = document.createElement("ul");
      list.className = "keypoints-list";
      keyPoints.forEach((point) => {
        appendTextElement(list, "li", "", point);
      });
      card.appendChild(list);
    } else {
      appendTextElement(card, "p", "secondary-text", "No key points returned.");
    }

    if (block.originalText) {
      const details = document.createElement("details");
      details.className = "original-details";

      const summary = document.createElement("summary");
      summary.textContent = "Original text";
      details.appendChild(summary);

      appendTextElement(details, "p", "original-text", block.originalText);
      card.appendChild(details);
    }

    resultContent.appendChild(card);
  });

  resultEmpty.hidden = true;
  resultContent.hidden = false;
}

function validateTextForSummary() {
  const text = sourceText.value.trim();

  if (!text) {
    setStatus("error", "Paste text before requesting a summary.");
    validationMessage.textContent = "Text is required before Clearead can summarize it.";
    validationMessage.className = "validation-message validation-error";
    sourceText.focus();
    return null;
  }

  if (sourceText.value.length > MAX_TEXT_CHARS) {
    setStatus("error", "The pasted text is over the 50,000 character backend limit.");
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
    showEmptyResult();
    return;
  }

  setLoading(true);
  showEmptyResult("Waiting for the Clearead backend response...");
  setStatus("loading", "Sending pasted text to the Clearead backend for summary...");

  try {
    const data = await requestSummary(text);
    renderSummaryResult(data);
    setStatus("success", "Summary complete.");
  } catch (error) {
    showEmptyResult("No summary is available yet.");
    setStatus("error", error.message || "Clearead could not summarize this text.");
  } finally {
    setLoading(false);
    updateCountsAndValidation();
  }
}

function clearText() {
  sourceText.value = "";
  updateCountsAndValidation();
  showEmptyResult();
  setStatus("neutral", "Ready for pasted text.");
  sourceText.focus();
}

sourceText.addEventListener("input", updateCountsAndValidation);
summaryButton.addEventListener("click", summarizeText);
simplifyButton.addEventListener("click", () => {
  setStatus("neutral", SIMPLIFY_UNAVAILABLE_MESSAGE);
});
clearButton.addEventListener("click", clearText);

updateCountsAndValidation();
showEmptyResult();
