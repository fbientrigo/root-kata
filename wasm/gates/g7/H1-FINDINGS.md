# G7 / Lead H1 Finding: `xeus-cpp-lite` / `CppInterOp` (Clang-Repl as WebAssembly) — HYPOTHESIS CONFIRMED (PASS)

**Verdict: Gate G7 PASS.**
A prebuilt, genuine in-browser C++ toolchain compiles the unmodified `wasm/gates/g2/genvector.cpp` entirely inside Chromium against the real sha256-pinned ROOT 6.40.04 headers, links/loads it into the runtime, and executes it producing byte-identical output to `wasm/gates/g2/expected.txt`. No server-side compilation, no custom ROOT reimplementations, and no `SharedArrayBuffer`/pthreads/COOP/COEP headers are required.

Canonical reproduction entry point:
```bash
bash wasm/gates/g7/run.sh
```
Exits 0 and prints `G7 PASS`.

---

## Hypothesis Under Test

A prebuilt C++ interpreter/compiler toolchain running as WebAssembly in the browser (`xeus-cpp-lite` / `CppInterOp`, based on Clang-Repl) can compile the exact G2 payload (`wasm/gates/g2/genvector.cpp`, unmodified) against the real sha256-pinned ROOT 6.40.04 source tree, execute it client-side in Chromium, and produce output byte-identical to `wasm/gates/g2/expected.txt`, without requiring multithreading or server-side infrastructure.

