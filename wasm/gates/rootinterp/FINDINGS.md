# M3 — ROOT's interpreter over CppInterOp, and P0 parity in the browser

## Verdict: **PASS**

```bash
bash wasm/gates/rootinterp/run.sh        # -> "rootinterp M3 PASS"
```

```
P0 PARITY: native CERN ROOT 6.40.04 == wasm ROOT in Chromium, byte for byte
           (39 values at %.17g)
```

The unmodified P0 program [`p0.cxx`](../p0deps/runtime/p0.cxx) — `TH1D` construction,
weighted fills, underflow and overflow, `GetEntries`, every `GetBinContent`, `Integral`,
`GetMean`, `GetStdDev`, the `TAxis` queries, `SetBinContent`/`SetBinError`, a heap histogram
and destruction, all printed at `%.17g` — is **compiled and executed inside Chromium** by
wasm ROOT and matches the pinned native CERN ROOT 6.40.04 build of the same file exactly.

The native reference is **rebuilt by the gate**, not read from a recorded file, so the
comparison is against a ROOT you can rebuild.

## What was built

`wasm/rootlight/interpreter/` — the only new ROOT-facing code in this project.

| file | role |
| --- | --- |
| `TCppInterOpInterpreter.{h,cxx}` | `TInterpreter` implemented over CppInterOp, plus the `extern "C"` `CreateInterpreter`/`DestroyInterpreter` ROOT `dlsym`s |
| `gen_fatal.py` | generates the loud-failure overrides **from ROOT's own pinned `TInterpreter.h`** |
| `implemented.txt` | the short list implemented by hand; everything else is generated |
| `build.sh` | builds `libCling.so` as an Emscripten side module |

The M3 split was **3 implemented, 139 loud failures**. M4a now builds the same adapter with
**10 implemented names and 128 loud failures**; see [the M4a findings](../rootformula/FINDINGS.md).
The original three were the measured P0 surface
([interp-probe](../rootlight/interp-probe/FINDINGS.md)): a P0 program calls only
`CreateInterpreter`, the constructor, `RegisterModule` (once per dictionary) and `Initialize`.

### It does not create a compiler

The constructor calls `Cpp::GetInterpreter()` and **fails if that returns null**. The browser
kernel (xeus-cpp-lite) already owns a clang-repl instance; this is an adapter onto it. A second
clang in the same wasm process is out of bounds (`wasm/NEXT.md:31`), and nothing here creates
one.

`libCling.so` is 61 KB. Its `CppImpl::*` references are deliberately left undefined and bind at
load time to `libclangCppInterOp.so`, which the kernel has already loaded `global:true`.

### RegisterModule is real, and small for a reason

These dictionaries are generated with `-writeEmptyRootPCM`, so `payloadCode` and `fwdDeclsCode`
arrive as **nullptr** and the content is the header list. When they are not null the code is
handed to `Cpp::Declare` and a failure throws; recording without declaring would be the silent
no-op the rules forbid.

The include paths baked into a generated dictionary are the *build machine's* absolute paths
(`/home/fabian/.cache/...`), which do not exist in a browser. `RegisterModule` adds the ones
that actually resolve and skips the rest, rather than filling the compiler's search path with
unreadable directories. This is the concrete form of the "generated Core includePaths still
contain native paths" caveat carried since M1.

## Loud failure, verified

The gate calls the permanently out-of-scope runtime dictionary generator and requires that the
program does **not** continue past it. Observed:

```
Error in <TCppInterOpInterpreter>: TInterpreter::GenerateDictionary is not implemented in wasm ROOT yet
```

Two channels on purpose: ROOT's own `::Error`, so it looks like every other ROOT diagnostic,
and a C++ exception, so execution cannot continue as if the call had worked.

**It must not be `exit()`.** M2b established that `exit()` traps inside Emscripten's atexit
dispatch here and discards everything the kernel captured for the cell — a loud failure routed
through `exit()` would be a *silent* one ([rootweb FINDINGS](../rootweb/FINDINGS.md)). The
exception path was chosen for that reason and is checked by this gate.

## Classification: PLATFORM PORT of the interpreter backend

ROOT already loads its interpreter as a plugin (`core/base/src/TROOT.cxx:2223-2262`:
`dlsym("CreateInterpreter")`). Supplying a real library behind that documented seam leaves
`TROOT`, `TH1`, `TAxis`, `TFormula` and the plugin manager untouched, and the numbers above
are produced by ROOT's own compiled `TH1D`. The adapter necessarily implements the bounded
`TInterpreter` service contract (for example `ProcessLine` and callable lookup); it does not
reimplement ROOT's histogram or scientific semantics.

## Not established

- This gate establishes only the P0 surface. M4a subsequently added bounded
  `TF1`/`TFormula`/`TGraph` support; `Fit`, full `TClass` reflection, `TFile` and `TTree`
  remain outside the proven surface.
- `RegisterModule`'s `Cpp::Declare` path is **untested**: every dictionary in this closure
  passes nullptr. The first non-empty payload will be the first real exercise of it.
- No autoparsing, no PCM reading, no streamers, no reflection.
- Parity is established for these 39 values on this machine, not for `TH1D` in general.
- Startup cost, memory use and repeated-cell behaviour are unmeasured.
