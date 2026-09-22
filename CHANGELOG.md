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
