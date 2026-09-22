"""Busca claves de API en los archivos que se le pasen.

Lo usan dos lugares, y es a propósito el mismo código en los dos.

  - el gancho de pre-commit, sobre los archivos que están por commitearse;
  - el CI, sobre todo el árbol, con `--todo`.

La clave de YouTube vive como secreto de GitHub y entra recién al compilar. Que
no se pueda commitear por accidente es mucho más barato de garantizar que de
revertir: una clave que llegó a un commit ya se considera filtrada, aunque se
borre después, porque el objeto queda en la historia y en cada clon.

Sale 0 si está limpio, 1 si encontró algo. No imprime nunca la clave, sólo dónde
está.
"""

import os
import re
import subprocess
import sys

# El formato de las claves de Google: "AIza" y 35 caracteres del alfabeto de
# URLs. Se exige el largo para no marcar cualquier texto que empiece igual.
RE_CLAVE_GOOGLE = re.compile(r"AIza[0-9A-Za-z_-]{30,}")

# El archivo con la clave XOR-eada que arma `build/build.py --con-clave`. Está
# en .gitignore, pero un `git add -f` distraído lo metería igual.
PROHIBIDOS = ("clave_yt.dat",)

# Binarios y carpetas que no tiene sentido leer.
EXT_BINARIAS = (".png", ".jpg", ".jpeg", ".ico", ".woff2", ".exe", ".zip", ".xlsx", ".dat")
CARPETAS_IGNORADAS = {".git", "__pycache__", "dist", "node_modules", ".ruff_cache", ".pytest_cache"}


def archivos_del_repo():
    """Todo lo versionado. Se le pregunta a git para no recorrer dist/ ni .git/."""
    salida = subprocess.run(
        ["git", "ls-files"], capture_output=True, text=True, check=False
    )
    return [l for l in salida.stdout.splitlines() if l.strip()]


def revisar(rutas):
    problemas = []
    for ruta in rutas:
        nombre = os.path.basename(ruta)
        if nombre in PROHIBIDOS:
            problemas.append(f"{ruta}: es el archivo de la clave y no va al repositorio")
            continue
        if ruta.lower().endswith(EXT_BINARIAS):
            continue
        if any(parte in CARPETAS_IGNORADAS for parte in ruta.replace("\\", "/").split("/")):
            continue
        try:
            with open(ruta, encoding="utf-8", errors="ignore") as f:
                for n, linea in enumerate(f, 1):
                    if RE_CLAVE_GOOGLE.search(linea):
                        problemas.append(f"{ruta}:{n}: parece haber una clave de API")
        except OSError:
            continue
    return problemas


def main(argv):
    rutas = archivos_del_repo() if ("--todo" in argv or not argv) else argv
    problemas = revisar([r for r in rutas if r != "--todo"])
    if problemas:
        print("No se puede commitear esto:")
        for p in problemas:
            print(f"  {p}")
        print("\nLa clave va en la variable MIGRADOR_CLAVE_YT o en la config local "
              "de la app, nunca en el repositorio.")
        return 1
    print(f"sin claves ({len(rutas)} archivos revisados)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
