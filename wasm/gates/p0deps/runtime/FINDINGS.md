# P0 native runtime dependency audit — does TH1D P0 need TCling?

**P0 requires TCling: NO.** None of the P0 behaviour needs the interpreter. Stock 6.40.02 still dlopens libCling as a side effect of incidental init, and aborts if the load fails. Evidence: run `r640/E1` blocks that one call with libCling denied, and its output is byte-identical to run A. `libCling_dlopen=0` and libCling is absent from `/proc/self/maps`. The 6.34.10 runs never request libCling at all.

## Files
| path | role |
|---|---|
| `wasm/gates/p0deps/runtime/p0.cxx` | P0 probe (TH1D/TAxis calls, `%.17g`, dumps `.so` set from `/proc/self/maps` when `P0_MAPS` is set). `-DP0_NO_ADD_DIRECTORY` builds variant D |
| `wasm/gates/p0deps/runtime/control.cxx` | positive control: `gInterpreter->ProcessLine("1+1;")`, `TClass::GetClass("TH1D")->GetListOfDataMembers()`, `TF1("f","gaus")` |
| `wasm/gates/p0deps/runtime/shim.c` | LD_PRELOAD: logs every `dlopen`/`dlmopen`. Prints `backtrace()` for any libCling request (all requests with `P0_BT_ALL=1`). `P0_DENY=<substr>` denies a matching load by opening a nonexistent path, so the caller gets NULL and a real `dlerror()`. `P0_AUTOREG=0/1` short-circuits `ROOT::Experimental::ObjectAutoRegistrationEnabled()` (run E only) |
| `wasm/gates/p0deps/runtime/run.sh` | builds and runs everything for both ROOTs, prints the summary table below |
| `~/.cache/rootwasm-p0/runtime/{r640,r634}/` | `<run>.out`, `<run>.err`, `<run>.err.demangled`, `<run>.maps`, `A_vs_<run>.diff`, `C_nodeny_vs_<run>.diff`, `needed.txt`. Summary is in `summary.txt` |

ROOTs: `r640` = `/home/fabian/thesis/FairShip/.pixi/envs/default` (conda-forge 6.40.02, primary). `r634` = `/home/fabian/.cache/rootwasm-th1d/root-host` (CERN 6.34.10, cross-check). Neither was modified. I read source from `~/.root-kata-wasm/src/root-6.40.04`, which is a patch release newer than the binary. The binary's backtrace symbols match that source's control flow.

Harness calls added beyond the brief: `GetName`, `TAxis::GetBinWidth`, heap `new TH1D` / `delete`, `GetBinError`, `GetDirectory`. The harnesses (`cpp-root-histogram*/harness.cpp`) also use `gROOT->SetBatch`, `TCanvas`, `Draw` and `SaveAs`. These are graphics calls, not P0, so the probe leaves them out.

## Commands
```
wasm/gates/p0deps/runtime/run.sh        # OUT=~/.cache/rootwasm-p0/runtime by default
```
Minimal link line (both ROOTs):
```
g++ $(root-config --cflags) p0.cxx -L$R/lib -Wl,-rpath,$R/lib -lHist -lCore
```
Linking with `-lHist` alone fails with `undefined reference to symbol '_ZN7TObjectdlEPv' … libCore.so.6.40: error adding symbols: DSO missing from command line`.

NEEDED lists (r640):
- `p0`: libHist.so.6.40, libCore.so.6.40, libstdc++, libgcc_s, libc
- `libHist`: libMatrix, libMathCore, libRIO, libCore, libstdc++, libm, libgcc_s, libc, ld-linux

Transitive NEEDED:
- libMathCore → libImt
- libImt → libMultiProc, libtbb
- libMultiProc → libNet, libRIO
- libNet → libssl, libcrypto
- libRIO → libThread
- libThread → libtbb

**libCling is not in any NEEDED closure. It is only ever dlopened.**

