"""
Qué le falta al catálogo relevado, según la discografía del artista en Deezer.

Por qué existe. Desde fines de 2026 YouTube no publica la lista de subidas de
los canales Topic y el catálogo se lista por el buscador (ver
`relevar_core.buscar_videos_del_canal`), que es un índice y no un listado: puede
no traer un tema que existe, y no avisa. Antes de eso el problema ya estaba,
más chico: un tema dado de baja en YouTube, o una colaboración que YouTube
guarda en el canal del otro artista, nunca aparecían y nadie lo notaba.

Lo que hace. Con los temas que ya se cruzaron con Deezer alcanza para saber qué
artista de Deezer es el del canal: es el dueño de los álbumes que se verificaron
como releases de este catálogo. No se lo busca por nombre, que es como se
termina con la discografía de un homónimo. Cuando el cruce no encontró ningún
tema, sí se busca el perfil por nombre, pero se lo acepta por sus temas y no
por cómo se llama (ver `buscar_artista`); y el usuario puede indicar cuál es. Con ese artista se pide su
discografía entera, que no cuesta cuota de YouTube, y se compara grabación por
grabación contra lo relevado.

Qué hace con lo que falta. Lo suma al catálogo con los datos de Deezer, que
tiene el título, el UPC, los ISRC y el orden (ver `sumar_de_deezer`): adentro
del disco, si el disco está, o como un release aparte. Lo que Deezer no sabe es
la distribuidora, que es un dato que sólo publica YouTube, y que algo falte en
YouTube no dice por qué: puede ser que el buscador no lo trajo, que esté en el
canal de otro artista o que nunca se haya entregado a YouTube. Por eso todo lo
sumado va marcado, y el release que no apareció queda sin elegir.

Se probó ir a buscar a YouTube, por nombre, cada release faltante. Cuesta 100
unidades de cuota por release y en el catálogo real con que se midió no recuperó
nada dentro del canal: lo que faltaba no estaba ahí. Por eso no se hace solo.

También se midió la otra fuente posible, las listas de álbum que el canal
muestra en su página («Albums & Singles»), mirándolas con un navegador en dos
catálogos reales. No sirven para listar. La página pública trae sólo las doce
primeras; el resto sale de la interfaz interna de la web, que no es la API
oficial. Y lo que traen no es el catálogo: YouTube pone en cada lugar el video
que prefiere, que muchas veces es el videoclip del canal oficial o la subida de
un tercero, sin la línea de la distribuidora. En un catálogo, 102 de los 166
videos de las listas eran de esos; en el otro, 64 de 272. De los temas del
propio canal que el buscador no había traído, casi todos eran grabaciones que
ya estaban con otro video o sumadas desde Deezer: en total aparecieron dos
grabaciones nuevas sobre más de cuatrocientas. El buscador más la discografía
de Deezer cubre lo mismo sin salir de las fuentes oficiales.
"""

import re
import urllib.parse
from collections import Counter
from typing import Any
from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher

from . import relevar_core as R
from .contratos import Completitud, CruceDeezer, Producto, ReleaseIncompleto, TemaFaltante, Track
from .productos import SIN_ALBUM, SIN_DATOS
from .texto import comparable, marcas_version, misma_version, plegado, sin_decorado

# Por debajo de este parecido entre el nombre del canal y el del artista de
# Deezer no se compara nada: mejor no revisar que revisar contra otro artista.
MIN_SIMILITUD_ARTISTA = 0.85
# Un mismo artista puede tener más de una ficha en Deezer («Los Del Maranaho» y
# «Los De Maranaho»). Se toman las que salieron del muestreo, hasta este tope.
MAX_ARTISTAS = 3
# Tope de releases a revisar, para que una discografía enorme no convierta el
# relevamiento en cientos de pedidos. Si se llega, se dice.
MAX_RELEASES = 300
# El mismo margen que usa el cruce de códigos para dar dos duraciones por iguales.
MARGEN_DURACION = 4
# Parecido mínimo entre dos títulos para tratarlos como la misma grabación
# cuando además duran lo mismo.
MIN_SIMILITUD_TITULO = 0.85


def completitud_vacia() -> Completitud:
    return {
        "revisada": False,
        "artista_deezer": "",
        "artista_id": 0,
        "como": "",
        "releases": 0,
        "temas": 0,
        "sin_respuesta": 0,
        "isrc_completados": 0,
        "verificados_por_tracklist": 0,
        "recortada": False,
        "faltan": [],
    }


def artistas_en_deezer(tracks: list[Track], cruce: CruceDeezer, artista) -> list[tuple[int, str]]:
    """Los artistas de Deezer que son el del canal: [(id, nombre)].

    Sale de un muestreo: cada tema ubicado en un álbum verificado vota por el
    artista de ese álbum. Se queda con los que además se llaman como el canal,
    porque un compilado verificado tiene de artista al sello o a «Varios».
    """
    albumes = cruce.get("albumes") or {}
    votos: Counter[tuple[int, str]] = Counter()
    for t in tracks:
        info = albumes.get(t.get("album_deezer_id") or 0) or {}
        if info.get("artist_id"):
            votos[(int(info["artist_id"]), info.get("artist_name") or "")] += 1
    objetivo = plegado(artista)
    if not objetivo:
        return []
    out = []
    for (aid, nombre), _n in votos.most_common():
        if _mismo_artista(artista, nombre):
            out.append((aid, nombre))
    return out[:MAX_ARTISTAS]


# Cuántos perfiles se miran al buscar al artista por su nombre, y cuántos temas
# del canal tienen que estar entre los más escuchados de un perfil para
# aceptarlo aunque no se llame igual.
MAX_CANDIDATOS = 5
MIN_COINCIDENCIAS = 3


def _coincidencias(tracks: list[Track], temas) -> int:
    """Cuántos temas del canal están en esa lista de Deezer: el mismo título,
    la misma versión y la misma duración, con las dos a la vista."""
    por_titulo: dict[str, list[tuple[str, int]]] = {}
    for x in temas:
        if x.get("title") and x.get("duration"):
            por_titulo.setdefault(comparable(x["title"]), []).append((x["title"], int(x["duration"])))
    n = 0
    for t in tracks:
        duracion = t.get("duration_s") or 0
        if not duracion or t.get("origen") == "deezer":
            continue
        if any(
            abs(d - duracion) <= MARGEN_DURACION and misma_version(titulo, t["track"])
            for titulo, d in por_titulo.get(comparable(t["track"]), [])
        ):
            n += 1
    return n


