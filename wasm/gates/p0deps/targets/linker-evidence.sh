#!/usr/bin/env bash
# Linker evidence (not dependency discovery): for lib$1, count its undefined dynamic
# symbols that each NEEDED ROOT lib DEFINES. "strong" = defined with T/D/B/R in that lib
# (its own code); "any" also counts weak/unique (W/V/u: inline/template copies).
# Usage: linker-evidence.sh Hist [Matrix]   # 2nd arg: print demangled strong hits from that lib
set -euo pipefail
L=${ROOTLIB:-/home/fabian/thesis/FairShip/.pixi/envs/default/lib}
lib=${1:-Hist}; show=${2:-}
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
nm -D --undefined-only "$L/lib$lib.so" | awk '{print $NF}' | sort -u > "$T/undef"
cp "$T/undef" "$T/unres"
printf '%-18s %6s %6s\n' NEEDED strong any
for n in $(readelf -d "$L/lib$lib.so" | sed -n 's/.*NEEDED.*\[\(lib\(Core\|Thread\|RIO\|MathCore\|Matrix\|Imt\|MultiProc\|Cling\|tbb\)\.so[.0-9]*\)\].*/\1/p'); do
  nm -D --defined-only "$L/$n" | awk '{print $NF}' | sort -u > "$T/any"
  nm -D --defined-only "$L/$n" | awk '$2 ~ /^[TDBR]$/ {print $NF}' | sort -u > "$T/strong"
  comm -12 "$T/undef" "$T/strong" > "$T/hs"
  printf '%-18s %6d %6d\n' "$n" "$(wc -l < "$T/hs")" "$(comm -12 "$T/undef" "$T/any" | wc -l)"
  comm -23 "$T/unres" "$T/any" > "$T/u2"; mv "$T/u2" "$T/unres"
  if [ -n "$show" ] && [[ $n == lib$show.so* ]]; then c++filt < "$T/hs" | sed 's/^/    /'; fi
done
printf '%-18s %6s %6d\n' "(not ROOT)" - "$(wc -l < "$T/unres")"
