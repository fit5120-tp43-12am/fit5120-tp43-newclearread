(() => {
  const NAMESPACE = "CleareadPageTools";
  const VERSION = "0.1.0";
  const MESSAGE_TYPE = "clearead:page-tool-command";
  const STYLE_ID = "clearead-readable-style";
  const RULER_ID = "clearead-reading-ruler";
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

  function runCommand(action) {
    if (action === "apply-readable-font") {
      return applyReadableFont();
    }

    if (action === "reset-readable-font") {
      return resetReadableFont();
    }

    if (action === "toggle-reading-ruler") {
      return toggleReadingRuler();
    }

    throw new Error("Clearead does not recognise that page tool action.");
  }

  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message?.type !== MESSAGE_TYPE) {
      return false;
    }

    try {
      sendResponse(runCommand(message.action));
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
  };
})();
