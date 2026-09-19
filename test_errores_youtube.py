# -*- coding: utf-8 -*-
"""Test offline de la traducción de errores de la YouTube Data API.

Corré:  python test_errores_youtube.py
Sale 0 si todo pasa, 1 si algo falla. No necesita red ni claves.

Por qué existe: lo que devuelve Google viene en inglés, con jerga y a veces con
un `<a href>` adentro del mensaje. Mostrarlo tal cual deja a la persona sin saber
qué hacer, y el caso más probable,el cupo diario agotado cuando muchos usan la
misma copiaes justo el que tiene solución simple. Este test fija que esa
traducción exista y que el código que la acompaña sea el correcto, porque de ese
código depende que la interfaz ofrezca el botón para cargar una clave propia.
"""
import json
import os

# Este test compara los mensajes en español, así que el idioma se fija:
# si no, en una máquina con el sistema en inglés compararía contra otra cosa.
os.environ["MIGRADOR_IDIOMA"] = "es"
import sys

import relevar_core as R


def cuerpo(reason, message, code=403):
    """Un error con la forma real de los de Google."""
    return json.dumps({
        "error": {
            "code": code,
            "message": message,
            "errors": [{"domain": "youtube.quota", "reason": reason,
                        "message": message}],
        }
    })


def main():
    fails = []

    def check(nombre, cond, detalle=""):
        if not cond:
            fails.append(f"  [{nombre}] falló {detalle}")

    # --- cupo agotado: el caso que más va a pasar -------------------------
    e = R._error_de_youtube(403, cuerpo(
        "quotaExceeded",
        'The request cannot be completed because you have exceeded your '
        '<a href="/youtube/v3/getting-started#quota">quota</a>.'))
    check("cuota.es_relevar_error", isinstance(e, R.RelevarError))
    check("cuota.codigo", e.codigo == "cuota", f"codigo={e.codigo!r}")
    check("cuota.en_castellano", "cupo" in str(e).lower(), str(e))
    check("cuota.dice_que_hacer", "clave" in str(e).lower(), str(e))
    check("cuota.sin_html", "<a" not in str(e) and "href" not in str(e), str(e))
    check("cuota.sin_ingles", "quota" not in str(e).lower(), str(e))

    # --- clave inválida y API sin habilitar ------------------------------
    e = R._error_de_youtube(400, cuerpo("keyInvalid", "API key not valid.", 400))
    check("clave.codigo", e.codigo == "clave", f"codigo={e.codigo!r}")

    # Google no siempre manda `reason`: a veces sólo el texto.
    e = R._error_de_youtube(400, json.dumps(
        {"error": {"code": 400, "message": "API key not valid. Please pass a valid API key."}}))
    check("clave.sin_reason", e.codigo == "clave", f"codigo={e.codigo!r}")

    e = R._error_de_youtube(403, cuerpo(
        "accessNotConfigured", "YouTube Data API has not been used in project 123"))
    check("api_sin_habilitar.codigo", e.codigo == "clave", f"codigo={e.codigo!r}")
    check("api_sin_habilitar.menciona_consola", "Cloud" in str(e), str(e))

    # --- rate limit: no es cuota, no ofrece cargar una clave -------------
    e = R._error_de_youtube(403, cuerpo("rateLimitExceeded", "Too many requests"))
    check("rate.sin_codigo", e.codigo == "", f"codigo={e.codigo!r}")
    check("rate.dice_esperar", "esperá" in str(e).lower(), str(e))

    # --- motivo desconocido: se muestra el de Google, pero limpio --------
    e = R._error_de_youtube(403, cuerpo(
        "algoNuevoQueGoogleInvento", 'Mirá <a href="http://x">esto</a>.'))
    check("desconocido.sin_codigo", e.codigo == "", f"codigo={e.codigo!r}")
    check("desconocido.sin_html", "<a" not in str(e), str(e))
    check("desconocido.conserva_texto", "esto" in str(e), str(e))

    # --- cuerpo que no es JSON: no puede reventar ------------------------
    e = R._error_de_youtube(500, "<html>502 Bad Gateway</html>")
    check("basura.es_relevar_error", isinstance(e, R.RelevarError))
    check("basura.no_vacio", len(str(e)) > 10, str(e))

    # --- el código sobrevive a la excepción ------------------------------
    # Es lo que jobs.py lee con getattr(e, "codigo", "") para que la interfaz
    # sepa qué salida ofrecer. Si RelevarError perdiera el atributo, el botón
    # desaparecería sin que nada más se rompa, que es la peor forma de fallar.
    try:
        raise R._error_de_youtube(403, cuerpo("quotaExceeded", "exceeded quota"))
    except R.RelevarError as err:
        check("codigo.sobrevive", getattr(err, "codigo", "") == "cuota")

    # Y un RelevarError común sigue funcionando sin código.
    simple = R.RelevarError("algo salió mal")
    check("compat.sin_codigo", simple.codigo == "")
    check("compat.mensaje", str(simple) == "algo salió mal")

    if fails:
        print("FALLARON:")
        print("\n".join(fails))
        return 1
    print("OK - traduccion de errores de la YouTube Data API")
    return 0


if __name__ == "__main__":
    sys.exit(main())
