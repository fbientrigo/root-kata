#!/usr/bin/env bash
# M3: ROOT's interpreter, implemented over CppInterOp, running in the browser.
#
# The gate is numerical fidelity, not "it started": the unmodified P0 program
# wasm/gates/p0deps/runtime/p0.cxx -- 39 TH1D/TAxis values printed at %.17g --
# is compiled and run *inside Chromium* by wasm ROOT, and must match the pinned
# native CERN ROOT 6.40.04 build of the same file byte for byte.
#
# Usage: run.sh [native|browser|loud|all]   (default all)
#   native   build and run p0.cxx against the pinned native ROOT -> the reference
#   browser  run the same p0.cxx in headless Chromium through wasm/gates/rootweb
#   loud     prove an unimplemented interpreter service fails unmistakably
#   all      all three, then diff
#
# Prints "rootinterp M3 PASS" / exit 0, or "rootinterp M3 FAIL: <reason>".
set -uo pipefail

HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd -P)"
REPO="$(cd -- "$HERE/../../.." >/dev/null 2>&1 && pwd -P)"
ROOTWEB="$REPO/wasm/gates/rootweb"
P0="$REPO/wasm/gates/p0deps/runtime/p0.cxx"
OUT="${OUT:-$HOME/.cache/rootwasm-p0/rootinterp}"
HOST_ROOT="${HOST_ROOT:-$HOME/.cache/rootwasm-p0/xbuild/root-6.40.04-host/root}"
WEB_BUILD="${BUILD:-$REPO/wasm/build/rootweb}"

step="${1:-all}"
fail() { echo "rootinterp M3 FAIL: $*" >&2; exit 1; }
mkdir -p "$OUT"

if [[ $step != native ]]; then
  bash "$REPO/wasm/rootlight/interpreter/build.sh" > "$OUT/interpreter-build.log" 2>&1 \
    || { tail -20 "$OUT/interpreter-build.log" >&2; fail "interpreter build"; }
fi

if [[ $step == native || $step == all ]]; then
  # The reference is regenerated here rather than read from a cache file, so the
  # comparison is against a ROOT you can rebuild, not a recorded number.
  [[ -x $HOST_ROOT/bin/root-config ]] \
    || fail "no pinned native ROOT at $HOST_ROOT (run wasm/gates/p0deps/xbuild/run.sh configure)"
  ver="$("$HOST_ROOT/bin/root-config" --version)"
  [[ $ver == 6.40/04 || $ver == 6.40.04 ]] || fail "pinned native ROOT is $ver, expected 6.40.04"
  # ROOTSYS must not leak in from the caller's shell: root-config resolves its
  # own prefix, and a stale ROOTSYS makes it pick another installation.
  CF="$(env -u ROOTSYS "$HOST_ROOT/bin/root-config" --cflags)" || fail "root-config --cflags"
  g++ $CF -o "$OUT/p0-native" "$P0" \
      -L"$HOST_ROOT/lib" -Wl,-rpath,"$HOST_ROOT/lib" -lHist -lCore \
      > "$OUT/native-build.log" 2>&1 || { tail -5 "$OUT/native-build.log" >&2; fail "native build"; }
  env -u ROOTSYS "$OUT/p0-native" > "$OUT/p0-native.out" 2> "$OUT/p0-native.err" \
    || { tail -5 "$OUT/p0-native.err" >&2; fail "native run"; }
  n="$(wc -l < "$OUT/p0-native.out")"
  [[ $n -eq 39 ]] || fail "native reference has $n lines, expected 39"
  echo "    native CERN ROOT $ver: $n values -> $OUT/p0-native.out"
fi

if [[ $step == browser || $step == all ]]; then
  bash "$ROOTWEB/run.sh" cell "$P0" > "$OUT/browser.log" 2>&1 \
    || { tail -20 "$OUT/browser.log" >&2; fail "could not run p0.cxx in the browser"; }
  cp "$WEB_BUILD/cell_stdout.txt" "$OUT/p0-browser.out"
  cp "$WEB_BUILD/cell_diag.txt" "$OUT/p0-browser.diag"
  [[ -s $OUT/p0-browser.out ]] || { head -c 400 "$OUT/p0-browser.diag" >&2; fail "p0.cxx produced no output in the browser"; }
  echo "    wasm ROOT in Chromium: $(wc -l < "$OUT/p0-browser.out") values -> $OUT/p0-browser.out"
fi

if [[ $step == loud || $step == all ]]; then
  # Falsifiability, and the project's own rule: a service this interpreter does
  # not implement must fail unmistakably, never quietly return a default.
  cat > "$OUT/loud.cxx" <<'CXX'
// An interpreter service that is out of scope for a browser, permanently:
// generating a dictionary at runtime requires rootcling, a host tool that will
// never exist here. Anything with a plausible future implementation would make
// this check expire the moment that milestone lands.
#include <cstdio>
#include "TInterpreter.h"
int main() {
  printf("loud.start\n");
  fflush(stdout);
  gInterpreter->GenerateDictionary("TFoo", "TFoo.h", "");
  printf("loud.unreachable\n");
  return 0;
}
CXX
  bash "$ROOTWEB/run.sh" cell "$OUT/loud.cxx" > "$OUT/loud.log" 2>&1 \
    || { tail -20 "$OUT/loud.log" >&2; fail "could not run the loud-failure cell"; }
  cp "$WEB_BUILD/cell_stdout.txt" "$OUT/loud.out"
  cp "$WEB_BUILD/cell_diag.txt" "$OUT/loud.diag"
  if [[ $(grep -c "loud.unreachable" "$OUT/loud.out") -ge 1 ]]; then
    fail "an unimplemented interpreter service returned instead of failing"
  fi
  if [[ $(cat "$OUT/loud.out" "$OUT/loud.diag" | grep -c "not implemented in wasm ROOT yet") -lt 1 ]]; then
    { echo "--- stdout:"; cat "$OUT/loud.out"; echo "--- diag:"; head -c 600 "$OUT/loud.diag"; } >&2
    fail "an unimplemented service failed without naming itself"
  fi
  echo "    unimplemented services fail loudly and by name"
fi

if [[ $step == all ]]; then
  if ! diff -u "$OUT/p0-native.out" "$OUT/p0-browser.out" > "$OUT/p0.diff"; then
    head -40 "$OUT/p0.diff" >&2
    fail "wasm ROOT in the browser does not match native ROOT"
  fi
  echo "    P0 PARITY: native CERN ROOT 6.40.04 == wasm ROOT in Chromium, byte for byte"
  echo "               ($(wc -l < "$OUT/p0-native.out") values at %.17g)"
  echo "rootinterp M3 PASS"
fi
