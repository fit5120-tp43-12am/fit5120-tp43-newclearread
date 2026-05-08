const MAX_LOOKUP_TERM_CHARS = 80;
const LOCAL_GUIDANCE_NOTE =
  "Local guidance only. This is not a full dictionary service.";
const FALLBACK_MEANING =
  "This looks like a word or phrase that may need context. Try reading the sentence around it and replacing it with a simpler phrase.";

const GLOSSARY = new Map([
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

export function normaliseLookupTerm(term) {
  return String(term || "")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, MAX_LOOKUP_TERM_CHARS);
}

export function explainLocalTerm(term) {
  const normalizedTerm = normaliseLookupTerm(term);
  const glossaryEntry = GLOSSARY.get(normalizedTerm.toLowerCase());

  if (!normalizedTerm) {
    return {
      ok: false,
      term: "",
      message: "Select one word or a short phrase on the page, then try again.",
      note: LOCAL_GUIDANCE_NOTE,
    };
  }

  return {
    ok: true,
    term: normalizedTerm,
    meaning: glossaryEntry?.meaning || FALLBACK_MEANING,
    parts: glossaryEntry?.parts || [],
    matchedLocalGlossary: Boolean(glossaryEntry),
    note: LOCAL_GUIDANCE_NOTE,
  };
}

export { MAX_LOOKUP_TERM_CHARS };
