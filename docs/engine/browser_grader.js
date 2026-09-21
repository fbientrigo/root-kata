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
export function isClose(a, b, relTol = 1e-9, absTol = 1e-9) {
  return Math.abs(a - b) <= Math.max(relTol * Math.max(Math.abs(a), Math.abs(b)), absTol);
}

/**
 * Format expected_got string according to language.
 * @param {string|number} expected
 * @param {string|number} actual
 * @param {string} lang
 * @returns {string}
 */
export function formatExpectedGot(expected, actual, lang) {
  return lang === 'es'
    ? `esperaba ${expected}, obtuvo ${actual}`
    : `expected ${expected}, got ${actual}`;
}

const UI_STRINGS = {
  es: {
    passedLabel: 'Resuelto',
    failedLabel: 'Aún no',
    testsPassed: (n, m) => `${n}/${m} pruebas pasaron`,
    allPassed: 'Todas las pruebas pasaron',
  },
  en: {
    passedLabel: 'Completed',
    failedLabel: 'Tests failed',
    testsPassed: (n, m) => `${n}/${m} tests passed`,
    allPassed: 'All tests passed',
  },
};

const EXERCISE_I18N = {
  'cpp-hello-world': {
    es: { cases: { 'prints something': 'imprime algo', 'exact output': 'salida exacta' }, messages: { 'Unexpected value': 'Valor inesperado' } },
    en: { cases: { 'prints something': 'prints something', 'exact output': 'exact output' }, messages: { 'Unexpected value': 'Unexpected value' } },
  },
  'cpp-array-print': {
    es: { cases: { 'value count': 'cantidad de valores', 'first value': 'primer valor', 'second value': 'segundo valor', 'third value': 'tercer valor' }, messages: { 'Unexpected value': 'Valor inesperado' } },
    en: { cases: { 'value count': 'value count', 'first value': 'first value', 'second value': 'second value', 'third value': 'third value' }, messages: { 'Unexpected value': 'Unexpected value' } },
  },
  'cpp-array-index': {
    es: { cases: { 'second value': 'segundo valor' }, messages: { 'Unexpected value': 'Valor inesperado' } },
    en: { cases: { 'second value': 'second value' }, messages: { 'Unexpected value': 'Unexpected value' } },
  },
  'cpp-count-above': {
    es: { cases: { 'mixed values': 'valores mixtos', 'strict boundary': 'frontera estricta', 'empty input': 'entrada vacía', 'negative threshold': 'umbral negativo' }, messages: { 'Unexpected value': 'Valor inesperado' } },
    en: { cases: { 'mixed values': 'mixed values', 'strict boundary': 'strict boundary', 'empty input': 'empty input', 'negative threshold': 'negative threshold' }, messages: { 'Unexpected value': 'Unexpected value' } },
  },
  'cpp-sum-positive': {
    es: { cases: { 'mixed signs': 'signos mixtos', 'all non-positive': 'todos no positivos', 'empty input': 'entrada vacía', 'floats': 'decimales' }, messages: { 'Unexpected value': 'Valor inesperado' } },
    en: { cases: { 'mixed signs': 'mixed signs', 'all non-positive': 'all non-positive', 'empty input': 'empty input', 'floats': 'floats' }, messages: { 'Unexpected value': 'Unexpected value' } },
  },
  'cpp-root-histogram': {
    es: {
      cases: {
        'ROOT object and binning': 'Objeto ROOT y binning',
        'fills input values': 'llena los valores de entrada',
        'underflow and overflow semantics': 'semántica de underflow y overflow',
      },
      messages: {
        'build_histogram returned nullptr': 'build_histogram devolvió nullptr',
        'Histogram name is wrong': 'El nombre del histograma es incorrecto',
        'Number of bins is wrong': 'El número de bins es incorrecto',
        'Lower edge is wrong': 'El borde inferior es incorrecto',
        'Upper edge is wrong': 'El borde superior es incorrecto',
        'Each input value should be filled once': 'Cada valor de entrada debe llenarse una vez',
        'In-range integral should be 3': 'La integral dentro del rango debe ser 3',
        'Histogram mean is unexpected': 'La media del histograma no es la esperada',
        'Under/overflow values still count as entries': 'Los valores bajo/sobre el rango también cuentan como entradas',
        'Default Integral() excludes under/overflow bins': 'Integral() por defecto excluye los bins de underflow y overflow',
      },
    },
    en: {
      cases: {
        'ROOT object and binning': 'ROOT object and binning',
        'fills input values': 'fills input values',
        'underflow and overflow semantics': 'underflow and overflow semantics',
      },
      messages: {
        'build_histogram returned nullptr': 'build_histogram returned nullptr',
        'Histogram name is wrong': 'Histogram name is wrong',
        'Number of bins is wrong': 'Number of bins is wrong',
        'Lower edge is wrong': 'Lower edge is wrong',
        'Upper edge is wrong': 'Upper edge is wrong',
        'Each input value should be filled once': 'Each input value should be filled once',
        'In-range integral should be 3': 'In-range integral should be 3',
        'Histogram mean is unexpected': 'Histogram mean is unexpected',
        'Under/overflow values still count as entries': 'Under/overflow values still count as entries',
        'Default Integral() excludes under/overflow bins': 'Default Integral() excludes under/overflow bins',
      },
    },
  },
  'cpp-root-histogram-inspect': {
    es: {
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
  },
  'cpp-root-histogram-range': {
    es: {
      cases: {
        'range keeps boundary visible': 'el rango mantiene visible el límite',
        'fills every measurement': 'llena cada medición',
      },
      messages: {
        'Histogram must be returned': 'Se debe devolver un histograma',
        'Histogram name is wrong': 'El nombre del histograma es incorrecto',
        'Expected 11 visible bins from 0 to 110': 'Se esperaban 11 bins visibles de 0 a 110',
        'Visible bins must stay 10 units wide': 'Los bins visibles deben mantener un ancho de 10 unidades',
        'Every calibration value should be filled once': 'Cada valor de calibración debe llenarse una vez',
        'All calibration values should be visible': 'Todos los valores de calibración deben ser visibles',
        'Calibration sample should not underflow': 'La muestra de calibración no debe tener underflow',
        'Calibration sample should not overflow': 'La muestra de calibración no debe tener overflow',
      },
    },
    en: {
      cases: {
        'range keeps boundary visible': 'range keeps boundary visible',
        'fills every measurement': 'fills every measurement',
      },
      messages: {
        'Histogram must be returned': 'Histogram must be returned',
        'Histogram name is wrong': 'Histogram name is wrong',
        'Expected 11 visible bins from 0 to 110': 'Expected 11 visible bins from 0 to 110',
        'Visible bins must stay 10 units wide': 'Visible bins must stay 10 units wide',
        'Every calibration value should be filled once': 'Every calibration value should be filled once',
        'All calibration values should be visible': 'All calibration values should be visible',
        'Calibration sample should not underflow': 'Calibration sample should not underflow',
        'Calibration sample should not overflow': 'Calibration sample should not overflow',
      },
    },
  },
  'cpp-root-histogram-selected-sample': {
    es: {
      cases: {
        'strict selection': 'selección estricta',
        'selection versus visible range': 'selección frente a rango visible',
      },
      messages: {
        'Histogram must be returned': 'Se debe devolver un histograma',
        'Histogram name is wrong': 'El nombre del histograma es incorrecto',
        'Histogram binning is wrong': 'El binning del histograma es incorrecto',
        'Strict cut should keep exactly three values': 'El corte estricto debe conservar exactamente tres valores',
        'All three selected values should be visible': 'Los tres valores seleccionados deben ser visibles',
        'Boundary value must not survive a strict cut': 'El valor límite no debe sobrevivir a un corte estricto',
        'Selected overflow value must still count as an entry': 'El valor seleccionado fuera de rango debe contar como entrada',
        'Only one selected value should be visible': 'Solo un valor seleccionado debe ser visible',
        'The out-of-range selected value should land in overflow': 'El valor seleccionado fuera de rango debe caer en overflow',
      },
    },
    en: {
      cases: {
        'strict selection': 'strict selection',
        'selection versus visible range': 'selection versus visible range',
      },
      messages: {
        'Histogram must be returned': 'Histogram must be returned',
        'Histogram name is wrong': 'Histogram name is wrong',
        'Histogram binning is wrong': 'Histogram binning is wrong',
        'Strict cut should keep exactly three values': 'Strict cut should keep exactly three values',
        'All three selected values should be visible': 'All three selected values should be visible',
        'Boundary value must not survive a strict cut': 'Boundary value must not survive a strict cut',
        'Selected overflow value must still count as an entry': 'Selected overflow value must still count as an entry',
        'Only one selected value should be visible': 'Only one selected value should be visible',
        'The out-of-range selected value should land in overflow': 'The out-of-range selected value should land in overflow',
      },
    },
  },
  'cpp-root-tgraph-points': {
    es: {
      cases: {
        'point count': 'conteo de puntos',
        'paired coordinates': 'coordenadas emparejadas',
      },
      messages: {
        'Graph must be returned': 'Se debe devolver un grafo',
        'Graph has the wrong number of points': 'El grafo tiene un número incorrecto de puntos',
        'x coordinate differs': 'La coordenada x difiere',
        'y coordinate differs': 'La coordenada y difiere',
      },
    },
    en: {
      cases: {
        'point count': 'point count',
        'paired coordinates': 'paired coordinates',
      },
      messages: {
        'Graph must be returned': 'Graph must be returned',
        'Graph has the wrong number of points': 'Graph has the wrong number of points',
        'x coordinate differs': 'x coordinate differs',
        'y coordinate differs': 'y coordinate differs',
      },
    },
  },
  'cpp-root-tf1-evaluate': {
    es: {
      cases: {
        'model definition': 'definición del modelo',
        'parameter change affects prediction': 'el cambio de parámetro afecta la predicción',
      },
      messages: {
        'Model must be returned': 'Se debe devolver un modelo',
        'TF1 name is wrong': 'El nombre de TF1 es incorrecto',
        'TF1 should have two parameters': 'TF1 debe tener dos parámetros',
        'Model range is wrong': 'El rango del modelo es incorrecto',
        'Intercept parameter is wrong': 'El parámetro de intercepto es incorrecto',
        'Slope parameter is wrong': 'El parámetro de pendiente es incorrecto',
        'Model evaluation is wrong': 'La evaluación del modelo es incorrecta',
        'Changing the slope should change the prediction': 'Cambiar la pendiente debe cambiar la predicción',
      },
    },
    en: {
      cases: {
        'model definition': 'model definition',
        'parameter change affects prediction': 'parameter change affects prediction',
      },
      messages: {
        'Model must be returned': 'Model must be returned',
        'TF1 name is wrong': 'TF1 name is wrong',
        'TF1 should have two parameters': 'TF1 should have two parameters',
        'Model range is wrong': 'Model range is wrong',
        'Intercept parameter is wrong': 'Intercept parameter is wrong',
        'Slope parameter is wrong': 'Slope parameter is wrong',
        'Model evaluation is wrong': 'Model evaluation is wrong',
        'Changing the slope should change the prediction': 'Changing the slope should change the prediction',
      },
    },
  },
  'cpp-root-tf1-range-parameters': {
    es: {
      cases: {
        'parameter meaning': 'significado de parámetros',
        'model domain and prediction': 'dominio del modelo y predicción',
      },
      messages: {
        'Model must be returned': 'Se debe devolver un modelo',
        'TF1 name is wrong': 'El nombre de TF1 es incorrecto',
        'Amplitude parameter is wrong': 'El parámetro de amplitud es incorrecto',
        'Tau parameter is wrong': 'El parámetro tau es incorrecto',
        'Model range is wrong': 'El rango del modelo es incorrecto',
        'Decay prediction is wrong': 'La predicción de decaimiento es incorrecta',
      },
    },
    en: {
      cases: {
        'parameter meaning': 'parameter meaning',
        'model domain and prediction': 'model domain and prediction',
      },
      messages: {
        'Model must be returned': 'Model must be returned',
        'TF1 name is wrong': 'TF1 name is wrong',
        'Amplitude parameter is wrong': 'Amplitude parameter is wrong',
        'Tau parameter is wrong': 'Tau parameter is wrong',
        'Model range is wrong': 'Model range is wrong',
        'Decay prediction is wrong': 'Decay prediction is wrong',
      },
    },
  },
};

function createCaseBuilder(exerciseId, lang = 'es') {
  const i18n = (EXERCISE_I18N[exerciseId] && EXERCISE_I18N[exerciseId][lang]) || EXERCISE_I18N[exerciseId]?.es || { cases: {}, messages: {} };
  return (caseKey, checkFn) => {
    const t0 = performance.now();
    let passed = true;
    let message = 'Passed';
    let expected = null;
    let actual = null;

    const fail = (msg, exp, act) => {
      passed = false;
      message = msg;
      expected = exp !== undefined ? exp : null;
      actual = act !== undefined ? act : null;
    };

    checkFn(fail);

    const caseName = i18n.cases[caseKey] || caseKey;
    const locMsg = passed ? 'Passed' : (i18n.messages[message] || message);
    return {
      name: caseName,
      passed,
      message: locMsg,
      expected: expected !== null ? String(expected) : null,
      actual: actual !== null ? String(actual) : null,
      expected_got: passed ? null : (expected !== null ? formatExpectedGot(expected, actual, lang) : null),
      duration_ms: Math.round((performance.now() - t0) * 100) / 100,
    };
  };
}

function buildGradingResult(cases, lang = 'es') {
  const ui = UI_STRINGS[lang] || UI_STRINGS.es;
  const n_pass = cases.filter((c) => c.passed).length;
  const isAllPassed = n_pass === cases.length;
  return {
    status: isAllPassed ? 'passed' : 'failed',
    status_label: isAllPassed ? ui.passedLabel : ui.failedLabel,
    summary: ui.testsPassed(n_pass, cases.length),
    cases,
  };
}

function gradeExact(exerciseId, r, lang, specs) {
  const mkCase = createCaseBuilder(exerciseId, lang);
  const cases = specs.map(([key, expected, close = false]) => mkCase(key, (fail) => {
    const actual = r[key];
    const passed = close
      ? isClose(Number(actual), Number(expected))
      : actual === expected;
    if (!passed) fail('Unexpected value', expected, actual);
  }));
  return buildGradingResult(cases, lang);
}

function gradeHelloWorld(r, lang) {
  return gradeExact('cpp-hello-world', r, lang, [
    ['prints something', true],
    ['exact output', true],
  ]);
}

function gradeArrayPrint(r, lang) {
  return gradeExact('cpp-array-print', r, lang, [
    ['value count', 3],
    ['first value', 4],
    ['second value', 8],
    ['third value', 15],
  ]);
}

function gradeArrayIndex(r, lang) {
  return gradeExact('cpp-array-index', r, lang, [['second value', 20]]);
}

function gradeCountAbove(r, lang) {
  return gradeExact('cpp-count-above', r, lang, [
    ['mixed values', 1],
    ['strict boundary', 1],
    ['empty input', 0],
    ['negative threshold', 2],
  ]);
}

function gradeSumPositive(r, lang) {
  return gradeExact('cpp-sum-positive', r, lang, [
    ['mixed signs', 8, true],
    ['all non-positive', 0, true],
    ['empty input', 0, true],
    ['floats', 3.75, true],
  ]);
}

// 1. cpp-root-histogram
function gradeHistogram(r, lang) {
  const mkCase = createCaseBuilder('cpp-root-histogram', lang);
  const cases = [];

  const checkObj = (fail) => {
    if (!r['returned object']) {
      fail('build_histogram returned nullptr', 'TH1D*', 'nullptr');
      return false;
    }
    return true;
  };

  cases.push(mkCase('ROOT object and binning', (fail) => {
    if (!checkObj(fail)) return;
    if (r['name'] !== 'h_pt') {
      fail('Histogram name is wrong', 'h_pt', r['name']);
    } else if (Number(r['nbins']) !== 10) {
      fail('Number of bins is wrong', 10, Number(r['nbins']));
    } else if (!isClose(Number(r['xmin']), 0.0)) {
      fail('Lower edge is wrong', 0.0, Number(r['xmin']));
    } else if (!isClose(Number(r['xmax']), 100.0)) {
      fail('Upper edge is wrong', 100.0, Number(r['xmax']));
    }
  }));

  cases.push(mkCase('fills input values', (fail) => {
    if (!checkObj(fail)) return;
    if (!isClose(Number(r['entries']), 3.0)) {
      fail('Each input value should be filled once', 3.0, Number(r['entries']));
    } else if (!isClose(Number(r['integral']), 3.0)) {
      fail('In-range integral should be 3', 3.0, Number(r['integral']));
    } else if (!isClose(Number(r['mean']), 20.0)) {
      fail('Histogram mean is unexpected', 20.0, Number(r['mean']));
    }
  }));

  cases.push(mkCase('underflow and overflow semantics', (fail) => {
    if (!checkObj(fail)) return;
    if (!isClose(Number(r['ovf entries']), 3.0)) {
      fail('Under/overflow values still count as entries', 3.0, Number(r['ovf entries']));
    } else if (!isClose(Number(r['ovf integral']), 1.0)) {
      fail('Default Integral() excludes under/overflow bins', 1.0, Number(r['ovf integral']));
    }
  }));

  return buildGradingResult(cases, lang);
}

// 2. cpp-root-histogram-inspect
function gradeHistogramInspect(r, lang) {
  const mkCase = createCaseBuilder('cpp-root-histogram-inspect', lang);
  const cases = [];

  cases.push(mkCase('entries versus bin contents', (fail) => {
    const entries = Number(r['entries']);
    const bin2 = Number(r['bin2 content']);
    const bin3 = Number(r['bin3 content']);
    if (!isClose(entries, 5.0)) {
      fail('Expected 5 total entries', 5.0, entries);
    } else if (!isClose(bin2, 2.0)) {
      fail('Expected 2 entries in ROOT bin 2', 2.0, bin2);
    } else if (!isClose(bin3, 0.0)) {
      fail('Expected an empty ROOT bin 3', 0.0, bin3);
    }
  }));

  cases.push(mkCase('summary statistics', (fail) => {
    const mean = Number(r['mean']);
    const stddev = Number(r['stddev']);
    if (!isClose(mean, 2.04, 1e-8, 1e-8)) {
      fail('Histogram mean does not match the filled observations', 2.04, mean);
    } else if (!isClose(stddev, 1.333566, 1e-5, 1e-5)) {
      fail('Histogram standard deviation does not match the filled observations', 1.333566, stddev);
    }
  }));

  return buildGradingResult(cases, lang);
}

// 3. cpp-root-histogram-range
function gradeHistogramRange(r, lang) {
  const mkCase = createCaseBuilder('cpp-root-histogram-range', lang);
  const cases = [];

  cases.push(mkCase('range keeps boundary visible', (fail) => {
    if (!r['returned object']) {
      fail('Histogram must be returned', true, false);
    } else if (r['name'] !== 'h_calibration') {
      fail('Histogram name is wrong', 'h_calibration', r['name']);
    } else if (Number(r['nbins']) !== 11) {
      fail('Expected 11 visible bins from 0 to 110', 11, Number(r['nbins']));
    } else if (!isClose(Number(r['xmin']), 0.0)) {
      fail('Expected 11 visible bins from 0 to 110', 0.0, Number(r['xmin']));
    } else if (!isClose(Number(r['xmax']), 110.0)) {
      fail('Expected 11 visible bins from 0 to 110', 110.0, Number(r['xmax']));
    } else if (!isClose(Number(r['bin width']), 10.0)) {
      fail('Visible bins must stay 10 units wide', 10.0, Number(r['bin width']));
    }
  }));

  cases.push(mkCase('fills every measurement', (fail) => {
    if (!isClose(Number(r['entries']), 11.0)) {
      fail('Every calibration value should be filled once', 11.0, Number(r['entries']));
    } else if (!isClose(Number(r['visible integral']), 11.0)) {
      fail('All calibration values should be visible', 11.0, Number(r['visible integral']));
    } else if (!isClose(Number(r['underflow']), 0.0)) {
      fail('Calibration sample should not underflow', 0.0, Number(r['underflow']));
    } else if (!isClose(Number(r['overflow']), 0.0)) {
      fail('Calibration sample should not overflow', 0.0, Number(r['overflow']));
    }
  }));

  return buildGradingResult(cases, lang);
}

// 4. cpp-root-histogram-selected-sample
function gradeHistogramSelectedSample(r, lang) {
  const mkCase = createCaseBuilder('cpp-root-histogram-selected-sample', lang);
  const cases = [];

  cases.push(mkCase('strict selection', (fail) => {
    if (!r['a returned']) {
      fail('Histogram must be returned', true, false);
    } else if (r['name'] !== 'h_selected') {
      fail('Histogram name is wrong', 'h_selected', r['name']);
    } else if (Number(r['nbins']) !== 5) {
      fail('Histogram binning is wrong', 5, Number(r['nbins']));
    } else if (!isClose(Number(r['xmin']), 0.0)) {
      fail('Histogram binning is wrong', 0.0, Number(r['xmin']));
    } else if (!isClose(Number(r['xmax']), 150.0)) {
      fail('Histogram binning is wrong', 150.0, Number(r['xmax']));
    } else if (!isClose(Number(r['a entries']), 3.0)) {
      fail('Strict cut should keep exactly three values', 3.0, Number(r['a entries']));
    } else if (!isClose(Number(r['a integral']), 3.0)) {
      fail('All three selected values should be visible', 3.0, Number(r['a integral']));
    } else if (!isClose(Number(r['a first bin']), 0.0)) {
      fail('Boundary value must not survive a strict cut', 0.0, Number(r['a first bin']));
    }
  }));

  cases.push(mkCase('selection versus visible range', (fail) => {
    if (!r['b returned']) {
      fail('Histogram must be returned', true, false);
    } else if (!isClose(Number(r['b entries']), 2.0)) {
      fail('Selected overflow value must still count as an entry', 2.0, Number(r['b entries']));
    } else if (!isClose(Number(r['b integral']), 1.0)) {
      fail('Only one selected value should be visible', 1.0, Number(r['b integral']));
    } else if (!isClose(Number(r['b overflow']), 1.0)) {
      fail('The out-of-range selected value should land in overflow', 1.0, Number(r['b overflow']));
    }
  }));

  return buildGradingResult(cases, lang);
}

// 5. cpp-root-tgraph-points
function gradeTGraphPoints(r, lang) {
  const mkCase = createCaseBuilder('cpp-root-tgraph-points', lang);
  const cases = [];

  cases.push(mkCase('point count', (fail) => {
    if (!r['returned object']) {
      fail('Graph must be returned', true, false);
    } else if (Number(r['n']) !== 3) {
      fail('Graph has the wrong number of points', 3, Number(r['n']));
    }
  }));

  cases.push(mkCase('paired coordinates', (fail) => {
    const expected = [[0.0, 2.0], [1.5, 3.5], [4.0, 3.0]];
    for (let i = 0; i < expected.length; i++) {
      const [expX, expY] = expected[i];
      const actX = Number(r[`x${i}`]);
      const actY = Number(r[`y${i}`]);
      if (!isClose(actX, expX)) {
        fail('x coordinate differs', expX, actX);
        return;
      }
      if (!isClose(actY, expY)) {
        fail('y coordinate differs', expY, actY);
        return;
      }
    }
  }));

  return buildGradingResult(cases, lang);
}

// 6. cpp-root-tf1-evaluate
function gradeTf1Evaluate(r, lang) {
  const mkCase = createCaseBuilder('cpp-root-tf1-evaluate', lang);
  const cases = [];

  cases.push(mkCase('model definition', (fail) => {
    if (!r['returned object']) {
      fail('Model must be returned', true, false);
    } else if (r['name'] !== 'calibration_model') {
      fail('TF1 name is wrong', 'calibration_model', r['name']);
    } else if (Number(r['npar']) !== 2) {
      fail('TF1 should have two parameters', 2, Number(r['npar']));
    } else if (!isClose(Number(r['xmin']), 0.0)) {
      fail('Model range is wrong', 0.0, Number(r['xmin']));
    } else if (!isClose(Number(r['xmax']), 10.0)) {
      fail('Model range is wrong', 10.0, Number(r['xmax']));
    } else if (!isClose(Number(r['p0']), 2.0)) {
      fail('Intercept parameter is wrong', 2.0, Number(r['p0']));
    } else if (!isClose(Number(r['p1']), 3.0)) {
      fail('Slope parameter is wrong', 3.0, Number(r['p1']));
    } else if (!isClose(Number(r['eval0']), 2.0)) {
      fail('Model evaluation is wrong', 2.0, Number(r['eval0']));
    } else if (!isClose(Number(r['eval2']), 8.0)) {
      fail('Model evaluation is wrong', 8.0, Number(r['eval2']));
    }
  }));

  cases.push(mkCase('parameter change affects prediction', (fail) => {
    if (!isClose(Number(r['eval2 changed']), 0.0)) {
      fail('Changing the slope should change the prediction', 0.0, Number(r['eval2 changed']));
    }
  }));

  return buildGradingResult(cases, lang);
}

// 7. cpp-root-tf1-range-parameters
function gradeTf1RangeParameters(r, lang) {
  const mkCase = createCaseBuilder('cpp-root-tf1-range-parameters', lang);
  const cases = [];

  cases.push(mkCase('parameter meaning', (fail) => {
    if (!r['returned object']) {
      fail('Model must be returned', true, false);
    } else if (r['name'] !== 'decay_model') {
      fail('TF1 name is wrong', 'decay_model', r['name']);
    } else if (!isClose(Number(r['p0']), 12.0)) {
      fail('Amplitude parameter is wrong', 12.0, Number(r['p0']));
    } else if (!isClose(Number(r['p1']), 2.0)) {
      fail('Tau parameter is wrong', 2.0, Number(r['p1']));
    } else if (!isClose(Number(r['eval0']), 12.0)) {
      fail('Decay prediction is wrong', 12.0, Number(r['eval0']));
    }
  }));

  cases.push(mkCase('model domain and prediction', (fail) => {
    const expectedEval4 = 12.0 * Math.exp(-2.0);
    if (!isClose(Number(r['xmin']), 0.0)) {
      fail('Model range is wrong', 0.0, Number(r['xmin']));
    } else if (!isClose(Number(r['xmax']), 10.0)) {
      fail('Model range is wrong', 10.0, Number(r['xmax']));
    } else if (!isClose(Number(r['eval4']), expectedEval4, 1e-10, 1e-10)) {
      fail('Decay prediction is wrong', expectedEval4, Number(r['eval4']));
    }
  }));

  return buildGradingResult(cases, lang);
}

const GRADERS = {
  'cpp-hello-world': gradeHelloWorld,
  'cpp-array-print': gradeArrayPrint,
  'cpp-array-index': gradeArrayIndex,
  'cpp-count-above': gradeCountAbove,
  'cpp-sum-positive': gradeSumPositive,
  'cpp-root-histogram': gradeHistogram,
  'cpp-root-histogram-inspect': gradeHistogramInspect,
  'cpp-root-histogram-range': gradeHistogramRange,
  'cpp-root-histogram-selected-sample': gradeHistogramSelectedSample,
  'cpp-root-tgraph-points': gradeTGraphPoints,
  'cpp-root-tf1-evaluate': gradeTf1Evaluate,
  'cpp-root-tf1-range-parameters': gradeTf1RangeParameters,
};

export class BrowserGrader {
  /**
   * Grade parsed rk output for a given exercise.
   * @param {string} exerciseId
   * @param {Object} rkData
   * @param {string} [lang='es']
   */
  static grade(exerciseId, rkData, lang = 'es') {
    const grader = GRADERS[exerciseId];
    if (grader) {
      return grader(rkData, lang);
    }
    throw new Error(`Browser grading not implemented for exercise: ${exerciseId}`);
  }
}
