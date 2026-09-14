# NEXT — one objective for the next session

## Objective

Scope a separately approved CMake + Emscripten cross-build beginning with the
target-side ROOT **Core** closure, using host `rootcling` for dictionaries where
needed. Do not start that build in this review.

## Why this is next

The static G4 rootcling cross-build compiled genuine dictionary and upstream
`TH1.cxx` wasm objects but could not link the target-side closure. The pinned
xeus-cpp-lite interpreter probe independently reaches the same boundary earlier:
the first `#include <TH1D.h>` incremental module fails on
`TVersionCheck::TVersionCheck(int)`, while the identical enlarged-header
GenVector control passes. The cheap interpreter path therefore cannot deliver
G5 without Core; another interpreter variation is not justified by current
evidence.

## Concrete next experiment

Design the smallest reproducible Core build against the pinned ROOT 6.40.04
source and Emscripten 4.0.9. Keep host-side dictionary generation separate from
the target runtime, record the exact Core sources and dependencies reached, and
stop at the first falsifiable link or execution result. Only after Core itself
has evidence of a usable target artifact should the `Hist`/`TH1D` closure be
scoped.

## Constraints

- Do not start a Core, MathCore, Hist, Cling, LLVM, or rootcling **build** without
  separately approved scope.
- Do not emulate `TH1D`, hand-write ROOT stubs, or substitute a reimplementation.
- Do not begin TF1, TGraph, G8, GUI, TFile/TTree, RDataFrame, or another ROOT
  subsystem in that session.

## Carry forward

- G7 remains PASS: the pinned in-browser C++ compiler works without threads or
  `SharedArrayBuffer`; its toolchain payload is about 99.5 MiB.
- G4 remains PARTIAL: genuine dictionary and `TH1.cxx` wasm objects exist, but
  no linked/running `TH1D` module exists.
- The interpreter evidence is pinned to ROOT 6.40.04 and includes the exact
  `TVersionCheck` symbol diagnostic; the bounded whole-TU retry stopped at
  missing out-of-scope `GuiTypes.h` and was not chased.
