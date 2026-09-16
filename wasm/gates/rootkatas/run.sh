#!/usr/bin/env bash
# M6a: the shipped ROOT Kata curriculum, run in the browser by wasm ROOT.
#
# Every earlier gate compares probe programs written for this experiment. This
# one runs the repository's own harnesses, its own rk.h emitter and its own
# validators, and requires the browser to agree with native ROOT and to pass
# grading. It reads `src/` and never writes to it (wasm/GATES.md:52).
#
# Usage: run.sh [exercise-id ...]   (default: all 13)
#
# Prints "rootkatas M6a PASS" / exit 0, or "rootkatas M6a FAIL: <reason>".
set -uo pipefail

HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd -P)"
REPO="$(cd -- "$HERE/../../.." >/dev/null 2>&1 && pwd -P)"
HOST_ROOT="${HOST_ROOT:-$HOME/.cache/rootwasm-p0/xbuild/root-6.40.04-host/root}"

fail() { echo "rootkatas M6a FAIL: $*" >&2; exit 1; }

command -v g++ >/dev/null || fail "g++ not found"
command -v node >/dev/null || fail "node not found"
command -v "${CHROMIUM_BIN:-chromium}" >/dev/null || fail "chromium not found (set CHROMIUM_BIN)"
[[ -x $HOST_ROOT/bin/root-config ]] || fail "no pinned native ROOT at $HOST_ROOT"
[[ -f $HOME/.cache/rootwasm-p0/interpreter/libCling.so ]] \
  || fail "no wasm interpreter built (run: bash wasm/rootlight/interpreter/build.sh)"

# Stage the browser payload once, then run every cell against that snapshot.
# Re-staging per cell copies ~124 MB and re-reads the shared $ROOTSYS, which
# another gate (rootlight's stage step does rm -rf) can be rebuilding meanwhile.
bash "$REPO/wasm/gates/rootweb/run.sh" payload > "$HOME/.cache/rootwasm-p0/rootkatas-payload.log" 2>&1 \
  || { tail -5 "$HOME/.cache/rootwasm-p0/rootkatas-payload.log" >&2; fail "could not stage the browser payload"; }

# ROOTSYS must not leak in from the caller's shell: root-config resolves its own
# prefix, and a stale ROOTSYS makes the native arm use another installation.
env -u ROOTSYS python3 "$HERE/sweep.py" "$@" || fail "see the per-exercise lines above"

echo "rootkatas M6a PASS"
