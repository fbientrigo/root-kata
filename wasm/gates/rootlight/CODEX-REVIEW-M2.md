# VERDICT: PARTIAL

Independent M1/M2 review on 2026-09-15, pinned ROOT 6.40.04 and Emscripten
4.0.9, branch `experiment/root-wasm-subset`, starting at `9423b18`.
**M1 is a Hist build gate; M2 currently establishes Node side-module execution,
not the complete user-approved M2 browser milestone.** G5 and P0 remain open.

# VERIFIED:

## Reproduction

The source and build directories under `~/.cache/rootwasm-p0/xbuild` were
deleted before configuration; the downloaded host ROOT installation and
Emscripten download caches were retained. The cached CERN tarball independently
hashes to `287ff87deef0eed0fedd32e7d59bdadd22dcb45a5c592c9e08d8d140212ef261`.
Its installed `RVersion.hxx` identifies ROOT 6.40.04. This verifies the retained
tarball, not a new download or a publisher-signed checksum.

```bash
bash wasm/gates/p0deps/xbuild/run.sh configure
bash wasm/gates/p0deps/xbuild/run.sh graph
BUILD_TIMEOUT=7000 bash wasm/gates/p0deps/xbuild/run.sh hist
bash wasm/gates/p0deps/xbuild/run.sh inspect
bash wasm/gates/p0deps/dictprobe/run.sh MathCore
bash wasm/gates/p0deps/dictprobe/run.sh Core
bash wasm/gates/rootlight/run.sh
```

REPRODUCTION_RESULTS_PENDING

## ROOT-owned compilation and dictionaries

`cmake --build . --target Hist` uses ROOT's generated source lists, library
targets, LinkDefs and dictionary rules. The inspected Hist order closure has
25 nodes, including Core, Thread, RIO/RootPcmObjs, MathCore, Matrix, Hist and
their six dictionaries; it contains no target LLVM, Clang, Cling or rootcling
build nodes. Removing Core's CLING **order** edge and choosing a host generator
does not remove ROOT's interpreter **runtime** dependency. LLVM/Cling targets
still exist and undergo top-level configuration.

The generator receives the wasm32 triple, target sysroot, C++17 and target
libc++ include order through `EXTRA_CLING_ARGS`. The declaration overlay is
generator-only; target compilation uses the generated ROOT rules. Whole Core
and MathCore dictionaries compile with target em++, without the tested
host-private STL spellings. Version matching removes the prior ROOT
6.40.02/6.40.04 skew; it does not make generator and compiler identical:
the official host rootcling reports LLVM 20.1.8, while Emscripten uses Clang 21.
These are evidence for the tested dictionary paths, not universal AST/PCM ABI
compatibility. Upstream empty-PCM options remain intact.

A new selected-layout probe with the **6.40.04** generator emits
`ReviewM2ABI<4,4,12,16,720,160,568,264>` for pointer, long, TObject, TString,
TH1D, TAxis, TFile and TMatrixD sizes. Target em++ accepts a `std::is_same`
static assertion against that exact template identity. Probe sources/logs
are in `~/.cache/rootwasm-p0/m2-review-abi`. This verifies selected ILP32
layouts across the new closure, not every field offset or metadata layout.
Pragma probes confirm the primary user-header parse is C++17, wasm32,
Emscripten, R__EMSCRIPTEN and little-endian, with no x86_64/R__B64. The tool
also reparses the header in a secondary **host C++23/x86_64/R__B64** context.
An unconditional target-only `#error` assertion therefore rejects that
secondary parse; it does not invalidate the measured target primary parse.
Generation still warns that it cannot extract the C++ standard-library
version, and host-side parsing emits a C++ standard mismatch warning.
The host/target serialization risk remains; version matching has not
eliminated it. The pragma transcript is `rootcling-macros.log` in the probe
directory.

The generator retains `-fignore-exceptions`, whereas target compilation uses
`-fwasm-exceptions`: this is a parsing profile, not a complete feature-flag
mirror. Pinned Clang predefine probes keep `__EXCEPTIONS` and
`__cpp_exceptions` enabled in both; wasm-EH-specific macros differ. No uses
of those differing macros were found in the covered ROOT/Core/Math/RIO/Hist
or target libc++ headers. Runtime exception ABI still needs the G7 probe.

Generated Core registration still embeds the native host installation's
absolute include path, alongside build-tree paths. Staging headers does not
relocate those strings. M3 module registration must resolve the mounted
target resources explicitly; header autoload/resource portability is not
established by the current factory-registration smoke.

The review hardens `inspect`: all six relocatable library outputs must have
wasm magic and the eight specified exact defined symbols; every member of
every `.a` beneath the build tree must be wasm, including `lib/libxxhash.a`
outside builtins. Empty archives, duplicate member
names, extraction/read/nm errors, missing flags and missing successful Hist
build logs fail. The selected Core codec/regex undefined-symbol check and
no-pthread compile check remain narrow checks, not complete symbol closure
or codec behavior tests. `all` now actually builds Hist; `build` retains the
historical Core-only operation. Configure/build/graph failures propagate.

