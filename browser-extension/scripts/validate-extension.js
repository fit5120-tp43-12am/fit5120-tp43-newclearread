import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { extname, join, relative } from "node:path";

const root = process.cwd();
const manifestPath = join(root, "manifest.json");
const manifest = JSON.parse(readFileSync(manifestPath, "utf8"));
const errors = [];
const allowedPermissions = new Set([
  "sidePanel",
  "activeTab",
  "scripting",
  "contextMenus",
  "storage",
]);
const allowedHostPermissions = new Set([
  "https://clear-read-a3c2gyajcjf5agfd.australiaeast-01.azurewebsites.net/*",
]);
const allowedPopupPath = "src/popup/popup.html";
const requiredIconPaths = Object.freeze({
  "16": "public/icons/icon-16.png",
  "32": "public/icons/icon-32.png",
  "48": "public/icons/icon-48.png",
  "128": "public/icons/icon-128.png",
});
const requiredFontPaths = Object.freeze([
  "public/fonts/OpenDyslexic-Regular.woff2",
  "public/fonts/OpenDyslexic-Bold.woff2",
  "public/fonts/OpenDyslexic-Italic.woff2",
  "public/fonts/OpenDyslexic-BoldItalic.woff2",
]);
const sourceFileExtensionsToScan = new Set([".css", ".html", ".js"]);
const forbiddenSourcePatterns = Object.freeze([
  {
    pattern: /\b(?:innerHTML|outerHTML|insertAdjacentHTML)\b/,
    message: "Avoid HTML string injection APIs in extension source.",
  },
  {
    pattern: /\beval\s*\(/,
    message: "eval() is blocked in extension source.",
  },
  {
    pattern: /\bnew\s+Function\b/,
    message: "new Function() is blocked in extension source.",
  },
  {
    pattern: /\blocalStorage\b/,
    message: "localStorage must not be used for extension data.",
  },
  {
    pattern: /\bchrome\.storage\.(?:local|sync)\b/,
    message: "Only chrome.storage.session is allowed for current extension state.",
  },
  {
    pattern: /<script[^>]+src=["']https?:\/\//i,
    message: "Remote script tags are blocked.",
  },
  {
    pattern: /https?:\/\/[^\s"'<>]+\.js\b/i,
    message: "Remote JavaScript URLs are blocked.",
  },
  {
    pattern: /@import\s+(?:url\()?["']?https?:\/\//i,
    message: "Remote CSS imports are blocked.",
  },
  {
    pattern: /url\(["']?https?:\/\//i,
    message: "Remote CSS assets are blocked in packaged extension UI.",
  },
  {
    pattern: /\b(?:api[_-]?key|access[_-]?token|secret|password)\b/i,
    message: "Credential-like names must not appear in packaged extension source.",
  },
]);

function requireValue(condition, message) {
  if (!condition) {
    errors.push(message);
  }
}

function toRelativePath(filePath) {
  return relative(root, filePath).replace(/\\/g, "/");
}

function collectSourceFiles(directoryPath) {
  if (!existsSync(directoryPath)) {
    return [];
  }

  const files = [];

  for (const entryName of readdirSync(directoryPath)) {
    const entryPath = join(directoryPath, entryName);
    const stats = statSync(entryPath);

    if (stats.isDirectory()) {
      files.push(...collectSourceFiles(entryPath));
      continue;
    }

    if (stats.isFile() && sourceFileExtensionsToScan.has(extname(entryPath))) {
      files.push(toRelativePath(entryPath));
    }
  }

  return files.sort();
}

function extractStringConst(source, constName) {
  const match = source.match(new RegExp(`const\\s+${constName}\\s*=\\s*["']([^"']+)["']`));
  return match?.[1] || "";
}

function extractExportedStringConst(source, constName) {
  const match = source.match(new RegExp(`export\\s+const\\s+${constName}\\s*=\\s*["']([^"']+)["']`));
  return match?.[1] || "";
}

function extractNumberConst(source, constName) {
  const match = source.match(new RegExp(`const\\s+${constName}\\s*=\\s*(\\d+)`));
  return match ? Number.parseInt(match[1], 10) : null;
}

function extractExportedNumberConst(source, constName) {
  const match = source.match(new RegExp(`export\\s+const\\s+${constName}\\s*=\\s*(\\d+)`));
  return match ? Number.parseInt(match[1], 10) : null;
}

function isBroadHostPermission(pattern) {
  return (
    pattern === "<all_urls>" ||
    pattern === "*://*/*" ||
    pattern === "http://*/*" ||
    pattern === "https://*/*" ||
    pattern.includes("*://") ||
    pattern.includes("://*.")
  );
}

function getPngDimensions(filePath) {
  const png = readFileSync(filePath);
  const pngSignature = "89504e470d0a1a0a";

  if (png.length < 24 || png.subarray(0, 8).toString("hex") !== pngSignature) {
    return null;
  }

  return {
    width: png.readUInt32BE(16),
    height: png.readUInt32BE(20),
  };
}

function isWoff2File(filePath) {
  const font = readFileSync(filePath);
  return font.length > 4 && font.subarray(0, 4).toString("utf8") === "wOF2";
}

function requireIconSet(iconSet, label) {
  requireValue(iconSet && typeof iconSet === "object", `${label} must be defined.`);

  if (!iconSet || typeof iconSet !== "object") {
    return;
  }

  for (const [size, expectedPath] of Object.entries(requiredIconPaths)) {
    requireValue(
      iconSet[size] === expectedPath,
      `${label}.${size} must be ${expectedPath}.`
    );

    const iconPath = join(root, expectedPath);
    if (!existsSync(iconPath)) {
      requireValue(false, `${expectedPath} must exist.`);
      continue;
    }

    const dimensions = getPngDimensions(iconPath);
    requireValue(
      dimensions?.width === Number(size) && dimensions?.height === Number(size),
      `${expectedPath} must be a ${size}x${size} PNG.`
    );
  }
}

function requireOpenDyslexicFonts() {
  for (const fontPath of requiredFontPaths) {
    const absolutePath = join(root, fontPath);
    requireValue(existsSync(absolutePath), `${fontPath} must exist.`);

    if (existsSync(absolutePath)) {
      requireValue(isWoff2File(absolutePath), `${fontPath} must be a WOFF2 font.`);
    }
  }

  requireValue(
    existsSync(join(root, "public", "fonts", "OFL.txt")),
    "The OpenDyslexic SIL OFL license file must be included."
  );
}

function requireFontWebAccessibleResources() {
  const resources = manifest.web_accessible_resources;

  requireValue(
    Array.isArray(resources),
    "OpenDyslexic font files must be declared in web_accessible_resources."
  );

  if (!Array.isArray(resources)) {
    return;
  }

  const fontResourceBlocks = resources.filter((entry) => {
    return requiredFontPaths.every((fontPath) => entry.resources?.includes(fontPath));
  });

  requireValue(
    fontResourceBlocks.length === 1,
    "OpenDyslexic fonts must be declared in exactly one web_accessible_resources entry."
  );

  if (fontResourceBlocks.length !== 1) {
    return;
  }

  const [fontResourceBlock] = fontResourceBlocks;
  const unexpectedResources = fontResourceBlock.resources.filter((resource) => {
    return !requiredFontPaths.includes(resource);
  });

  requireValue(
    unexpectedResources.length === 0,
    `Only OpenDyslexic font files should be web-accessible: ${unexpectedResources.join(", ")}`
  );
  requireValue(
    fontResourceBlock.matches?.includes("http://*/*") &&
      fontResourceBlock.matches?.includes("https://*/*"),
    "OpenDyslexic web-accessible font resources must match normal http and https webpages."
  );
}

function validateSourceFile(filePath) {
  const absolutePath = join(root, filePath);

  requireValue(existsSync(absolutePath), `${filePath} must exist.`);

  if (!existsSync(absolutePath)) {
    return;
  }

  const source = readFileSync(absolutePath, "utf8");

  for (const { pattern, message } of forbiddenSourcePatterns) {
    requireValue(!pattern.test(source), `${filePath}: ${message}`);
  }
}

function validateSharedConstants() {
  const sharedConfigPath = join(root, "src", "shared", "config.js");
  const serviceWorkerPath = join(root, "src", "background", "service-worker.js");
  const localDictionaryPath = join(root, "src", "services", "local-dictionary.js");
  const sidePanelHtmlPath = join(root, "src", "sidepanel", "sidepanel.html");

  if (
    !existsSync(sharedConfigPath) ||
    !existsSync(serviceWorkerPath) ||
    !existsSync(localDictionaryPath) ||
    !existsSync(sidePanelHtmlPath)
  ) {
    return;
  }

  const sharedConfigSource = readFileSync(sharedConfigPath, "utf8");
  const serviceWorkerSource = readFileSync(serviceWorkerPath, "utf8");
  const localDictionarySource = readFileSync(localDictionaryPath, "utf8");
  const sidePanelHtml = readFileSync(sidePanelHtmlPath, "utf8");

  const sharedBackendUrl = extractExportedStringConst(
    sharedConfigSource,
    "BACKEND_API_BASE_URL"
  );
  const serviceWorkerBackendUrl = extractStringConst(
    serviceWorkerSource,
    "BACKEND_API_BASE_URL"
  );

  requireValue(
    sharedBackendUrl && sharedBackendUrl === serviceWorkerBackendUrl,
    "The side panel and background service worker must use the same backend base URL."
  );

  const localDictionaryMax = extractNumberConst(
    localDictionarySource,
    "MAX_LOOKUP_TERM_CHARS"
  );
  const serviceWorkerDictionaryMax = extractNumberConst(
    serviceWorkerSource,
    "MAX_LOOKUP_TERM_CHARS"
  );
  const dictionaryInputMax = Number.parseInt(
    sidePanelHtml.match(/id="dictionary-term"[\s\S]*?maxlength="(\d+)"/)?.[1] || "",
    10
  );

  requireValue(
    Number.isInteger(localDictionaryMax) &&
      localDictionaryMax === serviceWorkerDictionaryMax &&
      localDictionaryMax === dictionaryInputMax,
    "Dictionary word length limits must match in local validation, service worker, and side panel input."
  );

  const maxSummaryChars = extractExportedNumberConst(sharedConfigSource, "MAX_TEXT_CHARS");
  const summaryInputMax = Number.parseInt(
    sidePanelHtml.match(/id="source-text"[\s\S]*?maxlength="(\d+)"/)?.[1] || "",
    10
  );

  requireValue(
    Number.isInteger(maxSummaryChars) && maxSummaryChars === summaryInputMax,
    "Summary text length limit must match shared config and side panel input."
  );
}

requireValue(manifest.manifest_version === 3, "manifest_version must be 3.");
requireValue(manifest.name, "manifest.name is required.");
requireValue(manifest.version, "manifest.version is required.");
requireValue(
  Number.parseInt(manifest.minimum_chrome_version, 10) >= 116,
  "minimum_chrome_version must be 116 or newer because the popup uses chrome.sidePanel.open()."
);
requireValue(
  manifest.side_panel?.default_path,
  "manifest.side_panel.default_path is required."
);
requireValue(
  manifest.action?.default_popup === allowedPopupPath,
  `manifest.action.default_popup must be ${allowedPopupPath}.`
);
requireIconSet(manifest.icons, "manifest.icons");
requireIconSet(manifest.action?.default_icon, "manifest.action.default_icon");
requireOpenDyslexicFonts();
requireFontWebAccessibleResources();
requireValue(
  manifest.background?.service_worker,
  "manifest.background.service_worker is required for popup-triggered side panel behavior."
);
requireValue(
  Array.isArray(manifest.permissions),
  "manifest.permissions must be an array."
);
if (Array.isArray(manifest.permissions)) {
  for (const permission of manifest.permissions) {
    requireValue(
      allowedPermissions.has(permission),
      `Unexpected extension permission requested: ${permission}.`
    );
  }
  requireValue(
    manifest.permissions.includes("sidePanel"),
    "The sidePanel permission is required."
  );
  requireValue(
    manifest.permissions.includes("activeTab"),
    "The activeTab permission is required for user-triggered page tools."
  );
  requireValue(
    manifest.permissions.includes("scripting"),
    "The scripting permission is required for programmatic page-tool injection."
  );
  requireValue(
    manifest.permissions.includes("contextMenus"),
    "The contextMenus permission is required for the right-click dictionary flow."
  );
  requireValue(
    manifest.permissions.includes("storage"),
    "The storage permission is required for session-only right-click dictionary enablement."
  );
}

requireValue(
  Array.isArray(manifest.host_permissions),
  "manifest.host_permissions must be an array."
);
if (Array.isArray(manifest.host_permissions)) {
  requireValue(
    manifest.host_permissions.length === allowedHostPermissions.size,
    "Only the deployed Clearead backend host permission should be requested."
  );

  for (const permission of manifest.host_permissions) {
    requireValue(
      !isBroadHostPermission(permission),
      `Broad host permission is blocked: ${permission}.`
    );
    requireValue(
      allowedHostPermissions.has(permission),
      `Only the deployed Clearead backend host permission is allowed: ${permission}.`
    );
  }
}
requireValue(!manifest.content_scripts, "Static content scripts must not be registered.");

if (manifest.side_panel?.default_path) {
  requireValue(
    existsSync(join(root, manifest.side_panel.default_path)),
    "The configured side panel file must exist."
  );
}

if (manifest.action?.default_popup) {
  requireValue(
    existsSync(join(root, manifest.action.default_popup)),
    "The configured popup file must exist."
  );
}

if (manifest.background?.service_worker) {
  const backgroundServiceWorkerPath = join(root, manifest.background.service_worker);

  requireValue(
    existsSync(backgroundServiceWorkerPath),
    "The configured background service worker must exist."
  );

  if (existsSync(backgroundServiceWorkerPath)) {
    const backgroundServiceWorkerSource = readFileSync(backgroundServiceWorkerPath, "utf8");

    requireValue(
      !/^\s*import\s/m.test(backgroundServiceWorkerSource),
      "The background service worker must stay classic and avoid static import statements."
    );
    requireValue(
      !/^\s*export\s/m.test(backgroundServiceWorkerSource),
      "The background service worker must stay classic and avoid export statements."
    );
  }
}

requireValue(
  existsSync(join(root, "src", "shared", "config.js")),
  "The side panel backend config module must exist."
);
requireValue(
  existsSync(join(root, "src", "services", "backend-api.js")),
  "The side panel backend API service module must exist."
);
requireValue(
  existsSync(join(root, "src", "services", "local-dictionary.js")),
  "The dictionary input validation module must exist."
);
requireValue(
  existsSync(join(root, "src", "content", "page-tools.js")),
  "The programmatically injected page tools content file must exist."
);
requireValue(
  existsSync(join(root, "src", "popup", "popup.js")),
  "The popup activation script must exist."
);

const sourceFilesToScan = collectSourceFiles(join(root, "src"));
requireValue(sourceFilesToScan.length > 0, "Extension source files must be present.");

for (const sourceFile of sourceFilesToScan) {
  validateSourceFile(sourceFile);
}

validateSharedConstants();

if (errors.length > 0) {
  console.error("Extension validation failed:");
  for (const error of errors) {
    console.error(`- ${error}`);
  }
  process.exit(1);
}

console.log("Extension validation passed.");
