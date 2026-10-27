"""
Con qué certificados se verifican las conexiones HTTPS.

Python no usa el llavero de macOS: busca los certificados raíz en la carpeta que
quedó grabada en el OpenSSL con el que se compiló. En el .app esa carpeta es la
de la máquina del CI y en la del usuario no existe, así que toda conexión HTTPS
fallaba con `CERTIFICATE_VERIFY_FAILED` y la app no podía relevar nada. Lo mismo
le pasa a quien corre el código con el Python de python.org en una Mac y nunca
ejecutó el "Install Certificates.command".

La salida es usar el paquete de certificados de `certifi`, que viaja adentro del
binario. Pero sólo cuando el sistema no tiene ninguno: si los tiene, pueden
incluir la raíz de una red corporativa que inspecciona el tráfico, y cambiarlos
por los de certifi rompería la conexión justo ahí. En Windows esto suma y no
reemplaza, porque Python lee además el almacén del sistema.
"""

import os
import ssl


def preparar():
    """Apunta OpenSSL a los certificados de certifi si el sistema no tiene."""
    if os.environ.get("SSL_CERT_FILE") or os.environ.get("SSL_CERT_DIR"):
        return  # lo eligió quien lanzó la app
    rutas = ssl.get_default_verify_paths()
    if rutas.cafile or rutas.capath:
        return
    try:
        import certifi
    except ImportError:
        return
    os.environ["SSL_CERT_FILE"] = certifi.where()
