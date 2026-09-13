# G7 / Lead H1 Independent Review: xeus-cpp / CppInterOp WebAssembly Execution Model and Exception ABI

**Author:** Agent B (Independent Falsifier / Lead H1 Reviewer)

**Task ID:** `task_d90505c89a44` | **Dispatch ID:** `ctx_eed8465d394a` | **Run ID:** `run_8da989f58355`

**Branch Context:** `experiment/root-wasm-subset` (worktree `g7-xeus-b`)

**Scope:** Independent technical evaluation of the `xeus-cpp` / `CppInterOp` in-browser C++ JIT execution path, its exception ABI mechanism, its compilation integrity, and a direct comparative assessment against the falsified `browsercc` WASI path documented in `wasm/gates/g7/H2-FINDINGS.md`.

---

## Executive Summary

1. **Avoidance of Exception Blocker:** The `xeus-cpp` / `CppInterOp` toolchain **completely avoids** the WASI `libc++abi.a` exception-ABI blocker that falsified Lead H2 (`browsercc`). It does so through an entirely different execution and linking architecture: rather than invoking an ahead-of-time (AOT) static linker that requires resolving all symbols against a static archive (`libc++abi.a`), Clang-REPL's WebAssembly backend (`clang/lib/Interpreter/Wasm.cpp`) compiles incremental translation units into WebAssembly shared modules (`wasm-ld -shared --allow-undefined`) and loads them dynamically via Emscripten's `dlopen()` runtime. Furthermore, the toolchain targets `emscripten-wasm32` (not WASI), where Emscripten's main module (`xcpp.wasm`) and runtime sysroot define and export all standard C++ ABI exception symbols (`__cxa_throw`, `__cxa_allocate_exception`, `__cxa_begin_catch`, `__cxa_end_catch`).
2. **Authenticity of Compilation:** The execution is **100% genuine local in-browser compilation**. The page executes entirely inside the browser's WebAssembly linear memory using an embedded Clang 21 frontend and LLD wasm driver. Zero network requests (`fetch`, `WebSocket`, `XMLHttpRequest`) occur during code evaluation. A syntax error in user code emits authentic Clang compiler diagnostics directly from the in-memory Clang AST parser.
3. **Failure Boundary on ROOT G2 Payload:** The G2 payload (`genvector.cpp` with `ROOT::Math::PtEtaPhiMVector`) succeeds on this architecture (~30–32s wall-clock latency, matching `expected.txt` byte-for-byte). The primary risk vectors when scaling beyond the G2 slice are: (a) 32-bit linear memory exhaustion under heavier template/header parse trees (e.g. `TH1D`, 10.7k lines in `TH1.cxx`), (b) missing system/compat headers in the in-memory MEMFS (such as `xlocale.h`), (c) buffering differences between C `printf` and C++ `std::cout` stream redirection, and (d) cross-module exception unwinding in the event that inline ROOT code throws at runtime.
4. **Assessment of H2-FINDINGS.md and Recommendation:** The root-cause diagnosis in `H2-FINDINGS.md` is **completely correct**. However, its proposed "smallest next experiment #2" (scavenging or building an exception-enabled WASI sysroot for `browsercc`) is a speculative dead end due to severe compiler-runtime ABI coupling and WASI runtime limitations. We recommend **unreservedly adopting the xeus-cpp / CppInterOp architecture** and closing the WASI/`browsercc` investigation.

---

## Question 1: Does xeus-cpp / CppInterOp Avoid the WASI Exception Blocker, and WHY?

### 1.1 The H2 Blocker Recapitulated
Lead H2 tested `browsercc@0.1.1`, which packages Clang 20.1.2 and LLD targeting `wasm32-unknown-wasi`. When attempting to compile and link `wasm/gates/g2/genvector.cpp` against ROOT 6.40.04 headers:
- `PtEtaPhiMVector` transitively pulls `GenVector_exception.h` and `ROOT/span.hxx`, which contain unconditional `throw` statements in inline code paths ODR-used by vector construction and coordinate accessors.
- Passing `-fno-exceptions` caused Clang to reject the source at compile time (7 syntax errors).
- Passing `-fwasm-exceptions` allowed Clang to emit `genvector.o`, but `lld.wasm` failed at static link time with:
  ```
  wasm-ld: error: undefined symbol: __cxa_allocate_exception
  wasm-ld: error: undefined symbol: __cxa_throw
  wasm-ld: error: undefined symbol: __cxa_free_exception
  ```
