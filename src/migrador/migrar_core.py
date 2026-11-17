"""
Orquestador del migrador de catálogos.

Une las piezas en el flujo de 4 pasos de la app:

  1. relevar(url)                 → catálogo crudo desde YouTube  (relevar_core)
  2. group_products(tracks)       → catálogo dividido en productos (productos)
     filter_products(...)         → selección manual / por fecha / por distribuidora
  3. preparar(seleccion, opciones)→ baja planilla / audios / portadas
  4. build_zip(...)               → carpeta organizada, lista para entregar

Los pasos 1 y 2 no necesitan ninguna credencial del usuario: funcionan para
cualquiera. El audio en calidad de entrega necesita que el usuario conecte su
propia cuenta de Tidal (ver `audio.TidalSession`); sin eso, la app igual entrega
planilla, portadas y audio de referencia claramente etiquetado.
"""

import os
import shutil
import tempfile

from . import audio as audio_mod
from . import completitud as completitud_mod
from . import paquete
from . import portadas as portadas_mod
from . import productos as productos_mod
from . import relevar_core
from .contratos import Diagnostico, OpcionesFiltro, Producto, ResultadoMigracion, Track
from .i18n import T


# ============================================================
# Paso 1 + 2, relevar y agrupar
# ============================================================


def relevar_catalogo(
    url, yt_key, with_codes=True, progress=None, use_musicbrainz=False, fraccion=None, reusar=True
) -> tuple[list[Producto], str, list[Track], Diagnostico]:
    """Releva el catálogo y lo devuelve ya agrupado en productos.

    Devuelve (productos, artista, tracks_planos, diagnostico_del_canal).
    `reusar=False` vuelve a listar el canal aunque ya se haya listado en esta
    sesión (ver `relevar_core._Listados`).
    """
    log = progress or (lambda *_: None)
    # relevar_core.relevar() devuelve un DICT, no una tupla: desempaquetarlo como
    # tupla toma sus claves y tira "too many values to unpack".
    res = relevar_core.relevar(
        url,
        yt_key,
        with_codes=with_codes,
        progress=progress,
        use_musicbrainz=use_musicbrainz,
        fraccion=fraccion,
        reusar=reusar,
    )
    tracks = res["tracks"]
    artista = res["artist"]

    # Qué tiene Deezer de este artista que no apareció en YouTube. Sólo si se
    # cruzaron códigos, porque es de ese cruce de donde sale qué artista de
    # Deezer es. No cuesta cuota de YouTube.
    comp = completitud_mod.completitud_vacia()
    if res.get("codes") is not None:
        if progress:
            progress(T("mig.comparando_deezer"), 0.96)
        comp = completitud_mod.revisar(
            tracks,
            res["cruce"],
            artista,
            avance=(lambda h, t: fraccion(0.96 + 0.03 * h / t)) if fraccion else None,
        )

    # Lo que falta y se puede sumar entra al catálogo con los datos de Deezer:
    # adentro de su disco, o como un release aparte que queda sin elegir.
    tracks = tracks + completitud_mod.sumar_de_deezer(tracks, comp, res["cruce"])
    prods = productos_mod.group_products(tracks, artist=artista)
    completitud_mod.marcar(prods, comp, res["cruce"])
    log(T("mig.agrupados", productos=len(prods), tracks=len(tracks)))

    # Diagnóstico del canal: si no trae descripciones auto-generadas, el
    # catálogo sale sin álbumes ni códigos y hay que avisarlo.
    diag: Diagnostico = {
        "es_topic": res.get("es_topic", True),
        "canal": res.get("channel_title", ""),
        # Si el usuario pegó un OAC, se relevó el Topic en su lugar: hay que
        # decírselo, no cambiar de canal en silencio.
        "via_topic": bool(res.get("via_topic")),
        "canal_pedido": res.get("canal_pedido", ""),
        "descartados": int(res.get("descartados") or 0),
        "codigos": {
            "pedidos": res.get("codes") is not None,
            "encontrados": int((res.get("codes") or {}).get("matched") or 0),
            "fallas": int((res.get("codes") or {}).get("fallas") or 0),
        },
        "via": res.get("via", "subidas"),
        "total_estimado": int(res.get("total_estimado") or 0),
        "cortado_por_cuota": bool(res.get("cortado_por_cuota")),
        "unidades": int(res.get("unidades") or 0),
        "reusado": bool(res.get("reusado")),
        "sin_distribuidora": int(res.get("sin_distribuidora") or 0),
        # Los que se vieron en YouTube, sin los que se sumaron de Deezer.
        "temas": len(res["tracks"]),
        "completitud": comp,
    }
    if diag["via_topic"]:
        log(T("mig.via_topic", pedido=diag["canal_pedido"], topic=diag["canal"]))
    if diag["descartados"]:
        log(T("mig.descartados", n=diag["descartados"]))
    if diag["cortado_por_cuota"]:
        log(T("mig.cortado_por_cuota", n=diag["temas"]))
    if comp["revisada"] and comp["temas"]:
        log(T("mig.faltan_en_youtube", n=comp["temas"], releases=len(comp["faltan"])))
    return prods, artista, tracks, diag


