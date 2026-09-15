# VERDICT: PARTIAL

Independent final review, 2026-09-15, on `experiment/root-wasm-subset`.
The conditional interpreter conclusion and ROOT-target dependency map hold for the
observed P0 workload. The proposed build is a valid investigation, not yet a
usable ROOT Light architecture: dictionary generation is blocked, several
platform details remain, and a Cling-free initialization port is unproven.
This review qualifies the synthesis in [VERDICT.md](VERDICT.md); worker findings
remain historical evidence. No new large build was started.

# VERIFIED:

- Re-ran `bash wasm/gates/p0deps/runtime/run.sh` against native ROOT 6.40.02 and
  6.34.10. All reported outcomes reproduced, including byte-identical ordinary
  output across the two releases. Decisive 6.40.02 rows:

  | Run | Exit | libCling requests | Denied requests | Output against A |
  | --- | ---: | ---: | ---: | --- |
  | A | 0 | 1 | 0 | reference |
  | B | 1 | 1 | 1 | different, empty |
  | D_B | 1 | 1 | 1 | different, empty |
  | E1 | 0 | 0 | 0 | identical |
  | E0 | 0 | 0 | 0 | ownership differs |
  | C_deny_autoreg | 1 | 1 | 1 | control fails |
  | static_init_deny | 0 | 0 | 0 | no constructor workload |

  E1's final maps contain no libCling. The denied control logs a real loader
  failure and `Fatal in <TROOT::InitInterpreter>`. The shim intercepts both
  `dlopen` and `dlmopen`, and its nonexistent-path load supplies a real
  `dlerror()`. The positive control establishes that denial works even with
  autoregistration interposition; its first interpreter operation aborts, so
  its later reflection and TF1 operations are not independently tested under
  denial. No plugin load was observed in this workload.
- E1 is valid **diagnostic isolation** of the autoregistration query's
  initialization side effect. It returns the observed/default enabled value;
  `GetDirectory()` stays non-null and all printed P0 values match A. It is
  evidence that these compiled TH1D/TAxis operations can run without TCling,
  not a proposed implementation of ROOT's configuration API.
