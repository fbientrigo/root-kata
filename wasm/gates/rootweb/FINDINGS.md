# M2b — genuine ROOT running in a real browser

## Verdict: **PASS**

```bash
bash wasm/gates/rootweb/run.sh            # -> "rootweb M2b PASS"
bash wasm/gates/rootweb/run.sh serve      # prints a URL; open it and type ROOT C++
```

CERN ROOT 6.40.04, built from ROOT's own CMake targets
([../p0deps/xbuild](../p0deps/xbuild)), executes inside headless Chromium in the pinned
xeus-cpp-lite / CppInterOp kernel, served over plain static HTTP with no COOP/COEP —
the real GitHub Pages hosting shape. Observed stdout ([expected.txt](expected.txt)):

```
smoke.start
tstring=root-wasm len=9
tnamed=n/title
tmath.gaus=0.35206532676429952
classtable.TH1D=1
staticroot=1
createinterpreter=0
```

The first five lines are asserted against **the same
[expected.txt the Node M2 gate uses](../rootlight/expected.txt)**, so browser and Node agree
byte for byte. `TString`, `TNamed` and `TMath::Gaus` are real compiled ROOT code, compiled
*in the browser* by clang-repl against ROOT's own headers, and `classtable.TH1D=1` shows the
host-generated `G__Hist` dictionary registered `TH1D` at runtime.

The last two lines are the interpreter boundary, stated as the decision ROOT itself makes
(see below): ROOT will take its static-ROOT path, and the one symbol still missing is
`CreateInterpreter`. That is exactly what M3 supplies.

Falsifiability ([wasm/REPRODUCE.md](../../REPRODUCE.md)): the gate also drives a
deliberately-corrupted copy of the same cell and requires empty stdout plus a genuine
compiler diagnostic naming the typo.

## Packaging

| piece | where it comes from |
| --- | --- |
| kernel (`xcpp.js/.wasm/.data`, `libxeus.so`, `libclangCppInterOp.so`) | G7's pinned, sha256-verified conda packages, unchanged |
| six ROOT side modules | the M2 staged tree, unchanged |
| `$ROOTSYS` (`include/`, `etc/`, `*.rootmap`, `*_rdict.pcm`) | packed by [build_rootsys.py](build_rootsys.py) into `rootsys.js`, mounted into MEMFS |
| `libroota.so` | **ROOT's own `core/base/src/roota.cxx`**, compiled unmodified |

Total staged payload ≈ 124 MB, of which ≈ 111 MB is the G7 compiler. The page reuses G7's
`fetch-xcpp-toolchain.sh` and its `drive.mjs` CDP driver unchanged.

## The kernel runs in a Web Worker

ROOT loads libraries with `dlopen(3)`, which Emscripten implements as a *synchronous*
WebAssembly compile. Browsers forbid synchronous compilation of anything but tiny modules on
the main thread, so a genuine multi-megabyte ROOT `dlopen` can only work off-thread. The
worker is therefore a requirement, not a UI convenience.

## PLATFORM PORT: ROOT's own static-ROOT path

`TROOT::InitInterpreter` (`core/base/src/TROOT.cxx:2227-2251`) begins:

```cpp
if (!dlsym(RTLD_DEFAULT, "usedToIdentifyRootClingByDlSym")
    && !dlsym(RTLD_DEFAULT, "usedToIdentifyStaticRoot")) {
   // dlopen libRIO by path, then dlopen libCling by path
} else {
   gInterpreterLib = RTLD_DEFAULT;
}
```

ROOT ships that marker as a three-line file, `core/base/src/roota.cxx`, whose entire content is
one `extern "C"` function. We compile **that file, unmodified**, as a side module and load it
with the others. ROOT then correctly concludes that its libraries are already linked into this
process and resolves `CreateInterpreter` from the global symbol table.

This is a genuine platform port, and it *removes* glue rather than adding it:

- Without it ROOT `dlopen`s `$ROOTSYS/lib/libRIO.so` **by absolute path**. Emscripten keys
  loaded modules by the exact requested string, and the six libraries were loaded under the
  basenames in ROOT's own NEEDED lists, so that call builds a **second instance of libRIO**.
  In the browser that second instantiation fails outright with
  `RuntimeError: function signature mismatch`.
- The Node M2 gate worked around the same problem by aliasing absolute paths onto
  `LDSO.loadedLibsByName`, which [the M1/M2 review](../rootlight/CODEX-REVIEW-M2.md) fairly
  flagged as bounded glue over private, version-pinned loader state. **This gate needs no such
  aliasing**, and the Node gate can adopt the same approach.

A/B evidence, same page, same build, one query parameter apart (`?roota=0`):

| | stdout | outcome |
| --- | --- | --- |
| `roota=1` | delivered | ROOT takes the static-ROOT path; no second libRIO |
| `roota=0` | delivered, then lost | `Could not load dynamic lib: /tmp/incr_module_3.wasm` → `function signature mismatch`, thrown by the nested second load of libRIO |

## Finding: `exit()` traps in this dynamic-linking configuration

Constructing a `TH1D` today reaches `TROOT::InitInterpreter`, finds no `CreateInterpreter`,
prints ROOT's own `Fatal` diagnostic to stderr and calls `exit(1)`. That `exit(1)` traps, and
the trap discards everything the kernel had captured for the cell — which is why the gate
asserts the boundary with two `dlsym` calls instead of by reading ROOT's message.

Bisected to `exit` itself, with no ROOT involved at all:

| cell | result |
| --- | --- |
| `printf(...); fflush(stdout); exit(1);` | no output; `Uncaught RuntimeError: function signature mismatch` |
| `printf(...); fflush(stdout); _Exit(1);` | **output delivered**; the current M3-loaded runner then reports that its incremental module ended |

`_Exit` skips `atexit`/static-destructor dispatch, so this differential localises the
stdout-losing trap to normal termination/exit-handler dispatch across side modules, rather
than ROOT code. It does not identify which registered handler has the bad signature.

It does not block M3: on the success path `CreateInterpreter` resolves and `exit(1)` is never
reached. It does mean **any loud failure M3 adds must not rely on `exit()`** being observable;
that is a constraint on M3's error reporting, to be verified there.

## Not established

- No interpreter yet: `TH1D h(...)`, `TF1`, `TFormula`, `TClass` reflection and
  `gROOT->ProcessLine` all still stop at `InitInterpreter`. M3 supplies `CreateInterpreter`.
- No P0 numerical parity in the browser yet — that is the M3 gate.
- The ~124 MB payload is a development staging tree, not a deployable bundle. No size,
  caching or cold-load budget is claimed.
- `exit()` remains broken here; `_Exit` preserves stdout but still terminates the incremental
  module, and no normal-termination fix was attempted.
- Memory, concurrency and repeated-cell behaviour are untested: the gate runs one page load
  with two cells.
