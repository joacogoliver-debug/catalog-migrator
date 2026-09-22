# -*- coding: utf-8 -*-
"""Validación pre-entrega. Sin red y sin dependencias extra.

Cubre las reglas que evitan un rechazo de la distribuidora.
  - formato de ISRC, incluidos los códigos especiales tipo QM/QZ
  - dígito verificador de UPC-A y EAN-13, contra códigos reales conocidos
  - códigos duplicados, ISRC entre tracks y UPC entre productos
  - dimensiones, forma y espacio de color de la portada, leídos de la cabecera
  - campos faltantes y años imposibles
  - separación entre error, que es rechazo, y aviso, que es revisar
"""

from datetime import date

import pytest

import validar as V


def _prod(title="Disco", upc="", year=2020, label="Sello", tracks=None,
          cover=None, orden_ok=True, cover_status="ok"):
    return {
        "product_id": "p001", "title": title, "kind": "album", "upc": upc,
        "release_year": year, "label": label, "distributor": "ONErpm",
        "track_count": len(tracks or []), "order_unconfirmed": not orden_ok,
        "cover_bytes": cover, "cover_status": cover_status,
        "tracks": tracks or [],
    }


def _track(track="Tema", isrc="ARABC2000001", dur=200):
    return {"track": track, "isrc": isrc, "duration_s": dur, "track_number": 1}


def codigos(res, nivel=None):
    """Los códigos de los hallazgos, que es lo que la interfaz agrupa y el test
    busca. El mensaje se traduce, el código nunca."""
    return sorted(h["codigo"] for h in res["hallazgos"]
                  if nivel is None or h["nivel"] == nivel)


# ============================================================
# ISRC
# ============================================================

@pytest.mark.parametrize("isrc, valido", [
    ("ARABC2000001", True),
    ("AR-ABC-20-00001", True),            # con guiones
    ("arabc2000001", True),               # en minúsculas
    ("QM24S2000001", True),               # QM/QZ los usan muchos digitales
    ("USA2P2100001", True),               # registrante alfanumérico
    ("ARABC200000", False),               # corto
    ("ARABC20000012", False),             # largo
    ("12ABC2000001", False),              # país numérico
    ("ARABC200000A", False),              # designación con letra
    ("", False),
    (None, False),
])
def test_formato_de_isrc(isrc, valido):
    assert V.isrc_valido(isrc) is valido


# ============================================================
# UPC y EAN
# ============================================================

@pytest.mark.parametrize("codigo, valido", [
    ("036000291452", True),               # UPC-A real, verificador 2
    ("036000291453", False),              # el mismo con el verificador mal
    ("4006381333931", True),              # EAN-13 real, verificador 3
    ("4006381333932", False),
    ("0-36000-29145-2", True),            # con guiones
    ("12345", False),                     # largo que no existe
    ("03600029145X", False),              # con letras
    ("", False),
])
def test_digito_verificador_de_upc(codigo, valido):
    assert V.upc_valido(codigo)[0] is valido


def test_el_motivo_del_upc_invalido_es_informativo():
    _, motivo = V.upc_valido("036000291453")
    assert "dígito verificador" in motivo


# ============================================================
# Medición de imágenes
# ============================================================

def test_mide_png_y_jpeg_sin_pillow(png, jpeg):
    assert V.medir_imagen(png(3000, 3000)) == (3000, 3000, 3)
    assert V.medir_imagen(jpeg(3000, 3000)) == (3000, 3000, 3)
    assert V.medir_imagen(jpeg(3000, 3000, 4)) == (3000, 3000, 4)     # CMYK
    assert V.medir_imagen(jpeg(3000, 1500)) == (3000, 1500, 3)


def test_lo_que_no_es_una_imagen_devuelve_none():
    assert V.medir_imagen(b"no soy una imagen") is None
    assert V.medir_imagen(b"") is None


# ============================================================
# Portadas
# ============================================================

def _cods_portada(cover, **kw):
    return codigos(V.validar([_prod(cover=cover, tracks=[_track()], **kw)]))


def test_una_portada_perfecta_no_genera_hallazgos(jpeg):
    c = _cods_portada(jpeg(3000, 3000))
    assert [x for x in c if x.startswith("portada")] == []


@pytest.mark.parametrize("imagen, codigo", [
    ((500, 500), "portada_chica"),
    ((3000, 2000), "portada_no_cuadrada"),
    ((1500, 1500), "portada_bajo_recomendado"),
])
def test_problemas_de_portada(jpeg, imagen, codigo):
    assert codigo in _cods_portada(jpeg(*imagen))


def test_portada_en_cmyk(jpeg):
    assert "portada_cmyk" in _cods_portada(jpeg(3000, 3000, 4))


def test_el_minimo_exacto_de_ingesta_entra(jpeg):
    """1400x1400 es el piso de Spotify y Apple. Justo en el piso no es error."""
    assert "portada_chica" not in _cods_portada(jpeg(1400, 1400))


def test_portada_ilegible_o_ausente():
    assert "portada_ilegible" in _cods_portada(b"basura!!")
    assert "portada_falta" in _cods_portada(None)


# ============================================================
# Duplicados
# ============================================================

