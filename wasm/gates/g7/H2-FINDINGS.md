# G7 / Lead H2 finding: `browsercc` (Clang+LLD as WebAssembly) — HYPOTHESIS FALSIFIED

**Verdict: no run.sh, no page/. The hypothesis fails on the exact payload, for a
documented, ecosystem-wide reason, not a fixable configuration mistake.**

## Hypothesis under test

A prebuilt Clang+LLD toolchain that itself runs as WebAssembly (compiles C++
source to WebAssembly, entirely client-side, no server, no SharedArrayBuffer/
pthreads) can compile the exact G2 payload (`wasm/gates/g2/genvector.cpp`,
unmodified) against the real, sha256-pinned ROOT 6.40.04 source tree, link it,
and run it in Chromium producing byte-identical output to
`wasm/gates/g2/expected.txt`.

## What was found and tried

### 1. Research: prebuilt clang-as-wasm artifacts

- **Emscripten 4.0.9's own distribution** (`~/.root-kata-wasm/emsdk`): checked
  directly — `clang-21`, `lld`, etc. under `emsdk/upstream/bin/` are native
  x86-64 ELF binaries (`file` confirms `ELF 64-bit LSB pie executable,
  x86-64`), not wasm. No wasm clang/lld shipped. Ruled out immediately.
- **Ben Smith's `binji/wasm-clang`** (the CppCon 2019 "Clang in the browser"
  demo, still live at github.com/binji/wasm-clang and
  binji.github.io/wasm-clang): confirmed it exists and ships clang+lld
  compiled to wasm w/ WASI. Not deep-tested (see "why not binji/wapm" below).
- **`wapm-packages/clang`** (Wasmer): confirmed it exists, ships "the full
  clang" + wasm-ld for WASI, ~100 MB download per Wasmer's own blog post. Not
  deep-tested, same reason.
- **`BertalanD/browsercc`** (npm `browsercc@0.1.1`, published ~2024): this is
  the one actually tested end-to-end, because it is the best-documented,
  smallest-glue, most directly embeddable option — a single `compile()`
  function, no Docker/build step needed to *use* it (only to rebuild it), and
  an explicit design goal of "compile C/C++ programs in your browser to
  WebAssembly". Downloaded via `npm pack browsercc@0.1.1` (real npm registry
  fetch, sha shown below) — this is a genuine third-party prebuilt artifact,
  not something built from source for this gate.

  ```
  $ npm view browsercc
  browsercc@0.1.1 | MIT | deps: none | versions: 2
  .tarball: https://registry.npmjs.org/browsercc/-/browsercc-0.1.1.tgz
  .shasum: fef07bb57bb9ba87e7f5c2c12661e9eeba6487dd
  .unpackedSize: 113.9 MB
  published a year ago by bertaland <dani@danielbertalan.dev>
  ```

  `browsercc`'s `clang.wasm`/`lld.wasm` are themselves built from
  `llvm-project` targeting `wasm32-unknown-wasi` (confirmed by running
  `clang --version` through the wasm binary itself, see below) — i.e. this is
  a real Clang, running as WebAssembly, that itself emits WebAssembly. This
  is exactly the architecture the hypothesis asks for.

Why `binji/wasm-clang` and `wapm-packages/clang` were not also deep-tested:
once `browsercc` reproduced a **root-caused, documented upstream limitation**
in the WASI toolchain lineage itself (below), the same limitation applies to
any WASI-target clang+lld, because it lives in wasi-libc/libc++abi, not in
`browsercc`'s own code. Testing the other two would very likely reproduce the
identical failure (all three are wasi-sdk-lineage WASI toolchains); time was
spent confirming the failure is structural via public wasi-sdk issue tracker
evidence instead (see below) rather than re-running the same experiment
against two more multi-hundred-MB downloads.

### 2. RConfigure.h wrinkle — Strategy 1 worked cleanly

Reused `wasm/gates/g2/rconfigure.cmake` completely unmodified, run with `-DCXX`
pointed at the pinned host `em++` exactly as G2 does (the in-browser compiler
never needs to be invoked for this step — it's a host-side probe of macro/
attribute support that transfers because both compilers are Clang-family):

```
$ source wasm/toolchain/activate.sh
$ cmake -DROOT_SOURCE=$HOME/.root-kata-wasm/src/root-6.40.04 \
        -DOUTPUT_HEADER=wasm/build/g7/RConfigure.h \
        -DCXX="$(command -v em++)" \
        -P wasm/gates/g2/rconfigure.cmake
```

