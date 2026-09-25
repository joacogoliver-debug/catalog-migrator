"""
Agrupación del catálogo relevado en *productos* (álbum / EP / single) y filtros
de selección para la migración.

El relevamiento de `relevar_core` devuelve una lista plana de tracks (uno por
video de YouTube). Para migrar un catálogo no se entrega track por track: se
entrega **producto por producto**, porque así lo recibe la distribuidora nueva
(un UPC, una portada, un conjunto de audios). Este módulo hace esa traducción.

Limitación conocida y deliberada: YouTube no expone el número de track dentro
del álbum. El orden que armamos acá es una *aproximación* por fecha de subida
(los álbumes suelen subirse en orden). El campo `track_number` queda en None
hasta que lo complete el enriquecimiento por Deezer, y el reporte de migración
avisa cuando un producto quedó sin orden confirmado.
"""

import re
from collections import Counter

from .contratos import OpcionDistribuidora, Producto, ResumenSeleccion, TipoProducto, Track
from .texto import comparable as _norm
from .texto import nombre_seguro

# Los dos centinelas que pone `relevar_core` cuando la descripcion de YouTube no
# trae el dato. NO son texto para mostrar y por eso no se traducen: el filtrado y
# la agrupacion los comparan por igualdad, y traducirlos romperia las dos cosas
# en silencio. Viven aca, que es donde se consumen, y `relevar_core` los importa
# en vez de repetir la cadena: escritos dos veces, cambiar uno rompe el otro sin
# que nada avise.
SIN_ALBUM = "(single / sin álbum)"
SIN_DATOS = "(sin datos)"

# Umbrales de formato, siguiendo la convención que usan las distribuidoras:
# 1-3 tracks = single, 4-6 = EP, 7+ = álbum.
#
# Es una heurística por cantidad de tracks, no un dato del release: YouTube no
# declara el formato. Un release de 3 tracks puede ser un EP y quedar acá como
# single. Por eso el tipo se muestra como orientativo y conviene verificarlo
# antes de la entrega; el reporte lo aclara.
MAX_TRACKS_SINGLE = 3
MAX_TRACKS_EP = 6


def _kind(n_tracks) -> TipoProducto:
    if n_tracks <= MAX_TRACKS_SINGLE:
        return "single"
    if n_tracks <= MAX_TRACKS_EP:
        return "ep"
    return "album"


def _mode(values):
    """Valor no vacío más frecuente (para consolidar sello/distribuidora/UPC
    cuando los tracks de un mismo álbum traen datos despareros)."""
    vals = [v for v in values if v not in (None, "", SIN_DATOS)]
    if not vals:
        return ""
    return Counter(vals).most_common(1)[0][0]


def _slug(s, maxlen=60):
    """Nombre de carpeta seguro, de hasta sesenta caracteres.

    El largo solo no alcanza para no pasarse de los 260 de Windows, porque la
    ruta suma la carpeta raíz y el nombre de cada archivo: el presupuesto total
    lo maneja `paquete.LARGO_MAX_RUTA`, que recorta el título del archivo."""
    return nombre_seguro(s, maxlen, "Sin titulo")


# ============================================================
# Agrupación
# ============================================================


def _agrupar_por_release(tracks):
    """Los grupos de tracks que forman cada release, antes de armar el producto.

    Un release se identifica por su álbum, su distribuidora y su fecha de
    lanzamiento, que YouTube publica en cada tema («Released on:»). Antes se
    agrupaba por álbum y año ℗, y ese año es de cada GRABACIÓN, no del release:
    la edición aniversario de un disco, con temas originales de ℗ 2013 y otros
    nuevos de ℗ 2023, salía partida en dos productos, cada uno con el mismo UPC.

    La distribuidora va en la clave porque el mismo álbum entregado por dos
    distribuidoras (en plena migración, o después de una baja que no se hizo)
    son dos releases en vivo: fundirlos daba un álbum con los tracks duplicados.

    Los tracks sin fecha se suman al release con fecha de su mismo álbum si hay
    uno solo. Si no, se agrupan por año ℗ como antes, juntando años seguidos,
    porque un disco de 1996 con un tema de ℗ 1997 es el mismo disco, y una
    reedición casi nunca sale al año siguiente. Años más separados siguen siendo
    releases distintos, que es lo que evita fusionar un álbum con su reedición.

    Después, los grupos sin fecha cuyos temas Deezer ubicó en el MISMO tracklist
    verificado se juntan: dos temas de ℗ 2001 y ℗ 2021 que en Deezer son los
    tracks 1 y 2 del mismo disco son un disco. Esa señal sólo junta, nunca
    separa: que un tema no se haya podido ubicar no dice que sea de otro release.
    """
    grupos = {}
    for t in tracks:
        album = (t.get("album") or "").strip()
        if not album or album == SIN_ALBUM:
            # Single: clave única por video, nunca se fusiona con otro.
            grupos[("__single__", t.get("video_id") or str(id(t)), "")] = [t]
            continue
        clave = (_norm(album), t.get("distributor") or "", t.get("release_date") or "")
        grupos.setdefault(clave, []).append(t)

    for album, dist, fecha in [k for k in grupos if k[0] != "__single__" and not k[2]]:
        sin_fecha = grupos.pop((album, dist, fecha))
        con_fecha = [k for k in grupos if k[0] == album and k[1] == dist and k[2]]
        if len(con_fecha) == 1:
            grupos[con_fecha[0]].extend(sin_fecha)
            continue
        for n, bloque in enumerate(_unir_por_tracklist(_por_anios_seguidos(sin_fecha))):
            grupos[(album, dist, f"sin-fecha-{n}")] = bloque
    return list(grupos.values())


