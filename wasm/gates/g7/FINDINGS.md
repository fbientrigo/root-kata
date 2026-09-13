# Gate G7 findings — compiling genuine ROOT C++ inside the browser

**Gate claim:** a genuine ROOT program, typed in the browser, is compiled client-side
(no server) and runs correctly in Chromium. Narrowed and pulled forward ahead of a
`TH1D` build-system decision because it is a prerequisite for G8 regardless of which
ROOT surface is eventually proven, and no earlier gate (including G2) had tested it —
G0/G2/G4 all compiled on a host `em++` and only *ran* the resulting `.wasm` in Chromium.

**Verdict: G7 PASS**, via hypothesis H1. Canonical reproduction: `bash wasm/gates/g7/run.sh`
(passed twice consecutively from a clean `wasm/build/g7/`, verified independently by the
orchestrator, not only by the implementing lead).

Two independent hypotheses were run in parallel, each in an isolated worktree, against the
identical payload (`wasm/gates/g2/genvector.cpp`, unmodified — already proven correct when
compiled by a host `em++` in gate G2) so that a pass or fail would be unambiguous.

## H1 — xeus-cpp-lite / CppInterOp (Clang-Repl-based): PASS

The actual prebuilt artifact is not an npm/GitHub-release binary — CppInterOp/xeus-cpp
ship source-only tags. The real prebuilt binaries are conda packages built by the
compiler-research project's own CI on the `emscripten-forge-4x` channel:

| Package | Version | Provides |
| --- | --- | --- |
| `xeus-cpp` | 0.10.0 | `xcpp.js`/`xcpp.wasm`/`xcpp.data` — the interpreter kernel, exporting an `xkernel` class via embind |
| `cppinterop` | 1.9.0 | `libclangCppInterOp.so` — Clang/LLVM 21.1.8 as a wasm dynamic library, `dlopen`'d by `xcpp.wasm` |
| `xeus` | 6.0.5 | `libxeus.so` — the other `dlopen`'d dependency |

Sha256-pinned in `wasm/gates/g7/xcpp-toolchain.env`; **the orchestrator independently
re-verified all three pins against the channel's live `repodata.json`** — they match exactly.

The page instantiates `Module.xkernel`, calls `get_server()`, and drives it with a genuine
Jupyter wire-protocol `execute_request` message (`msg_type: 'execute_request'`) — the same
protocol xeus-cpp uses for real. This is not a bespoke shortcut API.

**Correctness:** re-run independently by the orchestrator, twice consecutively from clean.
Output byte-identical to `wasm/gates/g2/expected.txt`:
```
pt=50.000000 eta=1.200000 phi=0.500000 m=0.105658
E=90.532840 px=43.879128 py=23.971277 pz=75.473068
sum_m=54.847433 sum_pt=52.238727
```

**Falsifiability:** a one-identifier-typo variant (`std::printfXX`) produces a genuine Clang
diagnostic, independently inspected by the orchestrator in the captured JSON:
```
input_line_2:10:8: error: no member named 'printfXX' in namespace 'std'; did you
      mean 'printf'?
/include/c++/v1/cstdio:167:9: note: 'printf' declared here
```
and zero stdout. This is Clang's own diagnostic format pointing at a real libc++ header
path inside the wasm sandbox — not producible by a canned response.

**Threads:** no `SharedArrayBuffer`/`Atomics` anywhere in `xcpp.js`; the whole run passed
under plain `python3 -m http.server` (confirmed via `curl -D-`: no COOP/COEP headers sent)
under `--headless --no-sandbox`. Satisfies the hard constraint (GitHub Pages cannot set
COOP/COEP).

**Payload:** 104,369,411 bytes total (~99.5 MiB): `libclangCppInterOp.so` 71.3MB,
`xcpp.data` 26.1MB, `xcpp.wasm` 2.2MB, `xcpp.js` 2.2MB, `headers.js` 2.3MB (the 355
mounted ROOT header files, 2.2MB), `libxeus.so` 0.3MB.

