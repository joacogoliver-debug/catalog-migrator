"""
El relevamiento, guardado para volver a él: reabrirlo y compararlo.

Por qué existe. La app no guarda el catálogo: vive en memoria y se va al
cerrarla, y eso es a propósito. Pero una migración no se hace en una sentada.
Se releva, se le pide a la distribuidora actual lo que falta, se espera una
semana, se cargan los códigos, se entrega, y un mes después habría que mirar si
la entrega nueva quedó con los códigos de la vieja. Cada una de esas vueltas
obligaba a relevar de cero, gastando cuota y perdiendo lo que se había cargado
a mano. Y la última, comprobar que la migración salió bien, directamente no se
podía hacer: no quedaba nada contra qué comparar.

Qué hace. El paquete trae un archivo más, el relevamiento tal como quedó
(`volcar`): los productos, sus temas, los códigos con su nivel de evidencia y
lo que el usuario cargó. No trae portadas ni audios. Es del usuario y queda
donde él guarde el paquete; la app sigue sin escribir nada por su cuenta. Con
ese archivo se pueden hacer dos cosas:

  - **Reabrirlo** (`abrir`): el catálogo vuelve a la pantalla como estaba, sin
    pedirle nada a YouTube ni a Deezer.
  - **Compararlo** (`comparar`) contra un relevamiento nuevo del mismo canal.
    Es la verificación que le faltaba al recorrido: dice, release por release,
    si ya está en la distribuidora nueva, si conservó el UPC y cada ISRC, si
    todavía está en las dos (falta dar de baja en la vieja), o si no aparece.

El archivo es un dato de afuera, igual que una planilla: puede venir de otra
persona. Se lee con tope de tamaño y se reconstruye campo por campo, con los
tipos que declara `contratos` y sólo las claves conocidas. Nada de lo que trae
se usa como ruta ni se ejecuta, y las carpetas se vuelven a calcular.

No importa nada que toque la red.
"""

import io
import json
import zipfile
from datetime import date
from typing import Any, cast

from . import evidencia
from .contratos import CandidatoISRC, Comparacion, Producto, ReleaseComparado, Track
from .i18n import T
from .productos import SIN_ALBUM, SIN_DATOS, asignar_carpetas
from .relevar_core import album_coincide
from .texto import comparable, misma_version
from .validar import gtin13
from .version import VERSION

FORMATO = "migrador-relevamiento"
VERSION_FORMATO = 1
MAX_BYTES = 5 * 1024 * 1024
MAX_PRODUCTOS = 5000
MAX_TRACKS = 50_000


class InstantaneaInvalida(ValueError):
    """El archivo no es un relevamiento guardado por la app. Para mostrar."""


# ============================================================
# Volcar
# ============================================================

# Lo que se guarda de cada tema y de cada producto, con su tipo. Es una lista
# cerrada: lo que no está acá no se escribe y no se lee. Quedan afuera los
# bytes de la portada, las rutas del audio y todo lo que se arma al preparar
# el paquete, que no es parte del relevamiento.
_TRACK: dict[str, type] = {
    "video_id": str,
    "track": str,
    "album": str,
    "distributor": str,
    "label": str,
    "isrc": str,
    "upc": str,
    "match": str,
    "duration_s": int,
    "views": int,
    "likes": int,
    "comments": int,
    "upload_date": str,
    "release_date": str,
    "p_line": str,
    "desc3": str,
    "url": str,
    "upc_descartado": str,
    "upc_por_tracklist": str,
    "fecha_deezer": str,
    "isrc_como": str,
    "isrc_nivel": str,
    "isrc_respaldo": str,
    "upc_como": str,
    "track_number": int,
    "disc_number": int,
    "orden_fuente": str,
    "album_deezer_id": int,
    "origen": str,
}
_PRODUCTO: dict[str, type] = {
    "product_id": str,
    "title": str,
    "kind": str,
    "artist": str,
    "release_date": str,
    "upload_date": str,
    "label": str,
    "p_line": str,
    "distributor": str,
    "upc": str,
    "total_views": int,
    "order_unconfirmed": bool,
    "fecha_fuente": str,
    "origen": str,
    "de_deezer": int,
    "upc_nivel": str,
    "upc_respaldo": str,
}
_OBLIGATORIAS_TRACK = ("track", "duration_s")
_TIPOS = ("single", "ep", "album")
LARGO_MAX_TEXTO = 2000


