// Tests de la interfaz, con `node --test`, sin navegador.
//
// `esc()` es la única barrera entre los títulos que vienen de YouTube, Deezer y
// Apple y el `innerHTML`; la CSP no la reemplaza. Hasta acá no la probaba nada.

import assert from 'node:assert/strict';
import fs from 'node:fs';
import { test } from 'node:test';

import { cargar } from './entorno.mjs';

const { ctx, ev, pantalla, poner, nodos, backend } = cargar();

const CONFIG = { version: '0', terminos_aceptados: true, tiene_clave: true, idiomas: ['es', 'en'], entorno: {} };

test('esc escapa todo lo que abre HTML o atributos', () => {
  assert.equal(ev(`esc('<img src=x onerror=alert(1)>')`), '&lt;img src=x onerror=alert(1)&gt;');
  assert.equal(ev(`esc('a & b')`), 'a &amp; b');
  assert.equal(ev(`esc('"comillas" y \\'simples\\'')`), '&quot;comillas&quot; y &#39;simples&#39;');
});

test('esc no se rompe con lo que no es texto', () => {
  assert.equal(ev('esc(null)'), '');
  assert.equal(ev('esc(undefined)'), '');
  assert.equal(ev('esc(0)'), '0');
});

test('un título hostil llega escapado a la pantalla', () => {
  ev(`
    S.config = { version: '0', terminos_aceptados: true, tiene_clave: true, idiomas: ['es', 'en'] };
    S.catalogo = {
      artista: '<script>alert(1)</script>',
      productos: [{ id: 'p1', titulo: '<img src=x onerror=alert(1)>', tipo: 'single', anio: 2020,
                    upc: '', sello: '', distribuidora: 'X', tracks: 1, views: 0, orden_estimado: false,
                    con_isrc: 0, detalle: [] }],
      resumen: { products: 1, tracks: 1, views: 0, with_upc: 0, with_isrc: 0 },
      filtros: { distribuidoras: [], anio_min: 2020, anio_max: 2020 },
      diagnostico: {},
    };
    S.seleccion = new Set(['p1']);
    S.paso = 2;
    render();
  `);
  const html = pantalla.innerHTML;
  assert.ok(html.includes('&lt;img src=x'), 'el título tenía que aparecer escapado');
  assert.ok(!html.includes('<img src=x'), 'el título no puede entrar como HTML');
  assert.ok(!html.includes('<script>alert'), 'el artista no puede entrar como HTML');
});

test('los números siguen al idioma', () => {
  ev(`ponerIdioma('es')`);
  assert.equal(ev('num(7000)'), '7.000');
  assert.equal(ev('pesoLegible(1234567)'), '1,2 MB');
  ev(`ponerIdioma('en')`);
  assert.equal(ev('num(7000)'), '7,000');
  assert.equal(ev('pesoLegible(1234567)'), '1.2 MB');
  ev(`ponerIdioma('es')`);
});

test('las cantidades concuerdan en singular y plural', () => {
  assert.equal(ev(`cuenta('comun.n_productos', 1)`), '1 producto');
  assert.equal(ev(`cuenta('comun.n_productos', 3)`), '3 productos');
  assert.equal(ev(`cuenta('comun.n_tracks', 1, '<b>1</b>')`), '<b>1</b> track');
});

test('cada código de hallazgo tiene su título en los dos idiomas', () => {
  const codigos = ev('CODIGOS_HALLAZGO');
  for (const idioma of ['es', 'en']) {
    ev(`ponerIdioma('${idioma}')`);
    for (const c of codigos) {
      const titulo = ev(`tituloHallazgo('${c}', '')`);
      assert.ok(titulo && titulo !== 'hallazgo.' + c, `${idioma}: falta el título de ${c}`);
    }
  }
  ev(`ponerIdioma('es')`);
});

test('el filtro por años deja afuera lo que no tiene año', () => {
  const ids = ev(`
    S.catalogo = { productos: [
      { id: 'a', titulo: 'Uno', anio: 2020, upc: '', distribuidora: 'X', detalle: [] },
      { id: 'b', titulo: 'Dos', anio: '', upc: '', distribuidora: 'X', detalle: [] },
      { id: 'c', titulo: 'Tres', anio: 2010, upc: '', distribuidora: 'X', detalle: [] },
    ] };
    S.filtro.modo = 'fechas'; S.filtro.anioDesde = 2015; S.filtro.anioHasta = 2025;
    productosFiltrados().map((p) => p.id);
  `);
  assert.deepEqual([...ids], ['a']);
  ev(`S.filtro.modo = 'manual'`);
});

test('el link pegado sigue en el campo después de un error', () => {
  ev(`S.config = ${JSON.stringify(CONFIG)}; S.catalogo = null; S.paso = 1; S.vista = null;
      S.url = 'https://www.youtube.com/@alguien"x'; S.error = 'Se agotó el cupo'; S.errorCodigo = 'cuota';
      render();`);
  assert.ok(pantalla.innerHTML.includes('value="https://www.youtube.com/@alguien&quot;x"'),
    'el campo tiene que volver con lo que se pegó, escapado');
  ev(`S.url = ''; S.error = ''; S.errorCodigo = '';`);
});

test('con la clave propia cargada, el error de cupo se va', async () => {
  poner('#clave', { value: 'AIzaClaveDePrueba' });
  poner('#setup-error');
  backend({ '/api/clave': { ok: true }, '/api/config': CONFIG });
  ev(`S.vista = 'clave'; S.error = 'Se agotó el cupo'; S.errorCodigo = 'cuota';`);
  await ev(`ACCIONES['guardar-clave']()`);
  assert.equal(ev('S.error'), '');
  assert.equal(ev('S.vista'), null);
  nodos.delete('#clave');
  nodos.delete('#setup-error');
});

test('un error que no es de cupo sigue a la vista después de cargar la clave', async () => {
  poner('#clave', { value: 'AIzaClaveDePrueba' });
  poner('#setup-error');
  backend({ '/api/clave': { ok: true }, '/api/config': CONFIG });
  ev(`S.vista = 'clave'; S.error = 'Ese canal no existe'; S.errorCodigo = 'canal';`);
  await ev(`ACCIONES['guardar-clave']()`);
  assert.equal(ev('S.error'), 'Ese canal no existe');
  ev(`S.error = ''; S.errorCodigo = '';`);
  nodos.delete('#clave');
  nodos.delete('#setup-error');
});

