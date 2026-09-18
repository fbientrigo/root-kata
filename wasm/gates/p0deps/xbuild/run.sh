#!/usr/bin/env bash
# M1: ROOT-owned Hist closure under Emscripten with a host rootcling.
# Usage: run.sh [configure|graph|build|hist|inspect|all|diag-libcxx]   (default: all)
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
X=${X:-$HOME/.cache/rootwasm-p0/xbuild}
PIN=$HOME/.root-kata-wasm/src/root-6.40.04
S=$X/src B=$X/build
# Pinned host generator: official CERN ROOT 6.40.04 binary release (same version as the source).
# root.cern publishes no .sha256 for it; this is the locally verified (gzip -t) tarball hash.
HOST_TARBALL=root_v6.40.04.Linux-debian13-x86_64-gcc14.2.tar.gz
HOST_SHA256=287ff87deef0eed0fedd32e7d59bdadd22dcb45a5c592c9e08d8d140212ef261
if [[ -z ${HOST_ROOTCLING:-} ]]; then
  HOST_ROOTCLING=$X/root-6.40.04-host/root/bin/rootcling
  if [[ ! -x $HOST_ROOTCLING ]]; then
    mkdir -p "$X"; cd "$X"
    until curl -sS -L -C - --retry 5 -o "$HOST_TARBALL" "https://root.cern/download/$HOST_TARBALL"; do sleep 5; done
    echo "$HOST_SHA256  $HOST_TARBALL" | sha256sum -c - || { echo "host ROOT tarball hash mismatch"; exit 1; }
    mkdir -p root-6.40.04-host && tar -xzf "$HOST_TARBALL" -C root-6.40.04-host
  fi
fi
source ~/.root-kata-wasm/emsdk/emsdk_env.sh >/dev/null 2>&1
# Target frontend for the host generator: mirrors em++ (target, sysroot, -DEMSCRIPTEN, include order)
# plus the generator-only stdlib.h overlay (../dictprobe/overlay). See ../dictprobe/FINDINGS.md.
SYSROOT=$EMSDK/upstream/emscripten/cache/sysroot
HOST_CLING_ARGS="-std=c++17 --target=wasm32-unknown-emscripten --sysroot=$SYSROOT -DEMSCRIPTEN -fignore-exceptions -nostdinc -nostdinc++ -isystem $SYSROOT/include/fakesdl -isystem $SYSROOT/include/compat -isystem $SYSROOT/include/c++/v1 -isystem $EMSDK/upstream/lib/clang/21/include -isystem $HERE/../dictprobe/overlay -isystem $SYSROOT/include"
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
    -DCMAKE_CXX_FLAGS=-fwasm-exceptions -DCMAKE_C_FLAGS=-fwasm-exceptions \
    -DROOT_HOST_ROOTCLING="$HOST_ROOTCLING" -DROOT_HOST_ROOTCLING_EXTRA_ARGS="$HOST_CLING_ARGS" > "$X/configure.log" 2>&1
  rc=$?; echo "exit=$rc seconds=$(($(date +%s)-start))" | tee -a "$X/configure.log"
  [[ $rc -eq 0 ]] || { echo "xbuild FAIL: configure"; exit "$rc"; }
fi

if [[ $step == graph || $step == all ]]; then
  # Recursive order closure of ROOT's Hist and Minuit2 targets in the generated Makefile2.
  # Minuit2 is not part of Hist's own closure (M4b needs it for TH1::Fit's minimizer plugin)
  # and must pass the same FORBIDDEN check independently.
  python3 - "$B/CMakeFiles/Makefile2" > "$X/hist-graph.txt" <<'EOF'
import re, sys
deps = {}
for m in re.finditer(r'^(\S+/all): (.*)$', open(sys.argv[1]).read(), re.M):
    deps.setdefault(m.group(1), []).extend(d for d in m.group(2).split() if d.endswith('/all'))
roots = [next(k for k in deps if re.fullmatch(pat, k)) for pat in
         (r'hist/hist/CMakeFiles/Hist\.dir/all', r'math/minuit2/CMakeFiles/Minuit2\.dir/all')]
bad_total = []
for root in roots:
    seen, todo = set(), [root]
    while todo:
        t = todo.pop()
        if t in seen: continue
        seen.add(t); todo += deps.get(t, [])
    print("root:", root)
    print("direct:", *deps[root], sep="\n  ")
    print("closure (%d):" % len(seen), *sorted(seen), sep="\n  ")
    bad = [t for t in seen if re.search(r'interpreter/|CLING|rootcling|/Cling\.dir|llvm|clang', t, re.I)]
    print("FORBIDDEN:", *bad if bad else ["none"], sep="\n  ")
    bad_total += bad
sys.exit(bool(bad_total))
EOF
  [[ $? -eq 0 ]] || { cat "$X/hist-graph.txt"; echo "xbuild FAIL: target graph"; exit 1; }
  cat "$X/hist-graph.txt" | sed -n '/FORBIDDEN/,$p'
  grep -n "rootcling" "$B/core/CMakeFiles/G__Core.dir/build.make" | head -3 > "$X/g__core-command.txt"
