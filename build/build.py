"""
Arma el ejecutable de la app.

    python build/build.py                      variante esencial
    python build/build.py --con-audio          suma el módulo de audio y ffmpeg
    python build/build.py --con-clave          mete una clave de YouTube adentro
    python build/build.py --con-audio --instalador     y arma el .exe instalador

Chequea el entorno, corre los tests, empaqueta con build/migrador.spec y deja el
resultado en dist/ junto a su SHA256, que es lo que se publica para que
cualquiera pueda verificar que el binario corresponde al código.

No firma el ejecutable: firmar cuesta plata (certificado EV en Windows, cuenta de
desarrollador en Apple) y este proyecto es gratis. En su lugar la confianza se
apoya en que el código es público, el binario se compila en GitHub Actions a la
vista de todos, y se publica el hash más una atestación de procedencia. Es la
misma postura que usa yt-dlp.
"""

import hashlib
import os
import re
import shutil
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = os.path.join(RAIZ, "build", "migrador.spec")
ISS = os.path.join(RAIZ, "build", "instalador.iss")
DIST = os.path.join(RAIZ, "dist")


def paso(texto):
    print(f"\n>>> {texto}")


def revisar_entorno():
    paso("Revisando el entorno")
    if sys.version_info < (3, 9):
        sys.exit("Hace falta Python 3.9 o más nuevo.")
    print(f"    Python {sys.version.split()[0]} en {sys.platform}")

    try:
        import PyInstaller  # noqa: F401

        print("    PyInstaller: ok")
    except ImportError:
        sys.exit("Falta PyInstaller. Instalalo con:  pip install pyinstaller")

    try:
        import openpyxl  # noqa: F401

        print("    openpyxl: ok")
    except ImportError:
        sys.exit("Falta openpyxl. Instalalo con:  pip install -r requirements-app.txt")

    # Se avisa acá y no cuando falle la corrida: "No module named pytest" a
    # mitad del build no dice qué instalar.
    try:
        import pytest  # noqa: F401

        print("    pytest: ok")
    except ImportError:
        sys.exit(
            "Falta pytest, que corre los tests antes de empaquetar. "
            "Instalalo con:  pip install -r requirements-dev.txt"
        )

    faltan = [
        f
        for f in (
            "app/launcher.py",
            "app/server.py",
            "app/web/index.html",
            "app/web/app.js",
            "app/web/app.css",
            "relevar_core.py",
            "validar.py",
            "paquete.py",
        )
        if not os.path.exists(os.path.join(RAIZ, f))
    ]
    if faltan:
        sys.exit(f"No encuentro estos archivos (¿estás corriendo desde la raíz del repo?): {faltan}")
    print("    archivos del proyecto: ok")

    # Las fuentes van adentro del binario. Si falta una, la app se ve con la
    # tipografía del sistema y nadie se entera hasta abrirla.
    #
    # Se pide exactamente lo que declara `tokens/fonts.css`, no una cantidad:
    # contar archivos parecía más simple y rompió el build cuando el rediseño
    # pasó de cuatro woff2 a tres. Lo que importa no es cuántos hay, es que esté
    # cada uno de los que el CSS pide.
    css = os.path.join(RAIZ, "app", "web", "tokens", "fonts.css")
    with open(css, encoding="utf-8") as f:
        pedidas = re.findall(r"url\(['\"]\.\./fonts/([^'\"]+)['\"]\)", f.read())
    if not pedidas:
        sys.exit(f"No pude leer ninguna fuente de {css}.")
    fuentes = os.path.join(RAIZ, "app", "web", "fonts")
    faltan_fuentes = [f for f in pedidas if not os.path.exists(os.path.join(fuentes, f))]
    if faltan_fuentes:
        sys.exit(f"fonts.css pide fuentes que no están en app/web/fonts: {faltan_fuentes}")
    print(f"    fuentes: {len(pedidas)} archivos, los que pide fonts.css")

    if not os.path.exists(os.path.join(RAIZ, "app", "web", "assets", "icono.ico")):
        sys.exit("Falta el icono. Generalo con:  python build/icono.py")
    print("    icono: ok")


