#!/usr/bin/env bash
# Idempotently fetch, sha256-verify, and unpack the pinned xeus-cpp-lite /
# CppInterOp WebAssembly conda packages (see xcpp-toolchain.env) into
# ${ROOT_WASM_TOOLS:-$HOME/.root-kata-wasm}/xcpp-toolchain/. Never writes inside
# the git repository. A sha256 mismatch is a hard failure; the offending file is
# left in place for inspection but never trusted.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd -P)"
# shellcheck source=./xcpp-toolchain.env
source "${SCRIPT_DIR}/xcpp-toolchain.env"

ROOT_WASM_TOOLS="${ROOT_WASM_TOOLS:-$HOME/.root-kata-wasm}"
CACHE_DIR="${ROOT_WASM_TOOLS}/cache/g7"
STAGE_DIR="${ROOT_WASM_TOOLS}/xcpp-toolchain"
mkdir -p "${CACHE_DIR}" "${STAGE_DIR}"

sha256_of() { sha256sum "$1" | awk '{print $1}'; }

fetch_and_verify() {
  local pkg="$1" expected_sha="$2"
  local path="${CACHE_DIR}/${pkg}"
  if [[ -f "${path}" ]]; then
    echo "fetch-xcpp-toolchain: ${pkg} already cached, skipping download" >&2
  else
    echo "fetch-xcpp-toolchain: downloading ${pkg}" >&2
    local tmp="${path}.part"
    curl -fL --retry 3 -o "${tmp}" "${XCPP_CHANNEL_BASE}/${pkg}"
    mv "${tmp}" "${path}"
  fi
  local actual_sha
  actual_sha="$(sha256_of "${path}")"
  if [[ "${actual_sha}" != "${expected_sha}" ]]; then
    echo "fetch-xcpp-toolchain: FATAL sha256 mismatch for ${pkg}" >&2
    echo "  expected: ${expected_sha}" >&2
    echo "  actual:   ${actual_sha}" >&2
    exit 1
  fi
  echo "fetch-xcpp-toolchain: sha256 verified for ${pkg}" >&2
}

fetch_and_verify "${XEUS_CPP_PKG}" "${XEUS_CPP_SHA256}"
fetch_and_verify "${CPPINTEROP_PKG}" "${CPPINTEROP_SHA256}"
fetch_and_verify "${XEUS_PKG}" "${XEUS_SHA256}"

STAMP="${STAGE_DIR}/.extracted-${XEUS_CPP_PKG}-${CPPINTEROP_PKG}-${XEUS_PKG}"
if [[ -f "${STAMP}" ]]; then
  echo "fetch-xcpp-toolchain: already extracted at ${STAGE_DIR}, skipping unpack" >&2
else
  echo "fetch-xcpp-toolchain: extracting into ${STAGE_DIR}" >&2
  rm -rf "${STAGE_DIR:?}/xeus-cpp-extract" "${STAGE_DIR:?}/cppinterop-extract" "${STAGE_DIR:?}/xeus-extract"
  mkdir -p "${STAGE_DIR}/xeus-cpp-extract" "${STAGE_DIR}/cppinterop-extract" "${STAGE_DIR}/xeus-extract"
  tar -xjf "${CACHE_DIR}/${XEUS_CPP_PKG}" -C "${STAGE_DIR}/xeus-cpp-extract"
  tar -xjf "${CACHE_DIR}/${CPPINTEROP_PKG}" -C "${STAGE_DIR}/cppinterop-extract"
  tar -xjf "${CACHE_DIR}/${XEUS_PKG}" -C "${STAGE_DIR}/xeus-extract"

  cp "${STAGE_DIR}/xeus-cpp-extract/bin/xcpp.js" "${STAGE_DIR}/xcpp.js"
  cp "${STAGE_DIR}/xeus-cpp-extract/bin/xcpp.wasm" "${STAGE_DIR}/xcpp.wasm"
  cp "${STAGE_DIR}/xeus-cpp-extract/bin/xcpp.data" "${STAGE_DIR}/xcpp.data"
  cp "${STAGE_DIR}/cppinterop-extract/lib/libclangCppInterOp.so.21.1" "${STAGE_DIR}/libclangCppInterOp.so"
  cp "${STAGE_DIR}/xeus-extract/lib/libxeus.so" "${STAGE_DIR}/libxeus.so"
  touch "${STAMP}"
fi

echo "fetch-xcpp-toolchain: done. Runtime files staged at ${STAGE_DIR}" >&2
echo "${STAGE_DIR}"
