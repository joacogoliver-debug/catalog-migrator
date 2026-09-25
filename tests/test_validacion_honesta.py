# -*- coding: utf-8 -*-
"""Que la validación diga lo que mira y lo que no. Sin red.

«Sin errores: el catálogo no tiene problemas que causen rechazo» se leía como
«lista para cargar», con los campos sin completar, el audio lossy y los códigos
dudosos adentro. Cubre:

  - el ruido de título, con los patrones que se escapaban y en el producto
  - UPC iguales escritos distinto, todo ceros, e ISRC normalizado al exportar
  - el modo de color de la portada
  - los avisos que faltaban, y lo que el reporte dice que no mira
"""

import csv
import io

import pytest

from conftest import _jpeg, _png, _producto, _track
from migrador import paquete as pq
from migrador import validar as V


def _cods(res, nivel=None):
    return [h["codigo"] for h in res["hallazgos"] if nivel is None or h["nivel"] == nivel]


@pytest.mark.parametrize(
    "titulo",
    [
        "Tema (Audio)",
        "Tema (Letra)",
        "Tema [Lyrics]",
        "Tema (Videoclip Oficial)",
        "Tema (Video Musical)",
        "Tema [MV]",
        "Tema (M/V)",
        "Tema (Official Visualiser)",
    ],
)
def test_los_patrones_que_se_escapaban(titulo):
    assert "titulo_con_ruido" in _cods(V.validar([_producto(tracks=[_track(titulo)])]))


def test_el_titulo_del_producto_tambien_se_revisa():
    res = V.validar([_producto(title="Disco (Official Video)", tracks=[_track("Tema")])])
    assert "titulo_con_ruido" in _cods(res)


def test_el_mismo_upc_de_12_y_de_13_digitos_es_duplicado():
    res = V.validar([_producto(title="A", upc="036000291452"), _producto(title="B", upc="0036000291452")])
    assert "upc_duplicado" in _cods(res, "error")


def test_un_upc_de_ceros_no_es_valido():
    assert V.upc_valido("000000000000")[0] is False
    assert V.upc_valido("0000000000000")[0] is False


def test_el_isrc_se_exporta_en_mayusculas_y_sin_guiones():
    p = _producto(title="Disco", tracks=[_track("Tema", isrc="us-rc1-76-07839")])
    fila = next(csv.DictReader(io.StringIO(pq.hoja_ingesta_csv([p], "Fulano"))))
    assert fila["ISRC"] == "USRC17607839"


def _png_tipo(tipo):
    datos = bytearray(_png(3000, 3000))
    datos[25] = tipo
    return bytes(datos)


@pytest.mark.parametrize(
    "datos, modo",
    [
        (lambda: _png_tipo(2), "rgb"),
        (lambda: _png_tipo(0), "gris"),
        (lambda: _png_tipo(3), "paleta"),
        (lambda: _png_tipo(6), "alfa"),
        (lambda: _jpeg(3000, 3000), "rgb"),
        (lambda: _jpeg(3000, 3000, comps=1), "gris"),
        (lambda: _jpeg(3000, 3000, comps=4), "cmyk"),
    ],
)
def test_el_modo_de_color_de_la_portada(datos, modo):
    assert V.modo_color(datos()) == modo


def test_una_portada_gris_o_transparente_se_avisa():
    for datos in (_png_tipo(0), _png_tipo(6), _jpeg(3000, 3000, comps=1)):
        res = V.validar([_producto(cover=datos, tracks=[_track("Tema")])])
        assert "portada_modo_color" in _cods(res, "aviso")
    res = V.validar([_producto(cover=_png_tipo(2), tracks=[_track("Tema")])])
    assert "portada_modo_color" not in _cods(res)


def test_un_isrc_de_confianza_media_se_avisa():
    t = _track("Tema", isrc="ARAAA2000001")
    t["match"] = "media"
    assert "isrc_confianza_media" in _cods(V.validar([_producto(tracks=[t])]), "aviso")


def test_el_audio_lossy_se_avisa_en_la_validacion(tmp_path):
    t = _track("Tema")
    t.update(audio_path=str(tmp_path / "a.m4a"), audio_format=".m4a")
    assert "audio_no_apto" in _cods(V.validar([_producto(tracks=[t])]), "aviso")


def test_los_campos_a_completar_se_dicen_una_vez():
    res = V.validar(
        [_producto(title="A", tracks=[_track("Uno")]), _producto(title="B", tracks=[_track("Dos")])]
    )
    assert _cods(res).count("campos_a_completar") == 1


def test_el_reporte_no_promete_aceptacion_y_dice_que_no_mira():
    res = V.validar([_producto(tracks=[_track("Tema")])])
    texto = V.reporte_validacion(res, "Fulano")
    assert "Sin errores de formato" in texto
    assert "garantía" in texto
    assert "NO mira" in texto