def _anio(v) -> int | str:
    return v if isinstance(v, int) and not isinstance(v, bool) and 1800 <= v <= 2200 else ""


def volcar(productos: list[Producto], artista, diag=None) -> bytes:
    """El relevamiento como JSON, para guardar adentro del paquete."""

    def de(origen: Any, campos: dict[str, type]) -> dict[str, Any]:
        return {k: origen[k] for k in campos if k in origen and origen[k] not in (None, "")}

    salida = []
    for p in productos:
        prod = de(p, _PRODUCTO)
        prod["release_year"] = _anio(p.get("release_year"))
        for clave in ("tambien_en", "faltan_temas"):
            if p.get(clave):
                prod[clave] = list(p.get(clave) or [])
        if p.get("datos"):
            prod["datos"] = dict(p.get("datos") or {})
        if p.get("upc_previo"):
            prod["upc_previo"] = dict(p.get("upc_previo") or {})
        prod["tracks"] = []
        for t in p.get("tracks", []):
            tema = de(t, _TRACK)
            tema["release_year"] = _anio(t.get("release_year"))
            tema["artists"] = list(t.get("artists") or [])
            tema["credits"] = {
                k: list(v) for k, v in dict(t.get("credits") or {}).items() if isinstance(v, list)
            }
            if t.get("isrc_candidatos"):
                tema["isrc_candidatos"] = [dict(c) for c in t.get("isrc_candidatos") or []]
            if t.get("isrc_previo"):
                tema["isrc_previo"] = dict(t.get("isrc_previo") or {})
            prod["tracks"].append(tema)
        salida.append(prod)
    datos = {
        "formato": FORMATO,
        "version": VERSION_FORMATO,
        "app": VERSION,
        "fecha": date.today().isoformat(),
        "artista": artista or "",
        # Del diagnóstico va sólo lo que sirve para contar cómo se relevó; lo
        # demás (la comparación con Deezer, entera) ya quedó en los productos.
        "canal": {
            "canal": (diag or {}).get("canal", ""),
            "via": (diag or {}).get("via", ""),
            "temas": int((diag or {}).get("temas") or 0),
        },
        "productos": salida,
    }
    return json.dumps(datos, ensure_ascii=False, indent=1).encode("utf-8")


# ============================================================
# Abrir
# ============================================================


def _texto(v, tope=LARGO_MAX_TEXTO) -> str:
    return v[:tope] if isinstance(v, str) else ""


def _entero(v) -> int:
    return v if isinstance(v, int) and not isinstance(v, bool) and 0 <= v < 10**12 else 0


def _lista_de_textos(v, tope=200) -> list[str]:
    return [_texto(x, 300) for x in v[:tope] if isinstance(x, str)] if isinstance(v, list) else []


def _mapa_de_textos(v, claves=None) -> dict[str, str]:
    if not isinstance(v, dict):
        return {}
    return {
        str(k)[:60]: _texto(x, 300)
        for k, x in list(v.items())[:40]
        if isinstance(x, str) and (claves is None or k in claves)
    }


def _leer(origen: Any, campos: dict[str, type]) -> dict[str, Any]:
    """Los campos conocidos de un objeto del archivo, con su tipo. Lo que no
    tiene el tipo esperado se descarta: no se intenta convertir."""
    out: dict[str, Any] = {}
    if not isinstance(origen, dict):
        return out
    for clave, tipo in campos.items():
        v = origen.get(clave)
        if tipo is str and isinstance(v, str) and v:
            out[clave] = _texto(v)
        elif tipo is int and isinstance(v, int) and not isinstance(v, bool):
            out[clave] = _entero(v)
        elif tipo is bool and isinstance(v, bool):
            out[clave] = v
    return out


