"""
Armado del entregable: un ZIP organizado por producto, listo para entregar a la
distribuidora nueva.

Estructura:

    Artista - Migracion 2026-08-13/
    ├── _LEEME.txt                     ← qué es esto y cómo está organizado
    ├── _Catalogo completo.xlsx        ← planilla maestra de todos los productos
    ├── _Reporte de migracion.txt      ← qué salió, qué faltó y por qué
    ├── 2019 - Nombre del Album [UPC]/
    │   ├── portada.jpg
    │   ├── datos.xlsx                 ← sólo este producto, con ISRCs
    │   ├── 01 - Primer Tema.flac
    │   └── 02 - Segundo Tema.flac
    └── 2021 - Nombre del Single [UPC]/
        └── ...

Por qué por producto y no por tipo de archivo: en una migración cada producto se
entrega como una unidad (un UPC, una portada, sus audios). Así cada carpeta ya
queda lista para subir, sin tener que cruzar tres carpetas distintas para armar
un release. El UPC en el nombre evita confundir un álbum con su reedición.

El ZIP se escribe a disco y no en memoria: un catálogo mediano en FLAC son
varios GB y no entra en RAM.
"""

import os
import zipfile
from datetime import date

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

# De contratos y no de audio: armar el entregable es el núcleo, y el módulo
# de audio es opcional. Atarlos significaba que un import mal puesto en
# audio.py rompiera la variante esencial, que ni siquiera lo usa.
from .contratos import FORMATOS_LOSSLESS, Producto
from .i18n import T
from .texto import mmss as _mmss
from .texto import nombre_seguro, parece_formula

NAVY = "1F3864"
GRIS = "F2F2F2"
AMBAR = "FFF2CC"


def _slug_archivo(s, maxlen=80):
    """Nombre de archivo seguro. Ochenta caracteres: va adentro de la carpeta
    del producto, que ya se comió parte del largo máximo de la ruta."""
    return nombre_seguro(s, maxlen, "sin-titulo")


def _fuente_corta(t):
    """Etiqueta corta de fuente/calidad para la planilla.

    LOSSLESS y LOSSY no se traducen: son la marca que mira quien revisa la
    entrega, y conviene que diga lo mismo en los dos idiomas.
    """
    if not t.get("audio_path"):
        return T("paq.sin_audio")
    fmt = (t.get("audio_format") or "").lstrip(".")
    return f"{'LOSSLESS' if t.get('audio_format') in FORMATOS_LOSSLESS else 'LOSSY'} ({fmt})"


# ============================================================
# Planillas
# ============================================================


# Las columnas de las planillas SÍ se traducen: las lee el usuario. Las de la
# hoja de ingesta no, y por eso están aparte (ver COLUMNAS_INGESTA).
#
# Es una función y no una constante porque el idioma se elige en caliente: una
# lista armada al importar el módulo quedaría en el idioma que hubiera al
# arrancar y no cambiaría más.
def columnas():
    return [
        (T("paq.col_producto"), 34),
        (T("paq.col_tipo"), 8),
        (T("paq.col_anio"), 6),
        ("UPC", 15),
        ("#", 4),
        (T("paq.col_track"), 34),
        ("ISRC", 14),
        (T("paq.col_duracion"), 9),
        (T("paq.col_sello"), 22),
        (T("paq.col_distribuidora"), 22),
        (T("paq.col_fuente"), 26),
        (T("paq.col_archivo"), 30),
        (T("paq.col_reproducciones"), 14),
        (T("paq.col_url"), 30),
    ]


# ============================================================
# Texto que viene de afuera, que no se ejecuta
# ============================================================
#
# Los títulos, el artista y el sello los escribe quien subió el catálogo a
# YouTube. openpyxl guarda como FÓRMULA cualquier texto que empiece con `=`, así
# que un título `=HYPERLINK("https://…?x="&A2,"Ver")` llegaba vivo a la
# planilla y se ejecutaba al abrirla. En el xlsx alcanza con marcar la celda
# como texto: se ve igual y no se evalúa.
#
# En el CSV no hay tipos, y un programa de planillas evalúa lo que empieza con
# `=`, `+`, `-` o `@`. Ahí sí hay que tocar el dato, con el apóstrofo que esos
# programas entienden como «esto es texto». Pero sólo cuando parece una
# fórmula (lleva un paréntesis, una barra o un signo de exclamación, que es lo
# que necesita una llamada o un enlace DDE): hay discos que se llaman «+», «=»
# o «-Intro-», y el nombre de un release no se altera por las dudas.


