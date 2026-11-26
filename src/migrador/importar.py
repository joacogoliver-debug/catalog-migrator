"""
Los códigos que tiene la distribuidora actual, conciliados contra el catálogo.

Por qué existe. Cuando falta un ISRC o un UPC, lo único correcto es pedírselo a
la distribuidora que hoy tiene el catálogo: un código nuevo es un release
nuevo, sin sus reproducciones ni sus playlists. La app lo decía en cada
pantalla, y ahí terminaba. La distribuidora contesta con una planilla (un
export de su panel, o la hoja de pedido que arma esta misma app, ver
`paquete.hoja_pedido_bytes`), y pasar esa planilla al catálogo era un trabajo
de copiar y pegar fila por fila, con el riesgo de pegar el código de la versión
en vivo en la de estudio.

Qué hace. Lee el archivo sin pedirle un formato: reconoce las columnas por su
encabezado, en castellano o en inglés, y las de códigos también por lo que
traen. Después concilia cada tema del catálogo con las filas del archivo y
separa cuatro casos, que es lo que importa:

    confirma    El archivo trae el mismo código que ya tenía el tema. Dos
                fuentes independientes de acuerdo: el código pasa a
                «confirmado».
    completa    El tema no tenía código y hay una sola fila que es ese tema.
    conflicto   El archivo dice un código y el relevamiento otro. No se elige:
                se muestran los dos, y decide una persona.
    ambiguo     Hay más de una fila que puede ser ese tema, con códigos
                distintos, y nada en el archivo las separa.

Nunca se pisa un código en silencio y nunca se elige entre dos candidatos: lo
que no es seguro se muestra. Es el mismo criterio que el resto del cruce (ante
la duda, en blanco), con una diferencia: acá la duda se le puede preguntar a
alguien.

Cómo se decide que una fila es un tema. Por el ISRC, si el tema ya lo tiene:
es exacto. Si no, por el título y la versión (`texto.misma_version`), y entre
las filas que se llaman igual, por lo que el archivo traiga para separarlas: el
release (su título o su UPC), la duración y el número de track. La idea de
comparar dos registros campo por campo y sumar lo que cada campo aporta viene
del enlace probabilístico de registros (Fellegi y Sunter, que es lo que
implementa splink) y de la distancia ponderada de beets; lo que se toma es el
criterio, con pesos fijos y a la vista, sin entrenar nada: con unos cientos de
filas no hay de dónde estimar probabilidades, y un peso que se puede leer es
un peso que se puede discutir.

No importa nada que toque la red. El archivo es un dato de afuera: se lee con
topes de tamaño y de filas, y nada de lo que trae se ejecuta.
"""

import csv
import io
import re
import zipfile
from difflib import SequenceMatcher

from . import ediciones, evidencia
from .contratos import FilaImportada, ItemImportacion, Producto, PropuestaImportacion, Track
from .i18n import T
from .relevar_core import album_coincide
from .texto import comparable, misma_version, sin_decorado
from .validar import RE_ISRC, gtin13, isrc_valido, upc_valido

# Topes de lectura. Una planilla de catálogo real tiene cientos o miles de
# filas; lo que pase de esto no es una planilla de catálogo.
MAX_BYTES = 5 * 1024 * 1024
MAX_DESCOMPRIMIDO = 80 * 1024 * 1024
MAX_FILAS = 50_000
MAX_COLUMNAS = 120
# En cuántas filas se busca el encabezado: los exports traen a veces un título
# y una fecha antes de la tabla.
FILAS_DE_ENCABEZADO = 25

MARGEN_DURACION = 4
MIN_SIMILITUD_TITULO = 0.9


class ArchivoInvalido(ValueError):
    """El archivo no se puede leer como una planilla de códigos. El mensaje es
    para mostrar."""


# ============================================================
# Columnas
# ============================================================

