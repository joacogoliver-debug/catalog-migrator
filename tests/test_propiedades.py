# -*- coding: utf-8 -*-
"""Lo que tiene que ser cierto para cualquier entrada, no sólo para los casos
que a alguien se le ocurrió escribir.

Los demás tests fijan casos: un título con una barra, un UPC con el dígito
mal. Éstos fijan reglas, y dejan que Hypothesis busque la entrada que las
rompe: un título en cualquier escritura, una planilla con cualquier contenido,
un archivo guardado con cualquier forma. Se usan donde entra algo de afuera y
donde un error termina en un archivo que alguien entrega: los nombres adentro
del ZIP, los códigos, la planilla importada y el relevamiento guardado.

Cada propiedad corre un número acotado de ejemplos, para que la suite siga
tardando segundos. Para salir a buscar de verdad, antes de un release o después
de tocar algo de esto, se le pide más:

    MIGRADOR_EJEMPLOS=3000 pytest tests/test_propiedades.py

Lo que encontraron al escribirlos: un corchete suelto pegado en el campo del
link terminaba en «Invalid IPv6 URL», y un retorno de carro suelto o un byte
nulo en una planilla tumbaban el lector de CSV.
"""

import json
import os
import re

import pytest

# Hypothesis es una herramienta de desarrollo. Si no está (quien compila con
# `build.py` sin las dependencias de desarrollo), estos tests se saltean, igual
# que el de contrato con tiddl: el resto de la suite no depende de ella.
pytest.importorskip("hypothesis")

from hypothesis import given, settings
from hypothesis import strategies as st

from migrador import ediciones as ED
from migrador import importar as IM
from migrador import instantanea as INS
from migrador import paquete as PQ
from migrador import productos as P
from migrador import relevar_core as R
from migrador import texto as TX
from migrador import validar as V

_PEDIDOS = int(os.environ.get("MIGRADOR_EJEMPLOS") or 0)
RAPIDO = settings(max_examples=_PEDIDOS or 120, deadline=None)
LENTO = settings(max_examples=_PEDIDOS or 40, deadline=None)