def buscar_artista(tracks: list[Track], artista) -> list[tuple[int, str]]:
    """El perfil del artista en Deezer, buscado por su nombre: [(id, nombre)].

    Es el camino para cuando el cruce tema por tema no encontró nada. Ese cruce
    depende del buscador de Deezer, que busca por texto: si el artista se
    escribe distinto en YouTube («Q' Lokura» y «Q’Lokura»), ningún tema
    aparece, no queda ningún álbum verificado del que sacar el artista, y la
    app terminaba diciendo que el artista no está en Deezer, con su perfil ahí.

    No alcanza con el nombre, que es como se termina con la discografía de un
    homónimo. A cada perfil que devuelve el buscador de artistas se le piden
    sus temas más escuchados y se cuenta cuántos temas del canal están ahí, por
    título y duración. Se acepta el que se llama igual y tiene alguno, o
    cualquiera que tenga varios: tres temas con el mismo título y la misma
    duración no son una casualidad.
    """
    if not comparable(artista):
        return []
    ruta = "search/artist?q=" + urllib.parse.quote(artista) + f"&limit={MAX_CANDIDATOS}"
    hallados = []
    for cand in ((R._deezer_json(ruta) or {}).get("data") or [])[:MAX_CANDIDATOS]:
        aid, nombre = int(cand.get("id") or 0), cand.get("name") or ""
        if not aid:
            continue
        top = (R._deezer_json(f"artist/{aid}/top?limit=100") or {}).get("data") or []
        n = _coincidencias(tracks, top)
        mismo = _mismo_artista(artista, nombre) or comparable(artista).replace(" ", "") == comparable(
            nombre
        ).replace(" ", "")
        if n >= MIN_COINCIDENCIAS or (mismo and n >= 1):
            hallados.append((n, aid, nombre))
    hallados.sort(key=lambda h: -h[0])
    return [(aid, nombre) for _n, aid, nombre in hallados[:MAX_ARTISTAS]]


def artista_por_id(artist_id) -> list[tuple[int, str]]:
    """El perfil que eligió el usuario, por su id: [(id, nombre)] o []."""
    datos = R._deezer_json(f"artist/{int(artist_id)}") or {}
    return [(int(datos["id"]), datos.get("name") or "")] if datos.get("id") else []


def discografia(artist_ids) -> tuple[list[dict[str, Any]], bool]:
    """Los releases de esos artistas en Deezer, sin repetir, y si se recortó."""
    vistos, out = set(), []
    for aid in artist_ids:
        ruta = f"artist/{aid}/albums?limit=100"
        while ruta:
            datos = R._deezer_json(ruta) or {}
            for a in datos.get("data") or []:
                if a.get("id") and a["id"] not in vistos:
                    vistos.add(a["id"])
                    out.append(a)
            if len(out) >= MAX_RELEASES:
                return out[:MAX_RELEASES], True
            siguiente = datos.get("next") or ""
            ruta = siguiente.split("api.deezer.com/", 1)[1] if "api.deezer.com/" in siguiente else ""
    return out, False


def _temas_de(album_id) -> list[TemaFaltante] | None:
    """Los temas de un álbum de Deezer, o None si Deezer no contestó."""
    datos = R._deezer_json(f"album/{album_id}/tracks?limit=500")
    if datos is None:
        return None
    return [
        {
            "titulo": x.get("title") or "",
            "isrc": x.get("isrc") or "",
            "duracion_s": int(x.get("duration") or 0),
            "posicion": int(x.get("track_position") or 0),
            "disco": int(x.get("disk_number") or 0),
            "artista": (x.get("artist") or {}).get("name") or "",
            "deezer_id": int(x.get("id") or 0),
        }
        for x in datos.get("data") or []
    ]


def completar_isrc(tracks: list[Track], tracklists) -> int:
    """Les pone ISRC a los temas que no lo consiguieron, desde la discografía.

    El cruce de códigos busca cada tema por texto, y la búsqueda de Deezer
    devuelve pocos resultados: un tema con un título común, o que está en
    varios discos, puede no salir entre ellos aunque Deezer lo tenga. La
    discografía del artista ya está bajada entera para comparar, y ahí el tema
    se encuentra sin buscar nada.

    Es tan conservador como el cruce: el mismo título, la misma versión y la
    misma duración, con las dos duraciones a la vista. Y si con eso quedan dos
    códigos distintos, no se elige: son dos grabaciones que se llaman y duran
    igual, y no hay cómo saber cuál es. Los cortes de un megamix, que se llaman
    como el tema pero duran un tercio, quedan en blanco, que es lo correcto.

    Devuelve cuántos completó.
    """
    por_titulo: dict[str, list[TemaFaltante]] = {}
    for temas in tracklists:
        for x in temas or []:
            if x["isrc"] and x["duracion_s"]:
                por_titulo.setdefault(comparable(x["titulo"]), []).append(x)
    completados = 0
    for t in tracks:
        duracion = t.get("duration_s") or 0
        if t.get("isrc") or not duracion:
            continue
        codigos = {
            x["isrc"]
            for x in por_titulo.get(comparable(t["track"]), [])
            if abs(x["duracion_s"] - duracion) <= MARGEN_DURACION and misma_version(x["titulo"], t["track"])
        }
        if len(codigos) == 1:
            t["isrc"], t["match"] = codigos.pop(), "alta"
            completados += 1
    return completados


class _Relevado:
    """Lo que se relevó de YouTube, indexado para preguntar si un tema está."""

    def __init__(self, tracks: list[Track]):
        self.isrcs = {t["isrc"] for t in tracks if t.get("isrc")}
        self.por_titulo: dict[str, list[Track]] = {}
        for t in tracks:
            self.por_titulo.setdefault(comparable(t["track"]), []).append(t)
        # Los releases tal como los nombra YouTube: el álbum, o el propio tema
        # cuando es un single.
        self.releases = {
            (t["album"] if t["album"] != SIN_ALBUM else t["track"], t.get("release_date") or "")
            for t in tracks
        }

    def tiene(self, tema: TemaFaltante) -> bool:
        """Si esa grabación de Deezer está entre lo relevado.

        Por ISRC cuando se puede, que es exacto. Si no, por título y duración:
        el tema de YouTube puede no haber conseguido su ISRC en el cruce, y no
        por eso falta.
        """
        if tema["isrc"] and tema["isrc"] in self.isrcs:
            return True
        titulo = comparable(tema["titulo"])
        for t in self.por_titulo.get(titulo, []):
            if not misma_version(t["track"], tema["titulo"]):
                continue
            a, b = t.get("duration_s") or 0, tema["duracion_s"]
            if not a or not b or abs(a - b) <= MARGEN_DURACION:
                return True
        # La misma grabación puede llamarse apenas distinto en otra edición del
        # disco («Te Quiero de Verdad» y «Yo Te Quiero de Verdad»), con otro
        # ISRC. Si el título se parece mucho y dura lo mismo, es la misma: acá
        # un falso «falta» es ruido que tapa los que faltan de verdad. La
        # duración se exige de los dos lados, porque el parecido solo no alcanza.
        if not tema["duracion_s"]:
            return False
        for otro, ts in self.por_titulo.items():
            if SequenceMatcher(None, titulo, otro).ratio() < MIN_SIMILITUD_TITULO:
                continue
            for t in ts:
                dur = t.get("duration_s") or 0
                if (
                    dur
                    and abs(dur - tema["duracion_s"]) <= MARGEN_DURACION
                    and misma_version(t["track"], tema["titulo"])
                ):
                    return True
        return False

    def tiene_release(self, titulo, fecha) -> bool:
        return any(R.album_coincide(t, titulo, f, fecha) for t, f in self.releases)


