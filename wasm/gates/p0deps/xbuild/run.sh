#!/usr/bin/env bash
# Phase 3 bounded cross-build: ROOT `Core` target under Emscripten with a HOST rootcling.
# Usage: run.sh [configure|graph|build|inspect|all|diag-libcxx]   (default: all)
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
X=${X:-$HOME/.cache/rootwasm-p0/xbuild}
PIN=$HOME/.root-kata-wasm/src/root-6.40.04
S=$X/src B=$X/build
# conda-forge 6.40.02 fallback (CERN 6.40.04 debian13 tarball was a >10 min download)
HOST_ROOTCLING=${HOST_ROOTCLING:-/home/fabian/thesis/FairShip/.pixi/envs/default/bin/rootcling}
source ~/.root-kata-wasm/emsdk/emsdk_env.sh >/dev/null 2>&1
emcc --version | head -1 | grep -q ' 4\.0\.9 ' || { echo "need emcc 4.0.9"; exit 1; }

step=${1:-all}
mkdir -p "$X" "$B"

if [[ $step == configure || $step == all ]]; then
  [[ -d $S ]] || cp -a "$PIN" "$S"
  (cd "$S" && { patch -p1 -R --dry-run -s < "$HERE/host-rootcling.patch" >/dev/null 2>&1 || patch -p1 < "$HERE/host-rootcling.patch"; })
  cd "$B"; start=$(date +%s)
  emcmake cmake -G "Unix Makefiles" "$S" -DCMAKE_BUILD_TYPE=Release \
    -Dminimal=ON -Dimt=OFF -Druntime_cxxmodules=OFF -Dclad=OFF -Dfail-on-missing=OFF \
    -Dbuiltin_zlib=ON -Dbuiltin_lzma=ON -Dbuiltin_lz4=ON -Dbuiltin_zstd=ON \
    -Dbuiltin_xxhash=ON -Dbuiltin_pcre=ON -Dbuiltin_nlohmannjson=ON -Dbuiltin_freetype=ON \
    -DROOT_HOST_ROOTCLING="$HOST_ROOTCLING" > "$X/configure.log" 2>&1
  echo "exit=$? seconds=$(($(date +%s)-start))" | tee -a "$X/configure.log"
fi

if [[ $step == graph || $step == all ]]; then
  # Recursive closure of Core/all in the generated Makefile2.
  python3 - "$B/CMakeFiles/Makefile2" > "$X/core-graph.txt" <<'EOF'
import re, sys
deps = {}
for m in re.finditer(r'^(\S+/all): (.*)$', open(sys.argv[1]).read(), re.M):
    deps.setdefault(m.group(1), []).extend(d for d in m.group(2).split() if d.endswith('/all'))
root = next(k for k in deps if re.fullmatch(r'core/CMakeFiles/Core\.dir/all', k))
seen, todo = set(), [root]
while todo:
    t = todo.pop()
    if t in seen: continue
    seen.add(t); todo += deps.get(t, [])
print("direct:", *deps[root], sep="\n  ")
print("closure (%d):" % len(seen), *sorted(seen), sep="\n  ")
bad = [t for t in seen if re.search(r'interpreter/|CLING|rootcling|/Cling\.dir|llvm|clang', t, re.I)]
print("FORBIDDEN:", *bad if bad else ["none"], sep="\n  ")
EOF
  cat "$X/core-graph.txt" | sed -n '/FORBIDDEN/,$p'
  grep -n "rootcling" "$B/core/CMakeFiles/G__Core.dir/build.make" | head -3 > "$X/g__core-command.txt"
fi

if [[ $step == build || $step == all ]]; then
  cd "$B"; start=$(date +%s)
  [[ -f $X/build.log ]] && mv "$X/build.log" "$X/build.$(date +%s).log"
  timeout ${BUILD_TIMEOUT:-4800} cmake --build . --target Core -j4 > "$X/build.log" 2>&1
  echo "exit=$? seconds=$(($(date +%s)-start))" | tee -a "$X/build.log"
fi

if [[ $step == diag-libcxx ]]; then
  # Diagnostic only (not part of the build): rerun the generated G__Core rootcling command
  # with the Emscripten libc++ instead of the host C++ stdlib. Writes to $X/diag-libcxx.
  D=$X/diag-libcxx; rm -rf "$D"; mkdir -p "$D"; cd "$D"
  sed -n '/rootcling -rootbuild/p' "$B/core/CMakeFiles/G__Core.dir/build.make" | head -1 |
    sed "s|^\s*cd $B/core && ||; s|-s $B/lib/libCore.so|-s $D/libCore.so|; s|-rmf $B/lib/libCore.rootmap|-rmf $D/libCore.rootmap|" > cmd.sh
  EXTRA_CLING_ARGS="-nostdinc++ -isystem $EMSDK/upstream/emscripten/cache/sysroot/include/c++/v1" bash cmd.sh > gen.log 2>&1
  echo "rootcling exit=$?" | tee -a gen.log
fi

if [[ $step == inspect || $step == all ]]; then
  cd "$B"; NM=$EMSDK/upstream/bin/llvm-nm
  lib=$(find lib core -maxdepth 2 -name 'libCore*' \( -name '*.a' -o -name '*.so' -o -name '*.wasm' \) | head -1)
  { echo "artifact: $lib"; ls -l "$lib"; file "$lib"
    for s in TROOT::InitInterpreter TObject::Class 'TVersionCheck::TVersionCheck(int)' getrandom G__Core; do
      echo "== $s"; $NM -C "$lib" 2>/dev/null | grep -F "$s" | head -5; done
    echo "== archive members matching G__"; (llvm-ar t "$lib" 2>/dev/null || $EMSDK/upstream/bin/llvm-ar t "$lib") | grep G__
  } > "$X/inspect.txt" 2>&1
  cat "$X/inspect.txt"
fi
