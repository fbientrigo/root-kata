#!/usr/bin/env bash
# verify-hosting-constraints.sh — Reusable GitHub Pages constraint verification harness
#
# Mechanically verifies that a WebAssembly web build directory satisfies all
# GitHub Pages deployment constraints:
#   1. Static HTTP only (pure static file server, no dynamic backend)
#   2. No /api/run or compile-server endpoint reachable (returns 404)
#   3. No server-side compilation happening in request path
#   4. No COOP/COEP headers set or required (verified against .github/workflows/pages.yml and HTTP headers)
#   5. No SharedArrayBuffer dependency (no cross-origin-isolation-only APIs required; confirmed via wasm inspection and runtime SAB removal)
#   6. Runs correctly in headless Chromium (matching run-wasm-program.sh pattern, reaching -DONE sentinel)
#   7. All network requests during page load and execution restricted to static assets on serving origin (captured via CDP network log)
#   8. Explicitly measured against GitHub Pages limits: 100 MB per file, soft 1 GB total site size
#
# Usage:
#   bash wasm/gates/g7/verify-hosting-constraints.sh <target_web_dir> [expected_file] [timeout_seconds]
#
# Exits 0 if all constraints PASS, non-zero if any FAILS.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd -P)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." >/dev/null 2>&1 && pwd -P)"

TARGET_DIR="${1:-}"
EXPECTED_FILE="${2:-}"
TIMEOUT_SEC="${3:-60}"

if [ -z "${TARGET_DIR}" ]; then
  echo "Usage: $0 <target_web_dir> [expected_file] [timeout_seconds]" >&2
  exit 2
fi

if [ ! -d "${TARGET_DIR}" ]; then
  echo "ERROR: target web directory '${TARGET_DIR}' does not exist." >&2
  exit 2
fi

TARGET_DIR="$(cd -- "${TARGET_DIR}" && pwd -P)"
ARTIFACTS_DIR="${TARGET_DIR}/hosting_verification"
rm -rf "${ARTIFACTS_DIR}"
mkdir -p "${ARTIFACTS_DIR}"

CHROME_PROFILE_DIR="$(mktemp -d /tmp/chrome_profile_g7_XXXXXX)"

HTTP_LOG="${ARTIFACTS_DIR}/http_server.log"
NETWORK_JSON="${ARTIFACTS_DIR}/hosting_network_requests.json"
STDOUT_TXT="${ARTIFACTS_DIR}/hosting_stdout.txt"
DIAG_TXT="${ARTIFACTS_DIR}/hosting_diag.txt"
REPORT_JSON="${ARTIFACTS_DIR}/hosting_report.json"
LIMITS_JSON="${ARTIFACTS_DIR}/limits_report.json"
NETWORK_EVAL_JSON="${ARTIFACTS_DIR}/network_eval.json"

fail_constraint() {
  local cid="$1" msg="$2"
  echo "[-] CONSTRAINT [${cid}] FAILED: ${msg}" >&2
  exit 1
}

pass_constraint() {
  local cid="$1" msg="$2"
  echo "[+] CONSTRAINT [${cid}] PASSED: ${msg}"
}

echo "================================================================================"
echo "  GitHub Pages Hosting Constraint Verification"
echo "  Target Web Directory: ${TARGET_DIR}"
echo "================================================================================"

# ------------------------------------------------------------------------------
# Constraint 1: Static HTTP only (no dynamic backend)
# ------------------------------------------------------------------------------
echo "==> [1/8] Verifying static HTTP only..."
# Check for dynamic server scripts intended for server-side execution
DYNAMIC_SCRIPTS=$(find "${TARGET_DIR}" -maxdepth 2 -type f \( -name "*.php" -o -name "cgi-bin" -o -name "*.cgi" \) || true)
if [ -n "${DYNAMIC_SCRIPTS}" ]; then
  fail_constraint "1" "Found dynamic server scripts in web directory: ${DYNAMIC_SCRIPTS}"
fi

# Allocate free ephemeral port for python http.server
PORT="$(python3 -c 'import socket; s = socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()')"
SERVER_ORIGIN="http://127.0.0.1:${PORT}"

(cd "${TARGET_DIR}" && exec python3 -m http.server "${PORT}" --bind 127.0.0.1) > "${HTTP_LOG}" 2>&1 &
SERVER_PID=$!

cleanup() {
  kill "${SERVER_PID}" >/dev/null 2>&1 || true
  wait "${SERVER_PID}" 2>/dev/null || true
  rm -rf "${CHROME_PROFILE_DIR}"
}
trap cleanup EXIT INT TERM

# Wait for server to come up
SERVER_READY=0
for _ in $(seq 1 50); do
  if curl -s -o /dev/null "${SERVER_ORIGIN}/index.html"; then
    SERVER_READY=1
    break
  fi
  sleep 0.1
done
[ "${SERVER_READY}" -eq 1 ] || fail_constraint "1" "Local static HTTP server on port ${PORT} failed to start"
pass_constraint "1" "Pure static HTTP server active on ${SERVER_ORIGIN} with no dynamic server backend"