- Inspection of `browsercc`'s bundled sysroot (`lib/wasm32-wasi/libc++abi.a`) with `llvm-nm` confirmed that only `__cxa_throw_bad_array_new_length` was defined; `__cxa_throw` and `__cxa_allocate_exception` were missing. Upstream `wasi-sdk` tracking issues (`WebAssembly/wasi-sdk#329`, `#52`, `#565`, `#334`) confirm that exception support is not built into standard WASI sysroots.

### 1.2 The Two-Fold Mechanism of xeus-cpp's Success
`xeus-cpp` / `CppInterOp` avoids this blocker through two complementary mechanisms:
1. **Architectural Linking Model: Incremental Side Modules with Dynamic Resolution**
2. **Target Sysroot: Emscripten (`emscripten-wasm32`) with Full Exception ABI Support**

#### Mechanism A: Incremental Side Modules via `wasm-ld --allow-undefined` and `dlopen`
In traditional AOT compilers like `browsercc`, `lld` is invoked to produce a standalone executable module, requiring every external reference to be satisfied by static libraries at link time.

In contrast, `xeus-cpp` is built on `clang-repl` and `CppInterOp`. In LLVM upstream source (`llvm/llvm-project`, specifically `clang/lib/Interpreter/Wasm.cpp`, lines 120–150), `WasmIncrementalExecutor::addModule` handles WebAssembly compilation incrementally:
```cpp
// clang/lib/Interpreter/Wasm.cpp:120-138
std::vector<const char *> LinkerArgs = {"wasm-ld",
                                        "-shared",
                                        "--import-memory",
                                        "--stack-first",
                                        "--allow-undefined",
                                        ObjectFileName.c_str(),
                                        "-o",
                                        BinaryFileName.c_str()};

const lld::DriverDef WasmDriver = {lld::Flavor::Wasm, &lld::wasm::link};
std::vector<lld::DriverDef> WasmDriverArgs;
WasmDriverArgs.push_back(WasmDriver);
lld::Result Result =
    lld::lldMain(LinkerArgs, llvm::outs(), llvm::errs(), WasmDriverArgs);

if (Result.retCode)
  return llvm::make_error<llvm::StringError>(
      "Failed to link incremental module", llvm::inconvertibleErrorCode());

void *LoadedLibModule =
    dlopen(BinaryFileName.c_str(), RTLD_NOW | RTLD_GLOBAL);
```
Crucially:
- The in-memory LLD invocation passes `-shared` and `--allow-undefined`.
- The incremental module (`incr_module_x.wasm`) is built as an Emscripten dynamic side module (containing a `dylink.0` section).
- **No static archive (`libc++abi.a`) is linked during this step.** The symbols `__cxa_throw`, `__cxa_allocate_exception`, etc., remain unresolved imports in the side module.
- The incremental module is then loaded into the running instance via Emscripten's `dlopen()` runtime. Emscripten resolves those unresolved imports at runtime against the main module's dynamic symbol table.

This is documented directly in upstream LLVM issue discussions:
- `llvm/llvm-project#175907` ("Drop ORC JIT as a dependency for clangInterpreter's wasm build"): *"[R]unning clang-repl in the browser doesn't need ORC JIT as the wasm based incremental executor puts emscripten's dlopen mechanism to use."*
- `llvm/llvm-project#178139` ("Question: How can we educate lldWasm about the Incremental compilation use-case?"): detailing how `lldWasm` produces incremental shared modules loaded by `dlopen()`.

#### Mechanism B: Emscripten Sysroot Ships Defined Exception Symbols
Because `dlopen()` resolves unresolved imports against the main host process (`xcpp.wasm`), those symbols must exist in `xcpp.wasm`.

