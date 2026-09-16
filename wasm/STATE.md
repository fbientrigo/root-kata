# STATE — ROOT WebAssembly Subset

## Current gate

**M6a — the shipped curriculum runs in the browser: PASS, independently reviewed.**
11 of the 13 katas are completed in Chromium with output byte-identical to
native ROOT and graded passed by their own validators. The remaining two are
blocked on `TClass` reflection (M4b).

Run everything with `bash wasm/run-gates.sh`. Open it yourself with
`bash wasm/gates/rootweb/run.sh serve`.

| milestone | gate | state |
| --- | --- | --- |
| M1 ROOT-owned Hist closure built for wasm | `gates/p0deps/xbuild` | **PASS**, independently reproduced |
| M2 those libraries loading and running under Node | `gates/rootlight` | **PASS**, independently reproduced |
| M2b the same in Chromium, plus an interactive page | [`gates/rootweb`](gates/rootweb/FINDINGS.md) | **PASS**, independently reproduced |
| M3 ROOT's TInterpreter over CppInterOp; P0 parity | [`gates/rootinterp`](gates/rootinterp/FINDINGS.md) | **PASS**, independently reproduced |
| M4a TF1/TFormula/TGraph parity | [`gates/rootformula`](gates/rootformula/FINDINGS.md) | **PASS**, independently reproduced |
| M6a the shipped ROOT Kata curriculum, in the browser | [`gates/rootkatas`](gates/rootkatas/FINDINGS.md) | **PASS**, independently reviewed |

Genuine CERN ROOT 6.40.04 now runs in Chromium over plain static HTTP with no
COOP/COEP, and matches native ROOT byte for byte on both probes: 39 TH1D/TAxis
values (P0) and 21 TF1/TFormula/TGraph values (P1), all at `%.17g`.

The interpreter now has **284** loud-failure overrides against 18 implemented
names, covering ROOT's non-pure `TInterpreter` defaults as well as
its pure virtuals — the gap the M3/M4 review recorded as the most important
unproven claim. Re-running every gate against the stricter adapter changed
nothing, so no proven path was relying on a silent default.

