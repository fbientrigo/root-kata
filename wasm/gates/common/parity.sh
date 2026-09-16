#!/usr/bin/env bash
# Run one unmodified C++ program against native ROOT and against wasm ROOT in
# the browser, and diff the two outputs.
#
# Usage: parity.sh <program.cxx> <work-dir> [extra link flags ...]
#
# Exits 0 and prints the value count on a match; otherwise prints the diff and
# exits non-zero. Callers own the PASS/FAIL wording for their gate.
#
# The native reference is rebuilt here rather than read from a recorded file, so
# the comparison is against a ROOT that can be rebuilt, not a stored number.
set -uo pipefail

HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd -P)"
REPO="$(cd -- "$HERE/../../.." >/dev/null 2>&1 && pwd -P)"
ROOTWEB="$REPO/wasm/gates/rootweb"
HOST_ROOT="${HOST_ROOT:-$HOME/.cache/rootwasm-p0/xbuild/root-6.40.04-host/root}"
WEB_BUILD="${BUILD:-$REPO/wasm/build/rootweb}"

SRC="${1:?usage: parity.sh <program.cxx> <work-dir> [extra link flags]}"
OUT="${2:?usage: parity.sh <program.cxx> <work-dir> [extra link flags]}"
shift 2
EXTRA=("$@")

fail() { echo "parity FAIL: $*" >&2; exit 1; }
mkdir -p "$OUT"
base="$(basename "${SRC%.*}")"

[[ -x $HOST_ROOT/bin/root-config ]] || fail "no pinned native ROOT at $HOST_ROOT"
ver="$(env -u ROOTSYS "$HOST_ROOT/bin/root-config" --version)"
[[ $ver == 6.40/04 || $ver == 6.40.04 ]] || fail "pinned native ROOT is $ver, expected 6.40.04"

# ROOTSYS must not leak in from the caller's shell: root-config resolves its own
# prefix, and a stale ROOTSYS makes it pick a different installation.
CF="$(env -u ROOTSYS "$HOST_ROOT/bin/root-config" --cflags)" || fail "root-config --cflags"
g++ $CF -o "$OUT/$base-native" "$SRC" \
    -L"$HOST_ROOT/lib" -Wl,-rpath,"$HOST_ROOT/lib" -lHist -lCore -lMathCore "${EXTRA[@]}" \
    > "$OUT/$base-native-build.log" 2>&1 \
  || { tail -10 "$OUT/$base-native-build.log" >&2; fail "native build of $SRC"; }
env -u ROOTSYS "$OUT/$base-native" > "$OUT/$base-native.out" 2> "$OUT/$base-native.err" \
  || { tail -10 "$OUT/$base-native.err" >&2; fail "native run of $base"; }

bash "$ROOTWEB/run.sh" cell "$SRC" > "$OUT/$base-browser.log" 2>&1 \
  || { tail -20 "$OUT/$base-browser.log" >&2; fail "could not run $base in the browser"; }
cp "$WEB_BUILD/cell_stdout.txt" "$OUT/$base-browser.out"
cp "$WEB_BUILD/cell_diag.txt" "$OUT/$base-browser.diag"

[[ -s $OUT/$base-browser.out ]] \
  || { head -c 600 "$OUT/$base-browser.diag" >&2; fail "$base produced no output in the browser"; }

if ! diff -u "$OUT/$base-native.out" "$OUT/$base-browser.out" > "$OUT/$base.diff"; then
  head -40 "$OUT/$base.diff" >&2
  fail "wasm ROOT does not match native ROOT for $base"
fi

echo "    $base: native CERN ROOT $ver == wasm ROOT in Chromium, $(wc -l < "$OUT/$base-native.out") values"
