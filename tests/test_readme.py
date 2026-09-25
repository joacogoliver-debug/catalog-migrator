"""El README como página de entrada: que lo que promete se pueda verificar.

Los enlaces de descarga apuntan a `releases/latest/download/<archivo>`, que
sirve para siempre porque los nombres no llevan versión. Pero sólo si el
archivo existe: un nombre mal escrito es un 404 justo en el primer clic. Acá se
arman los nombres que produce el workflow y se comparan con los del README.
"""

import os
import re

import pytest
import yaml

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESCARGA = "https://github.com/joacogoliver-debug/catalog-migrator/releases/latest/download/"


def _leer(*partes):
    with open(os.path.join(RAIZ, *partes), encoding="utf-8") as f:
        return f.read()


def _archivos_del_workflow():
    """Los nombres que publica `build.yml`, sin versión."""
    wf = yaml.safe_load(_leer(".github", "workflows", "build.yml"))
    matriz = wf["jobs"]["build"]["strategy"]["matrix"]
    nombres = set()
    for inc in matriz["include"]:
        for variante in matriz["variante"]:
            base = f"Migrador-de-Catalogos-{inc['nombre']}-{variante}"
            if inc["nombre"] == "windows":
                nombres |= {base + ".exe", base + "-instalador.exe"}
            else:
                nombres.add(base)
                if inc["nombre"].startswith("macos"):
                    nombres.add(base + "-app.zip")
    return nombres


@pytest.mark.parametrize("readme", ["README.md", "README.en.md"])
def test_cada_enlace_de_descarga_existe_en_el_release(readme):
    enlaces = re.findall(re.escape(DESCARGA) + r"([^)\s]+)", _leer(readme))
    assert enlaces, "el README tiene que llevar a la descarga directa"
    publicados = _archivos_del_workflow()
    for archivo in enlaces:
        assert archivo in publicados, f"{readme}: {archivo} no lo publica el workflow"


def test_los_dos_readme_llevan_a_los_mismos_archivos():
    es = re.findall(re.escape(DESCARGA) + r"([^)\s]+)", _leer("README.md"))
    en = re.findall(re.escape(DESCARGA) + r"([^)\s]+)", _leer("README.en.md"))
    assert es == en


@pytest.mark.parametrize("readme", ["README.md", "README.en.md"])
def test_ningun_comando_nombra_una_version_vieja(readme):
    """El `.deb` es el único con versión en el nombre, y el comando tiene que
    servir para cualquiera."""
    assert not re.search(r"migrador-catalogos_\d+\.\d+\.\d+", _leer(readme))


@pytest.mark.parametrize(
    ("readme", "secciones"),
    [
        ("README.md", ["## Para quién es", "## Descargar", "## Preguntas frecuentes", "## Si algo no anda"]),
        (
            "README.en.md",
            [
                "## Who it is for",
                "## Download",
                "## Frequently asked questions",
                "## If something does not work",
            ],
        ),
    ],
)
def test_lo_de_quien_usa_la_app_va_antes_que_lo_tecnico(readme, secciones):
    texto = _leer(readme)
    tecnico = texto.index(
        "## Correrla desde el código" if readme == "README.md" else "## Running it from source"
    )
    for s in secciones:
        assert s in texto, f"{readme}: falta {s}"
        assert texto.index(s) < tecnico, f"{readme}: {s} quedó después de lo técnico"


@pytest.mark.parametrize("archivo", ["README.md", "README.en.md", os.path.join("app", "web", "i18n.js")])
def test_sin_cifras_de_cupo_que_nadie_midio(archivo):
    """«Unos 500 catálogos por día» no salía de ninguna cuenta: depende del
    tamaño de cada canal y de si hubo que buscar el Topic."""
    assert not re.search(r"500 (catálogos|catalogs)", _leer(archivo))
