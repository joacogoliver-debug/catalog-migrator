// Tests de la interfaz, con `node --test`, sin navegador.
//
// `esc()` es la única barrera entre los títulos que vienen de YouTube, Deezer y
// Apple y el `innerHTML`; la CSP no la reemplaza. Hasta acá no la probaba nada.

import assert from 'node:assert/strict';
import fs from 'node:fs';
import { test } from 'node:test';

import { cargar } from './entorno.mjs';

const { ev, pantalla, poner, nodos, backend } = cargar();

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
