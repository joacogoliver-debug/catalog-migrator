# -*- coding: utf-8 -*-
"""El .deb de Linux. Sin red y sin dpkg.

El paquete se arma con la biblioteca estándar, así que también se puede
verificar con ella, en cualquier sistema. Eso es justamente lo que se ganó al
elegir .deb sobre AppImage: el formato es un `ar` con tres miembros, y un test
puede abrirlo y mirar adentro sin instalar herramientas de Debian.

Lo que se prueba acá es la estructura y los metadatos. Que el ejecutable de
adentro funcione es otra cosa, y de eso se ocupa el CI, que lo corre antes de
publicar.
"""

import gzip
import hashlib
import io
import tarfile

import pytest

from paquete_deb import ARQUITECTURA, PAQUETE, armar


@pytest.fixture(scope="module")
def deb(tmp_path_factory):
    """Un .deb armado con un ejecutable de mentira."""
    tmp = tmp_path_factory.mktemp("deb")
    binario = tmp / "Migrador de Catalogos"
    binario.write_bytes(b"\x7fELF" + b"ejecutable de mentira" * 50)

    destino = tmp / "salida.deb"
    armar(str(binario), str(destino), "9.9.9")
    return destino.read_bytes()


def _miembros(datos):
    """Los miembros del archivo `ar`, en orden, como {nombre: bytes}."""
    assert datos.startswith(b"!<arch>\n"), "no es un archivo ar"
    fuera = {}
    orden = []
    pos = 8
    while pos < len(datos):
        cabecera = datos[pos : pos + 60]
        nombre = cabecera[0:16].decode().strip()
        largo = int(cabecera[48:58].decode().strip())
        fuera[nombre] = datos[pos + 60 : pos + 60 + largo]
        orden.append(nombre)
        pos += 60 + largo + (largo % 2)
    return orden, fuera


def _tar(datos):
    return tarfile.open(fileobj=io.BytesIO(gzip.decompress(datos)))


# ============================================================
# Estructura
# ============================================================


def test_los_tres_miembros_estan_y_en_el_orden_que_pide_dpkg(deb):
    """dpkg exige exactamente estos tres y en este orden. Con otro orden el
    paquete no se instala, y el error no dice por qué."""
    orden, _m = _miembros(deb)
    assert orden == ["debian-binary", "control.tar.gz", "data.tar.gz"]


def test_la_version_del_formato_es_la_esperada(deb):
    _orden, m = _miembros(deb)
    assert m["debian-binary"] == b"2.0\n"


def test_el_paquete_es_reproducible(tmp_path):
    """Dos builds del mismo código dan el mismo archivo, byte por byte. Si no,
    el SHA256 que se publica junto al binario no sirve para comparar nada."""
    binario = tmp_path / "bin"
    binario.write_bytes(b"\x7fELFcontenido")

    uno, dos = tmp_path / "uno.deb", tmp_path / "dos.deb"
    armar(str(binario), str(uno), "9.9.9")
    armar(str(binario), str(dos), "9.9.9")

    assert hashlib.sha256(uno.read_bytes()).hexdigest() == hashlib.sha256(dos.read_bytes()).hexdigest()


# ============================================================
# Metadatos
# ============================================================


@pytest.fixture(scope="module")
def control(deb):
    _orden, m = _miembros(deb)
    with _tar(m["control.tar.gz"]) as t:
        archivo = t.extractfile("./control")
        assert archivo
        return archivo.read().decode("utf-8")


@pytest.mark.parametrize(
    "campo",
    ["Package:", "Version:", "Architecture:", "Maintainer:", "Description:", "Installed-Size:"],
)
def test_el_control_trae_los_campos_obligatorios(control, campo):
    assert campo in control


def test_el_control_dice_el_paquete_la_version_y_la_arquitectura(control):
    assert f"Package: {PAQUETE}" in control
    assert "Version: 9.9.9" in control
    assert f"Architecture: {ARQUITECTURA}" in control


def test_la_descripcion_larga_va_indentada(control):
    """Un renglón de la descripción sin el espacio adelante termina la
    descripción, y dpkg lo lee como un campo desconocido."""
    lineas = control.splitlines()
    i = lineas.index([x for x in lineas if x.startswith("Description:")][0])
    for linea in lineas[i + 1 :]:
        if not linea:
            continue
        assert linea.startswith(" "), linea


