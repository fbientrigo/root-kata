# Session note for the independent reviewer (Codex Sol High)

Date: 2026-09-13. Coordinator: Claude, via Orca orchestration Run `run_85d4c70077b6`.

## What this session was asked to determine

Whether genuine CERN ROOT `TH1D` can be cross-built for WebAssembly using ROOT's real
`rootcling` dictionary-generation step as a **host-only** build tool, while the actual
runtime libraries are Emscripten/wasm targets — as a build-system question, not a
product-integration one. Full task text is in the session's system prompt (not
reproduced here); the short version is `wasm/GATES.md`'s G4 claim ("Actual ROOT `TH1D`
builds to WebAssembly"), attacked with a smarter approach than the G4 `BLOCKER.md`
direct-no-library-link probe.

**Note for the reviewer:** `wasm/NEXT.md` (written by the prior session) explicitly
scoped the *next* objective as a cheaper interpreter-based probe (test whether G7's
xeus-cpp-lite/Cling can resolve `TH1D` interactively) and said a full CMake+rootcling
cross-build "should be scoped deliberately, not started as a small follow-up." This
session's instructions scoped exactly that deliberate, larger experiment directly,
bypassing the interpreter probe. That is a legitimate scope decision (NEXT.md asked for
deliberate scoping, not that this path never be taken), but the interpreter-based probe
NEXT.md proposed remains untried and should stay on record as a still-open, cheaper
alternative — not supersede or invalidate it.

## Three independent workers, what they found

Run via Orca (`worker-start`, agent `codex`), each in its own child worktree off
`experiment/root-wasm-subset`, all landing on model `gpt-5.6-luna` (effort `high`) after
the default Codex model hit a session rate limit early on (see "Infrastructure notes"):

- **Agy High A** (`root-kata-rootwasm-th1d-a`) — `AGY-HIGH-A-REPORT.md`. Built a focused
  probe: native host ROOT 6.34.10 `rootcling` generates a real dictionary from upstream
  `hist/hist/inc/LinkDef.h`; Emscripten compiles both the generated dictionary and genuine
  upstream `TH1.cxx` to real wasm object code (verified with `file`: "WebAssembly (wasm)
  binary module"). Link fails on missing Core symbols (`TVersionCheck::TVersionCheck`,
  `TObject`/`TNamed`/`TString`/`TAtt*`/`TAxis`/`TArrayD`) because Core itself was not
  cross-compiled in this probe. Also found the full top-level ROOT-for-wasm configure
  fails earlier, at `core/clib/src/attach.c` (Emscripten: `close`/`malloc`/`free`/`lseek`/
  `read` undeclared).
- **Agy High B** (`root-kata-rootwasm-th1d-b`) — `AGY-HIGH-B-DEPENDENCY-MAP.md`. Independent
  source-level dependency map with exact file:line citations. Confirms A's Hist/Core
  boundary and constructor/method locations, but corrects A's `Core -> CLING` reading:
  `add_dependencies(Core CLING rconfigure)` is a CMake **build-order** edge, not a link
  edge (`core/CMakeLists.txt:34`) — Cling/LLVM, `rootcling`/`rootcling_stage1`, and `Rint`
  can stay host-side. States the supported wasm runtime closure as `Hist + MathCore +
  Matrix + RIO + Thread + Core`. Also found the all-Emscripten top-level configure emits
  `rootcling.js`, i.e. it tries to compile the host tool itself as a wasm target — a build
  orchestration defect, not a runtime requirement.
- **Agy Medium** (`root-kata-rootwasm-th1d-matrix`) — `AGY-MEDIUM-BUILD-MATRIX.md`
  (reconstructed from terminal transcript; its own `worker_done` file write did not
  happen, see caveat in that file). Bounded config matrix: every variant that keeps
  `builtin_cling=ON` (the default) drags the full embedded LLVM/Cling build into even a
  single leaf target (`Hist`) and blows the 180s bound; `builtin_cling=OFF` fails
  immediately for lacking a system `llvm-config`. No source patched, no config found that
  configures/builds quickly.

