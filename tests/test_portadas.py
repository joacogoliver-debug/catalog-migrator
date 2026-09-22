# -*- coding: utf-8 -*-
"""Portadas vía iTunes Search API. Sin red.

Lo importante que cubre. Que el estado de la portada reporte la resolución
REAL y no la pedida. Apple sirve el tamaño máximo que tiene y responde 200
aunque sea más chico que el pedido, así que pedir 3000x3000 puede devolver
600x604. Reportar el tamaño pedido haría que la planilla diga que la portada
cumple el mínimo de ingesta cuando en realidad la van a rechazar.
"""

import pytest

import portadas as PT
from conftest import _producto


# ============================================================
# Reescritura de la URL del CDN de Apple
# ============================================================


@pytest.mark.parametrize(
    "url, px, esperado",
    [
        (
            "https://is1-ssl.mzstatic.com/image/thumb/abc/100x100bb.jpg",
            3000,
            "https://is1-ssl.mzstatic.com/image/thumb/abc/3000x3000bb.jpg",
        ),
        (
            "https://is1-ssl.mzstatic.com/image/thumb/abc/500x500bb.jpg",
            2000,
            "https://is1-ssl.mzstatic.com/image/thumb/abc/2000x2000bb.jpg",
        ),
        # Entra .png y sale .jpg, que es lo que el CDN sirve para ese nombre.
        (
            "https://is1-ssl.mzstatic.com/image/thumb/abc/100x100bb.png",
            1200,
            "https://is1-ssl.mzstatic.com/image/thumb/abc/1200x1200bb.jpg",
        ),
        ("", 3000, ""),
    ],
)
def test_upscale_de_la_url(url, px, esperado):
    assert PT._upscale(url, px) == esperado


# ============================================================
# Limpieza de títulos antes de buscar
# ============================================================


@pytest.mark.parametrize(
    "titulo, limpio",
    [
        ("Tema (Official Video)", "Tema"),
        ("Album [Remastered 2011]", "Album"),
        ("Disco (En Vivo)", "Disco"),
        ("Bocanada", "Bocanada"),
        # No debe comerse paréntesis que son parte del título.
        ("Cosquillas (feat. Alguien)", "Cosquillas (feat. Alguien)"),
    ],
)
def test_strip_ruido(titulo, limpio):
    assert PT._strip_ruido(titulo) == limpio


# ============================================================
# El estado reporta la resolución real
# ============================================================


@pytest.fixture
def portada_de(monkeypatch, jpeg):
    """Devuelve una función que corre `fetch_portadas` con una resolución dada.

    Reemplaza la búsqueda y la descarga para no tocar la red. Va por
    `monkeypatch` y no por asignación directa para que los parches se deshagan
    al terminar el test, aunque falle.
    """
    monkeypatch.setattr(
        PT,
        "buscar_portada",
        lambda artista, album, upc="": {
            "url100": "https://x/100x100bb.jpg",
            "matched_album": album,
            "matched_artist": artista,
            "match": "alta",
            "ratio": 1.0,
        },
    )

    def correr(px_real, no_cuadrada=False):
        alto = px_real + 4 if no_cuadrada else px_real
        monkeypatch.setattr(
            PT, "descargar_portada", lambda url100: (jpeg(px_real, alto, relleno=200), min(px_real, alto))
        )
        p = _producto(title="Disco", cover_status="")
        PT.fetch_portadas([p], "Artista", log=lambda *_: None)
        return p

    return correr


def test_cuando_apple_tiene_3000_el_estado_dice_3000(portada_de):
    """Caso real de Radiohead."""
    p = portada_de(3000)
    assert (p.get("cover_status") or "").startswith("3000x3000")
    assert p.get("cover_px") == 3000


def test_cuando_apple_tiene_menos_el_estado_no_miente(portada_de):
    """Caso real de Daft Punk. Pedimos 3000, Apple tiene 1500. Entra en ingesta
    pero el estado tiene que decir 1500."""
    p = portada_de(1500)
    estado = p.get("cover_status") or ""
    assert "1500x1500" in estado
    assert "3000" not in estado


def test_debajo_del_minimo_de_ingesta_se_avisa(portada_de):
    """Caso real de Cerati, 600x604. Debajo del mínimo y además no cuadrada."""
    p = portada_de(600, no_cuadrada=True)
    estado = p.get("cover_status") or ""
    assert "DEBAJO DEL MINIMO" in estado
    assert "3000" not in estado


def test_el_minimo_exacto_no_dispara_el_aviso(portada_de):
    p = portada_de(PT.COVER_MIN_INGESTA)
    assert "DEBAJO DEL MINIMO" not in (p.get("cover_status") or "")


def test_descarga_fallida(monkeypatch):
    monkeypatch.setattr(
        PT,
        "buscar_portada",
        lambda artista, album, upc="": {
            "url100": "https://x/100x100bb.jpg",
            "matched_album": album,
            "matched_artist": artista,
            "match": "alta",
            "ratio": 1.0,
        },
    )
    monkeypatch.setattr(PT, "descargar_portada", lambda url100: (None, 0))

    p = _producto(title="Disco", cover_status="")
    PT.fetch_portadas([p], "Artista", log=lambda *_: None)
    assert "falló la descarga" in (p.get("cover_status") or "")
    assert p.get("cover_bytes") is None


def test_sin_match_en_itunes(monkeypatch):
    monkeypatch.setattr(PT, "buscar_portada", lambda artista, album, upc="": None)

    p = _producto(title="Disco Inexistente", cover_status="")
    PT.fetch_portadas([p], "Artista", log=lambda *_: None)
    assert "no está en Apple Music" in (p.get("cover_status") or "")
    assert p.get("cover_bytes") is None
