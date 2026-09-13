# Gate G7: Browser-Hosting Constraint Verification

## Executive Summary

This report documents the mechanical verification of GitHub Pages deployment and browser-hosting constraints for client-side WebAssembly execution in ROOT Kata.

Verification was performed in two phases:
1. **Phase 1 (Baseline Validation):** The constraint-checking harness (`wasm/gates/g7/verify-hosting-constraints.sh`) was validated against the known-good G2 web target (`wasm/build/g2/web`). All constraints passed.
2. **Phase 2 (Candidate Verification):** The identical constraint-checking harness was executed against Lead A's G7 candidate build (`wasm/build/g7/web`, xeus-cpp-lite / CppInterOp) **twice consecutively from a completely clean state** (`rm -rf wasm/build/g7` before each build and test run). Both clean-state runs passed all constraints completely.

**Final Verdict: PASS across all hosting constraints.**

Codex's independent review subsequently added the missing `-fwasm-exceptions`
interpreter flag after proving that ordinary G2 execution passed without it but a real
throw/catch side module did not load. The amended static payload is 27 bytes larger
(104,369,411 bytes total); all hosting conclusions and limits remain unchanged.

---

## Hosting Constraints Specification

Every execution of the verification harness tests all eight of the following constraints:

| # | Constraint | Verification Mechanism | Status (G2 Baseline) | Status (G7 Candidate) |
|---|---|---|:---:|:---:|
| 1 | **Static HTTP only** (no dynamic backend of any kind) | Pure static file serving via `python3 -m http.server`; absence of server-side executable scripts | **PASS** | **PASS** |
| 2 | **No `/api/run` or compile-server endpoint reachable** | HTTP `curl -s -o /dev/null -w "%{http_code}" /api/run` returns 404; static assets contain no active `/api/run` fetch calls | **PASS** | **PASS** |
| 3 | **No server-side compilation in request path** | Server is unprivileged static file process; zero compiler subprocesses (`g++`, `clang++`, `em++`, `root-config`) spawned during browser run | **PASS** | **PASS** |
| 4 | **No COOP/COEP headers set or required** | Verified `.github/workflows/pages.yml` (standard `upload-pages-artifact` + `deploy-pages`); HTTP response headers verified to contain no `Cross-Origin-Opener-Policy` or `Cross-Origin-Embedder-Policy`; `window.crossOriginIsolated` confirmed `false` in Chromium | **PASS** | **PASS** |
| 5 | **No `SharedArrayBuffer` dependency** | All `.wasm` and `.so` binaries parsed for WebAssembly memory flags (`shared` bit = 0); `window.SharedArrayBuffer` explicitly deleted via `Page.addScriptToEvaluateOnNewDocument` prior to script execution | **PASS** | **PASS** |
| 6 | **Runs correctly in headless Chromium** | Driven in headless Chromium via Chrome DevTools Protocol (CDP); reaches `<title>*-DONE</title>`; extracted stdout matches `expected.txt` byte-for-byte | **PASS** (360 ms) | **PASS** (~7.5–10.3 s) |
| 7 | **Network requests restricted to static assets on serving origin** | Complete network log captured via CDP (`Network.requestWillBeSent` & `Network.responseReceived`); every request checked for origin match, static file existence, 0 cross-origin requests, 0 compile API requests | **PASS** (4/4 static) | **PASS** (9/9 static) |
| 8 | **Meets GitHub Pages published size limits** | Measured against GitHub Pages limits: max 100 MB per committed file, soft 1 GB total site size guidance | **PASS** (Max: 0.036 MB, Total: 0.047 MB) | **PASS** (Max: 67.96 MB, Total: 99.53 MB) |

---

## Verification Tooling Architecture

