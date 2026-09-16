// ROOT-in-the-browser kernel worker.
//
// Runs the pinned xeus-cpp-lite / CppInterOp kernel (a full Emscripten
// MAIN_MODULE) together with ROOT's own wasm libraries, loaded as side modules.
//
// Why a Web Worker and not the page: ROOT loads libraries with dlopen(3), which
// Emscripten implements as a *synchronous* WebAssembly compile. Browsers forbid
// synchronous compilation of anything but tiny modules on the main thread, so a
// genuine ROOT dlopen of a multi-megabyte libRIO can only work off-thread.
//
// Protocol with the page:
//   in : {type:'run', code, msgId}
//   out: {type:'status'|'log', text}          -- this file's own trace
//        anything with a .header field        -- a real Jupyter-wire message
//                                                posted by xeus itself
'use strict';

const ROOT_LIBS = ['Core', 'Thread', 'RIO', 'MathCore', 'Matrix', 'Hist'];

// ROOT's own roota.cxx, compiled unmodified. Its single extern "C" symbol tells
// TROOT::InitInterpreter that ROOT is already linked into this process, so ROOT
// resolves CreateInterpreter through the global symbol table rather than
// dlopen'ing libRIO and libCling by path -- which here would load a second copy
// of a library that is already present. See wasm/gates/rootweb/run.sh.
const STATIC_ROOT_MARKER = 'libroota.so';

// M3: ROOT's interpreter plugin (wasm/rootlight/interpreter). Loaded like any
// other side module so its CreateInterpreter is in the global symbol table,
// which is where TROOT::InitInterpreter looks once the static-ROOT marker is
// present. Absent before M3 is built; the page reports which state it is in.
const INTERPRETER = 'libCling.so';

function status(text) { postMessage({ type: 'status', text }); }
function log(text) { postMessage({ type: 'log', text }); }

let xserver = null;

// ?roota=0 disables the static-ROOT marker, for A/B debugging of the loader.
const useRoota = new URLSearchParams(location.search).get('roota') !== '0';

async function boot() {
  importScripts('./rootsys.js', './xcpp.js');
  log('[rootweb] rootsys blob: ' + Object.keys(ROOTSYS_TEXT).length + ' text + ' +
      Object.keys(ROOTSYS_BINARY).length + ' binary files');

  // Fetch the ROOT side modules up front. They are served as ordinary static
  // files; we need their bytes in MEMFS as well, because ROOT resolves
  // libraries through its own path search (TSystem::FindDynamicLibrary) before
  // calling dlopen, and that search stats the filesystem.
  const libBytes = {};
  await Promise.all(ROOT_LIBS.map(async (name) => {
    const r = await fetch('./lib' + name + '.so');
    if (!r.ok) throw new Error('fetch lib' + name + '.so: ' + r.status);
    libBytes['lib' + name + '.so'] = new Uint8Array(await r.arrayBuffer());
  }));
  const interpResp = await fetch('./' + INTERPRETER);
  const haveInterpreter = interpResp.ok;
  if (haveInterpreter) libBytes[INTERPRETER] = new Uint8Array(await interpResp.arrayBuffer());
  log('[rootweb] fetched ' + Object.keys(libBytes).length + ' side modules; interpreter: ' +
      (haveInterpreter ? 'present' : 'absent'));

  const Module = await createXeusModule({
    print: (t) => log('[stdout-raw] ' + t),
    printErr: (t) => log('[stderr-raw] ' + t),
    locateFile: (f) => f,
    noInitialRun: true,
    // Emscripten loads these before main, resolving each library's NEEDED list
    // (ROOT's own generated link dependencies) by basename.
    dynamicLibraries: (useRoota ? [STATIC_ROOT_MARKER] : [])
      .concat(ROOT_LIBS.map((n) => 'lib' + n + '.so'))
      .concat(haveInterpreter ? [INTERPRETER] : []),
  });
  log('[rootweb] kernel module ready');

  // Materialise $ROOTSYS. ROOT finds its resources by path at runtime, so the
  // tree has to have the same shape in MEMFS that it has on disk.
  const FS = Module.FS;
  const mkdirFor = (p) => FS.mkdirTree(p.substring(0, p.lastIndexOf('/')));
  for (const [p, text] of Object.entries(ROOTSYS_TEXT)) { mkdirFor(p); FS.writeFile(p, text); }
  for (const [p, b64] of Object.entries(ROOTSYS_BINARY)) {
    mkdirFor(p);
    FS.writeFile(p, Uint8Array.from(atob(b64), (c) => c.charCodeAt(0)));
  }
  FS.mkdirTree(ROOTSYS_MOUNT + '/lib');
  for (const [name, bytes] of Object.entries(libBytes)) {
    FS.writeFile(ROOTSYS_MOUNT + '/lib/' + name, bytes);
  }
  log('[rootweb] mounted ' + ROOTSYS_MOUNT);

  // Emscripten does not inherit a host environment. ROOTSYS is how ROOT finds
  // everything above; ROOT_LDSYSPATH is ROOT's own documented override
  // (TUnixSystem.cxx, DynamicPath) for the popen("LD_DEBUG=libs ... ls")
  // system-library probe, which no browser can run.
  Module.ENV.ROOTSYS = ROOTSYS_MOUNT;
  Module.ENV.ROOT_LDSYSPATH = ROOTSYS_MOUNT + '/lib';
  Module.ENV.LD_LIBRARY_PATH = ROOTSYS_MOUNT + '/lib';

  const argv = [
    'xcpp', '-std=c++17', '-fwasm-exceptions',
    '-I' + ROOTSYS_MOUNT + '/include',
    // The prebuilt xcpp.wasm's auto-detected include list omits Emscripten's
    // own "compat" directory (xlocale.h, reached via ROOT's TError.h). The
    // header is already inside xcpp.data; this only points at it. Same
    // adjustment G7 documents.
    '-I/include/compat',
  ];
  log('[rootweb] argv = ' + JSON.stringify(argv));

  const xkernel = new Module.xkernel(argv);
  xserver = xkernel.get_server();
  xkernel.start();
  status('ready');
}

self.onmessage = (ev) => {
  const msg = ev.data;
  if (!msg || msg.type !== 'run') return;
  if (!xserver) { status('not-ready'); return; }
  xserver.notify_listener({
    header: {
      msg_id: msg.msgId, msg_type: 'execute_request', username: 'rootweb',
      session: 's1', date: new Date().toISOString(), version: '5.3',
    },
    parent_header: {},
    metadata: {},
    content: { code: msg.code, silent: false, store_history: true, user_expressions: {}, allow_stdin: false },
    buffers: [],
    channel: 'shell',
  });
};

boot().catch((e) => {
  log('[rootweb] boot failed: ' + (e && e.stack ? e.stack : e));
  status('boot-failed: ' + e);
});
