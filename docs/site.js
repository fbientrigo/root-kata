(() => {
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
      if (!command || !navigator.clipboard?.writeText) return;
      navigator.clipboard.writeText(command).then(() => showToast('Kata command copied. Paste it into a Jupyter cell.')).catch(() => {});
    });
  });
})();