textos = st.text(max_size=120)
digitos = st.text(alphabet="0123456789", min_size=11, max_size=11)
letras = st.sampled_from("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
alfanum = st.sampled_from("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")


@st.composite
def isrcs(draw):
    """Un ISRC bien formado: país, registrante, año y designación."""
    pais = "".join(draw(st.lists(letras, min_size=2, max_size=2)))
    registrante = "".join(draw(st.lists(alfanum, min_size=3, max_size=3)))
    resto = draw(st.text(alphabet="0123456789", min_size=7, max_size=7))
    return pais + registrante + resto


@st.composite
def upcs(draw):
    """Un UPC-A válido que no es todo ceros."""
    base = draw(digitos.filter(lambda d: d.strip("0")))
    return base + str(V._gtin_check_digit(base))


# ============================================================
# Texto y nombres de archivo
# ============================================================


@RAPIDO
@given(textos, st.integers(min_value=1, max_value=120))
def test_un_nombre_seguro_sirve_en_cualquier_sistema(s, largo):
    """Pase lo que pase: ASCII, sin los caracteres que Windows prohíbe, sin
    punto ni espacio al final, nunca vacío, y dentro del largo pedido."""
    nombre = TX.nombre_seguro(s, largo, "x")
    assert nombre and len(nombre) <= max(largo, 1)
    assert nombre.isascii()
    assert not re.search(r'[<>:"/\\|?*\x00-\x1f]', nombre)
    assert nombre == nombre.strip(" .")
    assert nombre not in (".", "..")


@RAPIDO
@given(textos)
def test_comparar_dos_veces_da_lo_mismo(s):
    """`comparable` es la forma en que se decide si dos títulos son el mismo:
    aplicada de nuevo no puede cambiar, o dos pasadas darían grupos distintos."""
    assert TX.comparable(TX.comparable(s)) == TX.comparable(s)
    assert TX.plegado(TX.plegado(s)) == TX.plegado(s)


@RAPIDO
@given(textos, textos)
def test_ser_la_misma_version_no_depende_del_orden(a, b):
    assert TX.misma_version(a, b) == TX.misma_version(b, a)
    assert TX.misma_version(a, a)


@RAPIDO
@given(textos, st.text(max_size=30), st.one_of(st.integers(min_value=0, max_value=3000), st.just("")))
def test_la_carpeta_de_un_producto_nunca_sale_de_la_raiz(titulo, upc, anio):
    """El título viene de YouTube y el UPC de Deezer o de una planilla: con lo
    que traigan, la carpeta es un nombre y no una ruta."""
    carpeta = P.folder_name({"title": titulo, "upc": upc, "release_year": anio})
    assert "/" not in carpeta and "\\" not in carpeta and carpeta not in (".", "..")
    assert PQ.entrada_zip("raiz", carpeta, "datos.xlsx").count("/") == 2


@RAPIDO
@given(st.lists(st.tuples(textos, st.text(alphabet="0123456789", max_size=13)), min_size=1, max_size=12))
def test_dos_productos_nunca_comparten_carpeta(pares):
    productos = [{"title": t, "upc": u, "release_year": 2020} for t, u in pares]
    P.asignar_carpetas(productos)
    carpetas = [str(p["folder"]).casefold() for p in productos]
    assert len(set(carpetas)) == len(carpetas)


@RAPIDO
@given(textos, st.integers(min_value=0, max_value=99), st.integers(min_value=0, max_value=200))
def test_el_nombre_de_un_audio_respeta_el_largo_que_le_queda(titulo, numero, lugar):
    nombre = PQ.nombre_audio({"track": titulo, "track_number": numero, "audio_format": ".flac"}, lugar)
    assert nombre.endswith(".flac") and nombre.startswith(f"{numero:02d} - ")
    assert "/" not in nombre and "\\" not in nombre
    # El título se recorta hasta doce caracteres y no menos: por debajo de eso
    # el archivo deja de reconocerse.
    assert len(nombre) <= max(lugar, len(f"{numero:02d} - ") + 12 + len(".flac"))


# ============================================================
# Códigos
# ============================================================


@RAPIDO
@given(upcs())
def test_un_upc_bien_armado_valida_y_uno_con_otro_digito_no(upc):
    assert V.upc_valido(upc) == (True, "")
    for otro in "0123456789":
        if otro != upc[-1]:
            assert not V.upc_valido(upc[:-1] + otro)[0]


@RAPIDO
@given(upcs())
def test_doce_digitos_y_trece_con_un_cero_son_el_mismo_codigo(upc):
    assert V.upc_valido("0" + upc)[0], "el EAN-13 con cero adelante es el mismo código"
    assert V.gtin13(upc) == V.gtin13("0" + upc)
    assert V.gtin13(V.gtin13(upc)) == V.gtin13(upc)


@RAPIDO
@given(upcs())
def test_el_upc_que_excel_guardo_como_numero_se_recupera(upc):
    """Excel guarda el UPC como número: llega sin los ceros de adelante, con
    «.0» o en notación científica. Leído, tiene que ser el mismo código."""
    for como_lo_guarda in (str(int(upc)), f"{int(upc)}.0", f"{float(int(upc)):.11E}"):
        leido = IM._como_upc(como_lo_guarda)
        if len(str(int(upc))) >= 9:
            assert V.gtin13(leido) == V.gtin13(upc), como_lo_guarda


@RAPIDO
@given(isrcs(), st.sampled_from(["", "-", " "]), st.booleans())
def test_un_isrc_vale_con_guiones_con_espacios_y_en_minusculas(isrc, separador, minusculas):
    escrito = separador.join((isrc[:2], isrc[2:5], isrc[5:7], isrc[7:]))
    escrito = escrito.lower() if minusculas else escrito
    assert V.isrc_valido(escrito)
    assert ED.normalizar_isrc(escrito) == isrc


@RAPIDO
@given(st.text(max_size=20))
def test_lo_que_no_es_un_isrc_no_entra_al_catalogo(valor):
    """Cualquier texto que se quiera cargar como ISRC o se rechaza o queda
    normalizado y válido: no hay una tercera salida."""
    t = {"track": "Uno", "isrc": "", "duration_s": 200}
    p = {"product_id": "p001", "title": "Disco", "upc": "", "tracks": [t]}
    try:
        ED.poner_isrc([p], "p001", 0, valor)  # type: ignore[list-item]
    except ED.EdicionInvalida:
        assert t["isrc"] == ""
    else:
        assert t["isrc"] == "" or V.RE_ISRC.fullmatch(str(t["isrc"]))


@RAPIDO
@given(st.text(max_size=400))
def test_un_dato_cargado_a_mano_cabe_en_una_celda(valor):
    limpio = ED.limpiar_dato(valor)
    assert len(limpio) <= ED.LARGO_MAX_DATO
    assert not re.search(r"[\x00-\x1f\x7f]", limpio)
    assert limpio == limpio.strip()
    assert ED.limpiar_dato(limpio) == limpio


# ============================================================
# Lo que viene de YouTube
# ============================================================


@RAPIDO
@given(st.text(max_size=600))
def test_cualquier_descripcion_se_puede_leer(descripcion):
    """La descripción la escribe otro. Con lo que traiga, se lee sin caerse y
    lo que sale tiene la forma del contrato."""
    res = R.parse_description(descripcion)
    assert set(res) == {
        "distributor",
        "album",
        "release_year",
        "release_date",
        "label",
        "p_line",
        "artists",
        "credits",
    }
    assert res["release_year"] is None or R._anio_plausible(res["release_year"])
    assert res["release_date"] is None or re.fullmatch(r"\d{4}-\d{2}-\d{2}", res["release_date"])


@RAPIDO
@given(st.text(max_size=200))
def test_cualquier_cosa_pegada_en_el_campo_del_link_da_un_pedido_o_un_error(pegado):
    try:
        params, _muestra = R.pedido_de_canal(pegado)
    except R.RelevarError as e:
        assert e.codigo == "url"
    else:
        assert params is None or set(params) & {"id", "forHandle", "forUsername"}


# ============================================================
# La planilla importada
# ============================================================

celdas = st.one_of(
    st.text(max_size=30),
    isrcs(),
    upcs(),
    st.sampled_from(["ISRC", "UPC", "Track", "Album", "Título", "Duración", "3:20", "", "=1+1"]),
)


@LENTO
@given(st.binary(max_size=3000))
def test_cualquier_archivo_o_se_lee_o_se_rechaza_con_un_mensaje(datos):
    """Bytes cualesquiera: una planilla válida, o `ArchivoInvalido`. Ninguna
    otra excepción, que sería un 500 en la pantalla de quien importa."""
    try:
        filas, columnas = IM.leer(datos, "x.csv")
    except IM.ArchivoInvalido:
        return
    assert filas and ("isrc" in columnas or "upc" in columnas)


@LENTO
@given(
    st.lists(st.lists(celdas, min_size=1, max_size=7), min_size=1, max_size=25),
    st.sampled_from([",", ";", "\t"]),
)
def test_de_cualquier_planilla_salen_solo_codigos_validos(filas, separador):
    texto = "\n".join(separador.join(c.replace(separador, " ").replace("\n", " ") for c in f) for f in filas)
    try:
        leidas, _ = IM.leer(texto.encode("utf-8"), "x.csv")
    except IM.ArchivoInvalido:
        return
    for f in leidas:
        assert f["isrc"] or f["upc"], "una fila sin ningún código no tiene nada que aportar"
        assert not f["isrc"] or V.RE_ISRC.fullmatch(f["isrc"])
        assert not f["upc"] or V.upc_valido(f["upc"])[0]
        assert f["duracion_s"] >= 0 and f["numero"] >= 0


@st.composite
def catalogos(draw):
    """Un catálogo chico con títulos que se repiten, que es donde la
    conciliación puede confundirse."""
    titulos = draw(
        st.lists(
            st.sampled_from(["Uno", "Dos", "Tres", "Uno (En Vivo)", "Dos - Remix"]), min_size=1, max_size=6
        )
    )
    tracks = []
    for n, titulo in enumerate(titulos):
        tracks.append(
            {
                "track": titulo,
                "isrc": draw(st.one_of(st.just(""), isrcs())),
                "duration_s": draw(st.integers(min_value=0, max_value=400)),
                "track_number": n + 1,
            }
        )
    return [
        {
            "product_id": "p001",
            "title": draw(st.sampled_from(["Disco", "Uno"])),
            "upc": draw(st.one_of(st.just(""), upcs())),
            "tracks": tracks,
            "order_unconfirmed": False,
        }
    ]


filas_importadas = st.lists(
    st.fixed_dictionaries(
        {
            "isrc": st.one_of(st.just(""), isrcs()),
            "upc": st.one_of(st.just(""), upcs()),
            "track": st.sampled_from(["Uno", "Dos", "Tres", "Uno (En Vivo)", "Dos - Remix", "Otro", ""]),
            "album": st.sampled_from(["", "Disco", "Uno", "Otro Disco"]),
            "duracion_s": st.integers(min_value=0, max_value=400),
            "numero": st.integers(min_value=0, max_value=9),
        }
    ),
    max_size=12,
)


@LENTO
@given(catalogos(), filas_importadas)
def test_conciliar_nunca_cambia_nada_ni_aplica_solo_lo_dudoso(productos, filas):
    """Las dos promesas de la importación, para cualquier catálogo y cualquier
    planilla: proponer no toca el catálogo, y lo que no es seguro (un
    conflicto, un ambiguo) nunca queda elegido por defecto."""
    filas = [{**f, "fila": n} for n, f in enumerate(filas, 2) if f["isrc"] or f["upc"]]
    antes = json.dumps(productos, sort_keys=True)
    propuesta = IM.conciliar(productos, filas)  # type: ignore[arg-type]
    assert json.dumps(productos, sort_keys=True) == antes
    por_id = {it["id"]: it for it in propuesta["items"]}
    assert len(por_id) == len(propuesta["items"]), "cada ítem tiene su id"
    for elegido in IM.elegidos_por_defecto(propuesta):
        assert por_id[elegido]["tipo"] in ("confirma", "completa")
    for it in propuesta["items"]:
        if it["tipo"] == "completa" and it["codigo"] == "isrc":
            assert not productos[0]["tracks"][it["indice"]]["isrc"], (
                "completar no pisa un código que ya estaba"
            )
        if it["tipo"] == "confirma":
            assert it["actual"] == it["nuevo"]


@LENTO
@given(catalogos(), filas_importadas)
def test_aplicar_lo_que_viene_por_defecto_nunca_pisa_un_codigo(productos, filas):
    filas = [{**f, "fila": n} for n, f in enumerate(filas, 2) if f["isrc"] or f["upc"]]
    antes = [(t["isrc"]) for t in productos[0]["tracks"]]
    upc_antes = productos[0]["upc"]
    propuesta = IM.conciliar(productos, filas)  # type: ignore[arg-type]
    IM.aplicar(productos, propuesta, IM.elegidos_por_defecto(propuesta))
    for viejo, t in zip(antes, productos[0]["tracks"], strict=True):
        assert not viejo or t["isrc"] == viejo, "un código que estaba no cambia sin que alguien lo elija"
        assert not t["isrc"] or V.RE_ISRC.fullmatch(t["isrc"])
    assert not upc_antes or V.gtin13(productos[0]["upc"]) == V.gtin13(upc_antes)


# ============================================================
# El relevamiento guardado
# ============================================================

json_cualquiera = st.recursive(
    st.one_of(st.none(), st.booleans(), st.integers(), st.floats(allow_nan=False), st.text(max_size=20)),
    lambda hijos: st.one_of(
        st.lists(hijos, max_size=4), st.dictionaries(st.text(max_size=12), hijos, max_size=4)
    ),
    max_leaves=25,
)


@LENTO
@given(json_cualquiera)
def test_cualquier_json_o_es_un_relevamiento_o_se_rechaza(dato):
    try:
        INS.abrir(json.dumps(dato).encode("utf-8"))
    except INS.InstantaneaInvalida:
        pass


@LENTO
@given(json_cualquiera, json_cualquiera)
def test_un_relevamiento_con_cualquier_cosa_adentro_no_rompe_lo_que_sigue(producto, track):
    """Con el encabezado correcto y cualquier cosa adentro: si se acepta, lo
    que sale es un catálogo con el que se puede validar y armar la hoja."""
    crudo = {
        "formato": INS.FORMATO,
        "version": INS.VERSION_FORMATO,
        "artista": "A",
        "productos": [producto, {"title": "Disco", "tracks": [track, {"track": "Uno"}]}],
    }
    try:
        productos, artista, _ = INS.abrir(json.dumps(crudo).encode("utf-8"))
    except INS.InstantaneaInvalida:
        return
    assert artista == "A" and productos
    for p in productos:
        assert "/" not in p["folder"] and "\\" not in p["folder"] and p["tracks"]
        assert p["track_count"] == len(p["tracks"])
    V.validar(productos, artista)
    PQ.hoja_ingesta_csv(productos, artista, False, False)
    PQ.hoja_pedido_bytes(productos, artista)


@LENTO
@given(
    st.lists(
        st.tuples(st.text(min_size=1, max_size=40), st.one_of(st.just(""), isrcs())), min_size=1, max_size=8
    ),
    textos,
)
def test_guardar_y_reabrir_conserva_titulos_y_codigos(temas, titulo_disco):
    tracks = [
        {"track": titulo, "isrc": isrc, "duration_s": 200, "album": "Disco", "distributor": "X"}
        for titulo, isrc in temas
        if titulo.strip()
    ]
    if not tracks or not titulo_disco.strip():
        return
    p = {"product_id": "p001", "title": titulo_disco, "kind": "album", "upc": "", "tracks": tracks}
    productos, _, _ = INS.abrir(INS.volcar([p], "Artista"))  # type: ignore[list-item]
    assert productos[0]["title"] == titulo_disco
    assert [(t["track"], t["isrc"]) for t in productos[0]["tracks"]] == [
        (t["track"], t["isrc"]) for t in tracks
    ]
