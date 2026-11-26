"""
Validación pre-entrega: chequea el catálogo contra los requisitos que usan las
distribuidoras, para saber qué va a ser rechazado ANTES de mandarlo.

Dos niveles:
  error, la distribuidora lo va a rechazar. Hay que corregirlo.
  aviso, pasa la ingesta pero conviene revisarlo.

Todo se valida sin red y sin dependencias extra: los códigos se verifican por
sus reglas de formato y dígito verificador, y las dimensiones de las portadas se
leen de las cabeceras del archivo (JPEG/PNG) sin necesidad de Pillow.

Los mensajes salen de `i18n.py` y van en el idioma que el usuario eligió. El
`codigo` de cada hallazgo, en cambio, no se traduce nunca: es la llave con la
que la interfaz los agrupa y el test los busca.
"""

import re
from difflib import SequenceMatcher
from datetime import date

from .contratos import (
    CAMPOS_A_COMPLETAR,
    FORMATOS_LOSSLESS,
    Hallazgo,
    NivelHallazgo,
    Producto,
    ResultadoValidacion,
)
from .i18n import T
from .texto import comparable, misma_version, parece_formula, sin_decorado

# ISRC: CC-XXX-YY-NNNNN (12 caracteres sin guiones).
#   CC     país (2 letras; incluye códigos especiales como QM/QZ que usan varios
#          registrantes digitales)
#   XXX    registrante (3 alfanuméricos)
#   YY     año de referencia (2 dígitos)
#   NNNNN  designación (5 dígitos)
RE_ISRC = re.compile(r"^[A-Z]{2}[A-Z0-9]{3}\d{7}$")

# Mínimos de portada. Por debajo de 1400x1400 casi ninguna distribuidora la
# acepta; 3000x3000 es lo que piden varias para ingesta. El piso exacto varía
# según la distribuidora y la tienda, y por eso lo de en medio es un aviso.
COVER_MIN = 1400
COVER_RECOMENDADO = 3000

# Residuos típicos de títulos de YouTube que no van en una ficha de release.
#
# «En vivo» y «Live Session» estaban en la lista y salían como ruido, pero los
# títulos que llegan acá son Art Tracks, cuya versión es parte del dato: una
# grabación en vivo se llama «(En Vivo)» en todas las tiendas, y cambiarle el
# título en la migración hace que deje de coincidir con la original.
RE_RUIDO_TITULO = re.compile(
    r"\b(official\s*(music\s*)?video|video\s*oficial|lyric\s*video|video\s*lyric|"
    r"letra\s*oficial|audio\s*oficial|official\s*audio|official\s*visuali[sz]er|visuali[sz]er|"
    r"videoclip(\s*oficial)?|video\s*musical|hd|4k|full\s*album)\b",
    re.I,
)
# Los que sólo son ruido cuando son todo el paréntesis: «(Audio)» o «(Letra)»
# lo son, pero «Audio» o «Letra» pueden ser parte de un título.
RE_RUIDO_PARENTESIS = re.compile(r"[(\[]\s*(audio|letra|lyrics?|m\s*/?\s*v)\s*[)\]]", re.I)


def tiene_ruido(titulo):
    return bool(RE_RUIDO_TITULO.search(titulo or "") or RE_RUIDO_PARENTESIS.search(titulo or ""))


DURACION_MAX_SOSPECHOSA = 15 * 60  # 15 min: puede ser un mix o un álbum entero
ANIO_MIN = 1900


def lista_corta(nombres, tope=8):
    """Una lista de títulos para un mensaje, sin que treinta lo vuelvan ilegible."""
    nombres = list(nombres)
    if len(nombres) <= tope:
        return " · ".join(nombres)
    return " · ".join(nombres[:tope]) + " · " + T("val.y_mas", n=len(nombres) - tope)


def _hallazgo(nivel: NivelHallazgo, codigo, mensaje, producto="", track=None) -> Hallazgo:
    return {"nivel": nivel, "codigo": codigo, "mensaje": mensaje, "producto": producto, "track": track}


