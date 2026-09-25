/* ============================================================
   Textos de la interfaz, en español e inglés.

   Se carga antes que app.js, así que `T` ya existe cuando la primera vista se
   dibuja. El catálogo vive acá y no en el servidor porque la interfaz se pinta
   en el navegador: pedirle cada rótulo a /api/ sería un viaje por palabra.

   Lo que genera Python (el log, los errores del relevamiento, los archivos que
   van adentro del ZIP) tiene su propio catálogo en `i18n.py`. Son dos porque son
   dos procesos, no por gusto: la planilla se escribe del lado del servidor y ahí
   no llega este archivo.

   Uso:
       T('paso1.titulo')
       T('paso2.mostrando', {n: 4, total: 12})

   Si falta la traducción se cae al español; si falta la clave, se devuelve la
   clave. Un rótulo sin traducir se ve feo, que es exactamente lo que queremos:
   que se note y se arregle, no que la pantalla quede en blanco.

   Sobre el plural: no hay motor de pluralización. Donde importa hay dos claves,
   una en singular y otra en plural, y quien las usa elige. Con dos idiomas que
   pluralizan igual, un ICU MessageFormat sería una dependencia para nada.
   ============================================================ */

'use strict';

const IDIOMAS = ['es', 'en'];
const IDIOMA_POR_DEFECTO = 'es';

let _idioma = IDIOMA_POR_DEFECTO;

function idioma() {
  return _idioma;
}

function ponerIdioma(codigo) {
  const c = String(codigo || '').trim().toLowerCase().slice(0, 2);
  if (IDIOMAS.includes(c)) {
    _idioma = c;
    document.documentElement.setAttribute('lang', c);
  }
  return _idioma;
}

/* Reemplaza {n} por params.n. Sin motor de plantillas: alcanza para lo que hay
   y no agrega una dependencia a una app que se empaqueta como ejecutable. */
function _formatear(txt, params) {
  if (!params) return txt;
  return txt.replace(/\{(\w+)\}/g, (m, k) => (k in params ? String(params[k]) : m));
}

function T(clave, params) {
  const entrada = TEXTOS[clave];
  if (!entrada) return clave;
  return _formatear(entrada[_idioma] || entrada[IDIOMA_POR_DEFECTO] || clave, params);
}

/* Rellena el HTML estático marcado con data-t. Lo usa index.html, que tiene
   unos pocos textos fijos y no vale la pena pasarlos por render(). */
function traducirEstaticos(raiz) {
  (raiz || document).querySelectorAll('[data-t]').forEach((el) => {
    el.textContent = T(el.getAttribute('data-t'));
  });
  (raiz || document).querySelectorAll('[data-t-title]').forEach((el) => {
    el.setAttribute('title', T(el.getAttribute('data-t-title')));
  });
  (raiz || document).querySelectorAll('[data-t-aria]').forEach((el) => {
    el.setAttribute('aria-label', T(el.getAttribute('data-t-aria')));
  });
}

/* ============================================================
   Catálogo

   Ordenado por pantalla. La clave lleva el prefijo de dónde se usa, así buscar
   de dónde sale un texto es un grep y no una cacería.
   ============================================================ */