fi

if [[ $step == build || $step == hist || $step == all ]]; then
  # build: Core only (historical gate); hist: the Hist closure plus Minuit2
  # (Thread RIO MathCore Matrix Hist Minuit2) -- rootlight/run.sh stages both.
  targets=(Hist Minuit2); [[ $step == build ]] && targets=(Core)
  cd "$B"; start=$(date +%s)
  [[ -f $X/build.log ]] && mv "$X/build.log" "$X/build.$(date +%s).log"
  timeout ${BUILD_TIMEOUT:-4800} cmake --build . --target "${targets[@]}" -j${JOBS:-4} > "$X/build.log" 2>&1
  rc=$?; echo "exit=$rc seconds=$(($(date +%s)-start))" | tee -a "$X/build.log"
  [[ $rc -eq 0 ]] || { echo "xbuild FAIL: ${targets[*]} build"; exit "$rc"; }
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
  python3 - "$B" "$X/build.log" "$EMSDK/upstream/bin" > "$X/inspect.txt" 2>&1 <<'EOF'
from pathlib import Path
import subprocess, sys, tempfile

build, log, tools = map(Path, sys.argv[1:])
def run(tool, *args):
    return subprocess.check_output([str(tools / tool), *map(str, args)])

def check(condition, reason):
    if not condition:
        raise SystemExit("xbuild Hist FAIL: " + reason)

libs = ("Core", "Thread", "RIO", "MathCore", "Matrix", "Hist", "Minuit2")
symbols = {}
for lib in libs:
    path = build / "lib" / ("lib" + lib + ".so")
    check(path.read_bytes()[:4] == b"\0asm", str(path) + " is not wasm")
    print(path.name, path.stat().st_size, "WebAssembly")
    symbols[lib] = run("llvm-nm", "-C", path).decode()
# Each ROOT package must carry a dictionary definition, not just eight keys overall.
# Minuit2Minimizer itself has no compiled Class() (M4b confirmed it is constructed through
# interpreter reflection via TPluginManager, not a compiled dictionary) -- TMinuit2TraceObject
# is the one class in this library that does carry one.
for lib, symbol in zip(libs, ("TObject::Class()", "TThread::Class()", "TFile::Class()",
                              "TRandom::Class()", "TMatrixT<double>::Class()", "TH1D::Class()",
                              "TMinuit2TraceObject::Class()")):
    check(any(line.endswith(" T " + symbol) for line in symbols[lib].splitlines()),
          lib + ": missing dictionary " + symbol)
print("dict-libraries=7")
print("== dictionary / key symbols")
for symbol in ("TObject::Class()", "TVersionCheck::TVersionCheck(int)",
               "TROOT::InitInterpreter()", "TH1D::Class()",
               "TH1D::TH1D(char const*, char const*, int, double, double)",
               "TFormula::Class()", "TMatrixT<double>::Class()", "TFile::Class()"):
    count = sum(line.endswith(" T " + symbol)
                for output in symbols.values() for line in output.splitlines())
    print(count, symbol)
    check(count > 0, "missing defined " + symbol)
text = log.read_text()
check("Built target Hist" in text and "exit=0 " in text, "no successful Hist build log")
print("== non-wasm archive members skipped at link (must be 0)")
print(text.count("neither Wasm"))
check("neither Wasm" not in text, "link skipped non-wasm objects")
archives = sorted(build.rglob("*.a"))
check(bool(archives), "no builtin archives inspected")
member_count = 0
for archive in archives:
    members = run("llvm-ar", "t", archive).decode().splitlines()
    check(bool(members) and len(members) == len(set(members)),
          str(archive) + " has empty or duplicate member names")
    with tempfile.TemporaryDirectory() as directory:
        subprocess.run([str(tools / "llvm-ar"), "x", str(archive)], cwd=directory, check=True)
        for member in members:
            check((Path(directory) / member).read_bytes()[:4] == b"\0asm",
                  str(archive) + ": non-wasm " + member)
            member_count += 1
print("== builtin archive members that are not wasm (must be 0)\n0")
print("archive-count=%d member-count=%d" % (len(archives), member_count))
undefined = [line for line in run("llvm-nm", build / "lib/libCore.so").decode().splitlines()
             if any(" U " + prefix in line for prefix in
                    ("LZ4_", "ZSTD_", "lzma_", "inflate", "deflate", "pcre"))]
print("== undefined codec/regex symbols (must be 0)\n" + str(len(undefined)))
check(not undefined, "undefined codec/regex symbols")
flags = [p for area in ("core", "io", "math", "hist")
         for p in (build / area).rglob("flags.make")]
check(bool(flags), "no compile flags inspected")
pthread = [str(p) for p in flags if "-pthread" in p.read_text()]
print("== pthread in compile flags (must be 0)\n" + str(len(pthread)))
check(not pthread, "pthread compile flags: " + ", ".join(pthread))
print("xbuild Hist PASS")
EOF
  rc=$?; cat "$X/inspect.txt"
  [[ $rc -eq 0 ]] || { echo "xbuild Hist FAIL: inspect"; exit "$rc"; }
fi
