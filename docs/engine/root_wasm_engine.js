/**
 * Product-facing RootWasmEngine implementation.
 * Encapsulates the Web Worker, manages the explicit protocol, and guarantees
 * deterministic run isolation.
 */
import { parseDiagnostics } from './diagnostics.js';

/**
 * @typedef {'idle' | 'booting' | 'ready' | 'running' | 'error'} EngineStatus
 */

/**
 * @typedef {Object} EngineRunResult
 * @property {string} stdout
 * @property {string} stderr
 * @property {import('./diagnostics.js').CompilerDiagnostic[]} diagnostics
 * @property {number} elapsedMs
 * @property {boolean} ok
 */

export class RootWasmEngine {
  /**
   * @param {Object} [options]
   * @param {string} [options.workerUrl]
   * @param {string} [options.wasmBaseUrl]
   */
  constructor(options = {}) {
    this.workerUrl = options.workerUrl || new URL('./worker.js', import.meta.url).href;
    this.wasmBaseUrl = options.wasmBaseUrl || new URL('../wasm/', import.meta.url).href;
    /** @type {Worker|null} */
    this.worker = null;
    /** @type {EngineStatus} */
    this.status = 'idle';
    this.statusDetail = '';
    this.statusListeners = new Set();
    this.hasRun = false;
    this.pendingResolvers = new Map();
    this.initPromise = null;
    this.runSeq = 0;
  }

  /**
   * Register a callback for status transitions.
   * @param {(status: EngineStatus, detail?: string) => void} callback
   */
  onStatusChange(callback) {
    this.statusListeners.add(callback);
    callback(this.status, this.statusDetail);
    return () => this.statusListeners.delete(callback);
  }

  _setStatus(newStatus, detail = '') {
    this.status = newStatus;
    this.statusDetail = detail;
    for (const listener of this.statusListeners) {
      try {
        listener(newStatus, detail);
      } catch (err) {
        console.error('Error in status listener:', err);
      }
    }
  }

  /**
   * Initialize the Web Worker and start the ROOT WASM kernel.
   * @returns {Promise<void>}
   */
  async init() {
    if (this.status === 'ready' && this.worker && !this.hasRun) {
      return;
    }
    if (this.initPromise) {
      return this.initPromise;
    }

    this.initPromise = new Promise((resolve, reject) => {
      this._setStatus('booting', 'Spawning worker…');

      if (this.worker) {
        this.worker.terminate();
        this.worker = null;
      }

      this.hasRun = false;
      this.worker = new Worker(this.workerUrl);

      this.worker.onerror = (err) => {
        this._setStatus('error', err.message);
        reject(new Error(`Worker error: ${err.message}`));
      };

      this.worker.onmessage = (ev) => {
        const msg = ev.data;
        if (!msg || typeof msg !== 'object') return;

        switch (msg.type) {
          case 'STATUS':
            this._setStatus(msg.status, msg.detail);
            if (msg.status === 'ready') {
              resolve();
            } else if (msg.status === 'error') {
              reject(new Error(msg.detail || 'Engine error'));
            }
            break;

          case 'RESULT': {
            const resolver = this.pendingResolvers.get(msg.id);
            if (resolver) {
              this.pendingResolvers.delete(msg.id);
              resolver.resolve({
                stdout: msg.stdout || '',
                stderr: msg.stderr || '',
                diagnostics: parseDiagnostics(msg.diag || msg.stderr || ''),
                elapsedMs: msg.elapsedMs || 0,
                ok: !!msg.ok,
              });
            }
            break;
          }

          case 'FS_WRITE_OK': {
            const resolver = this.pendingResolvers.get(`fs_${msg.path}`);
            if (resolver) {
              this.pendingResolvers.delete(`fs_${msg.path}`);
              resolver.resolve();
            }
            break;
          }

          case 'ERROR': {
            console.error('[RootWasmEngine Worker Error]', msg.message);
            break;
          }
        }
      };

      this.worker.postMessage({ type: 'INIT', baseUrl: this.wasmBaseUrl });
    });

    try {
      await this.initPromise;
    } finally {
      this.initPromise = null;
    }
  }

  /**
   * Execute code in the ROOT WASM environment.
   * Guarantees deterministic AST isolation by resetting between submissions.
   * @param {string} code
   * @returns {Promise<EngineRunResult>}
   */
  async run(code) {
    if (this.hasRun || this.status !== 'ready') {
      // Re-initialize to ensure fresh Clang-Repl AST state with no leaked symbols
      await this.init();
    }

    if (!this.worker) {
      throw new Error('RootWasmEngine is not initialized');
    }

    this.hasRun = true;
    const runId = `run_${++this.runSeq}`;

    return new Promise((resolve, reject) => {
      this.pendingResolvers.set(runId, { resolve, reject });
      this.worker.postMessage({ type: 'RUN', code, id: runId });
    });
  }

  /**
   * Reset the engine to a clean state.
   * @returns {Promise<void>}
   */
  async reset() {
    this.dispose();
    await this.init();
  }

  /**
   * Mount a file into the virtual filesystem.
   * @param {string} path
   * @param {Uint8Array} bytes
   * @returns {Promise<void>}
   */
  async mountFile(path, bytes) {
    if (this.status !== 'ready') {
      await this.init();
    }

    return new Promise((resolve, reject) => {
      const key = `fs_${path}`;
      this.pendingResolvers.set(key, { resolve, reject });
      this.worker.postMessage({ type: 'FS_WRITE', path, bytes });
    });
  }

  /**
   * Terminate the worker and release resources.
   * @returns {Promise<void>}
   */
  async dispose() {
    if (this.worker) {
      this.worker.postMessage({ type: 'DISPOSE' });
      this.worker.terminate();
      this.worker = null;
    }
    this.hasRun = false;
    this.initPromise = null;
    this.pendingResolvers.clear();
    this._setStatus('idle', 'Engine disposed');
  }
}
