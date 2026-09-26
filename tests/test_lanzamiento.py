"""El material de lanzamiento: que esté listo y que cumpla las mismas reglas que la app.

La página de `docs/` y la imagen para redes no están publicadas: eso lo decide
quien administra el repositorio. Pero si mañana se activan, no pueden traer un
script, una fuente de un CDN ni un enlace de descarga que dé 404.
"""

import os
import re
import struct

import pytest

from test_readme import DESCARGA, _archivos_del_workflow

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGINAS = [os.path.join("docs", "index.html"), os.path.join("docs", "en.html")]


def _leer(ruta):
    with open(os.path.join(RAIZ, ruta), encoding="utf-8") as f:
        return f.read()


def test_la_imagen_para_redes_tiene_el_tamano_que_pide_github():
    with open(os.path.join(RAIZ, "docs", "redes", "social-preview.png"), "rb") as f:
        cabecera = f.read(24)
    assert cabecera[:8] == b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">II", cabecera[16:24]) == (1280, 640)


def test_la_imagen_se_arma_sin_nada_de_afuera():
    fuente = _leer(os.path.join("build", "imagen_redes.py"))
    html = fuente[fuente.index('HTML = """') : fuente.index('"""\n', fuente.index('HTML = """') + 10)]
    assert not re.search(r"(src|href)=\"https?://", html)


@pytest.mark.parametrize("pagina", PAGINAS)
def test_la_pagina_no_trae_scripts_ni_recursos_de_afuera(pagina):
    html = _leer(pagina)
    assert "<script" not in html, "sin scripts, como la app"
    # Lo que el navegador carga solo: estilos, imágenes, fuentes. Los enlaces
    # (<a href>) a GitHub son para que la persona haga clic, y ésos sí van.
    for etiqueta in re.findall(r"<(?:link|img|source)\b[^>]*>", html):
        assert not re.search(r"(src|href|srcset)=\"https?://", etiqueta), etiqueta
    assert "@import" not in html and "url(http" not in html


@pytest.mark.parametrize("pagina", PAGINAS)
def test_cada_descarga_de_la_pagina_existe_en_el_release(pagina):
    enlaces = re.findall(re.escape(DESCARGA) + r"([^\"\s]+)", _leer(pagina))
    assert enlaces
    publicados = _archivos_del_workflow()
    assert all(a in publicados for a in enlaces), enlaces


@pytest.mark.parametrize("pagina", PAGINAS)
def test_las_imagenes_de_la_pagina_existen(pagina):
    for ruta in re.findall(r"(?:src|srcset)=\"([^\"]+)\"", _leer(pagina)):
        assert os.path.exists(os.path.join(RAIZ, "docs", ruta)), ruta


def test_las_dos_paginas_se_nombran_entre_si():
    assert 'href="en.html"' in _leer(PAGINAS[0])
    assert 'href="index.html"' in _leer(PAGINAS[1])


@pytest.mark.parametrize("doc", ["LANZAMIENTO.md", "LANZAMIENTO.en.md"])
def test_el_material_dice_que_no_esta_publicado(doc):
    texto = _leer(os.path.join("docs", doc))
    assert ("no está publicado" if doc == "LANZAMIENTO.md" else "None of this is published") in texto