const TEXTOS = {
  /* ---------------------------------------------------------- app */
  'app.nombre': {
    es: 'Migrador de Catálogos',
    en: 'Catalog Migrator',
  },

  /* ---------------------------------------------------------- cabecera y pie */
  // El mismo nombre que `app.nombre`: eran dos grafías de la app en la misma pantalla.
  'cabecera.titulo': { es: 'Migrador de Catálogos', en: 'Catalog Migrator' },
  'cabecera.pasos': { es: 'Pasos', en: 'Steps' },
  'cabecera.idioma': { es: 'Idioma', en: 'Language' },
  'cabecera.tema': { es: 'Cambiar entre claro y oscuro', en: 'Switch between light and dark' },
  'cabecera.ir_a_claro': { es: 'Cambiar a modo claro', en: 'Switch to light mode' },
  'cabecera.ir_a_oscuro': { es: 'Cambiar a modo oscuro', en: 'Switch to dark mode' },
  'pie.hecho_por': { es: 'Hecho por', en: 'Made by' },
  'pie.terminos': { es: 'Términos de uso', en: 'Terms of use' },

  /* ---------------------------------------------------------- stepper */
  'stepper.paso1': { es: 'Pegá el link', en: 'Paste the link' },
  'stepper.paso2': { es: 'Elegí productos', en: 'Pick releases' },
  'stepper.paso3': { es: 'Elegí qué descargar', en: 'Pick what to download' },
  'stepper.paso4': { es: 'Descargá', en: 'Download' },

  /* ---------------------------------------------------------- título del documento */
  'titulo.terminos': { es: 'Términos de uso, {app}', en: 'Terms of use, {app}' },
  'titulo.clave': { es: 'Clave de YouTube, {app}', en: 'YouTube key, {app}' },
  'titulo.paso2': { es: '{artista}, elegir productos', en: '{artista}, pick releases' },
  'titulo.paso3': { es: '{artista}, qué descargar', en: '{artista}, what to download' },
  'titulo.paso4_armando': { es: '{artista}, armando el paquete', en: '{artista}, building the package' },
  'titulo.paso4_listo': { es: '{artista}, paquete listo', en: '{artista}, package ready' },

  /* ---------------------------------------------------------- comunes */
  'comun.volver': { es: 'Volver', en: 'Back' },
  'comun.cancelar': { es: 'Cancelar', en: 'Cancel' },
  'comun.continuar': { es: 'Continuar', en: 'Continue' },
  'comun.reintentar': { es: 'Reintentar', en: 'Try again' },
  'fatal.desconocido': { es: 'error desconocido', en: 'unknown error' },
  'comun.n_productos': { es: '{n} productos', en: '{n} releases' },
  'comun.n_productos_uno': { es: '{n} producto', en: '{n} release' },
  'comun.n_tracks': { es: '{n} tracks', en: '{n} tracks' },
  'comun.n_tracks_uno': { es: '{n} track', en: '{n} track' },
  'comun.n_errores': { es: '{n} errores', en: '{n} errors' },
  'comun.n_errores_uno': { es: '{n} error', en: '{n} error' },
  'comun.n_avisos': { es: '{n} avisos', en: '{n} warnings' },
  'comun.n_avisos_uno': { es: '{n} aviso', en: '{n} warning' },

  /* ---------------------------------------------------------- red */
  'red.timeout': {
    es: 'La app tardó demasiado en responder.',
    en: 'The app took too long to answer.',
  },
  'red.sin_conexion': {
    es: 'Se perdió la conexión con la app.',
    en: 'Lost the connection to the app.',
  },
  'red.sin_conexion_larga': {
    es: 'Se perdió la conexión con la app. Puede que se haya cerrado la ventana del servidor.',
    en: 'Lost the connection to the app. The server window may have been closed.',
  },
  'red.error_http': { es: 'Error {codigo}', en: 'Error {codigo}' },
  'red.proceso_fallo': { es: 'El proceso falló.', en: 'The job failed.' },

  /* ---------------------------------------------------------- arranque */
  'arranque.sin_motor_titulo': {
    es: 'No pude conectar con el motor de la app.',
    en: 'Could not reach the app engine.',
  },
  'arranque.sin_motor_detalle': {
    es: 'Cerrala y volvé a abrirla.',
    en: 'Close it and open it again.',
  },

  /* ---------------------------------------------------------- error irrecuperable */
  'fatal.titulo': {
    es: 'La app se encontró con un problema',
    en: 'The app ran into a problem',
  },
  'fatal.detalle': {
    es: 'El motor sigue andando. Reiniciá la interfaz y, si se repite, el detalle de abajo es lo que sirve para reportarlo.',
    en: 'The engine is still running. Restart the interface, and if it happens again, the detail below is what to report.',
  },
  'fatal.reiniciar': { es: 'Reiniciar la interfaz', en: 'Restart the interface' },

  /* ---------------------------------------------------------- progreso */
  'progreso.preparando': { es: 'Preparando', en: 'Getting ready' },
  'progreso.trabajando': { es: 'Trabajando', en: 'Working' },
  'progreso.aria_barra': { es: 'Avance del trabajo', en: 'Job progress' },

  /* ---------------------------------------------------------- términos */
  'terminos.titulo': { es: 'Términos de uso', en: 'Terms of use' },
  'terminos.bajada': {
    es: 'Se leen una vez. Después no vuelven a aparecer, y quedan siempre disponibles desde el pie de la ventana.',
    en: 'You read them once. After that they stay out of the way, and remain available from the footer.',
  },
  'terminos.aceptar': {
    es: 'Acepto y quiero usar la herramienta',
    en: 'I accept and want to use the tool',
  },
  'terminos.si_no': {
    es: 'Si no estás de acuerdo, cerrá la ventana.',
    en: 'If you do not agree, close the window.',
  },
  'terminos.cuerpo': {
    es: `
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
    junto al código.</p>

    <p class="small muted">La versión en español es la de referencia. La traducción al
    inglés se ofrece por comodidad y, si difieren, vale esta.</p>`,
    en: `
    <h4>What this tool is</h4>
    <p>Catalog Migrator is a free, open-source program for <strong>managing music
    catalogs</strong>. It surveys an artist's distributed catalog, recovers its ISRC
    and UPC codes, gathers the cover art and builds the ingestion sheet a new
    distributor asks for. That is its purpose and no other.</p>

    <h4>Who may use it, and what for</h4>
    <p>It is meant for rights holders, labels, distributors, managers and artists
    working on <strong>their own material, or material they administer with the
    owner's permission</strong>.</p>
    <p>By using it you state that you hold the rights or the permission you need over
    the content you process, and that you will honor the terms of service of the
    platforms the tool queries, among them YouTube, Deezer, Apple and Tidal.</p>

    <h4>What is not allowed</h4>
    <p>This tool neither endorses nor enables piracy. What follows is expressly
    outside its purpose and this license of use.</p>
    <ul>
      <li>Downloading, copying or redistributing material you hold no rights to.</li>
      <li>Using the audio module to obtain someone else's recordings, or to get around
      technical protection measures.</li>
      <li>Reselling, redistributing or publishing the content obtained without the
      owner's permission.</li>
      <li>Sharing third-party account credentials, or using a streaming account
      outside the terms of the service that provides it.</li>
      <li>Getting around the limits of the APIs the tool queries, or automating
      requests beyond what those APIs allow.</li>
    </ul>
    <p>The audio module is optional, ships turned off and requires you to connect your
    own paid account. It exists so a catalog owner can recover their own masters when
    the original file cannot be found. It does not replace the master delivered by the
    artist or the label, and the documentation and the reports it produces say so.</p>

    <h4>Your data</h4>
    <p>The app runs entirely on your computer. There are no accounts, no sign-up and
    no server of ours. The API key is stored in your home folder, the surveyed catalog
    lives in memory while the app is open, and nothing is sent anywhere other than the
    public APIs the tool queries to do its work.</p>

    <h4>No warranty</h4>
    <p>The software is provided as is, without warranty of any kind, express or
    implied. The data comes from third-party public sources and may be incomplete or
    out of date. <strong>Pre-delivery validation is a help, not a certificate</strong>,
    and it does not replace the distributor's review or the judgement of whoever
    delivers the material.</p>
    <p>The author is not liable for direct or indirect damages arising from the use of
    the tool, nor for decisions made from the data it produces, nor for the use each
    person makes of the material they process. Responsibility over the content rests
    entirely with whoever uses it.</p>

    <h4>License and trademarks</h4>
    <p>The code is distributed under the MIT license, whose full text is in the
    LICENSE file of the repository. Third-party trademarks and names mentioned belong
    to their owners, and the tool is neither affiliated with nor sponsored by any of
    them.</p>

    <h4>Changes</h4>
    <p>These terms may be updated in later versions. The version in force is the one
    shipped with the copy you are using, and it is in the public repository alongside
    the code.</p>

    <p class="small muted">The Spanish version is the reference one. This English
    translation is offered for convenience and, where they differ, the Spanish text
    prevails.</p>`,
  },

  /* ---------------------------------------------------------- clave de YouTube */
  'clave.titulo': { es: 'Conectá tu clave de YouTube', en: 'Connect your YouTube key' },
  'clave.titulo_propia': { es: 'Usar tu propia clave de YouTube', en: 'Use your own YouTube key' },
  'clave.bajada': {
    es: 'Se pide una sola vez. Queda guardada en tu computadora y no se comparte con nadie.',
    en: 'Asked for once. It stays on your computer and is not shared with anyone.',
  },
  'clave.bajada_propia': {
    es: 'La clave que cargues acá reemplaza a la que trae esta copia, y queda guardada sólo en tu computadora.',
    en: 'The key you enter here replaces the one this copy ships with, and stays only on your computer.',
  },
  'clave.como_titulo': { es: 'Cómo conseguirla, en tres pasos.', en: 'How to get one, in three steps.' },
  'clave.paso1': {
    es: 'Entrá a <a href="https://console.cloud.google.com/apis/credentials" target="_blank" rel="noopener noreferrer">Google Cloud Console, en Credenciales</a>, y creá un proyecto.',
    en: 'Go to <a href="https://console.cloud.google.com/apis/credentials" target="_blank" rel="noopener noreferrer">Google Cloud Console, Credentials</a>, and create a project.',
  },
  'clave.paso2': {
    es: 'Activá <em>YouTube Data API v3</em> en la biblioteca de APIs.',
    en: 'Enable <em>YouTube Data API v3</em> in the API library.',
  },
  'clave.paso3': {
    es: 'Creá una <em>clave de API</em> y pegala acá abajo.',
    en: 'Create an <em>API key</em> and paste it below.',
  },
  'clave.gratis': {
    es: 'Es gratis. El cupo diario alcanza para unos 500 catálogos.',
    en: 'It is free. The daily quota covers around 500 catalogs.',
  },
  'clave.rotulo': { es: 'Clave de la API de YouTube', en: 'YouTube API key' },
  'clave.ayuda': {
    es: 'La verificamos con una consulta de prueba antes de guardarla.',
    en: 'We check it with a test request before saving it.',
  },
  'clave.guardar': { es: 'Verificar y guardar', en: 'Check and save' },
  'clave.pega_antes': { es: 'Pegá la clave antes de guardar.', en: 'Paste the key before saving.' },
  'clave.verificando': { es: 'Verificando', en: 'Checking' },
  'clave.no_se_guardo': { es: 'No se pudo guardar.', en: 'Could not save it.' },

  /* ---------------------------------------------------------- paso 1 */
  'paso1.titulo': { es: '¿Qué catálogo querés migrar?', en: 'Which catalog do you want to migrate?' },
  'paso1.bajada': {
    es: 'Pegá el link del canal de YouTube del artista. Lo ideal es el <strong>canal Topic</strong>, el que se llama <span class="mono">«&lt;artista&gt; - Topic»</span>.',
    en: 'Paste the link to the artist\'s YouTube channel. The Topic channel is the one you want, the one named <span class="mono">"&lt;artist&gt; - Topic"</span>.',
  },
  'paso1.rotulo_link': { es: 'Link del canal', en: 'Channel link' },
  'paso1.ayuda_link': {
    es: 'Acepta la URL del canal, un <span class="mono">@handle</span> o el link de cualquier tema del artista.',
    en: 'Takes the channel URL, an <span class="mono">@handle</span> or the link of any of the artist\'s songs.',
  },
  'paso1.falta_link': { es: 'Pegá el link del canal.', en: 'Paste the channel link.' },
  'paso1.ya_relevado': {
    es: 'Tenés relevado el catálogo de {artista}. Relevar otro lo reemplaza.',
    en: 'You already surveyed {artista}. Surveying another one replaces it.',
  },
  'paso1.volver_catalogo': { es: 'Volver a ese catálogo', en: 'Back to that catalog' },
  'paso1.topic_titulo': { es: 'Conviene pegar el canal Topic.', en: 'Paste the Topic channel if you can.' },
  'paso1.topic_cuerpo': {
    es: 'Es el que YouTube genera solo con el catálogo distribuido, y el único que trae distribuidora, álbum, año y sello en cada descripción.',
    en: 'It is the one YouTube builds on its own from the distributed catalog, and the only one carrying distributor, album, year and label in every description.',
  },
  'paso1.topic_detalle': {
    es: 'Si pegás el canal oficial del artista igual funciona, porque la app busca su Topic y usa ese. Pero esa búsqueda gasta parte del cupo diario, y en artistas con nombres parecidos puede elegir el Topic equivocado. Pegando el Topic directo eso no pasa.',
    en: 'Pasting the artist\'s official channel works too, because the app looks up its Topic and uses that. But the lookup spends part of the daily quota, and with artists whose names are alike it can pick the wrong Topic. Pasting the Topic directly avoids that.',
  },
  'paso1.codigos_titulo': { es: 'Buscar códigos ISRC y UPC', en: 'Look up ISRC and UPC codes' },
  'paso1.codigos_detalle': {
    es: 'El ISRC identifica cada grabación y el UPC cada lanzamiento. Los busca en Deezer, sin clave ni costo. Tarda un poco más, pero son los códigos que la distribuidora nueva necesita.',
    en: 'The ISRC identifies each recording and the UPC each release. Looked up on Deezer, no key and no cost. It takes a little longer, but these are the codes the new distributor needs.',
  },
  'paso1.clave_incluida': {
    es: 'Esta copia trae una clave de YouTube compartida, con cupo para unos 500 catálogos por día entre todos.',
    en: 'This copy ships with a shared YouTube key, with quota for about 500 catalogs a day across everyone using it.',
  },
  'paso1.prefiero_mia': { es: 'Prefiero usar la mía', en: 'I would rather use mine' },
  'paso1.cargar_clave': { es: 'Cargar mi propia clave', en: 'Enter my own key' },
  'paso1.error_titulo': { es: 'No se pudo relevar.', en: 'The survey failed.' },
  'paso1.relevar': { es: 'Relevar catálogo', en: 'Survey catalog' },

  /* ---------------------------------------------------------- paso 2 */
  'paso2.bajada': {
    es: 'Catálogo relevado. Los datos salen de YouTube, Deezer y Apple.',
    en: 'Catalog surveyed. The data comes from YouTube, Deezer and Apple.',
  },
  'paso2.resumen': {
    es: '{productos} y {tracks}, con {views} reproducciones. UPC en {upc}, ISRC en {isrc}.',
    en: '{productos} and {tracks}, with {views} plays. UPC on {upc}, ISRC on {isrc}.',
  },
  'paso2.otro_artista': { es: 'Relevar otro artista', en: 'Survey another artist' },
  'paso2.productos': { es: 'Productos', en: 'Releases' },
  'paso2.mostrando': { es: 'Mostrando {n} de {total}', en: 'Showing {n} of {total}' },
  'paso2.aria_filtro': { es: 'Filtro', en: 'Filter' },
  'paso2.filtro_todos': { es: 'Todos', en: 'All' },
  'paso2.filtro_anio': { es: 'Por año', en: 'By year' },
  'paso2.filtro_distrib': { es: 'Por distribuidora', en: 'By distributor' },
  'paso2.buscar_placeholder': { es: 'Título, ISRC o UPC', en: 'Title, ISRC or UPC' },
  'paso2.aria_buscar': { es: 'Buscar en el catálogo', en: 'Search the catalog' },
  'paso2.desde_anio': { es: 'Desde el año', en: 'From year' },
  'paso2.hasta_anio': { es: 'Hasta el año', en: 'To year' },
  'paso2.rango_anios': {
    es: 'El catálogo va de {desde} a {hasta}. Los productos sin año quedan afuera.',
    en: 'The catalog runs from {desde} to {hasta}. Releases with no year are left out.',
  },
  'paso2.sin_anios': {
    es: 'Ningún producto tiene año de lanzamiento declarado. Usá otro filtro.',
    en: 'No release states a year. Use another filter.',
  },
  'paso2.vacio_titulo': {
    es: 'Ningún producto coincide con el filtro',
    en: 'No release matches the filter',
  },
  'paso2.vacio_detalle': {
    es: 'Probá ampliar el filtro o limpiar la búsqueda.',
    en: 'Try widening the filter or clearing the search.',
  },
  'paso2.vacio_sin_distrib_titulo': {
    es: 'No hay ninguna distribuidora marcada',
    en: 'No distributor is ticked',
  },
  'paso2.vacio_sin_distrib_detalle': {
    es: 'Marcá al menos una para ver sus productos.',
    en: 'Tick at least one to see its releases.',
  },
  'paso2.vacio_nada_falta_titulo': {
    es: 'A ningún producto le falta nada',
    en: 'No release is missing anything',
  },
  'paso2.vacio_nada_falta_detalle': {
    es: 'Todos tienen UPC, ISRC en cada track y el orden confirmado.',
    en: 'All of them have a UPC, an ISRC on every track and a confirmed order.',
  },
  'paso2.solo_faltantes': {
    es: 'Sólo los que tienen algo que completar',
    en: 'Only those with something to fill in',
  },
  'paso2.ocultos': {
    es: '{n} elegidos quedan afuera: el filtro los esconde y no entran al paquete.',
    en: '{n} picked releases are left out: the filter hides them and they will not go into the package.',
  },
  'paso2.ocultos_uno': {
    es: '1 elegido queda afuera: el filtro lo esconde y no entra al paquete.',
    en: '1 picked release is left out: the filter hides it and it will not go into the package.',
  },
  'paso2.ver_todos': { es: 'Ver todos', en: 'Show all' },
  'paso2.limpiar_filtro': { es: 'Limpiar el filtro', en: 'Clear the filter' },
  'paso2.leyenda': {
    es: 'Conservar el ISRC, el UPC y la fecha original es lo que hace que cada release nuevo se una al que ya está en las tiendas, con sus reproducciones y playlists. Lo que falta pedíselo primero a tu distribuidora actual: la app no inventa códigos ni orden.',
    en: 'Keeping the ISRC, the UPC and the original date is what makes each new release join the one already in stores, with its plays and playlists. Ask your current distributor for what is missing first: the app makes up neither codes nor track order.',
  },
  'paso2.elegidos': {
    es: 'Elegidos: {n} de {total}, {tracks}',
    en: 'Picked: {n} of {total}, {tracks}',
  },
  'paso2.marcar_todos': { es: 'Marcar todos', en: 'Select all' },
  'paso2.desmarcar_todos': { es: 'Desmarcar todos', en: 'Clear selection' },
  'paso2.canal_comun': { es: 'un canal común', en: 'a regular channel' },
  'paso2.via_topic': {
    es: 'Pegaste {pedido}, que no es un canal Topic, así que busqué y relevé {topic}.',
    en: 'You pasted {pedido}, which is not a Topic channel, so I looked up and surveyed {topic}.',
  },
  'paso2.que_es_topic': {
    es: 'El Topic es el que YouTube genera solo con el catálogo distribuido, y es el único que trae distribuidora, álbum, año y sello.',
    en: 'The Topic channel is the one YouTube builds on its own from the distributed catalog, and the only one carrying distributor, album, year and label.',
  },
  'paso2.descartados_uno': {
    es: 'Dejé afuera {n} video que no es un lanzamiento, como un videoclip, un vivo o una entrevista. Sin la descripción auto-generada de YouTube no tiene álbum ni códigos, así que no sirve para una migración.',
    en: 'I left out {n} video that is not a release, such as a music video, a live set or an interview. Without YouTube\'s auto-generated description it carries no album and no codes, so it is no use for a migration.',
  },
  'paso2.descartados': {
    es: 'Dejé afuera {n} videos que no son lanzamientos, como videoclips, vivos y entrevistas. Sin la descripción auto-generada de YouTube no tienen álbum ni códigos, así que no sirven para una migración.',
    en: 'I left out {n} videos that are not releases, such as music videos, live sets and interviews. Without YouTube\'s auto-generated description they carry no album and no codes, so they are no use for a migration.',
  },
  'paso2.codigos_no_pedidos': {
    es: 'No se buscaron los códigos, así que ISRC y UPC quedan vacíos. Para traerlos, relevá de nuevo con «Buscar códigos ISRC y UPC» marcado.',
    en: 'Codes were not looked up, so ISRC and UPC are empty. To bring them in, survey again with "Look up ISRC and UPC codes" ticked.',
  },
  'paso2.no_esta_en_deezer_titulo': {
    es: '{artista} no está en Deezer, o está con otro nombre.',
    en: '{artista} is not on Deezer, or is there under another name.',
  },
  'paso2.no_esta_en_deezer_cuerpo': {
    es: 'Por eso no hay ISRC ni UPC: no es una falla de la app, es que la fuente no los tiene. Pedíselos a tu distribuidora actual antes de aceptar códigos nuevos.',
    en: 'That is why there is no ISRC or UPC: it is not the app failing, the source does not have them. Ask your current distributor for them before accepting new codes.',
  },
  'paso2.deezer_no_respondio': {
    es: 'Deezer no respondió {n} consultas, aun después de reintentar. Algunos códigos pueden faltar por eso y no porque no existan: relevar de nuevo más tarde puede completarlos.',
    en: 'Deezer did not answer {n} lookups, even after retrying. Some codes may be missing because of that and not because they do not exist: surveying again later may fill them in.',
  },
  'paso2.deezer_no_respondio_uno': {
    es: 'Deezer no respondió una consulta, aun después de reintentar. Algún código puede faltar por eso y no porque no exista: relevar de nuevo más tarde puede completarlo.',
    en: 'Deezer did not answer one lookup, even after retrying. A code may be missing because of that and not because it does not exist: surveying again later may fill it in.',
  },
  'paso2.sin_metadata_titulo': {
    es: 'Este canal no trae la metadata del catálogo.',
    en: 'This channel carries no catalog metadata.',
  },
  'paso2.sin_metadata_cuerpo': {
    es: 'No hay álbumes, sellos ni años, y los códigos casi no se pueden encontrar.',
    en: 'There are no albums, labels or years, and the codes are nearly impossible to find.',
  },
  'paso2.usar_topic': { es: 'Relevar «{titulo}» en su lugar', en: 'Survey "{titulo}" instead' },
  'paso2.buscar_topic': {
    es: 'Buscá «{artista} - Topic» en YouTube y pegá ese link.',
    en: 'Search for "{artista} - Topic" on YouTube and paste that link.',
  },

  /* ---------------------------------------------------------- tabla */
  'tabla.col_producto': { es: 'Producto', en: 'Release' },
  'tabla.col_tipo': { es: 'Tipo', en: 'Type' },
  'tabla.col_anio': { es: 'Año', en: 'Year' },
  'tabla.col_faltantes': { es: 'Faltantes', en: 'Missing' },
  'tabla.col_n': { es: 'N', en: 'No.' },
  'tabla.col_track': { es: 'Track', en: 'Track' },
  'tabla.col_duracion': { es: 'Duración', en: 'Length' },
  'tabla.col_reproducciones': { es: 'Reproducciones', en: 'Plays' },
  'tabla.sin_upc': { es: 'sin UPC', en: 'no UPC' },
  'tabla.sin_isrc': { es: 'sin ISRC', en: 'no ISRC' },
  'tabla.sin_fecha': { es: 'sin fecha', en: 'no date' },
  'tabla.isrc_de': { es: 'ISRC {n} de {total}', en: 'ISRC {n} of {total}' },
  'tabla.orden_estimado': { es: 'orden estimado', en: 'order estimated' },
  'tabla.completo': { es: 'completo', en: 'complete' },
  'tabla.aria_elegir': { es: 'Elegir {titulo}', en: 'Select {titulo}' },
  'tabla.aria_ver_tracks': { es: 'Ver los tracks de {titulo}', en: 'Show the tracks of {titulo}' },
  'tabla.aria_marcar_todos': {
    es: 'Marcar todos los productos del filtro',
    en: 'Select every release in the filter',
  },

  /* ---------------------------------------------------------- paso 3 */
  'paso3.titulo': { es: '¿Qué querés descargar?', en: 'What do you want to download?' },
  'paso3.elegidos': {
    es: 'Elegiste {productos}, {tracks}.',
    en: 'You picked {productos}, {tracks}.',
  },
  'paso3.contenido': { es: 'Contenido del paquete', en: 'What goes in the package' },
  'paso3.planilla': { es: 'Planilla y validación', en: 'Spreadsheet and validation' },
  'paso3.planilla_detalle': {
    es: 'Excel con los datos y códigos, hoja de ingesta en CSV para la distribuidora, y el informe de validación previa.',
    en: 'Excel with the data and codes, ingestion sheet as CSV for the distributor, and the pre-delivery validation report.',
  },
  'paso3.portadas': { es: 'Portadas', en: 'Cover art' },
  'paso3.portadas_detalle': {
    es: 'La resolución más alta que tenga Apple Music. Te avisamos si queda por debajo del mínimo de ingesta.',
    en: 'The highest resolution Apple Music has. We tell you if it lands below the ingestion minimum.',
  },
  'paso3.audios': { es: 'Audios', en: 'Audio' },
  'paso3.audios_detalle': {
    es: 'FLAC lossless con tu propia cuenta de Tidal. La referencia de YouTube casi siempre falla, porque YouTube la bloquea.',
    en: 'Lossless FLAC with your own Tidal account. The YouTube reference almost always fails, because YouTube blocks it.',
  },
  // Una instrucción por sistema: `winget` en una Mac es una instrucción que no
  // se puede seguir.
  'paso3.falta_ffmpeg_windows': {
    es: 'Falta <strong>ffmpeg</strong>, el programa que arma los archivos de audio. Se instala una sola vez: abrí la Terminal de Windows y pegá <code>winget install --id Gyan.FFmpeg -e</code>. Después cerrá y volvé a abrir la app.',
    en: '<strong>ffmpeg</strong>, the program that puts the audio files together, is missing. You install it once: open Windows Terminal and paste <code>winget install --id Gyan.FFmpeg -e</code>. Then close and reopen the app.',
  },
  'paso3.falta_ffmpeg_mac': {
    es: 'Falta <strong>ffmpeg</strong>, el programa que arma los archivos de audio. Se instala una sola vez con Homebrew: abrí la Terminal y pegá <code>brew install ffmpeg</code>. Después cerrá y volvé a abrir la app.',
    en: '<strong>ffmpeg</strong>, the program that puts the audio files together, is missing. You install it once with Homebrew: open Terminal and paste <code>brew install ffmpeg</code>. Then close and reopen the app.',
  },
  'paso3.falta_ffmpeg_linux': {
    es: 'Falta <strong>ffmpeg</strong>, el programa que arma los archivos de audio. Instalalo con el gestor de paquetes de tu sistema, por ejemplo <code>sudo apt install ffmpeg</code>, y volvé a abrir la app.',
    en: '<strong>ffmpeg</strong>, the program that puts the audio files together, is missing. Install it with your system\'s package manager, for example <code>sudo apt install ffmpeg</code>, and reopen the app.',
  },
  'paso3.falta_modulo': {
    es: 'Esta versión de la app no incluye el módulo de audio. Necesitás la versión completa.',
    en: 'This build does not include the audio module. You need the full build.',
  },
  'paso3.falta_generico': {
    es: 'No disponible en esta computadora. El README explica, en «Si algo no anda», cómo sacar el diagnóstico que dice qué falta.',
    en: 'Not available on this computer. The README explains, under "If something does not work", how to get the diagnostic report that says what is missing.',
  },
  'paso3.resumen_zip': {
    es: 'Se va a generar un ZIP con una carpeta por producto.',
    en: 'A ZIP will be built, with one folder per release.',
  },
  'paso3.generar': { es: 'Generar paquete', en: 'Build package' },
  'paso3.sin_seleccion': { es: 'No hay productos elegidos.', en: 'No releases picked.' },
  'paso3.cancelado': {
    es: 'Cancelaste el armado del paquete. Lo que elegiste sigue como estaba.',
    en: 'You cancelled building the package. What you chose is still as it was.',
  },

  /* ---------------------------------------------------------- Tidal */
  'tidal.conectada_titulo': { es: 'Cuenta de Tidal conectada.', en: 'Tidal account connected.' },
  'tidal.conectada_detalle': {
    es: 'El audio va a bajar en FLAC lossless: la copia sin pérdida que sirve Tidal. Sirve para entregar cuando no tenés el archivo original, pero no siempre es el máster de estudio; si lo tenés, entregá ese.',
    en: 'Audio will download as lossless FLAC: the lossless copy Tidal streams. It works for delivery when you do not have the original file, but it is not always the studio master; if you have that, deliver it.',
  },
  'tidal.desconectar': { es: 'Desconectar', en: 'Disconnect' },
  'tidal.conecta_titulo': {
    es: 'Conectá tu cuenta en el sitio de Tidal.',
    en: 'Connect your account on the Tidal site.',
  },
  'tidal.abri': { es: 'Abrí {url}', en: 'Open {url}' },
  'tidal.con_codigo': { es: 'y usá el código {codigo}', en: 'and use the code {codigo}' },
  'tidal.ya_confirme': { es: 'Ya confirmé', en: 'I confirmed' },
  'tidal.conecta_para_audio': {
    es: 'Conectá Tidal para poder bajar el audio.',
    en: 'Connect Tidal to be able to download audio.',
  },
  'tidal.sin_cuenta_detalle': {
    es: 'Sin cuenta conectada sólo se puede intentar la referencia de YouTube, y hoy falla en la mayoría de los casos: YouTube sólo le entrega el audio a un navegador con la sesión iniciada, y buena parte de la música está protegida contra copia. Cuando falla, el reporte te dice el motivo track por track.',
    en: 'With no account connected the only option is the YouTube reference, and today it fails most of the time: YouTube only hands the audio to a browser with a signed-in session, and much of the music is copy protected. When it fails, the report tells you why, track by track.',
  },
  'tidal.conectar': { es: 'Conectar mi cuenta de Tidal', en: 'Connect my Tidal account' },
  'tidal.password': {
    es: 'Tu contraseña nunca pasa por esta app, porque te autenticás en el sitio de Tidal.',
    en: 'Your password never goes through this app, because you sign in on the Tidal site.',
  },
  'tidal.consultando': { es: 'Consultando', en: 'Checking' },
  'tidal.aun_no_confirmaste': {
    es: 'Todavía no confirmaste en Tidal. Completá el acceso en la otra pestaña, y en cuanto lo hagas se conecta solo, sin volver a apretar.',
    en: 'You have not confirmed on Tidal yet. Finish signing in on the other tab, and it connects on its own as soon as you do, with no need to click again.',
  },
  'tidal.err_corte': {
    es: 'Se cortó la comunicación con la app. Probá de nuevo.',
    en: 'The connection to the app dropped. Try again.',
  },
  'tidal.err_vencido': {
    es: 'El código venció. Cerrá esto y volvé a conectar la cuenta.',
    en: 'The code expired. Close this and connect the account again.',
  },
  'tidal.err_pendiente': {
    es: 'Todavía no me llegó la confirmación de Tidal.',
    en: 'Tidal has not confirmed yet.',
  },
  'tidal.err_rechazo': {
    es: 'Tidal rechazó la conexión. Volvé a intentar desde el principio.',
    en: 'Tidal turned the connection down. Start again from the top.',
  },
  'tidal.err_red': {
    es: 'No pude hablar con Tidal. Revisá que haya conexión a internet.',
    en: 'Could not reach Tidal. Check that there is an internet connection.',
  },
  'tidal.err_generico': { es: 'No se pudo conectar.', en: 'Could not connect.' },

  /* ---------------------------------------------------------- paso 4 */
  'paso4.armando': { es: 'Armando el paquete', en: 'Building the package' },
  'paso4.armando_detalle': {
    es: 'Tarda según cuántos tracks elegiste y qué pediste. Podés seguir en otra cosa con la ventana abierta: el avance queda acá.',
    en: 'It takes as long as the tracks you picked and what you asked for. You can do something else with the window open: the progress stays here.',
  },
  'paso4.error_titulo': { es: 'No se pudo generar', en: 'Could not build it' },
  'paso4.listo': { es: 'Tu paquete está listo', en: 'Your package is ready' },
  'paso4.resumen': {
    es: '{productos}, portadas para {portadas}. La validación encontró {errores} y {avisos}.',
    en: '{productos}, cover art for {portadas}. Validation found {errores} and {avisos}.',
  },
  'paso4.zip_disponible': {
    es: 'El ZIP queda disponible mientras la app esté abierta.',
    en: 'The ZIP stays available while the app is open.',
  },
  'paso4.que_sigue': { es: 'Qué sigue', en: 'What comes next' },
  'paso4.sigue_completar': {
    es: 'Descomprimí el ZIP y abrí la hoja de ingesta en Excel. Lo que dice <code>&lt;&lt;COMPLETAR&gt;&gt;</code> hay que llenarlo antes de subir: es lo que no sale de ninguna fuente pública.',
    en: 'Unzip it and open the ingestion sheet in Excel. Whatever says <code>&lt;&lt;COMPLETAR&gt;&gt;</code> has to be filled in before uploading: it is what no public source has.',
  },
  'paso4.sigue_pedir': {
    es: 'Pedile a tu distribuidora actual lo que falte: los ISRC y UPC que no aparecieron, las fechas originales, los másters en WAV o FLAC y el arte original.',
    en: 'Ask your current distributor for whatever is missing: the ISRCs and UPCs that did not turn up, the original dates, the masters as WAV or FLAC, and the original artwork.',
  },
  'paso4.sigue_cargar': {
    es: 'Cargá el catálogo en la distribuidora nueva con los mismos ISRC, UPC y fecha original. Es lo que une cada release al que ya está en las tiendas.',
    en: 'Load the catalog into the new distributor with the same ISRCs, UPCs and original dates. That is what joins each release to the one already in stores.',
  },
  'paso4.sigue_baja': {
    es: 'Hacé la baja en la distribuidora vieja recién cuando el catálogo nuevo esté en vivo en las tiendas. Si la bajás antes, los temas pueden quedar afuera mientras tanto.',
    en: 'Take the catalog down at the old distributor only once the new one is live in stores. If you take it down first, the songs can be missing in the meantime.',
  },
  'paso4.otros_productos': { es: 'Elegir otros productos', en: 'Pick other releases' },
  'paso4.descargar': { es: 'Descargar el paquete ({peso})', en: 'Download the package ({peso})' },

  /* ---------------------------------------------------------- validación */
  'validacion.titulo': { es: 'Validación previa', en: 'Pre-delivery validation' },
  'validacion.sin_nada_titulo': {
    es: 'Validación sin observaciones.',
    en: 'Validation came back clean.',
  },
  'validacion.sin_nada_detalle': {
    es: 'Nada de lo que las distribuidoras suelen rechazar.',
    en: 'None of what distributors usually reject.',
  },
  'validacion.errores_titulo': {
    es: '{n} errores que suelen causar rechazo.',
    en: '{n} errors that usually cause a rejection.',
  },
  'validacion.errores_titulo_uno': {
    es: '{n} error que suele causar rechazo.',
    en: '{n} error that usually causes a rejection.',
  },
  'validacion.errores_detalle_uno': {
    es: 'Conviene corregirlo antes de entregar. El detalle también está en {archivo}, dentro del ZIP.',
    en: 'Worth fixing before delivering. The detail is also in {archivo}, inside the ZIP.',
  },
  'validacion.errores_detalle': {
    es: 'Conviene corregirlos antes de entregar. El detalle también está en {archivo}, dentro del ZIP.',
    en: 'Worth fixing before delivering. The detail is also in {archivo}, inside the ZIP.',
  },
  'validacion.sin_errores': { es: 'Sin errores de rechazo.', en: 'No rejection errors.' },
  'validacion.hay_avisos': { es: 'Hay {n} avisos para revisar.', en: 'There are {n} warnings to look at.' },
  'validacion.hay_avisos_uno': { es: 'Hay {n} aviso para revisar.', en: 'There is {n} warning to look at.' },
  'validacion.cuenta_tracks': { es: '{tracks} en {productos}', en: '{tracks} across {productos}' },

  /* ---------------------------------------------------------- nombres de archivo del ZIP
     Estos NO son rótulos: son el nombre real del archivo que escribe
     `paquete.py`, y tienen que decir exactamente lo mismo que `paq.f_validacion`
     en `i18n.py`. Si uno cambia, cambia el otro: si no, la interfaz manda a
     buscar adentro del ZIP un archivo que no existe. */
  'archivos.validacion': {
    es: '_Validacion pre-entrega.txt',
    en: '_Pre-delivery validation.txt',
  },

  /* ---------------------------------------------------------- títulos de hallazgo */
  'hallazgo.upc_falta': { es: 'Sin UPC', en: 'No UPC' },
  'hallazgo.portada_modo_color': { es: 'Portada en gris, paleta o transparente', en: 'Cover in gray, palette or transparent' },
  'hallazgo.audio_no_apto': { es: 'Audio sólo de referencia', en: 'Reference-only audio' },
  'hallazgo.isrc_confianza_media': { es: 'ISRC de confianza media', en: 'Medium-confidence ISRC' },
  'hallazgo.campos_a_completar': { es: 'Campos a completar', en: 'Fields to fill in' },
  'hallazgo.artista_no_principal': { es: 'Otro artista principal', en: 'Another main artist' },
  'hallazgo.release_en_dos_distribuidoras': { es: 'Release en dos distribuidoras', en: 'Release at two distributors' },
  'hallazgo.upc_no_verificado': { es: 'UPC de otro release, descartado', en: 'Another release\'s UPC, dropped' },
  'hallazgo.upc_mezclado': { es: 'UPC distintos en un producto', en: 'Different UPCs in one release' },
  'hallazgo.isrc_falta': { es: 'Sin ISRC', en: 'No ISRC' },
  'hallazgo.sello_falta': { es: 'Sin sello', en: 'No label' },
  'hallazgo.anio_falta': { es: 'Sin año de lanzamiento', en: 'No release year' },
  'hallazgo.orden_sin_confirmar': { es: 'Orden de tracks estimado', en: 'Track order estimated' },
  'hallazgo.portada_falta': { es: 'Sin portada', en: 'No cover art' },
  'hallazgo.portada_bajo_recomendado': {
    es: 'Portada por debajo del recomendado',
    en: 'Cover below the recommended size',
  },
  'hallazgo.portada_chica': {
    es: 'Portada por debajo del mínimo',
    en: 'Cover below the minimum size',
  },
  'hallazgo.portada_no_cuadrada': { es: 'Portada no cuadrada', en: 'Cover is not square' },
  'hallazgo.portada_cmyk': { es: 'Portada en CMYK', en: 'Cover is CMYK' },
  'hallazgo.portada_ilegible': { es: 'Portada ilegible', en: 'Cover cannot be read' },
  'hallazgo.texto_como_formula': {
    es: 'Texto que parece una fórmula',
    en: 'Text that looks like a formula',
  },
  'hallazgo.titulo_con_ruido': {
    es: 'Título con texto de YouTube',
    en: 'Title carries YouTube text',
  },
  'hallazgo.duracion_larga': { es: 'Duración sospechosa', en: 'Suspicious length' },
  'hallazgo.duracion_falta': { es: 'Sin duración', en: 'No length' },
  'hallazgo.isrc_invalido': { es: 'ISRC inválido', en: 'Invalid ISRC' },
  'hallazgo.upc_invalido': { es: 'UPC inválido', en: 'Invalid UPC' },
  'hallazgo.isrc_duplicado': { es: 'ISRC repetido en un producto', en: 'ISRC repeated within a release' },
  'hallazgo.isrc_compartido': { es: 'Misma grabación en dos productos', en: 'Same recording on two releases' },
  'hallazgo.isrc_match_dudoso': { es: 'ISRC en grabaciones distintas', en: 'ISRC on different recordings' },
  'hallazgo.upc_duplicado': { es: 'UPC repetido', en: 'Duplicate UPC' },
  'hallazgo.anio_futuro': { es: 'Año en el futuro', en: 'Year in the future' },
  'hallazgo.anio_absurdo': { es: 'Año imposible', en: 'Impossible year' },
  'hallazgo.anio_invalido': { es: 'Año no numérico', en: 'Year is not a number' },
  'hallazgo.producto_sin_titulo': { es: 'Producto sin título', en: 'Release with no title' },
  'hallazgo.track_sin_titulo': { es: 'Track sin título', en: 'Track with no title' },
};
