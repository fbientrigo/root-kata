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

  const syncScroll = () => {
    // The textarea includes a final empty line and native scrollbar space.
    // A pre has different scroll limits; mirror offsets, not its scroll range.
    code.style.transform = `translate(${-editor.scrollLeft}px, ${-editor.scrollTop}px)`;
  };

  const render = () => {
    try {
      code.innerHTML = prism.highlight(editor.value, prism.languages.cpp, 'cpp');
      // Prism normalizes some characters (e.g. NBSP). Show the authoritative
      // native editor if highlighting cannot preserve the source exactly.
      shell.classList.toggle('syntax-highlighted', code.textContent === editor.value);
    } catch {
      shell.classList.remove('syntax-highlighted');
    }
    syncScroll();
  };

  editor.addEventListener('input', render);
  editor.addEventListener('scroll', syncScroll, {passive: true});

  render();
})();
