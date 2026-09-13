// H2 (Gate G7) repro: try to compile wasm/gates/g2/genvector.cpp against real
// pinned ROOT 6.40.04 GenVector/MathCore/Core headers using `browsercc`
// (npm, clang 20.1.2 + lld, both themselves compiled to wasm32-wasi), run
// entirely in Node so it can be iterated without a browser.
//
// This is NOT wired into a run.sh: the hypothesis was falsified (see
// ../H2-FINDINGS.md), so there is deliberately no passing gate here. This
// file exists only so the finding is independently reproducible.
//
// Usage:
//   cd wasm/gates/g7/repro && npm install
//   node compile-genvector.mjs [--flags="-std=c++17,-O2"]
//
// Requires: wasm/toolchain/fetch-root-src.sh already run (pinned ROOT source
// cached under ~/.root-kata-wasm/src/root-6.40.04), and
// wasm/gates/g2/rconfigure.cmake run once against the pinned host em++ to
// produce an RConfigure.h (see H2-FINDINGS.md step 2 for the exact command;
// this script expects the result at $RCONFIG_DIR/RConfigure.h, default
// wasm/build/g7/RConfigure.h relative to the repo root).

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(HERE, "../../../..");
const ROOT_WASM_TOOLS = process.env.ROOT_WASM_TOOLS || path.join(process.env.HOME, ".root-kata-wasm");
const ROOT_SRC = path.join(ROOT_WASM_TOOLS, "src/root-6.40.04");
const RCONFIG_DIR = process.env.RCONFIG_DIR || path.join(REPO_ROOT, "wasm/build/g7");
const GENVECTOR_CPP = path.join(REPO_ROOT, "wasm/gates/g2/genvector.cpp");

const INCLUDE_DIRS = [
  "math/genvector/inc",
  "math/mathcore/inc",
  "core/foundation/inc",
  "core/base/inc",
];

// browsercc's `compile()` does `fetch(new URL("sysroot.tar", import.meta.url))`,
// which resolves to a file:// URL when running from node_modules on disk.
// Node's fetch doesn't implement file://, so shim it -- this is a Node-only
// test-harness concern, not something the real (page-served-over-http) G7
// deliverable would need.
const nativeFetch = globalThis.fetch.bind(globalThis);
globalThis.fetch = async (url, ...rest) => {
  const href = typeof url === "string" ? url : url.href;
  if (href.startsWith("file://")) {
    return new Response(fs.readFileSync(fileURLToPath(href)));
  }
  return nativeFetch(url, ...rest);
};

const { compile } = await import("browsercc");

function walk(dir, base, out) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) walk(full, base, out);
    else if (entry.isFile()) out.push(path.relative(base, full));
  }
}

const extraFiles = {};
for (const inc of INCLUDE_DIRS) {
  const absBase = path.join(ROOT_SRC, inc);
  const rels = [];
  walk(absBase, absBase, rels);
  for (const rel of rels) {
    extraFiles[`/root-src/${inc}/${rel}`] = fs.readFileSync(path.join(absBase, rel), "utf-8");
  }
}
extraFiles["/root-src/rconfig/RConfigure.h"] = fs.readFileSync(
  path.join(RCONFIG_DIR, "RConfigure.h"),
  "utf-8",
);

const argFlags = process.argv.find((a) => a.startsWith("--flags="));
const extraFlags = argFlags ? argFlags.slice("--flags=".length).split(",") : [];

const flags = [
  "-std=c++17",
  "-O2",
  ...extraFlags,
  "-I/root-src/rconfig",
  ...INCLUDE_DIRS.map((d) => `-I/root-src/${d}`),
];

console.error("flags:", flags.join(" "));
const t0 = Date.now();
const { compileOutput, module } = await compile({
  source: fs.readFileSync(GENVECTOR_CPP, "utf-8"),
  fileName: "genvector.cpp",
  flags,
  extraFiles,
});
console.error(`compile+link: ${Date.now() - t0}ms`);
console.error(compileOutput || "(no compiler/linker output)");
process.exit(module ? 0 : 1);
