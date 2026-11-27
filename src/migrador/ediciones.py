"""
Lo que el usuario sabe y ninguna fuente pública trae.

Hasta acá la app era de sólo lectura: mostraba lo que encontró y, para todo lo
demás, mandaba a completar una planilla. Pero quien migra un catálogo casi
siempre tiene más datos que YouTube y Deezer juntos: el ISRC que le pasó su
distribuidora, el UPC que figura en un contrato, el género de su propio disco.
Sin dónde ponerlos, cada uno de esos datos se tipeaba en un Excel de
trescientas filas, después de armado el paquete, y la validación ya no los
miraba.

Este módulo es ese lugar. Tres cosas se pueden cambiar, y las tres quedan
dichas como lo que son:

  - **Un ISRC o un UPC.** Se valida el formato antes de aceptarlo (un código
    mal tipeado se rechaza acá, no en la ingesta), queda marcado como `manual`
    y se guarda el que había, para poder volver atrás.
  - **Los campos a completar** de la hoja de ingesta: género, idioma, explicit,
    línea ©, territorios, idioma de la letra. Se cargan una vez para todo el
    catálogo o para los productos elegidos.
  - **La elección entre candidatos**, cuando el relevamiento encontró dos
    grabaciones posibles y no eligió (ver `completitud.completar_isrc`).

Nada de esto es «inventar metadata»: lo escribe quien conoce el catálogo, y la
hoja y la validación dicen que salió de ahí.

Los productos se modifican en el lugar, igual que hacen `portadas` y `audio`.
No se importa nada que toque la red.
"""

import re

from . import evidencia
from collections.abc import Mapping

from .contratos import CAMPOS_A_COMPLETAR, Producto, Track
from .i18n import T
from .productos import asignar_carpetas
from .texto import sin_acentos
from .validar import isrc_valido, upc_valido

# Un dato de éstos es una palabra o una línea, no un texto: el tope evita que
# un pegado accidental termine en trescientas celdas.
LARGO_MAX_DATO = 200
_RE_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


class EdicionInvalida(ValueError):
    """Lo que se quiso cargar no se puede aceptar. El mensaje es para mostrar."""


def _producto(productos: list[Producto], product_id) -> Producto:
    for p in productos:
        if p["product_id"] == product_id:
            return p
    raise EdicionInvalida(T("edi.producto_no_existe"))


def _track(p: Producto, indice) -> Track:
    try:
        i = int(indice)
    except (TypeError, ValueError):
        raise EdicionInvalida(T("edi.track_no_existe")) from None
    if not 0 <= i < len(p["tracks"]):
        raise EdicionInvalida(T("edi.track_no_existe"))
    return p["tracks"][i]


def normalizar_isrc(isrc) -> str:
    """El ISRC como lo pide la ingesta: en mayúsculas, sin guiones ni espacios."""
    return re.sub(r"[\s\-]", "", str(isrc or "")).upper()


def normalizar_upc(upc) -> str:
    return re.sub(r"[\s\-]", "", str(upc or ""))


def poner_isrc(productos: list[Producto], product_id, indice, isrc, nivel=evidencia.MANUAL) -> Track:
    """Le pone a un tema el ISRC que escribió el usuario.

    Con el código vacío se deshace el cambio: vuelve el que había antes, con el
    nivel que le corresponda. Levanta `EdicionInvalida` si el formato no es el
    de un ISRC, que es el motivo de rechazo más común de una hoja de ingesta.
    """
    p = _producto(productos, product_id)
    t = _track(p, indice)
    limpio = normalizar_isrc(isrc)
    if not limpio:
        return restaurar_isrc(productos, product_id, indice)
    if not isrc_valido(limpio):
        raise EdicionInvalida(T("edi.isrc_invalido", isrc=str(isrc).strip()[:40]))
    if "isrc_previo" not in t:
        # Todo lo que hace falta para dejarlo como estaba, nivel incluido: un
        # código confirmado que se cambia y se restaura vuelve confirmado.
        t["isrc_previo"] = {
            "isrc": t.get("isrc") or "",
            "isrc_como": t.get("isrc_como") or "",
            "isrc_nivel": t.get("isrc_nivel") or "",
            "match": t.get("match") or "",
            "isrc_respaldo": t.get("isrc_respaldo") or "",
        }
    # El respaldo era del código anterior, no de éste.
    t.pop("isrc_respaldo", None)
    t["isrc"], t["isrc_nivel"], t["isrc_como"] = limpio, nivel, nivel
    evidencia.contar_sin_confirmar(p)
    return t


