import { API_ENDPOINTS, BACKEND_API_BASE_URL } from "../shared/config.js";

export class BackendApiError extends Error {
  constructor(message, options = {}) {
    super(message);
    this.name = "BackendApiError";
    this.status = options.status || 0;
    this.detail = options.detail || "";
    this.cause = options.cause;
  }
}

async function readJsonResponse(response) {
  const bodyText = await response.text();

  if (!bodyText) {
    return {};
  }

  try {
    return JSON.parse(bodyText);
  } catch (error) {
    throw new BackendApiError("The Clearead backend returned an unreadable response.", {
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

export async function requestTextProcessing(text) {
  let response;

  try {
    response = await fetch(buildBackendUrl(API_ENDPOINTS.processText), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ text }),
    });
  } catch (error) {
    throw new BackendApiError(
      `The Clearead backend is unavailable at ${BACKEND_API_BASE_URL}. Check your connection and try again.`,
      { cause: error }
    );
  }

  const data = await readJsonResponse(response);

  if (!response.ok) {
    const detail = getErrorDetail(data);
    const message =
      response.status === 400
        ? `Backend validation error: ${detail || "The submitted text was not accepted."}`
        : detail || `The Clearead backend returned HTTP ${response.status}.`;

    throw new BackendApiError(message, {
      status: response.status,
      detail,
    });
  }

  return data;
}
