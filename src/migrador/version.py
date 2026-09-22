"""
La versión de la aplicación. Una sola, y este archivo es el único lugar.

La leen cuatro cosas que tienen que decir lo mismo, y que cuando no lo dicen
nadie se entera hasta que alguien reporta un número raro:

  - la interfaz, que la muestra en el pie de la ventana;
  - el reporte de `--diagnostico`;
  - el instalador de Windows, a través de `build/build.py`;
  - las notas del release, a través de `build/notas_release.py`.

Vive en un archivo propio y no en `app/server.py` por dos razones. Una, que
`pyproject.toml` la lee de acá para declarar la versión del paquete, y para eso
necesita un módulo que se pueda importar sin levantar un servidor. La otra, que
la versión es del producto, y el producto es este paquete: la app de escritorio
es una de las formas de manejarlo.
"""

VERSION = "1.0.2"
