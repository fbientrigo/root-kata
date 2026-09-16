#!/usr/bin/env bash
# M4a: TFormula-backed TF1 and TGraph in the browser, matching native ROOT.
#
# This is the first gate whose numbers come from code the interpreter compiled
# at runtime: a TF1 built from a formula string is C++ that TFormula generates,
# hands to the interpreter, and then calls back into
# (hist/hist/src/TFormula.cxx:944-961, 3518-3527). If any part of that path were
# faked, these values would not match native ROOT.
#
# Usage: run.sh [parity|loud|all]   (default all)
#
# Prints "rootformula M4a PASS" / exit 0, or "rootformula M4a FAIL: <reason>".
set -uo pipefail

HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd -P)"
REPO="$(cd -- "$HERE/../../.." >/dev/null 2>&1 && pwd -P)"
OUT="${OUT:-$HOME/.cache/rootwasm-p0/rootformula}"
WEB_BUILD="${BUILD:-$REPO/wasm/build/rootweb}"

step="${1:-all}"
fail() { echo "rootformula M4a FAIL: $*" >&2; exit 1; }
mkdir -p "$OUT"

bash "$REPO/wasm/rootlight/interpreter/build.sh" > "$OUT/interpreter-build.log" 2>&1 \
  || { tail -20 "$OUT/interpreter-build.log" >&2; fail "interpreter build"; }

if [[ $step == parity || $step == all ]]; then
  bash "$REPO/wasm/gates/common/parity.sh" "$HERE/p1.cxx" "$OUT" -lGraf \
    || fail "TF1/TGraph output differs from native ROOT (see $OUT/p1.diff)"
fi

if [[ $step == loud || $step == all ]]; then
  # The boundary this milestone stops at, asserted rather than described:
  # TH1::Fit needs TClass reflection, which is not implemented, and it must say
  # so instead of returning a fit result that nothing computed.
  cat > "$OUT/fit.cxx" <<'CXX'
#include "TH1D.h"
#include "TF1.h"
#include <cstdio>
int main() {
  TH1D h("h", "h", 20, -5, 5);
  for (int i = 0; i < 20; ++i) { h.SetBinContent(i + 1, 10.0); h.SetBinError(i + 1, 1.0); }
  TF1 f("f", "gaus", -5, 5);
  f.SetParameters(10.0, 0.0, 1.0);
  printf("fit.start\n");
  fflush(stdout);
  h.Fit(&f, "QN0");
  printf("fit.returned\n");
  return 0;
}
CXX
  bash "$REPO/wasm/gates/rootweb/run.sh" cell "$OUT/fit.cxx" > "$OUT/fit.log" 2>&1 \
    || { tail -20 "$OUT/fit.log" >&2; fail "could not run the fit cell"; }
  cp "$WEB_BUILD/cell_stdout.txt" "$OUT/fit.out"
  cp "$WEB_BUILD/cell_diag.txt" "$OUT/fit.diag"
  if [[ $(grep -c "fit.returned" "$OUT/fit.out") -ge 1 ]]; then
    fail "TH1::Fit returned a result, but TClass reflection is not implemented -- \
a fit nothing computed is exactly the silent no-op this project forbids"
  fi
  if [[ $(cat "$OUT/fit.out" "$OUT/fit.diag" | grep -c "not implemented in wasm ROOT yet") -lt 1 ]]; then
    { echo "--- stdout:"; cat "$OUT/fit.out"; echo "--- diag:"; head -c 600 "$OUT/fit.diag"; } >&2
    fail "TH1::Fit failed without naming the missing service"
  fi
  svc=$(grep -o "TInterpreter::[A-Za-z_]* is not implemented" "$OUT/fit.diag" | head -1)
  echo "    TH1::Fit stops loudly at: ${svc:-an unimplemented interpreter service}"
fi

echo "rootformula M4a PASS"
