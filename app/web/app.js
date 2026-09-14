/* ============================================================
   Migrador de Catálogos — frontend.

   Vanilla JS a propósito: sin React, sin Babel en el navegador y sin CDN. La
   app se empaqueta como ejecutable, así que no puede depender de una descarga
   en tiempo de ejecución, y sin build step el binario se arma con sólo copiar
   archivos.

   Patrón: un objeto de estado (S), una función render() que dibuja según el
   paso, y eventos por delegación. Simple y suficiente para cinco pantallas.

   Lo visual sigue DESIGN-SYSTEM.md. Dos consecuencias que se ven en todo el
   archivo: los iconos son SVG de trazo de una sola familia (§7, nunca emojis) y
   los botones no llevan flechas pegadas al texto (§12).
   ============================================================ */

'use strict';

const S = {
  paso: 1,
  config: null,
  catalogo: null,
  seleccion: new Set(),
  expandidos: new Set(),
  filtro: { modo: 'manual', anioDesde: null, anioHasta: null, distribs: new Set(), texto: '' },
  opciones: { planilla: true, portadas: true, audio: false },
  job: null,
  resultado: null,
  error: '',
  errorCodigo: '',          // 'cuota' | 'clave' | '' — decide qué salida ofrecer
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

function num(n) {
  return (Number(n) || 0).toLocaleString('es-AR');
}

function pesoLegible(bytes) {
  const b = Number(bytes) || 0;
  if (b >= 1e9) return (b / 1e9).toFixed(2) + ' GB';
  if (b >= 1e6) return (b / 1e6).toFixed(1) + ' MB';
  if (b >= 1e3) return Math.round(b / 1e3) + ' KB';
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
    if (e && e.name === 'AbortError') throw new Error('La app tardó demasiado en responder.');
    throw new Error('Se perdió la conexión con la app.');
  } finally {
    clearTimeout(reloj);
  }
  let datos = {};
  try { datos = await r.json(); } catch (_) { /* respuesta sin cuerpo */ }
  if (!r.ok) {
    const e = new Error(datos.error || `Error ${r.status}`);
    e.codigo = datos.codigo_error || '';
    throw e;
  }
  return datos;
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
      throw new Error('Se perdió la conexión con la app. Puede que se haya cerrado la ventana del servidor.');
    }
    S.job = j;
    if (alAvanzar) alAvanzar(j);
    if (j.estado === 'listo') return j.resultado;
    if (j.estado === 'error') {
      const e = new Error(j.error || 'El proceso falló.');
      e.codigo = j.codigo_error || '';
      throw e;
    }
    if (j.estado === 'cancelado') throw new Error('CANCELADO');
  }
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
  const destino = enOscuro ? 'claro' : 'oscuro';
  btn.innerHTML = ico(enOscuro ? 'sol' : 'luna')
    + '<span class="sr">Cambiar a modo ' + destino + '</span>';
  btn.title = 'Cambiar a modo ' + destino;
}

/* ------------------------------------------------------------ stepper */

const PASOS = ['Pegá el link', 'Elegí productos', 'Elegí qué bajar', 'Descargá'];

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

  cont.innerHTML = PASOS.map((nombre, i) => {
    const n = i + 1;
    const actual = S.paso === n;
    const clase = actual ? 'activo' : (S.paso > n ? 'hecho' : 'inerte');
    const puede = !actual && pasoAlcanzable(n);
    const marca = S.paso > n ? ico('ok', 'ico-sm') : String(n);
    const cuerpo = `<span class="step-num">${marca}</span><span>${esc(nombre)}</span>`;
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
  } else if (f.modo === 'distribuidora' && f.distribs.size) {
    ps = ps.filter((p) => f.distribs.has(p.distribuidora));
  }

  if (f.texto.trim()) {
    const q = f.texto.trim().toLowerCase();
    ps = ps.filter((p) =>
      p.titulo.toLowerCase().includes(q) ||
      (p.upc || '').includes(q) ||
      (p.distribuidora || '').toLowerCase().includes(q) ||
      p.detalle.some((t) => t.titulo.toLowerCase().includes(q) || (t.isrc || '').toLowerCase().includes(q))
    );
  }
  return ps;
}

function seleccionados() {
  return productosFiltrados().filter((p) => S.seleccion.has(p.id));
}

/* ------------------------------------------------------------ render principal */

/* Redibujar reemplaza el DOM, así que el elemento que tenía el foco desaparece.
   Sin esto, alguien que navegue con teclado pierde su lugar cada vez que tilda
   un filtro. Guardamos cómo identificar al elemento enfocado y lo recuperamos. */

const ATRIBUTOS_FOCO = ['data-distrib', 'data-prod', 'data-opcion-check', 'data-modo', 'data-accion'];

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
  try {
    dibujar();
  } catch (e) {
    // Un error dibujando no puede dejar la pantalla en blanco sin explicación.
    mostrarFatal(e);
    return;
  }
  devolverFoco(foco);
}

function dibujar() {
  renderStepper();
  const v = $('#version');
  if (v) v.textContent = S.config ? 'v' + S.config.version : '';

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
  S.fatal = (e && e.message) || String(e || 'error desconocido');
  try {
    renderStepper();
    pantalla().innerHTML = vistaFatal();
  } catch (_) { /* no queda nada por hacer */ }
}

function vistaFatal() {
  return `<div class="card">
    <div class="card-head">
      <h2>La app se encontró con un problema</h2>
      <p>El motor sigue andando. Reiniciá la interfaz y, si se repite, el detalle
      de abajo es lo que sirve para reportarlo.</p>
    </div>
    ${alerta('danger', 'error', `<span class="mono">${esc(S.fatal)}</span>`)}
    <div class="row" style="margin-top:24px">
      <button class="btn btn-primary" data-accion="recargar">Reiniciar la interfaz</button>
    </div>
  </div>`;
}