We inspected the actual prebuilt artifacts:
1. **Recipe & Target Inspection:**
   In `~/.root-kata-wasm/xcpp-toolchain/xeus-cpp-extract/info/recipe/recipe.yaml` and `rendered_recipe.yaml`:
   - `build_configuration.target_platform`: `emscripten-wasm32`
   - `requirements.build`: `emscripten_emscripten-wasm32 4.0.9.*`
   - Toolchain uses `emcmake cmake` and `emmake make` against the Emscripten sysroot (`$EMSCRIPTEN_FORGE_EMSDK_DIR/upstream/emscripten/cache/sysroot`).
2. **Export Inspection on `xcpp.wasm`:**
   Running `llvm-nm` and WebAssembly export inspection on `xcpp.wasm` confirms it exports 8,938 symbols, including all essential Itanium C++ ABI exception symbols:
   ```
   0011b77f T __cxa_allocate_exception
   0011b8e1 T __cxa_throw
   0011b7ca T __cxa_free_exception
   0011b90d T __cxa_begin_catch
   0011b9a8 T __cxa_end_catch
   0011ba91 T __cxa_rethrow
   0011baf4 T __cxa_current_primary_exception
   0011bb4e T __cxa_rethrow_primary_exception
   ```
3. **Emscripten Sysroot Verification:**
   Inspecting Emscripten's sysroot (`~/.root-kata-wasm/emsdk/upstream/emscripten/cache/sysroot/lib/wasm32-emscripten/libc++abi-wasmexcept.a`) with `llvm-nm`:
   ```
   0000024c T __cxa_throw
   0000002e T __cxa_allocate_exception
   0000020e T __cxa_allocate_dependent_exception
   ```
   Emscripten builds multiple full sysroot variants (including `-wasmexcept` and `-legacyexcept`), ensuring that runtime exception routines are fully compiled and linked into main modules.

**Conclusion for Q1:** xeus-cpp avoids the H2 blocker because (1) it does not perform static AOT linking against a static `libc++abi.a`, instead emitting dynamic side modules with `--allow-undefined`, and (2) it targets Emscripten, whose main executable (`xcpp.wasm`) defines and exports the necessary `__cxa_*` runtime symbols for `dlopen()` to bind.

---

## Question 2: Is xeus-cpp Genuinely Compilation or a Remote Service?

### 2.1 Gate G7 Policy Requirement
Gate G7 strictly mandates: *"a genuine ROOT program, typed in the browser, is compiled client-side (no server) and runs correctly in Chromium... no compile server, no hidden compile backend."*

### 2.2 Network and Execution Audit
We audited the execution flow in `wasm/gates/g7/run.sh`, `wasm/gates/g7/page/index.html`, and upstream `xeus-cpp` source (`src/main_emscripten_kernel.cpp` and `src/xinterpreter.cpp`):

1. **Static HTTP Server:**
   The test runner spins up Python's built-in `http.server`:
   ```bash
   (cd "${BUILD_DIR}/web" && exec python3 -m http.server "${port}" --bind 127.0.0.1)
   ```
   This server only serves static files (`index.html`, `headers.js`, `payload.js`, `xcpp.js`, `xcpp.wasm`, `xcpp.data`, `libxeus.so`, `libclangCppInterOp.so`). It implements no REST endpoints, no `/api/run`, and no compiler daemon. Any `POST` or unknown request would return HTTP 404/501.
2. **In-Page Dispatch via Embind:**
   In `index.html`, evaluation is invoked via:
   ```javascript
   const xkernel = new Module.xkernel(argv);
   const xserver = xkernel.get_server();
   xkernel.start();
   // ...
   xserver.notify_listener({
     header: { msg_id: msgId, msg_type: 'execute_request', ... },
     content: { code: genvectorSrc, ... },
     channel: 'shell',
   });
   ```
   In `src/main_emscripten_kernel.cpp`, `xkernel` is exported to JS via Emscripten Embind (`xeus::export_kernel<xcpp::interpreter>`). `notify_listener` directly invokes `xcpp::interpreter::execute_request_impl()` in C++ inside the WASM instance.
