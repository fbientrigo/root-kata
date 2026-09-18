/**
 * ExerciseRunner for ROOT Kata browser execution.
 * Composes student code, teacher harness, and rk contract, invokes RootWasmEngine,
 * extracts results, grades them via BrowserGrader, and returns the /api/run schema.
 */
import { RootWasmEngine } from './root_wasm_engine.js';
import { BrowserGrader } from './browser_grader.js';
import { extractFirstError } from './diagnostics.js';

const RK_HEADER = `
#pragma once
#include <cstdio>
#include <string>
#include <vector>
namespace rk {
inline std::string& _buf(){ static std::string b; return b; }
inline void _key(const std::string& k){ if(!_buf().empty()) _buf()+=","; _buf()+="\\""+k+"\\":"; }
inline std::string _num(double v){ char s[64]; std::snprintf(s,sizeof s,"%.17g",v); return s; }
inline void emit(const std::string& k,double v){_key(k);_buf()+=_num(v);}
inline void emit(const std::string& k,int v){_key(k);_buf()+=std::to_string(v);}
inline void emit(const std::string& k,long v){_key(k);_buf()+=std::to_string(v);}
inline void emit(const std::string& k,bool v){_key(k);_buf()+=v?"true":"false";}
inline void emit(const std::string& k,const char* v){_key(k);_buf()+="\\""+std::string(v)+"\\"";}
inline void emit(const std::string& k,const std::string& v){_key(k);_buf()+="\\""+v+"\\"";}
inline int done(){std::fflush(stdout);std::printf("\\n{%s}\\n",_buf().c_str());std::fflush(stdout);return 0;}
}
`;

const HARNESS_HISTOGRAM_INSPECT = `
#include "TH1D.h"

int main() {
    TH1D hist("h_inspect", "", 5, 0.0, 5.0);
    for (double value : {0.2, 1.2, 1.7, 3.3, 3.8}) {
        hist.Fill(value);
    }

    const auto bin2 = inspect_histogram(hist, 2);
    rk::emit("entries", bin2.entries);
    rk::emit("bin2 content", bin2.bin_content);
    rk::emit("mean", bin2.mean);
    rk::emit("stddev", bin2.stddev);

    const auto bin3 = inspect_histogram(hist, 3);
    rk::emit("bin3 content", bin3.bin_content);

    return rk::done();
}
`;

// Shared default engine singleton
let defaultEngine = null;

export function getDefaultEngine() {
  if (!defaultEngine) {
    defaultEngine = new RootWasmEngine();
  }
  return defaultEngine;
}

/**
 * Compose student code with harness and rk.h contract using #line directives.
 * @param {string} exerciseId
 * @param {string} studentCode
 * @returns {string}
 */
function composeTranslationUnit(exerciseId, studentCode) {
  if (exerciseId === 'cpp-root-histogram-inspect') {
    return `${RK_HEADER}\n#line 1 "solution.cpp"\n${studentCode}\n#line 1 "harness.cpp"\n${HARNESS_HISTOGRAM_INSPECT}`;
  }
  throw new Error(`Exercise not supported in browser runner: ${exerciseId}`);
}

/**
 * Extract parsed JSON from the last line of stdout.
 * @param {string} stdout
 * @returns {{ data: Object|null, studentStdout: string }}
 */
function parseRkOutput(stdout) {
  const lines = (stdout || '').trim().split('\n');
  if (lines.length === 0) return { data: null, studentStdout: '' };

  for (let i = lines.length - 1; i >= 0; i--) {
    const line = lines[i].trim();
    if (line.startsWith('{') && line.endsWith('}')) {
      try {
        const parsed = JSON.parse(line);
        if (parsed && typeof parsed === 'object') {
          const studentStdout = lines.slice(0, i).join('\n');
          return { data: parsed, studentStdout };
        }
      } catch {}
    }
  }

  return { data: null, studentStdout: stdout };
}

export class ExerciseRunner {
  /**
   * Run an exercise in the browser and return the /api/run response shape.
   * @param {string} exerciseId
   * @param {string} studentCode
   * @param {Object} [options]
   * @param {string} [options.lang='es']
   * @param {RootWasmEngine} [options.engine]
   * @param {(status: string, detail?: string) => void} [options.onStatusChange]
   * @returns {Promise<Object>}
   */
  static async runExercise(exerciseId, studentCode, options = {}) {
    const lang = options.lang || 'es';
    const engine = options.engine || getDefaultEngine();

    let unsubscribe = null;
    if (options.onStatusChange) {
      unsubscribe = engine.onStatusChange(options.onStatusChange);
    }

    try {
      const compositeCode = composeTranslationUnit(exerciseId, studentCode);
      const runResult = await engine.run(compositeCode);

      // Check for compilation errors
      const hasErrors = runResult.diagnostics.some((d) => d.severity === 'error');
      if (!runResult.ok || hasErrors) {
        const firstError = extractFirstError(runResult.diagnostics, studentCode, 'solution.cpp');
        const summary = firstError
          ? (lang === 'es'
              ? `Error de compilación en ${firstError.file}:${firstError.line}: ${firstError.message}`
              : `Compilation failed at ${firstError.file}:${firstError.line}: ${firstError.message}`)
          : (lang === 'es' ? 'Error de compilación' : 'Compilation failed');

        return {
          status: 'compile_error',
          status_label: lang === 'es' ? 'Error de compilación' : 'Compilation error',
          summary,
          cases: [],
          first_error: firstError,
          stdout: runResult.stdout,
          stderr: runResult.stderr,
        };
      }

      // Parse JSON from rk::done()
      const { data: rkData, studentStdout } = parseRkOutput(runResult.stdout);
      if (!rkData) {
        return {
          status: 'harness_error',
          status_label: lang === 'es' ? 'Error del banco de pruebas' : 'Harness error',
          summary: lang === 'es'
            ? 'El banco de pruebas no produjo JSON en su última línea.'
            : 'The harness did not produce JSON on its last stdout line.',
          cases: [],
          first_error: null,
          stdout: runResult.stdout,
          stderr: runResult.stderr,
        };
      }

      // Grade cases
      const graded = BrowserGrader.grade(exerciseId, rkData, lang);

      return {
        status: graded.status,
        status_label: graded.status_label,
        summary: graded.summary,
        cases: graded.cases,
        first_error: null,
        stdout: studentStdout,
        stderr: runResult.stderr,
      };
    } finally {
      if (unsubscribe) unsubscribe();
    }
  }
}
