# ROOT TH1D WebAssembly experiment

Date: 2026-09-13

## Result

The credible subset experiment reached Emscripten compilation of genuine ROOT
code and a genuine ROOT dictionary, but did not produce a linked wasm module.
The host tool is ROOT 6.34.10's native x86-64 `rootcling`; the target compiler
is Emscripten 3.1.74 / Clang 20.

## Exact configuration and build commands

The source checkout is `/home/fabian/.cache/rootwasm-th1d/root-src` (ROOT
6.34.10). The native ROOT configuration used:

```sh
cmake -S /home/fabian/.cache/rootwasm-th1d/root-src \
  -B /home/fabian/.cache/rootwasm-th1d/root-host-build \
  -DCMAKE_BUILD_TYPE=Release -Dbuiltin_cling=ON -Dbuiltin_llvm=ON \
  -Dhttp=OFF -Dminimal=ON -Dpyroot=OFF -Dr=OFF -Droofit=OFF -Droot7=OFF \
  -Druntime_cxxmodules=OFF -Dsqlite=OFF -Dssl=OFF -Dtesting=OFF \
  -Dtmva=OFF -Dwebgui=OFF
```

The ROOT top-level Emscripten configuration used:

```sh
cmake -S /home/fabian/.cache/rootwasm-th1d/root-src \
  -B /home/fabian/.cache/rootwasm-th1d/root-wasm-build \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CROSSCOMPILING_EMULATOR=/home/fabian/.cache/rootwasm-th1d/emsdk/node/24.19.0_64bit/bin/node \
  -DCMAKE_TOOLCHAIN_FILE=/home/fabian/.cache/rootwasm-th1d/emsdk/upstream/emscripten/cmake/Modules/Platform/Emscripten.cmake \
  -Dbuiltin_cling=ON -Dbuiltin_llvm=ON -Dhttp=OFF -Dminimal=ON \
  -Dpyroot=OFF -Dr=OFF -Droofit=OFF -Droot7=OFF \
  -Druntime_cxxmodules=OFF -Dsqlite=OFF -Dssl=OFF -Dtesting=OFF \
  -Dtmva=OFF -Dwebgui=OFF
```

That top-level configure reaches generation but returns an install-export
error because Emscripten converts ROOT's `SHARED` declarations to static
libraries while builtin dependency targets are not in `ROOTExports`.

The smaller probe uses ROOT's own installed `RootMacros.cmake` and
`ROOT_GENERATE_DICTIONARY`, with an imported executable target pointing at the
native host `rootcling`; it does not link any host ROOT library. Its files are:

```text
/tmp/rootwasm-th1d-probe/CMakeLists.txt
/tmp/rootwasm-th1d-probe/main.cxx
```

Probe configure and build:

```sh
/home/fabian/.cache/rootwasm-th1d/emsdk/upstream/emscripten/emcmake \
  cmake -S /tmp/rootwasm-th1d-probe -B /tmp/rootwasm-th1d-probe-build-min \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_TOOLCHAIN_FILE=/home/fabian/.cache/rootwasm-th1d/emsdk/upstream/emscripten/cmake/Modules/Platform/Emscripten.cmake \
  -DCMAKE_CROSSCOMPILING_EMULATOR=/home/fabian/.cache/rootwasm-th1d/emsdk/node/24.19.0_64bit/bin/node
cmake --build /tmp/rootwasm-th1d-probe-build-min --target TH1D_wasm -j4
cmake --build /tmp/rootwasm-th1d-probe-build-min --target th1d_probe -j4
```

## Generated dictionary and target evidence

`rootcling` generated these files from upstream ROOT headers and its upstream
`hist/hist/inc/LinkDef.h`:

```text
/tmp/rootwasm-th1d-probe-build-min/G__TH1D_wasm.cxx       92700 bytes
/tmp/rootwasm-th1d-probe-build-min/libTH1D_wasm_rdict.pcm  632 bytes
/tmp/rootwasm-th1d-probe-build-min/libTH1D_wasm.rootmap    783 bytes
```

The generated C++ contains ROOT's standard “Do NOT change” banner and real
`TH1D::Class`, `TH1D::Dictionary`, `TH1D::Streamer`, and initialization code.
Both dictionary and implementation objects are WebAssembly binaries:

```text
CMakeFiles/G__TH1D_wasm.dir/G__TH1D_wasm.cxx.o  WebAssembly binary module
CMakeFiles/TH1D_wasm.dir/.../TH1.cxx.o          WebAssembly binary module
libTH1D_wasm.a                                   526656 bytes
```

No hand-written ROOT dictionary symbols or replacement histogram classes were
added.

## Dependency closure

ROOT's own `hist/hist/CMakeLists.txt` declares `Hist` dependencies:

```text
Hist -> MathCore, Matrix, RIO
Matrix -> MathCore
RIO -> Core, Thread
MathCore -> Core
```

Therefore the minimum ROOT runtime library closure for the genuine `Hist`
library is `Hist, MathCore, Matrix, RIO, Core, Thread`. ROOT's normal build
also has a build-time dependency on native Cling/LLVM to generate dictionaries;
that is separate from the runtime link closure.

## First blockers

The top-level ROOT wasm build (`cmake --build ... --target Hist -j4`) first
fails compiling upstream `core/clib/src/attach.c` with Emscripten: `close`,
`malloc`, `free`, `lseek`, and `read` are undeclared. This occurs before the
Hist target is built.

The focused probe gets further: dictionary generation and the genuine upstream
`hist/hist/src/TH1.cxx` compile succeed, then the first focused link failure is
the real missing Core symbol `TVersionCheck::TVersionCheck(int)`, followed by
TObject/TNamed/TString/TAtt*/TAxis/TArrayD symbols. This confirms the focused
archive cannot link without the ROOT closure above; no payload-size estimate
applies because no final wasm module was linked.
