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


# ============================================================
# Cómo contesta YouTube hoy por un canal Topic
# ============================================================
#
# Las respuestas de arriba se grabaron en septiembre de 2026, cuando un canal
# Topic todavía publicaba su lista de subidas. Éstas son del mismo canal dos
# meses después, grabadas con `build/grabar_fixtures.py --youtube-busqueda`: la
# lista ya no existe, y el canal se lista por el buscador. Hasta acá eso estaba
# probado sólo contra respuestas escritas a mano.


def _grabada_con_estado(nombre):
    with open(os.path.join(FIXTURES, nombre), encoding="utf-8") as f:
        datos = json.load(f)
    return datos["_grabado"]["estado_http"], datos["respuesta"]


def test_la_lista_de_subidas_de_un_topic_contesta_que_no_existe():
    estado, cuerpo = _grabada_con_estado("youtube_playlist_no_existe.json")
    assert estado == 404
    error = R._error_de_youtube(estado, json.dumps(cuerpo))
    assert error.codigo == "sin_lista", "de este código depende que el canal se liste por el buscador"
    assert "<code>" not in str(error) and "playlist" not in str(error).lower()


def test_la_busqueda_por_canal_trae_lo_que_el_listado_necesita():
    estado, pagina = _grabada_con_estado("youtube_search_canal.json")
    assert estado == 200
    assert pagina["pageInfo"]["totalResults"] > len(pagina["items"]), (
        "el total es una estimación del canal entero"
    )
    assert pagina.get("nextPageToken"), "y hay más páginas"
    for item in pagina["items"]:
        assert item["id"]["kind"] == "youtube#video" and len(item["id"]["videoId"]) == 11
        assert item["snippet"]["channelId"] == TOPIC
        # De la fecha depende seguir más allá del tope de quinientos resultados.
        assert item["snippet"]["publishedAt"].endswith("Z")
    fechas = [i["snippet"]["publishedAt"] for i in pagina["items"]]
    dias = [f[:10] for f in fechas]
    assert dias == sorted(dias, reverse=True), "`order=date` devuelve del día más nuevo al más viejo"
    # Y adentro de un día, mezclados: los temas de un disco se publican con
    # minutos de diferencia y no llegan en ese orden. De esto depende
    # `_proximo_corte`: si un día esto deja de ser así, el corte por día sobra.
    assert fechas != sorted(fechas, reverse=True), "adentro de un mismo día no vienen ordenados"


@pytest.fixture
def topic_de_hoy(monkeypatch):
    """`api_get` contesta como contesta hoy YouTube por el canal Topic grabado."""
    estado_404, cuerpo_404 = _grabada_con_estado("youtube_playlist_no_existe.json")
    _estado, pagina = _grabada_con_estado("youtube_search_canal.json")
    pedidos = []

    def api_get(endpoint, params, key, intentos=3):
        pedidos.append((endpoint, dict(params)))
        if endpoint == "channels":
            return _respuesta_grabada("youtube_channels.json")
        if endpoint == "playlistItems":
            raise R._error_de_youtube(estado_404, json.dumps(cuerpo_404))
        if endpoint == "search":
            # La segunda página grabada sería otra; alcanza con ver que el token
            # se sigue y que lo repetido no se cuenta dos veces.
            if params.get("pageToken"):
                ultima = dict(pagina)
                ultima.pop("nextPageToken", None)
                return ultima
            return pagina
        if endpoint == "videos":
            return _respuesta_grabada("youtube_videos.json")
        raise AssertionError(f"pedido inesperado: {endpoint}")

    monkeypatch.setattr(R, "api_get", api_get)
    return pedidos


def test_el_listado_por_buscador_contra_la_respuesta_real(topic_de_hoy):
    _estado, pagina = _grabada_con_estado("youtube_search_canal.json")
    ids, info = R.buscar_videos_del_canal(TOPIC, "k")
    assert ids == [i["id"]["videoId"] for i in pagina["items"]], "en el orden en que llegan y sin repetir"
    assert info["total_estimado"] == pagina["pageInfo"]["totalResults"]
    assert info["paginas"] == 2 and info["cortado_por_cuota"] is False
    busquedas = [p for e, p in topic_de_hoy if e == "search"]
    assert busquedas[0]["channelId"] == TOPIC and busquedas[0]["order"] == "date"
    assert busquedas[1]["pageToken"] == pagina["nextPageToken"]


def test_relevar_un_topic_de_punta_a_punta_como_contesta_hoy(topic_de_hoy):
    """El mismo canal que `test_relevar_de_punta_a_punta`, dos meses después: la
    lista de subidas contesta 404 y el catálogo sale igual, por el buscador."""
    res = R.relevar(f"https://www.youtube.com/channel/{TOPIC}", "k", with_codes=False)
    assert set(res) == set(Relevamiento.__annotations__)
    assert (res["via"], res["channel_id"], res["artist"]) == ("busqueda", TOPIC, "Daft Punk")
    assert (
        res["total_estimado"]
        == _grabada_con_estado("youtube_search_canal.json")[1]["pageInfo"]["totalResults"]
    )
    assert len(res["tracks"]) == len(_respuesta_grabada("youtube_videos.json")["items"])
    assert [e for e, _p in topic_de_hoy][:3] == ["channels", "playlistItems", "search"], (
        "primero la lista, que es la barata, y recién después el buscador"
    )
