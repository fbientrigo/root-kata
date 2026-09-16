# Independent review — ROOT WebAssembly M1 through M4a

Reviewed on 2026-09-16 against `experiment/root-wasm-subset`, pinned CERN ROOT
6.40.04 and Emscripten 4.0.9.

## Verdict: PARTIAL

All five executable milestone gates pass independently: M1, M2, M2b, M3 and
M4a. The two numerical parity claims are real byte-for-byte comparisons against
freshly rebuilt native executables: 39 P0 lines and 21 P1 lines, all printed at
`%.17g`. The remaining review qualification is the interpreter's global loud-
failure rule: all 128 unimplemented **pure virtuals** fail loudly, and the
non-pure defaults needed by the proven TFormula path are overridden, but many
other inherited non-pure `TInterpreter` defaults still return silent null/zero/
no-op values outside the tested surface.

## Reproduced gates

| Command | Result |
| --- | --- |
| `bash wasm/gates/p0deps/xbuild/run.sh` | `xbuild Hist PASS`; six wasm libraries, six dictionaries, 294 wasm archive members, no forbidden graph node, codec/regex undefined symbol, or pthread flag |
| `bash wasm/gates/rootlight/run.sh` | `rootlight M2 PASS`; genuine compiled ROOT calls run in Node and stop at missing `CreateInterpreter` |
| `bash wasm/gates/rootweb/run.sh` | `rootweb M2b PASS`; Chromium output matches Node, `CreateInterpreter` resolves, and the broken-cell control fails |
| `bash wasm/gates/rootinterp/run.sh` | `rootinterp M3 PASS`; 39 native/browser output lines byte-identical; unsupported runtime dictionary generation fails by name |
| `bash wasm/gates/rootformula/run.sh` | `rootformula M4a PASS`; 21 native/browser lines byte-identical; `TH1::Fit` stops at loud `SetClassInfo` failure |
| `bash wasm/rootlight/interpreter/build.sh` | `interpreter build PASS`; 128 generated loud overrides, 10 implemented names, exported `CreateInterpreter` and `DestroyInterpreter` |

The M3 and M4 entry points now build the interpreter themselves instead of
silently relying on a cached `libCling.so`.

## `host-rootcling.patch`: hunk-by-hunk classification

All 13 touched upstream files are **PLATFORM PORT**, not a reimplementation of
ROOT analysis semantics.

| File / hunk | Ruling |
| --- | --- |
| `cmake/modules/RootMacros.cmake` | PLATFORM PORT — selects a same-version host generator and supplies the wasm target frontend; it changes build-tool placement, not generated ROOT behavior. |
| `cmake/modules/CheckCompiler.cmake` | PLATFORM PORT — removes `-pthread` for the single-threaded, non-shared-memory browser target. |
| `core/CMakeLists.txt` | PLATFORM PORT — removes the target-architecture Cling build edge only when the host generator is selected. |
| `builtins/lzma/CMakeLists.txt` | PLATFORM PORT — forwards the active cross-toolchain file. |
| `builtins/zstd/CMakeLists.txt` (toolchain) | PLATFORM PORT — forwards the active cross-toolchain file. |
| `builtins/zstd/CMakeLists.txt` (dependency) | PLATFORM PORT — orders the imported archive after its `ExternalProject`, matching the existing builtin pattern. |
| `builtins/lz4/CMakeLists.txt` | PLATFORM PORT — forwards the active cross-toolchain file. |
| `builtins/zlib/CMakeLists.txt` | PLATFORM PORT — forwards the active cross-toolchain file. |
| `core/foundation/inc/ROOT/RConfig.hxx` | PLATFORM PORT — identifies Emscripten wasm32 as POSIX-like ILP32 and little-endian. |
| `core/unix/src/TUnixSystem.cxx` (two guards) | PLATFORM PORT — uses Emscripten's available `ioctl` declaration and musl `strerror` path. |
| `core/base/src/TROOT.cxx` | PLATFORM PORT — derives the ROOT library directory from `$ROOTSYS` because wasm has no ELF program headers. |
| `core/base/src/TUUID.cxx` | PLATFORM PORT — selects ROOT's existing no-interface fallback because browser wasm cannot enumerate host interfaces; UUID node-identity quality beyond that fallback remains unproved. |
| `io/io/src/TMapFile.cxx` | PLATFORM PORT — disables unavailable SysV semaphore operations; shared-memory `TMapFile` is explicitly unsupported. |
| `io/io/src/TFile.cxx` | PLATFORM PORT — disables the EOS-FUSE xattr redirect optimization where `getxattr` is unavailable; ordinary `TFile` behavior is not replaced. |

