"""
relevar_core.py: Motor de relevamiento de catálogos (sin CLI), para la app web.

Toma la URL de un canal de YouTube (Topic / Official Artist Channel / @handle),
enumera sus productos vía la YouTube Data API, opcionalmente enriquece con Deezer
(ISRC + UPC; MusicBrainz como respaldo opcional) y devuelve los productos como
datos. El Excel lo arma `paquete.py` con esos datos: acá no se escribe ninguna
planilla. Las claves se pasan como parámetros (la app las toma de sus secrets),
no se leen de archivos.

Función principal: relevar(url, yt_key, with_codes, progress) -> dict.
"""

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from difflib import SequenceMatcher

from .contratos import Creditos, DescripcionParseada, Relevamiento, Track
from .i18n import T
from .productos import SIN_ALBUM, SIN_DATOS
from .texto import comparable, marcas_version, misma_version, sin_decorado
from .texto import plegado as _normalize

API = "https://www.googleapis.com/youtube/v3"


class RelevarError(Exception):
    """Error de negocio (canal no encontrado, clave inválida, etc.) para mostrar al usuario.

    `codigo` clasifica el error para que la interfaz pueda ofrecer la salida que
    corresponde en vez de sólo mostrar un texto. Hoy se usa "cuota", que es el
    único caso donde la app puede proponer algo concreto: cargar una clave
    propia.
    """

    def __init__(self, mensaje, codigo=""):
        super().__init__(mensaje)
        self.codigo = codigo


# ============================================================
# Llamadas a la API
# ============================================================

# Errores de YouTube que son del momento y no del pedido. Reintentar tiene
# sentido; con 403 (cuota agotada, clave invalida) o 404 no lo tiene.
_HTTP_REINTENTABLE = (500, 502, 503, 504)


def api_get(endpoint, params, key, intentos=3):
    """GET a la YouTube Data API, con reintento ante fallas pasajeras.

    Un relevamiento son decenas de pedidos encadenados. Sin reintento, un 503
    suelto o un corte de red de dos segundos tiraba abajo el trabajo entero
    despues de varios minutos de avance, y el usuario tenia que empezar de cero
    gastando la cuota otra vez.
    """
    # La clave va en una cabecera y no en la URL. En la URL, cualquier error que
    # la citara (una excepción de urllib, un traceback en el log del trabajo, un
    # reporte) la llevaba con ella; hoy no hay ninguno que lo haga, y así no
    # puede haberlo. Google acepta `X-Goog-Api-Key` igual que `?key=`.
    url = f"{API}/{endpoint}?{urllib.parse.urlencode(params)}"
    ultimo = None
    for intento in range(intentos):
        req = urllib.request.Request(url, headers={"Accept": "application/json", "X-Goog-Api-Key": key})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "ignore")
            if e.code in _HTTP_REINTENTABLE and intento < intentos - 1:
                time.sleep(1.5 * (intento + 1))
                continue
            raise _error_de_youtube(e.code, body) from e
        except (urllib.error.URLError, TimeoutError, ValueError) as e:
            # URLError cubre DNS y conexion; ValueError, una respuesta que no es
            # JSON (un portal cautivo devolviendo HTML, por ejemplo).
            ultimo = e
            if intento < intentos - 1:
                time.sleep(1.5 * (intento + 1))
                continue
            raise RelevarError(T("yt.sin_conexion", detalle=f"{type(e).__name__}: {e}")) from e
    raise RelevarError(T("yt.sin_respuesta", detalle=ultimo))


# Lo que devuelve Google no está pensado para mostrarse: viene en inglés, con
# jerga y a veces con HTML adentro. Estos son los casos que de verdad le pasan a
# un usuario, traducidos y con la salida concreta al lado.
#
# Se guarda la clave del texto y no el texto: el idioma se elige en caliente y
# un diccionario armado al importar el módulo quedaría congelado en el que
# hubiera al arrancar.
_MOTIVOS_YOUTUBE = {
    "quotaExceeded": ("cuota", "yt.cuota_compartida"),
    "dailyLimitExceeded": ("cuota", "yt.cuota"),
    "rateLimitExceeded": ("", "yt.rate_limit"),
    "keyInvalid": ("clave", "yt.clave_invalida"),
    "accessNotConfigured": ("clave", "yt.api_sin_habilitar"),
    "ipRefererBlocked": ("clave", "yt.clave_restringida"),
    "forbidden": ("", "yt.prohibido"),
}


def _error_de_youtube(codigo_http, body):
    """Convierte un error de la API en algo que se pueda mostrar y accionar."""
    motivo, mensaje = "", ""
    # Acotado y no `except Exception`, que es lo que había: acá no hay red ni
    # una librería de por medio, sólo se navega un JSON, y las formas de que
    # falle se pueden enumerar. Un cuerpo que no es JSON o un `error` que no es
    # un diccionario dan ValueError, KeyError, TypeError o AttributeError; se
    # sigue sin motivo y abajo se muestra el texto crudo, que es lo correcto.
    # Cualquier otra excepción acá sería un error nuestro y tiene que verse.
    try:
        err = json.loads(body)["error"]
        mensaje = err.get("message") or ""
        errores = err.get("errors") or []
        if errores:
            motivo = errores[0].get("reason") or ""
    except (ValueError, KeyError, TypeError, AttributeError):
        pass

    if motivo in _MOTIVOS_YOUTUBE:
        codigo, clave = _MOTIVOS_YOUTUBE[motivo]
        return RelevarError(T(clave), codigo)

    if codigo_http == 400 and "API key not valid" in mensaje:
        return RelevarError(T(_MOTIVOS_YOUTUBE["keyInvalid"][1]), "clave")

    # Sin traducción conocida mostramos lo de Google, pero limpio: el texto suele
    # traer un <a href> adentro que en la interfaz se vería como HTML crudo.
    mensaje = re.sub(r"<[^>]+>", "", mensaje).strip() or body[:200]
    return RelevarError(T("yt.error_generico", codigo=codigo_http, mensaje=mensaje))


