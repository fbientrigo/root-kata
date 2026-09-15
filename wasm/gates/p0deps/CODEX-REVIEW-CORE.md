# VERDICT: PARTIAL

Independent Core-fix review, 2026-09-15, on `experiment/root-wasm-subset`,
following `bf5b0ce`. **Core target compilation is PASS; a usable ROOT wasm
runtime is not established.** The eight-file patch retains ROOT's own CMake
targets and makes narrowly justified platform changes. It does not remove
ROOT's runtime interpreter dependency or establish browser compatibility.

The source is pinned ROOT **6.40.04**, the target toolchain Emscripten
**4.0.9**, and the installed host generator **6.40.02**. Generator SHA-256:
`84809b688c01fa1ecd3d554102fbe1408722ae52c064163731983b28093fa4e7`.
This is version-mismatched diagnostic evidence, not pinned-generator parity.

# VERIFIED:

## Clean reproduction

The review uses a fresh cache rather than the coordinator's existing objects:

```bash
cd wasm/gates/p0deps/xbuild
export X="$HOME/.cache/rootwasm-p0/core-review-20260915"
bash run.sh configure
bash run.sh graph
bash run.sh build
bash run.sh inspect
XBUILD="$X" OUT="$HOME/.cache/rootwasm-p0/core-review-dictprobe-20260915" bash ../dictprobe/run.sh
```

Configure completed in 223 seconds (229 seconds for the wrapper). The generated Core order closure has
**14 nodes**, including `BUILTIN_ZSTD`, and `FORBIDDEN: none`. ROOT's actual
`G__Core` rule invokes the installed native rootcling with target frontend
arguments; compilation and the Core link rule invoke pinned em++.

| Check | Independent result |
| --- | --- |
| Actual `cmake --build . --target Core -j4` | exit 0, 398 seconds; `[100%] Built target Core` |
| Inspection | `xbuild Core PASS`; `TObject::Class()`, `TVersionCheck::TVersionCheck(int)` and unchanged `TROOT::InitInterpreter()` defined |
| Core output | 6,877,437-byte wasm relocatable object; SHA-256 `5970488eb3cc1034924a3b13395ac1b67d4c7da504c678ade6b02b78c3fd9b3a` |
| Undefined symbols | 0 selected codec/regex symbols; **397 total**, predominantly platform/C++ runtime inputs, not a fully linked executable |
| Archive members skipped as non-wasm | 0 diagnostics |
| Clean dictionary probe | rootcling exit 0; 27,985 lines; 0 host-private STL lines; em++ exit 0, 0 errors; 1,635,090-byte wasm object; `dictprobe PASS` |
| Fresh dictionary SHA-256 | `b35c8aa078097f46a1233c76dd90e0503674b428136cea4639e6a84767424b03` (generated registration paths depend on cache location) |

`bash -n` passes for both scripts. The applied patch reverses cleanly in a
dry run, and a complete source-tree comparison finds exactly its eight
modified files. Build caches and the pre-existing `gcore/` and `g2` change
are excluded from the commit. No curriculum or application code was changed.

## Target dictionary evidence beyond compilation

An independent header included the generated build's `TObject.h`, `TString.h`,
`TNamed.h`, `<vector>` and `<string>`, and defined:

```cpp
template<int P, int L, int O, int S, int N, int V, int C> struct ReviewABI {};
using TargetABI = ReviewABI<sizeof(void*), sizeof(long), sizeof(TObject),
                           sizeof(TString), sizeof(TNamed),
                           sizeof(std::vector<int>), sizeof(std::string)>;
```

With `#pragma link C++ class TargetABI+;`, the same `EXTRA_CLING_ARGS` and
`-writeEmptyRootPCM`, native rootcling exits 0 and emits the concrete identity
**`ReviewABI<4,4,12,16,44,12,12>`**. Target em++ independently accepts assertions
for those sizes, 4-byte alignment of the three ROOT classes, C++17 and
little-endian predefines. This establishes real ILP32 parsing and selected
matching class layouts, rather than just a dictionary that happens to compile.

The generator's primary header parse reports `__wasm32__`, `__EMSCRIPTEN__`,
`R__EMSCRIPTEN`, `R__UNIX`, `R__BYTESWAP` and `NEED_SIGJMP`, with neither
`__x86_64__` nor `R__B64`. The installed ROOT tool also performs a secondary
host-context header parse: a header containing unconditional target-only
`#error` checks fails there. The template identity above records the selected
target AST without assuming every internal tool operation is retargeted.

