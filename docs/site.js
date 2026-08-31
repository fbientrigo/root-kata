(() => {
  const lang = document.documentElement.lang || 'es';
  const MESSAGES = {
    es: {
      copied: 'Comando del kata copiado. Pégalo en una celda de Jupyter.',
      badges: { first_kata: 'Primer kata', first_root_histogram: 'Primer histograma ROOT', basics_complete: 'Fundamentos completados' },
      completed: 'Completado',
      showing: (visible, total) => `${visible} de ${total} ejercicios`,
      practiceHere: 'Practicar aquí',
      localTitle: 'Servidor local activo',
      localBody: 'Abre un kata y edita el código directamente en esta página.',
    },
    en: {
      copied: 'Kata command copied. Paste it into a Jupyter cell.',
      badges: { first_kata: 'First Kata', first_root_histogram: 'First ROOT Histogram', basics_complete: 'Basics Complete' },
      completed: 'Completed',
      showing: (visible, total) => `${visible} of ${total} exercises`,
      practiceHere: 'Practice here',
      localTitle: 'Local server active',
      localBody: 'Open a kata and edit the code directly on this page.',
    },
  };
  const msg = MESSAGES[lang] || MESSAGES.es;

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

  const isLocalServe = () =>
    location.protocol === 'http:' && ['127.0.0.1', 'localhost', '::1'].includes(location.hostname);

  const exerciseIdForLink = (link) => {
    const fromRow = link.closest('[data-eid]')?.dataset.eid;
    if (fromRow) return fromRow;
    const fromPath = location.pathname.match(/\/problems\/([\w-]+)\.html$/)?.[1];
    if (fromPath) return fromPath;
    return link.dataset.command?.match(/rk\.start\(["']([\w-]+)["']\)/)?.[1] || '';
  };

  const enableLocalWorkspace = () => {
    if (!isLocalServe()) return;
    document.querySelectorAll('.jupyter-link').forEach((link) => {
      const eid = exerciseIdForLink(link);
      if (!eid) return;
      link.href = `/kata/${encodeURIComponent(eid)}?lang=${encodeURIComponent(lang)}`;
      link.removeAttribute('target');
      link.removeAttribute('rel');
      link.textContent = msg.practiceHere;
      link.classList.add('local-workspace-link');
    });

    const note = document.querySelector('.local-note');
    if (note) {
      const strong = document.createElement('strong');
      const span = document.createElement('span');
      strong.textContent = msg.localTitle;
      span.textContent = msg.localBody;
      note.replaceChildren(strong, span);
    }
  };

  const setupWorkspaceRun = () => {
    const form = document.getElementById('run-form');
    const editor = document.getElementById('code-editor');
    const button = document.getElementById('run-button');
    const status = document.querySelector('.workspace-status');
    const feedback = document.getElementById('run-feedback');
    if (!form || !editor || !button || !status || !feedback) return;

    const exerciseId = decodeURIComponent(location.pathname.replace(/^\/kata\//, '').replace(/\/$/, ''));
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

    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      if (button.disabled) return;
      button.disabled = true;
      form.setAttribute('aria-busy', 'true');
      status.textContent = lang === 'es' ? 'Ejecutando…' : 'Running…';
      try {
        const response = await fetch('/api/run', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({exercise_id: exerciseId, code: editor.value, lang}),
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.message || result.error || 'Request failed');
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

  absorbParams();
  renderProgress();
  renderDifficultyFilter();
  enableLocalWorkspace();
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
