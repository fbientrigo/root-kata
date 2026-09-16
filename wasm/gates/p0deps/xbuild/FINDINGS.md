# Phase 3 bounded cross-build: ROOT `Core` under Emscripten with a HOST rootcling (Worker C)

## M1 verdict (coordinator, 2026-09-15): **HIST-CLOSURE-BUILT**

`run.sh configure && run.sh graph && run.sh hist && run.sh inspect` prints `xbuild Hist PASS`
from a clean cache (build 606 s at -j4). ROOT's own targets build all six P0 libraries for wasm:

| library | bytes |
| --- | ---: |
| libCore.so | 7233446 |
| libThread.so | 436463 |
| libRIO.so | 7614424 |
| libMathCore.so | 3413748 |
| libMatrix.so | 2042189 |
| libHist.so | 5585384 |

The gate now checks **every member** of every builtin archive (not the first, per the Core
review), all six libraries, and that these are defined: `TObject::Class()`,
`TVersionCheck::TVersionCheck(int)`, `TROOT::InitInterpreter()`, `TH1D::Class()`, the `TH1D`
constructor, `TFormula::Class()`, `TMatrixT<double>::Class()`, `TFile::Class()`; plus 0
non-wasm members, 0 undefined codec/regex symbols and 0 `-pthread` in compile flags.

Changes in M1:

| Item | Change | Class |
| --- | --- | --- |
| Host generator version mismatch | `run.sh` fetches and sha256-checks the **pinned CERN ROOT 6.40.04** binary release and uses its `rootcling` (sha256 `287ff87deef0eed0fedd32e7d59bdadd22dcb45a5c592c9e08d8d140212ef261`, verified locally; root.cern publishes no `.sha256`). The conda 6.40.02 mismatch is gone. | build config |
| Browser runtime is single-threaded | `CheckCompiler.cmake`: no `-pthread` under Emscripten. | PLATFORM PORT |
| G7 runtime ABI | configure with `-DCMAKE_CXX_FLAGS=-fwasm-exceptions -DCMAKE_C_FLAGS=-fwasm-exceptions`. | PLATFORM PORT |
| `TMapFile.cxx:854: use of undeclared identifier 'SEM_R'` | `HAVE_SEMOP` excludes `R__EMSCRIPTEN` (as it already excludes `R__WINGCC`). | PLATFORM PORT |

Dictionary generation transfers beyond Core: `../dictprobe/run.sh MathCore` passes
(generator exit 0, 0 host-private STL spellings, whole dictionary compiled by em++), which was
the Core review's recorded next experiment. `run.sh Core` still passes with the same script.

Three further platform ports (`TROOT::GetSharedLibDir`, `TFile` getxattr, `TUUID` getifaddrs)
were required to *load* these libraries; they are documented in
[../../rootlight/FINDINGS.md](../../rootlight/FINDINGS.md) (M2), which also records the
side-module packaging and the Node run.

Independent review: [M1/M2 review](../../rootlight/CODEX-REVIEW-M2.md).
The review strengthens the graph check to Hist's complete order closure,
propagates configure/build/graph errors, makes default `all` build Hist, and
checks all members of every `.a` under builtins with tool/read errors fatal.
The eight defined symbols are exact matches. These checks prove object
format and selected definitions, not full runtime closure or ROOT behavior.
`build` remains the explicit historical Core-only operation; its output alone
cannot satisfy the new six-library Hist inspection.

The Core-stage report follows unchanged as historical evidence.

## Current verdict (resolution, coordinator, 2026-09-15): **CORE-TARGET-BUILT**

ROOT's own `Core` CMake target builds under Emscripten 4.0.9 from the pinned 6.40.04 source. It
uses host rootcling (conda-forge 6.40.02, version-mismatched) for `G__Core`, and no
LLVM, Cling or rootcling is built for wasm.

Independent fresh-cache review reproduces this on 2026-09-15: configure exit 0,
Core build exit 0 in 398 seconds, 14-node order closure with no forbidden targets,
and both `xbuild Core PASS` and `dictprobe PASS`. The 6,877,437-byte Core output
is a relocatable object, not a loaded runtime library; see the review below.

`run.sh configure && run.sh graph && run.sh build && run.sh inspect` prints `xbuild Core PASS`.
The inspection checks below are narrow; the [independent Core review](../CODEX-REVIEW-CORE.md)
documents phase exit-status and stale-artifact limits and supplements archive sampling with
an all-member audit. The inspection reports:

- `lib/libCore.so` is a WebAssembly module.
- `TObject::Class()` from `G__Core` is defined.
- 0 non-wasm archive members were skipped at link.
- The first member of each discovered builtin archive (zlib, lz4, lzma, zstd, pcre) is wasm.
- 0 undefined codec or regex symbols remain.

Changes applied on top of the original three-hunk patch (all in `host-rootcling.patch`,
classification in brackets):

| Blocker (verbatim first error) | Change | Class |
| --- | --- | --- |
| `G__Core.cxx:315: use of undeclared identifier '__gnu_cxx'` | Target frontend for the host generator via `-DROOT_HOST_ROOTCLING_EXTRA_ARGS`, passed as `EXTRA_CLING_ARGS` by `RootMacros.cmake`. The args mirror em++ (`-target wasm32-unknown-emscripten`, `--sysroot`, `-DEMSCRIPTEN`, `include/{fakesdl,compat}`) plus the generator-only `../dictprobe/overlay/stdlib.h`. See `../dictprobe/FINDINGS.md`. | PLATFORM PORT (host tool env) |
| `clib/src/detach.c:67: call to undeclared function 'close'` | `RConfig.hxx`: new `__EMSCRIPTEN__ && __wasm32__` block defining `R__EMSCRIPTEN`, `R__UNIX`, `R__BYTESWAP` (wasm is little-endian) and `NEED_SIGJMP`. No platform was previously recognised, so `R__UNIX` was undefined. | PLATFORM PORT (platform identification) |
| `TUnixSystem.cxx:728: use of undeclared identifier 'sys_nerr'`, `:3462 'FIONBIO'` | Add `R__EMSCRIPTEN` to the two existing platform lists: `<sys/ioctl.h>` include and `strerror` (musl). | PLATFORM PORT (existing platform guards) |
| `No rule to make target 'builtins/ZSTD-prefix/lib/libzstd.a'` / `'zdict.h' file not found` | `builtins/zstd`: `add_dependencies(ZSTD::ZSTD BUILTIN_ZSTD)` (as `builtins/lz4` already does) and forward `CMAKE_TOOLCHAIN_FILE`. | PLATFORM PORT (build system) |
| `wasm-ld: warning: liblz4.a / libz.a: archive member ... is neither Wasm object file nor LLVM bitcode` (silently native x86-64 builtins) | Forward `CMAKE_TOOLCHAIN_FILE` in `builtins/lz4` and `builtins/zlib` (same pattern as lzma). | PLATFORM PORT (build system) |

Still open (not claimed):

- `libCore.so` is the pinned-emcc output of bare `-shared` (see CODEX-REVIEW). It is not a
  loaded side module, and it has not been linked or executed in node or Chromium.
- `-pthread` is still in the flags.
- `TROOT::InitInterpreter` is present and unchanged, so runtime still requires the Cling
  edge.
- Non-empty PCM generation segfaults on host/target serialization layout disagreement
  (`../dictprobe/FINDINGS.md`). **Correction:** pinned upstream MathCore, Matrix and Hist
  explicitly request `-writeEmptyRootPCM`, as do RIO and Thread, and all five generated
  commands preserve it. Non-empty PCM is unsupported but is not an established blocker
  for these stock targets.

The historical Worker C report follows unchanged.

## Historical verdict (Worker C): **BLOCKED-AT-COMPILE**

`G__Core.cxx` does not compile for wasm32. The host rootcling parsed ROOT's headers against the
**host C++ standard library (libstdc++)** and spelled libstdc++-private types into the dictionary.
Emscripten's libc++ has no such types.

```
build/core/G__Core.cxx:315:81: error: use of undeclared identifier '__gnu_cxx'
  315 |    static TGenericClassInfo *GenerateInitInstanceLocal(const ::reverse_iterator<__gnu_cxx::__normal_iterator<TString*,vector<TString> > >*)
build/core/G__Core.cxx:315:110: error: 'TString' does not refer to a value
...
fatal error: too many errors emitted, stopping now [-ferror-limit=]
20 errors generated.
gmake[3]: *** [core/CMakeFiles/G__Core.dir/build.make:496: core/CMakeFiles/G__Core.dir/G__Core.cxx.o] Error 1
```

**Result label:** host rootcling 6.40.02 vs source 6.40.04 (version-mismatched).