Not established: `TH1::Fit` and `cpp-root-histogram` (both blocked on `TClass`
reflection — measured, not assumed: each stops at `TInterpreter::SetClassInfo`,
so M4b unblocks both), `TFile`, `TTree`, graphics, in-browser grading (the
validators still run in CPython on the developer's machine), and the product
runner at `docs/site.js:238`, which is untouched.

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
11. **G7 PASS: a C++ compiler runs entirely client-side in Chromium and compiles genuine, unmodified ROOT headers correctly.** Two independent hypotheses ran in parallel against the identical G2 payload. **H1 (xeus-cpp-lite/CppInterOp, Clang-Repl-based) passed**: prebuilt `emscripten-forge-4x` conda packages (`xeus-cpp` 0.10.0, `cppinterop` 1.9.0, `xeus` 6.0.5), sha256-pinned and independently re-verified by the orchestrator against the channel's live `repodata.json`. The page drives a genuine `xkernel` via the real Jupyter `execute_request` wire protocol, mounts 355 real ROOT header files into its virtual FS, and produces output byte-identical to `wasm/gates/g2/expected.txt` — independently reproduced by the orchestrator twice consecutively from clean. A deliberately-broken variant produces a genuine Clang diagnostic (`error: no member named 'printfXX'... did you mean 'printf'?`) and no stdout. No `SharedArrayBuffer`/threads required — verified running under a plain `python3 -m http.server` with no COOP/COEP headers, satisfying the GitHub Pages hosting constraint. Payload: ~99.5 MiB. **H2 (Clang+LLD as WebAssembly, AOT/WASI-targeted) was falsified**: the prebuilt `browsercc` npm package genuinely compiles the same payload against the same real ROOT headers, but linking fails on `__cxa_allocate_exception`/`__cxa_throw` — every WASI-lineage prebuilt clang+lld shares a `libc++abi` with no exception-throwing runtime (a known, open upstream wasi-sdk gap), and ROOT's `GenVector_exception.h` deliberately keeps its `Throw()` inline so interactive `PtEtaPhiMVector` usage needs exceptions. See `gates/g7/FINDINGS.md` (synthesis) and `gates/g7/H2-FINDINGS.md` (H2 detail).
12. **G7 proves the compiler exists; the G4/G5 interpreter probe now tests the open `TH1D` question.** G7's payload was deliberately the already-proven GenVector program so its pass/fail was unambiguously about the compiler, not ROOT. The pinned interpreter probe mounts 631 genuine ROOT headers and passes the enlarged GenVector control, but `#include <TH1D.h>` fails with `TVersionCheck::TVersionCheck(int)` while loading the first incremental module.
13. **G4 cross-build review: PARTIAL.** Independent reproduction with ROOT 6.34.10's unmodified upstream `hist/hist/inc/LinkDef.h` and native host `rootcling` generated genuine `TH1D::Class`, `Dictionary`, and `Streamer` code. Emscripten compiled that dictionary and genuine upstream `hist/hist/src/TH1.cxx` as WebAssembly objects, but the focused link fails on `TVersionCheck`, `TObject`, `TNamed`, `TString`, `TAtt*`, `TAxis`, and `TArrayD` symbols because the target-side `Hist + MathCore + Matrix + RIO + Thread + Core` closure was not built. The all-Emscripten top-level `Hist` attempt remains in embedded LLVM/Cling compilation under the bounded build, so no linked module, six-call execution, native comparison, Chromium run, or final payload size exists; see [gates/g4/rootcling-crossbuild/CODEX-REVIEW.md](gates/g4/rootcling-crossbuild/CODEX-REVIEW.md). This evidence uses a worker checkout at 6.34.10 rather than the G0-pinned 6.40.04 source, so pinned-release confirmation remains open.
14. **G4/G5 interpreter probe: BLOCKED-AT-SYMBOL.** `bash gates/g4/interpreter-probe/probe.sh` independently reproduced the pinned ROOT 6.40.04 result: the identical enlarged 631-header mount passes G2's GenVector control, while `#include <TH1D.h>` fails with `Dynamic linking error: cannot resolve symbol _ZN13TVersionCheckC1Ei`. The pinned source confirms `TVersionCheck.h:31` creates the file-scope static, `TObject.h:18` includes it, and `TSystem.cxx:4462` defines its constructor. This corroborates the prior Core closure finding and closes the cheap interpreter path; no G5 call executes.

15. **P0 native audit: conditional interpreter dependency.** Independently reproduced on 6.40.02 and 6.34.10: stock 6.40 TH1D initialization reaches libCling through the autoregistration configuration lookup; denial aborts. Diagnostic E1 interposition preserves default P0 output without libCling, while the denied interpreter control still fails. This proves a narrow semantic isolation, not a configuration-preserving port; 6.40.04 runtime parity remains untested.
16. **ROOT-target Core build: PASS, runtime PARTIAL.** Independent fresh-cache reproduction with pinned 6.40.04/Emscripten 4.0.9 and version-mismatched host rootcling 6.40.02 completes ROOT's own Core target. The eight-file platform patch supplies the target generator environment, identifies wasm32 in RConfig/TUnixSystem, forwards builtin toolchains and schedules ZSTD. Core's 14-node order closure contains no target LLVM/Cling build nodes. Selected target class layouts agree with em++; the generator overlay does not reach target compilation. All members of the five codec/regex archives are wasm and their implementations are included, but no codec round trip or runtime reflection is tested. `libCore.so` remains relocatable, `-pthread` remains, and `InitInterpreter` is unchanged. Non-empty PCM serialization crashes, but pinned upstream MathCore, Matrix, Hist, RIO and Thread explicitly request empty PCM; that crash is not an established blocker for their stock targets. Candidate packages remain Core, Thread, RIO, MathCore, Matrix and Hist with `imt=OFF`. See [Core-fix review](gates/p0deps/CODEX-REVIEW-CORE.md), superseding the earlier [P0 compile blocker](gates/p0deps/CODEX-REVIEW.md).

## Gate-order correction

- Old assumption: G1 (a MathCore library build) must precede G2.
- Falsifying evidence: G2 ran without a ROOT library, while G1's package route enters Core → CLING.
- Second correction: G2's proven capability (GenVector/four-vectors) is not needed by any current or planned kata (fact 9). It validated the toolchain, not the product's ROOT surface.
- Third correction: G8 ("one kata fully client-side") requires compiling **the student's own C++** in the browser, which needs a C++ toolchain in the browser — a requirement independent of ROOT and unproven by any gate so far, including for the cheap header-only G2 slice.
- Replacement order: `G0 → G2 → G4 (blocker, documented) → G7 (PASS, compiler-in-browser) → TH1D build-system decision`.
- Fourth correction: G7 passed. A C++ compiler running client-side is no longer an open risk; it is confirmed (fact 11). The open risk moves entirely to `TH1D`/`TF1` — the curriculum's actual demand — which G7 did not touch.
- Fifth correction: the interpreter probe closes the cheap `TH1D` path without Core. The first-cell symbol failure under the pinned release means the next objective should scope a target-side Core cross-build, not another interpreter variation.
- Replacement order: `G0 → G2 → G4 (partial, documented) → G7 (PASS, compiler-in-browser) → Core cross-build scope → smallest validated ROOT capability`.
- Unresolved risk: GenVector does not establish a path for `TH1D`, files, or RDataFrame; ROOT Light is not yet viable as a useful curriculum subset on this evidence alone.

## Rejected approaches

- A hand-maintained `RConfigure.h`, ROOT stubs, or ROOT-like replacements.
- A full ROOT/MathCore/Core/Cling build to prove a header-only G2 claim.
- Treating browser rendering or JSROOT as ROOT computation.
- Stubbing `TH1D::Class()`/`Streamer()` to satisfy the linker: it would link, but is forking `TH1`, which the mission forbids (fact 8).
- Arguing the TH1D blocker from the CMake target graph alone: `add_dependencies` is build-order, not a link requirement (fact 8's correction).
- AOT clang+lld compiled to WebAssembly via any WASI-lineage prebuilt (`browsercc`, and by inheritance `binji/wasm-clang`, `wapm-packages/clang`): falsified for this project's needs by a shared, currently-open upstream `libc++abi` exception-handling gap (fact 11, H2).
- Treating the prebuilt xeus-cpp-lite interpreter as a cheap `TH1D` escape hatch: falsified by the first-cell `TVersionCheck` symbol wall; the interpreter still needs target-side Core.
- Building LLVM/Clang/LLD from source to fix the H2 gap: explicitly out of scope for a gate; not attempted.
- Resuming the pre-existing manual `gcore/` source manifest: retired diagnostic work, excluded from the P0 session commit. Use ROOT's own CMake targets.
- Treating E1's constant autoregistration interposition or an unverified `InitInterpreter` early return as a production port: configuration, dictionaries and cleanup require preserved ROOT behavior.

## Canonical reproduction

```bash
bash wasm/toolchain/install-emsdk.sh
bash wasm/gates/g7/run.sh # G7 PASS
bash wasm/gates/g4/interpreter-probe/probe.sh # BLOCKED-AT-SYMBOL (evidence)
```

## Historical G7 verified commit

`9fa5f547` — G7 implementation and close-out state, independently reproduced from
clean twice by Codex Sol High on 2026-09-13. The review also corrected the browser
interpreter arguments with `-fwasm-exceptions`; ordinary G2 execution did not expose
the omission, while a direct throw/catch probe did.

## Reviewer verdict

**M1 through M6a review: PASS**, independently reviewed 2026-09-16. The earlier
non-pure `TInterpreter` qualification is closed by 284 generated loud failures
plus an overload-coverage check. The four browser gates pass together; M6a
reproduces 11 native-identical, validator-passing exercises and two exact
`SetClassInfo` blockers. See [M1–M6a review](gates/CODEX-REVIEW-M3-M4.md); the
earlier [M1/M2 review](gates/rootlight/CODEX-REVIEW-M2.md) is historical.