/* Esqueleto con la forma del contenido que viene, en vez de un spinner
   centrado (§7). */
function vistaEsqueleto() {
  return `<div class="card">
    <div class="esqueleto" style="height:38px;width:60%"></div>
    <div class="esqueleto" style="height:16px;width:85%;margin-top:24px"></div>
    <div class="esqueleto" style="height:16px;width:70%"></div>
    <div class="esqueleto" style="height:40px;width:100%;margin-top:24px"></div>
  </div>`;
}

function alerta(tipo, icono, html) {
  const clase = tipo ? ` alerta-${tipo}` : '';
  return `<div class="alerta${clase}"><span class="alerta-icono">${ico(icono)}</span><div>${html}</div></div>`;
}

/* ------------------------------------------------------------ términos */

/** Los términos completos. Están acá y no en un archivo aparte para que la app
 *  los pueda mostrar sin internet y sin abrir el navegador. El texto es el mismo
 *  de TERMINOS.md, que es la copia canónica del repositorio. */
function textoTerminos() {
  return `
    <h4>Qué es esta herramienta</h4>
    <p>El Migrador de Catálogos es un programa gratuito y de código abierto para
    <strong>administrar catálogos musicales</strong>. Sirve para relevar el catálogo
    distribuido de un artista, recuperar sus códigos ISRC y UPC, reunir las portadas y
    armar la planilla de ingesta que pide una distribuidora nueva. Su finalidad es esa
    y no otra.</p>

    <h4>Quién puede usarla y para qué</h4>
    <p>Está pensada para titulares de derechos, sellos, distribuidoras, managers y
    artistas que trabajan sobre <strong>material propio, o sobre material que
    administran con autorización del titular</strong>.</p>
    <p>Al usarla declarás que tenés los derechos o la autorización necesaria sobre el
    contenido que procesás, y que vas a cumplir los términos de servicio de las
    plataformas que la herramienta consulta, entre ellas YouTube, Deezer, Apple y
    Tidal.</p>

    <h4>Qué no está permitido</h4>
    <p>Esta herramienta no avala ni habilita la piratería. Lo que sigue queda
    expresamente fuera de su finalidad y de esta licencia de uso.</p>
    <ul>
      <li>Descargar, copiar o redistribuir material sobre el que no tenés derechos.</li>
      <li>Usar el módulo de audio para obtener grabaciones ajenas, o para eludir
      medidas técnicas de protección.</li>
      <li>Revender, redistribuir o publicar el contenido obtenido sin autorización del
      titular.</li>
      <li>Compartir credenciales de cuentas de terceros, o usar una cuenta de
      streaming fuera de los términos del servicio que la provee.</li>
      <li>Eludir restricciones de las APIs que la herramienta consulta, o automatizar
      consultas por encima de los límites que esas APIs fijan.</li>
    </ul>
    <p>El módulo de audio es opcional, viene desactivado y requiere que conectes tu
    propia cuenta paga. Existe para que un titular de catálogo recupere sus propios
    másters cuando el archivo original no aparece. No reemplaza al máster entregado
    por el artista o el sello, y así está dicho en la documentación y en los reportes
    que genera.</p>

    <h4>Tus datos</h4>
    <p>La app corre entera en tu computadora. No hay cuentas, ni registro, ni un
    servidor del autor. La clave de la API queda guardada en tu carpeta personal, el
    catálogo relevado vive en memoria mientras la app está abierta, y no se envía nada
    a ningún destino que no sean las APIs públicas que la herramienta consulta para
    hacer su trabajo.</p>

    <h4>Sin garantía</h4>
    <p>El software se entrega tal cual, sin garantía de ningún tipo, expresa o
    implícita. Los datos provienen de fuentes públicas de terceros y pueden estar
    incompletos o desactualizados. <strong>La validación previa a la entrega es una
    ayuda, no un certificado</strong>, y no reemplaza la revisión de la distribuidora
    ni el criterio de quien entrega el material.</p>
    <p>El autor no responde por daños directos ni indirectos derivados del uso de la
    herramienta, ni por decisiones tomadas a partir de los datos que produce, ni por
    el uso que cada persona haga del material que procesa. La responsabilidad sobre el
    contenido es enteramente de quien lo usa.</p>

    <h4>Licencia y marcas</h4>
    <p>El código se distribuye bajo licencia MIT, cuyo texto completo está en el
    archivo LICENSE del repositorio. Las marcas y nombres de terceros mencionados
    pertenecen a sus titulares, y la herramienta no está afiliada ni patrocinada por
    ninguno de ellos.</p>

    <h4>Cambios</h4>
    <p>Estos términos pueden actualizarse en versiones siguientes. La versión vigente
    es la que acompaña a la copia que estás usando, y está en el repositorio público
    junto al código.</p>`;
}

function vistaTerminos(primeraVez) {
  if (primeraVez) {
    return `<div class="card doc fade">
        <h2>Términos de uso</h2>
      <p class="muted" style="margin-bottom:24px">Se leen una vez. Después no vuelven
      a aparecer, y quedan siempre disponibles desde el pie de la ventana.</p>
      ${textoTerminos()}
      <div class="row" style="margin-top:32px">
        <button class="btn btn-primary btn-lg" data-accion="aceptar-terminos">Acepto y quiero usar la herramienta</button>
      </div>
      <p class="small muted" style="margin-top:12px">Si no estás de acuerdo, cerrá la ventana.</p>
    </div>`;
  }

  return `<div class="card doc fade">
    <h2>Términos de uso</h2>
    ${textoTerminos()}
    <div class="row" style="margin-top:32px">
      <button class="btn btn-secondary" data-accion="cerrar-vista">Volver</button>
    </div>
  </div>`;
}