**Timing:** ~34s wall-clock, page-load to first correct output, dominated by the 71MB
`libclangCppInterOp.so` fetch over localhost — a real network would be slower on first
load, cached (browser HTTP cache / service worker) on repeat visits.

**One genuine wrinkle, not a shim:** the prebuilt `xcpp.wasm`'s auto-detected system
include path omits Emscripten's own `compat/` directory, which `<functional>` transitively
needs via `<__locale>` → `compat/xlocale.h`. That file already exists inside `xcpp.data`;
the fix was adding `-I/include/compat` to the interpreter's argv, not writing a
replacement header.

**Methodology note:** `wasm/gates/common/run-wasm-program.sh`'s `--virtual-time-budget`/
`--dump-dom` pattern (used by G0/G2/G4) does not work here — Chromium's virtual time
fast-forwards past a ~100MB real fetch and dumps the DOM mid-load. `wasm/gates/g7/drive.mjs`
instead drives Chromium over a real Chrome DevTools Protocol WebSocket with a real
wall-clock timeout (Node's built-in `fetch`/`WebSocket`, no new dependencies). This is a
new pattern specific to gates that load large payloads; `wasm/gates/common/` was left
untouched since no other gate needs it yet.

## H2 — Clang+LLD compiled to WebAssembly (AOT, WASI-targeted): FALSIFIED

Full detail in `wasm/gates/g7/H2-FINDINGS.md`. Summary: the prebuilt `browsercc` npm
package (real Clang 20.1.2 + LLD, both compiled to `wasm32-unknown-wasi`) genuinely
compiled the unmodified `genvector.cpp` against the real ROOT headers in ~4.5s — but
**linking failed**: undefined symbols `__cxa_allocate_exception`/`__cxa_throw`. ROOT's
own `GenVector_exception.h` documents that its `Throw()` is deliberately kept inline in
the header specifically so interactive/inline usage of `PtEtaPhiMVector` doesn't need a
separate library — i.e. the exception path is load-bearing ROOT design, not incidental.
Root cause, confirmed via `llvm-nm` on the extracted `libc++abi.a`: this WASI sysroot's
`libc++abi` ships no exception-throwing runtime symbols at all — a known, currently-open
upstream wasi-sdk gap (public issues #329, #52, #565, #334), shared by every WASI-lineage
prebuilt clang+lld (browsercc, binji/wasm-clang, wapm-packages/clang all descend from the
same wasi-sdk libc++abi). Fixing it means rebuilding `libunwind`+`libc++abi`+`libc++`
from source — explicitly out of scope for a gate.

Did **not** require threads/SharedArrayBuffer (confirmed via glue-code grep and
`WebAssembly.Module.imports`), so this path is not disqualified on the hosting
constraint — only on the exception-handling gap.

## H3 — hosting constraints: folded into H1/H2, not run separately

The GitHub Pages no-COOP/COEP constraint was already established from reading
`src/root_kata/web_server.py` (no COOP/COEP headers set anywhere) before this gate, and
both H1 and H2 independently confirmed their toolchains' actual thread requirements
empirically rather than needing a third, separate static-analysis lead.

## What this does and does not prove

**Proven:** a C++ compiler can run entirely client-side in Chromium, compile real,
unmodified ROOT headers, and produce correct output — Clang-Repl/interpreter
architecture (xeus-cpp-lite), not ahead-of-time compilation.

**Not proven:** anything about `TH1D`. G4 already established that `TH1D` needs a
rootcling-generated dictionary at link time (`wasm/gates/g4/BLOCKER.md`). G7's payload
was deliberately the already-proven GenVector program so a pass/fail would be
unambiguously about the compiler, not about ROOT. Whether xeus-cpp-lite's Clang-Repl
architecture changes the calculus for `TH1D` (an interpreter can, in principle, resolve
symbols differently than a static link — this is genuinely open) is the next question,
not a settled one.

**Payload cost is real and unresolved:** ~100MB for the toolchain alone, before any
ROOT library is added. This was accepted per the user's explicit "whatever fidelity
requires" decision, but it is a fact the next session's scoping must account for,
not a detail to lose.
