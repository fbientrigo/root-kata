#!/usr/bin/env bash
# Run the wasm experiment's gates in dependency order and report one line each.
#
# Usage: run-gates.sh [gate ...]        (default: the full ladder below)
#
# Each gate owns exactly one entry point that exits 0 and prints "<name> PASS",
# or exits non-zero and prints "<name> FAIL: <reason>" (wasm/GATES.md). This
# script only sequences them and summarises; it never decides a verdict itself.
#
# These are slow and local by design: they need the pinned emsdk, the pinned ROOT
# source, a native ROOT install, Node and headless Chromium, so they are not part
# of the repository's CI (which stays ROOT-free).
set -uo pipefail

HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd -P)"

# In dependency order: build -> load -> browser -> interpreter.
ALL=(
  "p0deps/xbuild"      # M1  ROOT's own CMake targets built for wasm
  "rootlight"          # M2  those libraries loading and running under Node
  "rootweb"            # M2b the same, in Chromium, plus the page you can open
  "rootinterp"         # M3  the interpreter, and P0 parity against native ROOT
  "rootformula"        # M4a TF1/TFormula/TGraph parity, and the TH1::Fit boundary
  "rootkatas"          # M6a the shipped curriculum, run in the browser
)
gates=("$@")
[[ ${#gates[@]} -eq 0 ]] && gates=("${ALL[@]}")

declare -a names=() results=()
rc_total=0
for g in "${gates[@]}"; do
  script="$HERE/gates/$g/run.sh"
  if [[ ! -f $script ]]; then
    names+=("$g"); results+=("MISSING $script"); rc_total=1; continue
  fi
  echo "==> $g"
  log="${TMPDIR:-/tmp}/rootwasm-gate-$(echo "$g" | tr / -).log"
  if bash "$script" 2>&1 | tee "$log"; then
    line="$(grep -E ' PASS' "$log" | tail -1)"
    names+=("$g"); results+=("${line:-PASS}")
  else
    line="$(grep -E ' FAIL' "$log" | tail -1)"
    names+=("$g"); results+=("${line:-FAIL (see $log)}")
    rc_total=1
    echo
    echo "--- stopping: $g did not pass (full log: $log)"
    break
  fi
  echo
done

echo "================ wasm gates ================"
for i in "${!names[@]}"; do printf '%-18s %s\n' "${names[$i]}" "${results[$i]}"; done
echo "============================================"
exit $rc_total
