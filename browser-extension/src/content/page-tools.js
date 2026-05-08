(() => {
  const NAMESPACE = "CleareadPageTools";
  const VERSION = "0.3.0";
  const MESSAGE_TYPE = "clearead:page-tool-command";
  const STYLE_ID = "clearead-readable-style";
  const RULER_ID = "clearead-reading-ruler";
  const DICTIONARY_POPOVER_ID = "clearead-dictionary-popover";
  const RULER_HEIGHT = 44;

  if (globalThis[NAMESPACE]?.version === VERSION) {
    return;
  }

  let rulerMoveHandler = null;

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

  function applyReadableFont() {
    if (document.getElementById(STYLE_ID)) {
      return {
        ok: true,
        message: "Readable font is already applied to this page.",
      };
    }

    const style = document.createElement("style");
    style.id = STYLE_ID;
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
      h6 {
        font-family: Arial, Verdana, Tahoma, sans-serif !important;
      }

      main,
      article,
      section,
      p,
      li,
      blockquote,
      dd,
      dt,
      figcaption {
        line-height: 1.6 !important;
      }

      p,
      li,
      blockquote {
        word-spacing: 0.04em !important;
      }
    `;

    (document.head || document.documentElement || requirePageContainer()).appendChild(style);

    return {
      ok: true,
      message: "Readable font applied to this page.",
    };
  }

  function resetReadableFont() {
    const style = document.getElementById(STYLE_ID);

    if (style) {
      style.remove();
      return {
        ok: true,
        message: "Readable font styles removed from this page.",
      };
    }

    return {
      ok: true,
      message: "No Clearead font styles were active on this page.",
    };
  }

  function setRulerPosition(clientY) {
    const ruler = document.getElementById(RULER_ID);

    if (!ruler) {
      return;
    }

    const maximumTop = Math.max(0, window.innerHeight - RULER_HEIGHT);
    const nextTop = Math.max(0, Math.min(maximumTop, clientY - RULER_HEIGHT / 2));
    ruler.style.transform = `translateY(${Math.round(nextTop)}px)`;
  }

  function enableReadingRuler() {
    if (document.getElementById(RULER_ID)) {
      return {
        ok: true,
        message: "Reading ruler is already on.",
      };
    }

    const ruler = document.createElement("div");
    ruler.id = RULER_ID;
    ruler.setAttribute("aria-hidden", "true");
    Object.assign(ruler.style, {
      position: "fixed",
      top: "0",
      left: "0",
      width: "100vw",
      height: `${RULER_HEIGHT}px`,
      pointerEvents: "none",
      zIndex: "2147483647",
      transform: "translateY(40vh)",
      background:
        "linear-gradient(180deg, rgba(255, 245, 157, 0.1), rgba(255, 224, 130, 0.34), rgba(255, 245, 157, 0.1))",
      borderTop: "1px solid rgba(245, 158, 11, 0.45)",
      borderBottom: "1px solid rgba(245, 158, 11, 0.45)",
      boxShadow: "0 0 0 9999px rgba(17, 24, 39, 0.08)",
    });

    requirePageContainer().appendChild(ruler);
    rulerMoveHandler = (event) => setRulerPosition(event.clientY);
    document.addEventListener("pointermove", rulerMoveHandler, { passive: true });
    setRulerPosition(window.innerHeight / 2);

    return {
      ok: true,
      message: "Reading ruler is on.",
    };
  }

  function disableReadingRuler() {
    const ruler = document.getElementById(RULER_ID);

    if (ruler) {
      ruler.remove();
    }

    if (rulerMoveHandler) {
      document.removeEventListener("pointermove", rulerMoveHandler);
      rulerMoveHandler = null;
    }

    return {
      ok: true,
      message: ruler ? "Reading ruler is off." : "Reading ruler was not active on this page.",
    };
  }

  function toggleReadingRuler() {
    return document.getElementById(RULER_ID)
      ? disableReadingRuler()
      : enableReadingRuler();
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

  function runCommand(action, explanation) {
    if (action === "apply-readable-font") {
      return applyReadableFont();
    }

    if (action === "reset-readable-font") {
      return resetReadableFont();
    }

    if (action === "toggle-reading-ruler") {
      return toggleReadingRuler();
    }

    if (action === "show-dictionary-popover") {
      return showDictionaryPopover(explanation);
    }

    throw new Error("Clearead does not recognise that page tool action.");
  }

  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message?.type !== MESSAGE_TYPE) {
      return false;
    }

    try {
      sendResponse(runCommand(message.action, message.explanation));
    } catch (error) {
      sendResponse({
        ok: false,
        message: error.message || "Clearead page tools could not update this page.",
      });
    }

    return true;
  });

  globalThis[NAMESPACE] = {
    version: VERSION,
    applyReadableFont,
    resetReadableFont,
    toggleReadingRuler,
    showDictionaryPopover,
  };
})();