# ============================================================
# Códigos
# ============================================================


def isrc_valido(isrc):
    """True si el ISRC tiene formato válido. Acepta guiones y minúsculas."""
    if not isrc:
        return False
    limpio = re.sub(r"[\s\-]", "", str(isrc)).upper()
    return bool(RE_ISRC.fullmatch(limpio))


def _gtin_check_digit(digitos_sin_check):
    """Dígito verificador GTIN (sirve para UPC-A y EAN-13).
    Pesos 3 y 1 alternados desde la derecha."""
    total = 0
    for i, ch in enumerate(reversed(digitos_sin_check)):
        total += int(ch) * (3 if i % 2 == 0 else 1)
    return (10 - total % 10) % 10


def gtin13(upc):
    """El UPC como GTIN-13, para comparar: un UPC-A de 12 dígitos y el mismo
    código como EAN-13 con un cero adelante son el mismo release."""
    limpio = re.sub(r"\D", "", str(upc or ""))
    return limpio.zfill(13) if len(limpio) in (12, 13) else limpio


def upc_valido(upc):
    """Valida largo y dígito verificador de un UPC-A (12) o EAN-13 (13).
    Devuelve (ok, motivo)."""
    if not upc:
        return False, T("val.upc_vacio")
    limpio = re.sub(r"[\s\-]", "", str(upc))
    if not limpio.isdigit():
        return False, T("val.upc_no_digitos")
    if len(limpio) not in (12, 13):
        return False, T("val.upc_largo", n=len(limpio))
    # Todo ceros pasa el dígito verificador y no es el código de nada: es lo
    # que queda en algunos sistemas cuando el campo nunca se cargó.
    if not limpio.strip("0"):
        return False, T("val.upc_ceros")
    esperado = _gtin_check_digit(limpio[:-1])
    if int(limpio[-1]) != esperado:
        return False, T("val.upc_check", tiene=limpio[-1], espera=esperado)
    return True, ""


# ============================================================
# Portadas, dimensiones y espacio de color desde la cabecera
# ============================================================


def medir_imagen(data):
    """Lee (ancho, alto, componentes) de un JPEG o PNG desde sus bytes.

    `componentes` sólo aplica a JPEG: 3 = YCbCr (lo normal), 4 = CMYK (las
    distribuidoras lo rechazan), 1 = escala de grises. Devuelve None si no
    reconoce el formato.
    """
    # Cada formato valida su propio mínimo: PNG necesita 24 bytes para llegar al
    # IHDR, JPEG bastante menos. Un mínimo único para los dos descartaría
    # archivos válidos.
    if not data or len(data) < 4:
        return None

    # PNG: firma de 8 bytes, luego el chunk IHDR con ancho y alto.
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        if len(data) < 24:
            return None
        ancho = int.from_bytes(data[16:20], "big")
        alto = int.from_bytes(data[20:24], "big")
        return ancho, alto, 3

    # JPEG: recorremos los marcadores hasta encontrar un SOF.
    if data[:2] == b"\xff\xd8":
        i = 2
        n = len(data)
        while i < n - 9:
            if data[i] != 0xFF:
                i += 1
                continue
            marcador = data[i + 1]
            # SOF0..SOF15 traen las dimensiones; C4/C8/CC no son SOF.
            if 0xC0 <= marcador <= 0xCF and marcador not in (0xC4, 0xC8, 0xCC):
                alto = int.from_bytes(data[i + 5 : i + 7], "big")
                ancho = int.from_bytes(data[i + 7 : i + 9], "big")
                comps = data[i + 9]
                return ancho, alto, comps
            if marcador in (0xD8, 0x01) or 0xD0 <= marcador <= 0xD7:
                i += 2
                continue
            largo = int.from_bytes(data[i + 2 : i + 4], "big")
            if largo <= 0:
                break
            i += 2 + largo
    return None