def _track_de(crudo: Any) -> Track | None:
    leido = _leer(crudo, _TRACK)
    if not all(k in leido for k in _OBLIGATORIAS_TRACK[:1]):
        return None
    creditos = crudo.get("credits") if isinstance(crudo.get("credits"), dict) else {}
    t: Track = {
        "video_id": leido.get("video_id", ""),
        "track": leido["track"],
        "album": leido.get("album") or SIN_ALBUM,
        "distributor": leido.get("distributor") or SIN_DATOS,
        "label": leido.get("label", ""),
        "release_year": _anio(crudo.get("release_year")),
        "isrc": leido.get("isrc", ""),
        "upc": leido.get("upc", ""),
        "match": leido.get("match", ""),
        "duration_s": leido.get("duration_s", 0),
        "views": leido.get("views", 0),
        "likes": leido.get("likes", 0),
        "comments": leido.get("comments", 0),
        "upload_date": leido.get("upload_date", ""),
        "release_date": leido.get("release_date", ""),
        "p_line": leido.get("p_line", ""),
        "artists": _lista_de_textos(crudo.get("artists"), 50),
        "credits": {
            "composers": _lista_de_textos(creditos.get("composers"), 50),
            "lyricists": _lista_de_textos(creditos.get("lyricists"), 50),
            "producers": _lista_de_textos(creditos.get("producers"), 50),
            "publishers": _lista_de_textos(creditos.get("publishers"), 50),
        },
        "desc3": leido.get("desc3", ""),
        "url": leido.get("url", ""),
    }
    # Un enlace que no es de YouTube ni de Deezer no se conserva: la interfaz
    # lo muestra como enlace, y no tiene por qué apuntar a ningún otro lado.
    if not t["url"].startswith(("https://youtu.be/", "https://www.deezer.com/")):
        t["url"] = ""
    opcionales = (
        "upc_descartado",
        "upc_por_tracklist",
        "fecha_deezer",
        "isrc_como",
        "isrc_nivel",
        "isrc_respaldo",
        "upc_como",
        "track_number",
        "disc_number",
        "orden_fuente",
        "album_deezer_id",
        "origen",
    )
    for clave in opcionales:
        if clave in leido:
            t[clave] = leido[clave]
    candidatos = crudo.get("isrc_candidatos")
    if isinstance(candidatos, list):
        limpios = [
            {
                "isrc": _texto(c.get("isrc"), 20),
                "titulo": _texto(c.get("titulo"), 300),
                "duracion_s": _entero(c.get("duracion_s")),
            }
            for c in candidatos[:20]
            if isinstance(c, dict)
        ]
        if limpios:
            t["isrc_candidatos"] = cast(list[CandidatoISRC], limpios)
    previo = _mapa_de_textos(
        crudo.get("isrc_previo"), ("isrc", "isrc_como", "isrc_nivel", "match", "isrc_respaldo")
    )
    if "isrc" in previo or isinstance(crudo.get("isrc_previo"), dict):
        t["isrc_previo"] = {
            k: previo.get(k, "") for k in ("isrc", "isrc_como", "isrc_nivel", "match", "isrc_respaldo")
        }
    return t


def _producto_de(crudo: Any, n: int, artista: str) -> Producto | None:
    leido = _leer(crudo, _PRODUCTO)
    tracks = [
        t for t in (_track_de(x) for x in (crudo.get("tracks") or [])[:2000] if isinstance(x, dict)) if t
    ]
    if not leido.get("title") or not tracks:
        return None
    from .ediciones import CAMPOS_A_COMPLETAR

    p: Producto = {
        "product_id": f"p{n:03d}",
        "title": leido["title"],
        "kind": leido["kind"] if leido.get("kind") in _TIPOS else "single",
        "artist": leido.get("artist") or artista,
        "release_year": _anio(crudo.get("release_year")),
        "release_date": leido.get("release_date", ""),
        "upload_date": leido.get("upload_date", ""),
        "label": leido.get("label", ""),
        "p_line": leido.get("p_line", ""),
        "distributor": leido.get("distributor", ""),
        "upc": leido.get("upc", ""),
        "tracks": tracks,
        "track_count": len(tracks),
        "total_views": leido.get("total_views", 0),
        "order_unconfirmed": bool(leido.get("order_unconfirmed")),
        "folder": "",
    }
    for clave in ("fecha_fuente", "origen", "de_deezer", "upc_nivel", "upc_respaldo"):
        if clave in leido:
            p[clave] = leido[clave]
    for clave in ("tambien_en", "faltan_temas"):
        lista = _lista_de_textos(crudo.get(clave))
        if lista:
            p[clave] = lista
    datos = _mapa_de_textos(crudo.get("datos"), CAMPOS_A_COMPLETAR)
    if datos:
        p["datos"] = {k: v[:200] for k, v in datos.items() if v}
    if isinstance(crudo.get("upc_previo"), dict):
        previo = _mapa_de_textos(crudo["upc_previo"], ("upc", "upc_nivel", "upc_respaldo"))
        p["upc_previo"] = {k: previo.get(k, "") for k in ("upc", "upc_nivel", "upc_respaldo")}
    return p


