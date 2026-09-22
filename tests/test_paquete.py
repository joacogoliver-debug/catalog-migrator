# -*- coding: utf-8 -*-
"""Armado del entregable. Sin red.

Cubre lo que sostiene la confianza en el ZIP.
  - la estructura es una carpeta por producto
  - las planillas y el reporte están en la raíz
  - los audios lossy quedan marcados en el nombre, y la marca sigue al idioma
  - los audios lossless NO llevan esa marca
  - el reporte lista los pendientes reales, sin UPC, sin portada, sin audio
  - el reporte avisa fuerte cuando no hubo cuenta de Tidal
  - se respetan los checkboxes
  - el paquete entero sale en el idioma elegido, nombres de archivo incluidos
"""

import glob
import os
import zipfile

import pytest

from migrador import i18n
from migrador import paquete as pq
from conftest import PAQUETE


@pytest.fixture
def zip_completo(productos_entregable, tmp_path):
    """El ZIP armado con todo, y sus nombres ya leídos."""
    destino = str(tmp_path / "salida.zip")
    ruta, tam = pq.build_zip(
        productos_entregable, "Artista Test", destino, con_tidal=True, log=lambda *_: None
    )
    with zipfile.ZipFile(ruta) as z:
        nombres = z.namelist()
        raiz = nombres[0].split("/")[0]
        crudo = z.read(f"{raiz}/_Reporte de migracion.txt")
    return {
        "ruta": ruta,
        "tam": tam,
        "nombres": nombres,
        "raiz": raiz,
        "reporte_crudo": crudo,
        "reporte": crudo.decode("utf-8-sig"),
    }


# ============================================================
# Estructura
# ============================================================


def test_el_zip_existe_y_pesa(zip_completo):
    assert os.path.exists(zip_completo["ruta"])
    assert zip_completo["tam"] > 0


@pytest.mark.parametrize(
    "archivo",
    [
        "_LEEME.txt",
        "_Reporte de migracion.txt",
        "_Catalogo completo.xlsx",
    ],
)
def test_los_archivos_de_raiz_estan(zip_completo, archivo):
    assert f"{zip_completo['raiz']}/{archivo}" in zip_completo["nombres"]


@pytest.mark.parametrize("carpeta", ["2020 - Album Bueno [111]", "2021 - Single Flojo"])
def test_una_carpeta_por_producto_con_su_planilla(zip_completo, carpeta):
    assert f"{zip_completo['raiz']}/{carpeta}/datos.xlsx" in zip_completo["nombres"]


def test_la_portada_va_solo_donde_habia(zip_completo):
    raiz = zip_completo["raiz"]
    assert f"{raiz}/2020 - Album Bueno [111]/portada.jpg" in zip_completo["nombres"]
    assert f"{raiz}/2021 - Single Flojo/portada.jpg" not in zip_completo["nombres"]


# ============================================================
# Etiquetado de calidad
# ============================================================


def test_el_lossless_no_lleva_marca(zip_completo):
    esperado = f"{zip_completo['raiz']}/2020 - Album Bueno [111]/01 - Tema Lossless.flac"
    assert esperado in zip_completo["nombres"]


def test_el_lossy_queda_marcado_en_el_nombre(zip_completo):
    marca = i18n.T("paq.tag_lossy")
    esperado = f"{zip_completo['raiz']}/2021 - Single Flojo/01 - Tema Lossy {marca}.m4a"
    assert esperado in zip_completo["nombres"]


def test_un_track_sin_audio_no_genera_archivo(zip_completo):
    assert not any("Tema Sin Audio" in n for n in zip_completo["nombres"])


@pytest.mark.parametrize(
    "track, esperado",
    [
        ({"audio_path": "x", "audio_format": ".flac"}, "LOSSLESS (flac)"),
        ({"audio_path": "x", "audio_format": ".m4a"}, "LOSSY (m4a)"),
        ({}, "sin audio"),
    ],
)
def test_fuente_corta(track, esperado):
    assert pq._fuente_corta(track) == esperado