def _texto_csv(v):
    return "'" + v if parece_formula(v) else v


def _celda(ws, fila, col, valor):
    """Escribe una celda. Un texto nunca queda como fórmula."""
    c = ws.cell(row=fila, column=col, value=valor)
    if isinstance(valor, str) and c.data_type == "f":
        c.data_type = "s"
    return c


def _encabezado(ws, titulo, subtitulo=""):
    _celda(ws, 1, 1, titulo).font = Font(size=14, bold=True, color=NAVY)
    if subtitulo:
        _celda(ws, 2, 1, subtitulo).font = Font(size=9, color="666666")
    fila = 4
    for i, (nombre, ancho) in enumerate(columnas(), 1):
        c = ws.cell(row=fila, column=i, value=nombre)
        c.font = Font(size=10, bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor=NAVY)
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        ws.column_dimensions[get_column_letter(i)].width = ancho
    ws.freeze_panes = f"A{fila + 1}"
    return fila + 1


def _filas_producto(ws, fila, p, con_archivo=True):
    for t in p["tracks"]:
        fuente = _fuente_corta(t)
        valores = [
            p["title"],
            p["kind"],
            p.get("release_year", ""),
            p.get("upc", ""),
            t.get("track_number", ""),
            t.get("track", ""),
            t.get("isrc", ""),
            _mmss(t.get("duration_s")),
            p.get("label", ""),
            p.get("distributor", ""),
            fuente,
            os.path.basename(t["audio_path"]) if (con_archivo and t.get("audio_path")) else "",
            t.get("views", 0),
            t.get("url", ""),
        ]
        for i, v in enumerate(valores, 1):
            c = _celda(ws, fila, i, v)
            c.alignment = Alignment(vertical="center")
            # Resaltamos en ámbar lo que NO es apto para entrega, para que no se
            # cuele un lossy en una entrega por distracción.
            #
            # Se mira si hay archivo y no el texto de la etiqueta: comparar
            # contra "sin audio" dejaba de funcionar con la app en inglés.
            hay_audio = bool(t.get("audio_path"))
            if i == 11 and hay_audio and not fuente.startswith("LOSSLESS"):
                c.fill = PatternFill("solid", fgColor=AMBAR)
            if i == 11 and not hay_audio:
                c.font = Font(size=10, color="C00000")
        fila += 1
    return fila


def _hoja(wb):
    """La hoja activa de un libro recién creado.

    openpyxl declara `Workbook.active` como opcional, y el código de acá la
    usaba sin mirar. Un libro nuevo siempre la trae, así que esto no cambia
    nada en la práctica; lo que cambia es que el día que no la traiga se vea
    acá y no como un AttributeError a mitad de armar el ZIP.
    """
    ws = wb.active
    if ws is None:
        raise RuntimeError("el libro de Excel salió sin hoja activa")
    return ws


def planilla_maestra_bytes(productos: list[Producto], artista):
    """Excel con todo el catálogo seleccionado."""
    from io import BytesIO

    wb = Workbook()
    ws = _hoja(wb)
    ws.title = T("paq.hoja_catalogo")
    fila = _encabezado(
        ws,
        T("paq.maestra_titulo", artista=artista),
        T(
            "paq.maestra_sub",
            fecha=date.today().isoformat(),
            productos=len(productos),
            tracks=sum(p["track_count"] for p in productos),
        ),
    )
    for p in productos:
        fila = _filas_producto(ws, fila, p)
    ws.auto_filter.ref = f"A4:{get_column_letter(len(columnas()))}{fila - 1}"

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ============================================================
# Hoja de ingesta, CSV para cargar en la distribuidora nueva
# ============================================================
#
# Las distribuidoras ingestan por planilla propia o por DDEX ERN. DDEX quedó
# afuera a propósito: emitir ERN válido requiere ser parte registrada de DDEX con
# un DPID propio, así que un XML "casi DDEX" sería peor que no darlo (se rechaza
# igual y da falsa sensación de que está listo). En su lugar damos un CSV con las
# columnas estándar que aceptan o mapean casi todas, y marcamos explícitamente lo
# que sólo puede completar el dueño del catálogo.

MARCA_COMPLETAR = "<<COMPLETAR>>"