# Cómo se llaman las columnas en los exports de las distribuidoras y en las
# planillas armadas a mano, ya normalizadas con `comparable`. El orden importa
# sólo adentro de cada lista: lo más específico primero.
_SINONIMOS = {
    "isrc": ("isrc", "isrc code", "codigo isrc", "isrc del track", "track isrc"),
    "upc": (
        "upc",
        "ean",
        "upc ean",
        "ean upc",
        "barcode",
        "bar code",
        "codigo de barras",
        "upc code",
        "release upc",
        "album upc",
        "gtin",
        "upc del release",
        "codigo upc",
    ),
    "track": (
        "track title",
        "track name",
        "song title",
        "song name",
        "song",
        "track",
        "titulo del track",
        "titulo del tema",
        "titulo de la cancion",
        "nombre del track",
        "nombre de la cancion",
        "tema",
        "cancion",
        "pista",
        "asset title",
        "recording title",
    ),
    "album": (
        "release title",
        "release name",
        "album title",
        "album name",
        "album",
        "release",
        "product title",
        "product name",
        "product",
        "titulo del album",
        "titulo del lanzamiento",
        "titulo del release",
        "nombre del album",
        "lanzamiento",
        "producto",
        "disco",
    ),
    "duracion": ("duration", "length", "duracion", "track length", "track duration", "time", "tiempo"),
    "numero": (
        "track number",
        "track no",
        "track num",
        "track",
        "numero de track",
        "nro de track",
        "numero",
        "position",
        "posicion",
        "sequence",
        "n",
    ),
    "version": ("version", "mix version", "version title", "track version", "subtitle", "subtitulo"),
}
# Un «title», «titulo» o «nombre» a secas: es el del tema, salvo que no haya
# otra columna para el release y los valores se repitan en bloques.
_GENERICOS_DE_TITULO = ("title", "titulo", "nombre", "name")


def _columna_por_encabezado(encabezados: list[str]) -> dict[str, int]:
    """Qué columna es cada cosa, por cómo se llama: {campo: índice}."""
    normales = [comparable(h) for h in encabezados]
    out: dict[str, int] = {}
    usadas: set[int] = set()
    # «track» puede ser el título del tema o su número: se resuelve después de
    # los campos que no tienen esa duda, y el número sólo toma lo que queda.
    for campo in ("isrc", "upc", "album", "duracion", "version", "track", "numero"):
        for sinonimo in _SINONIMOS[campo]:
            for i, h in enumerate(normales):
                if h == sinonimo and i not in usadas:
                    out[campo] = i
                    usadas.add(i)
                    break
            if campo in out:
                break
    if "track" not in out:
        for i, h in enumerate(normales):
            if h in _GENERICOS_DE_TITULO and i not in usadas:
                out["track"] = i
                break
    return out


def _parece_isrc(v) -> bool:
    return bool(RE_ISRC.fullmatch(ediciones.normalizar_isrc(v)))


def _parece_upc(v) -> bool:
    return upc_valido(_como_upc(v))[0]


def _como_upc(v) -> str:
    """Un UPC leído de una planilla. Excel lo guarda como número: llega
    «885012345678.0», o en notación científica, y sin el cero de adelante."""
    texto = str(v or "").strip()
    if re.fullmatch(r"\d+\.0+", texto):
        texto = texto.split(".")[0]
    elif re.fullmatch(r"\d(\.\d+)?[eE]\+?\d+", texto):
        try:
            texto = str(int(float(texto)))
        except (ValueError, OverflowError):
            return ""
    limpio = ediciones.normalizar_upc(texto)
    # Menos de doce dígitos que con ceros adelante son un UPC válido: son los
    # ceros que se comió la planilla al guardarlo como número.
    if limpio.isdigit() and 9 <= len(limpio) <= 11 and upc_valido(limpio.zfill(12))[0]:
        return limpio.zfill(12)
    return limpio


