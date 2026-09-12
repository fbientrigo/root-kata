#!/usr/bin/env bash
# Source this after defining gate_fail(). Runs an already-compiled Emscripten
# program in Node and Chromium, then compares both outputs to expected.txt.

run_wasm_program() {
  local gate="$1" build_dir="$2" expected_file="$3" node_js="$4" web_js="$5"
  local node_out="${build_dir}/node_stdout.txt"
  local chromium_out="${build_dir}/chromium_stdout.txt"
  local port server_pid dom_dump chromium_log ready

  echo "==> [c] running under node"
  node "${node_js}" > "${node_out}" || gate_fail "node run failed"

  cat > "${build_dir}/web/index.html" <<HTML
<!doctype html>
<html><head><meta charset="utf-8"><title>${gate} harness</title></head>
<body>
<pre id="output"></pre>
<script type="module">
  import createModule from "./$(basename "${web_js}")";
  const outEl = document.getElementById("output");
  createModule({
    print: (text) => { outEl.appendChild(document.createTextNode(text + "\\n")); },
    printErr: (text) => { outEl.appendChild(document.createTextNode("[stderr] " + text + "\\n")); },
    onExit: () => { document.title = "${gate}-DONE"; },
  }).catch((e) => {
    outEl.appendChild(document.createTextNode("[init-error] " + e + "\\n"));
    document.title = "${gate}-INIT-ERROR";
  });
</script>
</body></html>
HTML

  echo "==> [d] running under headless chromium"
  port="$(python3 -c 'import socket
s = socket.socket()
s.bind(("127.0.0.1", 0))
print(s.getsockname()[1])
s.close()')"
  (cd "${build_dir}/web" && exec python3 -m http.server "${port}" --bind 127.0.0.1) \
    > "${build_dir}/http_server.log" 2>&1 &
  server_pid=$!
  cleanup_wasm_program() {
    kill "${server_pid}" >/dev/null 2>&1 || true
    wait "${server_pid}" 2>/dev/null || true
  }
  trap cleanup_wasm_program RETURN

  ready=0
  for _ in $(seq 1 50); do
    if curl -s -o /dev/null "http://127.0.0.1:${port}/index.html"; then
      ready=1
      break
    fi
    sleep 0.1
  done
  [ "${ready}" -eq 1 ] || gate_fail "local HTTP server on port ${port} did not come up"

  dom_dump="${build_dir}/chromium_dom.html"
  chromium_log="${build_dir}/chromium_stderr.log"
  chromium --headless --disable-gpu --no-sandbox --disable-dev-shm-usage \
    --virtual-time-budget=10000 --dump-dom "http://127.0.0.1:${port}/index.html" \
    > "${dom_dump}" 2> "${chromium_log}" \
    || gate_fail "chromium invocation failed (see ${chromium_log})"
  grep -q "<title>${gate}-DONE</title>" "${dom_dump}" \
    || gate_fail "chromium page never reached ${gate}-DONE; see ${dom_dump} and ${chromium_log}"

  python3 - "${dom_dump}" > "${chromium_out}" <<'PY'
import html
import re
import sys

with open(sys.argv[1], encoding="utf-8") as f:
    dom = f.read()
m = re.search(r'<pre id="output">(.*?)</pre>', dom, re.S)
if not m:
    raise SystemExit("ERROR: #output element not found in DOM dump")
sys.stdout.write(html.unescape(m.group(1)))
PY
  [ -s "${chromium_out}" ] || gate_fail "no stdout captured from the chromium run"

  echo "==> [e] diffing node vs chromium vs expected.txt"
  if ! diff -u "${node_out}" "${chromium_out}" > "${build_dir}/node_vs_chromium.diff"; then
    cat "${build_dir}/node_vs_chromium.diff" >&2
    gate_fail "node and chromium stdout differ"
  fi
  if ! diff -u "${expected_file}" "${node_out}" > "${build_dir}/node_vs_expected.diff"; then
    cat "${build_dir}/node_vs_expected.diff" >&2
    gate_fail "node stdout does not match expected.txt"
  fi
}
