"""
Prueba, en la ventana nativa de verdad, que el paquete se puede bajar.

Por qué existe. Los tests de la app hablan con el servidor por HTTP y no abren
ninguna ventana, y la descarga es justo lo que depende de la ventana: en cada
sistema la maneja un código distinto de pywebview (WebView2 en Windows, WebKit
en macOS). En Windows se probaba a mano; en macOS no se probaba, y la primera
persona que usó la app en una Mac no pudo bajar el paquete.

Qué hace. Levanta el servidor con un ZIP de prueba ya registrado, abre la
ventana nativa y aprieta «Descargar» desde la página, con el mismo código que
corre el botón, y mira si el archivo llegó entero.

En macOS la ventana descarta las descargas sin avisar (se probó acá mismo: el
servidor entregaba el ZIP y el cuadro de «Guardar» nunca se abría), así que
ahí el botón le pide al servidor que copie el paquete a la carpeta Descargas.
La prueba apunta esa carpeta a una temporal y busca el archivo ahí. El panel
de «Guardar como» igual se reemplaza por uno que contesta solo: si alguna vez
la ventana vuelve a usarlo, la prueba no queda colgada esperando un clic.

Además consulta a Deezer y a Apple con el código de la app, porque de ahí
salen los ISRC, los UPC y las portadas, y eso tampoco se probaba en macOS.

Uso: python build/prueba_ventana.py        (sale con 0 si todo anduvo)
"""

import logging
import os
import platform
import sys
import tempfile
import threading
import time
import zipfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for carpeta in ("src", "app"):
    sys.path.insert(0, os.path.join(RAIZ, carpeta))

TRABAJO = "abcdef123456"
ARCHIVO = "prueba-paquete.zip"
# Lo que hace el botón «Descargar», con el paquete de prueba como resultado.
APRETAR = """
(async () => {
  try {
    S.resultado = { descarga: '/api/descargar/%s', guardar: '/api/guardar/%s', archivo: '%s', bytes: 1 };
    await ACCIONES.descargar();
  } catch (e) {
    console.error(e);
  }
})()
""" % (TRABAJO, TRABAJO, ARCHIVO)


class PanelQueAcepta:
    """Reemplazo del panel «Guardar como» de macOS: acepta solo, en `destino`."""

    destino = ""
    llamadas: list[str] = []  # qué le pidieron, en orden: dice por qué camino vino

    @classmethod
    def savePanel(cls):  # noqa: N802 (el nombre es el de AppKit)
        cls.llamadas.append("savePanel")
        return cls()

    def __getattr__(self, nombre):
        # setTitle_, setDirectoryURL_, setNameFieldStringValue_ y compañía.
        self.llamadas.append(nombre)
        return lambda *a, **k: None

    def runModal(self):  # noqa: N802
        self.llamadas.append("runModal")
        return 1  # NSFileHandlingPanelOKButton

    def filename(self):
        self.llamadas.append("filename")
        return self.destino


def consultar_fuentes():
    """Deezer y Apple, con el código de la app. Devuelve las líneas del informe
    y si las dos contestaron."""
    from migrador import certificados
    from migrador import portadas
    from migrador import relevar_core as R

    certificados.preparar()
    lineas, bien = [], True
    album = R._deezer_json("album/302127") or {}
    lineas.append(f"Deezer, un álbum por id: título {album.get('title')!r}, UPC {album.get('upc')!r}")
    bien = bien and bool(album.get("upc"))
    isrc, album_id, confianza = R.deezer_match({"track": "Around the World", "duration_s": 430}, "Daft Punk")
    lineas.append(f"Deezer, búsqueda de un tema: ISRC {isrc!r}, álbum {album_id}, confianza {confianza!r}")
    bien = bien and bool(isrc)
    apple = portadas._http_json(f"{portadas.ITUNES_SEARCH}?term=daft+punk+discovery&entity=album&limit=1")
    lineas.append(f"Apple, búsqueda de un álbum: {len((apple or {}).get('results') or [])} resultado(s)")
    bien = bien and bool((apple or {}).get("results"))
    return lineas, bien


