#!/usr/bin/env bash
# M2: link ROOT's own wasm libraries (xbuild Hist closure) as side modules and load them.
# Usage: run.sh [stage|link|smoke|all]  (default all). Heavy outputs: ~/.cache/rootwasm-p0/rootlight
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
XB=${XBUILD:-$HOME/.cache/rootwasm-p0/xbuild}/build
OUT=${OUT:-$HOME/.cache/rootwasm-p0/rootlight}
EMSDK=${EMSDK:-$HOME/.root-kata-wasm/emsdk}
source "$EMSDK/emsdk_env.sh" >/dev/null 2>&1
emcc --version | head -1 | grep -q ' 4\.0\.9 ' || { echo "rootlight FAIL: need emcc 4.0.9"; exit 1; }
LIBS=(Core Thread RIO MathCore Matrix Hist Minuit2)
step=${1:-all}
R=$OUT/rootsys   # staged ROOTSYS tree (lib/ include/ etc/), mounted as $ROOTSYS at runtime
ROOTSYS_LOCK=${ROOTSYS_LOCK:-$OUT/.rootsys.lock}
mkdir -p "$OUT"
exec {rootsys_lockfd}> "$ROOTSYS_LOCK"
flock -w 3600 "$rootsys_lockfd" \
  || { echo "rootlight FAIL: another process is using $R"; exit 1; }

# Staged ROOTSYS: lib/ holds one Emscripten side module per ROOT library, with the same
# NEEDED graph as native ROOT.
# obj/ keeps the relocatable outputs of ROOT's CMake targets they are linked from.

if [[ $step == stage || $step == all ]]; then
  rm -rf "$R"; mkdir -p "$R/lib" "$R/obj"
  for l in "${LIBS[@]}"; do
    cp "$XB/lib/lib$l.so" "$R/obj/" || { echo "rootlight FAIL: stage $l"; exit 1; }
  done
  cp "$XB"/lib/*.rootmap "$XB"/lib/*_rdict.pcm "$R/lib/" \
    || { echo "rootlight FAIL: stage dictionary resources"; exit 1; }
  cp -rL "$XB/include" "$R/include" && cp -rL "$XB/etc" "$R/etc" \
    || { echo "rootlight FAIL: stage ROOT headers/etc"; exit 1; }
fi

if [[ $step == link || $step == all ]]; then
  for l in "${LIBS[@]}"; do
    # Preserve ROOT's generated link dependencies instead of maintaining a parallel graph.
    deps=$(python3 - "$XB" "$l" <<'PYDEPS'
from pathlib import Path
import re, shlex, sys
build, lib = Path(sys.argv[1]), sys.argv[2]
links = list(build.glob("**/CMakeFiles/" + lib + ".dir/link.txt"))
assert len(links) == 1, "expected one ROOT-generated link rule for " + lib
command = links[0].read_text()
# CMake's Emscripten rules put library inputs in @response files.
command += " " + " ".join((links[0].parents[2] / arg[1:]).read_text()
                          for arg in shlex.split(command) if arg.startswith("@"))
names = dict.fromkeys(re.findall(r"lib(\w+)\.so", command))
print(" ".join(name for name in names if name != lib))
PYDEPS
    ) || { echo "rootlight FAIL: ROOT link dependencies for $l"; exit 1; }
    d=(); for x in $deps; do d+=("$R/lib/lib$x.so"); done
    em++ -fwasm-exceptions -sSIDE_MODULE=1 -O2 "$R/obj/lib$l.so" "${d[@]}" -o "$R/lib/lib$l.so" > "$OUT/link-$l.log" 2>&1 \
      || { grep error "$OUT/link-$l.log" | head; echo "rootlight FAIL: link $l"; exit 1; }
    echo "lib$l.so $(stat -c %s "$R/lib/lib$l.so")"
  done
fi

