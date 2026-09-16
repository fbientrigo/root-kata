#!/usr/bin/env bash
# Narrow Core experiment: prove the xeus dynamic-loader path, then load a
# genuine ROOT Core source slice before the formerly failing TH1D include.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd -P)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." >/dev/null 2>&1 && pwd -P)"
TOOLCHAIN_DIR="${REPO_ROOT}/wasm/toolchain"
G2_DIR="${REPO_ROOT}/wasm/gates/g2"
G7_DIR="${REPO_ROOT}/wasm/gates/g7"
BUILD_DIR="${REPO_ROOT}/wasm/build/gcore"
MANIFEST="${SCRIPT_DIR}/core-sources.tsv"

fail() { echo "GCORE FAIL: $*" >&2; exit 1; }

bash "${TOOLCHAIN_DIR}/fetch-root-src.sh" || fail "could not fetch pinned ROOT source"
# shellcheck source=../../toolchain/root-src.env
. "${TOOLCHAIN_DIR}/root-src.env"
ROOT_SOURCE="${ROOT_WASM_TOOLS:-$HOME/.root-kata-wasm}/src/root-${ROOT_VERSION}"
. "${TOOLCHAIN_DIR}/activate.sh" || fail "could not activate pinned Emscripten"
XCPP_STAGE="$(bash "${G7_DIR}/fetch-xcpp-toolchain.sh" | tail -1)" || fail "could not fetch xeus-cpp-lite"

rm -rf "${BUILD_DIR}"
mkdir -p "${BUILD_DIR}/web"
cmake -DROOT_SOURCE="${ROOT_SOURCE}" -DOUTPUT_HEADER="${BUILD_DIR}/RConfigure.h" -DOUTPUT_OPTIONS_HEADER="${BUILD_DIR}/RConfigOptions.h" -DCXX="$(command -v em++)" -P "${G2_DIR}/rconfigure.cmake"
"${ROOT_SOURCE}/cmake/unix/compiledata.sh" "${BUILD_DIR}/compiledata.h" "$(command -v em++)" -O2 '' '-std=c++17 -fwasm-exceptions' -shared '' so '' -lCore -lRint '' '' emscripten '' ''

