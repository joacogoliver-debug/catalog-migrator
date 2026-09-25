# -*- coding: utf-8 -*-
"""Ningún texto para el usuario escrito a mano fuera de los catálogos. Sin red.

El progreso de los trabajos («Listo.», «Preparando», «productos encontrados») y
el log del módulo de audio estaban escritos en castellano en el código, y con la
app en inglés se veían igual. `test_i18n` cuida los catálogos; éste cuida que no
se escriba texto por fuera de ellos, leyendo el código fuente:

  - nada de literales en el avance de un trabajo ni en su mensaje
  - nada de literales en el log del módulo de audio
"""

import ast
import os
import re

import pytest

from conftest import PAQUETE, RAIZ


def _arbol(*partes):
    with open(os.path.join(*partes), encoding="utf-8") as f:
        return ast.parse(f.read())


# Las etiquetas técnicas del log («[yt]», «[tidal]») no son idioma: no hay nada
# que traducir en ellas. Lo que se busca son palabras.
_RE_ETIQUETA = re.compile(r"\[[a-z]+\]")


def _tiene_palabras(texto):
    return any(c.isalpha() for c in _RE_ETIQUETA.sub("", texto))


def _es_texto(nodo):
    """Un literal con palabras: un str o un f-string con partes fijas."""
    if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str):
        return _tiene_palabras(nodo.value)
    if isinstance(nodo, ast.JoinedStr):
        return any(isinstance(v, ast.Constant) and _tiene_palabras(str(v.value)) for v in nodo.values)
    return False


@pytest.mark.parametrize("archivo", ["jobs.py", "server.py"])
def test_el_progreso_de_un_trabajo_sale_del_catalogo(archivo):
    malos = []
    for nodo in ast.walk(_arbol(RAIZ, "app", archivo)):
        if isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Attribute) and nodo.func.attr == "avance":
            if nodo.args and _es_texto(nodo.args[0]):
                malos.append(nodo.lineno)
        if isinstance(nodo, ast.Assign):
            for destino in nodo.targets:
                if isinstance(destino, ast.Attribute) and destino.attr == "mensaje" and _es_texto(nodo.value):
                    malos.append(nodo.lineno)
    assert malos == [], f"{archivo}: texto fijo en las líneas {malos}"


def test_el_log_del_audio_sale_del_catalogo():
    malos = [
        nodo.lineno
        for nodo in ast.walk(_arbol(PAQUETE, "audio.py"))
        if isinstance(nodo, ast.Call)
        and isinstance(nodo.func, ast.Name)
        and nodo.func.id == "log"
        and nodo.args
        and _es_texto(nodo.args[0])
    ]
    assert malos == [], f"audio.py: texto fijo en el log, líneas {malos}"


def test_la_pantalla_fatal_no_tiene_texto_propio():
    with open(os.path.join(RAIZ, "app", "web", "app.js"), encoding="utf-8") as f:
        assert "'error desconocido'" not in f.read()
