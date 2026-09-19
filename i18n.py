# -*- coding: utf-8 -*-
"""
Textos de la app en español e inglés.

Todo lo que el usuario lee sale de acá: los mensajes del log, los errores, los
rótulos de las planillas y el contenido de los archivos que van adentro del ZIP.
La interfaz tiene su propio catálogo en `app/web/i18n.js`, porque se dibuja en el
navegador y pedirle cada rótulo al servidor sería absurdo.

Cómo se usa:

    from i18n import T
    log(T("portadas.buscando", n=3, total=10))

Tres decisiones que el resto del código da por sentadas:

  - **La clave es el contrato, no el texto.** Si falta una traducción se cae al
    español, y si falta la clave entera se devuelve la clave. Nunca revienta: un
    texto sin traducir es un problema de traducción, no un motivo para que la app
    no arranque.

  - **El idioma es global y de un solo usuario.** Esto es una app de escritorio
    que corre para una persona, así que un módulo con estado alcanza y sobra. Si
    algún día sirviera a varios, esto hay que repensarlo.

  - **Las cabeceras de la hoja de ingesta no están acá y no se traducen.** Son
    los nombres de campo que espera la distribuidora, no texto para leer. Ver
    `paquete.COLUMNAS_INGESTA`.
"""

import os

IDIOMAS = ("es", "en")
POR_DEFECTO = "es"

_actual = POR_DEFECTO


# ============================================================
# Estado
# ============================================================

def idioma():
    """El idioma en uso, siempre uno de IDIOMAS."""
    return _actual


def poner_idioma(codigo):
    """Cambia el idioma. Devuelve el que quedó puesto.

    Acepta basura sin quejarse (un config.json editado a mano, una variable de
    entorno rara) y en ese caso deja el que había.
    """
    global _actual
    c = (codigo or "").strip().lower()[:2]
    if c in IDIOMAS:
        _actual = c
    return _actual


def idioma_del_sistema():
    """El idioma que parece querer el sistema operativo.

    Se mira el entorno primero porque es lo que respeta un usuario que arranca
    la app con LANG puesto a mano, y recién después la config regional. Cualquier
    cosa que no sea inglés cae en español, que es el idioma del proyecto.
    """
    for var in ("MIGRADOR_IDIOMA", "LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        v = (os.environ.get(var) or "").strip().lower()
        if v[:2] in IDIOMAS:
            return v[:2]

    try:
        import locale
        v = (locale.getlocale()[0] or "")
        if not v:
            # En Windows getlocale() devuelve None hasta que alguien llama a
            # setlocale. getdefaultlocale está deprecada pero es lo único que
            # contesta sin efectos de borde.
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                v = (locale.getdefaultlocale()[0] or "")
        v = v.strip().lower()
        if v.startswith("en"):
            return "en"
        if v.startswith("es"):
            return "es"
        # Windows devuelve nombres largos tipo "English_United States".
        if v.startswith("english"):
            return "en"
        if v.startswith("spanish"):
            return "es"
    except Exception:
        pass
    return POR_DEFECTO


# ============================================================
# Traducción
# ============================================================

def T(clave, **kw):
    """El texto de `clave` en el idioma actual, con los parámetros aplicados.

    Los parámetros van con formato de `str.format`: "{n} de {total}".
    """
    entrada = TEXTOS.get(clave)
    if entrada is None:
        return clave
    txt = entrada.get(_actual) or entrada.get(POR_DEFECTO) or clave
    if not kw:
        return txt
    try:
        return txt.format(**kw)
    except (KeyError, IndexError, ValueError):
        # Una llave de formato que no llegó no puede tumbar un relevamiento de
        # cuarenta minutos. Se devuelve el texto crudo y se sigue.
        return txt


def claves_sin_traducir(a="es", b="en"):
    """Las claves que existen en `a` y faltan en `b`. La usa el test."""
    return sorted(k for k, v in TEXTOS.items() if v.get(a) and not v.get(b))


# ============================================================
# Catálogo
#
# Ordenado por módulo. La clave lleva el prefijo del módulo que la emite, así
# buscar de dónde sale un texto es un grep y no una cacería.
# ============================================================

TEXTOS = {

    # ---- server ------------------------------------------------------------
    "server.idioma_invalido": {
        "es": "Idioma no reconocido. Los que hay son: {idiomas}.",
        "en": "Unknown language. The ones available are: {idiomas}.",
    },
    "server.falta_url": {
        "es": "Pegá el link del canal de YouTube.",
        "en": "Paste the YouTube channel link.",
    },
    "server.url_larga": {
        "es": "Ese link es demasiado largo para ser un canal de YouTube.",
        "en": "That link is too long to be a YouTube channel.",
    },
}
