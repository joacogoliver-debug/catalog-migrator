# Brief de automejora, ciclo 2

Rúbrica detallada que acompaña al `/goal` del ciclo 2. El `/goal` tiene un
tope de 4.000 caracteres y no entra todo ahí, así que lo que el goal dice en
una línea acá está desarrollado. Si este archivo está en `docs/`, Claude Code lo
lee en la Fase 1 y audita con estas preguntas. Si no está, el goal funciona
igual, con menos detalle.

El ciclo 1 (`AUDITORIA.md` y `MEJORAS.md`) fue andamiaje, tests, tipos,
paquete, empaquetado. El ciclo 2 mira el producto entero, con seis miradas
distintas, y cada una audita por separado antes de que exista un solo backlog.

## Cómo trabaja el equipo

**Formato de hallazgo** en `AUDITORIA-2.md`, uno por línea, agrupados por
mirada. Cada hallazgo lleva id (`IM01`, `DM01`, `SW01`, `UX01`, `SG01`,
`MK01`), archivo y línea cuando aplica, qué pasa, por qué le importa a quien usa
la app, impacto (alto, medio, bajo) y esfuerzo (alto, medio, bajo).

**Qué no es hallazgo.** Una decisión que ya está argumentada en el código o en
`MEJORAS.md` (por ejemplo `log=print`, el estado global del servidor, el módulo
de audio apagado por defecto, `http.server` en vez de un framework). Si una
mirada cree que la decisión está mal, lo escribe como hallazgo con el argumento
nuevo, no repite el viejo.

**Prioridad del backlog.** Primero lo que puede dañar al usuario o a su
catálogo (seguridad, datos incorrectos en la hoja de ingesta, bugs que
rompen el flujo). Después lo que más impacto tiene por menos esfuerzo. Último lo
cosmético. Un ítem grande se parte en ítems que cierran en un turno.

**Definición de hecho por ítem.** Implementado, con tests nuevos o ajustados
que fallan si se revierte el cambio, verificación completa en verde, entrada
en `CHANGELOG.md` y `CHANGELOG.en.md` bajo "Sin publicar", par es/en de todo
doc tocado, fila del backlog en "hecho" con notas de qué se verificó y qué
salió a la luz, y un commit propio.

**Verificación completa**, en este orden y sin saltear ninguno:

```bash
pytest -q --cov          # cobertura igual o mayor que al inicio del ciclo
ruff check .
ruff format --check .
pyright                  # 0 errores
python build/build.py
python build/capturas.py
git status               # limpio después del commit
```

## Mirada 1, industria musical

Quien mira es alguien que migró catálogos de verdad, del lado del sello y del
lado del artista, y sabe qué sale mal.

- ¿La app explica, en algún lado que el usuario vea, que conservar ISRC y UPC
  es lo que hace que las DSPs fusionen el release nuevo con el viejo y no se
  pierdan streams, playlists ni fecha original? ¿Advierte sobre la ventana
  entre la baja en la distribuidora vieja y el alta en la nueva?
- ¿Qué pasa con un single que después entró en un álbum (mismo ISRC, distinto
  UPC)? ¿Con un deluxe, una reedición, un remaster o una regrabación? ¿Con un
  compilado de varios artistas? ¿Con un feat donde el titular del master es
  otro? ¿Con un track que tiene dos titulares (split de master)?
- ¿Distingue Art Tracks del canal Topic de videos oficiales, lyric videos y
  visualizers? ¿Qué hace con duplicados, con un tema subido dos veces, con
  versiones live, acústicas, remixes y sped up?
- ¿La terminología es la que usa la industria, en es y en en? Fonograma vs
  obra, master vs publishing, sello vs distribuidora, titular vs autor,
  P-line y C-line, catálogo vs release.
- ¿Hay supuestos que un artista independiente o un manager no entenderían sin
  explicación? ¿Qué le pediría un manager a esta app que hoy no hace (lista
  de qué reclamarle a la distribuidora vieja, checklist de salida, línea de
  tiempo de la migración)?
- ¿Los textos toman partido por alguna distribuidora o dicen algo que no es
  cierto para todas?

## Mirada 2, distribución y metadata

Quien mira trabajó en ingesta y QC de una distribuidora y conoce los motivos
reales de rechazo.

- ISRC, formato de doce caracteres (país, registrante, año, serie), sin
  guiones al exportar, mayúsculas, uno por grabación y el mismo si es la misma
  grabación. UPC o EAN, doce o trece dígitos con dígito verificador correcto,
  uno por release. ¿La validación chequea esto de verdad o sólo el largo?
- Portada, mínimo 3000x3000, cuadrada, RGB, JPG o PNG, sin URLs, sin precio,
  sin logos de DSPs, sin texto borroso. ¿La app verifica lo que puede verificar
  (tamaño, proporción, modo de color) y lo que no, lo dice?
