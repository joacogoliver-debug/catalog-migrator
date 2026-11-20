# -*- coding: utf-8 -*-
"""Las rutas del servidor que no tenían test. Sin red.

- relevar como trabajo: termina, deja el catálogo en memoria y lo devuelve
- guardar la clave: se prueba antes de guardarla, y una mala no se guarda
- Tidal con el módulo de audio apagado
"""

import pytest

import server as backend
from conftest import _esperar, _producto
from migrador import relevar_core as R


@pytest.fixture(autouse=True)
def estado_restaurado(monkeypatch, tmp_path):
    e = backend.ESTADO
    antes = (e.productos, e.artista, e.diagnostico, e.catalogo_id)
    monkeypatch.setattr(backend, "dir_datos", lambda: str(tmp_path))
    yield
    e.productos, e.artista, e.diagnostico, e.catalogo_id = antes


def _terminar(job):
    trabajo = backend.JOBS.get(job["id"])
    assert trabajo is not None
    _esperar(lambda: trabajo.estado not in ("pendiente", "corriendo"), 10)
    return trabajo


def test_relevar_termina_y_deja_el_catalogo(monkeypatch):
    diag = {"es_topic": True, "canal": "Fulano - Topic"}
    monkeypatch.setattr(backend, "leer_clave", lambda: "clave-de-prueba")
    monkeypatch.setattr(
        backend.M,
        "relevar_catalogo",
        lambda url, clave, **kw: ([_producto(title="Disco")], "Fulano", [], diag),
    )
    trabajo = _terminar(backend.api_relevar({"url": "https://www.youtube.com/@fulano"})["job"])
    assert trabajo.estado == "listo"
    assert trabajo.resultado["artista"] == "Fulano"
    assert trabajo.resultado["catalogo_id"] == backend.ESTADO.catalogo_id
    assert [p["titulo"] for p in trabajo.resultado["productos"]] == ["Disco"]
    assert backend.ESTADO.artista == "Fulano"


def test_relevar_reusa_lo_listado_salvo_que_se_pida_de_cero(monkeypatch):
    """«Volver a listar» manda `de_cero`; un relevamiento común no, y reusa lo
    que ya se listó en la sesión para no gastar cuota de nuevo."""
    monkeypatch.setattr(backend, "leer_clave", lambda: "clave-de-prueba")
    pedidos = []

    def relevar(url, clave, **kw):
        pedidos.append(kw["reusar"])
        return [_producto(title="Disco")], "Fulano", [], {}

    monkeypatch.setattr(backend.M, "relevar_catalogo", relevar)
    _terminar(backend.api_relevar({"url": "https://www.youtube.com/@fulano"})["job"])
    _terminar(backend.api_relevar({"url": "https://www.youtube.com/@fulano", "de_cero": True})["job"])
    assert pedidos == [True, False]


def test_el_perfil_de_deezer_que_se_pega_llega_al_motor_como_su_id(monkeypatch):
    """Es lo que pidió quien no encontraba a su artista: decirle a la app cuál
    es el perfil. Sin link, el motor lo busca solo (id 0)."""
    monkeypatch.setattr(backend, "leer_clave", lambda: "clave-de-prueba")
    pedidos = []

    def relevar(url, clave, **kw):
        pedidos.append(kw["artista_deezer"])
        return [_producto(title="Disco")], "Fulano", [], {}

    monkeypatch.setattr(backend.M, "relevar_catalogo", relevar)
    canal = "https://www.youtube.com/@fulano"
    _terminar(backend.api_relevar({"url": canal})["job"])
    _terminar(
        backend.api_relevar({"url": canal, "deezer_artista": " https://www.deezer.com/es/artist/27 "})["job"]
    )
    assert pedidos == [0, 27]


@pytest.mark.parametrize(
    "pegado", ["cualquier cosa", "https://www.deezer.com/es/album/302127", "https://example.com/a"]
)
def test_un_link_de_deezer_que_no_es_de_un_artista_se_rechaza_antes_de_relevar(monkeypatch, pegado):
    monkeypatch.setattr(backend, "leer_clave", lambda: "clave-de-prueba")
    monkeypatch.setattr(backend.M, "relevar_catalogo", lambda *a, **k: pytest.fail("no tenía que relevar"))
    with pytest.raises(backend.ErrorDeCampo) as error:
        backend.api_relevar({"url": "https://www.youtube.com/@fulano", "deezer_artista": pegado})
    assert error.value.codigo == "deezer", "la interfaz lo muestra debajo del campo de Deezer"


