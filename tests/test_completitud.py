# -*- coding: utf-8 -*-
"""Qué le falta al catálogo, según la discografía de Deezer. Sin red.

Por qué existe. El buscador de YouTube, que desde fines de 2026 es la única
forma de listar un canal Topic, no garantiza traer todo y no avisa cuando no lo
trae. En el catálogo real con que se probó, Deezer tenía 26 grabaciones que no
habían aparecido: temas sueltos de discos relevados, dos discos casi enteros y
tres singles. Sin comparar contra algo, eso no se veía en ningún lado.

Lo que se fija acá:

  - el artista de Deezer sale de los álbumes verificados, no de su nombre
  - una grabación está si coincide su ISRC, o su título y su duración
  - dos ediciones del mismo disco no cuentan dos veces la misma falta
  - el disco relevado al que le faltan temas queda marcado en su producto
  - si Deezer no contesta, la revisión queda sin hacer y se dice
"""

from typing import Any

import pytest

from migrador import completitud as C
from migrador import productos as P
from migrador import relevar_core as R
from migrador.contratos import Completitud, CruceDeezer, ReleaseIncompleto, TemaFaltante, Track

ARTISTA = 4209085


def tema(titulo, isrc="", dur=200):
    return {"title": titulo, "isrc": isrc, "duration": dur}


class FalsoDeezer:
    """Doble de `relevar_core._deezer_json`: la discografía de un artista."""

    def __init__(self, discos, de_otros=None):
        # discos: {id: (título, tipo, fecha, [temas])}
        self.discos = discos
        self.de_otros = de_otros or {}
        self.caidos = set()
        self.pedidos = []
        self.titulares = {}  # id de álbum -> a nombre de quién figura, si no es el del canal

    def __call__(self, ruta):
        self.pedidos.append(ruta)
        if ruta.startswith("artist/"):
            aid = int(ruta.split("/")[1])
            ids = self.discos if aid == ARTISTA else self.de_otros.get(aid, {})
            data = [
                {"id": i, "title": d[0], "record_type": d[1], "release_date": d[2]}
                for i, d in ids.items()
                if i in self.discos
            ]
            return {"data": data}
        partes = ruta.split("?")[0].split("/")
        aid = int(partes[1])
        if aid in self.caidos:
            return None
        if len(partes) == 3 and partes[2] == "tracks":
            # Como contesta Deezer: cada tema con su posición, su disco y su
            # artista. Lo que el test no diga se completa en orden.
            return {
                "data": [
                    {
                        "id": aid * 100 + n,
                        "track_position": n,
                        "disk_number": 1,
                        "artist": {"name": self.titulares.get(aid, "Los del Ejemplo")},
                        **t,
                    }
                    for n, t in enumerate(self.discos[aid][3], 1)
                ]
            }
        return {
            "id": aid,
            "upc": f"UPC{aid}",
            "title": self.discos[aid][0],
            "label": "Sello de Deezer",
            "release_date": self.discos[aid][2],
            "artist": {"id": 1, "name": self.titulares.get(aid, "Los del Ejemplo")},
        }


def track(hacer_track, titulo, album, isrc="", dur=200, aid=None, fecha="2020-01-01"):
    t = hacer_track(titulo, album, 2020, isrc=isrc, dur=dur, released=fecha, vid=f"v-{titulo}-{album}")
    if aid:
        t["album_deezer_id"] = aid
    return t


def cruce(*verificados, artista="Los del Ejemplo", otros=None) -> CruceDeezer:
    albumes = {
        aid: {"artist_id": ARTISTA, "artist_name": artista, "upc": f"UPC{aid}", "title": f"Disco {aid}"}
        for aid in verificados
    }
    albumes.update(otros or {})
    return {"albumes": albumes, "verificados": {aid: [] for aid in verificados}}


@pytest.fixture
def deezer(monkeypatch):
    def poner(discos, **k):
        falso = FalsoDeezer(discos, **k)
        monkeypatch.setattr(R, "_deezer_json", falso)
        return falso

    return poner


# ============================================================
# De quién es la discografía
# ============================================================


def test_el_artista_sale_de_los_albumes_verificados(hacer_track):
    tracks = [track(hacer_track, f"T{i}", "Disco", aid=10) for i in range(5)]
    assert C.artistas_en_deezer(tracks, cruce(10, artista="Los Del Ejemplo"), "Los del Ejemplo") == [
        (ARTISTA, "Los Del Ejemplo")
    ]


def test_el_artista_de_un_compilado_no_cuenta(hacer_track):
    """Un compilado verificado tiene de artista al sello: no es el del canal,
    aunque sea el que más temas trajo."""
    tracks = [track(hacer_track, f"C{i}", "Compilado", aid=20) for i in range(9)]
    tracks += [track(hacer_track, "T", "Disco", aid=10)]
    otros = {20: {"artist_id": 777, "artist_name": "Leader Music"}}
    assert C.artistas_en_deezer(tracks, cruce(10, otros=otros), "Los del Ejemplo") == [
        (ARTISTA, "Los del Ejemplo")
    ]