def probar_tests():
    """Corre la batería offline antes de empaquetar.

    No tiene sentido publicar un binario que no pasa sus propios tests.

    Se delega en pytest y no se enumeran los archivos acá: la lista estaba
    escrita en tres lugares (este, el workflow del CI y el README) y un test
    nuevo que se olvidara en éste no bloqueaba un release, que es justo lo que
    este paso tiene que impedir.
    """
    paso("Corriendo los tests")
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"], cwd=RAIZ, env=env, capture_output=True, text=True
    )
    print((r.stdout or "").strip()[-3000:])
    if r.returncode == 5:
        # pytest sale 5 cuando no colectó ningún test. Sin este control, una
        # suite que dejó de encontrarse se ve igual que una suite en verde.
        sys.exit("pytest no encontró ningún test: no empaqueto.")
    if r.returncode != 0:
        print((r.stderr or "").strip()[-2000:])
        sys.exit("Los tests no pasaron: no empaqueto.")


def limpiar():
    paso("Limpiando builds anteriores")
    for d in (DIST, os.path.join(RAIZ, "build", "migrador")):
        if os.path.isdir(d):
            shutil.rmtree(d, ignore_errors=True)
            print(f"    borré {os.path.relpath(d, RAIZ)}")


def empaquetar():
    paso("Empaquetando con PyInstaller (tarda unos minutos)")
    r = subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            SPEC,
            "--noconfirm",
            "--clean",
            "--distpath",
            DIST,
            "--workpath",
            os.path.join(RAIZ, "build", "migrador"),
        ],
        cwd=RAIZ,
    )
    if r.returncode != 0:
        sys.exit("PyInstaller falló.")


def version():
    """La version de la app, leida de app/server.py.

    Es la unica fuente: el instalador, el release y lo que muestra la interfaz
    tienen que decir lo mismo. Escribirla en dos lados garantiza que tarde o
    temprano digan cosas distintas.
    """
    import re

    ruta = os.path.join(RAIZ, "app", "server.py")
    with open(ruta, encoding="utf-8") as f:
        m = re.search(r'^VERSION\s*=\s*"([^"]+)"', f.read(), re.M)
    if not m:
        sys.exit("No encontre VERSION en app/server.py.")
    return m.group(1)


def _iscc():
    """Dónde está el compilador de Inno Setup, o None."""
    if os.name != "nt":
        return None
    encontrado = shutil.which("iscc") or shutil.which("ISCC")
    if encontrado:
        return encontrado
    for base in (
        os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
        os.environ.get("ProgramFiles", r"C:\Program Files"),
    ):
        ruta = os.path.join(base, "Inno Setup 6", "ISCC.exe")
        if os.path.exists(ruta):
            return ruta
    return None


def terminos_txt():
    """Pasa los términos a texto plano para la pantalla de licencia del instalador.

    Se generan en vez de mantener copias a mano: si el .md y el .txt se
    escribieran por separado, tarde o temprano dirían cosas distintas y el
    usuario aceptaría una versión que no es la vigente.

    Son dos, uno por idioma, porque el instalador muestra la licencia en el
    idioma que se eligió en la primera pantalla. Devuelve la lista de rutas.
    """
    import re

    pares = [("TERMINOS.md", "TERMINOS.txt"), ("TERMS.md", "TERMS.txt")]
    salidas = []
    for nombre_md, nombre_txt in pares:
        origen = os.path.join(RAIZ, nombre_md)
        destino = os.path.join(RAIZ, "build", nombre_txt)
        with open(origen, encoding="utf-8") as f:
            md = f.read()

        lineas = []
        for linea in md.splitlines():
            if linea.strip() == "---":
                lineas.append("=" * 68)
                continue
            linea = re.sub(r"^#{1,6}\s*", "", linea)  # titulos
            linea = re.sub(r"\*\*(.+?)\*\*", r"\1", linea)  # negrita
            linea = re.sub(r"`([^`]+)`", r"\1", linea)  # codigo
            linea = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", linea)  # links
            linea = re.sub(r"^(\s*)-\s", r"\1* ", linea)  # vinetas
            lineas.append(linea)

        # Inno Setup lee el archivo de licencia como texto del sistema, asi que
        # va en UTF-8 con BOM y saltos de Windows para que no salga roto.
        with open(destino, "w", encoding="utf-8-sig", newline="\r\n") as f:
            f.write("\n".join(lineas).strip() + "\n")
        salidas.append(destino)
    return salidas