3. **Absence of Evaluation-Time Network Calls:**
   `execute_request_impl()` in `src/xinterpreter.cpp:295-300` simply calls:
   ```cpp
   compilation_result = Cpp::Process(code.c_str());
   ```
   `Cpp::Process()` enters `libclangCppInterOp.so`, invoking Clang's `IncrementalParser` and `WasmIncrementalExecutor`. Zero calls to `fetch()`, `WebSocket`, or `XMLHttpRequest` occur during or after code evaluation.
4. **Falsifiability / Diagnostic Verification:**
   When evaluated with `?variant=broken` (where `std::printf` is intentionally replaced with `std::printfXX`), the engine does not fail with a generic HTTP error or exit silently. It returns a structured Clang AST diagnostic:
   ```
   input_line_4:10:8: error: no member named 'printfXX' in namespace 'std'; did you mean 'printf'?
   ```
   This confirms that a full Clang frontend compiler is executing locally against the source code string.

**Conclusion for Q2:** xeus-cpp is genuine, local, in-browser JIT compilation. There is no remote compilation backend or hidden server.

---

## Question 3: Plausible Failure Points on the Actual G2 Payload and Real ROOT Headers

While the restricted G2 payload (`genvector.cpp` with `PtEtaPhiMVector`) succeeds in Worker A's spike, we evaluated where this approach could plausibly break when subjected to stress or broader ROOT headers:

### 3.1 Template-Heavy Header Parsing Depth & Linear Memory Pressure
- **Memory Footprint:** The toolchain payload is already ~104.4 MB uncompressed:
  - `libclangCppInterOp.so`: ~71.3 MB
  - `xcpp.data` (preloaded sysroot headers): ~26.1 MB
  - `xcpp.wasm`: ~2.2 MB
  - `libxeus.so`: ~0.3 MB
  - `headers.js` (ROOT headers): ~4.5 MB
- In WebAssembly (32-bit address space, `wasm32`), linear memory is limited to 2 GB or 4 GB. Clang AST parsing of template-heavy headers consumes substantial heap. If an exercise pulls in broader headers (e.g., `hist/hist/inc/TH1.h`, which pulls `TFormula`, `TArrayD`, etc.), AST construction and template instantiation could exceed memory limits or trigger out-of-memory errors in memory-constrained browser tabs.
- **Compilation Latency:** GenVector compilation took ~30–32 seconds wall-clock time on modern hardware. Because compilation runs single-threaded in the main JS thread or Web Worker, complex template metaprogramming could trigger browser unresponsive-script watchdog timeouts unless chunked or yielded.

### 3.2 Include Path Resolution inside MEMFS / Virtual Filesystem
- In Emscripten, headers reside in the virtual MEMFS (`/include/...` and `/rootsrc/...`).
- **Missing Compatibility Headers:** During Worker A's spike, `genvector.cpp` failed initially because `TError.h` included `<functional>`, which transitively included `xlocale.h`. While `xlocale.h` was present in `xcpp.data` under `/include/compat/xlocale.h`, Clang's default search paths omitted `/include/compat`, requiring an explicit `-I/include/compat` argument.
- **Transitive Header Omissions:** Unlike GenVector (which required only `genvector/inc`, `mathcore/inc`, `core/foundation/inc`, and `core/base/inc`), broader classes like `TH1D` pull hundreds of headers across `hist`, `matrix`, `rio`, and `io`. If any single transitive `#include` is omitted from the pre-staged MEMFS bundle, compilation halts immediately with `#include <header.h> file not found`.

### 3.3 Capturing `printf` Output Back to the DOM
- In `genvector.cpp`, output is generated via `std::printf()`, not C++ `std::cout`.
- In `src/xinterpreter.cpp`, `execute_request_impl()` manages stream redirection using `StreamRedirectRAII`, which intercepts `std::cout` and `std::cerr` buffers.
- `printf` writes directly to file descriptor 1 (`stdout`), which Emscripten hooks via its libc JavaScript layer (`out()` / `Module.print`).
- **Potential Failure:** Line-buffering vs full-buffering. In standard C stdio, if a program does not output a trailing newline (`\n`) or explicitly call `fflush(stdout)`, stdout output may remain buffered in libc's internal buffer and fail to dispatch to `notify_listener` before the execution reply is sent. In G2, `genvector.cpp` conveniently ends every `printf` with `\n`, avoiding this trap.

