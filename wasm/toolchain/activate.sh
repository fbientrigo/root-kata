#!/usr/bin/env bash
# Sourceable: puts the pinned Emscripten toolchain (emcc, em++, node shim) on PATH.
#
#   . wasm/toolchain/activate.sh
#
# Fails loudly (without killing an interactive shell, since this is sourced) if the
# pinned SDK has not been installed yet via wasm/toolchain/install-emsdk.sh.

_activate_emsdk_dir_lookup() {
  local script_dir
  script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd -P)"
  # shellcheck source=./emsdk.env
  . "${script_dir}/emsdk.env"

  local root_wasm_tools="${ROOT_WASM_TOOLS:-${ROOT_WASM_TOOLS_DEFAULT:-$HOME/.root-kata-wasm}}"
  echo "${root_wasm_tools}/emsdk"
}

_EMSDK_DIR="$(_activate_emsdk_dir_lookup)"

if [ ! -f "${_EMSDK_DIR}/emsdk_env.sh" ]; then
  echo "activate.sh: emsdk not found at ${_EMSDK_DIR}" >&2
  echo "activate.sh: run wasm/toolchain/install-emsdk.sh first." >&2
  unset _EMSDK_DIR
  unset -f _activate_emsdk_dir_lookup
  return 1 2>/dev/null || exit 1
fi

# emsdk_env.sh is chatty; quiet it down but still surface real errors.
if ! . "${_EMSDK_DIR}/emsdk_env.sh" >/tmp/emsdk_env.$$.log 2>&1; then
  echo "activate.sh: sourcing emsdk_env.sh failed:" >&2
  cat /tmp/emsdk_env.$$.log >&2
  rm -f /tmp/emsdk_env.$$.log
  unset _EMSDK_DIR
  unset -f _activate_emsdk_dir_lookup
  return 1 2>/dev/null || exit 1
fi
rm -f /tmp/emsdk_env.$$.log

if ! command -v emcc >/dev/null 2>&1; then
  echo "activate.sh: emsdk_env.sh sourced but emcc is not on PATH." >&2
  echo "activate.sh: run wasm/toolchain/install-emsdk.sh to (re)activate the pinned SDK." >&2
  unset _EMSDK_DIR
  unset -f _activate_emsdk_dir_lookup
  return 1 2>/dev/null || exit 1
fi

unset _EMSDK_DIR
unset -f _activate_emsdk_dir_lookup
