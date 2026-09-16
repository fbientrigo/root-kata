#!/usr/bin/env bash
# ROOT dictionary (usage: run.sh [Core|MathCore|Matrix|Hist|...], default Core) for wasm32 from the installed native rootcling (host tool), then em++ compile.
# Generator env mirrors em++'s own frontend (target, sysroot, -DEMSCRIPTEN, include order) plus a
# dictionary-generator-only stdlib.h overlay (see overlay/stdlib.h). em++ never sees the overlay.
# Prints dictprobe PASS / dictprobe FAIL: <stage>.
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
X=${XBUILD:-$HOME/.cache/rootwasm-p0/xbuild}
T=${1:-Core}
OUT=${OUT:-$HOME/.cache/rootwasm-p0/dictprobe/$T}
EMSDK=${EMSDK:-$HOME/.root-kata-wasm/emsdk}
SYS=$EMSDK/upstream/emscripten/cache/sysroot
BUILTIN=$EMSDK/upstream/lib/clang/21/include
rm -rf "$OUT"; mkdir -p "$OUT/lib"

# Exact generated command (xbuild build.make), outputs redirected into $OUT.
BM=$(find "$X/build" -path "*/CMakeFiles/G__$T.dir/build.make" | head -1)
[ -n "$BM" ] || { echo "dictprobe FAIL: no G__$T rule"; exit 2; }
WD=$(dirname "$(dirname "$(dirname "$BM")")")
# Exact generated command (all upstream options kept), outputs redirected into $OUT.
sed -n "s/^\t*cd [^&]*&& //; /rootcling -rootbuild.* G__$T.cxx /p" "$BM" | head -1 \
  | sed "s| -f G__$T.cxx | -f $OUT/G__$T.cxx |; s| -s [^ ]*lib$T.so | -s $OUT/lib/lib$T.so |; s| -rmf [^ ]*lib$T.rootmap | -rmf $OUT/lib/lib$T.rootmap |" \
  > "$OUT/rootcling-cmd.sh"
grep -q "$OUT/G__$T.cxx" "$OUT/rootcling-cmd.sh" || { echo "dictprobe FAIL: command-extract"; exit 2; }

export EXTRA_CLING_ARGS="-std=c++17 --target=wasm32-unknown-emscripten --sysroot=$SYS -DEMSCRIPTEN -fignore-exceptions -nostdinc -nostdinc++ -isystem $SYS/include/fakesdl -isystem $SYS/include/compat -isystem $SYS/include/c++/v1 -isystem $BUILTIN -isystem $HERE/overlay -isystem $SYS/include"
{ echo "EXTRA_CLING_ARGS=$EXTRA_CLING_ARGS"; cat "$OUT/rootcling-cmd.sh"; } > "$OUT/command.txt"

cd "$WD"
timeout 300 bash "$OUT/rootcling-cmd.sh" > "$OUT/rootcling.log" 2>&1; rc=$?
echo "rootcling exit=$rc" | tee -a "$OUT/rootcling.log"
[ $rc -eq 0 ] && [ -s "$OUT/G__$T.cxx" ] || { echo "dictprobe FAIL: generator (exit $rc)"; exit 1; }

gnu=$(grep -c '__gnu_cxx\|std::__cxx11' "$OUT/G__$T.cxx"); libcxx=$(grep -c 'std::__2\|__wrap_iter' "$OUT/G__$T.cxx")
echo "host-private-stl-lines=$gnu libcxx-lines=$libcxx lines=$(wc -l < "$OUT/G__$T.cxx")" | tee "$OUT/stl-spellings.txt"

source "$EMSDK/emsdk_env.sh" >/dev/null 2>&1
D=CMakeFiles/G__$T.dir
defs=$(sed -n 's/^CXX_DEFINES = //p' $D/flags.make); incs=$(sed -n 's/^CXX_INCLUDES = //p' $D/flags.make); flags=$(sed -n 's/^CXX_FLAGS = //p' $D/flags.make)
eval em++ $defs $incs $flags -o "$OUT/G__$T.cxx.o" -c "$OUT/G__$T.cxx" > "$OUT/compile.log" 2>&1; crc=$?
echo "em++ exit=$crc errors=$(grep -c 'error:' "$OUT/compile.log")" | tee -a "$OUT/compile.log"
[ $crc -eq 0 ] && [ "$gnu" -eq 0 ] && file "$OUT/G__$T.cxx.o" | grep -q WebAssembly || { echo "dictprobe FAIL: compile (exit $crc, host-stl-lines $gnu)"; exit 1; }
echo "dictprobe $T PASS"
