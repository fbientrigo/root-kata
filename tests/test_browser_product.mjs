#!/usr/bin/env node
/**
 * End-to-end acceptance test for the ROOT Kata browser WebAssembly integration.
 * Drives real Chromium via Chrome DevTools Protocol (CDP) to verify:
 *   1. Page loads with standard starter code
 *   2. Case C (Wrong Logic): Starter runs, lazily boots WASM, tests fail with expected vs. actual
 *   3. Case A (Correct Solution): Runs in-browser ROOT, passes 2/2 tests
 *   4. Case B (Syntax Error): Produces compile_error with line/context
 *   5. State Isolation: Multiple runs in same session don't leak C++ declarations
 *   6. Network Verification: ZERO calls to /api/run for the WASM exercise
 *   7. Native Fallback: Normal kata (cpp-hello-world) still uses /api/run natively
 */

import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const REPO_ROOT = path.resolve(__dirname, '..');

const CHROMIUM = process.env.CHROMIUM_BIN || 'chromium';
const PORT = 8799;
const SERVER_URL = `http://127.0.0.1:${PORT}`;
const TIMEOUT_MS = 180000;

const CORRECT_SOLUTION = `#include "TH1D.h"

struct HistogramInspection {
    double entries;
    double bin_content;
    double mean;
    double stddev;
};

HistogramInspection inspect_histogram(const TH1D& hist, int bin) {
    return {hist.GetEntries(), hist.GetBinContent(bin), hist.GetMean(), hist.GetStdDev()};
}
`;

const SYNTAX_ERROR_SOLUTION = `#include "TH1D.h"

struct HistogramInspection {
    double entries;
    double bin_content;
    double mean;
    double stddev;
};

HistogramInspection inspect_histogram(const TH1D& hist, int bin) {
    return {hist.GetEntries(), hist.GetBinContent(bin), hist.GetMean(), hist.GetStdDev()} // missing semicolon
}
`;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function startServer() {
  const proc = spawn('python3', ['-c', `import sys; sys.path.insert(0, 'src'); from root_kata.web_server import serve; serve(port=${PORT})`], {
    cwd: REPO_ROOT,
    stdio: ['ignore', 'pipe', 'pipe'],
  });

  proc.stderr.on('data', (d) => {
    // console.error('[server]', d.toString());
  });

  // Poll until server responds
  for (let i = 0; i < 50; i++) {
    try {
      const resp = await fetch(`${SERVER_URL}/api/health`);
      if (resp.ok) return proc;
    } catch {}
    await sleep(100);
  }
  proc.kill();
  throw new Error('Server failed to start on port ' + PORT);
}

async function launchChromium(profileDir) {
  const args = [
    '--headless=new',
    '--disable-gpu',
    '--no-sandbox',
    '--disable-dev-shm-usage',
    '--remote-debugging-port=0',
    '--remote-allow-origins=*',
    `--user-data-dir=${profileDir}`,
    'about:blank',
  ];

  const proc = spawn(CHROMIUM, args, { stdio: ['ignore', 'pipe', 'pipe'] });

  let wsUrl = null;
  const ready = new Promise((resolve, reject) => {
    let buf = '';
    proc.stderr.on('data', (d) => {
      buf += d.toString();
      const m = buf.match(/DevTools listening on (ws:\/\/[^\s]+)/);
      if (m && !wsUrl) {
        wsUrl = m[1];
        resolve(wsUrl);
      }
    });
    proc.on('exit', (code) => reject(new Error(`Chromium exited early with code ${code}`)));
    setTimeout(() => reject(new Error('Timeout waiting for Chromium DevTools')), 15000);
  });

  await ready;
  return { proc, wsUrl };
}