def test_el_reporte_del_paquete_lleva_el_diagnostico_del_relevamiento(monkeypatch):
    """Sin esto el reporte del ZIP salía sin decir cómo se listó el catálogo ni
    qué le falta, aunque la pantalla lo dijera."""
    diag = {"via": "busqueda", "temas": 1, "unidades": 101}
    monkeypatch.setattr(backend, "leer_clave", lambda: "clave-de-prueba")
    monkeypatch.setattr(
        backend.M,
        "relevar_catalogo",
        lambda url, clave, **kw: ([_producto(title="Disco")], "Fulano", [], diag),
    )
    relevado = _terminar(backend.api_relevar({"url": "https://www.youtube.com/@fulano"})["job"])
    recibido = {}

    def empaquetar(seleccion, artista, **kw):
        recibido.update(kw)
        with open(kw["out_path"], "wb") as f:
            f.write(b"zip")
        return kw["out_path"], 3

    monkeypatch.setattr(backend.M, "empaquetar", empaquetar)
    cuerpo = {
        "catalogo_id": relevado.resultado["catalogo_id"],
        "ids": [p["id"] for p in relevado.resultado["productos"]],
        "planilla": True,
        "portadas": False,
        "audio": False,
    }
    trabajo = _terminar(backend.api_preparar(cuerpo)["job"])
    assert trabajo.estado == "listo", trabajo.error
    assert recibido["diag"] == diag


def test_un_error_del_relevamiento_llega_con_su_codigo(monkeypatch):
    monkeypatch.setattr(backend, "leer_clave", lambda: "clave-de-prueba")

    def falla(url, clave, **kw):
        raise R.RelevarError("se agotó el cupo", "cuota")

    monkeypatch.setattr(backend.M, "relevar_catalogo", falla)
    trabajo = _terminar(backend.api_relevar({"url": "https://www.youtube.com/@fulano"})["job"])
    assert trabajo.estado == "error"
    assert trabajo.codigo_error == "cuota", "es lo que hace aparecer el botón de cargar clave"


def test_sin_clave_no_se_releva(monkeypatch):
    monkeypatch.setattr(backend, "leer_clave", lambda: "")
    with pytest.raises(ValueError):
        backend.api_relevar({"url": "https://www.youtube.com/@fulano"})


def test_una_clave_que_funciona_se_guarda(monkeypatch):
    monkeypatch.setattr(backend.R, "api_get", lambda endpoint, params, key: {"items": [{"id": "x"}]})
    assert backend.api_guardar_clave({"clave": "  una-clave-de-prueba  "}) == {"ok": True}
    assert backend.leer_config()["youtube_api_key"] == "una-clave-de-prueba"


def test_una_clave_que_no_funciona_no_se_guarda(monkeypatch):
    def rechaza(endpoint, params, key):
        raise R.RelevarError("YouTube rechazó la clave", "clave")

    monkeypatch.setattr(backend.R, "api_get", rechaza)
    with pytest.raises(ValueError):
        backend.api_guardar_clave({"clave": "mala"})
    assert "youtube_api_key" not in backend.leer_config()


@pytest.mark.parametrize("clave", ["", "  ", "a" * 201, "con\nsalto"])
def test_una_clave_rara_se_rechaza_sin_probarla(monkeypatch, clave):
    monkeypatch.setattr(backend.R, "api_get", lambda *a, **k: pytest.fail("no tenía que probarla"))
    with pytest.raises(backend.ErrorDeCampo) as e:
        backend.api_guardar_clave({"clave": clave})
    assert e.value.codigo == "clave"


def test_tidal_con_el_audio_apagado_no_hace_nada(monkeypatch):
    monkeypatch.setattr(backend, "AUDIO_HABILITADO", False)
    with pytest.raises(ValueError):
        backend.api_tidal_iniciar()
    monkeypatch.setattr(backend.ESTADO, "tidal", None)
    with pytest.raises(ValueError):
        backend.api_tidal_confirmar({"device_code": "x"})
    assert backend.api_tidal_desconectar() == {"ok": True}