def test_sin_ningun_album_verificado_no_se_adivina_por_nombre(hacer_track, deezer):
    falso = deezer({})
    tracks = [track(hacer_track, "T", "Disco", isrc="AR0000000001")]
    res = C.revisar(tracks, cruce(), "Los del Ejemplo")
    assert res["revisada"] is False and res["faltan"] == []
    assert falso.pedidos == [], "sin saber quién es, no se le pregunta nada a Deezer"


# ============================================================
# Qué falta
# ============================================================


def test_un_disco_relevado_al_que_le_falta_un_tema(hacer_track, deezer):
    deezer(
        {10: ("Disco", "album", "2020-01-01", [tema("Uno", "AR1"), tema("Dos", "AR2"), tema("Tres", "AR3")])}
    )
    tracks = [
        track(hacer_track, "Uno", "Disco", isrc="AR1", aid=10),
        track(hacer_track, "Dos", "Disco", isrc="AR2", aid=10),
    ]
    res = C.revisar(tracks, cruce(10), "Los del Ejemplo")

    assert set(res) == set(Completitud.__annotations__)
    assert res["revisada"] is True and res["artista_deezer"] == "Los del Ejemplo"
    assert (res["releases"], res["temas"]) == (1, 1)
    (f,) = res["faltan"]
    assert set(f) == set(ReleaseIncompleto.__annotations__)
    assert (f["titulo"], f["relevado"], f["total"], f["upc"]) == ("Disco", True, 3, "UPC10")
    assert [x["titulo"] for x in f["temas"]] == ["Tres"]
    assert set(f["temas"][0]) == set(TemaFaltante.__annotations__)


def test_un_tema_sin_isrc_esta_si_coincide_titulo_y_duracion(hacer_track, deezer):
    """El tema de YouTube puede no haber conseguido su ISRC: no por eso falta."""
    deezer({10: ("Disco", "album", "2020-01-01", [tema("Uno", "AR1", 200), tema("Dos", "AR2", 300)])})
    tracks = [
        track(hacer_track, "Uno", "Disco", dur=202, aid=10),  # sin ISRC, misma duración
        track(hacer_track, "Dos", "Disco", dur=180, aid=10),  # mismo título, otra grabación
    ]
    res = C.revisar(tracks, cruce(10), "Los del Ejemplo")
    assert [x["titulo"] for f in res["faltan"] for x in f["temas"]] == ["Dos"]


def test_un_titulo_apenas_distinto_que_dura_lo_mismo_es_el_mismo_tema(hacer_track, deezer):
    """Del catálogo real: «Te Quiero de Verdad» en una edición y «Yo Te Quiero
    de Verdad» en otra, con otro ISRC. Sin la duración, en cambio, no alcanza."""
    deezer(
        {
            10: ("Disco", "album", "2020-01-01", [tema("Yo Te Quiero de Verdad", "AR1", 181)]),
            11: (
                "Disco",
                "album",
                "2019-03-22",
                [tema("Te Quiero de Verdad", "QM9", 181), tema("Otro", "QM8", 0)],
            ),
        }
    )
    tracks = [track(hacer_track, "Yo Te Quiero de Verdad", "Disco", isrc="AR1", dur=181, aid=10)]
    res = C.revisar(tracks, cruce(10), "Los del Ejemplo")
    assert [x["titulo"] for f in res["faltan"] for x in f["temas"]] == ["Otro"]


def test_un_vivo_no_tapa_la_falta_de_la_version_de_estudio(hacer_track, deezer):
    deezer({10: ("Disco", "album", "2020-01-01", [tema("Tema", "AR1", 200)])})
    tracks = [track(hacer_track, "Tema (En Vivo)", "Disco", dur=200, aid=10)]
    res = C.revisar(tracks, cruce(10), "Los del Ejemplo")
    assert res["temas"] == 1


def test_un_disco_entero_que_no_aparecio(hacer_track, deezer):
    deezer(
        {
            10: ("Disco", "album", "2020-01-01", [tema("Uno", "AR1")]),
            30: ("Otro Disco", "album", "2007-06-16", [tema("A", "US1"), tema("B", "US2")]),
            31: ("Suelto", "single", "2026-03-19", [tema("Suelto", "AR9")]),
        }
    )
    tracks = [track(hacer_track, "Uno", "Disco", isrc="AR1", aid=10)]
    res = C.revisar(tracks, cruce(10), "Los del Ejemplo")

    assert [(f["titulo"], f["relevado"], len(f["temas"])) for f in res["faltan"]] == [
        ("Otro Disco", False, 2),
        ("Suelto", False, 1),
    ]
    assert res["temas"] == 3
    assert [f["upc"] for f in res["faltan"]] == ["UPC30", "UPC31"], "el UPC, para ir a buscarlos"