def restaurar_isrc(productos: list[Producto], product_id, indice) -> Track:
    """Vuelve al ISRC que encontró el relevamiento, si se lo había cambiado."""
    p = _producto(productos, product_id)
    t = _track(p, indice)
    previo = t.pop("isrc_previo", None)
    if previo is not None:
        t["isrc"], t["match"] = previo["isrc"], previo["match"]
        for clave in ("isrc_como", "isrc_nivel", "isrc_respaldo"):
            if previo.get(clave):
                t[clave] = previo[clave]
            else:
                t.pop(clave, None)
    evidencia.contar_sin_confirmar(p)
    return t


def poner_upc(productos: list[Producto], product_id, upc, nivel=evidencia.MANUAL) -> Producto:
    """Le pone a un producto el UPC que escribió el usuario.

    Se valida el largo y el dígito verificador. La carpeta del producto lleva
    el UPC en el nombre, así que se vuelven a asignar las carpetas.
    """
    p = _producto(productos, product_id)
    limpio = normalizar_upc(upc)
    if not limpio:
        return restaurar_upc(productos, product_id)
    ok, motivo = upc_valido(limpio)
    if not ok:
        raise EdicionInvalida(T("edi.upc_invalido", upc=str(upc).strip()[:40], motivo=motivo))
    if "upc_previo" not in p:
        p["upc_previo"] = {
            "upc": p.get("upc") or "",
            "upc_nivel": p.get("upc_nivel") or "",
            "upc_respaldo": p.get("upc_respaldo") or "",
        }
    p.pop("upc_respaldo", None)
    p["upc"], p["upc_nivel"] = limpio, nivel
    asignar_carpetas(productos)
    return p


def restaurar_upc(productos: list[Producto], product_id) -> Producto:
    """Vuelve al UPC que encontró el relevamiento, si se lo había cambiado."""
    p = _producto(productos, product_id)
    previo = p.pop("upc_previo", None)
    if previo is not None:
        p["upc"] = previo["upc"]
        for clave in ("upc_nivel", "upc_respaldo"):
            if previo.get(clave):
                p[clave] = previo[clave]
            else:
                p.pop(clave, None)
        asignar_carpetas(productos)
    return p


def limpiar_dato(valor) -> str:
    """Un dato cargado a mano, listo para una celda: sin saltos de línea ni
    caracteres de control, sin espacios de más y con el largo acotado."""
    texto = _RE_CONTROL.sub(" ", str(valor or ""))
    return re.sub(r"\s+", " ", texto).strip()[:LARGO_MAX_DATO].strip()


def poner_datos(productos: list[Producto], ids, datos: Mapping[str, object]) -> int:
    """Carga los campos a completar en los productos de `ids`.

    `datos` trae sólo los campos que se quieren cambiar: clave -> valor. Un
    valor vacío borra el campo, que vuelve a <<COMPLETAR>>. Las claves que no
    son de `CAMPOS_A_COMPLETAR` se rechazan: por acá no se cambia un título ni
    un sello. Devuelve cuántos productos se tocaron.
    """
    ajenas = sorted(set(datos) - set(CAMPOS_A_COMPLETAR))
    if ajenas:
        raise EdicionInvalida(T("edi.campo_desconocido", campo=", ".join(ajenas)[:80]))
    elegidos = set(ids or [])
    tocados = 0
    for p in productos:
        if p["product_id"] not in elegidos:
            continue
        propios = dict(p.get("datos") or {})
        for clave, valor in datos.items():
            limpio = limpiar_dato(valor)
            if limpio:
                propios[clave] = limpio
            else:
                propios.pop(clave, None)
        if propios:
            p["datos"] = propios
        else:
            p.pop("datos", None)
        tocados += 1
    return tocados


def dato(p: Producto, columna) -> str:
    """Lo que el usuario cargó para esa columna de la hoja, o ""."""
    datos = p.get("datos") or {}
    for clave, col in CAMPOS_A_COMPLETAR.items():
        if col == columna:
            return datos.get(clave, "")
    return ""


def sugerir_linea_c(p: Producto) -> str:
    """Una línea © armada con el año y el titular de la línea ℗, como sugerencia.

    No se carga sola: en un independiente el titular de la obra y el de la
    grabación suelen ser el mismo, pero no siempre, y decidirlo es de quien
    firma. La interfaz la ofrece para aceptarla con un clic.
    """
    anio, titular = p.get("release_year") or "", (p.get("label") or "").strip()
    if not anio or not titular:
        return ""
    return f"© {anio} {titular}"


def clave_de_columna(columna) -> str:
    """La clave interna de una columna de la hoja, sin acentos ni mayúsculas."""
    return re.sub(r"[^a-z0-9]+", "_", sin_acentos(columna).lower()).strip("_")
