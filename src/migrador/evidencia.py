"""
Qué tan comprobado está cada código, dicho con una sola palabra.

Por qué existe. Un ISRC llega a un tema por caminos muy distintos, y hasta acá
todos se veían igual: doce caracteres en una celda. El que salió de buscar
«título artista» en Deezer y quedarse con el resultado más parecido valía lo
mismo, a la vista, que el que además figura con ese mismo código en el
tracklist del release verificado. `match` decía «alta» para los dos. Quien
entrega esos códigos a una distribuidora los entrega todos con la misma
confianza, y no la merecen por igual.

Acá no se busca nada ni se cambia ningún código: se mira lo que el relevamiento
ya sabe y se lo dice. Tres niveles salen del relevamiento, y dos más de lo que
hace el usuario (ver `ediciones`):

    confirmado   Dos caminos independientes dan el mismo código. El ISRC que
                 encontró la búsqueda por texto es el que lleva ese tema en el
                 tracklist del álbum de Deezer verificado como su release; o el
                 tema es de Deezer y el código es el suyo.
    inferido     Un solo camino: la búsqueda por texto, o el título y la
                 duración en la discografía. Es el mejor candidato y casi
                 siempre es el bueno, pero nada más lo respalda.
    dudoso       La coincidencia fue parecida y no idéntica (`match` «media»).
    manual       Lo escribió el usuario.
    importado    Salió del archivo que le dio su distribuidora.

El UPC tiene los mismos niveles, por producto. Está confirmado cuando el álbum
de Deezer se comprobó como el release por el título y la fecha, o por la lista
exacta de temas; inferido cuando sólo por el título, o por alguna de las formas
más flojas de `completitud.verificar_por_tracklist`.

La idea de separar el identificador de la confianza con que se lo obtuvo viene
de los etiquetadores (beets recomienda un match «strong» sin preguntar y pide
confirmación para uno «medium»): lo que se toma de ahí es el criterio, no el
código.

Este módulo no importa nada que toque la red.
"""

from collections import Counter
from typing import Any

from .contratos import CruceDeezer, Producto, ResumenEvidencia, Track

CONFIRMADO, INFERIDO, DUDOSO = "confirmado", "inferido", "dudoso"
MANUAL, IMPORTADO = "manual", "importado"

# Las formas de verificar un release que no dependen sólo de cómo se llama: el
# título con la fecha, la lista exacta de temas, o el release propio de la
# fuente (el álbum de Deezer que se sumó entero, el de Tidal).
_UPC_FIRMES = ("fecha", "exacto", "deezer", "tidal")
# Los niveles que no salen del relevamiento sino de una decisión del usuario:
# volver a clasificar no los pisa.
_DEL_USUARIO = (MANUAL, IMPORTADO)


def _en_su_release(t: Track, tracklists: dict[int, list[Any]]) -> bool:
    """Si el tema figura con su mismo ISRC en el tracklist de su release."""
    temas = tracklists.get(t.get("album_deezer_id") or 0) or []
    return any(x.get("isrc") and x["isrc"] == t["isrc"] for x in temas)


def nivel_isrc(t: Track, tracklists: dict[int, list[Any]]) -> str:
    """El nivel del ISRC de un tema, o "" si no tiene."""
    if not t.get("isrc"):
        return ""
    if t.get("isrc_nivel") in _DEL_USUARIO:
        return t.get("isrc_nivel") or ""
    como = t.get("isrc_como") or ""
    # El archivo de la distribuidora trae el mismo código (ver `importar`): es
    # la segunda fuente más fuerte que puede haber, la de quien lo entregó.
    if como in ("deezer", "tidal") or t.get("isrc_respaldo"):
        return CONFIRMADO
    if _en_su_release(t, tracklists):
        return CONFIRMADO
    return DUDOSO if t.get("match") == "media" else INFERIDO


def clasificar(tracks: list[Track], cruce: CruceDeezer | None = None) -> None:
    """Le anota a cada tema el nivel de su ISRC (`isrc_nivel`).

    Va antes de agrupar en productos: mira el álbum de Deezer en que quedó
    ubicado cada tema, que es un dato del tema y no depende de que el producto
    entero haya quedado con el orden confirmado.

    Un tema que se sumó a un disco desde Deezer hereda el UPC del disco; se le
    anota de dónde salió (`upc_como`) para que el producto no quede a medias.
    """
    tracklists = (cruce or {}).get("discografia") or {}
    for t in tracks:
        nivel = nivel_isrc(t, tracklists)
        if nivel:
            t["isrc_nivel"] = nivel
            if not t.get("isrc_como"):
                t["isrc_como"] = "busqueda"
        else:
            t.pop("isrc_nivel", None)
        if t.get("upc") and not t.get("upc_como") and t.get("origen") == "deezer":
            t["upc_como"] = "deezer"


