(() => {
  const NAMESPACE = "CleareadPageTools";
  const VERSION = "0.7.7";
  const MESSAGE_TYPE = "clearead:page-tool-command-v7";
  const STYLE_ID = "clearead-readable-style";
  const RULER_ID = "clearead-reading-ruler-v2";
  const LEGACY_RULER_IDS = Object.freeze(["clearead-reading-ruler"]);
  const DICTIONARY_POPOVER_ID = "clearead-dictionary-popover";
  const DICTIONARY_TAIL_ID = "clearead-dictionary-tail";
  const LENS_SOURCE_ATTRIBUTE = "data-clearead-lens-source";
  const LENS_ZOOM = 1.45;
  const LENS_EMBEDDED_RESOURCE_SELECTOR =
    "iframe, video, audio, canvas, object, embed, source, track";
  const LENS_EMBEDDED_RESOURCE_ATTRIBUTES = Object.freeze([
    "src",
    "srcdoc",
    "srcset",
    "poster",
    "data",
    "code",
    "archive",
  ]);
  const LENS_CLONE_REFRESH_THROTTLE_MS = 260;
  const LENS_SCROLL_MUTATION_GRACE_MS = 900;
  const LENS_MUTATION_SAFETY_WINDOW_MS = 2500;
  const LENS_MUTATION_SAFETY_LIMIT = 160;
  const LENS_MAX_CLONE_ELEMENTS = 7000;
  const LENS_MAX_DOCUMENT_EDGE_PX = 60000;
  const LENS_MAX_DOCUMENT_AREA_PX = 90000000;
  const LENS_SAFETY_MESSAGE =
    "Lens stopped on this dynamic page. Try Highlight or Line guide.";
  const LENS_COMPLEX_PAGE_MESSAGE =
    "Lens may be too slow on this page. Try Highlight or Line guide.";
  const LENS_START_FAILED_MESSAGE =
    "Lens could not start on this page. Try Highlight or Line guide.";
  const OPEN_DYSLEXIC_FONT_FAMILY = "CleareadOpenDyslexic";
  const DEFAULT_LIGHT_PAGE_THEME = Object.freeze({
    name: "light",
    background: "#ffffff",
    text: "#172033",
    embeddedPlaceholderBackground: "rgba(226, 232, 240, 0.9)",
  });
  const DEFAULT_DARK_PAGE_THEME = Object.freeze({
    name: "dark",
    background: "#0d1117",
    text: "#f8fafc",
    embeddedPlaceholderBackground: "rgba(30, 41, 59, 0.92)",
  });
  const RULER_VISUAL_THEMES = Object.freeze({
    light: {
      border: "1px solid rgba(37, 99, 235, 0.46)",
      edgeGlow:
        "0 -14px 20px -16px rgba(37, 99, 235, 0.6), 0 14px 20px -16px rgba(37, 99, 235, 0.6), 0 0 0 9999px rgba(15, 23, 42, 0.18)",
      lensBorder: "1px solid rgba(37, 99, 235, 0.35)",
      lensShadow:
        "0 0 0 9999px rgba(15, 23, 42, 0.16), 0 14px 38px rgba(37, 99, 235, 0.22), inset 0 1px 0 rgba(255, 255, 255, 0.78)",
      lineColor: "rgba(37, 99, 235, 0.58)",
      lineShadow: "0 1px 0 rgba(255, 255, 255, 0.55)",
    },
    dark: {
      border: "2px solid rgba(147, 197, 253, 0.92)",
      edgeGlow:
        "0 -18px 30px -16px rgba(96, 165, 250, 0.95), 0 18px 30px -16px rgba(96, 165, 250, 0.95), 0 0 0 9999px rgba(0, 0, 0, 0.24), inset 0 1px 0 rgba(255, 255, 255, 0.24), inset 0 -1px 0 rgba(255, 255, 255, 0.24)",
      lensBorder: "2px solid rgba(147, 197, 253, 0.9)",
      lensShadow:
        "0 0 0 9999px rgba(0, 0, 0, 0.28), 0 16px 42px rgba(96, 165, 250, 0.32), 0 0 20px rgba(96, 165, 250, 0.22), inset 0 1px 0 rgba(255, 255, 255, 0.16)",
      lineColor: "rgba(191, 219, 254, 0.98)",
      lineShadow: "0 0 12px rgba(96, 165, 250, 0.75)",
    },
  });
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
      family: `'${OPEN_DYSLEXIC_FONT_FAMILY}', 'OpenDyslexic', 'Comic Sans MS', 'Trebuchet MS', Arial, sans-serif`,
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
      label: "Highlight",
      height: 50,
    },
    lens: {
      label: "Lens",
      height: 124,
    },
    line: {
      label: "Line guide",
      height: 56,
    },
  });

  if (globalThis[NAMESPACE]?.version === VERSION) {
    return;
  }

  globalThis[NAMESPACE]?.destroy?.();

  let rulerMoveHandler = null;
  let rulerScrollHandler = null;
  let lensMutationObserver = null;
  let lensRefreshFrame = 0;
  let lensRefreshTimer = null;
  let lensCloneDirty = false;
  let lastLensCloneRefreshAt = 0;
  let lastLensScrollAt = 0;
  let lensMutationWindowStartedAt = 0;
  let lensMutationCountInWindow = 0;
  let lastPageToolNotice = "";
  let lastPageToolNoticeType = "neutral";
  let dictionaryOutsideClickHandler = null;
  let dictionaryKeydownHandler = null;
  let dictionaryRepositionHandler = null;
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
      throw new Error("Page tools are unavailable here.");
    }
    return container;
  }

  function parseCssRgbColor(value) {
    const match = String(value || "")
      .trim()
      .match(/^rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)(?:\s*,\s*([\d.]+))?\s*\)$/i);

    if (!match) {
      return null;
    }

    const alpha = match[4] === undefined ? 1 : Number.parseFloat(match[4]);

    if (!Number.isFinite(alpha) || alpha <= 0.05) {
      return null;
    }

    return {
      r: Math.max(0, Math.min(255, Number.parseFloat(match[1]))),
      g: Math.max(0, Math.min(255, Number.parseFloat(match[2]))),
      b: Math.max(0, Math.min(255, Number.parseFloat(match[3]))),
      a: alpha,
    };
  }

  function toRgbString(color) {
    return `rgb(${Math.round(color.r)}, ${Math.round(color.g)}, ${Math.round(color.b)})`;
  }

  function getRelativeLuminance(color) {
    const channelValues = [color.r, color.g, color.b].map((channel) => {
      const normalized = channel / 255;
      return normalized <= 0.03928
        ? normalized / 12.92
        : ((normalized + 0.055) / 1.055) ** 2.4;
    });

    return (
      0.2126 * channelValues[0] +
      0.7152 * channelValues[1] +
      0.0722 * channelValues[2]
    );
  }

  function findEffectiveBackgroundColor(element) {
    let current = element;

    while (current && current.nodeType === Node.ELEMENT_NODE) {
      const color = parseCssRgbColor(globalThis.getComputedStyle(current).backgroundColor);

      if (color) {
        return color;
      }

      current = current.parentElement;
    }

    return null;
  }

  function getPageTheme() {
    const sampleX = Math.max(0, Math.min(window.innerWidth - 1, lastPointerX));
    const sampleY = Math.max(0, Math.min(window.innerHeight - 1, lastPointerY));
    const sampleElement = document.elementFromPoint(sampleX, sampleY);
    const backgroundColor =
      findEffectiveBackgroundColor(sampleElement) ||
      findEffectiveBackgroundColor(document.body) ||
      findEffectiveBackgroundColor(document.documentElement);
    const textColor =
      parseCssRgbColor(globalThis.getComputedStyle(document.body || document.documentElement).color) ||
      parseCssRgbColor(globalThis.getComputedStyle(document.documentElement).color);

    if (!backgroundColor) {
      return DEFAULT_LIGHT_PAGE_THEME;
    }

    const isDark = getRelativeLuminance(backgroundColor) < 0.22;
    const fallbackTheme = isDark ? DEFAULT_DARK_PAGE_THEME : DEFAULT_LIGHT_PAGE_THEME;

    return {
      ...fallbackTheme,
      name: isDark ? "dark" : "light",
      background: toRgbString(backgroundColor),
      text: textColor ? toRgbString(textColor) : fallbackTheme.text,
    };
  }

  function getRulerVisualTheme(pageTheme) {
    return RULER_VISUAL_THEMES[pageTheme.name] || RULER_VISUAL_THEMES.light;
  }

  function removeReadableFontStyle() {
    document.getElementById(STYLE_ID)?.remove();
  }

  function normaliseFontMode(fontMode) {
    return FONT_MODES[fontMode] ? fontMode : "verdana";
  }

  function getExtensionResourceUrl(path) {
    try {
      return chrome.runtime.getURL(path);
    } catch {
      return "";
    }
  }

  function getOpenDyslexicFontFaceCss() {
    const regularUrl = getExtensionResourceUrl(
      "public/fonts/OpenDyslexic-Regular.woff2"
    );
    const boldUrl = getExtensionResourceUrl("public/fonts/OpenDyslexic-Bold.woff2");
    const italicUrl = getExtensionResourceUrl(
      "public/fonts/OpenDyslexic-Italic.woff2"
    );
    const boldItalicUrl = getExtensionResourceUrl(
      "public/fonts/OpenDyslexic-BoldItalic.woff2"
    );

    if (!regularUrl || !boldUrl || !italicUrl || !boldItalicUrl) {
      return "";
    }

    return `
      @font-face {
        font-family: '${OPEN_DYSLEXIC_FONT_FAMILY}';
        src: url('${regularUrl}') format('woff2');
        font-weight: 400;
        font-style: normal;
        font-display: swap;
      }

      @font-face {
        font-family: '${OPEN_DYSLEXIC_FONT_FAMILY}';
        src: url('${boldUrl}') format('woff2');
        font-weight: 700;
        font-style: normal;
        font-display: swap;
      }

      @font-face {
        font-family: '${OPEN_DYSLEXIC_FONT_FAMILY}';
        src: url('${italicUrl}') format('woff2');
        font-weight: 400;
        font-style: italic;
        font-display: swap;
      }

      @font-face {
        font-family: '${OPEN_DYSLEXIC_FONT_FAMILY}';
        src: url('${boldItalicUrl}') format('woff2');
        font-weight: 700;
        font-style: italic;
        font-display: swap;
      }
    `;
  }

  function setReadableFont(fontMode = "verdana") {
    const normalisedMode = normaliseFontMode(fontMode);

    if (normalisedMode === "original") {
      removeReadableFontStyle();
      activeFontMode = "original";
      return {
        ok: true,
        fontMode: "original",
        message: "Original font restored.",
      };
    }

    const fontConfig = FONT_MODES[normalisedMode];
    removeReadableFontStyle();

    const style = document.createElement("style");
    style.id = STYLE_ID;
    style.dataset.cleareadFontMode = normalisedMode;
    style.textContent = `
      ${normalisedMode === "opendyslexic" ? getOpenDyslexicFontFaceCss() : ""}

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
      message: `${fontConfig.label} applied.`,
    };
  }

  function isCleareadOwnedElement(element) {
    const ownedSelector = [
      `#${RULER_ID}`,
      ...LEGACY_RULER_IDS.map((id) => `#${id}`),
      `#${DICTIONARY_POPOVER_ID}`,
      `#${DICTIONARY_TAIL_ID}`,
    ].join(", ");
    return Boolean(element?.closest?.(ownedSelector));
  }

  function isCleareadOwnedNode(node) {
    if (node?.nodeType !== Node.ELEMENT_NODE) {
      return false;
    }

    return isCleareadOwnedElement(node);
  }

  function mutationTouchesPageContent(mutation) {
    if (isCleareadOwnedElement(mutation.target)) {
      return false;
    }

    if (mutation.type === "childList") {
      const changedNodes = [...mutation.addedNodes, ...mutation.removedNodes];

      if (
        changedNodes.length > 0 &&
        changedNodes.every((node) => {
          return node.nodeType !== Node.ELEMENT_NODE || isCleareadOwnedNode(node);
        })
      ) {
        return false;
      }
    }

    return true;
  }

  function markLensCloneDirty(mutations) {
    if (activeRulerMode !== "lens") {
      return;
    }

    const pageMutations = mutations.filter(mutationTouchesPageContent);

    if (pageMutations.length === 0) {
      return;
    }

    const mutationWeight = getLensMutationWeight(pageMutations);

    const mutationLooksScrollDriven =
      getNow() - lastLensScrollAt <= LENS_SCROLL_MUTATION_GRACE_MS;

    if (
      mutationWeight > 0 &&
      !mutationLooksScrollDriven &&
      shouldTurnOffLensForRapidPageChanges(mutationWeight)
    ) {
      setPageToolNotice("error", LENS_SAFETY_MESSAGE);
      disableReadingRuler();
      return;
    }

    lensCloneDirty = true;
    scheduleLensCloneRefresh();
  }

  function getNow() {
    return globalThis.performance?.now?.() || Date.now();
  }

  function resetLensSafetyCounter() {
    lensMutationWindowStartedAt = 0;
    lensMutationCountInWindow = 0;
  }

  function getLensStructuralMutationWeight(mutations) {
    return mutations.reduce((weight, mutation) => {
      if (mutation.type !== "childList") {
        return weight;
      }

      const changedElements = [...mutation.addedNodes, ...mutation.removedNodes].filter((node) => {
        return node.nodeType === Node.ELEMENT_NODE && !isCleareadOwnedNode(node);
      });

      return weight + changedElements.length;
    }, 0);
  }

  function getLensMutationWeight(mutations) {
    return mutations.reduce((weight, mutation) => {
      if (mutation.type === "childList") {
        return weight + Math.max(1, getLensStructuralMutationWeight([mutation]));
      }

      return weight + 1;
    }, 0);
  }

  function shouldTurnOffLensForRapidPageChanges(mutationCount) {
    const now = getNow();

    if (
      !lensMutationWindowStartedAt ||
      now - lensMutationWindowStartedAt > LENS_MUTATION_SAFETY_WINDOW_MS
    ) {
      lensMutationWindowStartedAt = now;
      lensMutationCountInWindow = 0;
    }

    lensMutationCountInWindow += mutationCount;
    return lensMutationCountInWindow > LENS_MUTATION_SAFETY_LIMIT;
  }

  function setPageToolNotice(type, message) {
    lastPageToolNoticeType = type;
    lastPageToolNotice = message;
  }

  function scheduleLensCloneRefresh() {
    if (lensRefreshFrame || lensRefreshTimer) {
      return;
    }

    lensRefreshFrame = globalThis.requestAnimationFrame(() => {
      lensRefreshFrame = 0;
      setRulerPosition(lastPointerX, lastPointerY);

      if (lensCloneDirty) {
        const refreshDelay = Math.max(
          0,
          LENS_CLONE_REFRESH_THROTTLE_MS - (getNow() - lastLensCloneRefreshAt)
        );

        lensRefreshTimer = globalThis.setTimeout(() => {
          lensRefreshTimer = null;
          setRulerPosition(lastPointerX, lastPointerY);
        }, refreshDelay);
      }
    });
  }

  function stopLensMutationObserver() {
    if (lensMutationObserver) {
      lensMutationObserver.disconnect();
      lensMutationObserver = null;
    }

    if (lensRefreshFrame) {
      globalThis.cancelAnimationFrame(lensRefreshFrame);
      lensRefreshFrame = 0;
    }

    if (lensRefreshTimer) {
      globalThis.clearTimeout(lensRefreshTimer);
      lensRefreshTimer = null;
    }

    lensCloneDirty = false;
    lastLensCloneRefreshAt = 0;
    resetLensSafetyCounter();
  }

  function startLensMutationObserver() {
    stopLensMutationObserver();

    const container = getContainer();

    if (!container || !globalThis.MutationObserver) {
      return;
    }

    resetLensSafetyCounter();
    lensMutationObserver = new MutationObserver(markLensCloneDirty);
    lensMutationObserver.observe(container, {
      attributes: true,
      characterData: true,
      childList: true,
      subtree: true,
    });
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

  function getLensPageComplexity() {
    const container = getContainer();
    const width = getDocumentWidth();
    const height = getDocumentHeight();
    const elementCount = container?.getElementsByTagName?.("*")?.length || 0;

    return {
      elementCount,
      width,
      height,
      area: width * height,
    };
  }

  function getLensReadinessMessage() {
    if (!document.body) {
      return LENS_START_FAILED_MESSAGE;
    }

    const complexity = getLensPageComplexity();
    if (
      complexity.elementCount > LENS_MAX_CLONE_ELEMENTS ||
      complexity.width > LENS_MAX_DOCUMENT_EDGE_PX ||
      complexity.height > LENS_MAX_DOCUMENT_EDGE_PX ||
      complexity.area > LENS_MAX_DOCUMENT_AREA_PX
    ) {
      return LENS_COMPLEX_PAGE_MESSAGE;
    }

    return "";
  }

  function cleanLensClone(clone, pageTheme) {
    [RULER_ID, ...LEGACY_RULER_IDS, DICTIONARY_POPOVER_ID, DICTIONARY_TAIL_ID].forEach((id) => {
      clone.querySelectorAll(`#${id}`).forEach((element) => element.remove());
    });

    clone.querySelectorAll("script").forEach((element) => element.remove());

    clone.querySelectorAll("*").forEach((element) => {
      Array.from(element.attributes).forEach((attribute) => {
        const attributeName = attribute.name.toLowerCase();

        if (attributeName.startsWith("on") || attributeName === "autofocus") {
          element.removeAttribute(attribute.name);
        }
      });
    });

    clone.querySelectorAll("form").forEach((element) => {
      element.removeAttribute("action");
    });

    clone.querySelectorAll(LENS_EMBEDDED_RESOURCE_SELECTOR).forEach((element) => {
      LENS_EMBEDDED_RESOURCE_ATTRIBUTES.forEach((attributeName) => {
        element.removeAttribute(attributeName);
      });
      element.setAttribute("aria-hidden", "true");
      Object.assign(element.style, {
        background: pageTheme.embeddedPlaceholderBackground,
      });
    });
  }

  function createLensPageClone(pageTheme = getPageTheme()) {
    const clone = document.body
      ? document.body.cloneNode(true)
      : document.createElement("div");
    const bodyStyle = document.body ? globalThis.getComputedStyle(document.body) : null;

    clone.setAttribute("aria-hidden", "true");

    Object.assign(clone.style, {
      position: "absolute",
      top: "0",
      left: "0",
      width: `${getDocumentWidth()}px`,
      minHeight: `${getDocumentHeight()}px`,
      margin: bodyStyle?.margin || "0",
      padding: bodyStyle?.padding || "0",
      background: pageTheme.background,
      color: pageTheme.text,
      colorScheme: pageTheme.name,
      pointerEvents: "none",
      transformOrigin: "0 0",
    });

    cleanLensClone(clone, pageTheme);
    return clone;
  }

  function createLensCloneViewport(pageTheme) {
    const viewport = document.createElement("div");
    const source = document.createElement("div");

    Object.assign(viewport.style, {
      position: "absolute",
      inset: "0",
      overflow: "hidden",
      borderRadius: "inherit",
      background: pageTheme.background,
      color: pageTheme.text,
      colorScheme: pageTheme.name,
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

    source.appendChild(createLensPageClone(pageTheme));
    viewport.appendChild(source);
    return viewport;
  }

  function refreshLensCloneSource(source) {
    const ruler = document.getElementById(RULER_ID);
    const pageTheme = getPageTheme();
    if (ruler) {
      ruler.dataset.cleareadPageTheme = pageTheme.name;
      ruler.style.background = pageTheme.background;
    }
    source.replaceChildren(createLensPageClone(pageTheme));
    lensCloneDirty = false;
    lastLensCloneRefreshAt = getNow();
  }

  function updateLensCloneSource(ruler, clientX, clientY) {
    const source = ruler.querySelector(`[${LENS_SOURCE_ATTRIBUTE}]`);

    if (!source) {
      return;
    }

    const now = getNow();

    if (
      lensCloneDirty &&
      now - lastLensCloneRefreshAt >= LENS_CLONE_REFRESH_THROTTLE_MS
    ) {
      refreshLensCloneSource(source);
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

    stopLensMutationObserver();
  }

  function buildReadingRuler(rulerMode) {
    const modeConfig = RULER_MODES[rulerMode] || RULER_MODES.highlight;
    const pageTheme = getPageTheme();
    const visualTheme = getRulerVisualTheme(pageTheme);
    const ruler = document.createElement("div");
    ruler.id = RULER_ID;
    ruler.dataset.cleareadRulerMode = rulerMode;
    ruler.dataset.cleareadPageTheme = pageTheme.name;
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
        background: "transparent",
        borderTop: visualTheme.border,
        borderBottom: visualTheme.border,
        boxShadow: visualTheme.edgeGlow,
      });
    }

    if (rulerMode === "lens") {
      Object.assign(ruler.style, {
        left: "0",
        width: "min(720px, calc(100vw - 24px))",
        height: "124px",
        border: visualTheme.lensBorder,
        borderRadius: "18px",
        background: pageTheme.background,
        boxShadow: visualTheme.lensShadow,
      });

      ruler.appendChild(createLensCloneViewport(pageTheme));
    }

    if (rulerMode === "line") {
      Object.assign(ruler.style, {
        background: "transparent",
        borderTop: visualTheme.border,
        borderBottom: visualTheme.border,
        boxShadow: visualTheme.edgeGlow,
      });

      const centerLine = document.createElement("div");
      Object.assign(centerLine.style, {
        position: "absolute",
        top: "50%",
        left: "0",
        right: "0",
        height: "2px",
        transform: "translateY(-50%)",
        background: visualTheme.lineColor,
        boxShadow: visualTheme.lineShadow,
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

    if (normalisedMode === "lens") {
      const readinessMessage = getLensReadinessMessage();

      if (readinessMessage) {
        removeReadingRulerElement();
        activeRulerMode = "none";
        setPageToolNotice("error", readinessMessage);
        return {
          ok: true,
          rulerMode: "none",
          noticeType: "error",
          message: readinessMessage,
        };
      }
    }

    removeReadingRulerElement();
    activeRulerMode = normalisedMode;

    let ruler;
    try {
      ruler = buildReadingRuler(normalisedMode);
      requirePageContainer().appendChild(ruler);
    } catch (error) {
      removeReadingRulerElement();
      activeRulerMode = "none";

      if (normalisedMode === "lens") {
        setPageToolNotice("error", LENS_START_FAILED_MESSAGE);
        return {
          ok: true,
          rulerMode: "none",
          noticeType: "error",
          message: LENS_START_FAILED_MESSAGE,
        };
      }

      throw error;
    }

    rulerMoveHandler = (event) => setRulerPosition(event.clientX, event.clientY);
    document.addEventListener("pointermove", rulerMoveHandler, { passive: true });

    if (normalisedMode === "lens") {
      rulerScrollHandler = () => {
        lastLensScrollAt = getNow();
        setRulerPosition(lastPointerX, lastPointerY);
      };
      globalThis.addEventListener("scroll", rulerScrollHandler, { passive: true });
      startLensMutationObserver();
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
      message: hadRuler ? "Ruler off." : "No ruler is active.",
    };
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

  function describePageToolState(fontMode, rulerMode) {
    const fontLabel = FONT_MODES[fontMode]?.label || FONT_MODES.original.label;
    const rulerLabel = RULER_MODES[rulerMode]?.label || RULER_MODES.none.label;

    return `Font: ${fontLabel}. Ruler: ${rulerLabel}.`;
  }

  function getPageToolState() {
    const fontMode = getCurrentFontMode();
    const rulerMode = getCurrentRulerMode();
    const noticeMessage = lastPageToolNotice;
    const noticeType = lastPageToolNoticeType;

    lastPageToolNotice = "";
    lastPageToolNoticeType = "neutral";

    return {
      ok: true,
      fontMode,
      rulerMode,
      ...(noticeMessage ? { noticeType } : {}),
      message:
        noticeMessage ||
        describePageToolState(fontMode, rulerMode),
    };
  }

  function getSelectionAnchorRect() {
    const selection = globalThis.getSelection?.();

    if (!selection || selection.rangeCount === 0) {
      return null;
    }

    const range = selection.getRangeAt(0);
    const rects = Array.from(range.getClientRects());
    const visibleRect = rects.find((rect) => rect.width > 0 && rect.height > 0);
    const fallbackRect = range.getBoundingClientRect();
    return visibleRect || (fallbackRect.width > 0 && fallbackRect.height > 0 ? fallbackRect : null);
  }

  function clampNumber(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  function removeDictionaryPopover() {
    globalThis.speechSynthesis?.cancel?.();
    document.getElementById(DICTIONARY_POPOVER_ID)?.remove();
    document.getElementById(DICTIONARY_TAIL_ID)?.remove();

    if (dictionaryOutsideClickHandler) {
      document.removeEventListener("pointerdown", dictionaryOutsideClickHandler, true);
      dictionaryOutsideClickHandler = null;
    }

    if (dictionaryKeydownHandler) {
      document.removeEventListener("keydown", dictionaryKeydownHandler, true);
      dictionaryKeydownHandler = null;
    }

    if (dictionaryRepositionHandler) {
      globalThis.removeEventListener("scroll", dictionaryRepositionHandler, true);
      globalThis.removeEventListener("resize", dictionaryRepositionHandler, true);
      dictionaryRepositionHandler = null;
    }
  }

  function placeDictionaryPopover(popover) {
    const rect = getSelectionAnchorRect();
    const margin = 12;
    const gap = 16;
    const popoverRect = popover.getBoundingClientRect();
    const popoverWidth = Math.min(popoverRect.width || 360, window.innerWidth - margin * 2);
    const popoverHeight = Math.min(popoverRect.height || 460, window.innerHeight - margin * 2);
    const fallbackLeft = Math.max(margin, Math.round((window.innerWidth - popoverWidth) / 2));
    const fallbackTop = Math.max(margin, Math.round((window.innerHeight - popoverHeight) / 2));
    let nextLeft = fallbackLeft;
    let nextTop = fallbackTop;

    if (rect) {
      const anchorCenterX = rect.left + rect.width / 2;
      const anchorCenterY = rect.top + rect.height / 2;
      const fitsRight = rect.right + gap + popoverWidth <= window.innerWidth - margin;
      const fitsLeft = rect.left - gap - popoverWidth >= margin;
      const fitsBelow = rect.bottom + gap + popoverHeight <= window.innerHeight - margin;

      if (fitsRight || (!fitsLeft && rect.left < window.innerWidth / 2)) {
        nextLeft = rect.right + gap;
        nextTop = anchorCenterY - popoverHeight / 2;
      } else if (fitsLeft) {
        nextLeft = rect.left - gap - popoverWidth;
        nextTop = anchorCenterY - popoverHeight / 2;
      } else if (fitsBelow) {
        nextLeft = anchorCenterX - popoverWidth / 2;
        nextTop = rect.bottom + gap;
      } else {
        nextLeft = anchorCenterX - popoverWidth / 2;
        nextTop = rect.top - gap - popoverHeight;
      }
    }

    popover.style.left = `${Math.round(clampNumber(nextLeft, margin, window.innerWidth - popoverWidth - margin))}px`;
    popover.style.top = `${Math.round(clampNumber(nextTop, margin, window.innerHeight - popoverHeight - margin))}px`;
    positionDictionaryTail(popover, rect);
  }

  function positionDictionaryTail(popover, anchorRect) {
    document.getElementById(DICTIONARY_TAIL_ID)?.remove();

    if (!anchorRect) {
      return;
    }

    const cardRect = popover.getBoundingClientRect();
    const anchorX = anchorRect.left + anchorRect.width / 2;
    const anchorY = anchorRect.top + anchorRect.height / 2;
    const size = 18;
    const inset = 26;
    let left = cardRect.left - size / 2;
    let top = clampNumber(anchorY, cardRect.top + inset, cardRect.bottom - inset) - size / 2;

    if (anchorX > cardRect.right) {
      left = cardRect.right - size / 2;
      top = clampNumber(anchorY, cardRect.top + inset, cardRect.bottom - inset) - size / 2;
    } else if (anchorY < cardRect.top) {
      left = clampNumber(anchorX, cardRect.left + inset, cardRect.right - inset) - size / 2;
      top = cardRect.top - size / 2;
    } else if (anchorY > cardRect.bottom) {
      left = clampNumber(anchorX, cardRect.left + inset, cardRect.right - inset) - size / 2;
      top = cardRect.bottom - size / 2;
    }

    const tail = document.createElement("div");
    tail.id = DICTIONARY_TAIL_ID;
    tail.setAttribute("aria-hidden", "true");
    Object.assign(tail.style, {
      position: "fixed",
      left: `${Math.round(left)}px`,
      top: `${Math.round(top)}px`,
      width: `${size}px`,
      height: `${size}px`,
      pointerEvents: "none",
      zIndex: "2147483646",
      border: "1px solid #e4e9f2",
      borderRadius: "5px 2px 5px 2px",
      background: "#ffffff",
      boxShadow: "0 10px 22px rgba(15, 23, 42, 0.08)",
      transform: "rotate(45deg)",
    });

    requirePageContainer().appendChild(tail);
  }

  function appendPopoverText(parent, tagName, className, text) {
    const element = document.createElement(tagName);
    element.className = className;
    element.textContent = text;
    parent.appendChild(element);
    return element;
  }

  function appendSvgNode(parent, tagName, attributes) {
    const node = document.createElementNS("http://www.w3.org/2000/svg", tagName);

    Object.entries(attributes).forEach(([name, value]) => {
      node.setAttribute(name, value);
    });

    parent.appendChild(node);
    return node;
  }

  function appendDictionarySpeakerIcon(parent) {
    const svg = appendSvgNode(parent, "svg", {
      width: "15",
      height: "15",
      viewBox: "0 0 15 15",
      fill: "none",
      "aria-hidden": "true",
    });
    appendSvgNode(svg, "path", {
      d: "M2 5H4.5L7.5 2.5v10L4.5 10H2V5z",
      fill: "currentColor",
    });
    appendSvgNode(svg, "path", {
      d: "M10 4a5 5 0 0 1 0 7",
      stroke: "currentColor",
      "stroke-width": "1.4",
      "stroke-linecap": "round",
    });
    appendSvgNode(svg, "path", {
      d: "M11.5 6a2.5 2.5 0 0 1 0 3",
      stroke: "currentColor",
      "stroke-width": "1.4",
      "stroke-linecap": "round",
    });
  }

  function appendDictionaryCloseIcon(parent) {
    const svg = appendSvgNode(parent, "svg", {
      width: "12",
      height: "12",
      viewBox: "0 0 12 12",
      fill: "none",
      "aria-hidden": "true",
    });
    appendSvgNode(svg, "path", {
      d: "M1.5 1.5l9 9M10.5 1.5l-9 9",
      stroke: "currentColor",
      "stroke-width": "1.8",
      "stroke-linecap": "round",
    });
  }

  function getDictionaryPartTheme(type) {
    const normalizedType = String(type || "").toLowerCase();

    if (normalizedType.includes("prefix")) {
      return {
        rowBackground: "#fff1f2",
        rowBorder: "#fda4af",
        badgeBackground: "#ffe4e6",
        badgeColor: "#e11d48",
      };
    }

    if (normalizedType.includes("root")) {
      return {
        rowBackground: "#eff6ff",
        rowBorder: "#93c5fd",
        badgeBackground: "#dbeafe",
        badgeColor: "#1d4ed8",
      };
    }

    if (normalizedType.includes("suffix")) {
      return {
        rowBackground: "#f0fdf4",
        rowBorder: "#86efac",
        badgeBackground: "#dcfce7",
        badgeColor: "#15803d",
      };
    }

    if (normalizedType.includes("infix")) {
      return {
        rowBackground: "#faf5ff",
        rowBorder: "#d8b4fe",
        badgeBackground: "#ede9fe",
        badgeColor: "#7c3aed",
      };
    }

    return {
      rowBackground: "transparent",
      rowBorder: "transparent",
      badgeBackground: "transparent",
      badgeColor: "#0f172a",
    };
  }

  function formatDictionaryPartType(type) {
    return String(type || "part")
      .trim()
      .split(/\s+/)
      .filter(Boolean)
      .map((word) => `${word.charAt(0).toUpperCase()}${word.slice(1)}`)
      .join(" ") || "Part";
  }

  function normalizeDictionaryWordParts(explanation) {
    if (Array.isArray(explanation?.wordParts) && explanation.wordParts.length > 0) {
      return explanation.wordParts.map((part) => {
        return {
          part: part?.part || part?.form || "",
          meaning: part?.meaning || "",
          type: part?.type || "Part",
        };
      }).filter((part) => part.part || part.meaning);
    }

    if (Array.isArray(explanation?.parts) && explanation.parts.length > 0) {
      return explanation.parts.map((part) => {
        const [wordPart, ...meaningParts] = String(part).split(":");

        return {
          part: wordPart.trim(),
          meaning: meaningParts.join(":").trim(),
          type: "Part",
        };
      }).filter((part) => part.part || part.meaning);
    }

    return [];
  }

  function appendDictionarySection(parent, heading, bodyText) {
    const section = document.createElement("section");
    Object.assign(section.style, {
      display: "grid",
      gap: "8px",
      padding: "14px 20px",
      borderBottom: "1px solid #f8fafc",
    });

    const title = appendPopoverText(section, "h3", "clearead-dictionary-section-title", heading);
    Object.assign(title.style, {
      margin: "0",
      color: "#94a3b8",
      fontSize: "10.5px",
      fontWeight: "800",
      lineHeight: "1.25",
      letterSpacing: "0.1em",
      textTransform: "uppercase",
    });

    if (bodyText) {
      const body = appendPopoverText(section, "p", "clearead-dictionary-section-body", bodyText);
      Object.assign(body.style, {
        margin: "0",
        color: "#1e293b",
        fontSize: "14.5px",
        lineHeight: "1.7",
      });
    }

    parent.appendChild(section);
    return section;
  }

  function appendDictionaryWordParts(parent, wordParts) {
    const section = appendDictionarySection(parent, "Word parts");
    const list = document.createElement("div");
    Object.assign(list.style, {
      display: "flex",
      flexDirection: "column",
      gap: "8px",
    });

    wordParts.forEach((wordPart) => {
      const theme = getDictionaryPartTheme(wordPart.type);
      const item = document.createElement("div");
      Object.assign(item.style, {
        display: "flex",
        alignItems: "center",
        gap: "10px",
        borderLeft: `3px solid ${theme.rowBorder}`,
        borderRadius: "10px",
        background: theme.rowBackground,
        padding: "9px 12px",
      });

      const partLabel = appendPopoverText(item, "span", "clearead-dictionary-part", wordPart.part);
      Object.assign(partLabel.style, {
        display: "inline-flex",
        alignItems: "center",
        flex: "0 1 86px",
        minWidth: "46px",
        maxWidth: "96px",
        color: "#0f172a",
        fontSize: "13px",
        fontWeight: "800",
        lineHeight: "1.2",
        overflowWrap: "anywhere",
      });

      const meaning = appendPopoverText(
        item,
        "span",
        "clearead-dictionary-part-meaning",
        wordPart.meaning || "No meaning returned."
      );
      Object.assign(meaning.style, {
        flex: "1 1 auto",
        minWidth: "0",
        color: "#475569",
        fontSize: "13px",
        lineHeight: "1.5",
        overflowWrap: "anywhere",
      });

      const typeBadge = appendPopoverText(
        item,
        "span",
        "clearead-dictionary-part-type",
        formatDictionaryPartType(wordPart.type)
      );
      Object.assign(typeBadge.style, {
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        flex: "0 0 auto",
        borderRadius: "999px",
        background: theme.badgeBackground,
        color: theme.badgeColor,
        fontSize: "10.5px",
        fontWeight: "800",
        lineHeight: "1.2",
        letterSpacing: "0.06em",
        padding: "3px 9px",
        textTransform: "uppercase",
        whiteSpace: "nowrap",
      });

      list.appendChild(item);
    });

    section.appendChild(list);
  }

  function appendDictionaryMessage(parent, text, color = "#94a3b8") {
    const message = appendPopoverText(parent, "p", "clearead-dictionary-message", text);
    Object.assign(message.style, {
      margin: "0",
      padding: "20px",
      color,
      fontSize: "13px",
      fontWeight: "600",
      lineHeight: "1.5",
    });

    return message;
  }

  function removeLastDictionarySectionBorder(parent) {
    const sections = parent.querySelectorAll("section");
    const lastSection = sections[sections.length - 1];

    if (lastSection) {
      lastSection.style.borderBottom = "0";
    }
  }

  function speakDictionaryTerm(term) {
    const speech = globalThis.speechSynthesis;

    if (!speech || !term) {
      return;
    }

    speech.cancel();
    const utterance = new SpeechSynthesisUtterance(term);
    utterance.rate = 0.86;
    utterance.pitch = 1;
    speech.speak(utterance);
  }

  function showDictionaryPopover(explanation) {
    removeDictionaryPopover();

    const popover = document.createElement("aside");
    popover.id = DICTIONARY_POPOVER_ID;
    popover.setAttribute("role", "dialog");
    popover.setAttribute("aria-label", "Clearead dictionary");
    Object.assign(popover.style, {
      position: "fixed",
      top: "12px",
      left: "12px",
      width: "min(340px, calc(100vw - 24px))",
      maxHeight: "min(460px, calc(100vh - 24px))",
      overflow: "hidden",
      zIndex: "2147483647",
      border: "1px solid #e2e8f0",
      borderRadius: "18px",
      background: "#ffffff",
      boxShadow:
        "0 4px 6px rgba(0, 0, 0, 0.04), 0 12px 40px rgba(0, 0, 0, 0.12), 0 2px 0 rgba(255, 255, 255, 0.8) inset",
      color: "#0f172a",
      fontFamily: "Arial, Verdana, Calibri, sans-serif",
      lineHeight: "1.45",
      padding: "0",
      visibility: "hidden",
    });

    const header = document.createElement("div");
    Object.assign(header.style, {
      display: "flex",
      alignItems: "center",
      gap: "8px",
      padding: "18px 18px 14px 20px",
      borderBottom: "1px solid #f1f5f9",
    });

    const term = appendPopoverText(
      header,
      "h2",
      "clearead-dictionary-term",
      explanation?.term || "Selected word"
    );
    Object.assign(term.style, {
      margin: "0",
      flex: "1 1 auto",
      minWidth: "0",
      color: "#0f172a",
      fontSize: "22px",
      fontWeight: "800",
      lineHeight: "1.15",
      letterSpacing: "0",
      overflowWrap: "anywhere",
    });

    const speakerButton = document.createElement("button");
    speakerButton.type = "button";
    speakerButton.setAttribute("aria-label", `Hear ${explanation?.term || "selected word"}`);
    appendDictionarySpeakerIcon(speakerButton);
    Object.assign(speakerButton.style, {
      display: explanation?.ok ? "inline-flex" : "none",
      alignItems: "center",
      justifyContent: "center",
      width: "32px",
      height: "32px",
      flex: "0 0 auto",
      border: "0",
      borderRadius: "999px",
      background: "transparent",
      color: "#6366f1",
      cursor: "pointer",
      padding: "0",
    });
    speakerButton.addEventListener("click", () => {
      speakDictionaryTerm(explanation?.term || "");
    });
    header.appendChild(term);
    header.appendChild(speakerButton);

    const closeButton = document.createElement("button");
    closeButton.type = "button";
    closeButton.setAttribute("aria-label", "Close Clearead dictionary");
    appendDictionaryCloseIcon(closeButton);
    Object.assign(closeButton.style, {
      display: "inline-flex",
      alignItems: "center",
      justifyContent: "center",
      width: "28px",
      height: "28px",
      flex: "0 0 auto",
      border: "0",
      borderRadius: "999px",
      background: "transparent",
      color: "#98a2b3",
      cursor: "pointer",
      padding: "0",
    });
    closeButton.addEventListener("click", () => {
      removeDictionaryPopover();
    });
    header.appendChild(closeButton);
    popover.appendChild(header);

    const body = document.createElement("div");
    Object.assign(body.style, {
      display: "flex",
      flexDirection: "column",
      maxHeight: "min(394px, calc(100vh - 90px))",
      overflowY: "auto",
    });
    popover.appendChild(body);

    if (explanation?.loading) {
      appendDictionaryMessage(body, explanation.message || "Looking up...");
    } else if (!explanation?.ok) {
      appendDictionaryMessage(
        body,
        explanation?.message || "Select one English word on the page, then try again.",
        "#475569"
      );
    } else if (explanation.hasResult === false) {
      appendDictionarySection(
        body,
        "Result",
        explanation.noResultMessage ||
          "No dictionary result was returned for this word. Try another word or use the full Clearead website."
      );
      removeLastDictionarySectionBorder(body);
    } else {
      const content = document.createElement("div");
      Object.assign(content.style, {
        display: "flex",
        flexDirection: "column",
      });

      appendDictionarySection(
        content,
        "Simple meaning",
        explanation.simpleMeaning || explanation.meaning || "No simple meaning was returned."
      );
      const wordParts = normalizeDictionaryWordParts(explanation);

      if (wordParts.length > 0) {
        appendDictionaryWordParts(content, wordParts);
      } else {
        appendDictionarySection(content, "Word parts", "No word parts were returned.");
      }

      appendDictionarySection(
        content,
        "Meaning from parts",
        explanation.meaningFromParts || "No word-part explanation was returned."
      );
      removeLastDictionarySectionBorder(content);
      body.appendChild(content);
    }

    requirePageContainer().appendChild(popover);
    placeDictionaryPopover(popover);
    popover.style.visibility = "visible";

    dictionaryOutsideClickHandler = (event) => {
      if (event.target?.closest?.(`#${DICTIONARY_POPOVER_ID}`)) {
        return;
      }

      removeDictionaryPopover();
    };
    document.addEventListener("pointerdown", dictionaryOutsideClickHandler, true);

    dictionaryKeydownHandler = (event) => {
      if (event.key === "Escape") {
        removeDictionaryPopover();
      }
    };
    document.addEventListener("keydown", dictionaryKeydownHandler, true);

    dictionaryRepositionHandler = () => {
      const currentPopover = document.getElementById(DICTIONARY_POPOVER_ID);

      if (currentPopover) {
        placeDictionaryPopover(currentPopover);
      }
    };
    globalThis.addEventListener("scroll", dictionaryRepositionHandler, {
      capture: true,
      passive: true,
    });
    globalThis.addEventListener("resize", dictionaryRepositionHandler, {
      capture: true,
      passive: true,
    });

    return {
      ok: true,
      message: "Dictionary card shown.",
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

    if (action === "show-dictionary-popover") {
      return showDictionaryPopover(message.explanation);
    }

    throw new Error("Unknown page tool.");
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
        message: error.message || "Page tools are unavailable here.",
      });
    }

    return true;
  }

  chrome.runtime.onMessage.addListener(handleCleareadPageToolMessage);

  globalThis[NAMESPACE] = {
    version: VERSION,
    destroy() {
      chrome.runtime.onMessage.removeListener(handleCleareadPageToolMessage);
      removeReadingRulerElement();
      removeReadableFontStyle();
      removeDictionaryPopover();
    },
    setReadableFont,
    setReadingRuler,
    getPageToolState,
    showDictionaryPopover,
  };
})();
