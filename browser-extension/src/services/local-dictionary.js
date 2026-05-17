const MAX_LOOKUP_TERM_CHARS = 50;
const SINGLE_LOOKUP_WORD_PATTERN = /^[a-z]+(?:['-][a-z]+)*$/i;

function collapseLookupWhitespace(term) {
  return String(term || "")
    .replace(/\s+/g, " ")
    .trim();
}

export function normaliseLookupTerm(term) {
  return collapseLookupWhitespace(term).slice(0, MAX_LOOKUP_TERM_CHARS);
}

function stripEdgePunctuation(term) {
  return term.replace(/^[^a-zA-Z]+|[^a-zA-Z]+$/g, "");
}

export function normaliseLookupWord(term) {
  return stripEdgePunctuation(normaliseLookupTerm(term)).toLowerCase();
}

export function validateLookupWord(term) {
  const word = stripEdgePunctuation(collapseLookupWhitespace(term)).toLowerCase();

  if (!word) {
    return {
      ok: false,
      word: "",
      message: "Paste one English word first.",
    };
  }

  if (word.length > MAX_LOOKUP_TERM_CHARS || !SINGLE_LOOKUP_WORD_PATTERN.test(word)) {
    return {
      ok: false,
      word,
      message: "Use one English word only, not a sentence.",
    };
  }

  return { ok: true, word };
}

export { MAX_LOOKUP_TERM_CHARS };
