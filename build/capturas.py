# -*- coding: utf-8 -*-
"""
Genera las capturas de pantalla del README.

    python build/capturas.py

Escribe docs/capturas/*.png. Está acá, y no son imágenes sueltas subidas a mano,
por la misma razón que el icono: si la interfaz cambia, las capturas se rehacen
con un comando en vez de quedar mintiendo durante meses.

Cómo funciona. Levanta el servidor real de la app, deja una página temporal
(`_capturas.html`) al lado de la interfaz que carga el CSS y el JS de verdad con
`fetch` interceptado, y le saca la foto con Chrome en modo headless. O sea que lo
que se ve es la aplicación real corriendo, no una maqueta.

**Los datos son de ejemplo.** El artista, los títulos, los ISRC y los UPC son
inventados, para no publicar el catálogo de nadie. Los errores de validación que
se ven son reales en el sentido de que el validador los detectó sobre esos datos.
"""

import http.client
import json
import os
import shutil
import subprocess
import sys
import threading
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(RAIZ, "app", "web")
DESTINO = os.path.join(RAIZ, "docs", "capturas")
PAGINA = os.path.join(WEB, "_capturas.html")

sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "app"))

# Ancho cómodo de escritorio y alto suficiente para que entre la vista sin
# recortar. Chrome saca la foto del viewport, así que esto es el tamaño final.
ANCHO = 1280
ALTOS = {"01-pegar-link": 1000, "02-catalogo": 1330, "03-que-bajar": 1060,
         "04-listo": 1270, "05-catalogo-oscuro": 1330}

# Qué capturamos y con qué nombre. El orden es el del flujo de la app.
VISTAS = [
    ("01-pegar-link", "paso1", "claro"),
    ("02-catalogo", "paso2", "claro"),
    ("03-que-bajar", "paso3", "claro"),
    ("04-listo", "paso4", "claro"),
    ("05-catalogo-oscuro", "paso2", "oscuro"),
]


def navegador():
    for ruta in (
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.join(os.environ.get("LOCALAPPDATA", ""),
                     r"Google\Chrome\Application\chrome.exe"),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    ):
        if ruta and os.path.exists(ruta):
            return ruta
    for n in ("google-chrome", "chromium", "chromium-browser", "microsoft-edge"):
        r = shutil.which(n)
        if r:
            return r
    sys.exit("No encontré Chrome ni Edge para sacar las capturas.")


# ============================================================
# Datos de ejemplo
# ============================================================

