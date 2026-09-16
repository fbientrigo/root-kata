# M4a — TF1 / TFormula / TGraph in the browser

## Verdict: **PASS**, and the M4 boundary is `TH1::Fit`

```bash
bash wasm/gates/rootformula/run.sh      # -> "rootformula M4a PASS"
```

```
p1: native CERN ROOT 6.40.04 == wasm ROOT in Chromium, 21 values
TH1::Fit stops loudly at: TInterpreter::SetClassInfo is not implemented
```

## Why these 21 values are the interesting ones

Every number in [`p1.cxx`](p1.cxx) comes from **C++ the interpreter compiled at runtime**.
`TF1("lin", "[0]+[1]*x")` is not a lookup: `TFormula` generates a C++ function from the
string, declares it to the interpreter, resolves it through `TMethodCall`, and then calls the
resulting pointer on every `Eval` (`hist/hist/src/TFormula.cxx:944-961` and `3518-3527`). If
any part of that chain were faked, these values could not match native ROOT.

Covered: a parameter/variable formula and `SetParameter` re-evaluation, the named `gaus` and
`pol2` shortcuts, a formula calling into `TMath::Sqrt`, `GetNpar`/`GetNdim`/range accessors,
and `TGraph` construction, `Eval`, `GetPoint` and `GetMean`.

## What was implemented

Added to [`wasm/rootlight/interpreter`](../../rootlight/interpreter): **18 names implemented
by hand, 284 loud failures** (M3 ended at 3 implemented). Ten of the eighteen are the formula
path below; the other eight are the `ClassInfo_`/`CallFunc_` handle methods, which ROOT
declares non-pure and which therefore had to be named explicitly once non-pure coverage
landed.

That count grew after the [M3/M4 review](../CODEX-REVIEW-M3-M4.md) recorded this project's most
important unproven claim: only ROOT's **pure** virtuals were being overridden, so the ~167
non-pure `TInterpreter` methods kept ROOT's own inline defaults, which silently return `0`,
`nullptr` or nothing. Inheriting a silent no-op is the same defect as writing one.
`gen_fatal.py` now parses every explicit service virtual — including the ones ROOT declares
as `override = 0` with no `virtual` keyword — and unsupported *overloads* of names implemented
by hand (`ClassInfo_Init(tagnum)`, `ClassInfo_Delete(arena)`) are spelled out explicitly rather
than left to the base class. Generation also checks that the adapter overrides every overload
behind each excluded name, so a new sibling cannot silently inherit ROOT's default.

**Re-running the gates against the stricter adapter changed nothing**: `rootinterp M3 PASS`,
`rootformula M4a PASS` and `rootkatas M6a PASS` all still hold, so no proven path was relying
on a silent default.

| service | over CppInterOp |
| --- | --- |
| `Declare` | `Cpp::Declare` |
| `ProcessLine`, `ProcessLineSynch`, `Calc` | `Cpp::Evaluate`, falling back to `Cpp::Declare` — ROOT uses `ProcessLine` for both expressions and declarations (its autoparse trigger is a `namespace { }` block) |
| `CheckClassInfo` | `Cpp::GetScopeFromCompleteName` |
| `ClassInfo_*` handles | a scope handle over `Cpp::GetGlobalScope` / `GetScopeFromCompleteName` |
| `CallFunc_*` handles | a resolved function plus its callable wrapper |
| `CallFunc_SetFuncProto` | `Cpp::GetFunctionsUsingName`, then wrapper generation |

### The callable pointer is generated, not extracted

ROOT wants a raw `void (*)(void*, int, void**, void*)`. CppInterOp's `JitCall` holds a pointer
of exactly that shape — but it is a **private** member with no accessor, so reading it would
mean depending on that class's internal layout.

Instead, `MakeRootCallable` does what ROOT's own TCling does: it emits a small `extern "C"`
shim with ROOT's calling convention, compiles it with `Cpp::Declare`, and takes its address
with `Cpp::GetFunctionAddress`. Argument and return types come from
`Cpp::GetFunctionArgType`/`GetFunctionReturnType`, and a type it cannot express is reported
rather than guessed.

### Overloads are not resolved by prototype

`CallFunc_SetFuncProto` ignores the prototype string: it looks the name up and requires the
answer to be unambiguous. TFormula's generated functions have unique names, so this is exact
for the tested path — and an ambiguous name **fails loudly** instead of picking one. Real
prototype matching belongs with the reflection work below.

## The boundary: `TH1::Fit` needs TClass reflection

`TH1::Fit` resolves its minimizer through ROOT's genuine `TPluginManager`, which builds a
`TClass` — and that walks into the interpreter's reflection surface. Following it one call at a
time gave `CheckClassInfo` (implemented, genuinely) and then `SetClassInfo`, which is the
entrance to `TClingClassInfo`-shaped work: class info handles, data members, methods, offsets.

**That chain was not followed further on purpose.** Adding one method per error message is the
same "one missing symbol → add one file → repeat" pattern this project forbids; TClass
reflection is a subsystem to design, not a sequence of holes to plug. The gate therefore
asserts the boundary instead of describing it: `TH1::Fit` must **not** return, and must name
the service it stopped at. A fit that returned parameters nothing computed would be exactly
the silent no-op the rules forbid.

## Not established

- **No fitting.** `TH1::Fit`, `TGraph::Fit` and Minuit2 do not work. Minuit2 is configured in
  the wasm build tree but was never built, because reflection blocks it first.
- No `TClass` reflection, no `TFile`, no `TTree`, no graphics.
- Formula coverage is the 21 values above, not TFormula in general: no vectorised formulas, no
  lambda-based `TF1` (which needs `ProcessLine` to return a real function address), no
  `TF1::Integral`/`Derivative`, no multidimensional formulas.
- `ProcessLine`'s expression-then-declaration fallback is a behavioural choice, not a
  reproduction of TCling's parsing rules; a line that is neither reports a ROOT error and
  returns 0.
- Parity is established for this program on this machine.
