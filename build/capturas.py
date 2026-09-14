# -*- coding: utf-8 -*-
"""
Genera las capturas de pantalla de la app.

    python build/capturas.py                 las del README (claro, 1600x900)
    python build/capturas.py --todo          todas, claro y oscuro, 3200x1800
    python build/capturas.py --todo --salida "C:\\donde\\quieras"

Está acá, y no son imágenes sueltas subidas a mano, por la misma razón que el
icono: si la interfaz cambia, las capturas se rehacen con un comando en vez de
quedar mintiendo durante meses.

Cómo funciona. Levanta el servidor real de la app, deja una página temporal
(`_capturas.html`) al lado de la interfaz que carga el CSS y el JS de verdad con
`fetch` interceptado, y le saca la foto con Chrome en modo headless. Lo que se ve
es la aplicación real corriendo, no una maqueta.

Todo sale en **16:9**, que es el formato de una slide.

Las vistas más altas que el cuadro NO se desplazan con scroll. En headless,
`scrollTo` y la captura no componen bien: la cabecera sticky termina dibujada en
el medio de la imagen y arriba queda una franja vacía. En vez de eso se renderiza
cada vista a su alto natural, en una sola pasada, y de esa imagen se recortan los
cuadros de 16:9 que hagan falta. Es determinístico y sale más de una captura útil
por render.

**Los datos son de ejemplo.** El artista, los títulos, los ISRC y los UPC son
inventados, para no publicar el catálogo de nadie. Los problemas que se ven (un
producto sin UPC, otro con ISRC incompletos, un orden estimado) están puestos a
propósito, porque una captura donde todo está perfecto no muestra para qué sirve
la herramienta.
"""

import argparse
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
PAGINA = os.path.join(WEB, "_capturas.html")

sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "app"))

# 16:9. El contenedor de la app llega a 1440, así que a 1600 quedan márgenes
# naturales a los costados en vez de texto pegado al borde.
ANCHO, ALTO = 1600, 900


# ============================================================
# Las vistas
# ============================================================
#
# `prep`   JavaScript que corre con la app ya cargada, justo antes de render().
# `alto`   alto del viewport para que la vista entre entera, sin scroll.
# `cortes` de qué altura arranca cada cuadro 16:9 que se recorta de ese render.
# `readme` marca las pocas que van commiteadas.

