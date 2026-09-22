"""
Genera el icono de la app a partir del logo de marca.

    python build/icono.py

Escribe app/web/assets/icono.png (512) y app/web/assets/icono.ico (multi-tamaño).
Está acá y no como imagen suelta para que el icono sea reproducible desde el
código, igual que las capturas.

El símbolo completo es un semitono de 74 puntos: muy bueno de 32 px para arriba,
una mancha gris por debajo. Un icono de aplicación se ve casi siempre a 16, 24 y
32, así que acá se dibuja la **variante compacta**: menos puntos y más grandes,
con el mismo gesto de la marca, denso a la izquierda y disperso hacia la derecha.

Los colores son los de `symbol-on-teal`, que es lo que el manual de marca pide
para el icono de aplicación: cuadrado teal, origen en hueso, migrado en grafito.
"""

import os
import sys

from PIL import Image, ImageDraw

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESTINO = os.path.join(RAIZ, "app", "web", "assets")

TEAL = (56, 127, 126, 255)  # #387F7E
HUESO = (245, 242, 237, 255)  # #F5F2ED
GRAFITO = (20, 20, 20, 255)  # #141414

# Mismos datos que app/web/assets/logo-compacto.svg, en un viewBox de 64.
ORIGEN = [(15, 17, 6.4), (15, 32, 6.4), (15, 47, 6.4), (29, 17, 5.2), (29, 32, 5.2), (29, 47, 5.2)]
MIGRADO = [(42, 24, 3.8), (42, 40, 3.8), (53, 32, 2.6)]

# El símbolo ocupa el 80% del cuadrado, como pide el manual de marca.
ESCALA_SIMBOLO = 0.80
# Se dibuja ocho veces más grande y se reduce: es la forma barata de tener
# circunferencias suaves sin depender de un rasterizador de SVG.
SUPER = 8


def dibujar(lado):
    grande = lado * SUPER
    img = Image.new("RGBA", (grande, grande), TEAL)
    d = ImageDraw.Draw(img)

    # El logo es más ancho que alto, así que se centra midiendo lo que ocupa de
    # verdad y no el viewBox entero.
    todos = ORIGEN + MIGRADO
    x0 = min(cx - r for cx, _, r in todos)
    x1 = max(cx + r for cx, _, r in todos)
    y0 = min(cy - r for _, cy, r in todos)
    y1 = max(cy + r for _, cy, r in todos)

    k = grande * ESCALA_SIMBOLO / max(x1 - x0, y1 - y0)
    dx = (grande - (x1 - x0) * k) / 2 - x0 * k
    dy = (grande - (y1 - y0) * k) / 2 - y0 * k

    for puntos, color in ((ORIGEN, HUESO), (MIGRADO, GRAFITO)):
        for cx, cy, r in puntos:
            px, py, pr = cx * k + dx, cy * k + dy, r * k
            d.ellipse([px - pr, py - pr, px + pr, py + pr], fill=color)

    return img.resize((lado, lado), Image.LANCZOS)


def main():
    os.makedirs(DESTINO, exist_ok=True)

    png = os.path.join(DESTINO, "icono.png")
    dibujar(512).save(png)

    # Cada tamaño se dibuja de cero en vez de reescalar el de 512: a 16 px un
    # reescalado convierte los puntos en manchas.
    tamanos = (256, 128, 64, 48, 32, 24, 16)
    capas = [dibujar(n) for n in tamanos]
    ico = os.path.join(DESTINO, "icono.ico")
    capas[0].save(ico, format="ICO", sizes=[(n, n) for n in tamanos], append_images=capas[1:])

    for ruta in (png, ico):
        print(f"    {os.path.relpath(ruta, RAIZ)}  {os.path.getsize(ruta) / 1024:.1f} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
