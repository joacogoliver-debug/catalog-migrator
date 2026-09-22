"""
Migrador de Catálogos: el núcleo, sin interfaz.

Acá vive todo lo que hace el trabajo de verdad, y nada que sepa de HTTP, de
ventanas ni de navegadores. Eso está en `app/`, que consume este paquete.

La separación no es decorativa. Este núcleo se puede usar desde un script, desde
un cuaderno o desde otra interfaz, y se prueba sin levantar un servidor; la app
de escritorio es una de las formas de manejarlo, no su única forma posible.

El flujo son cuatro pasos y están en `migrar_core`:

    1. relevar_core.relevar(url, clave)    el catálogo desde YouTube
    2. productos.group_products(tracks)    agrupado en releases
    3. portadas / audio                    lo que se pidió descargar
    4. paquete.build_zip(...)              el entregable

`contratos` describe la forma de los datos que viajan entre esos pasos, `validar`
revisa el resultado antes de entregarlo, `texto` normaliza y `i18n` traduce.

Nada de esto importa nada de `app/`, y esa flecha no se da vuelta.
"""

# La versión de la aplicación vive en `app/server.py`, que es lo que leen el
# instalador, el release y la interfaz. No se repite acá para no tener dos
# números que tarde o temprano digan cosas distintas.