includes=(
  -I"${BUILD_DIR}" -I"${ROOT_SOURCE}/core/base/inc" -I"${ROOT_SOURCE}/core/foundation/inc"
  -I"${ROOT_SOURCE}/core/foundation/res" -I"${ROOT_SOURCE}/core/cont/inc" -I"${ROOT_SOURCE}/core/clib/inc"
  -I"${ROOT_SOURCE}/core/textinput/inc" -I"${ROOT_SOURCE}/core/meta/inc" -I"${ROOT_SOURCE}/core/thread/inc"
  -I"${ROOT_SOURCE}/core/unix/inc" -I"${ROOT_SOURCE}/core/gui/inc" -I"${ROOT_SOURCE}/core/zip/inc"
  -I"${ROOT_SOURCE}/core/lz4/inc" -I"${ROOT_SOURCE}/core/lzma/inc" -I"${ROOT_SOURCE}/core/zstd/inc"
  -I"${ROOT_SOURCE}/core/imt/inc" -I"${ROOT_SOURCE}/core/multiproc/inc"
)
objects=()
while IFS=$'\t' read -r source_path citation; do
  [[ -z "${source_path}" || "${source_path}" == \#* ]] && continue
  [[ -n "${citation}" ]] || fail "missing source citation for ${source_path}"
  [[ -f "${ROOT_SOURCE}/${source_path}" ]] || fail "manifest source missing: ${source_path}"
  source="${source_path##*/}"
  source="${source%.cxx}"
  objects+=("${BUILD_DIR}/${source}.o")
  source_flags=()
  if [[ "${source}" == RCryptoRandom ]]; then
    # ROOT's Core CMake selects this branch when sys/random.h provides getrandom.
    source_flags=(-include cstddef -DR__GETRANDOM_CLIB)
  fi
  # ROOT's Core target supplies this definition in core/base/CMakeLists.txt:243-259.
  em++ -std=c++17 -fwasm-exceptions -O2 -fPIC -DINSTALL_LIB_TO_INCLUDE=\"../include\" "${source_flags[@]}" -c "${ROOT_SOURCE}/${source_path}" -o "${BUILD_DIR}/${source}.o" "${includes[@]}"
done < "${MANIFEST}"
(( ${#objects[@]} )) || fail "empty Core source manifest"
"$(dirname "$(command -v em++)")/../bin/llvm-nm" --undefined-only "${objects[@]}" > "${BUILD_DIR}/undefined-symbols.txt"
em++ -fwasm-exceptions -sSIDE_MODULE=1 -sERROR_ON_UNDEFINED_SYMBOLS=0 "${objects[@]}" -o "${BUILD_DIR}/web/libCore-slice.wasm"
em++ -fwasm-exceptions -sSIDE_MODULE=1 "${SCRIPT_DIR}/side-control.cpp" -o "${BUILD_DIR}/web/side-control.wasm"
strings "${BUILD_DIR}/web/libCore-slice.wasm" | grep -Fx '_ZN13TVersionCheckC1Ei' >/dev/null || fail "Core slice does not export TVersionCheck"
sha256sum "${MANIFEST}" "${BUILD_DIR}/RConfigure.h" "${BUILD_DIR}/RConfigOptions.h" "${BUILD_DIR}/compiledata.h" "${objects[@]}" "${BUILD_DIR}/web/libCore-slice.wasm" "${BUILD_DIR}/web/side-control.wasm" > "${BUILD_DIR}/hashes.txt"

python3 "${G7_DIR}/build_headers.py" "${ROOT_SOURCE}" "${BUILD_DIR}/RConfigure.h" "${BUILD_DIR}/web/headers.js" hist/hist/inc core/cont/inc core/meta/inc math/matrix/inc io/io/inc core/thread/inc core/clib/inc
cp "${XCPP_STAGE}/xcpp.js" "${XCPP_STAGE}/xcpp.wasm" "${XCPP_STAGE}/xcpp.data" "${XCPP_STAGE}/libxeus.so" "${XCPP_STAGE}/libclangCppInterOp.so" "${BUILD_DIR}/web/"
cp "${SCRIPT_DIR}/page/index.html" "${BUILD_DIR}/web/index.html"

port="$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()')"
(cd "${BUILD_DIR}/web" && exec python3 -m http.server "${port}" --bind 127.0.0.1) >"${BUILD_DIR}/http.log" 2>&1 &
server_pid=$!
cleanup() { kill "${server_pid}" >/dev/null 2>&1 || true; wait "${server_pid}" 2>/dev/null || true; }
trap cleanup EXIT
for _ in $(seq 1 50); do curl -s -o /dev/null "http://127.0.0.1:${port}/index.html" && break; sleep .1; done

node "${G7_DIR}/drive.mjs" "http://127.0.0.1:${port}/index.html?module=control" GCORE-DONE 180000 "${BUILD_DIR}/chrome-control" >"${BUILD_DIR}/control.json"
python3 - "${BUILD_DIR}/control.json" <<'PY'
import json, sys
r = json.load(open(sys.argv[1]))
assert not r['timedOut'] and r['output'] == 'control=42\n', r
PY
echo 'control side module: PASS'

node "${G7_DIR}/drive.mjs" "http://127.0.0.1:${port}/index.html?module=core" GCORE-DONE 180000 "${BUILD_DIR}/chrome-core" >"${BUILD_DIR}/core.json"
classification="$(python3 - "${BUILD_DIR}" <<'PY'
import gzip, json, sys
b = sys.argv[1]
r = json.load(open(f'{b}/core.json'))
trace = r.get('trace') or ''
diag = r.get('diag') or ''
loaded = 'loaded libCore-slice.wasm' in trace
old_blocker = 'TVersionCheck' in diag or '_ZN13TVersionCheckC1Ei' in diag
if r['timedOut'] or not loaded:
    classification = 'module-load-failure'
elif old_blocker:
    classification = 'core-loaded-old-include-blocker'
elif 'execute=ok' in trace:
    classification = 'th1d-include-success'
else:
    classification = 'core-loaded-new-include-blocker'
sizes = {}
for name in ('libCore-slice.wasm', 'side-control.wasm'):
    path = f'{b}/web/{name}'
    payload = open(path, 'rb').read()
    sizes[name] = {'bytes': len(payload), 'gzip_9_bytes': len(gzip.compress(payload, compresslevel=9))}
symbols = [line.split()[-1] for line in open(f'{b}/undefined-symbols.txt', encoding='utf-8') if ' U ' in line]
evidence = {
    'classification': classification,
    'core_loaded_before_probe': loaded,
    'old_tversioncheck_blocker_present': old_blocker,
    'module_sizes': sizes,
    'undefined_object_references': {'count': len(symbols), 'unique_count': len(set(symbols))},
    'raw_chromium': r,
}
with open(f'{b}/classification.json', 'w', encoding='utf-8') as f:
    json.dump(evidence, f, indent=2)
print(classification)
PY
 )"
python3 - "${BUILD_DIR}/classification.json" <<'PY'
import json, sys
e = json.load(open(sys.argv[1]))
print('classification:', e['classification'])
for name, size in e['module_sizes'].items():
    print(f"{name}: {size['bytes']} bytes, gzip-9 {size['gzip_9_bytes']} bytes")
u = e['undefined_object_references']
print(f"undefined object references: {u['count']} ({u['unique_count']} unique symbols)")
print('core diagnostic:', repr(e['raw_chromium'].get('diag')))
print('core log:', repr(e['raw_chromium'].get('trace')))
PY
bash "${G7_DIR}/verify-hosting-constraints.sh" "${BUILD_DIR}/web" '' 180
case "${classification}" in
  th1d-include-success|core-loaded-new-include-blocker) ;;
  *) fail "${classification}; see ${BUILD_DIR}/classification.json for raw Chromium evidence" ;;
esac
echo 'GCORE PASS: genuine Core loaded before the unchanged TH1D include; see classification.json for the next evidence boundary.'
