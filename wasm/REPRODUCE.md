# Reproduction — ROOT WebAssembly Subset

Every gate has exactly one entry point that exits `0` and prints `gN PASS`,
or exits non-zero and prints `gN FAIL: <reason>`.

Nothing here writes inside the repository. All toolchain and source state lives under
`$ROOT_WASM_TOOLS` (default `~/.root-kata-wasm`). Build artifacts go to `wasm/build/`,
which is gitignored.

## Current completed gate: G7 — compile genuine ROOT C++ client-side in the browser

From a clean checkout of `experiment/root-wasm-subset`:

```bash
# 1. install the pinned Emscripten SDK (idempotent; ~minutes on first run, seconds after)
bash wasm/toolchain/install-emsdk.sh

# 2. run the G7 gate (also fetches and verifies pinned ROOT source and the
#    pinned xeus-cpp-lite/CppInterOp wasm conda packages, ~100 MiB cached
#    outside the repo under $ROOT_WASM_TOOLS)
rm -rf wasm/build
bash wasm/gates/g7/run.sh
```

Expected final line: `G7 PASS` (exit 0). Full evidence in
[g7/FINDINGS.md](gates/g7/FINDINGS.md) (and [g7/H2-FINDINGS.md](gates/g7/H2-FINDINGS.md)
for the parallel hypothesis that was falsified); independent review is recorded in
[g7/CODEX-REVIEW.md](gates/g7/CODEX-REVIEW.md). The gate compiles the already-proven
G2 `genvector.cpp` payload **inside the browser page itself** — via a prebuilt
xeus-cpp-lite/CppInterOp interpreter, driven over the real Jupyter wire protocol,
against the real, sha256-pinned ROOT 6.40.04 headers — then diffs the result against
`wasm/gates/g2/expected.txt`, and separately compiles a deliberately-broken variant to
confirm a genuine compiler diagnostic surfaces (not a canned response). No server-side
compilation, no `SharedArrayBuffer`/threads.

### Earlier gates, still independently reproducible

```bash
bash wasm/gates/g0/run.sh   # pinned-toolchain smoke check
bash wasm/gates/g2/run.sh   # genuine GenVector, host-compiled, runs in Chromium
bash wasm/gates/g4/run.sh   # intentionally exits 1: TH1D direct-link blocker (see g4/BLOCKER.md)
```

## Falsifiability check

A reproduction that cannot fail proves nothing.

To confirm G7 is checking something real (not a canned response), `wasm/gates/g7/run.sh`
already does this on every run: it compiles a deliberately-broken variant of the same
payload and asserts the page surfaces a genuine Clang diagnostic
(`error: no member named 'printfXX'...`) with no stdout. To re-inspect that evidence
directly after a run:

```bash
python3 -c "import json; print(json.load(open('wasm/build/g7/broken_result.json'))['diag'])"
```

To confirm G4 still checks the pinned `TH1D` boundary:

```bash
bash wasm/gates/g4/run.sh          # must print the TH1D constructor blocker and exit non-zero
grep -Fx 'TH1D::TH1D(char const*, char const*, int, double, double)' \
  wasm/build/g4/first-missing-symbol.txt
```

## Pins

| Thing | Pin | Single edit point |
| ----- | --- | ----------------- |
| Emscripten SDK | `4.0.9` | `wasm/toolchain/emsdk.env` |
| CERN ROOT source | `6.40.04` | `wasm/toolchain/root-src.env` |
| xeus-cpp-lite / CppInterOp (wasm) | `xeus-cpp` 0.10.0, `cppinterop` 1.9.0, `xeus` 6.0.5 | `wasm/gates/g7/xcpp-toolchain.env` |