# Cuántos temas tienen que coincidir, cada uno con el ISRC que encontró la
# búsqueda, para dar por comprobado un release del que sólo coincide el título.
MIN_TEMAS_PARA_CONFIRMAR = 2


def nivel_upc(p: Producto, tracklists: dict[int, list[Any]] | None = None) -> str:
    """El nivel del UPC de un producto, o "" si no tiene.

    Confirmado, si el álbum de Deezer se comprobó como este release por algo
    más que su título:

      - el título y la fecha, o la lista exacta de temas (`_UPC_FIRMES`);
      - o todos los temas que el producto tiene en YouTube están en ese mismo
        álbum, y dos o más con el ISRC que la búsqueda había encontrado por su
        cuenta. Un single y el álbum del que salió se llaman distinto; dos
        ediciones que se llaman igual casi nunca comparten los códigos de todas
        sus grabaciones.

    Inferido, lo demás: un release de un solo tema del que no coincide la
    fecha, o uno que se aceptó por una de las formas flojas.
    """
    upc = p.get("upc") or ""
    if not upc:
        return ""
    if p.get("upc_nivel") in _DEL_USUARIO:
        return p.get("upc_nivel") or ""
    if p.get("upc_respaldo"):
        return CONFIRMADO
    tracks = p.get("tracks", [])
    de_youtube = [t for t in tracks if t.get("origen") != "deezer"]
    if not de_youtube:
        # El release entero salió de Deezer: el UPC es el de ese álbum.
        return CONFIRMADO
    comos = {t.get("upc_como") or "" for t in de_youtube if t.get("upc") == upc}
    if comos & set(_UPC_FIRMES):
        return CONFIRMADO
    albumes = {t.get("album_deezer_id") for t in de_youtube}
    if len(albumes) == 1 and None not in albumes and all(t.get("upc") == upc for t in de_youtube):
        independientes = [
            t
            for t in de_youtube
            if t.get("isrc") and t.get("isrc_como") == "busqueda" and _en_su_release(t, tracklists or {})
        ]
        if len(independientes) >= MIN_TEMAS_PARA_CONFIRMAR:
            return CONFIRMADO
    return INFERIDO


def marcar_productos(productos: list[Producto], cruce: CruceDeezer | None = None) -> list[Producto]:
    """Le anota a cada producto el nivel de su UPC (`upc_nivel`) y cuántos de
    sus ISRC no están confirmados (`isrc_sin_confirmar`)."""
    tracklists = (cruce or {}).get("discografia") or {}
    for p in productos:
        nivel = nivel_upc(p, tracklists)
        if nivel:
            p["upc_nivel"] = nivel
        else:
            p.pop("upc_nivel", None)
        contar_sin_confirmar(p)
    return productos


def contar_sin_confirmar(p: Producto) -> int:
    """Vuelve a contar los ISRC inferidos o dudosos de un producto.

    Es lo único que hay que rehacer cuando el usuario cambia un código (ver
    `ediciones`). El nivel del UPC no se recalcula ahí: depende de los
    tracklists de Deezer, que después del relevamiento ya no están a la vista,
    y recalcularlo sin ellos bajaría a «inferido» un UPC que estaba confirmado.
    """
    p["isrc_sin_confirmar"] = sum(1 for t in p.get("tracks", []) if t.get("isrc_nivel") in (INFERIDO, DUDOSO))
    return p["isrc_sin_confirmar"]


def resumen(productos: list[Producto]) -> ResumenEvidencia:
    """Cuántos códigos hay de cada nivel, para decirlo arriba de la tabla."""
    isrc: Counter[str] = Counter()
    upc: Counter[str] = Counter()
    for p in productos:
        if p.get("upc_nivel"):
            upc[p.get("upc_nivel") or ""] += 1
        for t in p.get("tracks", []):
            if t.get("isrc_nivel"):
                isrc[t.get("isrc_nivel") or ""] += 1
    return {"isrc": dict(isrc), "upc": dict(upc)}