def test_otra_edicion_del_mismo_disco_no_cuenta_la_falta_dos_veces(hacer_track, deezer):
    """La de 1991 y su reedición de 2019, a veces con el mismo ISRC y a veces
    con otro: la grabación que falta es una."""
    deezer(
        {
            10: ("Apasionados", "album", "2019-03-22", [tema("Uno", "QM1"), tema("Historia", "QM2", 219)]),
            11: ("Apasionados", "album", "1991-01-01", [tema("Uno", "QM1"), tema("Historia", "QM2", 219)]),
            12: ("Apasionados", "album", "2003-01-01", [tema("Historia", "ARX", 220)]),
        }
    )
    tracks = [track(hacer_track, "Uno", "Apasionados", isrc="QM1", aid=10, fecha="2019-03-22")]
    res = C.revisar(tracks, cruce(10), "Los del Ejemplo")
    assert [(f["fecha"], f["relevado"]) for f in res["faltan"]] == [("2019-03-22", True)]
    assert res["temas"] == 1


def test_un_release_cuyas_grabaciones_estan_todas_no_se_informa(hacer_track, deezer):
    """Un compilado o una reedición con temas que ya se relevaron en otro disco."""
    deezer(
        {
            10: ("Disco", "album", "2020-01-01", [tema("Uno", "AR1")]),
            40: ("Grandes Éxitos", "album", "2022-01-01", [tema("Uno", "AR1")]),
        }
    )
    tracks = [track(hacer_track, "Uno", "Disco", isrc="AR1", aid=10)]
    res = C.revisar(tracks, cruce(10), "Los del Ejemplo")
    assert res["revisada"] is True and res["faltan"] == [] and res["temas"] == 0


def test_un_single_relevado_se_reconoce_por_su_titulo(hacer_track, deezer):
    """Un single no tiene álbum en YouTube: su release se llama como el tema."""
    deezer(
        {
            10: ("Disco", "album", "2020-01-01", [tema("Uno", "AR1")]),
            50: ("Suelto", "single", "2021-05-05", [tema("Suelto", "AR5"), tema("Suelto (Remix)", "AR6")]),
        }
    )
    tracks = [
        track(hacer_track, "Uno", "Disco", isrc="AR1", aid=10),
        track(hacer_track, "Suelto", "", isrc="AR5", fecha="2021-05-05"),
    ]
    (f,) = C.revisar(tracks, cruce(10), "Los del Ejemplo")["faltan"]
    assert (f["titulo"], f["relevado"]) == ("Suelto", True)
    assert [x["titulo"] for x in f["temas"]] == ["Suelto (Remix)"]


# ============================================================
# Cuando Deezer no ayuda
# ============================================================


def test_un_release_que_deezer_no_contesto_se_cuenta_aparte(hacer_track, deezer):
    falso = deezer(
        {
            10: ("Disco", "album", "2020-01-01", [tema("Uno", "AR1")]),
            30: ("Otro Disco", "album", "2007-06-16", [tema("A", "US1")]),
        }
    )
    falso.caidos.add(30)
    tracks = [track(hacer_track, "Uno", "Disco", isrc="AR1", aid=10)]
    res = C.revisar(tracks, cruce(10), "Los del Ejemplo")
    assert res["sin_respuesta"] == 1 and res["faltan"] == []


def test_si_la_discografia_no_llega_la_revision_queda_sin_hacer(hacer_track, monkeypatch):
    monkeypatch.setattr(R, "_deezer_json", lambda ruta: None)
    tracks = [track(hacer_track, "Uno", "Disco", isrc="AR1", aid=10)]
    res = C.revisar(tracks, cruce(10), "Los del Ejemplo")
    assert res == C.completitud_vacia()


def test_una_discografia_enorme_se_recorta_y_se_dice(hacer_track, deezer, monkeypatch):
    monkeypatch.setattr(C, "MAX_RELEASES", 3)
    deezer({i: (f"Disco {i}", "album", "2020-01-01", [tema(f"T{i}", f"AR{i}")]) for i in range(10, 20)})
    tracks = [track(hacer_track, "T10", "Disco 10", isrc="AR10", aid=10)]
    res = C.revisar(tracks, cruce(10), "Los del Ejemplo")
    assert res["recortada"] is True and res["releases"] == 3


def test_el_avance_se_avisa_por_release(hacer_track, deezer):
    deezer({i: (f"Disco {i}", "album", "2020-01-01", [tema(f"T{i}", f"AR{i}")]) for i in range(10, 14)})
    tracks = [track(hacer_track, "T10", "Disco 10", isrc="AR10", aid=10)]
    visto = []
    C.revisar(tracks, cruce(10), "Los del Ejemplo", avance=lambda h, t: visto.append((h, t)))
    assert visto == [(1, 4), (2, 4), (3, 4), (4, 4)]


# ============================================================
# La marca en el producto
# ============================================================


