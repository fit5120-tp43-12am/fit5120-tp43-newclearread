const sourceText = document.querySelector("#source-text");
const textCount = document.querySelector("#text-count");
const previewButton = document.querySelector("#preview-text");
const clearButton = document.querySelector("#clear-text");
const resultMessage = document.querySelector("#result-message");

function countWords(text) {
  const words = text.trim().match(/\S+/g);
  return words ? words.length : 0;
}

function updateCount() {
  const words = countWords(sourceText.value);
  textCount.textContent = `${words} ${words === 1 ? "word" : "words"}`;
}

function showPreviewPlaceholder() {
  const words = countWords(sourceText.value);

  if (words === 0) {
    resultMessage.textContent =
      "Paste text above to see the local placeholder state for future reading tools.";
    return;
  }

  resultMessage.textContent =
    `Local preview ready for ${words} ${words === 1 ? "word" : "words"}. Future versions will add simplify, summary, dictionary, and reading support tools here.`;
}

function clearText() {
  sourceText.value = "";
  updateCount();
  showPreviewPlaceholder();
  sourceText.focus();
}

sourceText.addEventListener("input", updateCount);
previewButton.addEventListener("click", showPreviewPlaceholder);
clearButton.addEventListener("click", clearText);

updateCount();
