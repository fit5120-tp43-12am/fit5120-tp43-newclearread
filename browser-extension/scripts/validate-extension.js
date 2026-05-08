import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

const root = process.cwd();
const manifestPath = join(root, "manifest.json");
const manifest = JSON.parse(readFileSync(manifestPath, "utf8"));
const errors = [];

function requireValue(condition, message) {
  if (!condition) {
    errors.push(message);
  }
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
  Array.isArray(manifest.permissions) &&
    manifest.permissions.length === 1 &&
    manifest.permissions[0] === "sidePanel",
  "Only the sidePanel permission should be requested in Phase 1."
);
requireValue(!manifest.host_permissions, "Phase 1 must not request host_permissions.");
requireValue(!manifest.content_scripts, "Phase 1 must not register content scripts.");
requireValue(!manifest.action?.default_popup, "Phase 1 must not register a popup.");

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

if (errors.length > 0) {
  console.error("Extension validation failed:");
  for (const error of errors) {
    console.error(`- ${error}`);
  }
  process.exit(1);
}

console.log("Extension validation passed.");
