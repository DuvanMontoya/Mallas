import { readdir, stat } from "node:fs/promises";
import path from "node:path";
import process from "node:process";

const root = path.resolve(process.cwd(), ".next");
const chunkRoot = path.join(root, "static", "chunks");

async function filesUnder(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const fullPath = path.join(directory, entry.name);
    if (entry.isDirectory()) files.push(...(await filesUnder(fullPath)));
    else if (/\.(?:js|css)$/.test(entry.name)) files.push(fullPath);
  }
  return files;
}

try {
  const files = await filesUnder(chunkRoot);
  const chunks = await Promise.all(
    files.map(async (file) => ({
      file: path.relative(chunkRoot, file).replaceAll("\\", "/"),
      bytes: (await stat(file)).size,
    })),
  );
  chunks.sort((left, right) => right.bytes - left.bytes);
  const totalBytes = chunks.reduce((sum, chunk) => sum + chunk.bytes, 0);
  console.log(`bundle_chunks=${chunks.length} total_kb=${(totalBytes / 1024).toFixed(1)}`);
  for (const chunk of chunks.slice(0, 10)) {
    console.log(`chunk=${chunk.file} kb=${(chunk.bytes / 1024).toFixed(1)}`);
  }
  console.log(
    "graph_loading=dynamic:ssr-false " +
      "source=components/dependency-graph-shell.tsx " +
      "note=React-Flow-and-ELK-are-route-scoped",
  );
} catch (error) {
  console.error(`bundle_audit_failed=${error instanceof Error ? error.message : String(error)}`);
  process.exitCode = 1;
}
