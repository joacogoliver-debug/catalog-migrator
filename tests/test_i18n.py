# -*- coding: utf-8 -*-
"""Los dos catálogos de traducción, completos y de acuerdo entre sí.

La app tiene dos catálogos, uno por proceso. `i18n.py` para lo que arma Python
(el log, los errores, los archivos del ZIP) y `app/web/i18n.js` para la
interfaz. Son dos porque son dos procesos, y eso abre tres formas de romperlos
que no se ven hasta que alguien abre la app en inglés.

  - una clave traducida al español y no al inglés, que sale en español sin avisar
  - una clave que la interfaz usa y el catálogo no define, que sale como
    "paso2.titulo" en la pantalla
  - el nombre de un archivo del ZIP que la interfaz nombra distinto de como lo
    escribe `paquete.py`, que manda a buscar algo que no existe

Este archivo cubre las tres.
"""

import io
import os
import re

import pytest

import i18n
from conftest import RAIZ


def _leer(*partes):
    return io.open(os.path.join(RAIZ, *partes), encoding="utf-8").read()


@pytest.fixture(scope="module")
def catalogo_js():
    """Las entradas de `app/web/i18n.js`, como {clave: {es: bool, en: bool}}.

    Se parsea con expresiones regulares y no con un motor de JS. El archivo es
    un objeto literal plano y meter una dependencia para leerlo sería peor que
    el problema que resuelve.
    """
    s = _leer("app", "web", "i18n.js")
    cuerpo = s[s.index("const TEXTOS = {") :]
    entradas = {}

    def anotar(clave, bloque):
        entradas[clave] = {
            "es": bool(re.search(r"\bes:\s*[`'\"]", bloque)),
            "en": bool(re.search(r"\ben:\s*[`'\"]", bloque)),
        }

    # Las de una sola línea, 'clave': { es: '...', en: '...' },
    for m in re.finditer(r"^  '([a-z0-9_.]+)':\s*\{([^\n]*)\},$", cuerpo, re.M):
        anotar(m.group(1), m.group(2))

    # Las de varias líneas. El `\{\n` no es adorno: sin él, una entrada de una
    # sola línea abría un match que seguía leyendo hasta el próximo `  },` y se
    # tragaba enteras las entradas del medio, que entonces figuraban como no
    # definidas.
    for m in re.finditer(r"^  '([a-z0-9_.]+)':\s*\{\n(.*?)^  \},", cuerpo, re.S | re.M):
        anotar(m.group(1), m.group(2))

    return entradas


@pytest.fixture(scope="module")
def claves_usadas_en_la_interfaz():
    app = _leer("app", "web", "app.js")
    html = _leer("app", "web", "index.html")
    usadas = set(re.findall(r"T\(\s*'([a-z0-9_.]+)'", app))
    usadas |= set(re.findall(r'data-t(?:-title|-aria)?="([a-z0-9_.]+)"', html))
    # Las que se arman concatenando un prefijo con un código.
    cods = re.search(r"const CODIGOS_HALLAZGO = \[(.*?)\];", app, re.S)
    assert cods, "app.js ya no declara CODIGOS_HALLAZGO"
    usadas |= {"hallazgo." + c for c in re.findall(r"'(\w+)'", cods.group(1))}
    usadas |= {"stepper." + p for p in ("paso1", "paso2", "paso3", "paso4")}
    # Las que se eligen con un ternario adentro del propio T(...). Se exige el
    # `T(` delante: sin eso entraban ternarios que no tienen nada que ver, como
    # el que elige entre los iconos 'sol' y 'luna'.
    for a, b in re.findall(r"T\([^)]*?\?\s*'([a-z0-9_.]+)'\s*:\s*'([a-z0-9_.]+)'", app):
        usadas |= {a, b}
    # Los prefijos sueltos son artefactos de la concatenación, no claves.
    return {k for k in usadas if not k.endswith(".")}


# ============================================================
# Catálogo de Python
# ============================================================


