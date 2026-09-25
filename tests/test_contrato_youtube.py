# -*- coding: utf-8 -*-
"""Contrato con la YouTube Data API, contra respuestas reales grabadas. Sin red.

Las respuestas las grabó `build/grabar_fixtures.py --youtube` del canal Topic de
Daft Punk, con la clave en una cabecera y fuera de toda URL. Hasta acá
`relevar()` completo, la paginación y `build_tracks` no tenían ningún test
contra lo que YouTube devuelve de verdad, y ahí vivían varios de los bugs de
este ciclo (la fecha de lanzamiento, los créditos, el handle codificado).

  - las respuestas no traen la clave por ningún lado
  - el canal, la paginación, la metadata y la búsqueda del Topic
  - `relevar()` de punta a punta, y su resultado contra el contrato
"""

import json
import os

import pytest

from conftest import FIXTURES, _respuesta_grabada
from migrador import productos as P
from migrador import relevar_core as R
from migrador.contratos import Relevamiento, ResumenDistribuidora, Track

TOPIC = "UCRr1xG_2WIDs18a6cIiCxeA"


@pytest.fixture
def youtube_grabado(monkeypatch):
    """`api_get` contesta con las respuestas grabadas, según lo que se pide."""
    pedidos = []

    def api_get(endpoint, params, key, intentos=3):
        pedidos.append((endpoint, dict(params)))
        if endpoint == "channels":
            return _respuesta_grabada(
                "youtube_channels.json" if params.get("id") == TOPIC else "youtube_channels_vacio.json"
            )
        if endpoint == "playlistItems":
            if not params.get("pageToken"):
                return _respuesta_grabada("youtube_playlist_1.json")
            # La página 2 grabada sigue apuntando a la 3 (el canal tiene más de
            # quinientos videos). Acá se la trata como la última: se graban dos
            # páginas, y alcanza para ver que el token se sigue.
            ultima = dict(_respuesta_grabada("youtube_playlist_2.json"))
            ultima.pop("nextPageToken", None)
            return ultima
        if endpoint == "videos":
            return _respuesta_grabada("youtube_videos.json")
        if endpoint == "search":
            return _respuesta_grabada("youtube_search_topic.json")
        raise AssertionError(f"pedido inesperado: {endpoint}")

    monkeypatch.setattr(R, "api_get", api_get)
    return pedidos


def test_ninguna_respuesta_grabada_trae_la_clave():
    for nombre in sorted(os.listdir(FIXTURES)):
        if not nombre.startswith("youtube_"):
            continue
        with open(os.path.join(FIXTURES, nombre), encoding="utf-8") as f:
            texto = f.read()
        datos = json.loads(texto)
        assert "key=" not in datos["_grabado"]["url"], nombre
        assert "AIza" not in texto, nombre


def test_el_canal_trae_su_lista_de_subidas(youtube_grabado):
    cid, subidas, titulo = R.resolve_channel(f"https://www.youtube.com/channel/{TOPIC}", "k")
    assert cid == TOPIC
    assert subidas.startswith("UU")
    assert titulo == "Daft Punk - Topic"


def test_un_canal_que_no_existe_se_dice(youtube_grabado):
    with pytest.raises(R.RelevarError) as e:
        R.resolve_channel("https://www.youtube.com/channel/UC" + "0" * 22, "k")
    assert e.value.codigo == "url"


def test_la_paginacion_sigue_el_token_hasta_el_final(youtube_grabado):
    ids = R.list_video_ids("UU", "k")
    uno = _respuesta_grabada("youtube_playlist_1.json")
    dos = _respuesta_grabada("youtube_playlist_2.json")
    assert len(ids) == len(uno["items"]) + len(dos["items"])
    assert [p for p in youtube_grabado if p[0] == "playlistItems"][1][1]["pageToken"] == uno["nextPageToken"]


def test_la_metadata_real_se_interpreta_entera(youtube_grabado):
    tracks = R.build_tracks(R.fetch_videos(["x"], "k"))
    assert tracks
    for t in tracks:
        assert set(Track.__required_keys__) <= set(t)
        assert t["distributor"] != P.SIN_DATOS, "son Art Tracks: todos traen distribuidora"
        assert t["duration_s"] > 0
        assert t["artists"], "la línea «Título · Artista» siempre está"
    # Lo que este ciclo empezó a leer, visto en respuestas de verdad.
    assert any(t["release_date"] for t in tracks)
    assert any(t["credits"]["composers"] for t in tracks)
    assert any(len(t["artists"]) > 1 for t in tracks), "hay feats en esta página"


def test_la_busqueda_del_topic_encuentra_el_canal(youtube_grabado):
    assert R.buscar_canal_topic("Daft Punk", "k") == (TOPIC, "Daft Punk - Topic")


def test_relevar_de_punta_a_punta(youtube_grabado):
    avances = []
    res = R.relevar(
        f"https://www.youtube.com/channel/{TOPIC}",
        "k",
        with_codes=False,
        progress=lambda m, f: avances.append(f),
    )
    assert set(res) == set(Relevamiento.__annotations__)
    for d in res["distribs"].values():
        assert set(d) == set(ResumenDistribuidora.__annotations__)
    assert res["artist"] == "Daft Punk"
    assert res["es_topic"] is True and res["via_topic"] is False
    assert len(res["tracks"]) == len(_respuesta_grabada("youtube_videos.json")["items"]), (
        "todo lo de la página es lanzamiento"
    )
    assert avances == sorted(avances), "la barra nunca va para atrás"
    productos = P.group_products(res["tracks"], res["artist"])
    assert productos and all(p["folder"] for p in productos)


def test_desde_un_canal_comun_cambia_al_topic(youtube_grabado, monkeypatch):
    """Si lo pegado no es el Topic, se busca el Topic y se releva ése."""
    canal_comun = json.loads(json.dumps(_respuesta_grabada("youtube_channels.json")))
    canal_comun["items"][0]["snippet"]["title"] = "Daft Punk"
    original = R.api_get

    def api_get(endpoint, params, key, intentos=3):
        if endpoint == "channels" and params.get("forHandle"):
            return canal_comun
        return original(endpoint, params, key)

    monkeypatch.setattr(R, "api_get", api_get)
    res = R.relevar("https://www.youtube.com/@daftpunk", "k", with_codes=False)
    assert res["via_topic"] is True
    assert res["channel_title"] == "Daft Punk - Topic"
