#!/usr/bin/env node
// hosting_driver.mjs — headless Chromium driver for hosting constraint verification.
//
// Drives headless Chromium via Chrome DevTools Protocol (CDP) over WebSocket
// using Node's built-in fetch and WebSocket (zero npm dependencies).
// Captures all network traffic, verifies lack of COOP/COEP isolation, verifies
// execution without SharedArrayBuffer, and scrapes DOM results.

import { spawn } from 'node:child_process';
import * as fs from 'node:fs';

const CHROMIUM = process.env.CHROMIUM_BIN || 'chromium';
const url = process.argv[2];
const timeoutMs = Number(process.argv[3] || 60000);
const userDataDir = process.argv[4];
const requestsJsonPath = process.argv[5];
const stdoutPath = process.argv[6];
const diagPath = process.argv[7];
const reportJsonPath = process.argv[8];

if (!url || !userDataDir || !requestsJsonPath || !stdoutPath || !diagPath || !reportJsonPath) {
  console.error('usage: hosting_driver.mjs <url> <timeout-ms> <userDataDir> <requestsJson> <stdoutFile> <diagFile> <reportJson>');
  process.exit(2);
}

async function main() {
  const args = [
    '--headless=new',
    '--disable-gpu',
    '--no-sandbox',
    '--disable-dev-shm-usage',
    '--disable-background-networking',
    '--disable-sync',
    '--disable-default-apps',
    '--remote-debugging-port=0',
    '--remote-allow-origins=*',
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

    const newTabResp = await fetch(`${httpBase}/json/new?about:blank`, { method: 'PUT' });
    const tab = await newTabResp.json();

    const ws = new WebSocket(tab.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => {
      ws.addEventListener('open', resolve, { once: true });
      ws.addEventListener('error', reject, { once: true });
    });

    let nextId = 1;
    const pending = new Map();
    const requests = [];
    const requestMap = new Map();

    ws.addEventListener('message', (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.id && pending.has(msg.id)) {
        pending.get(msg.id)(msg);
        pending.delete(msg.id);
      }
      if (msg.method === 'Network.requestWillBeSent') {
        const req = {
          requestId: msg.params.requestId,
          url: msg.params.request.url,
          method: msg.params.request.method,
          type: msg.params.type || 'Other',
          initiator: msg.params.initiator ? msg.params.initiator.type : 'unknown',
          timestamp: msg.params.timestamp,
          status: null,
          mimeType: null,
        };
        requests.push(req);
        requestMap.set(msg.params.requestId, req);
      } else if (msg.method === 'Network.responseReceived') {
        const req = requestMap.get(msg.params.requestId);
        if (req) {
          req.status = msg.params.response.status;
          req.mimeType = msg.params.response.mimeType;
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

    async function evaluate(expression) {
      const res = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: false });
      return res.result && res.result.result ? res.result.result.value : undefined;
    }

    await send('Network.enable');
    await send('Page.enable');
    await send('Runtime.enable');

    // Mechanically prove no SharedArrayBuffer dependency by explicitly removing it
    await send('Page.addScriptToEvaluateOnNewDocument', {
      source: 'try { delete window.SharedArrayBuffer; window.SharedArrayBuffer = undefined; window.__SAB_DISABLED_BY_TEST__ = true; } catch(e) {}',
    });

    // Navigate to target
    await send('Page.navigate', { url });

    const start = Date.now();
    let title = (await evaluate('document.title')) || '';
    while (!title.endsWith('-DONE') && !title.endsWith('-ERROR') && (Date.now() - start) < timeoutMs) {
      await new Promise((r) => setTimeout(r, 250));
      title = (await evaluate('document.title').catch(() => title)) || '';
    }

    const elapsedMs = Date.now() - start;
    const finalTitle = (await evaluate('document.title')) || '';
    const crossOriginIsolated = await evaluate('Boolean(window.crossOriginIsolated)');
    const sabType = await evaluate('typeof window.SharedArrayBuffer');
    const output = (await evaluate("document.getElementById('output') ? document.getElementById('output').textContent : ''")) || '';
    const diag = (await evaluate("document.getElementById('diag') ? document.getElementById('diag').textContent : ''")) || '';

    // Write captured files
    fs.writeFileSync(requestsJsonPath, JSON.stringify(requests, null, 2), 'utf-8');
    fs.writeFileSync(stdoutPath, output, 'utf-8');
    fs.writeFileSync(diagPath, diag, 'utf-8');

    const report = {
      finalTitle,
      success: finalTitle.endsWith('-DONE'),
      elapsedMs,
      crossOriginIsolated,
      sabType,
      requestsCount: requests.length,
      outputLength: output.length,
    };
    fs.writeFileSync(reportJsonPath, JSON.stringify(report, null, 2), 'utf-8');

    ws.close();
  } finally {
    proc.kill('SIGKILL');
  }
}

main().catch((e) => {
  console.error('[hosting_driver] FATAL', e);
  process.exit(1);
});
