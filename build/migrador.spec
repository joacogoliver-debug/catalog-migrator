# -*- mode: python ; coding: utf-8 -*-
"""
Receta de PyInstaller para el Migrador de Catálogos.

Se arma con:
    pyinstaller build/migrador.spec --noconfirm

Notas de por qué está así:

- `onefile`: un solo ejecutable es lo más simple de distribuir y de explicar.
  Arranca un poco más lento que `onedir` porque se descomprime en un temporal,
  pero para una app que después hace pedidos de red no se nota.

- `console=False`: sin ventana de terminal detrás, que es lo que hace que se
  sienta un programa y no un script. A cambio, un error de arranque sería
  invisible, así que el launcher escribe el traceback en
  ~/.migrador-catalogos/error.log.

- El motor es el paquete `migrador`, que vive en `src/`, y la app de escritorio
  está en `app/`. Las dos carpetas van a `pathex`, con `src` primero: si quedara
  una carpeta llamada `migrador` en otro lado del path, Python la tomaría como
  paquete de espacio de nombres y se empaquetaría eso en vez de esto.

- `tiddl` y `yt_dlp` entran sólo en la variante completa. La esencial sale más
  liviana y sin un descargador de audio adentro.

El nombre del archivo es siempre el mismo. El CI lo renombra con la plataforma y
la variante, así el spec no tiene que saber nada de cómo se publica.
"""

import os
import re
import sys

RAIZ = os.path.abspath(os.getcwd())
APP = os.path.join(RAIZ, "app")
SRC = os.path.join(RAIZ, "src")

# La versión, del único lugar donde está escrita. Se lee con una expresión
# regular y no importando el módulo: el spec corre adentro de PyInstaller, con
# un sys.path que no es el del proyecto.
with open(os.path.join(SRC, "migrador", "version.py"), encoding="utf-8") as _f:
    VERSION = re.search(r'^VERSION\s*=\s*"([^"]+)"', _f.read(), re.M).group(1)

# Cada sistema pide su formato. Si por algo faltara el archivo, se compila sin
# icono en vez de abortar el build: un binario sin icono sirve igual.
_assets = os.path.join(APP, "web", "assets")
_ico = os.path.join(_assets, "icono.ico")
_icns = os.path.join(_assets, "icono.icns")
ICONO = _ico if os.path.exists(_ico) else None
ICONO_MAC = _icns if os.path.exists(_icns) else ICONO

# Build CON el módulo de audio adentro: `python build/build.py --con-audio`.
# Suma unos 14 MB y mete un descargador de audio dentro del ejecutable. Igual
# necesita ffmpeg, que se empaqueta aparte más abajo.
CON_AUDIO = os.environ.get("MIGRADOR_BUILD_AUDIO", "") == "1"

# Build con una clave de YouTube adentro (`--con-clave`). La clave NUNCA está en
# el repositorio: build.py la toma de la variable MIGRADOR_CLAVE_YT, que en el CI
# es un secreto, y deja el archivo listo justo antes de empaquetar.
CLAVE = []
if os.environ.get("MIGRADOR_BUILD_CLAVE", "") == "1":
    _cl = os.path.join(RAIZ, "build", "terceros", "clave_yt.dat")
    if os.path.exists(_cl):
        CLAVE = [(_cl, ".")]
        print("[spec] clave de YouTube incluida en el binario")
    else:
        print("[spec] ATENCION: se pidio --con-clave pero falta clave_yt.dat")

# La variante con audio deja este archivo adentro del ejecutable. El servidor lo
# busca para prender el módulo sin depender de una variable de entorno: en un
# binario que se abre con doble clic no hay forma de pasarla, y pedirle al
# usuario que abra una consola para usar una función de su propio build no tiene
# sentido.
#
# El build con audio incluye ffmpeg, que es lo único que quedaba por instalar a
# mano. Se copia con el nombre canónico ("ffmpeg.exe") porque tiddl y yt-dlp lo
# invocan por nombre, y el binario de imageio-ffmpeg viene versionado.
# Es GPLv3 y va como programa separado, sin modificar: ver
# build/terceros/FFMPEG-LICENCIA.txt, que se incluye al lado.
FFMPEG = []
if CON_AUDIO:
    try:
        import imageio_ffmpeg
        _ff = imageio_ffmpeg.get_ffmpeg_exe()
        _nombre = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
        _copia = os.path.join(RAIZ, "build", "terceros", _nombre)
        if not os.path.exists(_copia) or os.path.getsize(_copia) != os.path.getsize(_ff):
            import shutil as _sh
            os.makedirs(os.path.dirname(_copia), exist_ok=True)
            _sh.copy2(_ff, _copia)
        FFMPEG = [(_copia, "ffmpeg")]
        print(f"[spec] ffmpeg incluido: {os.path.getsize(_copia) / 1048576:.0f} MB")
    except Exception as _e:
        print(f"[spec] ATENCION: no pude incluir ffmpeg ({_e}). "
              "El usuario va a tener que instalarlo aparte.")

_MARCA_AUDIO = os.path.join(RAIZ, "build", "CON_AUDIO")
if CON_AUDIO and not os.path.exists(_MARCA_AUDIO):
    with open(_MARCA_AUDIO, "w", encoding="utf-8") as _f:
        _f.write("Este build incluye el modulo de audio (Tidal + referencia).")

