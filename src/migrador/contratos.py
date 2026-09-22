"""
Las formas de los datos que viajan entre los módulos.

Hasta acá el contrato entre `relevar_core`, `productos`, `validar`, `portadas`,
`paquete` y `audio` vivía en los docstrings y en la cabeza de quien lo escribió.
Cada consumidor adivinaba qué claves existían, y `tests/test_migrar_core.py`
llegó a fijar ese contrato con un conjunto de cadenas escrito a mano, que es la
versión pobre de este archivo.

Por qué TypedDict y no dataclasses
----------------------------------
Los datos son diccionarios y se arman por partes. `relevar_core` crea el track,
`enrich_with_codes` le agrega el ISRC, `portadas` le pega los bytes de la tapa al
producto y `audio` la ruta del archivo a cada track. Después todo eso se
serializa a JSON para el frontend tal cual.

Pasarlo a dataclasses obligaría a reescribir unos doscientos accesos `p["title"]`
y a inventar una serialización, a cambio de nada que el usuario note. TypedDict
describe exactamente la misma estructura, la verifica pyright, y en tiempo de
ejecución no existe: son diccionarios comunes y el programa corre igual.

Las claves que se agregan más tarde van como `NotRequired`, que es justamente lo
que dice la verdad: un producto recién agrupado todavía no tiene portada.

Este módulo no importa nada del proyecto, a propósito, para que cualquiera pueda
importarlo sin arrastrar dependencias ni armar un ciclo.
"""

from typing import Literal, NotRequired, TypedDict

# Los formatos aptos para entrega, o sea lossless de verdad. Vive acá y no en
# `audio.py` porque es parte del contrato de lo que significa
# `Track.audio_format`, y quien arma el entregable lo necesita sin importar
# el módulo de audio, que es opcional y puede no estar instalado.
FORMATOS_LOSSLESS = {".flac"}

# El formato del release. Sale de la cantidad de tracks (1-3 / 4-6 / 7+), que es
# la convención de las distribuidoras y sigue siendo una heurística, no un dato
# declarado por YouTube. Ver `productos.MAX_TRACKS_SINGLE`.
TipoProducto = Literal["single", "ep", "album"]

# Un hallazgo de la validación es error, que la distribuidora rechaza, o aviso,
# que pasa la ingesta pero conviene mirar.
NivelHallazgo = Literal["error", "aviso"]

# El año llega como entero cuando se pudo parsear y como cadena vacía cuando no.
# Se escribe así y no `int | None` porque es lo que el código hace hoy, y esto
# describe el contrato real, no el que nos gustaría.
Anio = int | str


class DescripcionParseada(TypedDict):
    """Lo que `relevar_core.parse_description` saca de la descripción de YouTube.

    Todo es opcional porque una descripción puede no traer nada. `None` significa
    «no estaba», nunca «no lo buscamos».
    """

    distributor: str | None
    album: str | None
    release_year: int | None
    label: str | None


class CruceTidal(TypedDict):
    """Lo que el índice de Tidal aporta sobre un track, cuando hay cuenta.

    Es la única fuente del número de track real: YouTube no lo expone y el
    orden que arma `productos` es una estimación por fecha de subida. Cuando
    Tidal lo confirma para todos los tracks de un producto, se apaga
    `order_unconfirmed`.
    """

    track_id: int
    track_number: NotRequired[int | None]
    volume_number: NotRequired[int | None]
    upc: NotRequired[str]


class Track(TypedDict):
    """Un video de YouTube ya interpretado como grabación.

    Lo arma `relevar_core.build_tracks`. Las claves de abajo se completan
    después, cada una por su módulo, y por eso no son obligatorias.
    """

    video_id: str
    track: str
    # OJO: `album` y `distributor` pueden traer los centinelas `SIN_ALBUM` y
    # `SIN_DATOS` de `productos`. No son texto para mostrar y no se traducen.
    album: str
    distributor: str
    label: str
    release_year: Anio
    isrc: str
    upc: str
    match: str  # confianza del cruce con Deezer: "alta", "media" o ""
    duration_s: int
    views: int
    likes: int
    comments: int
    upload_date: str  # AAAA-MM-DD
    desc3: str
    url: str

    # Lo pone `productos.group_products`, estimado por fecha de subida. YouTube
    # no expone el número de track, así que el producto queda marcado con
    # `order_unconfirmed`.
    track_number: NotRequired[int | None]

    # Lo pone `audio.matchear_por_isrc`, cruzando el ISRC contra el índice de
    # la discografía en Tidal. `None` significa que se buscó y no apareció.
    tidal: NotRequired[CruceTidal | None]

    # Los pone `audio.fetch_audio`, sólo si se pidieron los audios.
    audio_path: NotRequired[str | None]
    audio_format: NotRequired[str | None]
    audio_label: NotRequired[str | None]
    # El motivo por el que no se pudo bajar, que el reporte transcribe para
    # que se pueda decidir si buscarlo por otro lado.
    audio_error: NotRequired[str]


