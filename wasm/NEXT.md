# NEXT — one objective for the next session

## Objective

Run one falsification-first `TH1D` dependency probe: use genuine ROOT headers and the pinned `em++` toolchain to identify the first unavoidable out-of-line ROOT symbol or library dependency for `TH1D` construction plus `Fill`.

## Constraints

- Do not start a Core, MathCore, Hist, Cling, LLVM, or rootcling build.
- Do not emulate `TH1D` or replace a missing ROOT symbol.
- Stop once the first blocker is reproducible and source-backed, or if a genuinely small standalone route is demonstrated.

## Why this is next

Histogram semantics are the strongest current ROOT Kata demand, but the documented Hist → MathCore/Matrix/RIO → Core path may make them too costly for ROOT Light. This probe decides whether the browser-native visualization boundary has any genuine ROOT histogram computation to consume.