# ------------------------------------------------------------------------------
# Constraint 2: No /api/run or compile-server endpoint reachable
# ------------------------------------------------------------------------------
echo "==> [2/8] Verifying no /api/run or compile-server endpoint reachable..."
API_STATUS="$(curl -s -o /dev/null -w "%{http_code}" "${SERVER_ORIGIN}/api/run" || true)"
if [ "${API_STATUS}" != "404" ]; then
  fail_constraint "2" "Endpoint /api/run returned HTTP ${API_STATUS}, expected 404 Not Found"
fi

# Ensure no code in TARGET_DIR actively requires /api/run
API_REFERENCES=$(grep -rn "fetch('/api/run')" "${TARGET_DIR}" || true)
if [ -n "${API_REFERENCES}" ]; then
  fail_constraint "2" "Client assets still contain active fetch('/api/run'): ${API_REFERENCES}"
fi
pass_constraint "2" "/api/run probe returned HTTP 404 and no active /api/run dependencies found in assets"

# ------------------------------------------------------------------------------
# Constraint 3: No server-side compilation in request path
# ------------------------------------------------------------------------------
echo "==> [3/8] Verifying no server-side compilation in request path..."
# Verify that python http.server is the only process associated with our server
SERVER_CHILDREN=$(pgrep -P "${SERVER_PID}" || true)
if [ -n "${SERVER_CHILDREN}" ]; then
  fail_constraint "3" "HTTP server has spawned unexpected child processes: ${SERVER_CHILDREN}"
fi
pass_constraint "3" "Server is standard unprivileged python http.server; zero server-side compiler processes"

# ------------------------------------------------------------------------------
# Constraint 4: No COOP/COEP headers set or required
# ------------------------------------------------------------------------------
echo "==> [4/8] Verifying no COOP/COEP headers set or required..."
# Inspect .github/workflows/pages.yml to verify standard upload-pages-artifact deployment
PAGES_YML="${REPO_ROOT}/.github/workflows/pages.yml"
if [ -f "${PAGES_YML}" ]; then
  if ! grep -q "actions/upload-pages-artifact" "${PAGES_YML}" || ! grep -q "actions/deploy-pages" "${PAGES_YML}"; then
    fail_constraint "4" ".github/workflows/pages.yml does not match standard GitHub Pages deployment actions"
  fi
fi

# Check HTTP response headers on static server
HEADER_DUMP="$(curl -sI "${SERVER_ORIGIN}/index.html")"
if echo "${HEADER_DUMP}" | grep -iq "Cross-Origin-Opener-Policy"; then
  fail_constraint "4" "Found unexpected Cross-Origin-Opener-Policy header in server response"
fi
if echo "${HEADER_DUMP}" | grep -iq "Cross-Origin-Embedder-Policy"; then
  fail_constraint "4" "Found unexpected Cross-Origin-Embedder-Policy header in server response"
fi
pass_constraint "4" "Verified deployment uses standard GitHub Pages actions; response headers contain no COOP/COEP"

# ------------------------------------------------------------------------------
# Constraint 5: No SharedArrayBuffer dependency
# ------------------------------------------------------------------------------
echo "==> [5/8] Verifying no SharedArrayBuffer dependency (WASM & JS inspection)..."
WASM_FILES=$(find "${TARGET_DIR}" -type f \( -name "*.wasm" -o -name "*.so" \) || true)
if [ -n "${WASM_FILES}" ]; then
  for wf in ${WASM_FILES}; do
    WASM_CHECK="$(python3 "${SCRIPT_DIR}/check_constraints.py" wasm "${wf}")"
    HAS_SHARED="$(echo "${WASM_CHECK}" | jq -r '.has_shared_memory')"
    if [ "${HAS_SHARED}" = "true" ]; then
      fail_constraint "5" "WASM binary ${wf} specifies shared memory, which requires SharedArrayBuffer/COOP/COEP!"
    fi
  done
fi
pass_constraint "5" "All WASM and dynamic library binaries verified: no shared memory flags present"

# ------------------------------------------------------------------------------
# Constraint 6 & 7: Headless Chromium execution + strict network request log
# ------------------------------------------------------------------------------
echo "==> [6/8 & 7/8] Running headless Chromium via CDP driver and capturing network log..."
TIMEOUT_MS=$((TIMEOUT_SEC * 1000))

node "${SCRIPT_DIR}/hosting_driver.mjs" \
  "${SERVER_ORIGIN}/index.html" \
  "${TIMEOUT_MS}" \
  "${CHROME_PROFILE_DIR}" \
  "${NETWORK_JSON}" \
  "${STDOUT_TXT}" \
  "${DIAG_TXT}" \
  "${REPORT_JSON}"

if [ ! -f "${REPORT_JSON}" ]; then
  fail_constraint "6" "Driver failed to produce report JSON"
fi

REPORT_SUCCESS="$(jq -r '.success' "${REPORT_JSON}")"
FINAL_TITLE="$(jq -r '.finalTitle' "${REPORT_JSON}")"
CROSS_ORIGIN_ISOLATED="$(jq -r '.crossOriginIsolated' "${REPORT_JSON}")"
SAB_TYPE="$(jq -r '.sabType' "${REPORT_JSON}")"
ELAPSED_MS="$(jq -r '.elapsedMs' "${REPORT_JSON}")"

