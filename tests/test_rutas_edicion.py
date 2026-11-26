# -*- coding: utf-8 -*-
"""Las rutas por las que el usuario cambia el catálogo: editar un código,
cargar datos, importar la planilla de la distribuidora, reabrir un relevamiento
guardado y compararlo. Sin red.

Lo que se cuida: que nada cambie sin pasar por la validación, que un archivo
que no sirve dé un error para mostrar y no un 500, y que una propuesta vieja no
se pueda aplicar sobre otro catálogo.
"""

import base64
import http.client
import json
import threading

import pytest

import server as backend
from conftest import _producto, _track
from migrador import instantanea as INS

UPC = "0885012345673"


@pytest.fixture(autouse=True)
def catalogo(monkeypatch, tmp_path):
    e = backend.ESTADO
    antes = (e.productos, e.artista, e.diagnostico, e.catalogo_id, e.importacion)
    monkeypatch.setattr(backend, "dir_datos", lambda: str(tmp_path))
    a = _track(track="Uno", isrc="ARAAA2000001", dur=200)
    a["isrc_nivel"] = "inferido"
    p = _producto(title="Disco", upc=UPC, tracks=[a, _track(track="Dos", dur=210)])
    q = _producto(title="Otro", upc="", tracks=[_track(track="Tres", dur=220)])
    q["product_id"] = "p002"
    e.guardar_catalogo([p, q], "Fulano", {"canal": "Fulano - Topic", "via": "busqueda", "temas": 3})
    yield e
    e.productos, e.artista, e.diagnostico, e.catalogo_id, e.importacion = antes


def _b64(datos: bytes) -> str:
    return base64.b64encode(datos).decode("ascii")


def _csv(*lineas) -> str:
    return _b64(("\n".join(",".join(linea) for linea in lineas) + "\n").encode("utf-8"))


# ============================================================
# Editar
# ============================================================


def test_editar_un_isrc_devuelve_el_catalogo_con_el_cambio(catalogo):
    res = backend.api_editar({"tipo": "isrc", "producto": "p001", "indice": 1, "valor": "ar-bbb-21-00002"})
    tema = res["productos"][0]["detalle"][1]
    assert (tema["isrc"], tema["nivel"], tema["editado"]) == ("ARBBB2100002", "manual", True)
    assert res["evidencia"]["isrc"] == {"inferido": 1, "manual": 1}
    assert res["catalogo_id"] == catalogo.catalogo_id, "editar no es otro catálogo: los ids siguen valiendo"


def test_un_codigo_invalido_es_un_error_para_mostrar(catalogo):
    with pytest.raises(ValueError) as e:
        backend.api_editar({"tipo": "isrc", "producto": "p001", "indice": 1, "valor": "no"})
    assert "ISRC" in str(e.value)
    with pytest.raises(ValueError):
        backend.api_editar({"tipo": "upc", "producto": "p002", "valor": "123"})
    assert catalogo.productos[1]["upc"] == ""


def test_editar_con_el_id_de_otro_catalogo_se_rechaza(catalogo):
    with pytest.raises(ValueError):
        backend.api_editar({"catalogo_id": "viejo", "tipo": "upc", "producto": "p002", "valor": UPC})


def test_cargar_datos_en_lote_y_la_linea_c_de_cada_producto(catalogo):
    res = backend.api_editar(
        {"tipo": "datos", "ids": ["p001", "p002"], "datos": {"genre": "Cuarteto"}, "c_sugerida": True}
    )
    assert [p["datos"]["genre"] for p in res["productos"]] == ["Cuarteto", "Cuarteto"]
    assert res["productos"][0]["datos"]["c_line"] == "© 2020 Sello"
    assert res["campos"][0] == "c_line"


def test_un_tipo_de_edicion_desconocido_no_hace_nada(catalogo):
    with pytest.raises(ValueError):
        backend.api_editar({"tipo": "titulo", "producto": "p001", "valor": "Otro"})
    with pytest.raises(ValueError):
        backend.api_editar({"tipo": "datos", "ids": "p001", "datos": {"genre": "x"}})


def test_no_se_edita_mientras_se_arma_un_paquete(catalogo, monkeypatch):
    monkeypatch.setattr(backend.JOBS, "activos", lambda: [object()])
    with pytest.raises(ValueError):
        backend.api_editar({"tipo": "upc", "producto": "p002", "valor": UPC})


# ============================================================
# Importar
# ============================================================


def test_importar_propone_y_aplicar_carga(catalogo):
    contenido = _csv(
        ["Track", "ISRC"], ["Uno", "ARAAA2000001"], ["Dos", "ARBBB2100002"], ["Otro tema", "ARCCC2200003"]
    )
    prop = backend.api_importar({"nombre": "export.csv", "contenido": contenido})
    assert prop["resumen"] == {"confirma": 1, "completa": 1, "conflicto": 0, "ambiguo": 0}
    assert prop["columnas"] == {"track": "Track", "isrc": "ISRC"}
    assert prop["sin_correspondencia_total"] == 1 and len(prop["elegidos"]) == 2
    assert catalogo.productos[0]["tracks"][1]["isrc"] == "", "importar sólo propone"

    res = backend.api_importar_aplicar({"id": prop["id"], "elegidos": prop["elegidos"]})
    assert res["hechos"] == {"confirmados": 1, "cargados": 1}
    niveles = [t["nivel"] for t in res["catalogo"]["productos"][0]["detalle"]]
    assert niveles == ["confirmado", "importado"]