def opciones_de_filtro(prods) -> OpcionesFiltro:
    """Todo lo que la UI necesita para armar los filtros del paso 2."""
    desde, hasta = productos_mod.year_range(prods)
    return {
        "distribuidoras": productos_mod.distributor_options(prods),
        "año_min": desde,
        "año_max": hasta,
        "total": len(prods),
    }


# ============================================================
# Paso 3, preparar el contenido pedido
# ============================================================


def preparar(
    seleccion: list[Producto],
    artista,
    quiere_planilla=True,
    quiere_audio=False,
    quiere_portadas=True,
    tidal_session=None,
    usar_referencia=True,
    calidad="LOSSLESS",
    log=print,
    avance_portadas=None,
    avance_audio=None,
    dir_audio=None,
):
    """Baja lo que se pidió para los productos seleccionados.

    Muta los productos agregándoles `cover_bytes` y, a cada track, `audio_path`
    + `audio_label`. Devuelve (seleccion, dir_temporal_audio, entorno).

    `avance_portadas(i, total)` se pasa tal cual a `fetch_portadas`: es de donde
    sale la barra de progreso de la parte que más tarda.
    """
    entorno = audio_mod.verificar_entorno()
    # Si quien llama da la carpeta del audio, es suya y la limpia él aunque esto
    # se corte a la mitad (ver `server.api_preparar`).

    if quiere_portadas:
        portadas_mod.fetch_portadas(seleccion, artista, log=log, avance=avance_portadas)

    if quiere_audio:
        con_tidal = bool(tidal_session and tidal_session.conectada)
        if con_tidal:
            if not entorno["puede_flac"]:
                log(T("mig.falta_ffmpeg"))
            else:
                indice, _ = audio_mod.construir_indice_isrc(tidal_session, artista, log=log)
                audio_mod.matchear_por_isrc(seleccion, indice, log=log)
        else:
            log(T("mig.sin_tidal"))

        if not entorno["puede_referencia"] and not con_tidal:
            log(T("mig.sin_referencia"))
        else:
            _, dir_audio = audio_mod.fetch_audio(
                seleccion,
                session=tidal_session if con_tidal else None,
                usar_referencia=usar_referencia,
                calidad=calidad,
                log=log,
                avance=avance_audio,
                dest_dir=dir_audio,
            )

    return seleccion, dir_audio, entorno


# ============================================================
# Paso 4, empaquetar
# ============================================================


def empaquetar(
    seleccion: list[Producto],
    artista,
    out_path=None,
    entorno=None,
    con_tidal=False,
    incluir_planilla=True,
    incluir_audio=True,
    incluir_portadas=True,
    log=print,
    avance=None,
    diag=None,
):
    """Arma el ZIP del entregable. Devuelve (ruta, tamaño_bytes).

    `diag` es el diagnóstico que devolvió `relevar_catalogo`: con él, el reporte
    del paquete dice cómo se listó el catálogo y qué le falta."""
    if out_path is None:
        out_path = os.path.join(
            tempfile.mkdtemp(prefix="migrador_zip_"),
            f"{relevar_core.slugify(artista)}-{T('paq.f_zip_sufijo')}.zip",
        )
    return paquete.build_zip(
        seleccion,
        artista,
        out_path,
        entorno=entorno,
        con_tidal=con_tidal,
        incluir_planilla=incluir_planilla,
        incluir_audio=incluir_audio,
        incluir_portadas=incluir_portadas,
        log=log,
        avance=avance,
        diag=diag,
    )


def limpiar(dir_audio):
    """Borra los audios temporales. Llamar después de servir el ZIP."""
    if dir_audio:
        shutil.rmtree(dir_audio, ignore_errors=True)


# ============================================================
# Flujo completo (para uso desde script / CLI)
# ============================================================


def migrar(
    url,
    yt_key,
    ids=None,
    year_from=None,
    year_to=None,
    distributors=None,
    quiere_planilla=True,
    quiere_audio=False,
    quiere_portadas=True,
    tidal_session=None,
    out_path=None,
    log=print,
) -> ResultadoMigracion:
    """Corre los 4 pasos de una. Devuelve dict con el resultado."""
    prods, artista, _, diag = relevar_catalogo(url, yt_key, progress=log)
    seleccion = productos_mod.filter_products(
        prods,
        ids=ids,
        year_from=year_from,
        year_to=year_to,
        distributors=distributors,
    )
    if not seleccion:
        raise relevar_core.RelevarError(T("mig.seleccion_vacia"))
    log(T("mig.seleccionados", n=len(seleccion), total=len(prods)))

    seleccion, dir_audio, entorno = preparar(
        seleccion,
        artista,
        quiere_planilla=quiere_planilla,
        quiere_audio=quiere_audio,
        quiere_portadas=quiere_portadas,
        tidal_session=tidal_session,
        log=log,
    )
    con_tidal = bool(tidal_session and tidal_session.conectada)
    ruta, tam = empaquetar(
        seleccion,
        artista,
        out_path=out_path,
        entorno=entorno,
        con_tidal=con_tidal,
        incluir_planilla=quiere_planilla,
        incluir_audio=quiere_audio,
        incluir_portadas=quiere_portadas,
        log=log,
        diag=diag,
    )
    limpiar(dir_audio)
    return {
        "artista": artista,
        "zip": ruta,
        "bytes": tam,
        "productos": len(seleccion),
        "resumen": productos_mod.summarize(seleccion),
    }
