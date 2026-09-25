# -*- coding: utf-8 -*-
"""Los nombres adentro del ZIP. Sin red.

Un ZIP que se descomprime mal falla en la máquina de otro, que es el peor lugar
para enterarse. Cubre:

  - que el UPC no pueda sacar una carpeta de la raíz
  - que dos productos no compartan carpeta, ni aun con títulos no latinos
  - que ninguna ruta pase el presupuesto de largo de Windows
  - que el armado se niegue a escribir una entrada insegura
"""

import zipfile

import pytest

from conftest import _producto, _track
from migrador import paquete as pq
from migrador import productos as pr


def test_del_upc_entran_solo_los_digitos():
    carpeta = pr.folder_name({"release_year": 2020, "title": "Disco", "upc": "../../../../../evil"})
    assert carpeta == "2020 - Disco"
    assert (
        pr.folder_name({"release_year": 2020, "title": "Disco", "upc": "0 1234-5678"})
        == "2020 - Disco [012345678]"
    )


def test_dos_singles_con_el_mismo_nombre_no_comparten_carpeta():
    tracks = [
        _track("Intro", year=2021, vid="a"),
        _track("intro", year=2021, vid="b"),
        _track("INTRO", year=2021, vid="c"),
    ]
    carpetas = [p["folder"] for p in pr.group_products(tracks)]
    assert len({c.casefold() for c in carpetas}) == 3, carpetas


def test_los_titulos_no_latinos_tampoco_se_pisan():
    """Al pasar a ASCII quedan todos en «Sin titulo»: eran tres entradas iguales."""
    tracks = [_track(t, year=2020, vid=v) for t, v in (("夜に駆ける", "a"), ("群青", "b"), ("怪物", "c"))]
    carpetas = sorted(p["folder"] for p in pr.group_products(tracks))
    assert carpetas == ["2020 - Sin titulo", "2020 - Sin titulo (2)", "2020 - Sin titulo (3)"]


def test_dos_albumes_que_difieren_despues_del_corte_tampoco():
    largo = "A" * 70
    tracks = [
        _track("t1", album=largo + " uno", year=2020, vid="a"),
        _track("t2", album=largo + " dos", year=2020, vid="b"),
    ]
    carpetas = [p["folder"] for p in pr.group_products(tracks)]
    assert carpetas[0] != carpetas[1]


@pytest.mark.parametrize("parte", ["..", ".", "", "a/b", "2020 - Disco [../../evil]", "a\\b"])
def test_una_entrada_insegura_no_se_escribe(parte):
    with pytest.raises(ValueError):
        pq.entrada_zip("Artista - Migracion", parte, "datos.xlsx")


def test_el_armado_se_niega_si_una_carpeta_se_sale(productos_entregable, tmp_path):
    productos_entregable[0]["folder"] = "../fuera"
    with pytest.raises(ValueError):
        pq.build_zip(productos_entregable, "Artista", str(tmp_path / "x.zip"), log=lambda *_: None)


def test_ninguna_ruta_pasa_el_presupuesto_ni_se_repite(tmp_path):
    """El peor caso: artista, disco y tema larguísimos, UPC de 13 dígitos y un
    audio lossy, que lleva la marca más larga. Antes daba 294 caracteres."""
    audio = tmp_path / "a.m4a"
    audio.write_bytes(b"x")
    tracks = []
    for n in (1, 2):
        t = _track("T" * 150 + str(n), album="D" * 150, year=2020, vid=f"v{n}", upc="0886443919259")
        t.update(track_number=n, audio_path=str(audio), audio_format=".m4a")
        tracks.append(t)
    productos = pr.group_products(tracks, "Artista " + "X" * 150)

    destino = tmp_path / "peor.zip"
    pq.build_zip(productos, "Artista " + "X" * 150, str(destino), log=lambda *_: None)
    nombres = zipfile.ZipFile(destino).namelist()

    assert max(len(n) for n in nombres) <= pq.LARGO_MAX_RUTA
    assert len(nombres) == len(set(nombres))
    audios = [n for n in nombres if n.endswith(".m4a")]
    assert len(audios) == 2
    # La marca de lossy y el número de track nunca se recortan.
    assert all(pq.T("paq.tag_lossy") in n for n in audios)
    assert sorted(n.rsplit("/", 1)[1][:2] for n in audios) == ["01", "02"]


def test_un_nombre_corto_no_se_recorta():
    t = {"track": "Tema", "track_number": 3, "audio_format": ".flac"}
    assert pq.nombre_audio(t) == "03 - Tema.flac"


def test_el_producto_de_ejemplo_sigue_con_su_carpeta():
    p = _producto(title="Mi Album", upc="123", year=2019)
    assert pr.asignar_carpetas([p])[0]["folder"] == "2019 - Mi Album [123]"