## Node execution and the actual stop

The five expected lines exercise genuine `TString`, `TNamed` and
`TMath::Gaus`; `TClassTable::GetDict("TH1D") != nullptr` demonstrates static
registration of the Hist dictionary factory. It does **not** call that
factory or prove `TH1D::Class()`/streaming/reflection works.

`smoke.cxx` then attempts a genuine TH1D constructor. The unchanged
`TROOT::InitInterpreter` loads RIO, searches for libCling and requires
`CreateInterpreter`/`DestroyInterpreter` (`core/base/src/TROOT.cxx:2223-2275`).
There is no supplied libCling. A missing DynamicPathName may yield a null
argument to `dlopen`; on this runtime that can select the main program, so the
observed final failure is **missing CreateInterpreter**, not necessarily a
failed libCling `dlopen`. This is the authentic interpreter seam. The TH1D
entries/integral/mean line never executes. The gate now requires ROOT's exit
status 1 as well as the expected prefix and boundary diagnostics.

# INVALIDATED:

- **Full M2 PASS:** the approved M2 includes Chromium inside the pinned G7
  kernel and passing the old `#include <TH1D.h>` symbol wall. This gate uses
  a freshly built MAIN_MODULE and NODERAWFS in Node. Neither browser MEMFS
  loading nor kernel symbol/exception compatibility is established.
- **Any library instantiated twice always fails:** grepping `already in
  TClassTable` detects the observed duplicate-registration symptom. It is
  not a general instance-count check; a duplicate can avoid that warning.
- **Dictionaries work at runtime without qualification:** registered factory
  addresses are proven; class-info construction, PCM loading, streamer
  metadata, actual serialization and reopen/round-trip behavior are not.
  Empty PCM generation does not resolve the previously demonstrated
  non-empty PCM host/target serialization crash.
- **UUID machine-random fallback preserves all identity semantics:** ROOT's
  default no-interface node seed is MD5 of zero-initialized machine info,
  time and hostname (`TUUID.cxx:539-589`), not fresh cryptographic entropy.
  Clock sequence seeding also uses time and PID. Browser workers can share
  hostname/PID conventions and coarsened clocks. Cross-worker/session
  collision resistance and valid `GetHostAddress()` are not established.
  UUIDv4 is a separate API/path; it is not what this patch substitutes.
- **No silent no-ops anywhere:** interpreter initialization is not skipped,
  and no ROOT math/dictionary implementation is replaced. However, excluding
  HAVE_SEMOP selects upstream TMapFile semaphore methods that do nothing and
  can return success. The result must not be advertised as shared-memory
  TMapFile support.
- **Finished payload/parity:** no browser P0 execution, native P0 comparison,
  kata validation, interpreter, fitting, graphics or deployable bundle is
  proven. Side-module byte counts omit the kernel, headers, dictionaries,
  etc, delivery compression and browser working memory.

# MINIMUM DEPENDENCIES:

For the preserved **stock Hist package closure** with `minimal=ON`, `imt=OFF`,
`runtime_cxxmodules=OFF`, `clad=OFF`: Core, Thread, RIO, MathCore, Matrix and
Hist. These are the correct six ROOT libraries for this target graph. This is
not proof of the mathematically smallest TH1 executable, a general ROOT
minimum, or a usable P0 closure without an interpreter backend.

Build inputs also include ROOT-generated configuration/headers, Core Clib,
RIO RootPcmObjs, target zlib/LZMA/LZ4/ZSTD/PCRE/xxhash, nlohmann headers and
Emscripten's libc/libc++/C++ ABI and dynamic-loader support. No TBB is required.
The native ROOT/Cling installation is a **host-tool** dependency only.

M2 retains one side module per library. The review replaces its handwritten
dependency map with dependencies extracted from each ROOT-generated
`CMakeFiles/<target>.dir/link.txt` and its response files; it relinks complete ROOT-built objects,
without maintaining a second source or library graph. Actual NEEDED entries
and packaged size are recorded below with the reproduction results.

# ARCHITECTURE:

## Platform ports and their restrictions

| Change | Classification and observable restriction |
| --- | --- |
| CheckCompiler drops `-pthread` for Emscripten | PLATFORM PORT for the approved single-threaded runtime. Does not preserve native thread/shared-memory behavior. `imt=OFF` alone is insufficient; compiler/linker memory ABI must also match. |
| TMapFile excludes HAVE_SEMOP | PLATFORM PORT selecting an existing unsupported-platform path, with silent loss of synchronization. Safe only within the single-threaded/no-process scope; future exposure needs loud rejection or genuine support. |
| GetSharedLibDir returns GetRootSys()+`/lib` | PLATFORM PORT using an explicit mounted bundle location instead of ELF discovery. It changes automatic relocation/path-discovery semantics. This profile has R__HAVE_CONFIG undefined and requires correct ROOTSYS before cached GetRootSys/GetSharedLibDir use; absent/stale ROOTSYS can select a wrong fallback. Other configured-prefix profiles need ROOTIGNOREPREFIX or an appropriate compiled prefix. |
| TFile skips EOS-FUSE getxattr redirect | PLATFORM PORT: browser MEMFS has no EOS-FUSE xattrs. Ordinary file paths remain genuine; EOS auto-redirect behavior is unavailable and untested. |
| TUUID avoids unsupported getifaddrs and selects upstream fallback | PLATFORM PORT of unavailable host-interface discovery, with loss of network-derived identity. UUID encoding, comparison and timestamp logic remain ROOT's; global uniqueness on the browser platform requires separate evidence. |

