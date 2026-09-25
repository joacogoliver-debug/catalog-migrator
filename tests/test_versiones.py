# -*- coding: utf-8 -*-
"""Versiones de una grabación: vivo, remix, remaster. Sin red.

Una versión en vivo es otra grabación, con su propio ISRC, y un álbum en vivo es
otro release, con su propia portada. La búsqueda en Deezer y en iTunes limpiaba
del título justo lo que dice qué versión es, y el vivo terminaba con el código y
la portada del de estudio, con confianza alta. Cubre:

  - qué marcas de versión se leen de un título, y dónde se buscan
  - que Deezer no le dé a una versión el ISRC de otra
  - que la confianza media exija la duración
  - que un artista vacío no cuente como coincidencia
  - que iTunes no le dé a un disco en vivo la portada del de estudio
"""

from typing import Any

import pytest

from migrador import portadas as PT
from migrador import relevar_core as R
from migrador.texto import marcas_version


@pytest.mark.parametrize(
    "titulo, marcas",
    [
        ("Tema", set()),
        ("Tema (En Vivo)", {"vivo"}),
        ("Tema [Live]", {"vivo"}),
        ("Tema - Live at Wembley", {"vivo"}),
        ("Tema (2011 Remaster)", {"remaster"}),
        ("Tema - Remastered 2011", {"remaster"}),
        ("Tema (Oliver Heldens Remix)", {"remix"}),
        ("Tema [Extended Mix]", {"remix", "extendida"}),
        ("Tema (Versión Acústica)", {"acustico"}),
        ("Tema (Sped Up)", {"acelerado"}),
        ("Veridis Quo (Edit)", {"edit"}),
        ("Tema (feat. Otra)", set()),
        # La palabra en el título mismo no es una versión.
        ("Live Forever", set()),
        ("Mix de Verano", set()),
        ("", set()),
        (None, set()),
    ],
)
def test_marcas_de_version(titulo, marcas):
    assert marcas_version(titulo) == frozenset(marcas)


# ============================================================
# Deezer
# ============================================================

# `Any` porque son respuestas de Deezer de mentira, que se completan abajo.
ESTUDIO: dict[str, Any] = {
    "id": 1,
    "title": "Tema",
    "isrc": "ARAAA2000001",
    "artist": {"name": "Fulano"},
    "duration": 200,
}
VIVO: dict[str, Any] = {
    "id": 2,
    "title": "Tema (En Vivo)",
    "isrc": "ARAAA2100002",
    "artist": {"name": "Fulano"},
    "duration": 245,
}
REMIX: dict[str, Any] = {
    "id": 3,
    "title": "Tema (Oliver Remix)",
    "isrc": "ARAAA2200003",
    "artist": {"name": "Fulano"},
    "duration": 200,
}
for c in (ESTUDIO, VIVO, REMIX):
    c["album"] = {"id": c["id"] * 10}


@pytest.fixture
def deezer(monkeypatch):
    """Deezer devuelve los candidatos que se le pasen, sin red."""

    def poner(*candidatos):
        monkeypatch.setattr(R, "_deezer_json", lambda path: {"data": list(candidatos)})

    return poner


def test_el_vivo_se_queda_con_el_isrc_del_vivo(deezer):
    """Verificado a mano al auditar: con los dos candidatos, el vivo se quedaba
    con el ISRC de estudio, con confianza media."""
    deezer(ESTUDIO, VIVO)
    isrc, _album, _conf = R.deezer_match({"track": "Tema (En Vivo)", "duration_s": 245}, "Fulano")
    assert isrc == "ARAAA2100002"


def test_si_deezer_solo_tiene_el_de_estudio_el_vivo_queda_sin_codigo(deezer):
    """Ante la duda, código en blanco: un hueco se ve, un código ajeno no."""
    deezer(ESTUDIO)
    assert R.deezer_match({"track": "Tema (En Vivo)", "duration_s": 245}, "Fulano") == ("", None, "")


