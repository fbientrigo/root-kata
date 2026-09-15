# P0 TH1D — ROOT target-level dependency map (Worker B)

Scope: analysis only. Pinned source `root-6.40.04` (`$S` below = `~/.root-kata-wasm/src/root-6.40.04`);
native linker/runtime evidence from ROOT **6.40.02** shared libs in the FairShip pixi env
(`$L` = `~/thesis/FairShip/.pixi/envs/default/lib`). No `.cxx` lists were assembled and no
dependency was discovered by chasing undefined symbols; the symbol counts in §2 only *weigh*
edges that the CMake graph in §1 already declares.

## TL;DR

1. **CMake:** Core → CLING is build-order only (`core/CMakeLists.txt:42`). But every ROOT
   library's *dictionary* is a custom command whose COMMAND is `$<TARGET_FILE:rootcling_stage1>`
   (Core, Thread, RIO) or `$<TARGET_FILE:rootcling>` (MathCore, Matrix, Hist)
   (`cmake/modules/RootMacros.cmake:643-677`). Inside the ROOT project those are always the
   **in-tree target** artifacts. 6.40.04 has no host-tool, `NATIVE`, `CMAKE_CROSSCOMPILING` or
   Emscripten hook for them. So `cmake --build . --target Hist` under emcmake must build
   `rootcling_stage1` and `rootcling` **for wasm32**. That drags in Cling/Clang/LLVM (§1, §4).
2. **Runtime (new, measured):** a plain P0 `TH1D("h","h",10,0,10)` **dlopens libRIO and
   libCling** from inside the constructor, even with `TH1::AddDirectory(false)`. Stack:
   `TH1D::TH1D → TH1::Build → ROOT::Experimental::ObjectAutoRegistrationEnabled →
   TEnv::GetValue → gROOT → GetROOT2 → TROOT::InitInterpreter → dlopen(libCling)`
   (§3). `InitInterpreter` calls `exit(1)` if either load fails (`TROOT.cxx:2232-2245`).
   Linking Hist is therefore not enough. A P0 wasm module must also satisfy the libCling
   runtime edge, either through dynamic loading or through ROOT's own `usedToIdentifyStaticRoot`
   branch, which still needs a real `CreateInterpreter`.
3. **Link:** libHist's NEEDED (Matrix, MathCore, RIO, Core) are all real symbol uses, but
   RIO is **1 symbol** (`TFile::Open` from `THnChain.cxx:141`) and Matrix is **10 strong**,
   all from non-P0 classes (TPrincipal, TMultiDimFit, TSVDUnfold) and their dictionary
   entries. Thread is not NEEDED by Hist. It comes in only through RIO (10 symbols).
   Neither Matrix nor RIO can be dropped without editing Hist's source list, because
   `G__Hist` covers every header.
4. **Host rootcling injection:** a configure-only experiment shows that pre-declaring IMPORTED
   `rootcling_stage1`/`rootcling` is rejected by ROOT's own CMake
   (`core/rootcling_stage1/CMakeLists.txt:38,40`, `main/CMakeLists.txt:121`). There is no
   zero-patch host-tool path in 6.40.04, and the in-tree `Core → CLING` order edge would still
   force LLVM (§5).

---

## 1. Dependency table (CMake + source)

Classes: **HOST** = host tool that runs during the build · **ORDER** = build-order only
(`add_dependencies` / custom-command `DEPENDS`) · **COMPILE** = include dirs/headers ·
**LINK** = `target_link_libraries`, or `DEPENDENCIES`/`LIBRARIES` of
`ROOT_STANDARD_LIBRARY_PACKAGE` (these become `PUBLIC`/`PRIVATE` link:
`RootMacros.cmake:981-982` via `:1399-1404`) · **RUNTIME** = dlopen/`gSystem->Load`/plugin
manager · **OPT** = optional or unused for P0.

### Macro wiring (applies to every package)

