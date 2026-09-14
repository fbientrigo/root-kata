# G4/G5 interpreter probe — independent review

Date: 2026-09-14
Reviewer: Codex

## Verdict

**BLOCKER confirmed.** The existing xeus-cpp-lite/CppInterOp interpreter does not
reach genuine `TH1D`: it fails while incrementally loading the first cell,
`#include <TH1D.h>`, with the missing Core constructor
`_ZN13TVersionCheckC1Ei`. The enlarged-header control passes, and the pinned
ROOT source citations confirm that this is an unconditional Core requirement,
not a broken header mount or a parse failure.

The cheap interpreter path is therefore closed for G5 without a target-side
Core build. G4 remains **PARTIAL**: the earlier rootcling cross-build produced
wasm objects but no linked module; this probe adds independent evidence that
Core is required even before a `TH1D` translation unit can be loaded.

## Independent reproduction

Ran from the repository root:

```bash
bash wasm/gates/g4/interpreter-probe/probe.sh
```

The script used the cached, hash-verified Emscripten 4.0.9 toolchain and ROOT
6.40.04 source, generated `RConfigure.h` with the pinned `em++`, and mounted
631 real ROOT header files (the G7 set plus the `TH1D` transitive closure).
The control variant used that same mount with G2's known-good `genvector.cpp`:

```text
control: PASS (harness+enlarged-includes verified sound)
```

The genuine `TH1D` probe then classified itself as:

```text
BLOCKED-AT-SYMBOL: `#include <TH1D.h>` failed
```

The first-cell diagnostic was reproduced exactly:

```text
Could not load dynamic lib: /tmp/incr_module_2.wasm
Error: Dynamic linking error: cannot resolve symbol _ZN13TVersionCheckC1Ei
Failed to execute via ::process:Failed to load incremental module
```

The three cells were `#include <TH1D.h>`, the unmodified `th1d.cpp` translation
unit, and `main();`. The first cell failed, so the latter two could not run.
The probe's one bounded `?variant=symbol-retry` attempt reproduced the same
first-cell failure; feeding the genuine upstream `TH1.cxx` next then stopped at
the expected out-of-scope GUI dependency:

```text
/rootsrc/core/base/inc/TVirtualPad.h:32:10: fatal error: 'GuiTypes.h' file not found
```

That retry is not evidence that JIT resolution succeeds or fails after a Core
build: the interpreter session was already broken, and the whole-TU attempt
was deliberately not chased into GUI headers.

## Source citation spot-check

Against `/home/fabian/.root-kata-wasm/src/root-6.40.04`:

| Claim | Checked evidence | Result |
| --- | --- | --- |
| Every translation unit including `TVersionCheck.h` creates the static check object | `core/base/inc/TVersionCheck.h:24-31` declares `TVersionCheck(int)` and defines `static TVersionCheck gVersionCheck(ROOT_VERSION_CODE)` | VERIFIED |
| `TObject.h` pulls in `TVersionCheck.h` | `core/base/inc/TObject.h:18` includes `"TVersionCheck.h"` | VERIFIED |
| The constructor is out-of-line in Core source | `core/base/src/TSystem.cxx:4462-4466` defines `TVersionCheck::TVersionCheck(int versionCode)` | VERIFIED |
| The `TH1D` header reaches `TObject.h` | ROOT header search shows `TH1D.h`'s inheritance/header chain reaches `TNamed.h` and `TObject.h` | VERIFIED |

The mangled diagnostic therefore names the constructor cited by the report.
It is a dynamic-link failure while Clang-Repl loads the incremental wasm module,
not a missing-header diagnostic. The control passing under the identical mount
further isolates the failure to the ROOT class-header path.

## Finding classification

| Finding | Classification | Independent disposition |
| --- | --- | --- |
| The probe reproduces the reported `BLOCKED-AT-SYMBOL` result at the first `TH1D` include | **REPRODUCTION** | Verified by a fresh run of `probe.sh`; exact symbol and diagnostic match. |
| The 631-header control succeeds | **VERIFIED** | `ctl-run` returned `ok`; the harness and enlarged mount are sound. |
| `_ZN13TVersionCheckC1Ei` is `TVersionCheck::TVersionCheck(int)` and is required by the cited ROOT header chain | **VERIFIED** | Pinned source lines agree with `FINDINGS.md`. |
| The cheap interpreter route can reach G5 without target-side Core | **BLOCKER** | It fails before `th1d.cpp` or `main()` can execute. |
| The probe invalidates the earlier G4 rootcling-crossbuild closure | **INVALIDATED** | The opposite is true: it corroborates and strengthens the Core-boundary finding. |
| The bounded whole-`TH1.cxx` retry reaches a usable JIT definition path | **NEXT-EVIDENCE-REQUIRED** | No conclusion is possible: the session was already broken and the retry hit missing `GuiTypes.h`. |
| No ROOT source, dictionary, stub, or reimplementation was introduced | **VERIFIED** | The probe uses genuine pinned headers/source and generated payload data only. |

## Compatibility check

Ran:

```bash
bash wasm/gates/g7/run.sh
```

It completed successfully with:

```text
G7 PASS
```

The backwards-compatible `build_headers.py` extension therefore leaves G7's
original three-argument path unaffected.

## Next objective

The next separately approved objective should scope a full CMake + Emscripten
cross-build beginning with target-side **Core**, using host `rootcling` only for
dictionary generation where needed. This is the smallest evidence-backed next
step because both the static rootcling cross-build and this interpreter probe
stop at the Core boundary; it is not a claim that the complete `Hist` closure
will be cheap or immediately buildable.

No Core, MathCore, Hist, Cling, LLVM, or rootcling build was started in this
review. GUI headers were not mounted, and the bounded retry was not extended.

No product wiring, curriculum, or unrelated ROOT subsystem was changed.