def test_el_producto_queda_marcado_con_lo_que_le_falta(hacer_track, deezer):
    deezer(
        {
            10: ("Disco", "album", "2020-01-01", [tema("Uno", "AR1"), tema("Dos", "AR2")]),
            30: ("Otro Disco", "album", "2007-06-16", [tema("A", "US1")]),
        }
    )
    tracks = [
        track(hacer_track, "Uno", "Disco", isrc="AR1", aid=10),
        track(hacer_track, "Entero", "Completo", isrc="AR7"),
    ]
    comp = C.revisar(tracks, cruce(10), "Los del Ejemplo")
    productos = C.marcar(P.group_products(tracks, "Los del Ejemplo"), comp)

    por_titulo = {p["title"]: p for p in productos}
    assert por_titulo["Disco"].get("faltan_temas") == ["Dos"]
    assert "faltan_temas" not in por_titulo["Completo"], "al que no le falta nada no se le pone la clave"


def test_sin_revision_ningun_producto_queda_marcado(catalogo_ejemplo):
    C.marcar(catalogo_ejemplo, C.completitud_vacia())
    assert not any("faltan_temas" in p for p in catalogo_ejemplo)


# ============================================================
# Hasta donde llega el dato: validación, reporte y tabla
# ============================================================


def _disco_incompleto(hacer_track, deezer):
    deezer(
        {
            10: ("Disco", "album", "2020-01-01", [tema("Uno", "AR1"), tema("Dos", "AR2")]),
            30: ("Otro Disco", "album", "2007-06-16", [tema("A", "US1")]),
        }
    )
    tracks = [track(hacer_track, "Uno", "Disco", isrc="AR1", aid=10)]
    comp = C.revisar(tracks, cruce(10), "Los del Ejemplo")
    return C.marcar(P.group_products(tracks, "Los del Ejemplo"), comp), comp


def test_la_validacion_avisa_del_disco_incompleto_sin_volverlo_error(hacer_track, deezer):
    from migrador import validar as V

    productos, _comp = _disco_incompleto(hacer_track, deezer)
    res = V.validar(productos, "Los del Ejemplo")
    (aviso,) = [h for h in res["hallazgos"] if h["codigo"] == "album_incompleto"]
    assert aviso["nivel"] == "aviso" and aviso["producto"] == "Disco"
    assert "(1): Dos." in aviso["mensaje"], "la cuenta va entre paréntesis: no hay «1 temas»"
    assert not [h for h in res["errores"] if h["codigo"] == "album_incompleto"]


def test_el_reporte_dice_como_se_listo_y_que_falta(hacer_track, deezer):
    from migrador import paquete

    productos, comp = _disco_incompleto(hacer_track, deezer)
    diag = {"via": "busqueda", "temas": 1, "unidades": 101, "cortado_por_cuota": False, "completitud": comp}
    texto = paquete.reporte_texto(productos, "Los del Ejemplo", diag=diag)

    assert "CÓMO SE LISTÓ EL CATÁLOGO" in texto
    assert "Por el buscador de YouTube. Temas: 1. Unidades de cuota: 101." in texto
    assert "EN DEEZER Y NO EN YOUTUBE. Grabaciones de Los del Ejemplo: 2" in texto
    assert "Otro Disco (album, 2007-06-16, UPC UPC30) [no apareció en YouTube]" in texto
    assert "      - A  US1" in texto
    assert "Disco (album, 2020-01-01, UPC UPC10) [está en el catálogo, incompleto]" in texto
    pendiente = "temas que Deezer tiene en este disco y no aparecieron en YouTube (1): Dos"
    assert pendiente in texto, "y en los pendientes del producto"


def test_el_reporte_de_un_catalogo_cortado_lo_dice_en_mayusculas(catalogo_ejemplo):
    from migrador import paquete

    diag = {
        "via": "busqueda",
        "temas": 150,
        "unidades": 300,
        "cortado_por_cuota": True,
        "completitud": C.completitud_vacia(),
    }
    texto = paquete.reporte_texto(catalogo_ejemplo, "X", diag=diag)
    assert "INCOMPLETO" in texto
    assert "No se comparó contra la discografía de Deezer" in texto


def test_el_reporte_sin_diagnostico_sale_como_siempre(catalogo_ejemplo):
    """Quien arma un ZIP desde un script, sin relevar, no pasa diagnóstico."""
    from migrador import paquete

    texto = paquete.reporte_texto(catalogo_ejemplo, "X")
    assert "CÓMO SE LISTÓ" not in texto and "PENDIENTES POR PRODUCTO" in texto
    assert paquete.reporte_texto(catalogo_ejemplo, "X", diag={}) == texto


