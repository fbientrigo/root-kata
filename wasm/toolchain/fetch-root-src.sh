#!/usr/bin/env bash
# Idempotently fetch and verify the pinned CERN ROOT source release for Gate G0.
#
# - Downloads the pinned tarball into ${ROOT_WASM_TOOLS:-$HOME/.root-kata-wasm}/cache/
#   (skips the download if the file is already there).
# - Verifies its sha256 against wasm/toolchain/root-src.env. A mismatch is a hard
#   failure (exit non-zero); the tarball is left in place for inspection but never
#   trusted.
# - Unpacks into ${ROOT_WASM_TOOLS:-$HOME/.root-kata-wasm}/src/root-$ROOT_VERSION,
#   but only if that directory does not already exist, so re-running is fast and
#   does not redo work.
# - Never writes anything inside the git repository; all state lives under
#   ROOT_WASM_TOOLS, which defaults to a directory outside the repo.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
# shellcheck source=./root-src.env
source "${SCRIPT_DIR}/root-src.env"

: "${ROOT_VERSION:?root-src.env must set ROOT_VERSION}"
: "${ROOT_SRC_URL:?root-src.env must set ROOT_SRC_URL}"
: "${ROOT_SRC_SHA256:?root-src.env must set ROOT_SRC_SHA256}"

ROOT_WASM_TOOLS="${ROOT_WASM_TOOLS:-$HOME/.root-kata-wasm}"
CACHE_DIR="${ROOT_WASM_TOOLS}/cache"
SRC_DIR="${ROOT_WASM_TOOLS}/src"
TARBALL_NAME="root_v${ROOT_VERSION}.source.tar.gz"
TARBALL_PATH="${CACHE_DIR}/${TARBALL_NAME}"
UNPACK_DIR="${SRC_DIR}/root-${ROOT_VERSION}"

mkdir -p "${CACHE_DIR}" "${SRC_DIR}"

sha256_of() {
  sha256sum "$1" | awk '{print $1}'
}

if [[ -f "${TARBALL_PATH}" ]]; then
  echo "fetch-root-src: tarball already present at ${TARBALL_PATH}, skipping download" >&2
else
  echo "fetch-root-src: downloading ${ROOT_SRC_URL}" >&2
  tmp_path="${TARBALL_PATH}.part"
  curl -fL --retry 3 -o "${tmp_path}" "${ROOT_SRC_URL}"
  mv "${tmp_path}" "${TARBALL_PATH}"
fi

actual_sha256="$(sha256_of "${TARBALL_PATH}")"
if [[ "${actual_sha256}" != "${ROOT_SRC_SHA256}" ]]; then
  echo "fetch-root-src: FATAL sha256 mismatch for ${TARBALL_PATH}" >&2
  echo "  expected: ${ROOT_SRC_SHA256}" >&2
  echo "  actual:   ${actual_sha256}" >&2
  exit 1
fi
echo "fetch-root-src: sha256 verified (${actual_sha256})" >&2

if [[ -d "${UNPACK_DIR}" ]]; then
  echo "fetch-root-src: ${UNPACK_DIR} already unpacked, skipping unpack" >&2
else
  echo "fetch-root-src: unpacking into ${SRC_DIR}" >&2
  tmp_unpack_dir="$(mktemp -d "${SRC_DIR}/.unpack-XXXXXX")"
  tar -xzf "${TARBALL_PATH}" -C "${tmp_unpack_dir}"
  # The tarball's top-level directory is expected to be "root-${ROOT_VERSION}".
  extracted_top="${tmp_unpack_dir}/root-${ROOT_VERSION}"
  if [[ ! -d "${extracted_top}" ]]; then
    echo "fetch-root-src: FATAL expected top-level dir 'root-${ROOT_VERSION}' not found after unpack" >&2
    rm -rf "${tmp_unpack_dir}"
    exit 1
  fi
  mv "${extracted_top}" "${UNPACK_DIR}"
  rm -rf "${tmp_unpack_dir}"
fi

echo "fetch-root-src: done. Source tree at ${UNPACK_DIR}" >&2