class _Dichas:
    """Las grabaciones que ya se informaron como faltantes, para no repetirlas.

    Dos ediciones del mismo disco traen la misma grabación, a veces con el
    mismo ISRC y a veces con otro: se la reconoce por cualquiera de las dos
    cosas, el ISRC o el título con su duración.
    """

    def __init__(self):
        self.isrcs = set()
        self.titulos: dict[str, list[int]] = {}
        self.n = 0

    def esta(self, tema: TemaFaltante) -> bool:
        if tema["isrc"] and tema["isrc"] in self.isrcs:
            return True
        duraciones = self.titulos.get(comparable(tema["titulo"]), [])
        return any(abs(d - tema["duracion_s"]) <= MARGEN_DURACION for d in duraciones)

    def sumar(self, tema: TemaFaltante):
        if self.esta(tema):
            return
        self.n += 1
        if tema["isrc"]:
            self.isrcs.add(tema["isrc"])
        self.titulos.setdefault(comparable(tema["titulo"]), []).append(tema["duracion_s"])


def _grupos(tracks: list[Track]) -> dict[tuple[str, str, str], list[Track]]:
    """Los releases tal como los muestra YouTube: (álbum, distribuidora, fecha).

    Sin los singles, que no tienen tracklist que mirar, y sin lo que ya se sumó
    de Deezer.
    """
    out: dict[tuple[str, str, str], list[Track]] = {}
    for t in tracks:
        if t["album"] == SIN_ALBUM or t.get("origen") == "deezer":
            continue
        out.setdefault(_clave_release(t), []).append(t)
    return out


def _clave_release(t: Track) -> tuple[str, str, str]:
    """A qué release de YouTube pertenece un track.

    El álbum va normalizado, igual que en `productos._agrupar_por_release`:
    «Grandes Éxitos» y «GRANDES EXITOS» son el mismo disco, y ahí terminan en un
    solo producto. Si acá fueran dos, cada mitad se completaría por su lado y el
    producto saldría con los temas repetidos.
    """
    return (comparable(t["album"]), t["distributor"], t.get("release_date") or "")


def _lugar(x: TemaFaltante) -> tuple[int, int]:
    return (x["disco"] or 1, x["posicion"])


def _versiones_compatibles(t: Track, tema: TemaFaltante, album_deezer) -> bool:
    """Si lo que YouTube y Deezer dicen de la versión no se contradice.

    La versión de un tema puede estar dicha en el título del tema o en el del
    disco, y cada plataforma elige. En el disco «En Vivo En El Teatro
    Colonial», YouTube titula «Alma Mía» y Deezer «Alma Mía (En Vivo)»: es el
    mismo tema, y comparados título contra título eran dos versiones. Se junta
    lo que dice cada lado, tema y disco, y lo que dice YouTube tiene que
    estar dicho en Deezer, que es el que da más detalle: «en vivo» contra «en
    vivo, acústico» es compatible. Al revés no: si YouTube dice «(En Vivo)» y
    Deezer no lo dice ni en el tema ni en el disco, es el de estudio.
    """
    album = t.get("album") or ""
    de_youtube = marcas_version(t["track"]) | marcas_version(album if album != SIN_ALBUM else "")
    de_deezer = marcas_version(tema["titulo"]) | marcas_version(album_deezer or "")
    return de_youtube <= de_deezer


def _ubicar(t: Track, temas: list[TemaFaltante], album_deezer="") -> TemaFaltante | None:
    """El tema del tracklist que es este track, o None si no hay uno solo.

    El mismo título y, si se conocen las dos, la misma duración. Con la misma
    duración se acepta además un título parecido, y uno cortado: YouTube corta
    los títulos a cien caracteres y les pone puntos suspensivos, y el
    enganchado de seis temas de un disco no coincidía nunca con el de Deezer.

    Y con la misma duración se acepta el mismo título con la versión dicha de
    otra forma (ver `_versiones_compatibles`), pero sólo si no hay un candidato
    que coincida sin esa licencia: en un disco que trae el tema de estudio y su
    versión en vivo, el de estudio va con el de estudio.
    """
    # Por su ISRC, si lo tiene y está una sola vez en el tracklist: es la
    # prueba más fuerte, y la única que separa dos temas que se llaman igual.
    if t.get("isrc"):
        por_codigo = [x for x in temas if x["isrc"] == t["isrc"]]
        if len(por_codigo) == 1:
            return por_codigo[0]
    titulo, duracion = comparable(t["track"]), t.get("duration_s") or 0
    crudo = (t["track"] or "").rstrip()
    cortado = comparable(crudo.rstrip(".…")) if crudo.endswith(("...", "…")) else ""
    base = comparable(sin_decorado(t["track"]))
    candidatos, por_version = [], []
    for x in temas:
        otro = comparable(x["titulo"])
        ambas = bool(duracion and x["duracion_s"])
        dura_igual = ambas and abs(duracion - x["duracion_s"]) <= MARGEN_DURACION
        if cortado and len(cortado) >= 20 and dura_igual and otro.startswith(cortado):
            candidatos.append(x)
        elif not misma_version(x["titulo"], t["track"]):
            if (
                dura_igual
                and base
                and comparable(sin_decorado(x["titulo"])) == base
                and _versiones_compatibles(t, x, album_deezer)
            ):
                por_version.append(x)
        elif ambas and not dura_igual:
            continue
        elif otro == titulo or (
            dura_igual
            and (
                SequenceMatcher(None, titulo, otro).ratio() >= MIN_SIMILITUD_TITULO
                # «Sobreviviendo» y «Sobreviviendo (feat. Toti Iglesias)»: el
                # mismo tema, con los invitados escritos de un solo lado.
                or (base and comparable(sin_decorado(x["titulo"])) == base)
            )
        ):
            candidatos.append(x)
    if candidatos:
        return candidatos[0] if len(candidatos) == 1 else None
    return por_version[0] if len(por_version) == 1 else None


def _poner(t: Track, x: TemaFaltante, album_id, con_isrc=True):
    """Deja el track ubicado en ese lugar del tracklist."""
    t["track_number"], t["disc_number"], t["orden_fuente"] = x["posicion"], x["disco"] or 1, "deezer"
    t["album_deezer_id"] = album_id
    # Ubicado por título y duración en el tracklist de su propio disco, el
    # código de ese lugar es el suyo. No si se lo ubicó por descarte.
    if con_isrc and not t.get("isrc") and x["isrc"]:
        t["isrc"], t["match"] = x["isrc"], "alta"


def _soltar_los_que_chocan(grupo: list[Track]):
    """Saca de su lugar a los temas de un disco que quedaron en el mismo lugar.

    El cruce ubica por título, y un single trae a veces dos temas que se llaman
    igual: «One More Time (Radio Edit)» de 236 segundos y de 321, que en Deezer
    son el «Short Radio Edit» y el «Radio Edit». Los dos caían en el lugar 2, y
    el disco quedaba con el orden «confirmado» y un número repetido. Se los
    suelta para volver a ubicarlos por ISRC y duración, que sí los distinguen.
    """
    lugares: dict[tuple[int, int | None], list[Track]] = {}
    for t in grupo:
        if t.get("orden_fuente"):
            lugares.setdefault((t.get("disc_number") or 1, t.get("track_number")), []).append(t)
    for repetidos in lugares.values():
        if len(repetidos) > 1:
            for t in repetidos:
                t.pop("orden_fuente", None)
                t.pop("disc_number", None)
                t["track_number"] = None


