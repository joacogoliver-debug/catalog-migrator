# -*- coding: utf-8 -*-
"""El UPC de cada producto. Sin red.

Deezer encuentra la grabación, y la misma grabación está en el single, en el
álbum y en cada compilado: el álbum que trae el resultado es el de cualquiera de
ellos. Su UPC terminaba en el producto sin preguntar, y un single quedaba con el
UPC del álbum (y, como la portada se busca por UPC, con su tapa). Cubre:

  - cuándo un álbum de Deezer es el release del producto
  - que el UPC de otro release quede en blanco, con la explicación
  - que la validación diga por qué no hay UPC, y avise si se mezclan
"""

import pytest

from conftest import _producto, _track
from migrador import productos as P
from migrador import relevar_core as R
from migrador import validar as V


@pytest.mark.parametrize(
    "producto, deezer, coincide",
    [
        ("Random Access Memories", "Random Access Memories", True),
        ("Disco", "disco", True),
        ("Corazón Roto", "Corazon Roto", True),
        ("Tema (feat. Otra)", "Tema", True),
        ("Tema", "Tema - Single", True),
        ("Tema", "Tema - EP", True),
        # Otro release, aunque comparta temas.
        ("Tema", "Disco Grande", False),
        ("Disco", "Disco (Deluxe)", False),
        ("Gira (En Vivo)", "Gira", False),
        ("Grandes Éxitos Vol. 1", "Grandes Éxitos Vol. 2", False),
        ("", "Disco", False),
        ("Disco", "", False),
    ],
)
def test_cuando_el_album_de_deezer_es_el_release(producto, deezer, coincide):
    assert R.album_coincide(producto, deezer) is coincide


@pytest.fixture
def deezer_falso(monkeypatch):
    """El single y el track del álbum encuentran la misma grabación, y Deezer la
    devuelve en el álbum para los dos: es exactamente el caso real."""
    monkeypatch.setattr(R, "deezer_match", lambda t, artist: ("ARAAA2000001", 10, "alta"))
    monkeypatch.setattr(
        R,
        "deezer_albumes",
        lambda ids: {10: {"upc": "036000291452", "title": "Disco Grande", "nb_tracks": 10, "tracks": []}},
    )


def test_el_single_no_se_queda_con_el_upc_del_album(deezer_falso):
    single = _track("Tema", year=2020, vid="a")
    del_album = _track("Tema", album="Disco Grande", year=2021, vid="b")
    R.enrich_with_codes([single, del_album], "Fulano", log=lambda *_: None)

    assert del_album["upc"] == "036000291452"
    assert single["upc"] == ""
    assert single.get("upc_descartado") == "Disco Grande"
    # El ISRC sí se conserva: es la misma grabación.
    assert single["isrc"] == del_album["isrc"] == "ARAAA2000001"


def test_la_validacion_dice_por_que_no_hay_upc(deezer_falso):
    single = _track("Tema", year=2020, vid="a")
    R.enrich_with_codes([single], "Fulano", log=lambda *_: None)
    res = V.validar(P.group_products([single], "Fulano"))
    cods = [h["codigo"] for h in res["hallazgos"]]
    assert "upc_no_verificado" in cods
    assert "upc_falta" not in cods
    msj = next(h["mensaje"] for h in res["hallazgos"] if h["codigo"] == "upc_no_verificado")
    assert "Disco Grande" in msj


def test_un_producto_con_upc_mezclados_se_avisa():
    p = _producto(
        title="Disco",
        upc="036000291452",
        tracks=[_track("Uno", upc="036000291452"), _track("Dos", upc="4006381333931")],
    )
    hallazgos = V.validar([p])["hallazgos"]
    mezcla = [h for h in hallazgos if h["codigo"] == "upc_mezclado"]
    assert [h["nivel"] for h in mezcla] == ["aviso"]


def test_sin_upc_descartado_sigue_siendo_la_falta_comun():
    cods = [h["codigo"] for h in V.validar([_producto(title="Disco", upc="")])["hallazgos"]]
    assert "upc_falta" in cods and "upc_no_verificado" not in cods


@pytest.mark.parametrize(
    "deezer, fecha_deezer, coincide",
    [
        # El caso real: YouTube no nombra la edición aniversario y Deezer sí.
        ("Random Access Memories (10th Anniversary Edition)", "2023-05-12", True),
        # La misma edición con otra fecha es la reedición de otro release.
        ("Random Access Memories (10th Anniversary Edition)", "2013-05-17", False),
        # Deluxe nunca entra por acá, aunque salga el mismo día.
        ("Random Access Memories (Deluxe Edition)", "2023-05-12", False),
    ],
)
def test_una_edicion_que_youtube_no_nombra_entra_con_la_misma_fecha(deezer, fecha_deezer, coincide):
    assert R.album_coincide("Random Access Memories", deezer, "2023-05-12", fecha_deezer) is coincide


def test_sin_fecha_del_producto_la_edicion_no_entra():
    assert not R.album_coincide("Disco", "Disco (Anniversary Edition)", "", "2023-05-12")