# Licencias de terceros que viajan adentro del binario. Las de las fuentes van
# siempre porque las fuentes siempre se empaquetan; la de ffmpeg, sólo en la
# variante que lo trae.
#
# Se toman las que estén en build/terceros en vez de nombrarlas una por una: la
# lista escrita a mano quedó pidiendo ARCHIVO y GEIST después de que el rediseño
# cambiara las tipografías, y como el filtro por `os.path.exists` las descartaba
# en silencio, el binario salía sin ninguna licencia de fuente adentro. La SIL
# OFL pide que viaje con la fuente, y `TERMINOS.md` promete que viaja.
_TERCEROS = os.path.join(RAIZ, "build", "terceros")
LICENCIAS = [
    (os.path.join(_TERCEROS, n), "licencias")
    for n in sorted(os.listdir(_TERCEROS))
    if n.endswith("-LICENCIA.txt") and n != "FFMPEG-LICENCIA.txt"
]
if not LICENCIAS:
    raise SystemExit("No hay ninguna licencia de fuente en build/terceros.")

# Estas se excluyen sólo en la variante esencial.
DEPS_AUDIO = [
    "yt_dlp", "tiddl",
    "requests", "requests_cache", "urllib3", "websockets",
    "mutagen", "brotli", "curl_cffi", "Cryptodome", "secretstorage",
    "pydantic", "pydantic_core", "typer", "rich", "click",
]

a = Analysis(
    [os.path.join(APP, "launcher.py")],
    pathex=[SRC, APP, RAIZ],
    binaries=[],
    datas=[
        # La interfaz completa (html, css, js, tokens, fuentes, assets).
        (os.path.join(APP, "web"), "web"),
    ] + LICENCIAS
      + ([(_MARCA_AUDIO, "."),
          (os.path.join(RAIZ, "build", "terceros", "FFMPEG-LICENCIA.txt"), "licencias")]
         if CON_AUDIO else []) + FFMPEG + CLAVE,
    hiddenimports=[
        # Los importa el server por nombre y PyInstaller no siempre los ve.
        "server", "jobs",
        "migrador",
        "migrador.relevar_core", "migrador.productos", "migrador.portadas",
        "migrador.contratos", "migrador.texto", "migrador.validar",
        "migrador.paquete", "migrador.migrar_core", "migrador.audio",
        "migrador.i18n",
        # openpyxl carga sus writers de forma perezosa.
        "openpyxl.cell._writer",
        # Ventana nativa propia. Alcanza con nombrar "webview":
        # pyinstaller-hooks-contrib trae hook-webview / hook-clr /
        # hook-clr_loader y se encarga del backend y del runtime .NET.
        # Forzar a mano los submódulos de plataforma rompe la selección de
        # backend, que es lo que hacía que no abriera ninguna ventana.
        "webview",
    ],
    hookspath=[],
    runtime_hooks=[],
    # En la variante esencial se excluye el módulo de audio y su árbol de
    # dependencias. Hay que hacerlo explícitamente: audio.verificar_entorno() hace
    # `import yt_dlp` para detectar si está, y a PyInstaller le alcanza ese import
    # para arrastrarlo con websockets, requests, mutagen, curl_cffi y compañía
    # (unos 14 MB, y un descargador de audio dentro del binario). Sacarlos no
    # rompe nada: el import está en try/except ImportError y el resultado es
    # "audio no disponible", que es el estado correcto ahí.
    excludes=[
        # Nada de esto se usa y sacarlo baja bastante el peso.
        "tkinter", "unittest", "pydoc", "doctest", "test",
        "numpy", "pandas", "matplotlib", "PIL",
        "streamlit", "fastapi", "uvicorn", "pytest",
    ] + ([] if CON_AUDIO else DEPS_AUDIO),
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Migrador de Catalogos",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,          # UPX suele disparar falsos positivos de antivirus
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # .ico y no .png: en Windows PyInstaller sólo acepta exe/ico, y sin Pillow
    # instalado no convierte solo (compilaba en una máquina con Pillow y fallaba
    # en el CI, que no lo tiene). El .ico está commiteado para no depender de eso.
    icon=ICONO,
)


# ============================================================
# macOS: envolver el ejecutable en un .app
# ============================================================
#
# Hasta acá en macOS se publicaba un ejecutable suelto. Eso significa que doble
# clic en el Finder no hace lo que uno espera, que no aparece en el Launchpad, y
# que abrirlo son cuatro comandos de Terminal. Un .app sin firmar sigue pidiendo
# el clic derecho la primera vez, pero al menos se ve y se abre como una
# aplicación.
#
# `BUNDLE` sólo existe en macOS y sólo tiene sentido ahí, así que va detrás de
# la condición: en Windows y en Linux el spec termina en el EXE de arriba.
if sys.platform == "darwin":
    app = BUNDLE(  # noqa: F821  (PyInstaller lo inyecta al ejecutar el spec)
        exe,
        name="Migrador de Catalogos.app",
        icon=ICONO_MAC,
        # Identificador del bundle. No está registrado en ningún lado y no hace
        # falta que lo esté: macOS lo usa para separar las preferencias de una
        # app de las de otra.
        bundle_identifier="ar.com.joacogarciaoliver.migradorcatalogos",
        info_plist={
            "CFBundleDisplayName": "Migrador de Catalogos",
            "CFBundleShortVersionString": VERSION,
            "CFBundleVersion": VERSION,
            # Sin esto macOS abre la ventana en modo compatibilidad y todo se ve
            # borroso en una pantalla Retina, que son todas desde hace años.
            "NSHighResolutionCapable": True,
            # No es una app de línea de comandos: no tiene que aparecer un icono
            # de Terminal en el Dock al lado del suyo.
            "LSBackgroundOnly": False,
            "NSHumanReadableCopyright": "MIT. Ver LICENSE.",
        },
    )
