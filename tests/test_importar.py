# -*- coding: utf-8 -*-
"""La planilla de la distribuidora actual, conciliada contra el catálogo.

Tres cosas que no pueden pasar: que un código se pise en silencio, que se
elija entre dos candidatos sin que nada los separe, y que la hoja de pedido de
la propia app, devuelta sin tocar, «confirme» los códigos con su propio eco.
"""

import io

import pytest
from openpyxl import Workbook, load_workbook

from migrador import importar as IM
from migrador import paquete as PQ
from migrador import validar as V

UPC_DISCO = "0885012345673"
UPC_SINGLE = "0885012345680"


def _csv(*lineas, sep=","):
    return ("\n".join(sep.join(linea) for linea in lineas) + "\n").encode("utf-8-sig")


def _xlsx(filas):
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    for fila in filas:
        ws.append(list(fila))
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _catalogo(hacer_producto, hacer_track):
    """Un disco de tres temas (uno sin ISRC, uno inferido) y el single de uno."""
    a = hacer_track(track="Corazón Roto", isrc="ARAAA2000001", dur=200)
    a["isrc_nivel"], a["track_number"] = "inferido", 1
    b = hacer_track(track="La Vuelta", dur=210)
    b["track_number"] = 2
    c = hacer_track(track="La Vuelta (En Vivo)", dur=260)
    c["track_number"] = 3
    disco = hacer_producto(title="Disco", upc=UPC_DISCO, tracks=[a, b, c])
    disco["upc_nivel"] = "inferido"
    s = hacer_track(track="Corazón Roto", isrc="ARAAA2000001", dur=200)
    s["isrc_nivel"] = "inferido"
    single = hacer_producto(title="Corazón Roto", upc="", tracks=[s], kind="single")
    single["product_id"] = "p002"
    return [disco, single]


def _de(propuesta, tipo, codigo="isrc"):
    return [it for it in propuesta["items"] if it["tipo"] == tipo and it["codigo"] == codigo]


# ============================================================
# Leer el archivo
# ============================================================


def test_lee_un_csv_con_encabezados_en_castellano_y_punto_y_coma():
    datos = _csv(
        ["Lanzamiento", "Código de barras", "Tema", "ISRC", "Duración"],
        ["Disco", UPC_DISCO, "La Vuelta", "ar-bbb-21-00002", "3:30"],
        sep=";",
    )
    filas, columnas = IM.leer(datos, "export.csv")
    assert filas == [
        {
            "fila": 2,
            "isrc": "ARBBB2100002",
            "upc": UPC_DISCO,
            "track": "La Vuelta",
            "album": "Disco",
            "duracion_s": 210,
            "numero": 0,
        }
    ]
    assert columnas == {
        "album": "Lanzamiento",
        "upc": "Código de barras",
        "track": "Tema",
        "isrc": "ISRC",
        "duracion": "Duración",
    }


def test_lee_un_xlsx_con_un_titulo_antes_de_la_tabla_y_el_upc_como_numero():
    """Los exports traen filas de título antes del encabezado, y Excel guarda
    el UPC como número: sin el cero de adelante y con un «.0» al final."""
    datos = _xlsx(
        [
            ["Catálogo de Fulano"],
            ["Exportado el 2026-11-01"],
            [],
            ["Release Title", "UPC", "Track Title", "ISRC", "Track Number"],
            ["Disco", 885012345673.0, "La Vuelta", "ARBBB2100002", 2],
        ]
    )
    filas, _ = IM.leer(datos, "export.xlsx")
    # Doce dígitos o trece con un cero adelante son el mismo código.
    assert V.gtin13(filas[0]["upc"]) == V.gtin13(UPC_DISCO)
    assert (filas[0]["numero"], filas[0]["fila"]) == (2, 5)


def test_recupera_el_cero_que_se_comio_la_planilla():
    """Un UPC que empieza con dos ceros, guardado como número, llega con once
    dígitos: con el cero adelante vuelve a cerrar el dígito verificador."""
    base = "00885012345"
    upc = base + str(V._gtin_check_digit(base))
    datos = _xlsx([["Track", "UPC", "ISRC"], ["Uno", float(upc), "ARBBB2100002"]])
    assert IM.leer(datos)[0][0]["upc"] == upc


