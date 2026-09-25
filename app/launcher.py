"""
Punto de entrada de la app de escritorio.

Levanta el servidor local en un puerto libre y abre la interfaz. Si `pywebview`
está instalado, la abre en una ventana nativa y la app se siente como un
programa de escritorio; si no, cae en el navegador por defecto, que funciona
igual de bien y no obliga a instalar nada.

Se corre así:
    python app/launcher.py            # ventana nativa o navegador
    python app/launcher.py --puerto 8777 --no-abrir
"""

import argparse
import os
import shutil
import subprocess
import sys
import threading
import time

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

import server as backend  # noqa: E402
from migrador.i18n import T  # noqa: E402

# El idioma se resuelve antes que nada: la primera linea que imprime el launcher
# ya tiene que salir en el idioma que corresponde.
backend.idioma_guardado()


def titulo():
    return T("app.nombre")


# ============================================================
# Ventana de la aplicación
# ============================================================


def permitir_descargas(webview):
    """Habilita las descargas en pywebview, si la versión instalada lo permite.

    `settings` existe desde pywebview 5, que es el piso que piden los
    requirements. Si igual falta, la ventana abre y el botón queda sin efecto,
    que es mejor que no abrir.
    """
    ajustes = getattr(webview, "settings", None)
    if isinstance(ajustes, dict):
        ajustes["ALLOW_DOWNLOADS"] = True
        return True
    return False


# ============================================================
# Cuándo cerrar
# ============================================================
#
# En el navegador, cerrar la pestaña no le avisa a nadie. La página late cada 15
# segundos (`/api/latido`), y el launcher cierra el servidor cuando deja de
# latir. Los números son holgados a propósito: una pestaña en segundo plano
# puede quedar con sus relojes demorados hasta un minuto, y cerrar la app con
# alguien adentro es peor que dejarla unos minutos de más.

SILENCIO_MAXIMO = 180.0  # sin latidos durante esto, ya no hay ninguna ventana
GRACIA_SIN_VENTANA = 300.0  # si la ventana nunca abrió, se espera esto y se cierra
PASO_VIGIA = 5.0
# Si entre dos vueltas pasó mucho más que PASO_VIGIA, la máquina estuvo
# suspendida: los relojes de la página también, así que el silencio no cuenta.
SALTO_DE_RELOJ = 30.0


class Vigia:
    """Decide cuándo no queda ninguna ventana abierta.

    Mientras haya un trabajo corriendo no cierra nunca: cerrar a mitad de un
    relevamiento lo pierde, y el trabajo va a terminar igual.
    """

    def __init__(self, ahora):
        self.referencia = ahora
        self.anterior = ahora
        self.vio_una_ventana = False

    def hay_que_cerrar(self, ahora, ultimo_latido, trabajando):
        if ahora - self.anterior > SALTO_DE_RELOJ:
            self.referencia = ahora
        self.anterior = ahora
        # Un latido de antes de que arrancara el vigía también cuenta: la página
        # carga enseguida, a veces antes de la primera vuelta.
        if ultimo_latido is not None:
            self.vio_una_ventana = True
            self.referencia = max(self.referencia, ultimo_latido)
        if trabajando:
            self.referencia = ahora
            return False
        limite = SILENCIO_MAXIMO if self.vio_una_ventana else GRACIA_SIN_VENTANA
        return ahora - self.referencia > limite


def esperar_ventanas(hilo, reloj=time.monotonic, dormir=time.sleep):
    """Espera mientras el servidor corra y alguna ventana siga latiendo."""
    vigia = Vigia(reloj())
    while hilo.is_alive():
        if vigia.hay_que_cerrar(reloj(), backend.ESTADO.ultimo_latido, bool(backend.JOBS.activos())):
            print(T("lau.sin_ventanas"))
            return
        dormir(PASO_VIGIA)


