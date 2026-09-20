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

const HARNESSES = {
  'cpp-root-histogram': `
#include "TH1D.h"
#include "TROOT.h"

int main() {
    gROOT->SetBatch(kTRUE);
    TH1::AddDirectory(kFALSE);

    TH1D* h = build_histogram({});
    rk::emit("returned object", h != nullptr);
    if (h) {
        rk::emit("name", h->GetName());
        rk::emit("nbins", h->GetNbinsX());
        rk::emit("xmin", h->GetXaxis()->GetXmin());
        rk::emit("xmax", h->GetXaxis()->GetXmax());
        delete h;
    }
    TH1D* f = build_histogram({10.0, 20.0, 30.0});
    if (f) {
        rk::emit("entries", f->GetEntries());
        rk::emit("integral", f->Integral());
        rk::emit("mean", f->GetMean());
        delete f;
    }
    TH1D* o = build_histogram({-5.0, 50.0, 150.0});
    if (o) {
        rk::emit("ovf entries", o->GetEntries());
        rk::emit("ovf integral", o->Integral());
        delete o;
    }
    return rk::done();
}
`,
  'cpp-root-histogram-inspect': `
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
`,
  'cpp-root-histogram-range': `
#include "TH1D.h"

int main() {
    const std::vector<double> values{0,10,20,30,40,50,60,70,80,90,100};
    TH1D* h = build_calibration_histogram(values);
    rk::emit("returned object", h != nullptr);
    if (h) {
        rk::emit("name", h->GetName());
        rk::emit("nbins", h->GetNbinsX());
        rk::emit("xmin", h->GetXaxis()->GetXmin());
        rk::emit("xmax", h->GetXaxis()->GetXmax());
        rk::emit("bin width", h->GetXaxis()->GetBinWidth(1));
        rk::emit("entries", h->GetEntries());
        rk::emit("visible integral", h->Integral());
        rk::emit("underflow", h->GetBinContent(0));
        rk::emit("overflow", h->GetBinContent(h->GetNbinsX() + 1));
        delete h;
    }
    return rk::done();
}
`,
  'cpp-root-histogram-selected-sample': `
#include "TH1D.h"

int main() {
    TH1D* a = build_selected_histogram({20.0, 50.0, 50.1, 80.0, 120.0}, 50.0);
    rk::emit("a returned", a != nullptr);
    if (a) {
        rk::emit("name", a->GetName());
        rk::emit("nbins", a->GetNbinsX());
        rk::emit("xmin", a->GetXaxis()->GetXmin());
        rk::emit("xmax", a->GetXaxis()->GetXmax());
        rk::emit("a entries", a->GetEntries());
        rk::emit("a integral", a->Integral());
        rk::emit("a first bin", a->GetBinContent(1));
        delete a;
    }
    TH1D* b = build_selected_histogram({-10.0, 10.0, 151.0}, 0.0);
    rk::emit("b returned", b != nullptr);
    if (b) {
        rk::emit("b entries", b->GetEntries());
        rk::emit("b integral", b->Integral());
        rk::emit("b overflow", b->GetBinContent(b->GetNbinsX() + 1));
        delete b;
    }
    return rk::done();
}
`,
  'cpp-root-tgraph-points': `
#include "TGraph.h"
#include <string>

int main() {
    TGraph* graph = build_graph({0.0, 1.5, 4.0}, {2.0, 3.5, 3.0});
    rk::emit("returned object", graph != nullptr);
    if (graph) {
        rk::emit("n", graph->GetN());
        for (int i = 0; i < graph->GetN(); ++i) {
            double x = 0.0, y = 0.0;
            graph->GetPoint(i, x, y);
            rk::emit("x" + std::to_string(i), x);
            rk::emit("y" + std::to_string(i), y);
        }
        delete graph;
    }
    return rk::done();
}
`,
  'cpp-root-tf1-evaluate': `
#include "TF1.h"

int main() {
    TF1* model = build_linear_model(2.0, 3.0);
    rk::emit("returned object", model != nullptr);
    if (model) {
        double xmin = 0.0, xmax = 0.0;
        model->GetRange(xmin, xmax);
        rk::emit("name", model->GetName());
        rk::emit("npar", model->GetNpar());
        rk::emit("xmin", xmin);
        rk::emit("xmax", xmax);
        rk::emit("p0", model->GetParameter(0));
        rk::emit("p1", model->GetParameter(1));
        rk::emit("eval0", model->Eval(0.0));
        rk::emit("eval2", model->Eval(2.0));
        model->SetParameter(1, -1.0);
        rk::emit("eval2 changed", model->Eval(2.0));
        delete model;
    }
    return rk::done();
}
`,
  'cpp-root-tf1-range-parameters': `
#include "TF1.h"

int main() {
    TF1* model = build_decay_model(12.0, 2.0);
    rk::emit("returned object", model != nullptr);
    if (model) {
        double xmin = 0.0, xmax = 0.0;
        model->GetRange(xmin, xmax);
        rk::emit("name", model->GetName());
        rk::emit("p0", model->GetParameter(0));
        rk::emit("p1", model->GetParameter(1));
        rk::emit("xmin", xmin);
        rk::emit("xmax", xmax);
        rk::emit("eval0", model->Eval(0.0));
        rk::emit("eval4", model->Eval(4.0));
        delete model;
    }
    return rk::done();
}
`,
};

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
  const harness = HARNESSES[exerciseId];
  if (!harness) {
    throw new Error(`Exercise not supported in browser runner: ${exerciseId}`);
  }
  return `${RK_HEADER}\n#line 1 "solution.cpp"\n${studentCode}\n#line 1 "harness.cpp"\n${harness}`;
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
