"""
Backend de la app de escritorio: servidor HTTP local + API JSON.

Usa `http.server` de la biblioteca estándar a propósito, en vez de FastAPI o
Flask. Es una app local de un solo usuario, así que no necesitamos ni ASGI ni
workers, y en cambio ganamos lo que más importa para empaquetar: **cero
dependencias nuevas**. El ejecutable queda chico y PyInstaller no tiene que
resolver los imports dinámicos de uvicorn, que son la causa habitual de que un
binario ande en desarrollo y falle empaquetado.

SEGURIDAD
---------
El servidor escucha sólo en 127.0.0.1, pero eso por sí solo no alcanza. Un
servidor local sin más protección lo puede usar **cualquier página web abierta
en el navegador de esa misma máquina**: le manda pedidos a localhost y, como el
navegador adjunta la petición igual, termina operando la app del usuario. Tres
defensas, las tres baratas y con test:

  1. **Token de sesión.** Se genera uno nuevo en cada arranque, se inyecta en
     index.html y toda ruta /api/ lo exige en la cabecera X-App-Token. Una
     página externa no puede leerlo, porque el origen es distinto y la política
     del navegador se lo impide.
  2. **Cabecera Host.** Se acepta sólo 127.0.0.1, localhost o [::1]. Eso corta
     el rebinding de DNS, que es la vuelta clásica para saltear la defensa
     anterior.
  3. **CSP.** La página no puede pedir ni ejecutar nada de afuera. Las dos
     primeras cortan a quien quiere entrar; ésta, a lo que la app muestra, que
     viene de YouTube, Deezer y Apple y no tiene que poder traer un script.

Encima de las tres, capas que suman y no reemplazan: `Sec-Fetch-Site` y
`Origin`, y las cabeceras que impiden meter la app en un iframe. Contra quién
existe cada cosa, y qué queda afuera a propósito, está en docs/AMENAZAS.md.

Endpoints:
  GET  /                      la interfaz
  GET  /<archivo>             estáticos (js, css, fuentes, assets)
  GET  /api/config            capacidades del entorno y estado de la clave
  GET  /api/actualizacion     si hay una versión más nueva publicada
  POST /api/actualizacion/abrir  abre la página de descargas en el navegador
  POST /api/terminos          aceptación de los términos de uso
  POST /api/clave             guardar la clave de YouTube
  POST /api/relevar           {url, con_codigos, de_cero} -> {job}    (asincrónico)
  POST /api/validar           {ids} -> hallazgos               (sincrónico)
  POST /api/editar            un ISRC, un UPC o los campos a completar -> catálogo
  POST /api/importar          {nombre, contenido} la planilla de la distribuidora -> propuesta
  POST /api/importar/aplicar  {id, elegidos, elecciones} -> catálogo
  POST /api/abrir             {contenido} un relevamiento guardado -> catálogo
  POST /api/comparar          {contenido} un relevamiento guardado -> comparación con el de ahora
  POST /api/preparar          {ids, opciones} -> {job}        (asincrónico)
  GET  /api/job/<id>          estado del trabajo
  POST /api/job/<id>/cancelar
  POST /api/descargar/<id>    pide un ticket de un solo uso para bajar el ZIP
  GET  /api/descargar/<id>    baja el ZIP (streaming), con la cabecera del token
  GET  /descargar/<ticket>    baja el ZIP con el ticket: es lo que usa el botón
  POST /api/guardar/<id>      copia el ZIP a la carpeta Descargas (ventana de macOS)
  POST /api/mostrar           muestra en su carpeta un paquete ya guardado
  POST /api/tidal/...         conexión opcional de Tidal
"""

import base64
import binascii
import json
import mimetypes
import os
import posixpath
import re
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, TypedDict, cast, override

# `app/` consume el paquete `migrador`, que vive en `src/`. Los dos caminos
# tienen que andar: corriendo desde el repositorio sin instalar nada, y adentro
# del ejecutable de PyInstaller, donde todo se extrae junto a `sys._MEIPASS`.
#
# `src` va PRIMERO en el path a propósito. Si en algún momento quedara una
# carpeta llamada `migrador` en otro lado del path (el workpath de PyInstaller
# se llamaba así hasta hace poco), Python la tomaría como paquete de espacio de
# nombres y se importaría eso en vez de esto, con un error incomprensible.
_AQUI = os.path.dirname(os.path.abspath(__file__))
_RAIZ = os.path.dirname(_AQUI)
for _p in (_AQUI, os.path.join(_RAIZ, "src"), _RAIZ):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from jobs import Ocupado, Registry  # noqa: E402
from migrador import audio as audio_mod  # noqa: E402
from migrador import completitud as completitud_mod  # noqa: E402
from migrador import ediciones as ED  # noqa: E402
from migrador import evidencia as EV  # noqa: E402
from migrador import i18n  # noqa: E402
from migrador import importar as IMP  # noqa: E402
from migrador import instantanea as INS  # noqa: E402
from migrador import migrar_core as M  # noqa: E402
from migrador import productos as P  # noqa: E402
from migrador import relevar_core as R  # noqa: E402
from migrador import validar as V  # noqa: E402
from migrador.contratos import EntornoAudio, PaqueteListo, Producto, ValidacionParaUI  # noqa: E402
from migrador.i18n import T  # noqa: E402
from migrador.texto import mmss as _mmss  # noqa: E402
from migrador.version import VERSION  # noqa: E402

# `VERSION` se reexporta acá porque medio código la busca en el servidor, pero
# vive en `migrador/version.py`, que es el único lugar donde está escrita.
__all__ = ["VERSION"]

# El nombre se pide a i18n en el momento de usarlo y no se guarda en una
# constante: el idioma se elige en caliente.

# Versión de los términos de uso. Si cambian de fondo se sube el número y la app
# los vuelve a pedir una vez; los cambios de redacción no lo tocan.
TERMINOS_VERSION = "1.0"

# Token de esta sesión. Nuevo en cada arranque: no se guarda en ningún lado, así
# que no hay nada que se pueda filtrar entre una ejecución y la siguiente.
TOKEN = secrets.token_urlsafe(24)

# Hosts que aceptamos en la cabecera Host. Cualquier otro nombre significa que
# alguien resolvió un dominio propio a 127.0.0.1 para hablarle a la app.
# Como llegan en la cabecera Host, sin el puerto. IPv6 va entre corchetes
# («[::1]:8000»); un «::1» suelto no puede llegar nunca, porque sin corchetes no
# se distingue del puerto. `Origin` lo trae sin corchetes y se los agrega quien
# lo compara (`_origen_propio`).
HOSTS_VALIDOS = ("127.0.0.1", "localhost", "[::1]")


def _audio_habilitado():
    """El módulo de audio viene apagado salvo que se pida explícitamente.

    Dos formas de prenderlo, y aun así sólo aparece si el entorno lo soporta:
      - MIGRADOR_AUDIO=1 al correr desde el código;
      - el archivo CON_AUDIO que deja adentro el build `--con-audio`, porque un
        ejecutable que se abre con doble clic no puede recibir variables de
        entorno.
    """
    if os.environ.get("MIGRADOR_AUDIO", "").strip().lower() in ("1", "true", "si", "sí"):
        return True
    return os.path.exists(os.path.join(_base_recursos(), "CON_AUDIO"))


def _base_recursos():
    """Carpeta donde viven los archivos de la interfaz.

    Empaquetado con PyInstaller los datos se extraen a `sys._MEIPASS`, que no
    coincide con la ubicación del módulo. Sin este ajuste la app anda en
    desarrollo y sirve 404 en el ejecutable.
    """
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", _AQUI)
    return _AQUI


WEB_DIR = os.path.join(_base_recursos(), "web")
AUDIO_HABILITADO = _audio_habilitado()
MAX_BODY = 8 * 1024 * 1024  # 8 MB: los payloads son listas de ids
# Al cerrar una conexión cuyo pedido no se leyó entero, cuánto se espera a que
# el cliente termine de mandar y cuánto se le descarta (ver `Handler.finish`).
ESPERA_CIERRE = 0.3  # segundos sin que llegue nada
TOPE_CIERRE = 2.0  # segundos en total

# Cuánto vale un ticket de descarga. Se pide en el momento del clic, así que un
# minuto sobra; más largo sólo agranda la ventana en que una URL copiada sirve.
TICKET_TTL = 60.0

# Espacio libre mínimo antes de empezar a armar un paquete. Con audio un
# catálogo entero puede pasar los 2 GB, y quedarse sin disco a mitad deja el ZIP
# corrupto y sin explicación.
MIN_LIBRE_BASE = 300 * 1024 * 1024
MIN_LIBRE_AUDIO = 3 * 1024 * 1024 * 1024