def _columnas_por_contenido(filas: list[list[str]], ya: dict[str, int]) -> dict[str, int]:
    """Las columnas de códigos, por lo que traen: sirve cuando el encabezado no
    dice nada («Código», «ID») o no hay encabezado."""
    out = dict(ya)
    ancho = max((len(f) for f in filas), default=0)
    for campo, parece in (("isrc", _parece_isrc), ("upc", _parece_upc)):
        if campo in out:
            continue
        mejor, mejor_n = -1, 0
        for i in range(ancho):
            if i in out.values():
                continue
            valores = [f[i] for f in filas if i < len(f) and str(f[i]).strip()]
            aciertos = sum(1 for v in valores if parece(v))
            if valores and aciertos >= max(2, 0.6 * len(valores)) and aciertos > mejor_n:
                mejor, mejor_n = i, aciertos
        if mejor >= 0:
            out[campo] = mejor
    return out


# ============================================================
# Lectura
# ============================================================


def _celdas_csv(datos: bytes) -> list[list[str]]:
    texto = None
    for codificacion in ("utf-8-sig", "utf-16", "cp1252"):
        try:
            texto = datos.decode(codificacion)
            break
        except UnicodeError:
            continue
    if texto is None:
        raise ArchivoInvalido(T("imp.no_se_lee"))
    muestra = texto[:8192]
    # El separador se deduce de las primeras líneas: un CSV exportado con la
    # configuración regional en castellano usa punto y coma.
    cuentas = {sep: muestra.count(sep) for sep in (",", ";", "\t", "|")}
    separador = max(cuentas, key=lambda s: cuentas[s]) if any(cuentas.values()) else ","
    filas = []
    for fila in csv.reader(io.StringIO(texto), delimiter=separador):
        filas.append([c.strip() for c in fila[:MAX_COLUMNAS]])
        if len(filas) > MAX_FILAS:
            break
    return filas


def _celdas_xlsx(datos: bytes) -> list[list[str]]:
    # Un xlsx es un ZIP. Antes de dárselo a openpyxl se mira cuánto ocupa
    # descomprimido: un archivo de pocos KB puede declarar varios GB adentro.
    try:
        with zipfile.ZipFile(io.BytesIO(datos)) as z:
            if sum(i.file_size for i in z.infolist()) > MAX_DESCOMPRIMIDO:
                raise ArchivoInvalido(T("imp.muy_grande"))
    except zipfile.BadZipFile:
        raise ArchivoInvalido(T("imp.no_se_lee")) from None
    from openpyxl import load_workbook

    try:
        # `read_only` no carga la planilla entera en memoria, y `data_only`
        # trae el valor de cada celda y no su fórmula: de acá no se ejecuta nada.
        libro = load_workbook(io.BytesIO(datos), read_only=True, data_only=True)
    except Exception:  # noqa: BLE001 (openpyxl levanta de todo ante un xlsx roto)
        raise ArchivoInvalido(T("imp.no_se_lee")) from None
    mejor: list[list[str]] = []
    try:
        for hoja in libro.worksheets:
            filas = []
            for fila in hoja.iter_rows(values_only=True):
                filas.append(["" if c is None else str(c).strip() for c in fila[:MAX_COLUMNAS]])
                if len(filas) > MAX_FILAS:
                    break
            # La hoja con más celdas escritas es la de los datos: los exports
            # traen a veces una primera hoja de instrucciones.
            if sum(1 for f in filas for c in f if c) > sum(1 for f in mejor for c in f if c):
                mejor = filas
    finally:
        libro.close()
    return mejor


def _segundos(v) -> int:
    """Una duración de planilla en segundos: «3:20», «0:03:20», «200» o «200.0»."""
    texto = str(v or "").strip()
    if not texto:
        return 0
    partes = texto.split(":")
    try:
        if len(partes) > 1:
            total = 0.0
            for parte in partes:
                total = total * 60 + float(parte)
            return int(round(total))
        n = float(texto)
    except ValueError:
        return 0
    # Un número suelto son segundos; si pasa de un día, son milisegundos.
    return int(round(n / 1000 if n > 86_400 else n))