The other patch hunks select the host rootcling, propagate ExternalProject
toolchains, schedule ZSTD and identify wasm32/Unix/little-endian. No TH1,
TFormula, Class or Streamer replacements are introduced. Classifying these as
platform ports does not erase the restrictions above.

## Loader glue and G7 compatibility

ROOTSYS and ROOT_LDSYSPATH use ROOT's own resource/search configuration; the
latter bypasses a subprocess-based system loader-path probe. `locateFile`
maps NEEDED basenames to actual library bytes. Aliasing the staged absolute
path and basename onto the **same existing DSO object** implements loader
identity resolution; it supplies no ROOT symbols or fake ROOT results.
The pinned Emscripten 4.0.9 `src/lib/libdylink.js:1036-1077` reuses that object,
its exports and handle mapping on subsequent loads. This is acceptable
bounded loader glue, not a portable SONAME implementation. It mutates private
LDSO state, handles only the initially loaded path aliases, does not canonicalize
all relative/symlink paths, and assumes a single correctly mounted bundle.
The locateFile callback also assumes basename input; absolute paths must
already resolve in the filesystem or alias table. Browser transfer needs
explicit tests rather than a claim that Node glue is already browser glue.

Pinned Emscripten, wasm32/libc++, no shared memory and `-fwasm-exceptions`
are the right intended G7 profile. G7's existing page supplies the exception
flag to incremental compilation, and its packaged xcpp.js exports
`Module.loadDynamicLibrary`, `Module.LDSO` and `Module.wasmTable`, with an
unshared memory. Matching flags are necessary, not an ABI integration test:
the fresh Node MAIN_MODULE can provide JS/runtime exports absent from G7,
and no cross-kernel/side-module throw/catch or typed C++ call is tested here.
The [Emscripten exception documentation](https://emscripten.org/docs/porting/exceptions.html)
requires the wasm exception flag at compilation and linkage; its current
dynamic-link documentation describes newer `-shared` behavior and must not
override pinned 4.0.9's relocatable-output evidence.

## M3 interpretation

Using ROOT's existing abstract TInterpreter/plugin seam to adapt the kernel's
**existing** CppInterOp instance is a reasonable interpreter-backend platform
port; CppInterOp already exposes GetInterpreter, Declare, Process, Evaluate
and reflection APIs in the pinned 1.9.0 header. ROOT's concrete analysis
classes and generated dictionaries stay genuine. This is substantial new
backend implementation, not merely renaming libCling or making compiler
availability imply ROOT reflection availability.

`llvm-nm -C` independently finds defined CppImpl::GetInterpreter, Declare,
Process and Evaluate in the pinned `libclangCppInterOp.so` (the public Cpp
namespace routes to that implementation). Their existence supports the
adapter seam; invoking them from a new ROOT plugin in G7 is still untested.

Preserve factory signatures, singleton ownership, module registration,
error/result conventions and shutdown. In particular, RegisterModule is
mandatory behavior, not an acceptable temporary no-op. Unsupported calls
must terminate or propagate an unambiguous ROOT error that the caller checks;
printing Error and returning a plausible success/default is insufficient.
Plugin factory/boot/registration should be a bounded first M3 gate, before
implementing 141 methods or proceeding to formula/fitting work.

# NEXT SINGLE EXPERIMENT:

**Complete the missing M2 host-integration probe before implementing M3.**
Preload these six modules and the staged ROOT resources into the pinned G7
Chromium kernel's MEMFS, using its existing loader and unshared memory.
Verify DSO object identity for basename and absolute-path loads, then execute
typed cells including TH1D.h and the existing pre-constructor smoke calls.
Include one throw/catch across a small side-module/kernel call boundary to
test the shared C++ exception runtime. Under plain static hosting without
COOP/COEP, require the same registration/smoke evidence and the authentic
missing-libCling/CreateInterpreter boundary; stop at the first earlier
symbol/import/resource/exception failure. Do not provide a placeholder
interpreter to make it pass.

This is higher information per unit work than writing a ROOT interpreter
adapter against a host that has never loaded these ROOT modules. If it
passes, begin the planned M3 factory/Initialize/RegisterModule adapter; if it
fails, the first host-integration diagnostic defines the port work required.