def instalador(variante):
    """Arma el instalador de Windows con Inno Setup.

    Es lo que convierte "bajá un .exe suelto" en un programa de verdad: queda en
    el menú Inicio, aparece en "Agregar o quitar programas" y se desinstala como
    cualquier otro. El portable se sigue publicando al lado para quien lo
    prefiera.
    """
    if os.name != "nt":
        print("    el instalador es sólo para Windows, lo salteo")
        return
    exe = _iscc()
    if not exe:
        print("    ATENCION: no encontré Inno Setup 6 (ISCC.exe), no armo el instalador.")
        print("    Se instala con:  winget install --id JRSoftware.InnoSetup -e")
        return
    paso("Armando el instalador de Windows")
    terminos_txt()
    v = version()
    print(f"    version: {v}")
    r = subprocess.run(
        [exe, ISS, f"/DMiVariante={variante}", f"/DMiVersion={v}", f"/DMiRaiz={RAIZ}"], cwd=RAIZ
    )
    if r.returncode != 0:
        sys.exit("Inno Setup falló.")


def resumen():
    paso("Resultado")
    if not os.path.isdir(DIST):
        sys.exit("No se generó dist/.")
    for nombre in sorted(os.listdir(DIST)):
        ruta = os.path.join(DIST, nombre)
        if not os.path.isfile(ruta) or nombre.endswith(".sha256"):
            continue
        h = hashlib.sha256()
        with open(ruta, "rb") as f:
            while True:
                bloque = f.read(1024 * 1024)
                if not bloque:
                    break
                h.update(bloque)
        tam = os.path.getsize(ruta) / 1e6
        print(f"    {nombre}  ({tam:.1f} MB)")
        print(f"    SHA256: {h.hexdigest()}")
        with open(ruta + ".sha256", "w", encoding="utf-8") as f:
            f.write(f"{h.hexdigest()}  {nombre}\n")

    print("\n    Listo. Está en dist/.")
    print("    En Windows y macOS va a mostrar un aviso de 'programa no reconocido'")
    print("    porque no está firmado: es esperable, y el README explica cómo seguir.")


def preparar_clave():
    """Deja la clave de YouTube lista para empaquetar.

    La lee de MIGRADOR_CLAVE_YT, o de la config local de la app si esa variable
    no está. NUNCA de un archivo del repositorio, para que no haya forma de que
    termine commiteada. En el CI la variable viene de un secreto de GitHub.

    El binario resultante CONTIENE la clave, y cualquiera que lo baje la puede
    extraer. Es una decisión consciente para que la versión completa funcione sin
    configurar nada: la clave tiene que estar restringida en Google Cloud a la
    YouTube Data API v3 y con tope de cuota.
    """
    import json as _json

    clave = os.environ.get("MIGRADOR_CLAVE_YT", "").strip()
    origen = "la variable MIGRADOR_CLAVE_YT"
    if not clave:
        cfg = os.path.join(os.path.expanduser("~"), ".migrador-catalogos", "config.json")
        if os.path.exists(cfg):
            try:
                with open(cfg, encoding="utf-8") as f:
                    clave = (_json.load(f).get("youtube_api_key") or "").strip()
                origen = "la config local de la app"
            except (OSError, ValueError):
                clave = ""
    if not clave:
        sys.exit("No encontré ninguna clave. Poné MIGRADOR_CLAVE_YT=... o cargala primero en la app.")

    # XOR con una semilla fija. NO es seguridad: sólo evita que la clave aparezca
    # en un `strings` del ejecutable y que la levante un scraper automático.
    semilla = 0x5A
    datos = bytes([semilla]) + bytes(b ^ semilla for b in clave.encode("utf-8"))
    destino = os.path.join(RAIZ, "build", "terceros", "clave_yt.dat")
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    with open(destino, "wb") as f:
        f.write(datos)

    paso("Clave de YouTube incluida en el ejecutable")
    print(f"    origen: {origen}")
    print(f"    termina en: ...{clave[-4:]}   (largo {len(clave)})")
    print("    Recordá que este binario la contiene y es extraíble.")
    print("    La clave tiene que estar restringida a YouTube Data API v3 y con tope de cuota.")


if __name__ == "__main__":
    con_clave = "--con-clave" in sys.argv
    con_audio = "--con-audio" in sys.argv
    con_instalador = "--instalador" in sys.argv

    if con_clave:
        os.environ["MIGRADOR_BUILD_CLAVE"] = "1"
    if con_audio:
        os.environ["MIGRADOR_BUILD_AUDIO"] = "1"
        print(">>> Variante completa (audio + ffmpeg adentro)")
    else:
        print(">>> Variante esencial (sin audio)")

    revisar_entorno()
    if con_clave:
        preparar_clave()
    if "--sin-tests" not in sys.argv:
        probar_tests()
    limpiar()
    empaquetar()
    if con_instalador:
        instalador("completa" if con_audio else "esencial")
    resumen()
