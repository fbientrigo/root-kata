(() => {
  const editor = document.getElementById('code-editor');
  const layer = document.getElementById('code-highlight');
  const code = layer?.querySelector('code');
  const shell = editor?.closest('.syntax-editor-shell');
  const prism = window.Prism;

  if (!editor || !layer || !code || !shell || !prism?.languages?.cpp) return;

  if (!prism.languages.cpp['root-type']) {
    prism.languages.insertBefore('cpp', 'class-name', {
      'root-namespace': {
        pattern: /\bROOT(?=\s*::)/,
        alias: 'root-api',
      },
      'root-type': {
        pattern: /\b(?:T[A-Z]\w*|Roo[A-Z]\w*)\b/,
        alias: ['class-name', 'root-api'],
      },
    });
  }

  let renderPending = false;

  const syncScroll = () => {
    layer.scrollTop = editor.scrollTop;
    layer.scrollLeft = editor.scrollLeft;
  };

  const render = () => {
    renderPending = false;
    code.innerHTML = prism.highlight(editor.value, prism.languages.cpp, 'cpp');
    syncScroll();
  };

  const scheduleRender = () => {
    if (renderPending) return;
    renderPending = true;
    window.requestAnimationFrame(render);
  };

  editor.addEventListener('input', scheduleRender);
  editor.addEventListener('scroll', syncScroll, {passive: true});

  render();
  shell.classList.add('syntax-highlighted');
})();
