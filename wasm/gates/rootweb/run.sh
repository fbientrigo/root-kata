#!/usr/bin/env bash
# M2b: genuine ROOT 6.40.04 running in a real browser.
#
# Loads ROOT's own wasm libraries (built by ROOT's own CMake targets, see
# wasm/gates/p0deps/xbuild) as Emscripten side modules inside the pinned
# xeus-cpp-lite / CppInterOp kernel from G7, and executes typed C++ against
# them -- served over plain static HTTP with no COOP/COEP, matching the real
# GitHub Pages target.
#
# Usage: run.sh [payload|serve|drive|cell|all]   (default all)
#   payload    stage the web root under wasm/build/rootweb/web
#   serve      stage, then serve it and print the URL to open (interactive; blocks)
#   drive      drive headless Chromium over the staged web root and assert the gate
#   cell FILE  stage FILE as the cell, run it once in Chromium, and write what it
#              printed to wasm/build/rootweb/cell_stdout.txt (no gate assertions).
#              This is the reusable browser runner other gates build on.
#   all        payload + drive
#
# Prints "rootweb M2b PASS" / exit 0, or "rootweb M2b FAIL: <reason>" / non-zero.
set -uo pipefail

HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd -P)"
REPO="$(cd -- "$HERE/../../.." >/dev/null 2>&1 && pwd -P)"
G7="$REPO/wasm/gates/g7"
ROOTLIGHT="$REPO/wasm/gates/rootlight"
BUILD="${BUILD:-$REPO/wasm/build/rootweb}"
WEB="$BUILD/web"
R="${ROOTSYS_STAGE:-$HOME/.cache/rootwasm-p0/rootlight/rootsys}"
LIBS=(Core Thread RIO MathCore Matrix Hist)
DONE_TITLE="ROOTWEB-DONE"
TIMEOUT_MS="${TIMEOUT_MS:-300000}"

step="${1:-all}"
[[ $step == cell ]] && CELL_SRC="${2:?usage: run.sh cell <file.cxx>}"

# $WEB and the captured cell output are shared mutable state: two runs at once
# silently mix one run's payload with another's stdout. Serialise them.
mkdir -p "$BUILD"
exec {lockfd}> "$BUILD/.lock"
if ! flock -w 3600 "$lockfd"; then
  echo "rootweb M2b FAIL: another rootweb run holds $BUILD/.lock" >&2
  exit 1
fi
fail() { echo "rootweb M2b FAIL: $*" >&2; exit 1; }

# Re-staging copies ~124 MB per call. A caller running many cells in a row
# (wasm/gates/rootkatas) can set ROOTWEB_REUSE=1 to keep an already-staged web
# root and only swap the cell, which is also what keeps it independent of
# another gate rebuilding the shared $ROOTSYS underneath it.
reuse=0
if [[ ${ROOTWEB_REUSE:-0} == 1 && -f $WEB/index.html && -f $WEB/rootsys.js && -f $WEB/xcpp.wasm ]]; then
  reuse=1
fi

if [[ $reuse == 1 && $step == cell ]]; then
  python3 "$HERE/build_cells.py" "$CELL_SRC" "$WEB/cells.js" "$HERE/welcome.cxx" \
    || fail "cell packaging failed"
