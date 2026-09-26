"""El cruce con Tidal por ISRC, con una sesión de mentira y sin red.

La misma grabación está en el single y en el álbum, y cada aparición trae su
número de track y su UPC. El índice guardaba una sola, la del último release
procesado, y como los singles se piden después de los álbumes, el tema del
álbum quedaba con el número 1 y el UPC del single, marcado «confirmado».
"""

from types import SimpleNamespace as NS
from typing import Any

import pytest

from migrador import audio
from migrador import paquete as PQ

UPC_ALBUM = "0886111000017"
UPC_SINGLE = "0886222000025"


def _track(isrc, numero, disco=1):
    return NS(
        item=NS(
            id=hash((isrc, numero)) % 10_000, isrc=isrc, trackNumber=numero, volumeNumber=disco, title=isrc
        )
    )


DISCOGRAFIA = {
    "ALBUMS": [NS(id=10, title="Disco", upc=UPC_ALBUM)],
    "EPSANDSINGLES": [NS(id=20, title="Tema Dos", upc=UPC_SINGLE)],
}
TRACKS = {
    10: [_track("ARAAA2000001", 1), _track("ARAAA2000002", 2), _track("ARAAA2000003", 3)],
    20: [_track("ARAAA2000002", 1)],
}


class _Api:
    def get_artist_albums(self, artist_id, limit, offset, filter):  # noqa: A002 (así se llama en tiddl)
        items = DISCOGRAFIA[filter][offset : offset + limit]
        return NS(items=items, totalNumberOfItems=len(DISCOGRAFIA[filter]))

    def get_album_items(self, album_id, limit, offset):
        items = TRACKS[album_id][offset : offset + limit]
        return NS(items=items, totalNumberOfItems=len(TRACKS[album_id]))


@pytest.fixture
def indice(monkeypatch):
    monkeypatch.setattr(audio, "buscar_artista_tidal", lambda session, artista: (1, "Fulano"))
    ind, artist_id = audio.construir_indice_isrc(NS(api=_Api()), "Fulano", log=lambda *_: None)
    assert artist_id == 1
    return ind


def _producto(isrcs, upc="", titulo="Disco") -> Any:
    # `Any` y no `Producto`: está a medio armar, con sólo lo que el cruce lee.
    return {
        "title": titulo,
        "upc": upc,
        "track_count": len(isrcs),
        "order_unconfirmed": True,
        "tracks": [{"isrc": i, "track": i} for i in isrcs],
    }


def test_el_indice_guarda_todas_las_apariciones(indice):
    assert {a["album_id"] for a in indice["ARAAA2000002"]} == {10, 20}


def test_el_tema_del_album_se_queda_con_el_numero_y_el_upc_del_album(indice):
    p = _producto(["ARAAA2000003", "ARAAA2000001", "ARAAA2000002"])
    audio.matchear_por_isrc([p], indice, log=lambda *_: None)
    numeros = {t["isrc"]: t["track_number"] for t in p["tracks"]}
    assert numeros == {"ARAAA2000001": 1, "ARAAA2000002": 2, "ARAAA2000003": 3}
    assert [t["isrc"] for t in p["tracks"]] == ["ARAAA2000001", "ARAAA2000002", "ARAAA2000003"]
    assert p["upc"] == UPC_ALBUM
    assert p["order_unconfirmed"] is False


def test_el_single_se_queda_con_lo_del_single(indice):
    p = _producto(["ARAAA2000002"], titulo="Tema Dos")
    audio.matchear_por_isrc([p], indice, log=lambda *_: None)
    assert p["tracks"][0]["track_number"] == 1
    assert p["upc"] == UPC_SINGLE


def test_con_upc_el_release_se_elige_por_el_codigo(indice):
    """El mismo UPC escrito con 12 dígitos también es el código del álbum."""
    p = _producto(["ARAAA2000002"], upc=UPC_ALBUM.lstrip("0"))
    assert audio.release_de_tidal(p, indice) == 10


def test_si_el_release_no_trae_todos_los_temas_el_orden_sigue_sin_confirmar(indice):
    p = _producto(["ARAAA2000001", "ARAAA2000002", "ARBBB9900001"])
    audio.matchear_por_isrc([p], indice, log=lambda *_: None)
    assert p["order_unconfirmed"] is True
    assert p["upc"] == "", "un UPC de un release que no es este producto no se toma"
    ajeno = next(t for t in p["tracks"] if t["isrc"] == "ARBBB9900001")
    assert ajeno["tidal"] is None


def test_la_hoja_dice_confirmado_por_tidal_solo_si_el_numero_es_de_este_release(indice):
    """Que el tema esté en Tidal no alcanza: el número tiene que ser del mismo release."""
    p = _producto(["ARAAA2000002", "ARAAA2000001"], titulo="Compilado")
    p["tracks"].append({"isrc": "ARBBB9900001", "track": "otro"})
    p["track_count"] = 3
    audio.matchear_por_isrc([p], indice, log=lambda *_: None)
    # El álbum tiene dos de los tres temas: no es este producto, y sus números
    # (1 y 2) no son los del compilado.
    assert all(PQ.orden_de(p, t) != "confirmed (Tidal)" for t in p["tracks"])
    assert all("track_number" not in t for t in p["tracks"])
    assert p["order_unconfirmed"] is True
    solo = _producto(["ARAAA2000002"], titulo="Tema Dos")
    audio.matchear_por_isrc([solo], indice, log=lambda *_: None)
    assert PQ.orden_de(solo, solo["tracks"][0]) == "confirmed (Tidal)"


def test_para_bajar_el_audio_sirve_cualquier_aparicion(indice):
    """Es la misma grabación: aunque el release no sea este producto, el
    track_id se puede bajar."""
    p = _producto(["ARAAA2000002", "ARBBB9900001"], titulo="Otro")
    audio.matchear_por_isrc([p], indice, log=lambda *_: None)
    assert p["tracks"][0]["tidal"]["track_id"]


def test_lo_que_deezer_ya_confirmo_no_se_pisa(indice):
    p = _producto(["ARAAA2000001", "ARAAA2000002", "ARAAA2000003"])
    for n, t in enumerate(p["tracks"], start=1):
        t["track_number"], t["orden_fuente"] = n, "deezer"
    audio.matchear_por_isrc([p], indice, log=lambda *_: None)
    assert all(t["orden_fuente"] == "deezer" for t in p["tracks"])