def leer(datos: bytes, nombre="") -> tuple[list[FilaImportada], dict[str, str]]:
    """Lee una planilla de códigos: (filas, columnas reconocidas).

    Acepta xlsx y CSV (con coma, punto y coma o tabulación). `columnas` dice
    qué encabezado del archivo se tomó para cada campo, para mostrarlo: quien
    importa tiene que poder ver que «Título» se leyó como el tema y no como el
    disco. Levanta `ArchivoInvalido` si no hay ninguna columna de códigos.
    """
    if len(datos) > MAX_BYTES:
        raise ArchivoInvalido(T("imp.muy_grande"))
    if not datos.strip():
        raise ArchivoInvalido(T("imp.vacio"))
    es_xlsx = datos[:4] == b"PK\x03\x04"
    if not es_xlsx and (nombre or "").lower().endswith((".xls", ".ods", ".numbers")):
        raise ArchivoInvalido(T("imp.formato_no_soportado"))
    crudas = _celdas_xlsx(datos) if es_xlsx else _celdas_csv(datos)
    # Con su número de fila en el archivo, que es el que después se muestra:
    # sacar las filas vacías no puede correr la cuenta.
    numeradas = [(n, f) for n, f in enumerate(crudas, 1) if any(c for c in f)]
    if not numeradas:
        raise ArchivoInvalido(T("imp.vacio"))
    celdas = [f for _n, f in numeradas]

    # El encabezado es la fila, de las primeras, que más columnas conocidas
    # nombra. Si ninguna nombra nada, no hay encabezado y se mira el contenido.
    mejor_i, mejor_cols = -1, {}
    for i, fila in enumerate(celdas[:FILAS_DE_ENCABEZADO]):
        cols = _columna_por_encabezado(fila)
        if len(cols) > len(mejor_cols):
            mejor_i, mejor_cols = i, cols
    cuerpo = celdas[mejor_i + 1 :] if mejor_i >= 0 else celdas
    encabezados = celdas[mejor_i] if mejor_i >= 0 else []
    cols = _columnas_por_contenido(cuerpo, mejor_cols)
    if "isrc" not in cols and "upc" not in cols:
        raise ArchivoInvalido(T("imp.sin_codigos"))

    def celda(fila, campo):
        i = cols.get(campo, -1)
        return fila[i] if 0 <= i < len(fila) else ""

    filas: list[FilaImportada] = []
    for (n, _f), fila in zip(numeradas[mejor_i + 1 :], cuerpo, strict=True):
        isrc = ediciones.normalizar_isrc(celda(fila, "isrc"))
        upc = _como_upc(celda(fila, "upc"))
        titulo, version = celda(fila, "track"), celda(fila, "version")
        if version and comparable(version) not in comparable(titulo):
            titulo = f"{titulo} ({version})"
        item: FilaImportada = {
            "fila": n,
            "isrc": isrc if isrc_valido(isrc) else "",
            "upc": upc if upc_valido(upc)[0] else "",
            "track": titulo,
            "album": celda(fila, "album"),
            "duracion_s": _segundos(celda(fila, "duracion")),
            "numero": _entero(celda(fila, "numero")),
        }
        if item["isrc"] or item["upc"]:
            filas.append(item)
    if not filas:
        raise ArchivoInvalido(T("imp.sin_codigos"))
    reconocidas = {
        campo: (encabezados[i] if i < len(encabezados) and encabezados[i] else f"#{i + 1}")
        for campo, i in sorted(cols.items(), key=lambda kv: kv[1])
    }
    return filas, reconocidas


def _entero(v) -> int:
    m = re.match(r"\s*(\d{1,4})(?:\.0+)?\s*$", str(v or ""))
    return int(m.group(1)) if m else 0


# ============================================================
# Conciliación
# ============================================================

# Lo que aporta cada campo cuando coincide, y lo que resta cuando contradice.
# El título es la condición de entrada y no suma: lo que se pesa es lo que
# separa dos filas que se llaman igual.
PESO_RELEASE = 3.0  # el mismo UPC, o el mismo título de release
PESO_DURACION = 2.0
PESO_NUMERO = 1.0
PESO_TITULO_EXACTO = 0.5
# Con cuánta ventaja sobre la segunda una fila es «la» fila de un tema.
VENTAJA_MINIMA = 1.0