test('cancelar el armado vuelve al paso 3 con un aviso, no con un error, y limpia el pie', async () => {
  ev(`S.config = ${JSON.stringify({ ...CONFIG, audio_habilitado: false })};
      S.catalogo = { catalogo_id: 'c1', artista: 'A', productos: [
        { id: 'p1', titulo: 'Uno', tipo: 'single', anio: 2020, upc: '', distribuidora: 'X', tracks: 1, detalle: [] }],
        resumen: {}, filtros: { distribuidoras: [] }, diagnostico: {} };
      S.seleccion = new Set(['p1']); S.paso = 3; S.vista = null;`);
  nodos.get('#pie-estado').textContent = 'Portada 3 de 4';
  backend({ '/api/preparar': { job: { id: 'j1' } }, '/api/job/j1': { estado: 'cancelado', log: [] } });
  await ev('ACCIONES.generar()');
  assert.equal(ev('S.error'), '', 'cancelar no es un error');
  assert.equal(ev('S.paso'), 3);
  assert.ok(ev('S.aviso'), 'tiene que decir que se canceló');
  assert.ok(!pantalla.innerHTML.includes('alerta-danger'), 'sin rojo');
  assert.equal(nodos.get('#pie-estado').textContent, '', 'el pie no puede seguir con el paso de un trabajo cancelado');
  ev(`S.aviso = ''; S.paso = 1;`);
});

test('la clave se pega a la vista, y «Verificando» usa un indicador que existe', () => {
  ev(`S.vista = 'clave'; render();`);
  assert.ok(pantalla.innerHTML.includes('id="clave" type="text"'));
  ev(`S.vista = null;`);
  const fuente = ev('ACCIONES["guardar-clave"].toString()');
  const css = fs.readFileSync(new URL('../../app/web/app.css', import.meta.url), 'utf8');
  for (const [, clase] of fuente.matchAll(/class="([a-z-]+)"/g)) {
    assert.ok(css.includes('.' + clase), `la clase .${clase} no existe en app.css`);
  }
});

test('un error se anuncia, y una alerta informativa no', () => {
  assert.ok(ev(`alerta('danger', 'error', 'x')`).includes('role="alert"'));
  assert.ok(!ev(`alerta('', 'info', 'x')`).includes('role='));
  assert.ok(ev(`alerta('', 'info', 'x', 'status')`).includes('role="status"'));
});

test('el foco no se pierde en el chevron ni en el stepper', () => {
  const attrs = ev('ATRIBUTOS_FOCO');
  assert.ok(attrs.includes('data-expandir'));
  assert.ok(attrs.includes('data-ir-paso'));
});

test('en un cambio de vista el foco va al título nuevo', () => {
  const titulo = { atributos: {}, enfocado: false,
    setAttribute(k, v) { this.atributos[k] = v; }, focus() { this.enfocado = true; } };
  const antes = pantalla.querySelector;
  pantalla.querySelector = (s) => (s === 'h1' ? titulo : null);
  ev(`S.config = ${JSON.stringify(CONFIG)}; S.catalogo = null; S.paso = 1; S.vista = null; S.entrando = true; render();`);
  assert.ok(titulo.enfocado, 'el título tenía que recibir el foco');
  assert.equal(titulo.atributos.tabindex, '-1');
  titulo.enfocado = false;
  ev('render()');
  assert.ok(!titulo.enfocado, 'un redibujado sin cambio de vista no mueve el foco');
  pantalla.querySelector = antes;
});

function catalogoDeTres() {
  ev(`S.config = ${JSON.stringify(CONFIG)}; S.vista = null; S.paso = 2;
      adoptarCatalogo({ catalogo_id: 'c', artista: 'A', diagnostico: {},
        resumen: { products: 3, tracks: 4, views: 0, with_upc: 2, with_isrc: 3 },
        filtros: { anio_min: 2020, anio_max: 2022, distribuidoras: [{ name: 'X', count: 2 }, { name: 'Y', count: 1 }] },
        productos: [
          { id: 'a', titulo: 'Completo', tipo: 'single', anio: 2020, upc: '1', distribuidora: 'X', tracks: 1, con_isrc: 1, detalle: [] },
          { id: 'b', titulo: 'Sin UPC', tipo: 'single', anio: 2021, upc: '', distribuidora: 'X', tracks: 1, con_isrc: 1, detalle: [] },
          { id: 'c', titulo: 'Sin ISRC', tipo: 'ep', anio: 2022, upc: '2', distribuidora: 'Y', tracks: 2, con_isrc: 1, detalle: [] },
        ] });`);
}

test('destildar todas las distribuidoras no muestra nada, y lo dice', () => {
  catalogoDeTres();
  ev(`S.filtro.modo = 'distribuidora'; S.filtro.distribs = new Set();`);
  assert.equal(ev('productosFiltrados().length'), 0);
  assert.equal(ev('motivoVacio().motivo'), 'sin_distrib');
  ev(`S.filtro.distribs = new Set(['Y'])`);
  assert.deepEqual([...ev('productosFiltrados().map((p) => p.id)')], ['c']);
});

test('el filtro de faltantes deja sólo lo que tiene algo que completar', () => {
  catalogoDeTres();
  ev(`S.filtro.faltantes = true`);
  assert.deepEqual([...ev('productosFiltrados().map((p) => p.id)')], ['b', 'c']);
  // Si el único producto está completo, la tabla vacía es una buena noticia.
  ev(`S.catalogo.productos = S.catalogo.productos.slice(0, 1)`);
  assert.equal(ev('productosFiltrados().length'), 0);
  assert.equal(ev('motivoVacio().motivo'), 'nada_falta');
  // Con una búsqueda encima, ya no se sabe si falta o no: es el vacío común.
  ev(`S.filtro.texto = 'zzz'`);
  assert.equal(ev('motivoVacio().motivo'), 'filtro');
  ev(`S.filtro.texto = ''; S.filtro.faltantes = false`);
});

