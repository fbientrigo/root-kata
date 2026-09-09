# Reproduction — ROOT WebAssembly Subset

Every gate has exactly one entry point that exits `0` and prints `gN PASS`,
or exits non-zero and prints `gN FAIL: <reason>`.

Nothing here writes inside the repository. All toolchain and source state lives under
`$ROOT_WASM_TOOLS` (default `~/.root-kata-wasm`). Build artifacts go to `wasm/build/`,
which is gitignored.

## Current gate: G0 — reproducible Emscripten toolchain

From a clean checkout of `experiment/root-wasm-subset`:

```bash
# 1. install the pinned Emscripten SDK (idempotent; ~minutes on first run, seconds after)
bash wasm/toolchain/install-emsdk.sh

# 2. run the gate
rm -rf wasm/build
bash wasm/gates/g0/run.sh
```

Expected final line: `G0 PASS` (exit 0).

`run.sh` compiles `wasm/gates/g0/smoke.cpp` to WebAssembly, executes it under **Node**
and under **headless Chromium**, and requires that both stdouts match each other *and*
`wasm/gates/g0/expected.txt` byte-for-byte. Any divergence is a hard failure.

### Pinned ROOT source (used from G1 onward, not by G0)

```bash
bash wasm/toolchain/fetch-root-src.sh
```

Downloads and sha256-verifies the pinned ROOT tarball into `$ROOT_WASM_TOOLS/cache/`
and unpacks to `$ROOT_WASM_TOOLS/src/root-<version>`. Idempotent; a checksum mismatch
is a hard failure.

## Falsifiability check

A reproduction that cannot fail proves nothing. To confirm the G0 gate is live:

```bash
echo "THIS LINE IS WRONG" >> wasm/gates/g0/expected.txt
bash wasm/gates/g0/run.sh          # must print "G0 FAIL: ..." and exit non-zero
git checkout wasm/gates/g0/expected.txt
```

## Pins

| Thing | Pin | Single edit point |
| ----- | --- | ----------------- |
| Emscripten SDK | `4.0.9` | `wasm/toolchain/emsdk.env` |
| CERN ROOT source | `6.40.04` | `wasm/toolchain/root-src.env` |
