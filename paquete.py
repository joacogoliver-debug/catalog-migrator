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
import re
import unicodedata
import zipfile
from datetime import date

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from audio import FORMATOS_LOSSLESS
from i18n import T

NAVY = "1F3864"
GRIS = "F2F2F2"
AMBAR = "FFF2CC"


def _slug_archivo(s, maxlen=80):
    """Nombre de archivo seguro en Windows/macOS/Linux."""
    s = unicodedata.normalize("NFD", s or "").encode("ascii", "ignore").decode("ascii")
    s = re.sub(r'[<>:"/\\|?*]', "", s)
    s = re.sub(r"[\x00-\x1f]", "", s)
    s = re.sub(r"\s+", " ", s).strip(" .")
    return (s[:maxlen].strip(" .") or "sin-titulo")


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
        (T("paq.col_producto"), 34), (T("paq.col_tipo"), 8), (T("paq.col_anio"), 6), ("UPC", 15),
        ("#", 4), (T("paq.col_track"), 34), ("ISRC", 14),
        (T("paq.col_duracion"), 9), (T("paq.col_sello"), 22), (T("paq.col_distribuidora"), 22),
        (T("paq.col_fuente"), 26), (T("paq.col_archivo"), 30), (T("paq.col_reproducciones"), 14),
        (T("paq.col_url"), 30),
    ]


def _encabezado(ws, titulo, subtitulo=""):
    ws["A1"] = titulo
    ws["A1"].font = Font(size=14, bold=True, color=NAVY)
    if subtitulo:
        ws["A2"] = subtitulo
        ws["A2"].font = Font(size=9, color="666666")
    fila = 4
    for i, (nombre, ancho) in enumerate(columnas(), 1):
        c = ws.cell(row=fila, column=i, value=nombre)
        c.font = Font(size=10, bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor=NAVY)
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        ws.column_dimensions[get_column_letter(i)].width = ancho
    ws.freeze_panes = f"A{fila + 1}"
    return fila + 1


def _mmss(seg):
    seg = int(seg or 0)
    return f"{seg // 60}:{seg % 60:02d}"


def _filas_producto(ws, fila, p, con_archivo=True):
    for t in p["tracks"]:
        fuente = _fuente_corta(t)
        valores = [
            p["title"], p["kind"], p.get("release_year", ""), p.get("upc", ""),
            t.get("track_number", ""), t.get("track", ""), t.get("isrc", ""),
            _mmss(t.get("duration_s")), p.get("label", ""), p.get("distributor", ""),
            fuente,
            os.path.basename(t["audio_path"]) if (con_archivo and t.get("audio_path")) else "",
            t.get("views", 0), t.get("url", ""),
        ]
        for i, v in enumerate(valores, 1):
            c = ws.cell(row=fila, column=i, value=v)
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