def al_cerrar(ventana):
    """El manejador de `closing` de la ventana nativa.

    Cerrar a mitad de un trabajo lo pierde entero, sin preguntar. Con un trabajo
    corriendo se pide confirmación; sin trabajo, se cierra como siempre.
    Devolver False es lo que le dice a pywebview que no cierre.
    """

    def cerrando():
        if not backend.JOBS.activos():
            return True
        preguntar = getattr(ventana, "create_confirmation_dialog", None)
        if preguntar is None:
            return True
        try:
            return bool(preguntar(T("lau.cerrar_titulo"), T("lau.cerrar_con_trabajo")))
        except Exception:  # noqa: BLE001 (si el diálogo no se puede mostrar, se cierra como antes)
            return True

    return cerrando


def _abrir_ventana_pywebview(url):
    """Ventana nativa propia. Es el camino por defecto: la app tiene que sentirse
    un programa, no una pestaña del navegador.

    `webview.start()` bloquea el hilo principal con el bucle de mensajes de la
    ventana y recién vuelve cuando el usuario la cierra, así que tiene que
    llamarse desde el hilo principal (en macOS es obligatorio). El servidor HTTP
    ya corre en su propio hilo.

    Devuelve False si pywebview no está o si no pudo abrir: ahí se usa el
    navegador en modo aplicación, que no depende de nada extra.
    """
    try:
        import webview
    except Exception:  # noqa: BLE001 (pywebview falla de muchas formas al importar)
        return False
    try:
        # pywebview trae las descargas apagadas, y el paquete es un ZIP que se
        # baja: sin esto, el botón «Descargar» de la ventana nativa no hacía
        # nada. Se prende acá y no en un módulo aparte porque es la única
        # ventana que baja archivos.
        permitir_descargas(webview)
        ventana = webview.create_window(titulo(), url, width=1180, height=860, min_size=(900, 640))
        eventos = getattr(ventana, "events", None)
        if eventos is not None:
            eventos.closing += al_cerrar(ventana)
        webview.start()
        return True
    except Exception:  # noqa: BLE001 (si la ventana no abre, se cae al navegador)
        return False


