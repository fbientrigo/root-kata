#!/usr/bin/env bash
set -euo pipefail

bash wasm/toolchain/install-emsdk.sh
bash wasm/toolchain/fetch-root-src.sh
bash wasm/gates/p0deps/xbuild/run.sh configure
bash wasm/gates/p0deps/xbuild/run.sh hist
bash wasm/gates/rootlight/run.sh stage
bash wasm/gates/rootlight/run.sh link
bash wasm/gates/g7/fetch-xcpp-toolchain.sh >/dev/null
bash wasm/rootlight/interpreter/build.sh
python3 scripts/stage_wasm_runtime.py
