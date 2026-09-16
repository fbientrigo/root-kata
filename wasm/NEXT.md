# NEXT — one objective for the next session

## Objective

Implement **TClass reflection over CppInterOp**, as one designed subsystem, so
`TH1::Fit` works. That is the single boundary M4 stopped at.

## Why this is next

M2b, M3 and M4a are PASS: genuine ROOT 6.40.04 runs in Chromium, and both
numerical probes match native ROOT byte for byte — 39 TH1D/TAxis values and 21
TF1/TFormula/TGraph values. `TH1::Fit` is the first thing a student hits that
still does not work, and it is the last piece of the shipped curriculum's
non-graphical surface (`cpp-root-fit-gaussian`).

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
- M1, M2, M2b, M3 and M4a were independently reproduced on 2026-09-16; the
  review remains PARTIAL only for the interpreter-wide loud-failure invariant
  outside those exercised gates.
- Still untouched, in order: graphics (M5), then the kata runner and JupyterLite
  (M6), then TFile/TTree/RDataFrame.
