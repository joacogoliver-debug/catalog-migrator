# -*- coding: utf-8 -*-
"""
Textos de la app en español e inglés.

Todo lo que el usuario lee sale de acá: los mensajes del log, los errores, los
rótulos de las planillas y el contenido de los archivos que van adentro del ZIP.
La interfaz tiene su propio catálogo en `app/web/i18n.js`, porque se dibuja en el
navegador y pedirle cada rótulo al servidor sería absurdo.

Cómo se usa:

    from i18n import T
    log(T("portadas.buscando", n=3, total=10))

Tres decisiones que el resto del código da por sentadas:

  - **La clave es el contrato, no el texto.** Si falta una traducción se cae al
    español, y si falta la clave entera se devuelve la clave. Nunca revienta: un
    texto sin traducir es un problema de traducción, no un motivo para que la app
    no arranque.

  - **El idioma es global y de un solo usuario.** Esto es una app de escritorio
    que corre para una persona, así que un módulo con estado alcanza y sobra. Si
    algún día sirviera a varios, esto hay que repensarlo.

  - **Las cabeceras de la hoja de ingesta no están acá y no se traducen.** Son
    los nombres de campo que espera la distribuidora, no texto para leer. Ver
    `paquete.COLUMNAS_INGESTA`.
"""

import os

IDIOMAS = ("es", "en")
POR_DEFECTO = "es"

_actual = POR_DEFECTO


# ============================================================
# Estado
# ============================================================

def idioma():
    """El idioma en uso, siempre uno de IDIOMAS."""
    return _actual


def poner_idioma(codigo):
    """Cambia el idioma. Devuelve el que quedó puesto.

    Acepta basura sin quejarse (un config.json editado a mano, una variable de
    entorno rara) y en ese caso deja el que había.
    """
    global _actual
    c = (codigo or "").strip().lower()[:2]
    if c in IDIOMAS:
        _actual = c
    return _actual


def idioma_forzado():
    """El idioma impuesto por `MIGRADOR_IDIOMA`, o "" si no está puesta.

    Gana sobre todo lo demás, incluso sobre lo que el usuario eligió en la app.
    Existe por dos motivos: permite arrancar la app en un idioma sin tocar la
    config, y hace que los tests y el CI sean deterministas en vez de depender
    del locale de la máquina que los corre.
    """
    v = (os.environ.get("MIGRADOR_IDIOMA") or "").strip().lower()[:2]
    return v if v in IDIOMAS else ""


def idioma_del_sistema():
    """El idioma que parece querer el sistema operativo.

    Se mira el entorno primero porque es lo que respeta un usuario que arranca
    la app con LANG puesto a mano, y recién después la config regional. Cualquier
    cosa que no sea inglés cae en español, que es el idioma del proyecto.
    """
    for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        v = (os.environ.get(var) or "").strip().lower()
        if v[:2] in IDIOMAS:
            return v[:2]

    try:
        import locale
        v = (locale.getlocale()[0] or "")
        if not v:
            # En Windows getlocale() devuelve None hasta que alguien llama a
            # setlocale. getdefaultlocale está deprecada pero es lo único que
            # contesta sin efectos de borde.
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                v = (locale.getdefaultlocale()[0] or "")
        v = v.strip().lower()
        if v.startswith("en"):
            return "en"
        if v.startswith("es"):
            return "es"
        # Windows devuelve nombres largos tipo "English_United States".
        if v.startswith("english"):
            return "en"
        if v.startswith("spanish"):
            return "es"
    except Exception:
        pass
    return POR_DEFECTO


# ============================================================
# Traducción
# ============================================================

def T(clave, **kw):
    """El texto de `clave` en el idioma actual, con los parámetros aplicados.

    Los parámetros van con formato de `str.format`: "{n} de {total}".
    """
    entrada = TEXTOS.get(clave)
    if entrada is None:
        return clave
    txt = entrada.get(_actual) or entrada.get(POR_DEFECTO) or clave
    if not kw:
        return txt
    try:
        return txt.format(**kw)
    except (KeyError, IndexError, ValueError):
        # Una llave de formato que no llegó no puede tumbar un relevamiento de
        # cuarenta minutos. Se devuelve el texto crudo y se sigue.
        return txt


