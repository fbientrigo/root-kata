#!/usr/bin/env bash
# Gate G7 canonical reproduction (narrowed hypothesis H1: xeus-cpp-lite / CppInterOp).
#
# Claim: a prebuilt, already-existing in-browser C++ toolchain (xeus-cpp-lite,
# built on CppInterOp/clang-repl) can compile the genuine ROOT C++ program
# wasm/gates/g2/genvector.cpp (unmodified) entirely client-side in headless
# Chromium -- no server-side compilation, no SharedArrayBuffer/pthreads -- and
# produce output that byte-for-byte matches wasm/gates/g2/expected.txt. A
# deliberately-broken variant of the same payload must fail with a genuine
# compiler diagnostic (falsifiability check).
#
# From a clean checkout, with no arguments, this script:
#   a. activates the pinned Emscripten toolchain and the pinned ROOT source
#      (both reused read-only from wasm/toolchain/, never modified)
#   b. fetches + sha256-verifies the pinned xeus-cpp-lite/CppInterOp wasm
#      conda packages (see xcpp-toolchain.env), cached under $ROOT_WASM_TOOLS
#   c. generates RConfigure.h the same way G2 does (CMake configure_file on
#      ROOT's own config/RConfigure.in), probed against the pinned em++ --
#      testing whether a Clang-based in-browser compiler accepts it unmodified
#   d. packages the ROOT header subtrees + RConfigure.h, and the genvector.cpp
#      payload (good + a deliberately-broken variant), into small JS files
#   e. stages a static web root and serves it over a short-lived local
#      python http.server (no API routes, no COOP/COEP headers -- matching
#      the real GitHub Pages deployment target)
#   f. drives headless Chromium via wasm/gates/g7/drive.mjs (a real-wall-clock
#      Chrome DevTools Protocol driver -- see that file for why this gate
#      cannot reuse wasm/gates/common/run-wasm-program.sh's
#      --virtual-time-budget/--dump-dom pattern) for both the good and the
#      deliberately-broken payload
#   g. diffs the good run's captured stdout against wasm/gates/g7/expected.txt,
#      and asserts the broken run produced a real compiler diagnostic and no
#      stdout
#   h. prints "G7 PASS"/exit 0, or "G7 FAIL: <reason>"/exit non-zero
#
# All build artifacts land in wasm/build/g7/ (gitignored). Downloaded toolchain
# binaries are cached outside the repo under $ROOT_WASM_TOOLS (never committed).
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd -P)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." >/dev/null 2>&1 && pwd -P)"
TOOLCHAIN_DIR="${REPO_ROOT}/wasm/toolchain"
G2_DIR="${REPO_ROOT}/wasm/gates/g2"
BUILD_DIR="${REPO_ROOT}/wasm/build/g7"
EXPECTED_FILE="${SCRIPT_DIR}/expected.txt"

gate_fail() {
  echo "G7 FAIL: $*" >&2
  exit 1
}

echo "==> [a] activating pinned Emscripten and ROOT source"
bash "${TOOLCHAIN_DIR}/fetch-root-src.sh" || gate_fail "could not fetch verified ROOT source"
# shellcheck source=../../toolchain/root-src.env
. "${TOOLCHAIN_DIR}/root-src.env"
ROOT_SOURCE="${ROOT_WASM_TOOLS:-$HOME/.root-kata-wasm}/src/root-${ROOT_VERSION}"
if ! . "${TOOLCHAIN_DIR}/activate.sh"; then
  gate_fail "could not activate pinned Emscripten"
fi
command -v em++ >/dev/null 2>&1 || gate_fail "em++ not on PATH"
command -v cmake >/dev/null 2>&1 || gate_fail "cmake not found"
command -v node >/dev/null 2>&1 || gate_fail "node not found"
command -v chromium >/dev/null 2>&1 || gate_fail "chromium not found"
command -v python3 >/dev/null 2>&1 || gate_fail "python3 not found"

echo "==> [b] fetching pinned xeus-cpp-lite / CppInterOp wasm toolchain"
XCPP_STAGE_DIR="$(bash "${SCRIPT_DIR}/fetch-xcpp-toolchain.sh" | tail -1)" \
  || gate_fail "could not fetch xeus-cpp-lite wasm toolchain"
for f in xcpp.js xcpp.wasm xcpp.data libxeus.so libclangCppInterOp.so; do
  [ -f "${XCPP_STAGE_DIR}/${f}" ] || gate_fail "missing staged toolchain file: ${f}"
done

echo "==> [c] generating RConfigure.h against the pinned em++ (same template G2 uses)"
rm -rf "${BUILD_DIR}"
mkdir -p "${BUILD_DIR}/web" "${BUILD_DIR}/web-broken-check"
cmake -DROOT_SOURCE="${ROOT_SOURCE}" -DOUTPUT_HEADER="${BUILD_DIR}/RConfigure.h" \
  -DCXX="$(command -v em++)" -P "${G2_DIR}/rconfigure.cmake" \
  || gate_fail "RConfigure.h generation against em++ failed"
[ -s "${BUILD_DIR}/RConfigure.h" ] || gate_fail "RConfigure.h generation produced an empty file"
grep -q "R__HAS_ATTRIBUTE_ALWAYS_INLINE" "${BUILD_DIR}/RConfigure.h" \
  || gate_fail "RConfigure.h missing expected probed macro (R__HAS_ATTRIBUTE_ALWAYS_INLINE)"
echo "    RConfigure.h generated unmodified from ROOT's own config/RConfigure.in via em++'s probes"

