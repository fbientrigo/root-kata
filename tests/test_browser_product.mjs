#!/usr/bin/env node
import { spawn, spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const REPO_ROOT = path.resolve(__dirname, '..');
const CHROMIUM = process.env.CHROMIUM_BIN || 'chromium';
const PORT = 8799;
const SERVER_URL = 'http://127.0.0.1:' + PORT;
const TIMEOUT_MS = 180000;

const SOLUTIONS = {
  'cpp-hello-world': '#include <iostream>\nvoid say_hello() { std::cout << "Hello, world!\\n"; }\n',
  'cpp-array-index': 'int second_value() {\n    int values[3] = {10, 20, 30};\n    return values[1];\n}\n',
  'cpp-array-print': '#include <iostream>\nvoid print_values() {\n    int values[3] = {4, 8, 15};\n    for (int value : values) std::cout << value << " ";\n}\n',
  'cpp-sum-positive': '#include <vector>\ndouble sum_positive(const std::vector<double>& values) {\n    double total = 0.0;\n    for (double value : values) if (value > 0.0) total += value;\n    return total;\n}\n',
  'cpp-count-above': '#include <vector>\nint count_above(const std::vector<double>& values, double threshold) {\n    int count = 0;\n    for (double value : values) if (value > threshold) ++count;\n    return count;\n}\n',
  'cpp-root-histogram': '#include <vector>\n#include "TH1D.h"\nTH1D* build_histogram(const std::vector<double>& values) {\n    auto* hist = new TH1D("h_pt", "h_pt", 10, 0.0, 100.0);\n    for (double value : values) hist->Fill(value);\n    return hist;\n}\n',
  'cpp-root-histogram-inspect': '#include "TH1D.h"\nstruct HistogramInspection {\n    double entries;\n    double bin_content;\n    double mean;\n    double stddev;\n};\nHistogramInspection inspect_histogram(const TH1D& hist, int bin) {\n    return {hist.GetEntries(), hist.GetBinContent(bin), hist.GetMean(), hist.GetStdDev()};\n}\n',
  'cpp-root-histogram-range': '#include <vector>\n#include "TH1D.h"\nTH1D* build_calibration_histogram(const std::vector<double>& values) {\n    auto* hist = new TH1D("h_calibration", "", 11, 0.0, 110.0);\n    for (double value : values) hist->Fill(value);\n    return hist;\n}\n',
  'cpp-root-histogram-selected-sample': '#include "TH1D.h"\n#include <vector>\nTH1D* build_selected_histogram(const std::vector<double>& values, double threshold) {\n    auto* hist = new TH1D("h_selected", "", 5, 0.0, 150.0);\n    for (double value : values) if (value > threshold) hist->Fill(value);\n    return hist;\n}\n',
  'cpp-root-tgraph-points': '#include "TGraph.h"\n#include <vector>\nTGraph* build_graph(const std::vector<double>& x, const std::vector<double>& y) {\n    return new TGraph(static_cast<int>(x.size()), x.data(), y.data());\n}\n',
  'cpp-root-tf1-evaluate': '#include "TF1.h"\nTF1* build_linear_model(double intercept, double slope) {\n    auto* model = new TF1("calibration_model", "[0] + [1]*x", 0.0, 10.0);\n    model->SetParameters(intercept, slope);\n    return model;\n}\n',
  'cpp-root-tf1-range-parameters': '#include "TF1.h"\nTF1* build_decay_model(double amplitude, double tau) {\n    auto* model = new TF1("decay_model", "[0]*exp(-x/[1])", 0.0, 10.0);\n    model->SetParameters(amplitude, tau);\n    return model;\n}\n'
};

const SYNTAX_ERROR = '#include "TH1D.h"\nstruct HistogramInspection { double entries; double bin_content; double mean; double stddev; };\nHistogramInspection inspect_histogram(const TH1D& hist, int bin) {\n    return {hist.GetEntries(), hist.GetBinContent(bin), hist.GetMean(), hist.GetStdDev()}\n}\n';

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function buildStaticPages() {
  const result = spawnSync('python3', ['scripts/build_pages.py'], { cwd: REPO_ROOT, encoding: 'utf8' });
  if (result.status !== 0) {
    throw new Error('Static page build failed:\n' + result.stdout + '\n' + result.stderr);
  }
}

async function startServer() {
  const proc = spawn('python3', ['-c', 'import sys; sys.path.insert(0, "src"); from root_kata.web_server import serve; serve(port=' + PORT + ')'], {
    cwd: REPO_ROOT,
    stdio: ['ignore', 'pipe', 'pipe']
  });
  for (let i = 0; i < 60; i++) {
    try {
      const resp = await fetch(SERVER_URL + '/api/health');
      if (resp.ok) return proc;
    } catch {}
    await sleep(100);
  }
  proc.kill();
  throw new Error('Server failed to start');
}

async function launchChromium(profileDir) {
  const proc = spawn(CHROMIUM, [
    '--headless=new', '--disable-gpu', '--no-sandbox', '--disable-dev-shm-usage',
    '--remote-debugging-port=0', '--remote-allow-origins=*', '--user-data-dir=' + profileDir, 'about:blank'
  ], { stdio: ['ignore', 'pipe', 'pipe'] });
  let buffer = '';
  const wsUrl = await new Promise((resolve, reject) => {
    proc.stderr.on('data', (data) => {
      buffer += data.toString();
      const match = buffer.match(/DevTools listening on (ws:\/\/[^\s]+)/);
      if (match) resolve(match[1]);
    });
    proc.on('exit', (code) => reject(new Error('Chromium exited early with ' + code)));
    setTimeout(() => reject(new Error('Timeout waiting for Chromium')), 15000);
  });
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
  const listeners = new Set();
  ws.addEventListener('message', (event) => {
    const msg = JSON.parse(event.data);
    if (msg.id && pending.has(msg.id)) {
      pending.get(msg.id)(msg);
      pending.delete(msg.id);
    } else {
      for (const listener of listeners) listener(msg);
    }
  });
  const send = (method, params = {}) => {
    const id = nextId++;
    return new Promise((resolve) => {
      pending.set(id, resolve);
      ws.send(JSON.stringify({ id, method, params }));
    });
  };
  return {
    send,
    addEventListener(fn) { listeners.add(fn); return () => listeners.delete(fn); },
    close() { ws.close(); }
  };
}

async function run() {
  buildStaticPages();
  const serverProc = await startServer();
  const profileDir = path.join(REPO_ROOT, 'wasm', 'build', 'chrome-profile-product-acceptance');
  fs.mkdirSync(profileDir, { recursive: true });
  const launched = await launchChromium(profileDir);
  const chromeProc = launched.proc;
  try {
    const httpBase = launched.wsUrl.replace('ws://', 'http://').replace(/\/devtools\/browser\/.*/, '');

    async function openPage(relativePath) {
      const url = SERVER_URL + relativePath;
      const resp = await fetch(httpBase + '/json/new?' + encodeURIComponent(url), { method: 'PUT' });
      const tab = await resp.json();
      const cdp = await createCdpClient(tab.webSocketDebuggerUrl);
      await cdp.send('Page.enable');
      await cdp.send('Runtime.enable');
      await cdp.send('Network.enable');
      const requests = [];
      cdp.addEventListener((msg) => {
        if (msg.method === 'Network.requestWillBeSent') requests.push(msg.params.request.url);
      });
      const evalCode = async (expression) => {
        const res = await cdp.send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
        return res.result && res.result.result ? res.result.result.value : undefined;
      };
      const waitFor = async (description, fn, timeout = TIMEOUT_MS) => {
        const started = Date.now();
        while (Date.now() - started < timeout) {
          const value = await fn();
          if (value) return value;
          await sleep(200);
        }
        throw new Error('Timeout waiting for ' + description);
      };
      await waitFor('page ready', () => evalCode('document.readyState === "complete"'));
      return { cdp, evalCode, waitFor, requests };
    }

    async function submit(page, code) {
      await page.evalCode('(() => { const editor = document.getElementById("code-editor"); editor.value = ' + JSON.stringify(code) + '; editor.dispatchEvent(new Event("input", {bubbles:true})); return true; })()');
      await page.evalCode('document.getElementById("run-form").requestSubmit(); true');
      await sleep(100);
      await page.waitFor('run complete', () => page.evalCode('!document.getElementById("run-button").disabled'));
      return page.evalCode('({cls: document.getElementById("run-feedback")?.className || "", text: document.getElementById("run-feedback")?.innerText || "", status: document.querySelector(".workspace-status")?.textContent || ""})');
    }

    console.log('[1/5] Dashboard and solve routing');
    const dashboard = await openPage('/');
    const dashboardContract = await dashboard.evalCode('({solveCount: document.querySelectorAll(".browser-solve-link").length, helloHref: document.querySelector("[data-eid=\\"cpp-hello-world\\"] .browser-solve-link")?.getAttribute("href"), gaussianHasSolve: !!document.querySelector("[data-eid=\\"cpp-root-fit-gaussian\\"] .browser-solve-link"), visibleJupyter: document.querySelectorAll(".jupyter-opt-in:not([hidden])").length})');
    if (dashboardContract.solveCount !== 12) throw new Error('Expected 12 solve CTAs, got ' + dashboardContract.solveCount);
    if (dashboardContract.helloHref !== 'solve/cpp-hello-world.html') throw new Error('Unexpected hello solve href: ' + dashboardContract.helloHref);
    if (dashboardContract.gaussianHasSolve) throw new Error('Gaussian fit must remain outside WASM support');
    if (dashboardContract.visibleJupyter !== 0) throw new Error('Jupyter must be hidden by default');
    dashboard.cdp.close();

    console.log('[2/5] Full-screen desktop workspace + diagnostics');
    const inspect = await openPage('/solve/cpp-root-histogram-inspect.html');
    await inspect.waitFor('solve editor', () => inspect.evalCode('document.getElementById("code-editor")?.value?.includes("inspect_histogram")'));
    await inspect.waitFor('Prism C++ highlighting', () => inspect.evalCode('document.querySelector(".syntax-editor-shell.syntax-highlighted") && document.querySelector("#code-highlight .token.keyword") && document.querySelector("#code-highlight .token.root-api")'));
    const highlighting = await inspect.evalCode('({root: document.querySelector("#code-highlight .token.root-api")?.textContent, sourceMatches: document.querySelector("#code-highlight code")?.textContent === document.getElementById("code-editor")?.value})');
    if (highlighting.root !== 'TH1D' || !highlighting.sourceMatches) throw new Error('Prism/ROOT highlighting is not synchronized: ' + JSON.stringify(highlighting));

    const layout = await inspect.evalCode('({hasGrid: !!document.querySelector(".solve-workspace"), hasProblem: !!document.getElementById("solve-problem"), hasToggle: !!document.getElementById("problem-toggle"), hasOutputToggle: !!document.getElementById("output-toggle"), hasOutputResizer: !!document.getElementById("output-resizer"), jupyterHidden: document.querySelector(".jupyter-opt-in")?.hidden === true, editorRadius: getComputedStyle(document.getElementById("code-editor")).borderRadius, runRadius: getComputedStyle(document.getElementById("run-button")).borderRadius})');
    if (!layout.hasGrid || !layout.hasProblem || !layout.hasToggle || !layout.hasOutputToggle || !layout.hasOutputResizer) throw new Error('Solve layout is incomplete');
    if (!layout.jupyterHidden) throw new Error('Jupyter should be hidden on solve page by default');
    if (layout.editorRadius !== '0px' || layout.runRadius !== '0px') throw new Error('Solve workspace must be square-edged: ' + JSON.stringify(layout));

    await inspect.evalCode('document.getElementById("run-form").requestSubmit(); true');
    await inspect.waitFor('starter run', () => inspect.evalCode('!document.getElementById("run-button").disabled'));
    const failedClass = await inspect.evalCode('document.getElementById("run-feedback").className');
    if (!failedClass.includes('status-failed')) throw new Error('Starter should fail visibly, got ' + failedClass);

    const correctInspect = await submit(inspect, SOLUTIONS['cpp-root-histogram-inspect']);
    if (!correctInspect.cls.includes('status-passed')) throw new Error('Inspect correct solution failed:\n' + correctInspect.text);
    await inspect.waitFor('highlight update after edit', () => inspect.evalCode('document.querySelector("#code-highlight code")?.textContent === document.getElementById("code-editor")?.value'));
    const syntaxResult = await submit(inspect, SYNTAX_ERROR);
    if (!syntaxResult.cls.includes('status-compile_error') || !syntaxResult.text.includes('solution.cpp')) {
      throw new Error('Compile diagnostics lost solution.cpp context:\n' + syntaxResult.text);
    }
    if (inspect.requests.some((url) => url.includes('/api/run'))) throw new Error('WASM solve page called /api/run');

    await inspect.evalCode('(() => { const editor = document.getElementById("code-editor"); editor.focus(); editor.setSelectionRange(5, 5); return editor.selectionStart; })()');
    await inspect.cdp.send('Input.dispatchKeyEvent', {type: 'keyDown', key: 'ArrowRight', code: 'ArrowRight', windowsVirtualKeyCode: 39, nativeVirtualKeyCode: 39});
    await inspect.cdp.send('Input.dispatchKeyEvent', {type: 'keyUp', key: 'ArrowRight', code: 'ArrowRight', windowsVirtualKeyCode: 39, nativeVirtualKeyCode: 39});
    const caretAfterArrow = await inspect.evalCode('document.getElementById("code-editor").selectionStart');
    if (caretAfterArrow !== 6) throw new Error('Editor arrow key was intercepted; caret is ' + caretAfterArrow);

    const splitBefore = await inspect.evalCode('document.getElementById("solve-output").getBoundingClientRect().height');
    await inspect.evalCode('document.getElementById("output-resizer").dispatchEvent(new KeyboardEvent("keydown", {key:"ArrowUp", bubbles:true})); true');
    const splitAfter = await inspect.evalCode('document.getElementById("solve-output").getBoundingClientRect().height');
    if (splitAfter <= splitBefore) throw new Error('Output separator did not resize the grid');

    await inspect.evalCode('document.getElementById("output-toggle").click()');
    if (!await inspect.evalCode('document.querySelector(".solve-code-pane").classList.contains("output-hidden")')) {
      throw new Error('Output pane did not hide');
    }
    await inspect.evalCode('document.getElementById("output-toggle").click()');

    await inspect.evalCode('document.getElementById("problem-toggle").click()');
    if (!await inspect.evalCode('document.querySelector(".solve-workspace").classList.contains("problem-hidden")')) {
      throw new Error('Desktop problem panel did not collapse');
    }

    console.log('[3/5] Mobile editor-first layout');
    await inspect.cdp.send('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
    await inspect.cdp.send('Page.reload', { ignoreCache: true });
    await inspect.waitFor('mobile solve editor', () => inspect.evalCode('!!document.getElementById("code-editor")'));
    const mobile = await inspect.evalCode('({hidden: document.querySelector(".solve-workspace").classList.contains("problem-hidden"), editorWidth: document.getElementById("code-editor").getBoundingClientRect().width, viewport: window.innerWidth})');
    if (!mobile.hidden) throw new Error('Mobile solve page should start editor-first');
    if (mobile.editorWidth < mobile.viewport * 0.9) throw new Error('Mobile editor wastes horizontal space: ' + JSON.stringify(mobile));
    inspect.cdp.close();

    console.log('[4/5] 12/13 katas execute fully in browser WASM');
    let passCount = 0;
    for (const exerciseId of Object.keys(SOLUTIONS)) {
      const page = await openPage('/solve/' + exerciseId + '.html');
      await page.waitFor(exerciseId + ' editor', () => page.evalCode('!!document.getElementById("code-editor")'));
      const result = await submit(page, SOLUTIONS[exerciseId]);
      if (!result.cls.includes('status-passed')) throw new Error(exerciseId + ' did not pass in WASM:\n' + result.text);
      if (page.requests.some((url) => url.includes('/api/run'))) throw new Error(exerciseId + ' unexpectedly called /api/run');
      passCount += 1;
      page.cdp.close();
      console.log('      PASS ' + exerciseId);
    }
    if (passCount !== 12) throw new Error('Expected 12 browser passes, got ' + passCount);

    console.log('[5/5] Jupyter is opt-in and persistent');
    const helloDefault = await openPage('/solve/cpp-hello-world.html?jupyter=0');
    const hiddenDefault = await helloDefault.evalCode('document.querySelector(".jupyter-opt-in")?.hidden === true');
    if (!hiddenDefault) throw new Error('Jupyter should be hidden after explicit disable');
    helloDefault.cdp.close();

    const helloOptIn = await openPage('/solve/cpp-hello-world.html?jupyter=1');
    const jupyter = await helloOptIn.evalCode('({hidden: document.querySelector(".jupyter-link[data-keep-jupyter]")?.hidden, text: document.querySelector(".jupyter-link[data-keep-jupyter]")?.textContent.trim(), href: document.querySelector(".jupyter-link[data-keep-jupyter]")?.getAttribute("href")})');
    if (jupyter.hidden || !jupyter.text || !jupyter.href || !jupyter.href.startsWith('http://127.0.0.1:8888/')) {
      throw new Error('Jupyter opt-in failed: ' + JSON.stringify(jupyter));
    }
    helloOptIn.cdp.close();

    console.log('\nBrowser acceptance PASS: fullscreen solve + 12/13 WASM + zero /api/run.');
    return 0;
  } finally {
    chromeProc.kill();
    serverProc.kill();
  }
}

run().then((code) => process.exit(code || 0)).catch((error) => {
  console.error('\nACCEPTANCE TEST FAILED:\n', error);
  process.exit(1);
});