VISTAS = [
    # --- entrada ---
    dict(nombre="entrada", readme=True, alto=1000, prep=""),
    dict(nombre="entrada-error-cuota", alto=1180, cortes=[0, 280], prep="""
        S.error = 'Se agotó el cupo diario de la API de YouTube. Si esta copia trae '
                + 'una clave compartida, el cupo se reparte entre todos los que la usan. '
                + 'Cargando tu propia clave tenés el cupo entero para vos, es gratis y '
                + 'se saca en tres pasos.';
        S.errorCodigo = 'cuota';"""),
    dict(nombre="clave-propia", alto=1000, prep="S.vista = 'clave';"),
    dict(nombre="terminos", alto=4000, cortes=[0, 850, 1700, 2550],
         prep="S.vista = 'terminos';"),

    # --- catálogo ---
    dict(nombre="catalogo", readme=True, alto=1340, cortes=[0, 440], prep="CAT();"),
    dict(nombre="catalogo-detalle", alto=1950, cortes=[620, 1050],
         prep="CAT(); S.expandidos.add('p2');"),
    dict(nombre="catalogo-seleccion", alto=1340, cortes=[440],
         prep="CAT(); S.seleccion.delete('p3'); S.seleccion.delete('p4');"),
    dict(nombre="catalogo-filtro-fecha", alto=1480, cortes=[420],
         prep="CAT(); S.filtro.modo='fechas'; S.filtro.anioDesde=2022; S.filtro.anioHasta=2024;"),
    dict(nombre="catalogo-filtro-distribuidora", alto=1480, cortes=[420],
         prep="CAT(); S.filtro.modo='distribuidora'; S.filtro.distribs=new Set(['DistroKid']);"),
    dict(nombre="catalogo-busqueda", alto=1200, cortes=[300],
         prep="CAT(); S.filtro.texto='jacar';"),
    dict(nombre="catalogo-vacio", alto=1150, cortes=[260],
         prep="CAT(); S.filtro.texto='zzz';"),

    # --- qué descargar ---
    dict(nombre="descargar", readme=True, alto=1060, prep="CAT(); S.paso=3;"),
    dict(nombre="descargar-audio", alto=1320, cortes=[0, 420],
         prep="CAT(); S.paso=3; S.opciones.audio=true;"),
    dict(nombre="descargar-tidal-conectando", alto=1320, cortes=[380], prep="""
        CAT(); S.paso = 3; S.opciones.audio = true;
        S.tidal = {url: 'https://link.tidal.com/ABC12', codigo: 'ABC12',
                   device_code: 'x', esperando: true};"""),
    dict(nombre="descargar-tidal-ok", alto=1180, cortes=[280], prep="""
        CAT(); S.paso = 3; S.opciones.audio = true;
        S.config.tidal_conectada = true;"""),

    # --- trabajo y resultado ---
    dict(nombre="progreso", readme=True, alto=1000, prep="""
        CAT(); S.paso = 4; S.ocupado = true;
        S.job = {progreso: 0.62, mensaje: 'Bajando portadas (3 de 4)', log: [
          'Relevando el canal Delta Serrano - Topic',
          '27 tracks en 4 productos',
          'Buscando ISRC y UPC en Deezer',
          'Cartografia del ruido: 9 de 9 ISRC',
          'Ducha fria: 3 de 5 ISRC',
          'Sesiones del jacaranda: sin UPC, 0 de 12 ISRC',
          'Muestrame la mini: 1 de 1 ISRC',
          'Portadas: pidiendo 3000x3000 a Apple',
          'Cartografia del ruido: 3000x3000',
          'Ducha fria: 1400x1400 (por debajo del recomendado)',
          'Sesiones del jacaranda: sin portada en Apple']};"""),
    dict(nombre="listo", readme=True, alto=1300, cortes=[0, 400],
         prep="CAT(); S.paso=4; S.resultado = RES;"),
    dict(nombre="listo-avisos", alto=1500, cortes=[420], prep="""
        CAT(); S.paso = 4; S.resultado = RES;
        DESPUES = function () {
          var d = document.querySelectorAll('details.acordeon');
          if (d[0]) d[0].open = false;
          if (d[1]) d[1].open = true;
        };"""),
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
                 "mensaje": "El título arrastra texto de YouTube, como (Official Video)."},
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

    html = html.replace("{{TOKEN}}", "capturas")   # nunca sale un pedido de verdad

    # Solo para capturar: la app estira `main` para que el pie quede pegado al
    # fondo de la ventana. Renderizando a un alto generoso eso deja un hueco
    # entre el contenido y el pie, y el recorte automatico no puede distinguir
    # ese hueco del final de la pagina. Sin el estiramiento, el render termina
    # exactamente donde termina el contenido.
    #
    # Y sin animaciones: la de entrada dura 240 ms, y como el reloj virtual de
    # Chrome corre solo, la foto caia a veces en la mitad del fade y salia toda
    # lavada. Una captura no tiene que depender de cuando se disparo.
    html = html.replace("</head>", "<style>"
                        ".app{min-height:0}"
                        "*,*::before,*::after{animation:none!important;transition:none!important}"
                        "</style></head>")

    preps = {v["nombre"]: v.get("prep", "") for v in VISTAS}

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
  const vista = q.get('vista') || 'entrada';
  const tema = q.get('tema') || 'claro';
  const PREPS = %(preps)s;
  const CATALOGO = %(catalogo)s;
  const RES = %(resultado)s;
  /* Atajo para las vistas que arrancan con el catálogo ya relevado. */
  const CAT = () => adoptarCatalogo(JSON.parse(JSON.stringify(CATALOGO)));
  let DESPUES = null;

  document.documentElement.setAttribute('data-theme', tema === 'oscuro' ? 'dark' : 'light');

  /* app.js arranca de forma asincrónica; esperamos a que tenga su config y
     recién ahí ponemos el estado de la vista que queremos fotografiar.
     Se mira `S` a secas y no `window.S`: en un script clásico un `const` de
     nivel superior queda en el ámbito léxico global y NUNCA aparece como
     propiedad de window, así que preguntar por window.S esperaba para siempre. */
  (function esperar() {
    if (typeof S === 'undefined' || !S.config) return setTimeout(esperar, 20);
    aplicarTema(tema);
    try { eval(PREPS[vista] || ''); } catch (e) { console.error('prep', vista, e); }
    render();
    if (DESPUES) DESPUES();
    document.documentElement.setAttribute('data-listo', vista);
  })();
})();
</script>
""" % {"config": json.dumps(CONFIG, ensure_ascii=False),
       "catalogo": json.dumps(catalogo_demo(), ensure_ascii=False),
       "resultado": json.dumps(resultado_demo(), ensure_ascii=False),
       "preps": json.dumps(preps, ensure_ascii=False)}

    html = html.replace('<script src="app.js"></script>', stub)
    with open(PAGINA, "w", encoding="utf-8") as f:
        f.write(html)


def recortar(render, carpeta, base, cortes, escala, tema):
    """Saca los cuadros de 16:9 del render y los deja numerados.

    Recortar en vez de hacer scroll es lo que evita el artefacto de headless, y
    de paso cada render rinde mas de una captura util."""
    from PIL import Image

    ancho_px, alto_px = ANCHO * escala, ALTO * escala
    img = Image.open(render).convert("RGB")

    # Dónde termina de verdad el contenido. Adivinar el alto de cada vista a
    # mano no escala: el primer intento dejó dos capturas de los términos en
    # blanco. Esto lo mide sobre el render y ajusta los cortes solo.
    fondo_fin = _fin_del_contenido(img)
    tope = max(0, fondo_fin - alto_px)

    # Cortes dentro de lo que existe, sin repetidos ni cuadros vacíos.
    ys, vistos = [], set()
    for corte in cortes:
        y = max(0, min(corte * escala, tope))
        if y not in vistos:
            vistos.add(y)
            ys.append(y)

    hechas = 0
    for n, y in enumerate(ys, 1):
        cuadro = img.crop((0, y, ancho_px, y + alto_px))
        nombre = base if len(ys) == 1 else f"{base}-{n}"
        salida = os.path.join(carpeta, nombre + ".png")
        cuadro.save(salida, optimize=True)
        print(f"    {tema:7} {nombre + '.png':44} {os.path.getsize(salida) / 1024:6.0f} KB")
        hechas += 1
    return hechas


def _fin_del_contenido(img, margen=48):
    """Última fila del render que no es fondo liso, más un margen.

    Se mira fila por fila desde abajo: una fila de fondo es toda del mismo
    color. Alcanza y sobra, porque el fondo de la app es plano y no hay ni
    degradados ni imágenes de relleno."""
    pix = img.load()
    for y in range(img.height - 1, -1, -1):
        primero = pix[0, y]
        # Muestreo cada 8 px: con 3200 de ancho, recorrerlo entero por fila es
        # medio millón de lecturas al pedo.
        for x in range(0, img.width, 8):
            if pix[x, y] != primero:
                return min(img.height, y + margen)
    return img.height


def main():
    ap = argparse.ArgumentParser(description="Capturas de la app, en 16:9.")
    ap.add_argument("--todo", action="store_true",
                    help="Todas las vistas, en claro y oscuro, al doble de resolución.")
    ap.add_argument("--salida", default=None,
                    help="Carpeta destino. Por defecto docs/capturas.")
    args = ap.parse_args()

    destino = args.salida or os.path.join(RAIZ, "docs", "capturas")
    # Las del README van commiteadas, así que a 1x para no engordar el repo. Las
    # del set completo son para armar slides, y ahí conviene el doble.
    escala = 2 if args.todo else 1
    temas = ("claro", "oscuro") if args.todo else ("claro",)
    # El numero sale de la lista completa, asi los nombres no se corren
    # cuando se marca o desmarca una vista como del README.
    vistas = [(i, v) for i, v in enumerate(VISTAS, 1)
              if args.todo or v.get("readme")]

    import server as backend

    escribir_pagina()
    chrome = navegador()
    print(f"    navegador: {chrome}")
    print(f"    destino:   {destino}")
    print(f"    tamano:    {ANCHO * escala}x{ALTO * escala} (16:9)")

    srv = backend.crear_servidor(0)
    puerto = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    for _ in range(100):
        try:
            c = http.client.HTTPConnection("127.0.0.1", puerto, timeout=1)
            c.request("GET", "/_capturas.html")
            if c.getresponse().status == 200:
                break
        except Exception:
            time.sleep(0.05)
    perfil = os.path.join(RAIZ, "build", "migrador", "perfil-capturas")
    crudo = os.path.join(RAIZ, "build", "migrador", "render.png")
    os.makedirs(os.path.dirname(crudo), exist_ok=True)
    hechas = 0
    try:
        for tema in temas:
            carpeta = os.path.join(destino, tema) if args.todo else destino
            os.makedirs(carpeta, exist_ok=True)
            for i, v in vistas:
                alto = v.get("alto", ALTO)
                url = (f"http://127.0.0.1:{puerto}/_capturas.html"
                       f"?vista={v['nombre']}&tema={tema}")
                if os.path.exists(crudo):
                    os.remove(crudo)
                r = subprocess.run([
                    chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                    f"--user-data-dir={perfil}", "--no-first-run",
                    f"--window-size={ANCHO},{alto}",
                    f"--force-device-scale-factor={escala}",
                    # Tiempo virtual: Chrome adelanta el reloj hasta que la
                    # pagina se queda quieta, asi no hay que adivinar cuanto
                    # tardan las fuentes.
                    "--virtual-time-budget=6000",
                    f"--screenshot={crudo}", url,
                ], capture_output=True, text=True)
                if not os.path.exists(crudo):
                    print(r.stdout[-600:])
                    print(r.stderr[-600:])
                    sys.exit(f"No se genero el render de {v['nombre']}")
                hechas += recortar(crudo, carpeta, f"{i:02d}-{v['nombre']}",
                                   v.get("cortes", [0]), escala, tema)
    finally:
        srv.shutdown()
        srv.server_close()
        for f in (PAGINA, crudo):
            if os.path.exists(f):
                os.remove(f)
        shutil.rmtree(perfil, ignore_errors=True)

        shutil.rmtree(perfil, ignore_errors=True)

    print(f"\n    {hechas} capturas en {destino}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
