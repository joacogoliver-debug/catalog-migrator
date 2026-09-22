# -*- coding: utf-8 -*-
"""Configuración compartida de la suite.

Tres cosas que antes repetía cada archivo de test, una por una.

  1. **El idioma.** Se fija en castellano antes de que nada importe `i18n`.
     Sin esto, los tests que comparan mensajes salían en el idioma del sistema
     de quien los corra, y en un CI con locale en inglés fallaban sin motivo.

  2. **El `sys.path`.** Los módulos viven en la raíz y el backend en `app/`.
     Cada test hacía su propio `sys.path.insert`, y algunos además cargaban los
     módulos por ruta con `importlib` para tener una instancia fresca. Con un
     único punto de entrada alcanza con importarlos normal, y el aislamiento lo
     da `monkeypatch`, que además deshace los parches solo.

  3. **Las fixtures del catálogo de ejemplo.** El mismo catálogo inventado
     estaba escrito cuatro veces con variaciones mínimas. Ahora está una vez.
"""

import os
import sys

# Antes de cualquier import del proyecto: `i18n` resuelve el idioma al
# importarse y la variable le gana a todo lo demás.
os.environ.setdefault("MIGRADOR_IDIOMA", "es")

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (RAIZ, os.path.join(RAIZ, "app")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pytest

import i18n
import productos as P
from contratos import Producto, TipoProducto, Track


# ============================================================
# Idioma
# ============================================================


@pytest.fixture(autouse=True)
def idioma_castellano():
    """Deja el idioma en castellano antes y después de cada test.

    Es `autouse` porque el idioma es estado global de un módulo, y un test que
    lo cambia y se cae a la mitad contaminaría a todos los que vengan detrás.
    """
    i18n.poner_idioma("es")
    yield
    i18n.poner_idioma("es")


# ============================================================
# Catálogo de ejemplo
# ============================================================


def _track(
    track,
    album="",
    year: "int | str" = "",
    dist="ONErpm",
    label="Sello",
    upc="",
    isrc="",
    date=None,
    vid=None,
    dur=200,
):
    """Un track con la forma exacta que devuelve `relevar_core.build_tracks`.

    Si esta forma cambia, los tests que la usan tienen que enterarse acá y no
    en diez lugares distintos.
    """
    anio = year or 2020
    t: Track = {
        "video_id": vid or f"v{abs(hash((track, album, year))) % 100000}",
        "track": track,
        "album": album or P.SIN_ALBUM,
        "distributor": dist,
        "label": label,
        "release_year": year,
        "isrc": isrc,
        "upc": upc,
        "match": "",
        "duration_s": dur,
        "views": 100,
        "likes": 1,
        "comments": 0,
        "upload_date": date or f"{anio}-01-01",
        "desc3": "",
        "url": f"https://youtu.be/{vid or 'x'}",
    }
    return t


def _producto(
    title="Disco",
    upc="",
    year: "int | str" = 2020,
    label="Sello",
    tracks=None,
    cover=None,
    orden_ok=True,
    cover_status="ok",
    kind: TipoProducto = "album",
) -> Producto:
    """Un producto con TODAS las claves que declara el contrato.

    Completo a propósito, aunque un test mire dos campos. Un doble a medio
    armar deja pasar código que lee una clave que en producción existe y en
    el test no, y ese es justamente el error que el contrato tipado evita.
    """
    ts: list[Track] = list(tracks or [])
    p: Producto = {
        "product_id": "p001",
        "title": title,
        "kind": kind,
        "artist": "Artista Test",
        "release_year": year,
        "release_date": f"{year or 2020}-01-01",
        "label": label,
        "distributor": "ONErpm",
        "upc": upc,
        "tracks": ts,
        "track_count": len(ts),
        "total_views": sum(int(t.get("views") or 0) for t in ts),
        "order_unconfirmed": not orden_ok,
        "folder": f"{year or 's-f'} - {title}",
        "cover_bytes": cover,
        "cover_status": cover_status,
    }
    return p


@pytest.fixture
def hacer_producto():
    """Fábrica de productos completos, para los tests que no relevan nada."""
    return _producto


@pytest.fixture
def hacer_track():
    """Fábrica de tracks, para los tests que arman catálogos a medida."""
    return _track


@pytest.fixture
def tracks_ejemplo():
    """Tres tracks, dos de un mismo álbum y un single suelto.

    El single trae un ISRC malformado a propósito, para que el mismo catálogo
    sirva de entrada al validador sin tener que inventar otro.
    """
    return [
        _track(
            "Tema A", "Disco Uno", 2020, isrc="ARABC2000001", upc="036000291452", vid="a1", date="2020-01-01"
        ),
        _track(
            "Tema B", "Disco Uno", 2020, isrc="ARABC2000002", upc="036000291452", vid="a2", date="2020-01-02"
        ),
        _track("Single", "", 2021, isrc="MALFORMADO", vid="b1", dist="DistroKid", date="2021-01-01"),
    ]


@pytest.fixture
def catalogo_ejemplo(tracks_ejemplo):
    """Los tracks de ejemplo ya agrupados en productos. Son dos."""
    return P.group_products(tracks_ejemplo, artist="Artista Test")


@pytest.fixture
def productos_entregable(tmp_path):
    """Dos productos con audio en disco, para los tests del empaquetado.

    Uno sale entero y bien (portada, UPC, FLAC), el otro es el caso que importa
    revisar, sin UPC, sin portada, con un audio lossy y un track sin audio.
    """
    import audio as audio_mod

    flac = tmp_path / "a.flac"
    m4a = tmp_path / "b.m4a"
    flac.write_bytes(b"FLAC-falso" * 100)
    m4a.write_bytes(b"AAC-falso" * 100)

    return [
        {
            "product_id": "p001",
            "title": "Album Bueno",
            "kind": "album",
            "release_year": 2020,
            "upc": "111",
            "label": "Sello",
            "distributor": "ONErpm",
            "track_count": 1,
            "total_views": 10,
            "order_unconfirmed": False,
            "folder": "2020 - Album Bueno [111]",
            "cover_bytes": b"\xff\xd8jpeg-falso",
            "cover_status": "ok 3000x3000",
            "tracks": [
                {
                    "track": "Tema Lossless",
                    "track_number": 1,
                    "isrc": "ARABC2000001",
                    "duration_s": 200,
                    "views": 10,
                    "url": "https://youtu.be/x",
                    "video_id": "x",
                    "audio_path": str(flac),
                    "audio_format": ".flac",
                    "audio_label": audio_mod.ETIQUETA_LOSSLESS,
                }
            ],
        },
        {
            "product_id": "p002",
            "title": "Single Flojo",
            "kind": "single",
            "release_year": 2021,
            "upc": "",
            "label": "",
            "distributor": "DistroKid",
            "track_count": 2,
            "total_views": 5,
            "order_unconfirmed": True,
            "folder": "2021 - Single Flojo",
            "cover_bytes": None,
            "cover_status": "sin match en iTunes",
            "tracks": [
                {
                    "track": "Tema Lossy",
                    "track_number": 1,
                    "isrc": "",
                    "duration_s": 180,
                    "views": 5,
                    "url": "",
                    "video_id": "y",
                    "audio_path": str(m4a),
                    "audio_format": ".m4a",
                    "audio_label": "lossy",
                },
                {
                    "track": "Tema Sin Audio",
                    "track_number": 2,
                    "isrc": "",
                    "duration_s": 90,
                    "views": 0,
                    "url": "",
                    "video_id": "z",
                    "audio_path": None,
                    "audio_format": None,
                    "audio_label": None,
                },
            ],
        },
    ]


# ============================================================
# Imágenes mínimas, para no depender de Pillow ni de archivos binarios
# ============================================================


def _png(ancho, alto):
    """PNG mínimo con un IHDR válido. Alcanza para leer las dimensiones."""
    import struct

    ihdr = struct.pack(">II", ancho, alto) + b"\x08\x06\x00\x00\x00"
    return b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + ihdr + b"\x00\x00\x00\x00"


def _jpeg(ancho, alto, comps=3, relleno=0):
    """JPEG mínimo con un marcador SOF0 válido. `comps=4` simula CMYK."""
    import struct

    sof = (
        b"\xff\xc0"
        + struct.pack(">H", 8 + 3 * comps)
        + b"\x08"
        + struct.pack(">HH", alto, ancho)
        + bytes([comps])
        + b"\x00" * (3 * comps)
    )
    return b"\xff\xd8" + sof + b"\xff\xd9" + b"\x00" * relleno


@pytest.fixture
def png():
    return _png


@pytest.fixture
def jpeg():
    return _jpeg


# ============================================================
# Espera por reloj
# ============================================================


def _esperar(cond, segundos=30, paso=0.02):
    """Espera hasta que `cond()` sea verdadera, o hasta agotar el tiempo.

    Por reloj y no por cantidad de vueltas. Un runner de CI cargado puede tardar
    mucho más que una máquina libre, y un test que se rinde por conteo se vuelve
    inestable justo en la puerta del build.
    """
    import time

    limite = time.monotonic() + segundos
    while time.monotonic() < limite:
        if cond():
            return True
        time.sleep(paso)
    return bool(cond())


@pytest.fixture
def esperar():
    return _esperar


# ============================================================
# Respuestas reales grabadas de Deezer e iTunes
# ============================================================

FIXTURES = os.path.join(RAIZ, "tests", "fixtures")


def _respuesta_grabada(nombre):
    """El cuerpo de una respuesta real, tal como la devolvió la API.

    Las graba `build/grabar_fixtures.py`, que es lo único del repositorio que
    toca la red. Los tests leen el archivo y no salen a ningún lado.
    """
    import json

    with open(os.path.join(FIXTURES, nombre), encoding="utf-8") as f:
        return json.load(f)["respuesta"]


@pytest.fixture
def respuesta_grabada():
    return _respuesta_grabada
