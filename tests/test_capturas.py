# -*- coding: utf-8 -*-
"""Las capturas del README. Sin Chrome y sin red.

Sacarlas de verdad necesita un navegador, y eso lo hace `build/capturas.py` en
la verificación completa. Acá se prueba lo que se puede sin él: que el material
de ejemplo diga lo mismo que la app.

  - los hallazgos de ejemplo tienen el nivel que les da `validar.py`
  - sus textos y las líneas del log salen del catálogo de i18n, en el idioma
    de la captura
  - los temporales no van a `build/migrador/`
"""

import os

import capturas
from conftest import RAIZ, _jpeg, _producto, _track
from migrador import i18n
from migrador import validar as V
from migrador.i18n import T


def test_los_hallazgos_de_ejemplo_tienen_el_nivel_que_da_la_validacion():
    """El ejemplo mostraba la falta de UPC como error, y la validación la emite
    como aviso: la captura enseñaba una validación que la app no hace."""
    p = _producto(
        title="Sesiones",
        upc="",
        label="",
        orden_ok=False,
        cover=_jpeg(1400, 1400),
        tracks=[
            _track("Hormiga (Official Video)", isrc="ARCB2240000"),
            _track("Otra", isrc="ARCB22400002"),
        ],
    )
    emitidos = {h["codigo"]: h["nivel"] for h in V.validar([p])["hallazgos"]}
    for h in capturas.resultado_demo()["validacion"]["hallazgos"]:
        assert emitidos.get(h["codigo"]) == h["nivel"], h["codigo"]


def test_el_resumen_de_ejemplo_cuenta_lo_que_muestra():
    v = capturas.resultado_demo()["validacion"]
    niveles = [h["nivel"] for h in v["hallazgos"]]
    assert v["resumen"]["errores"] == niveles.count("error")
    assert v["resumen"]["avisos"] == niveles.count("aviso")
    catalogo = capturas.catalogo_demo()["resumen"]
    assert v["resumen"]["productos"] == catalogo["products"]
    assert v["resumen"]["tracks"] == catalogo["tracks"]


def test_los_textos_de_ejemplo_salen_del_catalogo_en_los_dos_idiomas():
    """Escritos a mano se habían desviado de lo que la app escribe."""
    for idioma in i18n.IDIOMAS:
        i18n.poner_idioma(idioma)
        assert capturas.hallazgos_demo()[0] == T("val.upc_falta")
        assert T("por.sin_match") in capturas.log_portadas()[-1]
    i18n.poner_idioma("es")
    assert "está en Apple Music" in capturas.log_portadas()[-1]


def test_los_temporales_no_crean_una_carpeta_llamada_migrador_en_build():
    """`build/migrador/` al lado del path es un paquete de espacio de nombres
    que tapa al de verdad. El ciclo 1 la sacó de PyInstaller."""
    with open(os.path.join(RAIZ, "build", "capturas.py"), encoding="utf-8") as f:
        fuente = f.read()
    assert '"build", "migrador"' not in fuente
