# Backlog de mejoras, ciclo 2

Sale de [AUDITORIA-2.md](AUDITORIA-2.md). Un ítem por turno, en orden de
prioridad, y cada uno se cierra con su verificación completa antes del commit.
Un ítem grande está partido en ítems que cierran en uno.

Estados posibles, `pendiente`, `en curso`, `hecho`, `bloqueado`, `descartado`.

La prioridad sigue la regla del ciclo. Primero lo que puede dañar al usuario o a
su catálogo, que acá es la seguridad, el entregable que no se puede bajar y los
datos equivocados en la hoja de ingesta. Después lo que más rinde por esfuerzo.
Último lo cosmético.

Línea de base del ciclo: 391 tests, cobertura 59,82 % sobre un umbral de 58.

| id | prioridad | ítem | estado | notas |
|---|---|---|---|---|
| N01 | 1 | `build/capturas.py` sale en cero, y las capturas del README se regeneran en castellano y en inglés | hecho | SW22, SW23, UX24. La causa era un hilo del servidor que imprimía el corte de conexión de Chrome mientras el intérprete se cerraba. Se arregló en los dos lados: `server.Servidor` calla `ConnectionError` y `TimeoutError` en `handle_error` (cualquier otra excepción sigue saliendo entera, y hay test de las dos cosas), y `capturas.py` espera a los hilos de cada pedido y cierra su conexión de sondeo. Tres corridas seguidas en castellano y una en inglés, todas en cero y con stderr vacío. **Salieron dos cosas más.** Los textos de ejemplo escritos a mano se habían desviado de la app (un «no esta» sin tilde, y la falta de UPC mostrada como error cuando `validar.py` la emite como aviso); ahora salen de `T()` y un test compara sus niveles con los que emite la validación. Y el script seguía creando `build/migrador/`, la carpeta que el ciclo 1 había sacado de PyInstaller por ser un paquete de espacio de nombres; ahora usa un temporal del sistema. Las catorce capturas (siete por idioma) quedaron regeneradas con la versión real. |
| N02 | 2 | Bajar el ZIP desde la interfaz: ticket de un solo uso pedido con el token, descargas habilitadas en pywebview, y un test que baje el ZIP como lo hace el botón | hecho | UX01, SG07. `POST /api/descargar/<id>` (con el token, como todo `/api/`) devuelve `/descargar/<ticket>`, un ticket de `secrets.token_urlsafe(24)` que vale una vez y un minuto; la ruta que lo canjea sigue detrás del control de Host. Así la regla «toda ruta `/api/` exige la cabecera» sigue sin excepciones. Ocho tests nuevos bajan el ZIP **como lo hace el navegador**, sin cabecera: el ticket sirve una vez, uno inventado o vencido da 404, pedirlo exige el token, un Host ajeno da 403 sin gastarlo, y la interfaz ya no enlaza la API. Verificado además en un navegador real contra el servidor de verdad con un catálogo inventado: la ruta vieja sin token da **403** (el bug que veía el usuario), el ticket baja los 837.653 bytes enteros con `Content-Disposition: attachment`, y el reuso da 404. No se hizo clic en el botón para no bajar un archivo a la máquina; se reprodujo lo que hace, con `fetch`. **Salió a la luz** que además pywebview trae `ALLOW_DOWNLOADS` apagado, así que en la ventana nativa el botón tampoco habría hecho nada; ahora se prende al abrir (`launcher.permitir_descargas`, con test). Lo que no se pudo verificar acá es el diálogo de guardado de WebView2 con un clic humano. Nota para la edición de MOJO: el motor se porta a mano entre las dos, y es probable que tenga el mismo bug. |
| N03 | 3 | Contenido hostil que entra de afuera: yt-dlp sin config ajena, fórmulas neutralizadas en planillas y hoja, portadas sólo desde el CDN de Apple y con tope de tamaño | hecho | SG01, SG02, SG04. yt-dlp corre con `--ignore-config`, con `--` antes de la URL y con `cwd` en la carpeta del trabajo; cuando no está como módulo se busca con `_buscar_en_path`, que sólo mira carpetas absolutas del PATH, porque `shutil.which` en Windows antepone la carpeta de trabajo. Las fórmulas: en el xlsx toda celda de texto queda como texto (`_celda`); en el CSV se antepone un apóstrofo sólo cuando `texto.parece_formula` (empieza con `= + - @` y lleva un paréntesis, una barra o un signo de exclamación), para no tocar discos reales como «+», «=», «÷» o «-Intro-», y la validación avisa con `texto_como_formula` cada vez que la hoja cambió un dato. Las portadas sólo se piden por HTTPS a `*.mzstatic.com`, con tope de 25 MB. 35 tests nuevos en `tests/test_entrada_hostil.py`. **Salió a la luz un bug funcional**: la variante completa empaqueta el módulo `yt_dlp` y la detección decía «hay yt-dlp», pero la descarga llamaba a un programa `yt-dlp` del PATH, así que en una máquina sin yt-dlp instalado aparte el audio de referencia fallaba siempre. Ahora se usa el mismo módulo que se detectó (`sys.executable -m yt_dlp`, o el propio ejecutable con `--yt-dlp`, que atiende `launcher.correr_ytdlp_empaquetado`). **No se pudo verificar acá** el camino empaquetado de punta a punta: el build local es la variante esencial, sin audio; está cubierto por test unitario y lo va a ejercer el CI al compilar la completa. |
| N04 | 4 | Nombres adentro del ZIP: UPC sólo dígitos, carpetas únicas aunque dos productos se llamen igual o tengan títulos no latinos, largo total acotado, y ninguna entrada fuera de la raíz | hecho | SG03, SW02, SW05. Del UPC entran sólo los dígitos a la carpeta. `productos.asignar_carpetas` hace únicas las carpetas, comparando sin mayúsculas porque Windows no las distingue, con `(2)`, `(3)`. `paquete.LARGO_MAX_RUTA` (200) pone el presupuesto de la ruta interna: la raíz lleva el artista recortado a 40 y lo que sobra se descuenta del título del tema, sin tocar nunca el número de track ni la marca de lossy. `paquete.entrada_zip` es la segunda puerta, que se niega a escribir una parte con barra o `..`. 14 tests en `tests/test_nombres_zip.py`; el peor caso (artista, disco y tema de 150 caracteres, UPC de 13 y audio lossy) queda en 200 o menos, cuando antes pasaba los 290. **Decisión que se respetó**: los nombres de archivo siguen en ASCII, como ya hacía `nombre_seguro`, así que un título japonés sigue saliendo como «Sin titulo», pero ya no se pisa con otro y el título real va en la planilla de adentro. **Queda para N10** usar este mismo `nombre_audio` en la hoja de ingesta, que hoy nombra el archivo temporal. |
| N05 | 5 | ISRC repetido: error dentro de un producto; entre productos, aviso si es la misma grabación y error de match si no lo es | hecho | IM01, DM04. `validar._duplicados` separa tres casos. Repetido adentro de un producto sigue siendo `isrc_duplicado`, error. Entre productos, si título (normalizado) y duración (±3 s, `TOLERANCIA_MISMA_GRABACION`) coinciden, es `isrc_compartido`, un **aviso** que dice que se conserve el código; si no coinciden es `isrc_match_dudoso`, error, que es además la red para los vivos y remixes que se quedaron con el ISRC de estudio (lo que arregla de raíz N06). Los dos tests que fijaban la regla vieja no se borraron: se adaptaron a lo que ahora es correcto, y se sumaron seis, entre ellos el caso real single y álbum, que antes daba `apto False` y ahora da apto con un aviso. README en los dos idiomas con la regla nueva. **Salió a la luz** un detalle del armado del mensaje: si un ISRC aparecía primero en otro producto y después dos veces en éste, el repetido interno citaba la aparición del otro producto; ahora cada producto recuerda la suya, con test. |
| N06 | 6 | Versiones: en vivo, remix, remaster y feat no se borran al buscar en Deezer ni en iTunes; confianza media exige duración parecida; un artista vacío no cuenta como coincidencia | hecho | IM03, DM01, DM07. `_clean_title` limpia sólo lo que es de YouTube y sólo cuando es todo el paréntesis. `texto.marcas_version` lee la versión (vivo, remix, remaster, acústico, edit, sped up, demo, extendida, karaoke, instrumental) sólo en lo decorado, así que «Live Forever» no es un vivo; `texto.misma_version` exige además los mismos números. Un candidato de otra versión se descarta en Deezer, en MusicBrainz y en iTunes. La confianza media exige la duración cuando se conoce, y un artista vacío ya no cuenta. 38 tests en `tests/test_versiones.py`; dos casos de `test_strip_ruido` fijaban el comportamiento viejo y se adaptaron. **Contrastado con datos reales**: sobre 40 Art Tracks de Daft Punk, la lógica nueva no pierde ningún ISRC que la vieja encontraba y gana cuatro (la vieja borraba los corchetes `[feat. …]` y el título dejaba de parecerse). **Salió a la luz una debilidad previa**: «Tema (Parte 1)» contra «Tema (Parte 2)» coincidía en un 93 % y salía con confianza alta, igual que «Vol. 1» y «Vol. 2» en las portadas; de ahí la regla de los números. Es conservadora a propósito: «(Remastered)» contra «(Remastered 2011)» queda en blanco. |
| N07 | 7 | URLs de YouTube: handle con caracteres codificados, `UC…` suelto, `/user/`, `watch?v=` y `youtu.be` | hecho | SW01, SW08. `relevar_core.pedido_de_canal` decodifica el link antes de leerlo y reconoce `/channel/UC…`, el `UC…` suelto, `/user/` (`forUsername`), `@handle` y `/c/` (probado como handle, porque la API no tiene consulta para las URL personalizadas viejas). Un link a un tema (`watch?v=`, `youtu.be`, `/shorts/`, YouTube Music) se resuelve con `videos.list`, una unidad de cuota, al canal que lo subió. Lo que no se puede leer (una playlist, un link de Spotify, texto suelto) sigue siendo error de campo, con un mensaje que ahora dice qué se puede pegar; y un canal que no aparece nombra lo que se buscó ya decodificado. 27 tests en `tests/test_urls_youtube.py`. La ayuda del campo y el README dicen que también sirve el link de un tema; la captura de la entrada se regeneró por eso. **Lo que no se hizo**: las playlists siguen afuera a propósito, porque una playlist puede mezclar artistas y el relevamiento es por canal. |
| N08 | 8 | Fecha de lanzamiento real, desde `Released on:`. Nunca la fecha de subida ni un 1 de enero inventado | pendiente | IM04, DM03 |
| N09 | 9 | UPC verificado contra el álbum de Deezer; si no coincide, en blanco y con aviso | pendiente | IM02, DM05 |
| N10 | 10 | La hoja de ingesta y las planillas nombran los archivos que el ZIP trae de verdad | pendiente | DM02 |
| N11 | 11 | Agrupación por álbum y fecha de lanzamiento, no por año ℗, separando distribuidoras y avisando cuando el mismo release está en vivo en dos | pendiente | IM05, IM06 |
| N12 | 12 | Disco y número de track reales cuando el álbum de Deezer está verificado; si no, marcados como estimados. `Territories` a completar | pendiente | IM09, IM10, DM08, parte de DM09 |
| N13 | 13 | Artistas por track y créditos (compositor, letrista, productor) desde la descripción | pendiente | IM07, IM18, parte de DM09 y DM17 |
| N14 | 14 | La línea ℗ va entera a la P Line, y el sello deja de ser un pedazo de ella | pendiente | IM08, DM16 |
| N15 | 15 | La hoja de ingesta también en xlsx, con los códigos como texto, y el CSV avisado | pendiente | DM06, parte de DM17 |
| N16 | 16 | Validación: ruido de título sin falsos positivos, más patrones, códigos normalizados, modo de color de la portada, lo que no se puede validar dicho, confianza del match a la vista, y «sin errores de formato» en vez de «sin problemas» | pendiente | IM14, IM17, DM10 a DM15 |
| N17 | 17 | Servidor: cabeceras de aislamiento, `Sec-Fetch-Site`, cuerpo leído sin parsear hasta pasar Host y token, `chunked` rechazado, sin 500 con texto de excepción | pendiente | SG05, SG06, SG08, SG09 |
| N18 | 18 | Secretos: permisos desde la creación, clave en cabecera y no en la URL, un test que busque la clave en toda salida, y control de claves sobre la historia | pendiente | SG10, SG11, SG12 |
| N19 | 19 | CI: permisos mínimos por job, acciones fijadas por SHA, Dependabot, `pip-audit`, timeouts, caché, `concurrency`, versiones fijas, la clave fuera del entorno de pytest y el piso de yt-dlp | pendiente | SG13, SG14, SG15, SW18, SW19 |
| N20 | 20 | Deezer y la paginación: avance real, cancelación que responde, reintentos sólo donde sirven, «Deezer no respondió» distinto de «no hubo coincidencias», y la barra del armado por tramos | pendiente | SW03, SW07, SW12 |
| N21 | 21 | Concurrencia y temporales: un trabajo por vez bajo el mismo lock, lista de ids vacía es error, catálogo identificado, carpeta de audio que se borra al cancelar | pendiente | SW04, SW10, SW11 |
| N22 | 22 | Textos fuera de los catálogos y plurales | pendiente | SW14, UX16, UX17 |
| N23 | 23 | Respuestas grabadas de la YouTube Data API y tests de `relevar()` punta a punta y de las rutas del servidor que faltan; el umbral sube | pendiente | SW15 |
| N24 | 24 | Tests de `app.js` con `node --test`, sin navegador | pendiente | SW16 |
| N25 | 25 | pyright: las reglas de `strict` que dan cero, prendidas, y el contrato de `distribs` corregido | pendiente | SW17 |
| N26 | 26 | Recorrido: el link no se borra, el error viejo se va, cancelar no es error, el pie se limpia, la clave se ve y «Verificando» se mueve | pendiente | UX02, UX09, UX10, UX11, UX21 |
| N27 | 27 | Accesibilidad: bordes de control a 3 a 1, botón principal visible en claro, foco que no se pierde, errores anunciados, ES y EN con nombre | pendiente | UX03 a UX07 |
| N28 | 28 | Tabla: selección oculta avisada, cero distribuidoras es cero, filtro «con faltantes», cabecera y barra de acción fijas | pendiente | UX12 a UX15 |
| N29 | 29 | La guía de migración que la app no da: por qué conservar los códigos, cuándo dar de baja, qué pedirle a la distribuidora actual, artista ausente en Deezer, qué hacer con el ZIP, ISRC y UPC definidos, Tidal que no es el máster | pendiente | IM12, IM13, IM16, UX08, UX18, UX19, UX20 |
| N30 | 30 | Seguridad escrita: SECURITY.md con las tres defensas, el docstring del servidor, un modelo de amenazas en los dos idiomas, y la atestación dicha como es | pendiente | SG16, SG17, SG18 |
| N31 | 31 | README como landing: la promesa, para quién es y para quién no, descarga directa, sólo afirmaciones verificables, preguntas frecuentes, instalación de Mac y Linux al día | pendiente | MK01 a MK08, MK10, MK15, MK16 |
| N32 | 32 | CHANGELOG y notas del release que empiezan por quien usa la app | pendiente | MK11 |
| N33 | 33 | Deuda: campos de diagnóstico muertos, comentarios del repo viejo, metadata de `pyproject.toml`, DESIGN.md y tokens diciendo lo mismo | pendiente | SW09 (`units`), SW20, SW21, MK18, UX23 |
| N34 | 34 | Cerrar la app de verdad: latido en el modo navegador y confirmación al cerrar con un trabajo en curso | pendiente | SW06, UX22 |
| N35 | 35 | Tidal: el índice por ISRC guarda todas las apariciones y elige la del producto | pendiente | IM11 |
| N36 | 36 | Material de lanzamiento preparado: imagen para redes, landing en `docs/`, textos para cada canal, descripción y topics del repo | pendiente | MK12, MK13, MK19. Se prepara todo y queda `bloqueado`: publicar es del dueño |
| N37 | — | Un solo nombre hacia afuera, también en los binarios | bloqueado | MK09. ¿Los archivos de los releases siguen como `Migrador-de-Catalogos-…` o pasan a un nombre por idioma? Renombrarlos rompe los enlaces que ya circulan. La parte que no rompe nada, la grafía en la interfaz, entra en N22 |
| N38 | — | Dónde hacer una pregunta | bloqueado | MK14. ¿Se activa Discussions con una categoría de preguntas, o se suma una tercera plantilla de issue «Pregunta»? |
| N39 | — | Firmar y notarizar los binarios | bloqueado | Cuesta plata por año. ¿Se paga un certificado de Windows y la cuenta de desarrollador de Apple? Mientras tanto la confianza sigue apoyada en el código público, el build en Actions, el SHA256 y la atestación |