def catalogo_demo():
    """Un catálogo inventado, con los problemas que la app está hecha para
    encontrar: un producto sin UPC, otro con ISRC incompletos y un orden de
    tracks estimado. Una captura donde todo está perfecto no muestra para qué
    sirve la herramienta."""

    def tracks(n, titulos, prefijo, con_isrc):
        return [{
            "n": i + 1,
            "titulo": titulos[i],
            "isrc": f"AR{prefijo}{2400000 + i:07d}"[:12] if i < con_isrc else "",
            "duracion": f"{2 + (i % 3)}:{(17 + i * 7) % 60:02d}",
            "views": 48210 - i * 3100,
            "url": "#",
        } for i in range(n)]

    productos = [
        {"id": "p1", "titulo": "Cartografía del ruido", "tipo": "album",
         "anio": 2021, "fecha": "2021-04-16", "upc": "0885012345678",
         "sello": "Cerro Bayo", "distribuidora": "DistroKid",
         "tracks": 9, "views": 412_338, "orden_estimado": False, "con_isrc": 9,
         "detalle": tracks(9, ["Andén norte", "Cartografía del ruido", "Bagual",
                               "Tarde de abril", "Sin señal", "Kerosén",
                               "La última pieza", "Nadie mira el río",
                               "Cierre"], "CB1", 9)},
        {"id": "p2", "titulo": "Ducha fría", "tipo": "EP",
         "anio": 2023, "fecha": "2023-08-02", "upc": "0885012345685",
         "sello": "Cerro Bayo", "distribuidora": "DistroKid",
         "tracks": 5, "views": 188_402, "orden_estimado": False, "con_isrc": 3,
         "detalle": tracks(5, ["Ducha fría", "Mediodía", "Pileta vacía",
                               "Hormiga", "Nueve y cuarto"], "CB2", 3)},
        {"id": "p3", "titulo": "Sesiones del jacarandá", "tipo": "album",
         "anio": 2022, "fecha": "2022-12-27", "upc": "",
         "sello": "", "distribuidora": "Believe",
         "tracks": 12, "views": 96_771, "orden_estimado": True, "con_isrc": 0,
         "detalle": tracks(12, ["Walsh", "Quimeras", "Desenredo", "Vidrio",
                                "Telón de plomo", "Calavera", "Generala",
                                "Cornisa", "Velasco", "Engranaje", "Nagasaki",
                                "Abejorro azul"], "CB3", 0)},
        {"id": "p4", "titulo": "Muéstrame la mini", "tipo": "Single",
         "anio": 2024, "fecha": "2024-02-09", "upc": "0885012345708",
         "sello": "Garra", "distribuidora": "ONErpm",
         "tracks": 1, "views": 731_005, "orden_estimado": False, "con_isrc": 1,
         "detalle": tracks(1, ["Muéstrame la mini"], "CB4", 1)},
    ]
    return {
        "artista": "Delta Serrano",
        "diagnostico": {"via_topic": True, "canal": "Delta Serrano - Topic",
                        "canal_pedido": "Delta Serrano", "descartados": 17},
        "productos": productos,
        "resumen": {"products": 4, "tracks": 27, "with_upc": 3,
                    "with_isrc": 13, "views": 1_428_516},
        "filtros": {"distribuidoras": [{"name": "DistroKid", "count": 2},
                                       {"name": "Believe", "count": 1},
                                       {"name": "ONErpm", "count": 1}],
                    "anio_min": 2021, "anio_max": 2024},
    }


def resultado_demo():
    return {
        "archivo": "delta-serrano-migracion.zip",
        "bytes": 1_284_003_112,
        "descarga": "#",
        "productos": 4,
        "portadas": 3,
        "validacion": {
            "apto": False,
            "resumen": {"errores": 2, "avisos": 4},
            "hallazgos": [
                {"nivel": "error", "producto": "Sesiones del jacarandá", "track": "",
                 "mensaje": "Falta el UPC. Sin ese código la distribuidora asigna uno nuevo y se pierde la continuidad del release."},
                {"nivel": "error", "producto": "Ducha fría", "track": "Hormiga",
                 "mensaje": "El ISRC no tiene el formato de 12 caracteres."},
                {"nivel": "aviso", "producto": "Sesiones del jacarandá", "track": "",
                 "mensaje": "El orden de los tracks es estimado por fecha de subida y no está confirmado."},
                {"nivel": "aviso", "producto": "Sesiones del jacarandá", "track": "",
                 "mensaje": "Falta el sello (℗)."},
                {"nivel": "aviso", "producto": "Ducha fría", "track": "",
                 "mensaje": "La portada entra pero está por debajo de los 3000×3000 recomendados."},
                {"nivel": "aviso", "producto": "Muéstrame la mini", "track": "",
                 "mensaje": "El título arrastra texto de YouTube."},
            ],
        },
    }


CONFIG = {
    "version": "1.0.0", "terminos_aceptados": True, "terminos_version": "1.0",
    "tiene_clave": True, "clave_incluida": True, "audio_habilitado": True,
    "entorno": {"ffmpeg": True, "ffmpeg_incluido": True, "ffprobe": True,
                "js_runtime": True, "tiddl": True, "yt_dlp": True,
                "puede_flac": True, "puede_referencia": True},
    "tidal_conectada": False, "catalogo_cargado": False,
    "trabajo_en_curso": False,
}


# ============================================================
# La página de capturas
# ============================================================