# ============================================================
# Reporte
# ============================================================


def test_el_reporte_va_con_bom_y_los_acentos_sobreviven(zip_completo):
    """Con BOM, para que Windows muestre bien los acentos."""
    assert zip_completo["reporte_crudo"].startswith(b"\xef\xbb\xbf")
    assert "MIGRACIÓN" in zip_completo["reporte"]


@pytest.mark.parametrize(
    "rotulo, valor",
    [
        ("Aptos para entrega (FLAC lossless)", 1),
        ("Sólo referencia (lossy)", 1),
        ("Sin audio", 1),
    ],
)
def test_el_reporte_cuenta_los_audios_por_calidad(zip_completo, rotulo, valor):
    """Se compara rótulo y valor sin fijar los espacios del medio. El reporte
    alinea con ljust y el ancho depende del largo de la palabra, que cambia con
    el idioma. Fijar la separación exacta hacía que el test dependiera de una
    decisión de maquetado."""
    assert any(
        x.strip().startswith(rotulo) and x.rstrip().endswith(f": {valor}")
        for x in zip_completo["reporte"].splitlines()
    )


@pytest.mark.parametrize(
    "pendiente",
    [
        "sin UPC",
        "sin portada",
        "orden de tracks sin confirmar",
        "tracks sin ISRC",
    ],
)
def test_el_reporte_lista_los_pendientes_reales(zip_completo, pendiente):
    assert pendiente in zip_completo["reporte"]


def test_avisa_fuerte_cuando_no_hubo_cuenta_de_tidal(productos_entregable):
    rep = pq.reporte_texto(productos_entregable, "Artista Test", con_tidal=False)
    assert "NO hay audio apto" in rep


def test_con_tidal_conectado_pero_con_lossy_avisa_lo_otro(zip_completo):
    assert "no tiene máster" in zip_completo["reporte"]


# ============================================================
# Los checkboxes de la pantalla 3
# ============================================================


def test_sin_audio_y_sin_portadas(productos_entregable, tmp_path):
    destino = str(tmp_path / "solo_planilla.zip")
    pq.build_zip(
        productos_entregable,
        "Artista Test",
        destino,
        incluir_audio=False,
        incluir_portadas=False,
        log=lambda *_: None,
    )
    with zipfile.ZipFile(destino) as z:
        nombres = z.namelist()

    assert not any(x.endswith((".flac", ".m4a")) for x in nombres)
    assert not any(x.endswith("portada.jpg") for x in nombres)
    assert any(x.endswith("_Catalogo completo.xlsx") for x in nombres)


def test_sin_planilla_el_reporte_igual_va(productos_entregable, tmp_path):
    """El reporte va siempre. Es lo que explica qué falta."""
    destino = str(tmp_path / "solo_audio.zip")
    pq.build_zip(productos_entregable, "Artista Test", destino, incluir_planilla=False, log=lambda *_: None)
    with zipfile.ZipFile(destino) as z:
        nombres = z.namelist()

    assert not any(x.endswith(".xlsx") for x in nombres)
    assert any("Reporte de migracion" in x for x in nombres)


# ============================================================
# Nombres de archivo
# ============================================================


@pytest.mark.parametrize(
    "titulo, esperado",
    [
        ("Tema/Con:Barras*?", "TemaConBarras"),
        ("Tema...", "Tema"),
        ("", "sin-titulo"),
    ],
)
def test_slug_de_archivo(titulo, esperado):
    assert pq._slug_archivo(titulo) == esperado


# ============================================================
# El paquete entero sigue al idioma
# ============================================================