## Qué queda afuera y por qué

**IM15, el tipo de release por duración.** Algunas tiendas usan minutos además
de cantidad de tracks, y el dato ya está. No entra porque no se pudo verificar
desde acá la regla vigente de cada tienda, y cambiar una heurística documentada
por otra que tampoco está verificada es cambiar una suposición por otra. La
heurística actual está declarada en el README y en el reporte, que es lo que
importa.

**SW09, la caché de sesión para no gastar cuota dos veces.** Es real que un
corte a mitad obliga a repetir, y con la clave compartida eso duele. Pero un
relevamiento típico cuesta menos de diez unidades de las diez mil del día, y
sólo la búsqueda del Topic cuesta cien. La caché agrega estado en memoria que
hay que invalidar bien, sobre un servidor que ya tiene su estado argumentado
como global. Lo barato de SW09, que `units` miente, entra en N33.

**SW13, las portadas a disco en vez de en memoria.** Trescientas portadas son
cientos de MB de pico, lo cual es real, pero un catálogo de trescientos releases
es la excepción, y el armado con audio ya exige 3 GB libres en disco. Queda
anotado para el día que alguien lo sufra.

**El lock de dependencias con hashes (parte de SG13).** El build corre en cuatro
sistemas con ruedas distintas por plataforma, y un lock con hashes para esa
matriz es un archivo grande que hay que regenerar en cada sistema. Dependabot y
`pip-audit`, que entran en N19, detectan lo mismo que importa (una versión con
un CVE conocido) sin ese costo.

**La atestación obligatoria y el SBOM (parte de SG16).** Que la atestación
tolere fallar es una decisión escrita en `build.yml`: es un extra y no el
entregable, y un cambio de GitHub en ese servicio no tiene que bloquear una
publicación. No se da vuelta. Lo que sí está mal es que SECURITY.md y el README
la presenten como garantizada, y eso se corrige en N30. El SBOM pide una acción
de terceros más en el paso de publicar, que es el que tiene permiso de
escritura, y no se justifica todavía.

**Las columnas de DM17 que no tienen fuente.** Número de catálogo, subgénero y
los años de P y C por separado no salen de ningún lado público. Sumarlas vacías
agranda la hoja sin sumar información; lo que sí se hace es declararlas en el
LEEME como campos que la distribuidora puede pedir (N15).
