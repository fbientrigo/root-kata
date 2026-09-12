# Reproduction — ROOT WebAssembly Subset

Every gate has exactly one entry point that exits `0` and prints `gN PASS`,
or exits non-zero and prints `gN FAIL: <reason>`.

Nothing here writes inside the repository. All toolchain and source state lives under
`$ROOT_WASM_TOOLS` (default `~/.root-kata-wasm`). Build artifacts go to `wasm/build/`,
which is gitignored.

## Current completed gate: G2 — genuine GenVector in WebAssembly

From a clean checkout of `experiment/root-wasm-subset`:

```bash
# 1. install the pinned Emscripten SDK (idempotent; ~minutes on first run, seconds after)
bash wasm/toolchain/install-emsdk.sh

# 2. run the G2 gate (also fetches and verifies pinned ROOT source)
rm -rf wasm/build
bash wasm/gates/g2/run.sh
```

Expected final line: `G2 PASS` (exit 0).

The gate uses unmodified ROOT 6.40.04 GenVector headers plus an `RConfigure.h`
generated at run time from ROOT's `config/RConfigure.in` through CMake
`configure_file`; no generated header is kept in Git. It compiles a native reference
and WebAssembly Node/browser targets, then requires all three outputs to match
`wasm/gates/g2/expected.txt` byte-for-byte.

### G0 toolchain smoke gate

```bash
bash wasm/gates/g0/run.sh
```

G0 remains the independent pinned-toolchain check. G2 invokes the same activation and
also calls `wasm/toolchain/fetch-root-src.sh` itself.

## Falsifiability check

A reproduction that cannot fail proves nothing. To confirm G2 is live:

```bash
edit one number in wasm/gates/g2/expected.txt
bash wasm/gates/g2/run.sh          # must print "G2 FAIL: ..." and exit non-zero
git restore wasm/gates/g2/expected.txt
```

## Pins

| Thing | Pin | Single edit point |
| ----- | --- | ----------------- |
| Emscripten SDK | `4.0.9` | `wasm/toolchain/emsdk.env` |
| CERN ROOT source | `6.40.04` | `wasm/toolchain/root-src.env` |