def dir_datos():
    """Carpeta de la app en el home del usuario, para la clave y los temporales.

    Se crea cerrada, 0700, y no se abre después: ahí vive la clave de YouTube que
    carga el usuario. En Windows el modo no hace nada y lo que protege es el ACL
    del perfil, que ya es sólo de su dueño.
    """
    base = os.path.join(os.path.expanduser("~"), ".migrador-catalogos")
    os.makedirs(base, mode=0o700, exist_ok=True)
    return base


# ============================================================
# Config del usuario (clave de YouTube + aceptación de términos)
# ============================================================


def _ruta_config():
    return os.path.join(dir_datos(), "config.json")


def leer_config():
    """La config del usuario, o {} si no existe o está rota.

    Nunca levanta: un config.json corrupto tiene que degradar a "no hay nada
    guardado", no impedir que la app arranque.
    """
    p = _ruta_config()
    if not os.path.exists(p):
        return {}
    try:
        with open(p, encoding="utf-8") as f:
            datos = json.load(f)
        return datos if isinstance(datos, dict) else {}
    except (OSError, ValueError):
        return {}


def guardar_config(cambios):
    """Escribe la config de forma atómica.

    Primero a un archivo temporal y después `os.replace`, que en todos los
    sistemas es atómico. Escribir directo sobre el destino significa que un corte
    de luz a mitad del write deja un JSON truncado, y con él la clave perdida.
    """
    datos = leer_config()
    datos.update(cambios)
    destino = _ruta_config()
    tmp = destino + ".tmp"
    # El temporal nace con 0600. Antes se creaba con los permisos por defecto y
    # el chmod llegaba después del replace, así que en un sistema con varios
    # usuarios la clave quedaba legible por los demás durante esa ventana.
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, destino)
    try:
        os.chmod(destino, 0o600)  # un config viejo, de antes de esto, también se cierra
    except OSError:
        pass
    return datos


def _clave_incluida():
    """Clave de YouTube que viene dentro del ejecutable, o "".

    Existe para la variante `completa` de los releases: build/build.py
    --con-clave mete una clave adentro del binario, así quien lo baja lo abre y
    funciona sin crear su propio proyecto en Google Cloud.

    Va guardada con un XOR simple, que NO es seguridad: cualquiera con el
    ejecutable la puede sacar. Sólo evita que aparezca en un `strings` del
    binario y que la levante un scraper automático. Por eso la clave nunca está
    en el repositorio: vive como secreto del CI y entra recién al compilar.
    """
    ruta = os.path.join(_base_recursos(), "clave_yt.dat")
    if not os.path.exists(ruta):
        return ""
    try:
        with open(ruta, "rb") as f:
            datos = f.read()
        if len(datos) < 2:
            return ""
        semilla, cuerpo = datos[0], datos[1:]
        return bytes(b ^ semilla for b in cuerpo).decode("utf-8").strip()
    except (OSError, UnicodeDecodeError):
        return ""


def leer_clave():
    """Devuelve la clave de YouTube a usar.

    Orden de prioridad, de más específico a más general:
      1. la variable de entorno YOUTUBE_API_KEY;
      2. la que el usuario cargó en la app (queda en su carpeta personal);
      3. la que viene dentro del ejecutable, si es la variante con clave.

    Así, aunque el binario traiga una clave, quien quiera usar la propia la carga
    en la app y esa gana.
    """
    k = os.environ.get("YOUTUBE_API_KEY", "").strip()
    if k:
        return k
    propia = (leer_config().get("youtube_api_key") or "").strip()
    if propia:
        return propia
    return _clave_incluida()


def guardar_clave(clave):
    """Guarda la clave en el home del usuario. Queda sólo en su máquina."""
    guardar_config({"youtube_api_key": (clave or "").strip()})


def terminos_aceptados():
    return leer_config().get("terminos") == TERMINOS_VERSION


class ErrorDeCampo(ValueError):
    """Un valor que mandó el usuario no sirve, y la interfaz lo muestra debajo
    del campo en vez de como error general de la pantalla.

    Hereda de ValueError a propósito: así sigue cayendo en el 400 de siempre y no
    cambia el contrato de la API. Lo único que agrega es el `codigo`, que es lo
    que mira el frontend para saber dónde poner el mensaje. Antes lo deducía
    comparando el texto en español, y con la app en inglés dejaba de funcionar.
    """

    def __init__(self, mensaje, codigo="url"):
        super().__init__(mensaje)
        self.codigo = codigo


def idioma_del_instalador():
    """El idioma que eligió quien instaló la app, o "".

    El instalador de Windows deja un `idioma.txt` al lado del ejecutable con
    "es" o "en". Se usa sólo como valor inicial: apenas el usuario toca el
    selector de la cabecera, su elección queda en la config y manda.
    """
    base = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else _RAIZ
    try:
        with open(os.path.join(base, "idioma.txt"), encoding="utf-8") as f:
            v = f.read().strip().lower()[:2]
        return v if v in i18n.IDIOMAS else ""
    except OSError:
        return ""


def idioma_guardado():
    """El idioma que corresponde usar, y lo deja puesto en `i18n`.

    Orden de prioridad, de más específico a más general:

      1. la variable `MIGRADOR_IDIOMA`, que fuerza uno y gana siempre;
      2. el que el usuario eligió en la app y quedó en su config;
      3. el que eligió en el instalador, que dejó un idioma.txt al lado del exe;
      4. el que dice el sistema operativo.

    Los puntos 3 y 4 no se guardan en la config: son valores iniciales, no una
    decisión del usuario. Guardarlos haría que el selector arrancara mostrando
    como elegido algo que nadie eligió.
    """
    forzado = i18n.idioma_forzado()
    if forzado:
        return i18n.poner_idioma(forzado)
    guardado = (leer_config().get("idioma") or "").strip().lower()
    if guardado in i18n.IDIOMAS:
        return i18n.poner_idioma(guardado)
    return i18n.poner_idioma(idioma_del_instalador() or i18n.idioma_del_sistema())


# ============================================================
# Entorno de audio, cacheado
# ============================================================


class _CacheEntorno(TypedDict):
    valor: EntornoAudio | None
    cuando: float


_ENTORNO: _CacheEntorno = {"valor": None, "cuando": 0.0}
_ENTORNO_LOCK = threading.Lock()
_ENTORNO_TTL = 60.0


def entorno_audio(forzar=False):
    """`audio.verificar_entorno()` con caché corta.

    El frontend consulta /api/config seguido, y cada llamada recorre el PATH
    buscando ffmpeg y ffprobe. Es barato, pero no gratis, y no hay ninguna razón
    para hacerlo cincuenta veces por minuto. Igual se revalida cada minuto, así
    que instalar ffmpeg con la app abierta se nota sin reiniciar.
    """
    with _ENTORNO_LOCK:
        ahora = time.monotonic()
        if forzar or _ENTORNO["valor"] is None or ahora - _ENTORNO["cuando"] > _ENTORNO_TTL:
            try:
                _ENTORNO["valor"] = audio_mod.verificar_entorno()
            except Exception:  # noqa: BLE001
                # Si la detección falla, la app tiene que seguir andando sin
                # audio, no romperse entera.
                _ENTORNO["valor"] = {
                    "ffmpeg": False,
                    "ffmpeg_incluido": False,
                    "ffprobe": False,
                    "js_runtime": False,
                    "tiddl": False,
                    "yt_dlp": False,
                    "puede_flac": False,
                    "puede_referencia": False,
                }
            _ENTORNO["cuando"] = ahora
        return _ENTORNO["valor"]


# ============================================================
# Temporales viejos
# ============================================================

PREFIJOS_TEMP = ("migrador_zip_", "migrador_audio_", "migrador_tidal_")


def limpiar_temporales_viejos(horas=12):
    """Borra temporales que quedaron de una ejecución que terminó mal.

    Si la app se cierra de golpe (o la mata el sistema), los ZIP y los audios a
    medio bajar quedan en el temporal del sistema y nadie los saca nunca. Se
    borran sólo los de más de 12 horas, para no pisar los de otra instancia que
    esté corriendo ahora mismo.
    """
    corte = time.time() - horas * 3600
    base = tempfile.gettempdir()
    borrados = 0
    try:
        nombres = os.listdir(base)
    except OSError:
        return 0
    for n in nombres:
        if not n.startswith(PREFIJOS_TEMP):
            continue
        ruta = os.path.join(base, n)
        try:
            if os.path.isdir(ruta) and os.path.getmtime(ruta) < corte:
                shutil.rmtree(ruta, ignore_errors=True)
                borrados += 1
        except OSError:
            continue
    return borrados


# ============================================================
# Estado de la sesión
# ============================================================