The constraint checker is implemented in two standalone, reusable scripts:
- `wasm/gates/g7/verify-hosting-constraints.sh`: the top-level bash harness orchestrating server startup, endpoint probes, header checks, binary inspection, CDP execution, and limits verification.
- `wasm/gates/g7/hosting_driver.mjs`: a dependency-free Node.js script using Node's built-in `fetch` and global `WebSocket` (zero npm dependencies) to drive headless Chromium over CDP.
- `wasm/gates/g7/check_constraints.py`: a Python 3 helper performing WebAssembly binary header parsing (inspecting memory section flags), calculating file size metrics, and validating the captured network log JSON.

### Why Chrome DevTools Protocol (CDP) was selected over `--dump-dom`
In `wasm/gates/common/run-wasm-program.sh`, G0 and G2 run via `chromium --headless --virtual-time-budget=10000 --dump-dom`. However, as documented by Lead A, G7 loads ~100 MB of WebAssembly and data. Chromium's virtual time budget fast-forwards through idle CPU time during large localhost fetches, dumping the DOM before network completion. Furthermore, `--dump-dom` cannot intercept the network stream or remove `SharedArrayBuffer` prior to script evaluation.
The CDP driver connects directly to Chromium's DevTools WebSocket, enables `Network`, `Page`, and `Runtime` domains, intercepts all network requests with exact timestamps and headers, deletes `SharedArrayBuffer` before DOM construction, and polls `document.title` until completion.

---

## Phase 1: Baseline Validation against G2

The harness was first validated against the proven G2 WebAssembly browser target (`wasm/build/g2/web`):

```bash
bash wasm/gates/g7/verify-hosting-constraints.sh wasm/build/g2/web wasm/gates/g2/expected.txt
```

### Results
- **Execution:** Headless Chromium reached `G2-DONE` in 360 ms.
- **`window.crossOriginIsolated`:** `false`.
- **`typeof window.SharedArrayBuffer`:** `undefined` (explicitly removed; program executed without error).
- **Correctness:** Captured stdout byte-for-byte identical to `wasm/gates/g2/expected.txt`:
  ```
  pt=50.000000 eta=1.200000 phi=0.500000 m=0.105658
  E=90.532840 px=43.879128 py=23.971277 pz=75.473068
  sum_m=54.847433 sum_pt=52.238727
  ```
- **Network Requests:** 4 total requests, 100% same-origin, 0 cross-origin:
  | URL | Method | Type | HTTP Status | Mime Type |
  |---|---|---|:---:|---|
  | `http://127.0.0.1:35207/index.html` | GET | Document | 200 | `text/html` |
  | `http://127.0.0.1:35207/genvector.js` | GET | Script | 200 | `text/javascript` |
  | `http://127.0.0.1:35207/genvector.wasm` | GET | Fetch | 200 | `application/wasm` |
  | `http://127.0.0.1:35207/favicon.ico` | GET | Other | 404 | `text/html` (benign browser probe) |

- **GitHub Pages Limits:**
  - Largest file: `genvector.wasm` — **38,262 bytes (0.036 MB)** [Limit: 100 MB] -> **PASS**
  - Total site size: **48,952 bytes (0.047 MB)** [Limit: 1024 MB] -> **PASS**

Phase 1 confirmed that the verification harness reliably exercises and validates all constraints.

---

## Phase 2: Candidate Verification against G7 (xeus-cpp-lite)

The identical verification harness was run against Lead A's G7 candidate build (`wasm/build/g7/web`).
To satisfy G7 acceptance criterion #8, the check was run **twice consecutively from a completely clean state**:

```bash
# Clean reproduction run 1
rm -rf wasm/build/g7
bash wasm/gates/g7/run.sh
bash wasm/gates/g7/verify-hosting-constraints.sh wasm/build/g7/web wasm/gates/g7/expected.txt 120

# Clean reproduction run 2
rm -rf wasm/build/g7
bash wasm/gates/g7/run.sh
bash wasm/gates/g7/verify-hosting-constraints.sh wasm/build/g7/web wasm/gates/g7/expected.txt 120
```