def _json_del_archivo(datos: bytes) -> Any:
    """El JSON del relevamiento: el archivo mismo, o el que trae el paquete."""
    if len(datos) > MAX_BYTES:
        raise InstantaneaInvalida(T("ins.muy_grande"))
    crudo = datos
    if datos[:4] == b"PK\x03\x04":
        try:
            with zipfile.ZipFile(io.BytesIO(datos)) as z:
                candidatos = [
                    i
                    for i in z.infolist()
                    if i.filename.lower().endswith(".json") and i.file_size <= MAX_BYTES
                ]
                if not candidatos:
                    raise InstantaneaInvalida(T("ins.no_es"))
                # El de la raíz del paquete: el de ruta más corta.
                crudo = z.read(min(candidatos, key=lambda i: i.filename.count("/")))
        except zipfile.BadZipFile:
            raise InstantaneaInvalida(T("ins.no_es")) from None
    try:
        return json.loads(crudo.decode("utf-8-sig"))
    except (ValueError, UnicodeDecodeError, RecursionError):
        raise InstantaneaInvalida(T("ins.no_es")) from None


def abrir(datos: bytes) -> tuple[list[Producto], str, dict[str, Any]]:
    """Lee un relevamiento guardado: (productos, artista, datos del archivo).

    Acepta el archivo `.json` del paquete, o el ZIP entero si entra en el tope.
    Levanta `InstantaneaInvalida` si no es un relevamiento de esta app.
    """
    raiz = _json_del_archivo(datos)
    if not isinstance(raiz, dict) or raiz.get("formato") != FORMATO:
        raise InstantaneaInvalida(T("ins.no_es"))
    if not isinstance(raiz.get("version"), int) or raiz["version"] > VERSION_FORMATO:
        raise InstantaneaInvalida(T("ins.mas_nueva"))
    crudos = raiz.get("productos")
    if not isinstance(crudos, list) or not crudos:
        raise InstantaneaInvalida(T("ins.no_es"))
    artista = _texto(raiz.get("artista"), 300)
    productos: list[Producto] = []
    total = 0
    for crudo in crudos[:MAX_PRODUCTOS]:
        p = _producto_de(crudo, len(productos) + 1, artista) if isinstance(crudo, dict) else None
        if p is None:
            continue
        total += len(p["tracks"])
        if total > MAX_TRACKS:
            break
        productos.append(p)
    if not productos:
        raise InstantaneaInvalida(T("ins.no_es"))
    asignar_carpetas(productos)
    for p in productos:
        evidencia.contar_sin_confirmar(p)
    canal: dict[str, Any] = raiz["canal"] if isinstance(raiz.get("canal"), dict) else {}
    info = {
        "fecha": _texto(raiz.get("fecha"), 10),
        "app": _texto(raiz.get("app"), 20),
        "canal": _texto(canal.get("canal"), 300),
        "via": _texto(canal.get("via"), 20),
        "temas": _entero(canal.get("temas")),
    }
    return productos, artista, info


# ============================================================
# Comparar
# ============================================================

MARGEN_DURACION = 4


def _isrcs(p: Producto) -> set[str]:
    return {t["isrc"] for t in p.get("tracks", []) if t.get("isrc")}