class Estado:
    """Estado del catálogo en curso. Vive en memoria: al cerrar la app se va."""

    def __init__(self):
        self.productos = []
        self.artista = ""
        self.diagnostico = {}
        # Cambia con cada relevamiento. Los ids de producto son posicionales
        # (p001, p002…) y se regeneran, así que una pestaña que quedó con el
        # catálogo de antes pedía el ZIP de otro artista con sus ids viejos.
        self.catalogo_id = ""
        # La propuesta de la última planilla importada, hasta que se aplique o
        # se descarte: {"id", "catalogo_id", "propuesta"}. Una sola por vez.
        self.importacion: dict[str, Any] | None = None
        # Sin anotar, el tipo deducido sería None y guardar la sesión daría
        # error de tipos. Se escribe suelto para no importar `audio` acá.
        self.tidal: "audio_mod.TidalSession | None" = None
        self.zips = {}  # job_id -> ruta del zip
        self.guardados = set()  # rutas de los paquetes guardados en Descargas
        self.tickets = {}  # ticket -> (job_id, vence), ver emitir_ticket
        self.temporales = []
        # Cuándo latió por última vez alguna ventana (`time.monotonic()`), o None
        # si todavía no abrió ninguna. Lo mira el launcher para cerrar el
        # servidor cuando la app corre en el navegador y ya no queda ninguna.
        self.ultimo_latido: float | None = None
        self.lock = threading.RLock()

    def por_ids(self, ids):
        """Los productos elegidos. Sin ids, ninguno.

        Una lista vacía significaba «todos»: un pedido que llegara sin ids por
        error armaba el paquete del catálogo entero. La interfaz nunca lo manda
        así, pero es una trampa para el próximo que toque la API.
        """
        if not ids:
            return []
        with self.lock:
            productos = list(self.productos)
        return P.filter_products(productos, ids=ids)

    def guardar_catalogo(self, prods, artista, diag):
        with self.lock:
            self.productos = prods
            self.artista = artista
            self.diagnostico = diag
            self.catalogo_id = secrets.token_hex(6)
            # La propuesta de una planilla era sobre el catálogo de antes.
            self.importacion = None

    def zips_anteriores(self):
        """Borra los ZIP de paquetes anteriores. Se llama al armar uno nuevo: la
        interfaz sólo ofrece bajar el último, y con audio cada uno pesa GB."""
        with self.lock:
            viejos, self.zips = list(self.zips.values()), {}
        for ruta in viejos:
            shutil.rmtree(os.path.dirname(ruta), ignore_errors=True)

    def registrar_zip(self, job_id, ruta):
        with self.lock:
            self.zips[job_id] = ruta

    def registrar_temporal(self, ruta):
        with self.lock:
            self.temporales.append(ruta)

    def zip_de(self, job_id):
        with self.lock:
            return self.zips.get(job_id)

    def emitir_ticket(self, job_id, ttl=TICKET_TTL):
        """Un ticket de un solo uso para bajar el ZIP de `job_id`.

        Existe porque el botón de descarga es un enlace, y un enlace no puede
        mandar la cabecera `X-App-Token`: el ZIP daba 403 desde la interfaz
        desde la primera versión. Eximir la descarga del token habría abierto
        la primera defensa. El ticket no la abre, porque sólo se consigue con un
        POST que sí lleva el token, así que una página ajena no tiene cómo
        obtenerlo. Vale una vez y por un minuto, y la ruta que lo canjea sigue
        pasando por el control de Host.
        """
        ticket = secrets.token_urlsafe(24)
        with self.lock:
            ahora = time.monotonic()
            self.tickets = {k: v for k, v in self.tickets.items() if v[1] > ahora}
            self.tickets[ticket] = (job_id, ahora + ttl)
        return ticket

    def canjear_ticket(self, ticket):
        """El job_id del ticket, o None si no existe, ya se usó o venció."""
        with self.lock:
            dato = self.tickets.pop(ticket, None)
        if not dato:
            return None
        job_id, vence = dato
        return job_id if time.monotonic() <= vence else None

    def olvidar_zip(self, job_id):
        """Se llama cuando el trabajo se descarta del registro. Sin esto, cada
        paquete generado deja su ZIP en el disco hasta que se cierra la app, y
        una sesión larga con audio llena el temporal sin que nadie se entere."""
        with self.lock:
            ruta = self.zips.pop(job_id, None)
        if ruta:
            shutil.rmtree(os.path.dirname(ruta), ignore_errors=True)

    def limpiar(self):
        with self.lock:
            tidal, temporales, zips = self.tidal, self.temporales, self.zips
            self.tidal, self.temporales, self.zips, self.tickets = None, [], {}, {}
        if tidal:
            try:
                tidal.close()
            except Exception:  # noqa: BLE001
                pass
        for d in temporales:
            shutil.rmtree(d, ignore_errors=True)
        for ruta in zips.values():
            shutil.rmtree(os.path.dirname(ruta), ignore_errors=True)


ESTADO = Estado()
JOBS = Registry(al_descartar=lambda job_id: ESTADO.olvidar_zip(job_id))


# ============================================================
# Serialización para el frontend
# ============================================================


def producto_json(p):
    """Un producto tal como lo consume la tabla del frontend."""
    return {
        "id": p["product_id"],
        "titulo": p.get("title", ""),
        "tipo": p.get("kind", ""),
        "anio": p.get("release_year") or "",
        "fecha": p.get("release_date") or "",
        "upc": p.get("upc") or "",
        "sello": p.get("label") or "",
        "distribuidora": p.get("distributor") or "",
        "tracks": p.get("track_count", 0),
        "views": p.get("total_views", 0),
        "orden_estimado": bool(p.get("order_unconfirmed")),
        "con_isrc": sum(1 for t in p.get("tracks", []) if t.get("isrc")),
        # Los temas que este release tiene en Deezer y no aparecieron en YouTube.
        "faltan": list(p.get("faltan_temas") or []),
        # Lo que no se vio en YouTube y se sumó de Deezer: el release entero
        # ("deezer") o algunos de sus temas (`de_deezer`). `artista` es a nombre
        # de quién queda, que en una colaboración no es el del canal.
        "origen": p.get("origen") or "",
        "de_deezer": int(p.get("de_deezer") or 0),
        "artista": p.get("artist") or "",
        # Qué tan comprobados están los códigos (ver `evidencia`), y lo que
        # cargó el usuario (ver `ediciones`).
        "upc_nivel": p.get("upc_nivel") or "",
        "upc_editado": "upc_previo" in p,
        "sin_confirmar": int(p.get("isrc_sin_confirmar") or 0),
        "datos": dict(p.get("datos") or {}),
        "detalle": [
            {
                "n": t.get("track_number") or "",
                "titulo": t.get("track", ""),
                "isrc": t.get("isrc") or "",
                "duracion": _mmss(t.get("duration_s")),
                "views": t.get("views", 0),
                "url": t.get("url", ""),
                "origen": t.get("origen") or "",
                "nivel": t.get("isrc_nivel") or "",
                "editado": "isrc_previo" in t,
                "candidatos": [
                    {"isrc": c.get("isrc", ""), "duracion": _mmss(c.get("duracion_s"))}
                    for c in (t.get("isrc_candidatos") or [])
                ],
            }
            for t in p.get("tracks", [])
        ],
    }


def catalogo_json(productos, artista, diag=None):
    desde, hasta = P.year_range(productos)
    return {
        "catalogo_id": ESTADO.catalogo_id,
        "artista": artista,
        "diagnostico": diag or {},
        "productos": [producto_json(p) for p in productos],
        "resumen": P.summarize(productos),
        "evidencia": EV.resumen(productos),
        # Los campos que el usuario puede cargar, en el orden de la hoja.
        "campos": list(ED.CAMPOS_A_COMPLETAR),
        "filtros": {
            "distribuidoras": P.distributor_options(productos),
            "anio_min": desde,
            "anio_max": hasta,
        },
    }


# ============================================================
# Handlers de la API
# ============================================================


def carpeta_descargas():
    """La carpeta de descargas del usuario, o su carpeta personal si no la hay."""
    casa = os.path.expanduser("~")
    for nombre in ("Downloads", "Descargas"):
        ruta = os.path.join(casa, nombre)
        if os.path.isdir(ruta):
            return ruta
    return casa


def guardar_en_descargas(ruta_zip):
    """Copia el paquete a la carpeta de descargas y devuelve dónde quedó.

    Existe porque bajar un archivo depende de la ventana, y la de macOS
    descarta la descarga sin avisar: la página pedía el ZIP, el servidor lo
    entregaba y no pasaba nada, ni un cuadro de «Guardar». La app corre en la
    máquina del usuario, así que el servidor puede dejar el archivo en su lugar
    sin pasar por la ventana.

    Nunca pisa un archivo: si el nombre está tomado, le agrega un número.
    """
    carpeta = carpeta_descargas()
    base, ext = os.path.splitext(os.path.basename(ruta_zip))
    destino, n = os.path.join(carpeta, base + ext), 1
    while os.path.exists(destino):
        n += 1
        destino = os.path.join(carpeta, f"{base} ({n}){ext}")
    # A un nombre provisorio y después al definitivo: si la copia se corta, no
    # queda en Descargas un ZIP a medias con el nombre del paquete.
    parcial = destino + ".parcial"
    try:
        shutil.copyfile(ruta_zip, parcial)
        os.replace(parcial, destino)
    except OSError:
        if os.path.exists(parcial):
            os.remove(parcial)
        raise
    with ESTADO.lock:
        ESTADO.guardados.add(destino)
    return destino


