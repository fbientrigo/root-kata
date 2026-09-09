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

fail() {
  echo "G0 FAIL: $*" >&2
  exit 1
}

echo "==> [a] activating pinned emsdk toolchain"
# shellcheck source=../../toolchain/activate.sh
if ! . "${TOOLCHAIN_DIR}/activate.sh"; then
  fail "could not activate emsdk toolchain (see message above)"
fi

command -v emcc >/dev/null 2>&1 || fail "emcc not on PATH after activation"
command -v node >/dev/null 2>&1 || fail "node not found"
command -v chromium >/dev/null 2>&1 || fail "chromium not found on this machine"
command -v python3 >/dev/null 2>&1 || fail "python3 not found"

echo "==> [b] compiling smoke.cpp"
rm -rf "${BUILD_DIR}"
mkdir -p "${BUILD_DIR}/node" "${BUILD_DIR}/web"

EMCC_COMMON_FLAGS=(-std=c++17 -O2 -Wall -fexceptions -sDISABLE_EXCEPTION_CATCHING=0 -sEXIT_RUNTIME=1)

emcc "${SCRIPT_DIR}/smoke.cpp" "${EMCC_COMMON_FLAGS[@]}" \
  -o "${BUILD_DIR}/node/smoke.js" \
  || fail "node-target compile failed"

emcc "${SCRIPT_DIR}/smoke.cpp" "${EMCC_COMMON_FLAGS[@]}" \
  -sMODULARIZE=1 -sEXPORT_NAME=createSmokeModule -sEXPORT_ES6=1 -sENVIRONMENT=web \
  -o "${BUILD_DIR}/web/smoke.js" \
  || fail "web-target compile failed"

# Minimal harness: loads the modularized ES6 build, mirrors Module stdout into a
# <pre> element (real DOM text nodes, unlike a <textarea>.value which --dump-dom
# does not serialize), and flags completion via document.title so the diff step
# can tell a real run from a truncated one.
cat > "${BUILD_DIR}/web/index.html" <<'HTML'
<!doctype html>
<html><head><meta charset="utf-8"><title>G0 smoke harness</title></head>
<body>
<pre id="output"></pre>
<script type="module">
  import createSmokeModule from "./smoke.js";
  const outEl = document.getElementById("output");
  createSmokeModule({
    print: (text) => { outEl.appendChild(document.createTextNode(text + "\n")); },
    printErr: (text) => { outEl.appendChild(document.createTextNode("[stderr] " + text + "\n")); },
    onExit: () => { document.title = "G0-DONE"; },
  }).catch((e) => {
    outEl.appendChild(document.createTextNode("[init-error] " + e + "\n"));
    document.title = "G0-INIT-ERROR";
  });
</script>
</body></html>
HTML

echo "==> [c] running under node"
NODE_OUT="${BUILD_DIR}/node_stdout.txt"
node "${BUILD_DIR}/node/smoke.js" > "${NODE_OUT}" || fail "node run failed"

echo "==> [d] running under headless chromium"
PORT="$(python3 -c 'import socket
s = socket.socket()
s.bind(("127.0.0.1", 0))
print(s.getsockname()[1])
s.close()')"
SERVER_LOG="${BUILD_DIR}/http_server.log"

(cd "${BUILD_DIR}/web" && exec python3 -m http.server "${PORT}" --bind 127.0.0.1) \
  > "${SERVER_LOG}" 2>&1 &
SERVER_PID=$!

cleanup() {
  kill "${SERVER_PID}" >/dev/null 2>&1 || true
  wait "${SERVER_PID}" 2>/dev/null || true
}
trap cleanup EXIT

ready=0
for _ in $(seq 1 50); do
  if curl -s -o /dev/null "http://127.0.0.1:${PORT}/index.html"; then
    ready=1
    break
  fi
  sleep 0.1
done
[ "${ready}" -eq 1 ] || fail "local HTTP server on port ${PORT} did not come up (see ${SERVER_LOG})"

DOM_DUMP="${BUILD_DIR}/chromium_dom.html"
CHROMIUM_LOG="${BUILD_DIR}/chromium_stderr.log"

chromium \
  --headless --disable-gpu --no-sandbox --disable-dev-shm-usage \
  --virtual-time-budget=10000 \
  --dump-dom "http://127.0.0.1:${PORT}/index.html" \
  > "${DOM_DUMP}" 2> "${CHROMIUM_LOG}" \
  || fail "chromium invocation failed (see ${CHROMIUM_LOG})"

grep -q '<title>G0-DONE</title>' "${DOM_DUMP}" \
  || fail "chromium page never reached G0-DONE (program did not finish in time or errored); see ${DOM_DUMP} and ${CHROMIUM_LOG}"

CHROMIUM_OUT="${BUILD_DIR}/chromium_stdout.txt"
python3 - "${DOM_DUMP}" > "${CHROMIUM_OUT}" <<'PY'
import html
import re
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
    dom = f.read()

m = re.search(r'<pre id="output">(.*?)</pre>', dom, re.S)
if not m:
    print("ERROR: #output element not found in DOM dump", file=sys.stderr)
    sys.exit(1)

sys.stdout.write(html.unescape(m.group(1)))
PY

[ -s "${CHROMIUM_OUT}" ] || fail "no stdout captured from the chromium run"

echo "==> [e] diffing node vs chromium vs expected.txt"
if ! diff -u "${NODE_OUT}" "${CHROMIUM_OUT}" > "${BUILD_DIR}/node_vs_chromium.diff"; then
  cat "${BUILD_DIR}/node_vs_chromium.diff" >&2
  fail "node and chromium stdout differ (see ${BUILD_DIR}/node_vs_chromium.diff)"
fi

if ! diff -u "${EXPECTED_FILE}" "${NODE_OUT}" > "${BUILD_DIR}/node_vs_expected.diff"; then
  cat "${BUILD_DIR}/node_vs_expected.diff" >&2
  fail "node stdout does not match expected.txt (see ${BUILD_DIR}/node_vs_expected.diff)"
fi

echo "G0 PASS"
exit 0