def test_reconoce_las_columnas_de_codigos_por_lo_que_traen():
    """Sin un encabezado que diga «ISRC»: se reconoce la columna porque lo que
    trae tiene forma de ISRC."""
    datos = _csv(["Nombre", "Código"], ["La Vuelta", "ARBBB2100002"], ["Otro", "ARBBB2100003"])
    filas, columnas = IM.leer(datos)
    assert [f["isrc"] for f in filas] == ["ARBBB2100002", "ARBBB2100003"]
    assert columnas["isrc"] == "Código" and filas[0]["track"] == "La Vuelta"


def test_la_version_en_su_columna_se_suma_al_titulo():
    datos = _csv(["Track", "Version", "ISRC"], ["La Vuelta", "En Vivo", "ARCCC2200003"])
    assert IM.leer(datos)[0][0]["track"] == "La Vuelta (En Vivo)"


def test_un_codigo_mal_formado_del_archivo_no_entra():
    datos = _csv(["Track", "ISRC", "UPC"], ["Uno", "ARBBB21000", "123"], ["Dos", "ARBBB2100002", "123"])
    filas, _ = IM.leer(datos)
    assert len(filas) == 1 and filas[0]["upc"] == ""


@pytest.mark.parametrize(
    "datos",
    [
        b"",
        b"   \n",
        _csv(["Track", "Artista"], ["Uno", "Fulano"]),
        b"PK\x03\x04roto",
        b"\xff\xfe\x00\x01" * 3,
    ],
)
def test_un_archivo_que_no_sirve_se_dice_y_no_se_cae(datos):
    with pytest.raises(IM.ArchivoInvalido):
        IM.leer(datos, "x")


