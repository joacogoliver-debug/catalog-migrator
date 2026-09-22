# -*- coding: utf-8 -*-
"""Contrato del orquestador con `relevar_core`. Sin red y sin clave.

Existe por un bug concreto. `relevar_catalogo()` desempaquetaba como tupla el
DICT que devuelve `relevar_core.relevar()`, y tiraba «too many values to unpack»
en cuanto se relevaba de verdad. Ningún test lo agarró porque todos sembraban
los productos directamente, así que la única función que no se podía probar sin
clave era justo la puerta de entrada de la app.

La idea es fijar el CONTRATO. Se reemplaza `relevar_core.relevar` por un doble
que devuelve exactamente la forma real, con las mismas claves, sin tocar la red.
"""

import inspect
import os

import pytest

import migrar_core as M
import relevar_core
from contratos import Diagnostico, Relevamiento

# Las claves que `relevar()` tiene que devolver salen del contrato, no de una
# lista escrita a mano acá. Antes eran catorce cadenas copiadas, que es la forma
# más fácil de que el test y el código se separen sin que nadie se entere:
# agregar una clave al contrato y olvidarla acá no rompía nada.
CLAVES_REALES = set(Relevamiento.__annotations__)


def _track(titulo, album, anio, isrc="", upc="", vid="v1"):
    return {
        "video_id": vid,
        "track": titulo,
        "album": album,
        "distributor": "ONErpm",
        "label": "Sello",
        "release_year": anio,
        "isrc": isrc,
        "upc": upc,
        "match": "",
        "duration_s": 200,
        "views": 100,
        "likes": 1,
        "comments": 0,
        "upload_date": f"{anio}-01-01",
        "desc3": "",
        "url": f"https://youtu.be/{vid}",
    }


TRACKS_FALSOS = [
    _track("Tema A", "Disco", 2020, "ARABC2000001", "036000291452", "a1"),
    _track("Tema B", "Disco", 2020, "ARABC2000002", "036000291452", "a2"),
    _track("Single", "(single / sin álbum)", 2021, "ARABC2100001", "", "b1"),
]


def _respuesta_topic():
    """Lo que devuelve relevar() cuando el canal es un Topic y todo salió bien."""
    return {
        "artist": "Artista Doble",
        "channel_title": "Artista Doble - Topic",
        "tracks": TRACKS_FALSOS,
        "distribs": {"ONErpm": {"videos": 3, "views": 300}},
        "total_views": 300,
        "units": 3,
        "codes": {"isrc": 3, "upc": 2, "matched": 3, "source": "Deezer"},
        "es_topic": True,
        "cobertura_metadata": 1.0,
        "topic_sugerido": None,
        "via_topic": False,
        "canal_pedido": "Artista Doble - Topic",
        "descartados": 0,
    }


def _respuesta_canal_comun():
    """Canal común. Sin metadata, con el Topic sugerido, y simulando el caso en
    que se pegó un OAC y la app relevó su Topic."""
    sin_datos = [
        dict(
            t,
            distributor="(sin datos)",
            album="(single / sin álbum)",
            release_year="",
            label="",
            isrc="",
            upc="",
        )
        for t in TRACKS_FALSOS
    ]
    return {
        "artist": "Artista Doble",
        "channel_title": "Artista Doble",
        "tracks": sin_datos,
        "distribs": {},
        "total_views": 300,
        "units": 3,
        "codes": None,
        "es_topic": False,
        "cobertura_metadata": 0.0,
        "topic_sugerido": {
            "id": "UCxxx",
            "titulo": "Artista Doble - Topic",
            "url": "https://www.youtube.com/channel/UCxxx",
        },
        "via_topic": True,
        "canal_pedido": "Artista Doble Oficial",
        "descartados": 7,
    }


@pytest.fixture
def relevar_doble(monkeypatch):
    """Reemplaza `relevar_core.relevar` y registra con qué lo llamaron.

    Devuelve un dict de control. `escenario` elige qué respuesta dar, `llamadas`
    guarda los argumentos que recibió.
    """
    control = {"escenario": "topic", "llamadas": {}}

    def doble(url, yt_key, with_codes=True, progress=None, use_musicbrainz=False):
        control["llamadas"] = {"url": url, "yt_key": yt_key, "with_codes": with_codes}
        if progress:
            progress("probando el callback", 0.5)
        if control["escenario"] == "topic":
            return _respuesta_topic()
        return _respuesta_canal_comun()

    monkeypatch.setattr(relevar_core, "relevar", doble)
    return control


# ============================================================
# El contrato en sí
# ============================================================


@pytest.mark.parametrize("clave", sorted(CLAVES_REALES))
def test_relevar_sigue_devolviendo_la_clave(clave):
    """Se mira la fuente y no una llamada real, porque relevar() necesita red y
    una clave de YouTube."""
    fuente = inspect.getsource(relevar_core.relevar)
    assert f'"{clave}"' in fuente, "relevar() ya no devuelve esta clave, actualizá migrar_core"


# ============================================================
# relevar_catalogo, el desempaquetado que se rompía
# ============================================================


