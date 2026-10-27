# -*- coding: utf-8 -*-
"""Que las conexiones HTTPS tengan contra qué verificarse. Sin red.

Por qué existe. El .app de macOS salió sin encontrar los certificados del
sistema y toda consulta a YouTube fallaba con CERTIFICATE_VERIFY_FAILED, con un
mensaje que mandaba a revisar la conexión a internet. Estos tests fijan las dos
partes del arreglo: que se use certifi cuando el sistema no tiene certificados, y
que si la verificación igual falla el mensaje diga lo que pasa.
"""

import ssl
import urllib.error
from types import SimpleNamespace

import certifi
import pytest

from migrador import certificados as C
from migrador import relevar_core as R


def _rutas(cafile=None, capath=None):
    """Lo que devuelve `ssl.get_default_verify_paths()`: None si la ruta no existe."""
    return SimpleNamespace(cafile=cafile, capath=capath)


@pytest.fixture
def sin_variables(monkeypatch):
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)
    monkeypatch.delenv("SSL_CERT_DIR", raising=False)


def test_sin_certificados_del_sistema_usa_los_de_certifi(monkeypatch, sin_variables):
    """Es el caso del .app: la ruta grabada en OpenSSL no existe en la Mac."""
    monkeypatch.setattr(C.ssl, "get_default_verify_paths", lambda: _rutas())
    C.preparar()
    assert C.os.environ["SSL_CERT_FILE"] == certifi.where()


def test_con_certificados_del_sistema_no_los_toca(monkeypatch, sin_variables):
    """Los del sistema pueden traer la raíz de una red de oficina; certifi no."""
    monkeypatch.setattr(C.ssl, "get_default_verify_paths", lambda: _rutas(cafile="/etc/ssl/cert.pem"))
    C.preparar()
    assert "SSL_CERT_FILE" not in C.os.environ


def test_lo_que_eligio_quien_lanzo_la_app_se_respeta(monkeypatch):
    monkeypatch.setenv("SSL_CERT_FILE", "/mi/raiz.pem")
    monkeypatch.setattr(C.ssl, "get_default_verify_paths", lambda: _rutas())
    C.preparar()
    assert C.os.environ["SSL_CERT_FILE"] == "/mi/raiz.pem"


def test_el_paquete_de_certifi_existe_y_tiene_raices():
    """Si el archivo no está, apuntar a él no arregla nada."""
    ctx = ssl.create_default_context(cafile=certifi.where())
    assert ctx.cert_store_stats()["x509_ca"] > 50


def test_un_certificado_rechazado_no_dice_que_falta_internet(monkeypatch):
    llamadas = []

    def urlopen(req, timeout=None):
        llamadas.append(req)
        raise urllib.error.URLError(ssl.SSLCertVerificationError(1, "certificate verify failed"))

    monkeypatch.setattr(R.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(R.time, "sleep", lambda s: None)
    with pytest.raises(R.RelevarError) as e:
        R.api_get("channels", {"part": "id"}, "clave")
    assert "certificado" in str(e.value) or "certificate" in str(e.value)
    assert "internet" not in str(e.value)
    assert len(llamadas) == 1  # reintentar da el mismo resultado


def test_si_no_se_llego_a_youtube_no_se_culpa_a_la_clave(monkeypatch):
    """La pantalla de la clave propia decía «La clave no funcionó» por el mismo
    certificado rechazado. La clave nunca se llegó a probar."""
    import server as backend

    def sin_red(endpoint, params, key):
        raise R.RelevarError("no se llegó", "red")

    monkeypatch.setattr(backend.R, "api_get", sin_red)
    monkeypatch.setattr(backend, "guardar_clave", lambda c: pytest.fail("no tenía que guardarla"))
    with pytest.raises(ValueError) as e:
        backend.api_guardar_clave({"clave": "una-clave"})
    assert "no funcionó" not in str(e.value) and "did not work" not in str(e.value)
