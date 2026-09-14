# Agy High B: TH1D-for-wasm dependency map

This report is based on the cached ROOT source at
`/home/fabian/.cache/rootwasm-th1d/root-src`, git `6fced0c5` (`v6-34-10`).
It maps the exact API

```cpp
TH1D h("h", "h", 10, 0.0, 10.0);
h.Fill(1.0);
h.GetEntries();
h.GetBinContent(...);
h.Integral();
h.GetMean();
```

## Verdict

The smallest **unmodified upstream ROOT CMake target closure** is:

```text
ROOT::Hist
├── ROOT::MathCore ── ROOT::Core
├── ROOT::Matrix  ── ROOT::MathCore ── ROOT::Core
└── ROOT::RIO ───── ROOT::Core
                 └─ ROOT::Thread ── ROOT::Core
```

The direct `Hist` declaration is `DEPENDENCIES MathCore Matrix RIO`
(`hist/hist/CMakeLists.txt:168-174`). `Matrix` declares `MathCore`
(`math/matrix/CMakeLists.txt:79-80`), `MathCore` declares `Core`
(`math/mathcore/CMakeLists.txt:198-200`), and `RIO` declares `Core` and
`Thread` (`io/io/CMakeLists.txt:61-64`), while `Thread` declares `Core`
(`core/thread/CMakeLists.txt:65-68`). `ROOT_LINKER_LIBRARY` places these
dependencies in both the public link interface and the target's link command
(`cmake/modules/RootMacros.cmake:905-914`), and exports the same dependency
list (`:1000-1003`).

This is the supported target graph, not a claim that every object or code path
in those monolithic libraries is exercised by the six calls. With `imt=ON`,
`MathCore` also adds `Imt`; the small gate should use `imt=OFF`
(`math/mathcore/CMakeLists.txt:122-124,198-200`). Core's CMake target also
has platform/system support libraries and bundled compression/regex machinery;
those are build/link closure details of the stock Core target, not histogram
arithmetic requirements (`core/CMakeLists.txt:27,34-41`).

## Exact API evidence

`TH1D.h` is a wrapper that includes `TH1.h`; the `TH1D` class is declared in
`TH1.h`, where its `AddBinContent` and `RetrieveBinContent` implementations
operate on the `TArrayD` storage (`hist/hist/inc/TH1.h:670-703`). The concrete
fixed-bin constructor is out-of-line in `TH1.cxx:10436-10444` and delegates to
the `TH1` constructor (`hist/hist/src/TH1.cxx:697-704`). The requested methods
are also out-of-line: `Fill` (`:3346-3364`), `GetEntries` (`:4425-4433`),
`GetBinContent` (`:5084-5091`), `GetMean` (`:7558-7574`), and `Integral`
(`:7964-7979`). Thus a header-only or `TH1D`-only link cannot satisfy the
probe.

The constructor initializes axes, lists, style and directory hooks
(`TH1.cxx:771-807`); `Fill` finds the bin and updates contents and statistics
(`:3346-3363`); `GetMean` consumes `GetStats` (`:7558-7567`); and `Integral`
walks bin contents via `DoIntegral` (`:7964-7979`). `TArrayD` is part of Core's
container sources, not a separately linkable ROOT target: `core/cont/CMakeLists.txt:11-19`
lists its dictionary header and `:43-51` adds `TArrayD.cxx` to `Core`. These facts explain
why the call-level implementation needs substantial Core/Hist code, while they
do not turn file I/O, GUI, fitting, or the interpreter into API requirements.

## CMake build order versus wasm runtime

| Component | Role in stock ROOT build | Runtime status for compiled six-call code |
|---|---|---|
| `Hist`, `MathCore`, `Matrix`, `RIO`, `Thread`, `Core` | Library targets in the public closure above | The supported target/link closure; only parts of `Hist`/`Core` are directly exercised |
| `rootcling` | Executable run by dictionary custom commands; `main/CMakeLists.txt:96` links it to `RIO Cling Core Rint` | Not a runtime library |
| `rootcling_stage1` | Bootstrap executable for stage-1 dictionaries; `core/rootcling_stage1/CMakeLists.txt:27-33` | Not a runtime library |
| Cling, ClingUtils, Dictgen, MetaCling, Clang/LLVM | Dependencies of the dictionary/interpreter toolchain | Not required by compiled TH1D calls |
| `G__Hist.cxx` and generated PCM/rootmap | Standard `Hist` package dictionary generation; `ROOT_STANDARD_LIBRARY_PACKAGE` invokes `ROOT_GENERATE_DICTIONARY` (`RootMacros.cmake:1349-1371`) and adds its object to `Hist` (`:698-701`) | Dictionary C++ may be linked as part of stock `Hist`; PCM/rootmap are for reflection/autoload/module behavior, not these direct calls |
| `Rint` | Host `rootcling` link dependency | Host-only tool dependency |