### Clean Reproduction Run 1 Results
- **Build Status:** `G7 PASS`
- **Elapsed execution in Chromium:** 7,583 ms
- **Final Title:** `G7-DONE`
- **`window.crossOriginIsolated`:** `false`
- **`typeof window.SharedArrayBuffer`:** `undefined`
- **Output Diff:** `diff -u wasm/gates/g7/expected.txt hosting_stdout.txt` -> identical (0 diff bytes)
- **Constraint Verdict:** ALL 8 CONSTRAINTS PASSED

### Clean Reproduction Run 2 Results
- **Build Status:** `G7 PASS`
- **Elapsed execution in Chromium:** 10,328 ms
- **Final Title:** `G7-DONE`
- **`window.crossOriginIsolated`:** `false`
- **`typeof window.SharedArrayBuffer`:** `undefined`
- **Output Diff:** `diff -u wasm/gates/g7/expected.txt hosting_stdout.txt` -> identical (0 diff bytes)
- **Constraint Verdict:** ALL 8 CONSTRAINTS PASSED

---

## Network Request Log Evidence (G7 Candidate)

The actual Chromium network request log captured via CDP during page load and client-side compilation in Run 1 (`hosting_network_requests.json`) is presented below:

```json
[
  {
    "requestId": "41397FE65A810EFDE8BB920FE129E854",
    "url": "http://127.0.0.1:40095/index.html",
    "method": "GET",
    "type": "Document",
    "initiator": "other",
    "status": 200,
    "mimeType": "text/html"
  },
  {
    "requestId": "748503.2",
    "url": "http://127.0.0.1:40095/headers.js",
    "method": "GET",
    "type": "Script",
    "initiator": "parser",
    "status": 200,
    "mimeType": "text/javascript"
  },
  {
    "requestId": "748503.3",
    "url": "http://127.0.0.1:40095/payload.js",
    "method": "GET",
    "type": "Script",
    "initiator": "parser",
    "status": 200,
    "mimeType": "text/javascript"
  },
  {
    "requestId": "748503.4",
    "url": "http://127.0.0.1:40095/xcpp.js",
    "method": "GET",
    "type": "Script",
    "initiator": "parser",
    "status": 200,
    "mimeType": "text/javascript"
  },
  {
    "requestId": "748503.8",
    "url": "http://127.0.0.1:40095/xcpp.data",
    "method": "GET",
    "type": "Fetch",
    "initiator": "script",
    "status": 200,
    "mimeType": "application/octet-stream"
  },
  {
    "requestId": "748503.9",
    "url": "http://127.0.0.1:40095/xcpp.wasm",
    "method": "GET",
    "type": "Fetch",
    "initiator": "script",
    "status": 200,
    "mimeType": "application/wasm"
  },
  {
    "requestId": "748503.10",
    "url": "http://127.0.0.1:40095/libxeus.so",
    "method": "GET",
    "type": "Fetch",
    "initiator": "script",
    "status": 200,
    "mimeType": "application/octet-stream"
  },
  {
    "requestId": "748503.11",
    "url": "http://127.0.0.1:40095/favicon.ico",
    "method": "GET",
    "type": "Other",
    "initiator": "other",
    "status": 404,
    "mimeType": "text/html"
  },
  {
    "requestId": "748503.12",
    "url": "http://127.0.0.1:40095/libclangCppInterOp.so",
    "method": "GET",
    "type": "Fetch",
    "initiator": "script",
    "status": 200,
    "mimeType": "application/octet-stream"
  }
]
```

### Analysis of Network Traffic
1. **Zero Dynamic Requests:** No requests were made to `/api/run`, `/api/exercises`, or any compile-server backend.
2. **Zero Cross-Origin Requests:** All 9 requests targeted the serving origin `http://127.0.0.1:40095`. There were no external CDN calls, telemetry, or remote services contacted.
3. **Pure Static Asset Mapping:** Every requested resource (excluding the standard browser probe for `/favicon.ico`) directly resolved to a static file located on disk in the staged directory.