def planilla_maestra_bytes(productos, artista):
    """Excel con todo el catálogo seleccionado."""
    from io import BytesIO
    wb = Workbook()
    ws = wb.active
    ws.title = T("paq.hoja_catalogo")
    fila = _encabezado(
        ws, T("paq.maestra_titulo", artista=artista),
        T("paq.maestra_sub", fecha=date.today().isoformat(), productos=len(productos),
          tracks=sum(p["track_count"] for p in productos)),
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
    "UPC", "Release Title", "Release Artist", "Release Type", "Release Date",
    "Label", "P Line", "C Line", "Genre", "Language", "Territories",
    # --- nivel track ---
    "Disc Number", "Track Number", "ISRC", "Track Title", "Track Artist",
    "Duration", "Explicit", "Composer", "Publisher", "Lyrics Language",
    # --- referencia interna ---
    "Audio File", "Cover File", "Source Quality", "YouTube URL",
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
            w.writerow([
                p.get("upc") or MARCA_COMPLETAR,
                p.get("title", ""),
                artista,
                p.get("kind", ""),
                p.get("release_date") or (f"{anio}-01-01" if anio else MARCA_COMPLETAR),
                sello,
                p_line,
                MARCA_COMPLETAR,            # C Line: no sale de YouTube
                MARCA_COMPLETAR,            # Genre
                MARCA_COMPLETAR,            # Language
                "Worldwide",
                t.get("tidal", {}).get("volume_number") if t.get("tidal") else 1,
                t.get("track_number") or "",
                t.get("isrc") or MARCA_COMPLETAR,
                t.get("track", ""),
                artista,
                _mmss(t.get("duration_s")),
                MARCA_COMPLETAR,            # Explicit
                MARCA_COMPLETAR,            # Composer
                MARCA_COMPLETAR,            # Publisher
                MARCA_COMPLETAR,            # Lyrics Language
                os.path.basename(t["audio_path"]) if t.get("audio_path") else "",
                "portada.jpg" if p.get("cover_bytes") else "",
                _fuente_corta(t),
                t.get("url", ""),
            ])
    return buf.getvalue()


def planilla_producto_bytes(p, artista):
    """Excel de un solo producto, para que viaje dentro de su carpeta."""
    from io import BytesIO
    wb = Workbook()
    ws = wb.active
    ws.title = T("paq.hoja_producto")
    fila = _encabezado(
        ws, f"{artista}: {p['title']}",
        T("paq.producto_sub",
          tipo=p["kind"].upper(),
          anio=p.get("release_year") or T("paq.sin_fecha"),
          upc=p.get("upc") or T("paq.sin_upc_par"),
          tracks=p["track_count"]),
    )
    _filas_producto(ws, fila, p)
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ============================================================
# Reporte y leeme
# ============================================================

def reporte_texto(productos, artista, entorno=None, con_tidal=False):
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
    L.append(("  " + T("paq.rep_con_isrc")).ljust(a1)
             + f": {sum(1 for t in tracks if t.get('isrc'))}")
    L.append(T("paq.rep_con_upc").ljust(a1)
             + f": {sum(1 for p in productos if p.get('upc'))}")
    L.append(T("paq.rep_portadas").ljust(a1)
             + f": {sum(1 for p in productos if p.get('cover_bytes'))}/{len(productos)}")
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
            faltas.append(T("paq.falta_portada",
                            motivo=p.get("cover_status") or T("paq.no_buscada")))
        sin = [t for t in p["tracks"] if not t.get("audio_path")]
        if sin:
            faltas.append(T("paq.falta_audio", n=len(sin), total=p["track_count"]))
            # El motivo concreto por track: sirve para saber si hay que buscar
            # otra fuente o si el video simplemente ya no está.
            for t in sin:
                if t.get("audio_error"):
                    faltas.append(f"     {t.get('track', '')[:40]}: {t['audio_error']}")
        lossy = [t for t in p["tracks"]
                 if t.get("audio_path") and (t.get("audio_format") or "") not in FORMATOS_LOSSLESS]
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
        L.append(f"  ffmpeg: {si if entorno.get('ffmpeg') else no}, "
                 f"tiddl: {si if entorno.get('tiddl') else no}, "
                 f"yt-dlp: {si if entorno.get('yt_dlp') else no}")
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

def build_zip(productos, artista, out_path, entorno=None, con_tidal=False,
              incluir_planilla=True, incluir_audio=True, incluir_portadas=True,
              log=print):
    """Arma el ZIP del entregable en `out_path`. Devuelve (ruta, bytes).

    Se escribe directo a disco porque un catálogo en FLAC son varios GB.
    """
    F = nombres_archivos()
    raiz = f"{_slug_archivo(artista)} - {T('paq.carpeta_raiz')} {date.today().isoformat()}"
    # ZIP_STORED para el audio: FLAC y Opus ya están comprimidos, deflate
    # gastaría CPU sin ganar espacio. Sí comprimimos planillas y texto.
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as z:
        # Los .txt van con BOM (utf-8-sig): los abre gente en Windows y sin BOM
        # algunos editores viejos muestran los acentos rotos.
        z.writestr(f"{raiz}/{F['leeme']}", leeme().encode("utf-8-sig"))
        z.writestr(f"{raiz}/{F['reporte']}",
                   reporte_texto(productos, artista, entorno, con_tidal).encode("utf-8-sig"))

        # La validación va siempre: es lo que evita que la entrega se rechace.
        import validar as V
        res_val = V.validar(productos, artista)
        z.writestr(f"{raiz}/{F['validacion']}",
                   V.reporte_validacion(res_val, artista).encode("utf-8-sig"))

        if incluir_planilla:
            z.writestr(f"{raiz}/{F['catalogo']}",
                       planilla_maestra_bytes(productos, artista))
            # CSV de ingesta: es el archivo que se carga en la distribuidora.
            z.writestr(f"{raiz}/{F['ingesta']}",
                       hoja_ingesta_csv(productos, artista).encode("utf-8-sig"))

        for p in productos:
            carpeta = f"{raiz}/{p['folder']}"
            if incluir_planilla:
                z.writestr(f"{carpeta}/{T('paq.f_datos')}", planilla_producto_bytes(p, artista))
            if incluir_portadas and p.get("cover_bytes"):
                z.writestr(f"{carpeta}/{T('paq.f_portada')}", p["cover_bytes"])

            if incluir_audio:
                for t in p["tracks"]:
                    ruta = t.get("audio_path")
                    if not ruta or not os.path.exists(ruta):
                        continue
                    n = t.get("track_number") or 0
                    ext = t.get("audio_format") or os.path.splitext(ruta)[1]
                    nombre = f"{n:02d} - {_slug_archivo(t.get('track'))}{ext}"
                    # Los lossy van marcados en el nombre del archivo: es la
                    # última barrera para que no se entreguen por error.
                    if t.get("audio_format") not in FORMATOS_LOSSLESS:
                        marca = T("paq.tag_lossy")
                        nombre = f"{n:02d} - {_slug_archivo(t.get('track'))} {marca}{ext}"
                    z.write(ruta, f"{carpeta}/{nombre}", compress_type=zipfile.ZIP_STORED)
            log(T("paq.log_carpeta", carpeta=p["folder"]))

    tam = os.path.getsize(out_path)
    log(T("paq.log_zip_listo", mb=f"{tam / 1e6:.1f}"))
    return out_path, tam