def test_un_archivo_enorme_se_rechaza_sin_leerlo():
    with pytest.raises(IM.ArchivoInvalido):
        IM.leer(b"a," * (IM.MAX_BYTES // 2 + 1))


def test_una_formula_del_archivo_no_se_ejecuta():
    """`data_only`: de la planilla sale el valor guardado, nunca la fórmula."""
    datos = _xlsx([["Track", "ISRC"], ["=1+1", "ARBBB2100002"], ['=HYPERLINK("http://x")', "ARBBB2100003"]])
    filas, _ = IM.leer(datos)
    assert all(not f["track"].startswith("=") for f in filas)


# ============================================================
# Conciliar
# ============================================================


def test_el_mismo_codigo_en_el_archivo_confirma(hacer_producto, hacer_track):
    ps = _catalogo(hacer_producto, hacer_track)
    filas, _ = IM.leer(_csv(["Track", "ISRC"], ["Corazon roto", "ARAAA2000001"]))
    prop = IM.conciliar(ps, filas)
    # La misma grabación está en el disco y en el single: se confirman las dos.
    assert [(it["producto_id"], it["indice"]) for it in _de(prop, "confirma")] == [("p001", 0), ("p002", 0)]
    IM.aplicar(ps, prop, IM.elegidos_por_defecto(prop))
    assert ps[0]["tracks"][0]["isrc_nivel"] == "confirmado"
    assert ps[0]["tracks"][0]["isrc_respaldo"] == "archivo"


def test_completa_el_tema_que_no_tenia_codigo(hacer_producto, hacer_track):
    ps = _catalogo(hacer_producto, hacer_track)
    filas, _ = IM.leer(
        _csv(["Album", "Track", "ISRC", "Duration"], ["Disco", "La Vuelta", "ARBBB2100002", "3:30"])
    )
    prop = IM.conciliar(ps, filas)
    assert [(it["indice"], it["nuevo"]) for it in _de(prop, "completa")] == [(1, "ARBBB2100002")]
    hechos = IM.aplicar(ps, prop, IM.elegidos_por_defecto(prop))
    t = ps[0]["tracks"][1]
    assert (t["isrc"], t["isrc_nivel"], hechos["cargados"]) == ("ARBBB2100002", "importado", 1)


def test_la_version_en_vivo_no_se_queda_con_el_codigo_de_estudio(hacer_producto, hacer_track):
    """El error de copiar y pegar que esto evita: la fila del tema de estudio
    no es candidata para «(En Vivo)», aunque el resto del título sea igual."""
    ps = _catalogo(hacer_producto, hacer_track)
    filas, _ = IM.leer(_csv(["Track", "ISRC"], ["La Vuelta", "ARBBB2100002"]))
    prop = IM.conciliar(ps, filas)
    assert {it["indice"] for it in prop["items"]} == {1}


def test_un_codigo_distinto_es_un_conflicto_y_no_se_aplica_solo(hacer_producto, hacer_track):
    ps = _catalogo(hacer_producto, hacer_track)
    filas, _ = IM.leer(_csv(["Album", "Track", "ISRC"], ["Disco", "Corazón Roto", "ARZZZ9900009"]))
    prop = IM.conciliar(ps, filas)
    conflicto = _de(prop, "conflicto")[0]
    assert (conflicto["actual"], conflicto["nuevo"], conflicto["nivel"]) == (
        "ARAAA2000001",
        "ARZZZ9900009",
        "inferido",
    )
    assert conflicto["id"] not in IM.elegidos_por_defecto(prop)
    IM.aplicar(ps, prop, IM.elegidos_por_defecto(prop))
    assert ps[0]["tracks"][0]["isrc"] == "ARAAA2000001", "sin que el usuario lo elija, no se toca"
    IM.aplicar(ps, prop, [conflicto["id"]])
    t = ps[0]["tracks"][0]
    assert (t["isrc"], t["isrc_nivel"], t["isrc_previo"]["isrc"]) == (
        "ARZZZ9900009",
        "importado",
        "ARAAA2000001",
    )


def test_dos_filas_que_pueden_ser_el_tema_son_ambiguas(hacer_producto, hacer_track):
    """El mismo título dos veces en el archivo, con códigos distintos y nada
    que las separe: no se elige, se muestran las dos."""
    ps = _catalogo(hacer_producto, hacer_track)
    filas, _ = IM.leer(_csv(["Track", "ISRC"], ["La Vuelta", "ARBBB2100002"], ["La vuelta", "ARCCC1900007"]))
    prop = IM.conciliar(ps, filas)
    ambiguo = _de(prop, "ambiguo")[0]
    assert {c["isrc"] for c in ambiguo["candidatos"]} == {"ARBBB2100002", "ARCCC1900007"}
    assert ambiguo["id"] not in IM.elegidos_por_defecto(prop)
    # Elegir uno que no es candidato no hace nada; elegir uno que sí, lo carga.
    IM.aplicar(ps, prop, [ambiguo["id"]], {ambiguo["id"]: "ARXXX0000000"})
    assert ps[0]["tracks"][1]["isrc"] == ""
    IM.aplicar(ps, prop, [ambiguo["id"]], {ambiguo["id"]: "ARCCC1900007"})
    assert ps[0]["tracks"][1]["isrc"] == "ARCCC1900007"


def test_la_duracion_separa_dos_filas_que_se_llaman_igual(hacer_producto, hacer_track):
    ps = _catalogo(hacer_producto, hacer_track)
    filas, _ = IM.leer(
        _csv(
            ["Track", "ISRC", "Duration"],
            ["La Vuelta", "ARBBB2100002", "3:31"],
            ["La Vuelta", "ARCCC1900007", "5:02"],
        )
    )
    prop = IM.conciliar(ps, filas)
    assert [(it["indice"], it["nuevo"]) for it in _de(prop, "completa")] == [(1, "ARBBB2100002")]
    assert not _de(prop, "ambiguo")


def test_el_release_separa_la_fila_del_single_de_la_del_album(hacer_producto, hacer_track):
    """La grabación está en el single y en el disco, cada fila con su UPC: el
    UPC de cada producto sale de su fila, y no del otro."""
    ps = _catalogo(hacer_producto, hacer_track)
    ps[1]["tracks"][0]["isrc"] = ""  # para que el single no se concilie por ISRC
    filas, _ = IM.leer(
        _csv(
            ["Release", "UPC", "Track", "ISRC"],
            ["Disco", UPC_DISCO, "Corazón Roto", "ARAAA2000001"],
            ["Disco", UPC_DISCO, "La Vuelta", "ARBBB2100002"],
            ["Corazón Roto", UPC_SINGLE, "Corazón Roto", "ARAAA2000001"],
        )
    )
    prop = IM.conciliar(ps, filas)
    upcs = {(it["producto_id"], it["tipo"], it["nuevo"]) for it in prop["items"] if it["codigo"] == "upc"}
    assert upcs == {("p001", "confirma", UPC_DISCO), ("p002", "completa", UPC_SINGLE)}
    IM.aplicar(ps, prop, IM.elegidos_por_defecto(prop))
    assert (ps[1]["upc"], ps[1]["upc_nivel"]) == (UPC_SINGLE, "importado")
    assert (ps[0]["upc"], ps[0]["upc_nivel"]) == (UPC_DISCO, "confirmado")


def test_un_upc_que_llega_por_un_solo_tema_de_un_disco_no_se_propone(hacer_producto, hacer_track):
    """Una fila sin release, que coincide con un tema de un disco de tres: su
    UPC puede ser el del single, y no se le pone al disco."""
    ps = _catalogo(hacer_producto, hacer_track)
    ps[0]["upc"] = ""
    filas, _ = IM.leer(
        _csv(["Release", "UPC", "Track", "ISRC"], ["Otro Nombre", UPC_SINGLE, "La Vuelta", "ARBBB2100002"])
    )
    prop = IM.conciliar(ps, filas)
    assert not [it for it in prop["items"] if it["codigo"] == "upc" and it["producto_id"] == "p001"]


def test_lo_que_esta_en_el_archivo_y_no_en_el_catalogo_se_informa(hacer_producto, hacer_track):
    ps = _catalogo(hacer_producto, hacer_track)
    filas, _ = IM.leer(
        _csv(["Track", "ISRC"], ["Uno que no relevé", "ARDDD1800001"], ["Corazón Roto", "ARAAA2000001"])
    )
    prop = IM.conciliar(ps, filas)
    assert prop["sin_correspondencia_total"] == 1
    assert prop["sin_correspondencia"][0]["track"] == "Uno que no relevé"
    assert prop["resumen"]["confirma"] == 2


def test_conciliar_no_cambia_nada(hacer_producto, hacer_track):
    ps = _catalogo(hacer_producto, hacer_track)
    antes = repr(ps)
    filas, _ = IM.leer(
        _csv(["Track", "ISRC"], ["La Vuelta", "ARBBB2100002"], ["Corazón Roto", "ARZZZ9900009"])
    )
    IM.conciliar(ps, filas)
    assert repr(ps) == antes


# ============================================================
# La hoja de pedido: ida y vuelta
# ============================================================


def test_la_hoja_de_pedido_devuelta_sin_tocar_no_confirma_nada(hacer_producto, hacer_track):
    """Las columnas «UPC» e «ISRC» van vacías a propósito. Si llevaran los
    códigos de la app, devolverla sin tocar los «confirmaría» con su eco."""
    ps = _catalogo(hacer_producto, hacer_track)
    with pytest.raises(IM.ArchivoInvalido):
        IM.leer(PQ.hoja_pedido_bytes(ps, "Artista"), "pedido.xlsx")


@pytest.mark.parametrize("idioma", ["es", "en"])
def test_la_hoja_de_pedido_completada_vuelve_a_entrar(hacer_producto, hacer_track, idioma):
    """El ciclo entero: la app arma el pedido, la distribuidora completa las
    dos columnas, y la app lo lee y carga cada código en su lugar."""
    from migrador import i18n

    i18n.poner_idioma(idioma)
    ps = _catalogo(hacer_producto, hacer_track)
    wb = load_workbook(io.BytesIO(PQ.hoja_pedido_bytes(ps, "Artista")))
    ws = wb.active
    assert ws is not None
    filas = list(ws.iter_rows())
    encabezado = next(i for i, f in enumerate(filas) if [c.value for c in f].count("ISRC") == 1)
    nombres = [c.value for c in filas[encabezado]]
    col_isrc, col_upc = nombres.index("ISRC"), nombres.index("UPC")
    codigos = {
        "Corazón Roto": "ARAAA2000001",
        "La Vuelta": "ARBBB2100002",
        "La Vuelta (En Vivo)": "ARCCC2200003",
    }
    for fila in filas[encabezado + 1 :]:
        valores = [c.value for c in fila]
        assert not valores[col_isrc] and not valores[col_upc], "las columnas a completar van vacías"
        tema = next(str(v) for v in valores if str(v) in codigos)
        # Por coordenadas y no por la celda de la fila: openpyxl tipa la celda
        # como posiblemente combinada, que no se puede escribir.
        n = fila[0].row or 0
        ws.cell(row=n, column=col_isrc + 1, value=codigos[tema])
        del_disco = ps[0]["title"] in valores[:2] and "Disco" in valores
        ws.cell(row=n, column=col_upc + 1, value=UPC_DISCO if del_disco else UPC_SINGLE)
    buf = io.BytesIO()
    wb.save(buf)

    leidas, _ = IM.leer(buf.getvalue(), "pedido.xlsx")
    prop = IM.conciliar(ps, leidas)
    IM.aplicar(ps, prop, IM.elegidos_por_defecto(prop))
    assert [t["isrc"] for t in ps[0]["tracks"]] == ["ARAAA2000001", "ARBBB2100002", "ARCCC2200003"]
    assert [t["isrc_nivel"] for t in ps[0]["tracks"]] == ["confirmado", "importado", "importado"]
    assert (ps[0]["upc_nivel"], ps[1]["upc"]) == ("confirmado", UPC_SINGLE)


def test_la_hoja_de_pedido_pone_primero_lo_que_hay_que_pedir(hacer_producto, hacer_track):
    ok = hacer_track(track="Listo", isrc="ARAAA2000009", dur=200)
    ok["isrc_nivel"] = "confirmado"
    completo = hacer_producto(title="Completo", upc=UPC_SINGLE, tracks=[ok])
    completo["upc_nivel"] = "confirmado"
    ps = [completo] + _catalogo(hacer_producto, hacer_track)
    assert PQ.que_pedir(completo, ok) == ""
    assert PQ.que_pedir(ps[1], ps[1]["tracks"][1]) == "falta"
    assert PQ.que_pedir(ps[1], ps[1]["tracks"][0]) == "confirmar"
    ws = load_workbook(io.BytesIO(PQ.hoja_pedido_bytes(ps, "Artista"))).active
    assert ws is not None
    releases = [f[1] for f in ws.iter_rows(values_only=True) if f[1] in ("Completo", "Disco")]
    assert releases[0] == "Disco" and releases[-1] == "Completo"


def test_el_paquete_trae_la_hoja_de_pedido_solo_si_hay_algo_que_pedir(hacer_producto, hacer_track, tmp_path):
    import zipfile

    ps = _catalogo(hacer_producto, hacer_track)
    PQ.build_zip(ps, "Artista", str(tmp_path / "a.zip"), log=lambda m: None)
    with zipfile.ZipFile(tmp_path / "a.zip") as z:
        assert any(n.endswith(PQ.nombres_archivos()["pedido"]) for n in z.namelist())

    for p in ps:
        p["upc"], p["upc_nivel"] = p["upc"] or UPC_SINGLE, "confirmado"
        for n, t in enumerate(p["tracks"]):
            t["isrc"], t["isrc_nivel"] = t["isrc"] or f"ARQQQ210000{n}", "confirmado"
    PQ.build_zip(ps, "Artista", str(tmp_path / "b.zip"), log=lambda m: None)
    with zipfile.ZipFile(tmp_path / "b.zip") as z:
        assert not any(n.endswith(PQ.nombres_archivos()["pedido"]) for n in z.namelist())
