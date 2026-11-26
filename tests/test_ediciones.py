# -*- coding: utf-8 -*-
"""Lo que el usuario carga a mano: un código, o los campos que nadie más trae.

Lo que importa acá es que nada entre sin validar, que todo quede dicho como
cargado a mano, y que se pueda volver atrás sin perder lo que había.
"""

import csv
import io

import pytest

from migrador import ediciones as ED
from migrador import paquete as PQ
from migrador import validar as V

UPC_A = "0885012345673"
UPC_B = "0885012345680"


def _catalogo(hacer_producto, hacer_track):
    a = hacer_track(track="Uno", isrc="ARAAA2000001", dur=200)
    a["isrc_como"], a["isrc_nivel"], a["match"] = "busqueda", "confirmado", "alta"
    b = hacer_track(track="Dos", dur=210)
    p = hacer_producto(title="Disco", upc=UPC_A, tracks=[a, b])
    p["upc_nivel"] = "confirmado"
    q = hacer_producto(title="Otro", upc="", tracks=[hacer_track(track="Tres", dur=220)])
    q["product_id"] = "p002"
    return [p, q]


# ============================================================
# ISRC
# ============================================================


def test_poner_un_isrc_lo_normaliza_y_lo_marca_manual(hacer_producto, hacer_track):
    ps = _catalogo(hacer_producto, hacer_track)
    t = ED.poner_isrc(ps, "p001", 1, "ar-bbb-21-00002")
    assert (t["isrc"], t.get("isrc_nivel"), t.get("isrc_como")) == ("ARBBB2100002", "manual", "manual")


@pytest.mark.parametrize(
    "malo", ["ARAAA200000", "12AAA2000001", "ARAAA20000011", "no es un isrc", "ARAAA20O0001"]
)
def test_un_isrc_mal_formado_se_rechaza_y_no_cambia_nada(hacer_producto, hacer_track, malo):
    """El formato inválido es el rechazo más común de una hoja de ingesta: se
    para acá, donde se puede corregir, y no en la distribuidora."""
    ps = _catalogo(hacer_producto, hacer_track)
    with pytest.raises(ED.EdicionInvalida):
        ED.poner_isrc(ps, "p001", 1, malo)
    assert ps[0]["tracks"][1]["isrc"] == ""
    assert "isrc_previo" not in ps[0]["tracks"][1]


def test_restaurar_devuelve_el_codigo_y_su_nivel(hacer_producto, hacer_track):
    """Un código confirmado que se cambia y se deshace vuelve confirmado, no
    «inferido»: deshacer no puede dejar el dato peor de lo que estaba."""
    ps = _catalogo(hacer_producto, hacer_track)
    ED.poner_isrc(ps, "p001", 0, "ARZZZ9900009")
    ED.poner_isrc(ps, "p001", 0, "ARYYY9800008")  # dos cambios seguidos
    t = ED.restaurar_isrc(ps, "p001", 0)
    assert (t["isrc"], t.get("isrc_nivel"), t.get("isrc_como"), t["match"]) == (
        "ARAAA2000001",
        "confirmado",
        "busqueda",
        "alta",
    )
    assert "isrc_previo" not in t


def test_poner_un_isrc_vacio_es_deshacer(hacer_producto, hacer_track):
    ps = _catalogo(hacer_producto, hacer_track)
    ED.poner_isrc(ps, "p001", 1, "ARBBB2100002")
    t = ED.poner_isrc(ps, "p001", 1, "  ")
    assert t["isrc"] == "" and "isrc_nivel" not in t


def test_un_producto_o_un_tema_que_no_existe_se_dice(hacer_producto, hacer_track):
    ps = _catalogo(hacer_producto, hacer_track)
    for pid, indice in (("p999", 0), ("p001", 5), ("p001", -1), ("p001", "x")):
        with pytest.raises(ED.EdicionInvalida):
            ED.poner_isrc(ps, pid, indice, "ARBBB2100002")


def test_el_producto_recuenta_los_isrc_sin_confirmar(hacer_producto, hacer_track):
    ps = _catalogo(hacer_producto, hacer_track)
    ps[0]["tracks"][0]["isrc_nivel"] = "inferido"
    ED.poner_isrc(ps, "p001", 0, "ARBBB2100002")
    assert ps[0]["isrc_sin_confirmar"] == 0


# ============================================================
# UPC
# ============================================================


def test_poner_un_upc_valida_el_digito_verificador(hacer_producto, hacer_track):
    ps = _catalogo(hacer_producto, hacer_track)
    with pytest.raises(ED.EdicionInvalida):
        ED.poner_upc(ps, "p002", "0885012345678")  # el último dígito no cierra
    assert ps[1]["upc"] == ""
    p = ED.poner_upc(ps, "p002", " 0885-0123-45680 ")
    assert (p["upc"], p.get("upc_nivel")) == (UPC_B, "manual")


def test_el_upc_nuevo_va_a_la_carpeta_del_producto(hacer_producto, hacer_track):
    ps = _catalogo(hacer_producto, hacer_track)
    ED.poner_upc(ps, "p002", UPC_B)
    assert ps[1]["folder"].endswith(f"[{UPC_B}]")


