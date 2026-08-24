(() => {
  const lang = document.documentElement.lang || 'es';
  const toasts = {
    es: 'Comando del kata copiado. Pégalo en una celda de Jupyter.',
    en: 'Kata command copied. Paste it into a Jupyter cell.',
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
  document.querySelectorAll('.jupyter-link').forEach((link) => {
    link.addEventListener('click', () => {
      const command = link.dataset.command || '';
      try { localStorage.setItem('root-kata:lang', lang); } catch {}
      if (!command || !navigator.clipboard?.writeText) return;
      navigator.clipboard.writeText(command).then(() => showToast(toasts[lang] || toasts.es)).catch(() => {});
    });
  });
})();
