# -*- coding: utf-8 -*-
"""Las notas del release, que salen del CHANGELOG. Sin red.

El bloque que las escribía estaba a mano adentro del workflow, en dos idiomas y
sin decir qué había cambiado. Ahora se arman con `build/notas_release.py`, y lo
que más importa probar es el control que aborta cuando el CHANGELOG no tiene una
entrada para la versión que se está publicando: sin eso, un tag apurado produce
un release que miente, y eso se descubre ya publicado.
"""

import re

import pytest

import notas_release
import server as backend

VERSION_PUBLICADA = "1.0.2"
REPO = "joacogoliver-debug/catalog-migrator"


def test_la_version_sale_de_un_solo_lugar():
    """`build/build.py`, el instalador y las notas leen esta misma función."""
    assert notas_release.version() == backend.VERSION


# ============================================================
# Leer el CHANGELOG
# ============================================================


@pytest.mark.parametrize("archivo", ["CHANGELOG.md", "CHANGELOG.en.md"])
def test_encuentra_la_seccion_de_una_version_publicada(archivo):
    seccion = notas_release.seccion_changelog(archivo, VERSION_PUBLICADA)
    assert seccion
    # Trae el cuerpo, no el encabezado de la siguiente versión.
    assert "## [" not in seccion


@pytest.mark.parametrize("archivo", ["CHANGELOG.md", "CHANGELOG.en.md"])
def test_no_inventa_una_seccion_que_no_existe(archivo):
    assert notas_release.seccion_changelog(archivo, "9.9.9") is None


def test_los_enlaces_de_referencia_del_pie_no_entran():
    """En el repositorio sirven; en el release el número de versión ya es el
    título de la página."""
    seccion = notas_release.seccion_changelog("CHANGELOG.md", VERSION_PUBLICADA)
    assert seccion
    assert not re.search(r"^\[[^\]]+\]:\s*https?://", seccion, re.M)


# ============================================================
# Enlaces
# ============================================================


def test_absolutizar_convierte_los_relativos():
    salida = notas_release.absolutizar("[guía](docs/INSTALAR-MAC.md)", REPO)
    assert salida == f"[guía](https://github.com/{REPO}/blob/main/docs/INSTALAR-MAC.md)"


@pytest.mark.parametrize(
    "enlace",
    [
        "[x](https://ejemplo.com/a)",
        "[x](http://ejemplo.com/a)",
        "[x](#una-seccion)",
        "[x](mailto:alguien@ejemplo.com)",
    ],
)
def test_absolutizar_no_toca_los_que_ya_funcionan(enlace):
    assert notas_release.absolutizar(enlace, REPO) == enlace


def test_las_notas_no_dejan_ningun_enlace_relativo():
    """Un enlace relativo en el cuerpo de un release lo resuelve GitHub contra
    la URL del release, y termina en un 404."""
    cuerpo = notas_release.notas(VERSION_PUBLICADA, REPO)
    relativos = [
        d
        for _t, d in re.findall(r"\[([^\]]+)\]\(([^)\s]+)\)", cuerpo)
        if not d.startswith(("http://", "https://", "#", "mailto:"))
    ]
    assert relativos == []


# ============================================================
# El cuerpo completo
# ============================================================


def test_las_notas_traen_lo_que_cambio_y_tambien_como_bajarlo():
    cuerpo = notas_release.notas(VERSION_PUBLICADA, REPO)

    assert "## Qué cambió" in cuerpo
    assert "## What changed" in cuerpo
    assert "## Cuál bajar" in cuerpo
    assert "## Which one to download" in cuerpo
    assert "# In English" in cuerpo

    # Y lo del CHANGELOG está de verdad adentro, no sólo el título.
    seccion = notas_release.seccion_changelog("CHANGELOG.md", VERSION_PUBLICADA)
    assert seccion
    primera = seccion.splitlines()[0]
    assert primera in cuerpo


def _en_una_linea(texto):
    """La prosa viene envuelta a 79 columnas, así que una frase puede estar
    partida en dos renglones. Para buscarla hay que juntar los espacios."""
    return re.sub(r"\s+", " ", texto)


@pytest.mark.parametrize(
    "frase",
    [
        # Lo que más consultas genera, y sacarlo del release sería deshonesto.
        "el binario no está firmado",
        "the binary is not signed",
        # Y la advertencia sobre la clave incluida en la variante completa.
        "cualquiera que baje el binario la puede extraer",
        "anyone who downloads the binary can extract it",
    ],
)
def test_las_notas_no_pierden_las_advertencias(frase):
    cuerpo = _en_una_linea(notas_release.notas(VERSION_PUBLICADA, REPO))
    assert frase in cuerpo


def test_publicar_sin_entrada_en_el_changelog_aborta():
    """El control que justifica todo esto. Sin él, taguear con el CHANGELOG
    todavía en «Sin publicar» produce un release que no dice qué cambió."""
    with pytest.raises(SystemExit) as exc:
        notas_release.notas("9.9.9", REPO)

    mensaje = str(exc.value)
    assert "CHANGELOG.md" in mensaje
    assert "CHANGELOG.en.md" in mensaje
    assert "9.9.9" in mensaje


# ============================================================
# La prosa fija
# ============================================================


@pytest.mark.parametrize("archivo", ["es.md", "en.md"])
def test_la_prosa_solo_usa_el_marcador_del_repositorio(archivo):
    """Se interpola con `str.format`, así que una llave suelta en el texto haría
    fallar la publicación, y recién al taguear."""
    import os

    with open(os.path.join(notas_release.NOTAS, archivo), encoding="utf-8") as f:
        prosa = f.read()

    campos = set(re.findall(r"\{(\w*)\}", prosa))
    assert campos <= {"repo"}, campos
    prosa.format(repo=REPO)  # no tiene que levantar
