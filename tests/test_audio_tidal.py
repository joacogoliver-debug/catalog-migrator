# -*- coding: utf-8 -*-
"""Contrato con la librería tiddl. Sin credenciales y sin red.

Existe por un bug que llegó al usuario. `audio.py` importaba `TidalApi` cuando
la clase se llama `TidalAPI`. La conexión de Tidal se veía exitosa, y después no
bajaba ningún audio sin explicación, porque el import fallaba recién al usar la
sesión. Ninguna prueba lo agarró porque todo el módulo de audio dependía de
credenciales que no se pueden poner en un test.

La idea es verificar, SIN credenciales, que todo lo que `audio.py` le pide a
tiddl exista y tenga la forma esperada. Nombres de clase, métodos, firmas y los
campos que leemos de las respuestas. Es lo que separa «la librería cambió» de un
misterio en tiempo de ejecución.

Si tiddl no está instalado, el archivo entero se saltea. El módulo de audio es
opcional y el CI corre a propósito sin él.
"""

import inspect

import pytest

import audio

pytest.importorskip("tiddl", reason="el módulo de audio es opcional")

from tiddl.core.api import TidalAPI, TidalClient  # noqa: E402
from tiddl.core.api.api import AlbumItems, ArtistAlbumsItems, Search  # noqa: E402
from tiddl.core.api.models.base import AlbumItems as BaseAlbumItems  # noqa: E402
from tiddl.core.api.models.resources import Album, Track  # noqa: E402
from tiddl.core.auth import AuthAPI, AuthClientError  # noqa: E402


# ============================================================
# Constructores
# ============================================================


def test_firma_de_tidal_api():
    p = list(inspect.signature(TidalAPI.__init__).parameters)
    assert p[:4] == ["self", "client", "user_id", "country_code"]


@pytest.mark.parametrize("param", ["token", "cache_name"])
def test_tidal_client_acepta_token_y_cache_propia(param):
    """`cache_name` es lo que sostiene el aislamiento por sesión, para no tocar
    el `~/.tiddl` global, que es de un solo usuario por diseño."""
    assert param in inspect.signature(TidalClient.__init__).parameters


# ============================================================
# Métodos que usa audio.py
# ============================================================


@pytest.mark.parametrize(
    "metodo",
    [
        "get_search",
        "get_artist_albums",
        "get_album_items",
        "get_track",
        "get_track_stream",
    ],
)
def test_la_api_tiene_el_metodo(metodo):
    assert hasattr(TidalAPI, metodo)


@pytest.mark.parametrize("param", ["limit", "offset", "filter"])
def test_get_artist_albums_pagina_y_filtra(param):
    """Sin paginar y sin pedir EPSANDSINGLES el índice sale con 10 álbumes y
    ningún single."""
    assert param in inspect.signature(TidalAPI.get_artist_albums).parameters


def test_el_limite_por_defecto_sigue_siendo_bajo():
    """Por eso `audio.py` DEBE pasar `limit`. Si el default sube, revisar
    PAGINA_TIDAL."""
    p = inspect.signature(TidalAPI.get_artist_albums).parameters["limit"]
    assert p.default is not inspect.Parameter.empty
    assert p.default <= 50


@pytest.mark.parametrize("param", ["limit", "offset"])
def test_get_album_items_pagina(param):
    assert param in inspect.signature(TidalAPI.get_album_items).parameters


def test_get_track_stream_acepta_calidad():
    assert "quality" in inspect.signature(TidalAPI.get_track_stream).parameters


# ============================================================
# Autenticación
# ============================================================


@pytest.mark.parametrize("metodo", ["get_device_auth", "get_auth", "refresh_token"])
def test_la_autenticacion_tiene_el_metodo(metodo):
    assert hasattr(AuthAPI, metodo)


def test_el_error_de_auth_expone_el_motivo():
    """`audio.py` lo usa para distinguir el login todavía pendiente."""
    e = AuthClientError(status=400, error="authorization_pending")
    assert getattr(e, "error", None) == "authorization_pending"


# ============================================================
# Campos de los modelos que leemos
# ============================================================


@pytest.mark.parametrize("modelo", [ArtistAlbumsItems, AlbumItems])
@pytest.mark.parametrize("campo", ["items", "totalNumberOfItems"])
def test_los_listados_traen_items_y_total(modelo, campo):
    assert campo in modelo.model_fields


def test_la_busqueda_devuelve_artistas():
    assert "artists" in Search.model_fields
    assert "items" in Search.Artists.model_fields


@pytest.mark.parametrize("campo", ["id", "title", "upc"])
def test_del_album_leemos_upc_y_titulo(campo):
    assert campo in Album.model_fields


@pytest.mark.parametrize(
    "campo",
    [
        "id",
        "title",
        "isrc",
        "trackNumber",
        "volumeNumber",
        "mediaMetadata",
    ],
)
def test_del_track_leemos_isrc_y_el_orden_real(campo):
    """El orden real de los tracks es justo lo que YouTube no da."""
    assert campo in Track.model_fields


def test_los_items_del_album_vienen_envueltos():
    assert "item" in BaseAlbumItems.TrackItem.model_fields


def test_las_utilidades_de_descarga_existen():
    from tiddl.core.metadata import add_track_metadata  # noqa: F401
    from tiddl.core.utils import get_track_stream_data  # noqa: F401
    from tiddl.core.utils.ffmpeg import extract_flac  # noqa: F401


# ============================================================
# Y que audio.py haga lo que dice
# ============================================================


def test_el_indice_pide_eps_y_singles_y_pagina():
    src = inspect.getsource(audio.construir_indice_isrc)
    assert "EPSANDSINGLES" in src, "sin esto los singles y EPs nunca entran al índice"
    assert "offset" in src and "totalNumberOfItems" in src, (
        "sin paginar, la discografía queda cortada en el ítem 10"
    )


def test_las_clases_se_importan_de_verdad():
    """Se ejecuta, no se inspecciona. Si el nombre de la clase está mal, tira
    ImportError acá y no a mitad de una descarga."""
    ClaseAPI, ClaseCliente = audio.clases_tidal()
    assert ClaseAPI is TidalAPI
    assert ClaseCliente is TidalClient