def test_el_reporte_sale_en_ingles(hacer_track, deezer):
    from migrador import i18n, paquete

    productos, comp = _disco_incompleto(hacer_track, deezer)
    diag = {"via": "subidas", "temas": 1, "unidades": 2, "cortado_por_cuota": False, "completitud": comp}
    i18n.poner_idioma("en")
    texto = paquete.reporte_texto(productos, "Los del Ejemplo", diag=diag)
    assert "HOW THE CATALOG WAS LISTED" in texto and "uploads list. Tracks: 1. Quota units: 2." in texto
    assert "ON DEEZER BUT NOT ON YOUTUBE. Recordings by Los del Ejemplo: 2" in texto


def test_la_tabla_recibe_los_temas_que_faltan(hacer_track, deezer):
    import server

    productos, _comp = _disco_incompleto(hacer_track, deezer)
    assert server.producto_json(productos[0])["faltan"] == ["Dos"]
    productos[0].pop("faltan_temas")
    assert server.producto_json(productos[0])["faltan"] == []


def test_los_productos_sin_distribuidora_tienen_su_opcion_en_el_filtro(hacer_track):
    """Sin ella, al filtrar por distribuidora no había casilla que los mostrara."""
    tracks = [
        hacer_track("A", "Con", 2020, dist="ONErpm"),
        hacer_track("B", "Sin", 2021, dist=P.SIN_DATOS),
        hacer_track("C", "Sin Dos", 2022, dist=P.SIN_DATOS),
    ]
    opciones = P.distributor_options(P.group_products(tracks, "X"))
    assert opciones == [{"name": "", "count": 2}, {"name": "ONErpm", "count": 1}]


# ============================================================
# Sumar al catálogo lo que sólo está en Deezer
# ============================================================
#
# Informar lo que falta dejaba el trabajo a medias: había que sumarlo a mano a
# la hoja de ingesta, con sus códigos. Deezer ya los tiene, así que entra solo,
# marcado, y con una regla para cada caso.


def ubicado(t, pos, disco=1):
    """El track ya ubicado en el tracklist de su álbum, como lo deja el cruce."""
    t["track_number"], t["disc_number"], t["orden_fuente"] = pos, disco, "deezer"
    return t


def _catalogo(hacer_track, deezer, discos, tracks, titulares=None):
    falso = deezer(discos)
    falso.titulares.update(titulares or {})
    datos = cruce(10)
    comp = C.revisar(tracks, datos, "Los del Ejemplo")
    todos = tracks + C.sumar_de_deezer(tracks, comp, datos)
    productos = C.marcar(P.group_products(todos, "Los del Ejemplo"), comp, datos)
    return {p["title"]: p for p in productos}, comp, falso


def test_el_tema_que_faltaba_entra_al_disco_en_su_lugar(hacer_track, deezer):
    discos = {
        10: ("Disco", "album", "2020-01-01", [tema("Uno", "AR1"), tema("Dos", "AR2"), tema("Tres", "AR3")])
    }
    tracks = [
        ubicado(track(hacer_track, "Uno", "Disco", isrc="AR1", aid=10), 1),
        ubicado(track(hacer_track, "Tres", "Disco", isrc="AR3", aid=10), 3),
    ]
    for t in tracks:
        t["upc"], t["distributor"] = "UPC10", "ONErpm"
    productos, comp, _f = _catalogo(hacer_track, deezer, discos, tracks)

    disco = productos["Disco"]
    assert [(t.get("track_number"), t["track"]) for t in disco["tracks"]] == [
        (1, "Uno"),
        (2, "Dos"),
        (3, "Tres"),
    ]
    nuevo = disco["tracks"][1]
    assert set(Track.__required_keys__) <= set(nuevo), "con la forma de cualquier track"
    assert (nuevo.get("origen"), nuevo["isrc"], nuevo["video_id"], nuevo["views"]) == ("deezer", "AR2", "", 0)
    assert nuevo["url"] == "https://www.deezer.com/track/1002"
    assert (disco["distributor"], disco["upc"]) == ("ONErpm", "UPC10"), "el disco sigue siendo el mismo"
    assert disco["order_unconfirmed"] is False
    assert disco.get("de_deezer") == 1 and "origen" not in disco
    assert "faltan_temas" not in disco, "ya no falta: está"
    assert comp["faltan"][0]["sumado"] is True


def test_a_un_disco_con_el_orden_estimado_no_se_le_suma_nada(hacer_track, deezer):
    """Mezclar la posición real de un tema con las estimadas de los demás daría
    números repetidos. Ahí se avisa, como antes."""
    discos = {
        10: ("Disco", "album", "2020-01-01", [tema("Uno", "AR1"), tema("Dos", "AR2"), tema("Tres", "AR3")])
    }
    tracks = [
        ubicado(track(hacer_track, "Uno", "Disco", isrc="AR1", aid=10), 1),
        track(hacer_track, "Otro Nombre", "Disco"),  # del disco en YouTube, sin ubicar en Deezer
    ]
    productos, comp, _f = _catalogo(hacer_track, deezer, discos, tracks)
    disco = productos["Disco"]
    assert disco["track_count"] == 2 and "de_deezer" not in disco
    assert disco.get("faltan_temas") == ["Dos", "Tres"]
    assert comp["faltan"][0]["sumado"] is False