def test_isrc_y_upc_duplicados_son_error():
    res = V.validar([
        _prod(title="A", upc="036000291452", tracks=[_track("T1", "ARABC2000001")]),
        _prod(title="B", upc="036000291452", tracks=[_track("T2", "ARABC2000001")]),
    ])
    assert "isrc_duplicado" in codigos(res, "error")
    assert "upc_duplicado" in codigos(res, "error")
    assert res["apto"] is False

    # El mensaje tiene que decir DÓNDE está el duplicado, para poder arreglarlo.
    msj = [h["mensaje"] for h in res["hallazgos"] if h["codigo"] == "isrc_duplicado"][0]
    assert "T1" in msj and "T2" in msj


def test_el_duplicado_se_detecta_con_guiones_o_minusculas():
    res = V.validar([
        _prod(title="A", tracks=[_track("T1", "AR-ABC-20-00001")]),
        _prod(title="B", tracks=[_track("T2", "arabc2000001")]),
    ])
    assert "isrc_duplicado" in codigos(res, "error")


def test_los_codigos_vacios_no_cuentan_como_duplicados():
    res = V.validar([
        _prod(title="A", upc="", tracks=[_track("T1", "")]),
        _prod(title="B", upc="", tracks=[_track("T2", "")]),
    ])
    assert [c for c in codigos(res) if "duplicado" in c] == []


# ============================================================
# Años
# ============================================================

def test_anio_futuro_o_absurdo_es_error():
    futuro = V.validar([_prod(year=date.today().year + 2, tracks=[_track()])])
    assert "anio_futuro" in codigos(futuro, "error")
    absurdo = V.validar([_prod(year=1500, tracks=[_track()])])
    assert "anio_absurdo" in codigos(absurdo, "error")


def test_el_anio_actual_es_valido():
    res = V.validar([_prod(year=date.today().year, tracks=[_track()])])
    assert "anio_futuro" not in codigos(res)


def test_anio_faltante_es_aviso():
    assert "anio_falta" in codigos(V.validar([_prod(year="", tracks=[_track()])]), "aviso")


# ============================================================
# Error contra aviso
# ============================================================

def test_los_campos_faltantes_son_aviso_y_no_bloquean():
    """Faltar un código no bloquea la entrega. La distribuidora asigna uno
    nuevo, se pierde el historial, y eso es lo que hay que avisar."""
    res = V.validar([_prod(upc="", label="", tracks=[_track(isrc="")])])
    assert "upc_falta" in codigos(res, "aviso")
    assert "isrc_falta" in codigos(res, "aviso")
    assert "sello_falta" in codigos(res, "aviso")
    assert res["apto"] is True


def test_los_errores_de_formato_si_bloquean():
    res = V.validar([_prod(upc="99999999999", tracks=[_track(isrc="NOESUNISRC")])])
    assert "upc_invalido" in codigos(res, "error")
    assert "isrc_invalido" in codigos(res, "error")
    assert res["apto"] is False


# ============================================================
# Duraciones y títulos
# ============================================================

def test_duracion_cero_es_error_y_duracion_larga_es_aviso():
    assert "duracion_falta" in codigos(V.validar([_prod(tracks=[_track(dur=0)])]), "error")
    assert "duracion_larga" in codigos(V.validar([_prod(tracks=[_track(dur=3600)])]), "aviso")


@pytest.mark.parametrize("titulo", [
    "Tema (Official Video)", "Tema [Lyric Video]", "Tema - Video Oficial",
    "Tema (Official Audio)", "Tema 4K",
])
def test_detecta_texto_de_youtube_arrastrado_al_titulo(titulo):
    assert "titulo_con_ruido" in codigos(V.validar([_prod(tracks=[_track(titulo)])]))


@pytest.mark.parametrize("titulo", ["Amanecer", "Vivo"])
def test_un_titulo_limpio_no_dispara_el_aviso(titulo):
    """«Live Session» es ruido, pero «Vivo» solo no debería serlo."""
    assert "titulo_con_ruido" not in codigos(V.validar([_prod(tracks=[_track(titulo)])]))


def test_el_orden_sin_confirmar_se_avisa():
    res = V.validar([_prod(tracks=[_track()], orden_ok=False)])
    assert "orden_sin_confirmar" in codigos(res, "aviso")


# ============================================================
# Catálogo entero y reporte
# ============================================================

def test_un_catalogo_limpio_es_apto(jpeg):
    res = V.validar([_prod(upc="036000291452", cover=jpeg(3000, 3000),
                           tracks=[_track("Amanecer", "ARABC2000001")])], "Artista")
    assert res["apto"] is True
    assert res["resumen"]["errores"] == 0


def test_el_reporte_dice_si_hay_errores(jpeg):
    limpio = V.validar([_prod(upc="036000291452", cover=jpeg(3000, 3000),
                              tracks=[_track("Amanecer", "ARABC2000001")])], "Artista")
    assert "Sin errores" in V.reporte_validacion(limpio, "Artista")

    malo = V.validar([_prod(upc="123", tracks=[_track(isrc="MAL")])])
    rep = V.reporte_validacion(malo, "Artista")
    assert "ERRORES" in rep
    assert "suelen rechazar" in rep


def test_catalogo_vacio():
    res = V.validar([])
    assert res["apto"] is True
    assert res["hallazgos"] == []
