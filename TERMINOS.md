# Términos de uso

**Migrador de Catálogos** — versión 1.0 de estos términos, vigente desde el 14 de
septiembre de 2026.

Este documento es la copia canónica. El mismo texto aparece dentro de la
aplicación, que lo muestra la primera vez que se abre y lo deja siempre
accesible desde el pie de la ventana.

---

## 1. Qué es esta herramienta

El Migrador de Catálogos es un programa gratuito y de código abierto para
**administrar catálogos musicales**. Sirve para relevar el catálogo distribuido
de un artista, recuperar sus códigos ISRC y UPC, reunir las portadas y armar la
planilla de ingesta que pide una distribuidora nueva. Su finalidad es esa y no
otra.

La herramienta consulta APIs públicas de terceros y no aloja, no almacena y no
redistribuye contenido de ningún catálogo.

## 2. Quién puede usarla y para qué

Está pensada para titulares de derechos, sellos, distribuidoras, managers y
artistas que trabajan sobre **material propio, o sobre material que administran
con autorización del titular**.

Al usarla declarás que:

- tenés los derechos o la autorización necesaria sobre el contenido que
  procesás;
- vas a cumplir los términos de servicio de las plataformas que la herramienta
  consulta, entre ellas YouTube, Deezer, Apple y Tidal;
- sos responsable de las claves de API y de las cuentas que conectes, y de que
  su uso respete los límites y condiciones de cada proveedor.

## 3. Qué no está permitido

Esta herramienta **no avala ni habilita la piratería**. Lo que sigue queda
expresamente fuera de su finalidad y de esta licencia de uso.

- Descargar, copiar o redistribuir material sobre el que no tenés derechos.
- Usar el módulo de audio para obtener grabaciones ajenas, o para eludir medidas
  técnicas de protección.
- Revender, redistribuir o publicar el contenido obtenido sin autorización del
  titular.
- Compartir credenciales de cuentas de terceros, o usar una cuenta de streaming
  fuera de los términos del servicio que la provee.
- Eludir restricciones de las APIs que la herramienta consulta, o automatizar
  consultas por encima de los límites que esas APIs fijan.
- Presentar los resultados de la herramienta como una certificación oficial de
  titularidad o de derechos.

### Sobre el módulo de audio

El módulo de audio es **opcional, viene desactivado** y requiere que el usuario
conecte su propia cuenta paga. Existe para que un titular de catálogo recupere
sus propios másters cuando el archivo original no aparece. No reemplaza al máster
entregado por el artista o el sello, y así está dicho en la documentación y en
los reportes que la herramienta genera.

Usarlo sobre material ajeno es un uso indebido de la herramienta y una violación
de estos términos, además de, probablemente, de los términos del servicio del que
se obtenga el audio.

## 4. Tus datos

La aplicación corre entera en tu computadora.

- **No hay cuentas, ni registro, ni un servidor del autor.** La app levanta un
  servidor local en `127.0.0.1` que no queda expuesto en la red.
- **La clave de la API queda guardada en tu carpeta personal**
  (`~/.migrador-catalogos/config.json`) y no se envía a ningún lado que no sea
  Google.
- **El catálogo relevado vive en memoria** mientras la app está abierta y se
  descarta al cerrarla.
- Deezer, Apple y MusicBrainz se consultan con datos públicos del catálogo, como
  el nombre del artista, el título y la duración.
- Si conectás Tidal, el acceso es por device-code: tu contraseña nunca pasa por
  la aplicación. El token vive sólo en la sesión y se borra al cerrarla.

No se recoge telemetría de ningún tipo.

## 5. Sin garantía

El software se entrega **tal cual, sin garantía de ningún tipo**, expresa o
implícita, incluidas sin limitación las garantías de comerciabilidad, aptitud
para un propósito particular y no infracción.

Los datos provienen de fuentes públicas de terceros y pueden estar incompletos o
desactualizados. **La validación previa a la entrega es una ayuda, no un
certificado**, y no reemplaza la revisión de la distribuidora ni el criterio de
quien entrega el material. Varios campos se marcan explícitamente como estimados
o como pendientes de completar, y así hay que tratarlos.

En ningún caso el autor será responsable por daños directos, indirectos,
incidentales, especiales o consecuentes derivados del uso o de la imposibilidad
de uso de la herramienta, ni por decisiones tomadas a partir de los datos que
produce, ni por el uso que cada persona haga del material que procesa. **La
responsabilidad sobre el contenido es enteramente de quien lo usa.**

## 6. Licencia del código y marcas de terceros

El código se distribuye bajo **licencia MIT**, cuyo texto completo está en el
archivo [LICENSE](LICENSE). Estos términos describen el uso previsto de la
herramienta y no restringen los derechos que la licencia MIT otorga sobre el
código.

Las marcas, nombres y servicios de terceros mencionados pertenecen a sus
titulares. Esta herramienta **no está afiliada, patrocinada ni avalada** por
YouTube, Google, Deezer, Apple, Tidal, MusicBrainz ni por ninguna distribuidora.

La variante completa incluye **FFmpeg**, software de terceros bajo licencia
GPLv3, que se distribuye sin modificaciones y se invoca como programa separado.
Las tipografías Archivo, Geist y Geist Mono se distribuyen bajo SIL Open Font
License 1.1. Los textos de esas licencias viajan junto al programa, en la carpeta
`licencias`.

## 7. Cambios

Estos términos pueden actualizarse en versiones siguientes. La versión vigente es
la que acompaña a la copia que estás usando, y está publicada en el repositorio
junto al código. Si cambian de fondo, la aplicación los vuelve a mostrar una vez.

## 8. Contacto

Las consultas y los reportes van por los
[Issues del repositorio](https://github.com/joacogoliver-debug/catalog-migrator/issues).

Autor: [Joaquín García Oliver](https://www.linkedin.com/in/joaquingarciaoliver/).