def mostrar_en_carpeta(ruta):
    """Abre el administrador de archivos con ese archivo a la vista."""
    if sys.platform == "darwin":
        orden = ["open", "-R", ruta]
    elif sys.platform.startswith("win"):
        orden = ["explorer", f"/select,{ruta}"]
    else:
        orden = ["xdg-open", os.path.dirname(ruta)]
    subprocess.Popen(orden, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)  # noqa: S603


def api_mostrar(body):
    """Muestra en su carpeta un paquete que esta sesión guardó. Sólo ésos: la
    ruta viene de la página, y no se abre cualquier cosa que ella pida."""
    ruta = str((body or {}).get("ruta") or "")
    with ESTADO.lock:
        propio = ruta in ESTADO.guardados
    if not propio or not os.path.exists(ruta):
        raise ValueError(T("srv.guardado_no_esta"))
    try:
        mostrar_en_carpeta(ruta)
    except OSError as e:
        raise ValueError(T("srv.no_se_pudo_mostrar", detalle=e)) from e
    return {"ok": True}


def sistema():
    """'windows', 'mac' o 'linux', que es lo único que la interfaz necesita."""
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform == "darwin":
        return "mac"
    return "linux"


def api_config():
    # El frontend pasa por acá al abrir y después de cada operación larga: es el
    # mejor lugar para descartar trabajos vencidos y los ZIP que dejaron.
    JOBS.limpiar()
    return {
        "version": VERSION,
        # El idioma se resuelve en cada /api/config y no una sola vez al
        # arrancar: es lo que hace que un cambio quede aplicado también del lado
        # de Python, que es quien escribe el log y los archivos del ZIP.
        "idioma": idioma_guardado(),
        "idiomas": list(i18n.IDIOMAS),
        "terminos_aceptados": terminos_aceptados(),
        "terminos_version": TERMINOS_VERSION,
        "tiene_clave": bool(leer_clave()),
        # Para poder aclarar en la interfaz que está usando una clave incluida y
        # no la propia.
        "clave_incluida": (
            bool(_clave_incluida())
            and not os.environ.get("YOUTUBE_API_KEY", "").strip()
            and not (leer_config().get("youtube_api_key") or "").strip()
        ),
        "audio_habilitado": AUDIO_HABILITADO,
        # Para dar la instrucción de instalación que corresponde: `winget` en una
        # Mac es una instrucción que no se puede seguir.
        "sistema": sistema(),
        "entorno": entorno_audio(),
        "tidal_conectada": bool(ESTADO.tidal and ESTADO.tidal.conectada),
        "catalogo_cargado": bool(ESTADO.productos),
        "trabajo_en_curso": bool(JOBS.activos()),
    }


def api_idioma(body):
    """Cambia el idioma y lo deja guardado.

    Lo aplica además en `i18n` acá mismo, porque el próximo mensaje del log o el
    próximo ZIP se arman de este lado y tienen que salir ya en el idioma nuevo.
    """
    pedido = (body.get("idioma") or "").strip().lower()
    if pedido not in i18n.IDIOMAS:
        raise ValueError(T("server.idioma_invalido", idiomas=", ".join(i18n.IDIOMAS)))
    guardar_config({"idioma": pedido})
    return {"ok": True, "idioma": i18n.poner_idioma(pedido)}


def api_terminos(body):
    if not body.get("aceptar"):
        raise ValueError(T("srv.aceptar_terminos"))
    guardar_config({"terminos": TERMINOS_VERSION})
    return {"ok": True}


def api_guardar_clave(body):
    clave = (body.get("clave") or "").strip()
    if not clave:
        raise ErrorDeCampo(T("srv.pega_clave"), "clave")
    if len(clave) > 200 or "\n" in clave:
        raise ErrorDeCampo(T("srv.clave_rara"), "clave")
    # Validación real: pegamos una consulta mínima antes de darla por buena, así
    # el usuario se entera acá y no a mitad de un relevamiento.
    try:
        R.api_get("channels", {"part": "id", "id": "UC_x5XG1OV2P6uZZ5FSM9Ttw"}, clave)
    except Exception as e:  # noqa: BLE001
        # Sólo si YouTube contestó es un problema de la clave. Si ni siquiera se
        # llegó (sin red, certificado rechazado), la clave no se llegó a probar.
        sin_probar = getattr(e, "codigo", "") == "red"
        raise ValueError(T("srv.clave_sin_probar" if sin_probar else "srv.clave_no_funciono", error=e)) from e
    guardar_clave(clave)
    return {"ok": True}


def _mismo_catalogo(body):
    """Que el pedido hable del catálogo que está en memoria.

    Si viene un `catalogo_id` y no es el de ahora, otra pestaña relevó otro
    artista mientras tanto, y los ids que trae son de aquel catálogo. Sin id se
    acepta, como hasta ahora: es lo que mandan los scripts y los tests.
    """
    pedido = body.get("catalogo_id")
    if pedido and pedido != ESTADO.catalogo_id:
        raise ErrorDeCampo(T("srv.catalogo_cambio"), "catalogo")


def _sin_trabajo_en_curso():
    """Un trabajo largo por vez.

    Dos relevamientos simultáneos gastan cuota de YouTube por duplicado y
    escriben sobre el mismo catálogo en memoria, así que el segundo pisa al
    primero y el resultado depende de cuál termine último. Es más honesto
    negarlo con un mensaje que dejar que pase.
    """
    if JOBS.activos():
        raise ValueError(T("srv.trabajo_en_curso"))


def api_relevar(body):
    url = (body.get("url") or "").strip()
    # Van con código "url" y no como ValueError pelado: la interfaz los muestra
    # debajo del campo en vez de como error general, y para decidirlo mira el
    # código. Antes comparaba el texto del mensaje, que con la app en inglés
    # dejaba de coincidir.
    if not url:
        raise ErrorDeCampo(T("server.falta_url"))
    if len(url) > 2048:
        raise ErrorDeCampo(T("server.url_larga"))
    # El estado del servidor se mira antes que la configuración: si ya hay algo
    # corriendo, eso es lo que hay que decir, y además así el rechazo no depende
    # de si la clave está cargada o no.
    _sin_trabajo_en_curso()
    clave = leer_clave()
    if not clave:
        raise ValueError(T("srv.falta_clave"))
    con_codigos = bool(body.get("con_codigos", True))
    # Volver a listar el canal aunque ya se haya listado en esta sesión. Lo
    # pide el botón «Volver a listar», para quien sabe que el canal cambió.
    de_cero = bool(body.get("de_cero", False))
    # El perfil del artista en Deezer, cuando lo indica el usuario: es la
    # salida para cuando la app no lo encuentra sola, o elige a un homónimo.
    pegado = str(body.get("deezer_artista") or "").strip()[:2048]
    artista_deezer = R.id_de_artista_deezer(pegado) if pegado else 0
    if pegado and not artista_deezer:
        raise ErrorDeCampo(T("srv.deezer_link_invalido"), "deezer")

    def trabajo(job):
        prods, artista, _, diag = M.relevar_catalogo(
            url,
            clave,
            with_codes=con_codigos,
            progress=lambda m, f=None: job.avance(m, f),
            fraccion=job.fraccion,
            reusar=not de_cero,
            artista_deezer=artista_deezer,
        )
        ESTADO.guardar_catalogo(prods, artista, diag)
        texto = "srv.productos_encontrados_uno" if len(prods) == 1 else "srv.productos_encontrados"
        job.avance(T(texto, n=len(prods)), 1.0)
        return catalogo_json(prods, artista, diag)

    return {"job": _lanzar("relevar", trabajo).a_dict()}


def _lanzar(tipo, trabajo):
    """Lanza un trabajo largo, uno por vez, sin carrera (ver `Registry.lanzar`)."""
    try:
        return JOBS.lanzar(tipo, trabajo, exclusivo=True)
    except Ocupado:
        raise ValueError(T("srv.trabajo_en_curso")) from None


def api_validar(body) -> ValidacionParaUI:
    _mismo_catalogo(body)
    sel = ESTADO.por_ids(body.get("ids"))
    if not sel:
        raise ValueError(T("srv.sin_seleccion"))
    res = V.validar(sel, ESTADO.artista)
    return {
        "apto": res["apto"],
        "resumen": res["resumen"],
        "hallazgos": res["hallazgos"],
    }


# ============================================================
# Lo que carga el usuario: códigos, datos y archivos
# ============================================================