The three reports are mutually consistent and cross-referenced (B explicitly reviews and
refines A; Medium's finding about mandatory embedded LLVM/Cling matches B's `rootcling.js`
observation about the same underlying CMake defect).

## Suggested classification (for the reviewer to verify independently, not to adopt on faith)

**PARTIAL.** Real `rootcling` (native host) generated a real dictionary from unmodified
upstream ROOT source; Emscripten compiled genuine ROOT `.cxx` plus the generated
dictionary into real wasm object code; no hand-written `Class()`/`Streamer()`/stub/
reimplemented-histogram code was introduced anywhere (confirmed by A, and by B's
independent source citations). But no final linked, running wasm module exists — the
minimal six-call `TH1D` program (`Fill`/`GetEntries`/`GetBinContent`/`Integral`/
`GetMean`) was never executed in Chromium or compared against a native ROOT reference, so
gate-acceptance criteria 5-8 are not met. Root cause of the remaining gap is now
precisely located: the full `Hist + MathCore + Matrix + RIO + Thread + Core` closure
needs to itself be cross-compiled to wasm (not just `TH1.cxx` + dictionary), and stock
ROOT's top-level CMake does not cleanly separate "build `rootcling` for the host" from
"build library targets for wasm" (it tries to wasm-ify `rootcling` itself, and drags the
embedded LLVM/Cling sub-build into leaf-target builds even under `minimal=ON`).

## Infrastructure notes (do not re-derive; these are session mechanics, not gate evidence)

- All three workers hit the Codex account's session rate limit almost simultaneously
  partway through; Orca blocked scripted answers to the resulting interactive
  model-switch prompt (`agent_prompt_blocked` — a deliberate guard, not a bug), so they
  were relaunched fresh (`worker-start --retry-of`, same worktrees) on `gpt-5.6-luna`
  high effort per the user's explicit direction after they manually reset the account's
  limit. No repository files existed yet at that point, so nothing was lost by the
  restart beyond ~15-20 minutes of prior reasoning (not file changes).
- The host was under heavy memory pressure for most of this session from several
  long-running, unrelated `agy`/`codex` processes already on the machine (not started by
  this session) — swap was consistently 5+/7.9 GiB used. This caused the coordinator's
  own polling (`orca orchestration check --wait`) to be killed twice and, separately, the
  Orca runtime itself to briefly restart, which is why none of the three workers'
  `worker_done` messages actually reached the orchestration mailbox — all three finished
  their work but could not report it through the normal channel. Their reports were
  recovered directly from terminal transcripts via `orca orchestration worker-read`
  rather than through `worker_done` receipts. `worker-show`/`dispatch-show` for the
  three dispatches (`ctx_7c46eedcbaff`, `ctx_52a841913a3b`, `ctx_94ffb1b752a6`) will
  likely still show `dispatched`/no terminal `worker_done`, not because the work is
  incomplete but because of this delivery gap — verify against the actual worktree
  files and transcripts, not the dispatch status field.
- None of the three worker worktrees have any commits; each has exactly the untracked
  report file(s) named above (Medium has none — see its file's caveat). Nothing was
  staged or committed anywhere by the coordinator, per instructions.

## What's copied into the canonical worktree

This directory (`wasm/gates/g4/rootcling-crossbuild/`) — all files here were copied by
the coordinator from the three isolated worker worktrees, **uncommitted**, exactly as
the workers left them (except Medium's, reconstructed from transcript). Nothing else in
this repository was touched. `wasm/GATES.md`, `wasm/STATE.md`, and `wasm/NEXT.md` were
deliberately left unmodified — updating the gate ladder / state / next-objective record
is left to the reviewer's own independent-reproduction judgment, consistent with how G7
was closed out (commit `d442287` / `9fa5f54`).
