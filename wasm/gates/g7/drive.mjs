#!/usr/bin/env node
// Minimal, dependency-free Chrome DevTools Protocol driver for gate G7.
//
// wasm/gates/common/run-wasm-program.sh's pattern (headless chromium +
// --virtual-time-budget + --dump-dom) is designed for already-compiled,
// sub-megabyte wasm payloads (G0, G2). G7's toolchain payload is ~100MB
// (a real prebuilt LLVM/Clang built for wasm32), and --virtual-time-budget
// was observed (see wasm/gates/g7/H1-FINDINGS.md if present, or the gate
// report) to let Chromium fast-forward and dump the DOM before that fetch
// completes, well before the requested budget elapses. This driver instead
// polls document.title over a real Chrome DevTools Protocol WebSocket with a
// real wall-clock timeout, using only Node's built-in fetch/WebSocket (no
// npm dependencies), and only for this gate's browser-driving step.
//
// Usage: node drive.mjs <url> <done-title> <timeout-ms> <chrome-user-data-dir>
// Prints a single JSON object to stdout: { finalTitle, timedOut, elapsedMs, output }
// where `output` is the page's #log text (for diagnostics on failure).
import { spawn } from 'node:child_process';

const CHROMIUM = process.env.CHROMIUM_BIN || 'chromium';
const url = process.argv[2];
const doneTitle = process.argv[3];
const timeoutMs = Number(process.argv[4] || 120000);
const userDataDir = process.argv[5];

if (!url || !doneTitle || !userDataDir) {
  console.error('usage: drive.mjs <url> <done-title> <timeout-ms> <chrome-user-data-dir>');
  process.exit(2);
}

async function main() {
  const args = [
    '--headless=new', '--disable-gpu', '--no-sandbox', '--disable-dev-shm-usage',
    '--remote-debugging-port=0', '--remote-allow-origins=*',
    `--user-data-dir=${userDataDir}`,
    'about:blank',
  ];
  const proc = spawn(CHROMIUM, args, { stdio: ['ignore', 'pipe', 'pipe'] });

  let wsBrowserUrl = null;
  const wsReady = new Promise((resolve, reject) => {
    let buf = '';
    proc.stderr.on('data', (d) => {
      buf += d.toString();
      const m = buf.match(/DevTools listening on (ws:\/\/[^\s]+)/);
      if (m && !wsBrowserUrl) {
        wsBrowserUrl = m[1];
        resolve(wsBrowserUrl);
      }
    });
    proc.on('exit', (code) => reject(new Error(`chromium exited early with code ${code}: ${buf}`)));
    setTimeout(() => reject(new Error('timed out waiting for DevTools listening line')), 15000);
  });

  try {
    await wsReady;
    const httpBase = wsBrowserUrl.replace('ws://', 'http://').replace(/\/devtools\/browser\/.*/, '');

    const newTabResp = await fetch(`${httpBase}/json/new?${encodeURIComponent(url)}`, { method: 'PUT' });
    const tab = await newTabResp.json();

    const ws = new WebSocket(tab.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => {
      ws.addEventListener('open', resolve, { once: true });
      ws.addEventListener('error', reject, { once: true });
    });

    let nextId = 1;
    const pending = new Map();
    ws.addEventListener('message', (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.id && pending.has(msg.id)) {
        pending.get(msg.id)(msg);
        pending.delete(msg.id);
      }
    });
    function send(method, params = {}) {
      const id = nextId++;
      return new Promise((resolve) => {
        pending.set(id, resolve);
        ws.send(JSON.stringify({ id, method, params }));
      });
    }
    async function evaluate(expression) {
      const res = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: false });
      return res.result && res.result.result ? res.result.result.value : undefined;
    }

    await send('Runtime.enable');
    await send('Page.enable');

    const start = Date.now();
    let title = await evaluate('document.title');
    while (title !== doneTitle && (Date.now() - start) < timeoutMs) {
      await new Promise((r) => setTimeout(r, 500));
      title = await evaluate('document.title').catch(() => title);
    }

    const elapsedMs = Date.now() - start;
    const finalTitle = await evaluate('document.title');
    const output = await evaluate(
      "document.getElementById('output') ? document.getElementById('output').textContent : null"
    );
    const diag = await evaluate(
      "document.getElementById('diag') ? document.getElementById('diag').textContent : null"
    );
    const trace = await evaluate(
      "document.getElementById('log') ? document.getElementById('log').textContent : null"
    );

    console.log(JSON.stringify({
      finalTitle,
      timedOut: finalTitle !== doneTitle,
      elapsedMs,
      output,
      diag,
      trace,
    }));

    ws.close();
  } finally {
    proc.kill('SIGKILL');
  }
}

main().catch((e) => { console.error('[drive] FATAL', e); process.exit(1); });
