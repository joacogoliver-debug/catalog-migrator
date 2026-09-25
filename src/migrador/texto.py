"""
Normalización de texto y nombres de archivo, en un solo lugar.

Estas funciones estaban escritas seis veces, casi iguales pero no del todo, y
esa clase de casi es la peor. `productos._norm` y `portadas._norm` eran idénticas
palabra por palabra; `audio._norm` hacía lo mismo pero sin sacar los acentos, y
nada decía si eso era a propósito (no lo era, ver abajo). Los dos slugs de
carpeta y de archivo diferían en un `.strip()` que en uno de los dos dejaba pasar
un punto final, que en Windows es un nombre inválido.

Las tres normalizaciones son una sola cosa en tres grados, y por eso se componen
en vez de repetirse.

    sin_acentos("Corazón Roto!")   -> "Corazon Roto!"
    plegado("Corazón Roto!")       -> "corazon roto!"
    comparable("Corazón Roto!")    -> "corazon roto"

Este módulo no importa nada del proyecto, para que cualquiera lo pueda usar sin
arrastrar dependencias ni armar un ciclo.
"""

import re
import unicodedata

# Caracteres que Windows no admite en un nombre de archivo ni de carpeta.
_RE_PROHIBIDOS_WINDOWS = re.compile(r'[<>:"/\\|?*]')
_RE_CONTROL = re.compile(r"[\x00-\x1f]")
_RE_PUNTUACION = re.compile(r"[^\w\s]")
_RE_ESPACIOS = re.compile(r"\s+")
# Lo que un programa de planillas ejecuta al abrir un CSV: empieza con uno de
# esos signos y lleva lo que necesita una llamada o un enlace DDE. Ver
# `paquete._texto_csv`, que es quien lo usa para escribir.
_RE_FORMULA = re.compile(r"^[=+\-@\t\r].*[(|!]", re.S)


def sin_acentos(s):
    """Saca los acentos y todo lo que no sea ASCII, conservando mayúsculas.

    Se usa donde hace falta un texto plano pero legible, como el reporte de
    validación, que se abre en un Bloc de notas cualquiera.
    """
    return unicodedata.normalize("NFD", s or "").encode("ascii", "ignore").decode("ascii")


def plegado(s):
    """Sin acentos y en minúsculas. Conserva la puntuación.

    Es el grado que alcanza para buscar una subcadena adentro de otra, donde la
    puntuación no molesta y sacarla podría unir dos palabras.
    """
    return sin_acentos(s).lower()


def comparable(s):
    """La forma en que se comparan dos títulos para ver si son el mismo.

    Sin acentos, en minúsculas, sin puntuación y con los espacios colapsados.
    Es lo que hace que «Corazón Roto!» y «Corazon Roto» se agrupen como un solo
    álbum, y que el artista que YouTube escribe con tilde encuentre en Tidal al
    que está escrito sin ella.
    """
    return _RE_ESPACIOS.sub(" ", _RE_PUNTUACION.sub(" ", plegado(s))).strip()


def nombre_seguro(s, maxlen=80, fallback="sin-titulo"):
    """Un nombre de archivo o carpeta que funcione en Windows, macOS y Linux.

    Saca los caracteres prohibidos en vez de escaparlos: un título con una barra
    adentro no quiere decir nada como subcarpeta.

    El recorte va ANTES del último `strip`, y no al revés. Cortar en `maxlen`
    puede dejar justo un punto o un espacio al final, y Windows no admite ninguno
    de los dos: un nombre así falla recién al descomprimir el ZIP, en la máquina
    de otro.
    """
    s = sin_acentos(s)
    s = _RE_PROHIBIDOS_WINDOWS.sub("", s)
    s = _RE_CONTROL.sub("", s)
    s = _RE_ESPACIOS.sub(" ", s).strip(" .")
    return s[:maxlen].strip(" .") or fallback


# Las marcas de versión se buscan sólo en lo que DECORA un título: lo que va
# entre paréntesis o corchetes, y lo que sigue a un « - ». Buscarlas en el
# título entero haría que «Live Forever» contara como una versión en vivo.
_RE_DECORADO = re.compile(r"[(\[]([^)\]]*)[)\]]|\s[-\u2013]\s(.+)$")
_MARCAS_VERSION = tuple(
    (nombre, re.compile(patron))
    for nombre, patron in (
        ("vivo", r"\b(en vivo|ao vivo|live|en directo|directo)\b"),
        ("remix", r"\b(remix|rmx|mix|rework|bootleg|vip)\b"),
        ("remaster", r"\b(remaster|remastered|remasterizad[oa])\b"),
        ("acustico", r"\b(acoustic|acustic[oa]|unplugged|desenchufado)\b"),
        ("instrumental", r"\binstrumental\b"),
        ("edit", r"\bedit\b"),
        ("acelerado", r"\b(sped up|speed up|slowed|nightcore)\b"),
        ("demo", r"\bdemo\b"),
        ("extendida", r"\b(extended|extendida)\b"),
        ("karaoke", r"\bkaraoke\b"),
    )
)


def marcas_version(titulo):
    """Qué versión de una grabación dice ser un título, como un conjunto.

        marcas_version("Tema (En Vivo)")            -> {"vivo"}
        marcas_version("Tema - Remastered 2011")    -> {"remaster"}
        marcas_version("Tema (feat. Otra)")         -> set()
        marcas_version("Live Forever")              -> set()

    Dos títulos con marcas distintas no son la misma grabación, aunque el resto
    coincida letra por letra, y por eso no pueden compartir ISRC ni portada.
    """
    partes = " ".join(a or b for a, b in _RE_DECORADO.findall(plegado(titulo)))
    return frozenset(n for n, rx in _MARCAS_VERSION if rx.search(partes))


def misma_version(titulo_a, titulo_b):
    """Si dos títulos pueden ser la misma grabación, o el mismo disco.

    Tienen que declarar las mismas marcas de versión y llevar los mismos
    números. Los números importan porque son justo lo que separa «Parte 1» de
    «Parte 2», o «Vol. 1» de «Vol. 2», y el resto del título coincide en más de
    un noventa por ciento: comparados enteros, salían con confianza alta. Es
    una regla conservadora a propósito: «(Remastered)» contra «(Remastered
    2011)» también queda afuera, y eso deja el código en blanco en vez de
    ponerle el de otro remaster.
    """
    if marcas_version(titulo_a) != marcas_version(titulo_b):
        return False
    numeros = [sorted(re.findall(r"\d+", plegado(t))) for t in (titulo_a, titulo_b)]
    return numeros[0] == numeros[1]


def sin_decorado(titulo):
    """El título sin lo que va entre paréntesis o corchetes ni lo que sigue a
    un « - ». Sirve para comparar dos versiones que ya se sabe que son la misma
    y que la escriben distinto («(2011 Remaster)» y « - Remastered 2011»)."""
    return re.sub(r"\s+", " ", _RE_DECORADO.sub(" ", titulo or "")).strip()


def mmss(segundos):
    """Una duración en `m:ss`, que es como se lee una canción."""
    segundos = int(segundos or 0)
    return f"{segundos // 60}:{segundos % 60:02d}"


def parece_formula(v):
    """True si un texto se ejecutaría como fórmula al abrir el CSV en una planilla.

    No alcanza con mirar el primer carácter: hay discos que se llaman «+», «=» o
    «-Intro-», y marcarlos como sospechosos obligaría a tocar el nombre de un
    release por las dudas. Una fórmula que haga algo necesita un paréntesis, una
    barra o un signo de exclamación.
    """
    return isinstance(v, str) and bool(_RE_FORMULA.match(v))
