# -*- coding: utf-8 -*-
"""Avance real, cancelación que responde y reintentos donde sirven. Sin red.

Medido al auditar: con 600 tracks, «Cancelar» tardaba 24 segundos en responder
durante la búsqueda en Deezer, con la barra clavada en 55 %. La cancelación
sólo se nota cuando alguien avisa avance, y esa fase no avisaba nada. Cubre:

  - que cada fase larga avise avance, y que cancelar corte ahí
  - que Deezer reintente sólo lo pasajero, y que una falla se cuente
  - que un Retry-After raro no tumbe nada, y que YouTube reintente su límite
  - la barra del armado por tramos
"""

import io
import json
import threading
from email.message import Message
import time
import types
import urllib.error

import pytest

import jobs as J
from conftest import _producto, _track
from migrador import audio as A
from migrador import paquete as pq
from migrador import relevar_core as R


def _cabeceras(**valores):
    m = Message()
    for k, v in valores.items():
        m[k] = v
    return m


@pytest.fixture(autouse=True)
def sin_esperas(monkeypatch):
    monkeypatch.setattr(R.time, "sleep", lambda s: None)


# ---- Deezer: avance y cancelación ----


def _deezer_lento(monkeypatch, llamadas):
    lock = threading.Lock()

    def match(t, artist):
        with lock:
            llamadas.append(t["track"])
        time.sleep(0.01)
        return "", None, ""

    monkeypatch.setattr(R, "deezer_match", match)
    monkeypatch.setattr(R, "deezer_albumes", lambda ids: {})


def test_la_busqueda_de_codigos_avisa_cada_track(monkeypatch):
    _deezer_lento(monkeypatch, [])
    visto = []
    R.enrich_with_codes(
        [_track(f"T{i}") for i in range(25)],
        "A",
        log=lambda *_: None,
        avance=lambda h, n: visto.append((h, n)),
    )
    assert visto[-1] == (25, 25)
    assert [h for h, _n in visto] == list(range(1, 26))


def test_cancelar_corta_la_busqueda_enseguida(monkeypatch):
    llamadas = []
    _deezer_lento(monkeypatch, llamadas)

    def avance(h, n):
        if h >= 12:
            raise J.Cancelado()

    inicio = time.monotonic()
    with pytest.raises(J.Cancelado):
        R.enrich_with_codes([_track(f"T{i}") for i in range(300)], "A", log=lambda *_: None, avance=avance)
    # Lo que importa es que responda enseguida: antes eran 24 segundos. Cuántas
    # consultas llegan a salir antes del corte depende de la carga de la máquina,
    # así que sólo se exige que no hayan salido todas.
    assert time.monotonic() - inicio < 2
    assert len(llamadas) < 300, "las consultas pendientes tenían que cancelarse"


def test_el_trabajo_mueve_la_barra_sin_llenar_el_log():
    job = J.Job("prueba")
    job.fraccion(0.4)
    assert job.progreso == 0.4 and job.log == []
    job.cancelar()
    with pytest.raises(J.Cancelado):
        job.fraccion(0.5)


def test_listar_y_bajar_metadata_avisan_avance(monkeypatch):
    paginas = [
        {
            "items": [{"contentDetails": {"videoId": f"v{i}"}} for i in range(50)],
            "nextPageToken": "p2",
            "pageInfo": {"totalResults": 75},
        },
        {
            "items": [{"contentDetails": {"videoId": f"w{i}"}} for i in range(25)],
            "pageInfo": {"totalResults": 75},
        },
    ]
    monkeypatch.setattr(
        R,
        "api_get",
        lambda endpoint, params, key: paginas.pop(0) if endpoint == "playlistItems" else {"items": []},
    )
    visto = []
    ids = R.list_video_ids("UU1", "k", avance=lambda h, t: visto.append((h, t)))
    assert len(ids) == 75 and visto == [(50, 75), (75, 75)]

    visto.clear()
    R.fetch_videos(ids, "k", avance=lambda h, t: visto.append((h, t)))
    assert visto == [(50, 75), (75, 75)]


# ---- Deezer: reintentos ----


def _deezer_responde(monkeypatch, *respuestas):
    pedidos = []

    def http_json(url, headers=None, retries=3):
        pedidos.append(url)
        return respuestas[min(len(pedidos), len(respuestas)) - 1]

    monkeypatch.setattr(R, "_http_json", http_json)
    return pedidos


def test_un_no_hay_datos_no_se_reintenta(monkeypatch):
    """Antes eran seis reintentos con espera: nueve segundos por consulta."""
    pedidos = _deezer_responde(monkeypatch, {"error": {"code": 800, "message": "no data"}})
    R.FALLAS_DEEZER.empezar()
    assert R._deezer_json("album/1") is None
    assert len(pedidos) == 1
    assert R.FALLAS_DEEZER.n == 0, "no es una falla: es que no existe"


