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

Lo que NO hace. No agrega productos: de un release que sólo está en Deezer se
conocen el título, el UPC y los ISRC, pero no la distribuidora, que es un dato
que sólo publica YouTube. Y que algo falte en YouTube no dice por qué: puede ser
que el buscador no lo trajo, que esté en el canal de otro artista o que nunca se
haya entregado a YouTube. Por eso esto informa y no corrige.

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
from .productos import SIN_ALBUM
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
        if SequenceMatcher(None, objetivo, plegado(nombre)).ratio() >= MIN_SIMILITUD_ARTISTA:
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
        }
        for x in datos.get("data") or []
    ]


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


def revisar(tracks: list[Track], cruce: CruceDeezer, artista, avance=None) -> Completitud:
    """Compara lo relevado contra la discografía de Deezer.

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

    relevado = _Relevado(tracks)
    verificados = set(cruce.get("verificados") or {}) | {
        t.get("album_deezer_id") for t in tracks if t.get("album_deezer_id")
    }

    with ThreadPoolExecutor(max_workers=min(R.CODES_WORKERS, len(discos))) as ex:
        temas_por_disco = []
        for i, temas in enumerate(ex.map(lambda a: _temas_de(a["id"]), discos), 1):
            temas_por_disco.append(temas)
            if avance:
                avance(i, len(discos))

    candidatos: list[ReleaseIncompleto] = []
    for a, temas in zip(discos, temas_por_disco, strict=True):
        if temas is None:
            res["sin_respuesta"] += 1
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

    # El UPC de los que no se relevaron, que es con lo que se los busca después.
    # Se pide sólo para los que se van a mostrar.
    sin_upc = [f for f in res["faltan"] if not f["upc"]]
    if sin_upc:
        with ThreadPoolExecutor(max_workers=min(R.CODES_WORKERS, len(sin_upc))) as ex:
            for f, datos in zip(
                sin_upc, ex.map(lambda f: R._deezer_json(f"album/{f['deezer_id']}"), sin_upc), strict=True
            ):
                f["upc"] = (datos or {}).get("upc", "") or ""

    res.update(
        revisada=True,
        artista_deezer=artistas[0][1],
        releases=len(discos),
        temas=dichas.n,
        recortada=recortada,
    )
    return res


def marcar(productos: list[Producto], completitud: Completitud) -> list[Producto]:
    """Le anota a cada producto los temas que Deezer tiene y acá no están.

    Así el aviso sale pegado al disco, en la tabla y en la validación, además
    de en la lista general: es donde se lo va a ir a buscar.
    """
    relevados = [f for f in completitud["faltan"] if f["relevado"]]
    for p in productos:
        ids = {t.get("album_deezer_id") for t in p["tracks"]} - {None}
        temas = []
        for f in relevados:
            suyo = f["deezer_id"] in ids or (
                not ids and R.album_coincide(p["title"], f["titulo"], p.get("release_date") or "", f["fecha"])
            )
            if suyo:
                temas.extend(x["titulo"] for x in f["temas"] if x["titulo"] not in temas)
        if temas:
            p["faltan_temas"] = temas
    return productos
