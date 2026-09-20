// Web Worker for ROOT WebAssembly engine.
// Encapsulates xeus-cpp-lite, CppInterOp, and CERN ROOT runtime libraries.
// Exposes an explicit message protocol to RootWasmEngine.
'use strict';

const ROOT_LIBS = ['Core', 'Thread', 'RIO', 'MathCore', 'Matrix', 'Hist', 'Minuit2'];
const STATIC_ROOT_MARKER = 'libroota.so';
const INTERPRETER = 'libCling.so';

// Intercept self.postMessage to prevent raw xeus/Jupyter messages from leaking to the wrapper.
const rawPostMessage = self.postMessage.bind(self);
let activeHandler = null;

self.postMessage = function (data) {
  if (activeHandler && data && data.header) {
    activeHandler(data);
    return;
  }
  rawPostMessage(data);
};

function sendStatus(status, detail) {
  rawPostMessage({ type: 'STATUS', status, detail });
}

function sendLog(text) {
  rawPostMessage({ type: 'LOG', text });
}

let Module = null;
let xserver = null;
let xkernel = null;
let baseUrl = '/wasm/';

async function boot(customBaseUrl) {
  if (customBaseUrl) {
    baseUrl = customBaseUrl.endsWith('/') ? customBaseUrl : customBaseUrl + '/';
  }

  sendStatus('booting', 'Loading ROOT and compiler runtime…');

  // Load rootsys manifest and xeus-cpp loader
  importScripts(baseUrl + 'rootsys.js', baseUrl + 'xcpp.js');

  // Pre-fetch side modules
  const libBytes = {};
  await Promise.all(ROOT_LIBS.map(async (name) => {
    const r = await fetch(baseUrl + 'lib' + name + '.so');
    if (!r.ok) throw new Error('fetch lib' + name + '.so: ' + r.status);
    libBytes['lib' + name + '.so'] = new Uint8Array(await r.arrayBuffer());
  }));

  const rootaResp = await fetch(baseUrl + STATIC_ROOT_MARKER);
  if (rootaResp.ok) {
    libBytes[STATIC_ROOT_MARKER] = new Uint8Array(await rootaResp.arrayBuffer());
  }

  const interpResp = await fetch(baseUrl + INTERPRETER);
  const haveInterpreter = interpResp.ok;
  if (haveInterpreter) {
    libBytes[INTERPRETER] = new Uint8Array(await interpResp.arrayBuffer());
  }

  const moduleOpts = {
    print: (t) => rawPostMessage({ type: 'STDOUT', text: t + '\n' }),
    printErr: (t) => rawPostMessage({ type: 'STDERR', text: t + '\n' }),
    locateFile: (f) => baseUrl + f,
    noInitialRun: true,
    dynamicLibraries: (rootaResp.ok ? [STATIC_ROOT_MARKER] : [])
      .concat(ROOT_LIBS.map((n) => 'lib' + n + '.so'))
      .concat(haveInterpreter ? [INTERPRETER] : []),
    preRun: [() => {
      const FS = moduleOpts.FS;
      const mkdirFor = (p) => FS.mkdirTree(p.substring(0, p.lastIndexOf('/')));

      // Materialize ROOTSYS text and binary files
      for (const [p, text] of Object.entries(ROOTSYS_TEXT)) {
        mkdirFor(p);
        FS.writeFile(p, text);
      }
      for (const [p, b64] of Object.entries(ROOTSYS_BINARY)) {
        mkdirFor(p);
        FS.writeFile(p, Uint8Array.from(atob(b64), (c) => c.charCodeAt(0)));
      }

      // Materialize ROOT libraries
      FS.mkdirTree(ROOTSYS_MOUNT + '/lib');
      for (const [name, bytes] of Object.entries(libBytes)) {
        FS.writeFile(ROOTSYS_MOUNT + '/lib/' + name, bytes);
      }

      // Configure ROOT environment
      moduleOpts.ENV.ROOTSYS = ROOTSYS_MOUNT;
      moduleOpts.ENV.ROOT_LDSYSPATH = ROOTSYS_MOUNT + '/lib';
      moduleOpts.ENV.LD_LIBRARY_PATH = ROOTSYS_MOUNT + '/lib';
    }],
  };

  Module = await createXeusModule(moduleOpts);

  const argv = [
    'xcpp', '-std=c++17', '-fwasm-exceptions',
    '-I' + ROOTSYS_MOUNT + '/include',
    '-I/include/compat',
  ];

  xkernel = new Module.xkernel(argv);
  xserver = xkernel.get_server();
  xkernel.start();

  sendStatus('ready', 'Engine ready');
}

