import { API_ENDPOINTS, BACKEND_API_BASE_URL } from "../shared/config.js";

const SUMMARY_REQUEST_TIMEOUT_MS = 90000;
const DICTIONARY_REQUEST_TIMEOUT_MS = 30000;

export class BackendApiError extends Error {
  constructor(message, options = {}) {
    super(message);
    this.name = "BackendApiError";
    this.status = options.status || 0;
    this.detail = options.detail || "";
    this.cause = options.cause;
  }
}

async function readJsonResponse(response, contextLabel = "Response") {
  const bodyText = await response.text();

  if (!bodyText) {
    return {};
  }

  try {
    return JSON.parse(bodyText);
  } catch (error) {
    throw new BackendApiError(`${contextLabel} returned an unreadable response.`, {
      status: response.status,
      cause: error,
    });
  }
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

export async function requestSummary(text) {
  let response;
  const controller = new AbortController();
  const timeoutId = globalThis.setTimeout(() => {
    controller.abort();
  }, SUMMARY_REQUEST_TIMEOUT_MS);

  try {
    response = await fetch(buildBackendUrl(API_ENDPOINTS.pluginSummary), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ text }),
      signal: controller.signal,
    });
  } catch (error) {
    if (error?.name === "AbortError") {
      throw new BackendApiError(
        "Summary is taking too long. Try again or use the full Clearead website.",
        { cause: error }
      );
    }

    throw new BackendApiError(
      "Summary is unavailable. Check your connection and try again.",
      { cause: error }
    );
  } finally {
    globalThis.clearTimeout(timeoutId);
  }

  const data = await readJsonResponse(response, "Summary");

  if (!response.ok) {
    const detail = getErrorDetail(data);
    const message =
      response.status === 400
        ? detail || "This text was not accepted. Try shorter text."
        : detail || "Summary is unavailable. Try again later.";

    throw new BackendApiError(message, {
      status: response.status,
      detail,
    });
  }

  return data;
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

export async function requestDictionary(word) {
  let response;
  const controller = new AbortController();
  const timeoutId = globalThis.setTimeout(() => {
    controller.abort();
  }, DICTIONARY_REQUEST_TIMEOUT_MS);

  try {
    response = await fetch(buildBackendUrl(API_ENDPOINTS.dictionary), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ word }),
      signal: controller.signal,
    });
  } catch (error) {
    if (error?.name === "AbortError") {
      throw new BackendApiError(
        "Dictionary is taking too long. Try again or use the full Clearead website.",
        { cause: error }
      );
    }

    throw new BackendApiError(
      "Dictionary is unavailable. Check your connection and try again.",
      { cause: error }
    );
  } finally {
    globalThis.clearTimeout(timeoutId);
  }

  const data = await readJsonResponse(response, "Dictionary");

  if (!response.ok) {
    const detail = getErrorDetail(data);
    throw new BackendApiError(
      detail || "Dictionary is unavailable. Try again later.",
      {
        status: response.status,
        detail,
      }
    );
  }

  return normalizeDictionaryResponse(data, word);
}
