# -*- coding: utf-8 -*-
"""La línea ℗ y el sello. Sin red.

La columna Label llevaba todo lo que seguía al año en la línea ℗, licencia
incluida, y la P Line se armaba con el año del release, que no es el del ℗: una
edición de 2023 con grabaciones de ℗ 2013 salía con un ℗ que no es. Cubre, con
las formas reales que publica YouTube:

  - la P Line entera, tal como vino
  - el titular sin la licencia, también en líneas con más de un ℗
  - que el relleno de DistroKid siga sin contar como sello
"""

import csv
import io

import pytest

from conftest import _producto, _track
from migrador import paquete as pq
from migrador import productos as P
from migrador import relevar_core as R


def _desc(linea):
    return f"Provided to YouTube by X\n\nTema · Artista\n\nDisco\n\n{linea}\n\nReleased on: 2023-05-12"


@pytest.mark.parametrize(
    "linea, sello",
    [
        ("℗ 2023 Sello Chico", "Sello Chico"),
        (
            "℗ 2023 Daft Life Limited under exclusive license to Columbia Records, "
            "a Division of Sony Music Entertainment",
            "Daft Life Limited",
        ),
        ("℗ 2020 Sello Chico, a division of Otro Grupo", "Sello Chico"),
        ("℗ 2020 Sello Chico bajo licencia exclusiva de Grande", "Sello Chico"),
        # La línea real con dos ℗: el sello salía «℗ Distributed exclusively by…».
        (
            "℗ 2021 ℗ Distributed exclusively by Warner Music France / ADA France, ℗ 2001 Daft Life Ltd.",
            "Daft Life Ltd.",
        ),
        ("℗ 5358533 Records DK", None),  # el relleno de DistroKid
        ("℗ 2023", None),
    ],
)
def test_el_sello_es_el_titular_sin_la_licencia(linea, sello):
    assert R.parse_description(_desc(linea))["label"] == sello


def test_la_p_line_va_entera_como_vino():
    linea = "℗ 2013 Daft Life Limited under exclusive license to Columbia Records"
    r = R.parse_description(_desc(linea))
    assert r["p_line"] == linea
    assert r["release_year"] == 2013


def test_sin_linea_p_no_hay_p_line():
    assert R.parse_description("Provided to YouTube by X\n\nTema · A")["p_line"] is None


def test_la_hoja_lleva_la_linea_p_del_release_y_no_una_armada_con_su_anio():
    """Una edición de 2023 con grabaciones de ℗ 2013: el ℗ es el de la línea."""
    tracks = [
        _track(n, album="Disco", year=2013, released="2023-05-12", vid=n, label="Sello")
        for n in ("Uno", "Dos")
    ]
    for t in tracks:
        t["p_line"] = "℗ 2013 Sello under exclusive license to Grande"
    p = P.group_products(tracks)[0]
    assert p["release_year"] == 2023
    fila = next(csv.DictReader(io.StringIO(pq.hoja_ingesta_csv([p], "Fulano"))))
    assert fila["P Line"] == "℗ 2013 Sello under exclusive license to Grande"
    assert fila["Label"] == "Sello"


def test_sin_linea_p_la_hoja_pide_completarla():
    p = _producto(title="Disco", tracks=[_track("Uno")])
    p["p_line"] = ""
    fila = next(csv.DictReader(io.StringIO(pq.hoja_ingesta_csv([p], "Fulano"))))
    assert fila["P Line"] == pq.MARCA_COMPLETAR
