# STATE — ROOT WebAssembly Subset

## Current gate

**G4 — genuine `TH1D` direct WebAssembly probe: BLOCKER.**

## Confirmed facts

1. G0 remains reproducible with pinned Emscripten **4.0.9**, ROOT source **6.40.04**, Node and headless Chromium.
2. `PtEtaPhiMVector` is a genuine ROOT alias at `math/genvector/inc/Math/Vector4Dfwd.h:84`. Its common template path through `Math/Vector4D.h` compiles without linking a ROOT library.
3. G2 generates `RConfigure.h` at run time from pinned ROOT `config/RConfigure.in`, using CMake `configure_file`, the mechanism ROOT uses in `cmake/modules/RootConfiguration.cmake:549-573`. It probes the actual native/`em++` compiler for C++ standard and attribute support; its no-component profile leaves optional ROOT component macros undefined. No hand-written or checked-in compatibility header exists.
4. `bash wasm/gates/g2/run.sh` builds a native reference, Node wasm target, and browser wasm target from the same unmodified ROOT headers and program. All emitted:

   ```
   pt=50.000000 eta=1.200000 phi=0.500000 m=0.105658
   E=90.532840 px=43.879128 py=23.971277 pz=75.473068
   sum_m=54.847433 sum_pt=52.238727
   ```

5. G2 deliberately failed (non-zero, unified diff) after corrupting its expected `pt` to `999.000000`; the fixture was restored.
6. The normal library route remains expensive: Core has unconditional `add_dependencies(Core CLING rconfigure)` (`core/CMakeLists.txt:42`), while MathCore and Hist depend on Core.
7. [ROOT_LIGHT.md](ROOT_LIGHT.md) records the evidence-backed 20/80 inventory. The only Tier 1 computation is the restricted GenVector slice. Histograms are the strongest actual curriculum demand but remain Tier 2; TFormula/fitting, TFile/TTree and RDataFrame are Tier 3 under current evidence.
8. G4 ran the pinned `em++` direct-link probe with genuine `TH1D`, no ROOT libraries, and the G2-generated `RConfigure.h`. Its first missing symbol was `TH1D::TH1D(char const*, char const*, int, double, double)`. The reproducible error is preserved in `wasm/build/g4/first-missing-symbol.txt`. **Corrected rationale** (superseding an earlier, weaker version of this note): the blocker is not merely that Hist's CMake target depends on MathCore/Matrix/RIO which depend on Core which depends on CLING — `add_dependencies(Core CLING rconfigure)` (`core/CMakeLists.txt:42`) is a CMake *build-order* edge, not a link edge, and Core's actual `target_link_libraries` (`:44-49`) is only dl/threads/atomics; Cling is `dlsym`'d at runtime (`core/base/src/TROOT.cxx:2251`), not statically linked. The real blocker is `ClassDefOverride` (`hist/hist/inc/TH1.h:693,949`): it expands via `_ClassDefOutline_` (`core/base/inc/Rtypes.h:310-321`) to *declare without defining* `Class()`, `Streamer()`, `fgIsA`, `Dictionary()`; `IsA()`/`Streamer()` are virtual, so constructing one `TH1D` emits a vtable referencing those undefined symbols. Only `rootcling` supplies them (`core/dictgen/src/rootcling_impl.cxx:1122-1159`); `ClassImp` is a no-op in 6.40 (`Rtypes.h:373`), so there is no non-dictionary fallback. `TH1.cxx` is also a single 10,731-line TU pulling `TF1`/`TFormula`/`ROOT::Fit`/`GoFTest`, so the arithmetic-only `Fill`/`Get*` path cannot be linked in isolation either. See [g4/BLOCKER.md](gates/g4/BLOCKER.md) (corrected).
9. **Curriculum ROOT-API inventory** (all 13 exercises read directly): the shipped surface is `TH1D`/`TH1` (5 of 8 ROOT katas: ctor, `Fill`, `GetEntries`, `GetBinContent`, `SetBinContent`, `SetBinError`, `GetMean`, `GetStdDev`, `Integral`, `GetNbinsX`, `GetXaxis`, `Fit`, `Draw`), `TAxis` (4), `TF1`-from-formula-string (3, which transitively requires `TFormula`→`TInterpreter` — this is a **shipped**, not merely planned, interpreter dependency), `TGraph` data access (1), and one `TCanvas`/`gROOT::SetBatch`/`SaveAs("preview.png")` (1, decorative — no validator inspects the PNG). `TMath`, `TRandom`/`gRandom`, and `ROOT::Math` four-vectors (the G2 slice) appear **nowhere** in the curriculum, planned or shipped. Planned m2–m6 milestones add `TFile`/`TTree`, `RDataFrame`, `RVec`. Source: `curriculum/triads/*.csv`, `curriculum/plan.json`, `src/root_kata/exercises/*/harness.cpp`.
10. **The browser runner today does no client-side compilation of any kind.** `docs/site.js` (`fetch('/api/run')`) posts student code to a *local* Python server (`src/root_kata/web_server.py`, bound to `127.0.0.1`) which shells out to real `g++`/`root-config` — this is the existing, honest "no Cling, no PyROOT" design (`src/root_kata/cpp_runner.py:1-21`), not a mock of ROOT. There is no WASM, xeus-cpp, or JSROOT integration anywhere in `docs/`/`src/`/`scripts/`. `docs/site.js:231-254`'s single `fetch` call is the integration seam a wasm runner would replace. No COOP/COEP headers are set anywhere and GitHub Pages cannot set them, so any in-browser toolchain must be single-threaded (no `SharedArrayBuffer`, no pthreads).

## Gate-order correction

- Old assumption: G1 (a MathCore library build) must precede G2.
- Falsifying evidence: G2 ran without a ROOT library, while G1's package route enters Core → CLING.
- Second correction: G2's proven capability (GenVector/four-vectors) is not needed by any current or planned kata (fact 9). It validated the toolchain, not the product's ROOT surface.
- Third correction: G8 ("one kata fully client-side") requires compiling **the student's own C++** in the browser, which needs a C++ toolchain in the browser — a requirement independent of ROOT and unproven by any gate so far, including for the cheap header-only G2 slice.
- Replacement order: `G0 → G2 → G4 (blocker, documented) → G7 narrowed to a compiler-in-browser spike → TH1D build-system decision`.
- Unresolved risk: GenVector does not establish a path for `TH1D`, files, or RDataFrame; ROOT Light is not yet viable as a useful curriculum subset on this evidence alone.

## Rejected approaches

- A hand-maintained `RConfigure.h`, ROOT stubs, or ROOT-like replacements.
- A full ROOT/MathCore/Core/Cling build to prove a header-only G2 claim.
- Treating browser rendering or JSROOT as ROOT computation.
- Stubbing `TH1D::Class()`/`Streamer()` to satisfy the linker: it would link, but is forking `TH1`, which the mission forbids (fact 8).
- Arguing the TH1D blocker from the CMake target graph alone: `add_dependencies` is build-order, not a link requirement (fact 8's correction).

## Canonical reproduction

```bash
bash wasm/toolchain/install-emsdk.sh
bash wasm/gates/g4/run.sh # intentionally exits 1 with the pinned G4 blocker
```

## Last verified commit

`dd8f3b8` — `feat(wasm): prove GenVector WebAssembly gate`.

## Reviewer verdict

Not yet independently reviewed.