/* ------------------------------------------------------------ clave de YouTube */

function vistaClave() {
  const puedeVolver = !!(S.config && S.config.tiene_clave);

  return `
  <div class="card card-hero fade">
    <div class="card-head">
      <h1>${puedeVolver ? 'Usar tu propia clave de YouTube' : 'Conectá tu clave de YouTube'}</h1>
      <p>${puedeVolver
        ? 'La clave que cargues acá reemplaza a la que trae esta copia, y queda guardada sólo en tu computadora.'
        : 'Se pide una sola vez. Queda guardada en tu computadora y no se comparte con nadie.'}</p>
    </div>

    ${alerta('', 'llave', `
      <strong>Cómo conseguirla, en tres pasos.</strong>
      <ol>
        <li>Entrá a <a href="https://console.cloud.google.com/apis/credentials" target="_blank" rel="noopener noreferrer">Google Cloud Console, en Credenciales</a>, y creá un proyecto.</li>
        <li>Activá <em>YouTube Data API v3</em> en la biblioteca de APIs.</li>
        <li>Creá una <em>clave de API</em> y pegala acá abajo.</li>
      </ol>
      <p class="small" style="margin-top:8px">Es gratis. El cupo diario alcanza para unos 500 catálogos.</p>`)}

    <div class="field" style="margin-top:24px;max-width:480px">
      <label for="clave">Clave de la API de YouTube</label>
      <input class="input mono" id="clave" type="password" placeholder="AIza…"
             autocomplete="off" spellcheck="false" />
      <span class="hint">La verificamos con una consulta de prueba antes de guardarla.</span>
    </div>

    <div id="setup-error"></div>

    <div class="row" style="margin-top:24px">
      <button class="btn btn-primary" data-accion="guardar-clave">Verificar y guardar</button>
      ${puedeVolver ? '<button class="btn btn-secondary" data-accion="cerrar-vista">Cancelar</button>' : ''}
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
      <div class="row" style="margin-top:12px">
        <button class="btn btn-secondary btn-sm" data-accion="ver-clave">Cargar mi propia clave</button>
      </div>` : ''}`);
}

function avisoClaveIncluida() {
  if (!S.config || !S.config.clave_incluida) return '';
  return alerta('', 'info', `
    Esta copia trae una clave de YouTube ya configurada, así que no hace falta
    cargar ninguna. El cupo diario es compartido entre todos los que usen esta
    misma versión, y alcanza para unos 500 catálogos por día.
    <div class="row" style="margin-top:12px">
      <button class="btn btn-ghost btn-sm" data-accion="ver-clave">Prefiero usar mi propia clave</button>
    </div>`);
}

function vistaPaso1() {
  const corriendo = S.ocupado;
  return `
  <div class="card card-hero fade">
    <div class="card-head">
      <h1>¿Qué catálogo querés migrar?</h1>
      <p>Pegá el link del canal de YouTube del artista. Lo ideal es el
      <strong>canal Topic</strong>, el que se llama
      <span class="mono">«&lt;artista&gt; - Topic»</span>.</p>
    </div>

    <div class="field">
      <label for="url">Link del canal</label>
      <input class="input input-lg" id="url" type="url" spellcheck="false"
             placeholder="https://www.youtube.com/channel/UC…"
             ${corriendo ? 'disabled' : ''} />
      <span class="hint">Acepta la URL del canal o un <span class="mono">@handle</span>.</span>
    </div>

    ${alerta('', 'info', `
      <strong>Conviene pegar el canal Topic.</strong>
      Es el que YouTube genera solo con el catálogo distribuido, y el único que trae
      distribuidora, álbum, año y sello en cada descripción.
      <p style="margin-top:8px">Si pegás el canal oficial del artista igual funciona,
      porque la app busca su Topic y usa ese. Pero esa búsqueda gasta unas 100
      consultas del cupo diario, contra 20 que gasta relevar un catálogo entero, y en
      artistas con nombres parecidos puede elegir el Topic equivocado. Pegando el
      Topic directo eso no pasa.</p>`)}

    <label class="check" style="margin-top:24px">
      <input type="checkbox" id="con-codigos" checked ${corriendo ? 'disabled' : ''} />
      <span class="check-texto">
        <strong>Buscar códigos ISRC y UPC</strong>
        <span class="sub">Los busca en Deezer, sin clave ni costo. Tarda un poco más, pero son los códigos que la distribuidora nueva necesita.</span>
      </span>
    </label>

    ${avisoClaveIncluida()}

    ${bloqueError('No se pudo relevar.')}

    ${corriendo ? bloqueProgreso() : `
      <div class="row" style="margin-top:24px">
        <button class="btn btn-primary btn-lg" data-accion="relevar">Relevar catálogo</button>
      </div>`}
  </div>`;
}

function bloqueProgreso(conCancelar = true) {
  const j = S.job || { progreso: 0, mensaje: 'Preparando', log: [] };
  // La barra aparece cuando hay algo que medir. Antes de eso el spinner y el
  // log ya dicen que esta trabajando, y una barra que no mide nada es adorno.
  const conBarra = (j.progreso || 0) > 0;
  const log = (j.log || []).slice(-60).join('\n');
  return `
  <div style="margin-top:24px">
    <div class="row" style="margin-bottom:12px">
      <span class="spinner"></span>
      <strong id="progreso-mensaje">${esc(j.mensaje || 'Trabajando')}</strong>
      <span class="muted small mono">${j.progreso ? Math.round(j.progreso * 100) + '%' : ''}</span>
      ${conCancelar ? '<button class="btn btn-ghost btn-sm" style="margin-left:auto" data-accion="cancelar">Cancelar</button>' : ''}
    </div>
    ${conBarra ? `
      <div class="barra" role="progressbar" aria-valuemin="0" aria-valuemax="100"
           aria-valuenow="${Math.round(j.progreso * 100)}">
        <div class="barra-fill" style="transform:scaleX(${j.progreso.toFixed(3)})"></div>
      </div>` : ''}
    ${log ? `<div class="log" id="log">${esc(log)}</div>` : ''}
  </div>`;
}

/* ------------------------------------------------------------ paso 2 */

function avisoCanal() {
  const d = (S.catalogo && S.catalogo.diagnostico) || {};
  const partes = [];

  // Caso habitual y bueno: pegaron un canal común y la app encontró el Topic sola.
  if (d.via_topic && d.canal) {
    partes.push(alerta('ok', 'ok', `
      Pegaste <strong>${esc(d.canal_pedido || 'un canal común')}</strong>, que no es un
      canal Topic, así que busqué y relevé <strong>${esc(d.canal)}</strong>.
      <span class="small">El Topic es el que YouTube genera solo con el catálogo
      distribuido, y es el único que trae distribuidora, álbum, año y sello.</span>`));
  }

  if (d.descartados) {
    partes.push(alerta('', 'info', `
      Dejé afuera <strong>${num(d.descartados)} videos</strong> que no son
      lanzamientos, como videoclips, vivos y entrevistas. Sin la descripción
      auto-generada de YouTube no tienen álbum ni códigos, así que no sirven para una
      migración.`));
  }

  // Sólo si algo salió raro: el canal es Topic pero igual falta metadata.
  if (d.cobertura_metadata !== undefined && d.cobertura_metadata < 0.3) {
    const sug = d.topic_sugerido;
    partes.push(alerta('warn', 'alerta', `
      <strong>Este canal no trae la metadata del catálogo.</strong>
      No hay álbumes, sellos ni años, y los códigos casi no se pueden encontrar.
      ${sug ? `
        <div class="row" style="margin-top:12px">
          <button class="btn btn-secondary btn-sm" data-accion="usar-topic">
            Relevar «${esc(sug.titulo)}» en su lugar
          </button>
        </div>` : `
        <p class="small" style="margin-top:8px">
          Buscá «${esc(S.catalogo.artista)} - Topic» en YouTube y pegá ese link.
        </p>`}`));
  }

  return partes.join('');
}

/** Una métrica con su barra de acento arriba del número (§7). */
function kpi(label, valor, sub, negativo) {
  return `
    <div class="kpi">
      <div class="kpi-label">${esc(label)}</div>
      <div class="kpi-valor${negativo ? ' negativo' : ''}">${valor}${sub !== undefined && sub !== '' ? `<span class="kpi-sub"> / ${sub}</span>` : ''}</div>
    </div>`;
}

function vistaPaso2() {
  const c = S.catalogo;
  const ps = productosFiltrados();
  const sel = seleccionados();
  const r = c.resumen;

  return `
  <div class="fade">
    ${avisoCanal()}
    <div class="card">
      <div class="card-head row row-wrap">
        <div class="grow">
          <h1>${esc(c.artista)}</h1>
          <p>Catálogo relevado. Los datos salen de YouTube, Deezer y Apple.</p>
        </div>
        <button class="btn btn-ghost" data-accion="volver-1">Relevar otro artista</button>
      </div>

      <div class="kpis">
        ${kpi('Productos', num(r.products))}
        ${kpi('Tracks', num(r.tracks))}
        ${kpi('Con UPC', r.with_upc, r.products)}
        ${kpi('Con ISRC', r.with_isrc, r.tracks)}
        ${kpi('Reproducciones', num(r.views))}
      </div>
    </div>

    <div class="seccion">
      <div class="seccion-etiqueta">
        <span>Productos del catálogo</span>
        <span class="der">${ps.length} de ${c.productos.length}</span>
      </div>

      <div class="row row-wrap" style="margin-bottom:16px">
        <div class="segmented" role="group" aria-label="Modo de selección">
          <button class="${S.filtro.modo === 'manual' ? 'activo' : ''}" data-modo="manual">Uno por uno</button>
          <button class="${S.filtro.modo === 'fechas' ? 'activo' : ''}" data-modo="fechas">Por fecha</button>
          <button class="${S.filtro.modo === 'distribuidora' ? 'activo' : ''}" data-modo="distribuidora">Por distribuidora</button>
        </div>
        <div class="grow" style="min-width:200px;max-width:320px">
          <input class="input" id="buscar" type="search" placeholder="Título, ISRC o UPC"
                 aria-label="Buscar en el catálogo" value="${esc(S.filtro.texto)}" />
        </div>
      </div>

      ${panelFiltro()}

      ${ps.length === 0 ? `
        <div class="vacio">
          <h4>Ningún producto coincide con el filtro</h4>
          <p>Probá ampliar el rango de años o limpiar la búsqueda.</p>
          <button class="btn btn-primary" data-accion="limpiar-filtro">Limpiar el filtro</button>
        </div>` : tablaProductos(ps)}
    </div>

    <div class="barra-accion">
      <div class="resumen">
        <strong>${sel.length}</strong> de <strong>${ps.length}</strong> productos elegidos,
        ${sel.reduce((a, p) => a + p.tracks, 0)} tracks
      </div>
      <div class="acciones">
        <button class="btn btn-secondary" data-accion="sel-todo">Marcar todo</button>
        <button class="btn btn-secondary" data-accion="sel-nada">Desmarcar</button>
        <button class="btn btn-primary" data-accion="ir-3" ${sel.length ? '' : 'disabled'}>Continuar</button>
      </div>
    </div>
  </div>`;
}

function panelFiltro() {
  const f = S.filtro;
  const c = S.catalogo;

  if (f.modo === 'fechas') {
    const lo = c.filtros.anio_min, hi = c.filtros.anio_max;
    if (lo === null) {
      return alerta('warn', 'alerta', 'Ningún producto tiene año de lanzamiento declarado. Usá otro filtro.');
    }
    return `
    <div class="panel" style="margin-bottom:16px">
      <div class="row row-wrap">
        <div class="field" style="max-width:140px">
          <label for="anio-desde">Desde el año</label>
          <input class="input mono" id="anio-desde" type="number" min="${lo}" max="${hi}" value="${f.anioDesde ?? lo}" />
        </div>
        <div class="field" style="max-width:140px">
          <label for="anio-hasta">Hasta el año</label>
          <input class="input mono" id="anio-hasta" type="number" min="${lo}" max="${hi}" value="${f.anioHasta ?? hi}" />
        </div>
        <p class="small muted" style="align-self:flex-end;padding-bottom:10px">
          El catálogo va de ${lo} a ${hi}. Los productos sin año quedan afuera.
        </p>
      </div>
    </div>`;
  }

  if (f.modo === 'distribuidora') {
    const items = c.filtros.distribuidoras.map((d) => `
      <label class="check" style="margin-right:24px;margin-bottom:12px">
        <input type="checkbox" data-distrib="${esc(d.name)}" ${f.distribs.has(d.name) ? 'checked' : ''} />
        <span class="check-texto"><strong>${esc(d.name)}</strong><span class="sub">${d.count} producto${d.count === 1 ? '' : 's'}</span></span>
      </label>`).join('');
    return `
    <div class="panel" style="margin-bottom:16px">
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
    if (!p.upc) avisos.push('<span class="badge badge-danger">sin UPC</span>');
    if (p.con_isrc < p.tracks) avisos.push(`<span class="badge badge-danger">ISRC ${p.con_isrc} de ${p.tracks}</span>`);
    if (p.orden_estimado) avisos.push('<span class="badge badge-warn">orden estimado</span>');

    const detalle = abierto ? `
      <tr class="fila-detalle"><td colspan="7"><div class="detalle-inner">
        <table class="sub">
          <thead><tr><th>N</th><th>Track</th><th>ISRC</th><th>Duración</th><th class="td-num">Reproducciones</th></tr></thead>
          <tbody>${p.detalle.map((t) => `
            <tr>
              <td class="mono" data-col="N">${esc(t.n)}</td>
              <td data-col="Track">${esc(t.titulo)}</td>
              <td class="mono" data-col="ISRC">${t.isrc ? esc(t.isrc) : '<span class="muted">sin ISRC</span>'}</td>
              <td class="mono" data-col="Duración">${esc(t.duracion)}</td>
              <td class="td-num" data-col="Reproducciones">${num(t.views)}</td>
            </tr>`).join('')}
          </tbody>
        </table>
      </div></td></tr>` : '';

    return `
    <tr class="${elegido ? 'elegida' : ''}" data-fila="${esc(p.id)}">
      <td class="td-check">
        <label class="check"><input type="checkbox" data-prod="${esc(p.id)}" ${elegido ? 'checked' : ''} />
        <span class="sr">Elegir ${esc(p.titulo)}</span></label>
      </td>
      <td class="td-exp">
        <button class="btn-expandir" data-expandir="${esc(p.id)}" aria-expanded="${abierto}">
          ${ico('flecha', 'ico-sm')}<span class="sr">Ver los tracks de ${esc(p.titulo)}</span>
        </button>
      </td>
      <td data-col="Producto">
        <div class="celda-titulo">${esc(p.titulo)}</div>
        <div class="celda-sub">${p.tracks} track${p.tracks === 1 ? '' : 's'}${p.sello ? ', ' + esc(p.sello) : ''}</div>
      </td>
      <td data-col="Tipo"><span class="badge badge-accent">${esc(p.tipo)}</span></td>
      <td data-col="Año" class="nowrap mono">${esc(p.anio) || '<span class="muted">sin fecha</span>'}</td>
      <td data-col="UPC" class="mono">${p.upc ? esc(p.upc) : '<span class="muted">sin UPC</span>'}</td>
      <td data-col="Pendientes">${avisos.join(' ') || '<span class="badge badge-ok">completo</span>'}</td>
    </tr>${detalle}`;
  }).join('');

  return `
  <div class="tabla-wrap" id="tabla-wrap">
    <table class="tabla">
      <thead><tr>
        <th class="td-check"><label class="check"><input type="checkbox" id="check-todos"
          ${todos ? 'checked' : ''} ${!todos && algunos ? 'data-indeterminado="1"' : ''} />
          <span class="sr">Marcar todos los productos del filtro</span></label></th>
        <th class="td-exp"></th>
        <th>Producto</th><th>Tipo</th><th>Año</th><th>UPC</th><th>Pendientes</th>
      </tr></thead>
      <tbody>${filas}</tbody>
    </table>
  </div>`;
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
        <h1>¿Qué querés descargar?</h1>
        <p>${sel.length} producto${sel.length === 1 ? '' : 's'} elegido${sel.length === 1 ? '' : 's'},
           ${sel.reduce((a, p) => a + p.tracks, 0)} tracks.</p>
      </div>

      <div class="seccion-etiqueta"><span>Contenido del paquete</span></div>

      <div class="opciones">
        ${opcion('planilla', 'planilla', o.planilla, false, 'Planilla y validación',
          'Excel con los datos y códigos, hoja de ingesta en CSV para la distribuidora, y el informe de validación previa.')}

        ${opcion('portadas', 'imagen', o.portadas, false, 'Portadas',
          'La resolución más alta que tenga Apple Music. Te avisamos si queda por debajo del mínimo de ingesta.')}

        ${audioOn ? opcion('audio', 'musica', o.audio, !puedeAudio, 'Audios', puedeAudio
          ? 'FLAC lossless con tu propia cuenta de Tidal. La referencia de YouTube casi siempre falla, porque YouTube la bloquea.'
          : faltaParaAudio()) : ''}
      </div>

      ${o.audio && audioOn ? bloqueTidal(tidalOk) : ''}

      ${S.error ? alerta('danger', 'error', esc(S.error)) : ''}
    </div>

    <div class="barra-accion">
      <div class="resumen">Se va a generar un ZIP con una carpeta por producto.</div>
      <div class="acciones">
        <button class="btn btn-secondary" data-accion="volver-2">Volver</button>
        <button class="btn btn-primary" data-accion="generar"
          ${(o.planilla || o.portadas || o.audio) ? '' : 'disabled'}>Generar paquete</button>
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
    return 'Falta <strong>ffmpeg</strong> en esta computadora. Se instala una sola vez, '
         + 'abriendo PowerShell y pegando <code>winget install --id Gyan.FFmpeg -e</code>. '
         + 'Después cerrá y volvé a abrir la app.';
  }
  if (!e.tiddl && !e.yt_dlp) {
    return 'Esta versión de la app no incluye el módulo de audio. Necesitás la versión completa.';
  }
  return 'No disponible en esta computadora. Abrí la app con <code>--diagnostico</code> para ver qué falta.';
}

