# Independent review — ROOT WebAssembly M1 through M6a

Reviewed on 2026-09-16 against `experiment/root-wasm-subset`, pinned CERN ROOT
6.40.04 and Emscripten 4.0.9.

## Verdict: PASS

The original M1–M4a review was PARTIAL because non-pure `TInterpreter` defaults
could fail silently. The follow-up closes that objection: 284 unimplemented
service declarations now fail loudly, all overloads behind the 18 implemented
names are checked, and the four browser gates pass together. M6a also passes:
11 shipped exercises are byte-identical to native ROOT and pass their own
validators; the remaining two stop specifically at `TInterpreter::SetClassInfo`.

## Reproduced gates

| Command | Result |
| --- | --- |
| `bash wasm/gates/p0deps/xbuild/run.sh` | `xbuild Hist PASS`; six wasm libraries, six dictionaries, 294 wasm archive members, no forbidden graph node, codec/regex undefined symbol, or pthread flag |
| `bash wasm/gates/rootlight/run.sh` | `rootlight M2 PASS`; genuine compiled ROOT calls run in Node and stop at missing `CreateInterpreter` |
| `bash wasm/gates/rootweb/run.sh` | `rootweb M2b PASS`; Chromium output matches Node, `CreateInterpreter` resolves, and the broken-cell control fails |
| `bash wasm/gates/rootinterp/run.sh` | `rootinterp M3 PASS`; 39 native/browser output lines byte-identical; unsupported runtime dictionary generation fails by name |
| `bash wasm/gates/rootformula/run.sh` | `rootformula M4a PASS`; 21 native/browser lines byte-identical; `TH1::Fit` stops at loud `SetClassInfo` failure |
| `bash wasm/rootlight/interpreter/build.sh` | `interpreter build PASS`; 284 generated loud overrides, 18 implemented names, exported `CreateInterpreter` and `DestroyInterpreter` |
| `bash wasm/gates/rootkatas/run.sh` | `rootkatas M6a PASS`; 11/13 raw `rk` JSON lines byte-identical to native and validator-passing; two expected reflection blockers |
| `bash wasm/run-gates.sh rootweb rootinterp rootformula rootkatas` | all four browser gates pass together after the interpreter and shared-stage changes |

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

`gen_fatal.py` now reads every explicit virtual declaration in the pinned ROOT
header, including `override = 0` declarations without a `virtual` keyword. It
produces 284 loud overrides; the 18 implemented names account for 26 overload
declarations. `ClassInfo_Init(ClassInfo_t*, int)` and
`ClassInfo_Delete(ClassInfo_t*, void*)` are explicitly unsupported rather than
inherited from ROOT's silent defaults.

The name-based skip was a real regression risk: adding a sibling overload could
otherwise inherit a non-pure base default. Generation now compares the overload
count in ROOT with the adapter's explicit `override` declarations. Removing the
tag-number `ClassInfo_Init` overload was tested and fails generation with
`(ROOT, adapter): (2, 1)`. Independent Clang AST inspection found four additional
macro-expanded `ClassDefOverride` virtuals (`IsA`, `Streamer`, `ShowMembers`,
`CheckTObjectHashConsistency`); these have real ROOT dictionary implementations
and are not unsupported interpreter services.

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

## M6a curriculum ruling

The 13 gate solutions implement the stated exercise contracts without bypassing
the harnesses; all pass their own validators under native ROOT. The browser arm
substitutes the literal contents of `rk.h` and the solution at the harness's two local include
sites, leaving translation-unit order and behavior unchanged for these sources.
The gate now compares the raw final JSON lines as well as parsed values, so the
byte-identity claim is executable rather than prose.

The blocked assertion cannot pass on an arbitrary later failure. Both
`cpp-root-fit-gaussian` and `cpp-root-histogram` must name `SetClassInfo` or the
wasm-ROOT unsupported-service diagnostic. The correction is reproduced:
`cpp-root-histogram` reaches reflection before its `TCanvas`; graphics may still
become the next boundary after M4b.

## Shared-stage safety

The staged `$ROOTSYS` is shared mutable state. `rootlight` now holds an exclusive
`flock` while rebuilding or using it; the interpreter builder and rootweb payload
stager hold shared locks while reading it. A held producer lock delayed the
interpreter build until release, and the subsequent four-gate run passed.

## Remaining boundary

M1 through M6a are verified for their stated programs. General TClass
reflection, `TFile`, `TTree`, graphics, wrong/malformed student programs,
in-browser Python grading, repeated-cell behavior and cold-load performance are
not established.

REVIEW VERDICT: PASS — the single most important remaining unproven claim is that M4b TClass reflection is sufficient to complete both blocked katas; `cpp-root-histogram` may expose an M5 graphics boundary afterward.
