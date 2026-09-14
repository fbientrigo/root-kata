# G4/G5 interpreter probe — findings

Date: 2026-09-13 (session following the G4 rootcling-crossbuild review, commit `8649fd4`).
Executed by: Claude (this worktree), uncommitted. Not yet independently reviewed.

Answers `wasm/NEXT.md`'s objective: can the same prebuilt xeus-cpp-lite / CppInterOp
in-browser interpreter that G7 proved (Clang-Repl under the hood) construct genuine
`TH1D`, given the real headers mounted, with **no** rootcling-generated dictionary
anywhere in this page's toolchain?

## Result: BLOCKED-AT-SYMBOL

The cheap path is closed. The interpreter hits the identical missing-Core-symbol wall
that G4's static link hit — but one step earlier, at header-inclusion time rather than
at `main()`-call time.

## Reproduction

```bash
bash wasm/gates/g4/interpreter-probe/probe.sh
```

Reuses G7's proven machinery unmodified (`fetch-xcpp-toolchain.sh`, `drive.mjs`,
`g2/rconfigure.cmake`) plus one backwards-compatible edit to `g7/build_headers.py`
(accepts extra trailing subtree-dir args; G7's own 3-arg call is untouched — reran
`wasm/gates/g7/run.sh` after the edit and it still prints `G7 PASS`, 355 headers,
unchanged). Same pinned toolchain versions as G7: Emscripten `4.0.9`, ROOT source
`6.40.04` (the G0-pinned release — this closes the release-pin gap the G4
rootcling-crossbuild review left open on the parse side), xeus-cpp `0.10.0` /
cppinterop `1.9.0` / xeus `6.0.5`.

Three sequential interpreter cells, run as separate `execute_request`s over the real
Jupyter wire protocol (same pattern as G7), against the genuine, unmodified
`wasm/gates/g4/th1d.cpp`:

1. `c1-include`: `#include <TH1D.h>` alone
2. `c2-define`: the full `th1d.cpp` translation unit (declares `main()`, does not run it)
3. `c3-run`: `main();`

Header mount: G7's four subtrees (`math/genvector/inc`, `math/mathcore/inc`,
`core/foundation/inc`, `core/base/inc`) plus `TH1D`'s transitive closure
(`hist/hist/inc`, `core/cont/inc`, `core/meta/inc`, `math/matrix/inc`, `io/io/inc`,
`core/thread/inc`, `core/clib/inc`) — 631 files, 3,824,386 header bytes (vs. G7's 355
files / 2,221,663 bytes). Toolchain+page payload: 105,864,857 bytes total (the ~99.5
MiB xeus-cpp-lite toolchain is unchanged from G7; the extra headers add ~1.7 MiB).

**Falsifiability control** (`?variant=control`): the same enlarged 631-file include set
driving G2's already-proven `genvector.cpp` — passed (`ctl-run` status `ok`), so the
`TH1D` failure below is attributable to `TH1D`, not to a broken harness or the larger
mount.

## What happened

`c1-include` — merely `#include <TH1D.h>` — failed:

```
Could not load dynamic lib: /tmp/incr_module_2.wasm
Error: Dynamic linking error: cannot resolve symbol _ZN13TVersionCheckC1Ei
Failed to execute via ::process:Failed to load incremental module
```

