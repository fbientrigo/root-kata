#!/usr/bin/env bash
# Reproduces every run in FINDINGS.md. Outputs: ~/.cache/rootwasm-p0/runtime/<root>/
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=${OUT:-$HOME/.cache/rootwasm-p0/runtime}
declare -A ROOTS=(
  [r640]=/home/fabian/thesis/FairShip/.pixi/envs/default         # conda-forge 6.40.02 (primary)
  [r634]=/home/fabian/.cache/rootwasm-th1d/root-host             # CERN 6.34.10 (cross-check)
)
mkdir -p "$OUT"
gcc -shared -fPIC -O1 -o "$OUT/shim.so" "$HERE/shim.c" -ldl || exit 1

for tag in r640 r634; do
  R=${ROOTS[$tag]}; D=$OUT/$tag; mkdir -p "$D"; cd "$D" || exit 1
  CF=$("$R/bin/root-config" --cflags)
  LINK="-L$R/lib -Wl,-rpath,$R/lib -lHist -lCore"   # minimal: -lHist alone fails (DSO missing: libCore, _ZN7TObjectdlEPv)
  g++ $CF -o p0          "$HERE/p0.cxx"      $LINK || exit 1
  g++ $CF -DP0_NO_ADD_DIRECTORY -o p0_noadddir "$HERE/p0.cxx" $LINK || exit 1
  g++ $CF -o control     "$HERE/control.cxx" $LINK || exit 1
  printf '#include "TH1D.h"\nint main(){return 0;}\n' > static_init.cxx
  g++ $CF -o static_init static_init.cxx -Wl,--no-as-needed $LINK || exit 1
  { echo "# p0 NEEDED"; readelf -d p0 | grep NEEDED; echo "# libHist NEEDED"; readelf -d "$R/lib/libHist.so" | grep NEEDED; } > needed.txt

  run() {  # name, env..., -- , binary
    local name=$1; shift; local envs=(); while [ "$1" != "--" ]; do envs+=("$1"); shift; done; shift
    rm -f "$name.maps"; env "${envs[@]}" P0_MAPS="$D/$name.maps" LD_PRELOAD="$OUT/shim.so" "./$1" >"$name.out" 2>"$name.err"
    local rc=$?
    local req; req=$(grep -c 'dlopen(.*libCling' "$name.err")
    local den; den=$(grep -c 'libCling.*DENIED' "$name.err")
    local map=n/a; [ -f "$name.maps" ] && map=$(grep -c libCling "$name.maps")
    local ref=${2:-}; local d=same; cmp -s "$ref" "$name.out" 2>/dev/null || d=DIFF
    printf '%-6s %-22s rc=%-3s libCling_dlopen=%s denied=%s mapped_at_end=%s out_vs_ref=%s\n' "$tag" "$name" "$rc" "$req" "$den" "$map" "${ref:+$d}"
    c++filt < "$name.err" > "$name.err.demangled"
  }
  run A            -- p0
  run B            P0_DENY=libCling -- p0 A.out
  run D_A          -- p0_noadddir A.out
  run D_B          P0_DENY=libCling -- p0_noadddir A.out
  run E1           P0_DENY=libCling P0_AUTOREG=1 -- p0 A.out
  run E0           P0_DENY=libCling P0_AUTOREG=0 -- p0 A.out
  run C_nodeny     -- control
  run C_deny       P0_DENY=libCling -- control C_nodeny.out
  run C_deny_autoreg P0_DENY=libCling P0_AUTOREG=1 -- control C_nodeny.out
  run static_init_deny P0_DENY=libCling -- static_init
  for n in B D_A D_B E1 E0; do diff A.out $n.out > A_vs_$n.diff; done
  for n in C_deny C_deny_autoreg; do diff C_nodeny.out $n.out > C_nodeny_vs_$n.diff; done
  cd "$OUT"
done
cmp -s r640/A.out r634/A.out && echo "r640 A.out == r634 A.out (byte-identical)"