def _mismo_tema(fila: FilaImportada, t: Track) -> float:
    """Qué tan igual es el título de la fila al del tema: 1, algo menos, o 0."""
    a, b = fila["track"], t.get("track") or ""
    if not comparable(a) or not misma_version(a, b):
        return 0.0
    if comparable(a) == comparable(b):
        return 1.0
    if comparable(sin_decorado(a)) == comparable(sin_decorado(b)) and comparable(sin_decorado(a)):
        return 0.95
    r = SequenceMatcher(None, comparable(a), comparable(b)).ratio()
    return r if r >= MIN_SIMILITUD_TITULO else 0.0


def _puntaje(fila: FilaImportada, p: Producto, t: Track) -> float | None:
    """Cuánto respalda el archivo que esa fila es ese tema, o None si no puede
    serlo. Sólo se llama con filas que se llaman como el tema."""
    titulo = _mismo_tema(fila, t)
    if not titulo:
        return None
    puntos = PESO_TITULO_EXACTO if titulo == 1.0 else 0.0
    dur_a, dur_b = fila["duracion_s"], int(t.get("duration_s") or 0)
    if dur_a and dur_b:
        if abs(dur_a - dur_b) > 2 * MARGEN_DURACION:
            return None  # otra grabación: el mismo título con otra duración
        if abs(dur_a - dur_b) <= MARGEN_DURACION:
            puntos += PESO_DURACION
    if fila["upc"] and p.get("upc"):
        if gtin13(fila["upc"]) == gtin13(p["upc"]):
            puntos += PESO_RELEASE
        elif fila["album"] and comparable(fila["album"]) != comparable(p.get("title") or ""):
            puntos -= PESO_RELEASE  # dice ser de otro release, con nombre y código
    elif fila["album"]:
        if comparable(fila["album"]) == comparable(p.get("title") or ""):
            puntos += PESO_RELEASE
        elif len(p.get("tracks", [])) > 1 or comparable(fila["album"]) != comparable(fila["track"]):
            puntos -= PESO_RELEASE / 2
    if fila["numero"] and t.get("track_number") and not p.get("order_unconfirmed"):
        if fila["numero"] == t.get("track_number"):
            puntos += PESO_NUMERO
    return puntos


def _del_release(fila: FilaImportada, p: Producto) -> bool:
    """Si la fila dice ser de ese release: por su UPC, o por cómo se llama."""
    if fila["upc"] and p.get("upc") and gtin13(fila["upc"]) == gtin13(p["upc"]):
        return True
    return bool(fila["album"]) and album_coincide(p.get("title") or "", fila["album"])


def _sirve_para_el_upc(fila: FilaImportada, p: Producto) -> bool:
    """Si el UPC de esa fila puede ser el del producto.

    La misma grabación figura en el archivo una vez por release: en la fila
    del single y en la del álbum, con el mismo ISRC y dos UPC. Para el UPC de
    un producto cuentan sólo las filas de su release; o todas, cuando el
    archivo no dice de qué release es ninguna.
    """
    return _del_release(fila, p) or not fila["album"]


def _item(tipo, p: Producto, indice, t: Track | None, **datos) -> ItemImportacion:
    return {
        "id": "",
        "tipo": tipo,
        "codigo": datos.get("codigo", "isrc"),
        "producto_id": p["product_id"],
        "producto": p.get("title") or "",
        "indice": indice,
        "track": (t.get("track") or "") if t else "",
        "actual": datos.get("actual", ""),
        "nuevo": datos.get("nuevo", ""),
        "fila": datos.get("fila", 0),
        "candidatos": datos.get("candidatos", []),
        "nivel": datos.get("nivel", ""),
    }