def test_si_el_lugar_del_tema_esta_ocupado_no_se_lo_suma(hacer_track, deezer):
    discos = {10: ("Disco", "album", "2020-01-01", [tema("Uno", "AR1"), tema("Dos", "AR2")])}
    # YouTube tiene en el lugar 2 otra cosa, que el cruce ubicó ahí.
    tracks = [
        ubicado(track(hacer_track, "Uno", "Disco", isrc="AR1", aid=10), 1),
        ubicado(track(hacer_track, "Dos (En Vivo)", "Disco", aid=10), 2),
    ]
    productos, comp, _f = _catalogo(hacer_track, deezer, discos, tracks)
    assert productos["Disco"]["track_count"] == 2
    assert comp["faltan"][0]["sumado"] is False


def test_un_disco_que_no_aparecio_se_arma_entero_con_los_datos_de_deezer(hacer_track, deezer):
    discos = {
        10: ("Disco", "album", "2020-01-01", [tema("Uno", "AR1")]),
        30: (
            "Otro Disco",
            "album",
            "2007-06-16",
            [tema("A", "US1", 181), tema("Uno", "AR1"), tema("C", "US3")],
        ),
    }
    tracks = [ubicado(track(hacer_track, "Uno", "Disco", isrc="AR1", aid=10), 1)]
    productos, comp, falso = _catalogo(hacer_track, deezer, discos, tracks)

    otro = productos["Otro Disco"]
    assert otro.get("origen") == "deezer" and otro.get("de_deezer") == 3
    assert [t["track"] for t in otro["tracks"]] == ["A", "Uno", "C"], (
        "entero: también el tema que ya estaba en otro disco"
    )
    assert (otro["upc"], otro["label"], otro["release_date"], otro["release_year"]) == (
        "UPC30",
        "Sello de Deezer",
        "2007-06-16",
        2007,
    )
    assert otro["distributor"] == "", "la distribuidora sólo la publica YouTube: no se inventa"
    assert otro["order_unconfirmed"] is False and otro["artist"] == "Los del Ejemplo"
    assert otro["tracks"][0]["duration_s"] == 181 and otro["tracks"][0]["artists"] == ["Los del Ejemplo"]
    assert "origen" not in productos["Disco"]
    assert not [r for r in falso.pedidos if r.startswith("search")], "todo sale de lo que ya se pidió"
    assert [f["sumado"] for f in comp["faltan"]] == [True]


def test_un_single_que_no_aparecio_se_llama_como_su_tema(hacer_track, deezer):
    discos = {
        10: ("Disco", "album", "2020-01-01", [tema("Uno", "AR1")]),
        31: ("Suelto", "single", "2026-03-19", [tema("Suelto", "AR9")]),
    }
    tracks = [ubicado(track(hacer_track, "Uno", "Disco", isrc="AR1", aid=10), 1)]
    productos, _c, _f = _catalogo(hacer_track, deezer, discos, tracks)
    suelto = productos["Suelto"]
    assert (suelto["kind"], suelto["track_count"], suelto.get("origen")) == ("single", 1, "deezer")
    assert suelto["tracks"][0]["album"] == P.SIN_ALBUM


def test_una_colaboracion_queda_a_nombre_de_quien_figura(hacer_track, deezer):
    """Del catálogo real: cuatro de los seis lanzamientos que sólo estaban en
    Deezer figuraban a nombre de otro artista. Deezer los lista en la
    discografía de los dos, y adjudicárselos al del canal era regalarle un
    release ajeno."""
    from migrador import paquete
    from migrador import validar as V

    discos = {
        10: ("Disco", "album", "2020-01-01", [tema("Uno", "AR1")]),
        31: ("Es Mi Culpa", "single", "2026-03-19", [tema("Es Mi Culpa", "AR9")]),
        32: ("Propio", "single", "2026-04-01", [tema("Propio", "AR8")]),
    }
    tracks = [ubicado(track(hacer_track, "Uno", "Disco", isrc="AR1", aid=10), 1)]
    productos, _c, _f = _catalogo(hacer_track, deezer, discos, tracks, titulares={31: "Walter Encina"})

    assert productos["Es Mi Culpa"]["artist"] == "Walter Encina"
    assert productos["Propio"]["artist"] == "Los del Ejemplo"

    avisos = {
        h["producto"]: h["mensaje"]
        for h in V.validar(list(productos.values()), "Los del Ejemplo")["hallazgos"]
        if h["codigo"] == "solo_en_deezer"
    }
    assert "a nombre de Walter Encina, no de Los del Ejemplo" in avisos["Es Mi Culpa"]
    assert "Walter" not in avisos["Propio"] and "no apareció en YouTube" in avisos["Propio"]

    filas = {
        f[1]: f for f in paquete.filas_ingesta(list(productos.values()), "Los del Ejemplo", False, False)
    }
    assert filas["Es Mi Culpa"][2] == "Walter Encina", "en la hoja, a nombre de quien figura"
    assert filas["Disco"][2] == "Los del Ejemplo" and filas["Propio"][2] == "Los del Ejemplo"


