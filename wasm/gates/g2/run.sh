#!/usr/bin/env bash
# G2: genuine ROOT GenVector executes as WebAssembly without ROOT libraries.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd -P)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." >/dev/null 2>&1 && pwd -P)"
TOOLCHAIN_DIR="${REPO_ROOT}/wasm/toolchain"
BUILD_DIR="${REPO_ROOT}/wasm/build/g2"
EXPECTED_FILE="${SCRIPT_DIR}/expected.txt"
# shellcheck source=../common/run-wasm-program.sh
. "${SCRIPT_DIR}/../common/run-wasm-program.sh"

gate_fail() {
  echo "G2 FAIL: $*" >&2
  exit 1
}

echo "==> [a] activating pinned sources and Emscripten"
bash "${TOOLCHAIN_DIR}/fetch-root-src.sh" || gate_fail "could not fetch verified ROOT source"
# shellcheck source=../../toolchain/root-src.env
. "${TOOLCHAIN_DIR}/root-src.env"
ROOT_SOURCE="${ROOT_WASM_TOOLS:-$HOME/.root-kata-wasm}/src/root-${ROOT_VERSION}"
if ! . "${TOOLCHAIN_DIR}/activate.sh"; then
  gate_fail "could not activate pinned Emscripten"
fi
command -v em++ >/dev/null 2>&1 || gate_fail "em++ not on PATH"
command -v g++ >/dev/null 2>&1 || gate_fail "g++ not found"
command -v cmake >/dev/null 2>&1 || gate_fail "cmake not found"
command -v node >/dev/null 2>&1 || gate_fail "node not found"
command -v chromium >/dev/null 2>&1 || gate_fail "chromium not found"

echo "==> [b] generating ROOT-template configuration and compiling"
rm -rf "${BUILD_DIR}"
mkdir -p "${BUILD_DIR}/native" "${BUILD_DIR}/node" "${BUILD_DIR}/web"
for target in native wasm; do
  compiler=g++
  [ "${target}" = wasm ] && compiler=em++
  cmake -DROOT_SOURCE="${ROOT_SOURCE}" -DOUTPUT_HEADER="${BUILD_DIR}/${target}/RConfigure.h" \
    -DCXX="$(command -v "${compiler}")" -P "${SCRIPT_DIR}/rconfigure.cmake" \
    || gate_fail "ROOT-template configuration failed for ${target}"
done

ROOT_INCLUDES=(-I"${ROOT_SOURCE}/math/genvector/inc" -I"${ROOT_SOURCE}/math/mathcore/inc"
  -I"${ROOT_SOURCE}/core/foundation/inc" -I"${ROOT_SOURCE}/core/base/inc")
g++ -std=c++17 -O2 -I"${BUILD_DIR}/native" "${ROOT_INCLUDES[@]}" "${SCRIPT_DIR}/genvector.cpp" \
  -o "${BUILD_DIR}/native/genvector" || gate_fail "native reference compile failed"
"${BUILD_DIR}/native/genvector" > "${BUILD_DIR}/native_stdout.txt" || gate_fail "native reference run failed"
diff -u "${EXPECTED_FILE}" "${BUILD_DIR}/native_stdout.txt" > "${BUILD_DIR}/native_vs_expected.diff" \
  || { cat "${BUILD_DIR}/native_vs_expected.diff" >&2; gate_fail "native reference differs from expected.txt"; }

EMXX_FLAGS=(-std=c++17 -O2 -I"${BUILD_DIR}/wasm" "${ROOT_INCLUDES[@]}" -sEXIT_RUNTIME=1)
em++ "${SCRIPT_DIR}/genvector.cpp" "${EMXX_FLAGS[@]}" -o "${BUILD_DIR}/node/genvector.js" \
  || gate_fail "Node-target GenVector compile failed"
em++ "${SCRIPT_DIR}/genvector.cpp" "${EMXX_FLAGS[@]}" \
  -sMODULARIZE=1 -sEXPORT_NAME=createGenVectorModule -sEXPORT_ES6=1 -sENVIRONMENT=web \
  -o "${BUILD_DIR}/web/genvector.js" || gate_fail "browser-target GenVector compile failed"

run_wasm_program G2 "${BUILD_DIR}" "${EXPECTED_FILE}" \
  "${BUILD_DIR}/node/genvector.js" "${BUILD_DIR}/web/genvector.js"
echo "G2 PASS"
