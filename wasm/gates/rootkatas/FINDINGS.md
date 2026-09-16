# M6a — the shipped ROOT Kata curriculum, running in the browser

## Verdict: **PASS**

```bash
bash wasm/gates/rootkatas/run.sh          # -> "rootkatas M6a PASS"
```

```
cpp-array-index                        ok  identical to native, validator passed 1/1
cpp-array-print                        ok  identical to native, validator passed 4/4
cpp-count-above                        ok  identical to native, validator passed 4/4
cpp-hello-world                        ok  identical to native, validator passed 2/2
cpp-sum-positive                       ok  identical to native, validator passed 4/4
cpp-root-histogram-inspect             ok  identical to native, validator passed 2/2
cpp-root-histogram-range               ok  identical to native, validator passed 2/2
cpp-root-histogram-selected-sample     ok  identical to native, validator passed 2/2
cpp-root-tf1-evaluate                  ok  identical to native, validator passed 2/2
cpp-root-tf1-range-parameters          ok  identical to native, validator passed 2/2
cpp-root-tgraph-points                 ok  identical to native, validator passed 2/2
cpp-root-fit-gaussian                  ok  valid natively; BLOCKED as expected, awaiting M4b TClass reflection
cpp-root-histogram                     ok  valid natively; BLOCKED as expected, awaiting M4b TClass reflection
```

**11 of 13 exercises are completed in the browser exactly as they are natively**, and the two
that are not fail loudly and name what they are waiting for.

Every earlier gate compared probe programs written for this experiment. This one runs the
repository's own `harness.cpp`, its own `rk.h` emitter and its own `validator.py`, read and
never modified (`wasm/GATES.md:52`). For each exercise the gate requires **both**:

- the browser's `rk` JSON is byte-equal to the native ROOT 6.40.04 run of the same harness, and
- the exercise's own validator grades the browser's JSON as passed.

## The reference solutions are new, and they are fixtures

The repository ships no correct solutions: 11 of 13 `solution.cpp` files are `// TODO` stubs,
and two (`cpp-root-histogram-range`, `cpp-root-tf1-range-parameters`) are *deliberately seeded
wrong* as bug hunts. So [`solutions/`](solutions) holds one correct solution per exercise,
written for this gate. Two were lifted rather than rewritten, from the repository's own tests
(`tests/test_cpp.py:7` and `:66`).

They live under `wasm/` and never in `src/root_kata/exercises/`: rule 6 keeps the curriculum
unmodified. All 13 pass natively, which is what makes them usable as a reference at all.

## How a kata becomes a browser cell

The browser kernel compiles one translation unit and has no include path for the exercise's
local files, so the gate inlines `rk.h` and the solution in place of the harness's two
`#include "..."` lines. Nothing else about the harness changes. `rk::done()` prints the results
as the last line of stdout, which is what both arms parse.

## Finding: both blocked katas stop at the same place

`cpp-root-histogram` was expected to fail on its `TCanvas`. It does not — it stops earlier, at
`TInterpreter::SetClassInfo`, exactly like `cpp-root-fit-gaussian`:

```
Error in <TCppInterOpInterpreter>: TInterpreter::SetClassInfo is not implemented in wasm ROOT yet
```

So **TClass reflection (M4b), not graphics, is what blocks both**. Whether the canvas then also
needs M5 is unknown until reflection lands. The gate first requires each fixture to pass its
own validator under native ROOT, then asserts the browser blocker names reflection. A fixture
that merely manufactures a `SetClassInfo` failure cannot pass by accident; the gate turns
these into ordinary parity checks only when M4b lands.

## Two tolerance checks worth noting

They passed, and they are tighter than anything the experiment's own probes test:

- `cpp-root-tf1-evaluate` requires `"eval2 changed"` to be **exactly** `0.0` within `1e-9`,
  from a formula the interpreter compiled at runtime.
- `cpp-root-tf1-range-parameters` requires `"eval4"` to match **CPython's**
  `math.exp(-2.0) * 12` within `1e-10` — coupling wasm floating point to native ROOT *and* to
  the Python that grades it.

## Finding: the gates raced over shared state

The first full run failed from `cpp-root-histogram` onward with
`missing side module .../rootsys/lib/libThread.so`, because the reviewer was running
`wasm/gates/rootlight/run.sh` at the same time and its `stage` step does `rm -rf` on the shared
staged `$ROOTSYS`.

Fixed by staging the browser payload **once** per sweep (`ROOTWEB_REUSE=1`) instead of
re-copying ~124 MB per exercise. `rootweb/run.sh` also serialises its payload and captured
output. At the shared `$ROOTSYS` boundary, `rootlight` now holds an exclusive `flock` while
rebuilding it, while the interpreter builder and rootweb stager take shared locks while
reading it. A held producer lock delayed a consumer until release, and the full four-gate run
then passed.

## Payload, measured

The staged web root is **123.9 MB** raw. Compressed, its three largest files (105.8 MB of the
total) come to **18.7 MB** with brotli q11 and **27.4 MB** with gzip -9:

| file | raw | gzip -9 | brotli q11 |
| --- | ---: | ---: | ---: |
| `libclangCppInterOp.so` | 71.3 MB | 22.8 MB | 15.7 MB |
| `xcpp.data` | 26.1 MB | 3.0 MB | 2.0 MB |
| `rootsys.js` | 8.5 MB | 1.6 MB | 1.1 MB |

Almost all of it is the C++ compiler, not ROOT. GitHub Pages serves gzip, not brotli, unless
the payload is pre-compressed and content-negotiated — and the compiler is fetched by
Emscripten's loader rather than by markup, so any such scheme has to survive that path. This is
a one-time cached download; no cold-load time has been measured.

## Not established

- **No in-browser grading.** The validators run in CPython on the developer's machine. Running
  them in the page needs Pyodide, which is M6 proper.
- **The product runner is untouched.** `docs/site.js:238` still posts to a local server; this
  gate drives the browser itself.
- 11 exercises, one reference solution each, on this machine. Nothing is established about
  wrong or malformed student code in the browser, about compile-error reporting, or about
  timeouts and crashes — the paths `tests/test_cpp.py` covers natively with its
  `WRONG`/`BROKEN`/`CRASH`/`LOOP` payloads.
- No preview images: the one kata that draws is blocked.
