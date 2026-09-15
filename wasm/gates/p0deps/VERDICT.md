# P0 dependency verdict — ROOT Light (TH1D)

Session 2026-09-15. Evidence: `runtime/FINDINGS.md` (Phase 1), `targets/FINDINGS.md`
(Phase 2), `xbuild/FINDINGS.md` (Phase 3, one bounded Core-only cross-build).
Pinned source ROOT 6.40.04, Emscripten 4.0.9. Native evidence: conda-forge 6.40.02
(primary) and CERN 6.34.10 (cross-check).

**Independent review: PARTIAL.** [CODEX-REVIEW.md](CODEX-REVIEW.md) qualifies the
claims below, including E1's configuration limits, the unsupported host-PCH
explanation, incomplete platform/build details and the next probe's recipe.
Use that review for durable conclusions; this synthesis records session claims.

## DEPENDENCY VERDICT

- **P0 requires TCling: CONDITIONAL.**
  - *Semantically: NO.* With libCling denied (`P0_DENY=libCling`), only
    `ROOT::Experimental::ObjectAutoRegistrationEnabled()` is interposed, and it returns the
    ROOT 6 default `true` (run `r640/E1`). All P0 output is then byte-identical to the normal
    run, including directory registration (`directory_is_null = 0`). libCling is requested
    0 times. The positive control (`ProcessLine`, `TClass` data members, `TF1("gaus")`) dies
    under the same denial, even with the same interposition, so the denial is real.
    6.34.10 runs P0 with no libCling request at all.
  - *Stock 6.40 code path: YES.* The first `TH1D` constructor goes `TH1::Build`
    (`TH1.cxx:826`) → `ObjectAutoRegistrationEnabled` → `gEnv->GetValue`
    (`TROOT.cxx:325`) → `TEnv::Getvalue` uses `gROOT` as a key prefix (`TEnv.cxx:474,487`)
    → `GetROOT2()` → `TROOT::InitInterpreter()` (`TROOT.cxx:468-477`). That dlopens
    libRIO and libCling and calls `exit(1)` on failure (`TROOT.cxx:2223-2256`).
    `AddDirectory(false)` (tested, labelled variant D) does not avoid it. Neither does
    `ROOT_OBJECT_AUTO_REGISTRATION=0`, because the env var is read after `gEnv`.
  - *Interpreter service actually used by P0:* **none**. Only the unconditional init-time
    load and `CreateInterpreter`.
- **Minimum observed native runtime libraries (P0, libCling denied + E1):**
  - Exercised code: libCore, libMathCore, libHist.
  - Mapped only because of NEEDED: libMatrix, libRIO, libThread. Also libImt, libMultiProc,
    libNet and tbb/ssl, which come through the conda `imt=ON` MathCore.
  - libCling: loaded only by the incidental init above. Never a NEEDED/link edge.
  - Plugins: none loaded.
- **Minimum candidate wasm targets:** ROOT's own `Core → Thread → RIO → MathCore → Matrix → Hist`
  with `imt=OFF`. MathCore is a hard link dependency: `TH1.cxx` is one TU calling
  `ROOT::Fit`/`ROOT::Math`. Matrix (10 strong symbols) and RIO (1 symbol, `TFile::Open`
  from `THnChain`) are link-closure only, forced by Hist's whole-package source list and
  `G__Hist`. P0 never exercises them. Thread enters only via RIO. They cannot be dropped at
  target level without editing Hist's source list, which is forbidden.
- **Host-only tools:** `rootcling` / `rootcling_stage1` (dictionaries), `python3`
  (`root-argparse.py`), CMake `configure_file` (`RConfigure.h`). LLVM tablegen is needed
  only if Cling is configured.
- **Platform adaptations required** (all PLATFORM PORT, none applied to ROOT C++ yet):
  1. CMake host-tool selection (`ROOT_HOST_ROOTCLING`): `RootMacros.cmake:643-677`, and drop
     the build-order-only `add_dependencies(Core CLING)` (`core/CMakeLists.txt:42`). This is
     implemented in `xbuild/host-rootcling.patch`, and Core's graph then has 0
     interpreter/LLVM nodes.
  2. Forward `CMAKE_TOOLCHAIN_FILE` to the builtin lzma ExternalProject (also in the patch).
  3. **Unsolved:** generate dictionaries against the *target* C++ stdlib (wasm32 libc++/musl),
     not host libstdc++.
  4. **Unsolved, must be classified before implementing:** Core without libCling must not
     `exit(1)` in `InitInterpreter` when no interpreter exists. It is acceptable as a
     platform port only if interpreter-requiring calls then fail loudly and nothing is
     silently no-op'd.
  5. `R__USE_URANDOM` for entropy (already proven).

## INVALID ASSUMPTIONS

1. "P0 has no interpreter edge." False for stock 6.40. The `TH1D` constructor reaches
   `InitInterpreter` through a `.rootrc` lookup. The edge is incidental, not semantic.
2. "`TH1::AddDirectory(false)` / `ROOT_OBJECT_AUTO_REGISTRATION=0` removes ownership-related
   dependencies." False on 6.40. Evaluation order at `TH1.cxx:826` and `TROOT.cxx:325`
   still reaches `gROOT`.
3. "ROOT's CMake can use a host rootcling for its own libraries." False with zero patches.
   `ROOT::rootcling` import is gated on `CMAKE_PROJECT_NAME != ROOT` (`RootMacros.cmake:664`).
   Pre-declared IMPORTED targets fail configure (`core/rootcling_stage1/CMakeLists.txt:38,40`,
   `main/CMakeLists.txt:121`).
4. "Host rootcling output compiles for any target." False for Core. Installed (stage-2)
   rootcling parses through the host TCling/libstdc++. `G__Core.cxx` contains 236
   `__gnu_cxx::` and 24 `std::__cxx11` spellings, and em++ rejects it. `-compilerI` only
   de-duplicates includes (`rootcling_impl.cxx:3693,4062`). The earlier G4 success (Hist LinkDef, 6.34.10) did not
   generalise to Core. The reason is **unverified**: Hist's LinkDef may not request
   STL-iterator dictionaries.
5. "The nominal Hist closure is what P0 uses." Only Core + MathCore + Hist code runs. Matrix,
   RIO and Thread are link closure.

## TARGET BUILD RECOMMENDATION

Build **ROOT's own CMake targets** (`--target Hist`, `imt=OFF`, `minimal=ON`, builtin codecs)
with Emscripten. Use a **CMake-only host-tool split**: dictionaries come from a native rootcling
that parses against the **Emscripten wasm32 sysroot** (libc++ + musl, target triple). Link the
resulting static archives into one prelinked `root-light` side module loaded by
xeus-cpp/CppInterOp. Handle the libCling runtime edge only after an explicit
platform-port/semantics classification of `InitInterpreter` behaviour without Cling. Do not
reconstruct Core manually.

## NEXT BOUNDED BUILD

Rerun the exact generated `G__Core` rootcling command (`xbuild/run.sh diag-libcxx`) with the
complete wasm32 target include set:
`EXTRA_CLING_ARGS="-nostdinc -nostdinc++ -isystem $SYSROOT/include/c++/v1 -isystem $SYSROOT/include"`,
optionally `--target=wasm32-unknown-emscripten`. Then compile the resulting `G__Core.cxx` with
em++.

- If it passes, resume `cmake --build . --target Core` with those args wired into the patch.
- If the host PCH/interpreter rejects the target stdlib, the host stage-2 rootcling route is
  closed. The only remaining host option is a natively built 6.40.04 `rootcling_stage1`,
  which owns its own `cling::Interpreter` and carries no host PCH.
