"""
Arma las notas de un release, a partir del CHANGELOG.

    python build/notas_release.py                     la versión de app/server.py
    python build/notas_release.py --version 1.0.3
    python build/notas_release.py --salida notas.md

Por qué existe
--------------
Las notas estaban escritas a mano adentro de `.github/workflows/build.yml`, en un
bloque `body:` de ciento veinticinco líneas, en los dos idiomas. Lo que cambió en
cada versión no aparecía ahí en absoluto: el CHANGELOG existía y nadie lo leía al
publicar, así que quien bajaba el binario no tenía forma de saber qué cambió sin
ir a buscarlo.

Ahora las notas se arman con dos partes bien separadas:

  - **qué cambió**, que sale del CHANGELOG y no se escribe dos veces;
  - **cuál bajar y cómo verificarlo**, que no está en el CHANGELOG porque no es
    un cambio, y vive en `build/notas/es.md` y `build/notas/en.md`.

Además verifica que el CHANGELOG tenga de verdad una entrada para la versión que
se está publicando. Sin ese control, taguear `v1.0.3` con el CHANGELOG todavía en
«Sin publicar» produce un release que miente, y eso se descubre cuando ya está
publicado.
"""

import argparse
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOTAS = os.path.join(RAIZ, "build", "notas")

# Los dos CHANGELOG y el archivo de prosa que le corresponde a cada idioma.
IDIOMAS = [
    ("es", "CHANGELOG.md", "es.md"),
    ("en", "CHANGELOG.en.md", "en.md"),
]

REPO_POR_DEFECTO = "joacogoliver-debug/catalog-migrator"


def version():
    """La versión de la app, leída de `app/server.py`.

    Es la única fuente: el instalador, el release y lo que muestra la interfaz
    tienen que decir lo mismo. Escribirla en dos lados garantiza que tarde o
    temprano digan cosas distintas.
    """
    ruta = os.path.join(RAIZ, "app", "server.py")
    with open(ruta, encoding="utf-8") as f:
        m = re.search(r'^VERSION\s*=\s*"([^"]+)"', f.read(), re.M)
    if not m:
        sys.exit("No encontre VERSION en app/server.py.")
    return m.group(1)


def seccion_changelog(nombre_archivo, v):
    """Lo que el CHANGELOG dice de esta versión, sin el encabezado.

    Devuelve None si no hay una entrada para `v`, que es el caso que hay que
    frenar antes de publicar.
    """
    ruta = os.path.join(RAIZ, nombre_archivo)
    with open(ruta, encoding="utf-8") as f:
        texto = f.read()

    # El encabezado es "## [1.0.3] ..." y la sección termina en el próximo "## ".
    patron = rf"^## \[{re.escape(v)}\][^\n]*\n(.*?)(?=^## |\Z)"
    m = re.search(patron, texto, re.S | re.M)
    if not m:
        return None

    cuerpo = m.group(1).strip()
    # Los enlaces de referencia del pie ("[1.0.3]: https://...") no van adentro
    # del release: ahí el número de versión ya es el título de la página.
    cuerpo = re.sub(r"^\[[^\]]+\]:\s*https?://\S+\s*$", "", cuerpo, flags=re.M)
    return cuerpo.strip()


def absolutizar(texto, repo, rama="main"):
    """Convierte los enlaces relativos del CHANGELOG en enlaces que funcionen.

    En un archivo del repositorio, `[guía](docs/INSTALAR-MAC.md)` anda solo. En
    el cuerpo de un release, GitHub lo resuelve contra la URL del release y
    termina en un 404. Como el CHANGELOG se escribe para leerse en el repo, la
    conversión se hace acá y no se le pide a nadie que escriba enlaces absolutos
    en un archivo donde sobran.
    """

    def reemplazo(m):
        destino = m.group(2)
        if destino.startswith(("http://", "https://", "#", "mailto:")):
            return m.group(0)
        return f"[{m.group(1)}](https://github.com/{repo}/blob/{rama}/{destino.lstrip('./')})"

    return re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", reemplazo, texto)


def notas(v, repo=REPO_POR_DEFECTO):
    """El cuerpo completo del release, en los dos idiomas."""
    partes = []
    faltan = []

    for idioma, changelog, prosa in IDIOMAS:
        cambios = seccion_changelog(changelog, v)
        if cambios is None:
            faltan.append(changelog)
            continue

        with open(os.path.join(NOTAS, prosa), encoding="utf-8") as f:
            fija = f.read().format(repo=repo).strip()

        cambios = absolutizar(cambios, repo)
        titulo = "## Qué cambió" if idioma == "es" else "## What changed"
        if idioma == "en":
            partes.append("---\n\n# In English")
        partes.append(f"{titulo}\n\n{cambios}")
        partes.append(fija)

    if faltan:
        sys.exit(
            f"No hay una entrada para la version {v} en: {', '.join(faltan)}.\n"
            "Antes de taguear, la seccion '[Sin publicar]' se renombra a\n"
            f"'## [{v}] - <fecha>' en los dos CHANGELOG. Sin eso el release sale\n"
            "sin decir que cambio, que es justo lo que este script evita."
        )

    return "\n\n".join(partes) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Arma las notas de un release desde el CHANGELOG.")
    ap.add_argument("--version", default=None, help="por defecto, la de app/server.py")
    ap.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY") or REPO_POR_DEFECTO)
    ap.add_argument("--salida", default=None, help="archivo donde escribirlas; si no, a la salida estándar")
    args = ap.parse_args(argv)

    v = (args.version or version()).lstrip("v")
    cuerpo = notas(v, args.repo)

    if args.salida:
        with open(args.salida, "w", encoding="utf-8", newline="\n") as f:
            f.write(cuerpo)
        print(f"notas de la version {v} en {args.salida} ({len(cuerpo.splitlines())} lineas)")
    else:
        # Se escribe al buffer binario y no a sys.stdout: la consola de Windows
        # usa cp1252 y la prosa tiene flechas y comillas que ahi no entran, asi
        # que imprimirlas revienta con UnicodeEncodeError. Las notas son UTF-8
        # siempre, vayan a un archivo o a una tuberia.
        salida = getattr(sys.stdout, "buffer", None)
        if salida is None:
            sys.stdout.write(cuerpo)
        else:
            salida.write(cuerpo.encode("utf-8"))
            salida.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
