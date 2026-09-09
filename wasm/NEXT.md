# NEXT — one objective for the next session

## Objective

**Gate G2, attempted before G1: compile a single translation unit using genuine
`ROOT::Math::PtEtaPhiMVector` to WebAssembly with `em++`, and execute it in headless
Chromium producing the same numbers as the native build.**

Rationale: G2 is reachable header-only, with no ROOT library, no `libCore`, no Cling and
no rootcling (STATE.md fact 11). G1 as originally worded is blocked behind
`add_dependencies(Core CLING rconfigure)`. Do the cheap, decisive gate first.

## The one thing to settle first

`RConfigure.h` is CMake-generated. Decide, with evidence, which of these is true:

- (a) `rconfigure` can be run standalone from `config/RConfigure.in` without building Cling; or
- (b) a minimal hand-written `RConfigure.h` is legitimate for a header-only GenVector TU; or
- (c) neither — and G2 also needs the CMake configure step.

Do not proceed to declare G2 on a hand-waved stand-in.

## Concrete first experiment

```bash
bash wasm/toolchain/fetch-root-src.sh
source wasm/toolchain/activate.sh
em++ -std=c++17 -O2 \
  -I <generated-config-dir> \
  -I $ROOT_SRC/math/genvector/inc -I $ROOT_SRC/math/mathcore/inc \
  -I $ROOT_SRC/core/foundation/inc -I $ROOT_SRC/core/base/inc \
  gv.cpp -o gv.js
```

Reference native output that the wasm build must reproduce exactly:

```
pt=50.000000 eta=1.200000 phi=0.500000 m=0.105658
E=90.532840 px=43.879128 py=23.971277 pz=75.473068
sum_m=106.650073 sum_pt=57.553466
```

## Deliverable

`wasm/gates/g2/run.sh` printing `G2 PASS`, built on the same Node-vs-Chromium equivalence
harness as `wasm/gates/g0/run.sh`. Reuse that harness; do not invent a second one.

## Explicitly not next session

Do not attempt `TH1D`, `libMathCore.so`, rootcling, or any CMake-driven ROOT build.
Fact 12 says the GenVector bypass does not extend to Hist; that needs its own gate and its
own evidence.
