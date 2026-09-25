# -*- coding: utf-8 -*-
"""El número de disco y de track. Sin red.

YouTube no expone el orden, y la hoja de ingesta llevaba el estimado por fecha
de subida sin ninguna marca, con el disco fijo en 1. Deezer sí tiene el
tracklist real del álbum, y la app ya lo bajaba y lo tiraba. Cubre:

  - el tracklist de Deezer, de uno o de varios discos
  - dónde cae cada tema, sin adivinar entre dos candidatos
  - que el orden real valga sólo si está para todo el release
  - que un tema que Deezer no encontró igual se ubique con sus compañeros
  - que dos releases que se llaman igual pero salieron en otra fecha no se crucen
  - lo que la hoja dice de todo esto
"""

import csv
import io

import pytest

from conftest import _track
from migrador import paquete as pq
from migrador import productos as P
from migrador import relevar_core as R


def _album(*titulos, aid=10, upc="036000291452", titulo="Disco", fecha="2020-03-01"):
    return {
        aid: {
            "upc": upc,
            "title": titulo,
            "release_date": fecha,
            "record_type": "album",
            "nb_tracks": len(titulos),
            "tracks": [{"id": 100 + i, "title": t} for i, t in enumerate(titulos)],
        }
    }


def test_tracklist_de_un_solo_disco_pide_un_solo_track(monkeypatch):
    pedidos = []

    def deezer(path):
        pedidos.append(path)
        return {"disk_number": 1, "track_position": 3}

    monkeypatch.setattr(R, "_deezer_json", deezer)
    lista = R.tracklist_deezer(_album("A", "B", "C")[10])
    assert lista == [("A", 1, 1), ("B", 2, 1), ("C", 3, 1)]
    assert pedidos == ["track/102"]


def test_tracklist_de_dos_discos_numera_por_disco(monkeypatch):
    datos = {"track/100": (1, 1), "track/101": (2, 1), "track/102": (1, 2)}
    monkeypatch.setattr(
        R, "_deezer_json", lambda path: {"track_position": datos[path][0], "disk_number": datos[path][1]}
    )
    assert R.tracklist_deezer(_album("A", "B", "C")[10]) == [("A", 1, 1), ("B", 2, 1), ("C", 1, 2)]


def test_un_tracklist_de_varios_discos_incompleto_no_sirve(monkeypatch):
    datos = {
        "track/100": {"track_position": 1, "disk_number": 1},
        "track/101": {},
        "track/102": {"disk_number": 2},
    }
    monkeypatch.setattr(R, "_deezer_json", lambda path: datos[path])
    assert R.tracklist_deezer(_album("A", "B", "C")[10]) == []


def test_un_tema_se_ubica_sin_adivinar():
    lista = [("Uno", 1, 1), ("Dos", 2, 1), ("Dos", 3, 1), ("Uno (En Vivo)", 4, 1)]
    assert R._posicion_en(lista, "Uno") == (1, 1)
    assert R._posicion_en(lista, "Uno (En Vivo)") == (4, 1)
    assert R._posicion_en(lista, "Dos") is None  # dos candidatos: no se elige
    assert R._posicion_en(lista, "Tres") is None


@pytest.fixture
def deezer_con_album(monkeypatch):
    """Tres temas del disco. Deezer encuentra los dos primeros en el álbum y el
    tercero no lo encuentra, que es lo que pasa con datos reales."""

    def match(t, artist):
        return ("", None, "") if t["track"] == "Tres" else (f"ARAAA20000{t['track'][:1]}", 10, "alta")

    monkeypatch.setattr(R, "deezer_match", match)
    monkeypatch.setattr(R, "deezer_albumes", lambda ids: _album("Uno", "Dos", "Tres"))
    monkeypatch.setattr(R, "_deezer_json", lambda path: {"disk_number": 1})


def _disco(*titulos):
    return [
        _track(t, album="Disco", year=2020, released="2020-03-01", vid=t, date=f"2020-0{i + 1}-01")
        for i, t in enumerate(titulos)
    ]


def test_con_el_tracklist_verificado_el_orden_es_el_real(deezer_con_album):
    # Subidos en otro orden que el del disco: el estimado daría Tres, Dos, Uno.
    tracks = _disco("Tres", "Dos", "Uno")
    R.enrich_with_codes(tracks, "Fulano", log=lambda *_: None)
    p = P.group_products(tracks)[0]
    assert [(t["track"], t.get("track_number"), t.get("disc_number")) for t in p["tracks"]] == [
        ("Uno", 1, 1),
        ("Dos", 2, 1),
        ("Tres", 3, 1),
    ]
    assert p["order_unconfirmed"] is False


def test_un_orden_a_medias_no_se_da_por_confirmado(deezer_con_album, monkeypatch):
    monkeypatch.setattr(R, "deezer_albumes", lambda ids: _album("Uno", "Dos", "Otro"))
    tracks = _disco("Uno", "Dos", "Tres")
    R.enrich_with_codes(tracks, "Fulano", log=lambda *_: None)
    p = P.group_products(tracks)[0]
    assert p["order_unconfirmed"] is True
    assert [t.get("track_number") for t in p["tracks"]] == [1, 2, 3]
    assert not any(t.get("disc_number") for t in p["tracks"])


def test_la_misma_obra_en_otra_fecha_no_presta_su_tracklist():
    """La edición aniversario se llama igual que el original de diez años
    antes: por el título solo, sus temas se quedaban con el UPC del original."""
    assert not R.album_coincide("Disco", "Disco", "2023-05-12", "2013-05-17")
    assert R.album_coincide("Disco", "Disco", "2023-05-12", "2023-05-11")
    assert R.album_coincide("Disco", "Disco", "", "2013-05-17")


def test_temas_sin_fecha_ubicados_en_el_mismo_album_son_un_release():
    uno = _track("Uno", album="Single", year=2001, vid="a")
    dos = _track("Uno (Edit)", album="Single", year=2021, vid="b")
    for t, n in ((uno, 2), (dos, 1)):
        t.update(album_deezer_id=77, orden_fuente="deezer", track_number=n, disc_number=1)
    ps = P.group_products([uno, dos])
    assert len(ps) == 1
    assert [t["track"] for t in ps[0]["tracks"]] == ["Uno (Edit)", "Uno"]


def _hoja(productos):
    return list(csv.DictReader(io.StringIO(pq.hoja_ingesta_csv(productos, "Fulano"))))


def test_la_hoja_dice_de_donde_sale_el_orden_y_no_inventa_disco_ni_territorios(deezer_con_album):
    confirmado = _disco("Uno", "Dos", "Tres")
    R.enrich_with_codes(confirmado, "Fulano", log=lambda *_: None)
    estimado = [_track(t, album="Otro", year=2019, vid="x" + t) for t in ("A", "B")]
    single = [_track("Suelto", year=2018, vid="s")]
    filas = _hoja(P.group_products(confirmado + estimado + single))

    por_titulo = {f["Track Title"]: f for f in filas}
    assert por_titulo["Uno"]["Track Order"] == "confirmed (Deezer)"
    assert por_titulo["Uno"]["Disc Number"] == "1"
    assert por_titulo["A"]["Track Order"] == "estimated"
    assert por_titulo["A"]["Disc Number"] == pq.MARCA_COMPLETAR
    assert por_titulo["Suelto"]["Track Order"] == "confirmed"
    assert por_titulo["Suelto"]["Disc Number"] == "1"
    assert all(f["Territories"] == pq.MARCA_COMPLETAR for f in filas)