_RE_ID_CANAL = re.compile(r"^UC[\w-]{22}$")
_RE_ID_VIDEO = re.compile(r"^[\w-]{11}$")


def _id_de_video(url):
    """El id del video de un link a un tema (`watch?v=`, `youtu.be/`,
    `/shorts/`), o None. Sirve para llegar al canal que lo subió."""
    partes = urllib.parse.urlsplit(url if "://" in url else "https://" + url)
    host = (partes.hostname or "").lower()
    candidato = None
    if host.endswith("youtu.be"):
        candidato = partes.path.strip("/").split("/")[0]
    elif host.endswith("youtube.com"):
        if partes.path.rstrip("/") == "/watch":
            candidato = (urllib.parse.parse_qs(partes.query).get("v") or [""])[0]
        elif partes.path.startswith("/shorts/"):
            candidato = partes.path.split("/")[2]
    return candidato if candidato and _RE_ID_VIDEO.match(candidato) else None


def pedido_de_canal(url):
    """Cómo pedirle el canal a la API, a partir de lo que pegó el usuario.

    Devuelve (parámetros de `channels.list`, lo que se muestra si no aparece), o
    (None, id_de_video) cuando lo pegado es un tema y hay que buscar su canal
    primero. Levanta RelevarError si no hay por dónde agarrarlo.

    La URL se decodifica ANTES de buscar el handle. El navegador copia
    `youtube.com/@pe%C3%B1a`, y el regex se cortaba en el `%`: se pedía `@pe`,
    y si ese canal existía se relevaba el catálogo de otro artista sin ningún
    error, que es lo peor que puede pasar con un anexo de contrato.
    """
    url = urllib.parse.unquote((url or "").strip())
    base = {"part": "snippet,contentDetails"}

    m = re.search(r"/channel/(UC[\w-]+)", url)
    if m:
        return dict(base, id=m.group(1)), url
    if _RE_ID_CANAL.match(url):
        return dict(base, id=url), url
    m = re.search(r"/user/([\w.\-]+)", url)
    if m:
        return dict(base, forUsername=m.group(1)), m.group(1)
    m = re.search(r"@([\w.\-·]+)", url)
    if m:
        return dict(base, forHandle="@" + m.group(1)), "@" + m.group(1)
    # Las URL personalizadas viejas (`/c/Nombre`) no tienen consulta propia en
    # la API; hoy casi siempre coinciden con el handle, así que se prueba así.
    m = re.search(r"/c/([\w.\-]+)", url)
    if m:
        return dict(base, forHandle="@" + m.group(1)), m.group(1)
    video = _id_de_video(url)
    if video:
        return None, video
    raise RelevarError(T("yt.url_no_reconocida"), "url")


def resolve_channel(url, key):
    """Devuelve (channel_id, uploads_playlist_id, channel_title)."""
    params, muestra = pedido_de_canal(url)
    if params is None:
        # Pegaron el link de un tema: su canal sale de `videos.list`, que cuesta
        # una unidad de cuota, y de ahí se sigue como con cualquier canal.
        datos = api_get("videos", {"part": "snippet", "id": muestra}, key)
        items = datos.get("items") or []
        canal = ((items[0].get("snippet") or {}).get("channelId") if items else "") or ""
        if not canal:
            raise RelevarError(T("yt.video_no_encontrado"), "url")
        params, muestra = {"part": "snippet,contentDetails", "id": canal}, canal
    handle = muestra

    data = api_get("channels", params, key)
    items = data.get("items") or []
    if not items:
        raise RelevarError(T("yt.canal_no_encontrado", canal=handle), "url")
    ch = items[0]
    return (
        ch["id"],
        ch["contentDetails"]["relatedPlaylists"]["uploads"],
        ch["snippet"]["title"],
    )


RE_TOPIC = re.compile(r"\s*-\s*Topic$", re.I)

# Sufijos que llevan los canales oficiales (OAC) y que el canal Topic NO tiene.
# Sacarlos antes de buscar es lo que hace que "Fulano Oficial" encuentre
# "Fulano - Topic": buscando con el sufijo no matchea nunca.
RE_SUFIJOS_OAC = re.compile(r"\b(oficial|official|vevo)\b", re.I)

# Por debajo de esta similitud entre el nombre del canal pedido y el del Topic
# preferimos no arriesgar: mejor no cambiar de canal que relevar el catálogo de
# otro artista con nombre parecido.
MIN_SIMILITUD_TOPIC = 0.70


def _nombre_artista(titulo):
    """Nombre del artista sin "- Topic" ni sufijos de OAC."""
    n = RE_TOPIC.sub("", titulo or "").strip()
    n = RE_SUFIJOS_OAC.sub("", n)
    return re.sub(r"\s+", " ", n).strip(" -\u00b7|")


def es_canal_topic(titulo):
    return bool(RE_TOPIC.search((titulo or "").strip()))


def canal_uploads_por_id(channel_id, key):
    """(uploads_playlist_id, titulo) de un channel_id, o (None, None)."""
    data = api_get("channels", {"part": "snippet,contentDetails", "id": channel_id}, key)
    items = data.get("items") or []
    if not items:
        return None, None
    ch = items[0]
    return ch["contentDetails"]["relatedPlaylists"]["uploads"], ch["snippet"]["title"]