**Classification:** PLATFORM PORT (host/target toolchain split), not SEMANTICS. No ROOT C++
source is wrong. The generated dictionary is simply specific to the stdlib implementation of
whichever interpreter produced it. The fix is not a trivially small CMake change, though
(see the diagnostic below), so I stopped here as instructed.

What did work, in order:

1. **Patched configure.** Exit 0 in 219 s.
2. **Core's build graph.** It no longer contains any interpreter, CLING, rootcling or LLVM node
   (evidence below).
3. **Host rootcling.** It ran for `G__Core` with the STAGE1 options and produced `G__Core.cxx`
   (28017 lines).
4. **Builtins.** zlib, lz4, xxhash, pcre and nlohmann built for wasm. lzma built after a
   3-line toolchain-forwarding fix.

Core's non-dictionary objects (`base/`, `cont/`, `meta/`, …) were **never attempted**, because
`Core/all` waits on `G__Core/all`. Their wasm compile status is still unknown. Step 4
(artifact inspection) was not reached. No libCore exists.

Time used: about 30 min of the 90 min time-box.

## Commands

All commands are in `run.sh` (heavy outputs go to `~/.cache/rootwasm-p0/xbuild/`):

```
run.sh configure    # cp -a pinned src -> xbuild/src, apply host-rootcling.patch, emcmake cmake (§5 flags + -DROOT_HOST_ROOTCLING)
run.sh graph        # Makefile2 closure of core/CMakeFiles/Core.dir/all -> core-graph.txt
run.sh build        # cmake --build . --target Core -j4 -> build.log
run.sh diag-libcxx  # diagnostic only, see below
```

- Toolchain: emcc 4.0.9 (`bbf1caa6e24f64fca9eb6a13a9e02d3f42123e77`), verified by `run.sh`.
- Configure flags: exactly `targets/FINDINGS.md` §5, including `-Dbuiltin_freetype=ON`, plus
  `-DROOT_HOST_ROOTCLING=<path>`.
- Logs in `~/.cache/rootwasm-p0/xbuild/`:
  - `configure.log`
  - `core-graph.txt`
  - `g__core-command.txt`
  - `build-attempt2.log`: the blocker run.
  - Attempt 1 (the lzma failure) was overwritten. Its excerpt is below, and `run.sh` now rotates
    `build.log`.

## Host rootcling provenance

| | |
|---|---|
| Preferred | `https://root.cern/download/root_v6.40.04.Linux-debian13-x86_64-gcc14.2.tar.gz` (340,572,284 bytes, matches host Debian 13). The download averaged about 350 KiB/s, so it would take more than 10 min; the rule says skip. The background curl also died after 10:02 at 216 MiB. **Not used**, and no sha256 because the file is incomplete. |
| Used | conda-forge `root_base-6.40.02-cxx23_h0aec611_2` in `/home/fabian/thesis/FairShip/.pixi/envs/default/bin/rootcling`, sha256 `84809b688c01fa1ecd3d554102fbe1408722ae52c064163731983b28093fa4e7` |

I do not expect the version mismatch to be the cause. A CERN 6.40.04 build is also a
libstdc++ (gcc14.2) interpreter, so it would hit the same mechanism (next section).

## Why the dictionary is libstdc++-shaped (mechanism, with citations)