if [[ $step == smoke || $step == all ]]; then
  # ROOT's own static-build marker tells TROOT::InitInterpreter that the ROOT
  # libraries are already loaded, so it resolves CreateInterpreter through the
  # global symbol table instead of dlopen'ing a second libRIO by absolute path.
  . "$HERE/../../toolchain/root-src.env"
  ROOT_SRC="${ROOT_WASM_TOOLS:-$HOME/.root-kata-wasm}/src/root-${ROOT_VERSION}"
  ROOTA="$ROOT_SRC/core/base/src/roota.cxx"
  [[ -f $ROOTA ]] || { echo "rootlight FAIL: missing ROOT's roota.cxx"; exit 1; }
  em++ -fwasm-exceptions -O2 -sSIDE_MODULE=1 "$ROOTA" -o "$R/lib/libroota.so" \
    || { echo "rootlight FAIL: build roota.cxx"; exit 1; }

  # Emscripten does not forward host env vars to the program: pass them explicitly.
  # ROOT_LDSYSPATH is ROOT's own override (TUnixSystem.cxx DynamicPath) that skips the
  # popen("LD_DEBUG=libs ... ls") system-path probe; a browser cannot spawn processes.
  cat > "$OUT/env-pre.js" <<'JS'
// Node stand-in for what the browser page's loader does.
// 1. Emscripten does not forward host env vars: pass ROOTSYS explicitly. ROOT_LDSYSPATH is
//    ROOT's own override (TUnixSystem.cxx DynamicPath) for the popen("LD_DEBUG=libs ... ls")
//    system-path probe, which a browser cannot run.
// 2. Resolve ROOT side modules (loaded by NEEDED basename) from $ROOTSYS/lib.
Module.preRun = (Module.preRun || []).concat([() => {
  ENV.ROOTSYS = process.env.ROOTSYS;
  ENV.ROOT_LDSYSPATH = process.env.ROOTSYS + '/lib';
}]);
Module.locateFile = (p, prefix) => p.endsWith('.so') ? process.env.ROOTSYS + '/lib/' + p : prefix + p;
JS
  em++ -std=c++17 -fwasm-exceptions -O1 -I "$R/include" -sMAIN_MODULE=1 -sNODERAWFS=1 -sALLOW_MEMORY_GROWTH=1 --pre-js "$OUT/env-pre.js" \
    "$HERE/smoke.cxx" -L"$R/lib" "$R/lib/libroota.so" "$R/lib/libMinuit2.so" "$R/lib/libHist.so" "$R/lib/libMatrix.so" "$R/lib/libMathCore.so" "$R/lib/libRIO.so" "$R/lib/libThread.so" "$R/lib/libCore.so" -o "$OUT/smoke.js" > "$OUT/smoke-link.log" 2>&1 \
    || { grep -E "error" "$OUT/smoke-link.log" | head; echo "rootlight FAIL: smoke link"; exit 1; }
  (cd "$R/lib" && ROOTSYS=$R timeout 300 node "$OUT/smoke.js") > "$OUT/smoke.out" 2>&1; rc=$?; echo "node exit=$rc" >> "$OUT/smoke.out"
  cat "$OUT/smoke.out"
  # M2 gate: genuine ROOT initialises and runs compiled ROOT code in wasm, its libraries are
  # use ROOT's own static-build path, and the first gROOT use stops exactly
  # at the known interpreter boundary (M3 supplies libCling).
  [[ $rc -eq 1 ]] || { echo "rootlight FAIL: expected ROOT exit 1, got $rc"; exit 1; }
  head -5 "$OUT/smoke.out" > "$OUT/smoke.head"
  if ! diff -u "$HERE/expected.txt" "$OUT/smoke.head"; then echo "rootlight FAIL: smoke output"; exit 1; fi
  grep -qx 'staticroot=1' "$OUT/smoke.out" \
    || { echo "rootlight FAIL: ROOT static-build marker not visible"; exit 1; }
  grep -q "already in TClassTable" "$OUT/smoke.out" && { echo "rootlight FAIL: library loaded twice"; exit 1; }
  grep -qE 'Fatal in <TROOT::InitInterpreter>: cannot load symbol .*CreateInterpreter' "$OUT/smoke.out" \
    && echo "rootlight M2 PASS (static-ROOT path stops at CreateInterpreter, as expected)" \
    || { echo "rootlight FAIL: unexpected stop"; exit 1; }
fi