def _por_anios_seguidos(tracks):
    """Parte tracks sin fecha por año ℗, juntando los años consecutivos."""
    por_anio = {}
    for t in tracks:
        por_anio.setdefault(str(t.get("release_year") or ""), []).append(t)
    bloques, anterior = [], None
    for anio in sorted(por_anio):
        seguido = (
            anterior is not None and anio.isdigit() and anterior.isdigit() and int(anio) - int(anterior) <= 1
        )
        if seguido:
            bloques[-1].extend(por_anio[anio])
        else:
            bloques.append(list(por_anio[anio]))
        anterior = anio
    return bloques


def _unir_por_tracklist(bloques):
    """Junta los bloques que tienen temas ubicados en el mismo álbum de Deezer."""
    unidos = []  # [ids de álbum, tracks]
    for bloque in bloques:
        ids = {t.get("album_deezer_id") for t in bloque} - {None}
        destino = next((u for u in unidos if u[0] & ids), None)
        if destino:
            destino[0] |= ids
            destino[1].extend(bloque)
        else:
            unidos.append([set(ids), list(bloque)])
    return [tracks for _ids, tracks in unidos]


def _marcar_duplicados_entre_distribuidoras(productos):
    """Anota en cada producto las otras distribuidoras que tienen el mismo release.

    Es la señal más útil de una migración a medio hacer: el mismo disco en vivo
    dos veces. Se anota en el producto, y no se calcula en la validación sobre
    la selección, para que el aviso salga aunque se haya elegido uno solo.
    """
    por_release = {}
    for p in productos:
        if len(p["tracks"]) and (p["tracks"][0].get("album") or SIN_ALBUM) != SIN_ALBUM:
            clave = (_norm(p["title"]), p["release_date"] or str(p["release_year"] or ""))
            por_release.setdefault(clave, []).append(p)
    for mismos in por_release.values():
        distribuidoras = {p["distributor"] for p in mismos if p["distributor"]}
        if len(distribuidoras) > 1:
            for p in mismos:
                p["tambien_en"] = sorted(distribuidoras - {p["distributor"]})


def group_products(tracks: list[Track], artist="") -> list[Producto]:
    """Agrupa una lista de tracks en productos (ver `_agrupar_por_release`).

    Los tracks que vienen sin álbum quedan como singles independientes.
    """

    productos = []
    for ts in _agrupar_por_release(tracks):
        # El orden real sólo vale si está para TODOS los tracks del release:
        # mezclar números reales con estimados daría repetidos, y un orden a
        # medias parecería confirmado.
        confirmado = all(t.get("orden_fuente") for t in ts)
        if confirmado:
            ts = sorted(ts, key=lambda x: (x.get("disc_number") or 1, x.get("track_number") or 0))
        else:
            ts = sorted(ts, key=lambda x: (x.get("upload_date") or "", x.get("track") or ""))
        es_single = (ts[0].get("album") or SIN_ALBUM) == SIN_ALBUM
        titulo = ts[0].get("track", "") if es_single else (ts[0].get("album") or "").strip()

        años = [t.get("release_year") for t in ts if t.get("release_year")]
        lanzamientos = [t.get("release_date") for t in ts if t.get("release_date")]
        subidas = [t.get("upload_date") for t in ts if t.get("upload_date")]

        if not confirmado:
            for i, t in enumerate(ts, 1):
                # Orden provisorio por fecha de subida; se marca como no confirmado.
                # El disco de los que sí se ubicaron se descarta también: un
                # release con unos temas en el disco 1 y otros sin disco no es
                # un dato, es una mezcla.
                t["track_number"] = i
                t.pop("disc_number", None)

        productos.append(
            {
                "product_id": f"p{len(productos) + 1:03d}",
                "title": titulo,
                "kind": _kind(len(ts)),
                "artist": artist or "",
                # El año del release es el de su lanzamiento, cuando se sabe.
                # El año ℗ es de cada grabación: una edición aniversario de 2023
                # trae temas de ℗ 2013, y salía fechada en 2013.
                "release_year": int(min(lanzamientos)[:4]) if lanzamientos else (min(años) if años else ""),
                "release_date": min(lanzamientos) if lanzamientos else "",
                "upload_date": min(subidas) if subidas else "",
                "label": _mode(t.get("label") for t in ts),
                "p_line": _mode(t.get("p_line") for t in ts),
                "distributor": _mode(t.get("distributor") for t in ts),
                "upc": _mode(t.get("upc") for t in ts),
                "tracks": ts,
                "track_count": len(ts),
                "total_views": sum(int(t.get("views") or 0) for t in ts),
                # True cuando el orden salió sólo de la fecha de subida (sin confirmar).
                "order_unconfirmed": len(ts) > 1 and not confirmado,
            }
        )

    _marcar_duplicados_entre_distribuidoras(productos)

    # Más nuevo primero: es el orden en que la gente revisa su catálogo.
    productos.sort(
        key=lambda p: (str(p["release_year"] or ""), p["release_date"] or p["upload_date"] or ""),
        reverse=True,
    )
    for i, p in enumerate(productos, 1):
        p["product_id"] = f"p{i:03d}"
    asignar_carpetas(productos)
    return productos


