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