- Títulos y artistas según las guías de estilo que comparten las DSPs (Spotify,
  Apple Music, Amazon, YouTube Music). `feat.` en el título o en artistas,
  `Remix`, `Live`, `Acoustic Version`, mayúsculas, sin `(Official Video)`, sin
  emojis, sin "Various Artists" mal usado, artista principal vs invitado.
- Campos que las distribuidoras piden y la hoja de ingesta debería tener o
  declarar que no tiene. Sello, número de catálogo, género y subgénero, idioma
  de la letra, explicit por track, fecha de lanzamiento y fecha original,
  P-line, C-line, compositores y letristas con nombre legal, productor,
  territorios, versión, número de disco y de pista, duración.
- ¿Los nombres de archivo de audio y portada siguen alguna convención que las
  distribuidoras acepten? ¿El ZIP se puede cargar tal cual o hay que renombrar?
- Falsos positivos y falsos negativos de `validar.py`. ¿Qué marca como error
  algo que una distribuidora acepta? ¿Qué deja pasar que va a ser rechazado?
- Vocabulario de referencia para nombrar campos, DDEX ERN, sin adoptar el
  formato.

## Mirada 3, ingeniería de software

Quien mira va a mantener esto dentro de un año sin acordarse de nada.

- Bugs y casos borde. Canales con más de 500 videos, canales sin Topic,
  canales con handle y con `UC...`, links con parámetros, links de un video
  suelto, títulos con caracteres que Windows no acepta, nombres muy largos,
  catálogo vacío, red que se corta a la mitad, cuota de YouTube agotada (403
  `quotaExceeded`), clave inválida, respuesta parcial.
- Red y tiempos. Timeouts en cada llamada de `urllib`, reintentos con espera
  creciente donde tenga sentido, mensajes de error que dicen qué hacer.
- Concurrencia en `app/jobs.py` y `app/server.py`. Un job a la vez está
  decidido, pero ¿qué pasa si se cierra la ventana a mitad de un job, si se
  pide un ZIP que se está escribiendo, si dos pestañas pegan al mismo servidor?
- Rendimiento con catálogos grandes. Memoria al armar el ZIP, portadas en
  paralelo o en serie, progreso real vs estimado.
- Cobertura donde importa, no donde infla. Fixtures grabadas de la YouTube
  Data API (con `build/grabar_fixtures.py`, sin clave en el repo), tests de
  las rutas del servidor que faltan, tests de `app.js` si hay una forma barata
  de correrlos sin navegador.
- Tipos. Qué reglas de `strict` de pyright se pueden prender ya sin ruido, y
  prenderlas.
- CI y build. Acciones pinneadas, Dependabot o equivalente para pip y actions,
  caché de pip, build reproducible, `pip-audit` o similar como job.
- Deuda que encarece el próximo cambio, con el costo escrito.

## Mirada 4, UX y UI

Quien mira es diseñadora de producto y prueba la app como un manager que la
abre por primera vez, sin leer el README.

- El recorrido completo. Pegar el link, esperar, ver el catálogo, entender qué
  falta, validar, preparar, bajar el ZIP, y saber qué hacer después. ¿Dónde se
  traba alguien que no sabe qué es un ISRC?
- Estados. Vacío (antes de pegar nada), cargando (con progreso real y con la
  posibilidad de cancelar), error (con la causa y la acción siguiente), éxito
  (con el paso siguiente). ¿Todos existen y se ven bien en claro y oscuro?
- Textos. Claros, cortos, en el mismo tono en es y en en, sin jerga que no se
  explique, sin strings hardcodeados fuera de `i18n.js` e `i18n.py`, con
  plurales correctos.
- Accesibilidad. Contraste AA (4,5 a 1 en texto, 3 a 1 en componentes), foco
  visible y en orden lógico, todo operable con teclado, etiquetas en cada
  control, `aria-live` en el progreso, `prefers-reduced-motion` respetado,
  tamaños de texto que no se rompan al 150 %.
- Consistencia. Todo color, espacio y tipografía sale de `app/web/tokens/`, y
  `docs/DESIGN.md` dice lo mismo que el código.
- Tabla del catálogo con muchas filas. Ordenar, filtrar por lo que falta,
  ancho de columnas, scroll.
- Ventana. Tamaño mínimo en pywebview, comportamiento al achicar, y qué pasa
  cuando cae al navegador por falta de GTK o WebKit.
- Pantallas de configuración, términos y clave. ¿Se entienden sin el README?

## Mirada 5, ciberseguridad

Quien mira asume que el usuario tiene otras pestañas abiertas y que bajó el
binario de un link que le pasaron.

