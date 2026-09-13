# G4 blocker: direct `TH1D` needs Hist

Pinned ROOT **6.40.04** defines the fixed-bin `TH1D` constructor in
`hist/hist/src/TH1.cxx:10540`. `Fill` is at `:3411`, `GetEntries` at `:4496`,
`GetBinContent` at `:5161`, `GetMean` at `:7666`, and `Integral` at `:8092`.
They are not header-only.

The owning `Hist` CMake target is declared in `hist/hist/CMakeLists.txt`; it
depends on `MathCore`, `Matrix`, and `RIO`. `MathCore` depends on `Core`, and
`core/CMakeLists.txt:42` makes `Core` depend on `CLING` and `rconfigure`.
Therefore the first unresolved `TH1D` constructor is an honest Hist/Core/Cling
boundary, not a missing compatibility shim that this experiment may replace.