def ubicar_restantes(tracks: list[Track], tracklists) -> int:
    """Ubica en el tracklist de su disco los temas que quedaron sin ubicar.

    El cruce de códigos ubica cada tema por su título, sin la duración. Acá,
    con las duraciones del tracklist a la vista, se puede ubicar además el que
    tiene el título apenas distinto o cortado. Un solo tema sin ubicar deja el
    disco entero con el orden estimado, así que cada uno cuenta.
    """
    ubicados = 0
    for grupo in _grupos(tracks).values():
        ids = {t.get("album_deezer_id") for t in grupo} - {None}
        if len(ids) != 1:
            continue
        album_id = ids.pop()
        temas = tracklists.get(album_id) or []
        _soltar_los_que_chocan(grupo)
        ocupados = {
            (t.get("disc_number") or 1, t.get("track_number")) for t in grupo if t.get("orden_fuente")
        }
        for t in grupo:
            if t.get("orden_fuente"):
                continue
            x = _ubicar(t, temas)
            if x and x["posicion"] and _lugar(x) not in ocupados:
                _poner(t, x, album_id)
                ocupados.add(_lugar(x))
                ubicados += 1
    return ubicados


# Lo que una edición le agrega al título de un disco: uno o más paréntesis, o
# algo después de un guion o de dos puntos.
_RE_AGREGADO = re.compile(r"(\s*[(\[][^)\]]*[)\]])+|\s*[-–:]\s+.+")


def _es_edicion_de(album, titulo_deezer) -> bool:
    """Si el título de Deezer es el de YouTube con algo agregado al final.

    YouTube muestra el título del disco sin su versión: «Homework» para la
    «Homework (25th Anniversary Edition)», o «TRON: Legacy - The Complete
    Edition» para la que en Deezer sigue con «(Original Motion Picture
    Soundtrack)». El título solo no alcanza para decir que son el mismo
    release, y por eso esto no lo usa el cruce: lo usa quien además tiene a la
    vista el tracklist (ver `verificar_por_tracklist`).
    """
    a, b = plegado(album).strip(), plegado(titulo_deezer).strip()
    if not comparable(a):
        return False
    if b.startswith(a) and _RE_AGREGADO.fullmatch(b[len(a) :]):
        return True
    # O el mismo título con lo de entre paréntesis escrito distinto de cada
    # lado: «Acústico en Fm Pasión (En Vivo)» y «Acústico en Fm Pasión (102.7)
    # (En Vivo)». Sin contradecirse en la versión: un «(En Vivo)» no es la
    # edición de un «(Remixes)».
    if comparable(a) == comparable(b):
        return False  # el mismo título no es una edición: eso lo mira `album_coincide`
    base_a, base_b = comparable(sin_decorado(album)), comparable(sin_decorado(titulo_deezer))
    return bool(base_a) and base_a == base_b and marcas_version(album) == marcas_version(titulo_deezer)


def _entero(grupo: list[Track]) -> bool:
    """Si el disco quedó entero en un álbum de Deezer: todos sus temas
    ubicados, y en el mismo álbum."""
    actuales = {t.get("album_deezer_id") for t in grupo} - {None}
    return len(actuales) == 1 and all(t.get("orden_fuente") for t in grupo)


# Cuántos álbumes se miran por cada disco que se busca por su título.
MAX_ALBUMES_POR_DISCO = 8


def buscar_albumes(tracks: list[Track], artista, tracklists, cruce: CruceDeezer) -> list[dict[str, Any]]:
    """Busca en Deezer, por su título, los discos que no quedaron enteros.

    La discografía del artista no alcanza. Un compilado de varios artistas
    figura a nombre de «Varios Artistas» y no está en la discografía de nadie;
    y un single puede estar en otro perfil del mismo artista, o llamarse en
    Deezer con la versión agregada («Get Lucky (Radio Edit - feat. …)»). En un
    catálogo real, trece de cuarenta y dos lanzamientos quedaban sin UPC por
    eso, con el álbum publicado en Deezer.

    Devuelve los álbumes que se llaman como alguno de esos discos, con la
    misma forma que los de la discografía, y deja sus temas en `tracklists`.
    Que se llamen igual no los acepta: eso lo decide `verificar_por_tracklist`,
    que para éstos exige además que cada tema sea del artista.
    """
    hallados: dict[int, dict[str, Any]] = {}
    for grupo in _grupos(tracks).values():
        if _entero(grupo):
            continue
        album = grupo[0]["album"]
        # Con el artista, y si así no aparece, con el título solo: un compilado
        # de varios no lleva al artista en ningún lado que el buscador mire.
        for consulta in (f"{album} {artista}", album):
            ruta = "search/album?q=" + urllib.parse.quote(consulta) + f"&limit={MAX_ALBUMES_POR_DISCO}"
            propios = [
                x
                for x in (R._deezer_json(ruta) or {}).get("data") or []
                if x.get("id")
                and (
                    R.album_coincide(album, x.get("title") or "")
                    or _es_edicion_de(album, x.get("title") or "")
                )
            ]
            for x in propios:
                if int(x["id"]) not in tracklists:
                    hallados.setdefault(int(x["id"]), x)
            if propios:
                break
    if not hallados:
        return []
    infos = R.deezer_albumes(list(hallados))
    cruce.setdefault("albumes", {}).update(infos)
    with ThreadPoolExecutor(max_workers=min(R.CODES_WORKERS, len(hallados))) as ex:
        temas_de = dict(zip(hallados, ex.map(_temas_de, hallados), strict=True))
    albumes = []
    for album_id, x in hallados.items():
        temas = temas_de[album_id]
        if not temas:
            continue
        tracklists[album_id] = temas
        info = infos.get(album_id) or {}
        albumes.append(
            {
                "id": album_id,
                "title": info.get("title") or x.get("title") or "",
                "release_date": info.get("release_date") or "",
                "record_type": info.get("record_type") or x.get("record_type") or "",
            }
        )
    return albumes


# Qué parte de un disco tiene que estar ubicada sin dudas para ubicar al resto
# por descarte, y con cuántos temas como mínimo.
MIN_UBICADOS_PARA_DESCARTE = 0.75
MIN_TEMAS_PARA_DESCARTE = 4
# Qué parte del álbum de Deezer tiene que mostrar YouTube para aceptarlo con
# otra fecha y temas de más.
MIN_PARTE_DEL_ALBUM = 0.8