def buscar_canal_topic(titulo_canal, key):
    """Busca el canal "<artista> - Topic" a partir del título de otro canal.

    Sirve cuando te pasan un OAC: el Topic es el único que trae las descripciones
    auto-generadas con distribuidora, álbum, año y sello, y a veces es difícil de
    encontrar a mano.

    Devuelve (channel_id, titulo) o None. Busca primero coincidencia exacta del
    nombre base (sin acentos ni sufijos); si no hay, acepta el más parecido
    siempre que supere MIN_SIMILITUD_TOPIC.

    Cuesta 100 unidades de cuota (search.list), más que relevar un catálogo
    entero, así que se llama sólo cuando hace falta.
    """
    artista = _nombre_artista(titulo_canal)
    objetivo = _normalize(artista)
    if not objetivo:
        return None
    try:
        data = api_get(
            "search", {"part": "snippet", "q": f"{artista} - Topic", "type": "channel", "maxResults": 10}, key
        )
    except Exception:  # noqa: BLE001 (sin busqueda de Topic, se releva el canal pedido)
        return None

    mejor, mejor_score = None, 0.0
    for it in data.get("items") or []:
        sn = it.get("snippet") or {}
        titulo = sn.get("channelTitle") or sn.get("title") or ""
        if not es_canal_topic(titulo):
            continue
        cid = sn.get("channelId") or (it.get("id") or {}).get("channelId")
        if not cid:
            continue
        base = _normalize(_nombre_artista(titulo))
        if base == objetivo:
            return cid, titulo  # exacto: no hay nada mejor
        score = SequenceMatcher(None, objetivo, base).ratio()
        if score > mejor_score:
            mejor, mejor_score = (cid, titulo), score

    return mejor if mejor_score >= MIN_SIMILITUD_TOPIC else None


def list_video_ids(uploads_playlist, key):
    ids = []
    page = None
    while True:
        params = {"part": "contentDetails", "maxResults": 50, "playlistId": uploads_playlist}
        if page:
            params["pageToken"] = page
        data = api_get("playlistItems", params, key)
        for it in data.get("items", []):
            vid = it.get("contentDetails", {}).get("videoId")
            if vid:
                ids.append(vid)
        page = data.get("nextPageToken")
        if not page:
            break
    return ids


def fetch_videos(video_ids, key):
    out = []
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i : i + 50]
        data = api_get("videos", {"part": "snippet,statistics,contentDetails", "id": ",".join(batch)}, key)
        out.extend(data.get("items", []))
    return out


