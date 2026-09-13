# G4 blocker: direct `TH1D` needs a generated dictionary, not just Hist's CMake graph

Pinned ROOT **6.40.04** defines the fixed-bin `TH1D` constructor in
`hist/hist/src/TH1.cxx:10540`. `Fill` is at `:3411`, `GetEntries` at `:4496`,
`GetBinContent` at `:5161`, `GetMean` at `:7666`, and `Integral` at `:8092`.
They are not header-only.

## The blocker is a link-time symbol requirement, not a CMake build-order edge

An earlier version of this note argued from the CMake target graph alone: Hist
depends on MathCore/Matrix/RIO, MathCore depends on Core, and
`core/CMakeLists.txt:42` has `add_dependencies(Core CLING rconfigure)`. That
edge is real but is CMake **build ordering**, not a link requirement — Core's
actual `target_link_libraries` (`core/CMakeLists.txt:44-49`) is only
`${CMAKE_DL_LIBS}`, thread libs and atomics, and the interpreter is loaded at
runtime by name (`core/base/src/TROOT.cxx:2238` `gSystem->DynamicPathName
("libCling")`, `:2251` `dlsym(gInterpreterLib, "CreateInterpreter")`). So
"Hist needs Core, Core needs CLING" does not by itself prove a wasm link must
pull in Cling.

The real reason `TH1D` cannot be built as plain translation units is
`ClassDefOverride` (used at `hist/hist/inc/TH1.h:693` for `TH1` and `:949` for
`TH1D`, among others). It expands through `_ClassDefOutline_`
(`core/base/inc/Rtypes.h:310-321`) to **declare, without defining**:

```cpp
static atomic_TClass_ptr fgIsA;
static int ImplFileLine();
static const char *ImplFileName();
static const char *Class_Name();
static TClass *Dictionary();
static TClass *Class();
virtual void Streamer(TBuffer&) override;
```

and through `_ClassDefBase_` (`Rtypes.h:278-308`) defines `IsA()` and
`ShowMembers()` **inline as virtuals** that call `Class()`. Because `IsA()`
and `Streamer()` are virtual, constructing a single `TH1D` emits its vtable,
which references `TH1D::Class()` and `TH1D::Streamer(TBuffer&)` — undefined
unless something supplies them.

Only `rootcling` supplies them: `core/dictgen/src/rootcling_impl.cxx:1122-1159`
emits `Class_Name()`, `ImplFileName()`, `Dictionary()` and `Class()` (the last
calling `ROOT::GenerateInitInstanceLocal(...)->GetClass()`, which consults
`gInterpreterMutex`/`gInterpreter`) into a generated `G__*.cxx`. `ClassImp` —
the historical macro that used to backfill some of this — is an empty no-op in
6.40 (`Rtypes.h:373` `#define ClassImpUnique(name, key)`), so there is no
non-dictionary fallback macro to switch to.

`TH1::Streamer` is hand-written (`TH1.cxx:7076`); `TH1D::Streamer` is not —
only rootcling emits it. `TH1.cxx` is itself one 10,731-line translation unit
that also references `TF1`/`TFormula`/`ROOT::Fit`/`ROOT::Math::GoFTest`, so
even the arithmetic-only parts of `Fill`/`Get*` cannot be linked without
pulling in the rest of that file's dependency closure.

## Consequence for scope

Building genuine `TH1D` for wasm means running ROOT's real build system with
host `rootcling` generating dictionaries — not selecting a subset of plain
`.cxx` files, and not hand-writing stub `Class()`/`Streamer()` definitions
(that would link, but it is forking `TH1`, which this experiment forbids). The
G4 probe below stops at the first such symbol without attempting either.