def _por_descarte(grupo: list[Track], temas: list[TemaFaltante], lugares) -> set[int]:
    """Ubica por su título los temas que quedaron sin ubicar, en los lugares
    que quedaron libres. Modifica `lugares` y devuelve los índices que llenó.

    Con casi todo el disco ubicado sin dudas, el tema que queda y el lugar que
    queda, si se llaman igual, son el mismo aunque la duración no coincida: en
    un disco real, cinco de seis temas tenían su ISRC en el álbum de Deezer y
    el sexto figuraba ahí con otra duración. Sirve para dar el disco por
    verificado y ordenarlo; el ISRC de ese lugar no se le pone, porque la
    duración distinta puede ser otra grabación.
    """
    n = len(grupo)
    ubicados = sum(1 for x in lugares if x)
    if ubicados == n or n < MIN_TEMAS_PARA_DESCARTE or ubicados < MIN_UBICADOS_PARA_DESCARTE * n:
        return set()
    usados = {_lugar(x) for x in lugares if x}
    llenados = set()
    for i, t in enumerate(grupo):
        if lugares[i]:
            continue
        base = comparable(sin_decorado(t["track"]))
        libres = [
            x
            for x in temas
            if x["posicion"] and _lugar(x) not in usados and comparable(sin_decorado(x["titulo"])) == base
        ]
        if base and len(libres) == 1:
            lugares[i] = libres[0]
            usados.add(_lugar(libres[0]))
            llenados.add(i)
    return llenados


# Las formas de verificar que no dependen de que el álbum esté libre: por la
# fecha, o por la lista exacta de temas.
_FORMAS_FIRMES = ("fecha", "exacto")


def _con_su_isrc(grupo: list[Track], lugares) -> bool:
    """Si cada tema del disco quedó en un lugar que lleva su mismo ISRC."""
    return all(x and t.get("isrc") and x["isrc"] == t["isrc"] for t, x in zip(grupo, lugares, strict=True))


# Parecido mínimo entre el sello que declara YouTube y el de Deezer.
MIN_SIMILITUD_SELLO = 0.8


def _mismo_sello(a, b) -> bool:
    na, nb = comparable(a), comparable(b)
    if not na or not nb:
        return False
    return na in nb or nb in na or SequenceMatcher(None, na, nb).ratio() >= MIN_SIMILITUD_SELLO


def _del_mismo_sello(grupo: list[Track], candidatos, cruce: CruceDeezer):
    """De varios álbumes que calzan igual, los del sello que declara YouTube.

    El mismo single puede estar dos veces en Deezer, entregado por dos
    distribuidoras, con el mismo tema y dos UPC. Lo que los separa es el
    sello: YouTube lo publica en cada tema (la línea ℗ y «Provided to YouTube
    by»), y Deezer en el álbum. Si ninguno coincide, o coinciden varios, se
    devuelven todos y no se elige.
    """
    de_youtube = {t.get(campo) or "" for t in grupo for campo in ("label", "distributor")} - {""}
    if not de_youtube:
        return candidatos
    ids = [int(c[1]["id"]) for c in candidatos]
    albumes = cruce.setdefault("albumes", {})
    faltan = [i for i in ids if i not in albumes]
    if faltan:
        albumes.update(R.deezer_albumes(faltan))
    propios = [
        c
        for c in candidatos
        if any(_mismo_sello((albumes.get(int(c[1]["id"])) or {}).get("label", ""), s) for s in de_youtube)
    ]
    return propios or candidatos


def _es_de(tema: TemaFaltante, nombres) -> bool:
    """Si ese tema de Deezer figura a nombre de alguno de esos artistas."""
    de = comparable(tema["artista"])
    for nombre in nombres:
        n = comparable(nombre)
        if n and de and (n in de or de in n or _mismo_artista(tema["artista"], nombre)):
            return True
    return False