| Component | Edge | Class | Citation |
|---|---|---|---|
| `ROOT_STANDARD_LIBRARY_PACKAGE(X … DEPENDENCIES d LIBRARIES l)` | X → d (PUBLIC), X → l (PRIVATE) | LINK | `RootMacros.cmake:1399-1404` → `:981-982` |
| same | creates `G__X` via `ROOT_GENERATE_DICTIONARY(… MODULE X DEPENDENCIES d)` | — | `RootMacros.cmake:1412-1421` |
| `ROOT_GENERATE_DICTIONARY` | `G__X.cxx` becomes an OBJECT lib linked PRIVATE into X, so the dictionary is **part of libX** | LINK | `RootMacros.cmake:756-759` |
| same | the custom command `DEPENDS ${MODULE_LIB_DEPENDENCY}` = the dep **libraries themselves** (so `G__Hist.cxx` waits for libMathCore/libMatrix/libRIO to be built) | ORDER | `RootMacros.cmake:691-692, 743-745`; observed in prior build `hist/hist/CMakeFiles/G__Hist.dir/build.make:246-249` |
| same | passes `-m lib<dep>_rdict.pcm` for each dep that has a `G__dep` | ORDER + HOST input | `RootMacros.cmake:617-635` |
| same, `STAGE1` | COMMAND = `$<TARGET_FILE:rootcling_stage1>`; DEPENDS `rconfigure` | HOST (in-tree target) | `RootMacros.cmake:643-649` |
| same, non-STAGE1, `CMAKE_PROJECT_NAME STREQUAL ROOT` | COMMAND = `env ROOTIGNOREPREFIX=1 $<TARGET_FILE:rootcling> -rootbuild`; DEPENDS `rootcling rconfigure` | HOST (in-tree target) | `RootMacros.cmake:652-663` |
| same, non-ROOT project only | `$<TARGET_FILE:ROOT::rootcling>` (IMPORTED from an installed ROOT) or `rootcling` on PATH | HOST (importable) | `RootMacros.cmake:664-676`. **Unreachable for ROOT's own libraries**, because `CMAKE_PROJECT_NAME` is `ROOT` |
| `ROOT_LINKER_LIBRARY` | X → `G__X`, `move_headers`, `${BUILTIN}_TARGET` | ORDER | `RootMacros.cmake:984-986, 992, 1008-1012` |
| `ROOT_EXECUTABLE` | if a target of that name already exists it **renames** the new one to `<name>_new` | — | `RootMacros.cmake:1444-1446` (relevant to injection, §5) |
| CMake semantics | `$<TARGET_FILE:t>` in a custom COMMAND adds a target-level dependency on `t` | ORDER | CMake `add_custom_command` docs ("references to target names in generator expressions imply target-level dependencies") |

### Per component

