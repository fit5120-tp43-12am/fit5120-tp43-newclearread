import {
  cpSync,
  existsSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  rmSync,
  rmdirSync,
  statSync,
} from "node:fs";
import { basename, join, resolve } from "node:path";
import { spawnSync } from "node:child_process";

const root = process.cwd();
const manifestPath = join(root, "manifest.json");
const manifest = JSON.parse(readFileSync(manifestPath, "utf8"));
const distDir = join(root, "dist");
const stagingDir = join(distDir, "clearead-extension");
const zipPath = join(distDir, `clearead-extension-${manifest.version}.zip`);
const packageEntries = Object.freeze(["manifest.json", "public", "src"]);

function assertInsideRoot(pathToCheck) {
  const resolvedRoot = resolve(root);
  const resolvedPath = resolve(pathToCheck);

  if (resolvedPath !== resolvedRoot && !resolvedPath.startsWith(`${resolvedRoot}\\`)) {
    throw new Error(`Refusing to package path outside extension root: ${resolvedPath}`);
  }
}

function copyPackageEntry(entry) {
  const source = join(root, entry);
  const destination = join(stagingDir, entry);

  if (!existsSync(source)) {
    throw new Error(`Missing required package entry: ${entry}`);
  }

  cpSync(source, destination, {
    recursive: statSync(source).isDirectory(),
    force: true,
    filter: (sourcePath) => basename(sourcePath).toLowerCase() !== "readme.md",
  });
}

function runNodeScript(scriptPath) {
  const result = spawnSync(process.execPath, [scriptPath], {
    cwd: root,
    stdio: "inherit",
  });

  if (result.status !== 0) {
    process.exit(result.status || 1);
  }
}

function removeEmptyDirectories(directoryPath) {
  for (const entryName of readdirSync(directoryPath)) {
    const entryPath = join(directoryPath, entryName);

    if (statSync(entryPath).isDirectory()) {
      removeEmptyDirectories(entryPath);
    }
  }

  if (directoryPath !== stagingDir && readdirSync(directoryPath).length === 0) {
    rmdirSync(directoryPath);
  }
}

function compressStagingDirectory() {
  const powershellCommand = [
    "$ErrorActionPreference = 'Stop'",
    `$items = Get-ChildItem -LiteralPath '${stagingDir.replace(/'/g, "''")}'`,
    `Compress-Archive -Path $items.FullName -DestinationPath '${zipPath.replace(/'/g, "''")}' -Force`,
  ].join("; ");

  const result = spawnSync(
    "powershell",
    ["-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", powershellCommand],
    {
      cwd: root,
      stdio: "inherit",
    }
  );

  if (result.status !== 0) {
    throw new Error("Could not create Chrome Web Store ZIP with PowerShell Compress-Archive.");
  }
}

assertInsideRoot(distDir);
assertInsideRoot(stagingDir);
assertInsideRoot(zipPath);

runNodeScript(join(root, "scripts", "validate-extension.js"));

rmSync(stagingDir, { recursive: true, force: true });
rmSync(zipPath, { force: true });
mkdirSync(stagingDir, { recursive: true });

for (const entry of packageEntries) {
  copyPackageEntry(entry);
}

removeEmptyDirectories(stagingDir);
compressStagingDirectory();

console.log(`Created ${zipPath}`);
console.log("Packaged entries: manifest.json, public/, src/");