COLUMNAS_INGESTA = [
    # --- nivel release ---
    "UPC",
    "Release Title",
    "Release Artist",
    "Release Type",
    "Release Date",
    "Label",
    "P Line",
    "C Line",
    "Genre",
    "Language",
    "Territories",
    # --- nivel track ---
    "Disc Number",
    "Track Number",
    "ISRC",
    "Track Title",
    "Track Artist",
    "Duration",
    "Explicit",
    "Composer",
    "Publisher",
    "Lyrics Language",
    # --- referencia interna ---
    "Audio File",
    "Cover File",
    "Source Quality",
    "YouTube URL",
]


def hoja_ingesta_csv(productos, artista):
    """CSV con las columnas estándar de ingesta, una fila por track.

    Lo que sabemos va completo; lo que no puede salir de YouTube ni de las APIs
    públicas (género, explicit, compositores, editoriales) queda marcado con
    <<COMPLETAR>> en vez de vacío o inventado, así se ve de una qué falta.
    """
    import csv
    from io import StringIO

    buf = StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(COLUMNAS_INGESTA)

    for p in productos:
        anio = p.get("release_year") or ""
        sello = p.get("label") or MARCA_COMPLETAR
        # La línea ℗ se arma con lo que trae YouTube; si falta el año no la
        # inventamos.
        p_line = f"{anio} {sello}".strip() if anio and p.get("label") else MARCA_COMPLETAR
        for t in p["tracks"]:
            # Cada campo pasa por `_texto_csv`: ver la nota sobre las fórmulas.
            w.writerow(
                [
                    _texto_csv(v)
                    for v in [
                        p.get("upc") or MARCA_COMPLETAR,
                        p.get("title", ""),
                        artista,
                        p.get("kind", ""),
                        p.get("release_date") or (f"{anio}-01-01" if anio else MARCA_COMPLETAR),
                        sello,
                        p_line,
                        MARCA_COMPLETAR,  # C Line: no sale de YouTube
                        MARCA_COMPLETAR,  # Genre
                        MARCA_COMPLETAR,  # Language
                        "Worldwide",
                        t.get("tidal", {}).get("volume_number") if t.get("tidal") else 1,
                        t.get("track_number") or "",
                        t.get("isrc") or MARCA_COMPLETAR,
                        t.get("track", ""),
                        artista,
                        _mmss(t.get("duration_s")),
                        MARCA_COMPLETAR,  # Explicit
                        MARCA_COMPLETAR,  # Composer
                        MARCA_COMPLETAR,  # Publisher
                        MARCA_COMPLETAR,  # Lyrics Language
                        os.path.basename(t["audio_path"]) if t.get("audio_path") else "",
                        "portada.jpg" if p.get("cover_bytes") else "",
                        _fuente_corta(t),
                        t.get("url", ""),
                    ]
                ]
            )
    return buf.getvalue()


def planilla_producto_bytes(p, artista):
    """Excel de un solo producto, para que viaje dentro de su carpeta."""
    from io import BytesIO

    wb = Workbook()
    ws = _hoja(wb)
    ws.title = T("paq.hoja_producto")
    fila = _encabezado(
        ws,
        f"{artista}: {p['title']}",
        T(
            "paq.producto_sub",
            tipo=p["kind"].upper(),
            anio=p.get("release_year") or T("paq.sin_fecha"),
            upc=p.get("upc") or T("paq.sin_upc_par"),
            tracks=p["track_count"],
        ),
    )
    _filas_producto(ws, fila, p)
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ============================================================
# Reporte y leeme
# ============================================================