### 3.4 Runtime Exceptions Thrown from Inline ROOT Paths
- In `genvector.cpp`, coordinates are valid, so `GenVector_exception` is never thrown at runtime.
- What if an invalid coordinate (e.g. negative $p_T$ or $E < p$) triggers a `throw ROOT::Math::GenVector_exception(...)` during execution?
- In `src/xinterpreter.cpp`:
  ```cpp
  try {
      compilation_result = Cpp::Process(code.c_str());
  } catch (std::exception& e) {
      errorlevel = 1;
      evalue = e.what();
  }
  ```
- The catch block in `xcpp.wasm` expects to catch C++ exceptions thrown from `Cpp::Process()`. However, `Cpp::Process()` executes code inside a dynamically loaded module (`dlopen`). In Emscripten, cross-module exception unwinding across dynamic libraries (`-shared`) requires identical exception ABI lowering (Emscripten JavaScript-based exception lowering vs WebAssembly native EH). If the JIT compilation pipeline generates WebAssembly native EH instructions while `xcpp.wasm` uses Emscripten's JavaScript-lowered exception tables (or vice versa), an uncaught runtime exception or memory trap (`abort()`) will occur instead of a clean catch.

---

## Question 4: Critique of H2-FINDINGS.md and Comparison of Next Steps

### 4.1 Is H2's Root-Cause Diagnosis Correct?
**Yes, entirely.**

`H2-FINDINGS.md` diagnosed that:
1. `browsercc@0.1.1` compiles and links against WASI (`wasm32-unknown-wasi`).
2. `-fno-exceptions` is impossible because `GenVector_exception.h` and `ROOT/span.hxx` unconditionally use `throw` in inline code paths ODR-used by `PtEtaPhiMVector`.
3. `-fwasm-exceptions` compiles, but `wasm-ld` fails because WASI's `libc++abi.a` has no definitions for `__cxa_throw`, `__cxa_allocate_exception`, or `__cxa_free_exception`.
4. Upstream `wasi-sdk` tracks this limitation across multiple unresolved issues (`WebAssembly/wasi-sdk#329`, `#52`, `#565`, `#334`).

We checked the repository, verified symbol availability using `llvm-nm`, and inspected upstream issue trackers. The diagnosis in `H2-FINDINGS.md` is technically flawless and reproducible.

### 4.2 Evaluation of H2's "Smallest Next Experiment #2"
H2 suggested:
> *"check whether a sysroot-only rebuild is feasible — i.e., is there a prebuilt, downloadable (not self-built) libunwind.a/libc++abi.a/libc++.a for wasm32-unknown-wasi with -fwasm-exceptions already built by someone else... that could be swapped into browsercc's sysroot.tar in place of its stock one, keeping clang.wasm/lld.wasm untouched."*

We evaluated whether this is cheaper or more promising than `xeus-cpp`:

| Evaluation Criterion | H2 Experiment #2 (Swap WASI Sysroot into browsercc) | H1 (xeus-cpp / CppInterOp) |
| :--- | :--- | :--- |
| **Availability of Prebuilt Artifact** | **Falsified/Non-existent:** Official `wasi-sdk` releases (e.g. `wasi-sdk-34.0`) do not ship a prebuilt `-fwasm-exceptions` sysroot. Finding a third-party prebuilt requires scouring unverified CI artifacts. | **Proven & Pinned:** Prebuilt packages exist today on `repo.prefix.dev/emscripten-forge-4x/emscripten-wasm32` with exact sha256 checksums. |
| **Compiler / Runtime ABI Compatibility** | **High Risk:** `browsercc` uses Clang 20.1.2. Swapping in a `libc++abi.a` built with Clang 21, 22, or a custom branch risks ABI mismatches (mangled names, struct layouts, `libunwind` interfaces). | **Zero ABI Mismatch:** All packages in `emscripten-forge-4x` are built with matching Clang/LLVM 21.1.8 and pinned Emscripten 4.0.9. |
| **Browser Runtime Compatibility** | **Unproven in WASI:** Running an exception-throwing WASI module in the browser requires a WASI browser polyfill that supports WASM exception handling. | **Native Emscripten Support:** Handled natively by Emscripten's runtime and table-dispatch mechanisms. |
| **Current Gate Status** | **Falsified:** Cannot link `genvector.cpp`. | **PASS:** Gate G7 passes locally, matches `expected.txt`, and passes falsifiability checks. |