test('el paquete lleva todo lo tildado, aunque el filtro lo esconda, y se dice', () => {
  // Antes llevaba sólo lo elegido que se veía: buscar un título para chequearlo
  // y apretar «Continuar» armaba un paquete con ese único producto.
  catalogoDeTres();
  assert.equal(ev('elegidosOcultos()'), 0);
  ev(`S.filtro.texto = 'Completo'`);
  assert.equal(ev('productosFiltrados().length'), 1);
  assert.deepEqual([...ev('seleccionados().map((p) => p.id)')], ['a', 'b', 'c'], 'van los tres');
  assert.equal(ev('elegidosOcultos()'), 2);
  const html = ev('resumenElegidos(seleccionados())');
  assert.ok(html.includes('<strong>3</strong> de <strong>3</strong>'), 'el total es el del catálogo: ' + html);
  assert.ok(html.includes('2 elegidos no se ven por el filtro, pero van en el paquete'), html);
  assert.ok(html.includes('data-accion="limpiar-filtro"'), 'tiene que ofrecer la salida');
  ev(`ACCIONES['limpiar-filtro']()`);
  assert.equal(ev('elegidosOcultos()'), 0);
});

test('con un filtro puesto, marcar y desmarcar dicen que actúan sobre lo que se ve', () => {
  catalogoDeTres();
  assert.ok(ev('botonesDeMarcar(productosFiltrados())').includes('Desmarcar todos'));
  ev(`S.filtro.texto = 'Sin'`);
  const botones = ev('botonesDeMarcar(productosFiltrados())');
  assert.ok(botones.includes('Desmarcar los que se ven'), botones);
  ev(`ACCIONES['sel-nada']()`);
  assert.deepEqual([...ev('seleccionados().map((p) => p.id)')], ['a'], 'el que no se ve sigue elegido');
  ev(`S.filtro.texto = ''`);
});

test('marcar o desmarcar en lote se puede deshacer', () => {
  catalogoDeTres();
  ev(`S.seleccion = new Set(['a', 'c'])`);
  assert.ok(!ev('resumenElegidos(seleccionados())').includes('deshacer-seleccion'), 'sin acción en lote no hay nada que deshacer');
  ev(`ACCIONES['sel-nada']()`);
  assert.equal(ev('seleccionados().length'), 0);
  assert.ok(ev('resumenElegidos(seleccionados())').includes('data-accion="deshacer-seleccion"'));
  ev(`ACCIONES['deshacer-seleccion']()`);
  assert.deepEqual([...ev('seleccionados().map((p) => p.id)')], ['a', 'c'], 'vuelve lo elegido a mano, no todo');
  assert.ok(!ev('resumenElegidos(seleccionados())').includes('deshacer-seleccion'), 'y el botón se va');
});

test('volver al paso 1 no tira el paquete; otro catálogo sí', () => {
  catalogoDeTres();
  ev(`S.resultado = { archivo: 'x.zip', bytes: 1 }; S.paso = 4`);
  ev(`ACCIONES['volver-1']()`);
  assert.equal(ev('pasoAlcanzable(4)'), true, 'el paso 4 sigue a mano');
  catalogoDeTres();
  assert.equal(ev('S.resultado'), null, 'el paquete era del catálogo anterior');
});

test('las cabeceras ordenan: ascendente, descendente y de vuelta al orden original', () => {
  catalogoDeTres();
  const ids = () => [...ev('productosFiltrados().map((p) => p.id)')];
  assert.deepEqual(ids(), ['a', 'b', 'c']);
  const tocar = (col) => ev(`S.orden = siguienteOrden('${col}')`);
  tocar('anio');
  assert.deepEqual(ids(), ['a', 'b', 'c']);
  tocar('anio');
  assert.deepEqual(ids(), ['c', 'b', 'a'], 'más nuevo primero');
  tocar('anio');
  assert.deepEqual(ids(), ['a', 'b', 'c'], 'la tercera vez vuelve al orden del relevamiento');
  ev(`S.orden = { col: 'estado', dir: 'desc' }`);
  assert.equal(ids()[2], 'a', 'lo completo, al final');
  ev(`S.orden = { col: 'titulo', dir: 'asc' }`);
  assert.deepEqual(ids(), ['a', 'c', 'b'], 'Completo, Sin ISRC, Sin UPC');
  const cabecera = ev('tablaProductos(productosFiltrados())');
  assert.ok(cabecera.includes('aria-sort="ascending"'), 'el lector de pantalla sabe cómo está ordenada');
  assert.ok(cabecera.includes('data-orden="distribuidora"'));
  ev(`S.orden = null`);
});

test('Shift elige el tramo entero desde la última fila tocada, en el orden en que se ven', () => {
  catalogoDeTres();
  ev(`S.seleccion = new Set(); S.ancla = 'a'`);
  assert.deepEqual([...ev(`tramoDesdeAncla('c')`)], ['a', 'b', 'c']);
  ev(`S.orden = { col: 'titulo', dir: 'asc' }`);
  assert.deepEqual([...ev(`tramoDesdeAncla('c')`)], ['a', 'c'], 'el tramo sigue el orden de la pantalla');
  ev(`S.filtro.texto = 'Sin'`);
  assert.deepEqual([...ev(`tramoDesdeAncla('c')`)], ['c'], 'si la anterior no se ve, sólo ésta');
  ev(`S.filtro.texto = ''; S.orden = null; S.ancla = null`);
});

test('la tabla muestra la distribuidora, y separa lo que falta de lo que vino de Deezer', () => {
  catalogoDeTres();
  ev(`S.catalogo.productos[0].de_deezer = 1; S.catalogo.productos[2].distribuidora = ''`);
  const html = ev('tablaProductos(S.catalogo.productos)');
  assert.ok(html.includes('class="celda-distrib" title="X">X</td>'), 'se ve por qué distribuidora se entregó');
  assert.ok(html.includes('sin declarar'), 'y cuando no la declara, se dice');
  assert.ok(html.includes('badge badge-warn">sin UPC'), 'lo que falta, en ámbar');
  assert.ok(html.includes('badge badge-accent">1 tema de Deezer'), 'la procedencia, en neutro');
  assert.ok(html.includes('<colgroup>'), 'con anchos fijos, para que las columnas no salten');
  assert.ok(html.includes('Estado') && !html.includes('Faltantes'));
});

