/**
 * Browser-side grading logic for ROOT Kata exercises.
 * Implements exact semantic parity with the Python validator contract.
 */

/**
 * Compare two floating point numbers within relative and absolute tolerance.
 * Matches Python math.isclose(a, b, rel_tol=relTol, abs_tol=absTol).
 * @param {number} a
 * @param {number} b
 * @param {number} [relTol=1e-9]
 * @param {number} [absTol=1e-9]
 * @returns {boolean}
 */
function isClose(a, b, relTol = 1e-9, absTol = 1e-9) {
  return Math.abs(a - b) <= Math.max(relTol * Math.max(Math.abs(a), Math.abs(b)), absTol);
}

/**
 * Format expected_got string according to language.
 * @param {string|number} expected
 * @param {string|number} actual
 * @param {string} lang
 * @returns {string}
 */
function formatExpectedGot(expected, actual, lang) {
  return lang === 'es'
    ? `esperaba ${expected}, obtuvo ${actual}`
    : `expected ${expected}, got ${actual}`;
}

const LOCALIZATION = {
  es: {
    passedLabel: 'Resuelto',
    failedLabel: 'Aún no',
    testsPassed: (n, m) => `${n}/${m} pruebas pasaron`,
    allPassed: 'Todas las pruebas pasaron',
    cases: {
      'entries versus bin contents': 'entradas frente a contenido de bins',
      'summary statistics': 'estadísticas resumen',
    },
    messages: {
      'Expected 5 total entries': 'Se esperaban 5 entradas totales',
      'Expected 2 entries in ROOT bin 2': 'Se esperaban 2 entradas en el bin ROOT 2',
      'Expected an empty ROOT bin 3': 'Se esperaba que el bin ROOT 3 estuviera vacío',
      'Histogram mean does not match the filled observations': 'La media del histograma no coincide con las observaciones llenadas',
      'Histogram standard deviation does not match the filled observations': 'La desviación estándar del histograma no coincide con las observaciones llenadas',
    },
  },
  en: {
    passedLabel: 'Completed',
    failedLabel: 'Tests failed',
    testsPassed: (n, m) => `${n}/${m} tests passed`,
    allPassed: 'All tests passed',
    cases: {
      'entries versus bin contents': 'entries versus bin contents',
      'summary statistics': 'summary statistics',
    },
    messages: {
      'Expected 5 total entries': 'Expected 5 total entries',
      'Expected 2 entries in ROOT bin 2': 'Expected 2 entries in ROOT bin 2',
      'Expected an empty ROOT bin 3': 'Expected an empty ROOT bin 3',
      'Histogram mean does not match the filled observations': 'Histogram mean does not match the filled observations',
      'Histogram standard deviation does not match the filled observations': 'Histogram standard deviation does not match the filled observations',
    },
  },
};

/**
 * Grade execution output for cpp-root-histogram-inspect.
 * @param {Object} r - JSON object emitted by rk.h
 * @param {string} [lang='es']
 * @returns {Object} Structured grading result
 */
function gradeHistogramInspect(r, lang = 'es') {
  const i18n = LOCALIZATION[lang] || LOCALIZATION.es;
  const cases = [];

  // Case 1: entries versus bin contents
  const t0_c1 = performance.now();
  let c1_passed = true;
  let c1_msg = 'Passed';
  let c1_expected = null;
  let c1_actual = null;

  const entries = Number(r['entries']);
  const bin2 = Number(r['bin2 content']);
  const bin3 = Number(r['bin3 content']);

  if (!isClose(entries, 5.0)) {
    c1_passed = false;
    c1_msg = 'Expected 5 total entries';
    c1_expected = 5.0;
    c1_actual = entries;
  } else if (!isClose(bin2, 2.0)) {
    c1_passed = false;
    c1_msg = 'Expected 2 entries in ROOT bin 2';
    c1_expected = 2.0;
    c1_actual = bin2;
  } else if (!isClose(bin3, 0.0)) {
    c1_passed = false;
    c1_msg = 'Expected an empty ROOT bin 3';
    c1_expected = 0.0;
    c1_actual = bin3;
  }

  const c1_name = i18n.cases['entries versus bin contents'];
  const c1_loc_msg = c1_passed ? 'Passed' : (i18n.messages[c1_msg] || c1_msg);
  cases.push({
    name: c1_name,
    passed: c1_passed,
    message: c1_loc_msg,
    expected: c1_expected !== null ? String(c1_expected) : null,
    actual: c1_actual !== null ? String(c1_actual) : null,
    expected_got: c1_passed ? null : formatExpectedGot(c1_expected, c1_actual, lang),
    duration_ms: Math.round((performance.now() - t0_c1) * 100) / 100,
  });

  // Case 2: summary statistics
  const t0_c2 = performance.now();
  let c2_passed = true;
  let c2_msg = 'Passed';
  let c2_expected = null;
  let c2_actual = null;

  const mean = Number(r['mean']);
  const stddev = Number(r['stddev']);

  if (!isClose(mean, 2.04, 1e-8, 1e-8)) {
    c2_passed = false;
    c2_msg = 'Histogram mean does not match the filled observations';
    c2_expected = 2.04;
    c2_actual = mean;
  } else if (!isClose(stddev, 1.333566, 1e-5, 1e-5)) {
    c2_passed = false;
    c2_msg = 'Histogram standard deviation does not match the filled observations';
    c2_expected = 1.333566;
    c2_actual = stddev;
  }

  const c2_name = i18n.cases['summary statistics'];
  const c2_loc_msg = c2_passed ? 'Passed' : (i18n.messages[c2_msg] || c2_msg);
  cases.push({
    name: c2_name,
    passed: c2_passed,
    message: c2_loc_msg,
    expected: c2_expected !== null ? String(c2_expected) : null,
    actual: c2_actual !== null ? String(c2_actual) : null,
    expected_got: c2_passed ? null : formatExpectedGot(c2_expected, c2_actual, lang),
    duration_ms: Math.round((performance.now() - t0_c2) * 100) / 100,
  });

  const n_pass = cases.filter((c) => c.passed).length;
  const isAllPassed = n_pass === cases.length;

  return {
    status: isAllPassed ? 'passed' : 'failed',
    status_label: isAllPassed ? i18n.passedLabel : i18n.failedLabel,
    summary: i18n.testsPassed(n_pass, cases.length),
    cases,
  };
}

export class BrowserGrader {
  /**
   * Grade parsed rk output for a given exercise.
   * @param {string} exerciseId
   * @param {Object} rkData
   * @param {string} [lang='es']
   */
  static grade(exerciseId, rkData, lang = 'es') {
    if (exerciseId === 'cpp-root-histogram-inspect') {
      return gradeHistogramInspect(rkData, lang);
    }
    throw new Error(`Browser grading not implemented for exercise: ${exerciseId}`);
  }
}
