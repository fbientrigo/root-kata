# STATE — ROOT WebAssembly Subset

## Current gate

**G2 — genuine `ROOT::Math::PtEtaPhiMVector` WebAssembly: PASS.**

## Confirmed facts

1. G0 remains reproducible with pinned Emscripten **4.0.9**, ROOT source **6.40.04**, Node and headless Chromium.
2. `PtEtaPhiMVector` is a genuine ROOT alias at `math/genvector/inc/Math/Vector4Dfwd.h:84`. Its common template path through `Math/Vector4D.h` compiles without linking a ROOT library.
3. G2 generates `RConfigure.h` at run time from pinned ROOT `config/RConfigure.in`, using CMake `configure_file`, the mechanism ROOT uses in `cmake/modules/RootConfiguration.cmake:549-573`. It probes the actual native/`em++` compiler for C++ standard and attribute support; its no-component profile leaves optional ROOT component macros undefined. No hand-written or checked-in compatibility header exists.
4. `bash wasm/gates/g2/run.sh` builds a native reference, Node wasm target, and browser wasm target from the same unmodified ROOT headers and program. All emitted:

   ```
   pt=50.000000 eta=1.200000 phi=0.500000 m=0.105658
   E=90.532840 px=43.879128 py=23.971277 pz=75.473068
   sum_m=54.847433 sum_pt=52.238727
   ```

5. G2 deliberately failed (non-zero, unified diff) after corrupting its expected `pt` to `999.000000`; the fixture was restored.
6. The normal library route remains expensive: Core has unconditional `add_dependencies(Core CLING rconfigure)` (`core/CMakeLists.txt:42`), while MathCore and Hist depend on Core.
7. [ROOT_LIGHT.md](ROOT_LIGHT.md) records the evidence-backed 20/80 inventory. The only Tier 1 computation is the restricted GenVector slice. Histograms are the strongest actual curriculum demand but remain Tier 2; TFormula/fitting, TFile/TTree and RDataFrame are Tier 3 under current evidence.

## Gate-order correction

- Old assumption: G1 (a MathCore library build) must precede G2.
- Falsifying evidence: G2 ran without a ROOT library, while G1's package route enters Core → CLING.
- Replacement: `G0 → G2 → ROOT Light surface discovery → smallest capability probe`.
- Unresolved risk: GenVector does not establish a path for `TH1D`, files, or RDataFrame; ROOT Light is not yet viable as a useful curriculum subset on this evidence alone.

## Rejected approaches

- A hand-maintained `RConfigure.h`, ROOT stubs, or ROOT-like replacements.
- A full ROOT/MathCore/Core/Cling build to prove a header-only G2 claim.
- Treating browser rendering or JSROOT as ROOT computation.

## Canonical reproduction

```bash
bash wasm/toolchain/install-emsdk.sh
bash wasm/gates/g2/run.sh
```

## Last verified commit

`dd8f3b8` — `feat(wasm): prove GenVector WebAssembly gate`.

## Reviewer verdict

Not yet independently reviewed.