def test_restaurar_el_upc(hacer_producto, hacer_track):
    ps = _catalogo(hacer_producto, hacer_track)
    ED.poner_upc(ps, "p001", UPC_B)
    p = ED.restaurar_upc(ps, "p001")
    assert (p["upc"], p.get("upc_nivel")) == (UPC_A, "confirmado")
    assert p["folder"].endswith(f"[{UPC_A}]")


def test_un_upc_cargado_a_mano_que_repite_otro_lo_atrapa_la_validacion(hacer_producto, hacer_track):
    """No se rechaza al cargarlo (puede ser el mismo release en dos
    distribuidoras), pero no pasa sin que se diga."""
    ps = _catalogo(hacer_producto, hacer_track)
    ED.poner_upc(ps, "p002", UPC_A)
    assert "upc_duplicado" in {h["codigo"] for h in V.validar(ps)["hallazgos"]}


# ============================================================
# Los campos a completar
# ============================================================


def _fila(ps, columna, n=0):
    filas = list(csv.reader(io.StringIO(PQ.hoja_ingesta_csv(ps, "Artista", False, False))))
    return filas[1 + n][filas[0].index(columna)]


def test_lo_cargado_llega_a_la_hoja_de_ingesta(hacer_producto, hacer_track):
    ps = _catalogo(hacer_producto, hacer_track)
    assert _fila(ps, "Genre") == "<<COMPLETAR>>"
    n = ED.poner_datos(ps, ["p001"], {"genre": "  Cuarteto ", "explicit": "No", "c_line": "© 2020 Sello"})
    assert n == 1
    assert (_fila(ps, "Genre"), _fila(ps, "Explicit"), _fila(ps, "C Line")) == (
        "Cuarteto",
        "No",
        "© 2020 Sello",
    )
    # Lo que no se cargó sigue marcado, y el otro producto no se tocó.
    assert _fila(ps, "Language") == "<<COMPLETAR>>"
    assert _fila(ps, "Genre", 2) == "<<COMPLETAR>>"


def test_un_valor_vacio_devuelve_el_campo_a_completar(hacer_producto, hacer_track):
    ps = _catalogo(hacer_producto, hacer_track)
    ED.poner_datos(ps, ["p001"], {"genre": "Rock"})
    ED.poner_datos(ps, ["p001"], {"genre": ""})
    assert _fila(ps, "Genre") == "<<COMPLETAR>>"
    assert "datos" not in ps[0]


def test_por_aca_no_se_cambia_otra_cosa(hacer_producto, hacer_track):
    """Sólo los campos que ninguna fuente trae: un título o un sello no se
    pisan con un pedido a esta función."""
    ps = _catalogo(hacer_producto, hacer_track)
    with pytest.raises(ED.EdicionInvalida):
        ED.poner_datos(ps, ["p001"], {"title": "Otro título"})
    assert ps[0]["title"] == "Disco"


def test_un_dato_pegado_con_saltos_de_linea_queda_en_una_linea(hacer_producto, hacer_track):
    ps = _catalogo(hacer_producto, hacer_track)
    ED.poner_datos(ps, ["p001"], {"genre": "Rock\n\tLatino\x00" + "x" * 500})
    assert ps[0]["datos"]["genre"].startswith("Rock Latino x")
    assert len(ps[0]["datos"]["genre"]) <= ED.LARGO_MAX_DATO


def test_una_formula_cargada_a_mano_no_se_ejecuta_en_el_csv(hacer_producto, hacer_track):
    ps = _catalogo(hacer_producto, hacer_track)
    ED.poner_datos(ps, ["p001"], {"genre": '=HYPERLINK("http://x","y")'})
    assert _fila(ps, "Genre").startswith("'=")


def test_el_aviso_de_campos_a_completar_nombra_los_que_quedan(hacer_producto, hacer_track):
    ps = _catalogo(hacer_producto, hacer_track)
    todos = {clave: "x" for clave in ED.CAMPOS_A_COMPLETAR}
    ED.poner_datos(ps, ["p001", "p002"], {"genre": "Rock"})
    aviso = [h for h in V.validar(ps)["hallazgos"] if h["codigo"] == "campos_a_completar"]
    assert len(aviso) == 1 and "Language" in aviso[0]["mensaje"] and "Genre" not in aviso[0]["mensaje"]
    ED.poner_datos(ps, ["p001", "p002"], todos)
    assert "campos_a_completar" not in {h["codigo"] for h in V.validar(ps)["hallazgos"]}


def test_la_linea_c_sugerida_sale_del_anio_y_el_titular(hacer_producto, hacer_track):
    p = hacer_producto(year=2019, label="Sello Chico", tracks=[hacer_track(track="Uno")])
    assert ED.sugerir_linea_c(p) == "© 2019 Sello Chico"
    assert ED.sugerir_linea_c(hacer_producto(label="", tracks=[])) == ""


# ============================================================
# La evidencia en lo que se descarga
# ============================================================


def test_la_hoja_de_ingesta_dice_que_tan_comprobado_esta_cada_codigo(hacer_producto, hacer_track):
    ps = _catalogo(hacer_producto, hacer_track)
    ED.poner_isrc(ps, "p001", 1, "ARBBB2100002")
    assert (_fila(ps, "ISRC Evidence", 0), _fila(ps, "ISRC Evidence", 1)) == ("confirmed", "manual")
    assert _fila(ps, "UPC Evidence", 0) == "confirmed"
    assert _fila(ps, "ISRC Evidence", 2) == ""