_RE_ISO_DUR = re.compile(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")


def _iso_duration_to_seconds(s):
    if not s:
        return 0
    m = _RE_ISO_DUR.fullmatch(s)
    if not m:
        return 0
    h, mn, sec = (int(x) if x else 0 for x in m.groups())
    return h * 3600 + mn * 60 + sec


# ============================================================
# Parseo (distribuidora / álbum / año / sello) : autocontenido
# ============================================================

_RE_PHONO_LINE = re.compile(r"^\s*℗\s*(.+)$", re.MULTILINE)
# Año al principio de la línea ℗, seguido del sello si lo hay. El (?!\d) es lo
# que importa: sin él, "℗ 5358533 Records DK" ,el sello placeholder que pone
# DistroKid cuando el artista no cargó ninguno, se leía como el año 5358.
_RE_ANIO_SELLO = re.compile(r"^(\d{4})(?!\d)\s*(.*)$")
_RE_RELEASED = re.compile(r"Released on:\s*(\d{4})-(\d{2})-(\d{2})")
_RE_SELLO_RELLENO = re.compile(r"^\d{5,}\s+Records DK$", re.IGNORECASE)


# Lo que sigue al titular del ℗ y no es su nombre: la licencia y el grupo al que
# pertenece. «℗ 2020 Sello Chico under exclusive license to Warner» es de Sello
# Chico, y la columna Label llevaba la frase entera.
_RE_CORTE_TITULAR = re.compile(
    r"\s*(?:\bunder\s+(?:exclusive\s+)?licen[cs]e\b|,?\s*\ba\s+division\s+of\b|,?\s*\bdistributed\s+by\b|"
    r"\bbajo\s+licencia\b|\blicensed\s+to\b).*$",
    re.I,
)


def _titular(linea):
    """El titular de una línea ℗, sin la licencia, o None.

    Hay líneas con más de un ℗, como «2021 ℗ Distributed exclusively by Warner
    Music France, ℗ 2001 Daft Life Ltd.»: se recorren los tramos y se toma el
    primero que nombra a alguien, salteando los de distribución, que no son un
    titular. Antes el sello salía «℗ Distributed exclusively by…».
    """
    for tramo in linea.split("℗"):
        tramo = tramo.strip(" ,;")
        m = _RE_ANIO_SELLO.match(tramo)
        nombre = (m.group(2) if m and _anio_plausible(int(m.group(1))) else tramo).strip(" ,;")
        nombre = _RE_CORTE_TITULAR.sub("", nombre).strip(" ,;")
        if not nombre or re.match(r"(?i)distributed\b|\d{4}$", nombre):
            continue
        # "5358533 Records DK" no es un sello: es el relleno que pone DistroKid con
        # el id de la cuenta cuando el artista no declaró ninguno.
        if _RE_SELLO_RELLENO.match(nombre):
            continue
        return nombre
    return None


def _anio_plausible(a):
    """Un año de lanzamiento que pueda existir.

    La grabación más vieja que puede tener un ISRC es de fines del siglo XIX, y
    un lanzamiento futuro más allá del año que viene es un error de carga. Todo
    lo de afuera es basura que se coló del texto, no un dato."""
    return 1900 <= a <= date.today().year + 1


# Los roles de los créditos que publica YouTube, y a qué columna de la hoja de
# ingesta van. «Writer» va sólo a compositor: en un instrumental no hay letra, y
# ponerlo también como letrista sería afirmar algo que la fuente no dice. El
# resto (intérpretes, ingenieros, mastering) no es un dato que pida la ingesta.
_ROLES_CREDITO = {
    "composer": ("composers",),
    "composer lyricist": ("composers", "lyricists"),
    "songwriter": ("composers", "lyricists"),
    "writer": ("composers",),
    "author": ("lyricists",),
    "lyricist": ("lyricists",),
    "producer": ("producers",),
    "music publisher": ("publishers",),
    "publisher": ("publishers",),
}
_RE_LINEA_CREDITO = re.compile(r"^\s*([A-Za-z][A-Za-z ,\-]{1,80}?)\s*:\s*(.+?)\s*$")


def _creditos(bloques) -> Creditos:
    """Los créditos de los bloques de la descripción, por columna de la hoja."""
    out: dict[str, list[str]] = {"composers": [], "lyricists": [], "producers": [], "publishers": []}
    for bloque in bloques:
        for linea in bloque.splitlines():
            m = _RE_LINEA_CREDITO.match(linea)
            if not m or m.group(1).lower().startswith(("released on", "provided to youtube")):
                continue
            nombre = m.group(2).strip()
            # YouTube escribe a veces «Music  Publisher», con dos espacios.
            roles = [re.sub(r"\s+", " ", r).strip().lower() for r in m.group(1).split(",")]
            for rol in roles:
                for columna in _ROLES_CREDITO.get(rol, ()):
                    if nombre not in out[columna]:
                        out[columna].append(nombre)
    return {
        "composers": out["composers"],
        "lyricists": out["lyricists"],
        "producers": out["producers"],
        "publishers": out["publishers"],
    }


def parse_description(desc) -> DescripcionParseada:
    """Extrae distribuidor, álbum, año y sello de una descripción auto-generada."""
    res: DescripcionParseada = {
        "distributor": None,
        "album": None,
        "release_year": None,
        "release_date": None,
        "label": None,
        "p_line": None,
        "artists": [],
        "credits": {"composers": [], "lyricists": [], "producers": [], "publishers": []},
    }
    if not desc:
        return res

    first = desc.split("\n")[0].strip()
    prefix = "provided to youtube by "
    if first.lower().startswith(prefix):
        res["distributor"] = first[len(prefix) :].strip()

    # Álbum: tercer bloque del formato auto-generado
    #   [0] Provided to YouTube by X / [1] Track · Artista / [2] Álbum
    # En singles/EP no hay bloque de álbum y el [2] es la línea ℗ (o "Released
    # on:"): no es un álbum, así que lo descartamos y queda en SIN_ALBUM.
    blocks = [b.strip() for b in re.split(r"\n\s*\n", desc) if b.strip()]

    # Los artistas: el segundo bloque es «Título · Artista · Otro · Otro». Es lo
    # que trae los invitados y los coautores, que antes se perdían y la hoja
    # ponía el nombre del canal como artista de todos los temas.
    if len(blocks) >= 2 and blocks[0].lower().startswith(prefix) and " · " in blocks[1]:
        partes = [x.strip() for x in blocks[1].splitlines()[0].split(" · ")]
        res["artists"] = [x for x in partes[1:] if x]
    # Los créditos van después del bloque ℗, nunca en los dos primeros.
    if len(blocks) >= 3 and blocks[0].lower().startswith(prefix):
        res["credits"] = _creditos(blocks[3:])
    if len(blocks) >= 3 and blocks[0].lower().startswith(prefix):
        cand = blocks[2].splitlines()[0].strip()
        if cand and not cand.startswith("℗") and not cand.lower().startswith("released on:"):
            res["album"] = cand

    # Año + sello, de la línea ℗.
    #
    # El sello es opcional: "℗ 2023" a secas aporta el año sin inventar un sello.
    # Y el año también: DistroKid escribe "℗ 5358533 Records DK", donde ese
    # número es el id de la cuenta del artista. Por eso no alcanza con buscar
    # cuatro dígitos, hay que exigir que no siga otro y que el valor sea un año
    # que pueda existir. Si no lo es, la línea entera es el sello.
    pm = _RE_PHONO_LINE.search(desc)
    if pm:
        linea = re.sub(r"\s+", " ", pm.group(1)).strip()
        m = _RE_ANIO_SELLO.match(linea)
        if m and _anio_plausible(int(m.group(1))):
            res["release_year"] = int(m.group(1))
        # La línea entera es la P Line, tal como la publicó la distribuidora: es
        # un dato de la fuente. Se arma aparte del sello, que es un recorte.
        res["p_line"] = f"℗ {linea}" if linea else None
        # Mostrar el relleno de DistroKid como sello era mentir con cara de dato.
        res["label"] = _titular(linea)

    # "Released on:" es la fecha real del lanzamiento. Se guarda entera: es la
    # fecha que la hoja de ingesta necesita, y antes se leía sólo el año y la
    # hoja ponía en su lugar la fecha de subida a YouTube. Y es la fuente del año
    # cuando la línea ℗ no lo trae, que es el caso de todo DistroKid.
    rm = _RE_RELEASED.search(desc)
    if rm and _anio_plausible(int(rm.group(1))):
        try:
            res["release_date"] = date(int(rm.group(1)), int(rm.group(2)), int(rm.group(3))).isoformat()
        except ValueError:
            pass  # una fecha imposible (mes 13) no es un dato
        if not res["release_year"]:
            res["release_year"] = int(rm.group(1))
    return res


def build_tracks(videos) -> list[Track]:
    tracks = []
    for v in videos:
        sn = v.get("snippet", {})
        st = v.get("statistics", {})
        cd = v.get("contentDetails", {})
        desc = sn.get("description") or ""
        meta = parse_description(desc)
        pub = (sn.get("publishedAt") or "")[:10]
        desc3 = "\n".join((desc.split("\n"))[:3]).strip()
        tracks.append(
            {
                "video_id": v.get("id") or "",
                "track": sn.get("title") or "",
                # OJO: estos dos son CENTINELAS, no texto para mostrar, y por eso
                # no se traducen: `relevar()` filtra por SIN_DATOS y `productos`
                # agrupa por SIN_ALBUM, así que traducirlos rompería el filtrado y
                # la agrupación en silencio. Ninguno llega a la pantalla: los tracks
                # sin distribuidora se descartan, y a los que no tienen álbum el
                # producto los titula con el nombre del track.
                "album": meta["album"] or SIN_ALBUM,
                "distributor": meta["distributor"] or SIN_DATOS,
                "label": meta["label"] or "",
                "p_line": meta["p_line"] or "",
                "release_year": meta["release_year"] or "",
                "isrc": "",  # se completa por enriquecimiento (Deezer), si está disponible
                "upc": "",  # idem (a nivel álbum)
                "match": "",  # confianza del match con Deezer: alta / media / ""
                "duration_s": _iso_duration_to_seconds(cd.get("duration")),
                "views": int(st.get("viewCount", 0) or 0),
                "likes": int(st.get("likeCount", 0) or 0),
                "comments": int(st.get("commentCount", 0) or 0),
                "upload_date": pub,
                "release_date": meta["release_date"] or "",
                "artists": meta["artists"],
                "credits": meta["credits"],
                "desc3": desc3,
                "url": f"https://youtu.be/{v.get('id')}",
            }
        )
    return tracks


# ============================================================
# Enriquecimiento de códigos (ISRC + UPC): Deezer + respaldo MusicBrainz
# ============================================================
# Sin claves: Deezer y MusicBrainz son APIs públicas (adiós "se quedó sin
# créditos"). Deezer es la fuente principal (rápida y en paralelo: el ISRC viene
# en la búsqueda, el UPC por álbum). MusicBrainz es respaldo opcional para los
# tracks que Deezer no encuentre (lento: 1 pedido/seg, y cobertura despareja para
# artistas DIY → apagado por defecto). Match best-effort por título+artista+
# duración; ante la duda, código en blanco (mejor un hueco que un código errado).

DEEZER_API = "https://api.deezer.com"
MUSICBRAINZ_API = "https://musicbrainz.org/ws/2"
USER_AGENT = "MigradorDeCatalogos/1.0 (+https://github.com/joacogoliver-debug/catalog-migrator)"
# Deezer permite ~50 pedidos/5s por IP. Con 6 hilos + reintento ante quota,
# quedamos rápidos sin que nos corte. (MusicBrainz va aparte, secuencial.)
CODES_WORKERS = 6


def _deezer_json(path):
    """GET a Deezer con reintento. Deezer señala el límite de tasa con un JSON
    de error a HTTP 200 ({"error": {...}}), así que lo detectamos y reintentamos."""
    url = f"{DEEZER_API}/{path}"
    for _ in range(6):
        data = _http_json(url)
        if isinstance(data, dict) and data.get("error"):
            time.sleep(1.5)
            continue
        return data
    return None


# Sufijos de YouTube que ensucian el match y no están en el catálogo del DSP.
#
# Sólo lo que es de YouTube y nada más, y sólo cuando es TODO el paréntesis.
# Esto borraba antes cualquier paréntesis que nombrara «live», «en vivo»,
# «remaster» o «cover», y cualquier cosa entre corchetes: «Tema (En Vivo)»
# quedaba como «Tema», coincidía al cien por ciento con la versión de estudio y
# se quedaba con su ISRC, con confianza alta. Pero los tracks que llegan acá son
# Art Tracks del canal Topic, cuyo título ES la metadata que cargó la
# distribuidora: la versión es parte del dato, no ruido.
_RE_TITLE_NOISE = re.compile(
    r"\s*[(\[]\s*(?:official\s+(?:music\s+)?video|official\s+audio|video\s+oficial|"
    r"audio(?:\s+oficial)?|lyrics?\s+video|video\s+(?:lyric|con\s+letra)|letra|lyrics?|"
    r"visuali[sz]er|hd|4k)\s*[)\]]",
    re.IGNORECASE,
)


def _clean_title(title):
    t = _RE_TITLE_NOISE.sub("", title or "")
    return re.sub(r"\s+", " ", t).strip(" -·")


def _http_json(url, headers=None, retries=3):
    req = urllib.request.Request(url, headers=headers or {})
    for _ in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503):
                time.sleep(int(e.headers.get("Retry-After", "1")) + 1)
                continue
            return None
        except Exception:  # noqa: BLE001 (idem que portadas: red)
            time.sleep(1)
            continue
    return None