| Component | Edge | Class | Citation |
|---|---|---|---|
| **Core** | → `CLING` | ORDER | `core/CMakeLists.txt:42` |
| Core | → `rconfigure` (copies `ginclude/RConfigure.h` → `include/`) | ORDER | `core/CMakeLists.txt:16-25, 42` |
| Core | → `ensure_build_tree_marker` | ORDER | `core/base/CMakeLists.txt:260` |
| Core | `generateHeader(… root-argparse.py …)` → `TApplicationCommandLineOptionsHelp.h` | HOST (Python) | `core/CMakeLists.txt:37-40` |
| Core | dl, threads, atomic | LINK (PRIVATE) | `core/CMakeLists.txt:44-49` |
| Core | ZLIB (`find_package(ZLIB REQUIRED)`) | LINK (PRIVATE) | `core/zip/CMakeLists.txt:7,18` |
| Core | LibLZMA | LINK (PRIVATE) | `core/lzma/CMakeLists.txt:11-13` |
| Core | xxHash + LZ4 | LINK (PRIVATE) | `core/lz4/CMakeLists.txt:9-10` |
| Core | ZSTD | LINK (PRIVATE) | `core/zstd/CMakeLists.txt:5-7` |
| Core | PCRE2 or PCRE | LINK (PRIVATE) | `core/base/CMakeLists.txt:262-269` |
| Core | zip/lzma/lz4/zstd subdirectories are added unconditionally, so these codecs are required to *build* Core but **unused** by P0 (they are I/O codecs) | LINK req., OPT at runtime | `core/CMakeLists.txt:86-89` |
| Core | `thread/inc` added to **Core's PUBLIC** include dirs | COMPILE | `core/thread/CMakeLists.txt:69-71` |
| Core | dictionary `G__Core` **STAGE1** (`rootcling_stage1`); provides `TObject/TNamed/TAtt*/TString::Class()/Streamer()` that TH1 vtables need | HOST + LINK (dict in libCore) | `core/CMakeLists.txt:133-146`; need: `wasm/gates/g4/BLOCKER.md` |
| Core | `dlopen(libRIO)` then `dlopen(libCling)` + `dlsym CreateInterpreter`, `exit(1)` on failure; skipped only if `usedToIdentifyRootClingByDlSym` or `usedToIdentifyStaticRoot` is already visible | **RUNTIME, hit by P0** (§3) | `core/base/src/TROOT.cxx:2223-2256`, trigger `:468-477` |
| Core | `usedToIdentifyStaticRoot` is defined in `core/base/src/roota.cxx:2`, but **no CMakeLists in 6.40.04 compiles roota.cxx** | OPT (dormant path) | `grep -rn roota --include=CMakeLists.txt` finds nothing |
| Core | `gSystem->Load("libImt")` on first IMT request | RUNTIME, OPT | `core/base/src/TROOT.cxx:482-484` |
| **rootcling_stage1** | objects Clib + ClingUtils + Dictgen + Foundation_Stage1; links `clingMetaProcessor` (so Cling/Clang/LLVM static) | HOST | `core/rootcling_stage1/CMakeLists.txt:20-37` |
| rootcling_stage1 | → ClingUtils → CLING, LLVMRES | ORDER | `:52`; `core/clingutils/CMakeLists.txt:32,216`; `core/dictgen/CMakeLists.txt:36-41` |
| **CLING** (custom target) | aggregates `${CLING_LIBRARIES}` (+ intrinsics_gen, clang headers) | ORDER | `interpreter/CMakeLists.txt:439, 478-490` |
| interpreter | `add_subdirectory(interpreter)` is **unconditional**; there is no `cling` build option in 6.40.04 (only `builtin_cling/clang/llvm`, `clingtest`) | — | `CMakeLists.txt:380`; `cmake/modules/RootBuildOptions.cmake:85-86,98,190` |
| **Cling** (libCling) | links Core, RIO (PRIVATE); → `rootcling_stage1`, MetaCling → CLING, clangCppInterOp | LINK / ORDER | `core/metacling/src/CMakeLists.txt:126,133,136,84` |
| **rootcling** | executable links `RIO Cling Core Rint` | HOST (in-tree target) | `main/CMakeLists.txt:111-114` |
| **Thread** | → Core | LINK (PUBLIC) | `core/thread/CMakeLists.txt:63-64` |
| Thread | threads lib | LINK (PUBLIC) | `:74` |
| Thread | TBB (only `if(TBB_FOUND OR builtin_tbb)`) | LINK, OPT | `:65, 80-85` |
| Thread | dictionary STAGE1 | HOST (`rootcling_stage1`) | `:60` |
| **Imt** | `ROOT_LINKER_LIBRARY(Imt … DEPENDENCIES MultiProc)`, `PRIVATE Thread INTERFACE Core` (built even with `imt=OFF`) | LINK, OPT for P0 | `core/imt/CMakeLists.txt:11-26` |
| MultiProc | → Core, Net | LINK, OPT | `core/multiproc/CMakeLists.txt:32-34` |
| **RIO** | → Core, Thread | LINK (PUBLIC) | `io/io/CMakeLists.txt:63-65` |
| RIO | dl (PRIVATE), atomic (PUBLIC) | LINK | `:61-62, 69` |
| RIO | nlohmann_json (header-only, TBufferJSON) | LINK (PRIVATE) = COMPILE | `:70` |
| RIO | `$<TARGET_OBJECTS:RootPcmObjs>` (`rootclingIO.cxx`) | LINK | `:60`; `io/rootpcm/CMakeLists.txt:11` |
| RIO | liburing (only `if(uring)`) | OPT | `:72-75` |
| RIO | dictionary STAGE1 (`G__RIO`, DEPENDENCIES Core Thread) | HOST (`rootcling_stage1`) | `:105-131` |
| **MathCore** | → Core | LINK (PUBLIC) | `math/mathcore/CMakeLists.txt:185-186` |
| MathCore | → Imt **only `if(imt)`** | LINK (PRIVATE), OPT with `imt=OFF` | `:115-117, 187-188` |
| MathCore | threads | LINK (PRIVATE) | `:191` |
| MathCore | dictionary non-STAGE1 | HOST (`rootcling`) | `:119-189` (no STAGE1 flag) |
| MathCore | `Factory::CreateMinimizer` / `DistSampler` via plugin manager | RUNTIME, OPT (fit only) | `math/mathcore/src/Factory.cxx:91-92, 178-182` |
| **Matrix** | → MathCore | LINK (PUBLIC) | `math/matrix/CMakeLists.txt:79-80` |
| Matrix | dictionary non-STAGE1 | HOST (`rootcling`) | `:11, 81-82` |
| **Hist** | → MathCore, Matrix, RIO | LINK (PUBLIC) | `hist/hist/CMakeLists.txt:170-174` |
| Hist | dictionary non-STAGE1 over **all** headers (incl. THnChain, TPrincipal, TMultiDimFit, TSVDUnfold, TF1, TFormula) | HOST (`rootcling`) + LINK | `hist/hist/CMakeLists.txt:11-174` |
| Hist | `ROOT_SUPPORT_CLAD` if `clad` | OPT | `:178-180` |
| Hist | `TH1::Build` → `ObjectAutoRegistrationEnabled` → `gEnv` → `gROOT` → InitInterpreter | **RUNTIME, hit by P0** | `hist/hist/src/TH1.cxx:826`; `core/base/src/TROOT.cxx:315-336, 768` |
| Hist | `TVirtualHistPainter` / `TVirtualFitter` / `TFitEditor` / `TGLHistPainter` plugins | RUNTIME, OPT (Draw/Fit/GUI) | `TVirtualHistPainter.cxx:35-36`, `TVirtualFitter.cxx:119-120`, `TH1.cxx:4370-4371, 4591-4593` |
| Hist | `TFormula` JIT via `gInterpreter->ProcessLine` | RUNTIME, OPT for P0 (needed by TF1 katas) | `hist/hist/src/TFormula.cxx:688-697` |
| vdt | not referenced by Core/Thread/RIO/MathCore/Matrix/Hist CMakeLists; `minimal=ON` turns `vdt` OFF | OPT | `RootBuildOptions.cmake:180, 318-327` |
| `builtin_*` codecs/pcre/xxhash/nlohmann | select the in-tree source over `find_package`; defaults OFF | build-config only | `RootBuildOptions.cmake:99-113`; `builtins/{zlib,lzma,lz4,zstd,xxhash,pcre,nlohmann}` |
| `minimal=ON` | sets all `ROOT_BUILD_OPTION` defaults OFF **except** `builtin_llvm|builtin_clang|builtin_cling|shared|runtime_cxxmodules|thisroot_scripts` | — | `RootBuildOptions.cmake:193, 318-327` |