def folder_name(p):
    """Nombre de carpeta del producto dentro del ZIP: '2019 - Album [UPC]'.

    Del UPC entran sólo los dígitos. Viene de Deezer o de Tidal y se pegaba
    crudo: un UPC `../../evil` sacaba la carpeta de la raíz del ZIP, y un
    descompresor que no sanea escribía afuera.
    """
    año = p.get("release_year") or "s-f"  # s-f = sin fecha
    base = f"{año} - {_slug(p.get('title'))}"
    upc = re.sub(r"\D", "", p.get("upc") or "")
    return f"{base} [{upc}]" if upc else base


def asignar_carpetas(productos):
    """Le pone a cada producto una carpeta que no repite la de otro.

    Dos productos podían quedar con el mismo nombre: dos singles «Intro» del
    mismo año sin UPC, dos títulos que difieren recién después del carácter
    sesenta, o títulos en una escritura no latina, que al pasar a ASCII quedan
    todos en «Sin titulo». Adentro del ZIP eran dos entradas con el mismo
    nombre, y al descomprimir la portada y la planilla de uno pisaban las del
    otro. Se compara sin mayúsculas porque Windows no las distingue.
    """
    usados = set()
    for p in productos:
        base = folder_name(p)
        nombre, n = base, 2
        while nombre.casefold() in usados:
            nombre, n = f"{base} ({n})", n + 1
        usados.add(nombre.casefold())
        p["folder"] = nombre
    return productos


# ============================================================
# Filtros de selección
# ============================================================


def filter_products(
    productos: list[Producto],
    ids=None,
    year_from=None,
    year_to=None,
    date_from=None,
    date_to=None,
    distributors=None,
) -> list[Producto]:
    """Filtra productos para la migración. Los filtros se combinan con AND.

    - ids:          selección manual por product_id (lista o set)
    - year_from/to: rango por año de lanzamiento (℗), inclusive
    - date_from/to: rango por fecha de subida a YouTube 'YYYY-MM-DD', inclusive
    - distributors: nombres de distribuidora (match parcial, sin acentos)

    Un producto sin año declarado queda fuera si se filtra por año: preferimos
    excluirlo antes que colarlo en una selección donde no sabemos si entra.
    """
    sel = productos

    if ids is not None:
        ids = set(ids)
        sel = [p for p in sel if p["product_id"] in ids]

    if year_from is not None:
        sel = [p for p in sel if p["release_year"] and int(p["release_year"]) >= int(year_from)]
    if year_to is not None:
        sel = [p for p in sel if p["release_year"] and int(p["release_year"]) <= int(year_to)]

    if date_from is not None:
        sel = [p for p in sel if p["upload_date"] and p["upload_date"] >= date_from]
    if date_to is not None:
        sel = [p for p in sel if p["upload_date"] and p["upload_date"] <= date_to]

    if distributors:
        buscados = [_norm(d) for d in distributors if _norm(d)]
        sel = [p for p in sel if any(b in _norm(p["distributor"]) for b in buscados)]

    return sel


def distributor_options(productos) -> list[OpcionDistribuidora]:
    """Distribuidoras presentes, con su conteo, para armar el filtro en la UI."""
    c = Counter(p["distributor"] for p in productos if p.get("distributor"))
    return [{"name": n, "count": k} for n, k in c.most_common()]


def year_range(productos):
    """(mín, máx) de años presentes, o (None, None), para el slider de fechas."""
    años = sorted({int(p["release_year"]) for p in productos if p.get("release_year")})
    return (años[0], años[-1]) if años else (None, None)


def summarize(productos: list[Producto]) -> ResumenSeleccion:
    """Resumen de una selección, para mostrar antes de descargar."""
    return {
        "products": len(productos),
        "tracks": sum(p["track_count"] for p in productos),
        "albums": sum(1 for p in productos if p["kind"] == "album"),
        "eps": sum(1 for p in productos if p["kind"] == "ep"),
        "singles": sum(1 for p in productos if p["kind"] == "single"),
        "with_upc": sum(1 for p in productos if p.get("upc")),
        "with_isrc": sum(1 for p in productos for t in p["tracks"] if t.get("isrc")),
        "views": sum(p["total_views"] for p in productos),
    }