- **Installed `rootcling` is the stage-2 driver.**
  - `main/src/rootcling.cxx:31` sets `fBuildingROOTStage1 = false`.
  - In that mode rootcling does not create its own `cling::Interpreter`. It uses TCling's,
    through `TROOT` (`core/dictgen/src/rootcling_impl.cxx:4245-4260`).
  - TCling finds the C++ stdlib by querying the compiler that cling was *built* with
    (`interpreter/cling/lib/Interpreter/CIFactory.cpp:338-366`).
  - For conda that is a nonexistent build-farm g++, so the build log shows
    `ERROR in cling::CIFactory::createCI(): cannot extract standard library include paths!`.
  - It then falls back to clang's default host headers: `Possible C++ standard library mismatch,
    compiled with __GLIBCXX__ '20250808' … runtime … '20260626'`.
- **`-compilerI` does not retarget anything.**
  - ROOTMacros passes em++'s implicit include dirs as `-compilerI…/emscripten/cache/sysroot/include/c++/v1`
    (`RootMacros.cmake:718-721`).
  - That option only *suppresses duplicate `-isystem`* (`rootcling_impl.cxx:3693-3694, 4062-4069`).
    It adds no include path.
  - Result: `G__Core.cxx` contains 236 `__gnu_cxx::__normal_iterator` and 24 `std::__cxx11`
    spellings, and 0 `std::__1`.
- **The C++ standard differs too.** The host interpreter is a cxx23 build, while the wasm
  configure recorded 201703L. Every parse warns:
  `RConfigure.h:29: "The C++ standard in this build does not match ROOT configuration (201703L)"`.
  This is non-fatal, but it is another host/target skew.

### Diagnostic (not part of the build): force Emscripten libc++ into the host interpreter

`run.sh diag-libcxx` reruns the exact generated `G__Core` command with
`EXTRA_CLING_ARGS="-nostdinc++ -isystem $EMSDK/.../sysroot/include/c++/v1"`. `TCling` reads this
env var at `core/metacling/src/TCling.cxx:1453-1461`. Result: **rootcling exit=139** (segfault).

```
Warning in cling::IncrementalParser::CheckABICompatibility(): Failed to extract C++ standard library version.
.../sysroot/include/c++/v1/__mbstate_t.h:40:12: fatal error: 'bits/alltypes.h' file not found
```

- Emscripten's libc++ needs the wasm musl sysroot (`bits/alltypes.h`).
- Pointing an **x86_64 host interpreter** at wasm32 libc and libc++ headers means retargeting
  cling's whole target environment: triple, libc and PCH.
- That PCH is `etc/allDict.cxx.pch`, which the host ROOT built against libstdc++.
- That is not a small build-system flag. It is the architectural host/target mismatch: a
  dictionary generator has to parse with the **target** stdlib and ABI (wasm32 ILP32,
  libc++).

## The patch: `host-rootcling.patch` (CMake only, 3 files, all PLATFORM PORT)

Apply it with `patch -p1` against pinned 6.40.04; `--dry-run` is clean. It touches no ROOT C++
source.

1. **`cmake/modules/RootMacros.cmake` @643 (command selection).**
   - With `ROOT_HOST_ROOTCLING` set, both STAGE1 and non-STAGE1 dictionaries run
     `${ROOT_HOST_ROOTCLING} -rootbuild`.
   - `ROOTCLINGDEP` becomes `rconfigure` only.
   - STAGE1 keeps `pcm_name` empty, as upstream `:648` does.
   - This removes both `$<TARGET_FILE:rootcling_stage1>` and `$<TARGET_FILE:rootcling>`, and with
     them the implicit target-level edges, plus the `DEPENDS rootcling`.
   - Why `-rootbuild` for STAGE1 too: the real stage1 has `gBuildingROOT = fBuildingROOTStage1 = true`
     (`rootcling_impl.cxx:6085`). Stage-2 rootcling only sets `gBuildingROOT` via `-rootbuild`
     (`:3959-3963`, option at `:3550`).
   - Why no `ROOTIGNOREPREFIX=1` (upstream non-STAGE1 `:652-663` sets it): that variable makes TROOT
     ignore the compiled-in install prefix (`TROOT.cxx:3138-3141`). That is right for a build-tree
     rootcling and wrong for an *installed* one.
2. **`core/CMakeLists.txt` @42.** With `ROOT_HOST_ROOTCLING` set, the line becomes
   `add_dependencies(Core rconfigure)`, dropping the build-order-only `CLING` edge
   (targets/FINDINGS §3).
3. **`builtins/lzma/CMakeLists.txt` @37 (toolchain feature detection, added after build attempt 1).**
   - Forwards `CMAKE_TOOLCHAIN_FILE` to the xz ExternalProject.
   - Without it, xz's `test_big_endian` fails under a bare emcc
     (verbatim below). With it, configure, build and install succeed.
   - This is generic: it applies whenever a toolchain file is set, not only for Emscripten.

Deliberately **not** patched:

- The in-tree `rootcling_stage1` target (`core/rootcling_stage1/CMakeLists.txt`) and the
  `rootcling/genreflex/rootcint` targets (`main/CMakeLists.txt:111-133`) are still *defined*.
  After hunk 1 nothing in Core's graph references them.
- `add_subdirectory(interpreter)` still configures LLVM/Cling for wasm. That stays within the
  known budget (configure 219 s, of which reconfigure 17 s) and is never built for `--target Core`.

### Build attempt 1: first failure, before hunk 3 (verbatim)

```
CMake Error at /usr/share/cmake-3.31/Modules/TestBigEndian.cmake:72 (message):
  no suitable type found
