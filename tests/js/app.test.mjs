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

test('lo elegido que el filtro esconde se avisa, porque no entra al paquete', () => {
  catalogoDeTres();
  assert.equal(ev('elegidosOcultos()'), 0);
  ev(`S.filtro.texto = 'Completo'`);
  assert.equal(ev('elegidosOcultos()'), 2);
  const html = ev('resumenElegidos(seleccionados(), productosFiltrados())');
  assert.ok(html.includes('2 elegidos quedan afuera'), html);
  assert.ok(html.includes('data-accion="limpiar-filtro"'), 'tiene que ofrecer la salida');
  ev(`ACCIONES['limpiar-filtro']()`);
  assert.equal(ev('elegidosOcultos()'), 0);
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
