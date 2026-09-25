# -*- coding: utf-8 -*-
"""La clave de YouTube no sale de donde tiene que estar. Sin red.

- viaja en una cabecera y nunca en la URL, así ningún error la puede citar
- la config se escribe con permisos cerrados desde que nace
- el control de claves revisa también la historia de git
"""

import os
import subprocess
import urllib.error

import pytest

import server as backend
import sin_claves
from migrador import relevar_core as R

# Armada por partes, para que este mismo archivo no parezca tener una clave.
CLAVE = "AIza" + "Sy" + "X" * 33


class _Respuesta:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return b'{"items": []}'


def test_la_clave_va_en_una_cabecera_y_no_en_la_url(monkeypatch):
    visto = {}

    def urlopen(req, timeout=None):
        visto["url"], visto["cabeceras"] = req.full_url, dict(req.header_items())
        return _Respuesta()

    monkeypatch.setattr(R.urllib.request, "urlopen", urlopen)
    R.api_get("channels", {"part": "id", "id": "UC123"}, CLAVE)
    assert CLAVE not in visto["url"] and "key=" not in visto["url"]
    assert visto["cabeceras"].get("X-goog-api-key") == CLAVE


@pytest.mark.parametrize(
    "falla",
    [
        lambda req: urllib.error.URLError(f"no se pudo abrir {req.full_url}"),
        lambda req: TimeoutError(f"timeout en {req.full_url}"),
        lambda req: ValueError(f"respuesta rara de {req.full_url}"),
    ],
)
def test_ningun_error_de_red_muestra_la_clave(monkeypatch, falla):
    """Aunque la excepción cite la URL entera, la clave no está ahí."""

    def urlopen(req, timeout=None):
        raise falla(req)

    monkeypatch.setattr(R.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(R.time, "sleep", lambda s: None)
    with pytest.raises(R.RelevarError) as e:
        R.api_get("channels", {"part": "id"}, CLAVE)
    assert CLAVE not in str(e.value)
    assert CLAVE not in repr(e.value.__cause__)


def test_la_config_nace_con_permisos_cerrados(monkeypatch, tmp_path):
    modos = {}
    abrir = os.open

    def os_open(ruta, flags, modo=0o777):
        modos[os.path.basename(ruta)] = modo
        return abrir(ruta, flags, modo)

    monkeypatch.setattr(backend, "dir_datos", lambda: str(tmp_path))
    monkeypatch.setattr(backend.os, "open", os_open)
    backend.guardar_config({"youtube_api_key": CLAVE})
    assert modos["config.json.tmp"] == 0o600
    assert backend.leer_config()["youtube_api_key"] == CLAVE


def test_la_carpeta_de_la_config_nace_cerrada(monkeypatch, tmp_path):
    pedidos = {}

    def makedirs(ruta, mode=0o777, exist_ok=False):
        pedidos["modo"] = mode

    monkeypatch.setattr(backend.os.path, "expanduser", lambda _: str(tmp_path))
    monkeypatch.setattr(backend.os, "makedirs", makedirs)
    backend.dir_datos()
    assert pedidos["modo"] == 0o700


def _git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def test_una_clave_que_entro_y_salio_se_encuentra_en_la_historia(tmp_path, monkeypatch, capsys):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    (repo / "a.py").write_text(f'CLAVE = "{CLAVE}"\n', encoding="utf-8")
    _git(repo, "add", "a.py")
    _git(repo, "commit", "-qm", "con clave")
    (repo / "a.py").write_text("CLAVE = ''\n", encoding="utf-8")
    _git(repo, "commit", "-qam", "sin clave")

    monkeypatch.chdir(repo)
    assert sin_claves.main(["--todo"]) == 0, "en el árbol de hoy ya no está"
    assert sin_claves.main(["--historia"]) == 1, "pero en la historia sí"
    salida = capsys.readouterr().out
    assert "a.py" in salida
    assert CLAVE not in salida, "nunca se imprime la clave"
