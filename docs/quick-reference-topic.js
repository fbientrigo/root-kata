(() => {
  const page = document.querySelector('#topic-page');
  const title = document.querySelector('#topic-title');
  const summary = document.querySelector('#topic-summary');
  const mental = document.querySelector('#topic-mental');
  const workflow = document.querySelector('#topic-workflow');
  const recipes = document.querySelector('#topic-recipes');
  const canonical = document.querySelector('#topic-canonical');
  const pitfalls = document.querySelector('#topic-pitfalls');
  const docs = document.querySelector('#topic-doc-links');
  const breadcrumb = document.querySelector('#topic-breadcrumb-current');
  const error = document.querySelector('#topic-error');
  const toast = document.querySelector('#copy-toast');
  const languageButtons = [...document.querySelectorAll('[data-language]')];
  const state = { language: localStorage.getItem('root-kata-quickref-language') || 'cpp', base: null, topic: null };
  const el = (tag, className, text) => { const node = document.createElement(tag); if (className) node.className = className; if (text !== undefined) node.textContent = text; return node; };
  const showToast = (message) => { toast.textContent = message; toast.hidden = false; window.clearTimeout(showToast.timer); showToast.timer = window.setTimeout(() => { toast.hidden = true; }, 1400); };
  const copyText = async (text) => { try { await navigator.clipboard.writeText(text); } catch (_) { const area = document.createElement('textarea'); area.value = text; area.style.position = 'fixed'; area.style.opacity = '0'; document.body.append(area); area.select(); document.execCommand('copy'); area.remove(); } showToast('Código copiado'); };
  const codeRow = (codeText, label) => { const row = el('div', 'code-row'); const pre = el('pre'); pre.append(el('code', '', codeText)); const copy = el('button', 'copy-code', 'Copiar'); copy.type = 'button'; copy.setAttribute('aria-label', `Copiar código para ${label}`); copy.addEventListener('click', () => copyText(codeText)); row.append(pre, copy); return row; };
  const renderRecipe = (recipe) => { const article = el('article', 'topic-recipe'); article.append(el('h3', '', recipe.title)); if (recipe.why) article.append(el('p', 'topic-recipe-why', recipe.why)); article.append(codeRow(recipe[state.language], recipe.title)); if (recipe.note) article.append(el('p', 'topic-recipe-note', recipe.note)); return article; };
  const renderCanonicalItem = (item) => { const article = el('article', 'quickref-item'); article.append(el('h3', '', item.intent)); article.append(codeRow(item[state.language], item.intent)); (item.details || []).forEach((text) => article.append(el('p', 'topic-canonical-note', text))); return article; };
  const render = () => {
    const baseDomain = state.base; const topic = state.topic;
    page.dataset.domain = baseDomain.id; title.textContent = baseDomain.label; breadcrumb.textContent = baseDomain.label; summary.textContent = topic.summary; mental.textContent = topic.mental_model; document.title = `${baseDomain.label} · Hoja de trucos · ROOT Kata`;
    workflow.replaceChildren(...topic.workflow.map((step) => el('li', '', step)));
    recipes.replaceChildren(...topic.recipes.map(renderRecipe));
    canonical.replaceChildren(...baseDomain.items.map(renderCanonicalItem));
    pitfalls.replaceChildren(...topic.pitfalls.map((item) => el('li', '', item)));
    docs.replaceChildren();
    topic.docs.forEach((item) => { const anchor = el('a', '', `${item.label} ↗`); anchor.href = item.url; anchor.target = '_blank'; anchor.rel = 'noopener'; docs.append(anchor); });
  };
  const setLanguage = (language) => { state.language = language; localStorage.setItem('root-kata-quickref-language', language); languageButtons.forEach((button) => button.setAttribute('aria-pressed', String(button.dataset.language === language))); if (state.base && state.topic) render(); };
  languageButtons.forEach((button) => button.addEventListener('click', () => setLanguage(button.dataset.language)));
  const domainId = new URLSearchParams(window.location.search).get('domain');
  Promise.all([
    fetch('quick-reference.json').then((response) => { if (!response.ok) throw new Error(`Base HTTP ${response.status}`); return response.json(); }),
    fetch('quick-reference-topics.json').then((response) => { if (!response.ok) throw new Error(`Topics HTTP ${response.status}`); return response.json(); })
  ]).then(([baseData, topicData]) => {
    state.base = baseData.domains.find((domain) => domain.id === domainId);
    state.topic = topicData.topics.find((topic) => topic.id === domainId);
    if (!state.base || !state.topic) throw new Error(`Unknown domain: ${domainId}`);
    setLanguage(state.language === 'python' ? 'python' : 'cpp');
  }).catch((reason) => {
    console.error(reason);
    [...page.querySelectorAll('.topic-section, .topic-hero, .topic-breadcrumb')].forEach((node) => { node.hidden = true; });
    error.hidden = false;
  });
})();
