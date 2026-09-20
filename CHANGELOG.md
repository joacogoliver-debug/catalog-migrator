# Changelog

**Español** · [English](CHANGELOG.en.md)

Lo que cambió en cada versión publicada. Los números siguen
[SemVer](https://semver.org/lang/es/), y las descargas están en
[Releases](https://github.com/joacogoliver-debug/catalog-migrator/releases).

## Sin publicar

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

### Corregido
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

[1.0.1]: https://github.com/joacogoliver-debug/catalog-migrator/releases/tag/v1.0.1
[1.0.0]: https://github.com/joacogoliver-debug/catalog-migrator/releases/tag/v1.0.0