def probar_descarga():
    """Abre la ventana, aprieta «Descargar» y devuelve (líneas, anduvo)."""
    import server as backend
    import webview

    lineas = [f"pywebview {getattr(webview, '__version__', '?')}"]
    logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
    logging.getLogger("pywebview").setLevel(logging.DEBUG)

    carpeta = tempfile.mkdtemp(prefix="prueba-ventana-")
    origen = os.path.join(carpeta, "origen", ARCHIVO)
    os.makedirs(os.path.dirname(origen))
    with zipfile.ZipFile(origen, "w") as z:
        z.writestr("hola.txt", "hola " * 20000)
    backend.ESTADO.registrar_zip(TRABAJO, origen)
    destino = os.path.join(carpeta, "bajado.zip")

    pedidos, tickets = [], []
    descargar = backend.Handler._descargar
    emitir = backend.ESTADO.emitir_ticket

    def emitir_y_anotar(job_id, *a, **k):
        tickets.append(job_id)
        return emitir(job_id, *a, **k)

    backend.ESTADO.emitir_ticket = emitir_y_anotar

    def espia(self, job_id):
        pedidos.append(job_id)
        return descargar(self, job_id)

    backend.Handler._descargar = espia

    srv = backend.crear_servidor(0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}"

    en_mac = sys.platform == "darwin"
    backend.carpeta_descargas = lambda: carpeta
    if en_mac:
        # El módulo de pywebview para macOS llama a `AppKit.NSSavePanel`; se
        # le cambia ese nombre en el propio AppKit, que es el que él importó.
        import AppKit  # pyright: ignore[reportMissingImports]

        PanelQueAcepta.destino = destino
        AppKit.NSSavePanel = PanelQueAcepta

    sys.path.insert(0, os.path.join(RAIZ, "app"))
    import launcher

    launcher.permitir_descargas(webview)
    ventana = webview.create_window("prueba", url, width=900, height=640)
    assert ventana is not None
    resultado = {"anduvo": False}

    def correr():
        try:
            time.sleep(8)  # que la página termine de cargar
            # `run_js` y no `evaluate_js`: el segundo envuelve el código en un
            # `eval`, y la página lo prohíbe con su Content-Security-Policy.
            guardado = os.path.join(carpeta, ARCHIVO)
            if not en_mac:
                # Fuera de macOS se prueba primero la salida de emergencia, que
                # es el mismo guardado que en macOS hace el botón. Primero,
                # porque después el diálogo de «Guardar» de la descarga deja la
                # ventana ocupada.
                ventana.run_js(APRETAR.replace("ACCIONES.descargar()", "ACCIONES['guardar-en-descargas']()"))
                for _ in range(15):
                    time.sleep(1)
                    if os.path.exists(guardado):
                        break
            ventana.run_js(APRETAR)
            for _ in range(20):
                time.sleep(1)
                if (en_mac and os.path.exists(guardado)) or pedidos:
                    break
            lineas.append(f"tickets de descarga que pidió la página: {len(tickets)}")
            lineas.append(f"pedidos del ZIP que llegaron al servidor: {len(pedidos)}")
            if en_mac:
                lineas.append(f"lo que se le pidió al panel de guardar: {PanelQueAcepta.llamadas}")
                por_la_ventana = True
            else:
                # El diálogo de guardar no se reemplaza: de la descarga alcanza
                # con que el pedido del ZIP haya salido de la ventana.
                por_la_ventana = len(pedidos) == 1
            llego = os.path.exists(guardado)
            tam = os.path.getsize(guardado) if llego else 0
            lineas.append(f"archivos en la carpeta de la prueba: {sorted(os.listdir(carpeta))}")
            lineas.append(f"archivo guardado: {llego}, {tam} de {os.path.getsize(origen)} bytes")
            resultado["anduvo"] = por_la_ventana and llego and tam == os.path.getsize(origen)
        except Exception as e:  # noqa: BLE001 (es un informe: se anota y se sigue)
            lineas.append(f"la prueba se cortó: {e!r}")
        finally:
            print("\n".join(["", "==== INFORME ===="] + lineas), flush=True)
            os._exit(0 if resultado["anduvo"] and fuentes["bien"] else 1)

    threading.Thread(target=correr, daemon=True).start()
    webview.start()
    return lineas, resultado["anduvo"]


fuentes = {"bien": False}

if __name__ == "__main__":
    print(f"{platform.platform()} · Python {platform.python_version()}", flush=True)
    informe, fuentes["bien"] = consultar_fuentes()
    print("\n".join(informe), flush=True)
    probar_descarga()