Call Stack (most recent call first):
  /usr/share/cmake-3.31/Modules/TestBigEndian.cmake:37 (__TEST_BIG_ENDIAN_LEGACY_IMPL)
  cmake/tuklib_integer.cmake:85 (test_big_endian)
  CMakeLists.txt:298 (tuklib_integer)
gmake[2]: *** [CMakeFiles/Makefile2:13302: builtins/lzma/CMakeFiles/BUILTIN_LZMA.dir/all] Error 2
```

The ExternalProject passed only `-DCMAKE_C_COMPILER=emcc` (`builtins/lzma/CMakeLists.txt:35-37`),
not the Emscripten toolchain file. I verified the fix in scratch first, re-running xz's configure
with `-DCMAKE_TOOLCHAIN_FILE`, which gave exit 0.

## Graph evidence: `core-graph.txt`, from `build/CMakeFiles/Makefile2`

```
direct deps of core/CMakeFiles/Core.dir/all:
  move_headers, ensure_build_tree_marker, BUILTIN_ZLIB, PCRE, BUILTIN_LZMA, xxhash, BUILTIN_LZ4,
  core/rconfigure, core/G__Core, core/clib/Clib
closure (13): + gitinfotxt, builtin_nlohmann_json_incl, Core itself
FORBIDDEN (interpreter/|CLING|rootcling|Cling|llvm|clang): none
```

- **Unpatched baseline** (same checker on `targets/cfg-inject-baseline`): an 814-node closure
  including `interpreter/CMakeFiles/CLING.dir/all` and the `LLVM*` libraries.
- **Resolved command** (`G__Core.dir/build.make:483`):
  `…/pixi/envs/default/bin/rootcling -rootbuild -v2 -f G__Core.cxx -s …/lib/libCore.so … -writeEmptyRootPCM -DR__USE_URANDOM … -compilerI<emsdk sysroot> …`

## Stage-1 vs installed-rootcling differences (observed and cited)

| Aspect | Real `rootcling_stage1` | Installed `rootcling` used as a stage-1 substitute |
|---|---|---|
| Driver flag | `fBuildingROOTStage1=true` (`core/rootcling_stage1/src/rootcling_stage1.cxx:40`) | `false` (`main/src/rootcling.cxx:31`). No CLI flag can set it. |
| Interpreter | Own `cling::Interpreter` (`rootcling_impl.cxx:4245-4252`) | TCling via `TROOT`, which carries the **host ROOT's own loaded Core dictionary and PCH** (`:4253-4260`) |
| Include/etc dir | `CMAKE_BINARY_DIR/include`, `/etc` (`rootcling_stage1.cxx:25-33`) | Host install prefix |
| Emitted extras | none | `EmitTypedefs/EmitEnums` and `FinalizeStreamerInfoWriting` (`rootcling_impl.cxx:2653-2659, 4818-4820`). It wrote `lib/libCore_rdict.pcm` (668 B) even though STAGE1 declares no pcm output. |
| `-writeEmptyRootPCM` | honoured | honoured (suppresses fwd decls, `:4854-4867`) |
| Exit | n/a | 0 (with the stdlib-extraction ERROR and C++ standard warnings above) |

## Single smallest next step

Before any further build, answer one question: **can a cling-based rootcling running on x86_64
parse `Core`'s LinkDef against Emscripten's full wasm32 sysroot?**

1. Rerun `run.sh diag-libcxx` with the complete target include set:
   `EXTRA_CLING_ARGS="-nostdinc -nostdinc++ -isystem <sysroot>/include/c++/v1 -isystem <sysroot>/include"`.
   Here `<sysroot>` is `$EMSDK/upstream/emscripten/cache/sysroot`.
2. Optionally add `--target=wasm32-unknown-emscripten`.
3. Check whether it exits 0 and whether `G__Core.cxx` then compiles with em++.

The command only changes an env var in `run.sh` and takes about 1 min; no CMake or C++ changes.

- **If it still crashes or conflicts with the host PCH:** the host-tool route for ROOT
  dictionaries is architecturally closed. The remaining option is a generator that runs cling
  with the target stdlib, such as a wasm32 cling under node, which is the path this experiment
  was meant to avoid.
- **If it passes:** make the patch pass those args, still CMake-only, and resume
  `--target Core`. Core's non-dictionary objects are the next unknown.
