// Carga la interfaz real (i18n.js y app.js) en una VM de Node, sin navegador.
//
// Lo mínimo del DOM para que los dos archivos corran: `document`, un nodo que
// guarda lo que se le escribe en `innerHTML`, y lo que app.js lee al arrancar.
// No se simula el navegador: se prueba la lógica y lo que se dibuja, que es
// donde están los errores que importan (qué se escapa, qué se cuenta).

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import vm from 'node:vm';

const WEB = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', '..', 'app', 'web');

function nodo() {
  const base = { innerHTML: '', textContent: '', style: {}, dataset: {}, value: '' };
  return new Proxy(base, {
    get(t, k) {
      if (k in t) return t[k];
      if (k === 'classList') return { add() {}, remove() {}, toggle() {}, contains: () => false };
      if (k === 'querySelectorAll') return () => [];
      if (k === 'querySelector') return () => null;
      return () => {};
    },
  });
}

export function cargar({ idioma = 'es' } = {}) {
  const pantalla = nodo();
  // Los nodos que existen fuera de lo que dibuja render(): el pie, y los que un
  // test pone a mano para simular un campo lleno. Todo lo demás no existe.
  const nodos = new Map([['#pantalla', pantalla], ['#pie-estado', nodo()]]);
  const poner = (sel, props = {}) => {
    const n = Object.assign(nodo(), props);
    nodos.set(sel, n);
    return n;
  };
  const document = {
    querySelector: (s) => nodos.get(s) || null,
    querySelectorAll: () => [],
    addEventListener() {},
    documentElement: nodo(),
    body: nodo(),
    title: '',
  };
  const ctx = {
    document,
    navigator: { language: idioma },
    localStorage: { getItem: () => null, setItem() {} },
    matchMedia: () => ({ matches: false, addEventListener() {} }),
    // Sin red: el arranque cae en su rama de error y la interfaz queda lista.
    fetch: async () => { throw new Error('sin red'); },
    setTimeout,
    clearTimeout,
    // Un intervalo de verdad dejaría a `node --test` esperando para siempre.
    setInterval: () => 0,
    clearInterval() {},
    AbortController,
    console,
    Intl,
    requestAnimationFrame: (f) => f(),
  };
  ctx.window = ctx;
  ctx.window.addEventListener = () => {};
  vm.createContext(ctx);
  for (const archivo of ['i18n.js', 'app.js']) {
    vm.runInContext(fs.readFileSync(path.join(WEB, archivo), 'utf8'), ctx, { filename: archivo });
  }
  const ev = (codigo) => vm.runInContext(codigo, ctx);
  // Un backend de mentira: `rutas` va de la ruta pedida a lo que contesta.
  const backend = (rutas) => {
    ctx.fetch = async (ruta) => {
      const r = rutas[ruta];
      if (r === undefined) throw new Error(`ruta sin respuesta en el test: ${ruta}`);
      return { ok: true, status: 200, json: async () => r };
    };
  };
  return { ctx, ev, pantalla, poner, nodos, backend };
}