def _catalogo_actual() -> dict[str, Any]:
    return catalogo_json(ESTADO.productos, ESTADO.artista, ESTADO.diagnostico)


def _para_editar(body):
    """Lo común a todo lo que cambia el catálogo: que sea el de ahora, que
    exista, y que no se esté armando un paquete con él en este momento."""
    _mismo_catalogo(body)
    if not ESTADO.productos:
        raise ValueError(T("srv.sin_catalogo"))
    _sin_trabajo_en_curso()


def api_editar(body) -> dict[str, Any]:
    """Un cambio hecho a mano sobre el catálogo. Devuelve el catálogo entero.

    `tipo` dice qué: "isrc" y "upc" cargan un código (vacío, lo restauran),
    "datos" carga los campos a completar en los productos de `ids`. Lo que no
    se puede aceptar levanta `EdicionInvalida`, que es un ValueError y llega a
    la interfaz como un 400 con su mensaje.
    """
    _para_editar(body)
    tipo = body.get("tipo")
    with ESTADO.lock:
        productos = ESTADO.productos
        if tipo == "isrc":
            ED.poner_isrc(productos, body.get("producto"), body.get("indice"), body.get("valor"))
        elif tipo == "upc":
            ED.poner_upc(productos, body.get("producto"), body.get("valor"))
        elif tipo == "datos":
            datos = body.get("datos")
            ids = body.get("ids")
            if not isinstance(datos, dict) or not isinstance(ids, list):
                raise ValueError(T("srv.json_invalido"))
            datos = {str(k): v for k, v in datos.items() if isinstance(v, str)}
            ED.poner_datos(productos, [str(i) for i in ids], datos)
            if body.get("c_sugerida"):
                # La línea © armada con el año y el titular de cada producto:
                # no es un valor para todos, es uno por release.
                for p in productos:
                    if p["product_id"] in ids and ED.sugerir_linea_c(p):
                        ED.poner_datos([p], [p["product_id"]], {"c_line": ED.sugerir_linea_c(p)})
        else:
            raise ValueError(T("srv.json_invalido"))
    return _catalogo_actual()


def _archivo(body, tope):
    """Los bytes del archivo que mandó la interfaz, en base64.

    Viene adentro del JSON y no como un upload aparte para que pase por las
    mismas tres defensas que cualquier otro pedido, sin una ruta que las
    saltee. El tope se controla antes de decodificar.
    """
    contenido = body.get("contenido")
    if not isinstance(contenido, str) or not contenido:
        raise ValueError(T("srv.archivo_vacio"))
    if len(contenido) > tope * 4 // 3 + 16:
        raise ValueError(T("srv.archivo_grande"))
    try:
        return base64.b64decode(contenido, validate=True)
    except (ValueError, binascii.Error):
        raise ValueError(T("srv.archivo_vacio")) from None


def api_importar(body) -> dict[str, Any]:
    """Lee la planilla de la distribuidora y propone qué hacer. No cambia nada."""
    _para_editar(body)
    datos = _archivo(body, IMP.MAX_BYTES)
    filas, columnas = IMP.leer(datos, str(body.get("nombre") or "")[:200])
    with ESTADO.lock:
        propuesta = IMP.conciliar(ESTADO.productos, filas)
        importacion_id = secrets.token_hex(6)
        ESTADO.importacion = {"id": importacion_id, "catalogo_id": ESTADO.catalogo_id, "propuesta": propuesta}
    return {
        "id": importacion_id,
        "nombre": str(body.get("nombre") or "")[:200],
        "columnas": columnas,
        "elegidos": IMP.elegidos_por_defecto(propuesta),
        **propuesta,
    }


def api_importar_aplicar(body) -> dict[str, Any]:
    _para_editar(body)
    with ESTADO.lock:
        imp = ESTADO.importacion
        if not imp or imp["id"] != body.get("id") or imp["catalogo_id"] != ESTADO.catalogo_id:
            raise ValueError(T("srv.importacion_vencida"))
        elegidos = [str(x) for x in (body.get("elegidos") or []) if isinstance(x, str)]
        elecciones = body.get("elecciones") if isinstance(body.get("elecciones"), dict) else {}
        elecciones = {str(k): str(v) for k, v in elecciones.items()}
        hechos = IMP.aplicar(ESTADO.productos, imp["propuesta"], elegidos, elecciones)
        ESTADO.importacion = None
    return {"catalogo": _catalogo_actual(), "hechos": hechos}


def _diagnostico_de_archivo(info, productos):
    """El diagnóstico de un catálogo que se abrió de un archivo.

    No se relevó nada: no hay cuota gastada ni comparación con Deezer hecha
    ahora. `abierto` es lo que la interfaz mira para decirlo, en vez de los
    avisos del relevamiento.
    """
    con_isrc = sum(1 for p in productos for t in p["tracks"] if t.get("isrc"))
    return {
        "es_topic": True,
        "canal": info.get("canal", ""),
        "via_topic": False,
        "canal_pedido": info.get("canal", ""),
        "descartados": 0,
        "codigos": {"pedidos": True, "encontrados": con_isrc, "fallas": 0, "motivo": ""},
        "via": info.get("via") or "subidas",
        "total_estimado": 0,
        "cortado_por_cuota": False,
        "unidades": 0,
        "reusado": False,
        "sin_distribuidora": 0,
        "temas": info.get("temas") or sum(len(p["tracks"]) for p in productos),
        "completitud": completitud_mod.completitud_vacia(),
        "abierto": {"fecha": info.get("fecha", ""), "app": info.get("app", "")},
    }


def api_abrir(body) -> dict[str, Any]:
    """Reabre un relevamiento guardado en un paquete, sin pedirle nada a nadie."""
    _sin_trabajo_en_curso()
    productos, artista, info = INS.abrir(_archivo(body, INS.MAX_BYTES))
    diag = _diagnostico_de_archivo(info, productos)
    ESTADO.guardar_catalogo(productos, artista, diag)
    return catalogo_json(productos, artista, diag)


def api_comparar(body) -> dict[str, Any]:
    """Compara un relevamiento guardado contra el catálogo que está en pantalla."""
    _mismo_catalogo(body)
    if not ESTADO.productos:
        raise ValueError(T("srv.sin_catalogo"))
    antes, artista, info = INS.abrir(_archivo(body, INS.MAX_BYTES))
    with ESTADO.lock:
        comparacion = INS.comparar(antes, list(ESTADO.productos))
        ahora = ESTADO.artista
    from migrador.texto import comparable

    return {
        **comparacion,
        "fecha": info.get("fecha", ""),
        "artista": artista,
        # El archivo es de otro artista: la comparación no dice nada, y hay
        # que avisarlo antes de que alguien lea «no aparece» en cada fila.
        "otro_artista": bool(artista and ahora and comparable(artista) != comparable(ahora)),
    }


def _revisar_espacio(con_audio):
    minimo = MIN_LIBRE_AUDIO if con_audio else MIN_LIBRE_BASE
    try:
        libre = shutil.disk_usage(tempfile.gettempdir()).free
    except OSError:
        return  # si no se puede medir, seguimos
    if libre < minimo:
        raise ValueError(T("srv.poco_espacio", libre=f"{libre / 1e9:.1f}", minimo=f"{minimo / 1e9:.1f}"))


