# -*- coding: utf-8 -*-
"""Qué se puede pegar en el campo del link. Sin red.

Lo que importa no es aceptar muchas formas, sino no confundir una con otra: un
link mal leído no da error, releva el catálogo de otro artista. Cubre:

  - el handle con caracteres codificados, como lo copia el navegador
  - las formas de canal: /channel/, UC suelto, /user/, /c/ y @handle
  - el link de un tema, que se resuelve al canal que lo subió
  - lo que no se puede leer, con un mensaje que dice qué pegar
"""

import pytest

from migrador import relevar_core as R

UC = "UCRr1xG_2WIDs18a6cIiCxeA"


@pytest.mark.parametrize(
    "url, clave, valor",
    [
        # El caso del bug: el navegador codifica la ñ, y se pedía «@pe».
        ("https://www.youtube.com/@pe%C3%B1a", "forHandle", "@peña"),
        ("https://www.youtube.com/@peña", "forHandle", "@peña"),
        ("https://www.youtube.com/@Artista.Oficial/videos", "forHandle", "@Artista.Oficial"),
        ("https://youtube.com/@artista?si=AbC123", "forHandle", "@artista"),
        ("@artista", "forHandle", "@artista"),
        (f"https://www.youtube.com/channel/{UC}", "id", UC),
        (f"https://music.youtube.com/channel/{UC}?si=x", "id", UC),
        (f"https://www.youtube.com/channel/{UC}/featured", "id", UC),
        (UC, "id", UC),
        (f"  {UC}  ", "id", UC),
        ("https://www.youtube.com/user/DaftPunkVEVO", "forUsername", "DaftPunkVEVO"),
        ("https://www.youtube.com/c/DaftPunk", "forHandle", "@DaftPunk"),
    ],
)
def test_formas_de_canal(url, clave, valor):
    params, _muestra = R.pedido_de_canal(url)
    assert params is not None
    assert params[clave] == valor


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PL123&index=2",
        "https://youtu.be/dQw4w9WgXcQ?si=abc",
        "https://music.youtube.com/watch?v=dQw4w9WgXcQ&feature=share",
        "https://www.youtube.com/shorts/dQw4w9WgXcQ",
        "youtu.be/dQw4w9WgXcQ",
    ],
)
def test_el_link_de_un_tema_pide_primero_su_canal(url):
    params, video = R.pedido_de_canal(url)
    assert params is None
    assert video == "dQw4w9WgXcQ"


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/playlist?list=PL123",
        "https://open.spotify.com/artist/123",
        "no es un link",
        "",
        "https://www.youtube.com/watch?v=corto",
    ],
)
def test_lo_que_no_se_puede_leer_da_un_error_de_campo(url):
    with pytest.raises(R.RelevarError) as e:
        R.pedido_de_canal(url)
    assert e.value.codigo == "url"


def test_el_mensaje_dice_que_se_puede_pegar():
    with pytest.raises(R.RelevarError) as e:
        R.pedido_de_canal("https://www.youtube.com/playlist?list=PL123")
    assert "@" in str(e.value) and "tema" in str(e.value)


def test_un_tema_se_resuelve_al_canal_que_lo_subio(monkeypatch):
    pedidos = []

    def api(endpoint, params, key):
        pedidos.append((endpoint, dict(params)))
        if endpoint == "videos":
            return {"items": [{"snippet": {"channelId": UC}}]}
        return {
            "items": [
                {
                    "id": UC,
                    "contentDetails": {"relatedPlaylists": {"uploads": "UU" + UC[2:]}},
                    "snippet": {"title": "Daft Punk - Topic"},
                }
            ]
        }

    monkeypatch.setattr(R, "api_get", api)
    assert R.resolve_channel("https://youtu.be/dQw4w9WgXcQ", "k") == (UC, "UU" + UC[2:], "Daft Punk - Topic")
    assert pedidos[0] == ("videos", {"part": "snippet", "id": "dQw4w9WgXcQ"})
    assert pedidos[1][1]["id"] == UC


def test_un_tema_que_no_existe_lo_dice(monkeypatch):
    monkeypatch.setattr(R, "api_get", lambda endpoint, params, key: {"items": []})
    with pytest.raises(R.RelevarError) as e:
        R.resolve_channel("https://youtu.be/dQw4w9WgXcQ", "k")
    assert e.value.codigo == "url"


def test_un_canal_que_no_existe_nombra_lo_que_se_busco(monkeypatch):
    monkeypatch.setattr(R, "api_get", lambda endpoint, params, key: {"items": []})
    with pytest.raises(R.RelevarError) as e:
        R.resolve_channel("https://www.youtube.com/@pe%C3%B1a", "k")
    assert "@peña" in str(e.value)