## Summary table (`run.sh` output, verbatim)
```
r640   A                      rc=0   libCling_dlopen=1 denied=0 mapped_at_end=1 out_vs_ref=
r640   B                      rc=1   libCling_dlopen=1 denied=1 mapped_at_end=n/a out_vs_ref=DIFF
r640   D_A                    rc=0   libCling_dlopen=1 denied=0 mapped_at_end=1 out_vs_ref=DIFF
r640   D_B                    rc=1   libCling_dlopen=1 denied=1 mapped_at_end=n/a out_vs_ref=DIFF
r640   E1                     rc=0   libCling_dlopen=0 denied=0 mapped_at_end=0 out_vs_ref=same
r640   E0                     rc=0   libCling_dlopen=0 denied=0 mapped_at_end=0 out_vs_ref=DIFF
r640   C_nodeny               rc=0   libCling_dlopen=1 denied=0 mapped_at_end=n/a out_vs_ref=
r640   C_deny                 rc=1   libCling_dlopen=1 denied=1 mapped_at_end=n/a out_vs_ref=DIFF
r640   C_deny_autoreg         rc=1   libCling_dlopen=1 denied=1 mapped_at_end=n/a out_vs_ref=DIFF
r640   static_init_deny       rc=0   libCling_dlopen=0 denied=0 mapped_at_end=n/a out_vs_ref=
r634   A                      rc=0   libCling_dlopen=0 denied=0 mapped_at_end=0 out_vs_ref=
r634   B                      rc=0   libCling_dlopen=0 denied=0 mapped_at_end=0 out_vs_ref=same
r634   D_A                    rc=0   libCling_dlopen=0 denied=0 mapped_at_end=0 out_vs_ref=DIFF
r634   D_B                    rc=0   libCling_dlopen=0 denied=0 mapped_at_end=0 out_vs_ref=DIFF
r634   E1                     rc=0   libCling_dlopen=0 denied=0 mapped_at_end=0 out_vs_ref=same
r634   E0                     rc=0   libCling_dlopen=0 denied=0 mapped_at_end=0 out_vs_ref=same
r634   C_nodeny               rc=0   libCling_dlopen=1 denied=0 mapped_at_end=n/a out_vs_ref=
r634   C_deny                 rc=1   libCling_dlopen=1 denied=1 mapped_at_end=n/a out_vs_ref=DIFF
r634   C_deny_autoreg         rc=1   libCling_dlopen=1 denied=1 mapped_at_end=n/a out_vs_ref=DIFF
r634   static_init_deny       rc=0   libCling_dlopen=0 denied=0 mapped_at_end=n/a out_vs_ref=
r640 A.out == r634 A.out (byte-identical)
```
`mapped_at_end=n/a` means the process died before the maps dump, or the binary doesn't dump maps (control, static_init).

## Run A: normal execution (r640)
rc=0. Values (identical on r634):
- `entries = 11`
- `bin[0..11] = 1 1 2 1 1 1 1 2.5 0 0 1 1`
- `integral = 10.5`, `mean = 4.3085714285714287`, `stddev = 2.7711151025470997`
- `axis.FindBin(3.3) = 4`, `FindBin(-1) = 0`, `FindBin(11) = 11`
- `GetBinCenter(3) = 2.5`, `GetBinLowEdge(3) = 2`, `GetBinWidth(3) = 1`
- after `SetBinContent(4, 7.25)` / `SetBinError(4, 1.5)`: `integral = 16.75`, `entries = 12`, `mean = 4.0074626865671643`, `stddev = 2.1466609568194692`
- heap histogram: `mean = 2.04`, `stddev = 1.333566646253572`
- `destroyed = 1`

Full text is in `r640/A.out`.