def _mismo_release(a: Producto, b: Producto) -> bool:
    """Si dos productos, de dos relevamientos, son el mismo release."""
    if a.get("upc") and b.get("upc") and gtin13(a["upc"]) == gtin13(b["upc"]):
        return True
    if not album_coincide(
        a.get("title") or "", b.get("title") or "", a.get("release_date") or "", b.get("release_date") or ""
    ):
        return False
    # El mismo título: además tiene que parecerse por dentro. Dos singles que
    # se llaman igual no son el mismo release.
    isrc_a, isrc_b = _isrcs(a), _isrcs(b)
    if isrc_a and isrc_b and isrc_a & isrc_b:
        return True
    titulos_a = {comparable(t.get("track") or "") for t in a.get("tracks", [])}
    titulos_b = {comparable(t.get("track") or "") for t in b.get("tracks", [])}
    comunes = len(titulos_a & titulos_b)
    return comunes >= max(1, min(len(titulos_a), len(titulos_b)) // 2)


def _mismo_tema(a: Track, b: Track) -> bool:
    if comparable(a.get("track") or "") != comparable(b.get("track") or ""):
        return False
    if not misma_version(a.get("track") or "", b.get("track") or ""):
        return False
    da, db = int(a.get("duration_s") or 0), int(b.get("duration_s") or 0)
    return not (da and db) or abs(da - db) <= 2 * MARGEN_DURACION


def _comparar_release(antes: Producto, ahora: list[Producto]) -> ReleaseComparado:
    res: ReleaseComparado = {
        "titulo": antes.get("title") or "",
        "anio": antes.get("release_year") or "",
        "estado": "falta",
        "distribuidora_antes": antes.get("distributor") or "",
        "distribuidoras_ahora": sorted({p.get("distributor") or "" for p in ahora} - {""}),
        "upc_antes": antes.get("upc") or "",
        "upc_ahora": "",
        "isrc_cambiados": [],
        "isrc_perdidos": [],
        "temas_que_faltan": [],
    }
    # Lo que se ve en YouTube: un release que hoy sale sólo de Deezer no dice
    # qué distribuidora lo tiene, y no cuenta como «está».
    visibles = [p for p in ahora if p.get("origen") != "deezer"]
    if not visibles:
        res["estado"] = "falta" if not ahora else "sin_youtube"
        return res
    otras = [p for p in visibles if (p.get("distributor") or "") != (antes.get("distributor") or "")]
    # El que se mira para los códigos: el de la distribuidora nueva, si ya
    # está; si no, el que hay.
    nuevo = (otras or visibles)[0]
    res["upc_ahora"] = nuevo.get("upc") or ""
    for t in antes.get("tracks", []):
        par = next((x for x in nuevo.get("tracks", []) if t.get("isrc") and x.get("isrc") == t["isrc"]), None)
        par = par or next((x for x in nuevo.get("tracks", []) if _mismo_tema(t, x)), None)
        if par is None:
            res["temas_que_faltan"].append(t.get("track") or "")
        elif t.get("isrc") and par.get("isrc") and par["isrc"] != t["isrc"]:
            res["isrc_cambiados"].append(
                {"tema": t.get("track") or "", "antes": t["isrc"], "ahora": par["isrc"]}
            )
        elif t.get("isrc") and not par.get("isrc"):
            res["isrc_perdidos"].append(t.get("track") or "")
    upc_cambio = bool(
        res["upc_antes"] and res["upc_ahora"] and gtin13(res["upc_antes"]) != gtin13(res["upc_ahora"])
    )
    if not otras:
        res["estado"] = "igual"
    elif len(otras) < len(visibles):
        res["estado"] = "en_las_dos"
    elif upc_cambio or res["isrc_cambiados"]:
        res["estado"] = "codigos_cambiados"
    else:
        res["estado"] = "migrado"
    # En las dos a la vez y además con otro código: lo grave es el código.
    if res["estado"] == "en_las_dos" and (upc_cambio or res["isrc_cambiados"]):
        res["estado"] = "codigos_cambiados"
    return res


def comparar(antes: list[Producto], ahora: list[Producto]) -> Comparacion:
    """Qué pasó con cada release de un relevamiento guardado, según uno nuevo.

    `antes` es lo que se iba a migrar; `ahora`, el canal relevado hoy. Los
    estados, de mejor a peor:

        migrado            Está en otra distribuidora, con el mismo UPC y los
                           mismos ISRC.
        en_las_dos         Está en la de antes y en otra: falta la baja.
        igual              Sigue sólo en la de antes: todavía no se migró.
        sin_youtube        Hoy no se ve en YouTube, aunque figura en Deezer.
        falta              No aparece.
        codigos_cambiados  Está en otra distribuidora con otro UPC, o con algún
                           ISRC distinto: ese release perdió su historial.

    Los releases que se sumaron desde Deezer en el relevamiento guardado no se
    comparan: de ellos nunca se supo la distribuidora.
    """
    releases: list[ReleaseComparado] = []
    usados: set[int] = set()
    for a in antes:
        if a.get("origen") == "deezer":
            continue
        pares = [b for b in ahora if _mismo_release(a, b)]
        usados.update(id(b) for b in pares)
        releases.append(_comparar_release(a, pares))
    nuevos = [
        {
            "titulo": b.get("title") or "",
            "distribuidora": b.get("distributor") or "",
            "upc": b.get("upc") or "",
        }
        for b in ahora
        if id(b) not in usados and b.get("origen") != "deezer"
    ]
    cuenta: dict[str, int] = {}
    for r in releases:
        cuenta[r["estado"]] = cuenta.get(r["estado"], 0) + 1
    return {"releases": releases, "resumen": cuenta, "nuevos": nuevos[:200], "nuevos_total": len(nuevos)}
