#!/usr/bin/env node
// Node stand-in for page/kernel-worker.js, for debugging only.
//
// Same kernel, same ROOT side modules, same mounted $ROOTSYS -- but in Node,
// where a failure gives a real stack trace instead of an opaque
// "RuntimeError: function signature mismatch" at wasm://wasm/<hash>.
//
// Usage: node node-probe.mjs <web-dir> <rootsys-stage-dir> <cell.cxx> [--no-roota]
import { createRequire } from 'node:module';
import fs from 'node:fs';
import path from 'node:path';

const require = createRequire(import.meta.url);
const [webDir, stageDir, cellPath] = process.argv.slice(2);
const useRoota = !process.argv.includes('--no-roota');
if (!webDir || !stageDir || !cellPath) {
  console.error('usage: node-probe.mjs <web-dir> <rootsys-stage> <cell.cxx> [--no-roota]');
  process.exit(2);
}

const ROOT_LIBS = ['Core', 'Thread', 'RIO', 'MathCore', 'Matrix', 'Hist'];
const MOUNT = '/rootsys';

const createXeusModule = require(path.resolve(webDir, 'xcpp.js'));

// The prebuilt kernel fetches its own .wasm/.data/.so payload over HTTP even
// under Node, so serve the same static web root the browser gets.
const http = await import('node:http');
const server = http.createServer((req, res) => {
  const f = path.resolve(webDir, decodeURIComponent(req.url.slice(1)).split('?')[0]);
  fs.readFile(f, (err, buf) => {
    if (err) { res.writeHead(404); res.end(); return; }
    const ct = f.endsWith('.wasm') || f.endsWith('.so') ? 'application/wasm' : 'application/octet-stream';
    res.writeHead(200, { 'content-type': ct, 'content-length': buf.length });
    res.end(buf);
  });
});
await new Promise((r) => server.listen(0, '127.0.0.1', r));
const base = `http://127.0.0.1:${server.address().port}/`;
console.log('[probe] serving', webDir, 'at', base);

function mountDir(FS, src, dst) {
  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    const s = path.join(src, entry.name), d = dst + '/' + entry.name;
    if (entry.isDirectory()) { FS.mkdirTree(d); mountDir(FS, s, d); }
    else FS.writeFile(d, new Uint8Array(fs.readFileSync(s)));
  }
}

const Module = await createXeusModule({
  print: (t) => console.log('[out]', t),
  printErr: (t) => console.log('[err]', t),
  locateFile: (f) => base + f,
  noInitialRun: true,
  dynamicLibraries: (useRoota ? ['libroota.so'] : []).concat(ROOT_LIBS.map((n) => 'lib' + n + '.so')),
});
console.log('[probe] module ready, roota =', useRoota);

const FS = Module.FS;
for (const sub of ['include', 'etc']) {
  FS.mkdirTree(MOUNT + '/' + sub);
  mountDir(FS, path.join(stageDir, sub), MOUNT + '/' + sub);
}
FS.mkdirTree(MOUNT + '/lib');
for (const f of fs.readdirSync(path.join(stageDir, 'lib'))) {
  if (f.endsWith('.rootmap') || f.endsWith('_rdict.pcm') || ROOT_LIBS.some((n) => f === 'lib' + n + '.so')) {
    FS.writeFile(MOUNT + '/lib/' + f, new Uint8Array(fs.readFileSync(path.join(stageDir, 'lib', f))));
  }
}
Module.ENV.ROOTSYS = MOUNT;
Module.ENV.ROOT_LDSYSPATH = MOUNT + '/lib';
Module.ENV.LD_LIBRARY_PATH = MOUNT + '/lib';
console.log('[probe] mounted', MOUNT);
console.log('[probe] loadedLibsByName:', Object.keys(Module.LDSO.loadedLibsByName).join(' '));

const xkernel = new Module.xkernel(['xcpp', '-std=c++17', '-fwasm-exceptions',
  '-I' + MOUNT + '/include', '-I/include/compat']);
const xserver = xkernel.get_server();
xkernel.start();
console.log('[probe] kernel started');

let seq = 0;
function execute(code) {
  xserver.notify_listener({
    header: { msg_id: 'm' + (seq++), msg_type: 'execute_request', username: 'probe', session: 's1', date: new Date().toISOString(), version: '5.3' },
    parent_header: {}, metadata: {},
    content: { code, silent: false, store_history: true, user_expressions: {}, allow_stdin: false },
    buffers: [], channel: 'shell',
  });
}

const src = fs.readFileSync(cellPath, 'utf8');
try {
  execute(src);
  console.log('[probe] TU executed');
  execute('main();');
  console.log('[probe] main() executed');
} catch (e) {
  console.log('[probe] THREW:', e && e.stack ? e.stack : e);
}
console.log("[probe] DSOs now:", Object.keys(Module.LDSO.loadedLibsByName).join(" "));
server.close();
