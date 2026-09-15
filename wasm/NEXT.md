# NEXT — one objective for the next session

## Objective

Run one bounded **Core dictionary generation-and-compile probe** with the
already installed native rootcling and the complete Emscripten wasm32 target
include/ABI environment. Use pinned ROOT 6.40.04 and Emscripten 4.0.9; label the
installed 6.40.02 generator as version-mismatched diagnostic evidence.

## Why this is next

The P0 dependency session retained ROOT's own Core/Hist CMake targets and
removed target LLVM/Cling from their build-order closures with a CMake-only
host-tool patch. Core stopped at `G__Core.cxx`: the host generator emitted
libstdc++-private types that target libc++ cannot compile. The partial libc++
retry omitted musl includes and crashed; it did not close all native generator
routes. The independent review also invalidated the assumed ordinary ROOT PCH
attachment in rootcling mode. See
[gates/p0deps/CODEX-REVIEW.md](gates/p0deps/CODEX-REVIEW.md).

## Concrete next experiment

Extract the existing generated G__Core rootcling command from the xbuild cache
into a fresh cache directory, redirect its outputs there, and run it once with
C++17, the wasm32-unknown-emscripten target, the full target sysroot, libc++,
musl and Clang builtin include paths. Set `EXTRA_CLING_ARGS` on that command
directly: `xbuild/run.sh diag-libcxx` currently overwrites the environment.
Bound generation to 120 seconds; record the command, exit and diagnostics.
If generation succeeds, compile the entire resulting dictionary with em++ and
Core's generated compile settings. Stop at the first failure. This is one
probe, not a Core build; exact argument guidance is in the review.

Success establishes only a dictionary compile path. On failure, a genuine
native pinned `rootcling_stage1` remains a separate candidate; stage-2 failure
does not eliminate it. Do not build a new stage1 or wasm Cling before assessing
this cheap result.

## Constraints

- Do not start or resume a Core, MathCore, Hist, Cling, LLVM, or rootcling
  **build** without separately approved bounded scope.
- Use ROOT's own CMake targets for subsequent library work. The pre-existing
  manual `gcore/` source slice is retired diagnostic evidence and is excluded
  from the P0 commit.
- Do not replace autoregistration configuration with a constant, silently skip
  interpreter services, hand-write Class/Streamer methods, or emulate TH1D.
- Do not begin TF1, TGraph, G8, GUI, TFile/TTree or RDataFrame.

## Carry forward

- G7 remains PASS: the pinned browser compiler works without shared memory;
  its toolchain payload is about 99.5 MiB.
- G4 remains PARTIAL and G5 BLOCKED; no linked/running wasm TH1D exists.
- Candidate package closure is Core, Thread, RIO, MathCore, Matrix and Hist
  with `imt=OFF`; this is not yet a proven minimal executable closure.
- Stock 6.40 P0 initialization loads Cling; native E1 proves default-workload
  isolation only. A Cling-free platform profile still needs preserved ROOT
  configuration, dictionary/initialization state and cleanup behavior.
- Before any browser packaging claim, resolve target ABI/PCM correctness,
  builtin zstd scheduling/toolchain, generic `-pthread` flags, wasm exception
  compatibility and actual side-module linkage.