def escribir_pagina():
    """index.html con `fetch` interceptado y el estado puesto a mano.

    Se toca lo mínimo: el CSS y el JS son los de la app, sin copiar ni recortar
    nada. Si mañana cambia un botón, la captura lo muestra sola."""
    with open(os.path.join(WEB, "index.html"), encoding="utf-8") as f:
        html = f.read()

    # No hace falta token: nunca sale un pedido de verdad.
    html = html.replace("{{TOKEN}}", "capturas")

    stub = """
<script>
/* Interceptamos fetch ANTES de app.js: la app arranca pidiendo /api/config y sin
   esto mostraría el cartel de "no pude conectar". */
(function () {
  const RESP = {
    '/api/config': %(config)s,
    '/api/catalogo': %(catalogo)s
  };
  window.fetch = function (ruta) {
    const datos = RESP[String(ruta).split('?')[0]] || {};
    return Promise.resolve({
      ok: true, status: 200, json: () => Promise.resolve(datos)
    });
  };
})();
</script>
<script src="app.js"></script>
<script>
(function () {
  const q = new URLSearchParams(location.search);
  const vista = q.get('vista') || 'paso1';
  const tema = q.get('tema') || 'claro';
  if (tema === 'oscuro') document.documentElement.setAttribute('data-theme', 'dark');
  else document.documentElement.setAttribute('data-theme', 'light');

  /* app.js arranca de forma asincrónica; esperamos a que tenga su config y
     recién ahí ponemos el estado de la vista que queremos fotografiar.
     Se mira `S` a secas y no `window.S`: en un script clásico un `const` de
     nivel superior queda en el ámbito léxico global y NUNCA aparece como
     propiedad de window, así que preguntar por window.S esperaba para siempre
     y la foto salía del paso 1. */
  (function esperar() {
    if (typeof S === 'undefined' || !S.config) return setTimeout(esperar, 20);
    aplicarTema(tema);
    if (vista !== 'paso1') {
      adoptarCatalogo(%(catalogo)s);
      if (vista === 'paso3') { S.paso = 3; S.opciones = {planilla: true, portadas: true, audio: true}; }
      if (vista === 'paso4') { S.paso = 4; S.resultado = %(resultado)s; }
    }
    render();
    document.documentElement.setAttribute('data-listo', vista + ':' + S.paso);
  })();
})();
</script>
""" % {"config": json.dumps(CONFIG, ensure_ascii=False),
       "catalogo": json.dumps(catalogo_demo(), ensure_ascii=False),
       "resultado": json.dumps(resultado_demo(), ensure_ascii=False)}

    # Reemplazamos la carga normal de app.js por el bloque de arriba.
    html = html.replace('<script src="app.js"></script>', stub)
    with open(PAGINA, "w", encoding="utf-8") as f:
        f.write(html)


def main():
    import server as backend

    os.makedirs(DESTINO, exist_ok=True)
    escribir_pagina()
    chrome = navegador()
    print(f"    navegador: {chrome}")

    srv = backend.crear_servidor(0)
    puerto = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    # Esperamos a que el servidor conteste antes de disparar Chrome.
    for _ in range(100):
        try:
            c = http.client.HTTPConnection("127.0.0.1", puerto, timeout=1)
            c.request("GET", "/_capturas.html")
            if c.getresponse().status == 200:
                break
        except Exception:
            time.sleep(0.05)

    perfil = os.path.join(RAIZ, "build", "migrador", "perfil-capturas")
    try:
        for nombre, vista, tema in VISTAS:
            salida = os.path.join(DESTINO, nombre + ".png")
            url = f"http://127.0.0.1:{puerto}/_capturas.html?vista={vista}&tema={tema}"
            r = subprocess.run([
                chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                f"--user-data-dir={perfil}", "--no-first-run",
                f"--window-size={ANCHO},{ALTOS[nombre]}",
                # Tiempo virtual: Chrome adelanta el reloj hasta que la página se
                # queda quieta, así no hay que adivinar cuánto tardan las fuentes.
                "--virtual-time-budget=6000",
                f"--screenshot={salida}", url,
            ], capture_output=True, text=True)
            if not os.path.exists(salida):
                print(r.stdout[-800:])
                print(r.stderr[-800:])
                sys.exit(f"No se generó {nombre}.png")
            print(f"    {nombre}.png  {os.path.getsize(salida) / 1024:6.0f} KB")
    finally:
        srv.shutdown()
        srv.server_close()
        if os.path.exists(PAGINA):
            os.remove(PAGINA)
        shutil.rmtree(perfil, ignore_errors=True)

    print(f"\n    Listo. Están en {os.path.relpath(DESTINO, RAIZ)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