test('lo que sólo informa va junto y plegado; lo que pide algo queda a la vista', () => {
  catalogoDeTres();
  ev(`S.catalogo.diagnostico = ${JSON.stringify({
    via_topic: true, canal: 'A - Topic', canal_pedido: 'A', via: 'busqueda', temas: 26, unidades: 203,
    descartados: 17, sin_distribuidora: 2, codigos: { pedidos: true, encontrados: 3, fallas: 0 },
    completitud: { revisada: true, artista_deezer: 'A', releases: 4, temas: 0, faltan: [] },
  })}; S.verRelevamiento = false`);
  const html = ev('avisoCanal()');
  assert.equal((html.match(/class="alerta/g) || []).length, 0, 'nada pide acción: no hay avisos sueltos');
  assert.equal((html.match(/<details class="relevamiento"/g) || []).length, 1, 'una sola franja');
  assert.ok(!/<details class="relevamiento" open/.test(html), 'plegada');
  const resumen = html.slice(html.indexOf('<summary>'), html.indexOf('</summary>'));
  for (const dato of ['Topic: A - Topic', '<strong>26</strong> temas por el buscador', '<strong>203</strong> unidades de cupo',
    '<strong>17</strong> videos afuera', '2 temas sin distribuidora', 'códigos de «A» en Deezer']) {
    assert.ok(resumen.includes(dato), `falta «${dato}» en la línea plegada: ${resumen}`);
  }
  assert.ok(html.includes('data-accion="otro-deezer"'), 'el cambio de perfil sigue a mano, adentro');

  ev(`S.catalogo.diagnostico.codigos.fallas = 4`);
  const conFalla = ev('avisoCanal()');
  assert.ok(conFalla.indexOf('alerta-warn') < conFalla.indexOf('<details'), 'lo que pide algo va antes que la franja');

  ev(`ACCIONES['otro-deezer']()`);
  assert.ok(/<details class="relevamiento" open/.test(ev('avisoCanal()')), 'pedir otro perfil abre la franja');
  ev(`S.pideDeezer = false; S.verRelevamiento = false`);
});

test('cada texto nuevo del paso 2 está en los dos idiomas', () => {
  for (const idioma of ['es', 'en']) {
    ev(`ponerIdioma('${idioma}')`);
    for (const f of ["{ modo: 'distribuidora', distribs: new Set(), faltantes: false, texto: '' }",
      "{ modo: 'manual', distribs: new Set(), faltantes: true, texto: '' }",
      "{ modo: 'manual', distribs: new Set(), faltantes: false, texto: 'x' }"]) {
      ev(`S.filtro = ${f}`);
      const m = ev('motivoVacio()');
      for (const texto of [m.titulo, m.detalle]) {
        assert.ok(!texto.startsWith('paso2.'), `${idioma}: falta el texto de ${texto}`);
      }
    }
  }
  ev(`ponerIdioma('es')`);
});

test('«ISRC 0 de 27» se explica: no se pidió, no está en Deezer, o Deezer no respondió', () => {
  catalogoDeTres();
  const aviso = (codigos) => { ev(`S.catalogo.diagnostico = { codigos: ${JSON.stringify(codigos)} }`); return ev('avisoCanal()'); };
  assert.ok(aviso({ pedidos: false, encontrados: 0, fallas: 0 }).includes('No se buscaron los códigos'));
  assert.ok(aviso({ pedidos: true, encontrados: 0, fallas: 0 }).includes('No se encontró a'));
  assert.ok(aviso({ pedidos: true, encontrados: 0, fallas: 4 }).includes('Deezer no respondió 4 consultas'));
  assert.equal(aviso({ pedidos: true, encontrados: 3, fallas: 0 }), '', 'si salió bien no hay nada que decir');
  ev('S.catalogo.diagnostico = {}');
  assert.equal(ev('avisoCanal()'), '', 'un diagnóstico viejo, sin códigos, no rompe nada');
});

test('si no se encontró al artista en Deezer, se puede pegar el link de su perfil', () => {
  // De un caso real: la app decía que una artista «no está en Deezer» con su
  // perfil ahí, y no había forma de decirle cuál era.
  catalogoDeTres();
  ev(`S.url = 'https://www.youtube.com/channel/UCxxxxxxxxxxxxxxxxxxxxxx'; S.deezerLink = ''; S.deezerError = ''; S.pideDeezer = false`);
  ev(`S.catalogo.diagnostico = { codigos: { pedidos: true, encontrados: 0, fallas: 0 } }`);
  let html = ev('avisoCanal()');
  assert.ok(html.includes('id="deezer-link"') && html.includes('data-accion="usar-deezer"'), html);
  assert.ok(!html.includes('no es una falla de la app'), 'la app ya no le echa la culpa a la fuente');

  // Sin link no se releva nada: se pide el link.
  const cuerpos = [];
  const fetchDeAntes = ctx.fetch;
  ctx.fetch = async (ruta, opciones) => {
    if (ruta === '/api/relevar') cuerpos.push(JSON.parse(opciones.body));
    return { ok: false, status: 400, json: async () => ({ error: 'hasta acá llega la prueba' }) };
  };
  ev(`ACCIONES['usar-deezer']()`);
  assert.equal(cuerpos.length, 0);
  assert.equal(ev('S.deezerError'), 'Pegá el link del perfil.');
  ctx.fetch = fetchDeAntes;
  ev(`S.deezerError = ''`);
});

test('el link de Deezer viaja con el relevamiento, y otro canal lo descarta', async () => {
  const cuerpos = [];
  const fetchDeAntes = ctx.fetch;
  ctx.fetch = async (ruta, opciones) => {
    if (ruta === '/api/relevar') cuerpos.push(JSON.parse(opciones.body));
    return { ok: false, status: 400, json: async () => ({ error: 'hasta acá llega la prueba' }) };
  };
  catalogoDeTres();
  ev(`S.url = 'https://www.youtube.com/channel/UCx'; S.conCodigos = true; S.deezerError = ''; S.error = ''`);
  ev(`S.deezerLink = 'https://www.deezer.com/es/artist/27'`);
  await ev(`ACCIONES['usar-deezer']()`);
  assert.equal(cuerpos.length, 1);
  assert.equal(cuerpos[0].deezer_artista, 'https://www.deezer.com/es/artist/27');
  assert.equal(cuerpos[0].url, 'https://www.youtube.com/channel/UCx', 'el canal es el que ya se había pegado');
  assert.equal(cuerpos[0].de_cero, false, 'no vuelve a listar el canal: no gasta cupo de YouTube');
  ctx.fetch = fetchDeAntes;
  ev(`S.error = ''; S.errorCodigo = ''; S.ocupado = false; S.deezerLink = ''; S.deezerUsado = ''`);
});

test('con códigos encontrados se dice de qué perfil de Deezer salieron y se puede cambiar', () => {
  catalogoDeTres();
  ev(`S.pideDeezer = false; S.deezerLink = ''; S.deezerError = ''`);
  ev(`S.catalogo.diagnostico = { codigos: { pedidos: true, encontrados: 3, fallas: 0 },
      completitud: { revisada: true, artista_deezer: 'Los Del Ejemplo', releases: 4, temas: 0, faltan: [] } }`);
  let html = ev('avisoCanal()');
  assert.ok(html.includes('Los códigos salen del perfil de Deezer «Los Del Ejemplo».'), html);
  assert.ok(html.includes('data-accion="otro-deezer"') && !html.includes('id="deezer-link"'));
  ev(`S.pideDeezer = true`);
  html = ev('avisoCanal()');
  assert.ok(html.includes('id="deezer-link"'), 'al pedirlo aparece el campo');
  ev(`S.pideDeezer = false`);
});

test('la pantalla final dice qué sigue, con la baja al final', () => {
  const html = ev('queSigue()');
  const pasos = html.split('<li>').slice(1);
  assert.equal(pasos.length, 4);
  assert.ok(pasos[0].includes('&lt;&lt;COMPLETAR&gt;&gt;'));
  assert.ok(pasos[3].includes('baja'), 'dar de baja es lo último');
});

test('la instrucción para instalar ffmpeg es la del sistema de quien la lee', () => {
  const para = (so) => {
    ev(`S.config = { ...S.config, sistema: '${so}', entorno: { ffmpeg: false, tiddl: true } }`);
    return ev('faltaParaAudio()');
  };
  assert.ok(para('windows').includes('winget'));
  assert.ok(para('mac').includes('brew install ffmpeg'));
  assert.ok(!para('mac').includes('winget'));
  assert.ok(para('linux').includes('apt install ffmpeg'));
});

test('la página late contra /api/latido, con el token, y un latido que falla no rompe nada', async () => {
  const pedidos = [];
  ctx.fetch = async (ruta, opciones) => {
    pedidos.push({ ruta, opciones });
    return { ok: true, status: 200, json: async () => ({ ok: true }) };
  };
  await ev('latir()');
  assert.equal(pedidos.length, 1);
  assert.equal(pedidos[0].ruta, '/api/latido');
  assert.equal(pedidos[0].opciones.method, 'POST');
  assert.ok('X-App-Token' in pedidos[0].opciones.headers, 'sin token, el servidor lo rechaza');
  ctx.fetch = async () => { throw new Error('sin red'); };
  await ev('latir()');
});

// ------------------------------------------------------------ cómo se listó

const COMP_VACIA = { revisada: false, artista_deezer: '', releases: 0, temas: 0, sin_respuesta: 0, recortada: false, faltan: [] };
const COMP_FALTAN = {
  revisada: true, artista_deezer: 'Los <b>Ejemplo</b>', releases: 36, temas: 3, sin_respuesta: 0, recortada: false,
  faltan: [
    { deezer_id: 1, titulo: 'En Vivo', tipo: 'album', fecha: '2020-04-17', upc: '018736719585', relevado: true, total: 20,
      temas: [{ titulo: 'Voy a Morirme <i>de</i> Amor', isrc: 'USANG2074245', duracion_s: 62 }] },
    { deezer_id: 2, titulo: 'Un Sentimiento Vigente', tipo: 'album', fecha: '2007-06-16', upc: '018736381966', relevado: false, total: 12,
      temas: [{ titulo: 'Golpes Bajos', isrc: 'US3DF2007213', duracion_s: 232 }, { titulo: 'No Puedo', isrc: '', duracion_s: 221 }] },
  ],
};

function avisoCon(diag) {
  catalogoDeTres();
  ev(`S.catalogo.diagnostico = ${JSON.stringify({ codigos: { pedidos: true, encontrados: 3, fallas: 0 }, ...diag })}`);
  return ev('avisoCanal()');
}

test('un Topic listado por el buscador lo dice, con los temas y la cuota que gastó', () => {
  const html = avisoCon({ via: 'busqueda', temas: 290, unidades: 607, completitud: { ...COMP_VACIA, revisada: true, artista_deezer: 'A', releases: 36 } });
  assert.ok(html.includes('se listó por su buscador'), html);
  assert.ok(html.includes('<strong>290</strong> temas') && html.includes('<strong>607</strong> de las 10.000'), html);
  assert.ok(html.includes('no falta ninguna grabación'), 'comparado con Deezer y completo: se dice');
  assert.equal(avisoCon({ via: 'subidas', temas: 290, unidades: 12, completitud: COMP_VACIA }), '',
    'por la lista de subidas no hay nada que avisar');
});

test('si no se pudo comparar con Deezer, el aviso del buscador no promete que esté todo', () => {
  const html = avisoCon({ via: 'busqueda', temas: 290, unidades: 607, completitud: COMP_VACIA });
  assert.ok(html.includes('no pude compararlo'), html);
  assert.ok(!html.includes('no falta ninguna'), html);
});

test('un catálogo cortado por la cuota va primero y ofrece cargar una clave', () => {
  const html = avisoCon({ via: 'busqueda', temas: 150, unidades: 300, cortado_por_cuota: true, completitud: COMP_VACIA });
  assert.ok(html.indexOf('incompleto') < html.indexOf('se listó por su buscador'), 'el corte se lee antes que nada');
  assert.ok(html.includes('data-accion="ver-clave"'), 'tiene que ofrecer la salida');
});

test('lo que Deezer tiene y YouTube no trajo se avisa, y la lista se despliega a pedido', () => {
  const diag = { via: 'busqueda', temas: 290, unidades: 607, completitud: COMP_FALTAN };
  let html = avisoCon(diag);
  assert.ok(html.includes('Deezer tiene 3 grabaciones de Los &lt;b&gt;Ejemplo&lt;/b&gt;'), html);
  assert.ok(html.includes('data-accion="ver-faltantes"') && html.includes('aria-expanded="false"'));
  assert.ok(!html.includes('Golpes Bajos'), 'plegada, la lista no ocupa lugar');

  ev(`ACCIONES['ver-faltantes']()`);
  html = ev('avisoCanal()');
  assert.ok(html.includes('aria-expanded="true"'));
  assert.ok(html.indexOf('En Vivo') < html.indexOf('Un Sentimiento Vigente'), 'primero los discos que sí están');
  assert.ok(html.includes('Faltan 2 de 12:') && html.includes('Golpes Bajos · No Puedo'), html);
  assert.ok(html.includes('Falta 1 de 20:'), 'el singular concuerda');
  assert.ok(html.includes('UPC 018736381966'), 'con el UPC, para ir a buscarlo');
  assert.ok(html.includes('Voy a Morirme &lt;i&gt;de&lt;/i&gt; Amor'), 'los títulos de Deezer llegan escapados');

  // Otro catálogo arranca con la lista plegada.
  catalogoDeTres();
  assert.equal(ev('S.verFaltantes'), false);
});

test('el disco al que le faltan temas lleva su badge, entra al filtro de faltantes y lo detalla', () => {
  catalogoDeTres();
  ev(`S.catalogo.productos[0].faltan = ['Dos <b>', 'Tres']`);
  let html = ev('tablaProductos(S.catalogo.productos)');
  assert.ok(html.includes('faltan 2 temas'), html);
  ev(`S.filtro.faltantes = true`);
  assert.deepEqual([...ev('productosFiltrados().map((p) => p.id)')], ['a', 'b', 'c']);
  ev(`S.filtro.faltantes = false; S.expandidos.add('a')`);
  html = ev('tablaProductos(S.catalogo.productos)');
  assert.ok(html.includes('En Deezer este disco tiene además:') && html.includes('Dos &lt;b&gt; · Tres'), html);
  ev(`S.catalogo.productos[0].faltan = ['Uno']`);
  assert.ok(ev('tablaProductos(S.catalogo.productos)').includes('falta 1 tema'));
});

test('los temas sin distribuidora declarada se avisan y tienen su casilla en el filtro', () => {
  const html = avisoCon({ via: 'subidas', sin_distribuidora: 17, completitud: COMP_VACIA });
  assert.ok(html.includes('17 temas no declaran distribuidora'), html);
  ev(`S.catalogo.filtros.distribuidoras = [{ name: '', count: 2 }, { name: 'X', count: 1 }];
      S.catalogo.productos[0].distribuidora = '';
      S.filtro.modo = 'distribuidora'; S.filtro.distribs = new Set([''])`);
  assert.ok(ev('panelFiltro()').includes('Sin distribuidora declarada'));
  assert.deepEqual([...ev('productosFiltrados().map((p) => p.id)')], ['a']);
  ev(`S.filtro.modo = 'manual'`);
});

test('los avisos del listado están en los dos idiomas', () => {
  for (const idioma of ['es', 'en']) {
    ev(`ponerIdioma('${idioma}')`);
    ev('S.verFaltantes = true');
    const html = avisoCon({ via: 'busqueda', temas: 150, unidades: 300, cortado_por_cuota: true, sin_distribuidora: 1,
      completitud: { ...COMP_FALTAN, sin_respuesta: 2 } })
      + avisoCon({ via: 'busqueda', temas: 1, unidades: 101, sin_distribuidora: 2, completitud: COMP_VACIA });
    assert.ok(!/paso2\.[a-z_]+/.test(html), `${idioma}: quedó una clave sin texto en ${html}`);
  }
  ev(`ponerIdioma('es'); S.verFaltantes = false`);
});

// ------------------------------------------------------------ listado reusado

test('un listado reusado se dice, sin hablar de cuota gastada, y ofrece listar de nuevo', () => {
  const html = avisoCon({ via: 'busqueda', reusado: true, temas: 290, unidades: 0, completitud: COMP_VACIA });
  assert.ok(html.includes('no gasté cuota de YouTube'), html);
  assert.ok(html.includes('data-accion="relistar"'), 'con la salida para quien sabe que el canal cambió');
  assert.ok(!html.includes('de las 10.000'), 'no dice que gastó cero unidades: no gastó');
  assert.ok(html.includes('<strong>290</strong> temas'));
  assert.ok(!avisoCon({ via: 'busqueda', temas: 290, unidades: 607, completitud: COMP_VACIA }).includes('relistar'));
});

test('«Volver a listar» releva el mismo link pidiendo el listado de cero, una sola vez', async () => {
  const cuerpos = [];
  const fetchDeAntes = ctx.fetch;
  ctx.fetch = async (ruta, opciones) => {
    if (ruta === '/api/relevar') cuerpos.push(JSON.parse(opciones.body));
    return { ok: false, status: 400, json: async () => ({ error: 'hasta acá llega la prueba' }) };
  };
  catalogoDeTres();
  ev(`S.url = 'https://www.youtube.com/channel/UCx'; S.error = ''`);
  await ev(`ACCIONES.relistar()`);
  assert.equal(cuerpos.length, 1);
  assert.equal(cuerpos[0].de_cero, true);
  assert.equal(cuerpos[0].url, 'https://www.youtube.com/channel/UCx', 'el link sale del que ya se había pegado');
  assert.equal(ev('S.paso'), 1, 'vuelve al paso 1, que es donde está la barra de avance');

  await ev(`ACCIONES.relevar()`);
  assert.equal(cuerpos[1].de_cero, false, 'el pedido vale para una vez: el siguiente relevamiento reusa');
  ctx.fetch = fetchDeAntes;
  ev(`S.error = ''; S.errorCodigo = ''; S.ocupado = false`);
});

// ------------------------------------------------------------ lo sumado de Deezer

test('lo que sólo está en Deezer arranca sin elegir, marcado, y a nombre de quien figura', () => {
  catalogoDeTres();
  ev(`adoptarCatalogo({ ...S.catalogo, productos: [
        ...S.catalogo.productos,
        { id: 'd', titulo: 'Es Mi Culpa', tipo: 'single', anio: 2026, upc: '8', distribuidora: '', tracks: 1, con_isrc: 1,
          origen: 'deezer', de_deezer: 1, artista: 'Walter <Encina>', detalle: [] },
        { id: 'e', titulo: 'Propio', tipo: 'single', anio: 2026, upc: '9', distribuidora: '', tracks: 1, con_isrc: 1,
          origen: 'deezer', de_deezer: 1, artista: 'A', detalle: [] },
      ] })`);
  assert.deepEqual([...ev('[...S.seleccion]')], ['a', 'b', 'c'], 'no se eligen solos: no se sabe si son del catálogo');
  const html = ev('tablaProductos(S.catalogo.productos)');
  assert.equal(html.split('sólo en Deezer').length - 1, 2);
  assert.ok(html.includes('a nombre de Walter &lt;Encina&gt;'), 'la colaboración dice de quién es, escapado');
  assert.equal(html.split('a nombre de').length - 1, 1, 'el propio no lo dice');
  ev(`S.filtro.faltantes = true`);
  assert.deepEqual([...ev('productosFiltrados().map((p) => p.id)')], ['b', 'c', 'd', 'e'], 'entran a «algo que completar»');
  ev(`S.filtro.faltantes = false`);
});

test('el disco con temas sumados de Deezer lo dice en el badge y en cada tema', () => {
  catalogoDeTres();
  ev(`Object.assign(S.catalogo.productos[2], { de_deezer: 1, detalle: [
        { n: 1, titulo: 'Uno', isrc: 'AR1', duracion: '3:20', views: 5, origen: '' },
        { n: 2, titulo: 'Dos', isrc: 'AR2', duracion: '3:20', views: 0, origen: 'deezer' }] });
      S.expandidos.add('c')`);
  const html = ev('tablaProductos(S.catalogo.productos)');
  assert.ok(html.includes('1 tema de Deezer'), html);
  assert.equal(html.split('(sumado de Deezer: YouTube no lo muestra en este disco)').length - 1, 1, 'sólo en el tema que vino de Deezer');
  ev(`S.catalogo.productos[2].de_deezer = 3`);
  assert.ok(ev('tablaProductos(S.catalogo.productos)').includes('3 temas de Deezer'));
});

test('la lista de lo que faltaba dice qué pasó con cada lanzamiento', () => {
  const comp = { ...COMP_FALTAN, faltan: [
    { ...COMP_FALTAN.faltan[0], sumado: true },
    { ...COMP_FALTAN.faltan[1], sumado: true },
    { ...COMP_FALTAN.faltan[0], titulo: 'Vuela', sumado: false },
  ] };
  catalogoDeTres();
  ev(`S.catalogo.diagnostico = ${JSON.stringify({ via: 'busqueda', temas: 290, unidades: 607, completitud: comp })}; S.verFaltantes = true`);
  const html = ev('avisoCanal()');
  assert.ok(html.includes('sumé al catálogo'), html);
  assert.ok(html.includes('sumado a su disco') && html.includes('sumado aparte, sin elegir') && html.includes('sin sumar'), html);
  for (const idioma of ['es', 'en']) {
    ev(`ponerIdioma('${idioma}')`);
    assert.ok(!/paso2\.[a-z_]+|tabla\.[a-z_]+/.test(ev('avisoCanal()')), idioma);
  }
  ev(`ponerIdioma('es'); S.verFaltantes = false`);
});

// ------------------------------------------------------------ evidencia, edición e importación

function catalogoConEvidencia() {
  ev(`
    S.config = { version: '0', terminos_aceptados: true, tiene_clave: true, idiomas: ['es', 'en'] };
    S.vista = null; S.fatal = ''; S.ocupado = false;
    adoptarCatalogo({
      catalogo_id: 'c1', artista: 'Artista',
      productos: [{ id: 'p1', titulo: 'Disco', tipo: 'album', anio: 2020, upc: '0885012345673', upc_nivel: 'inferido',
                    sello: 'Sello', distribuidora: 'X', tracks: 3, views: 0, orden_estimado: false, con_isrc: 2,
                    sin_confirmar: 1, datos: { genre: 'Rock' }, upc_editado: false,
                    detalle: [
                      { n: 1, titulo: 'Uno', isrc: 'ARAAA2000001', duracion: '3:20', views: 0, nivel: 'confirmado', editado: false, candidatos: [] },
                      { n: 2, titulo: 'Dos', isrc: 'ARAAA2000002', duracion: '3:30', views: 0, nivel: 'inferido', editado: true, candidatos: [] },
                      { n: 3, titulo: 'Tres', isrc: '', duracion: '3:40', views: 0, nivel: '', editado: false,
                        candidatos: [{ isrc: 'ARBBB2100003', duracion: '3:40' }, { isrc: 'ARCCC1900004', duracion: '3:41' }] },
                    ] }],
      resumen: { products: 1, tracks: 3, views: 0, with_upc: 1, with_isrc: 2 },
      evidencia: { isrc: { confirmado: 1, inferido: 1 }, upc: { inferido: 1 } },
      campos: ['c_line', 'genre', 'language', 'territories', 'explicit', 'lyrics_language', 'uno_que_no_conozco'],
      filtros: { distribuidoras: [{ name: 'X', count: 1 }], anio_min: 2020, anio_max: 2020 },
      diagnostico: {},
    });
    S.expandidos = new Set(['p1']);
    render();
  `);
  return pantalla.innerHTML;
}

test('la tabla dice qué códigos conviene confirmar, sin tratarlos como faltantes', () => {
  const html = catalogoConEvidencia();
  // Un ISRC inferido y el UPC inferido: dos códigos por confirmar, en neutro.
  assert.ok(html.includes('badge badge-accent">2 códigos por confirmar'), 'falta el badge neutro');
  assert.ok(!html.includes('badge badge-warn">2 códigos'), 'por confirmar no es un faltante');
  assert.ok(html.includes('nivel nivel-neutro'), 'el inferido tiene que verse en la fila del tema');
  assert.ok(html.includes('1</span> de una sola fuente'), 'la oración de arriba dice cuántos son');
  assert.equal(ev(`leFaltaAlgo(S.catalogo.productos[0])`), true, 'entra al filtro de «algo que completar»');
});

test('un tema con candidatos los ofrece en vez de decir «sin ISRC»', () => {
  const html = catalogoConEvidencia();
  assert.ok(html.includes('data-accion="usar-candidato"') && html.includes('data-isrc="ARCCC1900004"'));
  assert.ok(html.includes('data-accion="restaurar-isrc"'), 'el que se cambió a mano se puede deshacer');
});

test('guardar un código mal formado deja el error al lado del campo y lo escrito a la vista', async () => {
  catalogoConEvidencia();
  ctx.fetch = async () => ({ ok: false, status: 400, json: async () => ({ error: 'no tiene el formato de un ISRC' }) });
  ev(`S.editando = { tipo: 'isrc', producto: 'p1', indice: 0, valor: 'ARAAA', error: '' };`);
  poner('#codigo-edit', { value: 'ARAAA' });
  await ev(`ACCIONES['guardar-codigo']()`);
  nodos.delete('#codigo-edit');
  assert.equal(ev('S.editando.error'), 'no tiene el formato de un ISRC');
  assert.equal(ev('S.editando.valor'), 'ARAAA');
  assert.ok(pantalla.innerHTML.includes('id="codigo-error"'), 'el error se dibuja junto al campo');
  assert.equal(ev('S.fatal'), '', 'un código inválido no es un error de la app');
  ev(`S.editando = null;`);
});

test('lo que trae la planilla importada llega escapado, y un conflicto no viene elegido', () => {
  catalogoConEvidencia();
  ev(`
    S.importacion = {
      id: 'i', nombre: '<b>export</b>.csv', filas: 3, columnas: { track: '<i>Tema</i>', isrc: 'ISRC' },
      resumen: { confirma: 0, completa: 1, conflicto: 1, ambiguo: 1 },
      items: [
        { id: 'i0001', tipo: 'completa', codigo: 'isrc', producto_id: 'p1', producto: 'Disco', indice: 2, track: '<img src=x onerror=alert(1)>', actual: '', nuevo: 'ARBBB2100003', fila: 2, candidatos: [], nivel: '' },
        { id: 'i0002', tipo: 'conflicto', codigo: 'isrc', producto_id: 'p1', producto: 'Disco', indice: 0, track: 'Uno', actual: 'ARAAA2000001', nuevo: 'ARZZZ9900009', fila: 3, candidatos: [], nivel: 'confirmado' },
        { id: 'i0003', tipo: 'ambiguo', codigo: 'isrc', producto_id: 'p1', producto: 'Disco', indice: 1, track: 'Dos', actual: '', nuevo: '', fila: 0, nivel: '',
          candidatos: [{ isrc: 'ARBBB2100003', titulo: 'Dos', album: '<u>Disco</u>', duracion_s: 200, fila: 4 }, { isrc: 'ARCCC1900004', titulo: 'Dos', album: '', duracion_s: 0, fila: 5 }] },
      ],
      sin_correspondencia: [{ fila: 9, track: '<script>x</script>', album: '', isrc: 'ARDDD1800001', upc: '' }],
      sin_correspondencia_total: 1,
    };
    S.importElegidos = new Set(['i0001']);
    S.importElecciones = {};
    render();
  `);
  const html = pantalla.innerHTML;
  for (const crudo of ['<img src=x', '<b>export', '<i>Tema', '<u>Disco', '<script>x']) {
    assert.ok(!html.includes(crudo), `entró sin escapar: ${crudo}`);
  }
  assert.ok(html.includes('&lt;img src=x'), 'el título del archivo tenía que verse, escapado');
  assert.ok(/data-item="i0001" checked/.test(html), 'lo que completa viene elegido');
  assert.ok(!/data-item="i0002" checked/.test(html), 'un conflicto no se aplica solo');
  assert.ok(html.includes('Aplicar 1 cambio<'), 'el botón dice cuántos cambios aplica');
  ev(`S.importacion = null;`);
});

test('la comparación pone primero lo que perdió su código y escapa lo que viene del archivo', () => {
  catalogoConEvidencia();
  ev(`
    S.comparacion = {
      fecha: '2026-10-01', artista: 'Artista', otro_artista: false, nuevos: [], nuevos_total: 0,
      resumen: { migrado: 1, codigos_cambiados: 1 },
      releases: [
        { titulo: 'Bien', anio: 2020, estado: 'migrado', distribuidora_antes: 'Vieja', distribuidoras_ahora: ['Nueva'], upc_antes: '1', upc_ahora: '1', isrc_cambiados: [], isrc_perdidos: [], temas_que_faltan: [] },
        { titulo: '<b>Mal</b>', anio: 2021, estado: 'codigos_cambiados', distribuidora_antes: 'Vieja', distribuidoras_ahora: ['Nueva'], upc_antes: '1', upc_ahora: '1',
          isrc_cambiados: [{ tema: '<i>Tema</i>', antes: 'ARAAA2000001', ahora: 'ARNEW2600777' }], isrc_perdidos: [], temas_que_faltan: [] },
      ],
    };
    render();
  `);
  const html = pantalla.innerHTML;
  assert.ok(html.indexOf('&lt;b&gt;Mal') < html.indexOf('>Bien<'), 'lo que cambió de código va primero');
  assert.ok(!html.includes('<b>Mal') && !html.includes('<i>Tema'), 'lo del archivo entró sin escapar');
  assert.ok(html.includes('ARNEW2600777'), 'se muestra el código nuevo');
  ev(`S.comparacion = null;`);
});

test('el formulario de datos no dibuja un campo que la interfaz no conoce', () => {
  catalogoConEvidencia();
  ev(`S.datosAbierto = true; render();`);
  const html = pantalla.innerHTML;
  assert.ok(html.includes('id="dato-genre"') && html.includes('id="dato-lyrics_language"'));
  assert.ok(!html.includes('uno_que_no_conozco'));
  assert.ok(html.includes('cargado en 1 de 1'), 'dice en cuántos de los elegidos ya está cargado');
  ev(`S.datosAbierto = false;`);
});

test('un catálogo abierto de un archivo lo dice, en vez de los avisos del relevamiento', () => {
  catalogoConEvidencia();
  ev(`S.catalogo.diagnostico = { abierto: { fecha: '2026-10-01' }, completitud: { revisada: false }, codigos: { pedidos: true } }; render();`);
  assert.ok(pantalla.innerHTML.includes('Relevamiento guardado el 2026-10-01'));
});

test('los textos de lo nuevo están en los dos idiomas', () => {
  for (const idioma of ['es', 'en']) {
    ev(`ponerIdioma('${idioma}')`);
    for (const nivel of ['confirmado', 'inferido', 'dudoso', 'manual', 'importado']) {
      assert.ok(ev(`etiquetaNivel('${nivel}')`).includes('class="nivel'), `${idioma}: ${nivel}`);
      assert.ok(!ev(`nombreNivel('${nivel}')`).includes('nivel.'), `${idioma}: ${nivel} sin traducir`);
    }
    for (const estado of ev('ESTADOS_COMPARACION')) {
      assert.ok(!ev(`TEXTO_ESTADO['${estado}'].nombre()`).startsWith('comp.'), `${idioma}: ${estado}`);
    }
  }
  ev(`ponerIdioma('es')`);
  assert.equal(ev(`etiquetaNivel('uno-que-no-existe')`), '');
});