The capability fallbacks in `TUUID`, `TMapFile` and `TFile` deliberately narrow
available services, but each follows an existing upstream fallback or removes an
unavailable optimization. None calculates histogram, formula, graph or I/O data
on ROOT's behalf.

## Static-ROOT loader path

The earlier Node-only workaround over `LDSO.loadedLibsByName` is no longer
justified. M2 now compiles ROOT's own `core/base/src/roota.cxx` unmodified and
loads its single `usedToIdentifyStaticRoot` symbol with the six libraries.
`TROOT::InitInterpreter` therefore takes ROOT's supported static-build path and
does not instantiate a second `libRIO` by absolute path. The revised Node gate
passes with `staticroot=1` and contains no private LDSO access.

## Interpreter ruling

`wasm/rootlight/interpreter` is architecturally a **PLATFORM PORT of the
interpreter backend**: it implements ROOT's documented `CreateInterpreter`
plugin seam over the compiler already owned by xeus-cpp-lite/CppInterOp. It does
not replace `TH1D`, `TAxis`, `TF1`, `TFormula` or `TGraph`, and the parity values
come from those compiled ROOT classes.

The stronger statement that it implements no ROOT semantics at all is too
broad. `ProcessLine`'s expression-then-declaration policy, class/scope lookup,
callable resolution and ROOT call-interface wrapper are implementations of the
`TInterpreter` service contract. They are bounded backend semantics, not a
reimplementation of ROOT's scientific/domain behavior; the source already
documents the places where its behavior is narrower than TCling.

`gen_fatal.py` reads the pinned ROOT header at build time and produced 128 loud
pure-virtual overrides while `implemented.txt` selected 10 names. A missed pure
virtual cannot produce a usable plugin: compilation of `new
TCppInterOpInterpreter` would fail because the class remained abstract. Name-
based exclusions cover every overload of an implemented name, so those
overloads were also inspected; unsupported vector-prototype and DeclId forms
explicitly call `rkUnsupported`.

The non-pure defaults used by the proven formula path are overridden by real
handle implementations: `ClassInfo_Init/Delete/IsValid`,
`CallFunc_Factory/Init/Delete/IsValid/IFacePtr`, and the two string-prototype
`CallFunc_SetFuncProto` overloads. Other non-pure base defaults remain silent.
Consequently the accurate claim is "loud for all unimplemented pure virtuals
and for the asserted boundaries," not "every possible unimplemented
TInterpreter service is loud."

`MakeRootCallable` does what it claims: it emits an `extern "C"` wrapper with
ROOT's generic call shape, compiles it through `Cpp::Declare`, and obtains its
address with `Cpp::GetFunctionAddress`. It never reads or names CppInterOp's
private `JitCall` member.

## `exit()` finding

The no-ROOT differential was reproduced in the same Chromium dynamic-linking
configuration. `printf` + `fflush` + `exit(1)` produced empty captured stdout
and `Uncaught RuntimeError: function signature mismatch`; replacing only
`exit(1)` with `_Exit(1)` preserved `exit-probe` in stdout. Because `_Exit`
skips normal exit-handler/static-destructor dispatch, this localises the
stdout-losing trap to normal termination across side modules. It does not prove
which registered handler has the mismatched signature, so the findings now say
that explicitly. The interpreter's `::Error` plus C++ exception is therefore
the correct observable failure mechanism here.

## Housekeeping

- `wasm/gates/rootlight/interp-probe/gen.log` was excluded as generated build output.
- `wasm/build/` remains ignored and contributes nothing to the commit.
- `wasm/gates/gcore/FINDINGS.md` now labels the manual Core slice clearly as retired, diagnostic-only evidence.

## Remaining boundary

M1 through M4a are verified for their stated programs. `TH1::Fit`, general
TClass reflection, `TFile`, `TTree`, graphics, repeated-cell/concurrency
behavior, deployable payload size, and the full inherited non-pure
`TInterpreter` surface are not established.

REVIEW VERDICT: PARTIAL — the most important unproven claim is that every unimplemented `TInterpreter` service fails loudly rather than inheriting a silent non-pure base default.