def verificar_por_tracklist(
    tracks: list[Track], discos, tracklists, cruce: CruceDeezer, de_artistas=None
) -> int:
    """Verifica contra la discografía los discos que el cruce no dejó enteros.

    El cruce verifica un disco cuando la búsqueda de alguno de sus temas cae en
    un álbum de Deezer que se llama igual. Hay dos formas de que eso salga mal:

      - Ninguna búsqueda cae ahí, porque cada tema está también en un compilado
        y la búsqueda devuelve ése. El disco queda sin UPC y con el orden
        estimado aunque Deezer lo tenga.
      - Cae en otra edición del disco. YouTube llama «Homework» a la edición
        aniversario, de 31 temas, y la búsqueda de sus temas más conocidos cae
        en el «Homework» original, de 16. El disco quedaba con el UPC del
        original, 13 temas sin ubicar y el orden estimado; y la edición
        aniversario entraba aparte, entera, como si no estuviera en YouTube.

    Con la discografía entera se lo busca al revés: el álbum que se llama
    igual, o igual con una edición agregada al título, y en cuyo tracklist
    están TODOS los temas del disco, cada uno en un lugar distinto, por ISRC o
    por título y duración. Sólo se miran los discos que no quedaron enteros en
    un álbum: uno ya verificado y con todos sus temas ubicados no se toca.

    Tres formas de aceptarlo, de más a menos segura:

      - Coincide además la fecha de lanzamiento. Es el mismo release, y puede
        tener más temas de los que YouTube muestra.
      - La fecha no coincide, pero el tracklist es exactamente el mismo: los
        mismos temas, ni uno más. Suele ser el mismo release con la fecha
        original de un lado y la de la edición digital del otro.
      - YouTube no publica la fecha del disco, así que no hay fecha que lo
        contradiga, y el álbum tiene todos sus temas y alguno más.
      - La fecha no coincide y el álbum tiene algún tema de más, pero YouTube
        muestra casi todo: cuatro temas o más, y al menos cuatro de cada cinco
        del álbum.
      - La fecha no coincide y el álbum tiene temas de más, pero cada tema del
        disco está ahí con su mismo ISRC. Es lo que pasa cuando YouTube muestra
        una parte del release (no repite una grabación que ya tiene en otro
        disco) y lo fecha distinto.

    `de_artistas`, si se pasa, son los nombres del artista: los álbumes que
    se evalúan no salieron de su discografía sino de buscar por título (ver
    `buscar_albumes`), y entonces cada tema ubicado tiene que figurar a su
    nombre. Sin eso, un single que se llama «Loca» se verificaría contra el
    «Loca» de cualquiera que dure parecido.

    Las dos últimas quedan anotadas (`upc_por_tracklist`) para que la
    validación lo diga. En cada forma tiene que haber un solo candidato. Si
    hay varios se desempata, en este orden: el que se llama igual que en
    YouTube antes que su edición; el que tiene cada tema con su mismo ISRC; y
    el que es del mismo sello que el disco en YouTube, que es lo que separa dos
    entregas del mismo single por dos distribuidoras. Con dos que siguen
    calzando igual no se elige. Devuelve cuántos discos verificó.
    """
    verificados = 0
    # A qué lanzamiento del catálogo corresponde ya cada álbum de Deezer.
    ocupados: dict[int, set[tuple[str, str, str]]] = {}
    for clave, grupo in _grupos(tracks).items():
        for t in grupo:
            album_id = t.get("album_deezer_id")
            if album_id and t.get("orden_fuente"):
                ocupados.setdefault(int(album_id), set()).add(clave)
    # Dos pasadas: primero lo que se verifica por la fecha o por la lista
    # exacta, y recién después las formas más flojas, que ya ven qué álbumes
    # quedaron tomados.
    for solo_firmes in (True, False):
        for clave, grupo in _grupos(tracks).items():
            fecha = clave[2]
            actuales = {t.get("album_deezer_id") for t in grupo} - {None}
            if _entero(grupo):
                continue
            # El título como lo escribe YouTube, y no el normalizado de la clave:
            # los paréntesis dicen qué versión es («(En Vivo)»), y ahí se pierden.
            album = grupo[0]["album"]
            formas: dict[str, list[tuple[bool, dict[str, Any], list[TemaFaltante | None], set[int]]]] = {
                "fecha": [],
                "exacto": [],
                "sin_fecha": [],
                "isrc": [],
                "casi": [],
            }
            for a in discos:
                titulo = a.get("title") or ""
                mismo_titulo = R.album_coincide(album, titulo)
                temas = tracklists.get(int(a["id"])) or []
                if not temas or not (mismo_titulo or _es_edicion_de(album, titulo)):
                    continue
                lugares = [_ubicar(t, temas, titulo) for t in grupo]
                descarte = _por_descarte(grupo, temas, lugares)
                if not all(x and x["posicion"] for x in lugares):
                    continue
                if len({_lugar(x) for x in lugares if x}) != len(grupo):
                    continue
                if de_artistas is not None and not all(x and _es_de(x, de_artistas) for x in lugares):
                    continue
                fecha_dz = a.get("release_date") or ""
                if fecha and fecha_dz and R.fechas_cercanas(fecha, fecha_dz):
                    forma = "fecha"
                elif len(temas) == len(grupo):
                    forma = "exacto"
                elif not fecha:
                    forma = "sin_fecha"
                elif _con_su_isrc(grupo, lugares):
                    forma = "isrc"
                elif len(grupo) >= MIN_TEMAS_PARA_DESCARTE and len(grupo) >= MIN_PARTE_DEL_ALBUM * len(temas):
                    forma = "casi"
                else:
                    continue
                # Un álbum que ya es de otro lanzamiento del catálogo no se
                # toma por una forma floja: tres singles de remixes terminaban
                # siendo, cada uno, el álbum de remixes entero.
                if forma not in _FORMAS_FIRMES and ocupados.get(int(a["id"]), set()) - {clave}:
                    continue
                formas[forma].append((mismo_titulo, a, lugares, descarte))
            forma, candidatos = next(((f, c) for f, c in formas.items() if c), ("", []))
            if solo_firmes and forma not in _FORMAS_FIRMES:
                continue
            if any(c[0] for c in candidatos):
                candidatos = [c for c in candidatos if c[0]]
            # Entre varios, el que todavía no es de otro lanzamiento: dos
            # singles que se llaman igual van cada uno con el suyo.
            libres = [c for c in candidatos if not ocupados.get(int(c[1]["id"]), set()) - {clave}]
            if len(candidatos) > 1 and libres:
                candidatos = libres
            if len(candidatos) > 1 and any(_con_su_isrc(grupo, c[2]) for c in candidatos):
                candidatos = [c for c in candidatos if _con_su_isrc(grupo, c[2])]
            if len(candidatos) > 1:
                candidatos = _del_mismo_sello(grupo, candidatos, cruce)
            if len(candidatos) != 1:
                continue
            _mismo, a, lugares, descarte = candidatos[0]
            album_id = int(a["id"])
            info = R.deezer_albumes([album_id]).get(album_id) or {}
            if actuales and not info.get("upc"):
                # El disco ya tiene un UPC, de otro álbum. Sin el de éste no se lo
                # cambia: quedaría ordenado por un álbum y con el código de otro.
                continue
            cruce.setdefault("albumes", {})[album_id] = info
            for i, (t, x) in enumerate(zip(grupo, lugares, strict=True)):
                if x is None:  # ya se comprobó arriba que están todos
                    continue
                _poner(t, x, album_id, con_isrc=i not in descarte)
                t["upc"] = info.get("upc", "") or ("" if actuales else t["upc"])
                t.pop("upc_descartado", None)
                if forma != "fecha":
                    t["upc_por_tracklist"] = f"{a.get('title') or ''} ({a.get('release_date') or ''})"
            ocupados.setdefault(album_id, set()).add(clave)
            verificados += 1
    return verificados