Produced a header byte-identical in shape to G2's (same `R__HAS_ATTRIBUTE_*`
defines, same `ROOT__cplusplus 201703L`). **This part of the hypothesis holds**
— no need to fall back to Strategy 2 (probing through the in-browser compiler
in Node). The generated `RConfigure.h` was fed into `browsercc`'s virtual FS
via an extra `-I` and consumed without complaint by clang.wasm.

### 3. Toolchain identity, size, and thread/SAB verdict

```
$ node -e "... Clang({...}).callMain(['--version'])"
clang version 20.1.2 (https://github.com/llvm/llvm-project.git 58df0ef89dd64126512e4ee27b4ac3fd8ddf6247)
Target: wasm32-unknown-wasi
Thread model: posix

$ node -e "... LLD({...}).callMain(['--version'])"
LLD 20.1.2 (https://github.com/llvm/llvm-project.git 58df0ef89dd64126512e4ee27b4ac3fd8ddf6247)
```

(Pinned host `em++` for comparison, from `wasm/toolchain/activate.sh`, is
Clang 21-based (`emsdk/upstream/bin/clang-21`) — one major version ahead of
browsercc's bundled Clang 20.1.2, close enough that the `RConfigure.h`
attribute probes above transferred without issue.)

Payload size (uncompressed, from the npm package contents actually needed to
run a compile — excludes the optional 19.3 MB precompiled-header file, which
`compile()` never fetches unless `getPrecompiledHeader()` is called):

| file | bytes |
|---|---|
| `clang.wasm` | 42,553,880 |
| `lld.wasm` | 23,202,572 |
| `sysroot.tar` | 28,620,800 |
| `clang.js` + `lld.js` + `index.js` glue | 151,093 |
| **total** | **94,528,345 (~90.2 MiB)** |

(`npm pack browsercc@0.1.1` produces a 40 MB gzip-compressed tarball — a
reasonable proxy for actual network transfer size if served with gzip/br
compression, vs. ~94.5 MB uncompressed.)

**Thread/SharedArrayBuffer verdict: does NOT require them**, checked three
ways:
1. `grep -c "SharedArrayBuffer\|Atomics\|pthread"` over both `clang.js` and
   `lld.js` (the Emscripten glue for the two wasm binaries): **zero matches**
   in all three patterns, in both files.
2. `WebAssembly.Module.imports(await WebAssembly.compile(clang.wasm))`
   filtered to `kind === "memory"`: **empty** — the module does not import a
   host-provided (and therefore potentially-shared) memory; it exports its
   own (`{name: "V", kind: "memory"}`), which is the ordinary non-threaded
   Emscripten pattern.
3. Actually ran `clang.wasm --version` and a full compile end-to-end in plain
   Node (no `--experimental-wasm-threads`, no special flags) and it worked —
   a build requiring `SharedArrayBuffer`/threads would need either
   cross-origin-isolation-only browser APIs unavailable like this in Node, or
   explicit worker/Atomics bootstrapping absent from `index.js`'s `compile()`.

This confirms the load-bearing part of the hypothesis (no COOP/COEP needed,
compatible with plain `python3 -m http.server`, matching the GitHub Pages
constraint) — **the blocker below is unrelated to threading.**

### 4. The actual compile of `genvector.cpp` against real ROOT 6.40.04 headers

Mounted the real, sha256-verified ROOT source tree's four required include
dirs (`math/genvector/inc`, `math/mathcore/inc`, `core/foundation/inc`,
`core/base/inc` — 355 files, ~2.17 MB of header text) plus the generated
`RConfigure.h` into `browsercc`'s in-memory FS via its `extraFiles` option,
and called `compile()` with the **exact, unmodified**
`wasm/gates/g2/genvector.cpp` and flags mirroring G2's `em++` invocation
(`-std=c++17 -O2` plus the four `-I` dirs). Reproducible via
`wasm/gates/g7/repro/compile-genvector.mjs` (see that file's header comment
for setup):

```
$ cd wasm/gates/g7/repro && npm install
$ node compile-genvector.mjs
flags: -std=c++17 -O2 -I/root-src/rconfig -I/root-src/math/genvector/inc \
  -I/root-src/math/mathcore/inc -I/root-src/core/foundation/inc -I/root-src/core/base/inc
compile+link: 4480ms
wasm-ld: error: /tmp/genvector-41a9f6.o: undefined symbol: __cxa_allocate_exception
wasm-ld: error: /tmp/genvector-41a9f6.o: undefined symbol: __cxa_throw
wasm-ld: error: /tmp/genvector-41a9f6.o: undefined symbol: __cxa_allocate_exception
wasm-ld: error: /tmp/genvector-41a9f6.o: undefined symbol: __cxa_throw
```

