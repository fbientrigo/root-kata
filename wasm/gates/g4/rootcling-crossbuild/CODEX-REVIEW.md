# G4 rootcling cross-build — independent review

Date: 2026-09-13
Reviewer: Codex Sol High

## Verdict

**PARTIAL.** The central build claim is reproduced through genuine dictionary generation and Emscripten compilation of unmodified ROOT code, but no linked or running WebAssembly module was produced. The remaining blocker is the target-side ROOT runtime closure, not dictionary generation: the focused link fails on missing Core-family symbols when only `TH1.cxx` and the generated dictionary are supplied.

The experiment used the worker checkout at `/home/fabian/.cache/rootwasm-th1d/root-src`, ROOT `6fced0c5` (`v6-34-10`), native host `rootcling`, and Emscripten 3.1.74 / Clang 20. This is genuine upstream ROOT evidence, but it is not the repository's pinned G0 source release (6.40.04); a final gate closure should repeat the same recipe against the pinned release.

## Independent reproduction

The fresh dictionary invocation used the real upstream `hist/hist/inc/LinkDef.h` and upstream headers, with no replacement ROOT code. It emitted a 92,527-byte `G__TH1D_independent.cxx`, a rootmap, and a PCM. The generated C++ contains the standard generation banner and genuine definitions:

```text
TH1D::Dictionary()
TH1D::Class()
TH1D::Streamer(TBuffer &R__b)
```

The generated dictionary and genuine upstream `hist/hist/src/TH1.cxx` were compiled separately with Emscripten. `file(1)` reported:

```text
G__TH1D_independent.o: WebAssembly (wasm) binary module version 0x1 (MVP)
TH1.cxx.o:             WebAssembly (wasm) binary module version 0x1 (MVP)
main.cxx.o:            WebAssembly (wasm) binary module version 0x1 (MVP)
```

The independent run used this command shape (the temporary output directory was fresh):

```sh
ROOT=/home/fabian/.cache/rootwasm-th1d/root-src
HOST=/home/fabian/.cache/rootwasm-th1d/root-host
EM=/home/fabian/.cache/rootwasm-th1d/emsdk/upstream/emscripten
MAIN=/tmp/rootwasm-th1d-probe/main.cxx
OUT=$(mktemp -d /tmp/rootwasm-th1d-independent.XXXXXX)
LD_LIBRARY_PATH="$HOST/lib:" "$HOST/bin/rootcling" -f "$OUT/G__TH1D.cxx" \
  -s "$OUT/libTH1D.so" -rml libTH1D.so -rmf "$OUT/libTH1D.rootmap" \
  -writeEmptyRootPCM -I"$ROOT/hist/hist/inc" -I"$ROOT/core/base/inc" \
  -I"$ROOT/core/cont/inc" -I"$HOST/include" \
  "$ROOT/hist/hist/inc/TAxis.h" "$ROOT/core/base/inc/TAttFill.h" \
  "$ROOT/core/base/inc/TAttLine.h" "$ROOT/core/base/inc/TAttMarker.h" \
  "$ROOT/core/cont/inc/TArrayC.h" "$ROOT/core/cont/inc/TArrayD.h" \
  "$ROOT/core/cont/inc/TArrayF.h" "$ROOT/core/cont/inc/TArrayI.h" \
  "$ROOT/core/cont/inc/TArrayL64.h" "$ROOT/core/cont/inc/TArrayS.h" \
  "$ROOT/hist/hist/inc/TF1.h" "$ROOT/hist/hist/inc/TFitResultPtr.h" \
  "$ROOT/hist/hist/inc/TH1.h" "$ROOT/hist/hist/inc/TH1D.h" \
  "$ROOT/hist/hist/inc/LinkDef.h"
INCS=(-I"$ROOT/hist/hist/inc" -I"$ROOT/core/base/inc" \
  -I"$ROOT/core/cont/inc" -I"$HOST/include")
"$EM/em++" -O3 -DNDEBUG -fPIC "${INCS[@]}" -c "$OUT/G__TH1D.cxx" -o "$OUT/G__TH1D.o"
"$EM/em++" -O3 -DNDEBUG "${INCS[@]}" -c "$ROOT/hist/hist/src/TH1.cxx" -o "$OUT/TH1.cxx.o"
"$EM/em++" -O3 -DNDEBUG "${INCS[@]}" -c "$MAIN" -o "$OUT/main.cxx.o"
file "$OUT"/*.o
"$EM/em++" "$OUT/main.cxx.o" "$OUT/TH1.cxx.o" "$OUT/G__TH1D.o" \
  -o "$OUT/th1d_probe.js" -sERROR_ON_UNDEFINED_SYMBOLS=1
```

Here `$MAIN` is the existing two-line probe that includes `TH1D.h`, constructs a `TH1D`, calls `Fill`, and checks `GetEntries`; it is not a ROOT implementation or dictionary substitute.

The direct link was then attempted with the three wasm objects and `-sERROR_ON_UNDEFINED_SYMBOLS=1`. It failed with `wasm-ld` errors beginning:

```text
undefined symbol: TVersionCheck::TVersionCheck(int)
undefined symbol: vtable for TObject
undefined symbol: vtable for TNamed
undefined symbol: TString::TString()
undefined symbol: TAttLine::TAttLine()
undefined symbol: TAxis::TAxis()
undefined symbol: TArrayD::TArrayD()
```

This independently reproduces High A's narrower result and the same missing Core boundary. It does not prove that the six-call program runs: link never completes.

The bounded top-level check was also rerun:

```text
timeout 180 cmake --build /home/fabian/.cache/rootwasm-th1d/root-wasm-build --target Hist -j2
```