def _match_score(yt_title, yt_artist, yt_dur, cand_title, cand_artist, cand_dur):
    ratio = SequenceMatcher(None, _normalize(_clean_title(yt_title)), _normalize(cand_title or "")).ratio()
    # Si los dos dicen ser la misma versión (los candidatos de otra ya se
    # descartaron antes), el decorado puede estar escrito distinto: «(2011
    # Remaster)» contra « - Remastered 2011». Ahí se compara también sin él. Sólo
    # cuando hay una marca: sin ella, «(Parte 1)» y «(Parte 2)» son dos temas.
    marcas = marcas_version(yt_title)
    if marcas and marcas == marcas_version(cand_title):
        base = SequenceMatcher(None, _normalize(sin_decorado(yt_title)), _normalize(sin_decorado(cand_title)))
        ratio = max(ratio, base.ratio())
    na, ns = _normalize(yt_artist), _normalize(cand_artist or "")
    # Los dos tienen que existir: con el artista del candidato vacío, `ns in na`
    # daba verdadero y cualquier resultado sin artista contaba como del mismo.
    artist_ok = bool(na and ns) and (na in ns or ns in na or SequenceMatcher(None, na, ns).ratio() >= 0.6)
    dur_close = None
    if yt_dur and cand_dur:
        dur_close = abs(yt_dur - cand_dur) <= 4
    score = ratio + (0.10 if artist_ok else 0) + (0.10 if dur_close else 0)
    return score, ratio, artist_ok, dur_close


def _confidence(ratio, artist_ok, dur_close):
    # La duración, cuando se conoce de los dos lados, tiene que coincidir en los
    # dos niveles. La confianza media no la miraba, y un vivo de 262 segundos
    # entraba como «media» contra el de estudio de 215.
    if dur_close is False:
        return ""
    if ratio >= 0.87 and artist_ok:
        return "alta"
    if ratio >= 0.72 and artist_ok:
        return "media"
    return ""


def _misma_version(titulo_a, titulo_b):
    """Si dos títulos pueden ser la misma grabación (ver `texto.misma_version`).
    Un candidato que no lo es se descarta antes de puntuar: ante la duda, código
    en blanco."""
    return misma_version(titulo_a, titulo_b)


