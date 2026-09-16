#!/usr/bin/env bash
# Build libCling.so for wasm ROOT: ROOT's TInterpreter implemented over the
# CppInterOp interpreter the browser kernel already runs.
#
# Usage: build.sh [output-dir]      (default: $HOME/.cache/rootwasm-p0/interpreter)
#
# The result is an Emscripten side module. Its CppImpl::* references are left
# undefined on purpose: libclangCppInterOp.so is already loaded global:true by
# the kernel, so they bind at load time to the kernel's own interpreter.
set -uo pipefail

HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd -P)"
REPO="$(cd -- "$HERE/../../.." >/dev/null 2>&1 && pwd -P)"
OUT="${1:-$HOME/.cache/rootwasm-p0/interpreter}"
R="${ROOTSYS_STAGE:-$HOME/.cache/rootwasm-p0/rootlight/rootsys}"
XCPP="${XCPP_STAGE:-$HOME/.root-kata-wasm/xcpp-toolchain}"

fail() { echo "interpreter build FAIL: $*" >&2; exit 1; }

[[ -d $R/include ]] || fail "no staged ROOTSYS at $R (run wasm/gates/rootlight/run.sh stage)"
[[ -d $XCPP/cppinterop-extract/include ]] || fail "no CppInterOp headers at $XCPP"

. "$REPO/wasm/toolchain/root-src.env"
ROOT_SRC="${ROOT_WASM_TOOLS:-$HOME/.root-kata-wasm}/src/root-${ROOT_VERSION}"
. "$REPO/wasm/toolchain/activate.sh" >/dev/null 2>&1 || fail "could not activate pinned Emscripten"
[[ $(emcc --version 2>/dev/null | grep -c ' 4\.0\.9 ') -ge 1 ]] || fail "need emcc 4.0.9"

mkdir -p "$OUT"

# The loud-failure overrides are generated from ROOT's own pinned header, so the
# set cannot drift from the TInterpreter ROOT actually calls.
python3 "$HERE/gen_fatal.py" "$ROOT_SRC/core/meta/inc/TInterpreter.h" "$HERE/implemented.txt" \
  > "$OUT/fatal_methods.inc" || fail "could not generate the loud-failure overrides"

em++ -std=c++17 -fwasm-exceptions -O2 -sSIDE_MODULE=1 \
  -I "$OUT" -I "$HERE" -I "$R/include" -I "$XCPP/cppinterop-extract/include" \
  "$HERE/TCppInterOpInterpreter.cxx" \
  -o "$OUT/libCling.so" > "$OUT/build.log" 2>&1 \
  || { grep -E "error" "$OUT/build.log" | head -20; fail "em++ link (see $OUT/build.log)"; }

NM="${EMSDK:-$HOME/.root-kata-wasm/emsdk}/upstream/bin/llvm-nm"
[[ -x $NM ]] || fail "llvm-nm not found at $NM"
for sym in CreateInterpreter DestroyInterpreter; do
  [[ $("$NM" --defined-only "$OUT/libCling.so" 2>/dev/null | grep -cw "$sym") -ge 1 ]] \
    || fail "libCling.so does not export $sym"
done

echo "    built $OUT/libCling.so ($(stat -c '%s' "$OUT/libCling.so") bytes)"
echo "interpreter build PASS"
