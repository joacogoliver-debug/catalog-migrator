# -*- coding: utf-8 -*-
"""Normalización de texto y nombres de archivo. Sin red.

Estas funciones estaban escritas seis veces en cinco módulos, casi iguales pero
no del todo. Ahora hay una sola implementación de cada una, y el último test de
este archivo es el que impide que vuelvan a bifurcarse.
"""

import pytest

from migrador import audio
from migrador import paquete
from migrador import portadas
from migrador import productos
from migrador import texto


# ============================================================
# Los tres grados de normalización
# ============================================================


@pytest.mark.parametrize(
    "entrada, esperado",
    [
        ("Corazón Roto!", "Corazon Roto!"),
        ("Bebé", "Bebe"),
        ("ñandú", "nandu"),
        ("", ""),
        (None, ""),
    ],
)
def test_sin_acentos(entrada, esperado):
    """Conserva mayúsculas y puntuación. Es el grado más suave."""
    assert texto.sin_acentos(entrada) == esperado


def test_plegado_es_sin_acentos_mas_minusculas():
    assert texto.plegado("Corazón Roto!") == "corazon roto!"
    assert texto.plegado(None) == ""


@pytest.mark.parametrize(
    "entrada, esperado",
    [
        ("Corazón Roto!", "corazon roto"),
        ("Corazon   Roto", "corazon roto"),
        ("  ¿Qué Pasó?  ", "que paso"),
        ("", ""),
        (None, ""),
    ],
)
def test_comparable(entrada, esperado):
    """Sin acentos, en minúsculas, sin puntuación y con los espacios juntos."""
    assert texto.comparable(entrada) == esperado


def test_dos_titulos_que_son_el_mismo_comparan_igual():
    """Es lo que hace que un álbum escrito de dos formas se agrupe una sola vez."""
    assert texto.comparable("Corazón Roto!") == texto.comparable("Corazon Roto")


# ============================================================
# Nombres de archivo y de carpeta
# ============================================================


@pytest.mark.parametrize(
    "entrada, esperado",
    [
        ("Tema/Con:Barras*?", "TemaConBarras"),  # prohibidos en Windows
        ("Tema...", "Tema"),  # no puede terminar en punto
        ("Tema   con   espacios", "Tema con espacios"),
        ("Canción", "Cancion"),
    ],
)
def test_nombre_seguro(entrada, esperado):
    assert texto.nombre_seguro(entrada) == esperado


def test_nombre_vacio_cae_al_texto_de_reemplazo():
    assert texto.nombre_seguro("") == "sin-titulo"
    assert texto.nombre_seguro(None, fallback="Sin titulo") == "Sin titulo"


def test_el_recorte_no_puede_dejar_un_punto_al_final():
    """El bug que separaba a las dos versiones de esta función.

    `productos._slug` recortaba y después limpiaba sólo espacios, así que un
    título cuyo carácter número 60 fuera un punto dejaba una carpeta terminada
    en punto. Windows no la admite, y eso falla recién al descomprimir el ZIP,
    en la máquina de otro.
    """
    titulo = "A" * 59 + ". Segunda parte"
    salida = texto.nombre_seguro(titulo, maxlen=60)
    assert len(salida) <= 60
    assert not salida.endswith(".")
    assert not salida.endswith(" ")


def test_el_recorte_no_puede_dejar_un_espacio_al_final():
    salida = texto.nombre_seguro("A" * 59 + " Segunda parte", maxlen=60)
    assert not salida.endswith(" ")


# ============================================================
# Duración
# ============================================================


@pytest.mark.parametrize(
    "segundos, esperado",
    [(0, "0:00"), (5, "0:05"), (60, "1:00"), (200, "3:20"), (3661, "61:01"), (None, "0:00")],
)
def test_mmss(segundos, esperado):
    assert texto.mmss(segundos) == esperado


# ============================================================
# Que no se vuelvan a bifurcar
# ============================================================


def test_todos_los_modulos_usan_la_misma_normalizacion():
    """Éste es el test que sostiene el arreglo.

    Había tres `_norm` distintas: dos idénticas y una tercera, en `audio`, que
    no sacaba los acentos. Nada decía si la diferencia era a propósito, y no lo
    era: hacía que un artista escrito con tilde en YouTube no encontrara en
    Tidal al mismo escrito sin ella, y la búsqueda cayera al primero que Tidal
    devolviera, que es cualquiera.
    """
    assert productos._norm is texto.comparable
    assert portadas._norm is texto.comparable
    assert audio._norm is texto.comparable


def test_los_dos_slugs_salen_de_la_misma_funcion():
    """Difieren sólo en el largo y en el texto de reemplazo, que es lo que
    justifica que sean dos nombres y no uno."""
    assert productos._slug("Tema/Con:Barras") == texto.nombre_seguro("Tema/Con:Barras", 60, "Sin titulo")
    assert paquete._slug_archivo("Tema/Con:Barras") == texto.nombre_seguro(
        "Tema/Con:Barras", 80, "sin-titulo"
    )
    assert productos._slug("") == "Sin titulo"
    assert paquete._slug_archivo("") == "sin-titulo"


def test_el_empaquetado_no_depende_del_modulo_de_audio():
    """`paquete` importaba `audio` sólo por una constante.

    Armar el entregable es el núcleo y funciona en la variante esencial, que no
    trae el módulo de audio. Atarlos significaba que un import mal puesto allá
    rompiera esto, que ni siquiera lo usa.
    """
    import ast
    import os
    from conftest import PAQUETE

    ruta = os.path.join(PAQUETE, "paquete.py")
    arbol = ast.parse(open(ruta, encoding="utf-8").read())
    importados = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.ImportFrom) and nodo.module:
            importados.add(nodo.module.split(".")[0])
        elif isinstance(nodo, ast.Import):
            importados |= {a.name.split(".")[0] for a in nodo.names}

    assert "audio" not in importados
    assert paquete.FORMATOS_LOSSLESS == {".flac"}
