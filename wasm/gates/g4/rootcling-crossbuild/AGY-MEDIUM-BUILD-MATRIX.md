# Agy Medium — bounded ROOT/Emscripten build-config matrix

Transcribed from the worker's terminal transcript (its `worker_done` delivery failed
because the Orca runtime was briefly unreachable; no file was written in its worktree,
so this is a reconstruction from the terminal record, not a file the worker itself
authored — reviewer should treat it as secondary to AGY-HIGH-A-REPORT.md / AGY-HIGH-B
and re-run the underlying commands if the exact evidence matters).

Toolchain: ROOT source 6.34.10 (its own checkout — not the G0-pinned 6.40.04), Emscripten
3.1.74, host build cache under `/home/fabian/.cache/rootwasm-th1d/`.

## Configurations tried (top-level ROOT CMake, all with Emscripten toolchain file)

| Config | Flags beyond `-Dminimal=ON` | Outcome | First blocker |
| --- | --- | --- | --- |
| `minimal-plain` | none | Bounded fail (180s cap) | Spends the full timeout building embedded LLVM (`-- Building LLVM in 'Release' mode.`) before any ROOT target compiles |
| `minimal-stripped` | GUI/X11/OpenGL/network/python/testing/examples/unrelated-math/fit disabled | Bounded fail (180s cap) | Same: reaches the same embedded-LLVM build path, still times out at 180s |
| `minimal-stripped-cc` | as above + explicit Emscripten `CC`/`CXX` | Bounded fail (180s cap, Exit status 124) | Same LLVM path; explicit compiler vars did not avoid it |
| `minimal-no-cling` | `-Dbuiltin_cling=OFF` (attempt to skip the embedded LLVM/Cling sub-build) | Fails fast (36.9s), `rc=1` | Missing external `llvm-config` — turning off the builtin LLVM/Cling build requires a system LLVM dev install that is not present on this host; no source patch attempted (per instructions) |
| `Hist` target dry-run against a pre-existing successful 6.34.10 wasm configure cache | n/a | Reaches ~25% of LLVM compilation before hitting the same 180s bound | `cmake --build ... --target Hist` pulls in the embedded LLVM/Cling build as a prerequisite even when only `Hist` is requested |

Full top-level configure (`root-wasm-build`) also independently hit the same install-export
blocker Agy High A found: `CMake Error: install(EXPORT "ROOTExports" ...) includes target
"RootAuth" which requires target "rsa" that is not in any export set.`

## Resource use

- Configure/partial-build cycles were bounded at 180s each by design (`timeout 180 cmake --build ...`).
- Disk growth for one partial `Hist` build attempt: ~41 MB (`before_kb=120772 after_kb=162780`).
- Host memory during the matrix run: `Mem: 7.6Gi total, 3.7Gi used, 137Mi free` / `Swap: 5.7Gi/7.9Gi used` — the host was already under heavy memory pressure from unrelated long-running sessions (see SESSION-NOTE.md).

## Key finding

Every "minimal" flag combination that keeps `builtin_cling=ON` (the default) still triggers
building the full embedded LLVM/Cling toolchain as part of configuring/building even a
single leaf target like `Hist` — none of `minimal=ON`, GUI/X11/OpenGL/network/python/
testing/examples-off, or unrelated-math/fit-off avoid this. The only way to skip it
(`-Dbuiltin_cling=OFF`) immediately fails because it then requires a **system** LLVM
(`llvm-config`) that was not installed on this host, and no such external LLVM was set up
or attempted (a system LLVM install was out of this task's bounded scope).

This is consistent with Agy High B's finding that stock ROOT's CMake does not model a
host-tool/target-library split: an all-Emscripten configure tries to build `rootcling`
itself as a wasm target (`rootcling.js`), and — per this matrix — also drags the full
LLVM/Cling build into the dependency graph of leaf library targets like `Hist`, even
though (per High B's source-level analysis) none of that LLVM/Cling/rootcling machinery
is actually required by the six-call `TH1D` API surface at runtime.

No ROOT source was patched. No config combination produced a fast, successful minimal
wasm configure within the bounded time; the repository was left clean (no files were
added to any worktree tracked by git for this worker).
