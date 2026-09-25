# -*- coding: utf-8 -*-
"""
Textos de la app en español e inglés.

Todo lo que el usuario lee sale de acá: los mensajes del log, los errores, los
rótulos de las planillas y el contenido de los archivos que van adentro del ZIP.
La interfaz tiene su propio catálogo en `app/web/i18n.js`, porque se dibuja en el
navegador y pedirle cada rótulo al servidor sería absurdo.

Cómo se usa:

    from migrador.i18n import T
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


def _aplicar_forzado():
    """Deja puesto `MIGRADOR_IDIOMA` apenas se importa el módulo.

    Sin esto, la variable sólo tenía efecto cuando el servidor resolvía el
    idioma al atender /api/config, y todo lo que corriera antes salía en
    español: el `--diagnostico` del launcher, un script que importe `paquete`
    para armar un ZIP, cualquier uso del motor sin servidor. El README dice que
    `MIGRADOR_IDIOMA=en` alcanza para tener la app en inglés, y ahora es cierto
    también fuera del servidor.

    No se mira el locale del sistema acá a propósito: eso es el último escalón
    de la prioridad y lo resuelve `server.idioma_guardado()`, que primero tiene
    que poder ver la config del usuario y el idioma.txt del instalador.
    """
    forzado = idioma_forzado()
    if forzado:
        poner_idioma(forzado)


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

        v = locale.getlocale()[0] or ""
        if not v:
            # En Windows getlocale() devuelve None hasta que alguien llama a
            # setlocale. getdefaultlocale está deprecada pero es lo único que
            # contesta sin efectos de borde.
            import warnings

            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                v = locale.getdefaultlocale()[0] or ""
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
    except Exception:  # noqa: BLE001 (el locale del sistema varia por plataforma)
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
    # ---- errores de la YouTube Data API -------------------------------------
    # Lo que devuelve Google no está pensado para mostrarse: viene en inglés, con
    # jerga y a veces con HTML adentro. Acá está traducido y con la salida
    # concreta al lado.
    "yt.cuota_compartida": {
        "es": (
            "Se agotó el cupo diario de la API de YouTube. Si esta copia trae una "
            "clave compartida, el cupo se reparte entre todos los que la usan. "
            "Cargando tu propia clave tenés el cupo entero para vos, es gratis y se "
            "saca en tres pasos."
        ),
        "en": (
            "The YouTube API daily quota ran out. If this copy ships with a shared "
            "key, the quota is split across everyone using it. With your own key you "
            "get the whole quota to yourself; it is free and takes three steps."
        ),
    },
    "yt.cuota": {
        "es": (
            "Se agotó el cupo diario de la API de YouTube. Cargando tu propia clave "
            "tenés el cupo entero para vos, es gratis y se saca en tres pasos."
        ),
        "en": (
            "The YouTube API daily quota ran out. With your own key you get the whole "
            "quota to yourself; it is free and takes three steps."
        ),
    },
    "yt.rate_limit": {
        "es": (
            "YouTube está recibiendo demasiadas consultas seguidas desde esta clave. "
            "Esperá un minuto y probá de nuevo."
        ),
        "en": ("YouTube is getting too many requests in a row from this key. Wait a minute and try again."),
    },
    "yt.clave_invalida": {
        "es": (
            "YouTube rechazó la clave. Revisá que la hayas copiado entera y que sea "
            "una clave de API, no un ID de cliente."
        ),
        "en": (
            "YouTube turned the key down. Check that you copied it whole and that it "
            "is an API key, not a client ID."
        ),
    },
    "yt.api_sin_habilitar": {
        "es": (
            "El proyecto de esta clave no tiene habilitada la YouTube Data API v3. "
            "Entrá a Google Cloud Console, buscá esa API en la biblioteca y "
            "habilitala."
        ),
        "en": (
            "The project behind this key does not have YouTube Data API v3 enabled. "
            "Go to Google Cloud Console, find that API in the library and enable it."
        ),
    },
    "yt.clave_restringida": {
        "es": (
            "Las restricciones de esta clave no permiten usarla desde esta "
            "computadora. En Google Cloud Console, dejá la restricción de "
            "aplicación en «Ninguna» y restringila sólo por API."
        ),
        "en": (
            "This key's restrictions do not allow using it from this computer. In "
            'Google Cloud Console, set the application restriction to "None" and '
            "restrict it by API only."
        ),
    },
    "yt.prohibido": {
        "es": "YouTube no permitió la consulta con esta clave.",
        "en": "YouTube did not allow the request with this key.",
    },
    "yt.error_generico": {
        "es": "YouTube respondió un error ({codigo}). {mensaje}",
        "en": "YouTube answered with an error ({codigo}). {mensaje}",
    },
    "yt.sin_conexion": {
        "es": "No pude hablar con la API de YouTube. Revisá que haya conexión a internet. ({detalle})",
        "en": "Could not reach the YouTube API. Check that there is an internet connection. ({detalle})",
    },
    "yt.sin_respuesta": {
        "es": "No pude hablar con la API de YouTube. ({detalle})",
        "en": "Could not reach the YouTube API. ({detalle})",
    },
    "yt.url_no_reconocida": {
        "es": (
            "No pude sacar el canal de ese link. Sirve el link del canal (con @nombre o con "
            "/channel/UC…) o el de cualquier tema del artista."
        ),
        "en": (
            "Could not work out the channel from that link. Use the channel link (with @name "
            "or /channel/UC…) or the link of any of the artist's songs."
        ),
    },
    "yt.video_no_encontrado": {
        "es": "No encontré ese tema en YouTube. Revisá el link, o pegá el del canal.",
        "en": "Could not find that song on YouTube. Check the link, or paste the channel's.",
    },
    "yt.canal_no_encontrado": {
        "es": "No se encontró el canal ({canal}). Revisá la URL.",
        "en": "Channel not found ({canal}). Check the URL.",
    },
    "yt.falta_clave": {
        "es": "Falta la API key de YouTube en el servidor.",
        "en": "The YouTube API key is missing on the server.",
    },
    "yt.canal_vacio": {
        "es": "El canal no tiene productos para relevar.",
        "en": "The channel has no releases to survey.",
    },
    "yt.sin_lanzamientos": {
        "es": (
            "No encontré lanzamientos en este canal: ninguno de sus {n} videos tiene "
            "la descripción auto-generada de YouTube (la que dice «Provided to "
            "YouTube by»). Eso pasa cuando el canal es un OAC con videos subidos a "
            "mano. Probá pegando el link del canal «<artista> - Topic», que es el "
            "que YouTube genera solo con el catálogo distribuido."
        ),
        "en": (
            "No releases found on this channel: none of its {n} videos carries "
            "YouTube's auto-generated description (the one that says \"Provided to "
            'YouTube by"). That happens when the channel is an official artist '
            "channel with hand-uploaded videos. Try pasting the link to the "
            '"<artist> - Topic" channel, the one YouTube builds on its own from '
            "the distributed catalog."
        ),
    },
    # ---- relevamiento: el log del trabajo -----------------------------------
    "rel.resolviendo": {"es": "Resolviendo canal…", "en": "Working out the channel…"},
    "rel.buscando_topic": {
        "es": "El canal no es un Topic: buscando el Topic del artista…",
        "en": "This is not a Topic channel: looking up the artist's Topic…",
    },
    "rel.uso_topic": {"es": "Uso el canal Topic: {canal}", "en": "Using the Topic channel: {canal}"},
    "rel.listando": {"es": "Listando productos…", "en": "Listing releases…"},
    "rel.bajando_metadata": {
        "es": "Bajando metadata de {n} productos…",
        "en": "Fetching metadata for {n} releases…",
    },
    "rel.descartados": {
        "es": "Descarté {n} videos que no son lanzamientos.",
        "en": "Left out {n} videos that are not releases.",
    },
    "rel.buscando_codigos": {
        "es": "Buscando códigos ISRC y UPC (Deezer)…",
        "en": "Looking up ISRC and UPC codes (Deezer)…",
    },
    "rel.armando_excel": {"es": "Armando el Excel…", "en": "Building the spreadsheet…"},
    "rel.deezer_resultado": {
        "es": "Deezer: códigos para {matched} de {n} tracks, UPC de {albumes} álbumes",
        "en": "Deezer: codes for {matched} of {n} tracks, UPC for {albumes} albums",
    },
    "rel.musicbrainz": {
        "es": "MusicBrainz (respaldo): {n} sin ISRC",
        "en": "MusicBrainz (fallback): {n} without ISRC",
    },
    # ---- orquestador --------------------------------------------------------
    "mig.agrupados": {
        "es": "{productos} productos a partir de {tracks} tracks",
        "en": "{productos} releases out of {tracks} tracks",
    },
    "mig.via_topic": {
        "es": "Pegaste «{pedido}»; se relevó su Topic, «{topic}»",
        "en": 'You pasted "{pedido}"; its Topic was surveyed instead, "{topic}"',
    },
    "mig.descartados": {
        "es": "Quedaron afuera {n} videos que no son lanzamientos",
        "en": "{n} videos were left out because they are not releases",
    },
    "mig.seleccionados": {
        "es": "Seleccionados {n} de {total} productos",
        "en": "{n} of {total} releases selected",
    },
    "mig.seleccion_vacia": {
        "es": "La selección quedó vacía: revisá los filtros.",
        "en": "The selection came out empty: check the filters.",
    },
    "mig.falta_ffmpeg": {
        "es": "Audio: falta ffmpeg: no puedo extraer FLAC. Revisá la instalación.",
        "en": "Audio: ffmpeg is missing, so FLAC cannot be extracted. Check the install.",
    },
    "mig.sin_tidal": {
        "es": "Audio: sin cuenta de Tidal conectada: el audio será de referencia (lossy)",
        "en": "Audio: no Tidal account connected, so the audio will be a lossy reference",
    },
    "mig.sin_referencia": {
        "es": "Audio: falta yt-dlp o ffmpeg: no puedo bajar ni la referencia",
        "en": "Audio: yt-dlp or ffmpeg is missing, so not even the reference can be downloaded",
    },
    # ---- audio --------------------------------------------------------------
    "aud.codigo_expiro": {
        "es": "[tidal] el código expiró sin confirmación",
        "en": "[tidal] the code expired without confirmation",
    },
    "aud.sin_cuenta": {
        "es": "La cuenta de Tidal no está conectada.",
        "en": "The Tidal account is not connected.",
    },
    "aud.sesion_vencida": {
        "es": "La sesión de Tidal no es válida o venció. Volvé a conectar la cuenta.",
        "en": "The Tidal session is not valid or has expired. Connect the account again.",
    },
    "aud.artista_no_encontrado": {
        "es": (
            "[tidal] no encontré a '{artista}' en el catálogo de Tidal. Si el nombre "
            "difiere del de Tidal, el match por ISRC no se puede armar."
        ),
        "en": (
            "[tidal] could not find '{artista}' in Tidal's catalog. If the name differs "
            "from Tidal's, the ISRC match cannot be built."
        ),
    },
    "aud.no_pude_listar": {
        "es": "[tidal] no pude listar {filtro}: {error}",
        "en": "[tidal] could not list {filtro}: {error}",
    },
    "aud.releases": {
        "es": "[tidal] releases en la discografía: {n}",
        "en": "[tidal] releases in the discography: {n}",
    },
    "aud.indice": {
        "es": "[tidal] índice armado: {isrc} ISRC en {releases} releases",
        "en": "[tidal] index built: {isrc} ISRCs across {releases} releases",
    },
    "aud.match": {
        "es": "[tidal] match por ISRC: {hit} encontrados, {miss} sin match, "
        "{sin_isrc} sin ISRC en el relevamiento",
        "en": "[tidal] ISRC match: {hit} found, {miss} unmatched, {sin_isrc} with no ISRC in the survey",
    },
    "aud.fallo_descarga": {
        "es": "falló la descarga",
        "en": "the download failed",
    },
    "aud.sin_ytdlp": {"es": "yt-dlp no está instalado", "en": "yt-dlp is not installed"},
    "aud.timeout": {"es": "tardó demasiado y se canceló", "en": "it took too long and was cancelled"},
    "aud.sin_archivo": {
        "es": "yt-dlp terminó pero no dejó ningún archivo",
        "en": "yt-dlp finished but left no file",
    },
    "aud.listos": {
        "es": "[audio] listos: {aptos} aptos para entrega, {ref} de referencia, {sin} sin audio",
        "en": "[audio] done: {aptos} fit for delivery, {ref} reference, {sin} with no audio",
    },
    # ---- servidor -----------------------------------------------------------
    "srv.aceptar_terminos": {
        "es": "Hay que aceptar los términos para usar la herramienta.",
        "en": "You have to accept the terms to use the tool.",
    },
    "srv.pega_clave": {
        "es": "Pegá la clave de la API de YouTube.",
        "en": "Paste the YouTube API key.",
    },
    "srv.clave_rara": {
        "es": "Eso no parece una clave de API.",
        "en": "That does not look like an API key.",
    },
    "srv.clave_no_funciono": {
        "es": "La clave no funcionó. {error}",
        "en": "The key did not work. {error}",
    },
    "srv.trabajo_en_curso": {
        "es": "Ya hay un trabajo en curso. Esperá a que termine o cancelalo.",
        "en": "There is already a job running. Wait for it to finish or cancel it.",
    },
    "srv.falta_clave": {
        "es": "Falta configurar la clave de la API de YouTube.",
        "en": "The YouTube API key has not been set up.",
    },
    "srv.poco_espacio": {
        "es": (
            "Queda poco espacio en disco ({libre} GB libres) y este paquete necesita al "
            "menos {minimo} GB. Liberá espacio y probá de nuevo."
        ),
        "en": (
            "Disk space is running low ({libre} GB free) and this package needs at least "
            "{minimo} GB. Free up space and try again."
        ),
    },
    "srv.elegi_algo": {
        "es": "Elegí al menos una cosa para descargar.",
        "en": "Pick at least one thing to download.",
    },
    "srv.sin_seleccion": {
        "es": "No hay productos seleccionados.",
        "en": "No releases are selected.",
    },
    "srv.paquete_listo": {"es": "Paquete listo.", "en": "Package ready."},
    "srv.armando_zip": {"es": "Armando el ZIP", "en": "Building the ZIP"},
    "srv.audio_desactivado": {
        "es": "El módulo de audio está desactivado.",
        "en": "The audio module is turned off.",
    },
    "srv.sin_tidal_en_curso": {
        "es": "No hay una conexión de Tidal en curso.",
        "en": "There is no Tidal connection in progress.",
    },
    "srv.content_length": {
        "es": "El pedido trae un Content-Length inválido.",
        "en": "The request has an invalid Content-Length.",
    },
    "srv.pedido_grande": {"es": "El pedido es demasiado grande.", "en": "The request is too large."},
    "srv.pedido_cortado": {"es": "El pedido llegó cortado.", "en": "The request arrived truncated."},
    "srv.json_invalido": {"es": "El pedido no es JSON válido.", "en": "The request is not valid JSON."},
    "srv.json_no_objeto": {
        "es": "El pedido tiene que ser un objeto JSON.",
        "en": "The request has to be a JSON object.",
    },
    "srv.sin_catalogo": {"es": "No hay un catálogo cargado.", "en": "No catalog is loaded."},
    "srv.zip_vencido": {
        "es": "El paquete ya no está disponible. Generalo de nuevo.",
        "en": "The package is no longer available. Build it again.",
    },
    "srv.trabajo_no_existe": {"es": "Ese trabajo ya no existe.", "en": "That job no longer exists."},
    "srv.rechazado": {"es": "Pedido rechazado.", "en": "Request rejected."},
    "srv.rechazado_token": {
        "es": "Pedido rechazado. Recargá la app.",
        "en": "Request rejected. Reload the app.",
    },
    "srv.no_encontrado": {"es": "No encontrado.", "en": "Not found."},
    "srv.inesperado": {"es": "Error inesperado. {error}", "en": "Unexpected error. {error}"},
    "srv.falta_index": {"es": "Falta index.html.", "en": "index.html is missing."},
    # ---- trabajos -----------------------------------------------------------
    "job.error": {"es": "Hubo un error.", "en": "Something went wrong."},
    # ---- launcher -----------------------------------------------------------
    # El cuerpo del reporte de `--diagnostico` queda en español a propósito: no
    # es algo que se lea en el uso normal, es un volcado técnico para pegar en un
    # issue, y quien lo lee del otro lado es el autor.
    "app.nombre": {"es": "Migrador de Catálogos", "en": "Catalog Migrator"},
    "lau.h_puerto": {
        "es": "Puerto local. 0 = elegir uno libre (recomendado).",
        "en": "Local port. 0 = pick a free one (recommended).",
    },
    "lau.h_no_abrir": {
        "es": "No abrir la interfaz; sólo dejar el servidor escuchando.",
        "en": "Do not open the interface; just leave the server listening.",
    },
    "lau.h_navegador": {
        "es": "Abrir en el navegador normal, con pestañas y barra de direcciones.",
        "en": "Open in the regular browser, with tabs and an address bar.",
    },
    "lau.h_sin_ventana": {
        "es": "No usar la ventana propia; abrir con el motor web del sistema.",
        "en": "Do not use the app's own window; open with the system web engine.",
    },
    "lau.h_diagnostico": {
        "es": "Escribir un reporte de qué puede hacer la app y salir.",
        "en": "Write a report of what the app can do here, and exit.",
    },
    # Etiquetas del reporte de --diagnostico. El README pide mandarlo cuando algo
    # no arranca, asi que se lee, y tiene que leerse en el idioma de quien lo abre.
    "diag.fecha": {"es": "fecha", "en": "date"},
    "diag.plataforma": {"es": "plataforma", "en": "platform"},
    "diag.empaquetado": {"es": "empaquetado", "en": "packaged"},
    "diag.url": {"es": "url local", "en": "local url"},
    "diag.clave": {"es": "clave de YouTube configurada", "en": "YouTube key configured"},
    "diag.audio": {"es": "modulo de audio", "en": "audio module"},
    "diag.entorno": {"es": "entorno de audio:", "en": "audio environment:"},
    "diag.ventana": {"es": "ventana:", "en": "window:"},
    "diag.pywebview_ok": {"es": "  pywebview importa: si", "en": "  pywebview imports: yes"},
    "diag.pywebview_no": {
        "es": "  pywebview importa: no ({error})",
        "en": "  pywebview imports: no ({error})",
    },
    "diag.prueba_ventana": {
        "es": "  abrir una ventana de prueba: {resultado}",
        "en": "  open a test window: {resultado}",
    },
    "diag.abrio_si": {"es": "si", "en": "yes"},
    "diag.abrio_no": {"es": "no abrio", "en": "did not open"},
    "diag.prueba_fallo": {
        "es": "  abrir una ventana de prueba: FALLO ({tipo}: {error})",
        "en": "  open a test window: FAILED ({tipo}: {error})",
    },
    "diag.titulo_prueba": {"es": "Prueba de ventana", "en": "Window test"},
    "diag.detalle": {"es": "  detalle: {detalle}", "en": "  detail: {detalle}"},
    "diag.guardado": {"es": "Guardado en: {ruta}", "en": "Saved to: {ruta}"},
    "lau.ctrl_c": {"es": "Ctrl+C para cerrar.", "en": "Ctrl+C to close."},
    "lau.cerrando": {"es": "Cerrando…", "en": "Closing…"},
    "lau.escuchando": {"es": "Escuchando en {url}", "en": "Listening on {url}"},
    "lau.primera_vez": {
        "es": "Primera vez: la app te va a pedir la clave de la API de YouTube.",
        "en": "First run: the app will ask you for the YouTube API key.",
    },
    "lau.ventana_propia": {
        "es": "Abrí la app en su propia ventana. Cerrala para terminar.",
        "en": "Opened the app in its own window. Close it to finish.",
    },
    "lau.en_navegador": {
        "es": "Abrí la app en tu navegador. Ctrl+C acá para cerrarla.",
        "en": "Opened the app in your browser. Ctrl+C here to close it.",
    },
    "lau.no_arranco": {
        "es": "No se pudo iniciar la app: {error}",
        "en": "Could not start the app: {error}",
    },
    "lau.detalle_en": {"es": "El detalle quedó en: {ruta}", "en": "The detail is in: {ruta}"},
    # ---- portadas -----------------------------------------------------------
    # `cover_status` se muestra en el log y dentro del aviso "Sin portada: …",
    # así que se traduce. No se compara contra su texto en ningún lado.
    "por.sin_match": {"es": "no está en Apple Music", "en": "not on Apple Music"},
    "por.fallo_descarga": {
        "es": "está en Apple Music pero falló la descarga",
        "en": "it is on Apple Music but the download failed",
    },
    "por.bajo_minimo": {
        "es": "{px}x{px}, DEBAJO DEL MINIMO de ingesta ({min}x{min})",
        "en": "{px}x{px}, BELOW THE INGESTION MINIMUM ({min}x{min})",
    },
    "por.maximo_apple": {
        "es": "{px}x{px}, el máximo que tiene Apple",
        "en": "{px}x{px}, the largest Apple has",
    },
    "por.una": {
        "es": "Portada {i} de {total}, {titulo}: {estado}",
        "en": "Cover {i} of {total}, {titulo}: {estado}",
    },
    "por.total": {"es": "Portadas: {ok} de {total}", "en": "Covers: {ok} of {total}"},
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
    "val.upc_no_verificado": {
        "es": (
            "Sin UPC. Deezer tiene estos temas en «{album}», que no parece este release, así que "
            "no se usó su UPC: habría sido el código de otro producto. Pedile el UPC de éste a tu "
            "distribuidora actual."
        ),
        "en": (
            'No UPC. Deezer has these songs on "{album}", which does not look like this release, '
            "so its UPC was not used: it would have been another release's code. Ask your current "
            "distributor for this one's UPC."
        ),
    },
    "val.upc_mezclado": {
        "es": (
            "Los tracks de este producto aparecen en Deezer bajo UPC distintos ({upcs}). "
            "Verificá cuál es el de este release antes de entregar."
        ),
        "en": (
            "The tracks of this release show up on Deezer under different UPCs ({upcs}). "
            "Check which one is this release's before delivering."
        ),
    },
    "val.release_en_dos_distribuidoras": {
        "es": (
            "Este release está en vivo en más de una distribuidora: {esta} y {otras}. Es lo normal a "
            "mitad de una migración, pero no para siempre: dalo de baja en la vieja recién cuando el "
            "nuevo esté publicado, y migrá uno solo de los dos."
        ),
        "en": (
            "This release is live at more than one distributor: {esta} and {otras}. That is normal "
            "halfway through a migration, but not forever: take it down at the old one only once the "
            "new one is live, and migrate just one of the two."
        ),
    },
    "val.artista_no_principal": {
        "es": (
            "El artista principal de este tema es {principal}, no {artista}. Puede ser un "
            "feat. en el disco de otro o un compilado: verificá quién controla el master antes "
            "de migrarlo."
        ),
        "en": (
            "This song's main artist is {principal}, not {artista}. It may be a feature on "
            "someone else's record or a compilation: check who controls the master before "
            "migrating it."
        ),
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
    "val.texto_como_formula": {
        "es": (
            "El texto empieza como una fórmula de planilla. En la hoja de ingesta va con un "
            "apóstrofo adelante para que no se ejecute al abrirla: revisá que el dato sea ése."
        ),
        "en": (
            "The text starts like a spreadsheet formula. In the ingestion sheet it carries a "
            "leading apostrophe so it does not run when opened: check that the value is right."
        ),
    },
    "val.titulo_con_ruido": {
        "es": "El título arrastra texto de YouTube, como (Official Video). Conviene limpiarlo.",
        "en": "The title carries YouTube text, such as (Official Video). Worth cleaning up.",
    },
    "val.isrc_duplicado": {
        "es": "el ISRC {isrc} está repetido adentro del mismo producto: aparece en '{uno}' y en '{otro}'",
        "en": "ISRC {isrc} is repeated within the same release: it shows up in '{uno}' and in '{otro}'",
    },
    # La misma grabación en dos releases, con el mismo código, es lo correcto:
    # el mensaje tiene que decir que se conserve, porque la salida obvia de un
    # «repetido» es pedir uno nuevo y eso parte el historial.
    "val.isrc_compartido": {
        "es": (
            "La misma grabación está en '{uno}' y en '{otro}', con el mismo ISRC ({isrc}). "
            "Es lo esperable si salió como single y después en el álbum: conservá el código, "
            "que es lo que mantiene su historial."
        ),
        "en": (
            "The same recording is in '{uno}' and in '{otro}', with the same ISRC ({isrc}). "
            "That is expected if it came out as a single and later on the album: keep the "
            "code, it is what preserves its history."
        ),
    },
    "val.isrc_match_dudoso": {
        "es": (
            "El ISRC {isrc} aparece en '{uno}' y en '{otro}', que no parecen la misma grabación "
            "(cambia el título o la duración). Lo más probable es que uno de los dos venga de una "
            "coincidencia equivocada: verificalo antes de entregar."
        ),
        "en": (
            "ISRC {isrc} shows up in '{uno}' and in '{otro}', which do not look like the same "
            "recording (the title or the length differ). Most likely one of them comes from a "
            "wrong match: check it before delivering."
        ),
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
    "paq.log_carpeta": {"es": "Carpeta {carpeta}", "en": "Folder {carpeta}"},
    "paq.log_zip_listo": {"es": "ZIP listo, {mb} MB", "en": "ZIP ready, {mb} MB"},
    # Va pegado al nombre del archivo de audio: es la última barrera para que un
    # lossy no se entregue por error, así que también tiene que leerse.
    "paq.tag_lossy": {"es": "[REFERENCIA-LOSSY]", "en": "[REFERENCE-LOSSY]"},
    # Va en el NOMBRE del archivo que se baja, asi que sin acentos ni espacios.
    "paq.f_zip_sufijo": {"es": "migracion", "en": "migration"},
    "paq.f_leeme": {"es": "_LEEME.txt", "en": "_READ ME.txt"},
    "paq.f_reporte": {"es": "_Reporte de migracion.txt", "en": "_Migration report.txt"},
    "paq.f_validacion": {"es": "_Validacion pre-entrega.txt", "en": "_Pre-delivery validation.txt"},
    "paq.f_catalogo": {"es": "_Catalogo completo.xlsx", "en": "_Full catalog.xlsx"},
    "paq.f_ingesta": {"es": "_Hoja de ingesta.csv", "en": "_Ingestion sheet.csv"},
    "paq.f_ingesta_xlsx": {"es": "_Hoja de ingesta.xlsx", "en": "_Ingestion sheet.xlsx"},
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
        "es": (
            "! No se conectó una cuenta de Tidal, así que NO hay audio apto para\n"
            "  entrega. Todo el audio de este paquete es referencia lossy de\n"
            "  YouTube. Para una entrega real hace falta el máster original."
        ),
        "en": (
            "! No Tidal account was connected, so there is NO audio fit for\n"
            "  delivery. Every audio file in this package is a lossy YouTube\n"
            "  reference. A real delivery needs the original master."
        ),
    },
    "paq.rep_algunos_aac": {
        "es": (
            "! Algunos tracks bajaron en AAC y no en FLAC: Tidal no tiene máster\n"
            "  lossless para esas grabaciones. Están marcados como lossy y NO\n"
            "  son aptos para entrega, hay que pedir el máster al sello/artista."
        ),
        "en": (
            "! Some tracks came down as AAC and not FLAC: Tidal has no lossless\n"
            "  master for those recordings. They are marked as lossy and are NOT\n"
            "  fit for delivery; ask the label or artist for the master."
        ),
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
    "paq.hoja_ingesta": {"es": "Ingesta", "en": "Ingestion"},
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
  {ingesta_xlsx}
      La misma hoja en Excel, para completar lo que falta.
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
"{ingesta}" trae las columnas estándar que aceptan o
mapean casi todas las distribuidoras, y sus nombres van en inglés a
propósito: son los nombres de campo que espera la distribuidora, no texto
para leer. Lo que se pudo relevar viene completo. Lo que no puede salir de
fuentes públicas está marcado con <<COMPLETAR>>:

  Genre, Language, Explicit, C Line, Territories

y "Disc Number" cuando el disco no se pudo confirmar. Territories va a
completar porque los derechos del release original no salen de ningún lado
público: ponerle "Worldwide" por defecto abriría al mundo un catálogo
licenciado sólo para una región.

Esos campos los tiene que llenar el dueño del catálogo, están marcados en vez
de vacíos o inventados justamente para que no pasen desapercibidos.

NO EDITES EL CSV CON EXCEL. Al abrirlo, Excel convierte el UPC en un número
(pierde el cero de adelante y lo muestra como 8,86E+11), lee "3:20" como una
hora y, con la configuración en castellano, mete todo en una sola columna. Si
lo guardás así, la hoja queda rota. Para completar lo que falta usá
"{ingesta_xlsx}", que trae las mismas filas con todo como texto y lo que falta
resaltado; si tu distribuidora carga CSV, exportalo desde ahí como "CSV UTF-8".

La distribuidora puede pedir campos que la hoja no trae porque no salen de
ningún lado público: número de catálogo, subgénero, versión del título, año de
la línea C. Si los pide, agregalos a mano.

"P Line" es la línea ℗ tal como la publicó la distribuidora original, y
"Label" es su titular, sin la licencia ("under exclusive license to…"). Para un
artista independiente el titular suele ser el propio artista, y no siempre es
el sello con el que va a salir en la distribuidora nueva: revisalo.

Composer, Lyricist, Producer y Publisher vienen de los créditos que publica
YouTube en cada tema, cuando la distribuidora original los mandó; si no, van
en <<COMPLETAR>>. Verificá que sean los nombres legales que pide la
distribuidora nueva. "Additional Artists" trae los otros artistas que YouTube
nombra en el tema, sin decir si son invitados (feat.) o artistas principales:
revisalo antes de cargar.

Las dos fechas, "Release Date" y "Original Release Date", traen la fecha real
del lanzamiento, que YouTube publica en cada tema. En una migración el release
conserva su fecha; si la distribuidora nueva te pide otra fecha de salida, esa
va en "Release Date". Cuando YouTube no la trae, quedan en <<COMPLETAR>>: la
fecha de subida del video no es la del lanzamiento.

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

  Orden de los tracks     Cuando Deezer tiene el álbum y es el mismo release,
                          o cuando se pudo cruzar con Tidal por ISRC, el número
                          de track es el real. Si no, es un estimado por fecha
                          de subida: la columna "Track Order" de la hoja de
                          ingesta dice cuál es cuál, y el reporte lo marca como
                          "sin confirmar".
""",
        "en": """HOW THIS PACKAGE IS ORGANIZED
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
  {ingesta_xlsx}
      The same sheet in Excel, to fill in what is missing.
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
"{ingesta}" carries the standard columns that nearly
every distributor accepts or maps, and their names are in English on
purpose: they are the field names the distributor expects, not text to
read. What could be surveyed comes filled in. What cannot come from public
sources is marked <<COMPLETAR>>:

  Genre, Language, Explicit, C Line, Territories

and "Disc Number" when the disc could not be confirmed. Territories is to be
filled in because the original release's rights do not come from anywhere
public: defaulting to "Worldwide" would open to the whole world a catalog
licensed for a single region.

Those fields have to be filled in by the catalog owner. They are marked rather
than left empty or made up precisely so they do not slip through.

DO NOT EDIT THE CSV IN EXCEL. When it opens it, Excel turns the UPC into a
number (it drops the leading zero and shows it as 8.86E+11), reads "3:20" as a
time and, with some regional settings, puts everything in a single column. If
you save it like that, the sheet is broken. To fill in what is missing use
"{ingesta_xlsx}", which has the same rows with everything as text and what is
missing highlighted; if your distributor loads CSV, export it from there as
"CSV UTF-8".

The distributor may ask for fields the sheet does not carry because they do not
come from anywhere public: catalog number, subgenre, title version, C line
year. If it asks, add them by hand.

"P Line" is the ℗ line exactly as the original distributor published it, and
"Label" is its holder, without the license ("under exclusive license to…"). For
an independent artist the holder is often the artist themselves, and not always
the label the release will go out under at the new distributor: review it.

Composer, Lyricist, Producer and Publisher come from the credits YouTube
publishes for each song, when the original distributor sent them; otherwise
they are <<COMPLETAR>>. Check that they are the legal names the new
distributor asks for. "Additional Artists" carries the other artists YouTube
names on the song, without saying whether they are featured (feat.) or main
artists: review it before loading.

Both dates, "Release Date" and "Original Release Date", carry the real release
date, which YouTube publishes for every song. In a migration the release keeps
its date; if the new distributor asks you for a different go-live date, that one
goes in "Release Date". When YouTube does not have it, they stay as
<<COMPLETAR>>: the video's upload date is not the release date.

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

  Track order             When Deezer has the album and it is the same
                          release, or where it could be cross-checked against
                          Tidal by ISRC, the track number is the real one.
                          Otherwise it is estimated from the upload date: the
                          "Track Order" column of the ingestion sheet says which
                          is which, and the report marks it as "unconfirmed".
""",
    },
}


_aplicar_forzado()
