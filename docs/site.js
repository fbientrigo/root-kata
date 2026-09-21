(() => {
  const lang = document.documentElement.lang || 'es';
  const MESSAGES = {
    es: {
      copied: 'Comando del kata copiado. Pégalo en una celda de Jupyter.',
      badges: { first_kata: 'Primer kata', first_root_histogram: 'Primer histograma ROOT', basics_complete: 'Fundamentos completados' },
      completed: 'Completado',
      showing: (visible, total) => `${visible} de ${total} ejercicios`,
      showProblem: 'Mostrar problema',
      hideProblem: 'Ocultar problema',
      showOutput: 'Mostrar salida',
      hideOutput: 'Ocultar salida',
    },
    en: {
      copied: 'Kata command copied. Paste it into a Jupyter cell.',
      badges: { first_kata: 'First Kata', first_root_histogram: 'First ROOT Histogram', basics_complete: 'Basics Complete' },
      completed: 'Completed',
      showing: (visible, total) => `${visible} of ${total} exercises`,
      showProblem: 'Show problem',
      hideProblem: 'Hide problem',
      showOutput: 'Show output',
      hideOutput: 'Hide output',
    },
  };
  const msg = MESSAGES[lang] || MESSAGES.es;
  const siteRoot = new URL('.', document.currentScript?.src || location.href);

  const readSet = (key) => {
    try {
      const raw = JSON.parse(localStorage.getItem(key) || '[]');
      return new Set(Array.isArray(raw) ? raw.filter((x) => typeof x === 'string' && /^[\w-]+$/.test(x)) : []);
    } catch { return new Set(); }
  };
  const writeSet = (key, set) => {
    try { localStorage.setItem(key, JSON.stringify([...set].sort())); } catch {}
  };

  const showToast = (message) => {
    document.querySelector('.toast')?.remove();
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.setAttribute('role', 'status');
    toast.textContent = message;
    document.body.append(toast);
    window.setTimeout(() => toast.remove(), 2600);
  };

  const absorbParams = () => {
    const params = new URLSearchParams(location.search);
    if (!params.has('solved') && !params.has('badge')) return;
    const solved = readSet('root-kata:solved');
    const badges = readSet('root-kata:badges');
    let changed = false;
    for (const key of ['solved', 'badge']) {
      for (const value of params.getAll(key).join(',').split(',')) {
        const id = value.trim();
        if (!id || !/^[\w-]+$/.test(id)) continue;
        const target = key === 'solved' ? solved : badges;
        if (!target.has(id)) { target.add(id); changed = true; }
      }
    }
    if (changed) { writeSet('root-kata:solved', solved); writeSet('root-kata:badges', badges); }
    history.replaceState(null, '', location.pathname + location.hash);
  };

  const renderProgress = () => {
    const panel = document.querySelector('.progress-panel');
    if (!panel) return;
    const total = Number(panel.dataset.total || 0);
    const solved = [...readSet('root-kata:solved')];
    const count = Math.min(solved.length, total);
    const bar = document.getElementById('overall-progress');
    const label = document.getElementById('progress-count');
    if (bar) bar.value = String(count);
    if (label) label.textContent = `${count} / ${total}`;
    const badgeList = document.getElementById('badge-list');
    if (badgeList) {
      badgeList.textContent = '';
      for (const id of readSet('root-kata:badges')) {
        const li = document.createElement('li');
        li.className = 'badge-pill';
        li.textContent = `🏅 ${msg.badges[id] || id}`;
        badgeList.append(li);
      }
    }
    document.querySelectorAll('.kata-row').forEach((row) => {
      const isSolved = solved.includes(row.dataset.eid || '');
      row.classList.toggle('solved', isSolved);
      row.querySelector('.status-icon')?.replaceChildren(document.createTextNode(isSolved ? '✓' : '○'));
      const statusLabel = row.querySelector('.status-label');
      if (statusLabel) statusLabel.textContent = isSolved ? msg.completed : '';
      const open = row.querySelector('.button.primary');
      const problem = row.querySelector('.problem-link');
      const done = row.querySelector('.completed-label');
      if (open) open.hidden = isSolved;
      if (done) done.hidden = !isSolved;
      if (problem && isSolved) problem.classList.add('emphasised');
    });
  };

  const renderDifficultyFilter = () => {
    const filter = document.getElementById('difficulty-filter');
    const count = document.getElementById('filter-count');
    if (!filter) return;
    const rows = [...document.querySelectorAll('.kata-row')];
    const apply = () => {
      const selected = filter.value || 'all';
      let visible = 0;
      rows.forEach((row) => {
        const show = selected === 'all' || row.dataset.difficulty === selected;
        row.hidden = !show;
        if (show) visible += 1;
      });
      if (count) count.textContent = msg.showing(visible, rows.length);
    };
    filter.addEventListener('change', apply);
    apply();
  };

  const setupJupyterOptIn = () => {
    const params = new URLSearchParams(location.search);
    let enabled = false;
    try {
      if (params.get('jupyter') === '1') localStorage.setItem('root-kata:jupyter-enabled', '1');
      if (params.get('jupyter') === '0') localStorage.removeItem('root-kata:jupyter-enabled');
      enabled = localStorage.getItem('root-kata:jupyter-enabled') === '1';
    } catch {
      enabled = params.get('jupyter') === '1';
    }

    document.querySelectorAll('.jupyter-opt-in').forEach((element) => {
      element.hidden = !enabled;
    });

    if (params.has('jupyter')) {
      params.delete('jupyter');
      const query = params.toString();
      history.replaceState(null, '', location.pathname + (query ? '?' + query : '') + location.hash);
    }
  };

  const setupSolveProblemToggle = () => {
    const workspace = document.querySelector('.solve-workspace');
    const toggle = document.getElementById('problem-toggle');
    if (!workspace || !toggle) return;

    const showLabel = toggle.dataset.showLabel || msg.showProblem;
    const hideLabel = toggle.dataset.hideLabel || msg.hideProblem;
    const setHidden = (hidden) => {
      workspace.classList.toggle('problem-hidden', hidden);
      toggle.setAttribute('aria-expanded', hidden ? 'false' : 'true');
      toggle.textContent = hidden ? showLabel : hideLabel;
    };

    setHidden(window.matchMedia('(max-width: 760px)').matches);
    toggle.addEventListener('click', () => setHidden(!workspace.classList.contains('problem-hidden')));
  };

  const setupSolveOutputPane = () => {
    const pane = document.querySelector('.solve-code-pane');
    const output = document.getElementById('solve-output');
    const resizer = document.getElementById('output-resizer');
    const toggle = document.getElementById('output-toggle');
    if (!pane || !output || !resizer || !toggle) return;

    const showLabel = toggle.dataset.showLabel || msg.showOutput;
    const hideLabel = toggle.dataset.hideLabel || msg.hideOutput;

    const setHidden = (hidden) => {
      pane.classList.toggle('output-hidden', hidden);
      toggle.setAttribute('aria-expanded', hidden ? 'false' : 'true');
      toggle.textContent = hidden ? showLabel : hideLabel;
    };

    const setHeight = (height) => {
      const min = 120;
      const max = Math.max(min, pane.clientHeight - 168);
      const clamped = Math.min(max, Math.max(min, height));
      pane.style.setProperty('--output-height', clamped + 'px');
    };

    const resizeFromY = (clientY) => {
      const rect = pane.getBoundingClientRect();
      setHeight(rect.bottom - clientY);
    };

    resizer.addEventListener('pointerdown', (event) => {
      if (pane.classList.contains('output-hidden')) return;
      event.preventDefault();
      resizer.setPointerCapture?.(event.pointerId);
      const move = (moveEvent) => resizeFromY(moveEvent.clientY);
      const stop = () => {
        window.removeEventListener('pointermove', move);
        window.removeEventListener('pointerup', stop);
      };
      window.addEventListener('pointermove', move);
      window.addEventListener('pointerup', stop, {once: true});
    });

    resizer.addEventListener('keydown', (event) => {
      if (!['ArrowUp', 'ArrowDown'].includes(event.key)) return;
      event.preventDefault();
      const current = output.getBoundingClientRect().height || 200;
      setHeight(current + (event.key === 'ArrowUp' ? 24 : -24));
    });

    toggle.addEventListener('click', () => {
      setHidden(!pane.classList.contains('output-hidden'));
    });
  };

  const setupWorkspaceRun = () => {
    const form = document.getElementById('run-form');
    const editor = document.getElementById('code-editor');
    const button = document.getElementById('run-button');
    const status = document.querySelector('.workspace-status');
    const feedback = document.getElementById('run-feedback');
    if (!form || !editor || !button || !status || !feedback) return;

    const grid = document.querySelector('.workspace-grid');
    const exerciseId = grid?.dataset?.exerciseId ||
      decodeURIComponent(location.pathname.replace(/^\/kata\//, '').replace(/\/$/, ''));
    const browserWasm = grid?.dataset?.browserWasm || 'native';

    const runtimeSelect = document.getElementById('runtime-target-select');
    if (runtimeSelect) {
      try {
        const savedTarget = localStorage.getItem('root-kata:runtime-target');
        if (savedTarget && ['wasm', 'native'].includes(savedTarget)) runtimeSelect.value = savedTarget;
      } catch {}
      runtimeSelect.addEventListener('change', () => {
        try { localStorage.setItem('root-kata:runtime-target', runtimeSelect.value); } catch {}
      });
    }
    const make = (tag, text, className) => {
      const element = document.createElement(tag);
      if (className) element.className = className;
      if (text !== undefined) element.textContent = text;
      return element;
    };
    const details = (label, text) => {
      const block = make('details');
      block.append(make('summary', label));
      block.append(make('pre', text));
      return block;
    };
    const render = (result) => {
      feedback.hidden = false;
      feedback.className = `run-feedback status-${String(result.status || 'unknown').replace(/[^\w-]/g, '')}`;
      feedback.replaceChildren(
        make('h2', result.status_label || result.status || (lang === 'es' ? 'Resultado' : 'Result')),
        make('p', result.summary || '')
      );
      if (Array.isArray(result.cases) && result.cases.length) {
        const list = make('ul', undefined, 'run-cases');
        list.setAttribute('aria-label', lang === 'es' ? 'Pruebas visibles' : 'Visible tests');
        result.cases.forEach((item) => {
          const row = make('li', undefined, item.passed ? 'case-passed' : 'case-failed');
          row.append(make('span', item.passed ? '✓' : '✕', 'case-mark'));
          row.append(make('span', item.name || ''));
          if (!item.passed) {
            const detail = [item.message];
            if (item.expected_got) detail.push(item.expected_got);
            if (detail.some(Boolean)) row.append(make('div', detail.filter(Boolean).join(' · '), 'case-detail'));
          }
          list.append(row);
        });
        feedback.append(list);
      }
      const error = result.first_error;
      if (error) {
        feedback.append(details(
          lang === 'es' ? 'Primer error del compilador' : 'First compiler error',
          [error.message, error.context || `${error.file || ''}:${error.line || ''}`].filter(Boolean).join('\n')
        ));
      }
      if (result.stdout) feedback.append(details('stdout', result.stdout));
      if (result.stderr) feedback.append(details('stderr', result.stderr));
    };

    const changeIndent = (outdent) => {
      const {value, selectionStart: start, selectionEnd: end} = editor;
      if (start === end) {
        editor.setRangeText('  ', start, end, 'end');
        return;
      }
      const lineStart = value.lastIndexOf('\n', start - 1) + 1;
      const lastLineEnd = end > start && value[end - 1] === '\n' ? end - 1 : end;
      const lineEnd = value.indexOf('\n', lastLineEnd);
      const blockEnd = lineEnd === -1 ? value.length : lineEnd;
      const changed = value.slice(lineStart, blockEnd).split('\n').map((line) =>
        outdent ? line.replace(/^ {1,2}/, '') : `  ${line}`
      ).join('\n');
      editor.setRangeText(changed, lineStart, blockEnd, 'select');
    };

    editor.addEventListener('keydown', (event) => {
      if (event.key === 'Tab') {
        event.preventDefault();
        changeIndent(event.shiftKey);
      } else if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
        event.preventDefault();
        if (!button.disabled) form.requestSubmit();
      }
    });

    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      if (button.disabled) return;
      button.disabled = true;
      form.setAttribute('aria-busy', 'true');
      status.textContent = lang === 'es' ? 'Ejecutando…' : 'Running…';
      try {
        let result;
        const selectedTarget = runtimeSelect ? runtimeSelect.value : 'wasm';
        if (browserWasm === 'supported' && selectedTarget === 'wasm') {
          const moduleUrl = new URL('engine/exercise_runner.js', siteRoot).href;
          const { ExerciseRunner } = await import(moduleUrl);
          result = await ExerciseRunner.runExercise(exerciseId, editor.value, {
            lang,
            onStatusChange: (engineStatus) => {
              if (engineStatus === 'booting') {
                status.textContent = lang === 'es' ? 'Cargando compilador…' : 'Loading compiler…';
              } else if (engineStatus === 'running') {
                status.textContent = lang === 'es' ? 'Ejecutando en WebAssembly…' : 'Running in WebAssembly…';
              }
            },
          });
        } else {
          const response = await fetch('/api/run', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({exercise_id: exerciseId, code: editor.value, lang}),
          });
          result = await response.json();
          if (!response.ok) throw new Error(result.message || result.error || 'Request failed');
        }
        render(result);
        status.textContent = result.summary || (lang === 'es' ? 'Ejecución terminada' : 'Run complete');
      } catch (error) {
        render({status: 'request_error', summary: error.message});
        status.textContent = lang === 'es' ? 'No se pudo ejecutar' : 'Could not run';
      } finally {
        button.disabled = false;
        form.removeAttribute('aria-busy');
      }
    });
  };

  setupJupyterOptIn();
  absorbParams();
  renderProgress();
  renderDifficultyFilter();
  setupSolveProblemToggle();
  setupSolveOutputPane();
  setupWorkspaceRun();

  document.querySelectorAll('.jupyter-link').forEach((link) => {
    link.addEventListener('click', () => {
      try { localStorage.setItem('root-kata:lang', lang); } catch {}
      if (link.classList.contains('local-workspace-link')) return;
      const command = link.dataset.command || '';
      if (!command || !navigator.clipboard?.writeText) return;
      navigator.clipboard.writeText(command).then(() => showToast(msg.copied)).catch(() => {});
    });
  });
})();