## 2. Native linker evidence (ROOT 6.40.02, x86_64)

Script: `linker-evidence.sh <Lib> [ShowFromLib]`. It counts `nm -D --undefined-only lib<Lib>`
symbols that each NEEDED ROOT lib defines. *strong* = defined as T/D/B/R (the lib's own code);
*any* also counts weak/unique inline or template copies.

| Library | NEEDED (ROOT/3rd-party only) |
|---|---|
| libCore | libpcre2-8, libz, liblzma, liblz4, libzstd, libdl, libpthread (no ROOT libs, **no libCling**) |
| libThread | libCore, libtbb |
| libRIO | libThread, libCore, libdl |
| libMathCore | libImt, libCore (conda build has `imt=ON`) |
| libMatrix | libMathCore, libCore |
| libHist | libMatrix, libMathCore, libRIO, libCore (**not** libThread) |
| libCling | libRIO, libCore, libz, libzstd, librt, libdl |

| Importer | from Core strong/any | MathCore | Matrix | RIO | Thread | Imt | tbb |
|---|---|---|---|---|---|---|---|
| libHist | 416 / 444 | 185 / 187 | **10 / 98** | **1 / 1** | — | — | — |
| libMatrix | 105 / 107 | 1 / 1 | — | — | — | — | — |
| libMathCore | 133 / 138 | — | — | — | — | 2 / 2 | — |
| libRIO | 555 / 586 | — | — | — | 10 / 11 | — | — |
| libThread | 147 / 160 | — | — | — | — | — | 5 / 5 |

What creates each edge:

- **Hist → RIO (1):** `TFile::Open(char const*, …)`, called only from `THnChain.cxx:141`.
  THnChain is in Hist's SOURCES and dictionary. It is a real use, but not on the P0 path.
- **Hist → Matrix (10 strong):** `TDecompSVD` (`TSVDUnfold.cxx:264-305`), `TDecompChol`
  (`TMultiDimFit.cxx:1343`), `TMatrixDSymEigen` (`TPrincipal.cxx:889`), plus
  `TMatrixT/TMatrixTSym/TMatrixTBase/TVectorT<double>::Class()` from dictionary and streamer
  code for members such as `TPrincipal.h:27-36` and `TMultiDimFit.h:28`. Also
  `TFitResult.h:28,58` (`TMatrixDSym`). The other 88 are weak template copies.
- **Hist → MathCore (185):** mostly `ROOT::Fit::*` (60) and `ROOT::Math::*` (64) from
  `HFitImpl.cxx` (64 `ROOT::Fit::` refs) and `TH1.cxx` (Chi2Test/KS/fit: `TH1.cxx:52-57,
  2546`). The rest is `TMath::*` and `TRandom3` (FillRandom). This is real code in `TH1.cxx`
  itself, a single TU, so MathCore is a hard link dependency even for P0.
- **RIO → Thread (10):** `TSemaphore`, `TRWSpinLock*Guard`, `TThread` (TFilePrefetch/TFileMerger).
- **MathCore → Imt (2):** `ROOT::TThreadExecutor` (parallel FitUtil). Absent with `imt=OFF`.
- **Matrix → MathCore (1):** `TMath::Hypot`.

Conclusion: every NEEDED edge is a real symbol use, not a nominal one. For P0 behaviour, only
Core and MathCore are exercised. Matrix, RIO and Thread are link-closure-only, forced by the
whole-package source list and `G__Hist`. RIO also returns as a *runtime* dlopen from Core (§3).

## 3. Core ↔ Cling: build-order vs runtime (answers task 3)

- **Build:** `add_dependencies(Core CLING rconfigure)` (`core/CMakeLists.txt:42`) is
  build-order only. Core's link line has no Cling (`:44-49`), and native `libCore.so` NEEDED
  has no libCling (§2). Confirmed.
- **Runtime:** libCling is loaded only through `dlopen` (`TROOT.cxx:2238-2239`) plus `dlsym`
  (`:2251, 2260`). **Not optional for P0.** Tiny native experiment
  (`~/.cache/rootwasm-p0/targets/native-dlopen/`: `p0.cxx`, linked `-lHist -lCore` only, run
  with `LD_DEBUG=files` and an `LD_PRELOAD` dlopen backtrace shim `shim.c`; reproduce with `bash experiments/native-dlopen.sh`):

  ```
  MARK before-ctor
  file=…/libRIO.so   dynamically loaded by …/libCore.so.6.40
  file=…/libCling.so dynamically loaded by …/libCore.so.6.40
  MARK after-ctor
  backtrace at dlopen(libCling):
    TROOT::InitInterpreter ← ROOT::Internal::GetROOT2 ← TEnv::Getvalue ← TEnv::GetValue
    ← ROOT::Experimental::ObjectAutoRegistrationEnabled ← TH1::Build ← TH1::TH1 ← TH1D::TH1D
  entries=10 bin3=2 mean=6.833333 std=2.211083 integral=45 nbins=10
  ```

  The same happens with `TH1::AddDirectory(false)`, because `TH1.cxx:826` evaluates
  `ObjectAutoRegistrationEnabled()` first, and that reads `gEnv` (`TROOT.cxx:325-326`) before
  the env var (`:338`). `TEnv::Getvalue` touches `gROOT` (`TEnv.cxx:474, 487`). The first
  `gROOT` after TROOT construction goes to `GetROOT2` → `InitInterpreter`
  (`TROOT.cxx:468-477`).
- **`-Dcling=OFF`:** no such option in 6.40.04. `interpreter/` is added unconditionally
  (`CMakeLists.txt:380`), and Core always adds `CLING` as an order dependency.
  `builtin_cling=OFF` means "use an external Cling", not "no Cling"
  (`RootBuildOptions.cmake:86, 360-364`). `minimal=ON` explicitly does **not** turn off
  `builtin_llvm/clang/cling` (`:320`).
- **Cross-compile/Emscripten support grep** (`CMakeLists.txt`, `cmake/`, `core/`, `io/`,
  `math/`, `hist/`, `main/`, `builtins/`): `CMAKE_CROSSCOMPILING` appears only at
  `CMakeLists.txt:565` (skip hsimple) and `RootConfiguration.cmake:498` (interference-size
  probe). There are **zero** hits for `EMSCRIPTEN`/`Emscripten`/`wasm`/`WebAssembly`, no
  `NATIVE_BINARY_DIR` outside roottest's macro (`RootMacros.cmake:2565`), and no
  `root_install_dir` / host-rootcling import for the ROOT project itself. Only bundled LLVM has
  its own cross support (a `NATIVE` tablegen sub-build, seen at
  `root-wasm-build/interpreter/llvm-project/llvm/NATIVE`), and that covers tablegen, not
  rootcling.

## 4. Minimal P0 target set and host/target split

**Target-side (wasm32) libraries, fixed by CMake LINK edges:**
`Core` (+ in-lib `G__Core`, codecs zlib/lzma/lz4+xxhash/zstd, pcre) → `Thread` → `RIO`
(+ RootPcmObjs, nlohmann header) → `MathCore` → `Matrix` → `Hist`. With `imt=OFF`, MathCore
does not link Imt, and `Imt`/`MultiProc`/`Net` are not in Hist's closure. The `Imt` target
itself is still defined.

**Also target-side for P0 to run (§3):** `libCling`, or an equivalent that satisfies
`InitInterpreter`. This is a runtime edge, not a link edge.

**Host-only tools:** `rootcling_stage1` (for G__Core, G__Thread, G__RIO), `rootcling` (for
G__MathCore, G__Matrix, G__Hist), `python3` (`root-argparse.py`), LLVM `llvm-tblgen`/
`clang-tblgen` (only if Cling is built at all), and CMake `configure_file` for RConfigure.h.
Both rootcling binaries must come from the **same 6.40.04 tree**: the dictionary format and
`-rootbuild` / `-writeEmptyRootPCM` flags are version-coupled, and G__X uses
`lib<dep>_rdict.pcm` produced by the same tool chain.

## 5. Recommended cross-build entry point

Flags below are verified as options in `RootBuildOptions.cmake`:

```bash
source ~/.root-kata-wasm/emsdk/emsdk_env.sh
emcmake cmake -G "Unix Makefiles" $S -DCMAKE_BUILD_TYPE=Release \
  -Dminimal=ON -Dimt=OFF -Druntime_cxxmodules=OFF -Dclad=OFF -Dfail-on-missing=OFF \
  -Dbuiltin_zlib=ON -Dbuiltin_lzma=ON -Dbuiltin_lz4=ON -Dbuiltin_zstd=ON \
  -Dbuiltin_xxhash=ON -Dbuiltin_pcre=ON -Dbuiltin_nlohmannjson=ON -Dbuiltin_freetype=ON
cmake --build . --target Hist   # do NOT run as a probe: builds wasm32 LLVM/Cling first
```

(`imt`:140, `runtime_cxxmodules`:157, `clad`:117, `builtin_*`:99-113, `minimal`:193,
`fail-on-missing`:191, `builtin_freetype`:91; Freetype is required even with `minimal=ON`, `SearchInstalledSoftware.cmake:248`.) Configure-verified on 6.40.04: exit 0, 264 s.

**Graph that `--target Hist` really pulls:** Hist → G__Hist (COMMAND `$<TARGET_FILE:rootcling>`
means a target-level dependency on `rootcling`) → `rootcling` links `Cling` → CLING →
LLVM/Clang for wasm32. Core → G__Core (`$<TARGET_FILE:rootcling_stage1>`) →
`rootcling_stage1` links `clingMetaProcessor`. The prior all-Emscripten 6.34.10 tree shows
the resolved commands as `core/rootcling_stage1/src/rootcling_stage1.js`
(`G__Core.dir/build.make:475`) and `bin/rootcling.js` (`G__Hist.dir/build.make:246,251`),
both linked by `em++` with no emulator prefix. The command-selection block in 6.40.04 differs
from 6.34.10 only in env/APPLE wrappers. It still uses `$<TARGET_FILE:…>` of in-tree targets.

**How native rootcling would be injected:** ROOT 6.40.04 offers **no supported mechanism** for
its own libraries. The only IMPORTED path, `ROOT::rootcling`, is gated on
`NOT CMAKE_PROJECT_NAME STREQUAL ROOT` (`RootMacros.cmake:664`). The candidate
no-source-patch injection is pre-declaring IMPORTED `rootcling_stage1`/`rootcling` via
`-DCMAKE_PROJECT_ROOT_INCLUDE=…`, exploiting the `_new` rename at `RootMacros.cmake:1444-1446`.
It was tested configure-only; the result is below.

**First expected architectural blocker:** `rootcling_stage1` and `rootcling` are in-tree
*target* executables. Under emcmake they are built as wasm (`.js`) and pull
Cling/Clang/LLVM into the wasm build before any Core object links. That matches the stall
recorded in `wasm/gates/g4/rootcling-crossbuild/CODEX-REVIEW.md`. libCling is a link
dependency of `rootcling`, not of Core. But separately, and after any successful link,
**Core's runtime `InitInterpreter` needs libCling for the P0 `TH1D` constructor** (§3).
Solving dictionary generation with host tools therefore does not remove Cling from the P0
runtime story.

### Configure-only injection experiment

Both configure runs used emsdk 4.0.9 with the flags above, pinned 6.40.04, and no build.
Directories: `~/.cache/rootwasm-p0/targets/cfg-inject{,-baseline}/`; scripts copied to `experiments/` (`configure-probe.sh`,
`inject-host-rootcling.cmake`, `build/configure.log`).

- **Baseline** (`+ -Dbuiltin_freetype=ON`): configure 258 s, generate 5 s, exit 0. `minimal=ON`
  still *requires* Freetype (`SearchInstalledSoftware.cmake:248`, for `graf`). Without it,
  configure fails, so `-Dbuiltin_freetype=ON` belongs in the entry-point flags. The generated
  graph for the pinned release (`build/CMakeFiles/Makefile2`) is:
  - `G__Core` ← `rconfigure`, `rootcling_stage1`. Command: `rootcling_stage1/src/rootcling_stage1.js -v2 -f G__Core.cxx`.
  - `G__Hist` ← `rconfigure`, `MathCore`, `Matrix`, `RIO`, `rootcling`. Command: `cmake -E env ROOTIGNOREPREFIX=1 …/bin/rootcling.js -rootbuild`.
  - `rootcling` ← `Core`, `complexDict`, `Cling`, `Rint`, `Thread`, `RIO`.
  - `Cling` and `rootcling_stage1` ← the full `interpreter/llvm-project/llvm/lib/*` set.
  - `Core` ← `ensure_build_tree_marker`, `BUILTIN_ZLIB`, `PCRE`, `BUILTIN_LZMA`, `xxhash`, `BUILTIN_LZ4`, **`interpreter/CLING`**, `rconfigure`, `G__Core`, `Clib`, ….

  This confirms on 6.40.04 what the 6.34.10 tree showed: `--target Hist` ⇒ wasm32 Cling + LLVM.
- **Injection** (`-DCMAKE_PROJECT_ROOT_INCLUDE=inject-host-rootcling.cmake`, 296 s, exit 1).
  The hook ran (`P0-PROBE: injected …`), and `ROOT_EXECUTABLE` renamed the in-tree targets
  (`Target rootcling_stage1 already exists. Renaming target name to rootcling_stage1_new`, and
  the same for `rootcling`). Configure then **fails**:

  ```
  CMake Error at core/rootcling_stage1/CMakeLists.txt:38 (target_compile_options):
    target_compile_options may only set INTERFACE properties on IMPORTED targets
  CMake Error at core/rootcling_stage1/CMakeLists.txt:40 (target_include_directories): …same
  CMake Error at main/CMakeLists.txt:121 (target_include_directories): …same
  -- Configuring incomplete, errors occurred!
  ```

  (The Freetype error at line 21 of that log is the independent issue above.) **Verdict:**
  there is no zero-patch injection. Using host rootcling for ROOT's own dictionaries needs a
  build-system change at exactly these points: `RootMacros.cmake:643-677` (command selection),
  `core/rootcling_stage1/CMakeLists.txt:38-52`, and `main/CMakeLists.txt:111-133`. Those are
  CMake edits, not ROOT source edits. Whether that is acceptable is a coordinator decision.

## 6. Open ambiguities a tiny experiment could resolve

1. **Host/target ABI in `_rdict.pcm` / dictionary.** Host x86_64 rootcling computes layouts
   and offsets (`TProtoClass`) for LP64. wasm32 is ILP32. Does rootcling honour a
   `--target`/`-compilerI` sysroot so `G__Hist.cxx` + `libHist_rdict.pcm` are wasm32-correct,
   or does P0 not read the pcm without Cling? Tiny check: run host rootcling on `TH1D` with
   and without Emscripten `-compilerI` and diff `G__*.cxx` and `rdict.pcm` sizes/offset
   tables. No build needed.
2. **Can the InitInterpreter edge be satisfied by ROOT-supported configuration?** For example,
   is `usedToIdentifyStaticRoot` (`roota.cxx`) linkable in any supported configuration
   (it is not compiled by 6.40.04 CMake), and is there a `.rootrc`/env setting that stops
   `TH1::Build` from reaching `gROOT`? Tiny check: rerun `native-dlopen/p0` with
   `ROOT_OBJECT_AUTO_REGISTRATION=0` and with a `.rootrc` setting `Root.ObjectAutoRegistration: 0`.
   **Env var already run:** `ROOT_OBJECT_AUTO_REGISTRATION=0` gives the identical backtrace,
   because `gEnv` is read first (`TROOT.cxx:325` before `:338`). The rc route cannot help either:
   `TEnv::Getvalue` itself touches `gROOT` (`TEnv.cxx:474, 487`). Still open: whether any
   supported static-ROOT configuration exposes `usedToIdentifyStaticRoot`.
3. ~~Does `$<TARGET_FILE:rootcling_stage1>` pick a pre-declared IMPORTED target?~~
   **Resolved: no.** Configure fails (§5 experiment).
   The remaining ambiguity is which minimal CMake-only change the project accepts: an
   `if(TARGET)`/cache-variable override in `RootMacros.cmake:643-677`, plus guarding the
   in-tree `rootcling*` definitions. Separately, `Core → CLING` (`core/CMakeLists.txt:42`)
   still forces the LLVM build under `--target Hist` even with host rootcling. So the same
   change must also address that ORDER edge. A configure-only check could use `Makefile2` to
   see whether `Core/all` still lists `interpreter/CLING`.
4. **Is Matrix/RIO/Thread closure avoidable at wasm link time?** With static archives and
   `--gc-sections`, does anything on the P0 path keep `THnChain`/`TPrincipal` alive, given that
   `G__Hist` registers all classes in static initializers? That can only be answered once
   libraries exist, so it is not a tiny experiment today.
