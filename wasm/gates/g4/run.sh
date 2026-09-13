#!/usr/bin/env bash
# G4: can genuine TH1D execute with the pinned toolchain and no ROOT libraries?
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd -P)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." >/dev/null 2>&1 && pwd -P)"
TOOLCHAIN_DIR="${REPO_ROOT}/wasm/toolchain"
BUILD_DIR="${REPO_ROOT}/wasm/build/g4"
EXPECTED_FILE="${SCRIPT_DIR}/expected.txt"
# shellcheck source=../common/run-wasm-program.sh
. "${SCRIPT_DIR}/../common/run-wasm-program.sh"

gate_fail() {
  echo "G4 FAIL: $*" >&2
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

echo "==> [b] generating ROOT-template configuration"
rm -rf "${BUILD_DIR}"
mkdir -p "${BUILD_DIR}/native" "${BUILD_DIR}/node" "${BUILD_DIR}/web"
for target in native wasm; do
  compiler=g++
  [ "${target}" = wasm ] && compiler=em++
  cmake -DROOT_SOURCE="${ROOT_SOURCE}" -DOUTPUT_HEADER="${BUILD_DIR}/${target}/RConfigure.h" \
    -DCXX="$(command -v "${compiler}")" -P "${REPO_ROOT}/wasm/gates/g2/rconfigure.cmake" \
    || gate_fail "ROOT-template configuration failed for ${target}"
done

ROOT_INCLUDES=(-I"${ROOT_SOURCE}/hist/hist/inc" -I"${ROOT_SOURCE}/math/mathcore/inc"
  -I"${ROOT_SOURCE}/math/matrix/inc" -I"${ROOT_SOURCE}/io/io/inc"
  -I"${ROOT_SOURCE}/core/base/inc" -I"${ROOT_SOURCE}/core/foundation/inc"
  -I"${ROOT_SOURCE}/core/clib/inc" -I"${ROOT_SOURCE}/core/cont/inc" -I"${ROOT_SOURCE}/core/meta/inc"
  -I"${ROOT_SOURCE}/core/imt/inc" -I"${ROOT_SOURCE}/core/zip/inc")

echo "==> [c] directly linking TH1D without ROOT libraries"
set +e
em++ -std=c++17 -O2 -I"${BUILD_DIR}/wasm" "${ROOT_INCLUDES[@]}" -sEXIT_RUNTIME=1 \
  "${SCRIPT_DIR}/th1d.cpp" -o "${BUILD_DIR}/node/th1d.js" \
  > "${BUILD_DIR}/direct-link.stdout" 2> "${BUILD_DIR}/direct-link.stderr"
link_status=$?
set -e
if [ "${link_status}" -ne 0 ]; then
  first_missing="$(sed -n '/undefined symbol:/ { s/.*undefined symbol: //; p; q; }' "${BUILD_DIR}/direct-link.stderr")"
  [ -n "${first_missing}" ] || gate_fail "direct link failed before an unresolved ROOT symbol; see ${BUILD_DIR}/direct-link.stderr"
  printf '%s\n' "${first_missing}" > "${BUILD_DIR}/first-missing-symbol.txt"
  grep -Fq 'TH1D::TH1D' "${BUILD_DIR}/first-missing-symbol.txt" \
    || gate_fail "first unresolved symbol was not the pinned TH1D constructor: ${first_missing}"
  echo "G4 FAIL: direct TH1D link requires ${first_missing}; see wasm/gates/g4/BLOCKER.md" >&2
  exit 1
fi

echo "==> [d] compiling native and browser references"
g++ -std=c++17 -O2 -I"${BUILD_DIR}/native" "${ROOT_INCLUDES[@]}" "${SCRIPT_DIR}/th1d.cpp" \
  -o "${BUILD_DIR}/native/th1d" || gate_fail "native reference compile failed"
"${BUILD_DIR}/native/th1d" > "${BUILD_DIR}/native_stdout.txt" || gate_fail "native reference run failed"
diff -u "${EXPECTED_FILE}" "${BUILD_DIR}/native_stdout.txt" > "${BUILD_DIR}/native_vs_expected.diff" \
  || { cat "${BUILD_DIR}/native_vs_expected.diff" >&2; gate_fail "native reference differs from expected.txt"; }
em++ -std=c++17 -O2 -I"${BUILD_DIR}/wasm" "${ROOT_INCLUDES[@]}" -sEXIT_RUNTIME=1 \
  -sMODULARIZE=1 -sEXPORT_NAME=createTH1DModule -sEXPORT_ES6=1 -sENVIRONMENT=web \
  "${SCRIPT_DIR}/th1d.cpp" -o "${BUILD_DIR}/web/th1d.js" || gate_fail "browser-target TH1D compile failed"
run_wasm_program G4 "${BUILD_DIR}" "${EXPECTED_FILE}" \
  "${BUILD_DIR}/node/th1d.js" "${BUILD_DIR}/web/th1d.js"
echo "G4 PASS"
