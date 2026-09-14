# ROOT WebAssembly Subset — Gate Ladder

## Mission

Determine the **smallest subset of actual CERN ROOT** that can be compiled to WebAssembly
and used to teach genuine ROOT programming entirely inside the browser.

This is **not** a project to port full ROOT. It is not a project to reimplement ROOT.

**Product priority:** students write genuine ROOT APIs with the least infrastructure possible.

## Gates

A gate is a falsifiable claim with a deterministic reproduction command.

| Gate | Claim |
| ---- | ----- |
| G0 | A reproducible Emscripten toolchain exists, pinned and re-runnable from a clean state. |
| G1 | ROOT MathCore builds to WebAssembly. **Deferred:** its normal build path reaches Core/Cling. |
| G2 | `ROOT::Math::PtEtaPhiMVector` executes correctly in Chromium. **PASS.** |
| G3 | The minimum ROOT Core/Physics dependency boundary is established and documented. |
| G4 | Actual ROOT `TH1D` builds to WebAssembly. **PARTIAL:** native `rootcling` generated a genuine dictionary and Emscripten compiled it plus upstream `TH1.cxx` to wasm objects; the target-side ROOT closure still prevents a linked module. The pinned in-browser interpreter probe independently reaches the same Core boundary at header-load time. |
| G5 | `TH1D` supports `Fill`, `GetEntries`, `GetBinContent`, `Integral`, `GetMean` in Chromium. **BLOCKED:** the proven in-browser interpreter cannot load `TH1D.h` without target-side Core. |
| G6 | `TGraph`/`TF1` evaluated — **only if inexpensive**. This gate may be declined on cost. |
| G7 | **Narrowed, pulled forward. PASS** (via xeus-cpp-lite/CppInterOp): a genuine ROOT program, typed in the browser, is compiled client-side (no server) and runs correctly in Chromium. Proves a compiler can run client-side; says nothing about `TH1D`, which remains partial at G4. |
| G8 | One existing genuine ROOT Kata exercise executes fully client-side. |

## Out of scope

Unless a later gate produces evidence that it is *necessary*:

full ROOT · PyROOT · RooFit · TMVA · full Cling · RDataFrame · TFile/TTree I/O ·
GUI/X11 · distributed execution · **custom reimplementations pretending to be ROOT**

For ROOT file inspection and visualization, assume **JSROOT** is used separately until
evidence requires native ROOT I/O.

## Rules that decide gates

1. **One gate per session.** Do not begin the next gate in the same session.
2. A gate is **not** complete because code compiled once. It requires a deterministic
   reproduction command that passes from a clean state.
3. Prefer **removing** dependencies and features over patching them.
4. Kill any path that:
   - requires reimplementing ROOT APIs;
   - broadens the dependency surface without evidence;
   - introduces infrastructure unrelated to the current gate;
   - cannot produce a falsifiable test.
5. Prefer 2-3 independent hypotheses in parallel over sequential blind debugging.
6. Do not modify the normal ROOT Kata curriculum (`curriculum/`, `src/`, `docs/`, `tests/`).
7. Do not merge experimental changes into `web/assembly`.

## Canonical branch

`experiment/root-wasm-subset`

## Reproduction contract

Every completed gate `gN` owns exactly one entry point:

```
wasm/gates/gN/run.sh
```

which exits `0` and prints `gN PASS`, or exits non-zero and prints `gN FAIL: <reason>`.
`wasm/REPRODUCE.md` lists the canonical command for the current gate.

G4 is a **PARTIAL** cross-build result. Its canonical direct-link command still
deliberately exits non-zero with the first unresolved symbol, while the
rootcling-crossbuild review proves a real dictionary and genuine upstream
`TH1.cxx` can each be compiled to wasm objects. See
`g4/rootcling-crossbuild/CODEX-REVIEW.md` for the independent reproduction and
the remaining target-side ROOT closure; no linked or browser-running `TH1D`
module exists yet. The bounded interpreter probe
(`g4/interpreter-probe/probe.sh`) now confirms that the same target-side Core
boundary is required even to load `#include <TH1D.h>`; see
`g4/interpreter-probe/CODEX-REVIEW.md`.

## Gate-order correction

Old assumption: G1 had to precede G2. Evidence: `math/mathcore/CMakeLists.txt`
depends on Core, and `core/CMakeLists.txt` unconditionally makes Core depend on
CLING (a build-order edge, not a link edge — see `gates/g4/BLOCKER.md`); the G2
template path compiled and ran without a ROOT library. Replacement:
`G0 → G2 → G4 (partial, documented) → G7 (narrowed) → smallest next capability probe`.

Second correction: reading all 13 shipped exercises plus `curriculum/triads/*.csv`
and `curriculum/plan.json` shows **no current or planned kata uses GenVector or
TMath** — G2's proven capability validated the toolchain, not the curriculum's
actual ROOT surface, which is `TH1D` (5/8 katas) and `TF1`/`TFormula` (3/8).

Third correction: gate G8 requires compiling *the student's own C++* in the
browser, which needs a C++ toolchain running client-side — independent of ROOT,
and unproven even for the cheap GenVector slice (G2 was compiled by a host
`em++`, never by an in-page toolchain). G7 is pulled forward and narrowed to
test exactly this, using the already-proven G2 program as payload so a failure
is unambiguously the compiler's, not ROOT's.

Fifth correction: the G4/G5 interpreter probe reproduced the missing
`TVersionCheck` Core symbol at `#include <TH1D.h>` under the pinned 6.40.04
headers, while the identical enlarged-header GenVector control passed. The cheap
interpreter path is closed without a target-side Core build.

Replacement order: `G0 → G2 → G4 (partial, documented) → G7 (PASS,
compiler-in-browser) → Core cross-build scope → smallest validated ROOT
capability`.

Risk carried forward: G2's bypass only proves the restricted GenVector template
path, not MathCore, Hist, or the wider curriculum; G7 passing proves the
toolchain exists but says nothing yet about which ROOT subset it can build.

## G7 result

**PASS**, via hypothesis H1 (xeus-cpp-lite/CppInterOp, Clang-Repl-based), run in
parallel against an independent hypothesis H2 (Clang+LLD as WebAssembly,
AOT/WASI-targeted) which **falsified** on an unrelated, ecosystem-wide gap: every
WASI-lineage prebuilt clang+lld shares a `libc++abi` with no exception-throwing
runtime, and ROOT's `GenVector_exception.h` keeps its `Throw()` inline specifically
so interactive `PtEtaPhiMVector` usage needs it. Full evidence and independent
re-verification in `gates/g7/FINDINGS.md` and `gates/g7/H2-FINDINGS.md`. `~99.5 MiB`
toolchain payload; no threads/`SharedArrayBuffer` required, satisfying the GitHub
Pages hosting constraint.

## G4/G5 interpreter result

`bash gates/g4/interpreter-probe/probe.sh` independently reproduced
`BLOCKED-AT-SYMBOL` under pinned ROOT 6.40.04: the enlarged 631-header control
passes, but `#include <TH1D.h>` fails while loading the first incremental wasm
module with `cannot resolve symbol _ZN13TVersionCheckC1Ei`. The source-cited
Core constructor is required before any `TH1D` cell can run; see
`gates/g4/interpreter-probe/CODEX-REVIEW.md`.