def test_los_scripts_de_instalacion_son_ejecutables(deb):
    _orden, m = _miembros(deb)
    with _tar(m["control.tar.gz"]) as t:
        modos = {x.name: x.mode for x in t.getmembers()}
    assert modos["./postinst"] == 0o755
    assert modos["./prerm"] == 0o755


def test_el_postinst_crea_el_enlace_y_el_prerm_lo_saca(deb):
    """Sin el enlace en /usr/bin la app no se puede abrir desde la terminal, y
    sin sacarlo al desinstalar queda un enlace roto."""
    _orden, m = _miembros(deb)
    with _tar(m["control.tar.gz"]) as t:
        post = t.extractfile("./postinst")
        pre = t.extractfile("./prerm")
        assert post and pre
        postinst = post.read().decode()
        prerm = pre.read().decode()

    assert postinst.startswith("#!/bin/sh")
    assert f"/usr/bin/{PAQUETE}" in postinst
    assert f"rm -f /usr/bin/{PAQUETE}" in prerm


# ============================================================
# Lo que queda instalado
# ============================================================


@pytest.fixture(scope="module")
def instalado(deb):
    _orden, m = _miembros(deb)
    with _tar(m["data.tar.gz"]) as t:
        return {x.name: x for x in t.getmembers()}


@pytest.mark.parametrize(
    "ruta",
    [
        f"./opt/{PAQUETE}/{PAQUETE}",
        f"./usr/share/applications/{PAQUETE}.desktop",
        f"./usr/share/icons/hicolor/512x512/apps/{PAQUETE}.png",
        f"./usr/share/doc/{PAQUETE}/copyright",
        f"./usr/share/doc/{PAQUETE}/TERMINOS.md",
    ],
)
def test_el_paquete_instala_el_archivo(instalado, ruta):
    assert ruta in instalado


def test_el_ejecutable_queda_ejecutable(instalado):
    assert instalado[f"./opt/{PAQUETE}/{PAQUETE}"].mode == 0o755


def test_todo_lo_demas_queda_de_solo_lectura(instalado):
    for ruta, info in instalado.items():
        if ruta.endswith(PAQUETE) and "/opt/" in ruta:
            continue
        assert info.mode == 0o644, ruta


def test_los_md5sums_cubren_todos_los_archivos(deb, instalado):
    """dpkg los usa para detectar un archivo modificado a mano. Si falta uno,
    ese archivo queda sin control y nadie se entera."""
    _orden, m = _miembros(deb)
    with _tar(m["control.tar.gz"]) as t:
        archivo = t.extractfile("./md5sums")
        assert archivo
        rutas = {linea.split("  ", 1)[1] for linea in archivo.read().decode().splitlines()}

    esperadas = {ruta.lstrip("./") for ruta in instalado}
    assert rutas == esperadas


# ============================================================
# La entrada del menú
# ============================================================


@pytest.fixture(scope="module")
def desktop(deb):
    _orden, m = _miembros(deb)
    with _tar(m["data.tar.gz"]) as t:
        archivo = t.extractfile(f"./usr/share/applications/{PAQUETE}.desktop")
        assert archivo
        return archivo.read().decode("utf-8")


def test_la_entrada_del_menu_empieza_como_corresponde(desktop):
    assert desktop.startswith("[Desktop Entry]")


@pytest.mark.parametrize("clave", ["Type=Application", "Name=", "Exec=", "Icon=", "Categories="])
def test_la_entrada_del_menu_trae_la_clave(desktop, clave):
    assert clave in desktop


def test_la_app_no_abre_una_terminal(desktop):
    """`Terminal=true` abriría una ventana negra al lado de la app, que es
    exactamente lo que este paquete viene a evitar."""
    assert "Terminal=false" in desktop


def test_el_icono_del_menu_es_el_nombre_del_paquete_y_no_una_ruta(desktop):
    """Así lo busca el sistema de temas de iconos, que es lo que hace que se vea
    bien en cualquier tamaño."""
    assert f"Icon={PAQUETE}\n" in desktop
