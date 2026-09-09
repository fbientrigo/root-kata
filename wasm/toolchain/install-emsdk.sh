#!/usr/bin/env bash
# Idempotent installer for the pinned Emscripten SDK (gate G0).
#
# - Clones (or updates) emsdk into ${ROOT_WASM_TOOLS:-$HOME/.root-kata-wasm}/emsdk,
#   OUTSIDE the repo. It never writes inside the repo and never touches shell rc files.
# - Checks out the pinned EMSDK_VERSION from wasm/toolchain/emsdk.env, then runs
#   `./emsdk install <ver>` and `./emsdk activate <ver>`.
# - Safe to re-run: emsdk's own install/activate are no-ops when already satisfied,
#   so a second run is fast and does not re-download.
#
# Usage: wasm/toolchain/install-emsdk.sh
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd -P)"

# shellcheck source=./emsdk.env
. "${SCRIPT_DIR}/emsdk.env"

: "${EMSDK_VERSION:?EMSDK_VERSION not set by emsdk.env}"
: "${EMSDK_GIT_URL:?EMSDK_GIT_URL not set by emsdk.env}"

ROOT_WASM_TOOLS="${ROOT_WASM_TOOLS:-${ROOT_WASM_TOOLS_DEFAULT:-$HOME/.root-kata-wasm}}"
EMSDK_DIR="${ROOT_WASM_TOOLS}/emsdk"

echo "==> Installing emsdk ${EMSDK_VERSION} into ${EMSDK_DIR}"
mkdir -p "${ROOT_WASM_TOOLS}"

if [ -d "${EMSDK_DIR}/.git" ]; then
  echo "==> emsdk checkout already present, fetching updates"
  git -C "${EMSDK_DIR}" fetch --tags --quiet origin
else
  git clone --quiet "${EMSDK_GIT_URL}" "${EMSDK_DIR}"
fi

git -C "${EMSDK_DIR}" checkout --quiet "${EMSDK_VERSION}"

"${EMSDK_DIR}/emsdk" install "${EMSDK_VERSION}"
"${EMSDK_DIR}/emsdk" activate "${EMSDK_VERSION}"

echo "==> emsdk ${EMSDK_VERSION} installed and activated at ${EMSDK_DIR}"
echo "==> Source wasm/toolchain/activate.sh to put emcc on PATH."