def test_la_validacion_y_el_reporte_dicen_que_se_sumo_de_deezer(hacer_track, deezer):
    from migrador import paquete
    from migrador import validar as V

    discos = {
        10: ("Disco", "album", "2020-01-01", [tema("Uno", "AR1"), tema("Dos", "AR2")]),
        30: ("Otro Disco", "album", "2007-06-16", [tema("A", "US1")]),
    }
    tracks = [ubicado(track(hacer_track, "Uno", "Disco", isrc="AR1", aid=10), 1)]
    productos, comp, _f = _catalogo(hacer_track, deezer, discos, tracks)
    lista = list(productos.values())

    por_codigo = {h["codigo"]: h for h in V.validar(lista, "Los del Ejemplo")["hallazgos"]}
    assert (
        por_codigo["temas_de_deezer"]["producto"] == "Disco"
        and "(1): Dos." in por_codigo["temas_de_deezer"]["mensaje"]
    )
    assert por_codigo["solo_en_deezer"]["nivel"] == "aviso"
    assert "album_incompleto" not in por_codigo

    diag = {"via": "busqueda", "temas": 1, "unidades": 101, "cortado_por_cuota": False, "completitud": comp}
    texto = paquete.reporte_texto(lista, "Los del Ejemplo", diag=diag)
    assert "[sumado a su disco]" in texto and "[sumado como lanzamiento aparte, sólo en Deezer]" in texto
    assert "sumados con los datos de Deezer (1): Dos" in texto
    assert "no apareció en YouTube: los datos son de Deezer" in texto


def test_un_tema_sin_video_no_va_a_buscar_la_referencia_a_youtube(hacer_track, deezer, monkeypatch, tmp_path):
    from migrador import audio as A

    discos = {
        10: ("Disco", "album", "2020-01-01", [tema("Uno", "AR1")]),
        31: ("Suelto", "single", "2026-03-19", [tema("Suelto", "AR9")]),
    }
    tracks = [ubicado(track(hacer_track, "Uno", "Disco", isrc="AR1", aid=10), 1)]
    productos, _c, _f = _catalogo(hacer_track, deezer, discos, tracks)
    pedidos = []

    def bajar(video_id, dest_dir, log=print, errores=None):
        pedidos.append(video_id)
        return None, None, None

    monkeypatch.setattr(A, "bajar_referencia_youtube", bajar)
    A.fetch_audio([productos["Suelto"], productos["Disco"]], dest_dir=str(tmp_path), log=lambda *_: None)
    assert pedidos == [productos["Disco"]["tracks"][0]["video_id"]], "sólo el que tiene video"
    assert "no apareció en YouTube" in productos["Suelto"]["tracks"][0].get("audio_error", "")


def test_la_tabla_recibe_de_donde_salio_cada_cosa(hacer_track, deezer):
    import server

    discos = {
        10: ("Disco", "album", "2020-01-01", [tema("Uno", "AR1"), tema("Dos", "AR2")]),
        31: ("Es Mi Culpa", "single", "2026-03-19", [tema("Es Mi Culpa", "AR9")]),
    }
    tracks = [ubicado(track(hacer_track, "Uno", "Disco", isrc="AR1", aid=10), 1)]
    productos, _c, _f = _catalogo(hacer_track, deezer, discos, tracks, titulares={31: "Walter Encina"})

    disco: dict[str, Any] = server.producto_json(productos["Disco"])
    assert (disco["origen"], disco["de_deezer"]) == ("", 1)
    assert [t["origen"] for t in disco["detalle"]] == ["", "deezer"]
    ajeno = server.producto_json(productos["Es Mi Culpa"])
    assert (ajeno["origen"], ajeno["de_deezer"], ajeno["artista"]) == ("deezer", 1, "Walter Encina")


def test_el_diagnostico_cuenta_los_temas_de_youtube_no_los_sumados(hacer_track, deezer, monkeypatch):
    """«290 temas, que gastaron 607 unidades» habla de lo que se listó en
    YouTube: los que se suman de Deezer no gastaron nada y no entran ahí."""
    from migrador import migrar_core as M

    deezer(
        {
            10: ("Disco", "album", "2020-01-01", [tema("Uno", "AR1"), tema("Dos", "AR2")]),
            30: ("Otro Disco", "album", "2007-06-16", [tema("A", "US1"), tema("B", "US2")]),
        }
    )
    uno = ubicado(track(hacer_track, "Uno", "Disco", isrc="AR1", aid=10), 1)
    relevado = {
        "artist": "Los del Ejemplo",
        "channel_title": "Los del Ejemplo - Topic",
        "tracks": [uno],
        "codes": {"isrc": 1, "upc": 1, "matched": 1, "source": "Deezer", "fallas": 0},
        "cruce": cruce(10),
        "via": "busqueda",
        "unidades": 101,
    }
    monkeypatch.setattr(M.relevar_core, "relevar", lambda *a, **k: relevado)
    prods, _artista, todos, diag = M.relevar_catalogo("https://www.youtube.com/@x", "k")
    assert diag["temas"] == 1 and len(todos) == 4
    assert {p["title"]: p["track_count"] for p in prods} == {"Disco": 2, "Otro Disco": 2}