def api_preparar(body):
    _mismo_catalogo(body)
    ids = body.get("ids") or []
    sel = ESTADO.por_ids(ids)
    if not sel:
        raise ValueError(T("srv.sin_seleccion"))

    quiere_planilla = bool(body.get("planilla", True))
    quiere_portadas = bool(body.get("portadas", True))
    quiere_audio = bool(body.get("audio", False)) and AUDIO_HABILITADO
    if not (quiere_planilla or quiere_portadas or quiere_audio):
        raise ValueError(T("srv.elegi_algo"))
    _sin_trabajo_en_curso()
    _revisar_espacio(quiere_audio)

    artista = ESTADO.artista
    # El diagnóstico se toma ahora y no al empaquetar: si mientras tanto se
    # releva otro canal, el reporte tiene que hablar de éste.
    diagnostico = ESTADO.diagnostico
    ses = ESTADO.tidal if quiere_audio else None

    def trabajo(job):
        # Sobre copias: preparar() agrega bytes de portada y rutas de audio a los
        # productos, y no queremos que el catálogo en memoria se llene de eso
        # después de cada descarga.
        # `dict(p, ...)` devuelve un dict pelado y pierde el tipo del producto.
        # La forma no cambia, sólo se copia, así que se le dice al verificador
        # lo que ya sabemos en vez de aflojar la firma de `validar`.
        copias = cast("list[Producto]", [dict(p, tracks=[dict(t) for t in p["tracks"]]) for p in sel])

        job.avance(T("srv.preparando"), 0.05)
        ESTADO.zips_anteriores()
        # La carpeta del audio la crea el trabajo y no `preparar`. Si la creaba
        # `preparar`, el trabajo recién se enteraba de ella cuando volvía, y un
        # paquete cancelado a mitad de las descargas dejaba varios GB en el
        # temporal, que sólo se limpiaban doce horas después.
        dir_audio = tempfile.mkdtemp(prefix="migrador_audio_") if quiere_audio else None
        if dir_audio:
            ESTADO.registrar_temporal(dir_audio)
        carpeta = None

        # La barra va por tramos: portadas, audio y ZIP, cada uno con su parte.
        # Antes las portadas iban de 5 a 85 % y el resto no informaba nada, así
        # que con audio la barra quedaba clavada en 85 % durante la fase más
        # larga, y en 90 % mientras se escribía el ZIP.
        #
        # Las fracciones las informa cada fase con números. Antes se sacaban
        # parseando su línea de log con un `^Portada (\d+) de (\d+)`, y eso se
        # rompía apenas la app pasaba a inglés.
        ultima = {"frac": None}
        fin_portadas = 0.40 if quiere_audio else 0.85

        def en_tramo(desde, hasta):
            def avance(i, total):
                if total > 0:
                    ultima["frac"] = desde + (hasta - desde) * min(i, total) / total

            return avance

        avance_portadas = en_tramo(0.05, fin_portadas)

        def avance_preparar(m):
            if ultima["frac"] is None:
                job.avance(m)
            else:
                job.avance(m, ultima["frac"])

        try:
            _, _dir, ent = M.preparar(
                copias,
                artista,
                quiere_planilla=quiere_planilla,
                quiere_audio=quiere_audio,
                quiere_portadas=quiere_portadas,
                tidal_session=ses,
                log=avance_preparar,
                avance_portadas=avance_portadas,
                avance_audio=en_tramo(fin_portadas, 0.85),
                dir_audio=dir_audio,
            )

            job.avance(T("srv.armando_zip"), 0.9)
            carpeta = tempfile.mkdtemp(prefix="migrador_zip_")
            destino = os.path.join(carpeta, f"{R.slugify(artista)}-{T('paq.f_zip_sufijo')}.zip")
            ruta, tam = M.empaquetar(
                copias,
                artista,
                out_path=destino,
                entorno=ent,
                con_tidal=bool(ses and ses.conectada),
                incluir_planilla=quiere_planilla,
                incluir_audio=quiere_audio,
                incluir_portadas=quiere_portadas,
                log=avance_preparar,
                avance=en_tramo(0.9, 0.99),
                diag=diagnostico,
            )
        except BaseException:
            # Si el armado falla o lo cancelan, la carpeta del ZIP a medio
            # escribir no tiene por qué quedarse en el disco.
            if carpeta:
                shutil.rmtree(carpeta, ignore_errors=True)
            raise
        finally:
            if dir_audio:
                M.limpiar(dir_audio)

        ESTADO.registrar_zip(job.id, ruta)

        val = V.validar(copias, artista)
        job.avance(T("srv.paquete_listo"), 1.0)
        listo: PaqueteListo = {
            "archivo": os.path.basename(ruta),
            "bytes": tam,
            "descarga": f"/api/descargar/{job.id}",
            "guardar": f"/api/guardar/{job.id}",
            "validacion": {"apto": val["apto"], "resumen": val["resumen"], "hallazgos": val["hallazgos"]},
            "portadas": sum(1 for p in copias if p.get("cover_bytes")),
            "productos": len(copias),
        }
        return listo

    return {"job": _lanzar("preparar", trabajo).a_dict()}


def api_tidal_iniciar():
    if not AUDIO_HABILITADO:
        raise ValueError(T("srv.audio_desactivado"))
    ses = audio_mod.TidalSession()
    info = ses.iniciar_login()
    # La sesión anterior, si quedó alguna a medio conectar, se cierra: dejarla
    # abierta mantiene un hilo y un directorio temporal por cada intento.
    anterior, ESTADO.tidal = ESTADO.tidal, ses
    if anterior:
        try:
            anterior.close()
        except Exception:  # noqa: BLE001
            pass
    # Sólo lo necesario para que el usuario complete el login en el sitio de Tidal.
    return {
        "url": info["url"],
        "codigo": info["user_code"],
        "device_code": info["device_code"],
        "expira_en": info["expires_in"],
    }


def api_tidal_confirmar(body):
    if not ESTADO.tidal:
        raise ValueError(T("srv.sin_tidal_en_curso"))
    estado = ESTADO.tidal.poll_login((body.get("device_code") or "").strip())
    return {"estado": estado, "conectada": bool(ESTADO.tidal.conectada)}


def api_tidal_desconectar():
    if ESTADO.tidal:
        try:
            ESTADO.tidal.close()
        except Exception:  # noqa: BLE001
            pass
        ESTADO.tidal = None
    return {"ok": True}


# Dónde se publican las versiones. La página es la que se le abre a quien
# quiere bajar la nueva: ahí están los archivos y cuál elegir para cada sistema.
PAGINA_VERSIONES = "https://github.com/joacogoliver-debug/catalog-migrator/releases/latest"
API_ULTIMA_VERSION = "https://api.github.com/repos/joacogoliver-debug/catalog-migrator/releases/latest"


def _numeros_de_version(texto):
    """«v1.3.10» -> (1, 3, 10), para comparar versiones como números y no
    como texto, donde «1.3.10» queda antes que «1.3.9»."""
    return tuple(int(n) for n in re.findall(r"\d+", str(texto or ""))[:3])


def api_actualizacion():
    """Si hay una versión más nueva publicada que la que está corriendo.

    Existe porque la app no se actualiza sola y nadie sabía con qué versión
    estaba probando: la primera pregunta de cada consulta era «¿cuándo la
    bajaste?». Se le pregunta a GitHub por la última versión publicada, sólo
    cuando alguien toca el botón: la app no llama a ningún lado por su cuenta.
    El pedido no lleva nada del usuario ni de su catálogo.
    """
    datos = R._http_json(API_ULTIMA_VERSION, headers={"Accept": "application/vnd.github+json"}, retries=1)
    ultima = str((datos or {}).get("tag_name") or "").lstrip("vV")
    if not _numeros_de_version(ultima):
        raise ValueError(T("srv.actualizacion_sin_respuesta"))
    return {
        "actual": VERSION,
        "ultima": ultima,
        "hay": _numeros_de_version(ultima) > _numeros_de_version(VERSION),
    }


def api_abrir_versiones():
    """Abre la página de descargas en el navegador del sistema. Lo hace el
    servidor y no un enlace de la página, porque la ventana propia no siempre
    saca un enlace hacia afuera. La dirección es fija: no la elige la página."""
    import webbrowser

    webbrowser.open(PAGINA_VERSIONES)
    return {"ok": True}


def api_latido():
    """La ventana avisa que sigue abierta.

    En la ventana nativa, cerrarla termina el proceso. En el navegador no hay
    forma de enterarse de que se cerró la pestaña, y el binario no tiene
    consola: sin esto, cada doble clic dejaba un servidor más corriendo para
    siempre. Pasa por el token como cualquier ruta, así que otra página no
    puede mantener viva la app.
    """
    ESTADO.ultimo_latido = time.monotonic()
    return {"ok": True}


RUTAS_POST = {
    "/api/idioma": api_idioma,
    "/api/terminos": api_terminos,
    "/api/clave": api_guardar_clave,
    "/api/relevar": api_relevar,
    "/api/validar": api_validar,
    "/api/editar": api_editar,
    "/api/importar": api_importar,
    "/api/importar/aplicar": api_importar_aplicar,
    "/api/abrir": api_abrir,
    "/api/comparar": api_comparar,
    "/api/preparar": api_preparar,
    "/api/tidal/confirmar": api_tidal_confirmar,
    "/api/mostrar": api_mostrar,
}
RUTAS_POST_SIN_BODY = {
    "/api/latido": api_latido,
    "/api/actualizacion/abrir": api_abrir_versiones,
    "/api/tidal/iniciar": api_tidal_iniciar,
    "/api/tidal/desconectar": api_tidal_desconectar,
}


# ============================================================
# Servidor
# ============================================================


