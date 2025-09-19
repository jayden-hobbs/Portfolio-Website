(function initTheme() {
  const key = 'theme-light';
  const root = document.documentElement;
  if (localStorage.getItem(key) === '1') root.classList.add('light');
  document.addEventListener('click', (e) => {
    if (e.target && e.target.id === 'themeToggle') {
      root.classList.toggle('light');
      localStorage.setItem(key, root.classList.contains('light') ? '1' : '0');
    }
  });
})();