`_ZN13TVersionCheckC1Ei` demangles to `TVersionCheck::TVersionCheck(int)`. This is not
a parse/missing-header error (the falsifiability control proves headers resolve fine
under this same mount) — it is a **dynamic-linking symbol failure** raised when
clang-repl tries to load the incrementally-JIT-compiled module for the translation
unit. `c2-define` and `c3-run` never ran (the interpreter's session state was already
broken by `c1`'s failed module load).

### Root cause, source-cited

`TVersionCheck.h:31`:

```cpp
static TVersionCheck gVersionCheck(ROOT_VERSION_CODE);
```

is a **file-scope static object**, unconditionally instantiated in every translation
unit that includes `TObject.h` (`core/base/inc/TObject.h:18` `#include
"TVersionCheck.h"`; `TH1D.h` → `TH1.h` → `TNamed.h`/`TAttLine.h`/etc. → `TObject.h`).
Its constructor is implemented out-of-line, in Core proper:

```
core/base/src/TSystem.cxx:4462: TVersionCheck::TVersionCheck(int versionCode)
```

So merely *including* `TObject.h` — which almost every ROOT class header does —
requires `TVersionCheck::TVersionCheck(int)` to already be resolvable wherever the
translation unit is loaded. In a static link this is one symbol among the many G4's
`BLOCKER.md` already catalogued (`TObject`'s vtable, `TString::TString()`, etc.). In
the interpreter, clang-repl compiles each cell to its own incremental wasm module and
tries to `dlopen`-style-load and link it immediately — so the identical missing-Core
wall surfaces at the **first** cell that includes any ROOT class header, before any
`TH1D`-specific code (dictionary-dependent or not) is even reached.

**This is the same finding as G4's rootcling-crossbuild review, via a different
mechanism, one step earlier.** It is not a new, narrower blocker — it is confirmation
that the target-side `Core` closure (not just `Hist + MathCore + Matrix + RIO +
Thread`) is unconditionally required before *any* ROOT class header can be used at
all, whether linked statically or loaded by the interpreter.

## Bounded conditional retry (one attempt, as scoped)

Per plan, since the result was `BLOCKED-AT-SYMBOL` (not a parse/missing-header issue),
one further cell was tried: feeding genuine upstream `hist/hist/src/TH1.cxx`
(unmodified, 391,109 bytes) to the interpreter before `th1d.cpp`, testing whether
clang-repl's JIT can resolve `TH1D`'s out-of-line definitions on the fly instead of
needing a rootcling dictionary. Reproduction: `?variant=symbol-retry`.

Result: still blocked, but on a **different**, expected wall — `c1-include` reproduced
the identical `TVersionCheck` error above (session state carries the same missing-Core
requirement), and the subsequent `TH1.cxx` cell failed for an unrelated, expected
reason:

```
/rootsrc/core/base/inc/TVirtualPad.h:32:10: fatal error: 'GuiTypes.h' file not found
```

`TH1.cxx` transitively includes `TVirtualPad.h` (for `Draw`-adjacent code paths, out of
this experiment's target capability), which needs `core/gui/inc` — a subtree
deliberately not mounted (drawing/GUI is explicitly out of scope per `wasm/GATES.md`).
This is a missing-header artifact of feeding a whole 10,731-line TU that references
more than the six target methods need, not new evidence about the `TVersionCheck`
wall itself — the retry is bounded to this one attempt, per plan, and is not chased
further (mounting `core/gui/inc` would itself need to stay header-only, since drawing
is out of scope, and there is no reason to expect it changes the root TVersionCheck
finding). `main();` (`c3-run`) never got a chance to run in this variant either
(session state remained broken from `c1`).

## Classification

| Question | Answer |
| --- | --- |
| Does an interpreter resolve `TH1D` differently than a static link? | No — same wall, same root cause (`Core`'s `TVersionCheck` constructor), surfaced one cell earlier because clang-repl links each cell's JIT module immediately rather than deferring to a final link step. |
| Is the cheap interpreter path viable for G5 without building `Core`? | No. |
| Does this invalidate the G4 rootcling-crossbuild review's target closure? | No — it corroborates it. `Core` was already named as part of the required `Hist + MathCore + Matrix + RIO + Thread + Core` closure; this probe shows `Core` is required even earlier than that review's link step, at the point of merely including any ROOT class header at all. |
| Was any ROOT source patched, or any dictionary/stub/reimplementation written? | No — `th1d.cpp` and the mounted headers are byte-identical to the pinned 6.40.04 tree; the retry's `TH1.cxx` cell is the genuine upstream file, unmodified. |

## Next objective (for the reviewer's independent judgment, not adopted on faith)

The cheap path is closed. `wasm/NEXT.md`'s own fallback applies: **a full CMake +
Emscripten cross-build with host `rootcling` generating dictionaries is now justified**
— scoped specifically around getting `Core` itself to link to wasm (the boundary both
this probe and the rootcling-crossbuild review converge on), not the full `Hist`
closure at once. That is a large, expensive gate and, per this session's own scope
(one gate per session; no Core/MathCore/Hist/Cling/LLVM/rootcling build without
separately approved scope), is explicitly **not** started here.

## What's NOT in this directory

No `GATES.md` / `STATE.md` / `NEXT.md` edits — left for the independent reviewer's own
judgment after reproduction, matching how the `rootcling-crossbuild` review was
handled. No files outside `wasm/gates/g4/interpreter-probe/` and the one
backwards-compatible `wasm/gates/g7/build_headers.py` edit were touched.