def test_ninguna_clave_a_medio_traducir_en_python():
    assert i18n.claves_sin_traducir("es", "en") == []
    assert i18n.claves_sin_traducir("en", "es") == []


def test_el_catalogo_de_python_no_esta_vacio():
    assert len(i18n.TEXTOS) > 100


def test_ninguna_clave_definida_dos_veces_en_python():
    """Un diccionario se come las claves repetidas sin decir nada. La última
    gana y la primera desaparece. Como las dos entradas suelen ser parecidas, el
    texto sigue saliendo en el idioma correcto y la única señal es que cambió
    una palabra. Por eso se lee el archivo y no el diccionario ya construido, en
    el que la duplicada ya no existe."""
    fuente = _leer("i18n.py")
    cuerpo = fuente[fuente.index("TEXTOS = {") :]
    literales = re.findall(r'^    "([a-z0-9_.]+)":', cuerpo, re.M)
    repetidas = sorted({k for k in literales if literales.count(k) > 1})
    assert repetidas == []


def test_el_formato_no_se_rompe_al_traducir():
    """Una clave cuyo texto en inglés se olvida un {parametro} que el español sí
    tiene deja un hueco en la frase, y al revés revienta el format()."""
    desparejas = {}
    for clave, entrada in i18n.TEXTOS.items():
        pes = set(re.findall(r"\{(\w+)\}", entrada.get("es", "")))
        pen = set(re.findall(r"\{(\w+)\}", entrada.get("en", "")))
        if pes != pen:
            desparejas[clave] = (sorted(pes), sorted(pen))
    assert desparejas == {}


# ============================================================
# Catálogo de la interfaz
# ============================================================


def test_el_catalogo_de_la_interfaz_no_esta_vacio(catalogo_js):
    assert len(catalogo_js) > 100


def test_ninguna_clave_a_medio_traducir_en_la_interfaz(catalogo_js):
    sin_en = sorted(k for k, v in catalogo_js.items() if v["es"] and not v["en"])
    sin_es = sorted(k for k, v in catalogo_js.items() if v["en"] and not v["es"])
    assert sin_en == []
    assert sin_es == []


def test_la_interfaz_no_usa_claves_sin_definir(catalogo_js, claves_usadas_en_la_interfaz):
    assert sorted(claves_usadas_en_la_interfaz - set(catalogo_js)) == []


def test_el_catalogo_de_la_interfaz_no_tiene_claves_de_mas(catalogo_js, claves_usadas_en_la_interfaz):
    assert sorted(set(catalogo_js) - claves_usadas_en_la_interfaz) == []


def test_ninguna_clave_definida_dos_veces_en_la_interfaz():
    fuente = _leer("app", "web", "i18n.js")
    cuerpo = fuente[fuente.index("const TEXTOS = {") :]
    literales = re.findall(r"^  '([a-z0-9_.]+)':", cuerpo, re.M)
    repetidas = sorted({k for k in literales if literales.count(k) > 1})
    assert repetidas == []


# ============================================================
# Los dos catálogos, de acuerdo
# ============================================================


@pytest.mark.parametrize("idioma", ["es", "en"])
def test_el_nombre_del_informe_de_validacion_coincide_de_los_dos_lados(idioma):
    """La pantalla 4 manda a abrir el informe de validación por su nombre. Si
    `paquete.py` lo escribe distinto, manda a buscar un archivo que no existe."""
    s = _leer("app", "web", "i18n.js")
    bloque = re.search(r"'archivos\.validacion':\s*\{(.*?)\},", s, re.S)
    assert bloque, "i18n.js ya no define archivos.validacion"
    en_js = re.search(rf"{idioma}:\s*'([^']+)'", bloque.group(1))
    assert en_js, f"archivos.validacion no tiene el texto en {idioma}"

    i18n.poner_idioma(idioma)
    assert en_js.group(1) == i18n.T("paq.f_validacion")
