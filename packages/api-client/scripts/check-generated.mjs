import { existsSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import openapiTS, { astToString, COMMENT_HEADER } from "openapi-typescript";

const schema = fileURLToPath(new URL("../../../artifacts/openapi.json", import.meta.url));
const generated = fileURLToPath(new URL("../src/generated.ts", import.meta.url));
if (!existsSync(generated)) {
  console.error(`Missing generated client: ${generated}`);
  process.exit(1);
}
if (!existsSync(schema)) {
  console.error(`Missing OpenAPI schema: ${schema}`);
  process.exit(1);
}

const source = readFileSync(generated, "utf8");
const schemaDocument = JSON.parse(readFileSync(schema, "utf8"));
const expected = `${COMMENT_HEADER}${astToString(await openapiTS(schemaDocument, { silent: true }))}`;
if (source !== expected) {
  console.error("Generated API client is stale; run pnpm generate.");
  process.exit(1);
}
console.log("Generated API client matches the checked-in OpenAPI schema.");