class Handler(BaseHTTPRequestHandler):
    server_version = f"Migrador/{VERSION}"
    protocol_version = "HTTP/1.1"
    # Con HTTP/1.1 las conexiones quedan vivas esperando el pedido siguiente. Sin
    # timeout, una conexión abandonada deja el hilo colgado y el cierre puede
    # llegar justo cuando el cliente va a reusarla (en Windows eso aparece como
    # WinError 10053 del lado del cliente). Con timeout se cierran ordenadamente.
    timeout = 60

    # ---- utilidades ----

    def _cabeceras_base(self):
        # nosniff evita que el navegador reinterprete una respuesta JSON como
        # otra cosa; la CSP deja a la página sin poder pedir nada afuera, que es
        # exactamente lo que hace una app que funciona sin internet.
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        # Ninguna otra página puede meter la app en un iframe, ni quedarse con
        # una referencia a su ventana, ni incrustar sus respuestas. Sin esto, una
        # pestaña que adivinara el puerto podía mostrar la app adentro de la suya
        # y engañar clics (aceptar los términos, conectar Tidal). Suman a las
        # tres defensas; no reemplazan ninguna.
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")

    def _json(self, datos, codigo=HTTPStatus.OK):
        cuerpo = json.dumps(datos, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        if self.close_connection:
            # Que el cliente sepa que esta conexión no se reusa.
            self.send_header("Connection", "close")
        self._cabeceras_base()
        self.end_headers()
        self.wfile.write(cuerpo)

    def _error(self, mensaje, codigo=HTTPStatus.BAD_REQUEST):
        cuerpo = {"error": str(mensaje)}
        # Los errores clasificados viajan con su código, así la interfaz puede
        # ofrecer la salida que corresponde (por ejemplo, cargar una clave propia
        # cuando se agotó el cupo).
        marca = getattr(mensaje, "codigo", "")
        if marca:
            cuerpo["codigo_error"] = marca
        self._json(cuerpo, codigo)

    # El pedido se rechazó sin leer su cuerpo, que sigue en el socket.
    cuerpo_sin_leer = False

    @override
    def finish(self):
        """Cierra la conexión, sin cortarle la respuesta al cliente.

        Cuando un pedido se rechaza sin leer su cuerpo (viene por partes, o es
        más grande que el tope), lo que el cliente mandó queda en el socket. Si
        se cierra así, el sistema no cierra: aborta la conexión, y en Windows el
        cliente recibe un «connection aborted» en vez del 400 que le explicaba
        qué hizo mal. Pasaba una de cada seis veces, y se veía como un test que
        fallaba porque sí.

        Lo que se hace es lo que hace cualquier servidor web: se termina de
        escribir, se avisa que no se va a escribir más y se descarta lo que el
        cliente siga mandando, un rato corto y acotado. Recién entonces se
        cierra.
        """
        if self.cuerpo_sin_leer:
            try:
                self.wfile.flush()
                self.connection.shutdown(socket.SHUT_WR)
                self.connection.settimeout(ESPERA_CIERRE)
                limite = time.monotonic() + TOPE_CIERRE
                while time.monotonic() < limite:
                    if not self.connection.recv(65536):
                        break
            except OSError:
                pass  # el cliente ya cortó, o no mandó nada más: no hay qué esperar
        super().finish()

    def _leer_crudo(self):
        """Lee y consume el cuerpo del pedido, sin interpretarlo.

        Consumirlo es obligatorio aunque no se use: ver la nota en do_POST. Si
        no se puede consumir entero (un largo que no es un número, uno más grande
        que el tope, o un cuerpo por partes que acá no se entiende), la conexión
        se cierra: lo que quede en el socket se metería adelante del pedido
        siguiente, que es el bug que la lectura obligatoria vino a cortar.
        """
        if self.headers.get("Transfer-Encoding"):
            self.close_connection = self.cuerpo_sin_leer = True
            raise ValueError(T("srv.sin_chunked"))
        try:
            largo = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            self.close_connection = self.cuerpo_sin_leer = True
            raise ValueError(T("srv.content_length")) from None
        if largo <= 0:
            return b""
        if largo > MAX_BODY:
            self.close_connection = self.cuerpo_sin_leer = True
            raise ValueError(T("srv.pedido_grande"))
        crudo = self.rfile.read(largo)
        if len(crudo) < largo:
            self.close_connection = True
            raise ValueError(T("srv.pedido_cortado"))
        return crudo

    def _parsear_body(self, crudo):
        """El cuerpo como objeto JSON, o {} si vino vacío."""
        if not crudo:
            return {}
        try:
            datos = json.loads(crudo.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise ValueError(T("srv.json_invalido")) from None
        if not isinstance(datos, dict):
            raise ValueError(T("srv.json_no_objeto"))
        return datos

    def _host_valido(self):
        host = (self.headers.get("Host") or "").strip()
        if not host:
            return False
        # Sacamos el puerto, con cuidado de no partir un IPv6 entre corchetes.
        if host.startswith("["):
            nombre = host.split("]")[0] + "]"
        else:
            nombre = host.split(":")[0]
        return nombre in HOSTS_VALIDOS

    def _token_valido(self):
        # Comparado en bytes: con texto, un token con caracteres fuera de ASCII
        # hacía que `compare_digest` levantara y el pedido terminaba en un 500
        # con el texto de la excepción, en vez de un 403 como cualquier otro.
        recibido = (self.headers.get("X-App-Token") or "").encode("utf-8", "replace")
        return secrets.compare_digest(recibido, TOKEN.encode("ascii"))

    def _origen_propio(self):
        """False si el navegador avisa que el pedido lo hizo otra página.

        Es una capa más sobre el token, que sigue siendo lo que protege: los
        navegadores actuales mandan `Sec-Fetch-Site` y, en los POST, `Origin`, y
        si dicen que viene de otro sitio no hay por qué seguir. Si no los mandan
        (un navegador viejo, o un cliente que no es un navegador) no se rechaza
        nada por eso: la decisión la sigue tomando el token.
        """
        sitio = (self.headers.get("Sec-Fetch-Site") or "").strip().lower()
        if sitio and sitio not in ("same-origin", "none"):
            return False
        origen = (self.headers.get("Origin") or "").strip()
        if origen and origen != "null":
            host = urllib.parse.urlsplit(origen).hostname or ""
            if host not in HOSTS_VALIDOS and f"[{host}]" not in HOSTS_VALIDOS:
                return False
        return True

    @override
    def log_message(self, formato, *args):
        # Silencio: el log de acceso de http.server ensucia la consola de la app.
        pass

    # ---- GET ----

    def do_GET(self):
        try:
            self._get()
        except (BrokenPipeError, ConnectionError):
            self.close_connection = True
        except Exception as e:  # noqa: BLE001
            # Sin esto, una excepción acá la imprime http.server como traceback y
            # el cliente ve la conexión cortada sin ningún mensaje.
            try:
                self._error(T("srv.inesperado", error=e), HTTPStatus.INTERNAL_SERVER_ERROR)
            except Exception:  # noqa: BLE001
                self.close_connection = True

    def _get(self):
        if not self._host_valido():
            return self._error(T("srv.rechazado"), HTTPStatus.FORBIDDEN)

        ruta = urllib.parse.urlparse(self.path).path

        if ruta.startswith("/api/"):
            if not self._token_valido() or not self._origen_propio():
                return self._error(T("srv.rechazado_token"), HTTPStatus.FORBIDDEN)

            if ruta == "/api/config":
                return self._json(api_config())

            if ruta == "/api/actualizacion":
                try:
                    return self._json(api_actualizacion())
                except ValueError as e:
                    return self._error(e, HTTPStatus.BAD_GATEWAY)

            if ruta == "/api/catalogo":
                # Permite recuperar el catálogo si se recarga la página: el
                # relevamiento cuesta cuota de YouTube y no queremos repetirlo por
                # un F5 accidental.
                if not ESTADO.productos:
                    return self._error(T("srv.sin_catalogo"), HTTPStatus.NOT_FOUND)
                return self._json(catalogo_json(ESTADO.productos, ESTADO.artista, ESTADO.diagnostico))

            m = re.fullmatch(r"/api/job/([0-9a-f]{6,32})", ruta)
            if m:
                job = JOBS.get(m.group(1))
                if not job:
                    return self._error(T("srv.trabajo_no_existe"), HTTPStatus.NOT_FOUND)
                return self._json(job.a_dict(con_log=True))

            m = re.fullmatch(r"/api/descargar/([0-9a-f]{6,32})", ruta)
            if m:
                return self._descargar(m.group(1))

            return self._error(T("srv.no_encontrado"), HTTPStatus.NOT_FOUND)

        # Fuera de /api/ a propósito: toda ruta de /api/ exige la cabecera del
        # token sin excepciones, y así la regla sigue siendo una sola. Ésta la
        # reemplaza por un ticket que sólo se obtiene con el token (ver
        # `Estado.emitir_ticket`).
        m = re.fullmatch(r"/descargar/([A-Za-z0-9_\-]{16,64})", ruta)
        if m:
            job_id = ESTADO.canjear_ticket(m.group(1))
            if not job_id:
                return self._error(T("srv.zip_vencido"), HTTPStatus.NOT_FOUND)
            return self._descargar(job_id)

        return self._estatico(ruta)

    def _descargar(self, job_id):
        ruta = ESTADO.zip_de(job_id)
        if not ruta or not os.path.exists(ruta):
            return self._error(T("srv.zip_vencido"), HTTPStatus.NOT_FOUND)
        tam = os.path.getsize(ruta)
        # El nombre sale de slugify(), pero igual lo limpiamos antes de meterlo en
        # una cabecera: un salto de línea ahí parte la respuesta en dos.
        nombre = re.sub(r"[^A-Za-z0-9._\- ]", "_", os.path.basename(ruta))
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/zip")
        self.send_header("Content-Disposition", f'attachment; filename="{nombre}"')
        self.send_header("Content-Length", str(tam))
        self.send_header("Cache-Control", "no-store")
        self._cabeceras_base()
        self.end_headers()
        # En bloques: un catálogo con audio puede pesar varios GB y no entra en RAM.
        try:
            with open(ruta, "rb") as f:
                shutil.copyfileobj(f, self.wfile, length=1024 * 256)
        except (BrokenPipeError, ConnectionError):
            # El usuario canceló la descarga. No es un error nuestro; cortamos la
            # conexión y listo, sin ensuciar la consola con un traceback.
            self.close_connection = True

    def _estatico(self, ruta):
        if ruta in ("/", "/index.html"):
            return self._pagina()

        # Normalizamos para que no se pueda salir de WEB_DIR con "..".
        limpio = posixpath.normpath(urllib.parse.unquote(ruta)).lstrip("/")
        if limpio.startswith("..") or os.path.isabs(limpio):
            return self._error(T("srv.no_encontrado"), HTTPStatus.NOT_FOUND)

        destino = os.path.normpath(os.path.join(WEB_DIR, limpio))
        base = os.path.normpath(WEB_DIR)
        try:
            afuera = os.path.commonpath([base, destino]) != base
        except ValueError:
            # En Windows, `/D:foo` queda en otra unidad y `commonpath` levanta:
            # eso daba un 500 con el texto de la excepción. Está afuera y listo.
            afuera = True
        if afuera:
            return self._error(T("srv.no_encontrado"), HTTPStatus.NOT_FOUND)
        if not os.path.isfile(destino):
            return self._error(T("srv.no_encontrado"), HTTPStatus.NOT_FOUND)

        tipo = mimetypes.guess_type(destino)[0] or "application/octet-stream"
        if destino.endswith(".woff2"):
            tipo = "font/woff2"  # no todos los sistemas lo tienen
        with open(destino, "rb") as f:
            cuerpo = f.read()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(cuerpo)))
        # Sin cache: si no, una actualización de la app sirve el JS viejo.
        self.send_header("Cache-Control", "no-store")
        self._cabeceras_base()
        self.end_headers()
        self.wfile.write(cuerpo)

    def _pagina(self):
        """index.html con el token de la sesión adentro."""
        ruta = os.path.join(WEB_DIR, "index.html")
        if not os.path.isfile(ruta):
            return self._error(T("srv.falta_index"), HTTPStatus.INTERNAL_SERVER_ERROR)
        with open(ruta, encoding="utf-8") as f:
            html = f.read()
        cuerpo = html.replace("{{TOKEN}}", TOKEN).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        # La página no pide nada afuera: todo, incluidas las fuentes, sale de
        # este mismo servidor. Declararlo cierra la puerta a que un título de
        # YouTube inyecte un recurso externo.
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
            "font-src 'self'; connect-src 'self'; form-action 'none'; base-uri 'none'; "
            "frame-ancestors 'none'; object-src 'none'",
        )
        self._cabeceras_base()
        self.end_headers()
        self.wfile.write(cuerpo)

    # ---- POST ----

    def do_POST(self):
        try:
            self._post()
        except (BrokenPipeError, ConnectionError):
            self.close_connection = True
        except Exception as e:  # noqa: BLE001
            try:
                self._error(T("srv.inesperado", error=e), HTTPStatus.INTERNAL_SERVER_ERROR)
            except Exception:  # noqa: BLE001
                self.close_connection = True

    def _post(self):
        ruta = urllib.parse.urlparse(self.path).path

        # El cuerpo se lee SIEMPRE y antes que nada, incluso en las rutas que no
        # lo usan y en las que vamos a rechazar. Con HTTP/1.1 la conexión se
        # reutiliza, así que un cuerpo sin leer queda en el socket y se mete
        # adelante del pedido siguiente: el método terminaba parseándose como
        # '{}POST' y el servidor respondía 501 "Unsupported method". Se veía como
        # un error aleatorio de Tidal que desaparecía al reintentar, porque el
        # reintento abría otra conexión.
        #
        # Leerlo no es interpretarlo: el JSON se parsea recién después de pasar
        # Host, token y origen. Antes, una página cualquiera podía hacer que el
        # servidor parseara ocho megas antes de rechazarla.
        try:
            crudo = self._leer_crudo()
        except ValueError as e:
            return self._error(e, HTTPStatus.BAD_REQUEST)

        if not self._host_valido():
            return self._error(T("srv.rechazado"), HTTPStatus.FORBIDDEN)
        if not self._token_valido() or not self._origen_propio():
            return self._error(T("srv.rechazado_token"), HTTPStatus.FORBIDDEN)
        try:
            cuerpo = self._parsear_body(crudo)
        except ValueError as e:
            return self._error(e, HTTPStatus.BAD_REQUEST)

        try:
            if ruta in RUTAS_POST_SIN_BODY:
                return self._json(RUTAS_POST_SIN_BODY[ruta]())

            m = re.fullmatch(r"/api/descargar/([0-9a-f]{6,32})", ruta)
            if m:
                ruta_zip = ESTADO.zip_de(m.group(1))
                if not ruta_zip or not os.path.exists(ruta_zip):
                    return self._error(T("srv.zip_vencido"), HTTPStatus.NOT_FOUND)
                return self._json({"url": f"/descargar/{ESTADO.emitir_ticket(m.group(1))}"})

            m = re.fullmatch(r"/api/guardar/([0-9a-f]{6,32})", ruta)
            if m:
                ruta_zip = ESTADO.zip_de(m.group(1))
                if not ruta_zip or not os.path.exists(ruta_zip):
                    return self._error(T("srv.zip_vencido"), HTTPStatus.NOT_FOUND)
                try:
                    destino = guardar_en_descargas(ruta_zip)
                except OSError as e:
                    return self._error(
                        T("srv.no_se_pudo_guardar", detalle=e), HTTPStatus.INTERNAL_SERVER_ERROR
                    )
                return self._json({"ruta": destino, "archivo": os.path.basename(destino)})

            m = re.fullmatch(r"/api/job/([0-9a-f]{6,32})/cancelar", ruta)
            if m:
                job = JOBS.get(m.group(1))
                if not job:
                    return self._error(T("srv.trabajo_no_existe"), HTTPStatus.NOT_FOUND)
                job.cancelar()
                return self._json({"ok": True})

            fn = RUTAS_POST.get(ruta)
            if not fn:
                return self._error(T("srv.no_encontrado"), HTTPStatus.NOT_FOUND)
            return self._json(fn(cuerpo))

        except ValueError as e:
            # Errores esperables y mostrables al usuario.
            return self._error(e, HTTPStatus.BAD_REQUEST)
        except R.RelevarError as e:
            return self._error(e, HTTPStatus.UNPROCESSABLE_ENTITY)
        except Exception as e:  # noqa: BLE001
            return self._error(T("srv.inesperado", error=e), HTTPStatus.INTERNAL_SERVER_ERROR)