class Producto(TypedDict):
    """Un release, que es la unidad con la que se entrega una migración.

    Lo arma `productos.group_products` agrupando tracks. Las claves de portada
    las agrega `portadas.fetch_portadas` más tarde, sobre una copia.
    """

    product_id: str
    title: str
    kind: TipoProducto
    artist: str
    release_year: Anio
    release_date: str
    label: str
    distributor: str
    upc: str
    tracks: list[Track]
    track_count: int
    total_views: int
    # True cuando el orden de los tracks salió sólo de la fecha de subida.
    order_unconfirmed: bool
    # Lo pone `group_products` al final, siempre. Es el nombre de la carpeta
    # del producto dentro del ZIP.
    folder: str

    # Los agrega `portadas.fetch_portadas`. `cover_px` es la resolución que Apple
    # devolvió DE VERDAD, no la que se pidió, que es la distinción de la que
    # depende que la planilla no mienta sobre el mínimo de ingesta.
    cover_bytes: NotRequired[bytes | None]
    cover_px: NotRequired[int]
    cover_status: NotRequired[str]
    cover_match: NotRequired[str]

    # Lo pone `audio.matchear_por_isrc`, como "3/5".
    tidal_cobertura: NotRequired[str]


class Hallazgo(TypedDict):
    """Un problema encontrado por la validación pre-entrega.

    `codigo` es la llave con la que la interfaz agrupa y el test busca, y no se
    traduce nunca. `mensaje` sí, y va en el idioma que el usuario eligió.
    """

    nivel: NivelHallazgo
    codigo: str
    mensaje: str
    producto: str
    track: str | None


class ResumenValidacion(TypedDict):
    productos: int
    tracks: int
    errores: int
    avisos: int


class ResultadoValidacion(TypedDict):
    """Lo que devuelve `validar.validar`.

    `apto` es lo único que decide si la entrega puede salir: es falso cuando hay
    al menos un error, y los avisos no lo tocan.
    """

    hallazgos: list[Hallazgo]
    errores: list[Hallazgo]
    avisos: list[Hallazgo]
    apto: bool
    resumen: ResumenValidacion


class ResumenSeleccion(TypedDict):
    """Lo que devuelve `productos.summarize`, para mostrar antes de descargar."""

    products: int
    tracks: int
    albums: int
    eps: int
    singles: int
    with_upc: int
    with_isrc: int
    views: int


class TopicSugerido(TypedDict):
    id: str
    titulo: str
    url: str


class Relevamiento(TypedDict):
    """Lo que devuelve `relevar_core.relevar`.

    Éste es el contrato que más se rompió en la práctica: `migrar_core` llegó a
    desempaquetarlo como si fuera una tupla. `tests/test_migrar_core.py` verifica
    que las claves de acá sigan estando en la función.
    """

    artist: str
    channel_title: str
    tracks: list[Track]
    distribs: dict[str, dict[str, int]]
    total_views: int
    units: int
    codes: dict[str, object] | None

    # Diagnóstico del canal. Sin esto la app no puede contar que cambió de canal
    # ni que descartó videos, y el cambio ocurriría a espaldas del usuario.
    es_topic: bool
    cobertura_metadata: float
    topic_sugerido: TopicSugerido | None
    via_topic: bool
    canal_pedido: str
    descartados: int


class Diagnostico(TypedDict):
    """El subconjunto del relevamiento que `migrar_core` le pasa a la interfaz."""

    es_topic: bool
    cobertura_metadata: float
    topic_sugerido: TopicSugerido | None
    canal: str
    via_topic: bool
    canal_pedido: str
    descartados: int


class EntornoAudio(TypedDict):
    """Qué puede hacer esta máquina, según `audio.verificar_entorno`.

    La interfaz no ofrece opciones que no puedan funcionar, así que estos
    booleanos son los que deciden qué ve el usuario.
    """

    ffmpeg: bool
    ffmpeg_incluido: bool
    ffprobe: bool
    js_runtime: str | bool | None
    tiddl: bool
    yt_dlp: bool
    puede_flac: bool
    puede_referencia: bool
