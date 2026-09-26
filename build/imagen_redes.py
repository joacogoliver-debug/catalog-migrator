"""
La imagen que muestra GitHub cuando alguien comparte el link del repositorio.

    python build/imagen_redes.py

Deja `docs/redes/social-preview.png`, de 1280×640, que es el tamaño que pide
GitHub en Settings → General → Social preview. Sin ella, cada link compartido
muestra la tarjeta genérica, con el nombre del repo y nada más.

Se arma igual que las capturas: una página con los tokens, las tipografías y el
logo de la app, servida desde `app/web` y fotografiada con Chrome headless. Así
la imagen no se desvía de la app: si cambia un color o el logo, se vuelve a
correr y sale igual que la app. Subirla es decisión de quien administra el
repositorio; esto sólo la deja lista.
"""

import functools
import http.server
import os
import subprocess
import sys
import tempfile
import threading
from typing import override

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(RAIZ, "app", "web")
PAGINA = os.path.join(WEB, "_redes.html")
SALIDA = os.path.join(RAIZ, "docs", "redes", "social-preview.png")
ANCHO, ALTO = 1280, 640

sys.path.insert(0, os.path.join(RAIZ, "build"))
from capturas import navegador  # noqa: E402

# Todo sale de este mismo servidor: tokens, tipografías y logo. Ni una fuente ni
# una imagen de afuera, como en la app.
HTML = """<!doctype html>
<html lang="es" data-theme="oscuro">
<head>
<meta charset="utf-8">
<link rel="stylesheet" href="tokens/fonts.css">
<link rel="stylesheet" href="tokens/colors.css">
<link rel="stylesheet" href="tokens/typography.css">
<link rel="stylesheet" href="tokens/spacing.css">
<style>
  html, body { margin: 0; width: 1280px; height: 640px; overflow: hidden; }
  body {
    background-color: var(--lienzo);
    background-image:
      linear-gradient(var(--linea-fuerte) 1px, transparent 1px),
      linear-gradient(90deg, var(--linea-fuerte) 1px, transparent 1px);
    background-size: 88px 88px;
    color: var(--texto);
    font-family: var(--sans);
    display: flex; align-items: center;
  }
  .caja { margin-left: 96px; max-width: 1000px; }
  .marca { display: flex; align-items: center; gap: 24px; margin-bottom: 56px; }
  .marca img { height: 64px; }
  .marca span { font-size: 30px; font-weight: 600; letter-spacing: -0.02em; }
  h1 { font-size: 68px; font-weight: 300; line-height: 1.05; letter-spacing: -0.02em; margin: 0 0 28px; }
  h1 em { font-style: normal; color: var(--texto-acento); }
  p { font-size: 26px; color: var(--texto-2); margin: 0 0 14px; }
  .mono { font-family: var(--mono); font-size: 20px; color: var(--texto-3); letter-spacing: 0.08em;
          text-transform: uppercase; margin-top: 40px; }
</style>
</head>
<body>
  <div class="caja">
    <div class="marca"><img src="assets/logo.svg" alt=""><span>Migrador de Catálogos</span></div>
    <h1>Cambiá de distribuidora<br><em>sin perder los códigos.</em></h1>
    <p>ISRC, UPC, portadas, hoja de ingesta y validación, desde el canal de YouTube.</p>
    <p>Switch distributors without losing your catalog's codes.</p>
    <div class="mono">Gratis · código abierto · Windows, macOS, Linux</div>
  </div>
</body>
</html>
"""


class _Silencioso(http.server.SimpleHTTPRequestHandler):
    @override
    def log_message(self, format, *args):  # noqa: A002 (así se llama en la biblioteca)
        # El log de acceso sólo ensucia la salida.
        pass


def main():
    with open(PAGINA, "w", encoding="utf-8") as f:
        f.write(HTML)
    manejador = functools.partial(_Silencioso, directory=WEB)
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), manejador)
    hilo = threading.Thread(target=srv.serve_forever, daemon=True)
    hilo.start()
    try:
        with tempfile.TemporaryDirectory() as perfil:
            r = subprocess.run(
                [
                    navegador(),
                    "--headless=new",
                    "--disable-gpu",
                    "--hide-scrollbars",
                    f"--user-data-dir={perfil}",
                    "--no-first-run",
                    f"--window-size={ANCHO},{ALTO}",
                    "--force-device-scale-factor=1",
                    "--virtual-time-budget=6000",
                    f"--screenshot={SALIDA}",
                    f"http://127.0.0.1:{srv.server_address[1]}/_redes.html",
                ],
                capture_output=True,
                text=True,
            )
        if not os.path.exists(SALIDA):
            print(r.stderr[-600:])
            sys.exit("No se generó la imagen.")
    finally:
        srv.shutdown()
        srv.server_close()
        hilo.join()
        os.remove(PAGINA)
    print(f"imagen para redes en {os.path.relpath(SALIDA, RAIZ)} ({os.path.getsize(SALIDA) // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
