# -*- coding: utf-8 -*-
"""Contrato con Deezer y con la iTunes Search API, contra respuestas reales.

Sin red. Los archivos de `tests/fixtures/` son respuestas que dieron las APIs de
verdad, grabadas una vez con `python build/grabar_fixtures.py`, que es lo único
del repositorio que sale a internet.

Por qué existe. Los otros tests construyen sus dobles a mano, con la forma que el
código espera. Eso prueba que el código es consistente consigo mismo, no que
entienda lo que las APIs devuelven. El día que Deezer renombre un campo, un doble
escrito a mano sigue pasando y el que se entera es el usuario.

Si alguno de estos tests se cae después de volver a grabar las fixtures, la
pregunta no es cómo actualizar el archivo: es qué cambió en la API y qué hay que
arreglar acá.
"""

import pytest

from migrador import portadas
from migrador import relevar_core as R
from conftest import _respuesta_grabada

# Los datos reales de la grabación. Están escritos acá, a la vista, para que se
# pueda verificar contra Deezer y contra iTunes que son los que dicen ser.
ISRC_REAL = "USQX91300108"
UPC_REAL = "886443927087"
ALBUM_ID_REAL = 6575789
TITULO_REAL = "Get Lucky (feat. Pharrell Williams and Nile Rodgers)"
DURACION_REAL = 367


# ============================================================
# La forma de lo que devuelven, que es lo que se rompe en silencio
# ============================================================


def test_deezer_search_trae_los_campos_que_leemos():
    """Si alguno de estos desaparece, el enriquecimiento deja de traer códigos y
    nada avisa: los tracks quedan sin ISRC, que es un aviso normal del validador."""
    items = _respuesta_grabada("deezer_search_libre.json")["data"]
    assert items, "la búsqueda libre tiene que traer resultados"
    for c in items:
        assert "id" in c
        assert "title" in c
        assert "duration" in c
        assert "name" in (c.get("artist") or {})
        assert "id" in (c.get("album") or {})


def test_deezer_album_trae_el_upc():
    album = _respuesta_grabada("deezer_album.json")
    assert album.get("upc") == UPC_REAL
    assert album.get("title") == "Random Access Memories"


def test_deezer_track_trae_el_isrc():
    """Es el pedido de respaldo, para los resultados de búsqueda que no lo traen."""
    assert _respuesta_grabada("deezer_track.json").get("isrc") == ISRC_REAL


def test_itunes_trae_los_campos_que_leemos():
    for nombre in ("itunes_search.json", "itunes_lookup_upc.json"):
        datos = _respuesta_grabada(nombre)
        assert "resultCount" in datos
        for r in datos["results"]:
            assert "artworkUrl100" in r
            assert "collectionName" in r
            assert "artistName" in r


def test_la_url_del_cdn_de_apple_sigue_teniendo_la_forma_que_reescribimos():
    """El truco de alta resolución depende del esquema de nombres del CDN.

    Se pide `100x100bb.jpg` y se reescribe a `3000x3000bb.jpg`. Es la parte más
    frágil de `portadas.py`, y hasta acá se probaba contra una URL inventada.
    Ésta es la que Apple devolvió de verdad.
    """
    url = _respuesta_grabada("itunes_lookup_upc.json")["results"][0]["artworkUrl100"]
    assert url.endswith("/100x100bb.jpg"), url

    grande = portadas._upscale(url, 3000)
    assert grande.endswith("/3000x3000bb.jpg"), grande
    assert grande.startswith("https://"), grande
    # Lo único que cambia es el tamaño: el resto de la ruta queda igual.
    assert grande.rsplit("/", 1)[0] == url.rsplit("/", 1)[0]


# ============================================================
# Deezer, con el cliente real y la red reemplazada
# ============================================================


@pytest.fixture
def deezer_grabado(monkeypatch):
    """Sirve las respuestas grabadas según el path que pida el código.

    Reemplaza `_deezer_json`, que es la frontera con la red. Todo lo de arriba
    (el armado de la consulta, el puntaje, la confianza) corre de verdad.
    """
    pedidos = []

    def falso(path):
        pedidos.append(path)
        if path.startswith("search?") and "track%3A" in path:
            return _respuesta_grabada("deezer_search_estricta.json")
        if path.startswith("search?"):
            return _respuesta_grabada("deezer_search_libre.json")
        if path.startswith("track/"):
            return _respuesta_grabada("deezer_track.json")
        if path.startswith("album/"):
            return _respuesta_grabada("deezer_album.json")
        raise AssertionError(f"el código pidió algo que no está grabado: {path}")

    monkeypatch.setattr(R, "_deezer_json", falso)
    return pedidos


def _track_de_youtube():
    """Un track con la forma que devuelve `build_tracks`, con los datos reales
    del video de YouTube correspondiente."""
    return {
        "video_id": "5NV6Rdv1a3I",
        "track": TITULO_REAL,
        "album": "Random Access Memories",
        "distributor": "Columbia",
        "label": "Columbia",
        "release_year": 2013,
        "isrc": "",
        "upc": "",
        "match": "",
        "duration_s": DURACION_REAL,
        "views": 0,
        "likes": 0,
        "comments": 0,
        "upload_date": "2013-04-19",
        "desc3": "",
        "url": "https://youtu.be/5NV6Rdv1a3I",
    }


