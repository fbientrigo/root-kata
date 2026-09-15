# NEXT — one objective for the next session

## Objective

Run one bounded **stock G__MathCore dictionary generation-and-whole-C++
compile probe** in the already configured ROOT-owned cross-build tree.
Use pinned ROOT 6.40.04/Emscripten 4.0.9 and label the installed 6.40.02
rootcling as version-mismatched diagnostic evidence.

## Why this is next

Core now builds from a fresh cache with target frontend arguments for the
host generator, target-built codecs and narrowly reviewed wasm32 platform
guards. The output is a relocatable object, and no runtime is proven. The
independent review also corrects the proposed next PCM blocker: upstream
MathCore, Matrix, Hist, RIO and Thread explicitly pass `-writeEmptyRootPCM`.
Their stock paths must be tested before prescribing a non-empty PCM fix.
See [Core-fix review](gates/p0deps/CODEX-REVIEW-CORE.md).

## Concrete next experiment

Extract the generated `G__MathCore` rootcling rule into a fresh probe directory.
Preserve all upstream options, including `-writeEmptyRootPCM`, Core's PCM
dependency and the target frontend environment; redirect only outputs.
Run from the generated working directory under a 120-second bound and record
the complete command, generator exit and diagnostics. If generation passes,
compile the entire emitted dictionary using pinned em++ and MathCore's
generated `flags.make`. Check target STL spellings and wasm object format.
Stop at the first failure.

This tests transfer to a non-STAGE1 dependency of Hist. Success proves only
that dictionary path; it does not prove a MathCore library, Hist, non-empty
PCM correctness or Cling-free execution.

## Constraints

- Use ROOT's own targets and generated rules. Do not resume the retired
  manual `gcore/` source slice.
- Do not start a MathCore/Hist/LLVM/Cling/compiler build in this dictionary
  probe. A larger Hist target build needs separately bounded scope.
- Do not remove upstream empty-PCM options to manufacture a blocker, invent
  metadata workarounds, hand-write Class/Streamer methods or emulate TH1D.
- Do not replace autoregistration configuration with a constant or silently
  skip interpreter initialization. Do not begin TF1, TGraph, G8, GUI,
  TFile/TTree or RDataFrame.

## Carry forward

- G7 remains PASS without shared memory; its compiler payload is about 99.5 MiB.
- G4 remains PARTIAL and G5 BLOCKED; no linked/running wasm TH1D exists.
- Candidate package closure is Core, Thread, RIO, MathCore, Matrix and Hist
  with `imt=OFF`; it is not a proven minimal executable closure.
- Non-empty PCM generation independently crashes on host/target serialization
  layout disagreement. Empty PCM is upstream behavior for the relevant targets.
- `libCore.so` is bare `-shared` relocatable output under pinned 4.0.9.
  `-pthread`, main/side-module linkage, G7 wasm exception compatibility,
  runtime reflection/resources and the unchanged InitInterpreter/Cling edge
  remain unresolved. The present inspection script needs stronger failure
  propagation and complete archive checks before unattended release use.