@pytest.fixture
def zip_en_ingles(productos_entregable, tmp_path):
    """Es lo que se promete. Quien elige inglés abre el ZIP en inglés, nombres
    de archivo incluidos. La fixture `idioma_castellano` del conftest devuelve
    el idioma al terminar, así que no contamina lo que venga después."""
    i18n.poner_idioma("en")
    destino = str(tmp_path / "en.zip")
    pq.build_zip(productos_entregable, "Artista Test", destino, con_tidal=True, log=lambda *_: None)
    with zipfile.ZipFile(destino) as z:
        nombres = z.namelist()
        raiz = nombres[0].split("/")[0]
        leidos = {n.split("/")[-1]: z.read(n) for n in nombres if n.endswith(".txt") or n.endswith(".csv")}
    return {"nombres": nombres, "raiz": raiz, "leidos": leidos}


def test_la_carpeta_raiz_sale_en_ingles(zip_en_ingles):
    assert zip_en_ingles["raiz"].endswith(f"Migration {pq.date.today().isoformat()}")


@pytest.mark.parametrize(
    "archivo",
    [
        "_READ ME.txt",
        "_Migration report.txt",
        "_Pre-delivery validation.txt",
        "_Full catalog.xlsx",
        "_Ingestion sheet.csv",
    ],
)
def test_los_archivos_de_raiz_salen_en_ingles(zip_en_ingles, archivo):
    assert any(x.endswith(archivo) for x in zip_en_ingles["nombres"])


def test_los_archivos_de_cada_producto_salen_en_ingles(zip_en_ingles):
    assert any(x.endswith("/data.xlsx") for x in zip_en_ingles["nombres"])
    assert any(x.endswith("/cover.jpg") for x in zip_en_ingles["nombres"])


def test_el_reporte_en_ingles_no_arrastra_castellano(zip_en_ingles):
    rep = zip_en_ingles["leidos"]["_Migration report.txt"].decode("utf-8-sig")
    assert "MIGRATION REPORT" in rep
    assert "PENDIENTES" not in rep


def test_el_leeme_nombra_los_archivos_como_se_llaman_de_verdad(zip_en_ingles):
    """El LEEME se arma con los nombres de archivo adentro. Tienen que ser los
    mismos que los del ZIP, o manda a buscar lo que no existe."""
    leeme = zip_en_ingles["leidos"]["_READ ME.txt"].decode("utf-8-sig")
    assert "_Pre-delivery validation.txt" in leeme


def test_las_columnas_de_la_hoja_de_ingesta_no_se_traducen(zip_en_ingles):
    """Son los nombres de campo que espera la distribuidora, no texto para
    leer."""
    ing = zip_en_ingles["leidos"]["_Ingestion sheet.csv"].decode("utf-8-sig")
    assert ing.splitlines()[0].startswith("UPC,Release Title,Release Artist")


# ============================================================
# Los logs tienen que poder imprimirse en una consola de Windows
# ============================================================


def test_ningun_log_usa_caracteres_que_cp1252_no_puede_imprimir():
    """Los mensajes de log van a stdout, y la consola de Windows usa cp1252. Un
    caracter fuera de ese set (una flecha, por ejemplo) tira UnicodeEncodeError
    y corta la migración a mitad de camino.

    Mira el código fuente en vez de ejecutar los logs, porque las rutas que los
    emiten necesitan red y credenciales.
    """
    archivos = glob.glob(os.path.join(PAQUETE, "*.py"))
    assert len(archivos) >= 8, f"esperaba recorrer el paquete y encontré {archivos}"

    problemas = []
    for ruta in archivos:
        if os.path.basename(ruta).startswith("test_"):
            continue
        with open(ruta, encoding="utf-8") as f:
            for i, linea in enumerate(f, 1):
                if "log(" not in linea and "print(" not in linea:
                    continue
                for ch in linea:
                    if ord(ch) > 127:
                        try:
                            ch.encode("cp1252")
                        except UnicodeEncodeError:
                            problemas.append(f"{os.path.basename(ruta)}:{i} {ch!r}")
    assert problemas == []