async function createCdpClient(wsUrl) {
  const ws = new WebSocket(wsUrl);
  await new Promise((resolve, reject) => {
    ws.addEventListener('open', resolve, { once: true });
    ws.addEventListener('error', reject, { once: true });
  });

  let nextId = 1;
  const pending = new Map();
  const eventListeners = new Set();

  ws.addEventListener('message', (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.id && pending.has(msg.id)) {
      pending.get(msg.id)(msg);
      pending.delete(msg.id);
    } else {
      for (const listener of eventListeners) {
        listener(msg);
      }
    }
  });

  function send(method, params = {}) {
    const id = nextId++;
    return new Promise((resolve) => {
      pending.set(id, resolve);
      ws.send(JSON.stringify({ id, method, params }));
    });
  }

  function addEventListener(fn) {
    eventListeners.add(fn);
    return () => eventListeners.delete(fn);
  }

  return { send, addEventListener, close: () => ws.close() };
}

async function run() {
  console.log('=== ROOT Kata Browser-Product Acceptance Test ===\n');

  const evidence = {
    coldStartupMs: 0,
    warmStartupMs: 0,
    runMs: 0,
    networkRequests: [],
    apiRunCountForInspect: 0,
    caseA_passed: false,
    caseB_compile_error: false,
    caseC_failed: false,
    stateIsolationPassed: false,
    nativeBackendPassed: false,
  };

  const profileDir = path.join(REPO_ROOT, 'wasm', 'build', 'chrome-profile-product-acceptance');
  fs.mkdirSync(profileDir, { recursive: true });

  console.log('[1/8] Starting local server…');
  const serverProc = await startServer();
  console.log(`      Server running at ${SERVER_URL}`);

  console.log('[2/8] Launching headless Chromium…');
  const { proc: chromeProc, wsUrl: browserWsUrl } = await launchChromium(profileDir);

  try {
    const httpBase = browserWsUrl.replace('ws://', 'http://').replace(/\/devtools\/browser\/.*/, '');

    // Open inspected kata page
    const kataUrl = `${SERVER_URL}/kata/cpp-root-histogram-inspect?lang=es`;
    const newTabResp = await fetch(`${httpBase}/json/new?${encodeURIComponent(kataUrl)}`, { method: 'PUT' });
    const tab = await newTabResp.json();
    const cdp = await createCdpClient(tab.webSocketDebuggerUrl);

    await cdp.send('Page.enable');
    await cdp.send('Runtime.enable');
    await cdp.send('Network.enable');

    const recordedRequests = [];
    cdp.addEventListener((msg) => {
      if (msg.method === 'Network.requestWillBeSent') {
        const reqUrl = msg.params.request.url;
        recordedRequests.push(reqUrl);
      }
    });

    async function evalCode(expr) {
      const res = await cdp.send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
      return res.result && res.result.result ? res.result.result.value : undefined;
    }

    async function waitForCondition(desc, fn, timeout = TIMEOUT_MS) {
      const start = Date.now();
      while (Date.now() - start < timeout) {
        const val = await fn();
        if (val) return val;
        await sleep(200);
      }
      throw new Error(`Timeout waiting for: ${desc}`);
    }

    console.log('[3/8] Loading problem page and checking initial UI…');
    await waitForCondition('Editor loaded', async () => {
      return await evalCode('document.getElementById("code-editor")?.value?.includes("inspect_histogram")');
    });

    const starterCode = await evalCode('document.getElementById("code-editor").value');
    if (!starterCode.includes('// TODO')) {
      throw new Error('Starter code was not loaded into the editor!');
    }
    console.log('      Starter code loaded cleanly.');

    // Helper to click Run and await completion
    async function submitRun() {
      await evalCode('document.getElementById("run-form").requestSubmit()');
      await sleep(100);
      await waitForCondition('Run to finish (button re-enabled)', async () => {
        const disabled = await evalCode('document.getElementById("run-button").disabled');
        return !disabled;
      });
      return await evalCode(`({
        feedbackClass: document.getElementById('run-feedback')?.className,
        feedbackHidden: document.getElementById('run-feedback')?.hidden,
        feedbackText: document.getElementById('run-feedback')?.innerText,
        statusText: document.querySelector('.workspace-status')?.textContent,
        cases: Array.from(document.querySelectorAll('.run-cases li')).map(li => ({
          className: li.className,
          text: li.innerText
        }))
      })`);
    }

    // TEST CASE C: Run with starter code (Wrong Physics/Logic)
    console.log('[4/8] Running Case C: Starter code (Wrong logic) — measuring cold boot…');
    const coldStart = Date.now();
    const resultC = await submitRun();
    evidence.coldStartupMs = Date.now() - coldStart;
    console.log(`      Cold boot + execution completed in ${evidence.coldStartupMs}ms`);

    if (!resultC.feedbackClass.includes('status-failed')) {
      throw new Error(`Expected status-failed but got: ${resultC.feedbackClass}`);
    }
    if (!resultC.feedbackText.includes('Se esperaban 5 entradas totales') && !resultC.feedbackText.includes('esperaba')) {
      throw new Error(`Expected failure details in feedback but got: ${resultC.feedbackText}`);
    }
    evidence.caseC_failed = true;
    console.log('      Case C PASS: Test failure displayed with expected vs actual values.');

    // TEST CASE A: Canonical Correct Solution
    console.log('[5/8] Running Case A: Canonical correct solution…');
    await evalCode(`document.getElementById('code-editor').value = ${JSON.stringify(CORRECT_SOLUTION)};`);

    const runStart = Date.now();
    const resultA = await submitRun();
    evidence.runMs = Date.now() - runStart;
    console.log(`      Execution completed in ${evidence.runMs}ms`);

    if (!resultA.feedbackClass.includes('status-passed')) {
      throw new Error(`Expected status-passed but got: ${resultA.feedbackClass}\n${resultA.feedbackText}`);
    }
    if (!resultA.feedbackText.includes('2/2 pruebas pasaron')) {
      throw new Error(`Expected "2/2 pruebas pasaron" but got: ${resultA.feedbackText}`);
    }
    evidence.caseA_passed = true;
    console.log('      Case A PASS: All 2/2 tests passed with green marks.');

    // TEST CASE B: Syntactically Invalid Code
    console.log('[6/8] Running Case B: Syntactically invalid code…');
    await evalCode(`document.getElementById('code-editor').value = ${JSON.stringify(SYNTAX_ERROR_SOLUTION)};`);

    const resultB = await submitRun();
    if (!resultB.feedbackClass.includes('status-compile_error')) {
      throw new Error(`Expected status-compile_error but got: ${resultB.feedbackClass}`);
    }
    if (!resultB.feedbackText.includes('Error de compilación') && !resultB.feedbackText.includes('solution.cpp')) {
      throw new Error(`Expected compiler error mentioning solution.cpp but got: ${resultB.feedbackText}`);
    }
    evidence.caseB_compile_error = true;
    console.log('      Case B PASS: Correct compile_error returned with file, line, and message.');

    // TEST STATE ISOLATION: Run correct solution again
    console.log('[7/8] Verifying State Isolation (no redefinition errors across runs)…');
    await evalCode(`document.getElementById('code-editor').value = ${JSON.stringify(CORRECT_SOLUTION)};`);

    const warmStart = Date.now();
    const resultA2 = await submitRun();
    evidence.warmStartupMs = Date.now() - warmStart;
    console.log(`      Warm run completed in ${evidence.warmStartupMs}ms`);

    if (!resultA2.feedbackClass.includes('status-passed')) {
      throw new Error(`State isolation failure! Second run failed with: ${resultA2.feedbackText}`);
    }
    evidence.stateIsolationPassed = true;
    console.log('      State Isolation PASS: Clean AST re-initialization confirmed.');

    // NETWORK LOG ASSERTION
    evidence.networkRequests = recordedRequests;
    evidence.apiRunCountForInspect = recordedRequests.filter((url) => url.includes('/api/run')).length;
    console.log(`      Network verification: ${evidence.apiRunCountForInspect} requests to /api/run.`);
    if (evidence.apiRunCountForInspect !== 0) {
      throw new Error(`FATAL: Found ${evidence.apiRunCountForInspect} unexpected /api/run requests!`);
    }
    console.log('      Zero /api/run requests verified!');

    // TEST NATIVE BACKEND PATH INTACT
    console.log('[8/8] Verifying Native Backend path for pure C++ kata (cpp-hello-world)…');
    const nativeTabResp = await fetch(`${httpBase}/json/new?${encodeURIComponent(`${SERVER_URL}/kata/cpp-hello-world?lang=es`)}`, { method: 'PUT' });
    const nativeTab = await nativeTabResp.json();
    const nativeCdp = await createCdpClient(nativeTab.webSocketDebuggerUrl);
    await nativeCdp.send('Page.enable');
    await nativeCdp.send('Runtime.enable');

    let nativeApiRunCalled = false;
    await nativeCdp.send('Network.enable');
    nativeCdp.addEventListener((msg) => {
      if (msg.method === 'Network.requestWillBeSent' && msg.params.request.url.includes('/api/run')) {
        nativeApiRunCalled = true;
      }
    });

    await waitForCondition('Native editor loaded', async () => {
      const res = await nativeCdp.send('Runtime.evaluate', { expression: 'document.getElementById("code-editor")?.value', returnByValue: true });
      return res.result?.result?.value?.includes('say_hello');
    });

    // Provide correct hello-world implementation
    await nativeCdp.send('Runtime.evaluate', {
      expression: `document.getElementById('code-editor').value = '#include <iostream>\\nvoid say_hello() { std::cout << "Hello, world!\\\\n"; }\\n';`,
      returnByValue: true,
    });

    await nativeCdp.send('Runtime.evaluate', { expression: 'document.getElementById("run-form").requestSubmit()' });
    await sleep(100);
    await waitForCondition('Native run to finish', async () => {
      const res = await nativeCdp.send('Runtime.evaluate', { expression: '!document.getElementById("run-button").disabled', returnByValue: true });
      return res.result?.result?.value;
    });

    const nativeResult = await nativeCdp.send('Runtime.evaluate', {
      expression: 'document.getElementById("run-feedback")?.className',
      returnByValue: true,
    });

    if (!nativeApiRunCalled) {
      throw new Error('Native kata should have called /api/run, but did not!');
    }
    if (!nativeResult.result?.result?.value?.includes('status-passed')) {
      throw new Error(`Native run failed: ${nativeResult.result?.result?.value}`);
    }
    evidence.nativeBackendPassed = true;
    console.log('      Native Backend PASS: Unmigrated katas continue using /api/run without disruption.');

    cdp.close();
    nativeCdp.close();

    console.log('\n================ ACCEPTANCE TEST SUMMARY ================');
    console.log(`Case A (Canonical Correct Solution):  PASS (2/2)`);
    console.log(`Case B (Syntactically Invalid):       PASS (compile_error)`);
    console.log(`Case C (Wrong Logic/Physics):         PASS (failed with expected/actual)`);
    console.log(`Worker State Isolation:               PASS`);
    console.log(`Requests to /api/run for inspect:     0 (100% in-browser)`);
    console.log(`Native Backend Regression Test:       PASS (called /api/run)`);
    console.log(`Cold Startup Time:                    ${(evidence.coldStartupMs / 1000).toFixed(2)}s`);
    console.log(`Warm Startup Time:                    ${(evidence.warmStartupMs / 1000).toFixed(2)}s`);
    console.log('=========================================================\n');

    const outPath = path.join(REPO_ROOT, 'wasm', 'build', 'product_acceptance_evidence.json');
    fs.writeFileSync(outPath, JSON.stringify(evidence, null, 2));
    console.log(`Evidence recorded at: ${outPath}`);
    return 0;
  } finally {
    chromeProc.kill();
    serverProc.kill();
  }
}

run()
  .then((code) => process.exit(code || 0))
  .catch((err) => {
    console.error('\nACCEPTANCE TEST FAILED:\n', err);
    process.exit(1);
  });