# ---- Deezer (principal, sin clave) ----
def deezer_match(t, artist):
    """Devuelve (isrc, album_id, confianza) o ('', None, '')."""
    title = _clean_title(t["track"])
    q = urllib.parse.quote(f'track:"{title}" artist:"{artist}"')
    items = (_deezer_json(f"search?q={q}&limit=5") or {}).get("data") or []
    if not items:  # reintento con búsqueda libre (el filtro estricto a veces no matchea)
        q2 = urllib.parse.quote(f"{title} {artist}")
        items = (_deezer_json(f"search?q={q2}&limit=5") or {}).get("data") or []
    if not items:
        return "", None, ""
    best, best_meta = None, None
    for c in items:
        if not _misma_version(t["track"], c.get("title", "")):
            continue
        sc = _match_score(
            t["track"],
            artist,
            t.get("duration_s", 0),
            c.get("title", ""),
            (c.get("artist") or {}).get("name", ""),
            c.get("duration", 0),
        )
        if best is None or sc[0] > best[0]:
            best, best_meta = sc, c
    if best is None or best_meta is None:
        return "", None, ""
    conf = _confidence(best[1], best[2], best[3])
    if not conf:
        return "", None, ""
    isrc = best_meta.get("isrc") or ""
    if not isrc:  # algunos resultados no traen ISRC en la búsqueda → pedir el track
        isrc = (_deezer_json(f"track/{best_meta.get('id')}") or {}).get("isrc") or ""
    return isrc, (best_meta.get("album") or {}).get("id"), conf


def deezer_albumes(album_ids):
    """Los álbumes de Deezer, por id: lo que se usa de cada uno.

    Antes se pedía el álbum entero y se guardaba sólo el UPC. El título es lo
    que permite saber si ese álbum es el release del que vino el track, que es
    la condición para que su UPC sirva (ver `album_coincide`).
    """
    ids = [a for a in album_ids if a]
    if not ids:
        return {}

    def work(aid):
        a = _deezer_json(f"album/{aid}") or {}
        return aid, {
            "upc": a.get("upc", "") or "",
            "title": a.get("title", "") or "",
            "record_type": a.get("record_type", "") or "",
            "release_date": a.get("release_date", "") or "",
            "nb_tracks": a.get("nb_tracks") or 0,
            "tracks": ((a.get("tracks") or {}).get("data")) or [],
        }

    out = {}
    with ThreadPoolExecutor(max_workers=min(CODES_WORKERS, len(ids))) as ex:
        for aid, info in ex.map(work, ids):
            out[aid] = info
    return out


def tracklist_deezer(info):
    """El tracklist real de un álbum de Deezer: [(título, posición, disco)].

    La lista del álbum viene en orden, pero sin número de disco. Para saber si
    hay más de uno alcanza con mirar el último track, que es un pedido; sólo si
    es de un disco posterior al primero se piden todos, para tener cada
    posición dentro de su disco, que es como la pide una distribuidora.
    """
    tracks = [t for t in info.get("tracks") or [] if t.get("id")]
    if not tracks:
        return []
    ultimo = _deezer_json(f"track/{tracks[-1]['id']}") or {}
    if int(ultimo.get("disk_number") or 1) <= 1:
        return [(t.get("title", ""), i, 1) for i, t in enumerate(tracks, 1)]

    def work(t):
        d = _deezer_json(f"track/{t['id']}") or {}
        return t.get("title", ""), int(d.get("track_position") or 0), int(d.get("disk_number") or 0)

    with ThreadPoolExecutor(max_workers=min(CODES_WORKERS, len(tracks))) as ex:
        lista = list(ex.map(work, tracks))
    # Si alguno no trajo su posición, la lista no sirve entera: un orden a
    # medias es peor que el estimado, porque parece confirmado.
    return lista if all(pos and disco for _t, pos, disco in lista) else []


def _posicion_en(lista, titulo):
    """(posición, disco) del tema en el tracklist, o None si no se lo puede
    ubicar sin dudas: tiene que haber un solo candidato."""
    candidatos = [
        (pos, disco)
        for t, pos, disco in lista
        if misma_version(t, titulo) and comparable(t) == comparable(titulo)
    ]
    if not candidatos:
        candidatos = [
            (pos, disco)
            for t, pos, disco in lista
            if misma_version(t, titulo)
            and SequenceMatcher(None, comparable(t), comparable(titulo)).ratio() >= 0.9
        ]
    return candidatos[0] if len(candidatos) == 1 else None


def deezer_album_upcs(album_ids):
    return {aid: info["upc"] for aid, info in deezer_albumes(album_ids).items()}


# Lo que Deezer (o iTunes) le agrega al título de un release y que no es parte
# del nombre: el formato al final, y los invitados.
_RE_SUFIJO_FORMATO = re.compile(r"\s+-\s+(single|ep)\s*$", re.I)
_RE_INVITADOS = re.compile(r"\s*[(\[]\s*(?:feat|ft|featuring|with|con)\.?\s[^)\]]*[)\]]", re.I)
MIN_SIMILITUD_ALBUM = 0.85
# Una edición del mismo release, que Deezer nombra y YouTube no (ver
# `album_coincide`). Deluxe, expanded y bonus quedan afuera: son otro release.
_RE_EDICION = re.compile(
    r"[(\[][^)\]]*\b(edition|edición|edicion|anniversary|aniversario)\b[^)\]]*[)\]]", re.I
)
_RE_OTRO_RELEASE = re.compile(r"deluxe|expanded|bonus|ampliad", re.I)


def _fechas_cercanas(a, b, dias=7):
    try:
        return abs((date.fromisoformat(a[:10]) - date.fromisoformat(b[:10])).days) <= dias
    except ValueError:
        return True  # una fecha ilegible no es evidencia de que sean distintos