The compiled Core object uses Emscripten libc++'s **`std::__2`** ABI namespace.
Generated alternate class names also contain `std::__2`. The existing probe's
407-line count matches `__wrap_iter`; it is not evidence for `std::__1`.
Neither `__gnu_cxx` nor `std::__cxx11` appears in the target dictionary.
Class initializer sizes/alignment are emitted as `sizeof(::TObject)` /
`alignof(::TObject)` and analogous expressions evaluated by the target compiler.
This does not validate all streamer decisions, offsets or runtime reflection.

## Generator-only overlay

The pinned Cling source at
`interpreter/cling/lib/Interpreter/Interpreter.cpp:455-506` chooses the
`at_quick_exit` linkage/exception specification using its **host build**.
The overlay renames musl's conflicting declaration while leaving Cling's
prelude declaration visible. It therefore changes the generator parser's view
of one declaration; it is not an unmodified target header environment.

Classification: **PLATFORM PORT, narrowly for this host-tool environment**.
Changing the temporary rename to `__rootwasm_review_unused_at_quick_exit` and
rerunning the entire Core command produces byte-identical `G__Core.cxx`
(SHA-256 `06a86bea897295dbfb79f2a7da9a64f8e255a94ae3ba868478aa8187447eaa64`
for both review A/B outputs). Neither rename, `at_quick_exit`, nor the overlay
path appears in that generated C++. Core's em++ dependency file contains no
overlay path, and neither compiler includes nor flags pass it to em++.
This is acceptable evidence for Core; future dictionaries selecting this
function need their own check. No generated C++ was manually edited.

## The two ROOT C++ edits

| Edit | Classification and evidence |
| --- | --- |
| New wasm32 Emscripten `RConfig.hxx` block | **PLATFORM PORT**. Selects ROOT's existing platform paths; no algorithm is rewritten. The guard excludes wasm64 and other targets. |
| `R__BYTESWAP` | Correct for little-endian wasm32. In ROOT this means conversion to/from its big-endian buffer representation, not that the CPU is big-endian: `core/base/inc/Bytes.h:68-106`; `core/cont/src/TBits.cxx:520` explicitly documents the meaning. `TString.h:181-269` also needs the little-endian representation masks, and `TString.cxx:560-647` selects the endian-independent hashing path. Leaving the flag absent was incorrect platform identification. No I/O or hashing algorithm is changed, but runtime/native parity is still untested. |
| `NEED_SIGJMP` | Valid for this pinned sysroot: `include/setjmp.h:27-31` makes `sigjmp_buf` an alias of `jmp_buf` and aliases `sigsetjmp`/`siglongjmp` to `setjmp`/`longjmp`. ROOT's `TException.h` and `TException.cxx` therefore select available functions. This does not add signal support or prove compatibility with wasm exception handling. |
| `R__UNIX` | Appropriate to select Emscripten's POSIX-like libc and ROOT's existing Unix implementation. It does not establish full Unix behavior: process, socket and signal operations still need runtime validation. |
| `TUnixSystem.cxx` guards | **PLATFORM PORT**. Includes the existing sysroot `<sys/ioctl.h>` declarations and uses musl's `strerror` instead of unavailable `sys_nerr`/`sys_errlist`. Existing ROOT operations are preserved; platform-specific errno text and ioctl support are not native-parity claims. |

## Builtins

The independent audit enumerates **every** member of the five archives with
pinned `llvm-ar`, checks each member's wasm magic, and checks representative
defined symbols in the resulting Core object. The coordinator's existing
artifacts contain 5 LZ4, 79 LZMA, 15 zlib, 37 ZSTD and 21 PCRE members, all wasm.
Core defines `R__zipLZ4`, `R__zipLZMA`, `R__zipZSTD`, `LZ4_compress_default`,
`ZSTD_compressCCtx`, `deflate`, `inflate`, `pcre_compile` and `XXH64`.
The fresh-cache audit independently reproduces the same complete member counts
and all nine representative definitions, checks the real phase log exits,
and finds no overlay path in any Core em++ dependency file. These checks establish target-built
codec inputs and their inclusion, not successful compression round trips.

# INVALIDATED:

1. **“Non-STAGE1 MathCore, Matrix and Hist write real non-empty PCM and must
   hit the next ABI blocker.”** Pinned upstream explicitly passes
   `-writeEmptyRootPCM`: MathCore `CMakeLists.txt:183`, Matrix `:82`, Hist
   `:169`, RIO `:123` and Thread `:62`. All five fresh generated dictionary
   commands contain that option. Empty PCM is upstream behavior here, not a
   new workaround. Non-empty PCM generation remains unsupported, but its
   failure does not establish a blocker for these stock targets.
2. **General host/target metadata correctness.** Removing `-writeEmptyRootPCM`
   from the independent ABI probe exits **139**, with `TClass and cling
   disagree` diagnostics including `TString` **24/16**, `TObject` **16/12**
   and `TDataType` **144/104**. Compiled host ROOT objects and target-parsed
   layouts mix in metadata serialization. The historical `TProtoClass`
   200/120 diagnostic is consistent with this mechanism; no usable non-empty
   Hist PCM has been generated or validated.