def test_deezer_match_saca_el_isrc_real(deezer_grabado):
    isrc, album_id, confianza = R.deezer_match(_track_de_youtube(), "Daft Punk")

    assert isrc == ISRC_REAL
    assert album_id == ALBUM_ID_REAL
    assert confianza in ("alta", "media")


def test_la_busqueda_estricta_no_encuentra_nada_y_por_eso_existe_el_respaldo(deezer_grabado):
    """Esto no es un caso de borde inventado: es lo que Deezer contesta hoy.

    La consulta con `track:"..." artist:"..."` devuelve cero resultados para un
    tema que sí está en su catálogo. Sin el respaldo por búsqueda libre, el
    enriquecimiento no traería ningún código para este disco.
    """
    assert _respuesta_grabada("deezer_search_estricta.json")["data"] == []

    R.deezer_match(_track_de_youtube(), "Daft Punk")

    assert len(deezer_grabado) >= 2, deezer_grabado
    assert "track%3A" in deezer_grabado[0], "la primera consulta es la estricta"
    assert "track%3A" not in deezer_grabado[1], "la segunda es la libre"


def test_un_artista_que_no_es_el_no_alcanza_la_confianza(deezer_grabado):
    """El puntaje exige que el artista coincida. Si no, es otro tema con título
    parecido, y traer su ISRC sería peor que no traer ninguno."""
    isrc, _album, confianza = R.deezer_match(_track_de_youtube(), "Otro Artista Cualquiera")
    assert confianza == ""
    assert isrc == ""


def test_deezer_album_upcs_devuelve_el_upc_real(deezer_grabado):
    assert R.deezer_album_upcs([ALBUM_ID_REAL]) == {ALBUM_ID_REAL: UPC_REAL}


def test_el_upc_real_pasa_el_validador():
    """Cierra el círculo: el código que Deezer devuelve de verdad tiene que ser
    válido según nuestras propias reglas de dígito verificador. Si no lo fuera,
    estaríamos marcando como error algo que la distribuidora acepta."""
    from migrador import validar

    assert validar.upc_valido(UPC_REAL)[0] is True


def test_el_isrc_real_pasa_el_validador():
    from migrador import validar

    assert validar.isrc_valido(ISRC_REAL) is True


# ============================================================
# iTunes, con el cliente real y la red reemplazada
# ============================================================


@pytest.fixture
def itunes_grabado(monkeypatch):
    """Sirve las respuestas grabadas según la URL que pida `portadas`."""
    pedidos = []

    def falso(url, retries=3):
        pedidos.append(url)
        if "/lookup?" in url:
            return _respuesta_grabada("itunes_lookup_upc.json")
        # El término con el que se grabó la respuesta vacía. Se compara con
        # eso y no con una heurística, para que no se confunda con la búsqueda
        # de un álbum inexistente de un artista que sí existe, que es otro caso.
        if "zzzz" in url:
            return _respuesta_grabada("itunes_search_vacia.json")
        return _respuesta_grabada("itunes_search.json")

    monkeypatch.setattr(portadas, "_http_json", falso)
    return pedidos


def test_con_upc_se_busca_por_lookup_y_el_match_es_exacto(itunes_grabado):
    info = portadas.buscar_portada("Daft Punk", "Random Access Memories", upc=UPC_REAL)

    assert info is not None
    assert info["match"] == "upc"
    assert info["ratio"] == 1.0
    assert info["matched_album"] == "Random Access Memories"
    assert info["matched_artist"] == "Daft Punk"
    assert info["url100"].endswith("/100x100bb.jpg")
    # Con UPC no hace falta la búsqueda por texto, y no se hace.
    assert len(itunes_grabado) == 1
    assert "/lookup?" in itunes_grabado[0]


def test_sin_upc_se_busca_por_texto(itunes_grabado):
    info = portadas.buscar_portada("Daft Punk", "Random Access Memories")

    assert info is not None
    assert info["matched_album"] == "Random Access Memories"
    assert info["match"] == "alta"
    assert info["ratio"] >= portadas.MIN_RATIO
    assert "/search?" in itunes_grabado[0]


def test_una_busqueda_sin_resultados_devuelve_none(itunes_grabado):
    """Con el mismo término con el que se grabó la respuesta vacía de Apple."""
    assert portadas.buscar_portada("zzzz qqqq", "no existe este disco 12345") is None


def test_un_album_que_no_se_parece_no_trae_la_portada_de_otro(itunes_grabado):
    """Preferimos no traer portada antes que traer la de otro disco. Es el
    umbral `MIN_RATIO`, y acá se prueba contra los candidatos reales que devuelve
    Apple para una búsqueda de Daft Punk."""
    assert portadas.buscar_portada("Daft Punk", "Un Disco Que No Existe En Absoluto") is None
