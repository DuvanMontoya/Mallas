import { cpSync, existsSync, mkdirSync } from "node:fs";
import { resolve } from "node:path";

const sourceRoot = resolve(".next");
const standaloneRoot = resolve(".next/standalone/apps/web");

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

console.log("Prepared Next standalone runtime assets.");