3. **The inspection gate proves all of its broad claims by itself.** It checks
   only the first member of each discovered archive, requires no inventory
   of all five archives, and checks only selected undefined-name prefixes
   (excluding, for example, xxhash). A missing implementation can yield zero
   undefined names if its wrapper is absent too. The graph phase reports
   forbidden nodes without failing on them. Configure/build phases print
   the subprocess exit but return the following successful `echo`/`tee`
   status; a stale library can survive a failed incremental build. The clean
   reproduction, explicit log exit checks, complete member inventory and
   representative definitions compensate for these limits in this review.
   `inspect` should not yet be treated as an unattended release gate.
4. **`libCore.so` is a loadable side module.** Under pinned 4.0.9, bare
   `-shared` with a `.so` suffix chooses relocatable object output; the build
   warning says so explicitly. See the
   [pinned Emscripten link implementation](https://github.com/emscripten-core/emscripten/blob/4.0.9/tools/link.py#L761-L771).
   A wasm magic header and defined symbols do not establish a runnable or
   dynamically loadable artifact. Current Emscripten documentation describes
   newer `-shared` behavior and must not supersede this pinned-source evidence.

# MINIMUM DEPENDENCIES:

- **Proven Core build inputs:** ROOT's Core/G__Core/Clib targets and generated
  headers; target zlib, LZMA, LZ4, ZSTD, PCRE, xxhash and nlohmann headers;
  Emscripten libc/libc++ and generated dl/thread/atomic link settings.
- **Host-only generator inputs:** the installed 6.40.02 rootcling and its
  native ROOT/Cling dependencies, plus the explicit wasm32 target frontend
  environment and declaration overlay. There is no target LLVM/Cling build
  in the verified Core closure. LLVM/Cling still undergo top-level CMake
  configuration and their targets remain defined.
- **Candidate TH1D package closure:** Core, Thread, RIO, MathCore, Matrix and
  Hist with `imt=OFF`. Neither its completed build nor a minimal executable
  closure is established by Core alone. TBB is not required in this profile.

# ARCHITECTURE:

Keep ROOT's source lists, dictionaries, generated configuration and CMake
targets. The patch changes host-tool selection/order edges, forwards the
toolchain to four ExternalProjects, schedules ZSTD like the existing LZ4
imported target, and identifies the wasm32 platform. There is no manual Core
source reconstruction and no replacement ROOT API.

No Node or Chromium runtime load/execution, TH1D call sequence, native output
parity, deployment payload size, or main/side-module package is established.
`-pthread` is still present in compilation and the relocatable link; the target
compiler defines `__EMSCRIPTEN_PTHREADS__`. The generator environment omits
that flag, so “mirrors em++” covers its target/sysroot/include choices, not
complete feature-flag equivalence. A no-shared-memory browser profile and
G7's `-fwasm-exceptions` compatibility remain open.

`TROOT::InitInterpreter()` is present and unchanged. At
`core/base/src/TROOT.cxx:2223-2275`, its ordinary path loads RIO/Cling and
requires `CreateInterpreter` and `DestroyInterpreter`; dropping a CMake
**order** edge does not remove this runtime edge. The installed host generator
also bakes its native include prefix into registration `includePaths`, so
runtime resource paths are not deployment-ready. Do not silently skip
initialization, replace configuration with a constant, or hand-write
Class/Streamer methods. CppInterOp's compiler is not ROOT's TInterpreter.

# NEXT SINGLE EXPERIMENT:

**One bounded generation-and-whole-dictionary compile probe for the stock
`G__MathCore` rule in the already configured tree.** This is the first cheap
transfer from the proven Core dictionary to a non-STAGE1 dependency of Hist.
Extract its generated rootcling rule, preserve **all upstream options**,
including `-writeEmptyRootPCM` and the Core PCM dependency, and redirect only
outputs to a fresh probe directory. Run from its generated working directory
with the same target environment under a 120-second bound. If generation
succeeds, compile the entire emitted C++ with em++ and that target's generated
`flags.make`; check target STL spellings and object format. Stop at the first
failure and record command/exit/diagnostics.

Pass means this stock non-STAGE1 dictionary path works, not that non-empty
PCM, a MathCore library, Hist, or interpreter-free execution works. Do not
remove `-writeEmptyRootPCM` to manufacture a blocker, invent a PCM workaround,
build new LLVM/Cling tools, or start a full Hist build in this probe. A larger
ROOT-owned Hist closure build is a separately scoped follow-up after this
cheap check.