function bloqueTidal(conectada) {
  if (conectada) {
    return `<div style="margin-top:24px">${alerta('ok', 'ok', `
      <strong>Cuenta de Tidal conectada.</strong> El audio va a bajar en FLAC lossless, apto para entrega.
      <div class="row" style="margin-top:12px">
        <button class="btn btn-ghost btn-sm" data-accion="tidal-salir">Desconectar</button>
      </div>`)}</div>`;
  }
  if (S.tidal) {
    return `<div style="margin-top:24px">${alerta('', 'enlace', `
      <strong>Conectá tu cuenta en el sitio de Tidal.</strong><br>
      Abrí <a href="${esc(S.tidal.url)}" target="_blank" rel="noopener noreferrer">${esc(S.tidal.url)}</a>
      ${S.tidal.codigo ? `y usá el código <span class="mono"><strong>${esc(S.tidal.codigo)}</strong></span>` : ''}.
      <div class="row" style="margin-top:12px">
        <button class="btn btn-secondary btn-sm" data-accion="tidal-confirmar">Ya confirmé</button>
        <button class="btn btn-ghost btn-sm" data-accion="tidal-salir">Cancelar</button>
      </div>
      ${S.tidal.aviso ? `<p class="small" style="margin-top:8px">${esc(S.tidal.aviso)}</p>` : ''}`)}</div>`;
  }
  return `<div style="margin-top:24px">${alerta('warn', 'alerta', `
    <strong>Conectá Tidal para poder bajar el audio.</strong>
    Sin cuenta conectada sólo se puede intentar la referencia de YouTube, y hoy falla
    en la mayoría de los casos. YouTube pide un token de origen que sólo se obtiene
    desde un navegador con sesión, y buena parte del audio de música está protegido
    con DRM. Cuando falla, el reporte te dice el motivo track por track.
    <div class="row" style="margin-top:12px">
      <button class="btn btn-secondary btn-sm" data-accion="tidal-iniciar">Conectar mi cuenta de Tidal</button>
    </div>
    <p class="small" style="margin-top:8px">Tu contraseña nunca pasa por esta app, porque te autenticás en el sitio de Tidal.</p>`)}</div>`;
}

