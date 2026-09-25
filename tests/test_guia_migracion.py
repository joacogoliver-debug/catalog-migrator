"""Lo que el paquete le dice a quien migra, además de los datos.

Una migración tiene una regla que pesa más que cualquier columna: conservar el
ISRC, el UPC y la fecha original, y dar de baja la distribuidora vieja recién
cuando la nueva está en vivo. Nada lo decía, y la pantalla 2 empujaba a aceptar
códigos nuevos. Estos tests fijan que el LEEME del ZIP lo diga en los dos
idiomas, y que no llame «máster» a la copia que sirve Tidal.
"""

import pytest

import server as backend
from migrador import i18n
from migrador import paquete as PQ


@pytest.fixture(params=["es", "en"])
def leeme(request):
    anterior = i18n.idioma()
    i18n.poner_idioma(request.param)
    try:
        yield request.param, PQ.leeme()
    finally:
        i18n.poner_idioma(anterior)


def test_el_leeme_explica_por_que_conservar_los_codigos(leeme):
    idioma, texto = leeme
    titulo = "ANTES DE DAR DE BAJA" if idioma == "es" else "BEFORE TAKING THE CATALOG DOWN"
    assert titulo in texto
    for codigo in ("ISRC", "UPC"):
        assert codigo in texto


def test_la_baja_va_despues_de_que_el_nuevo_este_en_vivo(leeme):
    """El orden es lo que importa: pedir, completar, cargar, y la baja al final."""
    idioma, texto = leeme
    seccion = texto[texto.index("ANTES DE DAR DE BAJA" if idioma == "es" else "BEFORE TAKING") :]
    pasos = [seccion.index(f"  {n}. ") for n in (1, 2, 3, 4)]
    assert pasos == sorted(pasos)
    ultimo = seccion[pasos[3] :].split("\n\n")[0]
    assert ("baja" if idioma == "es" else "take it down") in ultimo


def test_el_leeme_no_llama_master_a_la_copia_de_tidal(leeme):
    idioma, texto = leeme
    linea = next(renglon for renglon in texto.splitlines() if "LOSSLESS (flac)" in renglon)
    assert ("Máster lossless" if idioma == "es" else "Lossless master") not in linea
    assert "Tidal" in linea


def test_los_nombres_de_archivo_del_leeme_se_completan(leeme):
    """La sección nueva nombra archivos del paquete: tienen que salir con su
    nombre, no como `{reporte}`."""
    _idioma, texto = leeme
    assert "{" not in texto


@pytest.mark.parametrize(
    ("plataforma", "esperado"),
    [("win32", "windows"), ("darwin", "mac"), ("linux", "linux"), ("freebsd14", "linux")],
)
def test_la_config_dice_el_sistema_para_dar_la_instruccion_que_corresponde(monkeypatch, plataforma, esperado):
    monkeypatch.setattr(backend.sys, "platform", plataforma)
    assert backend.sistema() == esperado