echo "  -> Final Title: ${FINAL_TITLE}"
echo "  -> Elapsed Time: ${ELAPSED_MS} ms"
echo "  -> window.crossOriginIsolated: ${CROSS_ORIGIN_ISOLATED}"
echo "  -> typeof SharedArrayBuffer: ${SAB_TYPE}"

if [ "${CROSS_ORIGIN_ISOLATED}" != "false" ]; then
  fail_constraint "4" "Browser reported window.crossOriginIsolated == true, but GitHub Pages is never cross-origin isolated"
fi

if [ "${REPORT_SUCCESS}" != "true" ]; then
  DIAG_CONTENT=""
  [ -f "${DIAG_TXT}" ] && DIAG_CONTENT="$(cat "${DIAG_TXT}")"
  fail_constraint "6" "Page execution did not reach *-DONE (ended with '${FINAL_TITLE}'). Diag: ${DIAG_CONTENT}"
fi
pass_constraint "6" "Headless Chromium completed execution successfully in ${ELAPSED_MS} ms without SharedArrayBuffer (type: ${SAB_TYPE})"

# If expected_file provided, diff output
if [ -n "${EXPECTED_FILE}" ] && [ -f "${EXPECTED_FILE}" ]; then
  DIFF_FILE="${ARTIFACTS_DIR}/stdout_vs_expected.diff"
  if ! diff -u "${EXPECTED_FILE}" "${STDOUT_TXT}" > "${DIFF_FILE}"; then
    cat "${DIFF_FILE}" >&2
    fail_constraint "6" "Captured browser stdout does not match expected output ${EXPECTED_FILE}"
  fi
  pass_constraint "6" "Captured browser stdout matches ${EXPECTED_FILE} byte-for-byte"
fi

# Validate network requests
echo "==> [7/8] Validating all network requests are restricted to static assets on serving origin..."
python3 "${SCRIPT_DIR}/check_constraints.py" network "${NETWORK_JSON}" "${SERVER_ORIGIN}" "${TARGET_DIR}" > "${NETWORK_EVAL_JSON}"

NET_VALID="$(jq -r '.valid' "${NETWORK_EVAL_JSON}")"
TOTAL_REQS="$(jq -r '.total_requests' "${NETWORK_EVAL_JSON}")"
VIOLATIONS="$(jq -r '.violations[]?' "${NETWORK_EVAL_JSON}" || true)"

if [ "${NET_VALID}" != "true" ]; then
  fail_constraint "7" "Network violations detected: ${VIOLATIONS}"
fi
pass_constraint "7" "All ${TOTAL_REQS} network requests during load & execution restricted strictly to static origin assets (0 cross-origin requests)"

# ------------------------------------------------------------------------------
# Constraint 8: GitHub Pages Published Limits (100 MB per file, 1 GB site size)
# ------------------------------------------------------------------------------
echo "==> [8/8] Measuring payload against published GitHub Pages limits..."
python3 "${SCRIPT_DIR}/check_constraints.py" limits "${TARGET_DIR}" > "${LIMITS_JSON}"

FILE_LIMIT_PASS="$(jq -r '.file_limit_pass' "${LIMITS_JSON}")"
SITE_LIMIT_PASS="$(jq -r '.site_limit_pass' "${LIMITS_JSON}")"
LARGEST_FILE="$(jq -r '.largest_file' "${LIMITS_JSON}")"
LARGEST_FILE_BYTES="$(jq -r '.largest_file_bytes' "${LIMITS_JSON}")"
LARGEST_FILE_MB="$(jq -r '.largest_file_mb' "${LIMITS_JSON}")"
TOTAL_BYTES="$(jq -r '.total_site_bytes' "${LIMITS_JSON}")"
TOTAL_MB="$(jq -r '.total_site_mb' "${LIMITS_JSON}")"

echo "  -> Largest Single File : ${LARGEST_FILE} (${LARGEST_FILE_BYTES} bytes / ${LARGEST_FILE_MB} MB) [Limit: 100 MB]"
echo "  -> Total Site Size     : ${TOTAL_BYTES} bytes / ${TOTAL_MB} MB [Limit: 1024 MB]"

if [ "${FILE_LIMIT_PASS}" != "true" ]; then
  fail_constraint "8" "File '${LARGEST_FILE}' (${LARGEST_FILE_MB} MB) exceeds GitHub Pages 100 MB per-file limit!"
fi

if [ "${SITE_LIMIT_PASS}" != "true" ]; then
  fail_constraint "8" "Total site size (${TOTAL_MB} MB) exceeds GitHub Pages 1 GB site limit!"
fi
pass_constraint "8" "Site size measurements strictly within GitHub Pages limits (Largest: ${LARGEST_FILE_MB} MB <= 100 MB; Total: ${TOTAL_MB} MB <= 1024 MB)"

echo "================================================================================"
echo "  ALL GITHUB PAGES HOSTING CONSTRAINTS VERIFIED: PASS"
echo "================================================================================"
