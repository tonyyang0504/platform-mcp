// npm pack/publish: copy the repository's catalog (and the licence files) into the package, then remove the copies.
// The catalog is the single source in <repo>/catalog; the published package carries a snapshot of it.
import { cpSync, existsSync, rmSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const pkg = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const repo = resolve(pkg, "..", "..");
const copies = [["catalog", "catalog"], ["LICENSE", "LICENSE"], ["NOTICE", "NOTICE"]];
if (process.argv[2] === "copy") {
  for (const [from, to] of copies) {
    rmSync(join(pkg, to), { recursive: true, force: true });
    cpSync(join(repo, from), join(pkg, to), { recursive: true, filter: (src) => !src.includes(`${join(repo, "catalog", "sources")}`) });
  }
  if (!existsSync(join(pkg, "catalog", "schema", "vocab.json"))) throw new Error("catalog copy failed");
} else if (process.argv[2] === "clean") {
  for (const [, to] of copies) rmSync(join(pkg, to), { recursive: true, force: true });
} else {
  console.error("usage: node scripts/pack-catalog.mjs copy|clean");
  process.exit(2);
}