class Servidor(ThreadingHTTPServer):
    """El servidor de la app, que calla cuando el cliente corta.

    Una ventana que se cierra, una pestaña que recarga o un Chrome headless que
    termina cortan la conexión mientras el handler espera el pedido siguiente, y
    la lectura revienta con `ConnectionResetError` antes de llegar a `do_GET`,
    donde ya se atiende. `socketserver` lo imprimía como traceback en stderr,
    desde el hilo del pedido. En el ejecutable, que no tiene consola, eso va al
    vacío; pero si coincide con el cierre del intérprete es un `Fatal Python
    error`, que es lo que hacía fallar `build/capturas.py` una de cada tantas.

    Sólo se callan los cortes de conexión. Cualquier otra excepción sigue
    saliendo entera, porque ahí sí hay algo nuestro que arreglar.
    """

    @override
    def handle_error(self, request, client_address):
        if isinstance(sys.exc_info()[1], (ConnectionError, TimeoutError)):
            return
        super().handle_error(request, client_address)


def crear_servidor(puerto=0):
    """Servidor atado a localhost. puerto=0 deja que el sistema elija uno libre,
    así nunca choca con algo que ya esté escuchando."""
    limpiar_temporales_viejos()
    return Servidor(("127.0.0.1", puerto), Handler)


def main(puerto=0, abrir=True):
    srv = crear_servidor(puerto)
    url = f"http://127.0.0.1:{srv.server_address[1]}"
    print(f"{T('app.nombre')} v{VERSION}")
    print(f"Servidor local: {url}")
    if abrir:
        import webbrowser

        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nCerrando")
    finally:
        ESTADO.limpiar()
        srv.server_close()


if __name__ == "__main__":
    main()