def reporte_texto(productos: list[Producto], artista, entorno=None, con_tidal=False):
    """Reporte honesto de qué se pudo migrar y qué no. Es la pieza que evita
    sorpresas: dice producto por producto qué falta y por qué."""
    L = []
    tracks = [t for p in productos for t in p["tracks"]]
    aptos = [t for t in tracks if (t.get("audio_format") or "") in FORMATOS_LOSSLESS]
    ref = [t for t in tracks if t.get("audio_path") and t not in aptos]
    sin_audio = [t for t in tracks if not t.get("audio_path")]

    # Los rótulos se alinean con ljust: escritos con espacios a mano quedaban
    # torcidos en cuanto el idioma cambiaba el largo de la palabra.
    a1, a2 = 24, 36
    L.append(T("paq.rep_titulo", artista=artista))
    L.append(T("paq.rep_generado", fecha=date.today().isoformat()))
    L.append("=" * 68)
    L.append("")
    L.append(T("paq.rep_productos").ljust(a1) + f": {len(productos)}")
    L.append(T("paq.rep_tracks").ljust(a1) + f": {len(tracks)}")
    L.append(("  " + T("paq.rep_con_isrc")).ljust(a1) + f": {sum(1 for t in tracks if t.get('isrc'))}")
    L.append(T("paq.rep_con_upc").ljust(a1) + f": {sum(1 for p in productos if p.get('upc'))}")
    L.append(
        T("paq.rep_portadas").ljust(a1)
        + f": {sum(1 for p in productos if p.get('cover_bytes'))}/{len(productos)}"
    )
    L.append("")
    L.append(T("paq.rep_audio"))
    L.append(("  " + T("paq.rep_aptos")).ljust(a2) + f": {len(aptos)}")
    L.append(("  " + T("paq.rep_referencia")).ljust(a2) + f": {len(ref)}")
    L.append(("  " + T("paq.rep_sin_audio")).ljust(a2) + f": {len(sin_audio)}")
    L.append("")

    if not con_tidal:
        L.extend(T("paq.rep_sin_tidal").split("\n"))
        L.append("")
    elif ref:
        L.extend(T("paq.rep_algunos_aac").split("\n"))
        L.append("")

    L.append(T("paq.rep_pendientes"))
    L.append("-" * 68)
    hay_pendientes = False
    for p in productos:
        faltas = []
        if not p.get("upc"):
            faltas.append(T("paq.falta_upc"))
        if not p.get("cover_bytes"):
            faltas.append(T("paq.falta_portada", motivo=p.get("cover_status") or T("paq.no_buscada")))
        sin = [t for t in p["tracks"] if not t.get("audio_path")]
        if sin:
            faltas.append(T("paq.falta_audio", n=len(sin), total=p["track_count"]))
            # El motivo concreto por track: sirve para saber si hay que buscar
            # otra fuente o si el video simplemente ya no está.
            for t in sin:
                error = t.get("audio_error")
                if error:
                    faltas.append(f"     {t.get('track', '')[:40]}: {error}")
        lossy = [
            t
            for t in p["tracks"]
            if t.get("audio_path") and (t.get("audio_format") or "") not in FORMATOS_LOSSLESS
        ]
        if lossy:
            faltas.append(T("paq.falta_lossy", n=len(lossy)))
        sin_isrc = [t for t in p["tracks"] if not t.get("isrc")]
        if sin_isrc:
            faltas.append(T("paq.falta_isrc", n=len(sin_isrc)))
        if p.get("order_unconfirmed"):
            faltas.append(T("paq.falta_orden"))
        if faltas:
            hay_pendientes = True
            L.append(f"  {p['folder']}")
            for f in faltas:
                L.append(f"      - {f}")
    if not hay_pendientes:
        L.append("  " + T("paq.rep_sin_pendientes"))

    if entorno:
        si, no = T("paq.si"), T("paq.no")
        L.append("")
        L.append(T("paq.rep_entorno"))
        L.append(
            f"  ffmpeg: {si if entorno.get('ffmpeg') else no}, "
            f"tiddl: {si if entorno.get('tiddl') else no}, "
            f"yt-dlp: {si if entorno.get('yt_dlp') else no}"
        )
    return "\n".join(L) + "\n"


def nombres_archivos():
    """Los nombres de los cinco archivos de la raíz del ZIP, en el idioma elegido.

    Siguen al idioma, igual que el resto: quien baja el paquete en inglés espera
    abrirlo en inglés. El guion bajo del principio no es decorativo, los deja
    arriba de las carpetas al ordenar por nombre, y eso vale en los dos.

    Son una función y no constantes por lo mismo que `columnas()`: el idioma se
    elige en caliente.
    """
    return {
        "leeme": T("paq.f_leeme"),
        "reporte": T("paq.f_reporte"),
        "validacion": T("paq.f_validacion"),
        "catalogo": T("paq.f_catalogo"),
        "ingesta": T("paq.f_ingesta"),
    }


def leeme():
    """El _LEEME.txt del ZIP. El texto vive en `i18n.py`, en los dos idiomas."""
    return T("paq.leeme", **{k: v for k, v in nombres_archivos().items()})


# ============================================================
# ZIP
# ============================================================

# El largo máximo de una ruta adentro del ZIP. Windows no abre rutas de más de
# 260 caracteres, y «Extraer todo» del Explorador descomprime en
# `C:\Users\<usuario>\Downloads\<nombre del zip>\`, que ya se come unos
# sesenta. El peor caso medido antes de este tope pasaba los 290 adentro del
# ZIP, y fallaba recién al descomprimir, en la máquina de quien recibe la
# entrega. Lo que se recorta es el título del archivo de audio: la carpeta raíz
# y la del producto tienen su propio tope, y el número de track y la marca de
# lossy no se tocan nunca.
LARGO_MAX_RUTA = 200
LARGO_ARTISTA_RAIZ = 40


