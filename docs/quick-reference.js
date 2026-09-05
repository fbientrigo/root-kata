(() => {
  const content = document.querySelector('#quickref-content');
  const search = document.querySelector('#quickref-search');
  const filters = document.querySelector('#domain-filters');
  const count = document.querySelector('#quickref-count');
  const empty = document.querySelector('#quickref-empty');
  const toast = document.querySelector('#copy-toast');
  const languageButtons = [...document.querySelectorAll('[data-language]')];

  const state = {
    data: null,
    language: localStorage.getItem('root-kata-quickref-language') || 'cpp',
    domain: 'all',
    query: ''
  };

  const normalize = (value) => value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9_+#]+/g, ' ')
    .trim();

  const haystack = (domain, item) => normalize([
    domain.label,
    item.intent,
    ...(item.aliases || []),
    ...(item.details || [])
  ].join(' '));

  const stopwords = new Set([
    'a', 'an', 'and', 'do', 'how', 'i', 'is', 'need', 'the', 'this', 'to', 'want', 'forgot',
    'como', 'de', 'del', 'el', 'en', 'hacer', 'la', 'las', 'lo', 'los', 'me', 'necesito',
    'olvida', 'olvide', 'para', 'quiero', 'un', 'una', 'y'
  ]);

  const queryTerms = (query) => normalize(query)
    .split(/\s+/)
    .filter((term) => term && !stopwords.has(term));

  const matches = (domain, item) => {
    if (state.domain !== 'all' && domain.id !== state.domain) return false;
    if (!state.query) return true;
    const terms = queryTerms(state.query);
    const text = haystack(domain, item);
    return terms.length === 0 || terms.every((term) => text.includes(term));
  };

  const el = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };

  const link = (label, href) => {
    const node = el('a', '', label);
    node.href = href;
    if (/^https?:/.test(href)) {
      node.target = '_blank';
      node.rel = 'noopener';
    }
    return node;
  };

  const showToast = (message) => {
    toast.textContent = message;
    toast.hidden = false;
    window.clearTimeout(showToast.timer);
    showToast.timer = window.setTimeout(() => { toast.hidden = true; }, 1400);
  };

  const copyText = async (text) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch (_) {
      const area = document.createElement('textarea');
      area.value = text;
      area.style.position = 'fixed';
      area.style.opacity = '0';
      document.body.append(area);
      area.select();
      document.execCommand('copy');
      area.remove();
    }
    showToast('Código copiado');
  };

  const renderItem = (domain, item) => {
    const article = el('article', 'quickref-item');
    if (state.query) article.classList.add('is-match');

    const head = el('div', 'quickref-item-head');
    head.append(el('h3', '', item.intent));
    article.append(head);

    const codeRow = el('div', 'code-row');
    const pre = el('pre');
    const code = el('code', '', item[state.language]);
    pre.append(code);
    const copy = el('button', 'copy-code', 'Copiar');
    copy.type = 'button';
    copy.setAttribute('aria-label', `Copiar código para ${item.intent}`);
    copy.addEventListener('click', () => copyText(item[state.language]));
    codeRow.append(pre, copy);
    article.append(codeRow);

    const hasDetails = (item.details && item.details.length) || item.docs || item.kata;
    if (hasDetails) {
      const details = el('details', 'quickref-details');
      details.append(el('summary', '', 'Detalles'));
      (item.details || []).forEach((text) => details.append(el('p', '', text)));
      const links = el('div', 'quickref-links');
      if (item.kata) links.append(link('Practicar →', item.kata));
      if (item.docs) links.append(link('ROOT docs ↗', item.docs));
      if (links.children.length) details.append(links);
      article.append(details);
    }

    return article;
  };

  const render = () => {
    content.replaceChildren();
    let visibleItems = 0;
    let visibleDomains = 0;

    state.data.domains.forEach((domain) => {
      const items = domain.items.filter((item) => matches(domain, item));
      if (!items.length) return;
      visibleDomains += 1;
      visibleItems += items.length;

      const section = el('section', 'quickref-domain');
      section.dataset.domain = domain.id;
      section.append(el('h2', '', domain.label));
      items.forEach((item) => section.append(renderItem(domain, item)));
      content.append(section);
    });

    count.textContent = `${visibleItems} operaciones · ${visibleDomains} dominios`;
    empty.hidden = visibleItems !== 0;
    content.hidden = visibleItems === 0;
  };

  const renderFilters = () => {
    filters.replaceChildren();
    const options = [{ id: 'all', label: 'Todo' }, ...state.data.domains];
    options.forEach((domain) => {
      const button = el('button', 'domain-filter', domain.label);
      button.type = 'button';
      button.dataset.domain = domain.id;
      button.setAttribute('aria-pressed', String(state.domain === domain.id));
      button.addEventListener('click', () => {
        state.domain = domain.id;
        [...filters.children].forEach((candidate) => {
          candidate.setAttribute('aria-pressed', String(candidate.dataset.domain === state.domain));
        });
        render();
      });
      filters.append(button);
    });
  };

  const setLanguage = (language) => {
    state.language = language;
    localStorage.setItem('root-kata-quickref-language', language);
    languageButtons.forEach((button) => {
      button.setAttribute('aria-pressed', String(button.dataset.language === language));
    });
    render();
  };

  languageButtons.forEach((button) => {
    button.addEventListener('click', () => setLanguage(button.dataset.language));
  });

  search.addEventListener('input', () => {
    state.query = search.value;
    render();
  });

  document.addEventListener('keydown', (event) => {
    const typing = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement?.tagName || '');
    if (event.key === '/' && !typing) {
      event.preventDefault();
      search.focus();
      search.select();
    }
    if (event.key === 'Escape' && document.activeElement === search && search.value) {
      search.value = '';
      state.query = '';
      render();
    }
  });

  fetch('quick-reference.json')
    .then((response) => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response.json();
    })
    .then((data) => {
      state.data = data;
      renderFilters();
      setLanguage(state.language === 'python' ? 'python' : 'cpp');
    })
    .catch((error) => {
      console.error(error);
      empty.hidden = false;
      empty.textContent = 'No pude cargar la referencia. Recarga la página.';
      count.textContent = '';
    });
})();
