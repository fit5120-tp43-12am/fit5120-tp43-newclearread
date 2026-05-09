const MAX_LOOKUP_TERM_CHARS = 80;
const DICTIONARY_DEMO_TEXT = "demo demo demo";

export function normaliseLookupTerm(term) {
  return String(term || "")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, MAX_LOOKUP_TERM_CHARS);
}

export function createDemoWordParts() {
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

export function explainLocalTerm(term) {
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

export { MAX_LOOKUP_TERM_CHARS };