def _navegador_app(url):
    """Abre el navegador en "modo app": ventana propia, sin barra de direcciones
    ni pestañas. Se ve y se usa como un programa de escritorio.

    Es más robusto que empotrar un motor web propio: usa el Edge/Chrome que ya
    está en la máquina, no agrega nada al ejecutable y no depende de que
    PyInstaller logre empaquetar un runtime .NET. En Windows 11 Edge está siempre.
    """
    candidatos = []
    if sys.platform == "win32":
        pf = os.environ.get("ProgramFiles", r"C:\Program Files")
        pf86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
        local = os.environ.get("LOCALAPPDATA", "")
        candidatos = [
            os.path.join(pf86, "Microsoft", "Edge", "Application", "msedge.exe"),
            os.path.join(pf, "Microsoft", "Edge", "Application", "msedge.exe"),
            os.path.join(pf, "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(pf86, "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(local, "Google", "Chrome", "Application", "chrome.exe"),
        ]
    elif sys.platform == "darwin":
        # ~/Applications además de /Applications: en Mac es igual de común
        # instalar un navegador para el usuario y no para toda la máquina, y
        # ahí no lo encontrábamos. Safari no entra en esta lista porque no
        # tiene modo aplicación: con una Mac que sólo tenga Safari se cae al
        # navegador normal, que es el último escalón y funciona igual.
        casa = os.path.expanduser("~")
        candidatos = [
            base + sufijo
            for base in ("/Applications", os.path.join(casa, "Applications"))
            for sufijo in (
                "/Google Chrome.app/Contents/MacOS/Google Chrome",
                "/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
                "/Brave Browser.app/Contents/MacOS/Brave Browser",
            )
        ]
    else:
        for n in ("google-chrome", "chromium", "chromium-browser", "microsoft-edge"):
            ruta = shutil.which(n)
            if ruta:
                candidatos.append(ruta)

    for exe in candidatos:
        if not exe or not os.path.exists(exe):
            continue
        try:
            # Perfil aparte para que la ventana no herede pestañas ni sesión del
            # navegador del usuario, y quede como una app independiente.
            perfil = os.path.join(backend.dir_datos(), "ventana")
            subprocess.Popen(
                [
                    exe,
                    f"--app={url}",
                    f"--user-data-dir={perfil}",
                    "--no-first-run",
                    "--no-default-browser-check",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except Exception:  # noqa: BLE001 (si un navegador no arranca, se prueba el siguiente)
            continue
    return False


def _diagnostico(url):
    """Reporte de lo que la app puede hacer en esta máquina.

    Existe porque el ejecutable se compila sin consola: si algo no arranca, el
    usuario no ve ningún mensaje. Con `--diagnostico` queda un archivo que se
    puede mandar para saber qué falta.
    """
    import datetime
    import platform

    ahora = datetime.datetime.now().isoformat(timespec="seconds")
    lineas = [
        f"{titulo()} v{backend.VERSION}",
        f"{T('diag.fecha')}: {ahora}",
        f"python: {sys.version.split()[0]}   {T('diag.plataforma')}: {platform.platform()}",
        f"{T('diag.empaquetado')}: {bool(getattr(sys, 'frozen', False))}",
        f"{T('diag.url')}: {url}",
        f"{T('diag.clave')}: {bool(backend.leer_clave())}",
        f"{T('diag.audio')}: {backend.AUDIO_HABILITADO}",
        "",
        T("diag.entorno"),
    ]
    from migrador import audio as audio_mod

    for k, v in audio_mod.verificar_entorno().items():
        lineas.append(f"  {k}: {v}")

    lineas += ["", T("diag.ventana")]
    try:
        import webview

        lineas.append(T("diag.pywebview_ok"))
        # Y ahora lo que de verdad importa: intentar abrirla. Que el import ande
        # no significa que el backend pueda crear una ventana, y ese es
        # exactamente el caso que no se ve de ninguna otra forma en un binario
        # compilado sin consola.
        import threading as _th

        estado: dict[str, bool | str | None] = {"abrio": False, "error": None}

        def _cerrar():
            import time as _t

            _t.sleep(4)
            try:
                estado["abrio"] = len(webview.windows) > 0
                for w in list(webview.windows):
                    w.destroy()
            except Exception as e:  # noqa: BLE001 (el diagnostico informa el fallo, no se cae con el)
                estado["error"] = f"al cerrar: {e}"

        try:
            _th.Thread(target=_cerrar, daemon=True).start()
            webview.create_window(T("diag.titulo_prueba"), html="<p>ok</p>", width=420, height=240)
            webview.start()
            resultado = T("diag.abrio_si") if estado["abrio"] else T("diag.abrio_no")
            lineas.append(T("diag.prueba_ventana", resultado=resultado))
            if estado["error"]:
                lineas.append(T("diag.detalle", detalle=estado["error"]))
        except Exception as e:  # noqa: BLE001 (idem: es un reporte de que anda y que no)
            import traceback

            lineas.append(T("diag.prueba_fallo", tipo=type(e).__name__, error=e))
            for _l in traceback.format_exc().splitlines():
                lineas.append("    " + _l)
    except Exception as e:  # noqa: BLE001 (idem)
        lineas.append(T("diag.pywebview_no", error=e))

    ruta = os.path.join(backend.dir_datos(), "diagnostico.txt")
    with open(ruta, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lineas) + "\n")
    print("\n".join(lineas))
    print("\n" + T("diag.guardado", ruta=ruta))
    return ruta


def _registrar_falla(e):
    """Deja el error en un archivo. Empaquetado sin consola, una excepción al
    arrancar sería invisible: sin esto el usuario ve que 'no abre' y no hay
    forma de saber por qué."""
    import datetime
    import traceback

    try:
        ruta = os.path.join(backend.dir_datos(), "error.log")
        with open(ruta, "a", encoding="utf-8") as f:
            f.write(f"\n===== {datetime.datetime.now().isoformat()} =====\n")
            f.write(traceback.format_exc())
        print(T("lau.detalle_en", ruta=ruta))
    except Exception:  # noqa: BLE001 (escribir el log de error no puede romper el cierre)
        pass


def correr_ytdlp_empaquetado(argv):
    """Atiende al ejecutable cuando el módulo de audio lo llama como yt-dlp.

    Adentro del ejecutable no hay un `yt-dlp` suelto ni un Python aparte: el
    módulo viene empaquetado, y la única forma de correrlo como proceso propio
    (con su timeout y su stderr, que es de donde sale el motivo de cada falla)
    es volver a lanzar este mismo ejecutable con `audio.ARG_YTDLP_EMPAQUETADO`.
    Devuelve el código de salida, o None si `argv` no es ese pedido.
    """
    from migrador.audio import ARG_YTDLP_EMPAQUETADO

    if not argv or argv[0] != ARG_YTDLP_EMPAQUETADO:
        return None
    import yt_dlp

    try:
        yt_dlp.main(argv[1:])
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
    return 0


def main(argv=None):
    codigo = correr_ytdlp_empaquetado(sys.argv[1:] if argv is None else argv)
    if codigo is not None:
        return codigo

    ap = argparse.ArgumentParser(description=titulo())
    ap.add_argument("--puerto", type=int, default=0, help=T("lau.h_puerto"))
    ap.add_argument("--no-abrir", action="store_true", help=T("lau.h_no_abrir"))
    ap.add_argument("--navegador", action="store_true", help=T("lau.h_navegador"))
    ap.add_argument(
        "--sin-ventana-nativa", action="store_true", dest="sin_nativa", help=T("lau.h_sin_ventana")
    )
    ap.add_argument("--diagnostico", action="store_true", help=T("lau.h_diagnostico"))
    args = ap.parse_args(argv)

    srv = backend.crear_servidor(args.puerto)
    puerto = srv.server_address[1]
    url = f"http://127.0.0.1:{puerto}"

    hilo = threading.Thread(target=srv.serve_forever, name="http", daemon=True)
    hilo.start()

    # El diagnóstico trae su propio encabezado con el nombre y la versión, así
    # que acá no se repite: era lo único que imprimía el título dos veces.
    # El servidor sí se levanta igual, porque el reporte prueba contra él que la
    # ventana nativa pueda abrirse.
    if args.diagnostico:
        _diagnostico(url)
        srv.shutdown()
        srv.server_close()
        return 0

    print(f"{titulo()} v{backend.VERSION}")
    print(T("lau.escuchando", url=url))
    if not backend.leer_clave():
        print(T("lau.primera_vez"))

    try:
        if args.no_abrir:
            print(T("lau.ctrl_c"))
            hilo.join()
        elif args.navegador:
            import webbrowser

            webbrowser.open(url)
            print(T("lau.en_navegador"))
            esperar_ventanas(hilo)
        elif not args.sin_nativa and _abrir_ventana_pywebview(url):
            # La ventana se cerró: la app termina con ella, como cualquier
            # programa de escritorio.
            pass
        elif _navegador_app(url):
            # Ventana propia, sin barra de direcciones ni pestañas: se ve y se usa
            # como un programa de escritorio. Usa el motor web que ya está en la
            # máquina, así que no hay nada que empaquetar ni que pueda colgarse.
            print(T("lau.ventana_propia"))
            esperar_ventanas(hilo)
        else:
            import webbrowser

            webbrowser.open(url)
            print(T("lau.en_navegador"))
            esperar_ventanas(hilo)
    except KeyboardInterrupt:
        print("\n" + T("lau.cerrando"))
    finally:
        backend.ESTADO.limpiar()
        srv.shutdown()
        srv.server_close()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        print(T("lau.no_arranco", error=e))
        _registrar_falla(e)
        sys.exit(1)
