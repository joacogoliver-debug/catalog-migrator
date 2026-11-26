/* ============================================================
   Migrador de Catálogos : frontend.

   Vanilla JS a propósito: sin React, sin Babel en el navegador y sin CDN. La
   app se empaqueta como ejecutable, así que no puede depender de una descarga
   en tiempo de ejecución, y sin build step el binario se arma con sólo copiar
   archivos.

   Patrón: un objeto de estado (S), una función render() que dibuja según el
   paso, y eventos por delegación. Simple y suficiente para cinco pantallas.

   Lo visual sigue docs/DESIGN.md. Dos consecuencias que se ven en todo el archivo:
   los iconos son SVG de trazo de una sola familia y nunca emojis (§9), y los
   botones no llevan flechas pegadas al texto.

   Los textos no se escriben acá: salen de i18n.js con T(), y los que
   están en el HTML se marcan con data-t. Si aparece un literal en castellano
   en este archivo, es un bug: en inglés se ve igual.
   ============================================================ */

'use strict';

const S = {
  paso: 1,
  config: null,
  catalogo: null,
  seleccion: new Set(),
  expandidos: new Set(),
  verFaltantes: false,      // la lista de lo que Deezer tiene y YouTube no trajo, desplegada
  deCero: false,            // el próximo relevamiento vuelve a listar el canal, sin reusar
  filtro: { modo: 'manual', anioDesde: null, anioHasta: null, distribs: new Set(), texto: '', faltantes: false },
  opciones: { planilla: true, portadas: true, audio: false },
  job: null,
  resultado: null,
  error: '',
  errorCodigo: '',
  errorCampo: '',           // error de validacion del link, va bajo el campo
  deezerLink: '',           // el link del artista en Deezer que pegó el usuario, si pegó alguno
  deezerUsado: '',          // el que se mandó con el último relevamiento
  deezerError: '',
  pideDeezer: false,        // el campo está a la vista porque se pidió «usar otro perfil»
  errorDescarga: '',        // el ZIP ya no está (vence a la hora): aviso en la misma pantalla
  guardado: null,           // { ruta, archivo } del paquete copiado a la carpeta Descargas
  actualizacion: null,      // lo que contestó la búsqueda de versiones: { hay, ultima } | { buscando } | { error }
  guardando: false,
  entrando: false,          // el proximo render es un cambio de vista: anima la entrada
  // Lo que se escribió en el paso 1. Cada render() reemplaza el formulario
  // entero, y un campo sin `value` volvía vacío: al fallar, el error quedaba
  // debajo de un link que ya no se veía.
  url: '',
  conCodigos: true,
  aviso: '',                // un aviso neutro, no un error: «cancelaste el armado»
  // Lo que el usuario cambia a mano en el paso 2 (ver `ediciones` en el motor).
  editando: null,           // { tipo: 'isrc' | 'upc', producto, indice, valor, error }
  datosAbierto: false,      // el formulario de los campos a completar, a la vista
  datos: {},                // lo que se va escribiendo ahí: clave -> valor
  datosAlcance: 'elegidos', // a qué productos se aplica: 'elegidos' | 'todos'
  datosLineaC: false,       // usar «© año titular» de cada producto
  importacion: null,        // la propuesta de la planilla importada, hasta aplicarla
  importElegidos: new Set(),
  importElecciones: {},     // ítem ambiguo -> el ISRC que se eligió
  comparacion: null,        // el resultado de comparar con un relevamiento guardado
  archivoPara: '',          // para qué se abrió el selector de archivos
  leyendo: '',              // se está leyendo un archivo: 'importar' | 'comparar' | 'abrir'
  hecho: '',                // lo que se acaba de aplicar, dicho en una línea
  errorHerramienta: '',     // el error de la última herramienta, al lado de sus botones
  tidal: null,
  ocupado: false,
  // Pantallas que se superponen al flujo normal.
  vista: null,              // null | 'terminos' | 'clave'
  fatal: '',                // error irrecuperable: se dibuja y nada más
};

const $ = (sel) => document.querySelector(sel);
const pantalla = () => $('#pantalla');

/* ------------------------------------------------------------ iconos */
/* Trazo de 1.5 px, tamaño 20, una sola familia (§7). El grosor y el tamaño
   viven en la clase .ico del CSS, así que acá va sólo la geometría. */

const TRAZOS = {
  info: '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>',
  alerta: '<path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><path d="M12 9v4M12 17h.01"/>',
  error: '<circle cx="12" cy="12" r="10"/><path d="m15 9-6 6M9 9l6 6"/>',
  ok: '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><path d="m22 4-10 10.01-3-3"/>',
  planilla: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M16 13H8M16 17H8M10 9H8"/>',
  imagen: '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="m21 15-5-5L5 21"/>',
  musica: '<path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>',
  enlace: '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>',
  descargar: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m7 10 5 5 5-5M12 15V3"/>',
  flecha: '<path d="m9 18 6-6-6-6"/>',
  llave: '<circle cx="7.5" cy="15.5" r="4.5"/><path d="m21 2-9.6 9.6M15.5 7.5l3 3"/>',
  sol: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/>',
  luna: '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>',
};

/** Un icono. `clase` permite pedir la variante chica. */
function ico(nombre, clase = '') {
  const d = TRAZOS[nombre];
  if (!d) return '';
  return `<svg class="ico ${clase}" viewBox="0 0 24 24" aria-hidden="true" focusable="false">${d}</svg>`;
}

/* ------------------------------------------------------------ utilidades */

/** Escapa para insertar en HTML. Los títulos de YouTube traen de todo. */
function esc(v) {
  if (v === null || v === undefined) return '';
  return String(v).replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ));
}

/* El separador de miles y el decimal cambian con el idioma, y no son un
   detalle: "7.000" es siete mil en castellano y siete con tres decimales en
   ingles. Estaba fijo en es-AR, asi que la app en ingles mostraba las
   reproducciones con el punto castellano. */
function locale() {
  return idioma() === 'en' ? 'en-US' : 'es-AR';
}

function num(n) {
  return (Number(n) || 0).toLocaleString(locale());
}

/** Una cantidad con su palabra en singular o en plural: «1 producto», «3
 *  productos». `html`, si viene, es lo que se muestra en lugar del número. */
function cuenta(clave, n, html) {
  return T(n === 1 ? clave + '_uno' : clave, { n: html === undefined ? num(n) : html });
}

function pesoLegible(bytes) {
  const b = Number(bytes) || 0;
  const dec = (v, d) => v.toLocaleString(locale(), {
    minimumFractionDigits: d, maximumFractionDigits: d,
  });
  if (b >= 1e9) return dec(b / 1e9, 2) + ' GB';
  if (b >= 1e6) return dec(b / 1e6, 1) + ' MB';
  if (b >= 1e3) return num(Math.round(b / 1e3)) + ' KB';
  return b + ' B';
}

/* El token que el servidor inyecta en index.html. Sin esto, /api/ responde 403:
   es lo que impide que una página cualquiera abierta en el navegador le hable a
   la app por localhost. Ver la nota de seguridad en app/server.py. */
const TOKEN = (document.querySelector('meta[name="app-token"]') || {}).content || '';

/** Un pedido al backend.
 *
 *  Con timeout propio, porque `fetch` no tiene uno. Si el backend se cuelga, una
 *  promesa que nunca resuelve deja la interfaz esperando para siempre y sin
 *  ningún mensaje. Las consultas de estado de un trabajo llevan un timeout corto
 *  porque se repiten igual; las acciones, uno largo. */
async function api(ruta, cuerpo, ms = 30000) {
  const ctl = new AbortController();
  const reloj = setTimeout(() => ctl.abort(), ms);
  const opciones = cuerpo === undefined
    ? { method: 'GET', headers: { 'X-App-Token': TOKEN }, signal: ctl.signal }
    : {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-App-Token': TOKEN },
        body: JSON.stringify(cuerpo),
        signal: ctl.signal,
      };
  let r;
  try {
    r = await fetch(ruta, opciones);
  } catch (e) {
    if (e && e.name === 'AbortError') throw new Error(T('red.timeout'));
    throw new Error(T('red.sin_conexion'));
  } finally {
    clearTimeout(reloj);
  }
  let datos = {};
  try { datos = await r.json(); } catch (_) { /* respuesta sin cuerpo */ }
  if (!r.ok) {
    const e = new Error(datos.error || T('red.error_http', { codigo: r.status }));
    e.codigo = datos.codigo_error || '';
    throw e;
  }
  return datos;
}

/** El momento entre "termino" y la vista siguiente: el latido se apaga, aparece
 *  el tilde, y medio segundo despues cambia la pantalla. Con reduced-motion no
 *  se espera. */
