# STATE — ROOT WebAssembly Subset

## Current gate

**G0 — reproducible Emscripten toolchain. Independently reviewed: PASS.**

Session scope was G0 only. G1 was not started.

## Confirmed facts

Each fact below was verified by the orchestrator directly, not accepted from an agent report.

### Toolchain (G0)

1. Emscripten SDK **4.0.9** installs and activates reproducibly on Debian 13 from
   `wasm/toolchain/install-emsdk.sh`, into `~/.root-kata-wasm/emsdk`, never inside the repo.
   `emcc 4.0.9 (bbf1caa6e24f64fca9eb6a13a9e02d3f42123e77)`.
2. A non-trivial C++17 program (virtual dispatch, `std::unique_ptr`, thrown-and-caught
   exceptions, formatted floating-point) compiles to WebAssembly and produces **byte-identical
   stdout under Node v22.22.2 and headless Chromium 144**.
3. `wasm/gates/g0/run.sh` passed twice consecutively from a removed `wasm/build/`, and
   **failed correctly (exit 1, with a diff) when `expected.txt` was deliberately corrupted**.
   The gate is falsifiable, not merely green.
4. Headless Chromium execution needs no puppeteer/npm. `python3 -m http.server` on an
   ephemeral port + `--headless --dump-dom` suffices. Output must be written to real DOM
   text nodes: a `<textarea>.value` (Emscripten's default HTML shell) does **not** survive
   `--dump-dom` serialization. Server teardown is trapped; no leftover processes observed.

### Source pin

5. ROOT **6.40.04** is pinned and sha256-verified
   (`44ada253b1935d34b6801222232d50731fe7c5e3cbcfab47734c85031cfbe4d3`, 343548919 bytes).
   root.cern publishes **no checksum**; the digest comes from GitHub's release-asset API for
   tag `v6-40-04` and matches the byte-identical file served by root.cern.
6. Budget: tarball 328 MiB, unpacked 758 MiB, ~52 GB free. Disk is **comfortable**.
   Measured peak RSS for a heavy synthetic C++ TU: 445 MB. With ~5 GB available RAM,
   recommended parallelism for real ROOT-scale sources is **`-j2`..`-j3`** (estimate);
   `-j8` is fine only for single small translation units.

### Dependency boundary (reconnaissance for G1–G5)

7. `core/CMakeLists.txt:42` contains `add_dependencies(Core CLING rconfigure)` —
   **unconditional, with no `if()` guard**. Building any ROOT CMake target that depends on
   `Core` therefore requires building LLVM + Clang + Cling.
8. `math/mathcore/CMakeLists.txt` declares `ROOT_STANDARD_LIBRARY_PACKAGE(MathCore ...
   DEPENDENCIES Core ...)`. `hist/hist/CMakeLists.txt` declares `DEPENDENCIES MathCore
   Matrix RIO`. Both route through `Core`, hence through Cling.
9. Both invoke dictionary generation (`ROOT_GENERATE_DICTIONARY` via
   `ROOT_STANDARD_LIBRARY_PACKAGE`, `cmake/modules/RootMacros.cmake:1412`), putting
   **rootcling on the critical path** for a library-shaped build.
10. `-Dminimal=ON` does **not** disable `builtin_llvm`/`builtin_clang`/`builtin_cling`.
    There is no `-Dcling=OFF` escape hatch.
11. **GenVector is header-only, and this bypasses the wall.** Verified by the orchestrator:
    `ROOT::Math::PtEtaPhiMVector` (a typedef at `math/genvector/inc/Math/Vector4Dfwd.h:84`)
    compiled and ran correctly with **zero ROOT libraries linked** — no `libCore`, no
    `libMathCore`, no Cling, no rootcling, no CMake. `math/genvector/` contains **zero**
    references to `TInterpreter`/`TCling`/`TROOT.h`/`TClass.h`.
    Required include paths: `math/genvector/inc`, `math/mathcore/inc`,
    `core/foundation/inc`, `core/base/inc`, plus a `RConfigure.h` (see blocker).
    Observed native output, physics correct (p = pt·cosh η = 90.53, E = √(p²+m²)):
    ```
    pt=50.000000 eta=1.200000 phi=0.500000 m=0.105658
    E=90.532840 px=43.879128 py=23.971277 pz=75.473068
    ```
12. `hist/hist` has 40+ files touching the interpreter surface. The GenVector bypass
    is **specific to GenVector** and is not expected to extend to `TH1D`.

## Current blocker

None for G0.

The open question for G1/G2 is `RConfigure.h`: it is **generated** by CMake's `rconfigure`
target (the same target named in `add_dependencies(Core CLING rconfigure)`), from
`config/RConfigure.in` (69 lines). The header-only compile above only succeeded because the
orchestrator substituted a hand-written 6-line stand-in. Whether a stand-in is legitimate —
or whether `rconfigure` can be invoked without dragging in the Cling dependency — is
unproven and is the first thing to settle next session.

Note also that fact 11 was verified with native `g++`, **not** `em++`. The WebAssembly half
is unproven.

## Rejected approaches worth remembering

- **Reusing ROOT-to-wasm prior art — there is none.** Searched: emscripten-forge /
  conda-forge (`emscripten-wasm32`), root-project repo and issues, ROOT forum,
  compiler-research. No ROOT library has ever been compiled to WebAssembly. The one direct
  forum attempt got no working answer from ROOT developers and the user fell back to
  hand-written stub classes — which this project forbids.
- **JSROOT is not compiled ROOT.** It is an independent JavaScript reimplementation. ROOT
  dev statement: "We never think about usage of JSROOT with emscripten." Keep it for file
  inspection/visualization only, per mission.
- **`<textarea>` for scraping Chromium output** — silently empty under `--dump-dom`.
- **Emscripten "latest"** — xeus-cpp had to move pins (3.1.73 → 4.x) over a WebAssembly
  exception-handling ABI change. Pin exactly; do not drift.

## Proposed gate re-ordering (for reviewer decision — NOT acted upon)

Evidence suggests the ladder is mis-ordered. G1 ("MathCore builds to wasm") is a
library-shaped goal that hits the `Core → CLING` wall and rootcling, whereas the G2
deliverable (`PtEtaPhiMVector` in Chromium) is reachable header-only with no library at all.
G2 does not depend on G1.

Recommendation: attempt **G2 before G1**, and redefine G1 as "the smallest MathCore/GenVector
compile unit that runs in wasm" rather than "libMathCore.so builds". This is a proposal for
the reviewer; the orchestrator did not change the ladder unilaterally.

## Canonical reproduction

```bash
bash wasm/toolchain/install-emsdk.sh
rm -rf wasm/build && bash wasm/gates/g0/run.sh   # expect: G0 PASS
```

See `wasm/REPRODUCE.md`.

## Last verified commit

`deb92d9de7df86ec88042a3d8009622064c3458a` on `experiment/root-wasm-subset` —
the tree independently reviewed here.

## Reviewer verdict

**PASS** — independent review at `deb92d9de7df86ec88042a3d8009622064c3458a`.

- **VERIFIED:** `bash wasm/toolchain/install-emsdk.sh`, followed by a clean
  `wasm/build/` and `bash wasm/gates/g0/run.sh`, ended in `G0 PASS`. The gate compiled
  with `emcc 4.0.9`, then produced byte-identical 125-byte stdout under emsdk's Node
  v22.22.2 and host Chromium 144.0.7559.96, both matching `expected.txt`.
- **VERIFIED:** appending a wrong expected-output line caused `G0 FAIL` with exit 1 and
  a unified diff; `expected.txt` was restored from Git immediately afterward. The smoke
  program is standalone C++17 (`Shape`, exceptions, standard library, math) and contains
  no ROOT include, API, or replacement implementation.
- **VERIFIED:** the live GitHub release API for `v6-40-04` reports
  `root_v6.40.04.source.tar.gz`, 343548919 bytes, and
  `sha256:44ada253b1935d34b6801222232d50731fe7c5e3cbcfab47734c85031cfbe4d3`, exactly
  matching `root-src.env`; `fetch-root-src.sh` hard-fails before unpacking on a mismatch.
- **INVALIDATED:** none.
- **BLOCKER:** none for the stated G0 claim.
- **NEXT EVIDENCE REQUIRED:** none to accept G0. Its explicit host prerequisites are
  Bash, Git and network access for installation, then Python 3, curl, and a `chromium`
  executable for the browser leg; `run.sh` checks the latter three before use. Chromium is
  deliberately a checked host prerequisite rather than a pinned toolchain component. A
  future cross-host portability claim would need a documented/pinned browser matrix, but
  that is outside G0's pinned-Emscripten claim.
- **REPRODUCTION:** `bash wasm/toolchain/install-emsdk.sh`; clear `wasm/build/`; then
  `bash wasm/gates/g0/run.sh` (observed final line: `G0 PASS`).
