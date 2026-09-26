# -*- coding: utf-8 -*-
"""Las reglas de supply chain del CI, verificadas en los archivos. Sin red.

Un workflow no se puede correr acá, pero lo que importa de su seguridad está
escrito en él y se puede leer. Cubre:

  - que toda acción esté fijada por SHA, no por un tag que se puede mover
  - que la escritura la tenga sólo el job que publica
  - que todo job tenga timeout
  - que las dependencias se auditen y se actualicen
  - que los tests del build corran sin la clave en el entorno
"""

import importlib.util
import os
import re
import types

import pytest
import yaml

from conftest import RAIZ

WORKFLOWS = [os.path.join(RAIZ, ".github", "workflows", n) for n in ("tests.yml", "build.yml")]


def _cargar(ruta):
    with open(ruta, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _usos(ruta):
    with open(ruta, encoding="utf-8") as f:
        return re.findall(r"uses:\s*(\S+)(.*)", f.read())


@pytest.mark.parametrize("ruta", WORKFLOWS)
def test_toda_accion_esta_fijada_por_sha_con_su_tag(ruta):
    usos = _usos(ruta)
    assert usos
    for accion, resto in usos:
        assert re.fullmatch(r"[\w.-]+/[\w.-]+@[0-9a-f]{40}", accion), accion
        assert re.search(r"#\s*v\d", resto), f"{accion} sin el tag al lado"


@pytest.mark.parametrize("ruta", WORKFLOWS)
def test_de_base_ningun_workflow_escribe(ruta):
    assert _cargar(ruta)["permissions"] == {"contents": "read"}


def test_la_escritura_la_tiene_solo_el_que_publica():
    jobs = _cargar(WORKFLOWS[1])["jobs"]
    escriben = [n for n, j in jobs.items() if (j.get("permissions") or {}).get("contents") == "write"]
    assert escriben == ["publicar"]
    assert jobs["build"]["permissions"]["id-token"] == "write"  # la atestación


@pytest.mark.parametrize("ruta", WORKFLOWS)
def test_todo_job_tiene_timeout(ruta):
    for nombre, job in _cargar(ruta)["jobs"].items():
        assert job.get("timeout-minutes"), nombre


def test_las_dependencias_se_auditan():
    job = _cargar(WORKFLOWS[0])["jobs"]["dependencias"]
    comandos = " ".join(p.get("run", "") for p in job["steps"])
    for archivo in ("requirements-app.txt", "requirements-audio.txt", "requirements-build.txt"):
        assert archivo in comandos


def test_dependabot_mira_las_acciones_y_pip():
    config = _cargar(os.path.join(RAIZ, ".github", "dependabot.yml"))
    assert {u["package-ecosystem"] for u in config["updates"]} == {"github-actions", "pip"}


def test_el_compilador_tiene_version_fija():
    with open(os.path.join(RAIZ, "requirements-build.txt"), encoding="utf-8") as f:
        lineas = [x.strip() for x in f if x.strip() and not x.startswith("#")]
    assert lineas and all("==" in x for x in lineas)


def test_los_tests_del_build_corren_sin_la_clave(monkeypatch):
    spec = importlib.util.spec_from_file_location("build_build", os.path.join(RAIZ, "build", "build.py"))
    assert spec and spec.loader
    build = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build)

    visto = {}

    def run(cmd, **kw):
        visto.update(kw["env"])
        return types.SimpleNamespace(returncode=0, stdout="ok", stderr="")

    monkeypatch.setenv("MIGRADOR_CLAVE_YT", "clave-de-prueba")
    monkeypatch.setenv("YOUTUBE_API_KEY", "otra-de-prueba")
    monkeypatch.setattr(build.subprocess, "run", run)
    monkeypatch.setattr(build, "paso", lambda *_: None)
    build.probar_tests()
    assert "MIGRADOR_CLAVE_YT" not in visto and "YOUTUBE_API_KEY" not in visto


# ============================================================
# Plantillas de issue
# ============================================================

PLANTILLAS = os.path.join(RAIZ, ".github", "ISSUE_TEMPLATE")
# Las etiquetas que existen en el repositorio. Una plantilla que nombra una que
# no existe no avisa nada: GitHub la ignora y el issue entra sin etiqueta.
ETIQUETAS_DEL_REPO = {"bug", "enhancement", "question", "documentation", "accessibility"}


@pytest.mark.parametrize("nombre", sorted(n for n in os.listdir(PLANTILLAS) if n != "config.yml"))
def test_cada_plantilla_de_issue_es_un_formulario_valido(nombre):
    p = _cargar(os.path.join(PLANTILLAS, nombre))
    assert p["name"] and p["description"] and p["body"]
    assert set(p.get("labels", [])) <= ETIQUETAS_DEL_REPO, f"{nombre}: etiqueta que el repo no tiene"


def test_hay_donde_hacer_una_pregunta():
    """«¿Funciona con mi distribuidora?» no es un error ni una idea, y con el
    issue en blanco apagado no había dónde preguntarlo."""
    preguntas = [
        n
        for n in os.listdir(PLANTILLAS)
        if "question" in (_cargar(os.path.join(PLANTILLAS, n)).get("labels") or [])
    ]
    assert preguntas