During the bound, the all-Emscripten ROOT build remained at 27% compiling embedded LLVM/Cling support objects; it did not reach `Hist`. This supports the Medium matrix's build-system observation, while the reconstructed/transcript-only portions of that finding remain secondary evidence.

## Source citation spot-check

Against the same ROOT checkout named in High B, the following citations were checked with `nl -ba` and agree with the report:

| Claim | Source evidence |
| --- | --- |
| `Hist` directly depends on `MathCore`, `Matrix`, and `RIO` | `hist/hist/CMakeLists.txt:170-173` |
| `Matrix` depends on `MathCore` | `math/matrix/CMakeLists.txt:79-80` |
| `MathCore` depends on `Core` | `math/mathcore/CMakeLists.txt:198-200` |
| `RIO` depends on `Core` and `Thread` | `io/io/CMakeLists.txt:61-64` |
| `Thread` depends on `Core` | `core/thread/CMakeLists.txt:65-67` |
| ROOT's linker macro publishes dependency edges | `cmake/modules/RootMacros.cmake:905-914` and `:909-914` |
| The fixed-bin `TH1D` constructor is real out-of-line ROOT code | `hist/hist/inc/TH1.h:670-680`; `hist/hist/src/TH1.cxx:10436-10444` |
| The requested operations are implemented in `TH1.cxx` | `:3346-3364` (`Fill`), `:4425-4433` (`GetEntries`), `:5084-5091` (`GetBinContent`), `:7558-7574` (`GetMean`), `:7964-7980` (`Integral`) |
| `TArrayD` is compiled into `Core` | `core/cont/CMakeLists.txt:11-19` and `:43-51` |
| `Core -> CLING` is build order, while `rootcling` is a tool dependency | `core/CMakeLists.txt:34-41`; `main/CMakeLists.txt:96` |

High B's correction to High A is therefore valid: `add_dependencies(Core CLING rconfigure)` is not a wasm runtime link edge. The supported stock target closure is `Hist + MathCore + Matrix + RIO + Thread + Core`; Cling/LLVM, `rootcling`, `rootcling_stage1`, and `Rint` belong to the host/build side for this experiment.

## Worker finding disposition

| Worker finding | Disposition | Reason |
| --- | --- | --- |
| High A: host `rootcling` generated a real dictionary; genuine `TH1.cxx` and dictionary compiled to wasm; focused link stopped on missing Core symbols; top-level build has earlier blockers | **VERIFIED** | Fresh dictionary, object, and link reproduction match the core result. The report's broad `Hist`/Core boundary is correct; its shorthand `Core -> CLING` interpretation is superseded by High B's build-order correction. |
| High B: target closure is `Hist + MathCore + Matrix + RIO + Thread + Core`; host toolchain is not runtime closure; source citations identify the API and dependency edges | **VERIFIED** | Ten citation groups were spot-checked against the reported ROOT checkout and agree with the source. |
| Medium: minimal all-Emscripten configurations retain embedded LLVM/Cling and do not reach a quick `Hist` build; `builtin_cling=OFF` needs external LLVM | **REPRODUCTION** | The bounded `Hist` build independently remained in Emscripten LLVM compilation at 27% for 180 seconds. The full matrix and exact `builtin_cling=OFF` failure remain transcript-derived and should be rerun if they affect the next build design. |

## Ten-point gate acceptance

| # | Criterion | Result | Evidence |
| ---: | --- | --- | --- |
| 1 | Real ROOT source | PASS | Unmodified upstream ROOT 6.34.10 source, including `TH1.cxx` and `LinkDef.h`. |
| 2 | Real `rootcling`-generated dictionary | PASS | Fresh native host `rootcling` output; genuine `Class`, `Dictionary`, and `Streamer`. |
| 3 | Dictionary not manually replaced | PASS | No ROOT dictionary symbols, `Class()`/`Streamer()` definitions, or histogram replacements were written. |
| 4 | Compiled to wasm | PASS | `file(1)` identifies both fresh dictionary and `TH1.cxx` objects as wasm modules. |
| 5 | Constructs genuine `TH1D` | NOT MET | The final link does not exist, so construction is not executed. |
| 6 | `Fill`/`GetEntries`/`GetBinContent`/`Integral`/`GetMean` work | NOT MET | No executable reached these calls. |
| 7 | Matches native reference | NOT MET | No wasm execution or native-vs-wasm comparison was possible. |
| 8 | Runs under proven Chromium/wasm environment | NOT MET | No final module exists to run in Chromium. |
| 9 | Deterministic and documented | PARTIAL | Commands, versions, paths, and failure evidence are recorded here and in the worker reports; no committed cross-build runner exists yet, and the reproduction currently depends on external caches. |
| 10 | Dependency and payload sizes measured | PARTIAL | Object/archive sizes and the closure are measured; no final linked wasm payload exists, so final size is unavailable. |

The honest result is **4/10 met, 2/10 partial, 4/10 not met**. This is a narrower, reproducible cross-build result and does not justify a PASS.

## Next objective

`wasm/NEXT.md` still proposed the cheaper xeus-cpp-lite/Cling `TH1D` interpreter probe. This session's evidence makes that probe more valuable, not obsolete: the static path reaches genuine wasm objects but requires a large target closure, while G7 already provides a proven in-browser interpreter and the interpreter could resolve class metadata differently from a static link. The next session should therefore try the existing interpreter with genuine `TH1D` source and report the exact diagnostic before attempting another expensive ROOT build; if it fails, the full host-rootcling plus target closure can be scoped with this review's evidence.

No product wiring, curriculum, or unrelated ROOT subsystem was changed.