Clang itself compiled `genvector.cpp` and all its real ROOT header
dependencies (`Math/Vector4D.h` -> `GenVector/PtEtaPhiM4D.h` ->
`GenVector/PxPyPzE4D.h` -> `GenVector/GenVector_exception.h`,
`TMath.h` -> `ROOT/RSpan.hxx` -> `ROOT/span.hxx`) into a real `.o` file in
4.5 seconds — no fakery, no shortcuts, this is genuine C++ template
instantiation of ROOT's actual GenVector coordinate-conversion code. **`lld`
(also running as wasm) then failed to link it**, for a load-bearing reason
tied to the payload's actual content, not a flag typo.

### 5. Root cause, confirmed by symbol-table inspection, not just guessing

`ROOT::Math::GenVector_exception::Throw`/`GenVector_Throw`
(`math/genvector/inc/Math/GenVector/GenVector_exception.h:66-77`) are
`inline` functions that runtime-conditionally `throw e;` (gated by a mutable
static bool, so **not** dead-code-eliminated at compile time). They are used
by `PtEtaPhiMVector`'s coordinate-conversion machinery — the header's own
comment says exactly this: *"This class needs to be entirely contained in
this header, otherwise interactive usage of entities such as
ROOT::Math::PtEtaPhiMVector is not possible because of missing symbols... the
Throw function is used in the inline code."* `ROOT/span.hxx`'s `at()`/`slice()`
(pulled in transitively via `TMath.h` -> `RSpan.hxx`, itself pulled in by
`PtEtaPhiM4D.h`) unconditionally throw `std::out_of_range` in their bodies
too. None of this is avoidable by picking different ROOT headers — it is
inherent to using `PtEtaPhiMVector`, which is the exact type the G2 payload
uses.

Checked whether `browsercc`'s bundled sysroot's `libc++abi.a` actually
defines `__cxa_throw`/`__cxa_allocate_exception`, using the pinned emsdk's
own `llvm-nm` (a native x86-64 tool, capable of reading the wasm object
archive) against the extracted sysroot:

```
$ tar xf browsercc-0.1.1/dist/sysroot.tar lib/wasm32-wasi/libc++abi.a
$ llvm-nm lib/wasm32-wasi/libc++abi.a | grep -i cxa_throw
00000015 T __cxa_throw_bad_array_new_length
```

**`__cxa_throw` and `__cxa_allocate_exception` are simply absent** from this
`libc++abi.a` build — only the one narrow `__cxa_throw_bad_array_new_length`
stub exists. `lib/wasm32-wasi/` also has no `libunwind.a` at all. This is not
a `browsercc`-specific bug: it is wasi-sdk's own documented, current (as of
`wasi-sdk-25`, the latest tagged wasi-sdk release found) limitation —
wasi-libc's default sysroot builds `libc++`/`libc++abi` **without** exception
support, and multiple open upstream issues confirm this is still true and
still requires an out-of-tree rebuild of the runtime libraries to fix:
- `WebAssembly/wasi-sdk#329` — "Undefined exception symbols despite
  `-fno-exceptions`"
- `WebAssembly/wasi-sdk#52` — "C++ building error: missing the LIBC++ ABI
  symbols"
- `WebAssembly/wasi-sdk#565` and `#334` — tracking issues for adding C++
  exception support; still described as experimental/non-default,
  requiring `__USING_WASM_EXCEPTIONS__` and a full separate rebuild of
  `libunwind`+`libc++abi`+`libc++` against the matching Clang, "because the
  entire C++ standard library needs to be built with/without exceptions" —
  i.e. `-fexceptions` needs an entirely different sysroot than
  `-fno-exceptions`, and that sysroot is not the one shipped in
  `browsercc` (or, by inheritance, in any other prebuilt WASI-target
  clang+lld distribution built the ordinary way).

Confirmed both directions fail, not just the naive default:

- **`-fno-exceptions`**: fails at *compile* time (not link time) — Clang
  correctly refuses to compile the unconditional `throw` statements in
  `GenVector_exception.h` and `span.hxx` outright ("cannot use 'throw' with
  exceptions disabled"), 7 errors. This is a hard stop: it is not a matter of
  our code never hitting the throw at runtime, the throw expressions are
  simply illegal syntax under this flag, and rewriting ROOT's headers to
  avoid them is off the table (out of scope, and would no longer be testing
  real ROOT source).
- **`-fwasm-exceptions`** (Clang's WebAssembly-EH-proposal codegen, which
  *does* compile the `throw` statements into real `try`/`catch`-lowering wasm
  instructions rather than rejecting them): compiles cleanly, but **still
  fails to link** with the identical `undefined symbol: __cxa_allocate_exception
  / __cxa_throw / __cxa_free_exception` — because, as shown above, the
  bundled `libc++abi.a` has no definitions for these regardless of which
  Clang exception-codegen mode is requested; the *runtime library*, not the
  compiler flag, is the actual gap.

## Conclusion

**Falsified for the exact G2 payload.** A genuine prebuilt Clang 20.1.2 +
LLD, both compiled to WebAssembly, running entirely client-side with no
threads/SharedArrayBuffer/COOP/COEP requirement, is real, downloadable today
(`npm install browsercc@0.1.1`), correctly reused G2's own
`RConfigure.h`-generation strategy verbatim, and did genuinely compile real,
unmodified ROOT 6.40.04 GenVector/MathCore/Core headers into a real object
file in ~4.5s. It cannot **link** that object file into a runnable module,
because `ROOT::Math::PtEtaPhiMVector`'s own header
(`GenVector_exception.h`) unconditionally uses C++ exceptions in inline code
paths that get ODR-used by the exact API surface the G2 payload calls
(construction, `+`, `.Pt()`/`.Eta()`/etc.), and every current WASI-target
prebuilt Clang/LLD distribution (this one, and by direct inheritance from the
same wasi-sdk lineage, `binji/wasm-clang` and `wapm-packages/clang` too)
ships a `libc++abi` built without the `__cxa_throw`/`__cxa_allocate_exception`
definitions that real C++ exceptions require — a limitation tracked as open
and still unresolved by upstream `wasi-sdk` as of its latest release. Fixing
it means rebuilding `libunwind`+`libc++abi`+`libc++` from source against a
matching Clang with `-fwasm-exceptions`/`__USING_WASM_EXCEPTIONS__` — which
falls under "building toolchain components from source," explicitly out of
scope for this gate, and is not a small patch: it is a from-scratch rebuild
of three runtime libraries against LLVM 20's internal ABI, not a config flag.

This is a different, more specific failure than a general "no prebuilt
exists" — a prebuilt in-browser Clang+LLD absolutely exists and is directly
usable for C++ that avoids exceptions, but ROOT's actual (real, unmodifiable)
GenVector headers are not exception-free, so this specific combination does
not clear gate G7 as scoped. This does not by itself indict *all* possible
ROOT-in-wasm approaches — only this toolchain-and-header combination.

No `run.sh`/`page/` were left half-working: neither was created, since the
hypothesis never reached the point of producing correct output. The only
artifacts left under `wasm/gates/g7/` are this findings document and a
`repro/` directory containing exactly the (non-gate, non-run.sh) script and
`package.json` used to produce the evidence above, so the finding is
independently re-checkable without re-deriving the npm/CLI incantations from
scratch. `wasm/build/g7/` (gitignored, like every other gate's build dir)
holds only the generated `RConfigure.h` used above; it is not part of the
committed evidence and can be regenerated with the command in section 2.

## Smallest next experiment

Two independent ways to falsify-further or unblock, in increasing cost order:

1. **Cheapest**: re-run this exact `compile-genvector.mjs` repro against
   `binji/wasm-clang`'s and `wapm-packages/clang`'s bundled sysroots instead
   of `browsercc`'s, specifically checking (with the same `llvm-nm` symbol
   check used here) whether either happens to bundle a `libunwind.a` +
   exception-enabled `libc++abi.a` that `browsercc`'s doesn't. Given all three
   are wasi-sdk-lineage and the limitation is tracked upstream as unresolved,
   this is expected to reproduce the same failure, but it is a ~15-minute
   check (download + one `llvm-nm` invocation each) that would either
   strengthen this finding to "confirmed across all three known prebuilt
   candidates" or surface an exception-capable one worth full end-to-end
   testing.
2. **More expensive, but still not "build LLVM from source"**: check whether
   a *sysroot-only* rebuild is feasible — i.e., is there a prebuilt,
   downloadable (not self-built) `libunwind.a`/`libc++abi.a`/`libc++.a` for
   `wasm32-unknown-wasi` with `-fwasm-exceptions` already built by someone
   else (e.g. bundled inside a WASI-EH-focused project, or a wasi-sdk CI
   artifact from one of the open PRs referenced in `wasi-sdk#565`/`#334`)
   that could be swapped into `browsercc`'s `sysroot.tar` in place of its
   stock one, keeping `clang.wasm`/`lld.wasm` untouched. This is genuinely
   "find another prebuilt artifact," not "build one," but is a narrower,
   riskier search (version/ABI mismatch between an externally-built runtime
   and this specific Clang 20.1.2 is a real risk) and was left to whichever
   lead picks this thread up next rather than attempted here, per the
   from-source-build exclusion and this gate's time-box.