def carpeta_raiz(artista):
    """La carpeta que envuelve todo el paquete."""
    fecha = date.today().isoformat()
    return f"{_slug_archivo(artista, LARGO_ARTISTA_RAIZ)} - {T('paq.carpeta_raiz')} {fecha}"


def nombre_audio(t, lugar=110):
    """El nombre del archivo de audio de un track adentro de su carpeta.

    `lugar` es cuántos caracteres le quedan al nombre entero dentro del
    presupuesto de la ruta. Los lossy van marcados en el nombre: es la última
    barrera para que no se entreguen por error.
    """
    n = t.get("track_number") or 0
    ext = t.get("audio_format") or os.path.splitext(t.get("audio_path") or "")[1]
    marca = "" if t.get("audio_format") in FORMATOS_LOSSLESS else " " + T("paq.tag_lossy")
    prefijo = f"{n:02d} - "
    largo = max(12, min(80, lugar - len(prefijo) - len(marca) - len(ext)))
    return f"{prefijo}{_slug_archivo(t.get('track'), largo)}{marca}{ext}"


def entrada_zip(*partes):
    """El nombre de una entrada del ZIP, controlado.

    Cada parte ya sale de un nombre saneado; esto es la segunda puerta. Si
    alguna trae una barra o es `..`, el paquete no se arma: preferimos un error
    acá antes que un ZIP que escriba fuera de su carpeta al descomprimirse.
    """
    for parte in partes:
        if parte in ("", ".", "..") or "/" in parte or "\\" in parte:
            raise ValueError(f"nombre de entrada inseguro en el ZIP: {parte!r}")
    return "/".join(partes)


def build_zip(
    productos: list[Producto],
    artista,
    out_path,
    entorno=None,
    con_tidal=False,
    incluir_planilla=True,
    incluir_audio=True,
    incluir_portadas=True,
    log=print,
):
    """Arma el ZIP del entregable en `out_path`. Devuelve (ruta, bytes).

    Se escribe directo a disco porque un catálogo en FLAC son varios GB.
    """
    F = nombres_archivos()
    raiz = carpeta_raiz(artista)
    # ZIP_STORED para el audio: FLAC y Opus ya están comprimidos, deflate
    # gastaría CPU sin ganar espacio. Sí comprimimos planillas y texto.
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as z:
        # Los .txt van con BOM (utf-8-sig): los abre gente en Windows y sin BOM
        # algunos editores viejos muestran los acentos rotos.
        z.writestr(entrada_zip(raiz, F["leeme"]), leeme().encode("utf-8-sig"))
        z.writestr(
            entrada_zip(raiz, F["reporte"]),
            reporte_texto(productos, artista, entorno, con_tidal).encode("utf-8-sig"),
        )

        # La validación va siempre: es lo que evita que la entrega se rechace.
        from . import validar as V

        res_val = V.validar(productos, artista)
        z.writestr(
            entrada_zip(raiz, F["validacion"]), V.reporte_validacion(res_val, artista).encode("utf-8-sig")
        )

        if incluir_planilla:
            z.writestr(entrada_zip(raiz, F["catalogo"]), planilla_maestra_bytes(productos, artista))
            # CSV de ingesta: es el archivo que se carga en la distribuidora.
            z.writestr(
                entrada_zip(raiz, F["ingesta"]), hoja_ingesta_csv(productos, artista).encode("utf-8-sig")
            )

        for p in productos:
            carpeta = p["folder"]
            if incluir_planilla:
                z.writestr(entrada_zip(raiz, carpeta, T("paq.f_datos")), planilla_producto_bytes(p, artista))
            portada = p.get("cover_bytes")
            if incluir_portadas and portada:
                z.writestr(entrada_zip(raiz, carpeta, T("paq.f_portada")), portada)

            if incluir_audio:
                lugar = LARGO_MAX_RUTA - len(raiz) - len(carpeta) - 2
                for t in p["tracks"]:
                    ruta = t.get("audio_path")
                    if not ruta or not os.path.exists(ruta):
                        continue
                    nombre = entrada_zip(raiz, carpeta, nombre_audio(t, lugar))
                    z.write(ruta, nombre, compress_type=zipfile.ZIP_STORED)
            log(T("paq.log_carpeta", carpeta=p["folder"]))

    tam = os.path.getsize(out_path)
    log(T("paq.log_zip_listo", mb=f"{tam / 1e6:.1f}"))
    return out_path, tam