def conciliar(productos: list[Producto], filas: list[FilaImportada]) -> PropuestaImportacion:
    """Compara el archivo con el catálogo y propone qué hacer con cada código.

    No cambia nada: devuelve la propuesta, que la interfaz muestra y
    `aplicar` ejecuta sobre lo que el usuario dejó elegido.
    """
    por_isrc: dict[str, list[FilaImportada]] = {}
    por_titulo: dict[str, list[FilaImportada]] = {}
    for f in filas:
        if f["isrc"]:
            por_isrc.setdefault(f["isrc"], []).append(f)
        if comparable(f["track"]):
            por_titulo.setdefault(comparable(sin_decorado(f["track"])) or comparable(f["track"]), []).append(
                f
            )

    items: list[ItemImportacion] = []
    usadas: set[int] = set()
    # Las filas que quedaron asociadas a cada producto, para proponer su UPC.
    filas_de: dict[str, list[tuple[FilaImportada, bool]]] = {}

    for p in productos:
        for i, t in enumerate(p.get("tracks", [])):
            actual = ediciones.normalizar_isrc(t.get("isrc"))
            if actual and actual in por_isrc:
                # El mismo código en las dos fuentes. No hace falta nada más.
                for f in por_isrc[actual]:
                    usadas.add(f["fila"])
                    filas_de.setdefault(p["product_id"], []).append((f, _sirve_para_el_upc(f, p)))
                if t.get("isrc_nivel") != evidencia.CONFIRMADO:
                    items.append(
                        _item(
                            "confirma", p, i, t, actual=actual, nuevo=actual, fila=por_isrc[actual][0]["fila"]
                        )
                    )
                continue
            clave = comparable(sin_decorado(t.get("track") or "")) or comparable(t.get("track") or "")
            puntuadas = []
            for f in por_titulo.get(clave, []):
                if not f["isrc"]:
                    continue
                puntos = _puntaje(f, p, t)
                if puntos is not None:
                    puntuadas.append((puntos, f))
            if not puntuadas:
                continue
            puntuadas.sort(key=lambda x: -x[0])
            mejor = puntuadas[0][0]
            # Las que empatan arriba, una por código: dos filas con el mismo
            # ISRC (el single y el álbum) no son dos candidatos, son uno.
            arriba: dict[str, FilaImportada] = {}
            for puntos, f in puntuadas:
                if mejor - puntos < VENTAJA_MINIMA:
                    arriba.setdefault(f["isrc"], f)
            if len(arriba) > 1:
                items.append(
                    _item(
                        "ambiguo",
                        p,
                        i,
                        t,
                        actual=actual,
                        candidatos=[
                            {
                                "isrc": f["isrc"],
                                "titulo": f["track"],
                                "album": f["album"],
                                "duracion_s": f["duracion_s"],
                                "fila": f["fila"],
                            }
                            for f in arriba.values()
                        ],
                    )
                )
                continue
            f = next(iter(arriba.values()))
            usadas.add(f["fila"])
            filas_de.setdefault(p["product_id"], []).append((f, _sirve_para_el_upc(f, p)))
            if actual:
                items.append(
                    _item(
                        "conflicto",
                        p,
                        i,
                        t,
                        actual=actual,
                        nuevo=f["isrc"],
                        fila=f["fila"],
                        nivel=t.get("isrc_nivel") or "",
                    )
                )
            else:
                items.append(_item("completa", p, i, t, nuevo=f["isrc"], fila=f["fila"]))

    # Los UPC, por producto. Un release lleva un solo UPC: si las filas que se
    # asociaron a sus temas traen uno solo, es el suyo. Con dos, o con filas
    # que no dicen de qué release son, no se propone nada.
    propuestos: dict[str, list[str]] = {}
    for p in productos:
        asociadas = filas_de.get(p["product_id"]) or []
        upcs = {gtin13(f["upc"]): f for f, firme in asociadas if f["upc"] and firme}
        if len(upcs) != 1:
            continue
        (clave, f), actual = next(iter(upcs.items())), p.get("upc") or ""
        # Las filas tienen que cubrir el producto: un UPC que llega por un solo
        # tema de un disco de doce puede ser el del single.
        cubiertos = len({x["fila"] for x, firme in asociadas if firme})
        if cubiertos < max(1, len(p.get("tracks", [])) // 2):
            continue
        propuestos.setdefault(clave, []).append(p["product_id"])
        if actual and gtin13(actual) == clave:
            if p.get("upc_nivel") != evidencia.CONFIRMADO:
                items.append(
                    _item("confirma", p, -1, None, codigo="upc", actual=actual, nuevo=actual, fila=f["fila"])
                )
        elif actual:
            items.append(
                _item(
                    "conflicto",
                    p,
                    -1,
                    None,
                    codigo="upc",
                    actual=actual,
                    nuevo=f["upc"],
                    fila=f["fila"],
                    nivel=p.get("upc_nivel") or "",
                )
            )
        else:
            items.append(_item("completa", p, -1, None, codigo="upc", nuevo=f["upc"], fila=f["fila"]))
    # El mismo UPC propuesto para dos productos no es de ninguno de los dos
    # con seguridad: se saca de «completa» y queda como conflicto a mirar.
    repetidos = {pid for pids in propuestos.values() if len(pids) > 1 for pid in pids}
    for it in items:
        if it["codigo"] == "upc" and it["tipo"] == "completa" and it["producto_id"] in repetidos:
            it["tipo"] = "conflicto"

    for n, it in enumerate(items, 1):
        it["id"] = f"i{n:04d}"
    sobrantes = [f for f in filas if f["fila"] not in usadas and (f["isrc"] or f["upc"])]
    return {
        "items": items,
        "filas": len(filas),
        "sin_correspondencia": [
            {"fila": f["fila"], "track": f["track"], "album": f["album"], "isrc": f["isrc"], "upc": f["upc"]}
            for f in sobrantes[:200]
        ],
        "sin_correspondencia_total": len(sobrantes),
        "resumen": {
            tipo: sum(1 for it in items if it["tipo"] == tipo)
            for tipo in ("confirma", "completa", "conflicto", "ambiguo")
        },
    }


def elegidos_por_defecto(propuesta: PropuestaImportacion) -> list[str]:
    """Lo que se aplica si el usuario no toca nada: lo que confirma y lo que
    completa. Un conflicto o un ambiguo nunca se aplica solo."""
    return [it["id"] for it in propuesta["items"] if it["tipo"] in ("confirma", "completa")]


def aplicar(
    productos: list[Producto],
    propuesta: PropuestaImportacion,
    elegidos,
    elecciones: dict[str, str] | None = None,
) -> dict[str, int]:
    """Aplica al catálogo los ítems elegidos de una propuesta.

    `elecciones` trae, para cada ítem ambiguo elegido, el ISRC que se eligió
    entre sus candidatos; uno que no esté entre ellos se ignora. Devuelve
    cuántos códigos se confirmaron y cuántos se cargaron.
    """
    elegidos, elecciones = set(elegidos or []), elecciones or {}
    por_id = {p["product_id"]: p for p in productos}
    hechos = {"confirmados": 0, "cargados": 0}
    for it in propuesta["items"]:
        p = por_id.get(it["producto_id"])
        if it["id"] not in elegidos or p is None:
            continue
        nuevo = it["nuevo"]
        if it["tipo"] == "ambiguo":
            nuevo = elecciones.get(it["id"], "")
            if nuevo not in {c["isrc"] for c in it["candidatos"]}:
                continue
        if it["codigo"] == "upc":
            if it["tipo"] == "confirma":
                if gtin13(p.get("upc")) == gtin13(nuevo):
                    p["upc_respaldo"], p["upc_nivel"] = "archivo", evidencia.CONFIRMADO
                    hechos["confirmados"] += 1
            else:
                ediciones.poner_upc(productos, p["product_id"], nuevo, nivel=evidencia.IMPORTADO)
                hechos["cargados"] += 1
            continue
        if not 0 <= it["indice"] < len(p["tracks"]):
            continue
        t = p["tracks"][it["indice"]]
        if it["tipo"] == "confirma":
            if ediciones.normalizar_isrc(t.get("isrc")) == nuevo:
                t["isrc_respaldo"], t["isrc_nivel"] = "archivo", evidencia.CONFIRMADO
                hechos["confirmados"] += 1
        else:
            ediciones.poner_isrc(productos, p["product_id"], it["indice"], nuevo, nivel=evidencia.IMPORTADO)
            hechos["cargados"] += 1
    for p in productos:
        evidencia.contar_sin_confirmar(p)
    return hechos
