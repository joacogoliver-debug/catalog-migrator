# Changelog

**Español** · [English](CHANGELOG.en.md)

Lo que cambió en cada versión publicada. Los números siguen
[SemVer](https://semver.org/lang/es/), y las descargas están en
[Releases](https://github.com/joacogoliver-debug/catalog-migrator/releases).

## [Sin publicar]

### Cambiado
- **La suite de tests corre con pytest.** Los diez archivos eran scripts con un
  `main()` y una lista de strings, y `pytest -q` no colectaba ninguno: salía con
  éxito sin haber corrido nada. Ahora son 267 tests de verdad, con
  `tests/conftest.py`, fixtures compartidas del catálogo de ejemplo y el idioma
  fijado en un solo lugar.
- **Una sola lista de tests.** Estaba escrita tres veces, en `build/build.py`,
  en el workflow del CI y en el README, así que un test nuevo pedía acordarse de
  tres lugares y uno olvidado en `build.py` no bloqueaba un release. Ahora sale
  de `testpaths` en `pyproject.toml`.
- El CI corre un solo paso de tests en vez de once, y `build/build.py` corre la
  misma suite antes de empaquetar. Si pytest no colecta nada, el build aborta.

### Agregado
- El CI corre los tests en Python 3.13 y 3.14. Se compila con 3.13 y se escribe
  con 3.14, y esa diferencia no estaba cubierta por nada.
- `BLE` en ruff: cada `except Exception` tiene que justificarse. Había treinta y
  cuatro y sólo trece tenían una nota, que además no silenciaba nada porque la
  regla estaba apagada.
- **macOS tiene un `.app` y Linux un `.deb`.** Hasta ahora los dos se
  publicaban como un ejecutable suelto, que en macOS son cuatro comandos de
  Terminal y en Linux no aparece en ningún menú. El `.app` se arrastra a
  Aplicaciones y queda en el Launchpad; el `.deb` se instala con `apt`, queda en
  el menú con su icono y se desinstala como cualquier paquete. Los dos siguen sin
  firmar, que es otra cosa y cuesta plata.
- **El motor es un paquete, `migrador`, y vive en `src/`.** Los diez módulos
  estaban sueltos en la raíz y cada archivo se armaba el `sys.path` a mano. Ahora
  `app/` consume el paquete y esa flecha va en un solo sentido, así que el núcleo
  se prueba sin levantar un servidor. Los lanzadores pasaron a `scripts/`, y
  `pyproject.toml` declara los extras `[app]`, `[audio]` y `[dev]`, que un test
  verifica contra los `requirements-*.txt` para que no se separen.
- **Las notas de cada release salen del CHANGELOG.** Antes eran 125 líneas
  escritas a mano adentro del workflow, en dos idiomas, y no decían qué había
  cambiado: el CHANGELOG existía y nadie lo leía al publicar. Ahora se arman con
  `build/notas_release.py`, que además aborta si el CHANGELOG no tiene una
  entrada para la versión que se está tagueando.
- **Tests de contrato contra respuestas reales de Deezer y de iTunes.** Los
  dobles escritos a mano prueban que el código es consistente consigo mismo, no
  que entienda lo que las APIs devuelven. Ahora hay siete respuestas grabadas en
  `tests/fixtures/`, con su URL y su fecha, y los tests corren el cliente de
  verdad contra ellas. Siguen sin tocar la red.
- `texto.py`, con una sola implementación de la normalización de texto y de los
  nombres de archivo seguros. Estaban escritas seis veces en cinco módulos, casi
  iguales pero no del todo.
- `CONTRIBUTING.md` y plantillas de issue, en los dos idiomas. Las seis reglas
  que no se negocian (las tres defensas, sin frameworks, no inventar metadata, la
  clave fuera del repositorio, todo el texto traducido y un README honesto)
  estaban en la cabeza de quien mantiene y ahora están escritas.
- **El contrato entre módulos está escrito, en `contratos.py`.** Lo que
  devuelve el relevamiento y lo que consumen los productos, la validación, las
  portadas y el empaquetado dejó de vivir en los docstrings. Son TypedDict, así
  que en tiempo de ejecución no existen y el programa corre igual, pero pyright
  los verifica. El test del contrato del orquestador ya no repite las claves a
  mano: las lee de ahí.
- **El linter, el formateador y el verificador de tipos corren solos.**
  `pre-commit` pasa ruff y un control de claves de API antes de cada commit, y el
  CI suma `ruff format --check` y `pyright`, que hoy corre en cero errores. El
  control de claves es un solo script, `build/sin_claves.py`, compartido entre el
  gancho y el CI.
- **La CSP tiene test.** De las tres defensas del servidor local era la única
  sin uno, y es un string suelto adentro de un método, así que aflojarla no
  rompía nada. Ahora se verifica que esté entera, que ninguna directiva abra un
  origen externo, que los scripts inline sigan prohibidos, y que la propia
  página no incumpla su política.
- **Cobertura con umbral.** `pytest -q --cov` mide la app y falla si baja del
  umbral de `pyproject.toml`. El umbral está puesto donde estamos, no donde nos
  gustaría.
- `requirements-dev.txt` con las herramientas de quien desarrolla.
- `docs/AUDITORIA.md` y `docs/MEJORAS.md`, el diagnóstico del repositorio y el
  backlog que sale de él.

### Corregido
- El control de versión de `build/build.py` pedía Python 3.9 mientras el
  proyecto declara 3.13. Compilar con 3.9 pasaba el control y fallaba después,
  adentro del paquete. Ahora el piso se lee de `requires-python`, que es donde
  estaba bien escrito.
- El parseo de los errores de la YouTube Data API atrapaba cualquier excepción.
  Ahora nombra las cuatro que puede dar navegar un JSON, así que un error propio
  ahí deja de quedar tapado.
- La cobertura enumeraba los módulos por nombre, así que mover uno lo sacaba de
  la medición en silencio y el porcentaje subía sin que nadie hubiera escrito un
  test. Ahora se mide por carpeta.
- **Un artista escrito con tilde no encontraba en Tidal al mismo escrito sin
  ella.** La normalización que usaba el módulo de audio no sacaba los acentos, a
  diferencia de las otras dos, y sin coincidencia exacta la búsqueda caía al
  primer resultado que devolviera Tidal, que puede ser cualquiera.
- El nombre de la carpeta de un producto podía terminar en punto cuando el
  título era largo y el recorte caía justo ahí. Windows no admite ese nombre, y
  el error aparecía recién al descomprimir el ZIP, en la máquina de otro.
- El README tenía una imagen sin línea en blanco delante, que partía en dos la
  lista de «Cómo está hecha». La versión en inglés estaba bien.
- El docstring de `build/capturas.py` decía que las capturas del README salen en
  tema claro, y el código las genera en oscuro desde que ése es el tema con el que
  la app se abre.
- Al relevar un canal que no es Topic, la app cambia al Topic del artista. Si
  YouTube devolvía la lista de subidas pero no el título del canal, el cambio se
  hacía igual y el catálogo entero quedaba a nombre de nadie. Ahora se exigen los
  dos.
- `relevar_core.py` usaba `urllib.error` sin haberlo importado nunca. Andaba de
  rebote, porque `urllib.request` lo importa por dentro, pero cualquier cambio en
  ese detalle de la biblioteca estándar habría roto el manejo de errores de
  YouTube sin aviso. Lo encontró pyright.

## [1.0.2] — 2026-09-21

### Agregado
- **La app está en castellano y en inglés, entera**: la interfaz, el log del
  relevamiento, los mensajes de error y también lo que se descarga (los nombres
  de los archivos del ZIP, los encabezados de la planilla y el informe de
  validación). El instalador de Windows pregunta el idioma en la primera
  pantalla, y desde la app se puede cambiar cuando sea desde el selector del
  encabezado.
- `SECURITY.md` con qué entra y qué no, y por dónde reportar en privado.
- El linter (`ruff`) corre en el CI antes de los tests, con la configuración en
  `pyproject.toml`.
- El CI **corre el ejecutable** que va a publicar, en las cuatro plataformas, y
  falla el build si no llega a servir la app. Antes se publicaban binarios que
  nadie había ejecutado.

### Corregido
- **Faltaba el ejecutable para las Mac Intel.** Se compilaba uno solo, en un
  runner Apple Silicon, y se lo publicaba llamándolo «macos»: en una Mac Intel
  no arranca. Ahora se publican los dos, `macos-apple-silicon` y `macos-intel`,
  y hay una [guía de instalación para macOS](docs/INSTALAR-MAC.md).
- El navegador en modo aplicación no se buscaba en `~/Applications`, donde en
  Mac es igual de común tenerlo instalado.
- La barra de progreso de las portadas se congelaba en 5 % con la app en inglés:
  se deducía del texto del log con una expresión regular en castellano. Ahora el
  avance viaja por un callback y no se parsea nada.
- La banda de título del paso 3 se salía 24 px de su tarjeta por cada lado.
- Los números se formateaban siempre con la convención castellana, así que en
  inglés se leía «7.000 plays» donde va «7,000».
- Una clave de traducción estaba definida dos veces: Python se queda con la
  última en silencio, y la app en inglés decía «products» donde el resto de la
  interfaz dice «releases».

### Cambiado
- Los tests viven en `tests/`, y las decisiones de producto y de diseño en
  `docs/`.
- Se fue del repositorio el material de trabajo de la auditoría de interfaz:
  era el proceso, no el producto.

## [1.0.1] — 2026-09-15

### Cambiado
- Rediseño completo de la interfaz: se dejó de leer como un documento apilado y
  pasó a ser una aplicación con sus cuatro pasos a la vista, sobre la paleta de
  la marca (grafito, hueso y la rampa teal).
- El logotipo, en la cabecera y en el icono del ejecutable.
- Se borró la clasificación de distribuidoras: era una lista que envejecía sola
  y no aportaba a la migración.

### Corregido
- El empaquetado seguía pidiendo las tipografías viejas y fallaba al compilar.
- El sello numérico de DistroKid se estaba tomando como año de lanzamiento.

## [1.0.0] — 2026-09-14

Primera versión pública.

- Relevamiento del catálogo de un artista desde su canal de YouTube (Topic,
  canal oficial o `@handle`).
- **ISRC** y **UPC** por Deezer, sin clave y sin costo.
- Portadas por la iTunes Search API, y se informa la resolución que Apple
  devolvió y no la que se pidió.
- **Validación pre-entrega** que separa lo que la distribuidora rechaza de lo
  que sólo conviene mirar.
- **Hoja de ingesta** en CSV con las columnas estándar, y lo que no sale de
  fuentes públicas marcado `<<COMPLETAR>>`.
- ZIP con una carpeta por producto.
- Módulo de audio **opcional y apagado por defecto**: FLAC lossless con la
  cuenta paga propia de Tidal, y referencia lossy de YouTube, cada archivo
  etiquetado por lo que realmente es.
- Ejecutables para Windows, macOS y Linux compilados en GitHub Actions, con
  SHA256 y atestación de procedencia.

[1.0.2]: https://github.com/joacogoliver-debug/catalog-migrator/releases/tag/v1.0.2
[1.0.1]: https://github.com/joacogoliver-debug/catalog-migrator/releases/tag/v1.0.1
[1.0.0]: https://github.com/joacogoliver-debug/catalog-migrator/releases/tag/v1.0.0
