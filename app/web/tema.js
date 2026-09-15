/* Se ejecuta antes que el CSS, sincronico y en head, para que el primer frame ya
   salga en el tema elegido. La preferencia la escribe app.js en localStorage. */
try {
  if (localStorage.getItem('tema') === 'claro') {
    document.documentElement.setAttribute('data-theme', 'claro');
  }
} catch (_) { /* sin localStorage se usa el oscuro, que es el de por defecto */ }
