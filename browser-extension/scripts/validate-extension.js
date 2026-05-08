import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

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

function requireValue(condition, message) {
  if (!condition) {
    errors.push(message);
  }
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
      `Broad host permission is not allowed: ${permission}.`
    );
    requireValue(
      allowedHostPermissions.has(permission),
      `Only the deployed Clearead backend host permission is allowed in Phase 7: ${permission}.`
    );
  }
}
requireValue(!manifest.content_scripts, "Phase 7 must not register static content scripts.");

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
  "The local selected-word dictionary service module must exist."
);
requireValue(
  existsSync(join(root, "src", "content", "page-tools.js")),
  "The programmatically injected page tools content file must exist."
);
requireValue(
  existsSync(join(root, "src", "popup", "popup.js")),
  "The popup activation script must exist."
);

if (errors.length > 0) {
  console.error("Extension validation failed:");
  for (const error of errors) {
    console.error(`- ${error}`);
  }
  process.exit(1);
}

console.log("Extension validation passed.");
