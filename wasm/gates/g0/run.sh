#!/usr/bin/env bash
# Gate G0 canonical reproduction: "reproducible Emscripten toolchain".
#
# From a clean checkout, with no arguments, this script:
#   a. activates the pinned Emscripten toolchain (wasm/toolchain/activate.sh)
#   b. compiles smoke.cpp to a Node-runnable smoke.js/.wasm AND a modularized
#      ES-module smoke.js/.wasm + a minimal HTML harness for the browser
#   c. runs the Node build and captures stdout
#   d. serves the web build over a short-lived local HTTP server and runs it
#      under headless Chromium, scraping the program's stdout out of the DOM
#   e. diffs Node output vs Chromium output vs the checked-in expected.txt
#   f. prints "G0 PASS"/exit 0, or "G0 FAIL: <reason>"/exit non-zero
#
# All build artifacts land in wasm/build/g0/ (gitignored), never next to sources.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd -P)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." >/dev/null 2>&1 && pwd -P)"
TOOLCHAIN_DIR="${REPO_ROOT}/wasm/toolchain"
BUILD_DIR="${REPO_ROOT}/wasm/build/g0"
EXPECTED_FILE="${SCRIPT_DIR}/expected.txt"
# shellcheck source=../common/run-wasm-program.sh
. "${SCRIPT_DIR}/../common/run-wasm-program.sh"

gate_fail() {
  echo "G0 FAIL: $*" >&2
  exit 1
}

echo "==> [a] activating pinned emsdk toolchain"
# shellcheck source=../../toolchain/activate.sh
if ! . "${TOOLCHAIN_DIR}/activate.sh"; then
  gate_fail "could not activate emsdk toolchain (see message above)"
fi

command -v emcc >/dev/null 2>&1 || gate_fail "emcc not on PATH after activation"
command -v node >/dev/null 2>&1 || gate_fail "node not found"
command -v chromium >/dev/null 2>&1 || gate_fail "chromium not found on this machine"
command -v python3 >/dev/null 2>&1 || gate_fail "python3 not found"

echo "==> [b] compiling smoke.cpp"
rm -rf "${BUILD_DIR}"
mkdir -p "${BUILD_DIR}/node" "${BUILD_DIR}/web"

EMCC_COMMON_FLAGS=(-std=c++17 -O2 -Wall -fexceptions -sDISABLE_EXCEPTION_CATCHING=0 -sEXIT_RUNTIME=1)

emcc "${SCRIPT_DIR}/smoke.cpp" "${EMCC_COMMON_FLAGS[@]}" \
  -o "${BUILD_DIR}/node/smoke.js" \
  || gate_fail "node-target compile failed"

emcc "${SCRIPT_DIR}/smoke.cpp" "${EMCC_COMMON_FLAGS[@]}" \
  -sMODULARIZE=1 -sEXPORT_NAME=createSmokeModule -sEXPORT_ES6=1 -sENVIRONMENT=web \
  -o "${BUILD_DIR}/web/smoke.js" \
  || gate_fail "web-target compile failed"

run_wasm_program G0 "${BUILD_DIR}" "${EXPECTED_FILE}" \
  "${BUILD_DIR}/node/smoke.js" "${BUILD_DIR}/web/smoke.js"

echo "G0 PASS"
exit 0
