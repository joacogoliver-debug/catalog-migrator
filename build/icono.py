"""
Genera el icono de la app.

    python build/icono.py

Escribe app/web/assets/icono.png (512) y app/web/assets/icono.ico (multi-tamaño).
Está acá y no como imagen suelta para que el icono sea reproducible desde el
código, igual que todo lo demás del repositorio.

La forma sale de DESIGN-SYSTEM.md. Es la barra de acento repetida tres veces en
anchos decrecientes: geometría recta, sin redondeo, sin degradado y sin
ilustración. Se lee como una lista de catálogo, que es lo que la app manipula.

El teal va de fondo porque §3.1 lo permite en superficies chicas y puntuales, y
un icono lo es. Las barras van en hueso, que es la relación fondo/texto de la
marca en piezas oscuras.
"""

import os
import sys

from PIL import Image, ImageDraw

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESTINO = os.path.join(RAIZ, "app", "web", "assets")

TEAL = (56, 127, 126, 255)      # #387F7E
HUESO = (245, 242, 237, 255)    # #F5F2ED

# Proporciones relativas al lado, para que el dibujo sea el mismo en 16 y en 512.
MARGEN = 0.195
ALTO_BARRA = 0.105
SEPARACION = 0.075
ANCHOS = (1.0, 0.68, 0.40)


def dibujar(lado):
    img = Image.new("RGBA", (lado, lado), TEAL)
    d = ImageDraw.Draw(img)

    x0 = MARGEN * lado
    ancho_util = lado - 2 * x0
    alto = max(1, round(ALTO_BARRA * lado))
    sep = max(1, round(SEPARACION * lado))

    total = 3 * alto + 2 * sep
    y = (lado - total) / 2

    for w in ANCHOS:
        ancho = max(1, round(ancho_util * w))
        # Rectángulos exactos, sin redondeo: la marca es recta (§6).
        d.rectangle([round(x0), round(y), round(x0) + ancho - 1, round(y) + alto - 1],
                    fill=HUESO)
        y += alto + sep
    return img


def main():
    os.makedirs(DESTINO, exist_ok=True)

    grande = dibujar(512)
    png = os.path.join(DESTINO, "icono.png")
    grande.save(png)

    # Cada tamaño se dibuja de cero en vez de reescalar el de 512: a 16 px un
    # reescalado convierte las barras en manchas grises.
    tamanos = (256, 128, 64, 48, 32, 24, 16)
    capas = [dibujar(n) for n in tamanos]
    ico = os.path.join(DESTINO, "icono.ico")
    capas[0].save(ico, format="ICO",
                  sizes=[(n, n) for n in tamanos],
                  append_images=capas[1:])

    for ruta in (png, ico):
        print(f"    {os.path.relpath(ruta, RAIZ)}  {os.path.getsize(ruta) / 1024:.1f} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