- Servidor local. Token por sesión, chequeo de `Host` (DNS rebinding), CSP,
  y además `X-Content-Type-Options`, `Referrer-Policy`, `Cache-Control:
  no-store` en `/api/`. Límite de tamaño del body. Path traversal en estáticos
  y zip slip al escribir el ZIP. Nombres de archivo saneados al bajar portadas.
- Entrada del usuario. ¿El link se restringe a dominios de YouTube antes de
  hacer cualquier request (SSRF)? ¿Qué pasa con un link a un archivo o a una IP
  interna?
- Secretos en disco. Permisos del archivo de configuración (0600 donde el
  sistema lo permita), dónde queda la clave de YouTube que carga el usuario,
  dónde quedan las credenciales de Tidal, y si conviene el llavero del sistema
  (es una decisión del dueño si suma una dependencia).
- Subprocesos. ffmpeg y yt-dlp sin `shell=True`, argumentos como lista,
  rutas de salida controladas.
- Dependencias. Versiones con CVEs conocidos, política de actualización de
  yt-dlp, `pip-audit` en el CI.
- Supply chain. Acciones de GitHub pinneadas por SHA, permisos mínimos del
  `GITHUB_TOKEN` en cada workflow, atestación de procedencia (ya existe,
  verificar que siga), SHA256 publicado, SBOM si es barato.
- `SECURITY.md`. Que el alcance siga siendo cierto después de los cambios.
- Modelo de amenazas escrito, corto, en `docs/`, para que el próximo cambio
  sepa qué defensa no romper.

## Mirada 6, marketing de software y SEO

Quien mira lanzó herramientas gratuitas para nichos y sabe que sin canal no hay
usuarios. Nada de métricas, testimonios ni comparaciones inventadas.

- README como landing. Primera línea con la promesa en lenguaje del usuario,
  captura hero arriba, "para quién es" y "para quién no", CTA a Releases visible
  sin scrollear, y la parte técnica abajo. Las dos versiones (es y en) con la
  misma estructura.
- Nombre y posicionamiento. `Migrador de Catálogos` vs `catalog-migrator` vs el
  nombre del binario, uno solo hacia afuera. Una línea de posicionamiento que
  se pueda repetir.
- Metadata del repo. Descripción, topics (`music`, `music-distribution`,
  `isrc`, `upc`, `youtube-api`, `metadata`, etc.), website, imagen de social
  preview (es una decisión del dueño, dejar el archivo listo).
- SEO del HTML. `<title>`, `<meta name="description">`, `lang` correcto por
  idioma, Open Graph si algún día hay landing pública.
- Landing pública. ¿Suma una página en GitHub Pages con la captura, la promesa
  y los botones de descarga? Si sí, dejarla armada en `docs/` sin activar Pages
  (lo activa el dueño).
- CHANGELOG y release notes como comunicación. Que cada versión cuente qué
  cambia para el usuario, no sólo para el código.
- Canales. Dónde están los artistas independientes y managers que migran
  catálogo (comunidades, foros, listas awesome, directorios de software
  libre), y un texto corto y honesto para cada uno, listo para que el dueño lo
  publique.
- Objeciones. Un FAQ con las preguntas reales (¿es seguro?, ¿por qué no está
  firmado?, ¿me roban la clave?, ¿funciona con mi distribuidora?, ¿qué no
  hace?).

## Reglas que no se negocian

- Respetar `CONTRIBUTING.md`.
- No debilitar las tres defensas del servidor local ni borrar tests.
- Sin dependencias nuevas de runtime salvo justificación escrita en el ítem.
  Sin CDN, sin tipografías externas, sin telemetría de ningún tipo.
- Nada de claves ni credenciales en el repo. `build/sin_claves.py` tiene que
  seguir pasando.
- No cambiar la versión ni publicar releases. Todo va bajo "Sin publicar".
- No dar vuelta decisiones documentadas sin escribir el argumento nuevo.
- Nada de métricas, testimonios, logos de terceros ni comparaciones que no se
  puedan verificar.
- Mantener el estilo del repo. Español rioplatense, comentarios que explican
  el porqué, par es/en de cada documento.
- Un ítem por turno, un commit por ítem, en la rama `automejora/ciclo-2`, sin
  push.

## Lo que requiere decisión del dueño

No se hace. Se deja en `MEJORAS-2.md` como "bloqueado" con la pregunta
concreta y, si se puede, el trabajo preparado para que decidir sea un clic.

- Firmar y notarizar los binarios (cuesta plata por año).
- Registrar un dominio o activar GitHub Pages.
- Cambiar el nombre público de la herramienta.
- Sumar una dependencia para el llavero del sistema.
- Subir la imagen de social preview del repo.
- Publicar en directorios, comunidades o redes.
