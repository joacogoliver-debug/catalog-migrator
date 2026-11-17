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
termina con la discografía de un homónimo. Con ese artista se pide su
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
"""

from collections import Counter
from typing import Any
from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher

from . import relevar_core as R
from .contratos import Completitud, CruceDeezer, Producto, ReleaseIncompleto, TemaFaltante, Track
from .productos import SIN_ALBUM, SIN_DATOS
from .texto import comparable, misma_version, plegado

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


def _ubicar(t: Track, temas: list[TemaFaltante]) -> TemaFaltante | None:
    """El tema del tracklist que es este track, o None si no hay uno solo.

    El mismo título y, si se conocen las dos, la misma duración. Con la misma
    duración se acepta además un título parecido, y uno cortado: YouTube corta
    los títulos a cien caracteres y les pone puntos suspensivos, y el
    enganchado de seis temas de un disco no coincidía nunca con el de Deezer.
    """
    titulo, duracion = comparable(t["track"]), t.get("duration_s") or 0
    crudo = (t["track"] or "").rstrip()
    cortado = comparable(crudo.rstrip(".…")) if crudo.endswith(("...", "…")) else ""
    candidatos = []
    for x in temas:
        otro = comparable(x["titulo"])
        ambas = bool(duracion and x["duracion_s"])
        dura_igual = ambas and abs(duracion - x["duracion_s"]) <= MARGEN_DURACION
        if cortado and len(cortado) >= 20 and dura_igual and otro.startswith(cortado):
            candidatos.append(x)
        elif not misma_version(x["titulo"], t["track"]) or (ambas and not dura_igual):
            continue
        elif otro == titulo or (
            dura_igual and SequenceMatcher(None, titulo, otro).ratio() >= MIN_SIMILITUD_TITULO
        ):
            candidatos.append(x)
    return candidatos[0] if len(candidatos) == 1 else None


def _poner(t: Track, x: TemaFaltante, album_id):
    """Deja el track ubicado en ese lugar del tracklist."""
    t["track_number"], t["disc_number"], t["orden_fuente"] = x["posicion"], x["disco"] or 1, "deezer"
    t["album_deezer_id"] = album_id
    # Ubicado por título y duración en el tracklist de su propio disco, el
    # código de ese lugar es el suyo.
    if not t.get("isrc") and x["isrc"]:
        t["isrc"], t["match"] = x["isrc"], "alta"


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


def verificar_por_tracklist(tracks: list[Track], discos, tracklists, cruce: CruceDeezer) -> int:
    """Verifica contra la discografía los discos que el cruce no pudo verificar.

    El cruce verifica un disco cuando la búsqueda de alguno de sus temas cae en
    ese álbum de Deezer. Si ninguna cae ahí, porque cada tema está también en
    un compilado y la búsqueda devuelve ése, el disco queda sin UPC y con el
    orden estimado aunque Deezer lo tenga. Con la discografía entera se lo
    busca al revés: el álbum que se llama igual y en cuyo tracklist están
    TODOS los temas del disco, cada uno en un lugar distinto, por título y
    duración.

    Dos formas de aceptarlo, de más a menos segura:

      - Coincide además la fecha de lanzamiento. Es el mismo release, y puede
        tener más temas de los que YouTube muestra.
      - La fecha no coincide, pero el tracklist es exactamente el mismo: los
        mismos temas, ni uno más. Suele ser el mismo release con la fecha
        original de un lado y la de la edición digital del otro. Se acepta, y
        queda anotado (`upc_por_tracklist`) para que la validación lo diga.

    En los dos casos tiene que haber un solo candidato. Con dos ediciones que
    calzan igual no se elige. Devuelve cuántos discos verificó.
    """
    verificados = 0
    for (_album, _dist, fecha), grupo in _grupos(tracks).items():
        if any(t.get("album_deezer_id") for t in grupo):
            continue
        # El título como lo escribe YouTube, y no el normalizado de la clave:
        # los paréntesis dicen qué versión es («(En Vivo)»), y ahí se pierden.
        album = grupo[0]["album"]
        misma_fecha, exactos = [], []
        for a in discos:
            temas = tracklists.get(int(a["id"])) or []
            if not temas or not R.album_coincide(album, a.get("title") or ""):
                continue
            lugares = [_ubicar(t, temas) for t in grupo]
            if not all(x and x["posicion"] for x in lugares):
                continue
            if len({_lugar(x) for x in lugares if x}) != len(grupo):
                continue
            fecha_dz = a.get("release_date") or ""
            if fecha and fecha_dz and R.fechas_cercanas(fecha, fecha_dz):
                misma_fecha.append((a, lugares))
            elif len(temas) == len(grupo):
                exactos.append((a, lugares))
        candidatos = misma_fecha or exactos
        if len(candidatos) != 1:
            continue
        a, lugares = candidatos[0]
        album_id = int(a["id"])
        info = R.deezer_albumes([album_id]).get(album_id) or {}
        cruce.setdefault("albumes", {})[album_id] = info
        for t, x in zip(grupo, lugares, strict=True):
            if x is None:  # ya se comprobó arriba que están todos
                continue
            _poner(t, x, album_id)
            t["upc"] = info.get("upc", "") or t["upc"]
            t.pop("upc_descartado", None)
            if not misma_fecha:
                t["upc_por_tracklist"] = f"{a.get('title') or ''} ({a.get('release_date') or ''})"
        verificados += 1
    return verificados


def revisar(tracks: list[Track], cruce: CruceDeezer, artista, avance=None) -> Completitud:
    """Compara lo relevado contra la discografía de Deezer.

    Antes de ver qué falta, usa la discografía para mejorar lo relevado:
    completa los ISRC que la búsqueda no encontró, ubica en su disco los temas
    que quedaron sin ubicar y verifica los discos que el cruce no verificó.

    `avance(hechos, total)` se llama al terminar cada release, para mover la
    barra y dejar cancelar. Nunca levanta por Deezer: si no contesta, la
    revisión queda sin hacer y `revisada` lo dice.
    """
    res = completitud_vacia()
    artistas = artistas_en_deezer(tracks, cruce, artista)
    if not artistas:
        return res
    discos, recortada = discografia([aid for aid, _nombre in artistas])
    if not discos:
        return res

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
    res["isrc_completados"] = completar_isrc(tracks, tracklists.values())
    ubicar_restantes(tracks, tracklists)
    res["verificados_por_tracklist"] = verificar_por_tracklist(tracks, discos, tracklists, cruce)
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
        releases=len(discos),
        temas=dichas.n,
        recortada=recortada,
    )
    return res


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
