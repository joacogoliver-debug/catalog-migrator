# -*- coding: utf-8 -*-
"""Que las dependencias estén escritas una sola vez. Sin red.

Viven en dos lados a propósito. Los `requirements-*.txt` son la fuente: están
comentados, explican por qué hace falta cada cosa, y son lo que lee quien quiere
entender qué necesita la app sin saber de empaquetado. Los extras de
`pyproject.toml` los espejan, para que `pip install -e .[dev]` funcione.

Dos listas de dependencias que se separan es la forma clásica de que un build
ande en una máquina y no en otra, y de que el CI instale algo distinto de lo que
instala una persona. Esto lo impide.
"""

import re
import tomllib

import pytest

from conftest import RAIZ

# Cada extra de pyproject y el archivo que tiene que espejar.
PARES = [
    ("app", "requirements-app.txt"),
    ("audio", "requirements-audio.txt"),
    ("dev", "requirements-dev.txt"),
]


def _nombre(spec):
    """El nombre del paquete, sin la restricción de versión ni los extras."""
    return re.split(r"[<>=!~\[]", spec, maxsplit=1)[0].strip().lower().replace("_", "-")


def _del_requirements(nombre_archivo):
    with open(f"{RAIZ}/{nombre_archivo}", encoding="utf-8") as f:
        lineas = [linea.split("#", 1)[0].strip() for linea in f]
    return {linea for linea in lineas if linea}


@pytest.fixture(scope="module")
def extras():
    with open(f"{RAIZ}/pyproject.toml", "rb") as f:
        datos = tomllib.load(f)
    return datos["project"]["optional-dependencies"]


@pytest.mark.parametrize("extra, archivo", PARES)
def test_el_extra_y_el_requirements_piden_los_mismos_paquetes(extras, extra, archivo):
    del_toml = {_nombre(x) for x in extras[extra]}
    del_txt = {_nombre(x) for x in _del_requirements(archivo)}
    assert del_toml == del_txt


@pytest.mark.parametrize("extra, archivo", PARES)
def test_y_con_las_mismas_versiones(extras, extra, archivo):
    """No alcanza con que coincidan los nombres. Un `ruff==0.16.8` en un lado y
    un `ruff` suelto en el otro dan builds distintos, y el que falla es el que
    nadie mira."""
    normal = {x.strip().lower().replace("_", "-").replace(" ", "") for x in extras[extra]}
    del_txt = {x.strip().lower().replace("_", "-").replace(" ", "") for x in _del_requirements(archivo)}
    assert normal == del_txt


def test_el_nucleo_no_declara_dependencias(extras):
    """Relevar, agrupar y validar se hacen con la biblioteca estándar. Si algún
    día eso deja de ser cierto, que sea una decisión y no un descuido."""
    with open(f"{RAIZ}/pyproject.toml", "rb") as f:
        datos = tomllib.load(f)
    assert datos["project"]["dependencies"] == []


def test_los_tres_extras_existen(extras):
    assert set(extras) == {"app", "audio", "dev"}


# ============================================================
# Que el README no se quede atrás
# ============================================================


@pytest.mark.parametrize("readme", ["README.md", "README.en.md"])
def test_el_readme_nombra_todos_los_archivos_de_test(readme):
    """La tabla del README es una promesa de qué cubre la suite.

    Un archivo de test nuevo que no aparece ahí no es grave, pero la tabla deja
    de servir para saber qué hay, que es su único propósito. Ya pasó dos veces.
    """
    import os
    import re

    with open(f"{RAIZ}/{readme}", encoding="utf-8") as f:
        declarados = set(re.findall(r"`(tests/[\w.]+\.py)`", f.read()))
    reales = {f"tests/{n}" for n in os.listdir(f"{RAIZ}/tests") if n.endswith(".py")}

    assert sorted(reales - declarados) == []


@pytest.mark.parametrize("readme", ["README.md", "README.en.md"])
def test_el_readme_nombra_todos_los_modulos_del_paquete(readme):
    import os
    import re

    with open(f"{RAIZ}/{readme}", encoding="utf-8") as f:
        texto = f.read()
    declarados = set(re.findall(r"`(src/migrador/[\w.]+\.py)`", texto))
    reales = {
        f"src/migrador/{n}"
        for n in os.listdir(f"{RAIZ}/src/migrador")
        if n.endswith(".py") and n != "__init__.py"
    }

    assert sorted(reales - declarados) == []
    # Y al revés: la tabla no puede nombrar algo que ya no está.
    assert sorted(declarados - reales) == []
