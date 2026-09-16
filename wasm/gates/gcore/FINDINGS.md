# GCORE — genuine ROOT Core WebAssembly side-module probe

> **RETIRED — diagnostic evidence only.** This manual Core source slice is not an
> implementation path. M1 supersedes it with ROOT's own CMake target closure; keep this
> directory only because historical reviews cite its evidence.

## Verdict: BLOCKED-AT-RUNTIME-IMPORT

The pinned Emscripten `4.0.9` compiler builds unmodified ROOT `6.40.04` Core
sources and links them into one `-sSIDE_MODULE=1` module. Chromium loads and
executes the independent dynamic-loader control (`control=42`). The Core slice
does not load: its first remaining import is the Emscripten-runtime symbol
`getrandom`.

```
Error: Dynamic linking error: cannot resolve symbol getrandom
```

This is not a ROOT source or a Core dictionary symbol. It comes from the real
`core/base/src/RCryptoRandom.cxx`: `TUUID::UUIDv4()` calls
`ROOT::Internal::GetCryptoRandom`, and ROOT's `core/base/CMakeLists.txt:322-326`
selects its `getrandom` implementation when available. Emscripten's headers
provide the declaration, but xeus-cpp-lite's browser dynamic-link runtime does
not export the function. A shim would be new behavior, so it is outside this
gate's source-only closure rule.

## Reproduction and retained evidence

```bash
bash wasm/gates/gcore/run.sh
```

The script cleans `wasm/build/gcore`, verifies the pinned source/toolchain,
generates both `RConfigure.h` and `RConfigOptions.h` from ROOT templates,
compiles the ordered source manifest, and records:

| Artifact | Purpose |
| --- | --- |
| `core-sources.tsv` | Ordered upstream source list and the observed-symbol citation for every post-baseline addition. |
| `hashes.txt` | SHA-256 of generated headers, objects, manifest, and both side modules. |
| `undefined-symbols.txt` | Raw undefined object references. |
| `core.json` / `control.json` | Raw Chromium diagnostics and control result. |
| `classification.json` | Loader classification, exact diagnostic, module sizes, and object-reference counts. |

The observed clean run produced a `316847`-byte Core module (`93507` bytes at
gzip-9), a successful `control=42`, and `module-load-failure` at `getrandom`.
The old `TVersionCheck` include failure is not reached because the module
cannot load.

The same run also passes the static-host checks: static-only requests, no
compile backend, no COOP/COEP or `SharedArrayBuffer`, and no shared wasm
memory. It deliberately exits non-zero after preserving that evidence, because
Core was not loaded before the unchanged `#include <TH1D.h>` probe.

## Boundary

Do not add Hist, MathCore, Matrix, RIO, Thread, TH1D, or a hand-written entropy
shim here. A future step needs an evidence-backed way for the browser runtime
to provide `getrandom` (or an upstream ROOT browser configuration path) before
this Core-only closure can continue. `rootcling` is not implicated: no
Core-dictionary symbol has been observed.
