# -*- coding: utf-8 -*-
"""Un trabajo por vez, de verdad, y temporales que no quedan. Sin red.

- dos pedidos simultáneos no lanzan dos trabajos
- una lista de ids vacía no es «todos»
- una pestaña con el catálogo de antes no arma el paquete de otro artista
- la carpeta del audio se borra aunque se cancele a la mitad
- un paquete nuevo borra los ZIP de los anteriores
"""

import os
import threading

import pytest

import jobs as J
import server as backend
from conftest import _esperar, _producto, _track


@pytest.fixture(autouse=True)
def estado_restaurado():
    """El estado del servidor es global: lo que estos tests le hacen se deshace."""
    e = backend.ESTADO
    antes = (e.productos, e.artista, e.diagnostico, e.catalogo_id, dict(e.zips))
    yield
    e.productos, e.artista, e.diagnostico, e.catalogo_id, e.zips = antes


def _carrera(hilos=8):
    """Varios hilos que lanzan a la vez sobre el mismo registro."""
    registro = J.Registry()
    salida = threading.Event()
    barrera = threading.Barrier(hilos)
    lanzados, rechazados = [], []

    def intentar():
        barrera.wait()
        try:
            lanzados.append(registro.lanzar("x", lambda job: salida.wait(5), exclusivo=True))
        except J.Ocupado:
            rechazados.append(1)

    todos = [threading.Thread(target=intentar) for _ in range(hilos)]
    for h in todos:
        h.start()
    for h in todos:
        h.join()
    salida.set()
    return len(lanzados), len(rechazados)


def test_dos_lanzamientos_simultaneos_no_pasan_los_dos():
    """Mirar `activos()` y después lanzar dejaba una ventana en la que los dos
    pasaban. Con el control adentro del lock, gana uno solo."""
    for _ in range(20):
        assert _carrera(8) == (1, 7)


def test_sin_exclusivo_se_puede_lanzar_mas_de_uno():
    registro = J.Registry()
    salida = threading.Event()
    registro.lanzar("x", lambda job: salida.wait(5))
    registro.lanzar("x", lambda job: salida.wait(5))
    assert len(registro.activos()) == 2
    salida.set()


def test_una_lista_de_ids_vacia_no_es_todo_el_catalogo(monkeypatch):
    monkeypatch.setattr(backend.ESTADO, "productos", [_producto()])
    assert backend.ESTADO.por_ids([]) == []
    assert backend.ESTADO.por_ids(None) == []
    with pytest.raises(ValueError):
        backend.api_validar({})


def test_cada_relevamiento_tiene_su_catalogo_id():
    backend.ESTADO.guardar_catalogo([_producto()], "Uno", {})
    primero = backend.catalogo_json(backend.ESTADO.productos, "Uno")["catalogo_id"]
    backend.ESTADO.guardar_catalogo([_producto()], "Dos", {})
    assert backend.ESTADO.catalogo_id != primero


def test_una_pestana_con_el_catalogo_de_antes_no_arma_el_paquete():
    backend.ESTADO.guardar_catalogo([_producto()], "Artista Nuevo", {})
    with pytest.raises(backend.ErrorDeCampo) as e:
        backend.api_preparar({"catalogo_id": "de-otro-relevamiento", "ids": ["p001"]})
    assert e.value.codigo == "catalogo"
    # Sin id, como mandan los scripts, sigue andando la validación de siempre.
    assert backend.api_validar({"ids": ["p001"]})["resumen"]["productos"] == 1


def test_la_carpeta_del_audio_se_borra_aunque_se_cancele(monkeypatch):
    backend.ESTADO.guardar_catalogo([_producto(tracks=[_track("Tema")])], "A", {})
    visto = {}

    def preparar(copias, artista, **kw):
        visto["dir"] = kw.get("dir_audio")
        assert visto["dir"] and os.path.isdir(visto["dir"]), "tenía que existir antes de bajar nada"
        raise J.Cancelado()

    monkeypatch.setattr(backend, "AUDIO_HABILITADO", True)
    monkeypatch.setattr(backend, "_revisar_espacio", lambda con_audio: None)
    monkeypatch.setattr(backend.M, "preparar", preparar)
    job = backend.api_preparar({"ids": ["p001"], "audio": True})["job"]
    trabajo = backend.JOBS.get(job["id"])
    assert trabajo is not None
    _esperar(lambda: trabajo.estado == "cancelado", 10)
    assert not os.path.exists(visto["dir"])


def test_un_paquete_nuevo_borra_los_zip_anteriores(tmp_path):
    carpeta = tmp_path / "migrador_zip_viejo"
    carpeta.mkdir()
    (carpeta / "viejo.zip").write_bytes(b"PK")
    backend.ESTADO.registrar_zip("abc123", str(carpeta / "viejo.zip"))
    backend.ESTADO.zips_anteriores()
    assert not carpeta.exists()
    assert backend.ESTADO.zip_de("abc123") is None