def modo_color(data):
    """El modo de color de una portada: "rgb", "cmyk", "gris", "alfa" o "paleta",
    o "" si no se reconoce el formato.

    Para PNG se lee el tipo de color del encabezado, que antes se daba por RGB
    siempre: una portada en escala de grises, con paleta o con transparencia
    pasaba sin aviso, y varias tiendas piden RGB sin transparencia.
    """
    if not data:
        return ""
    if data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) >= 26:
        return {0: "gris", 2: "rgb", 3: "paleta", 4: "alfa", 6: "alfa"}.get(data[25], "")
    medida = medir_imagen(data)
    if not medida:
        return ""
    return {1: "gris", 3: "rgb", 4: "cmyk"}.get(medida[2], "")


def validar_portada(p):
    """Valida la portada de un producto. Devuelve lista de hallazgos."""
    out = []
    nombre = p.get("title", "")
    data = p.get("cover_bytes")

    if not data:
        out.append(
            _hallazgo(
                "aviso",
                "portada_falta",
                T("val.portada_falta", motivo=p.get("cover_status") or T("val.no_se_busco")),
                nombre,
            )
        )
        return out

    medida = medir_imagen(data)
    if not medida:
        out.append(_hallazgo("error", "portada_ilegible", T("val.portada_ilegible"), nombre))
        return out

    ancho, alto, comps = medida

    if ancho != alto:
        out.append(
            _hallazgo(
                "error", "portada_no_cuadrada", T("val.portada_no_cuadrada", ancho=ancho, alto=alto), nombre
            )
        )
    if min(ancho, alto) < COVER_MIN:
        out.append(
            _hallazgo(
                "error",
                "portada_chica",
                T("val.portada_chica", ancho=ancho, alto=alto, min=COVER_MIN),
                nombre,
            )
        )
    elif min(ancho, alto) < COVER_RECOMENDADO:
        out.append(
            _hallazgo(
                "aviso",
                "portada_bajo_recomendado",
                T("val.portada_bajo_recomendado", ancho=ancho, alto=alto, rec=COVER_RECOMENDADO),
                nombre,
            )
        )
    if comps == 4:
        out.append(_hallazgo("error", "portada_cmyk", T("val.portada_cmyk"), nombre))
    modo = modo_color(data)
    if modo in ("gris", "alfa", "paleta"):
        out.append(
            _hallazgo(
                "aviso", "portada_modo_color", T("val.portada_modo_color", modo=T("val.modo_" + modo)), nombre
            )
        )
    return out


# ============================================================
# Validación del catálogo
# ============================================================


