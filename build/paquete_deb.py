"""
Arma un .deb con el ejecutable ya compilado, para Debian y Ubuntu.

    python build/paquete_deb.py                    usa dist/ y la variante esencial
    python build/paquete_deb.py --variante completa
    python build/paquete_deb.py --binario dist/mi-ejecutable

Por qué un .deb y no un AppImage
--------------------------------
Los dos resuelven el mismo problema: en Linux se publicaba un ejecutable suelto,
y eso significa `chmod +x` y correrlo desde la terminal, sin icono, sin menú y
sin forma de desinstalarlo que no sea acordarse dónde quedó.

El .deb gana por una razón práctica. Se arma con la biblioteca estándar y nada
más, así que el build no depende de bajar `appimagetool` ni de que el runner
tenga FUSE, y el resultado se puede verificar en cualquier sistema, incluso
compilando desde Windows. AppImage exige una herramienta externa que hay que
bajar en cada build, y eso es justo lo que este proyecto evita.

Lo que instala
--------------
    /opt/migrador-catalogos/migrador-catalogos     el ejecutable
    /usr/bin/migrador-catalogos                    un enlace, para la terminal
    /usr/share/applications/...desktop             para que aparezca en el menú
    /usr/share/icons/hicolor/512x512/apps/...png   el icono
    /usr/share/doc/migrador-catalogos/copyright    la licencia

Cómo está hecho un .deb
-----------------------
Es un archivo `ar` con exactamente tres miembros, y en este orden:

    debian-binary     el texto "2.0\\n"
    control.tar.gz    los metadatos del paquete
    data.tar.gz       los archivos, con las rutas tal como quedan instaladas

El formato `ar` es una cabecera de sesenta bytes por miembro y relleno a byte
par. Son treinta líneas, y a cambio no hace falta `dpkg-deb`, que no existe en
Windows ni en macOS.
"""

import argparse
import gzip
import hashlib
import io
import os
import sys
import tarfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(RAIZ, "dist")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from notas_release import version  # noqa: E402

PAQUETE = "migrador-catalogos"
EJECUTABLE = "migrador-catalogos"
NOMBRE_MOSTRADO = "Migrador de Catalogos"

# El campo Architecture del .deb. Sólo se arma para 64 bits, que es lo que
# compila el CI.
ARQUITECTURA = "amd64"

CONTROL = """Package: {paquete}
Version: {version}
Section: sound
Priority: optional
Architecture: {arquitectura}
Maintainer: Joaquin Garcia Oliver <https://github.com/joacogoliver-debug>
Installed-Size: {kb}
Homepage: https://github.com/joacogoliver-debug/catalog-migrator
Description: Releva el catalogo de un artista y prepara su migracion
 Pega el link del canal de YouTube de un artista y devuelve los ISRC, los UPC,
 las portadas en alta resolucion, una hoja de ingesta lista para cargar y una
 validacion pre-entrega que dice que va a ser rechazado antes de mandarlo.
 .
 Corre entera en la maquina: no hay cuentas, no hay servidor y no hay
 telemetria. El ejecutable trae adentro todo lo que necesita, asi que este
 paquete no depende de ninguna libreria de Python del sistema.
"""

DESKTOP = """[Desktop Entry]
Type=Application
Name={nombre}
GenericName=Migrador de catalogos musicales
Comment=Releva el catalogo de un artista y prepara su migracion
Comment[en]=Survey an artist's catalog and prepare its migration
Exec={ejecutable}
Icon={paquete}
Terminal=false
Categories=AudioVideo;Audio;Utility;
Keywords=musica;catalogo;isrc;upc;distribuidora;music;catalog;
StartupWMClass={nombre}
"""


def _miembro_ar(nombre, datos, modo=b"100644"):
    """Un miembro del archivo `ar`, con su cabecera de sesenta bytes."""
    cabecera = (
        nombre.ljust(16).encode()
        # Fecha en cero, igual que adentro de los tar. Dos builds del mismo
        # codigo tienen que dar el mismo archivo, byte por byte: si no, el
        # SHA256 que se publica no sirve para comparar nada.
        + b"0".ljust(12)
        + b"0     "  # uid
        + b"0     "  # gid
        + modo.ljust(8)
        + str(len(datos)).ljust(10).encode()
        + b"\x60\x0a"  # fin de cabecera
    )
    assert len(cabecera) == 60, len(cabecera)
    # Los miembros se alinean a byte par.
    relleno = b"\n" if len(datos) % 2 else b""
    return cabecera + datos + relleno