def test_un_remix_no_se_queda_con_el_isrc_del_original(deezer):
    deezer(ESTUDIO, REMIX)
    isrc, _album, _conf = R.deezer_match({"track": "Tema (Oliver Remix)", "duration_s": 200}, "Fulano")
    assert isrc == "ARAAA2200003"
    deezer(ESTUDIO)
    assert R.deezer_match({"track": "Tema (Oliver Remix)", "duration_s": 200}, "Fulano")[0] == ""


def test_el_original_no_se_queda_con_el_de_una_version(deezer):
    deezer(VIVO, REMIX)
    assert R.deezer_match({"track": "Tema", "duration_s": 200}, "Fulano")[0] == ""


def test_el_mismo_remaster_escrito_distinto_si_coincide(deezer):
    remaster = dict(ESTUDIO, title="Tema - Remastered 2011", isrc="ARAAA1100009")
    deezer(remaster)
    isrc, _album, conf = R.deezer_match({"track": "Tema (2011 Remaster)", "duration_s": 200}, "Fulano")
    assert isrc == "ARAAA1100009" and conf


def test_el_ruido_de_youtube_se_sigue_limpiando(deezer):
    deezer(ESTUDIO)
    isrc, _album, _conf = R.deezer_match({"track": "Tema (Official Video)", "duration_s": 200}, "Fulano")
    assert isrc == "ARAAA2000001"


def test_la_confianza_media_exige_la_duracion():
    assert R._confidence(0.80, True, False) == ""
    assert R._confidence(0.80, True, None) == "media"
    assert R._confidence(0.95, True, True) == "alta"


def test_un_artista_vacio_no_cuenta_como_coincidencia():
    _score, _ratio, artist_ok, _dur = R._match_score("Tema", "Fulano", 200, "Tema", "", 200)
    assert artist_ok is False


# ============================================================
# iTunes
# ============================================================


def _itunes(monkeypatch, *discos):
    resultados = [
        {
            "collectionName": d,
            "artistName": "Fulano",
            "artworkUrl100": f"https://is1-ssl.mzstatic.com/{i}/100x100bb.jpg",
        }
        for i, d in enumerate(discos)
    ]
    monkeypatch.setattr(PT, "_http_json", lambda url, retries=3: {"results": resultados})


def test_el_disco_en_vivo_recibe_su_portada(monkeypatch):
    _itunes(monkeypatch, "Gira 2019", "Gira 2019 (En Vivo)")
    info = PT.buscar_portada("Fulano", "Gira 2019 (En Vivo)")
    assert info is not None
    assert info["matched_album"] == "Gira 2019 (En Vivo)"


def test_sin_la_version_en_vivo_no_se_usa_la_de_estudio(monkeypatch):
    _itunes(monkeypatch, "Gira 2019")
    assert PT.buscar_portada("Fulano", "Gira 2019 (En Vivo)") is None


def test_el_single_de_itunes_sigue_encontrandose(monkeypatch):
    """iTunes le agrega « - Single» al nombre, que no es una marca de versión."""
    _itunes(monkeypatch, "Tema - Single")
    info = PT.buscar_portada("Fulano", "Tema")
    assert info is not None


def test_dos_partes_de_un_tema_no_se_confunden(deezer):
    """Comparar sin decorado sólo vale entre dos versiones marcadas iguales: sin
    marca, «(Parte 1)» y «(Parte 2)» son dos temas distintos."""
    parte2 = dict(ESTUDIO, title="Tema (Parte 2)", isrc="ARAAA2000022")
    deezer(parte2)
    assert R.deezer_match({"track": "Tema (Parte 1)", "duration_s": 200}, "Fulano")[0] == ""


def test_el_volumen_2_no_recibe_la_portada_del_1(monkeypatch):
    _itunes(monkeypatch, "Grandes Éxitos Vol. 1")
    assert PT.buscar_portada("Fulano", "Grandes Éxitos Vol. 2") is None
    _itunes(monkeypatch, "Grandes Éxitos Vol. 1", "Grandes Éxitos Vol. 2")
    info = PT.buscar_portada("Fulano", "Grandes Éxitos Vol. 2")
    assert info is not None and info["matched_album"].endswith("2")
