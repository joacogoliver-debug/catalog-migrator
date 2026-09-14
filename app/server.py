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
navegador adjunta la petición igual, termina operando la app del usuario. Dos
defensas, las dos baratas:

  1. **Token de sesión.** Se genera uno nuevo en cada arranque, se inyecta en
     index.html y toda ruta /api/ lo exige en la cabecera X-App-Token. Una
     página externa no puede leerlo, porque el origen es distinto y la política
     del navegador se lo impide.
  2. **Cabecera Host.** Se acepta sólo 127.0.0.1 o localhost. Eso corta el
     rebinding de DNS, que es la vuelta clásica para saltear la defensa
     anterior.

Endpoints:
  GET  /                      la interfaz
  GET  /<archivo>             estáticos (js, css, fuentes, assets)
  GET  /api/config            capacidades del entorno y estado de la clave
  POST /api/terminos          aceptación de los términos de uso
  POST /api/clave             guardar la clave de YouTube
  POST /api/relevar           {url, con_codigos} -> {job}    (asincrónico)
  POST /api/validar           {ids} -> hallazgos               (sincrónico)
  POST /api/preparar          {ids, opciones} -> {job}        (asincrónico)
  GET  /api/job/<id>          estado del trabajo
  POST /api/job/<id>/cancelar
  GET  /api/descargar/<id>    baja el ZIP (streaming)
  POST /api/tidal/...         conexión opcional de Tidal