def test_una_propuesta_no_se_aplica_dos_veces_ni_sobre_otro_catalogo(catalogo):
    contenido = _csv(["Track", "ISRC"], ["Dos", "ARBBB2100002"])
    prop = backend.api_importar({"contenido": contenido})
    backend.api_importar_aplicar({"id": prop["id"], "elegidos": prop["elegidos"]})
    with pytest.raises(ValueError):
        backend.api_importar_aplicar({"id": prop["id"], "elegidos": prop["elegidos"]})
    # Otra propuesta, y en el medio se releva otro catálogo.
    prop = backend.api_importar({"contenido": _csv(["Track", "ISRC"], ["Tres", "ARDDD2300004"])})
    catalogo.guardar_catalogo([_producto(title="Nuevo", tracks=[_track(track="Tres")])], "Otra", {})
    with pytest.raises(ValueError):
        backend.api_importar_aplicar({"id": prop["id"], "elegidos": prop["elegidos"]})
    assert catalogo.productos[0]["tracks"][0]["isrc"] == ""


@pytest.mark.parametrize(
    "contenido",
    [None, "", "esto no es base64 !!!", _b64(b"sin,codigos\nuno,dos\n"), _b64(b"PK\x03\x04roto")],
    ids=["nada", "vacio", "no-base64", "sin-codigos", "zip-roto"],
)
def test_un_archivo_que_no_sirve_es_un_error_para_mostrar(catalogo, contenido):
    with pytest.raises(ValueError):
        backend.api_importar({"nombre": "x.csv", "contenido": contenido})
    assert catalogo.importacion is None


def test_un_archivo_mas_grande_que_el_tope_se_rechaza_sin_decodificar(catalogo, monkeypatch):
    monkeypatch.setattr(
        backend.base64, "b64decode", lambda *a, **k: pytest.fail("no tenía que decodificarlo")
    )
    with pytest.raises(ValueError):
        backend.api_importar({"contenido": "A" * (backend.IMP.MAX_BYTES * 2)})


# ============================================================
# Abrir y comparar
# ============================================================


def test_abrir_un_relevamiento_guardado_lo_deja_como_catalogo(catalogo):
    guardado = INS.volcar(catalogo.productos, "Fulano", catalogo.diagnostico)
    id_antes = catalogo.catalogo_id
    catalogo.productos, catalogo.artista = [], ""
    res = backend.api_abrir({"contenido": _b64(guardado)})
    assert res["artista"] == "Fulano" and [p["titulo"] for p in res["productos"]] == ["Disco", "Otro"]
    assert res["diagnostico"]["abierto"]["fecha"], "la interfaz tiene que poder decir que salió de un archivo"
    assert res["diagnostico"]["unidades"] == 0
    assert res["catalogo_id"] != id_antes
    # Y con eso se puede validar y seguir, como con cualquier catálogo.
    assert backend.api_validar({"ids": ["p001"]})["resumen"]["productos"] == 1


def test_abrir_algo_que_no_es_un_relevamiento_no_toca_el_catalogo(catalogo):
    with pytest.raises(ValueError):
        backend.api_abrir({"contenido": _b64(b'{"formato": "otra-cosa"}')})
    assert catalogo.artista == "Fulano"


def test_comparar_contra_un_relevamiento_guardado(catalogo):
    guardado = INS.volcar(catalogo.productos, "Fulano", catalogo.diagnostico)
    # Hoy el disco está en otra distribuidora, y un tema cambió de código.
    catalogo.productos[0]["distributor"] = "Mojo"
    catalogo.productos[0]["tracks"][0]["isrc"] = "ARNEW2600777"
    res = backend.api_comparar({"contenido": _b64(guardado)})
    disco = res["releases"][0]
    assert (disco["estado"], disco["distribuidoras_ahora"]) == ("codigos_cambiados", ["Mojo"])
    assert disco["isrc_cambiados"][0]["ahora"] == "ARNEW2600777"
    assert res["releases"][1]["estado"] == "igual"
    assert res["otro_artista"] is False and res["fecha"]


def test_comparar_avisa_si_el_archivo_es_de_otro_artista(catalogo):
    guardado = INS.volcar(catalogo.productos, "Mengano", {})
    assert backend.api_comparar({"contenido": _b64(guardado)})["otro_artista"] is True


# ============================================================
# Por HTTP: las mismas defensas que el resto
# ============================================================


def test_las_rutas_nuevas_exigen_el_token():
    servidor = backend.crear_servidor(0)
    hilo = threading.Thread(target=servidor.serve_forever, daemon=True)
    hilo.start()
    try:
        puerto = servidor.server_address[1]
        cuerpo = json.dumps({"tipo": "upc", "producto": "p002", "valor": UPC})
        for ruta in ("/api/editar", "/api/importar", "/api/importar/aplicar", "/api/abrir", "/api/comparar"):
            c = http.client.HTTPConnection("127.0.0.1", puerto, timeout=5)
            c.request("POST", ruta, cuerpo, {"Content-Type": "application/json"})
            assert c.getresponse().status == 403, ruta
            c.close()
        c = http.client.HTTPConnection("127.0.0.1", puerto, timeout=5)
        c.request(
            "POST", "/api/editar", cuerpo, {"Content-Type": "application/json", "X-App-Token": backend.TOKEN}
        )
        r = c.getresponse()
        assert r.status == 200 and json.loads(r.read())["productos"][1]["upc"] == UPC
        c.close()
    finally:
        servidor.shutdown()
        servidor.server_close()
