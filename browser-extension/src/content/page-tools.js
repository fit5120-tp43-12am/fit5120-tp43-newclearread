(() => {
  const NAMESPACE = "CleareadPageTools";
  const VERSION = "0.7.0";
  const MESSAGE_TYPE = "clearead:page-tool-command-v6";
  const STYLE_ID = "clearead-readable-style";
  const RULER_ID = "clearead-reading-ruler-v2";
  const LEGACY_RULER_IDS = Object.freeze(["clearead-reading-ruler"]);
  const DICTIONARY_POPOVER_ID = "clearead-dictionary-popover";
  const LENS_SOURCE_ATTRIBUTE = "data-clearead-lens-source";
  const LENS_ZOOM = 1.45;
  const FONT_MODES = Object.freeze({
    original: {
      label: "Original",
      family: "",
    },
    verdana: {
      label: "Verdana",
      family: "'Verdana', 'Geneva', sans-serif",
    },
    opendyslexic: {
      label: "OpenDyslexic",
      family: "'OpenDyslexic', 'Comic Sans MS', 'Trebuchet MS', Arial, sans-serif",
    },
    calibri: {
      label: "Calibri",
      family: "'Calibri', 'Gill Sans', 'Trebuchet MS', sans-serif",
    },
  });
  const RULER_MODES = Object.freeze({
    none: {
      label: "No ruler",
      height: 0,
    },
    highlight: {
      label: "Highlight ruler",
      height: 50,
    },
    lens: {
      label: "Lens ruler",
      height: 124,
    },
    line: {
      label: "Line guide ruler",
      height: 56,
    },
  });

  if (globalThis[NAMESPACE]?.version === VERSION) {
    return;
  }

  globalThis[NAMESPACE]?.destroy?.();

  let rulerMoveHandler = null;
  let rulerScrollHandler = null;
  let activeFontMode = "original";
  let activeRulerMode = "none";
  let lastPointerX = Math.round(window.innerWidth / 2);
  let lastPointerY = Math.round(window.innerHeight / 2);

  function getContainer() {
    return document.body || document.documentElement;
  }

  function requirePageContainer() {
    const container = getContainer();
    if (!container) {
      throw new Error("Clearead page tools cannot find a page container to update.");
    }
    return container;
  }

  function removeReadableFontStyle() {
    document.getElementById(STYLE_ID)?.remove();
  }

  function normaliseFontMode(fontMode) {
    return FONT_MODES[fontMode] ? fontMode : "verdana";
  }

  function setReadableFont(fontMode = "verdana") {
    const normalisedMode = normaliseFontMode(fontMode);

    if (normalisedMode === "original") {
      removeReadableFontStyle();
      activeFontMode = "original";
      return {
        ok: true,
        fontMode: "original",
        message: "Original page font restored.",
      };
    }

    const fontConfig = FONT_MODES[normalisedMode];
    removeReadableFontStyle();

    const style = document.createElement("style");
    style.id = STYLE_ID;
    style.dataset.cleareadFontMode = normalisedMode;
    style.textContent = `
      body,
      main,
      article,
      section,
      aside,
      p,
      li,
      blockquote,
      dd,
      dt,
      figcaption,
      label,
      summary,
      table,
      input,
      textarea,
      select,
      button,
      h1,
      h2,
      h3,
      h4,
      h5,
      h6,
      a,
      span {
        font-family: ${fontConfig.family} !important;
      }

      main,
      article,
      section,
      p,
      li,
      blockquote,
      dd,
      dt,
      figcaption,
      label,
      summary,
      table {
        line-height: 1.82 !important;
      }

      p,
      li,
      blockquote,
      dd,
      dt,
      figcaption,
      label,
      summary,
      a,
      span {
        letter-spacing: 0.035em !important;
        word-spacing: 0.14em !important;
      }
    `;

    (document.head || document.documentElement || requirePageContainer()).appendChild(style);
    activeFontMode = normalisedMode;

    return {
      ok: true,
      fontMode: normalisedMode,
      message: `${fontConfig.label} font applied with wider reading spacing.`,
    };
  }

  function applyReadableFont(fontMode = "verdana") {
    return setReadableFont(fontMode);
  }

  function resetReadableFont() {
    return setReadableFont("original");
  }

  function isCleareadOwnedElement(element) {
    const ownedSelector = [`#${RULER_ID}`, ...LEGACY_RULER_IDS.map((id) => `#${id}`), `#${DICTIONARY_POPOVER_ID}`].join(", ");
    return Boolean(element?.closest?.(ownedSelector));
  }

  function getDocumentWidth() {
    return Math.max(
      document.documentElement?.scrollWidth || 0,
      document.body?.scrollWidth || 0,
      window.innerWidth
    );
  }

  function getDocumentHeight() {
    return Math.max(
      document.documentElement?.scrollHeight || 0,
      document.body?.scrollHeight || 0,
      window.innerHeight
    );
  }

  function cleanLensClone(clone) {
    [RULER_ID, ...LEGACY_RULER_IDS, DICTIONARY_POPOVER_ID].forEach((id) => {
      clone.querySelectorAll(`#${id}`).forEach((element) => element.remove());
    });

    clone.querySelectorAll("script").forEach((element) => element.remove());
    clone.querySelectorAll("iframe, video, audio, canvas, object, embed").forEach((element) => {
      element.removeAttribute("src");
      element.removeAttribute("srcdoc");
      element.setAttribute("aria-hidden", "true");
      Object.assign(element.style, {
        background: "rgba(226, 232, 240, 0.9)",
      });
    });
  }

  function createLensPageClone() {
    const clone = document.createElement("div");
    const bodyStyle = document.body ? globalThis.getComputedStyle(document.body) : null;

    clone.setAttribute("aria-hidden", "true");
    clone.className = document.body?.className || "";
    clone.innerHTML = document.body?.innerHTML || "";

    Object.assign(clone.style, {
      position: "absolute",
      top: "0",
      left: "0",
      width: `${getDocumentWidth()}px`,
      minHeight: `${getDocumentHeight()}px`,
      margin: bodyStyle?.margin || "0",
      padding: bodyStyle?.padding || "0",
      pointerEvents: "none",
      transformOrigin: "0 0",
    });

    cleanLensClone(clone);
    return clone;
  }

  function createLensCloneViewport() {
    const viewport = document.createElement("div");
    const source = document.createElement("div");

    Object.assign(viewport.style, {
      position: "absolute",
      inset: "0",
      overflow: "hidden",
      borderRadius: "inherit",
      background: "#ffffff",
      contain: "layout style paint",
    });

    source.setAttribute(LENS_SOURCE_ATTRIBUTE, "true");
    Object.assign(source.style, {
      position: "absolute",
      top: "0",
      left: "0",
      width: `${getDocumentWidth()}px`,
      minHeight: `${getDocumentHeight()}px`,
      pointerEvents: "none",
      transformOrigin: "0 0",
      willChange: "transform",
    });

    source.appendChild(createLensPageClone());
    viewport.appendChild(source);
    return viewport;
  }

  function updateLensCloneSource(ruler, clientX, clientY) {
    const source = ruler.querySelector(`[${LENS_SOURCE_ATTRIBUTE}]`);

    if (!source) {
      return;
    }

    const rect = ruler.getBoundingClientRect();
    const pageX = window.scrollX + clientX;
    const pageY = window.scrollY + clientY;
    const focusX = Math.max(0, Math.min(rect.width, clientX - rect.left));
    const focusY = Math.max(0, Math.min(rect.height, clientY - rect.top));
    const translateX = focusX - pageX * LENS_ZOOM;
    const translateY = focusY - pageY * LENS_ZOOM;

    source.style.width = `${getDocumentWidth()}px`;
    source.style.minHeight = `${getDocumentHeight()}px`;
    source.style.transform = `translate3d(${translateX}px, ${translateY}px, 0) scale(${LENS_ZOOM})`;
  }

  function setRulerPosition(clientX, clientY) {
    const ruler = document.getElementById(RULER_ID);

    if (!ruler) {
      return;
    }

    lastPointerX = Number.isFinite(clientX) ? clientX : lastPointerX;
    lastPointerY = Number.isFinite(clientY) ? clientY : lastPointerY;

    if (activeRulerMode === "lens") {
      const rulerWidth = ruler.offsetWidth || Math.min(720, window.innerWidth - 24);
      const rulerHeight = ruler.offsetHeight || 124;
      const maximumLeft = Math.max(12, window.innerWidth - rulerWidth - 12);
      const maximumTop = Math.max(12, window.innerHeight - rulerHeight - 12);
      const nextLeft = Math.max(12, Math.min(maximumLeft, lastPointerX - rulerWidth / 2));
      const nextTop = Math.max(12, Math.min(maximumTop, lastPointerY - rulerHeight / 2));

      ruler.style.transform = `translate3d(${Math.round(nextLeft)}px, ${Math.round(nextTop)}px, 0)`;
      updateLensCloneSource(ruler, lastPointerX, lastPointerY);
      return;
    }

    const rulerHeight = ruler.offsetHeight || RULER_MODES[activeRulerMode]?.height || 50;
    const maximumTop = Math.max(0, window.innerHeight - rulerHeight);
    const nextTop = Math.max(0, Math.min(maximumTop, lastPointerY - rulerHeight / 2));
    ruler.style.transform = `translateY(${Math.round(nextTop)}px)`;
  }

  function removeReadingRulerElement() {
    document.getElementById(RULER_ID)?.remove();
    LEGACY_RULER_IDS.forEach((id) => document.getElementById(id)?.remove());

    if (rulerMoveHandler) {
      document.removeEventListener("pointermove", rulerMoveHandler);
      rulerMoveHandler = null;
    }

    if (rulerScrollHandler) {
      globalThis.removeEventListener("scroll", rulerScrollHandler);
      rulerScrollHandler = null;
    }

  }

  function buildReadingRuler(rulerMode) {
    const modeConfig = RULER_MODES[rulerMode] || RULER_MODES.highlight;
    const ruler = document.createElement("div");
    ruler.id = RULER_ID;
    ruler.dataset.cleareadRulerMode = rulerMode;
    ruler.setAttribute("aria-hidden", "true");
    Object.assign(ruler.style, {
      position: "fixed",
      top: "0",
      left: "0",
      width: "100vw",
      height: `${modeConfig.height}px`,
      pointerEvents: "none",
      zIndex: "2147483647",
      transform: "translateY(40vh)",
      overflow: "hidden",
      willChange: "transform",
    });

    if (rulerMode === "highlight") {
      Object.assign(ruler.style, {
        background:
          "linear-gradient(180deg, rgba(219, 234, 254, 0.12), rgba(96, 165, 250, 0.22), rgba(219, 234, 254, 0.12))",
        borderTop: "1px solid rgba(37, 99, 235, 0.32)",
        borderBottom: "1px solid rgba(37, 99, 235, 0.32)",
        boxShadow: "0 0 0 9999px rgba(15, 23, 42, 0.13)",
      });
    }

    if (rulerMode === "lens") {
      Object.assign(ruler.style, {
        left: "0",
        width: "min(720px, calc(100vw - 24px))",
        height: "124px",
        border: "1px solid rgba(37, 99, 235, 0.35)",
        borderRadius: "18px",
        background: "#ffffff",
        boxShadow:
          "0 0 0 9999px rgba(15, 23, 42, 0.16), 0 14px 38px rgba(37, 99, 235, 0.22), inset 0 1px 0 rgba(255, 255, 255, 0.78)",
      });

      ruler.appendChild(createLensCloneViewport());
    }

    if (rulerMode === "line") {
      Object.assign(ruler.style, {
        background:
          "linear-gradient(180deg, rgba(219, 234, 254, 0.1), rgba(147, 197, 253, 0.2), rgba(219, 234, 254, 0.1))",
        borderTop: "1px solid rgba(37, 99, 235, 0.28)",
        borderBottom: "1px solid rgba(37, 99, 235, 0.28)",
        boxShadow: "0 0 0 9999px rgba(15, 23, 42, 0.13)",
      });

      const centerLine = document.createElement("div");
      Object.assign(centerLine.style, {
        position: "absolute",
        top: "50%",
        left: "0",
        right: "0",
        height: "2px",
        transform: "translateY(-50%)",
        background: "rgba(37, 99, 235, 0.58)",
        boxShadow: "0 1px 0 rgba(255, 255, 255, 0.55)",
      });
      ruler.appendChild(centerLine);
    }

    return ruler;
  }

  function setReadingRuler(rulerMode = "highlight") {
    const normalisedMode = RULER_MODES[rulerMode] ? rulerMode : "highlight";

    if (normalisedMode === "none") {
      return disableReadingRuler();
    }

    removeReadingRulerElement();
    activeRulerMode = normalisedMode;

    const ruler = buildReadingRuler(normalisedMode);
    requirePageContainer().appendChild(ruler);
    rulerMoveHandler = (event) => setRulerPosition(event.clientX, event.clientY);
    document.addEventListener("pointermove", rulerMoveHandler, { passive: true });

    if (normalisedMode === "lens") {
      rulerScrollHandler = () => setRulerPosition(lastPointerX, lastPointerY);
      globalThis.addEventListener("scroll", rulerScrollHandler, { passive: true });
    }

    setRulerPosition(window.innerWidth / 2, window.innerHeight / 2);

    return {
      ok: true,
      rulerMode: normalisedMode,
      message: `${RULER_MODES[normalisedMode].label} is on.`,
    };
  }

  function disableReadingRuler() {
    const hadRuler = Boolean(
      document.getElementById(RULER_ID) ||
        LEGACY_RULER_IDS.some((id) => document.getElementById(id))
    );
    removeReadingRulerElement();
    activeRulerMode = "none";

    return {
      ok: true,
      rulerMode: "none",
      message: hadRuler ? "Reading ruler is off." : "No reading ruler is active on this page.",
    };
  }

  function toggleReadingRuler() {
    const hasRuler =
      document.getElementById(RULER_ID) ||
      LEGACY_RULER_IDS.some((id) => document.getElementById(id));

    return hasRuler
      ? disableReadingRuler()
      : setReadingRuler("highlight");
  }

  function getCurrentFontMode() {
    const storedFontMode = document.getElementById(STYLE_ID)?.dataset.cleareadFontMode;

    if (FONT_MODES[storedFontMode]) {
      activeFontMode = storedFontMode;
      return storedFontMode;
    }

    if (!document.getElementById(STYLE_ID)) {
      activeFontMode = "original";
      return "original";
    }

    return FONT_MODES[activeFontMode] ? activeFontMode : "verdana";
  }

  function getCurrentRulerMode() {
    const ruler = document.getElementById(RULER_ID);
    const storedRulerMode = ruler?.dataset.cleareadRulerMode;

    if (RULER_MODES[storedRulerMode]) {
      activeRulerMode = storedRulerMode;
      return storedRulerMode;
    }

    if (LEGACY_RULER_IDS.some((id) => document.getElementById(id))) {
      return RULER_MODES[activeRulerMode] && activeRulerMode !== "none"
        ? activeRulerMode
        : "highlight";
    }

    activeRulerMode = "none";
    return "none";
  }

  function getPageToolState() {
    const fontMode = getCurrentFontMode();
    const rulerMode = getCurrentRulerMode();

    return {
      ok: true,
      fontMode,
      rulerMode,
      message:
        fontMode === "original" && rulerMode === "none"
          ? "Page tools ready."
          : "Page tools synced with the current page.",
    };
  }

  function getSelectionAnchorRect() {
    const selection = globalThis.getSelection?.();

    if (!selection || selection.rangeCount === 0) {
      return null;
    }

    const range = selection.getRangeAt(0);
    const rects = range.getClientRects();
    return rects[0] || range.getBoundingClientRect();
  }

  function placeDictionaryPopover(popover) {
    const rect = getSelectionAnchorRect();
    const fallbackLeft = Math.min(24, Math.max(12, window.innerWidth - 340));
    const fallbackTop = Math.min(96, Math.max(12, window.innerHeight - 260));
    const preferredLeft = rect ? rect.left : fallbackLeft;
    const preferredTop = rect ? rect.bottom + 10 : fallbackTop;
    const maxLeft = Math.max(12, window.innerWidth - 340);
    const maxTop = Math.max(12, window.innerHeight - 260);

    popover.style.left = `${Math.round(Math.min(Math.max(12, preferredLeft), maxLeft))}px`;
    popover.style.top = `${Math.round(Math.min(Math.max(12, preferredTop), maxTop))}px`;
  }

  function appendPopoverText(parent, tagName, className, text) {
    const element = document.createElement(tagName);
    element.className = className;
    element.textContent = text;
    parent.appendChild(element);
    return element;
  }

  function showDictionaryPopover(explanation) {
    const existingPopover = document.getElementById(DICTIONARY_POPOVER_ID);

    if (existingPopover) {
      existingPopover.remove();
    }

    const popover = document.createElement("aside");
    popover.id = DICTIONARY_POPOVER_ID;
    popover.setAttribute("role", "dialog");
    popover.setAttribute("aria-label", "Clearead dictionary");
    Object.assign(popover.style, {
      position: "fixed",
      width: "min(320px, calc(100vw - 24px))",
      maxHeight: "min(260px, calc(100vh - 24px))",
      overflow: "auto",
      zIndex: "2147483647",
      border: "1px solid #cbd5e1",
      borderRadius: "8px",
      background: "#ffffff",
      boxShadow: "0 18px 42px rgba(15, 23, 42, 0.22)",
      color: "#172033",
      fontFamily: "Arial, Verdana, Tahoma, sans-serif",
      lineHeight: "1.45",
      padding: "12px",
    });

    const header = document.createElement("div");
    Object.assign(header.style, {
      display: "flex",
      alignItems: "flex-start",
      justifyContent: "space-between",
      gap: "10px",
      marginBottom: "8px",
    });

    const label = appendPopoverText(header, "p", "clearead-dictionary-label", "Clearead");
    Object.assign(label.style, {
      margin: "0",
      color: "#2563eb",
      fontSize: "12px",
      fontWeight: "700",
      letterSpacing: "0",
    });

    const closeButton = document.createElement("button");
    closeButton.type = "button";
    closeButton.setAttribute("aria-label", "Close Clearead dictionary");
    closeButton.textContent = "x";
    Object.assign(closeButton.style, {
      width: "28px",
      height: "28px",
      flex: "0 0 auto",
      border: "1px solid #d0d7e2",
      borderRadius: "6px",
      background: "#ffffff",
      color: "#243043",
      cursor: "pointer",
      font: "700 18px/1 Arial, Verdana, Tahoma, sans-serif",
    });
    closeButton.addEventListener("click", () => popover.remove());
    header.appendChild(closeButton);
    popover.appendChild(header);

    if (!explanation?.ok) {
      appendPopoverText(
        popover,
        "p",
        "clearead-dictionary-message",
        explanation?.message || "Select one word or a short phrase on the page, then try again."
      );
    } else {
      const term = appendPopoverText(
        popover,
        "h2",
        "clearead-dictionary-term",
        explanation.term
      );
      Object.assign(term.style, {
        margin: "0 0 8px",
        color: "#101828",
        fontSize: "17px",
        lineHeight: "1.3",
        overflowWrap: "anywhere",
      });

      const meaning = appendPopoverText(
        popover,
        "p",
        "clearead-dictionary-meaning",
        explanation.meaning
      );
      Object.assign(meaning.style, {
        margin: "0 0 8px",
        color: "#243043",
        fontSize: "14px",
      });

      if (Array.isArray(explanation.parts) && explanation.parts.length > 0) {
        const partsList = document.createElement("ul");
        Object.assign(partsList.style, {
          display: "grid",
          gap: "4px",
          margin: "0 0 8px",
          paddingLeft: "18px",
          color: "#4f5f72",
          fontSize: "13px",
        });

        explanation.parts.forEach((part) => {
          appendPopoverText(partsList, "li", "", part);
        });
        popover.appendChild(partsList);
      }
    }

    const note = appendPopoverText(
      popover,
      "p",
      "clearead-dictionary-note",
      explanation?.note || "Local guidance only. This is not a full dictionary service."
    );
    Object.assign(note.style, {
      margin: "8px 0 0",
      color: "#607086",
      fontSize: "12px",
    });

    requirePageContainer().appendChild(popover);
    placeDictionaryPopover(popover);

    return {
      ok: true,
      message: explanation?.matchedLocalGlossary
        ? "Local glossary meaning shown."
        : "Local fallback guidance shown.",
    };
  }

  function runCommand(message) {
    const action = message.action;

    if (action === "set-readable-font") {
      return setReadableFont(message.fontMode);
    }

    if (action === "get-page-tool-state") {
      return getPageToolState();
    }

    if (action === "set-reading-ruler") {
      return setReadingRuler(message.rulerMode);
    }

    if (action === "apply-readable-font") {
      return applyReadableFont(message.fontMode);
    }

    if (action === "reset-readable-font") {
      return resetReadableFont();
    }

    if (action === "toggle-reading-ruler") {
      return toggleReadingRuler();
    }

    if (action === "show-dictionary-popover") {
      return showDictionaryPopover(message.explanation);
    }

    throw new Error("Clearead does not recognise that page tool action.");
  }

  function handleCleareadPageToolMessage(message, _sender, sendResponse) {
    if (message?.type !== MESSAGE_TYPE) {
      return false;
    }

    try {
      sendResponse(runCommand(message));
    } catch (error) {
      sendResponse({
        ok: false,
        message: error.message || "Clearead page tools could not update this page.",
      });
    }

    return true;
  }

  chrome.runtime.onMessage.addListener(handleCleareadPageToolMessage);

  globalThis[NAMESPACE] = {
    version: VERSION,
    destroy() {
      chrome.runtime.onMessage.removeListener(handleCleareadPageToolMessage);
    },
    applyReadableFont,
    resetReadableFont,
    setReadableFont,
    setReadingRuler,
    getPageToolState,
    toggleReadingRuler,
    showDictionaryPopover,
  };
})();