def revisar(tracks: list[Track], cruce: CruceDeezer, artista, avance=None, artista_deezer=0) -> Completitud:
    """Compara lo relevado contra la discografía de Deezer.

    De quién es la discografía, por orden: el perfil que indicó el usuario
    (`artista_deezer`, su id), el dueño de los álbumes que el cruce verificó,
    o el que se encuentra buscando por nombre y comprobando con sus temas (ver
    `buscar_artista`). `como` dice cuál de los tres fue.

    Antes de ver qué falta, usa la discografía para mejorar lo relevado:
    completa los ISRC que la búsqueda no encontró, ubica en su disco los temas
    que quedaron sin ubicar y verifica los discos que el cruce no verificó.

    `avance(hechos, total)` se llama al terminar cada release, para mover la
    barra y dejar cancelar. Nunca levanta por Deezer: si no contesta, la
    revisión queda sin hacer y `revisada` lo dice.
    """
    res = completitud_vacia()
    if artista_deezer:
        artistas, como = artista_por_id(artista_deezer), "manual"
    else:
        artistas, como = artistas_en_deezer(tracks, cruce, artista), "cruce"
        if not artistas:
            artistas, como = buscar_artista(tracks, artista), "nombre"
    if not artistas:
        return res
    discos, recortada = discografia([aid for aid, _nombre in artistas])
    if not discos:
        return res
    sin_isrc = [t for t in tracks if not t.get("isrc")]

    with ThreadPoolExecutor(max_workers=min(R.CODES_WORKERS, len(discos))) as ex:
        temas_por_disco = []
        for i, temas in enumerate(ex.map(lambda a: _temas_de(a["id"]), discos), 1):
            temas_por_disco.append(temas)
            if avance:
                avance(i, len(discos))
    tracklists: dict[int, list[TemaFaltante]] = {
        int(a["id"]): temas for a, temas in zip(discos, temas_por_disco, strict=True) if temas is not None
    }
    res["sin_respuesta"] = sum(1 for temas in temas_por_disco if temas is None)

    # Los discos que el cruce verificó y que no son de la discografía del
    # artista: un compilado, que en Deezer figura a nombre del sello.
    for album_id in {t.get("album_deezer_id") or 0 for t in tracks} - {0} - set(tracklists):
        temas = _temas_de(album_id)
        if temas is not None:
            tracklists[album_id] = temas

    # Antes de ver qué falta: un tema que consigue acá su código o su lugar
    # deja de depender del título para que se lo reconozca.
    ubicar_restantes(tracks, tracklists)
    # Los ISRC se completan después de verificar, y no antes: una de las formas
    # de verificar es que cada tema esté en el álbum con su mismo ISRC, y eso
    # vale si el ISRC lo encontró el cruce, no si salió de ese mismo álbum.
    res["verificados_por_tracklist"] = verificar_por_tracklist(tracks, discos, tracklists, cruce)
    # Lo que la discografía no resolvió se busca disco por disco, por su
    # título. Estos álbumes sirven para verificar, y nada más: no entran a la
    # cuenta de lo que falta, que es sobre la discografía del artista.
    por_titulo = buscar_albumes(tracks, artista, tracklists, cruce)
    if por_titulo:
        nombres = [artista] + [nombre for _aid, nombre in artistas]
        res["verificados_por_tracklist"] += verificar_por_tracklist(
            tracks, por_titulo, tracklists, cruce, de_artistas=nombres
        )
        # Los que no resultaron ser de este catálogo se van: sus temas son de
        # otros artistas, y de ahí no puede salir un ISRC ni un faltante.
        usados = {t.get("album_deezer_id") for t in tracks}
        for a in por_titulo:
            if int(a["id"]) not in usados:
                tracklists.pop(int(a["id"]), None)
    completar_isrc(tracks, tracklists.values())
    # Los que consiguieron su código en esta revisión, por cualquiera de las
    # dos vías: su lugar en el disco, o su título y duración en la discografía.
    res["isrc_completados"] = sum(1 for t in sin_isrc if t.get("isrc"))
    relevado = _Relevado(tracks)
    verificados = set(cruce.get("verificados") or {}) | {
        t.get("album_deezer_id") for t in tracks if t.get("album_deezer_id")
    }

    candidatos: list[ReleaseIncompleto] = []
    for a in discos:
        temas = tracklists.get(int(a["id"]))
        if temas is None:
            continue
        faltan = [x for x in temas if not relevado.tiene(x)]
        if not faltan:
            continue
        titulo, fecha = a.get("title") or "", a.get("release_date") or ""
        candidatos.append(
            {
                "deezer_id": int(a["id"]),
                "titulo": titulo,
                "tipo": a.get("record_type") or "",
                "fecha": fecha,
                "upc": ((cruce.get("albumes") or {}).get(a["id"]) or {}).get("upc", ""),
                "relevado": a["id"] in verificados or relevado.tiene_release(titulo, fecha),
                "total": len(temas),
                "temas": faltan,
                "sumado": False,
            }
        )

    # Primero los releases que sí se relevaron, y después los que no, por fecha.
    # Un release que no se relevó y cuyas faltas ya están todas dichas es otra
    # edición del mismo disco (la de 1991 y su reedición de 2019): repetirlo
    # sería contar dos veces la misma grabación.
    candidatos.sort(key=lambda f: (not f["relevado"], f["fecha"], f["titulo"]))
    dichas = _Dichas()
    for f in candidatos:
        if not f["relevado"] and all(dichas.esta(x) for x in f["temas"]):
            continue
        for x in f["temas"]:
            dichas.sumar(x)
        res["faltan"].append(f)

    # Los datos del álbum de los que no se conocen todavía: el UPC, que es con
    # lo que se los busca después, y el sello. Se piden sólo para los que se
    # van a mostrar, y quedan en el cruce junto con los tracklists, que es lo
    # que usa `sumar_de_deezer`.
    albumes = cruce.setdefault("albumes", {})
    sin_datos = [f["deezer_id"] for f in res["faltan"] if f["deezer_id"] not in albumes]
    if sin_datos:
        albumes.update(R.deezer_albumes(sin_datos))
    for f in res["faltan"]:
        f["upc"] = f["upc"] or (albumes.get(f["deezer_id"]) or {}).get("upc", "")
    cruce["discografia"] = tracklists

    res.update(
        revisada=True,
        artista_deezer=artistas[0][1],
        artista_id=artistas[0][0],
        como=como,
        releases=len(discos),
        temas=dichas.n,
        recortada=recortada,
    )
    return res


def fechar_desde_deezer(tracks: list[Track], cruce: CruceDeezer) -> int:
    """Le anota a cada tema sin fecha la de su disco en Deezer (`fecha_deezer`).

    YouTube publica la fecha de lanzamiento de un disco en cada tema, pero no
    siempre: en un catálogo real, más de la mitad de los discos no la traían,
    y en la hoja de ingesta la fecha quedaba para completar a mano aunque el
    disco estuviera verificado contra Deezer, que la tiene.

    Sólo para los temas ubicados en un álbum cuyo UPC es el que llevan: es la
    fecha de ESE release, no la de un álbum que se llama parecido. No pisa la
    fecha de YouTube, y va en un campo aparte para que se sepa de dónde salió
    (ver `productos.group_products`). Devuelve a cuántos temas se la anotó.
    """
    albumes = cruce.get("albumes") or {}
    anotados = 0
    for t in tracks:
        info = albumes.get(t.get("album_deezer_id") or 0) or {}
        fecha = info.get("release_date") or ""
        if t.get("release_date") or not t.get("upc") or t["upc"] != info.get("upc"):
            continue
        # Deezer devuelve «0000-00-00» cuando no sabe la fecha.
        anio = _anio(fecha)
        if isinstance(anio, int) and anio >= 1900:
            t["fecha_deezer"] = fecha
            anotados += 1
    return anotados


URL_DEEZER = "https://www.deezer.com/track/{id}"


def _track_de_deezer(tema: TemaFaltante, **datos) -> Track:
    """Un tema de Deezer con la forma de un track relevado.

    Lo que YouTube habría dicho y Deezer no dice queda vacío: no tiene video,
    ni vistas, ni línea ℗, ni créditos. `origen` lo marca para que nadie lo
    tome por un tema que se vio en YouTube.
    """
    t: Track = {
        "video_id": "",
        "track": tema["titulo"],
        "album": datos["album"],
        "distributor": datos["distributor"],
        "label": datos["label"],
        "release_year": datos["anio"],
        "isrc": tema["isrc"],
        "upc": datos["upc"],
        # El código no sale de un cruce por parecido: es el del propio tema.
        "match": "alta" if tema["isrc"] else "",
        "duration_s": tema["duracion_s"],
        "views": 0,
        "likes": 0,
        "comments": 0,
        "upload_date": "",
        "release_date": datos["fecha"],
        "p_line": "",
        # Deezer puede escribir al artista apenas distinto («Los De Maranaho»):
        # si es el del canal, va como lo escribe el canal, que es como figura
        # en el resto del catálogo.
        "artists": [datos.get("artista") or tema["artista"]] if tema["artista"] else [],
        "credits": {"composers": [], "lyricists": [], "producers": [], "publishers": []},
        "desc3": "",
        "url": URL_DEEZER.format(id=tema["deezer_id"]) if tema["deezer_id"] else "",
        "track_number": tema["posicion"],
        "disc_number": tema["disco"] or 1,
        "orden_fuente": "deezer",
        "album_deezer_id": datos["aid"],
        "origen": "deezer",
    }
    return t


def _mismo_artista(a, b) -> bool:
    return SequenceMatcher(None, plegado(a), plegado(b)).ratio() >= MIN_SIMILITUD_ARTISTA


