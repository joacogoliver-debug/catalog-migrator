# -*- coding: utf-8 -*-
"""Test offline de los dos catálogos de traducción (sin red, sin pytest).

Corré:  python test_i18n.py
Sale 0 si todo pasa, 1 si algo falla.

La app tiene dos catálogos, uno por proceso: `i18n.py` para lo que arma Python
(el log, los errores, los archivos del ZIP) y `app/web/i18n.js` para la interfaz.
Son dos porque son dos procesos, y eso abre tres formas de romperlos que no se
ven hasta que alguien abre la app en inglés:

  - una clave traducida al español y no al inglés, que sale en español sin avisar;
  - una clave que la interfaz usa y el catálogo no define, que sale como
    "paso2.titulo" en la pantalla;
  - el nombre de un archivo del ZIP que la interfaz nombra distinto de como lo
    escribe `paquete.py`, que manda a buscar algo que no existe.

Este test cubre las tres.
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import i18n                                                        # noqa: E402

FALLOS = []


def check(nombre, cond, detalle=""):
    if not cond:
        FALLOS.append(f"  [{nombre}] {detalle}")


def _catalogo_js():
    """Las entradas de app/web/i18n.js, como {clave: {es, en}}.

    Se parsea con expresiones regulares y no con un motor de JS: el archivo es
    un objeto literal plano y meter una dependencia para leerlo sería peor que
    el problema que resuelve.
    """
    s = io.open(os.path.join(HERE, "app", "web", "i18n.js"), encoding="utf-8").read()
    cuerpo = s[s.index("const TEXTOS = {"):]
    entradas = {}

    def anotar(clave, bloque):
        entradas[clave] = {
            "es": bool(re.search(r"\bes:\s*[`'\"]", bloque)),
            "en": bool(re.search(r"\ben:\s*[`'\"]", bloque)),
        }

    # Las de una sola línea: 'clave': { es: '...', en: '...' },
    for m in re.finditer(r"^  '([a-z0-9_.]+)':\s*\{([^\n]*)\},$", cuerpo, re.M):
        anotar(m.group(1), m.group(2))

    # Las de varias líneas. El `\{\n` no es adorno: sin él, una entrada de una
    # sola línea abría un match que seguía leyendo hasta el próximo `  },` y se
    # tragaba enteras las entradas del medio, que entonces figuraban como no
    # definidas.
    for m in re.finditer(r"^  '([a-z0-9_.]+)':\s*\{\n(.*?)^  \},", cuerpo, re.S | re.M):
        anotar(m.group(1), m.group(2))

    return entradas


def _claves_usadas_en_la_interfaz():
    app = io.open(os.path.join(HERE, "app", "web", "app.js"), encoding="utf-8").read()
    html = io.open(os.path.join(HERE, "app", "web", "index.html"), encoding="utf-8").read()
    usadas = set(re.findall(r"T\(\s*'([a-z0-9_.]+)'", app))
    usadas |= set(re.findall(r'data-t(?:-title|-aria)?="([a-z0-9_.]+)"', html))
    # Las que se arman concatenando un prefijo con un código.
    cods = re.search(r"const CODIGOS_HALLAZGO = \[(.*?)\];", app, re.S)
    usadas |= {"hallazgo." + c for c in re.findall(r"'(\w+)'", cods.group(1))}
    usadas |= {"stepper." + p for p in ("paso1", "paso2", "paso3", "paso4")}
    # Las que se eligen con un ternario adentro del propio T(...). Se exige el
    # `T(` delante: sin eso entraban ternarios que no tienen nada que ver, como
    # el que elige entre los iconos 'sol' y 'luna'.
    for a, b in re.findall(r"T\([^)]*?\?\s*'([a-z0-9_.]+)'\s*:\s*'([a-z0-9_.]+)'", app):
        usadas |= {a, b}
    # Los prefijos sueltos son artefactos de la concatenación, no claves.
    return {k for k in usadas if not k.endswith(".")}


def main():
    # --- Python: ninguna clave a medio traducir -------------------------
    sin_en = i18n.claves_sin_traducir("es", "en")
    check("py.todas_en_ingles", not sin_en, f"sin traducir: {sin_en}")
    sin_es = i18n.claves_sin_traducir("en", "es")
    check("py.todas_en_espanol", not sin_es, f"sin original: {sin_es}")
    check("py.hay_catalogo", len(i18n.TEXTOS) > 100, f"{len(i18n.TEXTOS)} claves")

    # --- Interfaz: ídem -------------------------------------------------
    js = _catalogo_js()
    check("js.hay_catalogo", len(js) > 100, f"{len(js)} claves")
    js_sin_en = sorted(k for k, v in js.items() if v["es"] and not v["en"])
    check("js.todas_en_ingles", not js_sin_en, f"sin traducir: {js_sin_en}")
    js_sin_es = sorted(k for k, v in js.items() if v["en"] and not v["es"])
    check("js.todas_en_espanol", not js_sin_es, f"sin original: {js_sin_es}")

    # --- Interfaz: nada sin definir, nada de más ------------------------
    usadas = _claves_usadas_en_la_interfaz()
    faltan = sorted(usadas - set(js))
    check("js.sin_definir", not faltan, f"usadas y no definidas: {faltan}")
    sobran = sorted(set(js) - usadas)
    check("js.sin_usar", not sobran, f"definidas y sin usar: {sobran}")

    # --- El nombre del archivo tiene que decir lo mismo de los dos lados -
    # La pantalla 4 manda a abrir el informe de validación por su nombre. Si
    # `paquete.py` lo escribe distinto, manda a buscar un archivo que no existe.
    s = io.open(os.path.join(HERE, "app", "web", "i18n.js"), encoding="utf-8").read()
    bloque = re.search(r"'archivos\.validacion':\s*\{(.*?)\},", s, re.S).group(1)
    for idioma in ("es", "en"):
        en_js = re.search(rf"{idioma}:\s*'([^']+)'", bloque).group(1)
        i18n.poner_idioma(idioma)
        en_py = i18n.T("paq.f_validacion")
        check(f"archivo.validacion.{idioma}", en_js == en_py,
              f"js={en_js!r} py={en_py!r}")
    i18n.poner_idioma("es")

    # --- Ninguna clave definida dos veces -------------------------------
    # Un diccionario de Python se come las claves repetidas sin decir nada: la
    # ultima gana y la primera desaparece. Como las dos entradas suelen ser
    # parecidas, el texto sigue saliendo en el idioma correcto y la unica senal
    # es que cambio una palabra. Por eso se lee el archivo, no el diccionario ya
    # construido: en el diccionario la duplicada ya no existe.
    fuente = io.open(os.path.join(HERE, "i18n.py"), encoding="utf-8").read()
    cuerpo = fuente[fuente.index("TEXTOS = {"):]
    literales = re.findall(r'^    "([a-z0-9_.]+)":', cuerpo, re.M)
    repetidas = sorted({k for k in literales if literales.count(k) > 1})
    check("py.sin_claves_repetidas", not repetidas, f"definidas dos veces: {repetidas}")

    fuente_js = io.open(os.path.join(HERE, "app", "web", "i18n.js"), encoding="utf-8").read()
    cuerpo_js = fuente_js[fuente_js.index("const TEXTOS = {"):]
    js_literales = re.findall(r"^  '([a-z0-9_.]+)':", cuerpo_js, re.M)
    js_repetidas = sorted({k for k in js_literales if js_literales.count(k) > 1})
    check("js.sin_claves_repetidas", not js_repetidas, f"definidas dos veces: {js_repetidas}")

    # --- El formato no se rompe al traducir -----------------------------
    # Una clave cuyo texto en inglés se olvida un {parametro} que el español sí
    # tiene deja un hueco en la frase, y al revés revienta el format().
    for clave, entrada in i18n.TEXTOS.items():
        pes = set(re.findall(r"\{(\w+)\}", entrada.get("es", "")))
        pen = set(re.findall(r"\{(\w+)\}", entrada.get("en", "")))
        check(f"formato.{clave}", pes == pen, f"es={sorted(pes)} en={sorted(pen)}")

    if FALLOS:
        print("FALLARON:")
        print("\n".join(FALLOS))
        return 1
    print(f"OK - i18n ({len(i18n.TEXTOS)} claves en Python, {len(js)} en la interfaz)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
