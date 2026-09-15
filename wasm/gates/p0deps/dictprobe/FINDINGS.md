# Core dictionary for wasm32 from a host rootcling (Codex NEXT SINGLE EXPERIMENT)

## Verdict: PASS (generate + em++ compile of the entire `G__Core.cxx`)

```
bash wasm/gates/p0deps/dictprobe/run.sh   # -> rootcling exit=0, em++ exit=0 errors=0, "dictprobe PASS"
```

| | |
| --- | --- |
| Generator | installed conda-forge rootcling 6.40.02 (sha256 `84809b688c01fa1e…`), version-mismatched with the 6.40.04 source |
| Command | exact generated `G__Core` command from `xbuild` `build.make`, with outputs redirected to `~/.cache/rootwasm-p0/dictprobe` |
| Output | `G__Core.cxx`, 27985 lines |
| STL spellings | **0** host-private (`__gnu_cxx` / `std::__cxx11`), 407 `__wrap_iter` lines; actual libc++ alternate names use Emscripten's `std::__2`, not `std::__1` |
| Compile | pinned em++ 4.0.9 with Core's generated `flags.make` (C++17, `-O3`, `-pthread`, `-fPIC`): exit 0, 0 errors, 1.6 MB object |

### Generator environment

The generator environment is passed through `EXTRA_CLING_ARGS`, which TCling reads at
`core/metacling/src/TCling.cxx:1453-1461`:

```
-std=c++17 --target=wasm32-unknown-emscripten --sysroot=$SYSROOT -DEMSCRIPTEN -fignore-exceptions
-nostdinc -nostdinc++
-isystem $SYSROOT/include/fakesdl -isystem $SYSROOT/include/compat -isystem $SYSROOT/include/c++/v1
-isystem $EMSDK/upstream/lib/clang/21/include -isystem <this dir>/overlay -isystem $SYSROOT/include
```

It mirrors em++'s target/sysroot/include choices, not every feature flag (`-pthread` is absent
from the generator args). I got those choices from `em++ -v`: `-target wasm32-unknown-emscripten`,
`--sysroot`, `-DEMSCRIPTEN`, `-fignore-exceptions`, and `-iwithsysroot/include/{fakesdl,compat}`.
The generator-only overlay is added before musl's `include`.

## How each blocker was resolved

1. **`__gnu_cxx` in the dictionary.** The previous xbuild attempt parsed with host libstdc++.
   Fixed by the full target environment above.
2. **`xlocale.h` not found.** em++ adds `include/compat`, and so does the fix.
3. **`__BYTE_ORDER__` undefined.** This was an artefact of the incomplete include
   environment in the first probe. It is gone with the em++-equivalent environment, and no
   extra define was added.
4. **`at_quick_exit` exception-spec conflict.** Cling's interpreter prelude declares
   `at_quick_exit(void(*)()) throw ()`. The `throw ()` is chosen by the cling *host build*
   (`#if defined(__GLIBC__)`, `interpreter/cling/lib/Interpreter/Interpreter.cpp:455-506`) and
   is emitted unconditionally, even with `-noruntime`. It conflicts with musl
   `stdlib.h:50`. Fixed with `overlay/stdlib.h`, which renames only musl's redeclaration during
   generator parsing. `::at_quick_exit` stays declared through cling's prelude. **em++ never sees
   the overlay**, and the generated dictionary does not reference `at_quick_exit`.

## Evidence that the target frontend is really in effect

A probe header (`~/.cache/rootwasm-p0/dictfix/probe.h`) encodes predefines as class names in
the generated dictionary:

- Host run: `IS_X86_64`, `HAS_GLIBC`.
- Under this environment, cling reports class sizes of `TObject` 12 and `TString` 16. The host
  x86_64 sizes are 16 and 24. So the frontend parses with wasm32 ILP32 layouts.
- A second probe shows user headers parse with `__cplusplus == 201703L`.

Independent review also generated `ReviewABI<4,4,12,16,44,12,12>` encoding pointer,
long, TObject, TString, TNamed, vector and string sizes, and checked them with target em++.
Changing the overlay's temporary rename produced byte-identical whole Core dictionary code;
the target dependency file contains no overlay path. See
[the Core review](../CODEX-REVIEW-CORE.md) for the evidence and verification boundary.

## Classification

**PLATFORM PORT: host-tool environment only.**

- No ROOT C++ source, dictionary output or generated code is edited.
- The overlay exists only in the host generator's include search path. It works around a
  glibc-host assumption in cling's JIT prelude and does not alter the compiled target headers.
- The independent Core review confirms this classification for the tested Core path.

## Known limits (not solved here)

- **Non-empty rdict.pcm crashes the host generator.** Without `-writeEmptyRootPCM`, the host
  generator segfaults: `TClass and cling disagree on the size of the class TProtoClass,
  respectively 200 120`. The installed stage-2 rootcling is itself a host (LP64) ROOT
  application: it streams its own compiled `TProtoClass`/`TString` while cling uses wasm32
  layouts.
  - `G__Core` is STAGE1 (`-writeEmptyRootPCM`), so it is unaffected.
  - **Correction from independent review:** pinned upstream MathCore, Matrix and Hist
    explicitly request `-writeEmptyRootPCM`, as do RIO and Thread; their generated commands
    preserve it. The non-empty PCM crash is real but is not an established blocker for
    these stock targets. Whether a Cling-free runtime reads any PCM remains unverified.
- **Standard-mismatch warnings at startup.** `RConfigure.h:29` ("C++ standard … does not match
  … 201703L") is still emitted twice during interpreter bootstrap. The user-header parse is
  verified C++17, but the bootstrap source of the warning is not identified.
- **Offsets and layout.** Selected target class sizes/alignment are independently checked;
  all offsets, streamer choices and runtime reflection remain unvalidated.

## History

The first run of this probe, without `-DEMSCRIPTEN`, `include/compat` or the overlay, failed:
`rootcling exit=139`, with `at_quick_exit` and `__BYTE_ORDER__` diagnostics. Each blocker above
was then fixed by a single change and re-run.