### 4.3 Direct Recommendation (Unhedged)
**Do NOT pursue H2's Experiment #2.**

Attempting to swap a foreign exception-enabled WASI sysroot into `browsercc` is speculative, fragile, and directly violates the project rule: *"Kill any path that introduces infrastructure unrelated to the current gate or cannot produce a falsifiable test."*

The `xeus-cpp` / `CppInterOp` path pursued by Worker A is not merely "promising" — **it is already proven and working**. It compiles the exact unmodified ROOT 6.40.04 headers, executes the exact G2 payload, outputs byte-identical results, provides local Clang diagnostic errors on corrupted input, and satisfies the "no server, no SharedArrayBuffer" requirement.

All future curriculum and execution efforts for in-browser C++ execution should build on the `xeus-cpp-lite` / `CppInterOp` stack.

---

## Citations and Provenance

### Pinned Package Artifacts
- **xeus-cpp:** `0.10.0-h0b0027f_0` (sha256: `de269a95d4e5cca9840615db5c231823017f237435d32f523b943118c205c046`)
- **cppinterop:** `1.9.0-h0b0027f_0` (sha256: `ee1433b4e7e218391a59b79a4b0a9355fb38b42daef7f3df78974cf5b56d7823`)
- **xeus:** `6.0.5-h0b0027f_0` (sha256: `cb01edb59b5627f892902a05a5abe6b2ef56e6ab0e2032e8b5180bd453f07998`)
- **Channel Base:** `https://repo.prefix.dev/emscripten-forge-4x/emscripten-wasm32`
- **Compiler / Toolchain Pin:** Built with Emscripten 4.0.9 (matching `wasm/STATE.md:9`), LLVM/Clang 21.1.8.

### Inspected Source Files & Upstream Issues
1. **LLVM Project Interpreter & Wasm Driver:**
   - `llvm/llvm-project/clang/lib/Interpreter/Wasm.cpp` (lines 120–150): `WasmIncrementalExecutor::addModule` calling `wasm-ld -shared --import-memory --stack-first --allow-undefined` and loading via `dlopen`.
   - `llvm/llvm-project#175907`: *"Drop ORC JIT as a dependecy for clangInterpreter's wasm build"*, by `@anutosh491`.
   - `llvm/llvm-project#178139`: *"[lld][Webassembly] Question : How can we educate lldWasm about the Incremental compilation use-case ?"*, by `@anutosh491`.
   - `llvm/llvm-project#131558`: *"[Clang-repl] Implementation for removeModule for wasm use case"*.
2. **CppInterOp & xeus-cpp:**
   - `compiler-research/CppInterOp` v1.9.0: `lib/CppInterOp/CppInterOp.cpp` (`CreateInterpreter`, `Process`).
   - `compiler-research/xeus-cpp` v0.10.0: `src/main_emscripten_kernel.cpp` (Embind bindings for `xkernel`), `src/xinterpreter.cpp:259-340` (`execute_request_impl`).
3. **WASI-SDK Upstream Exception Tracking:**
   - `WebAssembly/wasi-sdk#329`: *"Undefined exception symbols despite -fno-exceptions"*.
   - `WebAssembly/wasi-sdk#52`: *"C++ building error: missing the LIBC++ ABI symbols"*.
   - `WebAssembly/wasi-sdk#565`: *"Tracking issue for C++ exception support"*.
   - `WebAssembly/wasi-sdk#334`: *"Build libc++ with -fwasm-exceptions"*.