elif [[ $step == payload || $step == serve || $step == all || $step == cell ]]; then
  [[ -d $R/include && -d $R/etc ]] \
    || fail "no staged ROOTSYS at $R -- run: bash wasm/gates/rootlight/run.sh stage"
  for l in "${LIBS[@]}"; do
    [[ -f $R/lib/lib$l.so ]] || fail "missing side module $R/lib/lib$l.so (run rootlight link)"
  done

  XCPP="$(bash "$G7/fetch-xcpp-toolchain.sh" | tail -1)" \
    || fail "could not fetch the pinned xeus-cpp-lite toolchain"
  for f in xcpp.js xcpp.wasm xcpp.data libxeus.so libclangCppInterOp.so; do
    [[ -f $XCPP/$f ]] || fail "missing staged toolchain file: $f"
  done

  rm -rf "$WEB"; mkdir -p "$WEB"
  cp "$XCPP"/{xcpp.js,xcpp.wasm,xcpp.data,libxeus.so,libclangCppInterOp.so} "$WEB/"
  for l in "${LIBS[@]}"; do cp "$R/lib/lib$l.so" "$WEB/"; done

  # ROOT's own static-ROOT marker, compiled unmodified from ROOT's source.
  # TROOT::InitInterpreter (core/base/src/TROOT.cxx:2227-2247) looks this symbol
  # up with dlsym(RTLD_DEFAULT, ...): when it is present, ROOT knows its
  # libraries are already linked into the process and resolves CreateInterpreter
  # through the global symbol table instead of dlopen'ing libRIO and libCling by
  # path. That is exactly this process: the six libraries are already loaded.
  # Without it ROOT dlopens a *second* copy of libRIO, which in wasm fails with
  # "function signature mismatch". PLATFORM PORT: ROOT's own supported path.
  . "$REPO/wasm/toolchain/root-src.env"
  ROOT_SRC="${ROOT_WASM_TOOLS:-$HOME/.root-kata-wasm}/src/root-${ROOT_VERSION}"
  ROOTA="$ROOT_SRC/core/base/src/roota.cxx"
  [[ -f $ROOTA ]] || fail "missing ROOT's own roota.cxx at $ROOTA"
  if [[ ! -f $BUILD/libroota.so || $ROOTA -nt $BUILD/libroota.so ]]; then
    . "$REPO/wasm/toolchain/activate.sh" >/dev/null 2>&1 || fail "could not activate pinned Emscripten"
    mkdir -p "$BUILD"
    em++ -fwasm-exceptions -O2 -sSIDE_MODULE=1 "$ROOTA" -o "$BUILD/libroota.so" \
      || fail "could not build ROOT's roota.cxx as a side module"
  fi
  cp "$BUILD/libroota.so" "$WEB/"

  # M3: the real interpreter plugin, when it has been built. Its presence is what
  # flips createinterpreter= from 0 to 1.
  INTERP="${INTERP_STAGE:-$HOME/.cache/rootwasm-p0/interpreter}/libCling.so"
  if [[ -f $INTERP ]]; then
    cp "$INTERP" "$WEB/"
    echo "    staging the M3 interpreter: $INTERP"
  fi
  cp "$HERE/page/index.html" "$HERE/page/kernel-worker.js" "$WEB/"

  # The interp-probe's stub libCling is diagnostic-only and must never be served.
  # The genuine plugin is the one built from wasm/rootlight/interpreter.
  if [[ -e $WEB/libCling.so ]]; then
    # grep -q would SIGPIPE llvm-nm and, under pipefail, fail on a match.
    n_sym=$("${EMSDK:-$HOME/.root-kata-wasm/emsdk}/upstream/bin/llvm-nm" --defined-only \
      "$WEB/libCling.so" 2>/dev/null | grep -c TCppInterOpInterpreter)
    [[ ${n_sym:-0} -ge 1 ]] \
      || fail "refusing to serve a libCling.so that is not the TCppInterOpInterpreter plugin"
  fi

  python3 "$HERE/build_rootsys.py" "$R" "$WEB/rootsys.js" || fail "rootsys packaging failed"
  python3 "$HERE/build_cells.py" "${CELL_SRC:-$HERE/boundary.cxx}" "$WEB/cells.js" "$HERE/welcome.cxx" || fail "cell packaging failed"

  total=0
  for f in "$WEB"/*; do total=$((total + $(stat -c '%s' "$f"))); done
  echo "    staged $WEB: $(ls "$WEB" | wc -l) files, $total bytes"
fi

serve_web() {  # sets $port, $server_pid
  port="$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1]); s.close()')"
  (cd "$WEB" && exec python3 -m http.server "$port" --bind 127.0.0.1) > "$BUILD/http_server.log" 2>&1 &
  server_pid=$!
  for _ in $(seq 1 50); do
    curl -s -o /dev/null "http://127.0.0.1:$port/index.html" && return 0
    sleep 0.1
  done
  return 1
}

if [[ $step == serve ]]; then
  serve_web || fail "local HTTP server did not come up"
  trap 'kill $server_pid 2>/dev/null' EXIT
  echo
  echo "    ROOT (wasm) is being served. Open:"
  echo "        http://127.0.0.1:$port/"
  echo "    Type C++ with a main(), press Run. Ctrl-C to stop."
  echo
  wait $server_pid
  exit 0
fi

if [[ $step == cell ]]; then
  command -v node >/dev/null || fail "node not found"
  serve_web || fail "local HTTP server did not come up"
  trap 'kill $server_pid 2>/dev/null' EXIT
  node "$G7/drive.mjs" "http://127.0.0.1:$port/index.html?auto=1&variant=good${DRIVE_EXTRA:-}" \
    "$DONE_TITLE" "$TIMEOUT_MS" "$BUILD/chrome-profile-cell" \
    > "$BUILD/cell.json" 2> "$BUILD/cell.log" \
    || { tail -20 "$BUILD/cell.log" >&2; fail "browser driver failed"; }
  python3 -c '
import json, sys
build = sys.argv[1]
with open(build + "/cell.json", encoding="utf-8") as f:
    r = json.load(f)
if r["timedOut"]:
    sys.exit("    cell did not finish within the timeout")
open(build + "/cell_stdout.txt", "w", encoding="utf-8").write(r.get("output") or "")
open(build + "/cell_diag.txt", "w", encoding="utf-8").write(r.get("diag") or "")
' "$BUILD" || fail "the cell did not run"
  echo "    stdout -> $BUILD/cell_stdout.txt, diagnostics -> $BUILD/cell_diag.txt"
  exit 0
fi

if [[ $step == drive || $step == all ]]; then
  command -v node >/dev/null || fail "node not found"
  command -v "${CHROMIUM_BIN:-chromium}" >/dev/null || fail "chromium not found (set CHROMIUM_BIN)"
  [[ -f $WEB/index.html ]] || fail "no staged web root -- run: $0 payload"

  serve_web || fail "local HTTP server did not come up"
  trap 'kill $server_pid 2>/dev/null' EXIT

  for v in ${VARIANTS:-good broken}; do
    node "$G7/drive.mjs" "http://127.0.0.1:$port/index.html?auto=1&variant=$v${DRIVE_EXTRA:-}" \
      "$DONE_TITLE" "$TIMEOUT_MS" "$BUILD/chrome-profile-$v" \
      > "$BUILD/$v.json" 2> "$BUILD/$v.log" \
      || { tail -20 "$BUILD/$v.log" >&2; fail "browser driver failed on the $v payload"; }
  done

  python3 - "$BUILD" "$ROOTLIGHT/expected.txt" "$HERE/expected.txt" <<'PY' || fail "gate assertions failed (see above)"
import json, re, sys
build, node_expected_path, expected_path = sys.argv[1], sys.argv[2], sys.argv[3]
node_expected = open(node_expected_path, encoding="utf-8").read()
expected = open(expected_path, encoding="utf-8").read()

def load(v):
    with open(f"{build}/{v}.json", encoding="utf-8") as f:
        return json.load(f)

def die(msg, r=None):
    print(f"    {msg}", file=sys.stderr)
    if r is not None:
        print("    trace tail:\n" + "\n".join((r.get("trace") or "").splitlines()[-25:]), file=sys.stderr)
    sys.exit(1)

good = load("good")
if good["timedOut"]:
    die("good run did not reach the done sentinel within the timeout", good)

out, diag = good.get("output") or "", good.get("diag") or ""
open(f"{build}/good_stdout.txt", "w", encoding="utf-8").write(out)
open(f"{build}/good_diag.txt", "w", encoding="utf-8").write(diag)

# 1. the same genuine ROOT output the Node M2 gate asserts, byte for byte
head = "".join(out.splitlines(keepends=True)[:5])
if head != node_expected:
    die(f"stdout differs from the Node M2 gate\n      expected: {node_expected!r}\n      got:      {head!r}", good)

# 2. plus this gate's own expectation, including ROOT's static-ROOT decision
head6 = "".join(out.splitlines(keepends=True)[:6])
if head6 != expected:
    die(f"stdout mismatch\n      expected: {expected!r}\n      got:      {head6!r}", good)

# 3. exactly one instance of each ROOT library
if "already in TClassTable" in out + diag:
    die("duplicate dictionary registration: a ROOT library was instantiated twice", good)

# 4. the interpreter decision TROOT::InitInterpreter makes is observable.
#    0 before M3 supplies CreateInterpreter, 1 after; both are a valid M2b.
m = re.search(r"^createinterpreter=([01])$", out, re.M)
if not m:
    die(f"no createinterpreter evidence line in stdout: {out!r}", good)
print(f"    CreateInterpreter resolvable through RTLD_DEFAULT: {m.group(1)}")

# 5. falsifiability: the same harness must be able to fail
broken = load("broken")
if broken["timedOut"]:
    die("broken run did not reach the done sentinel within the timeout", broken)
bout, bdiag = broken.get("output") or "", broken.get("diag") or ""
if bout.strip():
    die(f"broken payload produced stdout instead of failing: {bout!r}", broken)
if "printfXX" not in bdiag:
    die(f"broken payload did not surface a genuine compiler diagnostic; diag was {bdiag!r}", broken)

print("    good: genuine ROOT output matches expected.txt, one DSO per library")
print("    broken: genuine compiler diagnostic, no stdout (falsifiability check passed)")
PY

  echo "rootweb M2b PASS"
  exit 0
fi