echo "==> [d] packaging ROOT headers and the genvector.cpp payload for the browser"
python3 "${SCRIPT_DIR}/build_headers.py" "${ROOT_SOURCE}" "${BUILD_DIR}/RConfigure.h" "${BUILD_DIR}/web/headers.js" \
  || gate_fail "header packaging failed"
python3 "${SCRIPT_DIR}/build_payload.py" "${G2_DIR}/genvector.cpp" "${BUILD_DIR}/web/payload.js" \
  || gate_fail "payload packaging failed"

cp "${XCPP_STAGE_DIR}/xcpp.js" "${XCPP_STAGE_DIR}/xcpp.wasm" "${XCPP_STAGE_DIR}/xcpp.data" \
   "${XCPP_STAGE_DIR}/libxeus.so" "${XCPP_STAGE_DIR}/libclangCppInterOp.so" "${BUILD_DIR}/web/"
cp "${SCRIPT_DIR}/page/index.html" "${BUILD_DIR}/web/index.html"

echo "==> [e] serving the static web root and driving headless Chromium"
port="$(python3 -c 'import socket
s = socket.socket()
s.bind(("127.0.0.1", 0))
print(s.getsockname()[1])
s.close()')"
(cd "${BUILD_DIR}/web" && exec python3 -m http.server "${port}" --bind 127.0.0.1) \
  > "${BUILD_DIR}/http_server.log" 2>&1 &
server_pid=$!
cleanup_g7() { kill "${server_pid}" >/dev/null 2>&1 || true; wait "${server_pid}" 2>/dev/null || true; }
trap cleanup_g7 EXIT

ready=0
for _ in $(seq 1 50); do
  if curl -s -o /dev/null "http://127.0.0.1:${port}/index.html"; then
    ready=1
    break
  fi
  sleep 0.1
done
[ "${ready}" -eq 1 ] || gate_fail "local HTTP server on port ${port} did not come up"

PAYLOAD_BYTES=0
for f in xcpp.js xcpp.wasm xcpp.data libxeus.so libclangCppInterOp.so headers.js payload.js index.html; do
  sz="$(stat -c '%s' "${BUILD_DIR}/web/${f}")"
  PAYLOAD_BYTES=$((PAYLOAD_BYTES + sz))
done
echo "    total toolchain+page payload: ${PAYLOAD_BYTES} bytes"

echo "==> [f] driving the good payload"
good_start_ms="$(date +%s%3N)"
node "${SCRIPT_DIR}/drive.mjs" "http://127.0.0.1:${port}/index.html?variant=good" "G7-DONE" 180000 \
  "${BUILD_DIR}/chrome-profile-good" > "${BUILD_DIR}/good_result.json" 2> "${BUILD_DIR}/good_drive.log" \
  || { cat "${BUILD_DIR}/good_drive.log" >&2; gate_fail "browser driver failed on the good payload"; }
good_end_ms="$(date +%s%3N)"

if ! python3 - "${BUILD_DIR}/good_result.json" "${BUILD_DIR}" <<'PY'
import json
import sys

result_path, build_dir = sys.argv[1], sys.argv[2]
with open(result_path, encoding="utf-8") as f:
    result = json.load(f)

if result["timedOut"]:
    print("good-payload run did not reach G7-DONE within the timeout", file=sys.stderr)
    print(result.get("trace", ""), file=sys.stderr)
    sys.exit(1)

with open(f"{build_dir}/good_stdout.txt", "w", encoding="utf-8") as f:
    f.write(result["output"] or "")
PY
then
  gate_fail "good-payload run did not complete (see above)"
fi

if ! diff -u "${EXPECTED_FILE}" "${BUILD_DIR}/good_stdout.txt" > "${BUILD_DIR}/good_vs_expected.diff"; then
  cat "${BUILD_DIR}/good_vs_expected.diff" >&2
  gate_fail "in-browser compiled genvector.cpp output does not match expected.txt"
fi
echo "    good payload: stdout matches expected.txt byte-for-byte"
echo "    good payload wall-clock: $(( good_end_ms - good_start_ms )) ms (page load through first correct output)"

echo "==> [g] driving the deliberately-broken payload (falsifiability check)"
node "${SCRIPT_DIR}/drive.mjs" "http://127.0.0.1:${port}/index.html?variant=broken" "G7-DONE" 180000 \
  "${BUILD_DIR}/chrome-profile-broken" > "${BUILD_DIR}/broken_result.json" 2> "${BUILD_DIR}/broken_drive.log" \
  || { cat "${BUILD_DIR}/broken_drive.log" >&2; gate_fail "browser driver failed on the broken payload"; }

if ! python3 - "${BUILD_DIR}/broken_result.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as f:
    result = json.load(f)

if result["timedOut"]:
    print("broken-payload run did not reach G7-DONE within the timeout", file=sys.stderr)
    sys.exit(1)

stdout = result.get("output") or ""
diag = result.get("diag") or ""

if stdout.strip():
    print(f"broken payload produced stdout instead of failing: {stdout!r}", file=sys.stderr)
    sys.exit(1)

if "printfXX" not in diag:
    print("broken payload did not surface the expected genuine compiler diagnostic", file=sys.stderr)
    print(f"diag was: {diag!r}", file=sys.stderr)
    sys.exit(1)
PY
then
  gate_fail "falsifiability check failed (see above)"
fi
echo "    broken payload: produced a genuine compiler diagnostic, no stdout (falsifiability check passed)"

echo "G7 PASS"
exit 0