def album_coincide(titulo_producto, titulo_deezer, fecha_producto="", fecha_deezer=""):
    """Si el álbum de Deezer es el release del que vino el track.

    La búsqueda de Deezer encuentra la GRABACIÓN, y la misma grabación está en
    el single, en el álbum y en cada compilado. El `album_id` que trae el
    resultado es el de cualquiera de ellos, y su UPC terminaba en el producto:
    un single quedaba con el UPC del álbum, y como la portada se busca primero
    por UPC, también con su tapa. Ahora el UPC se acepta sólo si el título del
    álbum de Deezer es el del producto, sin mirar el formato ni los invitados y
    con la misma versión (un «Deluxe» o un «En Vivo» es otro release).

    Hay un caso que el título solo no resuelve. YouTube llama «Random Access
    Memories» a la edición aniversario, que en Deezer es «Random Access
    Memories (10th Anniversary Edition)». Con la misma fecha de lanzamiento de
    los dos lados, un título que sólo le agrega una edición entre paréntesis es
    el mismo release; con otra fecha, es la reedición de otro, y queda afuera.
    Un «Deluxe», «Expanded» o con «Bonus» nunca entra por acá: puede salir el
    mismo día que la estándar y es otro release, con otro UPC.
    """

    def limpio(t):
        return _RE_INVITADOS.sub("", _RE_SUFIJO_FORMATO.sub("", t or "")).strip()

    a, b = limpio(titulo_producto), limpio(titulo_deezer)
    if not (comparable(a) and comparable(b)):
        return False
    # Con las dos fechas a la vista, un release que salió en otra fecha es otro,
    # aunque el título sea idéntico: la edición aniversario se llama igual que el
    # original de diez años antes, y sus temas se quedaban con el UPC y el
    # tracklist del original. Una semana de margen, porque cada plataforma puede
    # fechar la misma entrega con un día de diferencia.
    if fecha_producto and fecha_deezer and not _fechas_cercanas(fecha_producto, fecha_deezer):
        return False
    # La edición se mira primero: su «10th» traería un número que el título de
    # YouTube no tiene, y ahí lo que decide es la fecha, no los números.
    extra = b[len(a) :].strip() if b.lower().startswith(a.lower()) else ""
    if extra and _RE_EDICION.fullmatch(extra) and not _RE_OTRO_RELEASE.search(extra):
        return bool(fecha_producto and fecha_deezer)
    if not misma_version(a, b):
        return False
    if comparable(a) == comparable(b):
        return True
    return SequenceMatcher(None, comparable(a), comparable(b)).ratio() >= MIN_SIMILITUD_ALBUM


# ---- MusicBrainz (respaldo opcional; límite 1 pedido/seg) ----
def musicbrainz_isrc(t, artist):
    """ISRC desde MusicBrainz. 2 pedidos (search + lookup). Devuelve '' si no hay."""
    q = urllib.parse.quote(f'recording:"{_clean_title(t["track"])}" AND artist:"{artist}"')
    data = _http_json(
        f"{MUSICBRAINZ_API}/recording?query={q}&fmt=json&limit=5", headers={"User-Agent": USER_AGENT}
    )
    for r in (data or {}).get("recordings", []) or []:
        ac = " ".join(a.get("name", "") for a in (r.get("artist-credit") or []) if isinstance(a, dict))
        dur = round((r.get("length") or 0) / 1000)
        if not _misma_version(t["track"], r.get("title", "")):
            continue
        sc = _match_score(t["track"], artist, t.get("duration_s", 0), r.get("title", ""), ac, dur)
        if _confidence(sc[1], sc[2], sc[3]):
            time.sleep(1.1)  # respetar el límite de MusicBrainz entre los 2 pedidos
            look = _http_json(
                f"{MUSICBRAINZ_API}/recording/{r['id']}?fmt=json&inc=isrcs",
                headers={"User-Agent": USER_AGENT},
            )
            isrcs = (look or {}).get("isrcs") or []
            return isrcs[0] if isrcs else ""
    return ""


def enrich_with_codes(tracks, artist, log=print, use_musicbrainz=False):
    """Completa isrc/upc/match en los tracks. Deezer principal + MB opcional."""
    n = len(tracks)

    # 1) Deezer en paralelo (ISRC + album_id por track).
    def work(t):
        return (t,) + deezer_match(t, artist)

    album_ids = {}
    matched = 0
    if n:
        with ThreadPoolExecutor(max_workers=min(CODES_WORKERS, n)) as ex:
            for t, isrc, album_id, conf in ex.map(work, tracks):
                if conf:
                    t["isrc"], t["match"] = isrc, conf
                    if album_id:
                        album_ids.setdefault(album_id, []).append(t)
                    matched += 1

    # 2) UPC por álbum (Deezer, en paralelo), sólo si el álbum es el release.
    log(T("rel.deezer_resultado", matched=matched, n=n, albumes=len(album_ids)))
    albumes = deezer_albumes(list(album_ids.keys()))
    for aid, ts in album_ids.items():
        info = albumes.get(aid) or {}
        for t in ts:
            # El título del release en YouTube: el del álbum, o el del propio
            # track cuando es un single.
            propio = t["album"] if t["album"] != SIN_ALBUM else t["track"]
            coincide = album_coincide(
                propio, info.get("title", ""), t.get("release_date", ""), info.get("release_date", "")
            )
            if info.get("upc") and coincide:
                t["upc"] = info["upc"]
            elif info.get("upc"):
                # Se deja constancia de por qué no hay UPC, para que la
                # validación lo diga en vez de un «falta» sin explicación.
                t["upc_descartado"] = info.get("title", "")

    # 3) El orden real, del tracklist del álbum. Sólo para los tracks cuyo
    # álbum se verificó como este release: el orden de otro release (el del
    # álbum, para un single) no dice nada de éste.
    listas = {}  # release de YouTube (álbum, fecha) -> tracklist verificado
    for aid, ts in album_ids.items():
        info = albumes.get(aid) or {}
        verificados = [t for t in ts if info.get("upc") and t["upc"] == info["upc"]]
        lista = tracklist_deezer(info) if verificados else []
        for t in verificados:
            if lista:
                listas.setdefault((comparable(t["album"]), t.get("release_date") or ""), (aid, lista))
            lugar = _posicion_en(lista, t["track"])
            if lugar:
                t["track_number"], t["disc_number"], t["orden_fuente"] = lugar[0], lugar[1], "deezer"
                t["album_deezer_id"] = aid

    # Segunda pasada. Un tema que Deezer no encontró, o que encontró en otro
    # release (su propio single), igual es parte de este release en YouTube, y
    # el tracklist verificado de sus compañeros sirve para ubicarlo. Con datos
    # reales, sin esto un solo tema así dejaba el release entero como estimado.
    for t in tracks:
        clave = (comparable(t["album"]), t.get("release_date") or "")
        if t.get("orden_fuente") or t["album"] == SIN_ALBUM or clave not in listas:
            continue
        aid, lista = listas[clave]
        lugar = _posicion_en(lista, t["track"])
        if lugar:
            t["track_number"], t["disc_number"], t["orden_fuente"] = lugar[0], lugar[1], "deezer"
            t["album_deezer_id"] = aid

    # 4) MusicBrainz: respaldo SÓLO para los que quedaron sin ISRC (secuencial, lento).
    if use_musicbrainz:
        pendientes = [t for t in tracks if not t["isrc"]]
        if pendientes:
            log(T("rel.musicbrainz", n=len(pendientes)))
            for t in pendientes:
                isrc = musicbrainz_isrc(t, artist)
                if isrc:
                    t["isrc"] = isrc
                    t["match"] = t["match"] or "media"
                time.sleep(1.1)  # 1 pedido/seg

    isrc_n = sum(1 for t in tracks if t["isrc"])
    upc_n = sum(1 for t in tracks if t["upc"])
    return {"matched": matched, "isrc": isrc_n, "upc": upc_n, "source": "Deezer"}


