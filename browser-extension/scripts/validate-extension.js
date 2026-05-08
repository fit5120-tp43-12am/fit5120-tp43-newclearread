import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

const root = process.cwd();
const manifestPath = join(root, "manifest.json");
const manifest = JSON.parse(readFileSync(manifestPath, "utf8"));
const errors = [];
const allowedPermissions = new Set(["sidePanel"]);
const allowedHostPermissions = new Set([
  "https://clear-read-a3c2gyajcjf5agfd.australiaeast-01.azurewebsites.net/*",
]);

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

requireValue(manifest.manifest_version === 3, "manifest_version must be 3.");
requireValue(manifest.name, "manifest.name is required.");
requireValue(manifest.version, "manifest.version is required.");
requireValue(
  manifest.side_panel?.default_path,
  "manifest.side_panel.default_path is required."
);
requireValue(
  manifest.background?.service_worker,
  "manifest.background.service_worker is required for action-click side panel behavior."
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
      `Only the deployed Clearead backend host permission is allowed in Phase 3: ${permission}.`
    );
  }
}
requireValue(!manifest.content_scripts, "Phase 3 must not register content scripts.");
requireValue(!manifest.action?.default_popup, "Phase 3 must not register a popup.");

if (manifest.side_panel?.default_path) {
  requireValue(
    existsSync(join(root, manifest.side_panel.default_path)),
    "The configured side panel file must exist."
  );
}

if (manifest.background?.service_worker) {
  requireValue(
    existsSync(join(root, manifest.background.service_worker)),
    "The configured background service worker must exist."
  );
}

requireValue(
  existsSync(join(root, "src", "shared", "config.js")),
  "The side panel backend config module must exist."
);
requireValue(
  existsSync(join(root, "src", "services", "backend-api.js")),
  "The side panel backend API service module must exist."
);

if (errors.length > 0) {
  console.error("Extension validation failed:");
  for (const error of errors) {
    console.error(`- ${error}`);
  }
  process.exit(1);
}

console.log("Extension validation passed.");
