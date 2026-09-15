#!/usr/bin/env bash
# Tiny native runtime check: does a P0 TH1D ctor dlopen libCling? (ROOT 6.40.02 pixi env)
set -euo pipefail
E=${ROOTENV:-/home/fabian/thesis/FairShip/.pixi/envs/default}
H=$(cd "$(dirname "$0")" && pwd); D=${OUT:-$HOME/.cache/rootwasm-p0/targets/native-dlopen}; mkdir -p "$D"
g++ -std=c++23 -I"$E/include" "$H/p0.cxx" -o "$D/p0" -Wl,--no-as-needed -L"$E/lib" -lHist -lCore -Wl,-rpath,"$E/lib"
gcc -shared -fPIC "$H/shim.c" -o "$D/shim.so"
out=$(LD_PRELOAD="$D/shim.so" "$D/p0" 2>&1)
grep -E 'MARK|_Z|entries' <<<"$out" | sed 's/.*(\(_Z[^+]*\).*/\1/' | c++filt
grep -q '_ZN5TROOT15InitInterpreterEv' <<<"$out" && echo "RESULT: TH1D ctor reaches TROOT::InitInterpreter -> dlopen(libCling)"
