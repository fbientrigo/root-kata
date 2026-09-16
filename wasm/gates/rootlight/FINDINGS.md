# M2 — ROOT's own libraries as WebAssembly side modules

## Verdict: **Node subgate PASS; full M2 PARTIAL**

Independent [M1/M2 review](CODEX-REVIEW-M2.md): the approved M2 also requires
Chromium inside G7. That host integration has not run.

```
bash wasm/gates/p0deps/xbuild/run.sh            # M1: configure + graph + hist + inspect -> "xbuild Hist PASS"
bash wasm/gates/rootlight/run.sh                # M2 -> "rootlight M2 PASS"
```

Genuine ROOT 6.40.04, built by ROOT's own CMake targets, initializes and executes in
WebAssembly under Node with pinned Emscripten 4.0.9. Observed output (`expected.txt`):

```
smoke.start
tstring=root-wasm len=9
tnamed=n/title
tmath.gaus=0.35206532676429952
classtable.TH1D=1
```

- `TString`, `TNamed`, `TMath::Gaus` are real compiled ROOT code.
- `classtable.TH1D=1`: the `G__Hist` dictionary registered `TH1D` in `TClassTable`, so
  host-generated factory registration works at runtime; invoking factories,
  reflection and serialization remain untested.
- The first `gROOT` use then stops with ROOT's own diagnostic:
  `Fatal in <TROOT::InitInterpreter>: cannot load symbol ... "CreateInterpreter"`.
  ROOT's own `roota.cxx` marker selects its static-build path, so it does not try to load a
  second `libRIO` or `libCling` by absolute path. This is the documented M2 boundary; M3
  supplies that symbol.
- The gate requires the expected output, ROOT exit 1 and the interpreter-boundary
  diagnostic. It rejects the observed duplicate-registration warning
  (`already in TClassTable`); this is a symptom check, not a complete count of
  module instances.

## Packaging: one side module per ROOT library

Each ROOT library is linked as its own Emscripten side module. Dependencies
come from ROOT-generated `link.txt` and its CMake response files, replacing
the original handwritten dependency map. This preserves the package graph
for the tested loader paths; it does not establish general native-loader parity:

| module | bytes | NEEDED |
| --- | ---: | --- |
| libCore.so | 3708648 | — |
| libThread.so | 206875 | libCore |
| libRIO.so | 3867648 | libCore, libThread |
| libMathCore.so | 1802000 | libCore |
| libMatrix.so | 999513 | libMathCore, libCore |
| libHist.so | 2906312 | libMathCore, libMatrix, libRIO, libThread, libCore |
| libroota.so | 141 | — (ROOT's unmodified static-build marker) |

The original run measured about 13.5 MiB of uncompressed side modules, with
genuine library boundaries preserved. This excludes the kernel, headers,
PCM/rootmap/etc resources and browser working memory; no deployable P0 bundle
or comparison with a prelinked payload is established.

`$ROOTSYS` is staged as `lib/` (side modules, `.rootmap`, `_rdict.pcm`), `obj/` (the
relocatable outputs of ROOT's CMake targets they are linked from), `include/` and `etc/`.

## Runtime environment (no ROOT changes)

`run.sh` writes `env-pre.js`, the Node stand-in for what the browser page's loader will do:

1. `ENV.ROOTSYS` — Emscripten does not forward host environment variables.
2. `ENV.ROOT_LDSYSPATH` — **ROOT's own documented override** (`TUnixSystem.cxx`, `DynamicPath`)
   for the `popen("LD_DEBUG=libs LD_PRELOAD=DOESNOTEXIST ls")` system-path probe. A browser
   cannot spawn processes. No patch was needed.
3. `Module.locateFile` — resolves NEEDED basenames to `$ROOTSYS/lib`.
4. ROOT's unmodified `core/base/src/roota.cxx` is compiled as a side module. Its
   `usedToIdentifyStaticRoot` symbol selects `TROOT::InitInterpreter`'s supported static-build
   path, avoiding the second absolute-path load of `libRIO`. This replaces the earlier aliasing
   of Emscripten's private, version-pinned `LDSO.loadedLibsByName` state.

## Platform ports added since the Core build (all in `../p0deps/xbuild/host-rootcling.patch`)

Each was the first error of a run, and each follows an existing upstream platform guard:

| First error | Change | Class |
| --- | --- | --- |
| `TMapFile.cxx:854: use of undeclared identifier 'SEM_R'` | `HAVE_SEMOP` guard excludes `R__EMSCRIPTEN` (as it already excludes `R__WINGCC`). No SysV semaphores in wasm. | PLATFORM PORT |
| `undefined symbol: dl_iterate_phdr` (`TROOT::GetSharedLibDir`) | New `R__EMSCRIPTEN` branch returning `$ROOTSYS/lib`; wasm has no ELF program headers. ROOT already derives `$ROOTSYS` from the environment (`FoundationUtils::GetRootSys`). | PLATFORM PORT |
| `undefined symbol: getxattr` (`TFile::Open`) | EOS-FUSE xattr redirect block excluded for `R__EMSCRIPTEN`. | PLATFORM PORT |
| Crash in `__syscall_socket(AF_NETLINK)`/`sendto` during `TUUID::GetNodeIdentifier` | On `R__EMSCRIPTEN` take ROOT's own "no network interface" path (`adr = 1`), which upstream already documents and uses when `getifaddrs` fails. Emscripten's netlink `getifaddrs` traps instead of failing. | PLATFORM PORT |

Also in M1: `-pthread` is dropped for Emscripten (`CheckCompiler.cmake`; the browser runtime is
single-threaded), everything is built `-fwasm-exceptions` to match the G7 runtime, and the host
generator is now the **pinned CERN ROOT 6.40.04** binary release (sha256
`287ff87deef0eed0fedd32e7d59bdadd22dcb45a5c592c9e08d8d140212ef261`, verified locally; root.cern
publishes no `.sha256`), so the earlier 6.40.02 version mismatch is gone.

## Not established

- No browser run yet: this gate is Node (`-sNODERAWFS`). The Chromium/xeus-cpp-lite path is M3.
- No interpreter: `TF1`, `TFormula`, `TClass` reflection, `gROOT->ProcessLine` and every
  `TH1D` constructor still stop at `InitInterpreter`.
- No P0 numerical parity yet — that needs M3.
- `TMapFile` synchronization, EOS redirection and UUID network identity are
  unavailable. Default UUID node fallback hashes time/hostname/machine info;
  cross-worker/session uniqueness is untested. The TMapFile platform path
  silently disables semaphore operations, so no shared-memory support is claimed.