let msgSeq = 0;

function executeCell(code) {
  return new Promise((resolve) => {
    let stdoutText = '';
    let stderrText = '';
    let diagText = '';
    const msgId = 'm' + (msgSeq++);

    activeHandler = (msg) => {
      const mt = msg.header.msg_type;
      if (mt === 'stream' && msg.content && typeof msg.content.text === 'string') {
        if (msg.content.name === 'stdout') {
          stdoutText += msg.content.text;
          rawPostMessage({ type: 'STDOUT', text: msg.content.text });
        } else {
          stderrText += msg.content.text;
          diagText += msg.content.text;
          rawPostMessage({ type: 'STDERR', text: msg.content.text });
        }
      } else if (mt === 'error') {
        const errText = (msg.content && msg.content.evalue) || '';
        diagText += errText;
        rawPostMessage({ type: 'DIAGNOSTIC', text: errText });
      } else if (mt === 'execute_reply') {
        activeHandler = null;
        resolve({
          status: msg.content.status,
          stdout: stdoutText,
          stderr: stderrText,
          diag: diagText,
        });
      }
    };

    xserver.notify_listener({
      header: {
        msg_id: msgId,
        msg_type: 'execute_request',
        username: 'root-kata',
        session: 's1',
        date: new Date().toISOString(),
        version: '5.3',
      },
      parent_header: {},
      metadata: {},
      content: { code, silent: false, store_history: true, user_expressions: {}, allow_stdin: false },
      buffers: [],
      channel: 'shell',
    });
  });
}

async function handleRun(msg) {
  const startTime = performance.now();
  sendStatus('running', 'Compiling and executing…');

  // Step 1: Compile the student + harness translation unit
  const compResult = await executeCell(msg.code);

  if (compResult.status !== 'ok') {
    const elapsedMs = Math.round(performance.now() - startTime);
    rawPostMessage({
      type: 'RESULT',
      id: msg.id,
      stdout: compResult.stdout,
      stderr: compResult.stderr,
      diag: compResult.diag,
      elapsedMs,
      ok: false,
    });
    sendStatus('ready', 'Compilation failed');
    return;
  }

  // Step 2: Execute main()
  const runResult = await executeCell('main();');
  const elapsedMs = Math.round(performance.now() - startTime);

  const fullStdout = compResult.stdout + runResult.stdout;
  const fullStderr = compResult.stderr + runResult.stderr;
  const fullDiag = compResult.diag + runResult.diag;

  rawPostMessage({
    type: 'RESULT',
    id: msg.id,
    stdout: fullStdout,
    stderr: fullStderr,
    diag: fullDiag,
    elapsedMs,
    ok: runResult.status === 'ok',
  });
  sendStatus('ready', 'Execution complete');
}

self.onmessage = async (ev) => {
  const msg = ev.data;
  if (!msg || typeof msg !== 'object') return;

  switch (msg.type) {
    case 'INIT':
      try {
        await boot(msg.baseUrl);
      } catch (err) {
        rawPostMessage({ type: 'ERROR', message: String(err) });
        sendStatus('error', 'Boot failed: ' + err.message);
      }
      break;

    case 'RUN':
      if (!xserver) {
        rawPostMessage({ type: 'ERROR', message: 'Engine not ready' });
        return;
      }
      try {
        await handleRun(msg);
      } catch (err) {
        rawPostMessage({ type: 'ERROR', message: String(err) });
        sendStatus('error', 'Run failed: ' + err.message);
      }
      break;

    case 'FS_WRITE':
      if (!Module || !Module.FS) {
        rawPostMessage({ type: 'ERROR', message: 'Filesystem not ready' });
        return;
      }
      try {
        const p = msg.path;
        const dir = p.substring(0, p.lastIndexOf('/'));
        if (dir) Module.FS.mkdirTree(dir);
        Module.FS.writeFile(p, msg.bytes);
        rawPostMessage({ type: 'FS_WRITE_OK', path: p });
      } catch (err) {
        rawPostMessage({ type: 'ERROR', message: `FS_WRITE failed for ${msg.path}: ${err}` });
      }
      break;

    case 'RESET':
      // Reset is managed at engine level via worker re-creation for full CppInterOp isolation
      sendStatus('ready', 'Reset complete');
      break;

    case 'DISPOSE':
      self.close();
      break;

    default:
      sendLog('Unknown message type: ' + msg.type);
  }
};