This directly tests the Emscripten-targeted dynamic JIT/interpreter route against the falsified WASI AOT route (Lead H2 / `browsercc`, which failed at link time due to missing `__cxa_throw` / `__cxa_allocate_exception` in WASI's `libc++abi.a`).

---

## Required Evidence Items

### 1. Upstream Artifact Name, Version, Registry/URL, and Cryptographic Hash

All artifacts are genuine third-party prebuilt WebAssembly packages published on the `emscripten-forge-4x` conda channel on prefix.dev, built by the `compiler-research` project CI:

- **Registry / Base URL:**
  `https://repo.prefix.dev/emscripten-forge-4x/emscripten-wasm32`
- **Channel Metadata:**
  Verified against live `repodata.json`: `https://repo.prefix.dev/emscripten-forge-4x/emscripten-wasm32/repodata.json`

| Package | Version & Build | SHA256 Hash | Size (bytes) | Provided Runtime Files |
|---|---|---|---:|---|
| `xeus-cpp` | `0.10.0-h0b0027f_0` | `de269a95d4e5cca9840615db5c231823017f237435d32f523b943118c205c046` | 3,357,922 | `bin/xcpp.js`, `bin/xcpp.wasm`, `bin/xcpp.data` |
| `cppinterop` | `1.9.0-h0b0027f_0` | `ee1433b4e7e218391a59b79a4b0a9355fb38b42daef7f3df78974cf5b56d7823` | 19,851,624 | `lib/libclangCppInterOp.so.21.1` (staged as `libclangCppInterOp.so`) |
| `xeus` | `6.0.5-h0b0027f_0` | `cb01edb59b5627f892902a05a5abe6b2ef56e6ab0e2032e8b5180bd453f07998` | 310,492 | `lib/libxeus.so` |

Pinned configuration is stored in `wasm/gates/g7/xcpp-toolchain.env` and fetched idempotently via `wasm/gates/g7/fetch-xcpp-toolchain.sh`.

---

### 2. Exact, Re-Runnable Commands

#### A. Full Gate Run (Single Entry Point)
```bash
bash wasm/gates/g7/run.sh
```
This script runs the entire sequence from clean state: activates pinned emsdk and ROOT source, downloads and verifies the toolchain tarballs, generates `RConfigure.h`, packages headers and payload, starts a local HTTP server, drives headless Chromium for both the valid and broken payloads, verifies the diffs, and prints `G7 PASS`.

#### B. Step-by-Step Manual Reproduction

1. **Activate toolchain and ROOT source:**
   ```bash
   bash wasm/toolchain/fetch-root-src.sh
   source wasm/toolchain/activate.sh
   ```

2. **Fetch and unpack xeus-cpp-lite toolchain:**
   ```bash
   bash wasm/gates/g7/fetch-xcpp-toolchain.sh
   ```

3. **Generate `RConfigure.h` using ROOT's template and host `em++` probe:**
   ```bash
   cmake -DROOT_SOURCE="${HOME}/.root-kata-wasm/src/root-6.40.04" \
         -DOUTPUT_HEADER="wasm/build/g7/RConfigure.h" \
         -DCXX="$(command -v em++)" \
         -P "wasm/gates/g2/rconfigure.cmake"
   ```

4. **Package ROOT headers and payload into static assets:**
   ```bash
   mkdir -p wasm/build/g7/web
   python3 wasm/gates/g7/build_headers.py \
     "${HOME}/.root-kata-wasm/src/root-6.40.04" \
     "wasm/build/g7/RConfigure.h" \
     "wasm/build/g7/web/headers.js"
   python3 wasm/gates/g7/build_payload.py \
     "wasm/gates/g2/genvector.cpp" \
     "wasm/gates/g7/web/payload.js"
   cp "${HOME}/.root-kata-wasm/xcpp-toolchain/"{xcpp.js,xcpp.wasm,xcpp.data,libxeus.so,libclangCppInterOp.so} wasm/build/g7/web/
   cp wasm/gates/g7/page/index.html wasm/build/g7/web/index.html
   ```

5. **Serve and drive in headless Chromium:**
   ```bash
   python3 -m http.server 8000 --bind 127.0.0.1 --directory wasm/build/g7/web &
   SERVER_PID=$!
   node wasm/gates/g7/drive.mjs "http://127.0.0.1:8000/index.html?variant=good" "G7-DONE" 180000 wasm/build/g7/chrome-profile
   kill $SERVER_PID
   ```

---

### 3. How the Real ROOT Headers Are Mounted and Exposed

- **Source Headers:** 355 real header files (~2.22 MB of header source) from the verified ROOT 6.40.04 tarball, covering the exact four subtrees used by Gate G2:
  - `math/genvector/inc`
  - `math/mathcore/inc`
  - `core/foundation/inc`
  - `core/base/inc`
- **Configuration Header:** `RConfigure.h` generated at runtime from ROOT's own `config/RConfigure.in` via `wasm/gates/g2/rconfigure.cmake` using the pinned host `em++` compiler probes. It leaves optional ROOT components undefined (`undef`) and defines compiler capability macros (`R__HAS_ATTRIBUTE_ALWAYS_INLINE`, `R__HAS_ATTRIBUTE_NOINLINE`, `ROOT__cplusplus 201703L`). The resulting header was consumed verbatim by the in-browser compiler.
- **Virtual Filesystem Mounting:** `build_headers.py` packages the 355 files plus `RConfigure.h` into a single JavaScript structure `ROOT_HEADERS` in `headers.js`. During page initialization, before starting `xkernel`, the page populates Emscripten's virtual in-memory filesystem:
  ```javascript
  const paths = Object.keys(ROOT_HEADERS);
  for (const vpath of paths) {
    const dir = vpath.substring(0, vpath.lastIndexOf('/'));
    Module.FS.mkdirTree(dir);
    Module.FS.writeFile(vpath, ROOT_HEADERS[vpath]);
  }
  ```
  All ROOT headers are mounted under `/rootsrc/`.
- **Interpreter Arguments:** Passed directly to `Module.xkernel(argv)`:
  ```javascript
  const argv = [
    'xcpp',
    '-std=c++17',
    '-fwasm-exceptions',
    '-I/rootsrc/generated',
    '-I/rootsrc/math/genvector/inc',
    '-I/rootsrc/math/mathcore/inc',
    '-I/rootsrc/core/foundation/inc',
    '-I/rootsrc/core/base/inc',
    '-I/include/compat',
  ];
  ```
  `-I/include/compat` points to the pre-existing `compat/xlocale.h` header bundled inside `xcpp.data` (Emscripten's standard libc++ compatibility header), requiring no custom shims.

---

### 4. C++ Exception Handling Verification

Unlike the WASI toolchain evaluated in H2 where `libc++abi.a` omitted `__cxa_throw` and `__cxa_allocate_exception`, the Emscripten-built `xeus-cpp` binary fully implements and exports C++ exception runtime symbols.

#### A. Symbol Inspection
Using `llvm-nm` from the pinned Emscripten SDK on `xcpp.wasm`:
```bash
$ llvm-nm ~/.root-kata-wasm/xcpp-toolchain/xcpp.wasm | grep -E "__cxa_(throw|allocate_exception)"
0011b77f T __cxa_allocate_exception
0011b8e1 T __cxa_throw
00015b46 T __cxa_throw_bad_array_new_length
```
Both `__cxa_allocate_exception` and `__cxa_throw` are present and defined (`T`) in the main executable.

#### B. Dynamic Symbol Resolution for ROOT GenVector
`ROOT::Math::PtEtaPhiMVector` includes `Math/GenVector/GenVector_exception.h`, which contains an inline `GenVector_Throw()` function calling `throw GenVector_exception(msg)`. Because `__cxa_allocate_exception` and `__cxa_throw` are resolved by `xcpp.wasm`, compiling `genvector.cpp` generates an incremental module that resolves all dynamic relocations without error.

#### C. Empirical Throw / Catch Round Trip in Chromium
To verify that exceptions not only link but also execute and unwind correctly inside Chromium, a throw/catch round trip was executed through `xkernel`:

```cpp
#include <cstdio>
#include <stdexcept>

int test_exceptions() {
  try {
    throw std::runtime_error("test exception caught successfully");
  } catch (const std::exception& e) {
    std::printf("CAUGHT: %s\n", e.what());
    return 0;
  }
  return 1;
}
test_exceptions();
```

With `-fwasm-exceptions` in `argv`, Clang configures LLVM's WebAssembly exception handling:
```
-target-feature +exception-handling -target-feature +multivalue -target-feature +reference-types -exception-model=wasm -mllvm -wasm-enable-eh
```
Execution in headless Chromium completed with:
```
CAUGHT: test exception caught successfully
```
and exited cleanly with zero errors. This proves that:
1. `__cxa_allocate_exception` and `__cxa_throw` allocate and raise genuine C++ exceptions;
2. `try / catch` blocks in JIT-compiled incremental modules catch the exception;
3. `e.what()` is accessible across the exception object;
4. Unwinding completes without crashing or leaking to the JavaScript host.

---

### 5. Multithreading / SharedArrayBuffer / COOP / COEP Assessment

Checked and confirmed single-threaded through three distinct checks:

1. **Grepping JS Glue for Threading Primitives:**
   - `SharedArrayBuffer`: **0 matches** in `xcpp.js`.
   - `Atomics`: **0 matches** in `xcpp.js`.
   - `pthread`: **2 matches**, both confined to the static filesystem table entry strings `/include/c++/v1/__thread/support/pthread.h` and `/include/pthread.h` inside `xcpp.data`. No runtime threading APIs are referenced.

2. **WebAssembly Module Imports Inspection:**
   Using Node.js `WebAssembly.Module.imports()` across all modules:
   - `xcpp.wasm`: memory import `{module: "env", name: "memory", kind: "memory"}`
   - `libclangCppInterOp.so`: memory import `{module: "env", name: "memory", kind: "memory"}`
   - `libxeus.so`: memory import `{module: "env", name: "memory", kind: "memory"}`
   Inspection of `xcpp.js` reveals the memory instantiation:
   ```javascript
   new WebAssembly.Memory({initial: INITIAL_MEMORY/65536, maximum: 32768})
   ```
   **`shared: true` is absent.** The WebAssembly memory is an ordinary, unshared memory passed between the main module and side modules via Emscripten dynamic linking.

3. **Execution Without Cross-Origin Isolation:**
   The test harness runs under a standard `python3 -m http.server` without custom HTTP headers.
   - `Cross-Origin-Opener-Policy` (COOP) and `Cross-Origin-Embedder-Policy` (COEP) are not sent.
   - `window.crossOriginIsolated` is `false` in Chromium.
   - Execution passes completely without warnings or failures related to threading.
   This satisfies the deployment constraint for GitHub Pages.

---

### 6. Actual Chromium Execution Result Compared to `expected.txt`

The unmodified `wasm/gates/g2/genvector.cpp` payload was compiled and executed client-side in Chromium. The captured `#output` content was:

```
pt=50.000000 eta=1.200000 phi=0.500000 m=0.105658
E=90.532840 px=43.879128 py=23.971277 pz=75.473068
sum_m=54.847433 sum_pt=52.238727
```

- Unified diff against `wasm/gates/g2/expected.txt`: **empty (0 exit code)**
- SHA256 of `wasm/gates/g2/expected.txt`:
  `048b9aaf4ccb0097213e58105248d666ddec2961cf6ead360e9f974f76553647`
- SHA256 of Chromium captured stdout:
  `048b9aaf4ccb0097213e58105248d666ddec2961cf6ead360e9f974f76553647`

The output is byte-for-byte identical to the native and G2 reference outputs.

---

### 7. Compiler / Interpreter Diagnostics From Deliberately Broken Program

To verify that the harness actually invokes a genuine C++ compiler rather than replaying precomputed output, `wasm/gates/g7/build_payload.py` generates a corrupted variant (`std::printfXX` instead of `std::printf`) invoked via `?variant=broken`.

In Chromium, the execution produced zero stdout and returned the following Clang diagnostic:

```
In file included from <<< inputs >>>:1:
input_line_2:10:8: error: no member named 'printfXX' in namespace 'std'; did you
      mean 'printf'?
   10 |   std::printfXX("pt=%.6f eta=%.6f phi=%.6f m=%.6f\n", muon.Pt(), muon.Et...
      |        ^~~~~~~~
      |        printf
/include/c++/v1/cstdio:167:9: note: 'printf' declared here
  167 | using ::printf _LIBCPP_USING_IF_EXISTS;
      |         ^
Failed to parse via ::process:Parsing failed.
```

This diagnostic:
- Identifies the exact file, line, and column in the REPL input;
- Proposes the correct fix (`did you mean 'printf'?`);
- Cites the declaration in the virtual filesystem at `/include/c++/v1/cstdio:167:9`;
- Emits no stdout.

This confirms the presence of an active, genuine in-browser Clang frontend.

---

### 8. Payload Size and Transfer Budget Analysis

Exact file sizes of all runtime assets required for in-browser execution:

| File | Component Description | Uncompressed Size | gzip -9 Size | brotli Size |
|---|---|---:|---:|---:|
| `libclangCppInterOp.so` | Clang/LLVM 21.1.8 shared library | 71,256,623 bytes (67.96 MiB) | 22,807,516 bytes (21.75 MiB) | 15,652,472 bytes (14.93 MiB) |
| `xcpp.data` | Virtual filesystem image (libc++, headers) | 26,074,947 bytes (24.87 MiB) | 2,995,637 bytes (2.86 MiB) | 1,975,478 bytes (1.88 MiB) |
| `headers.js` | 355 ROOT 6.40.04 headers + RConfigure.h | 2,308,595 bytes (2.20 MiB) | 426,921 bytes (0.41 MiB) | 315,095 bytes (0.30 MiB) |
| `xcpp.wasm` | xeus-cpp kernel WebAssembly binary | 2,240,059 bytes (2.14 MiB) | 746,346 bytes (0.71 MiB) | 591,491 bytes (0.56 MiB) |
| `xcpp.js` | Emscripten runtime JS glue & dynamic linker | 2,193,469 bytes (2.09 MiB) | 304,714 bytes (0.29 MiB) | 222,968 bytes (0.21 MiB) |
| `libxeus.so` | xeus Jupyter kernel protocol library | 289,063 bytes (0.28 MiB) | 85,593 bytes (0.08 MiB) | 65,412 bytes (0.06 MiB) |
| `index.html` | Browser driver & DOM interface | 5,490 bytes (0.01 MiB) | 2,356 bytes (< 0.01 MiB) | 1,949 bytes (< 0.01 MiB) |
| `payload.js` | GenVector test source code | 1,165 bytes (< 0.01 MiB) | 381 bytes (< 0.01 MiB) | 375 bytes (< 0.01 MiB) |
| **Total** | **Full client-side toolchain** | **104,369,411 bytes (~99.53 MiB)** | **27,369,464 bytes (~26.10 MiB)** | **18,825,240 bytes (~17.95 MiB)** |

- **Uncompressed total:** 104,369,411 bytes (~99.53 MiB / 104.37 MB)
- **gzip transfer total:** 27,369,464 bytes (~26.10 MiB / 27.37 MB)
- **Brotli transfer total:** 18,825,240 bytes (~17.95 MiB / 18.83 MB)
- **Largest single file:** `libclangCppInterOp.so` at 71,256,623 bytes (67.96 MiB raw, 22.81 MB gzip, 14.93 MB brotli).

---

## Synthesis: H1 vs H2 Comparison

| Dimension | H1: `xeus-cpp-lite` / `CppInterOp` | H2: `browsercc` (Clang+LLD WASI) |
|---|---|---|
| **Architecture** | In-browser interpreter / JIT (Clang-Repl) | Ahead-of-Time compiler + linker (`clang.wasm` + `lld.wasm`) |
| **Target OS / ABI** | `wasm32-unknown-emscripten` | `wasm32-unknown-wasi` |
| **Exception Handling** | Supported: `__cxa_throw` and `__cxa_allocate_exception` defined in `xcpp.wasm`; native Wasm EH executes throw/catch round trips | **Falsified**: `libc++abi.a` lacks `__cxa_throw` and `__cxa_allocate_exception`; linking fails on `GenVector_exception.h` |
| **Threading Requirement** | None (unshared memory, no SAB/Atomics, runs without COOP/COEP) | None |
| **Real ROOT Headers** | Compiles unmodified ROOT 6.40.04 GenVector headers | Compiles unmodified ROOT 6.40.04 GenVector headers |
| **Link / Execution** | **PASS**: output byte-identical to `expected.txt` | **FAIL**: linker symbol errors prevent module emission |
| **Payload Size** | 104.4 MB uncompressed (26.1 MB gzip / 17.95 MB brotli) | 94.5 MB uncompressed (~40 MB gzip) |
| **Execution Latency** | ~35s wall-clock on localhost | ~4.5s compile time before link failure |

---

## What This Proves and What Remains Open

### What Is Proven
1. Genuine C++ compilation and execution of unmodified ROOT headers inside Chromium without server-side compute is technically viable today using prebuilt, pinned WebAssembly packages.
2. The exception limitation that killed H2 does not apply to H1: the Emscripten toolchain provides exception symbols and supports native WebAssembly exception handling.
3. No cross-origin isolation (COOP/COEP) or multithreading headers are required, making this approach compatible with static hosting environments such as GitHub Pages.

### What Remains Open
1. **Curriculum Coverage (`TH1D` and beyond):**
   Gate G4 proved that `TH1D` constructors ODR-use dictionary symbols (`Class()`, `Streamer()`, `Dictionary()`) generated exclusively by `rootcling`. While `xeus-cpp-lite` successfully executes the GenVector template slice, `TH1D` requires either precompiled ROOT dictionary libraries loaded as dynamic modules or a lightweight client-side dictionary mechanism.
2. **Transfer and Initialization Cost:**
   A ~18–26 MB compressed payload (~100 MB uncompressed) represents a substantial initial load overhead. For a web application, service worker caching or progressive loading will be necessary.
