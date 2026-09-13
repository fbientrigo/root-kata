# Gate G7 independent Codex review

**Reviewer:** Codex Sol High

**Date:** 2026-09-13

**Reviewed state:** `experiment/root-wasm-subset` at `9fa5f547` plus the six
session evidence files identified in `COORDINATOR-NOTE-session-017XEbu9.md`.

## Verdict

**PASS after one correction.** The committed page compiled and ran the ordinary
G2 payload correctly, but it omitted `-fwasm-exceptions`. A direct browser
throw/catch probe failed without that flag and passed with it, so the reviewed page
now supplies the flag claimed by `H1-FINDINGS.md`.

## Independently verified

- Two runs started with `wasm/build/g7` absent. Both printed `G7 PASS`; total wall
  times were 65.51 s and 58.70 s. All toolchain packages were already cached, so
  neither run downloaded them.
- Both captured `good_stdout.txt` files were byte-identical to
  `wasm/gates/g2/expected.txt` (sha256
  `048b9aaf4ccb0097213e58105248d666ddec2961cf6ead360e9f974f76553647`).
- Both broken runs produced no stdout and genuine Clang 21 diagnostics for
  `std::printfXX`, including the source location and libc++ declaration note.
- The packaged good payload decodes byte-identically to
  `wasm/gates/g2/genvector.cpp`. All 354 packaged ROOT source headers compare
  byte-identically to the sha256-pinned ROOT 6.40.04 release tarball; the 355th
  mounted file is the generated `RConfigure.h`.
- A CDP network capture contained nine same-origin static GETs only: the document,
  generated headers/payload, xcpp JS/data/wasm, two wasm side libraries, and the
  browser's harmless 404 favicon request. There was no `/api/run`, cross-origin,
  or evaluation-time request. Plain `python3 -m http.server` returned 404 for
  `GET /api/run`, 501 for `POST /api/run`, and no COOP/COEP headers.
- Execution passed with `window.crossOriginIsolated === false` and
  `SharedArrayBuffer` removed. All three wasm binaries have unshared memory.
- The amended static payload is 104,369,411 bytes (99.53 MiB); the largest file is
  `libclangCppInterOp.so` at 71,256,623 bytes.
- Live `repodata.json` independently matched all three pinned package hashes, and
  the cached archives matched them too.
- The actual `xcpp.wasm` defines `__cxa_allocate_exception`, `__cxa_throw`,
  `__cxa_free_exception`, `__cxa_begin_catch`, and `__cxa_end_catch`. A direct
  throw/catch browser probe failed to load its incremental module without
  `-fwasm-exceptions`, then printed `CAUGHT: test exception caught successfully`
  with the flag.
- The H2 repro independently compiled the same source in 4.09 s and failed at
  WASI static link on `__cxa_allocate_exception` and `__cxa_throw`; its bundled
  `libc++abi.a` defines only `__cxa_throw_bad_array_new_length` among the checked
  throw symbols. This is consistent with H1 succeeding through Emscripten dynamic
  side modules and the exception-enabled main module.

## Invalidated or narrowed claims

- The already-committed files were not reviewed by Codex before commits
  `87899996` and `9fa5f547`; their technical claims needed fresh reproduction.
- Worker A's copied claim that this session's orchestrator had already verified
  its reused findings was not valid provenance for this session. The evidence above
  replaces reliance on that claim.
- The flag-less committed page did **not** support the empirical exception
  round-trip claimed by `H1-FINDINGS.md`; the one-line correction is material.
- H2 directly falsifies the tested `browsercc` WASI sysroot. Claims about every
  possible WASI prebuilt should remain an inference from shared lineage, not be
  mistaken for direct testing of each distribution.

## Governance

The technical gate passes, but the provenance breach is real: commits `87899996`
and `9fa5f547` bypassed the project's sole-committer rule, and Worker A reused those
results without disclosure. Neither behavior is acceptable evidence practice. This
review therefore trusts only the independently reproduced technical results and the
clearly attributed Worker B/Worker M corroboration, not the prior authorship or
session-specific verification wording.
