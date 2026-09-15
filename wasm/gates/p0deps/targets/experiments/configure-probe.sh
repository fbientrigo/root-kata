#!/usr/bin/env bash
source ~/.root-kata-wasm/emsdk/emsdk_env.sh >/dev/null 2>&1
cd ${BUILD:-$HOME/.cache/rootwasm-p0/targets/cfg-inject/build}
S=/home/fabian/.root-kata-wasm/src/root-6.40.04
start=$(date +%s)
timeout 900 emcmake cmake -G "Unix Makefiles" $S -DCMAKE_BUILD_TYPE=Release   -Dminimal=ON -Dimt=OFF -Druntime_cxxmodules=OFF -Dclad=OFF -Dfail-on-missing=OFF   -Dbuiltin_zlib=ON -Dbuiltin_lzma=ON -Dbuiltin_lz4=ON -Dbuiltin_zstd=ON -Dbuiltin_xxhash=ON   -Dbuiltin_pcre=ON -Dbuiltin_nlohmannjson=ON   ${EXTRA:-} > configure.log 2>&1
echo "exit=$? seconds=$(($(date +%s)-start))" >> configure.log
