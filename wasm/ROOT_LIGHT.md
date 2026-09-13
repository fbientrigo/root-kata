# ROOT Light evidence matrix

This is a capability inventory, not a promise to port ROOT. Curriculum evidence is
from `curriculum/triads/*.csv` and `curriculum/plan.json`; dependency evidence is
from the sha256-pinned ROOT 6.40.04 source tree fetched by `fetch-root-src.sh`.

| Learner capability | Genuine ROOT surface | Educational demand | Dependency evidence | wasm evidence | ROOT Light tier |
| --- | --- | --- | --- | --- | --- |
| Represent and combine four-vectors | `ROOT::Math::PtEtaPhiMVector` | High physics value; no current kata yet uses it | Common template path is `math/genvector/inc/Math/Vector4D.h`; no linked ROOT library in G2 | Native, Node and Chromium agree in G2 | 1, restricted template slice |
| Make/fill/inspect a distribution | `TH1D` / `TH1` | Highest current demand: m0/m1 and downstream RDF triads | `TH1D` constructor (`hist/hist/src/TH1.cxx:10540`), `Fill` (`:3411`), `GetEntries` (`:4496`), `GetBinContent` (`:5161`), `GetMean` (`:7666`), and `Integral` (`:8092`) are out of line; Hist → MathCore → Core → CLING | G4's pinned direct `em++` link first lacks `TH1D::TH1D(char const*, char const*, int, double, double)` | 2 |
| Inspect simple statistics | individual inline `TMath` calls | Repeated histogram/statistics intent | MathCore package depends on Core (`math/mathcore/CMakeLists.txt`); only a proven inline call is cheap | G2 uses the `TMath` inline path indirectly | 2 |
| Represent paired measurements | `TGraph` data access | m1 graph triad | Constructors are out of line (`hist/hist/src/TGraph.cxx`), in Hist | No wasm probe | 2 |
| Evaluate a parameterized model | `TF1` / `TFormula` | m1 function and fit triads | `TFormula` includes and calls `TInterpreter` (`hist/hist/inc/TFormula.h`, `hist/hist/src/TFormula.cxx`) | No wasm probe | 3 |
| Fit a distribution | `TH1::Fit`, Minuit | m1 fitting triads | Fit is in TH1; Minuit depends on Graf, Hist, Matrix, MathCore (`math/minuit/CMakeLists.txt`) | No wasm probe | 3 |
| Read/write event data | `TFile`, `TTree` | m2 file/tree triads | RIO depends Core+Thread (`io/io/CMakeLists.txt`); Tree depends Net/RIO/MathCore (`tree/tree/CMakeLists.txt`) | No wasm probe; browser filesystem/data-loading remains additional cost | 3 |
| Define/filter/analyse columns | `RDataFrame`, `RVec` | m3–m6 dominant workflow | RDF depends Tree/TreePlayer/Hist/RIO/ROOTVecOps and calls `gInterpreter` for string expressions (`tree/dataframe/CMakeLists.txt`, `tree/dataframe/src/RDFUtils.cxx`) | No wasm probe | 3 |
| Draw a result | ROOT values → browser SVG/canvas | Drawing is not an acceptance target; current validators inspect ROOT-observable data | ROOT rendering adds HistPainter/Gpad/Graf; browser drawing need not compute ROOT semantics | Existing web layer already presents structured runner results | Outside ROOT Light computation |

## Conclusion

Tier 1 is deliberately tiny: the proven `PtEtaPhiMVector` template slice. It is a
credible physics-object seed, not evidence that the current full curriculum can run
in-browser. In particular, current lessons make histogram and RDataFrame workflows
high-value, and neither has a cheap WebAssembly path yet.

The working architecture is therefore falsifiable: genuine ROOT computation in wasm
produces scalar values or arrays, then browser-native UI renders those values. It is
supported for the G2 slice and m0/m1-style observable displays, but falsified as a
claim to cover the planned m2+ TFile/TTree/RDataFrame curriculum without further gates.