def claves_sin_traducir(a="es", b="en"):
    """Las claves que existen en `a` y faltan en `b`. La usa el test."""
    return sorted(k for k, v in TEXTOS.items() if v.get(a) and not v.get(b))


# ============================================================
# Catálogo
#
# Ordenado por módulo. La clave lleva el prefijo del módulo que la emite, así
# buscar de dónde sale un texto es un grep y no una cacería.
# ============================================================

TEXTOS = {

    # ---- server ------------------------------------------------------------
    "server.idioma_invalido": {
        "es": "Idioma no reconocido. Los que hay son: {idiomas}.",
        "en": "Unknown language. The ones available are: {idiomas}.",
    },
    "server.falta_url": {
        "es": "Pegá el link del canal de YouTube.",
        "en": "Paste the YouTube channel link.",
    },
    "server.url_larga": {
        "es": "Ese link es demasiado largo para ser un canal de YouTube.",
        "en": "That link is too long to be a YouTube channel.",
    },

    # ---- validar ------------------------------------------------------------
    # Estos mensajes viajan en cada hallazgo y terminan en tres lugares: la
    # pantalla 4, el informe de texto del ZIP y la hoja de validación. El
    # `codigo` del hallazgo no está acá porque no se traduce.
    "val.sin_titulo": {"es": "(sin título)", "en": "(untitled)"},
    "val.no_se_busco": {"es": "no se buscó", "en": "not looked up"},

    "val.portada_falta": {
        "es": "Sin portada: {motivo}.",
        "en": "No cover art: {motivo}.",
    },
    "val.portada_ilegible": {
        "es": "No se pudieron leer las dimensiones de la portada. Puede ser un formato no soportado.",
        "en": "Could not read the cover dimensions. It may be an unsupported format.",
    },
    "val.portada_no_cuadrada": {
        "es": "La portada es de {ancho}x{alto} y tiene que ser cuadrada.",
        "en": "The cover is {ancho}x{alto} and has to be square.",
    },
    "val.portada_chica": {
        "es": "La portada es de {ancho}x{alto}, por debajo del mínimo de {min}x{min}.",
        "en": "The cover is {ancho}x{alto}, below the {min}x{min} minimum.",
    },
    "val.portada_bajo_recomendado": {
        "es": "La portada es de {ancho}x{alto}. Entra, pero el recomendado es {rec}x{rec}.",
        "en": "The cover is {ancho}x{alto}. It passes, but {rec}x{rec} is the recommended size.",
    },
    "val.portada_cmyk": {
        "es": "La portada parece estar en CMYK y tiene que ser RGB.",
        "en": "The cover looks like CMYK and has to be RGB.",
    },

    "val.producto_sin_titulo": {
        "es": "El producto no tiene título.",
        "en": "The release has no title.",
    },
    "val.upc_falta": {
        "es": "Sin UPC. La distribuidora va a asignar uno nuevo y se pierde la continuidad del release.",
        "en": "No UPC. The distributor will assign a new one and the release loses its continuity.",
    },
    "val.upc_invalido": {
        "es": "El UPC {upc} no es válido: {motivo}.",
        "en": "UPC {upc} is not valid: {motivo}.",
    },
    "val.upc_vacio": {"es": "vacío", "en": "empty"},
    "val.upc_no_digitos": {
        "es": "tiene caracteres que no son dígitos",
        "en": "it has characters that are not digits",
    },
    "val.upc_largo": {
        "es": "tiene {n} dígitos (se esperan 12 para UPC-A o 13 para EAN-13)",
        "en": "it has {n} digits (12 expected for UPC-A, 13 for EAN-13)",
    },
    "val.upc_check": {
        "es": "dígito verificador incorrecto (termina en {tiene}, debería ser {espera})",
        "en": "wrong check digit (it ends in {tiene}, it should be {espera})",
    },
    "val.anio_falta": {"es": "Sin año de lanzamiento.", "en": "No release year."},
    "val.anio_futuro": {
        "es": "El año de lanzamiento ({anio}) está en el futuro.",
        "en": "The release year ({anio}) is in the future.",
    },
    "val.anio_absurdo": {
        "es": "El año de lanzamiento ({anio}) no es plausible.",
        "en": "The release year ({anio}) is not plausible.",
    },
    "val.anio_invalido": {
        "es": "El año de lanzamiento ({anio}) no es un número.",
        "en": "The release year ({anio}) is not a number.",
    },
    "val.sello_falta": {
        "es": "Sin sello (℗). Varias distribuidoras lo piden.",
        "en": "No label (℗). Several distributors ask for it.",
    },
    "val.orden_sin_confirmar": {
        "es": "El orden de los tracks es estimado por fecha de subida y no está confirmado.",
        "en": "Track order is estimated from the upload date and is not confirmed.",
    },

    "val.track_sin_titulo": {"es": "El track no tiene título.", "en": "The track has no title."},
    "val.isrc_falta": {
        "es": "Sin ISRC. La distribuidora va a asignar uno nuevo y se pierde el historial de la grabación.",
        "en": "No ISRC. The distributor will assign a new one and the recording loses its history.",
    },
    "val.isrc_invalido": {
        "es": "El ISRC {isrc} no tiene el formato de 12 caracteres (CC-XXX-YY-NNNNN).",
        "en": "ISRC {isrc} does not follow the 12-character format (CC-XXX-YY-NNNNN).",
    },
    "val.duracion_falta": {"es": "Sin duración.", "en": "No length."},
    "val.duracion_larga": {
        "es": "Dura {minutos} minutos: puede ser un mix o un álbum entero en un solo video, no un track.",
        "en": "It runs {minutos} minutes: it may be a mix or a whole album in one video, not a track.",
    },
    "val.titulo_con_ruido": {
        "es": "El título arrastra texto de YouTube, como (Official Video). Conviene limpiarlo.",
        "en": "The title carries YouTube text, such as (Official Video). Worth cleaning up.",
    },

    "val.isrc_duplicado": {
        "es": "el ISRC {isrc} está repetido: aparece en '{uno}' y en '{otro}'",
        "en": "ISRC {isrc} is repeated: it shows up in '{uno}' and in '{otro}'",
    },
    "val.upc_duplicado": {
        "es": "el UPC {upc} está repetido: lo usan '{uno}' y '{otro}'",
        "en": "UPC {upc} is repeated: it is used by '{uno}' and '{otro}'",
    },

    # ---- validar: el informe de texto que va en el ZIP ----------------------
    "val.rep_titulo": {
        "es": "VALIDACIÓN PRE-ENTREGA: {artista}",
        "en": "PRE-DELIVERY VALIDATION: {artista}",
    },
    "val.rep_generado": {"es": "Generado: {fecha}", "en": "Generated: {fecha}"},
    "val.rep_productos": {"es": "Productos revisados", "en": "Releases checked"},
    "val.rep_tracks": {"es": "Tracks revisados", "en": "Tracks checked"},
    "val.rep_errores": {"es": "Errores", "en": "Errors"},
    "val.rep_avisos": {"es": "Avisos", "en": "Warnings"},
    "val.rep_sin_errores": {
        "es": "Sin errores: el catálogo no tiene problemas que causen rechazo.",
        "en": "No errors: the catalog has nothing that would cause a rejection.",
    },
    "val.rep_con_errores_1": {
        "es": "! Hay errores que las distribuidoras suelen rechazar. Corregirlos",
        "en": "! There are errors distributors usually reject. Fix them",
    },
    "val.rep_con_errores_2": {
        "es": "  antes de la entrega.",
        "en": "  before delivering.",
    },
    "val.rep_h_errores": {"es": "ERRORES", "en": "ERRORS"},
    "val.rep_h_avisos": {"es": "AVISOS", "en": "WARNINGS"},
    "val.rep_catalogo": {"es": "(catálogo)", "en": "(catalog)"},

    # ---- paquete: cabeceras de las planillas --------------------------------
    # Estas SÍ se traducen: las lee el usuario. Las de la hoja de ingesta no,
    # porque son nombres de campo de la distribuidora (ver COLUMNAS_INGESTA).
    "paq.col_producto": {"es": "Producto", "en": "Release"},
    "paq.col_tipo": {"es": "Tipo", "en": "Type"},
    "paq.col_anio": {"es": "Año", "en": "Year"},
    "paq.col_track": {"es": "Track", "en": "Track"},
    "paq.col_duracion": {"es": "Duración", "en": "Length"},
    "paq.col_sello": {"es": "Sello", "en": "Label"},
    "paq.col_distribuidora": {"es": "Distribuidora", "en": "Distributor"},
    "paq.col_fuente": {"es": "Fuente / Calidad", "en": "Source / Quality"},
    "paq.col_archivo": {"es": "Archivo", "en": "File"},
    "paq.col_reproducciones": {"es": "Reproducciones", "en": "Plays"},
    "paq.col_url": {"es": "URL YouTube", "en": "YouTube URL"},

    # ---- paquete: nombres de archivo y de carpeta ---------------------------
    "paq.carpeta_raiz": {"es": "Migracion", "en": "Migration"},
    "paq.f_leeme": {"es": "_LEEME.txt", "en": "_READ ME.txt"},
    "paq.f_reporte": {"es": "_Reporte de migracion.txt", "en": "_Migration report.txt"},
    "paq.f_validacion": {"es": "_Validacion pre-entrega.txt", "en": "_Pre-delivery validation.txt"},
    "paq.f_catalogo": {"es": "_Catalogo completo.xlsx", "en": "_Full catalog.xlsx"},
    "paq.f_ingesta": {"es": "_Hoja de ingesta.csv", "en": "_Ingestion sheet.csv"},
    "paq.f_datos": {"es": "datos.xlsx", "en": "data.xlsx"},
    "paq.f_portada": {"es": "portada.jpg", "en": "cover.jpg"},

    # ---- paquete: el reporte de migración -----------------------------------
    "paq.rep_titulo": {
        "es": "REPORTE DE MIGRACIÓN: {artista}",
        "en": "MIGRATION REPORT: {artista}",
    },
    "paq.rep_generado": {"es": "Generado: {fecha}", "en": "Generated: {fecha}"},
    "paq.rep_productos": {"es": "Productos seleccionados", "en": "Releases selected"},
    "paq.rep_tracks": {"es": "Tracks totales", "en": "Tracks in total"},
    "paq.rep_con_isrc": {"es": "Con ISRC", "en": "With ISRC"},
    "paq.rep_con_upc": {"es": "Productos con UPC", "en": "Releases with UPC"},
    "paq.rep_portadas": {"es": "Portadas obtenidas", "en": "Covers obtained"},
    "paq.rep_audio": {"es": "AUDIO", "en": "AUDIO"},
    "paq.rep_aptos": {
        "es": "Aptos para entrega (FLAC lossless)",
        "en": "Fit for delivery (lossless FLAC)",
    },
    "paq.rep_referencia": {"es": "Sólo referencia (lossy)", "en": "Reference only (lossy)"},
    "paq.rep_sin_audio": {"es": "Sin audio", "en": "No audio"},
    "paq.rep_sin_tidal": {
        "es": ("! No se conectó una cuenta de Tidal, así que NO hay audio apto para\n"
               "  entrega. Todo el audio de este paquete es referencia lossy de\n"
               "  YouTube. Para una entrega real hace falta el máster original."),
        "en": ("! No Tidal account was connected, so there is NO audio fit for\n"
               "  delivery. Every audio file in this package is a lossy YouTube\n"
               "  reference. A real delivery needs the original master."),
    },
    "paq.rep_algunos_aac": {
        "es": ("! Algunos tracks bajaron en AAC y no en FLAC: Tidal no tiene máster\n"
               "  lossless para esas grabaciones. Están marcados como lossy y NO\n"
               "  son aptos para entrega, hay que pedir el máster al sello/artista."),
        "en": ("! Some tracks came down as AAC and not FLAC: Tidal has no lossless\n"
               "  master for those recordings. They are marked as lossy and are NOT\n"
               "  fit for delivery; ask the label or artist for the master."),
    },
    "paq.rep_pendientes": {"es": "PENDIENTES POR PRODUCTO", "en": "OPEN ITEMS BY RELEASE"},
    "paq.rep_sin_pendientes": {
        "es": "(ninguno: todos los productos quedaron completos)",
        "en": "(none: every release came out complete)",
    },
    "paq.rep_entorno": {"es": "ENTORNO", "en": "ENVIRONMENT"},
    "paq.si": {"es": "sí", "en": "yes"},
    "paq.no": {"es": "NO", "en": "NO"},

    "paq.falta_upc": {"es": "sin UPC", "en": "no UPC"},
    "paq.no_buscada": {"es": "no buscada", "en": "not looked up"},
    "paq.falta_portada": {"es": "sin portada ({motivo})", "en": "no cover ({motivo})"},
    "paq.falta_audio": {
        "es": "{n}/{total} tracks sin audio",
        "en": "{n}/{total} tracks with no audio",
    },
    "paq.falta_lossy": {
        "es": "{n} tracks sólo en calidad de referencia",
        "en": "{n} tracks at reference quality only",
    },
    "paq.falta_isrc": {"es": "{n} tracks sin ISRC", "en": "{n} tracks with no ISRC"},
    "paq.falta_orden": {
        "es": "orden de tracks sin confirmar (estimado por fecha de subida)",
        "en": "track order unconfirmed (estimated from the upload date)",
    },

    # ---- paquete: planillas -------------------------------------------------
    "paq.sin_audio": {"es": "sin audio", "en": "no audio"},
    "paq.hoja_catalogo": {"es": "Catálogo", "en": "Catalog"},
    "paq.hoja_producto": {"es": "Producto", "en": "Release"},
    "paq.maestra_titulo": {
        "es": "{artista}: Catálogo para migración",
        "en": "{artista}: Catalog for migration",
    },
    "paq.maestra_sub": {
        "es": "Generado el {fecha}, {productos} productos, {tracks} tracks",
        "en": "Generated on {fecha}, {productos} releases, {tracks} tracks",
    },
    "paq.producto_sub": {
        "es": "{tipo}, {anio}, UPC {upc}, {tracks} tracks",
        "en": "{tipo}, {anio}, UPC {upc}, {tracks} tracks",
    },
    "paq.sin_fecha": {"es": "s/f", "en": "n/d"},
    "paq.sin_upc_par": {"es": "(sin UPC)", "en": "(no UPC)"},

    # ---- paquete: el LEEME que va en la raíz del ZIP ------------------------
    "paq.leeme": {
        "es": """CÓMO ESTÁ ORGANIZADO ESTE PAQUETE
=================================

Una carpeta por producto (álbum / EP / single). Cada una trae:

  portada.jpg   La portada en la resolución más alta que tenía Apple Music
                (hasta 3000x3000).
  datos.xlsx    Los datos de ese producto: tracks, ISRC, UPC, sello, duración.
  NN - Tema.ext Los audios, numerados en el orden del release.

En la raíz:

  {catalogo}
      Todos los productos en una sola planilla.
  {ingesta}
      El archivo para cargar en la distribuidora nueva.
  {validacion}
      Qué va a ser rechazado y qué conviene revisar.
  {reporte}
      Qué se pudo obtener y qué quedó pendiente.

EMPEZÁ POR LA VALIDACIÓN
------------------------
Abrí primero "{validacion}". Separa dos cosas:

  ERRORES  La distribuidora los rechaza (código con formato inválido, dígito
           verificador mal, código duplicado, portada chica o no cuadrada).
           Hay que corregirlos antes de entregar.

  AVISOS   Pasan la ingesta pero conviene revisarlos (falta un ISRC o un UPC y
           se va a asignar uno nuevo, un título arrastra texto de YouTube).

SOBRE LA HOJA DE INGESTA
------------------------
"{ingesta}" trae las columnas estándar que aceptan o mapean casi todas las
distribuidoras, y sus nombres van en inglés a propósito: son los nombres de
campo que espera la distribuidora, no texto para leer. Lo que se pudo relevar
viene completo. Lo que no puede salir de fuentes públicas está marcado con
<<COMPLETAR>>:

  Genre, Language, Explicit, Composer, Publisher, C Line

Esos campos los tiene que llenar el dueño del catálogo, están marcados en vez
de vacíos o inventados justamente para que no pasen desapercibidos.

SOBRE LA CALIDAD DEL AUDIO: LEER ANTES DE ENTREGAR
---------------------------------------------------
La columna "Fuente / Calidad" de las planillas dice, track por track, de dónde
salió el audio:

  LOSSLESS (flac)  Máster lossless de Tidal. Apto para entregar.

  LOSSY (m4a/opus/webm)  Audio ya comprimido. Sirve como referencia, inventario
                o verificación, pero NO es apto para entregar a una
                distribuidora: se subiría con pérdida de calidad. Estos casos
                están resaltados en ámbar en la planilla.

Si un track figura como LOSSY, hay que conseguir el máster original con el
artista o el sello antes de la entrega. El reporte lista exactamente cuáles.

OTROS DATOS QUE SON ESTIMADOS
-----------------------------
YouTube no declara todo lo que necesita una ficha de release, así que dos campos
son aproximaciones y conviene verificarlos:

  Tipo (single/EP/álbum)  Se deduce de la cantidad de tracks (1-3 single,
                          4-6 EP, 7+ álbum). Un EP corto puede figurar como
                          single.

  Orden de los tracks     Cuando se pudo cruzar con Tidal por ISRC, el número
                          de track es el real. Si no, es un estimado por fecha
                          de subida y el reporte lo marca como "sin confirmar".
""",
        "en": """HOW THIS PACKAGE IS ORGANISED
=============================

One folder per release (album / EP / single). Each one holds:

  cover.jpg     The cover at the highest resolution Apple Music had
                (up to 3000x3000).
  data.xlsx     That release's data: tracks, ISRC, UPC, label, length.
  NN - Song.ext The audio files, numbered in release order.

In the root:

  {catalogo}
      Every release in a single spreadsheet.
  {ingesta}
      The file to load into the new distributor.
  {validacion}
      What will be rejected and what is worth reviewing.
  {reporte}
      What could be obtained and what is still open.

START WITH THE VALIDATION
-------------------------
Open "{validacion}" first. It separates two things:

  ERRORS    The distributor rejects these (badly formatted code, wrong check
            digit, duplicate code, cover too small or not square). They have to
            be fixed before delivering.

  WARNINGS  These pass ingestion but are worth reviewing (a missing ISRC or UPC
            that will get a new one assigned, a title carrying YouTube text).

ABOUT THE INGESTION SHEET
-------------------------
"{ingesta}" carries the standard columns that nearly every distributor accepts
or maps, and their names are in English on purpose: they are the field names
the distributor expects, not text to read. What could be surveyed comes filled
in. What cannot come from public sources is marked <<COMPLETAR>>:

  Genre, Language, Explicit, Composer, Publisher, C Line

Those fields have to be filled in by the catalog owner. They are marked rather
than left empty or made up precisely so they do not slip through.

ABOUT AUDIO QUALITY: READ BEFORE DELIVERING
-------------------------------------------
The "Source / Quality" column of the spreadsheets says, track by track, where
the audio came from:

  LOSSLESS (flac)  Lossless master from Tidal. Fit for delivery.

  LOSSY (m4a/opus/webm)  Already compressed audio. Useful as a reference, for
                inventory or for checking, but NOT fit for delivering to a
                distributor: it would be uploaded with quality already lost.
                These cases are highlighted in amber in the spreadsheet.

If a track shows as LOSSY, get the original master from the artist or the label
before delivering. The report lists exactly which ones.

OTHER DATA THAT IS ESTIMATED
----------------------------
YouTube does not state everything a release needs, so two fields are
approximations and are worth checking:

  Type (single/EP/album)  Worked out from the track count (1-3 single, 4-6 EP,
                          7+ album). A short EP can show up as a single.

  Track order             Where it could be cross-checked against Tidal by
                          ISRC, the track number is the real one. Otherwise it
                          is estimated from the upload date, and the report
                          marks it as "unconfirmed".
""",
    },
}
