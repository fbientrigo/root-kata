# NEXT — one objective for the next session

## Objective

Implement **TClass reflection over CppInterOp**, as one designed subsystem. It
is the single boundary everything remaining stops at.

## Why this is next

M2b, M3, M4a and M6a are PASS. Genuine ROOT 6.40.04 runs in Chromium; both
numerical probes match native ROOT byte for byte (39 TH1D/TAxis values, 21
TF1/TFormula/TGraph values); and **11 of the 13 shipped katas are completed in
the browser** with output identical to native ROOT and graded passed by their
own validators ([gates/rootkatas](gates/rootkatas/FINDINGS.md)).

Exactly two exercises remain, and reflection blocks **both** — measured, not
assumed. `cpp-root-histogram` was expected to fail on its `TCanvas`; it does not,
it stops earlier at the same place as `cpp-root-fit-gaussian`:

```
Error in <TCppInterOpInterpreter>: TInterpreter::SetClassInfo is not implemented in wasm ROOT yet
```

So this one subsystem finishes the curriculum's non-graphical surface and tells
us whether M5 graphics is needed at all for the canvas kata.

Following it one error at a time gave `CheckClassInfo` (implemented) and then
`SetClassInfo`, which is the entrance to `TClingClassInfo`-shaped work. **Do not
continue that way.** Adding one method per error message is the same
"one missing symbol -> add one file -> repeat" pattern this project forbids,
applied to the interpreter instead of to libCore.

## Concrete next experiment

First, read ROOT's own `core/metacling/src/TClingClassInfo.cxx` and map the
`ClassInfo_*`/`MethodInfo_*`/`DataMemberInfo_*` family onto CppInterOp's
reflection API (`GetScope`, `GetClassMethods`, `GetDatamembers`,
`GetFunctionArgType`, `Construct`, `Allocate`) as a whole, then implement that
map. Decide up front, and record, which of ROOT's questions CppInterOp can
answer truthfully and which must keep failing loudly.

Second, check the assumption already written down but never tested: that
`TClass::New` for `ROOT::Minuit2::Minuit2Minimizer` comes from libMinuit2's
**compiled dictionary** rather than from interpreter reflection. Minuit2 is
configured in the wasm build tree but has never been built; build it.

The gate is `wasm/gates/rootformula/run.sh` with its boundary check inverted:
`TH1::Fit` must return, and its fitted parameters must match native ROOT at
`%.17g` through `wasm/gates/common/parity.sh`.

## Constraints and carry forward

- ROOT's own targets and generated dictionaries only; no handwritten
  `Class()`/`Streamer()`, no reimplemented ROOT semantics. The interpreter
  adapter stays the only new ROOT-facing code.
- **Unimplemented services must keep failing loudly.** A reflection answer that
  is merely plausible is worse than an error: it makes ROOT quietly wrong.
  `exit()` is not available for this — it traps inside Emscripten's atexit
  dispatch and discards the captured output
  ([rootweb FINDINGS](gates/rootweb/FINDINGS.md)).
- `CallFunc_SetFuncProto` currently ignores the prototype string and requires an
  unambiguous name. Real overload resolution belongs with this reflection work.
- M1, M2, M2b, M3 and M4a were independently reproduced on 2026-09-16. The
  review's one qualification — loud failure for ROOT's inherited **non-pure**
  `TInterpreter` defaults — has since been closed: coverage went from 128 to
  **284** loud overrides and every gate still passes. The follow-up review also
  reproduced M6a and closed with PASS.
- `rootlight`'s destructive stage and the `$ROOTSYS` consumers now coordinate
  through an exclusive/shared `flock`; a rebuild can no longer corrupt a sweep.
- Still untouched, in order: graphics (M5, and only if reflection does not
  settle the canvas kata), then in-browser grading and the `docs/site.js:238`
  runner seam (M6), then TFile/TTree/RDataFrame.
- The staged payload is 123.9 MB raw, 27.4 MB gzip, 18.7 MB brotli — almost all
  of it the C++ compiler, not ROOT. Measured, never load-tested.
