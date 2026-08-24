(() => {
  const lang = document.documentElement.lang || 'es';
  const MESSAGES = {
    es: {
      copied: 'Comando del kata copiado. Pégalo en una celda de Jupyter.',
      badges: { first_kata: 'Primer kata', first_root_histogram: 'Primer histograma ROOT', basics_complete: 'Fundamentos completados' },
      completed: 'Completado',
    },
    en: {
      copied: 'Kata command copied. Paste it into a Jupyter cell.',
      badges: { first_kata: 'First Kata', first_root_histogram: 'First ROOT Histogram', basics_complete: 'Basics Complete' },
      completed: 'Completed',
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

  // --- absorb progress carried in the URL (?solved=<id>&badge=<id>), then clean it
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

  // --- dashboard rendering
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

  absorbParams();
  renderProgress();

  document.querySelectorAll('.jupyter-link').forEach((link) => {
    link.addEventListener('click', () => {
      const command = link.dataset.command || '';
      try { localStorage.setItem('root-kata:lang', lang); } catch {}
      if (!command || !navigator.clipboard?.writeText) return;
      navigator.clipboard.writeText(command).then(() => showToast(msg.copied)).catch(() => {});
    });
  });
})();
