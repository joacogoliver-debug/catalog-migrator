# -*- coding: utf-8 -*-
"""Corre los tests de la interfaz (tests/js/), que son de Node, desde pytest.

Así `pytest -q`, que es lo que corre la verificación completa, el build y el
CI, los cubre sin un paso aparte. Node no es una dependencia del proyecto: si no
está instalado, estos tests se saltean con el motivo dicho. En los runners de
GitHub viene instalado.
"""

import os
import shutil
import subprocess

import pytest

from conftest import RAIZ

NODE = shutil.which("node")


@pytest.mark.skipif(NODE is None, reason="Node no está instalado: los tests de app.js no corren")
def test_los_tests_de_la_interfaz_pasan():
    archivo = os.path.join(RAIZ, "tests", "js", "app.test.mjs")
    r = subprocess.run(
        [NODE or "node", "--test", archivo],
        cwd=RAIZ,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )
    assert r.returncode == 0, (r.stdout or "")[-3000:] + (r.stderr or "")[-2000:]
