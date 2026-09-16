# Which TInterpreter services does P0 actually need? (diagnostic probe)

## Result

**Three, plus construction:** `CreateInterpreter`, the constructor, `RegisterModule` (once per
loaded dictionary) and `Initialize`. Nothing else in `TInterpreter` is called by the P0
program — not `AutoLoad`, `AutoParse`, `Declare`, `ProcessLine`, `ClassInfo_*` or any
reflection entry point.

With those four calls stubbed, **the full P0 surface runs in WebAssembly and matches native
ROOT 6.40.04 byte for byte**:

```
diff p0-native.out p0-wasm.out   -> identical, 39 values
```

`p0.cxx` is the unchanged program from [../../p0deps/runtime](../../p0deps/runtime): `TH1D`
construction, weighted fills, underflow and overflow, `GetEntries`, `GetBinContent`,
`Integral`, `GetMean`, `GetStdDev`, the `TAxis` queries, `SetBinContent`/`SetBinError`, a heap
histogram and destruction. Native reference built with the pinned CERN 6.40.04 release; wasm
built with pinned Emscripten 4.0.9 and run in Node.

This confirms in the target runtime what the native audit
([../../p0deps/runtime/FINDINGS.md](../../p0deps/runtime/FINDINGS.md), run `E1`) predicted:
P0 histogram behaviour needs no interpreter service, only the initialization handshake.

## What this probe is, and is not

`probe.cxx` + `stub_methods.inc` are **diagnostic only and must never ship**. Every one of
`TInterpreter`'s 142 pure virtuals is overridden by generated code that logs its name and
returns a default. That is exactly the "silent no-op" the project rules forbid in a product,
which is why:

- it lives in this probe directory, is not part of any gate's PASS path, and is not installed
  into a runtime payload;
- its only claims are (a) the list of methods called, and (b) that the P0 numbers are
  unaffected, which is meaningful *because* the stub does nothing;
- any ROOT feature that genuinely needs an interpreter is wrong under it by construction.

`gen_stub.py` generates the overrides from ROOT's own `core/meta/inc/TInterpreter.h`, so the
list tracks the pinned header rather than a hand-maintained copy.

## Reproduce

```bash
cd wasm/gates/rootlight/interp-probe
python3 gen_stub.py ~/.root-kata-wasm/src/root-6.40.04/core/meta/inc/TInterpreter.h > stub_methods.inc
em++ -std=c++17 -fwasm-exceptions -O1 -I $ROOTSYS/include -sSIDE_MODULE=1 probe.cxx \
     $ROOTSYS/lib/libCore.so -o $ROOTSYS/lib/libCling.so      # $ROOTSYS = the M2 staged tree
RK_INTERP_LOG=calls.log ROOTSYS=$ROOTSYS node p0.js           # p0.cxx linked as in ../run.sh
```

Observed `calls.log` (in order): `CreateInterpreter`, `ctor`, `RegisterModule` ×6 (Core,
Thread, RIO, MathCore, Matrix, Hist), `Initialize`.

## Consequence for M3

The shippable interpreter plugin needs to implement genuinely only:

1. `CreateInterpreter`/`DestroyInterpreter` (the `TROOT.cxx:2251-2262` plugin seam);
2. `RegisterModule` — feed each dictionary's forward declarations and payload code to
   CppInterOp, which is what makes `TClass`/`TFormula` work later;
3. `Initialize`.

Everything else can fail loudly until a milestone needs it (`Declare`, `ProcessLine`, `Calc`
and the `ClassInfo_*` family for M4's `TF1`/`TFormula`). P0 therefore does not depend on M4.

An open question this probe does **not** answer: whether a `RegisterModule` that only records
(rather than declares to a real compiler) is acceptable for P0 in the product. It is not, by
the no-silent-no-op rule — M3 implements it against CppInterOp.