---

## Detailed GitHub Pages Published Limits Measurement

GitHub Pages enforces:
- **100 MB maximum per committed file** (hard limit on GitHub git push and release assets).
- **1 GB soft guidance total site size** (recommended maximum size of the published static deployment).

The G7 candidate web target was measured file by file using `check_constraints.py limits`:

| File | Exact Bytes | Size (MiB) | Size (MB, dec) | Exceeds 100 MB Limit? |
|---|---|---|---|:---:|
| `libclangCppInterOp.so` | 71,256,623 | 67.956 MiB | 71.26 MB | **NO** (Passes with 28.74 MB headroom) |
| `xcpp.data` | 26,074,947 | 24.867 MiB | 26.07 MB | **NO** (Passes with 73.93 MB headroom) |
| `headers.js` | 2,308,595 | 2.202 MiB | 2.31 MB | **NO** |
| `xcpp.wasm` | 2,240,059 | 2.136 MiB | 2.24 MB | **NO** |
| `xcpp.js` | 2,193,469 | 2.092 MiB | 2.19 MB | **NO** |
| `libxeus.so` | 289,063 | 0.276 MiB | 0.29 MB | **NO** |
| `index.html` | 5,463 | 0.005 MiB | < 0.01 MB | **NO** |
| `payload.js` | 1,165 | 0.001 MiB | < 0.01 MB | **NO** |
| **TOTAL SITE SIZE** | **104,369,384** | **99.534 MiB** | **104.37 MB** | **NO** (Passes within 1 GB limit with ~895 MB headroom) |

### Findings on Size
- **Largest committed file:** `libclangCppInterOp.so` is **71,256,623 bytes (67.96 MiB / 71.26 MB)**, which is strictly less than the 100 MB (104,857,600 bytes) limit. It can be safely committed to git without Git LFS or repository rejection.
- **Total static site size:** The complete staged bundle is **104,369,384 bytes (99.53 MiB / 104.37 MB)**, which represents less than 10% of the 1 GB GitHub Pages site guideline.

---

## Verification of COOP/COEP and GitHub Pages Workflow

Analysis of `.github/workflows/pages.yml`:
```yaml
      - name: Upload static site
        uses: actions/upload-pages-artifact@v4
        with:
          path: docs
      - name: Deploy Pages
        id: deployment
        uses: actions/deploy-pages@v4
```

- `actions/upload-pages-artifact@v4` packages the static site directory into a tarball and uploads it as a GitHub Pages artifact.
- `actions/deploy-pages@v4` deploys the artifact to GitHub's static hosting infrastructure.
- GitHub Pages static hosting serves assets through Fastly/GitHub CDN and does **not** allow configuring custom HTTP headers such as `Cross-Origin-Opener-Policy` (COOP) or `Cross-Origin-Embedder-Policy` (COEP).
- As proven by the G7 execution with `SharedArrayBuffer` removed and `window.crossOriginIsolated == false`, the xeus-cpp-lite toolchain does **not** rely on COOP/COEP or cross-origin isolation. It functions completely under standard static hosting.

---

## Conclusion and Gate G7 Verdict

All hosting constraints required for GitHub Pages deployment have been mechanically verified:
1. Pure static HTTP hosting verified.
2. No backend server or `/api/run` dependency verified.
3. No server-side compilation in the request path verified.
4. No COOP/COEP headers required verified.
5. No SharedArrayBuffer or cross-origin-isolation dependency verified.
6. Execution in headless Chromium verified (byte-exact match to expected output).
7. All network requests strictly confined to static origin assets verified with captured CDP network logs.
8. File size and site size strictly comply with published GitHub Pages limits.
9. Verified twice consecutively from clean state.

**Verdict: Gate G7 hosting constraints PASSED.**
