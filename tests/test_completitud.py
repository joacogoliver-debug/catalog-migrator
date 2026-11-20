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
        # Lo que contesta el buscador de artistas, y los temas más escuchados
        # de cada perfil: {id: (nombre, [temas])}.
        self.perfiles = {}
        # Álbumes que existen en Deezer pero no en la discografía del artista
        # (un compilado de varios), y los que devuelve el buscador de álbumes.
        self.fuera_de_discografia = set()
        self.por_titulo = []
        self.sellos = {}  # id de álbum -> sello, si no es el de siempre

    def __call__(self, ruta):
        self.pedidos.append(ruta)
        if ruta.startswith("search/album?"):
            return {
                "data": [
                    {"id": i, "title": self.discos[i][0], "record_type": self.discos[i][1]}
                    for i in self.por_titulo
                ]
            }
        if ruta.startswith("search/artist?"):
            return {"data": [{"id": i, "name": nombre} for i, (nombre, _top) in self.perfiles.items()]}
        if ruta.startswith("artist/") and "/top" in ruta:
            return {"data": self.perfiles.get(int(ruta.split("/")[1]), ("", []))[1]}
        if ruta.startswith("artist/") and "/" not in ruta[len("artist/") :]:
            aid = int(ruta.split("/")[1])
            if aid == ARTISTA:
                return {"id": aid, "name": "Los del Ejemplo"}
            return {"id": aid, "name": self.perfiles[aid][0]} if aid in self.perfiles else {}
        if ruta.startswith("artist/"):
            aid = int(ruta.split("/")[1])
            ids = self.discos if aid == ARTISTA else self.de_otros.get(aid, {})
            data = [
                {"id": i, "title": d[0], "record_type": d[1], "release_date": d[2]}
                for i, d in ids.items()
                if i in self.discos and i not in self.fuera_de_discografia
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
            "label": self.sellos.get(aid, "Sello de Deezer"),
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
    """Un perfil que se llama igual y no tiene ningún tema del canal es un
    homónimo: no se usa su discografía."""
    falso = deezer({})
    falso.perfiles = {ARTISTA: ("Los del Ejemplo", [tema("Otra Cosa", "XX1", 200)])}
    tracks = [track(hacer_track, "T", "Disco", isrc="AR0000000001")]
    res = C.revisar(tracks, cruce(), "Los del Ejemplo")
    assert res["revisada"] is False and res["faltan"] == []
    assert not any("/albums" in ruta for ruta in falso.pedidos), "no se le pide la discografía"


# ============================================================
# El perfil del artista, cuando el cruce tema por tema no encontró nada
# ============================================================
#
# De un caso real: la app decía que una artista «no está en Deezer» con su
# perfil ahí. El cruce depende del buscador de Deezer, que busca por texto; si
# ningún tema aparece, no queda álbum verificado del que sacar el artista, y la
# comparación con la discografía, que no necesita al buscador, nunca corría.


def _sin_cruce(hacer_track):
    """Un disco de tres temas del que el cruce no encontró nada."""
    return [
        track(hacer_track, "Uno", "Disco", dur=200),
        track(hacer_track, "Dos", "Disco", dur=210),
        track(hacer_track, "Tres", "Disco", dur=220),
    ]


DISCO_SIN_CRUCE = {
    10: (
        "Disco",
        "album",
        "2020-01-01",
        [tema("Uno", "AR1", 200), tema("Dos", "AR2", 211), tema("Tres", "AR3", 219)],
    )
}


def test_el_artista_se_encuentra_por_nombre_y_sus_temas_lo_confirman(hacer_track, deezer):
    falso = deezer(DISCO_SIN_CRUCE)
    falso.perfiles = {ARTISTA: ("Los Del Ejemplo", [tema("Dos", "AR2", 211)])}
    tracks = _sin_cruce(hacer_track)
    datos: CruceDeezer = {"albumes": {}, "verificados": {}}
    comp = C.revisar(tracks, datos, "Los del Ejemplo")

    assert comp["revisada"] is True
    assert (comp["artista_deezer"], comp["artista_id"], comp["como"]) == (
        "Los Del Ejemplo",
        ARTISTA,
        "nombre",
    )
    assert [t["isrc"] for t in tracks] == ["AR1", "AR2", "AR3"], "los códigos salen de la discografía"
    assert {t["upc"] for t in tracks} == {"UPC10"} and comp["verificados_por_tracklist"] == 1
    (disco,) = P.group_products(tracks, "Los del Ejemplo")
    assert disco["upc"] == "UPC10" and disco["order_unconfirmed"] is False


def test_un_perfil_con_otro_nombre_se_acepta_si_tiene_varios_temas_del_canal(hacer_track, deezer):
    """En YouTube «Q' Lokura» y en Deezer «Q’Lokura»: el nombre no coincide,
    pero tres temas con el mismo título y la misma duración no son casualidad."""
    falso = deezer(DISCO_SIN_CRUCE)
    falso.perfiles = {
        77: ("Otro Que Suena Parecido", [tema("Uno", "ZZ1", 300)]),
        ARTISTA: (
            "Ejemplo, Los",
            [tema("Uno", "AR1", 200), tema("Dos", "AR2", 211), tema("Tres", "AR3", 219)],
        ),
    }
    tracks = _sin_cruce(hacer_track)
    comp = C.revisar(tracks, {"albumes": {}, "verificados": {}}, "Los del Ejemplo")
    assert (comp["artista_id"], comp["como"]) == (ARTISTA, "nombre")
    assert [t["isrc"] for t in tracks] == ["AR1", "AR2", "AR3"]


def test_un_perfil_con_otro_nombre_y_un_solo_tema_no_alcanza(hacer_track, deezer):
    falso = deezer(DISCO_SIN_CRUCE)
    falso.perfiles = {ARTISTA: ("Otra Banda", [tema("Uno", "AR1", 200)])}
    tracks = _sin_cruce(hacer_track)
    comp = C.revisar(tracks, {"albumes": {}, "verificados": {}}, "Los del Ejemplo")
    assert comp["revisada"] is False and all(not t["isrc"] for t in tracks)


def test_el_perfil_que_indica_el_usuario_se_usa_sin_buscar(hacer_track, deezer):
    """El link que se pega manda: no se busca por nombre ni se pide evidencia."""
    falso = deezer(DISCO_SIN_CRUCE)
    tracks = _sin_cruce(hacer_track)
    comp = C.revisar(
        tracks, {"albumes": {}, "verificados": {}}, "Un Nombre Que No Ayuda", artista_deezer=ARTISTA
    )
    assert (comp["artista_deezer"], comp["artista_id"], comp["como"]) == (
        "Los del Ejemplo",
        ARTISTA,
        "manual",
    )
    assert [t["isrc"] for t in tracks] == ["AR1", "AR2", "AR3"]
    assert not any(ruta.startswith("search/") for ruta in falso.pedidos)


def test_un_perfil_indicado_que_no_existe_deja_la_revision_sin_hacer(hacer_track, deezer):
    deezer(DISCO_SIN_CRUCE)
    comp = C.revisar(_sin_cruce(hacer_track), {"albumes": {}, "verificados": {}}, "X", artista_deezer=999)
    assert comp["revisada"] is False


@pytest.mark.parametrize(
    ("pegado", "esperado"),
    [
        ("https://www.deezer.com/es/artist/4209085", 4209085),
        ("https://www.deezer.com/artist/27?utm_source=x", 27),
        ("deezer.com/en-gb/artist/27/top_track", 27),
        ("27", 27),
        ("  https://www.deezer.com/us/artist/27  ", 27),
        ("https://www.deezer.com/es/album/302127", 0),
        ("https://example.com/artist/27", 0),
        ("cualquier cosa", 0),
        ("", 0),
    ],
)
def test_el_link_del_perfil_de_deezer_se_entiende(pegado, esperado, monkeypatch):
    def urlopen(*_a, **_k):
        raise AssertionError("no hay que abrir nada para leer un link común")

    monkeypatch.setattr(R.urllib.request, "urlopen", urlopen)
    assert R.id_de_artista_deezer(pegado) == esperado


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
    todos = tracks + C.sumar_de_deezer(tracks, comp, datos, "Los del Ejemplo")
    C.fechar_desde_deezer(todos, datos)
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


# ============================================================
# Un release se entrega entero
# ============================================================
#
# YouTube no repite una grabación que ya tiene en otro disco. Del catálogo
# real: un compilado de cincuenta temas del que mostraba doce, y la hoja de
# ingesta salía con un «álbum» de doce temas numerados 2, 17, 18, 19…


def _ejemplo(nombre):
    return {"artist": {"name": nombre}}


def test_un_release_se_completa_con_los_lugares_que_youtube_no_muestra(hacer_track, deezer):
    discos = {
        10: (
            "Grandes Éxitos",
            "album",
            "2020-01-01",
            [tema("Uno", "AR1"), tema("Dos", "AR2"), tema("Tres", "AR3"), tema("Cuatro", "AR4")],
        ),
    }
    tracks = [
        ubicado(track(hacer_track, "Uno", "Grandes Éxitos", isrc="AR1", aid=10), 1),
        ubicado(track(hacer_track, "Cuatro", "Grandes Éxitos", isrc="AR4", aid=10), 4),
        # «Dos» está en YouTube, pero en su disco original.
        track(hacer_track, "Dos", "El Original", isrc="AR2", fecha="2001-05-05"),
    ]
    tracks[2]["views"] = 900
    productos, comp, _f = _catalogo(hacer_track, deezer, discos, tracks)

    disco = productos["Grandes Éxitos"]
    assert [(t.get("track_number"), t["track"]) for t in disco["tracks"]] == [
        (1, "Uno"),
        (2, "Dos"),
        (3, "Tres"),
        (4, "Cuatro"),
    ], "entero y numerado de corrido"
    dos, tres = disco["tracks"][1], disco["tracks"][2]
    assert dos.get("origen") == "deezer" and dos["video_id"] == tracks[2]["video_id"], (
        "con el video de la misma grabación, que es de donde sale el audio de referencia"
    )
    assert dos["views"] == 0, "las vistas son del video en su disco: no se cuentan dos veces"
    assert (tres["video_id"], tres["url"]) == ("", "https://www.deezer.com/track/1003")
    assert disco.get("de_deezer") == 2 and "faltan_temas" not in disco
    assert comp["faltan"][0]["sumado"] is True
    assert productos["El Original"]["track_count"] == 1, "el disco original no se toca"


def test_un_compilado_del_artista_a_nombre_del_sello_se_completa(hacer_track, deezer):
    """El álbum figura en Deezer a nombre del sello, pero los temas son del
    artista: lo que decide es de quién es lo que falta."""
    propio = _ejemplo("Los De Ejemplo")  # escrito apenas distinto, como en Deezer
    discos = {
        10: ("Las Mejores", "album", "2020-01-01", [tema("Uno", "AR1") | propio, tema("Dos", "AR2") | propio])
    }
    tracks = [ubicado(track(hacer_track, "Uno", "Las Mejores", isrc="AR1", aid=10), 1)]
    productos, _c, _f = _catalogo(hacer_track, deezer, discos, tracks, titulares={10: "Leader Music"})
    disco = productos["Las Mejores"]
    assert disco["track_count"] == 2
    assert disco["tracks"][1]["artists"] == ["Los del Ejemplo"], (
        "a nombre del canal, como el resto del catálogo"
    )


def test_un_disco_compartido_no_se_completa_con_temas_de_otro_artista(hacer_track, deezer):
    from migrador import validar as V

    otros = [tema(f"De Otros {i}", f"XX{i}") | _ejemplo("Los Lamas") for i in range(1, 11)]
    discos = {10: ("20 Temas Juntos", "album", "2020-01-01", [tema("Uno", "AR1"), *otros])}
    tracks = [ubicado(track(hacer_track, "Uno", "20 Temas Juntos", isrc="AR1", aid=10), 1)]
    productos, _c, _f = _catalogo(hacer_track, deezer, discos, tracks)

    disco = productos["20 Temas Juntos"]
    assert disco["track_count"] == 1 and "de_deezer" not in disco
    assert disco.get("faltan_temas") == [f"De Otros {i}" for i in range(1, 11)]
    (aviso,) = [
        h for h in V.validar([disco], "Los del Ejemplo")["hallazgos"] if h["codigo"] == "album_incompleto"
    ]
    assert "(10): De Otros 1 · " in aviso["mensaje"] and aviso["mensaje"].count("De Otros") == 8
    assert "y 2 más" in aviso["mensaje"], "diez títulos no hacen ilegible el mensaje"


def test_un_disco_que_ya_esta_entero_no_recibe_nada(hacer_track, deezer):
    discos = {10: ("Disco", "album", "2020-01-01", [tema("Uno", "AR1"), tema("Dos", "AR2")])}
    tracks = [
        ubicado(track(hacer_track, "Uno", "Disco", isrc="AR1", aid=10), 1),
        ubicado(track(hacer_track, "Dos", "Disco", isrc="AR2", aid=10), 2),
    ]
    productos, comp, _f = _catalogo(hacer_track, deezer, discos, tracks)
    assert productos["Disco"]["track_count"] == 2 and "de_deezer" not in productos["Disco"]
    assert comp["faltan"] == []


# ============================================================
# Ubicar lo que el cruce no ubicó
# ============================================================


def test_un_titulo_cortado_por_youtube_se_ubica_por_su_comienzo_y_su_duracion(hacer_track, deezer):
    """YouTube corta los títulos a cien caracteres. El enganchado de seis temas
    del catálogo real no coincidía con el de Deezer, quedaba sin ubicar y
    dejaba el disco entero con el orden estimado, además de figurar como
    faltante cuando estaba."""
    largo = (
        "Alguien como yo / Abrazame otra vez / No vuelvas a intentar / Sabes como te quiero / Como pienso yo"
    )
    discos = {
        10: ("Disco", "album", "2020-01-01", [tema("Uno", "AR1"), tema(largo + " / Tu por mi", "AR2", 615)])
    }
    tracks = [
        ubicado(track(hacer_track, "Uno", "Disco", isrc="AR1", aid=10), 1),
        track(hacer_track, largo[:88] + "...", "Disco", dur=616, aid=10),
    ]
    deezer(discos)
    res = C.revisar(tracks, cruce(10), "Los del Ejemplo")
    assert (tracks[1].get("track_number"), tracks[1].get("orden_fuente")) == (2, "deezer")
    assert tracks[1]["isrc"] == "AR2", "y con su lugar, su código"
    assert res["faltan"] == [], "estaba: no falta"


@pytest.mark.parametrize(
    ("titulo", "duracion", "motivo"),
    [
        ("Alguien como yo / Abrazame otra vez...", 300, "el comienzo coincide pero dura otra cosa"),
        ("Alguien como yo...", 616, "un comienzo de quince letras no identifica nada"),
        ("Otro comienzo / Abrazame otra vez / Y algo más largo todavía...", 616, "no es el comienzo"),
    ],
)
def test_un_titulo_cortado_no_se_ubica_por_las_dudas(hacer_track, deezer, titulo, duracion, motivo):
    largo = "Alguien como yo / Abrazame otra vez / No vuelvas a intentar / Sabes como te quiero"
    discos = {10: ("Disco", "album", "2020-01-01", [tema("Uno", "AR1"), tema(largo, "AR2", 615)])}
    tracks = [
        ubicado(track(hacer_track, "Uno", "Disco", isrc="AR1", aid=10), 1),
        track(hacer_track, titulo, "Disco", dur=duracion, aid=10),
    ]
    deezer(discos)
    C.revisar(tracks, cruce(10), "Los del Ejemplo")
    assert "orden_fuente" not in tracks[1], motivo


# ============================================================
# Verificar un disco por su lista de temas
# ============================================================
#
# Del catálogo real: cuatro discos sin UPC y con el orden estimado que Deezer
# tenía enteros. Cada tema estaba también en un compilado, y la búsqueda
# devolvía el compilado.


def _base(hacer_track):
    """Un disco ya verificado: es lo que dice de quién es la discografía."""
    return ubicado(track(hacer_track, "Base", "Verificado", isrc="AR0", aid=10), 1)


def test_un_disco_se_verifica_por_su_tracklist_cuando_coincide_la_fecha(hacer_track, deezer):
    discos = {
        10: ("Verificado", "album", "2020-01-01", [tema("Base", "AR0")]),
        20: (
            "Pasajeros",
            "album",
            "2025-07-30",
            [tema("A", "US1", 200), tema("B", "US2", 210), tema("C", "US3", 220)],
        ),
        # El compilado tiene los mismos temas: es el que devolvía la búsqueda.
        21: ("Las 50 Mejores", "album", "2026-02-27", [tema("A", "US1", 200), tema("C", "US3", 220)]),
    }
    tracks = [
        _base(hacer_track),
        track(hacer_track, "C", "Pasajeros", dur=221, fecha="2025-07-30"),
        track(hacer_track, "A", "Pasajeros", dur=199, fecha="2025-07-30"),
    ]
    tracks[1]["upc_descartado"] = "Las 50 Mejores"
    productos, comp, _f = _catalogo(hacer_track, deezer, discos, tracks)

    assert comp["verificados_por_tracklist"] == 1
    disco = productos["Pasajeros"]
    assert disco["upc"] == "UPC20" and disco["order_unconfirmed"] is False
    assert [(t.get("track_number"), t["track"], t["isrc"]) for t in disco["tracks"]] == [
        (1, "A", "US1"),
        (2, "B", "US2"),
        (3, "C", "US3"),
    ], "verificado, ordenado, con sus códigos y completado con el tema que YouTube no mostraba"
    assert not any("upc_por_tracklist" in t or "upc_descartado" in t for t in disco["tracks"])


def test_con_otra_fecha_solo_vale_el_tracklist_exacto_y_se_avisa(hacer_track, deezer):
    """YouTube muestra la fecha de la edición digital y Deezer la original. Con
    exactamente los mismos temas es casi seguro el mismo release, pero no es
    seguro del todo: se acepta y se dice."""
    from migrador import validar as V

    discos = {
        10: ("Verificado", "album", "2020-01-01", [tema("Base", "AR0")]),
        20: ("A Mi Manera", "album", "2018-10-10", [tema("A", "US1", 200), tema("B", "US2", 210)]),
    }
    tracks = [
        _base(hacer_track),
        track(hacer_track, "A", "A Mi Manera", dur=200, fecha="2019-03-22"),
        track(hacer_track, "B", "A Mi Manera", dur=212, fecha="2019-03-22"),
    ]
    productos, comp, _f = _catalogo(hacer_track, deezer, discos, tracks)
    disco = productos["A Mi Manera"]
    assert comp["verificados_por_tracklist"] == 1 and disco["upc"] == "UPC20"
    assert disco["release_date"] == "2019-03-22", "la fecha del producto sigue siendo la de YouTube"
    (aviso,) = [
        h for h in V.validar([disco], "Los del Ejemplo")["hallazgos"] if h["codigo"] == "upc_por_tracklist"
    ]
    assert aviso["nivel"] == "aviso" and "A Mi Manera (2018-10-10)" in aviso["mensaje"]


@pytest.mark.parametrize(
    ("discos_de_deezer", "motivo"),
    [
        (
            {
                20: (
                    "A Mi Manera",
                    "album",
                    "2018-10-10",
                    [tema("A", "US1"), tema("B", "US2"), tema("C", "US3")],
                )
            },
            "con otra fecha y un tema de más, puede ser otra edición",
        ),
        (
            {
                20: ("A Mi Manera", "album", "2018-10-10", [tema("A", "US1"), tema("B", "US2")]),
                21: ("A Mi Manera", "album", "1992-01-04", [tema("A", "XX1"), tema("B", "XX2")]),
            },
            "dos ediciones calzan igual: no se elige",
        ),
        (
            {20: ("Las 50 Mejores", "album", "2019-03-22", [tema("A", "US1"), tema("B", "US2")])},
            "tiene los temas pero es otro disco: se llama distinto",
        ),
        (
            {20: ("A Mi Manera", "album", "2019-03-22", [tema("A", "US1"), tema("Otro", "US2")])},
            "le falta uno de los temas del disco",
        ),
        (
            {20: ("A Mi Manera", "album", "2019-03-22", [tema("A", "US1", 200), tema("B", "US2", 300)])},
            "un tema dura otra cosa: es otra grabación",
        ),
    ],
)
def test_un_disco_no_se_verifica_por_tracklist_ante_la_duda(hacer_track, deezer, discos_de_deezer, motivo):
    discos = {10: ("Verificado", "album", "2020-01-01", [tema("Base", "AR0")]), **discos_de_deezer}
    tracks = [
        _base(hacer_track),
        track(hacer_track, "A", "A Mi Manera", dur=200, fecha="2019-03-22"),
        track(hacer_track, "B", "A Mi Manera", dur=200, fecha="2019-03-22"),
    ]
    _productos, comp, _f = _catalogo(hacer_track, deezer, discos, tracks)
    assert comp["verificados_por_tracklist"] == 0, motivo
    # Se miran los tracks de YouTube y no el producto por su título: si a Deezer
    # le sobra un tema, ese álbum entra aparte, como «sólo en Deezer», y se
    # llama igual.
    assert all(not t["upc"] and "orden_fuente" not in t for t in tracks[1:]), motivo


def test_un_disco_que_el_cruce_ya_verifico_no_se_vuelve_a_buscar(hacer_track, deezer):
    """El UPC que ya tiene viene de un álbum verificado: no se pisa con otro."""
    discos = {
        10: ("Verificado", "album", "2020-01-01", [tema("Base", "AR0"), tema("Dos", "AR2")]),
        20: ("Verificado", "album", "2020-01-01", [tema("Base", "AR0"), tema("Dos", "AR2")]),
    }
    tracks = [_base(hacer_track), track(hacer_track, "Dos", "Verificado", dur=200)]
    tracks[0]["upc"] = "UPC10"
    _productos, comp, _f = _catalogo(hacer_track, deezer, discos, tracks)
    assert comp["verificados_por_tracklist"] == 0
    assert tracks[0]["upc"] == "UPC10"


def test_el_mismo_disco_escrito_con_otra_mayuscula_se_completa_una_sola_vez(hacer_track, deezer):
    """YouTube puede escribir el álbum distinto de un tema a otro. Para agrupar
    son el mismo disco; si para completar fueran dos, cada mitad recibiría los
    temas que le faltan y el producto saldría con los lugares repetidos."""
    discos = {
        10: (
            "Grandes Éxitos",
            "album",
            "2020-01-01",
            [tema("Uno", "AR1"), tema("Dos", "AR2"), tema("Tres", "AR3")],
        )
    }
    tracks = [
        ubicado(track(hacer_track, "Uno", "Grandes Éxitos", isrc="AR1", aid=10), 1),
        ubicado(track(hacer_track, "Tres", "GRANDES EXITOS", isrc="AR3", aid=10), 3),
    ]
    productos, _c, _f = _catalogo(hacer_track, deezer, discos, tracks)
    assert len(productos) == 1
    (disco,) = productos.values()
    assert [(t.get("track_number"), t["track"]) for t in disco["tracks"]] == [
        (1, "Uno"),
        (2, "Dos"),
        (3, "Tres"),
    ]


# ============================================================
# Dos temas que se llaman igual en el mismo disco
# ============================================================
#
# De un segundo catálogo real: un single con dos «One More Time (Radio Edit)»,
# de 236 y de 321 segundos. En Deezer son el «Short Radio Edit» y el «Radio
# Edit». El cruce ubica por título, los ponía a los dos en el lugar 2 y daba el
# orden por confirmado, con un número repetido.


def _radio_edits(hacer_track):
    corto = ubicado(
        track(hacer_track, "One More Time (Radio Edit)", "One More Time", isrc="GB54", dur=236, aid=10), 2
    )
    largo = ubicado(
        track(hacer_track, "One More Time (Radio Edit)", "One More Time", isrc="GB50", dur=321, aid=10), 2
    )
    corto["video_id"], largo["video_id"] = "corto", "largo"
    mix = ubicado(
        track(hacer_track, "One More Time (12 Mix)", "One More Time", isrc="GB51", dur=481, aid=10), 3
    )
    return [corto, largo, mix]


DISCO_RADIO_EDITS = {
    10: (
        "One More Time",
        "ep",
        "2000-11-13",
        [
            tema("One More Time (Short Radio Edit)", "GB54", 235),
            tema("One More Time (Radio Edit)", "GB50", 320),
            tema("One More Time (12 Mix)", "GB51", 480),
        ],
    )
}


def test_dos_temas_con_el_mismo_titulo_se_separan_por_su_isrc(hacer_track, deezer):
    tracks = _radio_edits(hacer_track)
    productos, comp, _f = _catalogo(hacer_track, deezer, DISCO_RADIO_EDITS, tracks)
    disco = productos["One More Time"]
    assert [(t.get("track_number"), t["isrc"], t["duration_s"]) for t in disco["tracks"]] == [
        (1, "GB54", 236),
        (2, "GB50", 321),
        (3, "GB51", 481),
    ]
    assert disco["order_unconfirmed"] is False and disco["track_count"] == 3
    assert "de_deezer" not in disco, "no faltaba ninguno: el «Short Radio Edit» era el de 236 segundos"
    assert comp["faltan"] == []


def test_sin_isrc_dos_temas_con_el_mismo_titulo_se_separan_por_la_duracion(hacer_track, deezer):
    """Sin código queda la duración: el de 236 segundos es el «Short Radio
    Edit» de 235, que se llama casi igual, y el de 321 es el «Radio Edit»."""
    tracks = _radio_edits(hacer_track)
    for t in tracks:
        t["isrc"] = ""
    productos, _c, _f = _catalogo(hacer_track, deezer, DISCO_RADIO_EDITS, tracks)
    disco = productos["One More Time"]
    assert [(t.get("track_number"), t["duration_s"], t["isrc"]) for t in disco["tracks"]] == [
        (1, 236, "GB54"),
        (2, 321, "GB50"),
        (3, 481, "GB51"),
    ], "cada uno en su lugar, y con el código de ese lugar"
    assert disco["order_unconfirmed"] is False


def test_si_no_hay_como_separarlos_el_disco_queda_con_el_orden_estimado(hacer_track, deezer):
    """Dos temas con el mismo título y la misma duración, sin código: no hay
    con qué decidir cuál es cuál, y un número repetido no es un orden."""
    discos = {10: ("Disco", "album", "2020-01-01", [tema("Tema", "AR1", 200), tema("Otro", "AR2", 300)])}
    tracks = [
        ubicado(track(hacer_track, "Tema", "Disco", dur=200, aid=10), 1),
        ubicado(track(hacer_track, "Tema", "Disco", dur=200, aid=10), 1),
    ]
    tracks[0]["video_id"], tracks[1]["video_id"] = "uno", "dos"
    productos, _c, _f = _catalogo(hacer_track, deezer, discos, tracks)
    disco = productos["Disco"]
    assert disco["order_unconfirmed"] is True
    assert disco["track_count"] == 2 and "de_deezer" not in disco, "y no se le suma nada a un disco sin orden"


def test_dos_temas_en_el_mismo_lugar_nunca_son_un_orden_confirmado(hacer_track):
    """La regla vale aunque no se haya podido comparar con Deezer: es de
    `productos`, y no depende de que alguien haya arreglado el choque antes."""
    tracks = _radio_edits(hacer_track)
    (disco,) = P.group_products(tracks, "Daft Punk")
    assert disco["order_unconfirmed"] is True
    assert sorted(t.get("track_number") or 0 for t in disco["tracks"]) == [1, 2, 3], "de corrido, estimados"


# ============================================================
# La edición del disco, y su fecha
# ============================================================
#
# De un segundo catálogo real. YouTube llama «Homework» a la edición aniversario,
# de 31 temas, y no publica su fecha. La búsqueda de los 16 temas originales cae
# en el «Homework» de 1997: el disco quedaba con ese UPC, 13 temas sin ubicar y
# el orden estimado, y la edición aniversario entraba aparte, entera, como un
# release que «sólo está en Deezer».


def _tarea(hacer_track, fecha=""):
    """Un disco con dos temas ubicados en la edición original y dos remixes que
    sólo están en la edición aniversario."""
    uno = ubicado(track(hacer_track, "Uno", "Tarea", isrc="AR1", dur=200, aid=10, fecha=fecha), 1)
    dos = ubicado(track(hacer_track, "Dos", "Tarea", isrc="AR2", dur=210, aid=10, fecha=fecha), 2)
    uno["upc"] = dos["upc"] = "UPC10"
    remix_uno = track(hacer_track, "Uno (Remix)", "Tarea", dur=301, fecha=fecha)
    remix_dos = track(hacer_track, "Dos (Remix)", "Tarea", dur=310, fecha=fecha)
    remix_uno["upc_descartado"] = "Tarea (Edición 25 Aniversario)"
    return [uno, dos, remix_uno, remix_dos]


def _ediciones(fecha_aniversario="1997-01-20"):
    originales = [tema("Uno", "AR1", 200), tema("Dos", "AR2", 210)]
    remixes = [
        tema("Uno (Remix)", "AR3", 300),
        tema("Dos (Remix)", "AR4", 310),
        tema("Tres (Remix)", "AR5", 320),
    ]
    return {
        10: ("Tarea", "album", "1997-01-16", originales),
        20: ("Tarea (Edición 25 Aniversario)", "album", fecha_aniversario, originales + remixes),
    }


def test_un_disco_a_medio_ubicar_pasa_a_la_edicion_que_tiene_todos_sus_temas(hacer_track, deezer):
    from migrador import validar as V

    productos, comp, _f = _catalogo(hacer_track, deezer, _ediciones(), _tarea(hacer_track))

    assert comp["verificados_por_tracklist"] == 1
    assert list(productos) == ["Tarea"], "la edición aniversario no entra aparte: es este disco"
    disco = productos["Tarea"]
    assert disco["upc"] == "UPC20" and disco["order_unconfirmed"] is False
    assert [(t.get("track_number"), t["track"], t["isrc"], t.get("origen", "")) for t in disco["tracks"]] == [
        (1, "Uno", "AR1", ""),
        (2, "Dos", "AR2", ""),
        (3, "Uno (Remix)", "AR3", ""),
        (4, "Dos (Remix)", "AR4", ""),
        (5, "Tres (Remix)", "AR5", "deezer"),
    ], "ordenado por la edición aniversario, con sus códigos y el tema que YouTube no mostró"
    assert not any("upc_descartado" in t for t in disco["tracks"])
    (aviso,) = [
        h for h in V.validar([disco], "Los del Ejemplo")["hallazgos"] if h["codigo"] == "upc_por_tracklist"
    ]
    assert "Tarea (Edición 25 Aniversario) (1997-01-20)" in aviso["mensaje"], (
        "y se dice de dónde salió el UPC"
    )


def test_con_otra_fecha_la_edicion_vale_si_youtube_muestra_casi_todo_el_album(hacer_track, deezer):
    """De un catálogo real: «En Vivo En El Teatro Colonial, Vol. 1» tenía 17
    temas en YouTube y 19 en Deezer, con otra fecha. Quedaba sin UPC ni ISRC
    siendo el único álbum con ese título. Con cuatro temas o más, y al menos
    cuatro de cada cinco del álbum, se acepta y se avisa."""
    from migrador import validar as V

    tracks = _tarea(hacer_track, fecha="1997-01-16")
    productos, comp, _f = _catalogo(hacer_track, deezer, _ediciones("2022-02-22"), tracks)
    assert comp["verificados_por_tracklist"] == 1
    disco = productos["Tarea"]
    assert disco["upc"] == "UPC20" and disco["order_unconfirmed"] is False
    assert disco["release_date"] == "1997-01-16", "la fecha sigue siendo la de YouTube"
    assert [h["codigo"] for h in V.validar([disco], "Los del Ejemplo")["hallazgos"]].count(
        "upc_por_tracklist"
    ) == 1


def test_con_otra_fecha_y_mostrando_poco_del_album_no_se_pasa_de_edicion(hacer_track, deezer):
    """La fecha de YouTube es un dato. Si además el disco es una parte chica
    del álbum, puede ser otro release: queda como estaba."""
    discos = _ediciones("2022-02-22")
    discos[20][3].extend(
        [tema("Cuatro (Remix)", "AR6", 330), tema("Cinco (Remix)", "AR7", 340), tema("Seis", "AR8", 350)]
    )
    tracks = _tarea(hacer_track, fecha="1997-01-16")
    productos, comp, _f = _catalogo(hacer_track, deezer, discos, tracks)
    assert comp["verificados_por_tracklist"] == 0
    assert [t["upc"] for t in tracks] == ["UPC10", "UPC10", "", ""], "queda como estaba"
    assert productos["Tarea"]["order_unconfirmed"] is True


def test_entre_el_disco_y_su_edicion_vale_el_que_se_llama_igual(hacer_track, deezer):
    """Sin fecha en YouTube y con los temas en los dos, no hay motivo para
    creer que es la edición: YouTube lo llama como el original."""
    discos = _ediciones()
    tracks = [
        _base(hacer_track),
        track(hacer_track, "Uno", "Tarea", dur=200, fecha=""),
        track(hacer_track, "Dos", "Tarea", dur=210, fecha=""),
    ]
    discos[30] = ("Verificado", "album", "2020-01-01", [tema("Base", "AR0")])
    falso = deezer(discos)
    datos = cruce(30)
    tracks[0]["album_deezer_id"] = 30
    comp = C.revisar(tracks, datos, "Los del Ejemplo")
    assert comp["verificados_por_tracklist"] == 1 and falso
    assert {t["upc"] for t in tracks[1:]} == {"UPC10"}


@pytest.mark.parametrize(
    ("de_youtube", "de_deezer", "es_edicion"),
    [
        ("Homework", "Homework (25th Anniversary Edition)", True),
        ("TRON: Legacy - The Complete Edition", "TRON: Legacy - The Complete Edition (Original Score)", True),
        ("Tarea", "Tarea - Edición Aniversario", True),
        ("Tarea", "TAREA [Deluxe] (Remasterizado)", True),
        ("Tarea", "Tarea", False),
        ("Tarea", "Tareas", False),
        ("Tarea", "Tarea 2", False),
        ("Tarea", "Tarea para el Hogar", False),
        ("Tarea (En Vivo)", "Tarea", False),
        ("", "(Edición Aniversario)", False),
    ],
)
def test_que_es_una_edicion_del_disco(de_youtube, de_deezer, es_edicion):
    assert C._es_edicion_de(de_youtube, de_deezer) is es_edicion


def test_sin_fecha_en_youtube_el_disco_lleva_la_de_su_album_de_deezer(hacer_track, deezer):
    from migrador import validar as V

    productos, _c, _f = _catalogo(hacer_track, deezer, _ediciones(), _tarea(hacer_track))
    disco = productos["Tarea"]
    assert (disco["release_date"], disco["release_year"], disco.get("fecha_fuente")) == (
        "1997-01-20",
        1997,
        "deezer",
    )
    (aviso,) = [
        h for h in V.validar([disco], "Los del Ejemplo")["hallazgos"] if h["codigo"] == "fecha_de_deezer"
    ]
    assert aviso["nivel"] == "aviso" and ": 1." in aviso["mensaje"]


def test_la_fecha_de_youtube_no_se_pisa_con_la_de_deezer(hacer_track):
    con_fecha = ubicado(track(hacer_track, "Uno", "Disco", aid=10, fecha="2019-03-22"), 1)
    con_fecha["upc"] = "UPC10"
    datos = cruce(10, otros={})
    datos["albumes"][10]["release_date"] = "1992-01-04"
    assert C.fechar_desde_deezer([con_fecha], datos) == 0
    (disco,) = P.group_products([con_fecha], "Los del Ejemplo")
    assert disco["release_date"] == "2019-03-22" and "fecha_fuente" not in disco


@pytest.mark.parametrize(
    ("fecha_deezer", "upc", "motivo"),
    [
        ("0000-00-00", "UPC10", "Deezer no sabe la fecha"),
        ("", "UPC10", "Deezer no trae fecha"),
        ("1992-01-04", "", "el disco no se verificó: no lleva el UPC de ese álbum"),
        ("1992-01-04", "OTRO", "lleva el UPC de otro álbum"),
    ],
)
def test_sin_fecha_confiable_el_disco_queda_sin_fecha(hacer_track, fecha_deezer, upc, motivo):
    t = ubicado(track(hacer_track, "Uno", "Disco", aid=10, fecha=""), 1)
    t["upc"] = upc
    datos = cruce(10)
    datos["albumes"][10]["release_date"] = fecha_deezer
    assert C.fechar_desde_deezer([t], datos) == 0, motivo
    (disco,) = P.group_products([t], "Los del Ejemplo")
    assert disco["release_date"] == "" and "fecha_fuente" not in disco, motivo


def test_el_mismo_tema_con_un_agregado_en_el_titulo_no_es_un_cruce_dudoso(hacer_track):
    """En la banda de sonido es «Overture (From "TRON: Legacy"/Score)» y en su
    edición completa, «Overture»: el mismo ISRC, la misma duración. Salía como
    error «no parecen la misma grabación», veintidós veces en un catálogo."""
    from migrador import validar as V

    a = hacer_track('Overture (From "TRON: Legacy"/Score)', "Banda", 2010, dur=149)
    b = hacer_track("Overture", "Edición Completa", 2020, dur=148)
    assert V._parentesco(a, b) == "misma"
    b["duration_s"] = 190
    assert V._parentesco(a, b) == "otra", "con otra duración sigue siendo otra grabación"
    vivo = hacer_track("Overture (En Vivo)", "Vivo", 2021, dur=149)
    assert V._parentesco(a, vivo) == "otra", "y una versión declarada, también"


# ============================================================
# Lo que subió la cobertura, medido con siete catálogos reales
# ============================================================
#
# ISRC de 91 % a 97 %, UPC de 93 % a 97 %, orden confirmado de 77 % a 89 %.
# Cada test es un caso que salió de mirar por qué un lanzamiento quedaba sin
# código teniendo su álbum publicado en Deezer.


def _en_vivo(hacer_track, fecha="2022-11-17"):
    """Un disco en vivo como lo muestra YouTube: la versión está en el título
    del disco, y los temas van sin ella."""
    album = "En Vivo en el Teatro"
    return [
        track(hacer_track, "Alma Mía", album, dur=153, fecha=fecha),
        track(hacer_track, "Corre, Corre", album, dur=108, fecha=fecha),
        track(hacer_track, "Cicatrices", album, dur=222, fecha=fecha),
    ]


DISCO_EN_VIVO = {
    10: ("Verificado", "album", "2020-01-01", [tema("Base", "AR0")]),
    20: (
        "En Vivo en el Teatro",
        "album",
        "2022-01-12",
        [
            tema("Alma Mía (En Vivo)", "AR1", 152),
            tema("Corre, Corre (En Vivo)", "AR2", 107),
            tema("Cicatrices (En Vivo; Acústico)", "AR3", 221),
        ],
    ),
}


def test_la_version_dicha_en_el_titulo_del_disco_vale_para_sus_temas(hacer_track, deezer):
    """El caso que más pesaba: discos en vivo enteros sin un solo código. En
    un catálogo real eran 70 temas sin ISRC y 8 lanzamientos sin UPC."""
    tracks = [_base(hacer_track), *_en_vivo(hacer_track)]
    productos, comp, _f = _catalogo(hacer_track, deezer, DISCO_EN_VIVO, tracks)
    disco = productos["En Vivo en el Teatro"]
    assert comp["verificados_por_tracklist"] == 1 and disco["upc"] == "UPC20"
    assert [(t.get("track_number"), t["track"], t["isrc"]) for t in disco["tracks"]] == [
        (1, "Alma Mía", "AR1"),
        (2, "Corre, Corre", "AR2"),
        (3, "Cicatrices", "AR3"),
    ]
    assert comp["isrc_completados"] == 3


def test_si_youtube_dice_en_vivo_y_deezer_no_lo_dice_en_ningun_lado_es_otro_tema(hacer_track):
    """Al revés no vale: «Tema (En Vivo)» en un disco común no es el «Tema»
    de estudio, aunque dure lo mismo."""
    vivo = track(hacer_track, "Tema (En Vivo)", "Disco", dur=200)
    estudio: TemaFaltante = {
        "titulo": "Tema",
        "isrc": "AR1",
        "duracion_s": 200,
        "posicion": 1,
        "disco": 1,
        "artista": "X",
        "deezer_id": 1,
    }
    assert C._ubicar(vivo, [estudio], "Disco") is None
    assert C._ubicar(vivo, [estudio], "Disco (En Vivo)") == estudio, "salvo que lo diga el disco de Deezer"


def test_un_remix_no_es_la_version_en_vivo(hacer_track):
    remix = track(hacer_track, "Tema (Remix)", "Disco en Vivo", dur=200)
    vivo: TemaFaltante = {
        "titulo": "Tema (En Vivo)",
        "isrc": "AR1",
        "duracion_s": 200,
        "posicion": 1,
        "disco": 1,
        "artista": "X",
        "deezer_id": 1,
    }
    assert C._ubicar(remix, [vivo], "Disco en Vivo") is None


def test_con_el_tema_de_estudio_y_su_vivo_en_el_disco_cada_uno_va_con_el_suyo(hacer_track):
    t = track(hacer_track, "Tema", "Disco", dur=200)
    estudio: TemaFaltante = {
        "titulo": "Tema",
        "isrc": "AR1",
        "duracion_s": 200,
        "posicion": 1,
        "disco": 1,
        "artista": "X",
        "deezer_id": 1,
    }
    vivo: TemaFaltante = {
        "titulo": "Tema (En Vivo)",
        "isrc": "AR2",
        "duracion_s": 201,
        "posicion": 2,
        "disco": 1,
        "artista": "X",
        "deezer_id": 2,
    }
    assert C._ubicar(t, [vivo, estudio], "Disco") == estudio


def test_el_mismo_tema_con_los_invitados_de_un_solo_lado(hacer_track):
    t = track(hacer_track, "Sobreviviendo", "Sobreviviendo", dur=247)
    con: TemaFaltante = {
        "titulo": "Sobreviviendo (feat. Toti Iglesias)",
        "isrc": "AR1",
        "duracion_s": 246,
        "posicion": 1,
        "disco": 1,
        "artista": "X",
        "deezer_id": 1,
    }
    assert C._ubicar(t, [con], "Sobreviviendo (feat. Toti Iglesias)") == con
    con["duracion_s"] = 300
    assert C._ubicar(t, [con], "Sobreviviendo (feat. Toti Iglesias)") is None, "con otra duración, no"


@pytest.mark.parametrize(
    ("de_youtube", "de_deezer", "es_edicion"),
    [
        ("Acústico en Fm Pasión (En Vivo)", "Acústico en Fm Pasión (102.7) (En Vivo)", True),
        ("Disco (En Vivo)", "Disco (Remixes)", False),
        ("Disco (En Vivo)", "Disco (Deluxe)", False),
    ],
)
def test_el_mismo_disco_con_el_parentesis_escrito_distinto(de_youtube, de_deezer, es_edicion):
    assert C._es_edicion_de(de_youtube, de_deezer) is es_edicion


def test_un_primero_de_enero_es_un_anio_sin_dia():
    assert R.fechas_cercanas("2010-01-01", "2010-12-07") is True
    assert R.fechas_cercanas("2010-12-07", "2010-01-01") is True
    assert R.fechas_cercanas("2010-01-01", "2011-03-01") is False
    assert R.fechas_cercanas("2010-03-01", "2010-12-07") is False, "con día, la fecha es la fecha"


def test_un_compilado_de_varios_se_encuentra_buscando_su_titulo(hacer_track, deezer):
    """No está en la discografía de nadie: figura a nombre de «Varios
    Artistas». Se lo busca por título y se acepta por los temas del artista."""
    discos = {
        10: ("Verificado", "album", "2020-01-01", [tema("Base", "AR0")]),
        30: (
            "Compilado de Verano",
            "album",
            "2021-12-20",
            [
                {"title": "De Otro", "isrc": "ZZ1", "duration": 180, "artist": {"name": "Otra Banda"}},
                tema("Mío", "AR5", 200),
                {"title": "De Otro Más", "isrc": "ZZ2", "duration": 190, "artist": {"name": "Tercera Banda"}},
            ],
        ),
    }
    falso = deezer(discos)
    falso.fuera_de_discografia = {30}
    falso.por_titulo = [30]
    mio = track(hacer_track, "Mío", "Compilado de Verano", isrc="AR5", dur=200, fecha="2021-11-15")
    tracks = [_base(hacer_track), mio]
    datos = cruce(10)
    comp = C.revisar(tracks, datos, "Los del Ejemplo")
    assert comp["verificados_por_tracklist"] == 1
    assert (mio["upc"], mio["track_number"]) == ("UPC30", 2)
    assert comp["faltan"] == [], "los temas de otros no cuentan como faltantes del artista"


def test_un_album_que_se_llama_igual_pero_es_de_otro_artista_no_se_usa(hacer_track, deezer):
    """Buscando por título aparece el «Loca» de cualquiera. Si el tema no
    figura a nombre del artista, no es su single aunque dure lo mismo."""
    discos = {
        10: ("Verificado", "album", "2020-01-01", [tema("Base", "AR0")]),
        30: (
            "Loca",
            "single",
            "2021-11-15",
            [{"title": "Loca", "isrc": "ZZ9", "duration": 200, "artist": {"name": "Otra Banda"}}],
        ),
    }
    falso = deezer(discos)
    falso.fuera_de_discografia = {30}
    falso.por_titulo = [30]
    loca = track(hacer_track, "Loca", "Loca", dur=200, fecha="2021-11-15")
    comp = C.revisar([_base(hacer_track), loca], cruce(10), "Los del Ejemplo")
    assert comp["verificados_por_tracklist"] == 0 and not loca["upc"] and not loca["isrc"]


def test_dos_singles_que_se_llaman_igual_van_cada_uno_con_el_suyo(hacer_track, deezer):
    """De un catálogo real: dos «Canción Sin Miedo» en YouTube y dos en
    Deezer. Los dos quedaban con el mismo UPC."""
    discos = {
        10: ("Verificado", "album", "2020-01-01", [tema("Base", "AR0")]),
        20: ("Canción", "single", "2021-03-21", [tema("Canción", "AR1", 156)]),
        21: ("Canción", "single", "2021-03-03", [tema("Canción", "AR1", 156)]),
    }
    deezer(discos)
    primero = track(hacer_track, "Canción", "Canción", isrc="AR1", dur=156, fecha="2021-03-22")
    segundo = track(hacer_track, "Canción", "Canción", isrc="AR1", dur=156, fecha="2021-10-01")
    comp = C.revisar([_base(hacer_track), primero, segundo], cruce(10), "Los del Ejemplo")
    assert comp["verificados_por_tracklist"] == 2
    assert (primero["upc"], segundo["upc"]) == ("UPC20", "UPC21")


def test_un_album_que_ya_es_de_otro_lanzamiento_no_se_toma_por_una_forma_floja(hacer_track, deezer):
    """De un catálogo real: tres singles de remixes terminaban siendo, cada
    uno, el álbum «(Remixes)» entero, que ya era otro lanzamiento del canal."""
    remixes = [tema(f"Tema (Remix {n})", f"AR{n}", 200 + n) for n in range(1, 6)]
    discos = {
        10: ("Verificado", "album", "2020-01-01", [tema("Base", "AR0")]),
        20: ("Tema (Remixes)", "album", "2014-08-04", remixes),
    }
    deezer(discos)
    album = [
        ubicado(
            track(
                hacer_track,
                f"Tema (Remix {n})",
                "Tema (Remixes)",
                isrc=f"AR{n}",
                dur=200 + n,
                aid=20,
                fecha="2014-08-04",
            ),
            n,
        )
        for n in range(1, 6)
    ]
    single = track(hacer_track, "Tema (Remix 2)", "Tema", isrc="AR2", dur=202, fecha="2005-10-28")
    comp = C.revisar([_base(hacer_track), *album, single], cruce(10, 20), "Los del Ejemplo")
    assert comp["verificados_por_tracklist"] == 0 and not single["upc"]


def test_el_mismo_single_entregado_dos_veces_se_separa_por_el_sello(hacer_track, deezer):
    discos = {
        10: ("Verificado", "album", "2020-01-01", [tema("Base", "AR0")]),
        20: ("Canción", "single", "2021-03-21", [tema("Canción", "AR1", 156)]),
        21: ("Canción", "single", "2021-03-03", [tema("Canción", "AR1", 156)]),
    }
    falso = deezer(discos)
    falso.sellos = {20: "Discos del Sur", 21: "Sello"}
    t = track(hacer_track, "Canción", "Canción", isrc="AR1", dur=156, fecha="2021-10-01")
    comp = C.revisar([_base(hacer_track), t], cruce(10), "Los del Ejemplo")
    assert comp["verificados_por_tracklist"] == 1 and t["upc"] == "UPC21", "el del sello que declara YouTube"


def test_con_casi_todo_ubicado_el_tema_que_queda_va_al_lugar_que_queda(hacer_track, deezer):
    """De un catálogo real: cinco de seis temas con su ISRC en el álbum, y el
    sexto figuraba en Deezer con otra duración. El disco se verifica y se
    ordena; a ese tema no se le pone el ISRC, que puede ser de otra grabación."""
    temas = [tema(f"T{n}", f"AR{n}", 200 + n) for n in range(1, 6)] + [tema("Enamorada", "AR6", 85)]
    discos = {
        10: ("Verificado", "album", "2020-01-01", [tema("Base", "AR0")]),
        20: ("Pasión", "ep", "2019-03-22", temas),
    }
    tracks = [track(hacer_track, f"T{n}", "Pasión", dur=200 + n, fecha="2019-03-22") for n in range(1, 6)]
    rara = track(hacer_track, "Enamorada", "Pasión", dur=215, fecha="2019-03-22")
    productos, _comp, _f = _catalogo(hacer_track, deezer, discos, [_base(hacer_track), *tracks, rara])
    disco = productos["Pasión"]
    assert disco["upc"] == "UPC20" and disco["order_unconfirmed"] is False
    assert (rara.get("track_number"), rara["isrc"]) == (6, "")


def test_con_pocos_temas_no_se_ubica_nada_por_descarte(hacer_track, deezer):
    discos = {
        10: ("Verificado", "album", "2020-01-01", [tema("Base", "AR0")]),
        20: ("Pasión", "ep", "2019-03-22", [tema("T1", "AR1", 201), tema("Enamorada", "AR6", 85)]),
    }
    tracks = [
        track(hacer_track, "T1", "Pasión", dur=201, fecha="2019-03-22"),
        track(hacer_track, "Enamorada", "Pasión", dur=215, fecha="2019-03-22"),
    ]
    _p, comp, _f = _catalogo(hacer_track, deezer, discos, [_base(hacer_track), *tracks])
    assert comp["verificados_por_tracklist"] == 0


def test_un_disco_del_que_youtube_muestra_una_parte_se_verifica_por_sus_isrc(hacer_track, deezer):
    """YouTube no repite una grabación que ya tiene en otro disco: de un
    release de tres temas puede mostrar uno, con otra fecha. Si ese tema está
    en el álbum con el ISRC que le encontró el cruce, es el álbum."""
    discos = {
        10: ("Verificado", "album", "2020-01-01", [tema("Base", "AR0")]),
        20: (
            "Tres en Uno",
            "single",
            "2021-05-19",
            [tema("Uno", "AR1", 204), tema("Dos", "AR2", 190), tema("Tres", "AR3", 180)],
        ),
    }
    con_isrc = track(hacer_track, "Uno", "Tres en Uno", isrc="AR1", dur=204, fecha="2021-02-05")
    deezer(discos)
    comp = C.revisar([_base(hacer_track), con_isrc], cruce(10), "Los del Ejemplo")
    assert comp["verificados_por_tracklist"] == 1 and con_isrc["upc"] == "UPC20"

    sin_isrc = track(hacer_track, "Uno", "Tres en Uno", dur=204, fecha="2021-02-05")
    deezer(discos)
    comp = C.revisar([_base(hacer_track), sin_isrc], cruce(10), "Los del Ejemplo")
    assert comp["verificados_por_tracklist"] == 0, "sin el ISRC del cruce, la fecha distinta manda"