Shared objects mapped at end of r640 A (`r640/A.maps`):
- ROOT: libCore, libHist, libMathCore, libMatrix, libRIO, libThread, libImt, libNet, libMultiProc, **libCling.so.6.40.02**
- other: libtbb.so.12.18, libtbbmalloc.so.2.18, libssl, libcrypto, libpcre2-8, libz, liblzma, liblz4, libzstd, libstdc++, libgcc_s, libc, libm, libdl, libpthread, **librt** (librt comes in only through libCling's NEEDED)

No plugin `.so` was loaded.

dlopen requests in A, in order:
1. `libtbbmalloc.so.2` ×3 and `libtcm.so.1` ×2. These are tbb's own allocator probing (libtcm is absent, harmless).
2. `$R/lib/libRIO.so`
3. `$R/lib/libCling.so`

Requests 2 and 3 both come from `TROOT::InitInterpreter()` (`P0_BT_ALL=1` backtrace). After loading, cling prints `ERROR in cling::CIFactory::createCI(): cannot extract standard library include paths!` because the conda build-env compiler path is baked in. The run is otherwise unaffected.

## First operation that reaches the interpreter (r640)
The first `TH1D` constructor. Backtrace from `r640/A.err.demangled`:
```
shim dlopen(.../libCling.so)
libCore  TROOT::InitInterpreter()+0x3c9
libCore  ROOT::Internal::GetROOT2()+0x30
libCore  TEnv::Getvalue(char const*) const+0x4a6
libCore  TEnv::GetValue(char const*, int) const+0x29
libCore  (+0x22640b)   = static defaultState lambda in ObjectAutoRegistrationEnabledImpl()
libCore  ROOT::Experimental::ObjectAutoRegistrationEnabled()+0x56
libHist  TH1::Build()+0x1bd
libHist  TH1::TH1(char const*, char const*, int, double, double)+0x152
libHist  TH1D::TH1D(char const*, char const*, int, double, double)+0x23
p0       main
```
Source (6.40.04):
- `hist/hist/src/TH1.cxx:826`: `if (ROOT::Experimental::ObjectAutoRegistrationEnabled() && TH1::AddDirectoryStatus())`. The autoreg check comes first, so `AddDirectory(false)` does not skip it.
- `core/base/src/TROOT.cxx:315-345`: the one-time default reads `gEnv->GetValue("Root.ObjectAutoRegistration", -1)`.
- `core/base/src/TEnv.cxx:474-488`: `TEnv::Getvalue` builds lookup keys as `gSystem->GetName() + "." + gROOT->GetName()` and `gROOT->GetName() + "." + name`.
- `gROOT` expands to `ROOT::GetROOT()`, which becomes `GetROOT2()` after TROOT construction. `GetROOT2()` calls `InitInterpreter()` and `InitThreads()` once (`TROOT.cxx:468-476`).

**So the trigger is a `.rootrc` key lookup that uses gROOT's name as a prefix. It has nothing to do with histogram semantics, so it is incidental init.**

Static init: there is no libCling request before `main`. `static_init` (links libHist and libCore with `--no-as-needed`, then `main(){return 0;}`) runs under denial with rc=0 and makes 0 libCling requests.

## Run B: libCling denied (r640)
Denial log and result:
```
[shim] dlopen(.../lib/libCling.so) -> DENIED
Fatal in <TROOT::InitInterpreter>: cannot load library /p0-denied-by-shim/libCling.so: cannot open shared object file: No such file or directory
```
- rc=1, stdout empty, so `A_vs_B.diff` is all of A's lines.
- The abort happens inside the first `TH1D` constructor.
- Same backtrace as A.

r634 B: rc=0, output byte-identical to A, 0 libCling requests. 6.34 `TH1::Build` has no `ObjectAutoRegistrationEnabled` call, and the symbol doesn't exist in 6.34 libCore.

## Run C: positive control
- **r640 and r634, no denial:** rc=0. `ProcessLine(1+1) = 2`, `TClass(TH1D).datamembers = 1`, `TF1(gaus).Eval(0.5) = 0.88249690258459546`. libCling is dlopened via `TInterpreter::Instance() → GetROOT2() → InitInterpreter()`.
- **Same denial (`P0_DENY=libCling`):** rc=1. stdout stops after `control.start = 1`. The log shows `-> DENIED` and then the same `Fatal in <TROOT::InitInterpreter>`. This is true on both ROOTs, so the denial really takes effect.
- **`C_deny_autoreg`** (denial plus the run-E override): still rc=1 with the same Fatal. The override does not hide real interpreter use.

## Run D: "AddDirectory(false)"
`TH1::AddDirectory(false)` is the first statement.
- **D_A (r640):** rc=0. The only diff against A is the added `variant = AddDirectory(false)` line and `directory_is_null = 0 → 1`. All numeric values are identical. The loaded library set is identical to A (`diff A.maps D_A.maps` is empty, libCling is still loaded).
- **D_B (r640):** rc=1, same Fatal. **`AddDirectory(false)` does not avoid libCling on 6.40**, because of the `&&` evaluation order at TH1.cxx:826.
- **r634 D_A / D_B:** rc=0, same one-line diff, no libCling.

## Run E: decisive isolation (r640)
The shim defines `ROOT::Experimental::ObjectAutoRegistrationEnabled()`. libHist binds that symbol to the shim (`LD_DEBUG=bindings`: `binding file libHist.so.6.40 to shim.so: normal symbol _ZN4ROOT12Experimental29ObjectAutoRegistrationEnabledEv`). This removes only the gEnv→gROOT path, and libCling stays denied.
- **E1** (returns true, the ROOT 6 default): rc=0, **`A.out` and `E1.out` are byte-identical**. That includes `directory_is_null = 0`, so directory registration into gROOT still works without an interpreter. There are 0 libCling requests, and the `libRIO.so` dlopen disappears too. `diff A.maps E1.maps` shows only `libCling.so.6.40.02` and `librt.so.1` removed.
- **E0** (returns false): rc=0. The only diff is `directory_is_null = 0 → 1`.

Every other P0 call (Fill including underflow, overflow and weights, GetEntries, GetBinContent, Integral, GetMean, GetStdDev, the TAxis calls, SetBinContent, SetBinError, heap new/delete, destruction) runs to completion with no interpreter.

## Implication for a WASM P0 build
- The library-set difference between A and E1 is libCling plus librt only. MultiProc, Net, Imt, tbb, ssl and crypto are still loaded through NEEDED, not dlopen. They are link-time baggage from libMathCore→libImt and libImt→libMultiProc, not runtime needs that this audit proved.
- On 6.40, `TH1::Build` reaches `TROOT::InitInterpreter` through `TEnv::Getvalue`'s `gROOT` use, and fails fatally when libCling is missing. A Cling-free build must neutralize that path. Options include making the TEnv lookup avoid `ROOT::GetROOT()`, or giving `ObjectAutoRegistrationEnabledImpl` a compile-time default. This is untested beyond the E1 interposition.
- 6.34.10 has no such path.
