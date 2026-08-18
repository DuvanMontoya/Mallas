import { cpSync, existsSync, mkdirSync, readdirSync } from "node:fs";
import { resolve } from "node:path";

const sourceRoot = resolve(".next");
const standaloneRoot = resolve(".next/standalone/apps/web");
const tracedPnpmRoot = resolve(".next/standalone/node_modules/.pnpm");
const workspacePnpmRoot = resolve("../../node_modules/.pnpm");

if (!existsSync(resolve(sourceRoot, "standalone"))) {
  throw new Error("Next standalone output was not generated.");
}

const staticSource = resolve(sourceRoot, "static");
const staticTarget = resolve(standaloneRoot, ".next/static");
mkdirSync(staticTarget, { recursive: true });
cpSync(staticSource, staticTarget, { recursive: true, force: true });

const publicSource = resolve("public");
if (existsSync(publicSource)) {
  cpSync(publicSource, resolve(standaloneRoot, "public"), { recursive: true, force: true });
}

// Next's output-file tracer currently copies only the CommonJS entrypoints of
// @swc/helpers with pnpm, while the standalone server imports its ESM helpers.
// Complete the exact traced package version instead of pinning a version here.
const tracedSwcHelpers = readdirSync(tracedPnpmRoot).filter((name) =>
  name.startsWith("@swc+helpers@"),
);
if (tracedSwcHelpers.length === 0) {
  throw new Error("Next standalone output did not trace @swc/helpers.");
}
for (const packageDirectory of tracedSwcHelpers) {
  const source = resolve(
    workspacePnpmRoot,
    packageDirectory,
    "node_modules/@swc/helpers",
  );
  const target = resolve(
    tracedPnpmRoot,
    packageDirectory,
    "node_modules/@swc/helpers",
  );
  if (!existsSync(source)) {
    throw new Error(`The traced ${packageDirectory} package is missing from the workspace.`);
  }
  cpSync(source, target, { recursive: true, force: true, dereference: true });
}

console.log("Prepared Next standalone runtime assets.");