def test_el_limite_de_tasa_se_reintenta_y_despues_se_cuenta(monkeypatch):
    pedidos = _deezer_responde(monkeypatch, {"error": {"code": 4}})
    R.FALLAS_DEEZER.empezar()
    assert R._deezer_json("search?q=x") is None
    assert len(pedidos) == 6
    assert R.FALLAS_DEEZER.n == 1


def test_el_limite_de_tasa_pasajero_se_recupera(monkeypatch):
    _deezer_responde(monkeypatch, {"error": {"code": 4}}, {"data": [1]})
    assert R._deezer_json("search?q=x") == {"data": [1]}


def test_deezer_caido_queda_dicho_en_el_log(monkeypatch):
    _deezer_responde(monkeypatch, None)
    log = []
    stats = R.enrich_with_codes([_track("Tema")], "A", log=log.append)
    assert stats["fallas"] > 0
    assert any("Deezer no respondió" in linea for linea in log)


@pytest.mark.parametrize(
    "valor, esperado",
    [("3", 3.0), ("Wed, 21 Oct 2026 07:28:00 GMT", 2.0), ("9999", 30.0), (None, 2.0)],
)
def test_un_retry_after_raro_no_tumba_nada(valor, esperado):
    """Con una fecha HTTP, `int()` levantaba y eso cortaba el relevamiento."""
    e = types.SimpleNamespace(headers={} if valor is None else {"Retry-After": valor})
    assert R._retry_after(e) == esperado


def test_http_json_con_retry_after_de_fecha_reintenta_y_sigue(monkeypatch):
    intentos = []

    class Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b'{"ok": 1}'

    def urlopen2(req, timeout=None):
        intentos.append(1)
        if len(intentos) == 1:
            raise urllib.error.HTTPError(
                req.full_url,
                429,
                "lento",
                _cabeceras(**{"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"}),
                None,
            )
        return Resp()

    monkeypatch.setattr(R.urllib.request, "urlopen", urlopen2)
    assert R._http_json("https://api.deezer.com/x") == {"ok": 1}


# ---- YouTube: el límite de tasa se reintenta, la cuota no ----


def _youtube(monkeypatch, *errores):
    pedidos = []

    class Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b'{"items": []}'

    def urlopen(req, timeout=None):
        pedidos.append(1)
        if len(pedidos) <= len(errores):
            codigo, motivo = errores[len(pedidos) - 1]
            cuerpo = json.dumps({"error": {"errors": [{"reason": motivo}], "message": motivo}}).encode()
            raise urllib.error.HTTPError(req.full_url, codigo, motivo, _cabeceras(), io.BytesIO(cuerpo))
        return Resp()

    monkeypatch.setattr(R.urllib.request, "urlopen", urlopen)
    return pedidos


def test_el_limite_de_tasa_de_youtube_se_reintenta(monkeypatch):
    pedidos = _youtube(monkeypatch, (403, "rateLimitExceeded"))
    assert R.api_get("channels", {}, "k") == {"items": []}
    assert len(pedidos) == 2


def test_la_cuota_agotada_no_se_reintenta(monkeypatch):
    pedidos = _youtube(monkeypatch, (403, "quotaExceeded"))
    with pytest.raises(R.RelevarError) as e:
        R.api_get("channels", {}, "k")
    assert e.value.codigo == "cuota"
    assert len(pedidos) == 1


# ---- el armado ----


def test_el_zip_avisa_cada_producto(tmp_path):
    visto = []
    productos = [_producto(title=f"Disco {i}", tracks=[_track(f"T{i}")]) for i in range(3)]
    for i, p in enumerate(productos):
        p["folder"] = f"2020 - Disco {i}"
    pq.build_zip(
        productos, "A", str(tmp_path / "p.zip"), log=lambda *_: None, avance=lambda h, n: visto.append((h, n))
    )
    assert visto == [(1, 3), (2, 3), (3, 3)]


def test_el_audio_avisa_cada_descarga(monkeypatch, tmp_path):
    monkeypatch.setattr(
        A,
        "bajar_referencia_youtube",
        lambda vid, d, log=None, errores=None: (tmp_path / f"{vid}.m4a", "ref", ".m4a"),
    )
    visto = []
    productos = [_producto(tracks=[_track("Uno", vid="a"), _track("Dos", vid="b")])]
    A.fetch_audio(
        productos, dest_dir=str(tmp_path), log=lambda *_: None, avance=lambda h, n: visto.append((h, n))
    )
    assert visto == [(1, 2), (2, 2)]