The dictionary command selects `$<TARGET_FILE:rootcling>` and makes
`rootcling`/`rconfigure` build prerequisites (`RootMacros.cmake:614-622`), or
`rootcling_stage1` for stage-1 dictionaries (`:605-612`). Separately, Core has
`add_dependencies(Core CLING rconfigure)` (`core/CMakeLists.txt:34`). This is
a CMake build-order edge, **not** `target_link_libraries(Core Cling)` and not
evidence that Cling must be in the wasm runtime.

The practical host/target split is therefore: use a native host ROOT
`rootcling` (and its host Cling/LLVM/RIO/Core/Rint support) to generate the
dictionary artifacts, then compile/link the target-side library closure for
wasm. The stock ROOT CMake configuration does not model this split
automatically: the inspected Emscripten build emits `rootcling.js` from
`root-wasm-build/main/CMakeFiles/rootcling.dir/link.txt`, demonstrating that
an all-target-toolchain configure can compile the tool under the target
toolchain. That configuration fact is a build orchestration limitation, not a
runtime dependency. If the dictionary is
pre-generated or omitted in a deliberately source-pruned slice, the generator
and its host toolchain never need to be compiled to wasm.

## Optional or out of scope functionality

`Hist` is a broad monolithic package and its source list compiles many adjacent
histogram, graph, profile, `TF1`, and fitting-related translation units
(`hist/hist/CMakeLists.txt:100-167`). That package compile overhead must not be
mistaken for an API-level runtime dependency. There is no separate target edge
from `Hist` to drawing: `HistPainter` is its own package, and its CMake file
depends on `Gpad`, `Graf`, `Hist`, `MathCore`, and `Matrix`
(`hist/histpainter/CMakeLists.txt:11-24`). No Tree/TTree, RDataFrame, RooFit,
TMVA, GUI, fitting, or TFormula target is in the closure above.

Likewise, `RIO` is a supported `Hist` target dependency because the full Hist
library exposes streaming and file-related surfaces, even though the exact six
calls do not read or write files. `Matrix` and `Thread` are likewise target
closure requirements rather than operations exercised by this probe. A static
archive with section-level dead stripping may remove unused members; that can
shrink the final wasm binary but does not change the upstream CMake target
graph. Removing these targets requires a maintained source-pruned/custom ROOT
slice, not simply omitting them from a consumer link line.

Core's private/system and bundled support closure is configuration-dependent:
`Core` links `${CMAKE_DL_LIBS}`, `${CMAKE_THREAD_LIBS_INIT}`, and atomic support
privately (`core/CMakeLists.txt:36-41`), and its built-in compression pieces are
assembled under `core/lzma`, `core/lz4`, `core/zstd`, and `core/zip`
(`core/lzma/CMakeLists.txt:11-19`, `core/lz4/CMakeLists.txt:7-14`,
`core/zstd/CMakeLists.txt:5-13`, `core/zip/CMakeLists.txt:7-20`). In the
cached Emscripten configuration these are bundled targets/archives, but no
file/compression operation is invoked by the requested API. Treat them as
stock-Core build/link baggage, not as semantic histogram requirements.

## Review of Agy High A

A's final G4 terminal artifact claims the concrete constructor is defined in
`Hist`, that the direct probe first misses
`TH1D::TH1D(char const*, char const*, int, double, double)`, and summarizes the
chain as `Hist -> MathCore -> Core -> CLING`; it also records that Hist declares
`MathCore`, `Matrix`, and `RIO`. The constructor/method finding and the
high-level Hist/Core boundary are confirmed by the source evidence above.

Two refinements are required:

1. **Challenge the interpretation of `Core -> CLING`.** `core/CMakeLists.txt:34`
   proves only `add_dependencies(Core CLING rconfigure)`: Cling is a build-order
   prerequisite. The runtime target interface created by `ROOT_LINKER_LIBRARY`
   does not link `Cling`; `rootcling` is a dictionary executable, and its
   `RIO Cling Core Rint` dependencies are host-tool dependencies
   (`main/CMakeLists.txt:96`). A direct `em++` link failure without ROOT
   libraries demonstrates missing library objects, not a requirement to ship
   Cling/LLVM in the wasm runtime.
2. **Confirm and make explicit the omitted transitive edges.** The unmodified
   `Hist` target is not merely `Hist -> MathCore`: its direct `Matrix` and `RIO`
   dependencies are public, `RIO` adds `Thread`, and all of these reach Core.
   Therefore A's closure is correct only if “Hist depends on MathCore, Matrix,
   RIO” is retained; `Hist -> MathCore -> Core -> CLING` alone is incomplete as
   a CMake target graph and misleading as a runtime graph.

Bottom line: A correctly identifies the real ROOT library boundary and the
constructor blocker. This report confirms the supported wasm target closure as
`Hist + MathCore + Matrix + RIO + Thread + Core`, while moving Cling/LLVM,
rootcling/rootcling_stage1, Rint, and dictionary generation into the host/build
side rather than the wasm runtime.

No repository files other than this untracked report were changed; no commit was
created.
