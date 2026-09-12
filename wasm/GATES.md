# ROOT WebAssembly Subset — Gate Ladder

## Mission

Determine the **smallest subset of actual CERN ROOT** that can be compiled to WebAssembly
and used to teach genuine ROOT programming entirely inside the browser.

This is **not** a project to port full ROOT. It is not a project to reimplement ROOT.

**Product priority:** students write genuine ROOT APIs with the least infrastructure possible.

## Gates

A gate is a falsifiable claim with a deterministic reproduction command.

| Gate | Claim |
| ---- | ----- |
| G0 | A reproducible Emscripten toolchain exists, pinned and re-runnable from a clean state. |
| G1 | ROOT MathCore builds to WebAssembly. **Deferred:** its normal build path reaches Core/Cling. |
| G2 | `ROOT::Math::PtEtaPhiMVector` executes correctly in Chromium. **PASS.** |
| G3 | The minimum ROOT Core/Physics dependency boundary is established and documented. |
| G4 | Actual ROOT `TH1D` builds to WebAssembly. |
| G5 | `TH1D` supports `Fill`, `GetEntries`, `GetBinContent`, `Integral`, `GetMean` in Chromium. |
| G6 | `TGraph`/`TF1` evaluated — **only if inexpensive**. This gate may be declined on cost. |
| G7 | The proven ROOT subset is exposed through the existing xeus-cpp browser runtime. |
| G8 | One existing genuine ROOT Kata exercise executes fully client-side. |

## Out of scope

Unless a later gate produces evidence that it is *necessary*:

full ROOT · PyROOT · RooFit · TMVA · full Cling · RDataFrame · TFile/TTree I/O ·
GUI/X11 · distributed execution · **custom reimplementations pretending to be ROOT**

For ROOT file inspection and visualization, assume **JSROOT** is used separately until
evidence requires native ROOT I/O.

## Rules that decide gates

1. **One gate per session.** Do not begin the next gate in the same session.
2. A gate is **not** complete because code compiled once. It requires a deterministic
   reproduction command that passes from a clean state.
3. Prefer **removing** dependencies and features over patching them.
4. Kill any path that:
   - requires reimplementing ROOT APIs;
   - broadens the dependency surface without evidence;
   - introduces infrastructure unrelated to the current gate;
   - cannot produce a falsifiable test.
5. Prefer 2-3 independent hypotheses in parallel over sequential blind debugging.
6. Do not modify the normal ROOT Kata curriculum (`curriculum/`, `src/`, `docs/`, `tests/`).
7. Do not merge experimental changes into `web/assembly`.

## Canonical branch

`experiment/root-wasm-subset`

## Reproduction contract

Every completed gate `gN` owns exactly one entry point:

```
wasm/gates/gN/run.sh
```

which exits `0` and prints `gN PASS`, or exits non-zero and prints `gN FAIL: <reason>`.
`wasm/REPRODUCE.md` lists the canonical command for the current gate.

## Gate-order correction

Old assumption: G1 had to precede G2. Evidence: `math/mathcore/CMakeLists.txt`
depends on Core, and `core/CMakeLists.txt` unconditionally makes Core depend on
CLING; the G2 template path compiled and ran without a ROOT library. Replacement:
`G0 → G2 → ROOT Light surface discovery → smallest next capability probe`. Risk:
this bypass only proves the restricted GenVector template path, not MathCore, Hist,
or the wider curriculum.
