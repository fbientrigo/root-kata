# NEXT — one objective for the next session

## Objective

Test whether xeus-cpp-lite's Clang-Repl/Cling interpreter (proven working in-browser by
G7) can construct a genuine `TH1D` through its own interactive class-resolution machinery
— which historically differs from ahead-of-time static linking — *before* committing to
another full CMake + host-`rootcling` cross-build of Core/MathCore/Matrix/RIO/Hist.

## Why this, specifically, is next

G4 proved that a **static, no-library link** of `TH1D` fails on undefined
`Class()`/`Streamer()` symbols that only `rootcling` emits (`wasm/gates/g4/BLOCKER.md`).
G7 proved a **Cling-based interpreter** can run entirely client-side. Real ROOT's Cling
is known to resolve classes interactively at the prompt without a precompiled dictionary
in some cases (autoloading, on-the-fly `TClass`/`TProtoClass` generation) — a mechanism
that is architecturally different from G4's static-link probe and untested by any gate
so far. The larger rootcling cross-build review now shows that the static route can
reach real wasm objects but stops at the target-side Core closure, without producing
a linked module. If it works for `TH1D`, the interpreter path to G5 is far cheaper than
another full ROOT build.
If it does not — if the interpreter hits the identical missing-dictionary wall — that is
still valuable: it closes off the cheap path and confirms the full build is necessary
before paying for it.

## Concrete first experiment

Using the `wasm/gates/g7/` toolchain and mounting technique (same `xkernel`/
`execute_request` pattern, same header-mounting approach), submit genuine ROOT source
that constructs a `TH1D` and calls `Fill`/`GetEntries` — e.g.:

```cpp
#include <TH1D.h>
TH1D h("h", "", 10, 0, 1);
h.Fill(0.5);
h.GetEntries();
```

through the interpreter (not compiled ahead-of-time), mounting `hist/hist/inc`,
`core/base/inc`, `core/meta/inc`, `core/cont/inc`, `math/matrix/inc`, `io/io/inc` into
its virtual FS alongside the include paths G7 already proved. Report plainly whether it
resolves, and if not, the exact diagnostic — the interpreter's error message may itself
be informative about what's missing (a missing `.pcm`, a missing `libHist.so`, etc.).

## Constraints

- Do not start a Core, MathCore, Hist, Cling, LLVM, or rootcling **build** without a
  separately approved scope — this objective is a probe through the *existing* prebuilt
  interpreter, not a new build.
- Do not emulate `TH1D` or hand-write any part of it.
- If the interpreter also fails, the next decision (not this session's job) is whether to
  scope a full CMake + Emscripten cross-build with host `rootcling` generating
  dictionaries — a large, expensive gate that should be scoped deliberately, not started
  as a "small follow-up."

## Also carry forward, unresolved

- Payload cost: G7's toolchain alone is ~99.5 MiB before any ROOT library is added. This
  was accepted per an explicit "whatever fidelity requires" product decision, but the
  next session's scoping should keep the number honest rather than let it grow unnoticed.
- G7 passed independent Codex Sol High review; no further G7 review blocks the next
  separately-approved probe.
- The G4 rootcling cross-build is **PARTIAL**, not a PASS: real dictionary and
  `TH1.cxx` wasm objects were reproduced, but no linked/running module exists.
  It used ROOT 6.34.10 from the experiment cache; repeat against the pinned
  6.40.04 source before claiming release-specific closure.