"""

import json
import mimetypes
import os
import posixpath
import re
import secrets
import shutil
import sys
import tempfile
import threading
import time
import urllib.parse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# El paquete corre tanto desde el repo como desde el binario de PyInstaller.
_AQUI = os.path.dirname(os.path.abspath(__file__))
_RAIZ = os.path.dirname(_AQUI)
for _p in (_RAIZ, _AQUI):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import audio as audio_mod                     # noqa: E402
import migrar_core as M                       # noqa: E402
import productos as P                         # noqa: E402
import relevar_core as R                      # noqa: E402
import validar as V                           # noqa: E402
from jobs import Registry                     # noqa: E402

VERSION = "1.0.0"
APP = "Migrador de Catálogos"

# Versión de los términos de uso. Si cambian de fondo se sube el número y la app
# los vuelve a pedir una vez; los cambios de redacción no lo tocan.
TERMINOS_VERSION = "1.0"

# Token de esta sesión. Nuevo en cada arranque: no se guarda en ningún lado, así
# que no hay nada que se pueda filtrar entre una ejecución y la siguiente.
TOKEN = secrets.token_urlsafe(24)

# Hosts que aceptamos en la cabecera Host. Cualquier otro nombre significa que
# alguien resolvió un dominio propio a 127.0.0.1 para hablarle a la app.
HOSTS_VALIDOS = ("127.0.0.1", "localhost", "::1", "[::1]")


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
MAX_BODY = 8 * 1024 * 1024          # 8 MB: los payloads son listas de ids

# Espacio libre mínimo antes de empezar a armar un paquete. Con audio un
# catálogo entero puede pasar los 2 GB, y quedarse sin disco a mitad deja el ZIP
# corrupto y sin explicación.
MIN_LIBRE_BASE = 300 * 1024 * 1024
MIN_LIBRE_AUDIO = 3 * 1024 * 1024 * 1024


def dir_datos():
    """Carpeta de la app en el home del usuario, para la clave y los temporales."""
    base = os.path.join(os.path.expanduser("~"), ".migrador-catalogos")
    os.makedirs(base, exist_ok=True)
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
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, destino)
    try:
        os.chmod(destino, 0o600)    # en Windows es no-op, en Unix protege el archivo
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


# ============================================================
# Entorno de audio, cacheado
# ============================================================

_ENTORNO = {"valor": None, "cuando": 0.0}
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
            except Exception:                        # noqa: BLE001
                # Si la detección falla, la app tiene que seguir andando sin
                # audio, no romperse entera.
                _ENTORNO["valor"] = {
                    "ffmpeg": False, "ffmpeg_incluido": False, "ffprobe": False,
                    "js_runtime": False, "tiddl": False, "yt_dlp": False,
                    "puede_flac": False, "puede_referencia": False,
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
        self.tidal = None
        self.zips = {}              # job_id -> ruta del zip
        self.temporales = []
        self.lock = threading.RLock()

    def por_ids(self, ids):
        with self.lock:
            productos = list(self.productos)
        if not ids:
            return productos
        return P.filter_products(productos, ids=ids)

    def guardar_catalogo(self, prods, artista, diag):
        with self.lock:
            self.productos = prods
            self.artista = artista
            self.diagnostico = diag

    def registrar_zip(self, job_id, ruta):
        with self.lock:
            self.zips[job_id] = ruta

    def registrar_temporal(self, ruta):
        with self.lock:
            self.temporales.append(ruta)

    def zip_de(self, job_id):
        with self.lock:
            return self.zips.get(job_id)

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
            self.tidal, self.temporales, self.zips = None, [], {}
        if tidal:
            try:
                tidal.close()
            except Exception:                        # noqa: BLE001
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

def _mmss(seg):
    seg = int(seg or 0)
    return f"{seg // 60}:{seg % 60:02d}"


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
        "detalle": [{
            "n": t.get("track_number") or "",
            "titulo": t.get("track", ""),
            "isrc": t.get("isrc") or "",
            "duracion": _mmss(t.get("duration_s")),
            "views": t.get("views", 0),
            "url": t.get("url", ""),
        } for t in p.get("tracks", [])],
    }


def catalogo_json(productos, artista, diag=None):
    desde, hasta = P.year_range(productos)
    return {
        "artista": artista,
        "diagnostico": diag or {},
        "productos": [producto_json(p) for p in productos],
        "resumen": P.summarize(productos),
        "filtros": {
            "distribuidoras": P.distributor_options(productos),
            "anio_min": desde,
            "anio_max": hasta,
        },
    }


# ============================================================
# Handlers de la API
# ============================================================

def api_config():
    # El frontend pasa por acá al abrir y después de cada operación larga: es el
    # mejor lugar para descartar trabajos vencidos y los ZIP que dejaron.
    JOBS.limpiar()
    return {
        "version": VERSION,
        "terminos_aceptados": terminos_aceptados(),
        "terminos_version": TERMINOS_VERSION,
        "tiene_clave": bool(leer_clave()),
        # Para poder aclarar en la interfaz que está usando una clave incluida y
        # no la propia.
        "clave_incluida": (bool(_clave_incluida())
                           and not os.environ.get("YOUTUBE_API_KEY", "").strip()
                           and not (leer_config().get("youtube_api_key") or "").strip()),
        "audio_habilitado": AUDIO_HABILITADO,
        "entorno": entorno_audio(),
        "tidal_conectada": bool(ESTADO.tidal and ESTADO.tidal.conectada),
        "catalogo_cargado": bool(ESTADO.productos),
        "trabajo_en_curso": bool(JOBS.activos()),
    }


def api_terminos(body):
    if not body.get("aceptar"):
        raise ValueError("Hay que aceptar los términos para usar la herramienta.")
    guardar_config({"terminos": TERMINOS_VERSION})
    return {"ok": True}


def api_guardar_clave(body):
    clave = (body.get("clave") or "").strip()
    if not clave:
        raise ValueError("Pegá la clave de la API de YouTube.")
    if len(clave) > 200 or "\n" in clave:
        raise ValueError("Eso no parece una clave de API.")
    # Validación real: pegamos una consulta mínima antes de darla por buena, así
    # el usuario se entera acá y no a mitad de un relevamiento.
    try:
        R.api_get("channels", {"part": "id", "id": "UC_x5XG1OV2P6uZZ5FSM9Ttw"}, clave)
    except Exception as e:                       # noqa: BLE001
        raise ValueError(f"La clave no funcionó. {e}")
    guardar_clave(clave)
    return {"ok": True}


def _sin_trabajo_en_curso():
    """Un trabajo largo por vez.

    Dos relevamientos simultáneos gastan cuota de YouTube por duplicado y
    escriben sobre el mismo catálogo en memoria, así que el segundo pisa al
    primero y el resultado depende de cuál termine último. Es más honesto
    negarlo con un mensaje que dejar que pase.
    """
    if JOBS.activos():
        raise ValueError("Ya hay un trabajo en curso. Esperá a que termine o cancelalo.")


def api_relevar(body):
    url = (body.get("url") or "").strip()
    if not url:
        raise ValueError("Pegá el link del canal de YouTube.")
    if len(url) > 2048:
        raise ValueError("Ese link es demasiado largo para ser un canal de YouTube.")
    # El estado del servidor se mira antes que la configuración: si ya hay algo
    # corriendo, eso es lo que hay que decir, y además así el rechazo no depende
    # de si la clave está cargada o no.
    _sin_trabajo_en_curso()
    clave = leer_clave()
    if not clave:
        raise ValueError("Falta configurar la clave de la API de YouTube.")
    con_codigos = bool(body.get("con_codigos", True))

    def trabajo(job):
        prods, artista, _, diag = M.relevar_catalogo(
            url, clave, with_codes=con_codigos,
            progress=lambda m, f=None: job.avance(m, f))
        ESTADO.guardar_catalogo(prods, artista, diag)
        job.avance(f"{len(prods)} productos encontrados.", 1.0)
        return catalogo_json(prods, artista, diag)

    return {"job": JOBS.lanzar("relevar", trabajo).a_dict()}


def api_validar(body):
    sel = ESTADO.por_ids(body.get("ids"))
    if not sel:
        raise ValueError("No hay productos seleccionados.")
    res = V.validar(sel, ESTADO.artista)
    return {
        "apto": res["apto"],
        "resumen": res["resumen"],
        "hallazgos": res["hallazgos"],
    }


def _revisar_espacio(con_audio):
    minimo = MIN_LIBRE_AUDIO if con_audio else MIN_LIBRE_BASE
    try:
        libre = shutil.disk_usage(tempfile.gettempdir()).free
    except OSError:
        return                                   # si no se puede medir, seguimos
    if libre < minimo:
        raise ValueError(
            f"Queda poco espacio en disco ({libre / 1e9:.1f} GB libres) y este "
            f"paquete necesita al menos {minimo / 1e9:.1f} GB. Liberá espacio y "
            "probá de nuevo.")


def api_preparar(body):
    ids = body.get("ids") or []
    sel = ESTADO.por_ids(ids)
    if not sel:
        raise ValueError("No hay productos seleccionados.")

    quiere_planilla = bool(body.get("planilla", True))
    quiere_portadas = bool(body.get("portadas", True))
    quiere_audio = bool(body.get("audio", False)) and AUDIO_HABILITADO
    if not (quiere_planilla or quiere_portadas or quiere_audio):
        raise ValueError("Elegí al menos una cosa para descargar.")
    _sin_trabajo_en_curso()
    _revisar_espacio(quiere_audio)

    artista = ESTADO.artista
    ses = ESTADO.tidal if quiere_audio else None

    def trabajo(job):
        # Sobre copias: preparar() agrega bytes de portada y rutas de audio a los
        # productos, y no queremos que el catálogo en memoria se llene de eso
        # después de cada descarga.
        copias = [dict(p, tracks=[dict(t) for t in p["tracks"]]) for p in sel]

        job.avance("Preparando", 0.05)
        dir_audio = None
        carpeta = None
        try:
            _, dir_audio, ent = M.preparar(
                copias, artista, quiere_planilla=quiere_planilla,
                quiere_audio=quiere_audio, quiere_portadas=quiere_portadas,
                tidal_session=ses, log=lambda m: job.avance(m))
            if dir_audio:
                ESTADO.registrar_temporal(dir_audio)

            job.avance("Armando el ZIP", 0.9)
            carpeta = tempfile.mkdtemp(prefix="migrador_zip_")
            destino = os.path.join(carpeta, f"{R.slugify(artista)}-migracion.zip")
            ruta, tam = M.empaquetar(
                copias, artista, out_path=destino, entorno=ent,
                con_tidal=bool(ses and ses.conectada),
                incluir_planilla=quiere_planilla, incluir_audio=quiere_audio,
                incluir_portadas=quiere_portadas, log=lambda m: job.avance(m))
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
        job.avance("Paquete listo.", 1.0)
        return {
            "archivo": os.path.basename(ruta),
            "bytes": tam,
            "descarga": f"/api/descargar/{job.id}",
            "validacion": {"apto": val["apto"], "resumen": val["resumen"],
                           "hallazgos": val["hallazgos"]},
            "portadas": sum(1 for p in copias if p.get("cover_bytes")),
            "productos": len(copias),
        }

    return {"job": JOBS.lanzar("preparar", trabajo).a_dict()}


def api_tidal_iniciar():
    if not AUDIO_HABILITADO:
        raise ValueError("El módulo de audio está desactivado.")
    ses = audio_mod.TidalSession()
    info = ses.iniciar_login()
    # La sesión anterior, si quedó alguna a medio conectar, se cierra: dejarla
    # abierta mantiene un hilo y un directorio temporal por cada intento.
    anterior, ESTADO.tidal = ESTADO.tidal, ses
    if anterior:
        try:
            anterior.close()
        except Exception:                            # noqa: BLE001
            pass
    # Sólo lo necesario para que el usuario complete el login en el sitio de Tidal.
    return {"url": info["url"], "codigo": info["user_code"],
            "device_code": info["device_code"], "expira_en": info["expires_in"]}


def api_tidal_confirmar(body):
    if not ESTADO.tidal:
        raise ValueError("No hay una conexión de Tidal en curso.")
    estado = ESTADO.tidal.poll_login((body.get("device_code") or "").strip())
    return {"estado": estado, "conectada": bool(ESTADO.tidal.conectada)}


def api_tidal_desconectar():
    if ESTADO.tidal:
        try:
            ESTADO.tidal.close()
        except Exception:                            # noqa: BLE001
            pass
        ESTADO.tidal = None
    return {"ok": True}


RUTAS_POST = {
    "/api/terminos": api_terminos,
    "/api/clave": api_guardar_clave,
    "/api/relevar": api_relevar,
    "/api/validar": api_validar,
    "/api/preparar": api_preparar,
    "/api/tidal/confirmar": api_tidal_confirmar,
}
RUTAS_POST_SIN_BODY = {
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

    def _json(self, datos, codigo=HTTPStatus.OK):
        cuerpo = json.dumps(datos, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        self._cabeceras_base()
        self.end_headers()
        self.wfile.write(cuerpo)

    def _error(self, mensaje, codigo=HTTPStatus.BAD_REQUEST):
        self._json({"error": str(mensaje)}, codigo)

    def _leer_body(self):
        """Lee y consume el cuerpo del pedido. Devuelve {} si viene vacío.

        Consumirlo es obligatorio aunque no se use: ver la nota en do_POST.
        """
        try:
            largo = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            raise ValueError("El pedido trae un Content-Length inválido.")
        if largo <= 0:
            return {}
        if largo > MAX_BODY:
            raise ValueError("El pedido es demasiado grande.")
        crudo = self.rfile.read(largo)
        if len(crudo) < largo:
            raise ValueError("El pedido llegó cortado.")
        try:
            datos = json.loads(crudo.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise ValueError("El pedido no es JSON válido.")
        if not isinstance(datos, dict):
            raise ValueError("El pedido tiene que ser un objeto JSON.")
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
        recibido = self.headers.get("X-App-Token") or ""
        return secrets.compare_digest(recibido, TOKEN)

    def log_message(self, formato, *args):
        # Silencio: el log de acceso de http.server ensucia la consola de la app.
        pass

    # ---- GET ----

    def do_GET(self):
        try:
            self._get()
        except (BrokenPipeError, ConnectionError):
            self.close_connection = True
        except Exception as e:                       # noqa: BLE001
            # Sin esto, una excepción acá la imprime http.server como traceback y
            # el cliente ve la conexión cortada sin ningún mensaje.
            try:
                self._error(f"Error inesperado. {e}", HTTPStatus.INTERNAL_SERVER_ERROR)
            except Exception:                        # noqa: BLE001
                self.close_connection = True

    def _get(self):
        if not self._host_valido():
            return self._error("Pedido rechazado.", HTTPStatus.FORBIDDEN)

        ruta = urllib.parse.urlparse(self.path).path

        if ruta.startswith("/api/"):
            if not self._token_valido():
                return self._error("Pedido rechazado. Recargá la app.", HTTPStatus.FORBIDDEN)

            if ruta == "/api/config":
                return self._json(api_config())

            if ruta == "/api/catalogo":
                # Permite recuperar el catálogo si se recarga la página: el
                # relevamiento cuesta cuota de YouTube y no queremos repetirlo por
                # un F5 accidental.
                if not ESTADO.productos:
                    return self._error("No hay un catálogo cargado.", HTTPStatus.NOT_FOUND)
                return self._json(catalogo_json(ESTADO.productos, ESTADO.artista,
                                                ESTADO.diagnostico))

            m = re.fullmatch(r"/api/job/([0-9a-f]{6,32})", ruta)
            if m:
                job = JOBS.get(m.group(1))
                if not job:
                    return self._error("Ese trabajo ya no existe.", HTTPStatus.NOT_FOUND)
                return self._json(job.a_dict(con_log=True))

            m = re.fullmatch(r"/api/descargar/([0-9a-f]{6,32})", ruta)
            if m:
                return self._descargar(m.group(1))

            return self._error("No encontrado.", HTTPStatus.NOT_FOUND)

        return self._estatico(ruta)

    def _descargar(self, job_id):
        ruta = ESTADO.zip_de(job_id)
        if not ruta or not os.path.exists(ruta):
            return self._error("El paquete ya no está disponible. Generalo de nuevo.",
                               HTTPStatus.NOT_FOUND)
        tam = os.path.getsize(ruta)
        # El nombre sale de slugify(), pero igual lo limpiamos antes de meterlo en
        # una cabecera: un salto de línea ahí parte la respuesta en dos.
        nombre = re.sub(r'[^A-Za-z0-9._\- ]', "_", os.path.basename(ruta))
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/zip")
        self.send_header("Content-Disposition", f'attachment; filename="{nombre}"')
        self.send_header("Content-Length", str(tam))
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
            return self._error("No encontrado.", HTTPStatus.NOT_FOUND)

        destino = os.path.normpath(os.path.join(WEB_DIR, limpio))
        base = os.path.normpath(WEB_DIR)
        if os.path.commonpath([base, destino]) != base:
            return self._error("No encontrado.", HTTPStatus.NOT_FOUND)
        if not os.path.isfile(destino):
            return self._error("No encontrado.", HTTPStatus.NOT_FOUND)

        tipo = mimetypes.guess_type(destino)[0] or "application/octet-stream"
        if destino.endswith(".woff2"):
            tipo = "font/woff2"                  # no todos los sistemas lo tienen
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
            return self._error("Falta index.html.", HTTPStatus.INTERNAL_SERVER_ERROR)
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
            "font-src 'self'; connect-src 'self'; form-action 'none'; base-uri 'none'")
        self._cabeceras_base()
        self.end_headers()
        self.wfile.write(cuerpo)

    # ---- POST ----

    def do_POST(self):
        try:
            self._post()
        except (BrokenPipeError, ConnectionError):
            self.close_connection = True
        except Exception as e:                       # noqa: BLE001
            try:
                self._error(f"Error inesperado. {e}", HTTPStatus.INTERNAL_SERVER_ERROR)
            except Exception:                        # noqa: BLE001
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
        try:
            cuerpo = self._leer_body()
        except ValueError as e:
            return self._error(e, HTTPStatus.BAD_REQUEST)

        if not self._host_valido():
            return self._error("Pedido rechazado.", HTTPStatus.FORBIDDEN)
        if not self._token_valido():
            return self._error("Pedido rechazado. Recargá la app.", HTTPStatus.FORBIDDEN)

        try:
            if ruta in RUTAS_POST_SIN_BODY:
                return self._json(RUTAS_POST_SIN_BODY[ruta]())

            m = re.fullmatch(r"/api/job/([0-9a-f]{6,32})/cancelar", ruta)
            if m:
                job = JOBS.get(m.group(1))
                if not job:
                    return self._error("Ese trabajo ya no existe.", HTTPStatus.NOT_FOUND)
                job.cancelar()
                return self._json({"ok": True})

            fn = RUTAS_POST.get(ruta)
            if not fn:
                return self._error("No encontrado.", HTTPStatus.NOT_FOUND)
            return self._json(fn(cuerpo))

        except ValueError as e:
            # Errores esperables y mostrables al usuario.
            return self._error(e, HTTPStatus.BAD_REQUEST)
        except R.RelevarError as e:
            return self._error(e, HTTPStatus.UNPROCESSABLE_ENTITY)
        except Exception as e:                        # noqa: BLE001
            return self._error(f"Error inesperado. {e}", HTTPStatus.INTERNAL_SERVER_ERROR)


def crear_servidor(puerto=0):
    """Servidor atado a localhost. puerto=0 deja que el sistema elija uno libre,
    así nunca choca con algo que ya esté escuchando."""
    limpiar_temporales_viejos()
    return ThreadingHTTPServer(("127.0.0.1", puerto), Handler)


def main(puerto=0, abrir=True):
    srv = crear_servidor(puerto)
    url = f"http://127.0.0.1:{srv.server_address[1]}"
    print(f"{APP} v{VERSION}")
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