def test_relevar_catalogo_desempaqueta_bien(relevar_doble):
    prods, artista, tracks, _diag = M.relevar_catalogo("https://www.youtube.com/@Test", "clave-falsa")

    assert artista == "Artista Doble"
    assert len(tracks) == 3
    # Si desempaquetara mal, acá vendrían strings, que son las claves del dict.
    assert all(isinstance(t, dict) for t in tracks)
    assert len(prods) == 2  # Disco + el single
    assert {p["title"] for p in prods} == {"Disco", "Single"}
    assert all(p["artist"] == "Artista Doble" for p in prods)


def test_los_argumentos_llegan_tal_cual(relevar_doble):
    M.relevar_catalogo("https://www.youtube.com/@Test", "clave-falsa")
    assert relevar_doble["llamadas"] == {
        "url": "https://www.youtube.com/@Test",
        "yt_key": "clave-falsa",
        "with_codes": True,
    }


def test_el_callback_de_progreso_llega_y_se_usa(relevar_doble):
    avances = []
    M.relevar_catalogo(
        "https://www.youtube.com/@Test", "clave-falsa", progress=lambda m, f=None: avances.append(m)
    )
    assert "probando el callback" in avances
    assert any("productos" in a for a in avances)


# ============================================================
# Diagnóstico del canal
# ============================================================


def test_diagnostico_de_un_canal_topic(relevar_doble):
    _p, _a, _t, diag = M.relevar_catalogo("https://www.youtube.com/@Test", "clave-falsa")
    assert diag["es_topic"] is True
    assert diag["cobertura_metadata"] == 1.0
    assert diag["topic_sugerido"] is None
    assert diag["via_topic"] is False


def test_diagnostico_de_un_canal_comun(relevar_doble):
    """Lo importante del caso OAC. Que se avise el cambio de canal y lo
    descartado, en vez de que ocurra en silencio."""
    relevar_doble["escenario"] = "comun"
    avisos = []
    prods, _a, _t, diag = M.relevar_catalogo(
        "https://www.youtube.com/@Test", "clave-falsa", progress=lambda m, f=None: avisos.append(m)
    )

    assert diag["es_topic"] is False
    assert diag["via_topic"] is True
    assert diag["canal_pedido"] == "Artista Doble Oficial"
    assert diag["descartados"] == 7
    assert diag["cobertura_metadata"] == 0.0
    assert (diag["topic_sugerido"] or {}).get("titulo") == "Artista Doble - Topic"

    assert any("relev" in a and "Topic" in a for a in avisos)
    assert any("afuera" in a and "7 videos" in a for a in avisos)

    # Sin álbumes declarados, cada track queda como su propio producto. Es el
    # síntoma que ve el usuario, N productos igual a N tracks.
    assert len(prods) == len(TRACKS_FALSOS)


# ============================================================
# Opciones de filtro y flujo completo
# ============================================================


def test_opciones_de_filtro_sobre_lo_relevado(relevar_doble):
    prods, _a, _t, _d = M.relevar_catalogo("https://www.youtube.com/@Test", "clave-falsa")
    op = M.opciones_de_filtro(prods)
    assert op["total"] == 2
    assert op["año_min"] == 2020
    assert op["año_max"] == 2021
    assert op["distribuidoras"][0]["name"] == "ONErpm"


def test_flujo_completo_sin_red_solo_planilla(relevar_doble, tmp_path):
    destino = str(tmp_path / "salida.zip")
    res = M.migrar(
        "https://www.youtube.com/@Test",
        "clave-falsa",
        quiere_planilla=True,
        quiere_portadas=False,
        quiere_audio=False,
        out_path=destino,
        log=lambda *_: None,
    )

    assert res["artista"] == "Artista Doble"
    assert res["productos"] == 2
    assert os.path.exists(res["zip"])
    assert res["bytes"] > 0
    assert res["resumen"]["tracks"] == 3


def test_un_filtro_que_no_deja_nada_es_un_error_mostrable(relevar_doble, tmp_path):
    destino = str(tmp_path / "salida.zip")
    with pytest.raises(relevar_core.RelevarError) as exc:
        M.migrar(
            "https://www.youtube.com/@Test",
            "clave-falsa",
            year_from=2099,
            out_path=destino,
            log=lambda *_: None,
        )
    assert "filtros" in str(exc.value)


def test_el_diagnostico_es_un_subconjunto_del_relevamiento(relevar_doble):
    """`migrar_core` arma el diagnóstico a partir de lo que devuelve `relevar()`.

    Todas sus claves menos `canal` salen de ahí con el mismo nombre. Si el
    contrato de arriba perdiera una, esto se rompe acá en vez de dejar un campo
    vacío en la pantalla.
    """
    propias = set(Diagnostico.__annotations__) - {"canal"}
    assert propias <= set(Relevamiento.__annotations__)

    _p, _a, _t, diag = M.relevar_catalogo("https://www.youtube.com/@Test", "clave-falsa")
    assert set(diag) == set(Diagnostico.__annotations__)
