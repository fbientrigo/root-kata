# Reproduction — ROOT WebAssembly Subset

Every gate has exactly one entry point that exits `0` and prints `gN PASS`,
or exits non-zero and prints `gN FAIL: <reason>`.

Nothing here writes inside the repository. All toolchain and source state lives under
`$ROOT_WASM_TOOLS` (default `~/.root-kata-wasm`). Build artifacts go to `wasm/build/`,
which is gitignored.

## Current completed gate: G4 — direct `TH1D` blocker

From a clean checkout of `experiment/root-wasm-subset`:

```bash
# 1. install the pinned Emscripten SDK (idempotent; ~minutes on first run, seconds after)
bash wasm/toolchain/install-emsdk.sh

# 2. run the G4 gate (also fetches and verifies pinned ROOT source)
rm -rf wasm/build
bash wasm/gates/g4/run.sh
```

Expected final line: `G4 FAIL: direct TH1D link requires
TH1D::TH1D(char const*, char const*, int, double, double); ...` (exit 1).
This is the completed falsification result, not a broken setup. The first missing
symbol is saved at `wasm/build/g4/first-missing-symbol.txt` and its ROOT source
and CMake dependency chain are in [g4/BLOCKER.md](gates/g4/BLOCKER.md).

The probe uses unmodified ROOT 6.40.04 headers plus an `RConfigure.h` generated
at run time from ROOT's `config/RConfigure.in` through CMake `configure_file`.
It directly links the fixed-sample constructor/`Fill`/statistics program with no
ROOT library. It stops at the first unavoidable symbol; native, Node, Chromium,
and expected-output comparisons run automatically only if that direct link succeeds.

### G0 toolchain smoke gate

```bash
bash wasm/gates/g0/run.sh
```

G0 remains the independent pinned-toolchain check. G2 invokes the same activation and
also calls `wasm/toolchain/fetch-root-src.sh` itself.

## Falsifiability check

A reproduction that cannot fail proves nothing. To confirm G4 still checks the
pinned boundary:

```bash
bash wasm/gates/g4/run.sh          # must print the TH1D constructor blocker and exit non-zero
grep -Fx 'TH1D::TH1D(char const*, char const*, int, double, double)' \
  wasm/build/g4/first-missing-symbol.txt
```

If a future ROOT/toolchain change lets that direct link pass, temporarily corrupt
`wasm/gates/g4/expected.txt`; the native/Node/Chromium comparison path must then
fail before G4 can report `PASS`.

## Pins

| Thing | Pin | Single edit point |
| ----- | --- | ----------------- |
| Emscripten SDK | `4.0.9` | `wasm/toolchain/emsdk.env` |
| CERN ROOT source | `6.40.04` | `wasm/toolchain/root-src.env` |