/* ------------------------------------------------------------ paso 4 */

function vistaPaso4() {
  if (S.ocupado) {
    return `<div class="card fade">
      <div class="card-head">
        <h1>Armando el paquete</h1>
        <p>Podés dejar la ventana abierta. Te avisamos cuando esté.</p>
      </div>
      ${bloqueProgreso()}
    </div>`;
  }

  if (S.error) {
    return `<div class="card fade">
      <div class="card-head"><h1>No se pudo generar</h1></div>
      ${alerta('danger', 'error', esc(S.error))}
      <div class="row" style="margin-top:24px">
        <button class="btn btn-secondary" data-accion="volver-3">Volver</button>
        <button class="btn btn-primary" data-accion="generar">Reintentar</button>
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
        <h1>Tu paquete está listo</h1>
        <p>${r.productos} producto${r.productos === 1 ? '' : 's'}, ${pesoLegible(r.bytes)}.</p>
      </div>

      <div class="kpis" style="margin-bottom:24px">
        ${kpi('Productos', num(r.productos))}
        ${kpi('Portadas', r.portadas, r.productos)}
        ${kpi('Errores', v.resumen.errores, '', v.resumen.errores > 0)}
        ${kpi('Avisos', v.resumen.avisos)}
      </div>

      <a class="btn btn-primary btn-lg" href="${esc(r.descarga)}" download>
        ${ico('descargar')} Descargar ${esc(r.archivo)}
      </a>
    </div>

    ${panelValidacion(v)}

    <div class="barra-accion">
      <div class="resumen">El ZIP queda disponible mientras la app esté abierta.</div>
      <div class="acciones">
        <button class="btn btn-secondary" data-accion="volver-2">Elegir otros productos</button>
        <button class="btn btn-ghost" data-accion="volver-1">Relevar otro artista</button>
      </div>
    </div>
  </div>`;
}

function panelValidacion(v) {
  if (v.apto && !v.resumen.avisos) {
    return alerta('ok', 'ok', '<strong>Validación sin observaciones.</strong> No encontré nada de lo que las distribuidoras suelen rechazar.');
  }

  const errores = v.hallazgos.filter((h) => h.nivel === 'error');
  const avisos = v.hallazgos.filter((h) => h.nivel === 'aviso');

  const cabecera = errores.length
    ? alerta('danger', 'error', `<strong>${errores.length} error${errores.length === 1 ? '' : 'es'} que suelen causar rechazo.</strong>
        Conviene corregirlos antes de entregar. El detalle también está en
        <span class="mono">_Validacion pre-entrega.txt</span>, dentro del ZIP.`)
    : alerta('ok', 'ok', `<strong>Sin errores de rechazo.</strong> Hay ${avisos.length} aviso${avisos.length === 1 ? '' : 's'} para revisar.`);

  const grupo = (lista, titulo, abierto) => !lista.length ? '' : `
    <details class="acordeon" ${abierto ? 'open' : ''}>
      <summary>${ico('flecha', 'ico-sm')}${titulo}, ${lista.length} en total</summary>
      <div class="acordeon-body">
        <div class="tabla-wrap" style="max-height:340px">
          <table class="tabla">
            <thead><tr><th>Producto</th><th>Track</th><th>Qué pasa</th></tr></thead>
            <tbody>${lista.map((h) => `
              <tr>
                <td data-col="Producto">${esc(h.producto)}</td>
                <td data-col="Track">${h.track ? esc(h.track) : '<span class="muted">todo el producto</span>'}</td>
                <td data-col="Qué pasa">${esc(h.mensaje)}</td>
              </tr>`).join('')}
            </tbody>
          </table>
        </div>
      </div>
    </details>`;

  return `<div class="seccion">
    <div class="seccion-etiqueta">
      <span>Validación previa</span>
      <span class="der">${v.resumen.errores} error${v.resumen.errores === 1 ? '' : 'es'} · ${v.resumen.avisos} aviso${v.resumen.avisos === 1 ? '' : 's'}</span>
    </div>
    ${cabecera}
    <div style="margin-top:16px">
      ${grupo(errores, 'Errores', true)}
      ${grupo(avisos, 'Avisos', false)}
    </div>
  </div>`;
}

/* ------------------------------------------------------------ Tidal */

/** Traduce los códigos crudos a algo que se entienda. */
function mensajeTidal(crudo) {
  const c = String(crudo || '').toLowerCase();
  if (c.includes('501') || c.includes('unsupported method')) {
    return 'Se cortó la comunicación con la app. Probá de nuevo.';
  }
  if (c.includes('expired')) {
    return 'El código venció. Cerrá esto y volvé a conectar la cuenta.';
  }
  if (c.includes('authorization_pending') || c.includes('pendiente') || c.includes('slow_down')) {
    return 'Todavía no me llegó la confirmación de Tidal.';
  }
  if (c.includes('invalid') || c.includes('token')) {
    return 'Tidal rechazó la conexión. Volvé a intentar desde el principio.';
  }
  if (c.includes('failed to fetch') || c.includes('networkerror') || c.includes('conexión')) {
    return 'No pude hablar con Tidal. Revisá que haya conexión a internet.';
  }
  return crudo || 'No se pudo conectar.';
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
      if (manual) {
        S.tidal.aviso = 'Todavía no confirmaste en Tidal. Completá el acceso en la otra pestaña, '
                      + 'y en cuanto lo hagas se conecta solo, sin volver a apretar.';
      }
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

  recargar() { window.location.reload(); },

  'ver-terminos'() { S.vista = 'terminos'; render(); window.scrollTo(0, 0); },
  'ver-clave'() { S.vista = 'clave'; render(); window.scrollTo(0, 0); },
  'cerrar-vista'() { S.vista = null; render(); },

  async 'aceptar-terminos'() {
    await api('/api/terminos', { aceptar: true });
    S.config = await api('/api/config');
    render();
    window.scrollTo(0, 0);
  },

  'limpiar-filtro'() {
    S.filtro.texto = '';
    S.filtro.modo = 'manual';
    render();
  },

  async 'guardar-clave'() {
    const campo = $('#clave');
    const caja = $('#setup-error');
    const clave = campo ? campo.value.trim() : '';
    if (!clave) {
      caja.innerHTML = alerta('danger', 'error', 'Pegá la clave antes de guardar.');
      return;
    }
    caja.innerHTML = `<div class="row" style="margin-top:16px"><span class="spinner"></span><span>Verificando</span></div>`;
    try {
      await api('/api/clave', { clave }, 45000);
      S.config = await api('/api/config');
      S.vista = null;
      render();
    } catch (e) {
      caja.innerHTML = alerta('danger', 'error', `<strong>No se pudo guardar.</strong><br>${esc(e.message)}`);
    }
  },

  async relevar() {
    const campo = $('#url');
    const url = campo ? campo.value.trim() : '';
    if (!url) { S.error = 'Pegá el link del canal.'; render(); return; }
    S.error = ''; S.errorCodigo = ''; S.ocupado = true; S.job = null; render();
    try {
      const conCodigos = $('#con-codigos') ? $('#con-codigos').checked : true;
      const { job } = await api('/api/relevar', { url, con_codigos: conCodigos });
      const cat = await esperarJob(job, () => actualizarProgreso());
      adoptarCatalogo(cat);          // arranca con todo elegido
      S.ocupado = false;
      render();
    } catch (e) {
      S.ocupado = false;
      S.error = e.message === 'CANCELADO' ? '' : e.message;
      S.errorCodigo = e.codigo || '';
      render();
    }
  },

  async cancelar() {
    if (S.job) { try { await api(`/api/job/${S.job.id}/cancelar`, {}); } catch (_) {} }
  },

  async 'usar-topic'() {
    const sug = ((S.catalogo && S.catalogo.diagnostico) || {}).topic_sugerido;
    if (!sug) return;
    // Relevamos el Topic con el mismo flujo del paso 1, sin que tenga que ir a
    // buscar el link a mano.
    S.paso = 1; S.error = ''; S.errorCodigo = ''; S.ocupado = true; S.job = null; render();
    try {
      const { job } = await api('/api/relevar', { url: sug.url, con_codigos: true });
      adoptarCatalogo(await esperarJob(job, () => actualizarProgreso()));
      S.ocupado = false; render();
    } catch (e) {
      S.ocupado = false;
      S.error = e.message === 'CANCELADO' ? '' : e.message;
      S.errorCodigo = e.codigo || '';
      render();
    }
  },

  'volver-1'() { S.paso = 1; S.error = ''; S.errorCodigo = ''; S.resultado = null; render(); },
  'volver-2'() { S.paso = 2; S.error = ''; S.errorCodigo = ''; render(); },
  'volver-3'() { S.paso = 3; S.error = ''; S.errorCodigo = ''; render(); },
  'ir-3'() { S.paso = 3; S.error = ''; S.errorCodigo = ''; render(); },

  'sel-todo'() { productosFiltrados().forEach((p) => S.seleccion.add(p.id)); render(); },
  'sel-nada'() { productosFiltrados().forEach((p) => S.seleccion.delete(p.id)); render(); },

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
    S.tidal.aviso = 'Consultando';
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
    if (!ids.length) { S.error = 'No hay productos elegidos.'; render(); return; }
    S.error = ''; S.errorCodigo = ''; S.resultado = null; S.ocupado = true; S.paso = 4; S.job = null; render();
    try {
      const { job } = await api('/api/preparar', {
        ids,
        planilla: S.opciones.planilla,
        portadas: S.opciones.portadas,
        audio: S.opciones.audio,
      });
      S.resultado = await esperarJob(job, () => actualizarProgreso());
      S.ocupado = false; render();
    } catch (e) {
      S.ocupado = false;
      S.error = e.message === 'CANCELADO' ? 'Cancelado.' : e.message;
      S.errorCodigo = e.codigo || '';
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
  if (msj) msj.textContent = j.mensaje || 'Trabajando';
  const log = $('#log');
  if (log) {
    const pegadoAbajo = log.scrollHeight - log.scrollTop - log.clientHeight < 30;
    log.textContent = (j.log || []).slice(-60).join('\n');
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
    if (fn) { ev.preventDefault(); seguro(fn); }
    return;
  }

  const irPaso = ev.target.closest('[data-ir-paso]');
  if (irPaso) {
    const n = parseInt(irPaso.dataset.irPaso, 10);
    if (pasoAlcanzable(n)) { S.paso = n; S.error = ''; seguro(render); }
    return;
  }

  const modo = ev.target.closest('[data-modo]');
  if (modo) { S.filtro.modo = modo.dataset.modo; seguro(render); return; }

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

  if (t.dataset.prod) {
    if (t.checked) S.seleccion.add(t.dataset.prod); else S.seleccion.delete(t.dataset.prod);
    // Actualización puntual: redibujar la tabla entera en cada clic se siente lento.
    const fila = filaDe(t.dataset.prod);
    if (fila) fila.classList.toggle('elegida', t.checked);
    seguro(actualizarResumenSeleccion);
    return;
  }

  if (t.id === 'check-todos') {
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
  if (ev.target.id === 'buscar') {
    S.filtro.texto = ev.target.value;
    clearTimeout(document.__buscarTimer);
    // Debounce: filtrar en cada tecla sobre un catálogo grande se nota. El foco y
    // el cursor los recupera render() por su cuenta.
    document.__buscarTimer = setTimeout(() => seguro(render), 180);
  }
});

document.addEventListener('keydown', (ev) => {
  if (ev.key !== 'Enter') return;
  if (ev.target.id === 'url') { ev.preventDefault(); seguro(ACCIONES.relevar); }
  if (ev.target.id === 'clave') { ev.preventDefault(); seguro(ACCIONES['guardar-clave']); }
});

/* Cualquier error que se escape queda a la vista, en vez de dejar una pantalla
   congelada sin explicación. */
window.addEventListener('error', (ev) => { if (!S.fatal) mostrarFatal(ev.error || ev.message); });
window.addEventListener('unhandledrejection', (ev) => { if (!S.fatal) mostrarFatal(ev.reason); });

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
    caja.innerHTML = `<strong>${sel.length}</strong> de <strong>${ps.length}</strong> productos elegidos, `
                   + `${sel.reduce((a, p) => a + p.tracks, 0)} tracks`;
  }
  const btn = document.querySelector('[data-accion="ir-3"]');
  if (btn) btn.disabled = sel.length === 0;
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
  S.seleccion = new Set(cat.productos.map((p) => p.id));
  S.expandidos = new Set();
  S.filtro = {
    modo: 'manual',
    anioDesde: cat.filtros.anio_min,
    anioHasta: cat.filtros.anio_max,
    distribs: new Set(cat.filtros.distribuidoras.map((d) => d.name)),
    texto: '',
  };
  S.paso = 2;
}

(async function iniciar() {
  aplicarTema(temaGuardado());
  render();
  try {
    S.config = await api('/api/config', undefined, 15000);
  } catch (e) {
    pantalla().innerHTML = alerta('danger', 'error',
      '<strong>No pude conectar con el motor de la app.</strong><br>Cerrala y volvé a abrirla.');
    return;
  }

  if (S.config.catalogo_cargado) {
    try { adoptarCatalogo(await api('/api/catalogo')); } catch (_) { /* seguimos en el paso 1 */ }
  }

  render();
  const i = $('#url');
  if (i) i.focus();
})();
