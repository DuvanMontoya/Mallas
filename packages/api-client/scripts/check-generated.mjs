import { existsSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const schema = fileURLToPath(new URL("../../../artifacts/openapi.json", import.meta.url));
const generated = fileURLToPath(new URL("../src/generated.ts", import.meta.url));
if (!existsSync(generated)) {
  console.error(`Missing generated client: ${generated}`);
  process.exit(1);
}
if (existsSync(schema)) {
  const source = readFileSync(generated, "utf8");
  if (!source.includes("export interface paths")) {
    console.error("Generated client does not contain the expected OpenAPI paths type.");
    process.exit(1);
  }
}
console.log("Generated API client is present.");
