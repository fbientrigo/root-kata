#!/usr/bin/env bash
# Core dictionary for wasm32 from the installed native rootcling (host tool), then em++ compile.
# Generator env mirrors em++'s own frontend (target, sysroot, -DEMSCRIPTEN, include order) plus a
# dictionary-generator-only stdlib.h overlay (see overlay/stdlib.h). em++ never sees the overlay.
# Prints dictprobe PASS / dictprobe FAIL: <stage>.
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
X=${XBUILD:-$HOME/.cache/rootwasm-p0/xbuild}
OUT=${OUT:-$HOME/.cache/rootwasm-p0/dictprobe}
EMSDK=${EMSDK:-$HOME/.root-kata-wasm/emsdk}
SYS=$EMSDK/upstream/emscripten/cache/sysroot
BUILTIN=$EMSDK/upstream/lib/clang/21/include
rm -rf "$OUT"; mkdir -p "$OUT/lib"

# Exact generated command (xbuild build.make), outputs redirected into $OUT.
sed -n 's/^\t*cd [^&]*&& //; /bin\/rootcling -rootbuild.*G__Core.cxx/p' \
  "$X/build/core/CMakeFiles/G__Core.dir/build.make" | head -1 \
  | sed "s| -f G__Core.cxx | -f $OUT/G__Core.cxx |; s| -s [^ ]*libCore.so | -s $OUT/lib/libCore.so |; s| -rmf [^ ]*libCore.rootmap | -rmf $OUT/lib/libCore.rootmap |" \
  > "$OUT/rootcling-cmd.sh"
grep -q "$OUT/G__Core.cxx" "$OUT/rootcling-cmd.sh" || { echo "dictprobe FAIL: command-extract"; exit 2; }

export EXTRA_CLING_ARGS="-std=c++17 --target=wasm32-unknown-emscripten --sysroot=$SYS -DEMSCRIPTEN -fignore-exceptions -nostdinc -nostdinc++ -isystem $SYS/include/fakesdl -isystem $SYS/include/compat -isystem $SYS/include/c++/v1 -isystem $BUILTIN -isystem $HERE/overlay -isystem $SYS/include"
{ echo "EXTRA_CLING_ARGS=$EXTRA_CLING_ARGS"; cat "$OUT/rootcling-cmd.sh"; } > "$OUT/command.txt"

cd "$X/build/core"
timeout 300 bash "$OUT/rootcling-cmd.sh" > "$OUT/rootcling.log" 2>&1; rc=$?
echo "rootcling exit=$rc" | tee -a "$OUT/rootcling.log"
[ $rc -eq 0 ] && [ -s "$OUT/G__Core.cxx" ] || { echo "dictprobe FAIL: generator (exit $rc)"; exit 1; }

gnu=$(grep -c '__gnu_cxx\|std::__cxx11' "$OUT/G__Core.cxx"); libcxx=$(grep -c 'std::__1\|__wrap_iter' "$OUT/G__Core.cxx")
echo "host-private-stl-lines=$gnu libcxx-lines=$libcxx lines=$(wc -l < "$OUT/G__Core.cxx")" | tee "$OUT/stl-spellings.txt"

source "$EMSDK/emsdk_env.sh" >/dev/null 2>&1
D=CMakeFiles/G__Core.dir
defs=$(sed -n 's/^CXX_DEFINES = //p' $D/flags.make); incs=$(sed -n 's/^CXX_INCLUDES = //p' $D/flags.make); flags=$(sed -n 's/^CXX_FLAGS = //p' $D/flags.make)
eval em++ $defs $incs $flags -o "$OUT/G__Core.cxx.o" -c "$OUT/G__Core.cxx" > "$OUT/compile.log" 2>&1; crc=$?
echo "em++ exit=$crc errors=$(grep -c 'error:' "$OUT/compile.log")" | tee -a "$OUT/compile.log"
[ $crc -eq 0 ] && [ "$gnu" -eq 0 ] || { echo "dictprobe FAIL: compile (exit $crc, host-stl-lines $gnu)"; exit 1; }
echo "dictprobe PASS"