def validar(productos: list[Producto], artista="") -> ResultadoValidacion:
    """Valida una selección de productos. Devuelve dict con hallazgos y resumen."""
    out = []
    anio_actual = date.today().year

    # --- por producto ---
    for p in productos:
        nombre = p.get("title", "") or T("val.sin_titulo")

        if not (p.get("title") or "").strip():
            out.append(_hallazgo("error", "producto_sin_titulo", T("val.producto_sin_titulo"), nombre))

        upc = (p.get("upc") or "").strip()
        descartados = sorted({t.get("upc_descartado") or "" for t in p.get("tracks", [])} - {""})
        if not upc and descartados:
            texto = T("val.upc_no_verificado", album=", ".join(descartados))
            out.append(_hallazgo("aviso", "upc_no_verificado", texto, nombre))
        elif not upc:
            out.append(_hallazgo("aviso", "upc_falta", T("val.upc_falta"), nombre))
        else:
            ok, motivo = upc_valido(upc)
            if not ok:
                out.append(
                    _hallazgo("error", "upc_invalido", T("val.upc_invalido", upc=upc, motivo=motivo), nombre)
                )

        # Los tracks de un mismo release tienen que venir del mismo UPC. Si no,
        # Deezer los encontró en releases distintos y el producto se quedó con
        # el más votado, que puede no ser éste.
        upcs_tracks = {re.sub(r"\D", "", t.get("upc") or "") for t in p.get("tracks", [])} - {""}
        if len(upcs_tracks) > 1:
            texto = T("val.upc_mezclado", upcs=", ".join(sorted(upcs_tracks)))
            out.append(_hallazgo("aviso", "upc_mezclado", texto, nombre))

        anio = p.get("release_year")
        if not anio:
            out.append(_hallazgo("aviso", "anio_falta", T("val.anio_falta"), nombre))
        else:
            try:
                a = int(anio)
                if a > anio_actual:
                    out.append(_hallazgo("error", "anio_futuro", T("val.anio_futuro", anio=a), nombre))
                elif a < ANIO_MIN:
                    out.append(_hallazgo("error", "anio_absurdo", T("val.anio_absurdo", anio=a), nombre))
            except (TypeError, ValueError):
                out.append(_hallazgo("error", "anio_invalido", T("val.anio_invalido", anio=anio), nombre))

        if not (p.get("label") or "").strip():
            out.append(_hallazgo("aviso", "sello_falta", T("val.sello_falta"), nombre))

        # Lo que viene de YouTube puede traer una fórmula de planilla. En la
        # hoja de ingesta se le antepone un apóstrofo para que no se ejecute,
        # y eso cambia el dato: hay que decirlo, no hacerlo en silencio.
        for campo in (p.get("title"), p.get("label")):
            if parece_formula(campo):
                out.append(_hallazgo("aviso", "texto_como_formula", T("val.texto_como_formula"), nombre))

        otras = p.get("tambien_en") or []
        if otras:
            texto = T(
                "val.release_en_dos_distribuidoras", otras=", ".join(otras), esta=p.get("distributor", "")
            )
            out.append(_hallazgo("aviso", "release_en_dos_distribuidoras", texto, nombre))

        if tiene_ruido(p.get("title")):
            out.append(_hallazgo("aviso", "titulo_con_ruido", T("val.titulo_con_ruido"), nombre))

        # El audio de referencia no es apto para entregar. El reporte ya lo decía;
        # la validación, que es lo que se mira primero, no lo mencionaba.
        lossy = [
            t
            for t in p.get("tracks", [])
            if t.get("audio_path") and t.get("audio_format") not in FORMATOS_LOSSLESS
        ]
        if lossy:
            out.append(_hallazgo("aviso", "audio_no_apto", T("val.audio_no_apto", n=len(lossy)), nombre))

        if p.get("order_unconfirmed"):
            out.append(_hallazgo("aviso", "orden_sin_confirmar", T("val.orden_sin_confirmar"), nombre))

        # Lo que no se vio en YouTube y se sumó con los datos de Deezer. Se
        # puede entregar, pero antes hay que mirarlo: del release entero no se
        # sabe la distribuidora ni si es del catálogo, y del tema suelto conviene
        # confirmar que sigue siendo parte del disco.
        por_tracklist = sorted({t.get("upc_por_tracklist") or "" for t in p.get("tracks", [])} - {""})
        if upc and por_tracklist:
            texto = T("val.upc_por_tracklist", album=por_tracklist[0])
            out.append(_hallazgo("aviso", "upc_por_tracklist", texto, nombre))
        elif upc and p.get("upc_nivel") == "inferido":
            # El UPC salió de un álbum de Deezer que se llama igual, y nada más
            # lo respalda (ver `evidencia.nivel_upc`). Se exporta como
            # cualquier otro: hay que decir que conviene confirmarlo.
            out.append(_hallazgo("aviso", "upc_inferido", T("val.upc_inferido", upc=upc), nombre))

        # Los ISRC que salieron de un solo camino, juntos: uno por tema eran
        # quince avisos iguales en un disco de remixes.
        inferidos = [t.get("track", "") for t in p.get("tracks", []) if t.get("isrc_nivel") == "inferido"]
        if inferidos:
            texto = T("val.isrc_inferido", n=len(inferidos), temas=lista_corta(inferidos))
            out.append(_hallazgo("aviso", "isrc_inferido", texto, nombre))

        de_deezer = [t.get("track", "") for t in p.get("tracks", []) if t.get("origen") == "deezer"]
        if p.get("origen") == "deezer":
            ajeno = p.get("artist") and artista and comparable(p.get("artist")) != comparable(artista)
            texto = (
                T("val.solo_en_deezer_ajeno", titular=p.get("artist"), artista=artista)
                if ajeno
                else T("val.solo_en_deezer")
            )
            out.append(_hallazgo("aviso", "solo_en_deezer", texto, nombre))
        elif de_deezer:
            texto = T("val.temas_de_deezer", n=len(de_deezer), temas=lista_corta(de_deezer))
            out.append(_hallazgo("aviso", "temas_de_deezer", texto, nombre))

        # Deezer tiene temas de este disco que no aparecieron en YouTube. Es un
        # aviso y no un error: el disco se puede entregar así, pero incompleto,
        # y eso hay que saberlo antes y no cuando la distribuidora lo publique.
        faltan = p.get("faltan_temas") or []
        if faltan:
            texto = T("val.album_incompleto", n=len(faltan), temas=lista_corta(faltan))
            out.append(_hallazgo("aviso", "album_incompleto", texto, nombre))

        out.extend(validar_portada(p))

        # --- por track ---
        for t in p.get("tracks", []):
            titulo = t.get("track", "") or T("val.sin_titulo")

            if not (t.get("track") or "").strip():
                out.append(_hallazgo("error", "track_sin_titulo", T("val.track_sin_titulo"), nombre, titulo))

            isrc = (t.get("isrc") or "").strip()
            candidatos = t.get("isrc_candidatos") or []
            if not isrc and candidatos:
                # No es que falte: hay más de una grabación que puede ser, y
                # no se eligió. Se dice entre cuáles, que es lo que hace falta
                # para resolverlo.
                texto = T("val.isrc_ambiguo", codigos=", ".join(c["isrc"] for c in candidatos[:4]))
                out.append(_hallazgo("aviso", "isrc_ambiguo", texto, nombre, titulo))
            elif not isrc:
                out.append(_hallazgo("aviso", "isrc_falta", T("val.isrc_falta"), nombre, titulo))
            elif not isrc_valido(isrc):
                out.append(
                    _hallazgo("error", "isrc_invalido", T("val.isrc_invalido", isrc=isrc), nombre, titulo)
                )

            dur = int(t.get("duration_s") or 0)
            if dur <= 0:
                out.append(_hallazgo("error", "duracion_falta", T("val.duracion_falta"), nombre, titulo))
            elif dur > DURACION_MAX_SOSPECHOSA:
                out.append(
                    _hallazgo(
                        "aviso", "duracion_larga", T("val.duracion_larga", minutos=dur // 60), nombre, titulo
                    )
                )

            # Si el artista del canal no es el principal del tema, el master
            # puede ser de otro: un feat. en el disco de otro artista, o un
            # compilado. Migrarlo sin preguntar es migrar algo ajeno.
            artistas = t.get("artists") or []
            dueno = p.get("artist") or artista
            if artistas and dueno and comparable(artistas[0]) != comparable(dueno):
                texto = T("val.artista_no_principal", principal=artistas[0], artista=dueno)
                out.append(_hallazgo("aviso", "artista_no_principal", texto, nombre, titulo))

            if parece_formula(t.get("track")):
                out.append(
                    _hallazgo("aviso", "texto_como_formula", T("val.texto_como_formula"), nombre, titulo)
                )

            # Un código que salió de una coincidencia parecida y no idéntica se
            # exporta igual que uno seguro; la validación tiene que decirlo.
            if isrc and t.get("match") == "media":
                texto = T("val.isrc_confianza_media", isrc=isrc)
                out.append(_hallazgo("aviso", "isrc_confianza_media", texto, nombre, titulo))

            if tiene_ruido(titulo):
                out.append(_hallazgo("aviso", "titulo_con_ruido", T("val.titulo_con_ruido"), nombre, titulo))

    out.extend(_duplicados(productos))

    # De dónde salió la fecha, dicho una vez: es un dato de la hoja que no
    # viene de YouTube, y en un catálogo viejo son la mitad de los discos.
    con_fecha_de_deezer = sum(1 for p in productos if p.get("fecha_fuente") == "deezer")
    if con_fecha_de_deezer:
        texto = T("val.fecha_de_deezer", n=con_fecha_de_deezer)
        out.append(_hallazgo("aviso", "fecha_de_deezer", texto, ""))

    # Lo que la hoja no puede traer nunca, dicho una vez para todo el catálogo:
    # sin esto, «sin errores» se leía como «lista para cargar». Si el usuario
    # ya cargó algunos en la app (ver `ediciones`), se nombran los que quedan;
    # y si los cargó todos, no hay nada que avisar.
    if productos:
        pendientes = [
            columna
            for clave, columna in CAMPOS_A_COMPLETAR.items()
            if any(not (p.get("datos") or {}).get(clave) for p in productos)
        ]
        if len(pendientes) == len(CAMPOS_A_COMPLETAR) and not any(p.get("datos") for p in productos):
            out.append(_hallazgo("aviso", "campos_a_completar", T("val.campos_a_completar"), ""))
        elif pendientes:
            texto = T("val.campos_a_completar_parcial", campos=", ".join(pendientes))
            out.append(_hallazgo("aviso", "campos_a_completar", texto, ""))

    errores = [h for h in out if h["nivel"] == "error"]
    avisos = [h for h in out if h["nivel"] == "aviso"]
    return {
        "hallazgos": out,
        "errores": errores,
        "avisos": avisos,
        "apto": not errores,
        "resumen": {
            "productos": len(productos),
            "tracks": sum(len(p.get("tracks", [])) for p in productos),
            "errores": len(errores),
            "avisos": len(avisos),
        },
    }


# Cuánto pueden diferir dos duraciones de la misma grabación. Entre el single y
# el álbum la diferencia suele ser de cero a un par de segundos (un silencio al
# final, un fundido); una versión distinta difiere bastante más.
TOLERANCIA_MISMA_GRABACION = 3
# Hasta dónde dos entregas de la misma grabación pueden diferir por el corte: un
# silencio de más al principio o al final. El cruce de códigos le da a cada
# tema el ISRC de la grabación de Deezer si dura lo mismo con cuatro segundos de
# margen, así que dos temas que recibieron el mismo código pueden diferir hasta
# en ocho entre ellos sin que ninguno de los dos cruces esté mal.
TOLERANCIA_OTRO_CORTE = 8
# Parecido mínimo entre dos títulos para tomarlos por el mismo cuando además
# duran lo mismo: «La Llamada del Amor» y «La Llamada de Amor».
MIN_SIMILITUD_TITULO = 0.9


def _mismo_titulo(a, b, misma_duracion):
    """Si dos títulos nombran el mismo tema.

    Iguales sin acentos ni puntuación, o casi iguales cuando además duran lo
    mismo: una distribuidora escribe «del» donde la otra escribió «de», y eso
    no es otra grabación. Nunca si cambia la versión o un número: «Parte 1» y
    «Parte 2» se parecen más de un noventa por ciento.
    """
    ta, tb = comparable(a), comparable(b)
    if ta == tb:
        return True
    if not misma_duracion or not misma_version(a or "", b or ""):
        return False
    # El mismo tema con un agregado entre paréntesis que no es una versión: en
    # la banda de sonido es «Overture (From "TRON: Legacy"/Score)» y en su
    # edición completa, «Overture».
    if comparable(sin_decorado(a or "")) == comparable(sin_decorado(b or "")):
        return True
    return SequenceMatcher(None, ta, tb).ratio() >= MIN_SIMILITUD_TITULO


def _parentesco(a, b):
    """Qué relación tienen dos tracks que llevan el mismo ISRC.

      - "misma": el mismo título y la misma duración. Es la misma grabación.
      - "otro_corte": el mismo título y unos segundos de diferencia. Casi
        siempre es la misma grabación entregada con otro corte, y a veces una
        regrabación: no se puede saber desde acá, y se avisa.
      - "otra": cambia el título, o la duración por mucho. El código de uno de
        los dos viene de un cruce equivocado.

    Si a alguno le falta la duración se decide por el título, que es lo que hay.
    """
    da, db = int(a.get("duration_s") or 0), int(b.get("duration_s") or 0)
    diferencia = abs(da - db) if (da and db) else 0
    dura_igual = bool(da and db) and diferencia <= TOLERANCIA_MISMA_GRABACION
    if not _mismo_titulo(a.get("track"), b.get("track"), dura_igual):
        return "otra"
    if diferencia <= TOLERANCIA_MISMA_GRABACION:
        return "misma"
    return "otro_corte" if diferencia <= TOLERANCIA_OTRO_CORTE else "otra"


def _duplicados(productos):
    """ISRC repetido entre tracks y UPC repetido entre productos.

    El ISRC identifica una GRABACIÓN, no un lugar en un release, y por eso la
    regla no es la misma adentro de un producto que entre productos:

      - Adentro de un producto, repetido es error: un release no puede traer dos
        veces la misma grabación con el mismo código.
      - Entre productos, la misma grabación con el mismo ISRC es lo correcto. Es
        el single que después entró en el álbum, o el deluxe. Antes esto salía
        como error y el paquete dejaba de ser apto, y la salida obvia para el
        usuario era pedir un código nuevo, que parte el historial de la
        grabación: justo lo que una migración tiene que evitar. Ahora es un
        aviso que dice que se conserve.
      - Entre productos pero con otro título u otra duración, no es la misma
        grabación: el código casi seguro vino de un match equivocado en Deezer.
        Eso sí es error, y es además la red que atrapa un vivo o un remix que se
        quedó con el ISRC de la versión de estudio.

    El UPC identifica un release, así que repetido entre productos es error: la
    distribuidora rechaza la ingesta o, peor, sobrescribe el release equivocado.
    """
    out = []

    vistos_isrc = {}  # isrc -> (producto, track) de la primera aparición
    for p in productos:
        en_este = {}  # isrc -> dónde apareció primero, adentro de este producto
        compartidos = []  # (isrc, dónde estaba, dónde está acá, track)
        for t in p.get("tracks", []):
            isrc = re.sub(r"[\s\-]", "", (t.get("isrc") or "")).upper()
            if not isrc:
                continue
            donde = f"{p.get('title', '')} / {t.get('track', '')}"
            titulo, pista = p.get("title", ""), t.get("track", "")
            if isrc in en_este:
                texto = T("val.isrc_duplicado", isrc=isrc, uno=en_este[isrc], otro=donde)
                out.append(_hallazgo("error", "isrc_duplicado", texto, titulo, pista))
            elif isrc in vistos_isrc:
                p0, t0 = vistos_isrc[isrc]
                uno = f"{p0.get('title', '')} / {t0.get('track', '')}"
                parentesco = _parentesco(t0, t)
                if parentesco == "misma":
                    compartidos.append((isrc, uno, donde, pista))
                elif parentesco == "otro_corte":
                    segundos = abs(int(t0.get("duration_s") or 0) - int(t.get("duration_s") or 0))
                    texto = T("val.isrc_otro_corte", isrc=isrc, uno=uno, otro=donde, n=segundos)
                    out.append(_hallazgo("aviso", "isrc_otro_corte", texto, titulo, pista))
                else:
                    texto = T("val.isrc_match_dudoso", isrc=isrc, uno=uno, otro=donde)
                    out.append(_hallazgo("error", "isrc_match_dudoso", texto, titulo, pista))
            else:
                vistos_isrc[isrc] = (p, t)
            en_este.setdefault(isrc, donde)

        # Un compilado comparte TODOS sus temas con otros discos: un aviso por
        # cada uno eran cien avisos que decían lo mismo y tapaban a los demás.
        if len(compartidos) == 1:
            isrc, uno, donde, pista = compartidos[0]
            texto = T("val.isrc_compartido", isrc=isrc, uno=uno, otro=donde)
            out.append(_hallazgo("aviso", "isrc_compartido", texto, p.get("title", ""), pista))
        elif compartidos:
            temas = lista_corta([pista for _i, _u, _d, pista in compartidos], 5)
            texto = T("val.isrc_compartidos", n=len(compartidos), temas=temas)
            out.append(_hallazgo("aviso", "isrc_compartido", texto, p.get("title", "")))

    vistos_upc = {}
    for p in productos:
        upc = gtin13(p.get("upc"))
        if not upc:
            continue
        if upc in vistos_upc:
            p0 = vistos_upc[upc]
            # Si los dos son el mismo release en dos distribuidoras, el UPC
            # repetido no es un código mal puesto: es que se eligieron los dos.
            # Sigue siendo un error, porque no se puede entregar dos veces el
            # mismo release, pero el arreglo es otro y hay que decirlo.
            mismo = p0.get("distributor") in (p.get("tambien_en") or [])
            clave = "val.upc_duplicado_mismo_release" if mismo else "val.upc_duplicado"
            out.append(
                _hallazgo(
                    "error",
                    "upc_duplicado",
                    T(clave, upc=upc, uno=p0.get("title", ""), otro=p.get("title", "")),
                    p.get("title", ""),
                )
            )
        else:
            vistos_upc[upc] = p

    return out


# ============================================================
# Reporte
# ============================================================


def reporte_validacion(res, artista=""):
    """Reporte de texto de la validación, para incluir en el ZIP."""
    L = [
        T("val.rep_titulo", artista=artista),
        T("val.rep_generado", fecha=date.today().isoformat()),
        "=" * 68,
        "",
    ]
    r = res["resumen"]
    # Los rótulos se alinean con ljust y no con espacios a mano: en inglés miden
    # otra cosa y las dos columnas quedaban torcidas.
    ancho = 20
    L.append(T("val.rep_productos").ljust(ancho) + f": {r['productos']}")
    L.append(T("val.rep_tracks").ljust(ancho) + f": {r['tracks']}")
    L.append(T("val.rep_errores").ljust(ancho) + f": {r['errores']}")
    L.append(T("val.rep_avisos").ljust(ancho) + f": {r['avisos']}")
    L.append("")

    if res["apto"]:
        L.append(T("val.rep_sin_errores"))
        L.append(T("val.rep_sin_errores_2"))
    else:
        L.append(T("val.rep_con_errores_1"))
        L.append(T("val.rep_con_errores_2"))
    L.append("")

    # Lo que esta validación no mira, dicho siempre: es una ayuda, no un
    # certificado, y quien la lee tiene que saber dónde termina.
    L.extend(T("val.rep_no_valida").split("\n"))
    L.append("")

    for nivel, titulo in (("error", T("val.rep_h_errores")), ("aviso", T("val.rep_h_avisos"))):
        grupo = [h for h in res["hallazgos"] if h["nivel"] == nivel]
        if not grupo:
            continue
        L.append(titulo)
        L.append("-" * 68)
        por_producto = {}
        for h in grupo:
            por_producto.setdefault(h["producto"] or T("val.rep_catalogo"), []).append(h)
        for prod, hs in por_producto.items():
            L.append(f"  {prod}")
            for h in hs:
                donde = f" [{h['track']}]" if h["track"] else ""
                L.append(f"      - {h['mensaje']}{donde}")
        L.append("")

    return "\n".join(L) + "\n"