def _tar_gz(archivos):
    """Un tar.gz determinístico a partir de {ruta_instalada: (bytes, modo)}.

    Determinístico a propósito: sin fecha ni dueño variables, dos builds del
    mismo código dan el mismo archivo, y el SHA256 que se publica sirve para
    comparar de verdad.
    """
    crudo = io.BytesIO()
    with tarfile.open(fileobj=crudo, mode="w", format=tarfile.GNU_FORMAT) as tar:
        for ruta in sorted(archivos):
            datos, modo = archivos[ruta]
            info = tarfile.TarInfo("./" + ruta.lstrip("/"))
            info.size = len(datos)
            info.mode = modo
            info.mtime = 0
            info.uid = info.gid = 0
            info.uname = info.gname = "root"
            tar.addfile(info, io.BytesIO(datos))
    return gzip.compress(crudo.getvalue(), mtime=0)


def contenido(binario, v):
    """Lo que el paquete instala, como {ruta: (bytes, modo)}."""
    with open(binario, "rb") as f:
        ejecutable = f.read()
    with open(os.path.join(RAIZ, "app", "web", "assets", "icono.png"), "rb") as f:
        icono = f.read()
    with open(os.path.join(RAIZ, "LICENSE"), encoding="utf-8") as f:
        licencia = f.read()

    desktop = DESKTOP.format(nombre=NOMBRE_MOSTRADO, ejecutable=EJECUTABLE, paquete=PAQUETE)
    # Los términos viajan adentro del paquete: la app los muestra igual la
    # primera vez que se abre, pero tienen que poder leerse sin abrirla.
    with open(os.path.join(RAIZ, "TERMINOS.md"), encoding="utf-8") as f:
        terminos = f.read()

    return {
        f"opt/{PAQUETE}/{EJECUTABLE}": (ejecutable, 0o755),
        f"usr/share/applications/{PAQUETE}.desktop": (desktop.encode("utf-8"), 0o644),
        f"usr/share/icons/hicolor/512x512/apps/{PAQUETE}.png": (icono, 0o644),
        f"usr/share/doc/{PAQUETE}/copyright": (licencia.encode("utf-8"), 0o644),
        f"usr/share/doc/{PAQUETE}/TERMINOS.md": (terminos.encode("utf-8"), 0o644),
    }, v


def armar(binario, destino, v=None):
    """Escribe el .deb y devuelve su ruta."""
    v = v or version()
    archivos, v = contenido(binario, v)

    data = _tar_gz(archivos)
    kb = max(1, sum(len(d) for d, _m in archivos.values()) // 1024)

    md5s = "".join(
        f"{hashlib.md5(datos).hexdigest()}  {ruta}\n" for ruta, (datos, _m) in sorted(archivos.items())
    )
    # El enlace en /usr/bin lo hace el postinst y no un symlink adentro del tar:
    # así apunta bien aunque el paquete se instale con otra raíz.
    postinst = f"#!/bin/sh\nset -e\nln -sf /opt/{PAQUETE}/{EJECUTABLE} /usr/bin/{EJECUTABLE}\nexit 0\n"
    prerm = f"#!/bin/sh\nset -e\nrm -f /usr/bin/{EJECUTABLE}\nexit 0\n"

    control = _tar_gz(
        {
            "control": (
                CONTROL.format(paquete=PAQUETE, version=v, arquitectura=ARQUITECTURA, kb=kb).encode("utf-8"),
                0o644,
            ),
            "md5sums": (md5s.encode("utf-8"), 0o644),
            "postinst": (postinst.encode("utf-8"), 0o755),
            "prerm": (prerm.encode("utf-8"), 0o755),
        }
    )

    with open(destino, "wb") as f:
        f.write(b"!<arch>\n")
        f.write(_miembro_ar("debian-binary", b"2.0\n"))
        f.write(_miembro_ar("control.tar.gz", control))
        f.write(_miembro_ar("data.tar.gz", data))
    return destino


def main(argv=None):
    ap = argparse.ArgumentParser(description="Arma el .deb con el ejecutable ya compilado.")
    ap.add_argument("--binario", default=None, help="por defecto, el que esté en dist/")
    ap.add_argument("--variante", default="esencial", choices=["esencial", "completa"])
    ap.add_argument("--salida", default=None)
    args = ap.parse_args(argv)

    binario = args.binario
    if not binario:
        candidatos = [
            os.path.join(DIST, n)
            for n in sorted(os.listdir(DIST))
            if os.path.isfile(os.path.join(DIST, n)) and not n.endswith((".sha256", ".deb"))
        ]
        if not candidatos:
            sys.exit("No encontre ningun ejecutable en dist/. Compila primero con build/build.py.")
        binario = candidatos[0]

    v = version()
    salida = args.salida or os.path.join(DIST, f"{PAQUETE}_{v}-{args.variante}_{ARQUITECTURA}.deb")
    armar(binario, salida, v)
    print(f"    {os.path.relpath(salida, RAIZ)}  ({os.path.getsize(salida) / 1e6:.1f} MB)")
    print(f"    se instala con:  sudo apt install ./{os.path.basename(salida)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
