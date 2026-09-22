# -*- coding: utf-8 -*-
"""Traducción de los errores de la YouTube Data API. Sin red y sin claves.

Por qué existe. Lo que devuelve Google viene en inglés, con jerga y a veces con
un `<a href>` adentro del mensaje. Mostrarlo tal cual deja a la persona sin
saber qué hacer, y el caso más probable, el cupo diario agotado cuando muchos
usan la misma copia, es justo el que tiene solución simple. Este test fija que
esa traducción exista y que el código que la acompaña sea el correcto, porque de
ese código depende que la interfaz ofrezca el botón para cargar una clave
propia.
"""

import json

import pytest

from migrador import relevar_core as R


def cuerpo(reason, message, code=403):
    """Un error con la forma real de los de Google."""
    return json.dumps(
        {
            "error": {
                "code": code,
                "message": message,
                "errors": [{"domain": "youtube.quota", "reason": reason, "message": message}],
            }
        }
    )


def test_cupo_agotado_es_el_caso_que_mas_va_a_pasar():
    e = R._error_de_youtube(
        403,
        cuerpo(
            "quotaExceeded",
            "The request cannot be completed because you have exceeded your "
            '<a href="/youtube/v3/getting-started#quota">quota</a>.',
        ),
    )

    assert isinstance(e, R.RelevarError)
    assert e.codigo == "cuota"  # de esto depende el botón de la interfaz
    texto = str(e)
    assert "cupo" in texto.lower()
    assert "clave" in texto.lower()  # dice qué hacer
    assert "<a" not in texto and "href" not in texto
    assert "quota" not in texto.lower()  # nada en inglés


def test_clave_invalida():
    e = R._error_de_youtube(400, cuerpo("keyInvalid", "API key not valid.", 400))
    assert e.codigo == "clave"


def test_clave_invalida_aunque_google_no_mande_reason():
    e = R._error_de_youtube(
        400,
        json.dumps({"error": {"code": 400, "message": "API key not valid. Please pass a valid API key."}}),
    )
    assert e.codigo == "clave"


def test_api_sin_habilitar_manda_a_la_consola_de_google():
    e = R._error_de_youtube(
        403, cuerpo("accessNotConfigured", "YouTube Data API has not been used in project 123")
    )
    assert e.codigo == "clave"
    assert "Cloud" in str(e)


def test_rate_limit_no_es_cuota_y_no_ofrece_cargar_una_clave():
    e = R._error_de_youtube(403, cuerpo("rateLimitExceeded", "Too many requests"))
    assert e.codigo == ""
    assert "esperá" in str(e).lower()


def test_motivo_desconocido_muestra_el_de_google_pero_limpio():
    e = R._error_de_youtube(403, cuerpo("algoNuevoQueGoogleInvento", 'Mirá <a href="http://x">esto</a>.'))
    assert e.codigo == ""
    assert "<a" not in str(e)
    assert "esto" in str(e)


def test_un_cuerpo_que_no_es_json_no_revienta():
    e = R._error_de_youtube(500, "<html>502 Bad Gateway</html>")
    assert isinstance(e, R.RelevarError)
    assert len(str(e)) > 10


def test_el_codigo_sobrevive_a_la_excepcion():
    """Es lo que `jobs.py` lee con `getattr(e, "codigo", "")` para que la
    interfaz sepa qué salida ofrecer. Si RelevarError perdiera el atributo, el
    botón desaparecería sin que nada más se rompa, que es la peor forma de
    fallar."""
    try:
        raise R._error_de_youtube(403, cuerpo("quotaExceeded", "exceeded quota"))
    except R.RelevarError as err:
        assert getattr(err, "codigo", "") == "cuota"


def test_un_relevar_error_comun_sigue_funcionando_sin_codigo():
    simple = R.RelevarError("algo salió mal")
    assert simple.codigo == ""
    assert str(simple) == "algo salió mal"


@pytest.mark.parametrize(
    "cuerpo_crudo",
    [
        "<html>502 Bad Gateway</html>",  # no es JSON
        "",  # vacío
        "[1, 2, 3]",  # JSON válido, pero una lista
        '{"error": "un texto y no un objeto"}',  # `error` no es un diccionario
        '{"error": {"errors": "tampoco es una lista"}}',
        '{"error": {"errors": [42]}}',  # la lista trae algo que no es un dict
        '{"sin_error": true}',  # falta la clave entera
    ],
)
def test_ningun_cuerpo_raro_hace_reventar_el_parseo(cuerpo_crudo):
    """El parseo del error de Google atrapa cuatro excepciones nombradas y no un
    `except Exception`, así que vale la pena fijar las formas de romperlo.

    Todas tienen que terminar en un RelevarError mostrable. Si alguna se
    escapara, el usuario vería un traceback en vez del mensaje, y justo en el
    momento en que algo ya salió mal.
    """
    e = R._error_de_youtube(500, cuerpo_crudo)
    assert isinstance(e, R.RelevarError)
    assert str(e)