async function cierreDelTrabajo() {
  const b = $('#bloque-progreso');
  if (!b || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  b.classList.add('listo');
  const pct = $('#progreso-pct'); if (pct) pct.textContent = '100%';
  const barra = $('.barra-fill'); if (barra) barra.style.transform = 'scaleX(1)';
  await new Promise((r) => setTimeout(r, 500));
}

/** Espera a que termine un trabajo del backend, mostrando el avance. */
async function esperarJob(job, alAvanzar) {
  const id = job.id;
  let fallos = 0;
  for (;;) {
    await new Promise((res) => setTimeout(res, 400));
    let j;
    try {
      j = await api(`/api/job/${id}`, undefined, 15000);
      fallos = 0;
    } catch (e) {
      // Un corte aislado no significa que la app se cayó. Con keep-alive es
      // normal que una consulta suelta falle, así que sólo avisamos después de
      // varias seguidas y un blip no interrumpe un trabajo que va bien.
      if (++fallos < 5) continue;
      throw new Error(T('red.sin_conexion_larga'));
    }
    S.job = j;
    if (alAvanzar) alAvanzar(j);
    if (j.estado === 'listo') { limpiarPie(); return j.resultado; }
    if (j.estado === 'error') {
      limpiarPie();
      const e = new Error(j.error || T('red.proceso_fallo'));
      e.codigo = j.codigo_error || '';
      throw e;
    }
    if (j.estado === 'cancelado') { limpiarPie(); throw new Error('CANCELADO'); }
  }
}

/** El pie muestra el paso del trabajo en curso. Terminado, cancelado o fallado,
 *  «Portada 3 de 4» ya no es el estado de nada. */
function limpiarPie() {
  const pie = $('#pie-estado');
  if (pie) pie.textContent = '';
}

/* ------------------------------------------------------------ tema */

function temaGuardado() {
  // localStorage puede estar bloqueado. Es una preferencia, no un dato: si no
  // se puede leer, se usa el tema del sistema y listo.
  try { return localStorage.getItem('tema') || ''; } catch (_) { return ''; }
}

/** Oscuro es el modo por defecto, no el del sistema.
 *
 *  Sale de la escena de uso y no de la categoria: esta app se abre de noche
 *  para hacer trabajo de inventario. Por eso el oscuro no lleva atributo y el
 *  claro es el que se declara. */
function aplicarTema(t) {
  const raiz = document.documentElement;
  if (t === 'claro') raiz.setAttribute('data-theme', 'claro');
  else raiz.removeAttribute('data-theme');

  const btn = $('#btn-tema');
  if (!btn) return;
  const enOscuro = !raiz.hasAttribute('data-theme');
  const rotulo = T(enOscuro ? 'cabecera.ir_a_claro' : 'cabecera.ir_a_oscuro');
  btn.innerHTML = ico(enOscuro ? 'sol' : 'luna') + `<span class="sr">${esc(rotulo)}</span>`;
  btn.title = rotulo;
}

/* ------------------------------------------------------------ idioma */

/** Marca el idioma en uso en el selector de la cabecera. */
function marcarIdioma() {
  document.querySelectorAll('#selector-idioma button').forEach((b) => {
    b.classList.toggle('activo', b.getAttribute('data-idioma') === idioma());
    b.setAttribute('aria-pressed', String(b.getAttribute('data-idioma') === idioma()));
  });
}

/* ------------------------------------------------------------ stepper */

const PASOS = ['paso1', 'paso2', 'paso3', 'paso4'];

/** ¿Se puede ir a ese paso? Nada de saltar a un paso sin los datos que
 *  necesita. Volver atrás siempre se puede, y el estado de los pasos anteriores
 *  se conserva. */
function pasoAlcanzable(n) {
  if (S.ocupado) return false;             // en medio de un trabajo no se navega
  if (n === 1) return true;
  if (n === 2) return !!S.catalogo;
  if (n === 3) return !!S.catalogo && seleccionados().length > 0;
  if (n === 4) return !!S.resultado;
  return false;
}

function renderStepper() {
  const cont = $('#stepper');
  if (!cont) return;
  // El stepper no tiene sentido mientras se leen los términos o se carga la
  // clave: esas pantallas no son parte del flujo de cuatro pasos.
  if (S.vista || S.fatal || !S.config || !S.config.terminos_aceptados || !S.config.tiene_clave) {
    cont.innerHTML = '';
    return;
  }

  cont.innerHTML = PASOS.map((clavePaso, i) => {
    const n = i + 1;
    const actual = S.paso === n;
    const clase = actual ? 'activo' : (S.paso > n ? 'hecho' : 'inerte');
    const puede = !actual && pasoAlcanzable(n);
    const marca = S.paso > n ? ico('ok', 'ico-sm') : String(n);
    const cuerpo = `<span class="step-num">${marca}</span><span>${esc(T('stepper.' + clavePaso))}</span>`;
    // Los alcanzables son botones de verdad, así se vuelve con el mouse y con el
    // teclado. Sin esto, corregir una selección obligaba a relevar de nuevo.
    return puede
      ? `<button type="button" class="step ${clase}" data-ir-paso="${n}">${cuerpo}</button>`
      : `<div class="step ${clase}" ${actual ? 'aria-current="step"' : ''}>${cuerpo}</div>`;
  }).join('');
}

/* ------------------------------------------------------------ productos filtrados */

function productosFiltrados() {
  if (!S.catalogo) return [];
  let ps = S.catalogo.productos;
  const f = S.filtro;

  if (f.modo === 'fechas' && f.anioDesde !== null) {
    ps = ps.filter((p) => p.anio && p.anio >= f.anioDesde && p.anio <= f.anioHasta);
  } else if (f.modo === 'distribuidora') {
    // Sin ninguna marcada no se muestra nada. Antes, destildar la última
    // mostraba todo: el filtro hacía lo contrario de lo que se le pedía.
    ps = ps.filter((p) => f.distribs.has(p.distribuidora));
  }

  if (f.faltantes) ps = ps.filter(leFaltaAlgo);

  if (f.texto.trim()) {
    const q = f.texto.trim().toLowerCase();
    ps = ps.filter((p) =>
      p.titulo.toLowerCase().includes(q) ||
      (p.upc || '').includes(q) ||
      (p.distribuidora || '').toLowerCase().includes(q) ||
      p.detalle.some((t) => t.titulo.toLowerCase().includes(q) || (t.isrc || '').toLowerCase().includes(q))
    );
  }
  return ordenar(ps);
}

/** Qué tan lejos está un producto de poder entregarse tal cual: los huecos que
 *  hay que completar pesan uno cada uno; lo que vino de Deezer, medio, porque
 *  hay que mirarlo pero no falta nada. Es la clave del orden por estado. */
function gravedad(p) {
  const huecos = (!p.upc ? 1 : 0) + (p.con_isrc < p.tracks ? 1 : 0) + (p.orden_estimado ? 1 : 0)
    + ((p.faltan || []).length ? 1 : 0);
  return huecos + (p.origen === 'deezer' || p.de_deezer > 0 ? 0.5 : 0) + (porConfirmar(p) ? 0.25 : 0);
}

/** Cuántos códigos del producto conviene confirmar: los ISRC que salieron de
 *  una sola fuente, y el UPC si está en la misma situación. No falta nada, y
 *  por eso pesa menos que un hueco; pero es lo que hay que mirar antes de
 *  entregar, y la tabla lo tiene que poder mostrar. */
function porConfirmar(p) {
  return (p.sin_confirmar || 0) + (p.upc_nivel === 'inferido' ? 1 : 0);
}

const CLAVES_DE_ORDEN = {
  titulo: (p) => p.titulo,
  distribuidora: (p) => p.distribuidora || '',
  tipo: (p) => p.tipo || '',
  anio: (p) => Number(p.anio) || 0,
  estado: gravedad,
};

/** El orden que se eligió en la cabecera, o el del relevamiento si no se eligió
 *  ninguno. Estable: ante un empate manda el orden original, así dos clics
 *  seguidos no barajan las filas que empatan. */
function ordenar(ps) {
  const o = S.orden;
  const clave = o && CLAVES_DE_ORDEN[o.col];
  if (!clave) return ps;
  const lugar = new Map(S.catalogo.productos.map((p, i) => [p.id, i]));
  return [...ps].sort((a, b) => {
    const x = clave(a), y = clave(b);
    const c = typeof x === 'number'
      ? x - y
      : String(x).localeCompare(String(y), undefined, { numeric: true, sensitivity: 'base' });
    return (o.dir === 'desc' ? -c : c) || lugar.get(a.id) - lugar.get(b.id);
  });
}

/** Lo mismo que la tabla marca con un badge: sin UPC, con ISRC faltantes o con
 *  el orden sin confirmar. En un catálogo de quinientos productos, «¿qué me
 *  falta?» no se puede contestar scrolleando. */
function leFaltaAlgo(p) {
  return !p.upc || p.con_isrc < p.tracks || !!p.orden_estimado || (p.faltan || []).length > 0
    || p.origen === 'deezer' || p.de_deezer > 0 || porConfirmar(p) > 0;
}

/** Los elegidos que el filtro esconde. Van en el paquete igual, y por eso se
 *  dice: si no, el paquete lleva más de lo que se ve en la tabla. */
function elegidosOcultos() {
  if (!S.catalogo) return 0;
  const visibles = new Set(productosFiltrados().map((p) => p.id));
  let n = 0;
  for (const id of S.seleccion) if (!visibles.has(id)) n++;
  return n;
}

/** Lo que va al paquete: todo lo tildado, se vea o no. El filtro es para mirar,
 *  no para decidir qué se entrega. Antes el paquete llevaba sólo lo elegido
 *  que el filtro dejaba ver, y buscar un título para chequearlo terminaba en un
 *  paquete con ese único producto. */
function seleccionados() {
  if (!S.catalogo) return [];
  return S.catalogo.productos.filter((p) => S.seleccion.has(p.id));
}

/** Si hay un filtro que esconde filas. Cambia cómo se llaman los botones de
 *  marcar: con filtro, actúan sólo sobre lo que se ve. */
function hayFiltro() {
  return !!S.catalogo && productosFiltrados().length !== S.catalogo.productos.length;
}

/* ------------------------------------------------------------ render principal */

/* Redibujar reemplaza el DOM, así que el elemento que tenía el foco desaparece.
   Sin esto, alguien que navegue con teclado pierde su lugar cada vez que tilda
   un filtro. Guardamos cómo identificar al elemento enfocado y lo recuperamos. */

const ATRIBUTOS_FOCO = [
  'data-distrib', 'data-prod', 'data-opcion-check', 'data-modo', 'data-expandir', 'data-ir-paso', 'data-alcance',
  'data-item', 'data-dato', 'data-accion',
];

function tomarFoco() {
  const el = document.activeElement;
  if (!el || el === document.body || el === document.documentElement) return null;
  const marca = { id: el.id || null, attr: null, valor: null, inicio: null, fin: null };
  if (!marca.id) {
    for (const a of ATRIBUTOS_FOCO) {
      if (el.hasAttribute(a)) { marca.attr = a; marca.valor = el.getAttribute(a); break; }
    }
  }
  if (!marca.id && !marca.attr) return null;
  // En campos de texto conservamos también la posición del cursor.
  if (typeof el.selectionStart === 'number') {
    try { marca.inicio = el.selectionStart; marca.fin = el.selectionEnd; } catch (_) {}
  }
  return marca;
}

function devolverFoco(marca) {
  if (!marca) return;
  let el = null;
  if (marca.id) {
    el = document.getElementById(marca.id);
  } else {
    // Comparamos el valor en JS en vez de armar un selector: los nombres de
    // distribuidora pueden traer comillas y romperían el selector.
    el = [...document.querySelectorAll(`[${marca.attr}]`)]
      .find((n) => n.getAttribute(marca.attr) === marca.valor) || null;
  }
  if (!el) return;
  try {
    el.focus({ preventScroll: true });
    if (marca.inicio !== null && typeof el.setSelectionRange === 'function') {
      el.setSelectionRange(marca.inicio, marca.fin);
    }
  } catch (_) { /* el elemento ya no acepta foco */ }
}

function render() {
  const foco = tomarFoco();
  const cambioDeVista = S.entrando;
  try {
    dibujar();
  } catch (e) {
    // Un error dibujando no puede dejar la pantalla en blanco sin explicación.
    mostrarFatal(e);
    return;
  }
  if (cambioDeVista) enfocarTitulo();
  else devolverFoco(foco);
}

/** En un cambio de pantalla el foco va al título nuevo. Si no, queda en el
 *  botón que ya no existe, el navegador lo manda al principio de la página, y
 *  con teclado o lector hay que recorrer toda la cabecera para llegar. */
function enfocarTitulo() {
  const h = pantalla().querySelector('h1');
  if (!h) return;
  h.setAttribute('tabindex', '-1');
  try { h.focus({ preventScroll: true }); } catch (_) { /* sin foco no se rompe nada */ }
}

/* El area que scrollea es main, no la ventana. */
function arriba() { const m = document.querySelector('main'); if (m) m.scrollTop = 0; }

function tituloDocumento() {
  const base = T('app.nombre');
  if (S.vista === 'terminos') return T('titulo.terminos', { app: base });
  if (S.vista === 'clave') return T('titulo.clave', { app: base });
  const a = S.catalogo && S.catalogo.artista;
  if (S.paso === 2 && a) return T('titulo.paso2', { artista: a });
  if (S.paso === 3 && a) return T('titulo.paso3', { artista: a });
  if (S.paso === 4 && a) return T(S.ocupado ? 'titulo.paso4_armando' : 'titulo.paso4_listo', { artista: a });
  return base;
}

function dibujar() {
  renderStepper();
  document.title = tituloDocumento();
  // La clase queda puesta hasta el proximo render, que la saca: solo animan los
  // nodos que se insertan en este.
  pantalla().classList.toggle('entrando', !!S.entrando);
  S.entrando = false;
  const v = $('#version');
  if (v) v.textContent = S.config ? 'v' + S.config.version : '';
  const act = $('#actualizacion');
  if (act) {
    act.textContent = S.config ? textoActualizacion() : '';
    act.classList.toggle('hay-version', !!(S.actualizacion && S.actualizacion.hay));
    act.disabled = !!(S.actualizacion && S.actualizacion.buscando);
  }

  if (S.fatal) { pantalla().innerHTML = vistaFatal(); return; }
  if (!S.config) { pantalla().innerHTML = vistaEsqueleto(); return; }

  // Los términos van primero, y una sola vez.
  if (!S.config.terminos_aceptados) { pantalla().innerHTML = vistaTerminos(true); return; }
  if (S.vista === 'terminos') { pantalla().innerHTML = vistaTerminos(false); return; }
  if (S.vista === 'clave' || !S.config.tiene_clave) { pantalla().innerHTML = vistaClave(); return; }

  if (S.paso === 1) pantalla().innerHTML = vistaPaso1();
  else if (S.paso === 2) pantalla().innerHTML = vistaPaso2();
  else if (S.paso === 3) pantalla().innerHTML = vistaPaso3();
  else pantalla().innerHTML = vistaPaso4();

  // El estado "indeterminado" de una casilla no existe en HTML: es una
  // propiedad que hay que poner por JS después de dibujar.
  const todos = $('#check-todos');
  if (todos && todos.dataset.indeterminado) todos.indeterminate = true;
}

function mostrarFatal(e) {
  S.fatal = (e && e.message) || String(e || T('fatal.desconocido'));
  try {
    renderStepper();
    pantalla().innerHTML = vistaFatal();
  } catch (_) { /* no queda nada por hacer */ }
}

function vistaFatal() {
  return `<div class="card">
    <div class="card-head">
      <h2>${esc(T('fatal.titulo'))}</h2>
      <p>${esc(T('fatal.detalle'))}</p>
    </div>
    ${alerta('danger', 'error', `<span class="mono">${esc(S.fatal)}</span>`)}
    <div class="row mt-5">
      <button class="btn btn-primary" data-accion="recargar">${esc(T('fatal.reiniciar'))}</button>
    </div>
  </div>`;
}

/* Esqueleto con la forma del contenido que viene, en vez de un spinner
   centrado (§7). */
function vistaEsqueleto() {
  return `<div class="card card-hero" aria-busy="true">
    <div class="esqueleto esq-titulo"></div>
    <div class="esqueleto esq-linea"></div>
    <div class="esqueleto esq-linea-corta"></div>
    <div class="esqueleto esq-etiqueta"></div>
    <div class="esqueleto esq-campo"></div>
    <div class="esqueleto esq-boton"></div>
  </div>`;
}

/** Un error se anuncia apenas aparece (`role="alert"`); el resto de las alertas
 *  son parte de la pantalla y se leen con ella, salvo que quien la llama pida
 *  `status` para un aviso que aparece por algo que acaba de pasar. */
function alerta(tipo, icono, html, rol = tipo === 'danger' ? 'alert' : '') {
  const clase = tipo ? ` alerta-${tipo}` : '';
  const r = rol ? ` role="${rol}"` : '';
  return `<div class="alerta${clase}"${r}><span class="alerta-icono">${ico(icono)}</span><div>${html}</div></div>`;
}

/* ------------------------------------------------------------ términos */

/** Los términos completos. El texto vive en el catálogo de i18n, en los dos
 *  idiomas, y no en un archivo aparte, para que la app los pueda mostrar sin
 *  internet y sin abrir el navegador. La copia canónica del repositorio son
 *  TERMINOS.md y TERMS.md; si cambian, cambia también el catálogo. */
function textoTerminos() {
  return T('terminos.cuerpo');
}

function vistaTerminos(primeraVez) {
  if (primeraVez) {
    return `<div class="card doc fade">
      <div class="doc-head"><h2>${esc(T('terminos.titulo'))}</h2></div>
      <p class="muted mb-5">${esc(T('terminos.bajada'))}</p>
      ${textoTerminos()}
      <div class="row mt-6">
        <button class="btn btn-primary btn-lg" data-accion="aceptar-terminos">${esc(T('terminos.aceptar'))}</button>
      </div>
      <p class="small muted mt-3">${esc(T('terminos.si_no'))}</p>
    </div>`;
  }

  return `<div class="card doc fade">
    <div class="doc-head">
      <h2>${esc(T('terminos.titulo'))}</h2>
      <button class="btn btn-secondary btn-sm a-la-derecha" data-accion="cerrar-vista">${esc(T('comun.volver'))}</button>
    </div>
    ${textoTerminos()}
    <div class="row mt-6">
      <button class="btn btn-secondary" data-accion="cerrar-vista">${esc(T('comun.volver'))}</button>
    </div>
  </div>`;
}

/* ------------------------------------------------------------ clave de YouTube */

function vistaClave() {
  const puedeVolver = !!(S.config && S.config.tiene_clave);

  return `
  <div class="card card-hero fade">
    <div class="card-head">
      <h1>${esc(T(puedeVolver ? 'clave.titulo_propia' : 'clave.titulo'))}</h1>
      <p>${esc(T(puedeVolver ? 'clave.bajada_propia' : 'clave.bajada'))}</p>
    </div>

    ${alerta('', 'llave', `
      <strong>${esc(T('clave.como_titulo'))}</strong>
      <ol>
        <li>${T('clave.paso1')}</li>
        <li>${T('clave.paso2')}</li>
        <li>${T('clave.paso3')}</li>
      </ol>
      <p class="small mt-2">${esc(T('clave.gratis'))}</p>`)}

    <div class="field mt-5 field-clave">
      <label for="clave">${esc(T('clave.rotulo'))}</label>
      <!-- A la vista y no como contraseña: es una clave de API que se pega, no
           se tipea, y lo que traba a quien la carga por primera vez es no poder
           ver si pegó la clave entera o un pedazo. -->
      <input class="input mono" id="clave" type="text" placeholder="AIza…"
             autocomplete="off" autocapitalize="off" spellcheck="false" />
      <span class="hint">${esc(T('clave.ayuda'))}</span>
    </div>

    <div id="setup-error"></div>

    <div class="row mt-5">
      <button class="btn btn-primary" data-accion="guardar-clave">${esc(T('clave.guardar'))}</button>
      ${puedeVolver ? `<button class="btn btn-secondary" data-accion="cerrar-vista">${esc(T('comun.cancelar'))}</button>` : ''}
    </div>
  </div>`;
}

/* ------------------------------------------------------------ paso 1 */

/** El error del relevamiento, con la salida concreta cuando la sabemos.
 *
 *  Un cartel que dice "se agotó el cupo" y nada más es un callejón sin salida,
 *  justo en el caso más probable cuando muchos usan la misma copia. La solución
 *  existe, es gratis y son tres pasos, así que el botón va acá y no en la
 *  documentación. */
function bloqueError(titulo) {
  if (!S.error) return '';
  const puedeCargarClave = S.errorCodigo === 'cuota' || S.errorCodigo === 'clave';
  return alerta('danger', 'error', `
    <strong>${esc(titulo)}</strong><br>${esc(S.error)}
    ${puedeCargarClave ? `
      <div class="row mt-3">
        <button class="btn btn-secondary btn-sm" data-accion="ver-clave">${esc(T('paso1.cargar_clave'))}</button>
      </div>` : ''}`);
}

function avisoClaveIncluida() {
  if (!S.config || !S.config.clave_incluida) return '';
  // Con el error de cupo a la vista ya hay un boton para cargar la clave propia.
  if (S.error && (S.errorCodigo === 'cuota' || S.errorCodigo === 'clave')) return '';
  // Una linea y un link: quien no tiene problema no necesita un bloque entero.
  return `<p class="small muted mt-5">${esc(T('paso1.clave_incluida'))}
    <button type="button" class="link-inline" data-accion="ver-clave">${esc(T('paso1.prefiero_mia'))}</button></p>`;
}

function vistaPaso1() {
  const corriendo = S.ocupado;
  return `
  <div class="card card-hero fade">
    <div class="card-head">
      <h1>${esc(T('paso1.titulo'))}</h1>
      <p>${T('paso1.bajada')}</p>
    </div>

    <div class="field">
      <label for="url">${esc(T('paso1.rotulo_link'))}</label>
      <input class="input input-lg${S.errorCampo ? ' error' : ''}" id="url" type="url" spellcheck="false"
             placeholder="https://www.youtube.com/channel/UC…" value="${esc(S.url)}"
             ${S.errorCampo ? 'aria-invalid="true" aria-describedby="url-error"' : ''}
             ${corriendo ? 'disabled' : ''} />
      ${S.errorCampo
        ? `<span class="hint hint-error" id="url-error">${esc(S.errorCampo)}</span>`
        : `<span class="hint">${T('paso1.ayuda_link')}</span>`}
    </div>

    ${S.catalogo && !corriendo ? alerta('', 'info', `
      ${T('paso1.ya_relevado', { artista: `<strong>${esc(S.catalogo.artista)}</strong>` })}
      <div class="row mt-3"><button class="btn btn-ghost btn-sm" data-accion="volver-2">${esc(T('paso1.volver_catalogo'))}</button></div>`) : ''}

    ${alerta('', 'info', `
      <strong>${esc(T('paso1.topic_titulo'))}</strong>
      ${esc(T('paso1.topic_cuerpo'))}
      <p class="mt-2">${esc(T('paso1.topic_detalle'))}</p>`)}

    <label class="check mt-5">
      <input type="checkbox" id="con-codigos" aria-labelledby="con-codigos-l" ${S.conCodigos ? 'checked' : ''} ${corriendo ? 'disabled' : ''} />
      <span class="check-texto">
        <strong id="con-codigos-l">${esc(T('paso1.codigos_titulo'))}</strong>
        <span class="sub">${esc(T('paso1.codigos_detalle'))}</span>
      </span>
    </label>

    ${avisoClaveIncluida()}

    ${bloqueError(T('paso1.error_titulo'))}

    ${corriendo ? bloqueProgreso() : `
      <div class="row mt-5">
        <button class="btn btn-primary btn-lg" data-accion="relevar">${esc(T('paso1.relevar'))}</button>
      </div>
      <p class="small muted mt-4">
        ${esc(T('paso1.abrir_ayuda'))}
        <button type="button" class="link-inline" data-accion="elegir-archivo" data-para="abrir" ${S.leyendo ? 'disabled' : ''}>${esc(T(S.leyendo === 'abrir' ? 'herr.leyendo' : 'paso1.abrir'))}</button>
      </p>
      ${S.errorHerramienta ? alerta('danger', 'error', esc(S.errorHerramienta)) : ''}
      ${selectorDeArchivo()}`}
  </div>`;
}

/** El selector de archivos, uno solo y escondido: los botones lo abren. Vive
 *  en la vista y no se crea con `createElement` para que el foco y el lector
 *  de pantalla lo traten como cualquier otro control de la página. */
function selectorDeArchivo() {
  return `<input type="file" id="archivo" class="sr" tabindex="-1" aria-hidden="true" accept=".xlsx,.csv,.txt,.json,.zip" />`;
}

function bloqueProgreso(conCancelar = true) {
  const j = S.job || { progreso: 0, mensaje: T('progreso.preparando'), log: [] };
  // La barra aparece cuando hay algo que medir. Antes de eso el spinner y el
  // log ya dicen que esta trabajando, y una barra que no mide nada es adorno.
  const conBarra = (j.progreso || 0) > 0;
  const log = (j.log || []).slice(-60).join('\n');
  return `
  <div class="mt-5 bloque-progreso" id="bloque-progreso">
    <div class="row mb-3">
      <span class="latido" aria-hidden="true"><i></i><i></i><i></i></span>${ico('ok', 'ico-listo')}
      <strong id="progreso-mensaje" aria-live="polite">${esc(j.mensaje || T('progreso.trabajando'))}</strong>
      <span class="muted small mono" id="progreso-pct">${j.progreso ? Math.round(j.progreso * 100) + '%' : ''}</span>
      ${conCancelar ? `<button class="btn btn-secondary btn-sm a-la-derecha" data-accion="cancelar">${esc(T('comun.cancelar'))}</button>` : ''}
    </div>
    ${conBarra ? `
      <div class="barra" role="progressbar" aria-label="${esc(T('progreso.aria_barra'))}" aria-valuemin="0" aria-valuemax="100"
           aria-valuenow="${Math.round(j.progreso * 100)}">
        <div class="barra-fill" style="transform:scaleX(${j.progreso.toFixed(3)})"></div>
      </div>` : ''}
    ${log ? `<div class="log" id="log">${(j.log || []).slice(-60).map((l) => `<div>${esc(l)}</div>`).join('')}</div>` : ''}
  </div>`;
}

/* ------------------------------------------------------------ paso 2 */

/** Lo que Deezer tiene de este artista y no apareció en YouTube.
 *
 *  El buscador de YouTube, que hoy es la única forma de listar un canal Topic,
 *  no garantiza traer todo y no avisa cuando no lo trae. Esto es lo único que
 *  lo deja ver. La lista va plegada: el titular alcanza para decidir si hay
 *  que mirarla. */
function avisoFaltantes(comp) {
  if (!comp || !comp.revisada || !comp.temas) return '';
  const estado = (f) => {
    if (!f.sumado) return T('paso2.faltan_sin_sumar');
    return T(f.relevado ? 'paso2.faltan_sumado_disco' : 'paso2.faltan_sumado_aparte');
  };
  const fila = (f) => `
    <li><strong>${esc(f.titulo)}</strong>
      <span class="muted">${esc([f.tipo, (f.fecha || '').slice(0, 4), f.upc ? 'UPC ' + f.upc : '', estado(f)].filter(Boolean).join(', '))}</span>
      <span class="sub">${esc(T(f.temas.length === 1 ? 'paso2.faltan_de_uno' : 'paso2.faltan_de', { n: f.temas.length, total: f.total }))}
        ${esc(f.temas.map((t) => t.titulo).join(' · '))}</span></li>`;
  const grupo = (titulo, items) => (items.length
    ? `<p class="small mt-3"><strong>${esc(titulo)}</strong></p><ul class="lista-faltan">${items.map(fila).join('')}</ul>`
    : '');
  const lista = S.verFaltantes ? `
      <p class="small mt-3">${esc(T('paso2.faltan_detalle'))}</p>
      ${grupo(T('paso2.faltan_relevados'), comp.faltan.filter((f) => f.relevado))}
      ${grupo(T('paso2.faltan_no_relevados'), comp.faltan.filter((f) => !f.relevado))}` : '';
  return alerta('warn', 'alerta', `
    <strong>${esc(T(comp.temas === 1 ? 'paso2.faltan_titulo_uno' : 'paso2.faltan_titulo', { n: num(comp.temas), artista: comp.artista_deezer }))}</strong>
    ${esc(T('paso2.faltan_cuerpo'))}
    ${comp.sin_respuesta || comp.recortada ? esc(T('paso2.faltan_parcial')) : ''}
    <button type="button" class="link-inline" data-accion="ver-faltantes" aria-expanded="${!!S.verFaltantes}">${esc(T(S.verFaltantes ? 'paso2.faltan_ocultar' : 'paso2.faltan_ver'))}</button>
    ${lista}`);
}

/** Lo que el paso 2 tiene para decir sobre cómo se relevó el catálogo.
 *
 *  Antes cada cosa era un aviso de ancho completo, uno abajo del otro: cinco
 *  cajas, a veces nueve, y la tabla quedaba fuera de la ventana. Ahora se
 *  separa lo que pide que alguien haga algo (la cuota cortó el listado, Deezer
 *  tiene grabaciones que no aparecieron, Deezer no contestó, no se encontró al
 *  artista), que sigue a la vista y primero, de lo que sólo informa (se usó el
 *  Topic, se listó por el buscador, se dejaron videos afuera, de qué perfil
 *  salieron los códigos), que va junto en una sola franja plegada. */
function avisoCanal() {
  const d = (S.catalogo && S.catalogo.diagnostico) || {};
  const comp = d.completitud || {};
  // El catálogo salió de un archivo guardado: no se relevó nada ahora, y los
  // avisos del relevamiento (la cuota, Deezer, el canal) no corresponden.
  if (d.abierto) {
    return alerta('', 'info', `
      <strong>${esc(T('paso2.abierto_titulo', { fecha: d.abierto.fecha || '' }))}</strong>
      ${esc(T('paso2.abierto_cuerpo'))}`);
  }
  const partes = [];
  const datos = []; // { corto, largo }: la franja plegada «Cómo se relevó»

  // La cuota se acabó a mitad del listado. Va primero: todo lo demás se lee
  // sobre un catálogo que está incompleto.
  if (d.cortado_por_cuota) {
    partes.push(alerta('warn', 'alerta', `
      <strong>${esc(T('paso2.cortado_titulo'))}</strong>
      ${esc(T('paso2.cortado_cuerpo', { n: num(d.temas || 0) }))}
      <div class="row mt-3">
        <button class="btn btn-secondary btn-sm" data-accion="ver-clave">${esc(T('paso1.cargar_clave'))}</button>
      </div>`));
  }

  // Caso habitual y bueno: pegaron un canal común y la app encontró el Topic sola.
  if (d.via_topic && d.canal) {
    datos.push({
      corto: esc(T('paso2.rel_topic', { topic: d.canal })),
      largo: `${T('paso2.via_topic', {
        pedido: `<strong>${esc(d.canal_pedido || T('paso2.canal_comun'))}</strong>`,
        topic: `<strong>${esc(d.canal)}</strong>`,
      })} ${esc(T('paso2.que_es_topic'))}`,
    });
  }

  // Cómo se listó. Desde fines de 2026 un canal Topic sólo se puede listar por
  // el buscador, que cuesta cien veces más cuota y no garantiza traer todo: las
  // dos cosas se dicen, con el número.
  // El listado es el de un relevamiento anterior de esta sesión. Se dice, con
  // la forma de pedirlo de nuevo: quien sabe que el canal cambió no tiene por
  // qué cerrar la app para verlo.
  if (d.reusado) {
    datos.push({
      corto: esc(T('paso2.rel_reusado')),
      largo: `${esc(T('paso2.reusado'))}
        <button type="button" class="link-inline" data-accion="relistar">${esc(T('paso2.relistar'))}</button>`,
    });
  }

  if (d.via === 'busqueda') {
    const frases = [d.reusado
      ? T('paso2.por_buscador_reusado', { n: `<strong>${num(d.temas || 0)}</strong>` })
      : T('paso2.por_buscador', {
        n: `<strong>${num(d.temas || 0)}</strong>`,
        unidades: `<strong>${num(d.unidades || 0)}</strong>`,
      })];
    if (comp.revisada && !comp.temas) {
      frases.push(esc(T('paso2.buscador_completo', { artista: comp.artista_deezer, n: num(comp.releases) })));
    } else if (!comp.revisada) {
      frases.push(esc(T('paso2.buscador_sin_comparar')));
    }
    const cortos = [T('paso2.rel_buscador', { n: `<strong>${num(d.temas || 0)}</strong>` })];
    if (!d.reusado) cortos.push(T('paso2.rel_unidades', { n: `<strong>${num(d.unidades || 0)}</strong>` }));
    if (!comp.revisada) cortos.push(esc(T('paso2.rel_sin_comparar')));
    datos.push({ corto: cortos.join(', '), largo: frases.join(' ') });
  }

  partes.push(avisoFaltantes(comp));

  // Los códigos. Sin esto, «ISRC 0 de 27» parecía una falla de la app cuando
  // podía ser que no se pidieron o que el artista no está en Deezer.
  const cod = d.codigos;

  // De qué perfil de Deezer salieron los códigos, con la forma de cambiarlo:
  // dos artistas pueden llamarse igual, y la app puede haber elegido al otro.
  const perfil = d.completitud;
  if (cod && cod.pedidos && cod.encontrados && perfil && perfil.revisada) {
    datos.push({
      corto: esc(T('paso2.rel_perfil', { artista: perfil.artista_deezer })),
      largo: `${esc(T('paso2.deezer_perfil_usado', { artista: perfil.artista_deezer }))}
        ${S.pideDeezer ? formDeezer(perfil) : `<button type="button" class="link-inline" data-accion="otro-deezer">${esc(T('paso2.deezer_otro_perfil'))}</button>`}`,
    });
  }

  if (d.sin_distribuidora) {
    const n = num(d.sin_distribuidora);
    datos.push(d.sin_distribuidora === 1
      ? { corto: esc(T('paso2.rel_sin_distrib_uno')), largo: esc(T('paso2.sin_distribuidora_uno', { n })) }
      : { corto: esc(T('paso2.rel_sin_distrib', { n })), largo: esc(T('paso2.sin_distribuidora', { n })) });
  }

  if (d.descartados) {
    const n = `<strong>${num(d.descartados)}</strong>`;
    datos.push(d.descartados === 1
      ? { corto: T('paso2.rel_descartados_uno', { n }), largo: T('paso2.descartados_uno', { n }) }
      : { corto: T('paso2.rel_descartados', { n }), largo: T('paso2.descartados', { n }) });
  }

  if (cod && !cod.pedidos) {
    datos.push({ corto: esc(T('paso2.rel_sin_codigos')), largo: esc(T('paso2.codigos_no_pedidos')) });
  } else if (cod && cod.fallas) {
    const motivo = cod.motivo ? ' ' + T('paso2.deezer_motivo', { motivo: cod.motivo }) : '';
    partes.push(alerta('warn', 'alerta', esc(T(cod.fallas === 1 ? 'paso2.deezer_no_respondio_uno' : 'paso2.deezer_no_respondio', { n: num(cod.fallas) }) + motivo)));
  } else if (cod && !cod.encontrados && S.catalogo.productos.length) {
    partes.push(alerta('warn', 'alerta', `
      <strong>${esc(T('paso2.no_esta_en_deezer_titulo', { artista: S.catalogo.artista }))}</strong>
      ${esc(T('paso2.no_esta_en_deezer_cuerpo'))}
      ${formDeezer(d.completitud)}`));
  }

  return partes.join('') + franjaRelevamiento(datos);
}

/** «Cómo se relevó»: lo que sólo informa, en una línea que se despliega. Plegada
 *  dice lo esencial con los números; desplegada, cada cosa con su explicación y
 *  sus botones. Es un <details> de verdad, así el lector de pantalla y el
 *  teclado lo abren como cualquier otro, y el estado sobrevive al redibujo. */
function franjaRelevamiento(datos) {
  if (!datos.length) return '';
  return `
    <details class="relevamiento" ${S.verRelevamiento ? 'open' : ''}>
      <summary>
        <span class="relevamiento-rotulo">${esc(T('paso2.relevamiento'))}</span>
        <span class="relevamiento-datos">${datos.map((x) => `<span>${x.corto}</span>`).join('')}</span>
        ${ico('flecha', 'ico-sm')}
      </summary>
      <ul class="relevamiento-detalle">${datos.map((x) => `<li>${x.largo}</li>`).join('')}</ul>
    </details>`;
}

/** El campo para pegar el link del artista en Deezer. Es la salida para cuando
 *  la app no encuentra el perfil sola, o usa el de un homónimo. */
function formDeezer(comp) {
  const vacio = S.deezerLink && S.deezerUsado === S.deezerLink && comp && !comp.revisada;
  const error = S.deezerError || (vacio ? T('paso2.deezer_perfil_vacio') : '');
  return `
    <div class="form-deezer">
      <label for="deezer-link">${esc(T('paso2.deezer_link_label'))}</label>
      <div class="form-deezer-linea">
        <input class="input${error ? ' error' : ''}" id="deezer-link" type="url" spellcheck="false"
               placeholder="https://www.deezer.com/es/artist/…" value="${esc(S.deezerLink)}"
               ${error ? 'aria-invalid="true" aria-describedby="deezer-error"' : ''}>
        <button type="button" class="btn btn-secondary" data-accion="usar-deezer">${esc(T('paso2.deezer_usar'))}</button>
      </div>
      ${error ? `<span class="hint hint-error" id="deezer-error">${esc(error)}</span>` : ''}
    </div>`;
}

/** «Elegidos: 3 de 12 productos, 27 tracks», para la barra del paso 2. El total
 *  es el del catálogo y no el de lo que se ve, porque lo elegido es del catálogo:
 *  va al paquete aunque el filtro lo esconda. */
function resumenElegidos(sel) {
  const total = S.catalogo ? S.catalogo.productos.length : sel.length;
  const tracks = sel.reduce((a, p) => a + p.tracks, 0);
  const texto = T('paso2.elegidos', {
    n: `<strong>${num(sel.length)}</strong>`,
    total: cuenta('comun.n_productos', total, `<strong>${num(total)}</strong>`),
    tracks: cuenta('comun.n_tracks', tracks),
  });
  const deshacer = S.deshacer
    ? `<button type="button" class="link-inline deshacer" data-accion="deshacer-seleccion">${esc(T('paso2.deshacer'))}</button>`
    : '';
  const ocultos = elegidosOcultos();
  if (!ocultos) return texto + deshacer;
  return `${texto}${deshacer}<span class="ocultos">${esc(T(ocultos === 1 ? 'paso2.ocultos_uno' : 'paso2.ocultos', { n: num(ocultos) }))}
    <button type="button" class="link-inline" data-accion="limpiar-filtro">${esc(T('paso2.ver_todos'))}</button></span>`;
}

function vistaPaso2() {
  const c = S.catalogo;
  const ps = productosFiltrados();
  const sel = seleccionados();
  const r = c.resumen;

  return `
  <div class="fade">
    <div class="card">
      <div class="card-head row row-wrap">
        <div class="grow">
          <h1>${esc(c.artista)}</h1>
          <p>${esc(T('paso2.bajada'))}</p>
          <p class="lectura">
            ${T('paso2.resumen', {
              productos: cuenta('comun.n_productos', r.products, `<span class="n">${num(r.products)}</span>`),
              tracks: cuenta('comun.n_tracks', r.tracks, `<span class="n">${num(r.tracks)}</span>`),
              views: `<span class="n">${num(r.views)}</span>`,
              upc: cuenta('comun.n_productos', r.products, `<span class="n${r.with_upc < r.products ? ' atencion' : ''}">${num(r.with_upc)} / ${num(r.products)}</span>`),
              isrc: cuenta('comun.n_tracks', r.tracks, `<span class="n${r.with_isrc < r.tracks ? ' atencion' : ''}">${num(r.with_isrc)} / ${num(r.tracks)}</span>`),
            })}
          </p>
          ${lecturaEvidencia()}
        </div>
        <button class="btn btn-ghost" data-accion="volver-1">${esc(T('paso2.otro_artista'))}</button>
      </div>
    </div>

    ${avisoCanal()}

    ${herramientas()}

    <div class="seccion">
      <div class="seccion-etiqueta">
        <h2>${esc(T('paso2.productos'))}</h2>
        <span class="der">${esc(T('paso2.mostrando', { n: ps.length, total: c.productos.length }))}</span>
      </div>

      <div class="row row-wrap mb-4">
        <div class="segmented" role="group" aria-label="${esc(T('paso2.aria_filtro'))}">
          <button class="${S.filtro.modo === 'manual' ? 'activo' : ''}" aria-pressed="${S.filtro.modo === 'manual'}" data-modo="manual">${esc(T('paso2.filtro_todos'))}</button>
          <button class="${S.filtro.modo === 'fechas' ? 'activo' : ''}" aria-pressed="${S.filtro.modo === 'fechas'}" data-modo="fechas">${esc(T('paso2.filtro_anio'))}</button>
          <button class="${S.filtro.modo === 'distribuidora' ? 'activo' : ''}" aria-pressed="${S.filtro.modo === 'distribuidora'}" data-modo="distribuidora">${esc(T('paso2.filtro_distrib'))}</button>
        </div>
        <div class="grow buscador">
          <input class="input" id="buscar" type="search" placeholder="${esc(T('paso2.buscar_placeholder'))}"
                 aria-label="${esc(T('paso2.aria_buscar'))}" value="${esc(S.filtro.texto)}" />
        </div>
        <label class="check check-faltantes">
          <input type="checkbox" id="solo-faltantes" ${S.filtro.faltantes ? 'checked' : ''} />
          <span class="check-texto">${esc(T('paso2.solo_faltantes'))}</span>
        </label>
      </div>

      ${panelFiltro()}

      ${ps.length === 0 ? `
        <div class="vacio">
          <h4>${esc(motivoVacio().titulo)}</h4>
          <p>${esc(motivoVacio().detalle)}</p>
          <button class="btn btn-primary" data-accion="limpiar-filtro">${esc(T('paso2.limpiar_filtro'))}</button>
        </div>` : tablaProductos(ps) + `
        <p class="leyenda">${esc(T('paso2.leyenda'))}</p>`}
    </div>

    <div class="barra-accion">
      <div class="resumen">
        ${resumenElegidos(sel)}
      </div>
      <div class="acciones">
        ${botonesDeMarcar(ps)}
        <button class="btn btn-primary" data-accion="ir-3" ${sel.length ? '' : 'disabled'}>${esc(T('comun.continuar'))}</button>
      </div>
    </div>
  </div>`;
}

/** Marcar y desmarcar actúan sobre lo que se ve. Con un filtro puesto, se dice
 *  en el botón: «Desmarcar todos» con tres filas a la vista desmarcaba tres, y
 *  los elegidos que el filtro escondía seguían yendo al paquete. Se ofrece sólo
 *  el que tiene sentido: marcar si falta alguno, desmarcar si hay alguno. */
function botonesDeMarcar(ps) {
  const elegidos = ps.filter((p) => S.seleccion.has(p.id)).length;
  const filtro = hayFiltro();
  return `
        <button class="btn btn-secondary" data-accion="sel-todo" ${elegidos < ps.length ? '' : 'hidden'}>${esc(filtro ? T('paso2.marcar_visibles') : T('paso2.marcar_todos'))}</button>
        <button class="btn btn-secondary" data-accion="sel-nada" ${elegidos ? '' : 'hidden'}>${esc(filtro ? T('paso2.desmarcar_visibles') : T('paso2.desmarcar_todos'))}</button>`;
}

/** Por qué la tabla quedó vacía, para decir eso y no siempre lo de los años.
 *  Cada `T()` va con su clave entera, así el test de i18n la encuentra. */
function motivoVacio() {
  const f = S.filtro;
  if (f.modo === 'distribuidora' && !f.distribs.size) {
    return { motivo: 'sin_distrib', titulo: T('paso2.vacio_sin_distrib_titulo'), detalle: T('paso2.vacio_sin_distrib_detalle') };
  }
  // Sólo el filtro de faltantes y nada más: es una buena noticia, no un filtro
  // mal puesto.
  if (f.faltantes && !f.texto.trim() && f.modo === 'manual') {
    return { motivo: 'nada_falta', titulo: T('paso2.vacio_nada_falta_titulo'), detalle: T('paso2.vacio_nada_falta_detalle') };
  }
  return { motivo: 'filtro', titulo: T('paso2.vacio_titulo'), detalle: T('paso2.vacio_detalle') };
}

function panelFiltro() {
  const f = S.filtro;
  const c = S.catalogo;

  if (f.modo === 'fechas') {
    const lo = c.filtros.anio_min, hi = c.filtros.anio_max;
    if (lo === null) {
      return alerta('warn', 'alerta', esc(T('paso2.sin_anios')));
    }
    return `
    <div class="panel mb-4">
      <div class="row row-wrap">
        <div class="field field-corto">
          <label for="anio-desde">${esc(T('paso2.desde_anio'))}</label>
          <input class="input mono" id="anio-desde" type="number" min="${lo}" max="${hi}" value="${f.anioDesde ?? lo}" />
        </div>
        <div class="field field-corto">
          <label for="anio-hasta">${esc(T('paso2.hasta_anio'))}</label>
          <input class="input mono" id="anio-hasta" type="number" min="${lo}" max="${hi}" value="${f.anioHasta ?? hi}" />
        </div>
        <p class="small muted nota-al-pie">
          ${esc(T('paso2.rango_anios', { desde: lo, hasta: hi }))}
        </p>
      </div>
    </div>`;
  }

  if (f.modo === 'distribuidora') {
    const items = c.filtros.distribuidoras.map((d) => `
      <label class="check check-suelto">
        <input type="checkbox" data-distrib="${esc(d.name)}" ${f.distribs.has(d.name) ? 'checked' : ''} />
        <span class="check-texto"><strong>${esc(d.name || T('paso2.sin_distribuidora_opcion'))}</strong><span class="sub">${esc(T(d.count === 1 ? 'comun.n_productos_uno' : 'comun.n_productos', { n: d.count }))}</span></span>
      </label>`).join('');
    return `
    <div class="panel mb-4">
      <div class="row row-wrap">${items}</div>
    </div>`;
  }
  return '';
}

function tablaProductos(ps) {
  const todos = ps.length > 0 && ps.every((p) => S.seleccion.has(p.id));
  const algunos = ps.some((p) => S.seleccion.has(p.id));

  const filas = ps.map((p) => {
    const elegido = S.seleccion.has(p.id);
    const abierto = S.expandidos.has(p.id);
    const avisos = [];
    // Un codigo que falta es un aviso: la distribuidora asigna uno nuevo y no
    // rechaza. El rojo queda para lo que la validacion marca como error.
    // Dos niveles. En ámbar, lo que falta para entregar: un código, el orden,
    // temas del disco. En neutro, de dónde salió algo: no falta nada, pero hay
    // que mirarlo. Antes todo era ámbar y «1 tema de Deezer» pesaba lo mismo
    // que «sin UPC».
    if (!p.upc) avisos.push(`<span class="badge badge-warn">${esc(T('tabla.sin_upc'))}</span>`);
    if (p.con_isrc < p.tracks) avisos.push(`<span class="badge badge-warn">${esc(T('tabla.isrc_de', { n: p.con_isrc, total: p.tracks }))}</span>`);
    if (p.orden_estimado) avisos.push(`<span class="badge badge-warn">${esc(T('tabla.orden_estimado'))}</span>`);
    const ajeno = p.origen === 'deezer' && p.artista && S.catalogo && p.artista !== S.catalogo.artista;
    const faltan = p.faltan || [];
    if (faltan.length) avisos.push(`<span class="badge badge-warn">${esc(T(faltan.length === 1 ? 'tabla.faltan_temas_uno' : 'tabla.faltan_temas', { n: faltan.length }))}</span>`);
    if (p.origen === 'deezer') {
      avisos.push(`<span class="badge badge-accent">${esc(T('tabla.solo_deezer'))}</span>`);
    } else if (p.de_deezer) {
      avisos.push(`<span class="badge badge-accent">${esc(T(p.de_deezer === 1 ? 'tabla.de_deezer_uno' : 'tabla.de_deezer', { n: p.de_deezer }))}</span>`);
    }
    // En neutro también: el código está, pero salió de una sola fuente.
    const aConfirmar = porConfirmar(p);
    if (aConfirmar) avisos.push(`<span class="badge badge-accent">${esc(T(aConfirmar === 1 ? 'tabla.por_confirmar_uno' : 'tabla.por_confirmar', { n: aConfirmar }))}</span>`);

    const detalle = abierto ? `
      <tr class="fila-detalle"><td colspan="8"><div class="detalle-inner">
        <table class="sub sub-codigos">
          <thead><tr><th scope="col">${esc(T('tabla.col_n'))}</th><th scope="col">${esc(T('tabla.col_track'))}</th><th scope="col">ISRC</th><th scope="col">${esc(T('tabla.col_evidencia'))}</th><th scope="col">${esc(T('tabla.col_duracion'))}</th><th scope="col" class="td-num">${esc(T('tabla.col_reproducciones'))}</th></tr></thead>
          <tbody>${p.detalle.map((t, i) => `
            <tr>
              <td class="mono">${esc(t.n)}</td>
              <td>${esc(t.titulo)}${t.origen === 'deezer' && p.origen !== 'deezer' ? ` <span class="muted">${esc(T('tabla.tema_de_deezer'))}</span>` : ''}</td>
              <td class="mono celda-codigo">${celdaIsrc(p, t, i)}</td>
              <td>${etiquetaNivel(t.nivel)}</td>
              <td class="mono">${esc(t.duracion)}</td>
              <td class="td-num">${num(t.views)}</td>
            </tr>`).join('')}
          </tbody>
        </table>
        <p class="small fila-upc"><span class="rotulo">${esc(T('tabla.upc_del_producto'))}</span> <span class="mono celda-codigo">${celdaUpc(p)}</span> ${etiquetaNivel(p.upc_nivel)}</p>
        ${faltan.length ? `<p class="small nota-faltan"><strong>${esc(T('tabla.faltan_detalle'))}</strong> ${esc(faltan.join(' · '))}</p>` : ''}
      </div></td></tr>` : '';

    return `
    <tr class="${elegido ? 'elegida' : ''}" data-fila="${esc(p.id)}">
      <td class="td-check">
        <label class="check"><input type="checkbox" data-prod="${esc(p.id)}" ${elegido ? 'checked' : ''} />
        <span class="sr">${esc(T('tabla.aria_elegir', { titulo: p.titulo }))}</span></label>
      </td>
      <td class="td-exp">
        <button class="btn-expandir" data-expandir="${esc(p.id)}" aria-expanded="${abierto}">
          ${ico('flecha', 'ico-sm')}<span class="sr">${esc(T('tabla.aria_ver_tracks', { titulo: p.titulo }))}</span>
        </button>
      </td>
      <td>
        <div class="celda-titulo">${esc(p.titulo)}</div>
        <div class="celda-sub">${esc(T(p.tracks === 1 ? 'comun.n_tracks_uno' : 'comun.n_tracks', { n: p.tracks }))}${p.sello ? ', ' + esc(p.sello) : ''}${ajeno ? ', ' + esc(T('tabla.a_nombre_de', { artista: p.artista })) : ''}</div>
      </td>
      <td class="celda-distrib" ${p.distribuidora ? `title="${esc(p.distribuidora)}"` : ''}>${p.distribuidora ? esc(p.distribuidora) : `<span class="apagado">${esc(T('tabla.sin_distribuidora'))}</span>`}</td>
      <td><span class="tipo">${esc(p.tipo)}</span></td>
      <td class="nowrap mono">${esc(p.anio) || `<span class="muted">${esc(T('tabla.sin_fecha'))}</span>`}</td>
      <td class="mono">${p.upc ? esc(p.upc) : `<span class="muted">${esc(T('tabla.sin_upc'))}</span>`}</td>
      <td><span class="badges">${avisos.join('') || `<span class="badge badge-ok">${esc(T('tabla.completo'))}</span>`}</span></td>
    </tr>${detalle}`;
  }).join('');

  // Anchos fijos: con el ancho automático cada filtro cambiaba qué filas había,
  // y con ellas el ancho de cada columna. La tabla saltaba de lugar.
  return `
  <div class="tabla-wrap" id="tabla-wrap">
    <table class="tabla">
      <colgroup><col class="c-check"><col class="c-exp"><col><col class="c-distrib"><col class="c-tipo"><col class="c-anio"><col class="c-upc"><col class="c-estado"></colgroup>
      <thead><tr>
        <th scope="col" class="td-check"><label class="check"><input type="checkbox" id="check-todos"
          ${todos ? 'checked' : ''} ${!todos && algunos ? 'data-indeterminado="1"' : ''} />
          <span class="sr">${esc(T('tabla.aria_marcar_todos'))}</span></label></th>
        <th scope="col" class="td-exp"></th>
        ${cabeceraOrdenable('titulo', T('tabla.col_producto'))}${cabeceraOrdenable('distribuidora', T('tabla.col_distribuidora'))}${cabeceraOrdenable('tipo', T('tabla.col_tipo'))}${cabeceraOrdenable('anio', T('tabla.col_anio'))}<th scope="col">UPC</th>${cabeceraOrdenable('estado', T('tabla.col_estado'))}
      </tr></thead>
      <tbody>${filas}</tbody>
    </table>
  </div>`;
}

/** Una cabecera que ordena al tocarla: primero ascendente, después
 *  descendente, y la tercera vez vuelve al orden del relevamiento. `aria-sort`
 *  es lo que le dice al lector de pantalla cómo está ordenada la tabla. */
function siguienteOrden(col) {
  const actual = S.orden && S.orden.col === col ? S.orden.dir : '';
  if (actual === '') return { col, dir: 'asc' };
  return actual === 'asc' ? { col, dir: 'desc' } : null;
}

function cabeceraOrdenable(col, texto) {
  const dir = S.orden && S.orden.col === col ? S.orden.dir : '';
  const aria = dir === 'asc' ? 'ascending' : (dir === 'desc' ? 'descending' : 'none');
  return `<th scope="col" aria-sort="${aria}"><button type="button" class="orden${dir ? ' orden-' + dir : ''}" data-orden="${col}">
    <span>${esc(texto)}</span>${ico('flecha', 'ico-sm')}</button></th>`;
}

/* ------------------------------------------------------------ evidencia y edición */

/** Qué tan comprobado está un código, en una palabra. «Confirmado» va apagado:
 *  es lo normal y no tiene que competir con lo que sí hay que mirar. */
const NIVELES = {
  confirmado: { texto: () => T('nivel.confirmado'), ayuda: () => T('nivel.confirmado_ayuda'), clase: 'nivel-ok' },
  inferido: { texto: () => T('nivel.inferido'), ayuda: () => T('nivel.inferido_ayuda'), clase: 'nivel-neutro' },
  dudoso: { texto: () => T('nivel.dudoso'), ayuda: () => T('nivel.dudoso_ayuda'), clase: 'nivel-warn' },
  manual: { texto: () => T('nivel.manual'), ayuda: () => T('nivel.manual_ayuda'), clase: 'nivel-propio' },
  importado: { texto: () => T('nivel.importado'), ayuda: () => T('nivel.importado_ayuda'), clase: 'nivel-propio' },
};

function nombreNivel(nivel) {
  return NIVELES[nivel] ? NIVELES[nivel].texto() : '';
}

function etiquetaNivel(nivel) {
  const n = NIVELES[nivel];
  if (!n) return '';
  return `<span class="nivel ${n.clase}" title="${esc(n.ayuda())}">${esc(n.texto())}</span>`;
}

/** La oración de arriba de la tabla: cuántos ISRC están confirmados y cuántos
 *  no. Sólo si hay alguno sin confirmar; con todo confirmado no agrega nada. */
function lecturaEvidencia() {
  const e = (S.catalogo && S.catalogo.evidencia) || {};
  const isrc = e.isrc || {};
  const upc = e.upc || {};
  const flojos = (isrc.inferido || 0) + (isrc.dudoso || 0);
  const upcFlojos = upc.inferido || 0;
  if (!flojos && !upcFlojos) return '';
  const partes = [];
  if (flojos) {
    partes.push(T(flojos === 1 ? 'paso2.evidencia_isrc_uno' : 'paso2.evidencia_isrc', {
      n: `<span class="n">${num(flojos)}</span>`,
      confirmados: `<span class="n">${num((isrc.confirmado || 0) + (isrc.manual || 0) + (isrc.importado || 0))}</span>`,
    }));
  }
  if (upcFlojos) {
    partes.push(T(upcFlojos === 1 ? 'paso2.evidencia_upc_uno' : 'paso2.evidencia_upc', { n: `<span class="n">${num(upcFlojos)}</span>` }));
  }
  return `<p class="lectura lectura-evidencia">${partes.join(' ')} ${esc(T('paso2.evidencia_que_hacer'))}</p>`;
}

function esEditando(tipo, producto, indice) {
  const e = S.editando;
  return !!e && e.tipo === tipo && e.producto === producto && (tipo === 'upc' || e.indice === indice);
}

/** El formulario de un código, en el lugar. Un solo campo, Enter guarda y
 *  Escape cancela: es una corrección puntual, no una pantalla. */
function editorCodigo(tipo) {
  const e = S.editando;
  const rotulo = T(tipo === 'isrc' ? 'edicion.aria_isrc' : 'edicion.aria_upc');
  return `<span class="editor-codigo">
    <input class="input input-codigo mono${e.error ? ' error' : ''}" id="codigo-edit" type="text" spellcheck="false" autocomplete="off"
      maxlength="20" value="${esc(e.valor)}" aria-label="${esc(rotulo)}" ${e.error ? 'aria-invalid="true" aria-describedby="codigo-error"' : ''} />
    <button type="button" class="btn btn-secondary btn-sm" data-accion="guardar-codigo">${esc(T('edicion.guardar'))}</button>
    <button type="button" class="link-inline" data-accion="cancelar-codigo">${esc(T('edicion.cancelar'))}</button>
    ${e.error ? `<span class="hint hint-error" id="codigo-error" role="alert">${esc(e.error)}</span>` : ''}
  </span>`;
}

function celdaIsrc(p, t, i) {
  if (esEditando('isrc', p.id, i)) return editorCodigo('isrc');
  const marca = `data-producto="${esc(p.id)}" data-indice="${i}"`;
  const editar = `<button type="button" class="link-inline accion-codigo" data-accion="editar-isrc" ${marca}>${esc(T(t.isrc ? 'edicion.cambiar' : 'edicion.cargar'))}<span class="sr"> ${esc(T('edicion.de', { titulo: t.titulo }))}</span></button>`;
  const deshacer = t.editado
    ? `<button type="button" class="link-inline accion-codigo" data-accion="restaurar-isrc" ${marca}>${esc(T('edicion.deshacer'))}</button>` : '';
  if (t.isrc) return `${esc(t.isrc)} ${editar}${deshacer}`;
  // Sin código pero con candidatos: el relevamiento encontró más de una
  // grabación posible y no eligió. Se ofrecen acá, que es donde se decide.
  const candidatos = (t.candidatos || []).map((c) =>
    `<button type="button" class="btn btn-secondary btn-sm candidato" data-accion="usar-candidato" ${marca} data-isrc="${esc(c.isrc)}">${esc(c.isrc)} <span class="muted">${esc(c.duracion)}</span></button>`).join('');
  if (candidatos) {
    return `<span class="candidatos"><span class="muted">${esc(T('edicion.elegir_entre'))}</span> ${candidatos} ${editar}</span>`;
  }
  return `<span class="muted">${esc(T('tabla.sin_isrc'))}</span> ${editar}${deshacer}`;
}

function celdaUpc(p) {
  if (esEditando('upc', p.id)) return editorCodigo('upc');
  const marca = `data-producto="${esc(p.id)}"`;
  const editar = `<button type="button" class="link-inline accion-codigo" data-accion="editar-upc" ${marca}>${esc(T(p.upc ? 'edicion.cambiar' : 'edicion.cargar'))}</button>`;
  const deshacer = p.upc_editado
    ? `<button type="button" class="link-inline accion-codigo" data-accion="restaurar-upc" ${marca}>${esc(T('edicion.deshacer'))}</button>` : '';
  return `${p.upc ? esc(p.upc) : `<span class="muted">${esc(T('tabla.sin_upc'))}</span>`} ${editar}${deshacer}`;
}

/* ------------------------------------------------------------ herramientas del paso 2 */

/** Las tres cosas que se pueden hacer con el catálogo además de mirarlo:
 *  traer los códigos de la distribuidora actual, cargar lo que ninguna fuente
 *  trae, y comparar con un relevamiento anterior. */
function herramientas() {
  const ocupado = !!S.leyendo;
  const boton = (para, texto) =>
    `<button type="button" class="btn btn-secondary btn-sm" data-accion="elegir-archivo" data-para="${para}" ${ocupado ? 'disabled' : ''}>${esc(S.leyendo === para ? T('herr.leyendo') : texto)}</button>`;
  return `
  <div class="herramientas">
    <div class="row row-wrap">
      ${boton('importar', T('herr.importar'))}
      <button type="button" class="btn btn-secondary btn-sm" data-accion="abrir-datos" aria-expanded="${S.datosAbierto}">${esc(T('herr.datos'))}</button>
      ${boton('comparar', T('herr.comparar'))}
    </div>
    ${selectorDeArchivo()}
    ${S.errorHerramienta ? alerta('danger', 'error', esc(S.errorHerramienta)) : ''}
    ${S.hecho ? alerta('ok', 'ok', esc(S.hecho), 'status') : ''}
    ${S.importacion ? panelImportacion() : ''}
    ${S.datosAbierto ? panelDatos() : ''}
    ${S.comparacion ? panelComparacion() : ''}
  </div>`;
}

const TIPOS_IMPORTACION = ['conflicto', 'ambiguo', 'completa', 'confirma'];
const TEXTO_IMPORTACION = {
  conflicto: { titulo: () => T('imp.t_conflicto'), detalle: () => T('imp.d_conflicto') },
  ambiguo: { titulo: () => T('imp.t_ambiguo'), detalle: () => T('imp.d_ambiguo') },
  completa: { titulo: () => T('imp.t_completa'), detalle: () => T('imp.d_completa') },
  confirma: { titulo: () => T('imp.t_confirma'), detalle: () => T('imp.d_confirma') },
};
const COLUMNA_IMPORTADA = {
  isrc: () => T('imp.col_isrc'), upc: () => T('imp.col_upc'), track: () => T('imp.col_track'),
  album: () => T('imp.col_album'), duracion: () => T('imp.col_duracion'), numero: () => T('imp.col_numero'),
  version: () => T('imp.col_version'),
};

/** La propuesta de la planilla: qué confirma, qué completa, y lo que no se
 *  aplica solo. Primero lo que pide una decisión; lo seguro va plegado. */
function panelImportacion() {
  const imp = S.importacion;
  const r = imp.resumen;
  const columnas = Object.entries(imp.columnas || {})
    .map(([campo, nombre]) => `${esc(COLUMNA_IMPORTADA[campo] ? COLUMNA_IMPORTADA[campo]() : campo)}: <span class="mono">${esc(nombre)}</span>`).join(' · ');

  const grupo = (tipo) => {
    const items = imp.items.filter((it) => it.tipo === tipo);
    if (!items.length) return '';
    const filas = items.slice(0, 200).map((it) => {
      const elegido = S.importElegidos.has(it.id);
      const donde = it.codigo === 'upc'
        ? `<strong>${esc(it.producto)}</strong> <span class="muted">UPC</span>`
        : `<strong>${esc(it.track)}</strong> <span class="muted">${esc(it.producto)}</span>`;
      let cambio;
      if (tipo === 'ambiguo') {
        cambio = it.candidatos.map((c) => `
          <label class="check check-suelto">
            <input type="radio" name="amb-${esc(it.id)}" data-eleccion="${esc(it.id)}" value="${esc(c.isrc)}" ${S.importElecciones[it.id] === c.isrc ? 'checked' : ''} />
            <span class="check-texto"><span class="mono">${esc(c.isrc)}</span><span class="sub">${esc([c.album, c.duracion_s ? mmss(c.duracion_s) : '', T('imp.fila', { n: c.fila })].filter(Boolean).join(' · '))}</span></span>
          </label>`).join('');
      } else if (tipo === 'conflicto') {
        cambio = `<span class="mono">${esc(it.actual)}</span> <span class="muted">${esc(T('imp.del_catalogo', { nivel: nombreNivel(it.nivel) }))}</span>
          <span class="flecha-cambio">→</span> <span class="mono">${esc(it.nuevo)}</span> <span class="muted">${esc(T('imp.fila', { n: it.fila }))}</span>`;
      } else {
        cambio = `<span class="mono">${esc(it.nuevo)}</span> <span class="muted">${esc(T('imp.fila', { n: it.fila }))}</span>`;
      }
      return `
      <li class="item-importacion">
        <label class="check"><input type="checkbox" data-item="${esc(it.id)}" ${elegido ? 'checked' : ''} />
          <span class="sr">${esc(T('imp.aria_aplicar', { titulo: it.track || it.producto }))}</span></label>
        <div class="item-donde">${donde}</div>
        <div class="item-cambio">${cambio}</div>
      </li>`;
    }).join('');
    const abierto = tipo === 'conflicto' || tipo === 'ambiguo';
    return `
    <details class="grupo-importacion" ${abierto ? 'open' : ''}>
      <summary><strong>${esc(TEXTO_IMPORTACION[tipo].titulo())}</strong> <span class="n">${num(items.length)}</span>
        <span class="muted">${esc(TEXTO_IMPORTACION[tipo].detalle())}</span></summary>
      <ul class="lista-importacion">${filas}</ul>
    </details>`;
  };

  const sobran = imp.sin_correspondencia_total || 0;
  const aplicar = S.importElegidos.size;
  return `
  <div class="panel panel-herramienta" role="region" aria-label="${esc(T('herr.importar'))}">
    <h3>${esc(T('imp.titulo', { archivo: imp.nombre || '' }))}</h3>
    <p class="small muted">${T('imp.leido', { filas: `<span class="n">${num(imp.filas)}</span>` })} ${columnas}</p>
    ${!imp.items.length ? `<p class="mt-3">${esc(T('imp.nada'))}</p>` : TIPOS_IMPORTACION.map(grupo).join('')}
    ${sobran ? `
    <details class="grupo-importacion">
      <summary><strong>${esc(T('imp.t_sobran'))}</strong> <span class="n">${num(sobran)}</span>
        <span class="muted">${esc(T('imp.d_sobran'))}</span></summary>
      <ul class="lista-importacion">${imp.sin_correspondencia.slice(0, 50).map((f) => `
        <li class="item-importacion"><span></span><div class="item-donde"><strong>${esc(f.track || f.album || '')}</strong> <span class="muted">${esc(f.track ? f.album : '')}</span></div>
          <div class="item-cambio"><span class="mono">${esc(f.isrc || f.upc)}</span> <span class="muted">${esc(T('imp.fila', { n: f.fila }))}</span></div></li>`).join('')}
      </ul>
    </details>` : ''}
    <div class="row row-wrap mt-4">
      <button type="button" class="btn btn-primary" data-accion="aplicar-importacion" ${aplicar ? '' : 'disabled'}>${esc(T(aplicar === 1 ? 'imp.aplicar_uno' : 'imp.aplicar', { n: num(aplicar) }))}</button>
      <button type="button" class="btn btn-ghost" data-accion="descartar-importacion">${esc(T('imp.descartar'))}</button>
    </div>
    ${r.conflicto || r.ambiguo ? `<p class="small muted mt-3">${esc(T('imp.nota_decisiones'))}</p>` : ''}
  </div>`;
}

function mmss(segundos) {
  const s = Math.max(0, Math.round(Number(segundos) || 0));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
}

/** Los campos que ninguna fuente pública trae, para cargarlos una vez y no en
 *  trescientas celdas de una planilla. Un campo vacío no cambia nada. */
const CAMPO_A_COMPLETAR = {
  c_line: { rotulo: () => T('datos.c_c_line'), ejemplo: () => T('datos.p_c_line') },
  genre: { rotulo: () => T('datos.c_genre'), ejemplo: () => T('datos.p_genre') },
  language: { rotulo: () => T('datos.c_language'), ejemplo: () => T('datos.p_language') },
  territories: { rotulo: () => T('datos.c_territories'), ejemplo: () => T('datos.p_territories') },
  explicit: { rotulo: () => T('datos.c_explicit'), ejemplo: () => T('datos.p_explicit') },
  lyrics_language: { rotulo: () => T('datos.c_lyrics_language'), ejemplo: () => T('datos.p_lyrics_language') },
};

function panelDatos() {
  // Sólo los campos que esta versión de la interfaz conoce: si el servidor
  // suma uno, no se dibuja un campo sin rótulo.
  const campos = ((S.catalogo && S.catalogo.campos) || []).filter((k) => CAMPO_A_COMPLETAR[k]);
  const sel = seleccionados();
  const total = S.catalogo.productos.length;
  const destino = S.datosAlcance === 'todos' ? S.catalogo.productos : sel;
  const cargados = (clave) => destino.filter((p) => (p.datos || {})[clave]).length;
  return `
  <div class="panel panel-herramienta" role="region" aria-label="${esc(T('herr.datos'))}">
    <h3>${esc(T('datos.titulo'))}</h3>
    <p class="small muted">${esc(T('datos.bajada'))}</p>
    <div class="grilla-datos mt-3">
      ${campos.map((clave) => `
      <div class="field">
        <label for="dato-${esc(clave)}">${esc(CAMPO_A_COMPLETAR[clave].rotulo())}</label>
        <input class="input" id="dato-${esc(clave)}" data-dato="${esc(clave)}" type="text" maxlength="200" autocomplete="off"
          placeholder="${esc(CAMPO_A_COMPLETAR[clave].ejemplo())}" value="${esc(S.datos[clave] || '')}"
          ${clave === 'c_line' && S.datosLineaC ? 'disabled' : ''} />
        <span class="hint">${esc(T('datos.ya', { n: num(cargados(clave)), total: num(destino.length) }))}</span>
      </div>`).join('')}
    </div>
    <label class="check mt-3">
      <input type="checkbox" id="datos-linea-c" ${S.datosLineaC ? 'checked' : ''} />
      <span class="check-texto"><strong>${esc(T('datos.linea_c_titulo'))}</strong><span class="sub">${esc(T('datos.linea_c_detalle'))}</span></span>
    </label>
    <div class="row row-wrap mt-4">
      <div class="segmented" role="group" aria-label="${esc(T('datos.aria_alcance'))}">
        <button type="button" class="${S.datosAlcance === 'elegidos' ? 'activo' : ''}" aria-pressed="${S.datosAlcance === 'elegidos'}" data-alcance="elegidos">${esc(T('datos.a_elegidos', { n: num(sel.length) }))}</button>
        <button type="button" class="${S.datosAlcance === 'todos' ? 'activo' : ''}" aria-pressed="${S.datosAlcance === 'todos'}" data-alcance="todos">${esc(T('datos.a_todos', { n: num(total) }))}</button>
      </div>
      <button type="button" class="btn btn-primary" data-accion="guardar-datos" ${destino.length ? '' : 'disabled'}>${esc(T('datos.guardar'))}</button>
      <button type="button" class="btn btn-ghost" data-accion="abrir-datos">${esc(T('datos.cerrar'))}</button>
    </div>
  </div>`;
}

const ESTADOS_COMPARACION = ['codigos_cambiados', 'falta', 'sin_youtube', 'en_las_dos', 'igual', 'migrado'];
const CLASE_ESTADO = {
  codigos_cambiados: 'badge-danger', falta: 'badge-warn', sin_youtube: 'badge-warn',
  en_las_dos: 'badge-warn', igual: 'badge-accent', migrado: 'badge-ok',
};
const TEXTO_ESTADO = {
  codigos_cambiados: { nombre: () => T('comp.e_codigos_cambiados'), detalle: () => T('comp.d_codigos_cambiados') },
  falta: { nombre: () => T('comp.e_falta'), detalle: () => T('comp.d_falta') },
  sin_youtube: { nombre: () => T('comp.e_sin_youtube'), detalle: () => T('comp.d_sin_youtube') },
  en_las_dos: { nombre: () => T('comp.e_en_las_dos'), detalle: () => T('comp.d_en_las_dos') },
  igual: { nombre: () => T('comp.e_igual'), detalle: () => T('comp.d_igual') },
  migrado: { nombre: () => T('comp.e_migrado'), detalle: () => T('comp.d_migrado') },
};

/** Qué pasó con cada release del relevamiento guardado. Lo malo primero: es a
 *  lo que se viene a mirar después de una migración. */
function panelComparacion() {
  const c = S.comparacion;
  const cuenta = ESTADOS_COMPARACION.filter((e) => c.resumen[e])
    .map((e) => `<span class="badge ${CLASE_ESTADO[e]}">${esc(TEXTO_ESTADO[e].nombre())} ${num(c.resumen[e])}</span>`).join('');
  const orden = [...c.releases].sort((a, b) => ESTADOS_COMPARACION.indexOf(a.estado) - ESTADOS_COMPARACION.indexOf(b.estado));
  const filas = orden.slice(0, 500).map((r) => {
    const detalle = [];
    if (r.upc_antes && r.upc_ahora && r.estado === 'codigos_cambiados' && r.upc_antes.replace(/^0+/, '') !== r.upc_ahora.replace(/^0+/, '')) {
      detalle.push(`UPC <span class="mono">${esc(r.upc_antes)}</span> <span class="flecha-cambio">→</span> <span class="mono">${esc(r.upc_ahora)}</span>`);
    }
    for (const x of r.isrc_cambiados) {
      detalle.push(`${esc(x.tema)}: <span class="mono">${esc(x.antes)}</span> <span class="flecha-cambio">→</span> <span class="mono">${esc(x.ahora)}</span>`);
    }
    if (r.temas_que_faltan.length) detalle.push(esc(T('comp.faltan_temas', { temas: r.temas_que_faltan.slice(0, 8).join(' · ') })));
    if (r.isrc_perdidos.length) detalle.push(esc(T('comp.isrc_perdidos', { temas: r.isrc_perdidos.slice(0, 8).join(' · ') })));
    const mismas = r.distribuidoras_ahora.length === 1 && r.distribuidoras_ahora[0] === r.distribuidora_antes;
    const distribuidoras = r.distribuidoras_ahora.length && !mismas
      ? `${esc(r.distribuidora_antes || T('tabla.sin_distribuidora'))} <span class="flecha-cambio">→</span> ${esc(r.distribuidoras_ahora.join(', '))}`
      : esc(r.distribuidora_antes || T('tabla.sin_distribuidora'));
    return `
    <tr>
      <td><div class="celda-titulo">${esc(r.titulo)}</div>${detalle.length ? `<div class="celda-sub">${detalle.join('<br>')}</div>` : ''}</td>
      <td class="nowrap mono">${esc(r.anio)}</td>
      <td>${distribuidoras}</td>
      <td>${TEXTO_ESTADO[r.estado] ? `<span class="badge ${CLASE_ESTADO[r.estado]}" title="${esc(TEXTO_ESTADO[r.estado].detalle())}">${esc(TEXTO_ESTADO[r.estado].nombre())}</span>` : ''}</td>
    </tr>`;
  }).join('');
  return `
  <div class="panel panel-herramienta" role="region" aria-label="${esc(T('herr.comparar'))}">
    <h3>${esc(T('comp.titulo', { fecha: c.fecha || '' }))}</h3>
    ${c.otro_artista ? alerta('warn', 'alerta', esc(T('comp.otro_artista', { artista: c.artista }))) : ''}
    <p class="small muted">${esc(T('comp.bajada'))}</p>
    <p class="badges mt-3">${cuenta}</p>
    ${c.releases.length ? `
    <div class="tabla-comparacion mt-3">
      <table class="sub">
        <thead><tr><th scope="col">${esc(T('tabla.col_producto'))}</th><th scope="col">${esc(T('tabla.col_anio'))}</th><th scope="col">${esc(T('tabla.col_distribuidora'))}</th><th scope="col">${esc(T('tabla.col_estado'))}</th></tr></thead>
        <tbody>${filas}</tbody>
      </table>
    </div>` : `<p class="mt-3">${esc(T('comp.nada'))}</p>`}
    ${c.nuevos_total ? `<p class="small muted mt-3">${esc(T(c.nuevos_total === 1 ? 'comp.nuevos_uno' : 'comp.nuevos', { n: num(c.nuevos_total), titulos: c.nuevos.slice(0, 6).map((n) => n.titulo).join(' · ') }))}</p>` : ''}
    <p class="small muted mt-3">${esc(T('comp.limite'))}</p>
    <div class="row mt-3"><button type="button" class="btn btn-ghost" data-accion="cerrar-comparacion">${esc(T('datos.cerrar'))}</button></div>
  </div>`;
}

/** Un archivo como base64, para mandarlo adentro del JSON: así pasa por el
 *  mismo camino, y las mismas defensas, que cualquier otro pedido. */
async function leerEnBase64(archivo) {
  const bytes = new Uint8Array(await archivo.arrayBuffer());
  let binario = '';
  // De a tramos: `String.fromCharCode(...bytes)` con un archivo de megas
  // revienta el límite de argumentos.
  for (let i = 0; i < bytes.length; i += 0x8000) {
    binario += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
  }
  return btoa(binario);
}

const TOPE_ARCHIVO = 5 * 1024 * 1024;

/** Lo que pasa cuando se eligió un archivo, según para qué se había pedido. */
async function archivoElegido(archivo) {
  const para = S.archivoPara;
  if (!archivo || !para) return;
  S.errorHerramienta = ''; S.hecho = '';
  if (archivo.size > TOPE_ARCHIVO) { S.errorHerramienta = T('herr.muy_grande'); render(); return; }
  S.leyendo = para; render();
  try {
    const cuerpo = { nombre: archivo.name || '', contenido: await leerEnBase64(archivo) };
    if (S.catalogo) cuerpo.catalogo_id = S.catalogo.catalogo_id;
    if (para === 'importar') {
      const imp = await api('/api/importar', cuerpo, 120000);
      S.importacion = imp;
      S.importElegidos = new Set(imp.elegidos || []);
      S.importElecciones = {};
    } else if (para === 'comparar') {
      S.comparacion = await api('/api/comparar', cuerpo, 120000);
    } else if (para === 'abrir') {
      delete cuerpo.catalogo_id;
      adoptarCatalogo(await api('/api/abrir', cuerpo, 120000));
      S.entrando = true;
    }
  } catch (e) {
    S.errorHerramienta = e.message;
  }
  S.leyendo = ''; S.archivoPara = '';
  render();
}

/** Aplica al catálogo en pantalla el que devolvió el servidor después de un
 *  cambio, sin perder lo elegido, lo desplegado ni el filtro: es el mismo
 *  catálogo con un dato distinto, no uno nuevo. */
function refrescarCatalogo(cat) {
  S.catalogo = cat;
  S.resultado = null;   // el paquete armado ya no es de lo que se ve
  S.guardado = null;
}

async function editar(cuerpo) {
  const cat = await api('/api/editar', { catalogo_id: S.catalogo.catalogo_id, ...cuerpo });
  refrescarCatalogo(cat);
}

/* ------------------------------------------------------------ paso 3 */

function vistaPaso3() {
  const sel = seleccionados();
  const o = S.opciones;
  const cfg = S.config;
  const audioOn = cfg.audio_habilitado;
  const puedeAudio = audioOn && (cfg.entorno.puede_flac || cfg.entorno.puede_referencia);
  const tidalOk = cfg.tidal_conectada;

  return `
  <div class="fade">
    <div class="card">
      <div class="card-head">
        <h1>${esc(T('paso3.titulo'))}</h1>
        <p>${esc(T('paso3.elegidos', {
          productos: cuenta('comun.n_productos', sel.length),
          tracks: cuenta('comun.n_tracks', sel.reduce((a, p) => a + p.tracks, 0)),
        }))}</p>
      </div>
      ${S.aviso ? alerta('', 'info', esc(S.aviso), 'status') : ''}
    </div>

    <div class="seccion">
      <div class="seccion-etiqueta"><h2>${esc(T('paso3.contenido'))}</h2></div>

      <div class="opciones">
        ${opcion('planilla', 'planilla', o.planilla, false, T('paso3.planilla'), esc(T('paso3.planilla_detalle')))}

        ${opcion('portadas', 'imagen', o.portadas, false, T('paso3.portadas'), esc(T('paso3.portadas_detalle')))}

        ${audioOn ? opcion('audio', 'musica', o.audio, !puedeAudio, T('paso3.audios'), puedeAudio
          ? esc(T('paso3.audios_detalle'))
          : faltaParaAudio()) : ''}
      </div>

      ${o.audio && audioOn ? bloqueTidal(tidalOk) : ''}

      ${S.error ? alerta('danger', 'error', esc(S.error)) : ''}
    </div>

    <div class="barra-accion">
      <div class="resumen frase">${esc(T('paso3.resumen_zip'))}</div>
      <div class="acciones">
        <button class="btn btn-secondary" data-accion="volver-2">${esc(T('comun.volver'))}</button>
        <button class="btn btn-primary" data-accion="generar"
          ${(o.planilla || o.portadas || o.audio) ? '' : 'disabled'}>${esc(T('paso3.generar'))}</button>
      </div>
    </div>
  </div>`;
}

/** Una opción de descarga. Es una fila de una lista, no una tarjeta: tres cajas
 *  iguales de icono, titulo y texto son el andamio perezoso de siempre, y era
 *  buena parte de lo que hacia que esta pantalla se viera como cualquier otra. */
function opcion(clave, icono, elegida, deshabilitada, titulo, detalle) {
  return `
    <div class="opcion ${elegida ? 'elegida' : ''} ${deshabilitada ? 'deshabilitada' : ''}" data-opcion="${clave}">
      <span class="opcion-icono">${ico(icono)}</span>
      <label class="check grow">
        <input type="checkbox" ${elegida ? 'checked' : ''} ${deshabilitada ? 'disabled' : ''} data-opcion-check="${clave}" />
        <span class="check-texto"><strong>${esc(titulo)}</strong>
          <span class="sub">${detalle}</span>
        </span>
      </label>
    </div>`;
}

/** Qué falta para poder bajar audio, con el comando concreto para resolverlo.
 *  Decir sólo "no disponible" deja a la persona sin saber qué hacer, y este es
 *  el caso típico de alguien que abrió la app en una máquina nueva. */
function faltaParaAudio() {
  const e = (S.config && S.config.entorno) || {};
  if (!e.ffmpeg && (e.tiddl || e.yt_dlp)) {
    const so = S.config && S.config.sistema;
    if (so === 'mac') return T('paso3.falta_ffmpeg_mac');
    if (so === 'linux') return T('paso3.falta_ffmpeg_linux');
    return T('paso3.falta_ffmpeg_windows');
  }
  if (!e.tiddl && !e.yt_dlp) return T('paso3.falta_modulo');
  return T('paso3.falta_generico');
}

function bloqueTidal(conectada) {
  if (conectada) {
    return `<div class="mt-5">${alerta('ok', 'ok', `
      <strong>${esc(T('tidal.conectada_titulo'))}</strong> ${esc(T('tidal.conectada_detalle'))}
      <div class="row mt-3">
        <button class="btn btn-ghost btn-sm" data-accion="tidal-salir">${esc(T('tidal.desconectar'))}</button>
      </div>`)}</div>`;
  }
  if (S.tidal) {
    return `<div class="mt-5">${alerta('', 'enlace', `
      <strong>${esc(T('tidal.conecta_titulo'))}</strong><br>
      ${T('tidal.abri', { url: `<a href="${esc(S.tidal.url)}" target="_blank" rel="noopener noreferrer">${esc(S.tidal.url)}</a>` })}
      ${S.tidal.codigo ? T('tidal.con_codigo', { codigo: `<span class="mono"><strong>${esc(S.tidal.codigo)}</strong></span>` }) : ''}.
      <div class="row mt-3">
        <button class="btn btn-secondary btn-sm" data-accion="tidal-confirmar">${esc(T('tidal.ya_confirme'))}</button>
        <button class="btn btn-ghost btn-sm" data-accion="tidal-salir">${esc(T('comun.cancelar'))}</button>
      </div>
      ${S.tidal.aviso ? `<p class="small mt-2">${esc(S.tidal.aviso)}</p>` : ''}`)}</div>`;
  }
  return `<div class="mt-5">${alerta('warn', 'alerta', `
    <strong>${esc(T('tidal.conecta_para_audio'))}</strong>
    ${esc(T('tidal.sin_cuenta_detalle'))}
    <div class="row mt-3">
      <button class="btn btn-secondary btn-sm" data-accion="tidal-iniciar">${esc(T('tidal.conectar'))}</button>
    </div>
    <p class="small mt-2">${esc(T('tidal.password'))}</p>`)}</div>`;
}

/* ------------------------------------------------------------ paso 4 */

function vistaPaso4() {
  if (S.ocupado) {
    return `<div class="card fade">
      <div class="card-head">
        <h1>${esc(T('paso4.armando'))}</h1>
        <p>${esc(T('paso4.armando_detalle'))}</p>
      </div>
      ${bloqueProgreso()}
    </div>`;
  }

  if (S.error) {
    return `<div class="card fade">
      <div class="card-head"><h1>${esc(T('paso4.error_titulo'))}</h1></div>
      ${alerta('danger', 'error', esc(S.error))}
      <div class="row mt-5">
        <button class="btn btn-secondary" data-accion="volver-3">${esc(T('comun.volver'))}</button>
        <button class="btn btn-primary" data-accion="generar">${esc(T('comun.reintentar'))}</button>
      </div>
    </div>`;
  }

  const r = S.resultado;
  if (!r) return vistaEsqueleto();
  const v = r.validacion || { apto: true, resumen: { errores: 0, avisos: 0 }, hallazgos: [] };

  return `
  <div class="fade">
    <div class="card">
      <div class="card-head">
        <h1>${esc(T('paso4.listo'))}</h1>
        <p><span class="mono">${esc(r.archivo)}</span>, ${pesoLegible(r.bytes)}.</p>
        <p class="lectura">
          ${T('paso4.resumen', {
            productos: cuenta('comun.n_productos', r.productos, `<span class="n">${num(r.productos)}</span>`),
            portadas: `<span class="n${r.portadas < r.productos ? ' atencion' : ''}">${num(r.portadas)} / ${num(r.productos)}</span>`,
            errores: `<span class="n${v.resumen.errores ? ' negativo' : ''}">${esc(T(v.resumen.errores === 1 ? 'comun.n_errores_uno' : 'comun.n_errores', { n: v.resumen.errores }))}</span>`,
            avisos: `<span class="n${v.resumen.avisos ? ' atencion' : ''}">${esc(T(v.resumen.avisos === 1 ? 'comun.n_avisos_uno' : 'comun.n_avisos', { n: v.resumen.avisos }))}</span>`,
          })}
        </p>
      </div>
    </div>

    ${panelValidacion(v)}

    ${queSigue()}

    ${S.errorDescarga ? alerta('danger', 'error', esc(S.errorDescarga)) : ''}
    ${S.guardado ? alerta('', 'ok', `${esc(T('paso4.guardado'))} <span class="mono">${esc(S.guardado.ruta)}</span>
      <button class="btn btn-ghost" data-accion="mostrar-guardado">${esc(T('paso4.mostrar'))}</button>`, 'status') : ''}

    <div class="barra-accion">
      <div class="resumen frase">${esc(T('paso4.zip_disponible'))}</div>
      <div class="acciones">
        <button class="btn btn-ghost" data-accion="volver-1">${esc(T('paso2.otro_artista'))}</button>
        <button class="btn btn-secondary" data-accion="volver-2">${esc(T('paso4.otros_productos'))}</button>
        <button class="btn btn-primary" data-accion="descargar" ${S.guardando ? 'disabled' : ''}>
          ${ico('descargar')} ${esc(T(S.guardando ? 'paso4.guardando' : 'paso4.descargar', { peso: pesoLegible(r.bytes) }))}
        </button>
      </div>
    </div>
    ${guardaSola() || !r.guardar ? '' : `<p class="muted nota-descarga">${esc(T('paso4.no_bajo'))}
      <button class="btn-enlace" data-accion="guardar-en-descargas">${esc(T('paso4.guardar_en_descargas'))}</button></p>`}
  </div>`;
}

/** Lo que dice el botón de actualizaciones del pie, según lo que se sabe. */
function textoActualizacion() {
  const a = S.actualizacion;
  if (!a) return T('pie.buscar_actualizacion');
  if (a.buscando) return T('pie.buscando_actualizacion');
  if (a.error) return T('pie.actualizacion_fallo');
  return a.hay ? T('pie.hay_version', { version: a.ultima }) : T('pie.al_dia');
}

/** Si «Descargar» guarda el paquete directo en la carpeta Descargas, sin
 *  pasar por la descarga de la ventana. Es el caso de la ventana propia en
 *  macOS, que descarta las descargas sin avisar: se apretaba el botón y no
 *  pasaba nada. En un navegador común la descarga funciona y se deja como está. */
function guardaSola() {
  return !!(S.config && S.config.sistema === 'mac' && window.pywebview);
}

/** Lo que viene después del ZIP. El éxito terminaba en «Descargar» sin decir
 *  qué hacer con lo descargado, y en una migración el orden importa: la baja
 *  en la distribuidora vieja es lo último, no lo primero. */
function queSigue() {
  return `
    <div class="seccion">
      <div class="seccion-etiqueta"><h2>${esc(T('paso4.que_sigue'))}</h2></div>
      <ol class="pasos-siguientes">
        <li>${T('paso4.sigue_completar')}</li>
        <li>${esc(T('paso4.sigue_pedir'))}</li>
        <li>${esc(T('paso4.sigue_cargar'))}</li>
        <li>${esc(T('paso4.sigue_baja'))}</li>
      </ol>
    </div>`;
}

/* Titulo corto por codigo de hallazgo, para la cabecera de cada grupo. El texto
   sale del catalogo con la clave `hallazgo.<codigo>`; si el codigo no esta
   traducido, se cae al mensaje del primer hallazgo del grupo. */
const CODIGOS_HALLAZGO = [
  'upc_falta', 'isrc_falta', 'sello_falta', 'anio_falta', 'orden_sin_confirmar',
  'portada_falta', 'portada_bajo_recomendado', 'portada_chica', 'portada_no_cuadrada',
  'portada_cmyk', 'portada_ilegible', 'titulo_con_ruido', 'duracion_larga',
  'duracion_falta', 'isrc_invalido', 'upc_invalido', 'isrc_duplicado', 'upc_duplicado',
  'anio_futuro', 'anio_absurdo', 'anio_invalido', 'producto_sin_titulo', 'track_sin_titulo',
  'texto_como_formula', 'isrc_compartido', 'isrc_match_dudoso', 'upc_no_verificado',
  'upc_mezclado', 'release_en_dos_distribuidoras', 'album_incompleto',
  'solo_en_deezer', 'temas_de_deezer', 'isrc_otro_corte', 'upc_por_tracklist', 'fecha_de_deezer',
  'artista_no_principal', 'portada_modo_color', 'audio_no_apto', 'isrc_confianza_media',
  'campos_a_completar', 'isrc_inferido', 'upc_inferido', 'isrc_ambiguo',
];

function tituloHallazgo(codigo, porDefecto) {
  return CODIGOS_HALLAZGO.includes(codigo) ? T('hallazgo.' + codigo) : porDefecto;
}

function panelValidacion(v) {
  if (v.apto && !v.resumen.avisos) {
    return alerta('ok', 'ok', `<strong>${esc(T('validacion.sin_nada_titulo'))}</strong> ${esc(T('validacion.sin_nada_detalle'))}`);
  }

  const errores = v.hallazgos.filter((h) => h.nivel === 'error');
  const avisos = v.hallazgos.filter((h) => h.nivel === 'aviso');

  const cabecera = errores.length
    ? alerta('danger', 'error', `<strong>${esc(T(errores.length === 1 ? 'validacion.errores_titulo_uno' : 'validacion.errores_titulo', { n: errores.length }))}</strong>
        ${T(v.resumen.errores === 1 ? 'validacion.errores_detalle_uno' : 'validacion.errores_detalle', { archivo: `<span class="mono">${esc(T('archivos.validacion'))}</span>` })}`)
    : alerta('ok', 'ok', `<strong>${esc(T('validacion.sin_errores'))}</strong> ${esc(T(avisos.length === 1 ? 'validacion.hay_avisos_uno' : 'validacion.hay_avisos', { n: avisos.length }))}`);

  // Agrupados por tipo de hallazgo: 41 filas de "sin ISRC" no se leen; "Sin
  // ISRC, 30 tracks en 8 productos" si, y adentro esta cada uno.
  const porTipo = (lista) => {
    const m = new Map();
    lista.forEach((h) => {
      if (!m.has(h.codigo)) m.set(h.codigo, { codigo: h.codigo, items: [] });
      m.get(h.codigo).items.push(h);
    });
    return [...m.values()];
  };
  const cuenta = (g) => {
    const prods = new Set(g.items.map((h) => h.producto)).size;
    const tracks = g.items.filter((h) => h.track).length;
    const enProductos = T(prods === 1 ? 'comun.n_productos_uno' : 'comun.n_productos', { n: prods });
    if (tracks && tracks === g.items.length) {
      return T('validacion.cuenta_tracks', {
        tracks: T(tracks === 1 ? 'comun.n_tracks_uno' : 'comun.n_tracks', { n: tracks }),
        productos: enProductos,
      });
    }
    return enProductos;
  };
  const grupo = (lista, nivel, abierto) => porTipo(lista).map((g) => {
    const mensajes = new Set(g.items.map((h) => h.mensaje));
    return `
    <details class="acordeon" ${abierto ? 'open' : ''}>
      <summary>${ico('flecha', 'ico-sm')}${esc(tituloHallazgo(g.codigo, g.items[0].mensaje))}
        <span class="cuenta${nivel === 'error' ? ' negativo' : ''}">${cuenta(g)}</span></summary>
      <div class="acordeon-body">
        ${mensajes.size === 1 ? `<p class="hallazgo-mensaje">${esc(g.items[0].mensaje)}</p>` : ''}
        <ul class="lista-hallazgos">${g.items.map((h) => `
          <li><strong>${esc(h.producto)}</strong>${h.track ? ` <span class="muted">${esc(h.track)}</span>` : ''}${mensajes.size > 1 ? `<div class="muted">${esc(h.mensaje)}</div>` : ''}</li>`).join('')}
        </ul>
      </div>
    </details>`;
  }).join('');

  return `<div class="seccion">
    <div class="seccion-etiqueta">
      <h2>${esc(T('validacion.titulo'))}</h2>
      <span class="der">${esc(T(v.resumen.errores === 1 ? 'comun.n_errores_uno' : 'comun.n_errores', { n: v.resumen.errores }))}, ${esc(T(v.resumen.avisos === 1 ? 'comun.n_avisos_uno' : 'comun.n_avisos', { n: v.resumen.avisos }))}</span>
    </div>
    ${cabecera}
    <div class="mt-4">
      ${grupo(errores, 'error', true)}
      ${grupo(avisos, 'aviso', false)}
    </div>
  </div>`;
}

/* ------------------------------------------------------------ Tidal */

/** Traduce los códigos crudos a algo que se entienda. */
function mensajeTidal(crudo) {
  const c = String(crudo || '').toLowerCase();
  if (c.includes('501') || c.includes('unsupported method')) return T('tidal.err_corte');
  if (c.includes('expired')) return T('tidal.err_vencido');
  if (c.includes('authorization_pending') || c.includes('pendiente') || c.includes('slow_down')) {
    return T('tidal.err_pendiente');
  }
  if (c.includes('invalid') || c.includes('token')) return T('tidal.err_rechazo');
  if (c.includes('failed to fetch') || c.includes('networkerror') || c.includes('conexión')) {
    return T('tidal.err_red');
  }
  return crudo || T('tidal.err_generico');
}

/** Una consulta de estado. `manual` distingue el clic del poll automático. */
async function _confirmarTidal({ manual }) {
  if (!S.tidal) return false;
  try {
    const d = await api('/api/tidal/confirmar', { device_code: S.tidal.device_code });
    if (d.conectada) {
      S.tidal = null;
      S.config = await api('/api/config');
      render();
      return true;
    }
    if (d.estado === 'pendiente') {
      // El poll automático NO toca el aviso. Si lo borrara, pisaría el mensaje
      // que dejó el clic en "Ya confirmé" y el botón parecería no hacer nada.
      if (manual) S.tidal.aviso = T('tidal.aun_no_confirmaste');
    } else {
      S.tidal.aviso = mensajeTidal(d.estado);
    }
    render();
  } catch (e) {
    if (S.tidal) S.tidal.aviso = mensajeTidal(e.message);
    render();
  }
  return false;
}

/** Consulta sola hasta que se conecte o venza el código. El código de Tidal vive
 *  5 minutos exactos, así que 100 vueltas de 3 s cubren justo esa ventana. */
async function _pollTidal() {
  const mio = S.tidal;
  // 3 s y no 2: Tidal responde `slow_down` si se consulta muy seguido, y el
  // usuario además puede apretar "Ya confirmé" en el medio.
  for (let i = 0; i < 100 && S.tidal === mio && mio.esperando; i++) {
    await new Promise((r) => setTimeout(r, 3000));
    if (S.tidal !== mio) return;                 // canceló o reinició
    if (await _confirmarTidal({ manual: false })) return;
  }
}

/* ------------------------------------------------------------ acciones */

const ACCIONES = {
  'cambiar-tema'() {
    // Dos estados, no tres. "Seguir al sistema" sonaba respetuoso pero en la
    // practica significaba que ninguno de los dos temas era el principal.
    const siguiente = temaGuardado() === 'claro' ? 'oscuro' : 'claro';
    try {
      localStorage.setItem('tema', siguiente);
    } catch (_) { /* no se pudo guardar la preferencia; el tema se aplica igual */ }
    aplicarTema(siguiente);
  },

  /** El idioma se guarda del lado del servidor y no en localStorage, porque
   *  Python también lo necesita: el log, los errores del relevamiento y los
   *  archivos del ZIP se arman allá. */
  async 'cambiar-idioma'(el) {
    const nuevo = el && el.getAttribute('data-idioma');
    if (!nuevo || nuevo === idioma()) return;
    aplicarIdioma(nuevo);            // la interfaz cambia ya, sin esperar la red
    render();
    try {
      await api('/api/idioma', { idioma: nuevo });
      if (S.config) S.config.idioma = nuevo;
    } catch (_) {
      // Si no se pudo guardar, la interfaz igual quedó en el idioma nuevo y la
      // próxima apertura vuelve al anterior. No vale un cartel de error.
    }
  },

  recargar() { window.location.reload(); },

  /** Bajar el ZIP. Antes era un `<a href download>` directo a /api/, y un enlace
   *  no puede mandar la cabecera del token: el servidor contestaba 403 y el
   *  paquete no se podía bajar desde la interfaz. Ahora se pide con el token un
   *  ticket de un solo uso, y el enlace que se abre es el del ticket. */
  async descargar() {
    const r = S.resultado;
    if (!r) return;
    if (guardaSola() && r.guardar) return ACCIONES['guardar-en-descargas']();
    let url;
    try {
      ({ url } = await api(r.descarga, {}));
    } catch (e) {
      // El caso esperable es el ZIP vencido (vive una hora). No es un error
      // fatal: el paquete se vuelve a armar desde el paso 3.
      S.errorDescarga = e.message;
      render();
      return;
    }
    if (S.errorDescarga) { S.errorDescarga = ''; render(); }
    const a = document.createElement('a');
    a.href = url;
    a.download = r.archivo || '';
    document.body.appendChild(a);
    a.click();
    a.remove();
  },

  /** Copiar el ZIP a la carpeta Descargas, del lado del servidor. Diez
   *  minutos de espera: con audio el paquete pesa varios GB. */
  async 'guardar-en-descargas'() {
    const r = S.resultado;
    if (!r || !r.guardar || S.guardando) return;
    S.guardando = true; S.errorDescarga = ''; render();
    try {
      S.guardado = await api(r.guardar, {}, 600000);
    } catch (e) {
      S.errorDescarga = e.message;
    }
    S.guardando = false;
    render();
  },

  async 'mostrar-guardado'() {
    if (!S.guardado) return;
    try {
      await api('/api/mostrar', { ruta: S.guardado.ruta });
    } catch (e) {
      S.errorDescarga = e.message;
      render();
    }
  },

  /** El botón del pie. La primera vez pregunta si hay una versión más nueva;
   *  si la hay, el mismo botón pasa a abrir la página para bajarla. */
  async 'buscar-actualizacion'() {
    if (S.actualizacion && S.actualizacion.hay) {
      try { await api('/api/actualizacion/abrir', {}); } catch (_) { /* queda el aviso a la vista */ }
      return;
    }
    S.actualizacion = { buscando: true };
    render();
    try {
      S.actualizacion = await api('/api/actualizacion');
    } catch (e) {
      S.actualizacion = { error: e.message };
    }
    render();
  },

  /* ---- lo que el usuario cambia a mano ---- */

  'elegir-archivo'(el) {
    S.archivoPara = (el && el.getAttribute('data-para')) || '';
    const campo = $('#archivo');
    if (campo) { campo.value = ''; campo.click(); }
  },

  'editar-isrc'(el) {
    const producto = el.getAttribute('data-producto'), indice = Number(el.getAttribute('data-indice'));
    const p = S.catalogo.productos.find((x) => x.id === producto);
    S.editando = { tipo: 'isrc', producto, indice, valor: (p && p.detalle[indice] && p.detalle[indice].isrc) || '', error: '' };
    conScrollPreservado(render);
    const c = $('#codigo-edit'); if (c) { c.focus(); c.select(); }
  },

  'editar-upc'(el) {
    const producto = el.getAttribute('data-producto');
    const p = S.catalogo.productos.find((x) => x.id === producto);
    S.editando = { tipo: 'upc', producto, indice: -1, valor: (p && p.upc) || '', error: '' };
    conScrollPreservado(render);
    const c = $('#codigo-edit'); if (c) { c.focus(); c.select(); }
  },

  'cancelar-codigo'() { S.editando = null; conScrollPreservado(render); },

  async 'guardar-codigo'() {
    const e = S.editando;
    if (!e) return;
    const campo = $('#codigo-edit');
    const valor = (campo ? campo.value : e.valor).trim();
    try {
      await editar({ tipo: e.tipo, producto: e.producto, indice: e.indice, valor });
      S.editando = null;
    } catch (err) {
      // El formato inválido se dice al lado del campo, con lo escrito a la
      // vista para corregirlo: no es un error de la app.
      S.editando = { ...e, valor, error: err.message };
    }
    conScrollPreservado(render);
    const c = $('#codigo-edit'); if (c) c.focus();
  },

  async 'usar-candidato'(el) {
    await editar({ tipo: 'isrc', producto: el.getAttribute('data-producto'), indice: Number(el.getAttribute('data-indice')), valor: el.getAttribute('data-isrc') });
    conScrollPreservado(render);
  },

  async 'restaurar-isrc'(el) {
    await editar({ tipo: 'isrc', producto: el.getAttribute('data-producto'), indice: Number(el.getAttribute('data-indice')), valor: '' });
    conScrollPreservado(render);
  },

  async 'restaurar-upc'(el) {
    await editar({ tipo: 'upc', producto: el.getAttribute('data-producto'), valor: '' });
    conScrollPreservado(render);
  },

  'abrir-datos'() { S.datosAbierto = !S.datosAbierto; S.hecho = ''; S.errorHerramienta = ''; render(); },

  async 'guardar-datos'() {
    const ids = (S.datosAlcance === 'todos' ? S.catalogo.productos : seleccionados()).map((p) => p.id);
    const datos = {};
    for (const [clave, valor] of Object.entries(S.datos)) if (String(valor).trim()) datos[clave] = String(valor).trim();
    if (!Object.keys(datos).length && !S.datosLineaC) { S.errorHerramienta = T('datos.nada_que_guardar'); render(); return; }
    try {
      await editar({ tipo: 'datos', ids, datos, c_sugerida: S.datosLineaC });
      S.hecho = T(ids.length === 1 ? 'datos.hecho_uno' : 'datos.hecho', { n: num(ids.length) });
      S.datos = {}; S.datosLineaC = false; S.datosAbierto = false; S.errorHerramienta = '';
    } catch (e) {
      S.errorHerramienta = e.message;
    }
    render();
  },

  async 'aplicar-importacion'() {
    const imp = S.importacion;
    if (!imp) return;
    try {
      const r = await api('/api/importar/aplicar', {
        catalogo_id: S.catalogo.catalogo_id, id: imp.id,
        elegidos: [...S.importElegidos], elecciones: S.importElecciones,
      });
      refrescarCatalogo(r.catalogo);
      S.hecho = T('imp.hecho', { cargados: num(r.hechos.cargados), confirmados: num(r.hechos.confirmados) });
      S.importacion = null; S.errorHerramienta = '';
    } catch (e) {
      S.errorHerramienta = e.message;
    }
    render();
  },

  'descartar-importacion'() { S.importacion = null; S.errorHerramienta = ''; render(); },
  'cerrar-comparacion'() { S.comparacion = null; render(); },

  'ver-terminos'() { S.vista = 'terminos'; S.entrando = true; render(); arriba(); },
  'ver-clave'() { S.vista = 'clave'; S.entrando = true; render(); arriba(); },
  'ver-faltantes'() { S.verFaltantes = !S.verFaltantes; render(); },
  // Vuelve al paso 1, que es donde está el campo y la barra de avance, y
  // releva el mismo link pidiendo el listado de cero.
  relistar() { S.paso = 1; S.deCero = true; S.error = ''; S.errorCodigo = ''; render(); return ACCIONES.relevar(); },

  'otro-deezer'() {
    S.pideDeezer = true; S.verRelevamiento = true; render();
    const c = $('#deezer-link'); if (c) c.focus();
  },

  /** Volver a buscar los códigos con el perfil de Deezer que se pegó. No gasta
   *  cupo de YouTube: el listado del canal es el de esta sesión. */
  'usar-deezer'() {
    const campo = $('#deezer-link');
    S.deezerLink = campo ? campo.value.trim() : S.deezerLink;
    if (!S.deezerLink) {
      S.deezerError = T('paso2.deezer_falta_link'); render();
      const c = $('#deezer-link'); if (c) c.focus();
      return undefined;
    }
    S.deezerError = ''; S.paso = 1; S.error = ''; S.errorCodigo = ''; render();
    return ACCIONES.relevar();
  },
  'cerrar-vista'() { S.vista = null; S.entrando = true; render(); arriba(); },

  async 'aceptar-terminos'() {
    await api('/api/terminos', { aceptar: true });
    S.config = await api('/api/config');
    render();
    arriba();
  },

  'limpiar-filtro'() {
    S.filtro.texto = '';
    S.filtro.modo = 'manual';
    S.filtro.faltantes = false;
    render();
  },

  async 'guardar-clave'() {
    const campo = $('#clave');
    const caja = $('#setup-error');
    const clave = campo ? campo.value.trim() : '';
    if (!clave) {
      caja.innerHTML = alerta('danger', 'error', esc(T('clave.pega_antes')));
      return;
    }
    // `.latido` es el indicador de trabajo de toda la app; el `.spinner` que
    // había acá no existía en el CSS, y «Verificando» quedaba quieto.
    caja.innerHTML = `<div class="row mt-4" role="status"><span class="latido" aria-hidden="true"><i></i><i></i><i></i></span><span>${esc(T('clave.verificando'))}</span></div>`;
    try {
      await api('/api/clave', { clave }, 45000);
      S.config = await api('/api/config');
      S.vista = null;
      // El error de cupo o de clave era el motivo para venir acá, y la clave
      // nueva lo resuelve: dejarlo a la vista decía que seguía el problema.
      if (S.errorCodigo === 'cuota' || S.errorCodigo === 'clave') { S.error = ''; S.errorCodigo = ''; }
      S.entrando = true;
      render(); arriba();
    } catch (e) {
      caja.innerHTML = alerta('danger', 'error', `<strong>${esc(T('clave.no_se_guardo'))}</strong><br>${esc(e.message)}`);
    }
  },

  async relevar() {
    const campo = $('#url');
    // Sin el campo a la vista (cuando se pide desde el paso 2), vale el link
    // que ya se había pegado.
    const url = campo ? campo.value.trim() : (S.url || '');
    S.url = url;
    // «Volver a listar» pide el listado de cero; un relevamiento común reusa
    // el de esta sesión si lo hay. Vale para un solo pedido.
    const deCero = S.deCero;
    S.deCero = false;
    if (!url) {
      S.errorCampo = T('paso1.falta_link'); render();
      const c = $('#url'); if (c) c.focus();
      return;
    }
    const casilla = $('#con-codigos');
    if (casilla) S.conCodigos = casilla.checked;
    S.error = ''; S.errorCodigo = ''; S.errorCampo = ''; S.ocupado = true; S.job = null; render();
    try {
      S.deezerUsado = S.deezerLink;
      const { job } = await api('/api/relevar', {
        url, con_codigos: S.conCodigos, de_cero: deCero, deezer_artista: S.deezerLink,
      });
      const cat = await esperarJob(job, () => actualizarProgreso());
      await cierreDelTrabajo();
      adoptarCatalogo(cat);          // arranca con todo elegido
      S.pideDeezer = false;
      S.ocupado = false; S.entrando = true;
      render(); arriba();
    } catch (e) {
      S.ocupado = false;
      // Un link que el servidor no reconoce es un problema del campo, no del
      // mundo. Se mira el código y no el texto: con la app en inglés, comparar
      // contra una frase en español dejaba de funcionar justo acá.
      if (e.codigo === 'url') {
        S.errorCampo = e.message; S.error = '';
      } else if (e.codigo === 'deezer') {
        // El link de Deezer no sirve: se vuelve a donde está el campo, con el
        // catálogo que ya había, y se dice ahí.
        S.deezerError = e.message; S.error = '';
        if (S.catalogo) { S.paso = 2; S.pideDeezer = true; S.verRelevamiento = true; }
      } else {
        S.error = e.message === 'CANCELADO' ? '' : e.message;
      }
      S.errorCodigo = e.codigo || '';
      render();
      if (S.errorCampo) { const c = $('#url'); if (c) c.focus(); }
    }
  },

  async cancelar() {
    if (S.job) { try { await api(`/api/job/${S.job.id}/cancelar`, {}); } catch (_) {} }
  },

  // No descarta el paquete: «Relevar otro artista» en el paso 4 tiraba un ZIP
  // que todavía no se había bajado, al lado de un texto que decía que seguía
  // disponible. Se descarta cuando hay otro catálogo (`adoptarCatalogo`).
  'volver-1'() { S.paso = 1; S.aviso = ''; S.error = ''; S.errorCodigo = ''; S.entrando = true; render(); arriba(); },
  'volver-2'() { S.paso = 2; S.aviso = ''; S.error = ''; S.errorCodigo = ''; S.entrando = true; render(); arriba(); },
  'volver-3'() { S.paso = 3; S.aviso = ''; S.error = ''; S.errorCodigo = ''; S.entrando = true; render(); arriba(); },
  'ir-3'() { S.paso = 3; S.aviso = ''; S.error = ''; S.errorCodigo = ''; S.entrando = true; render(); arriba(); },

  'sel-todo'() { recordarSeleccion(); productosFiltrados().forEach((p) => S.seleccion.add(p.id)); conScrollPreservado(render); },
  'sel-nada'() { recordarSeleccion(); productosFiltrados().forEach((p) => S.seleccion.delete(p.id)); conScrollPreservado(render); },
  'deshacer-seleccion'() {
    if (!S.deshacer) return;
    S.seleccion = S.deshacer;
    S.deshacer = null;
    conScrollPreservado(render);
  },

  async 'tidal-iniciar'() {
    S.error = '';
    try {
      const d = await api('/api/tidal/iniciar', {});
      S.tidal = { url: d.url, codigo: d.codigo, device_code: d.device_code, esperando: true };
      // Le abrimos el sitio de Tidal para que no tenga que copiar el link.
      window.open(d.url, '_blank', 'noopener');
      render();
      // Y consultamos solos, porque Tidal tarda unos segundos en registrar la
      // confirmación. Si dependiera del botón, el usuario apretaría justo antes y
      // vería un error que no es un error.
      _pollTidal();
    } catch (e) { S.error = mensajeTidal(e.message); render(); }
  },

  async 'tidal-confirmar'() {
    if (!S.tidal) return;
    S.error = '';                    // el aviso anterior no debe quedar pegado
    S.tidal.aviso = T('tidal.consultando');
    render();
    await _confirmarTidal({ manual: true });
  },

  async 'tidal-salir'() {
    if (S.tidal) S.tidal.esperando = false;       // corta el poll automático
    S.error = '';
    try { await api('/api/tidal/desconectar', {}); } catch (_) {}
    S.tidal = null;
    try { S.config = await api('/api/config'); } catch (_) {}
    render();
  },

  async generar() {
    const ids = seleccionados().map((p) => p.id);
    if (!ids.length) { S.error = T('paso3.sin_seleccion'); render(); return; }
    S.error = ''; S.errorCodigo = ''; S.errorDescarga = ''; S.guardado = null; S.aviso = ''; S.resultado = null; S.ocupado = true; S.paso = 4; S.job = null; render();
    try {
      const { job } = await api('/api/preparar', {
        // Si en otra ventana se relevó otro artista, el servidor lo nota por
        // acá y no arma el paquete de aquél con los ids de éste.
        catalogo_id: S.catalogo && S.catalogo.catalogo_id,
        ids,
        planilla: S.opciones.planilla,
        portadas: S.opciones.portadas,
        audio: S.opciones.audio,
      });
      S.resultado = await esperarJob(job, () => actualizarProgreso());
      await cierreDelTrabajo();
      S.ocupado = false; S.entrando = true; render(); arriba();
    } catch (e) {
      S.ocupado = false;
      if (e.message === 'CANCELADO') {
        // Cancelar es algo que hizo la persona, no algo que falló: vuelve a
        // donde estaba, con lo elegido intacto, y sin rojo.
        S.paso = 3; S.aviso = T('paso3.cancelado'); S.entrando = true;
      } else {
        S.error = e.message;
        S.errorCodigo = e.codigo || '';
      }
      render();
    }
  },
};

/** Actualiza sólo el bloque de progreso, para no redibujar (ni perder el scroll
 *  del log) en cada consulta al backend. */
function actualizarProgreso() {
  const j = S.job;
  if (!j) return;
  const barra = $('.barra-fill');
  if (barra) {
    barra.style.transform = 'scaleX(' + (j.progreso || 0).toFixed(3) + ')';
    const cont = $('.barra');
    if (cont) cont.setAttribute('aria-valuenow', Math.round((j.progreso || 0) * 100));
  } else if (j.progreso > 0) {
    // Llego el primer avance y la barra todavia no existe en el DOM. Se dibuja
    // una sola vez; de ahi en adelante entra por la rama de arriba.
    render();
    return;
  }
  const msj = $('#progreso-mensaje');
  if (msj) msj.textContent = j.mensaje || T('progreso.trabajando');
  const pct = $('#progreso-pct');
  if (pct) pct.textContent = j.progreso ? Math.round(j.progreso * 100) + '%' : '';
  const log = $('#log');
  if (log) {
    const pegadoAbajo = log.scrollHeight - log.scrollTop - log.clientHeight < 30;
    const lineas = (j.log || []).slice(-60);
    const previas = log.childElementCount;
    // Solo se agregan las lineas nuevas, y entran con un fade; las de antes no
    // se tocan, asi la lista no parpadea en cada consulta.
    if (previas > lineas.length || (previas && log.children[0].textContent !== lineas[0])) log.textContent = '';
    for (let i = log.childElementCount; i < lineas.length; i++) {
      const el = document.createElement('div');
      el.className = previas ? 'nueva' : '';
      el.textContent = lineas[i];
      log.appendChild(el);
    }
    if (pegadoAbajo) log.scrollTop = log.scrollHeight;
  }
  const pie = $('#pie-estado');
  if (pie) pie.textContent = j.mensaje || '';
}

/* ------------------------------------------------------------ eventos */

/** Envuelve un manejador para que una excepción no deje la interfaz muerta sin
 *  decir nada. Antes, cualquier error adentro de una acción cortaba el flujo en
 *  silencio y la app parecía colgada. */
function seguro(fn) {
  try {
    const r = fn();
    if (r && typeof r.catch === 'function') r.catch(mostrarFatal);
  } catch (e) {
    mostrarFatal(e);
  }
}

/** Busca una fila por su id sin armar un selector con el id adentro: los
 *  product_id salen de títulos reales y pueden traer comillas. */
function filaDe(id) {
  return [...document.querySelectorAll('[data-fila]')].find((n) => n.getAttribute('data-fila') === id) || null;
}

document.addEventListener('click', (ev) => {
  const btnAccion = ev.target.closest('[data-accion]');
  if (btnAccion) {
    const fn = ACCIONES[btnAccion.dataset.accion];
    // Se le pasa el elemento: hay acciones, como el cambio de idioma, que
    // necesitan saber cuál de varios botones con la misma acción se apretó.
    if (fn) { ev.preventDefault(); seguro(() => fn(btnAccion)); }
    return;
  }

  const irPaso = ev.target.closest('[data-ir-paso]');
  if (irPaso) {
    const n = parseInt(irPaso.dataset.irPaso, 10);
    if (pasoAlcanzable(n)) { S.paso = n; S.error = ''; S.aviso = ''; S.entrando = true; seguro(render); arriba(); }
    return;
  }

  const modo = ev.target.closest('[data-modo]');
  if (modo) { S.filtro.modo = modo.dataset.modo; seguro(render); return; }

  const alcance = ev.target.closest('[data-alcance]');
  if (alcance) { S.datosAlcance = alcance.dataset.alcance; seguro(render); return; }

  const orden = ev.target.closest('[data-orden]');
  if (orden) {
    S.orden = siguienteOrden(orden.dataset.orden);
    seguro(() => conScrollPreservado(render));
    return;
  }

  // Con Shift, la casilla o la fila eligen todo el tramo desde la última que se
  // tocó. El evento `change` no trae la tecla, así que se anota acá.
  if (ev.target.matches && ev.target.matches('input[data-prod]')) S.conShift = ev.shiftKey;

  // La fila entera elige el producto; la casilla, el chevron y los links siguen
  // haciendo lo suyo. Apuntar a 15 px no es una interaccion.
  const fila = ev.target.closest('tr[data-fila]');
  if (fila && !ev.target.closest('button, a, input, label')) {
    const cb = fila.querySelector('input[data-prod]');
    if (cb) {
      S.conShift = ev.shiftKey;
      cb.checked = !cb.checked;
      cb.dispatchEvent(new Event('change', { bubbles: true }));
    }
    return;
  }

  const expandir = ev.target.closest('[data-expandir]');
  if (expandir) {
    const id = expandir.dataset.expandir;
    if (S.expandidos.has(id)) S.expandidos.delete(id); else S.expandidos.add(id);
    seguro(() => conScrollPreservado(render));
    return;
  }

  // Clic en la tarjeta de opción (no en su casilla) también la alterna.
  const tarjeta = ev.target.closest('[data-opcion]');
  if (tarjeta && ev.target.tagName !== 'INPUT' && !tarjeta.classList.contains('deshabilitada')) {
    const k = tarjeta.dataset.opcion;
    S.opciones[k] = !S.opciones[k];
    seguro(render);
  }
});

document.addEventListener('change', (ev) => {
  const t = ev.target;

  if (t.id === 'archivo') {
    seguro(() => archivoElegido(t.files && t.files[0]));
    return;
  }
  if (t.dataset.item) {
    if (t.checked) S.importElegidos.add(t.dataset.item); else S.importElegidos.delete(t.dataset.item);
    seguro(render);
    return;
  }
  if (t.dataset.eleccion) {
    // Elegir entre los candidatos de un ítem ambiguo es también elegir el ítem.
    S.importElecciones[t.dataset.eleccion] = t.value;
    S.importElegidos.add(t.dataset.eleccion);
    seguro(render);
    return;
  }
  if (t.id === 'datos-linea-c') { S.datosLineaC = t.checked; seguro(render); return; }

  if (t.dataset.prod) {
    const id = t.dataset.prod;
    const tramo = S.conShift ? tramoDesdeAncla(id) : [id];
    S.conShift = false;
    S.ancla = id;
    // Un tramo se deshace como cualquier acción en lote. Un clic suelto, no: se
    // deshace con otro clic, y el «Deshacer» anterior ya no correspondería.
    if (tramo.length > 1) recordarSeleccion(); else S.deshacer = null;
    for (const x of tramo) {
      if (t.checked) S.seleccion.add(x); else S.seleccion.delete(x);
      // Actualización puntual: redibujar la tabla entera en cada clic se siente lento.
      const fila = filaDe(x);
      if (fila) {
        fila.classList.toggle('elegida', t.checked);
        const cb = fila.querySelector('input[data-prod]');
        if (cb) cb.checked = t.checked;
      }
    }
    seguro(actualizarResumenSeleccion);
    return;
  }

  if (t.id === 'check-todos') {
    recordarSeleccion();
    if (t.checked) productosFiltrados().forEach((p) => S.seleccion.add(p.id));
    else productosFiltrados().forEach((p) => S.seleccion.delete(p.id));
    seguro(() => conScrollPreservado(render));
    return;
  }

  if (t.dataset.distrib !== undefined) {
    if (t.checked) S.filtro.distribs.add(t.dataset.distrib);
    else S.filtro.distribs.delete(t.dataset.distrib);
    seguro(render);
    return;
  }

  if (t.id === 'solo-faltantes') {
    S.filtro.faltantes = t.checked;
    seguro(render);
    return;
  }

  if (t.dataset.opcionCheck) {
    S.opciones[t.dataset.opcionCheck] = t.checked;
    seguro(render);
    return;
  }

  if (t.id === 'anio-desde' || t.id === 'anio-hasta') {
    const campoDesde = $('#anio-desde'), campoHasta = $('#anio-hasta');
    const desde = parseInt(campoDesde ? campoDesde.value : '', 10);
    const hasta = parseInt(campoHasta ? campoHasta.value : '', 10);
    S.filtro.anioDesde = Number.isFinite(desde) ? desde : null;
    S.filtro.anioHasta = Number.isFinite(hasta) ? hasta : null;
    // Un rango invertido no devuelve nada y se lee como que la app se rompió.
    if (S.filtro.anioDesde !== null && S.filtro.anioHasta !== null
        && S.filtro.anioDesde > S.filtro.anioHasta) {
      const x = S.filtro.anioDesde;
      S.filtro.anioDesde = S.filtro.anioHasta;
      S.filtro.anioHasta = x;
    }
    seguro(render);
  }
});

document.addEventListener('input', (ev) => {
  // Otro canal es otro artista: el perfil de Deezer que se había pegado no vale.
  if (ev.target.id === 'url' && ev.target.value.trim() !== (S.url || '').trim()) {
    S.deezerLink = ''; S.deezerUsado = ''; S.deezerError = '';
  }
  if (ev.target.id === 'url') S.url = ev.target.value;
  if (ev.target.dataset && ev.target.dataset.dato) S.datos[ev.target.dataset.dato] = ev.target.value;
  if (ev.target.id === 'codigo-edit' && S.editando) S.editando.valor = ev.target.value;
  if (ev.target.id === 'deezer-link') { S.deezerLink = ev.target.value; S.deezerError = ''; }
  if (ev.target.id === 'url' && S.errorCampo) {
    S.errorCampo = '';
    ev.target.classList.remove('error');
    const h = $('#url-error'); if (h) h.remove();
  }
  if (ev.target.id === 'buscar') {
    S.filtro.texto = ev.target.value;
    clearTimeout(document.__buscarTimer);
    // Debounce: filtrar en cada tecla sobre un catálogo grande se nota. El foco y
    // el cursor los recupera render() por su cuenta.
    document.__buscarTimer = setTimeout(() => seguro(render), 180);
  }
});

document.addEventListener('keydown', (ev) => {
  if (ev.key === 'Escape' && ev.target.id === 'codigo-edit') { ev.preventDefault(); seguro(ACCIONES['cancelar-codigo']); return; }
  if (ev.key !== 'Enter') return;
  if (ev.target.id === 'codigo-edit') { ev.preventDefault(); seguro(ACCIONES['guardar-codigo']); return; }
  if (ev.target.id === 'url') { ev.preventDefault(); seguro(ACCIONES.relevar); }
  if (ev.target.id === 'clave') { ev.preventDefault(); seguro(ACCIONES['guardar-clave']); }
});

/* Cualquier error que se escape queda a la vista, en vez de dejar una pantalla
   congelada sin explicación. */
window.addEventListener('error', (ev) => { if (!S.fatal) mostrarFatal(ev.error || ev.message); });
window.addEventListener('unhandledrejection', (ev) => { if (!S.fatal) mostrarFatal(ev.reason); });

/** Guarda la selección antes de una acción en lote, para poder deshacerla.
 *  «Desmarcar todos» está al lado de «Continuar» y un clic de más borraba lo
 *  elegido a mano en un catálogo de cientos de productos, sin vuelta atrás. */
function recordarSeleccion() {
  S.deshacer = new Set(S.seleccion);
}

/** Las filas entre la última que se tocó y ésta, en el orden en que se ven. Si
 *  la anterior ya no está a la vista (otro filtro, otro orden), sólo ésta. */
function tramoDesdeAncla(id) {
  const ids = productosFiltrados().map((p) => p.id);
  const a = ids.indexOf(S.ancla), b = ids.indexOf(id);
  if (a < 0 || b < 0) return [id];
  return ids.slice(Math.min(a, b), Math.max(a, b) + 1);
}

/* El <details> de «Cómo se relevó» se abre y se cierra solo, sin pasar por
   render(). Se anota el estado para que el próximo redibujo lo respete. El
   evento `toggle` no burbujea: se escucha en la captura. */
document.addEventListener('toggle', (ev) => {
  if (ev.target.classList && ev.target.classList.contains('relevamiento')) S.verRelevamiento = ev.target.open;
}, true);

/** Redibuja conservando el scroll de la tabla. */
function conScrollPreservado(fn) {
  const caja = $('#tabla-wrap');
  const prev = caja ? caja.scrollTop : 0;
  fn();
  const nuevo = $('#tabla-wrap');
  if (nuevo) nuevo.scrollTop = prev;
}

function actualizarResumenSeleccion() {
  const ps = productosFiltrados();
  const sel = seleccionados();
  const caja = document.querySelector('.barra-accion .resumen');
  if (caja) {
    caja.innerHTML = resumenElegidos(sel);
  }
  const btn = document.querySelector('[data-accion="ir-3"]');
  if (btn) btn.disabled = sel.length === 0;
  // Solo se ofrece la accion que tiene sentido: marcar si falta alguno, desmarcar si hay alguno.
  const visiblesElegidos = ps.filter((p) => S.seleccion.has(p.id)).length;
  const bTodo = document.querySelector('[data-accion="sel-todo"]');
  if (bTodo) bTodo.hidden = visiblesElegidos >= ps.length;
  const bNada = document.querySelector('[data-accion="sel-nada"]');
  if (bNada) bNada.hidden = visiblesElegidos === 0;
  const todos = $('#check-todos');
  if (todos) {
    todos.checked = ps.length > 0 && ps.every((p) => S.seleccion.has(p.id));
    todos.indeterminate = !todos.checked && ps.some((p) => S.seleccion.has(p.id));
  }
}

/* ------------------------------------------------------------ arranque */

/** Carga el catálogo que el backend ya tenga en memoria. Sirve para que un F5 no
 *  obligue a relevar de nuevo, que cuesta cuota de YouTube. */
function adoptarCatalogo(cat) {
  S.catalogo = cat;
  // Arranca con todo elegido menos lo que sólo está en Deezer: de eso no se
  // sabe la distribuidora ni si es del catálogo, y lo tiene que elegir alguien.
  S.seleccion = new Set(cat.productos.filter((p) => p.origen !== 'deezer').map((p) => p.id));
  S.expandidos = new Set();
  S.verFaltantes = false;
  S.verRelevamiento = false;
  S.orden = null;
  S.ancla = null;
  S.deshacer = null;
  // Otro catálogo: el paquete del anterior ya no es de lo que se ve, ni lo
  // que se estaba editando, importando o comparando.
  S.resultado = null;
  S.guardado = null;
  S.editando = null; S.importacion = null; S.comparacion = null;
  S.datosAbierto = false; S.datos = {}; S.datosLineaC = false;
  S.hecho = ''; S.errorHerramienta = '';
  S.filtro = {
    modo: 'manual',
    anioDesde: cat.filtros.anio_min,
    anioHasta: cat.filtros.anio_max,
    distribs: new Set(cat.filtros.distribuidoras.map((d) => d.name)),
    texto: '',
    faltantes: false,
  };
  S.paso = 2;
}

/** Aplica el idioma a todo lo que no pasa por render(): el html lang, los
 *  textos fijos de index.html y el botón marcado del selector. */
function aplicarIdioma(codigo) {
  ponerIdioma(codigo);
  traducirEstaticos();
  marcarIdioma();
  aplicarTema(temaGuardado());     // el rótulo del botón de tema también cambia
}

/* Cada tanto la página avisa que sigue abierta. En el navegador, cerrar la
   pestaña no le avisa a nadie y el binario no tiene consola: el launcher cierra
   el servidor cuando ninguna ventana late. Un latido que falla no importa, el
   siguiente lo compensa. */
const LATIDO_MS = 15000;
function latir() { return api('/api/latido', {}, 10000).catch(() => {}); }

(async function iniciar() {
  aplicarTema(temaGuardado());
  // Antes de tener config no se sabe el idioma elegido, así que se arranca con
  // el del navegador. Es sólo para el esqueleto: /api/config lo corrige enseguida.
  aplicarIdioma((navigator.language || '').slice(0, 2));
  render();
  try {
    S.config = await api('/api/config', undefined, 15000);
  } catch (e) {
    pantalla().innerHTML = alerta('danger', 'error',
      `<strong>${esc(T('arranque.sin_motor_titulo'))}</strong><br>${esc(T('arranque.sin_motor_detalle'))}`);
    return;
  }
  aplicarIdioma(S.config.idioma);
  latir();
  setInterval(latir, LATIDO_MS);

  if (S.config.catalogo_cargado) {
    try { adoptarCatalogo(await api('/api/catalogo')); } catch (_) { /* seguimos en el paso 1 */ }
  }

  render();
  const i = $('#url');
  if (i) i.focus();
})();