def _aggregate_distributors(tracks):
    agg = {}
    for t in tracks:
        d = agg.setdefault(t["distributor"], {"videos": 0, "views": 0, "top": 0, "top_title": ""})
        d["videos"] += 1
        d["views"] += t["views"]
        if t["views"] > d["top"]:
            d["top"] = t["views"]
            d["top_title"] = t["track"]
    return agg


def slugify(name):
    s = re.sub(r"[^\w\s-]", "", name, flags=re.UNICODE).strip()
    return re.sub(r"\s+", "_", s) or "Artista"


# ============================================================
# Orquestador (lo llama la app web)
# ============================================================


def relevar(url, yt_key, with_codes=True, progress=None, use_musicbrainz=False) -> Relevamiento:
    """Releva el catálogo completo de un canal.

    with_codes: buscar ISRC/UPC (Deezer; sin clave). use_musicbrainz: respaldo
    lento opcional. progress(msg, frac): callback de avance (0.0-1.0).
    Devuelve dict: artist, channel_title, tracks, distribs, total_views, units, codes.
    Lanza RelevarError ante problemas mostrables al usuario.
    """

    def step(msg, frac):
        if progress:
            progress(msg, frac)

    if not yt_key:
        raise RelevarError(T("yt.falta_clave"), "clave")

    step(T("rel.resolviendo"), 0.05)
    _ch_id, uploads, title = resolve_channel(url, yt_key)
    canal_pedido = title

    # Si lo que pegaron NO es un canal Topic (típicamente un OAC), buscamos su
    # Topic y relevamos ese. El Topic es el único que trae las descripciones
    # auto-generadas con distribuidora, álbum, año y sello; un OAC tiene videos
    # subidos a mano y de ahí no sale metadata. Encontrar el Topic a mano suele
    # ser molesto, así que lo hace la app.
    via_topic = False
    if not es_canal_topic(title):
        step(T("rel.buscando_topic"), 0.10)
        hallado = buscar_canal_topic(title, yt_key)
        if hallado:
            t_uploads, t_title = canal_uploads_por_id(hallado[0], yt_key)
            # Se exigen los dos y no sólo la playlist: el título es de donde sale
            # el nombre del artista, y cambiar de canal con el título vacío deja
            # el catálogo entero a nombre de nadie.
            if t_uploads and t_title:
                uploads, title, via_topic = t_uploads, t_title, True
                step(T("rel.uso_topic", canal=t_title), 0.12)

    step(T("rel.listando"), 0.15)
    vids = list_video_ids(uploads, yt_key)
    if not vids:
        raise RelevarError(T("yt.canal_vacio"))

    step(T("rel.bajando_metadata", n=len(vids)), 0.30)
    videos = fetch_videos(vids, yt_key)

    # Nos quedamos SÓLO con los lanzamientos: los que tienen distribuidora
    # parseada de "Provided to YouTube by". Los demás (vlogs, vivos, videoclips,
    # entrevistas) no son productos de catálogo y sin metadata sólo ensucian el
    # resultado: sin este filtro, un canal común devolvía cientos de "productos"
    # sin álbum ni códigos.
    todos = build_tracks(videos)
    tracks = [t for t in todos if t["distributor"] != SIN_DATOS]
    descartados = len(todos) - len(tracks)

    if not tracks:
        raise RelevarError(T("yt.sin_lanzamientos", n=len(todos)))

    if descartados:
        step(T("rel.descartados", n=descartados), 0.45)

    artist = _nombre_artista(title)

    # Después del filtro, todo lo que quedó tiene metadata, así que la cobertura
    # es 1.0 por construcción. El campo se mantiene porque la interfaz lo usa.
    es_topic = es_canal_topic(title)
    cobertura = 1.0
    topic_sugerido = None

    codes_stats = None
    if with_codes:
        step(T("rel.buscando_codigos"), 0.55)
        codes_stats = enrich_with_codes(
            tracks, artist, log=lambda m: step(m, 0.75), use_musicbrainz=use_musicbrainz
        )

    step(T("rel.armando_excel"), 0.95)
    units = 1 + 2 * ((len(vids) + 49) // 50)
    return {
        "artist": artist,
        "channel_title": title,
        "tracks": tracks,
        "distribs": _aggregate_distributors(tracks),
        "total_views": sum(t["views"] for t in tracks),
        "units": units,
        "codes": codes_stats,
        "es_topic": es_topic,
        "cobertura_metadata": round(cobertura, 3),
        "topic_sugerido": topic_sugerido,
        # Para contarle al usuario qué canal se usó y qué quedó afuera, en vez de
        # que el cambio ocurra a sus espaldas.
        "via_topic": via_topic,
        "canal_pedido": canal_pedido,
        "descartados": descartados,
    }