def _como_el_canal(nombre, artista) -> str:
    """El nombre del artista del canal, si `nombre` es ese artista; si no, "" ."""
    return artista if (nombre and artista and _mismo_artista(nombre, artista)) else ""


def _anio(fecha) -> int | str:
    return int(fecha[:4]) if fecha[:4].isdigit() else ""


def sumar_de_deezer(
    tracks: list[Track], completitud: Completitud, cruce: CruceDeezer, artista=""
) -> list[Track]:
    """Los temas que le faltan a lo relevado, como tracks para agrupar.

    Un release se entrega entero, y YouTube no siempre lo muestra entero: no
    repite una grabación que ya tiene en otro disco, así que de un compilado de
    cincuenta temas puede mostrar doce. Y el buscador puede no traer alguno.
    Tres casos:

      - **El disco está, verificado y con el orden confirmado, y le faltan
        lugares de su tracklist.** Lo que falta entra al disco, en su posición,
        con la distribuidora y el UPC del disco. Es el mismo release: lo dice
        el UPC. Si la grabación está en YouTube en otro disco, el tema lleva
        ese video, que es de donde se puede sacar el audio de referencia.
      - **El disco está pero lo que le falta es de otro artista**: un disco
        compartido, o un compilado de varios. No se completa con temas ajenos:
        queda anotado qué le falta (`cruce["incompletos"]`).
      - **El disco entero no apareció.** Se arma con todo su tracklist de
        Deezer. Queda sin distribuidora, que es un dato que sólo publica
        YouTube, y marcado para que la interfaz no lo elija sola: puede ser una
        colaboración que está en el canal de otro artista, o un release que
        nunca se entregó a YouTube.

    Todo lo sumado lleva `origen: "deezer"`. Marca en cada release de
    `completitud["faltan"]` si se pudo sumar. No pide nada a la red: todo lo
    que usa quedó en `cruce` cuando se revisó.
    """
    nuevos: list[Track] = []
    tracklists = cruce.get("discografia") or {}
    albumes = cruce.get("albumes") or {}
    con_video: dict[str, Track] = {}
    for t in tracks:
        if t.get("isrc") and t.get("video_id"):
            con_video.setdefault(t["isrc"], t)

    completados = set()
    incompletos: dict[tuple[str, str, str], list[str]] = {}
    for clave, grupo in _grupos(tracks).items():
        ids = {t.get("album_deezer_id") for t in grupo}
        if len(ids) != 1 or None in ids or not all(t.get("orden_fuente") for t in grupo):
            continue
        album_id = ids.pop()
        temas = tracklists.get(album_id or 0) or []
        ocupados = {(t.get("disc_number") or 1, t.get("track_number")) for t in grupo}
        libres = [x for x in temas if _lugar(x) not in ocupados]
        if not libres:
            continue
        # De quién son los temas que faltan, y no de quién es el álbum: un
        # compilado del artista figura en Deezer a nombre del sello, y es suyo
        # entero. Si el tema no dice de quién es, vale el titular del álbum.
        titular = (albumes.get(album_id or 0) or {}).get("artist_name") or ""
        ajeno = bool(artista) and any(
            not _mismo_artista(x["artista"] or titular or artista, artista) for x in libres
        )
        if ajeno or not all(x["posicion"] for x in temas):
            incompletos[clave] = [x["titulo"] for x in libres]
            continue
        ref = grupo[0]
        for x in libres:
            nuevo = _track_de_deezer(
                x,
                album=ref["album"],
                distributor=ref["distributor"],
                # El sello vacío: el del disco sale de sus temas de YouTube.
                label="",
                anio=ref["release_year"],
                upc=ref["upc"],
                fecha=ref.get("release_date") or "",
                aid=album_id,
                artista=_como_el_canal(x["artista"], artista),
            )
            gemelo = con_video.get(x["isrc"]) if x["isrc"] else None
            if gemelo:
                nuevo["video_id"], nuevo["url"] = gemelo["video_id"], gemelo["url"]
            nuevos.append(nuevo)
        completados.add(album_id)
    cruce["incompletos"] = incompletos

    for f in completitud["faltan"]:
        album_id = f["deezer_id"]
        if f["relevado"]:
            f["sumado"] = album_id in completados
            continue
        temas = tracklists.get(album_id) or []
        if not temas or not all(x["posicion"] for x in temas):
            continue
        info = albumes.get(album_id) or {}
        nuevos.extend(
            _track_de_deezer(
                x,
                # Un release de un solo tema es un single: se llama como el tema.
                album=f["titulo"] if len(temas) > 1 else SIN_ALBUM,
                distributor=SIN_DATOS,
                label=info.get("label", ""),
                anio=_anio(f["fecha"]),
                upc=f["upc"],
                fecha=f["fecha"],
                aid=album_id,
                artista=_como_el_canal(x["artista"], artista),
            )
            for x in temas
        )
        f["sumado"] = True
    return nuevos


def marcar(
    productos: list[Producto], completitud: Completitud, cruce: CruceDeezer | None = None
) -> list[Producto]:
    """Le anota a cada producto lo que salió de la comparación con Deezer.

    Los temas que el release tiene en Deezer y acá no están (`faltan_temas`),
    cuando no se pudieron sumar: así el aviso sale pegado al disco, en la tabla
    y en la validación, que es donde se lo va a ir a buscar. Y cuántos de sus
    temas vienen de Deezer (`de_deezer`, `origen`), cuando sí.

    Un release que sólo está en Deezer puede figurar ahí a nombre de otro
    artista: una colaboración, que Deezer lista en la discografía de los dos.
    En ese caso el producto queda a nombre de quien figura, no del canal, para
    que la hoja no le adjudique al artista un release que no es suyo.
    """
    albumes = (cruce or {}).get("albumes") or {}
    incompletos = (cruce or {}).get("incompletos") or {}
    for p in productos:
        de_deezer = sum(1 for t in p["tracks"] if t.get("origen") == "deezer")
        if de_deezer:
            p["de_deezer"] = de_deezer
        if de_deezer and de_deezer == len(p["tracks"]):
            p["origen"] = "deezer"
            titular = (albumes.get(p["tracks"][0].get("album_deezer_id") or 0) or {}).get("artist_name") or ""
            if titular and not _mismo_artista(titular, p["artist"]):
                p["artist"] = titular
    relevados = [f for f in completitud["faltan"] if f["relevado"] and not f["sumado"]]
    for p in productos:
        ids = {t.get("album_deezer_id") for t in p["tracks"]} - {None}
        temas: list[str] = []
        for t in p["tracks"]:
            temas.extend(x for x in incompletos.get(_clave_release(t), []) if x not in temas)
        for f in relevados:
            suyo = f["deezer_id"] in ids or (
                not ids and R.album_coincide(p["title"], f["titulo"], p.get("release_date") or "", f["fecha"])
            )
            if suyo:
                temas.extend(x["titulo"] for x in f["temas"] if x["titulo"] not in temas)
        if temas:
            p["faltan_temas"] = temas
    return productos