# ============================================================
# Los ISRC que la búsqueda no encontró, desde la discografía
# ============================================================
#
# En el catálogo real quedaban 53 temas sin ISRC. Doce estaban en la
# discografía que ya se baja para comparar, con su título y su duración: la
# búsqueda por texto de Deezer, que devuelve cinco resultados, no los había
# traído. Los otros eran cortes de un megamix, y esos tienen que seguir vacíos.


def test_un_tema_sin_isrc_lo_consigue_de_la_discografia(hacer_track, deezer):
    deezer({10: ("Disco", "album", "2020-01-01", [tema("Uno", "AR1", 200), tema("Dos", "AR2", 215)])})
    tracks = [
        track(hacer_track, "Uno", "Disco", isrc="AR1", dur=200, aid=10),
        track(hacer_track, "Dos", "Disco", dur=213),  # la búsqueda no lo encontró
    ]
    res = C.revisar(tracks, cruce(10), "Los del Ejemplo")
    assert (tracks[1]["isrc"], tracks[1]["match"]) == ("AR2", "alta")
    assert res["isrc_completados"] == 1
    assert res["faltan"] == [], "y con su código, ya no figura como faltante"


@pytest.mark.parametrize(
    ("titulo", "duracion", "motivo"),
    [
        ("Dos", 72, "el corte de un megamix se llama igual y dura un tercio"),
        ("Dos (En Vivo)", 215, "es otra versión"),
        ("Dos", 0, "sin la duración no hay con qué confirmarlo"),
        ("Otro Tema", 215, "no está en la discografía"),
    ],
)
def test_ante_la_duda_el_isrc_queda_en_blanco(hacer_track, deezer, titulo, duracion, motivo):
    deezer({10: ("Disco", "album", "2020-01-01", [tema("Uno", "AR1", 200), tema("Dos", "AR2", 215)])})
    tracks = [
        track(hacer_track, "Uno", "Disco", isrc="AR1", dur=200, aid=10),
        track(hacer_track, titulo, "Megamix", dur=duracion),
    ]
    res = C.revisar(tracks, cruce(10), "Los del Ejemplo")
    assert tracks[1]["isrc"] == "", motivo
    assert res["isrc_completados"] == 0


def test_dos_grabaciones_que_se_llaman_y_duran_igual_no_se_eligen(hacer_track, deezer):
    """La de estudio y una regrabación, las dos de 215 segundos, con códigos
    distintos: no hay cómo saber cuál es la de YouTube."""
    deezer(
        {
            10: ("Disco", "album", "2020-01-01", [tema("Uno", "AR1", 200), tema("Dos", "AR2", 215)]),
            11: ("Regrabado", "album", "2024-01-01", [tema("Dos", "AR9", 216)]),
        }
    )
    tracks = [
        track(hacer_track, "Uno", "Disco", isrc="AR1", dur=200, aid=10),
        track(hacer_track, "Dos", "Otro", dur=215),
    ]
    C.revisar(tracks, cruce(10), "Los del Ejemplo")
    assert tracks[1]["isrc"] == ""


def test_la_misma_grabacion_en_dos_discos_no_es_ambigua(hacer_track, deezer):
    """El mismo código en el disco y en el compilado es un solo código."""
    deezer(
        {
            10: ("Disco", "album", "2020-01-01", [tema("Uno", "AR1", 200), tema("Dos", "AR2", 215)]),
            11: ("Grandes Éxitos", "album", "2024-01-01", [tema("Dos", "AR2", 217)]),
        }
    )
    tracks = [
        track(hacer_track, "Uno", "Disco", isrc="AR1", dur=200, aid=10),
        track(hacer_track, "Dos", "Otro", dur=216),
    ]
    C.revisar(tracks, cruce(10), "Los del Ejemplo")
    assert tracks[1]["isrc"] == "AR2"


def test_un_isrc_que_ya_estaba_no_se_toca(hacer_track, deezer):
    deezer({10: ("Disco", "album", "2020-01-01", [tema("Uno", "AR1", 200)])})
    tracks = [track(hacer_track, "Uno", "Disco", isrc="XX9", dur=200, aid=10)]
    tracks[0]["match"] = "media"
    C.revisar(tracks, cruce(10), "Los del Ejemplo")
    assert (tracks[0]["isrc"], tracks[0]["match"]) == ("XX9", "media")