- Checked pinned 6.40.04 source: `TH1.cxx:826` evaluates autoregistration before
  `AddDirectoryStatus`; `TROOT.cxx:315-345` reads `gEnv` before the environment;
  `TEnv.cxx:474,487` uses `gROOT`; `GetROOT2` calls `InitInterpreter` at
  `TROOT.cxx:468-477`. The missing-library path exits at `:2223-2256`.
  The [ROOT 6.40 source reference](https://root.cern.ch/doc/v640/TROOT_8cxx_source.html)
  corroborates this initialization mechanism. Binary reproduction is 6.40.02,
  not a runtime test of 6.40.04.
- Re-ran `targets/linker-evidence.sh Hist Matrix`: Matrix **10 strong / 98 total**,
  MathCore **185 / 187**, RIO **1 / 1**, Core **416 / 444**. These are matches
  between undefined and exported dynamic symbols, not call counts. Pinned
  CMake and the generated Hist link response file agree on the six ROOT
  libraries. Core has no Cling link edge; the explicit CLING dependency is
  build order, and dictionary commands introduce separate tool/order edges.
  [CMake's custom-command documentation](https://cmake.org/cmake/help/v3.21/command/add_custom_command.html)
  confirms that `TARGET_FILE` references introduce target-level dependencies.
- `host-rootcling.patch` dry-runs cleanly on the pinned source. Independently
  traversed generated `Makefile2`: patched Core has **13** nodes, patched Hist
  **24**, with no interpreter/CLING/rootcling/LLVM/Clang build node in either
  closure. Hist reaches exactly Core, Thread, RIO, MathCore, Matrix and Hist.
  Their source lists and ROOT-generated dictionary machinery are retained.
- Independently recompiled the existing `G__Core.cxx` with pinned em++ 4.0.9,
  C++17 and the generated include response file. It failed at line 315 on
  `__gnu_cxx`, reproducing the host-libstdc++/target-libc++ blocker without
  rebuilding Core. Cache logs confirm lzma's successful cross-build after
  toolchain forwarding. No libCore runtime artifact exists.
- No manual ROOT source manifest, handwritten Class/Streamer, interpreter
  stub, or histogram reimplementation occurs in `p0deps/`. The interposition
  shims are native audit instrumentation only. The pre-existing `gcore/`
  **does** compile an ordered manual source manifest; it is retired diagnostic
  work and is excluded from this commit, as is its unrelated
  `g2/rconfigure.cmake` support change. Neither is attributed to this session.
- All five session shell scripts passed `bash -n`; the review's six required
  section names and the absence of build artifacts in `p0deps/` were checked.

# INVALIDATED:

- E1 does **not** preserve every ROOT configuration: it bypasses `.rootrc`,
  `ROOT_OBJECT_AUTO_REGISTRATION`, thread-local state and explicit enable/disable
  changes. Matching output covers the default probe, not directory membership
  identity, directory-owned deletion, or every lifetime path. A production
  constant-return replacement would change ROOT semantics and is rejected.
- “Only load and CreateInterpreter” understates stock initialization.
  `TROOT.cxx:2258-2320` also schedules TROOT cleanup, locates DestroyInterpreter,
  adds the interpreter to cleanups, sets `fgRootInit`, registers buffered
  modules, clears that buffer and calls `Initialize()`. E1 bypasses all of this.
  Simply removing `exit(1)` or returning early is not a validated platform port.
- The asserted host `allDict.cxx.pch` cause is not established and conflicts
  with the normal rootcling branch: `TCling.cxx:1093-1096` detects
  `usedToIdentifyRootClingByDlSym`; the installed executable exports it.
  PCH attachment at `:1399-1428` is inside `if (!fromRootCling)`.
  Installed rootcling still uses TCling and host stdlib discovery, but does not
  ordinarily attach that application PCH. Missing `bits/alltypes.h` proves an
  incomplete include environment; the recorded segfault does not close every
  native host-generator route.
- The maps/linker audit does not prove that only Core/MathCore/Hist code
  executes, or that RIO/Matrix/Thread execute no initialization code.
  Mapped libraries and symbol resolution are not execution traces. Additional
  `LD_DEBUG=bindings` inspection is also insufficient: native libHist has
  `BIND_NOW`. MathCore is a verified package link requirement; no exclusive
  list of libraries executing P0 calls is established.
- The displayed “Core → Thread → RIO → MathCore → Matrix → Hist” is a build
  ordering, not a chain of direct dependencies. MathCore depends on Core,
  not RIO. Whole-TU reasoning alone does not exclude linker garbage collection;
  the conservative six-target closure follows ROOT's declared package edges
  and dictionary coverage, not a proof that all code survives wasm linking.
- The current build does not produce the recommended static archives:
  `CMakeCache.txt` has `shared=ON`, and Core's link command uses `-shared`.
  In **pinned 4.0.9**, `tools/link.py:761-770` makes bare `-shared` without
  SIDE_MODULE emit a relocatable static object. Current online Emscripten docs
  describe newer behavior, so they cannot replace this pinned-source check.
  `-pthread` also appears in compile/link flags despite `imt=OFF`
  (`CheckCompiler.cmake:211-216,243-244`). Single-threaded G7 compatibility,
  wasm exception ABI and final side-module linking remain separate obligations.
- Builtin zstd is linked by Core but its ExternalProject is absent from the
  observed Core/Hist Makefile2 order closures; its expected archive does not
  exist. Its CMake command also lacks target compiler/toolchain forwarding
  (`builtins/zstd/CMakeLists.txt:44-61`). The three-file patch is not evidence
  that every builtin will be scheduled and built for wasm correctly.
- The proposed environment-only retry does not work as written with
  `run.sh diag-libcxx`: that script overwrites `EXTRA_CLING_ARGS` unconditionally.
  Script exit zero is not a successful build verdict either: xbuild logs an
  error then echoes its status; runtime intentionally observes failing runs.

# MINIMUM DEPENDENCIES:

For the untouched ROOT package boundary, the **candidate**, not proven minimal
wasm executable, comprises:

| ROOT target | Direct ROOT link dependencies |
| --- | --- |
| Core | none; platform libraries and codec/regex dependencies |
| Thread | Core |
| RIO | Core, Thread |
| MathCore | Core; Imt only when enabled |
| Matrix | MathCore; Core transitively |
| Hist | MathCore, Matrix, RIO; Core and Thread transitively |

Use `imt=OFF` to remove Imt/MultiProc/Net/TBB from this package closure; that
setting does not remove ROOT's generic pthread compilation flags. Core also
requires zlib, lzma, lz4, xxhash, zstd and PCRE/PCRE2; RIO uses nlohmann headers
and RootPcmObjs. No P0 plugin requirement was observed. Stock 6.40 has the
additional runtime RIO/Cling initialization edge; its removal needs a verified
port. Native E1 does not demonstrate a linkable Cling-free wasm closure.

Host tools are ROOT's genuine dictionary generator(s), Python and CMake;
LLVM/Clang are dependencies of a native generator if one must be built, not
necessarily target runtime libraries. Installed 6.40.02 stage-2 rootcling is a
version-mismatched diagnostic substitute, not proven equivalent to the pinned
stage-1 generator. Generated C++ and any consumed PCM/layout metadata must be
valid for target libc++, wasm32 and the target C++ standard.

# ARCHITECTURE:

**Retain ROOT's own Core and eventual Hist CMake targets.** The host-command
selection, removal of a build-order CLING edge, and lzma toolchain forwarding
are platform/build-system adaptations: they change tools, not ROOT algorithms.
The patch is experimentally sound for graph isolation, but stage-2 substitution
for STAGE1 changes generator mode and creates an undeclared PCM artifact;
`-rootbuild` does not set `fBuildingROOTStage1`. Do not treat it as finished
host-tool support.

A Cling-free platform profile is acceptable only if genuine compiled ROOT
behavior is preserved: configuration and directory ownership, dictionary
registration/metadata availability, initialization state and teardown must have
explicit evidence. Unsupported interpreter services must fail deterministically
at their API boundaries, without fake TInterpreter objects, generated-dictionary
stubs or silent no-ops. Loud failure is necessary but insufficient to validate
an InitInterpreter early return. No such C++ adaptation is approved by this
review. xeus-cpp/CppInterOp's compiler does not automatically implement
TInterpreter for ROOT.

A single prelinked ROOT side module remains a candidate packaging strategy.
Build genuine target libraries first; validate target-built codec inputs,
no shared memory, G7 exception compatibility, initialization and P0 parity
before browser claims. Do not resume the retired manual Core reconstruction.

# NEXT SINGLE EXPERIMENT:

**One bounded Core-dictionary generation-and-compile probe using the already
installed native rootcling and the complete Emscripten target environment.**
No CMake configure or library/compiler build is needed. Extract the existing
G__Core rootcling command into a fresh review cache directory and redirect its
output/rootmap/library paths there. Run it once under a 120-second timeout with
C++17, `--target=wasm32-unknown-emscripten`, the target sysroot, and explicit
libc++, musl and Clang builtin include paths. For example, the extra arguments
must include:

```
-std=c++17 --target=wasm32-unknown-emscripten --sysroot=<sysroot>
-nostdinc -nostdinc++
-isystem <sysroot>/include/c++/v1 -isystem <sysroot>/include
-isystem <emsdk>/upstream/lib/clang/21/include
```

Set `EXTRA_CLING_ARGS` on the extracted command directly; do not invoke the
existing diag helper expecting it to preserve that environment. Record the
complete command, generator exit/diagnostics and target configuration. If it
produces C++, compile **that entire generated dictionary** with em++ using
Core's generated compile settings. Pass requires both steps to succeed without
host-private STL types; it establishes only this dictionary compile path, not
runtime or PCM correctness. Stop at the first generator/compile failure.

This cheaply distinguishes incomplete includes from a target/frontend/JIT
limitation using tools already present. A native pinned `rootcling_stage1`
remains a distinct next candidate on failure, preferably an existing artifact;
its own interpreter avoids stage-2 ROOT coupling but still needs target
stdlib/ABI support. Failure of stage-2 alone cannot rule it out. Building
native stage1 or wasm-targeted Cling would incur LLVM/Clang work and requires
separate bounded scope; neither precedes this cheap probe. Do not resume a
Core or Hist build merely because include discovery improves.
