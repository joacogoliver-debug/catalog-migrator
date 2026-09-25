# Auditoría del repositorio, ciclo 2

Estado del código en el commit `1e18556` (v1.1.0), rama `main`, árbol limpio.
Fecha de la revisión, 25 de septiembre de 2026.

El ciclo 1 ([AUDITORIA.md](AUDITORIA.md) y [MEJORAS.md](MEJORAS.md)) fue
andamiaje: tests, tipos, paquete, empaquetado. Éste mira el producto entero con
seis miradas distintas, cada una auditando por separado antes de que existiera un
solo backlog, con la rúbrica de [BRIEF-AUTOMEJORA.md](BRIEF-AUTOMEJORA.md). Es un
diagnóstico: no se tocó una línea de código para escribirlo. El plan sale de acá y
vive en [MEJORAS-2.md](MEJORAS-2.md).

No se repiten los hallazgos del ciclo 1 ni se discuten las decisiones que ya
están argumentadas (`log=print`, el estado global del servidor, el audio apagado
por defecto, `http.server`, no generar DDEX, un trabajo a la vez). Donde una
mirada cree que una decisión está mal, el hallazgo trae el argumento nuevo.

## Qué se verificó de verdad

| Comprobación | Resultado |
|---|---|
| `pytest -q --cov` | 391 tests en verde, cobertura **59,82 %** sobre un umbral de 58 |
| `ruff check .` y `ruff format --check .` | en verde |
| `pyright` | 0 errores, modo `basic` |
| `python build/build.py` | en verde, binario de 54,1 MB |
| `python build/capturas.py` | genera las siete capturas y **sale con `Fatal Python error`** al cerrar |
| Capturas regeneradas contra las commiteadas | cambian cinco, y la única diferencia es el pie: las publicadas dicen `v1.0.1` y la versión es 1.1.0 |
| Descripciones reales de YouTube | cincuenta Art Tracks del canal Topic de Daft Punk (511 videos), leídos con la API para comprobar qué trae de verdad una descripción auto-generada. No quedaron en el repositorio |
| `pip-audit` | no está instalado en la máquina, así que no hubo escaneo automático de CVE |

Lo que las descripciones reales mostraron, y que cambia varias conclusiones:

- `Released on: 2023-11-17` viene con la **fecha completa** en 45 de 50. Un tema
  de 2001 figura subido el 2024-12-12.
- Vienen los **créditos**: `Composer:`, `Lyricist:`, `Writer:`, `Producer:`, a
  veces combinados (`Composer, Lyricist: Nombre`) y a veces con dos espacios.
- La segunda línea trae **todos los artistas**: `Get Lucky · Daft Punk · Pharrell
  Williams · Nile Rodgers`.
- Hay líneas ℗ con dos titulares: `℗ 2021 ℗ Distributed exclusively by Warner
  Music France / ADA France, ℗ 2001 Daft Life Ltd.`
- El mismo álbum sale partido en dos productos, `Homework` 1996 y `Homework` 1997,
  porque el año ℗ es de cada grabación y no del release.

## Resumen

Hay tres cosas que dañan al usuario hoy y que ninguna herramienta del ciclo 1
podía ver, porque los tests prueban el código contra sí mismo:

1. **El botón final no funciona.** «Descargar el paquete» es un `<a href>` común
   y el servidor exige el token en una cabecera que un enlace no puede mandar. Da
   403 desde la primera versión pública. Los tests pasan porque su cliente siempre
   manda el token.
2. **La hoja de ingesta lleva datos equivocados con cara de datos buenos.** La
   fecha de lanzamiento es la fecha de subida a YouTube, las versiones en vivo y
   los remixes se quedan con el ISRC de la versión de estudio, un single puede
   quedar con el UPC del álbum, los nombres de archivo de audio no coinciden con
   los del ZIP, y un ISRC que se repite legítimamente entre el single y el álbum
   se marca como error y se manda a «corregir».
3. **Dos entradas hostiles.** Un `yt-dlp.conf` en la carpeta de Descargas ejecuta
   comandos con el módulo de audio prendido, y un título con `=HYPERLINK(...)`
   entra como fórmula viva en las planillas.

Lo demás es lo esperable de un producto que funciona: accesibilidad a medio
camino, estados que faltan, supply chain del CI sin cerrar, y un README que
promete un poco más de lo que la app sostiene.

---

## Mirada 1, industria musical

Quien mira migró catálogos del lado del sello y del lado del artista.

| id | dónde | qué pasa | por qué le importa a quien la usa | impacto | esfuerzo |
|---|---|---|---|---|---|
| IM01 | `src/migrador/validar.py:298-316`, `src/migrador/i18n.py:857` | Un ISRC repetido entre productos distintos es `error` y el paquete deja de ser apto. Es exactamente el caso del single que después entró en el álbum, o del deluxe | El usuario «arregla» un código correcto, pide uno nuevo y parte el historial de la grabación, que es lo que la migración tiene que evitar | alto | bajo |
| IM02 | `src/migrador/relevar_core.py:481-511`, `:573-575`, `src/migrador/productos.py:113` | El UPC de cada track es el del álbum de Deezer que ganó el match, sin mirar si ese álbum es el mismo release. Un single puede quedar con el UPC del álbum, o al revés | UPC de otro producto en la hoja de ingesta y en el nombre de la carpeta; y como la portada se busca primero por UPC (`portadas.py:81`), también baja la portada del otro | alto | medio |
| IM03 | `src/migrador/relevar_core.py:432-441`, `:472-477` | `_clean_title` borra `(En Vivo)`, `(Live)`, `(Remaster)`, `(cover)` y todo lo que va entre corchetes antes de comparar. Verificado: «Tema (En Vivo)» de 245 s, con la versión en vivo exacta entre los candidatos, se queda con el ISRC de estudio | Un ISRC equivocado que se ve igual que uno bueno. La grabación en vivo se entrega con el código de otra | alto | bajo |
| IM04 | `src/migrador/productos.py:97`, `:110`, `src/migrador/paquete.py:262` | La `Release Date` de la hoja es la fecha de subida a YouTube. Si falta, inventa `{año}-01-01`. La fecha real está en `Released on:` y se descarta | La fecha original es uno de los datos que hacen que las DSPs reconozcan el release migrado como el mismo | alto | bajo |
| IM05 | `src/migrador/productos.py:87` | Los productos se agrupan por (álbum, año ℗), y el año ℗ es de cada grabación. Verificado con datos reales: `Homework` sale como dos productos, 1996 y 1997 | Releases que no existen en la hoja de ingesta, cada uno con el mismo UPC | alto | medio |
| IM06 | `src/migrador/productos.py:79-88`, `:112` | El mismo álbum entregado por dos distribuidoras (en plena migración, o después de una baja que no se hizo) se funde en un producto con los tracks duplicados | Un álbum de diez tracks sale con veinte, y se esconde la señal más útil del caso: hay un release duplicado en vivo | alto | bajo |
| IM07 | `src/migrador/paquete.py:260`, `:273`, `src/migrador/relevar_core.py:304-358` | `Release Artist` y `Track Artist` son siempre el nombre del canal. La descripción trae «Título · Artista · Invitado» y se ignora | Los feats y colaboradores se pierden en la ficha nueva, que deja de coincidir con la original | medio | medio |
| IM08 | `src/migrador/relevar_core.py:343`, `src/migrador/paquete.py:251-254` | El titular de la línea ℗ se presenta como «Sello», con todo lo que venga pegado («under exclusive license to…»). La línea con dos ℗ deja un sello que empieza con `℗` | Se mezcla titular del fonograma con marca comercial, y el Label de la hoja sale sucio | medio | bajo |
| IM09 | `src/migrador/paquete.py:268-269` | `Territories` va fijo en `Worldwide` y `Disc Number` en 1 | Es metadata inventada. Un release con licencia por territorio se abriría al mundo en la ingesta nueva | medio | bajo |
| IM10 | `src/migrador/paquete.py:270`, `src/migrador/productos.py:101` | `Track Number` sale del orden estimado por fecha de subida y entra al CSV sin ninguna marca. Deezer ya devuelve el tracklist real en `album/{id}`, que la app baja y descarta | El archivo que se carga en la distribuidora lleva un orden que puede ser falso. Argumento nuevo sobre la decisión documentada: el dato real ya se descarga | medio | bajo |
| IM11 | `src/migrador/audio.py:447`, `:484-497` | El índice de Tidal se arma por ISRC y el último release procesado pisa a los anteriores. El track del álbum puede quedar con el número y el UPC del single, y el orden se marca confirmado | Con audio prendido, la app dice «orden confirmado» justo cuando no lo es | medio | medio |
| IM12 | `app/web/i18n.js:434`, `src/migrador/i18n.py:623-626`, `:666-669`, `:831-904` | Ningún texto explica que conservar ISRC, UPC y fecha original es lo que hace que el release nuevo se una al viejo, ni que la baja en la distribuidora vieja va recién cuando el nuevo está en vivo. La pantalla 2 dice «Lo que falta se completa en la distribuidora nueva» | Es la regla número uno de una migración, y el texto empuja a aceptar códigos nuevos | alto | bajo |
| IM13 | `src/migrador/paquete.py:317-402` | El reporte lista lo que falta pero no lo convierte en acciones: qué pedirle a la distribuidora actual (export de códigos, fechas, masters, arte) ni la secuencia de la baja | El ZIP es lo que le llega al manager, y ahí no hay un checklist de salida | medio | bajo |
| IM14 | `src/migrador/validar.py:38-43` | El aviso de «texto de YouTube en el título» salta con `En Vivo`, `Live Session` y `HD`, que después del filtro de Art Tracks son parte del título real | Cambiarle el título a una versión en la migración hace que deje de coincidir con la original | medio | bajo |
| IM15 | `src/migrador/productos.py:32-48` | El tipo single/EP/álbum ignora la duración. Algunas tiendas usan también minutos totales | Sólo afecta al rótulo `Release Type`. No se pudo verificar la regla vigente de cada tienda desde acá | bajo | bajo |
| IM16 | `src/migrador/i18n.py:882`, `app/web/i18n.js:536` | El FLAC de Tidal se presenta como «máster» y «apto para entregar». Es la copia que sirve la plataforma, que puede ser de menor resolución que el máster | La misma clase de etiquetado optimista que el proyecto ya rechaza para el audio lossy | medio | bajo |
| IM17 | `src/migrador/i18n.py:857`, `src/migrador/validar.py:32` | El LEEME dice «la distribuidora los rechaza», absoluto, donde la interfaz dice «suelen». El comentario atribuye 1400 px a «Spotify/Apple» | Afirma algo que no es cierto para todas las distribuidoras | bajo | bajo |
| IM18 | `src/migrador/relevar_core.py:304-358`, `src/migrador/paquete.py:276-277` | Los créditos de la descripción (Composer, Lyricist, Writer, Producer) se descartan y la hoja los marca como imposibles de obtener | Publishing es lo que más le cuesta juntar a un manager, y el dato estaba ahí | medio | bajo |

Verificaciones de esta mirada, que no son hallazgos: la app se queda sólo con
Art Tracks (`relevar_core.py:668`), así que videoclips, lyric videos y
visualizers no entran como productos; el sello de relleno de DistroKid se
descarta; ningún texto toma partido por una distribuidora.

## Mirada 2, distribución y metadata

Quien mira trabajó en ingesta y QC de una distribuidora.

| id | dónde | qué pasa | por qué le importa a quien la usa | impacto | esfuerzo |
|---|---|---|---|---|---|
| DM01 | `src/migrador/relevar_core.py:432-436` | El mismo limpiador de IM03 borra también `(Remix)`, `(Discovery Mix)`, `(feat. …)` y `[Extended Mix]`: un remix se queda con el ISRC del original con confianza `alta`. La confianza `media` no mira la duración | Es el peor error posible en una ingesta: dos grabaciones con el mismo código | alto | bajo |
| DM02 | `src/migrador/paquete.py:129`, `:279-280`, `:488-493` | `Audio File` del CSV y del xlsx es el nombre del archivo temporal (`tidal_998877.flac`), no el que tiene adentro del ZIP (`01 - Tema.flac`). `Cover File` dice `portada.jpg` fijo, que en inglés es `cover.jpg`, y aparece aunque no se hayan pedido portadas | En la carga masiva la distribuidora cruza audio y hoja por nombre de archivo, y así no cruza nada | alto | bajo |
| DM03 | `src/migrador/relevar_core.py:291`, `:352-357` | El regex de `Released on:` captura sólo el año, y no hay columna de fecha original | Mismo daño que IM04. Vocabulario de referencia, DDEX `OriginalReleaseDate` | alto | bajo |
| DM04 | `src/migrador/validar.py:298-316`, `tests/test_validar.py:145` | El duplicado de ISRC no distingue dentro del producto de entre productos. Propuesta de QC: dentro, error; entre productos, aviso si título y duración coinciden, y error de «match probable equivocado» si no | La regla actual es un falso positivo grave y, bien hecha, además atrapa los ISRC equivocados de DM01 | alto | bajo |
| DM05 | `src/migrador/relevar_core.py:520`, `src/migrador/portadas.py:81-92` | El UPC se acepta sin comparar título del álbum ni cantidad de tracks, y después la portada se busca por ese UPC con `ratio 1.0` | El UPC es la llave del release: entregar el de otro hace que se rechace o que se actualice el release equivocado | alto | medio |
| DM06 | `src/migrador/paquete.py:246`, `:258` | El LEEME pide completar los `<<COMPLETAR>>`, y lo natural es abrir el CSV en Excel: el UPC pasa a notación científica y pierde el cero, en es-AR el separador es `;` y todo cae en una columna, y `3:20` se lee como una hora | El CSV que sale de Excel ya no sirve para cargar | alto | bajo |
| DM07 | `src/migrador/portadas.py:44-53` | `_strip_ruido` saca `En Vivo`, `Live` y `Remaster` antes de buscar en iTunes. Probado: un álbum en vivo recibe la portada del de estudio con `match alta` | Portada de otro release en la carpeta de entrega | medio | bajo |
| DM08 | `src/migrador/paquete.py:268-273`, `src/migrador/productos.py:92` | Además de IM09 y IM10: con la misma fecha de subida el desempate del orden es alfabético, y si Tidal no trae `volume_number` la celda queda vacía | Campos estructurales rellenados como si fueran datos | medio | bajo |
| DM09 | `src/migrador/relevar_core.py:324-328`, `:520` | Las fixtures grabadas del propio repo muestran datos que la app baja y descarta: `record_type`, `nb_tracks`, `release_date` y `tracks` del álbum de Deezer, `track_position` y `disk_number` del track | Varias columnas que la hoja da por imposibles tienen fuente pública | medio | medio |
| DM10 | `src/migrador/validar.py:279`, `src/migrador/i18n.py:701-703` | «Sin errores: el catálogo no tiene problemas que causen rechazo» aunque haya `<<COMPLETAR>>` obligatorios, audio lossy o códigos de confianza media | Promete más de lo que mira. PRODUCT.md dice que la validación no es un certificado | medio | bajo |
| DM11 | `src/migrador/relevar_core.py:565`, `app/server.py:457-485` | La confianza del match (`alta`/`media`) se calcula y no llega a la tabla, ni a las planillas, ni a la hoja | Un ISRC dudoso se exporta igual que uno seguro | medio | bajo |
| DM12 | `src/migrador/validar.py:38-43` | `(En Vivo)` y `(Live Session)` dan aviso de ruido y `(Live)` no: el mismo caso se trata distinto según el idioma | Inconsistencia que además es falso positivo (IM14) | bajo | bajo |
| DM13 | `src/migrador/validar.py:38-43`, `:268` | Se escapan `(Audio)`, `(Letra)`, `(Lyrics)`, `(Videoclip Oficial)`, `[MV]`, `(Official Visualiser)`. El título del producto no se revisa | Rechazos de estilo que la validación no anticipa. Varía por distribuidora | bajo | bajo |
| DM14 | `src/migrador/validar.py:75-88`, `:320`, `src/migrador/paquete.py:271` | `036000291452` y `0036000291452` son el mismo GTIN y no salen como duplicado. `000000000000` pasa como UPC válido. El ISRC se exporta tal cual vino, con guiones o minúsculas si los trae | Casos poco probables hoy con Deezer, baratos de cerrar | bajo | bajo |
| DM15 | `src/migrador/validar.py:110-115`, `:190` | Para PNG el modo de color se da por RGB siempre: grises, paleta y transparencia pasan sin aviso. Un JPEG en grises tampoco avisa. Nada dice qué no se puede verificar (texto, URLs, logos, portadas agrandadas) | La validación calla sobre lo que no mira | medio | bajo |
| DM16 | `src/migrador/relevar_core.py:343`, `src/migrador/paquete.py:254` | Mismo origen que IM08, visto desde la hoja: la `P Line` combina `release_year` (que puede venir de `Released on`) con el titular, en vez de copiar la línea ℗ | La P Line no es la que figura en el release | medio | bajo |
| DM17 | `src/migrador/paquete.py:203-232` | Faltan columnas que las distribuidoras piden: fecha original, número de catálogo, versión, letrista, productor. `Explicit` no admite `Clean`. Las columnas internas van mezcladas con las de ingesta | La hoja no declara lo que no tiene | medio | bajo |

Verificaciones de esta mirada: el ISRC se valida por estructura y no por largo
(`validar.py:30`); el dígito verificador GTIN es correcto para UPC-A y EAN-13; el
xlsx escribe UPC e ISRC como texto; el CSV va en UTF-8 con BOM y fechas ISO; la
portada se mide en el archivo y no se confía en lo pedido.

## Mirada 3, ingeniería de software

Quien mira va a mantener esto dentro de un año sin acordarse de nada.

| id | dónde | qué pasa | por qué le importa | impacto | esfuerzo |
|---|---|---|---|---|---|
| SW01 | `src/migrador/relevar_core.py:146` | El regex del handle no admite `%`. `youtube.com/@pe%C3%B1a`, como lo copia el navegador, se resuelve como `@pe` | Si `@pe` existe, la app releva el catálogo de otro artista sin ningún error | alto | bajo |
| SW02 | `src/migrador/productos.py:121-126`, `src/migrador/texto.py:33`, `src/migrador/paquete.py:474-479` | Dos productos pueden tener el mismo nombre de carpeta: dos singles «Intro» del mismo año sin UPC, títulos que difieren después del carácter 60, o títulos en escritura no latina, que quedan todos como `Sin titulo` | Al descomprimir, la portada y la planilla de un producto pisan las del otro | alto | bajo |
| SW03 | `src/migrador/relevar_core.py:242-266`, `:561-571` | No hay ningún aviso de avance durante la paginación ni durante Deezer, que es la fase más larga. Medido: 24 s entre «Cancelar» y el estado cancelado, con la barra clavada en 55 % | El botón parece no andar y la app rechaza un relevamiento nuevo por «trabajo en curso» | medio | bajo |
| SW04 | `app/server.py:685`, `:719-720`, `src/migrador/audio.py:607` | La carpeta de audio se crea adentro de `preparar` y el servidor recién se entera cuando vuelve: si se cancela a mitad, queda en el disco | Un catálogo con audio pesa varios GB, y el intento siguiente puede fallar por falta de espacio | medio | bajo |
| SW05 | `src/migrador/productos.py:61-62`, `src/migrador/paquete.py:450`, `:493` | El comentario dice que 60 caracteres alcanzan para no pasarse de 260 en Windows. El peor caso medido adentro del ZIP ya son 294 | «Extraer todo» del Explorador falla en la máquina de quien recibe | medio | bajo |
| SW06 | `app/launcher.py:69`, `:281-291` | En el modo navegador, cerrar la ventana no cierra el servidor, y el binario no tiene consola. En la ventana nativa, cerrar a mitad de un trabajo no pregunta | Procesos huérfanos, una instancia nueva por cada doble clic, y relevamientos perdidos | medio | medio |
| SW07 | `src/migrador/relevar_core.py:418-428`, `:452` | Deezer reintenta seis veces con 1,5 s cualquier error, también el `800 no data`, que es permanente (9 s perdidos por consulta). Un `Retry-After` con fecha tira `ValueError` y tumba el relevamiento. Si Deezer está caído, se ve igual que «no hubo coincidencias» | Minutos perdidos, y un error que se lleva la cuota de YouTube ya gastada | medio | bajo |
| SW08 | `src/migrador/relevar_core.py:141-148` | Se rechazan un `UC…` suelto, `/user/Nombre`, `watch?v=` y `youtu.be/…` | La gente pega el link de un tema; resolverlo cuesta una unidad de cuota | bajo | bajo |
| SW09 | `src/migrador/relevar_core.py:655-660`, `:693` | Un corte a mitad hace perder todo el relevamiento, y `units` subestima el costo (no cuenta las 100 unidades de `search`) y no lo usa nadie | Con la clave compartida, cada reintento gasta lo mismo otra vez | medio | medio |
| SW10 | `app/server.py:571-580`, `:596-610` | «Un trabajo a la vez» se chequea y se registra sin el mismo lock. Reproducido abriendo la ventana 50 ms | Dos relevamientos simultáneos, justo lo que la regla quiere evitar | bajo | bajo |
| SW11 | `app/server.py:402-403`, `src/migrador/productos.py:128` | Los ids de producto son posicionales y se regeneran en cada relevamiento; una lista de ids vacía significa «todos» | Con dos pestañas, una arma el ZIP del artista de la otra. Una trampa para el próximo que toque la API | bajo | bajo |
| SW12 | `app/server.py:672-682`, `:698`, `:710` | Durante el audio la barra queda en 85 % y durante el ZIP en 90 % | Son las fases de minutos, y parecen colgadas | medio | bajo |
| SW13 | `src/migrador/portadas.py:180` | Todas las portadas quedan en memoria hasta cerrar el ZIP | Estimado, cientos de MB con trescientos productos | bajo | bajo |
| SW14 | `app/jobs.py:130`, `:134`, `app/server.py:607`, `:661` | «Listo.», «Cancelado.», «productos encontrados.» y «Preparando» en castellano fijo | La app en inglés muestra castellano en el progreso | bajo | bajo |
| SW15 | `src/migrador/relevar_core.py:243-266`, `:362-397`, `:553-591`, `:625-694`, `build/grabar_fixtures.py` | `relevar()` completo, la paginación, `build_tracks` y el enriquecimiento no tienen test, y no hay respuestas grabadas de la YouTube Data API. El contrato de `relevar()` se verifica buscando texto en el código fuente | Es justo donde viven SW01, SW03 y SW07 | medio | medio |
| SW16 | `app/web/app.js` | Se puede testear sin navegador con `node --test` y un DOM mínimo (probado con Node 24), y hoy no tiene tests | `esc()` es la barrera entre los títulos de YouTube y el `innerHTML` | medio | bajo |
| SW17 | `src/migrador/contratos.py:226`, `src/migrador/relevar_core.py:597`, `:701` | Veintiséis reglas de `strict` dan cero errores hoy y no están prendidas. `strictDictionaryInference` destapa un error real de contrato: `distribs` declara `int` y lleva un `str` | El camino a `strict` escrito en el ciclo 1 se puede avanzar sin ruido | medio | bajo |
| SW18 | `.github/workflows/build.yml:23-26`, `:60-246` | Ver SG14 y SG15: permisos amplios y acciones sin fijar por SHA | | medio | bajo |
| SW19 | `requirements-dev.txt`, `.github/workflows/tests.yml:31`, `:95` | `pyright>=`, `openpyxl` y `pillow` sin versión en el CI; sin `timeout-minutes`, sin caché de pip, sin `concurrency` | Un CI que se puede romper solo, y un PyInstaller colgado que corre seis horas en runners de macOS | medio | bajo |
| SW20 | `src/migrador/relevar_core.py:682-683`, `app/web/app.js:628-641`, `:1234-1247` | `cobertura_metadata` y `topic_sugerido` son constantes, y las dos ramas de la interfaz que los usan no se ejecutan nunca | Tres campos, dos ramas y sus textos para mantener sin que hagan nada | bajo | bajo |
| SW21 | `pyproject.toml:25`, `:70`, `:95-99`, `src/migrador/productos.py:12-13` | Comentarios que describen el repo de antes del ciclo 1: la versión «en app/server.py», los módulos «en la raíz», un ignore para un archivo que ya no existe | El repo se apoya en sus comentarios para explicar sus decisiones | bajo | bajo |
| SW22 | `build/capturas.py:664`, `:714` | Al terminar, el hilo del servidor sigue escribiendo a stderr mientras el intérprete se cierra: `Fatal Python error: _enter_buffered_busy` y código de salida distinto de cero, aunque las siete capturas salieron bien | La verificación completa no puede estar en verde | medio | bajo |
| SW23 | `docs/capturas/` | Las capturas publicadas muestran `v1.0.1` | El README dice que «no pueden quedar desactualizadas sin que se note», y se notó | bajo | bajo |

Verificaciones: toda llamada a `urlopen` tiene timeout; `api_get` reintenta los
5xx con espera creciente y no reintenta 403 ni 404; los errores de YouTube salen
traducidos y con código; el ZIP se escribe a disco y se sirve en bloques; se
registra recién terminado, así que no se puede bajar uno a medio escribir.

Tabla de reglas de pyright, conteo neto sobre la configuración actual.

| Reglas | Errores |
|---|---|
| `reportUnnecessaryTypeIgnoreComment`, `reportUnusedVariable`, `reportUnusedClass`, `reportUnusedFunction`, `reportUnnecessaryComparison`, `reportUnnecessaryIsInstance`, `reportUnnecessaryCast`, `reportUnnecessaryContains`, `reportMissingTypeArgument`, `strictListInference`, `strictSetInference`, `strictParameterNoneValue`, `reportUntypedFunctionDecorator`, `reportUntypedClassDecorator`, `reportUntypedBaseClass`, `reportUntypedNamedTuple`, `reportConstantRedefinition`, `reportDeprecated`, `reportDuplicateImport`, `reportInconsistentConstructor`, `reportMatchNotExhaustive`, `reportTypeCommentUsage`, `reportPrivateImportUsage`, `deprecateTypingAliases`, `reportPropertyTypeMismatch`, `reportImportCycles` | 0 |
| `reportUnusedImport` | 8, todos imports que sólo prueban si un módulo existe |
| `strictDictionaryInference` | 13, uno de ellos un error real de contrato |
| `reportPrivateUsage` | 21, todos en tests |
| `reportMissingParameterType` | 622 |
| `strict` completo | 3105 |

## Mirada 4, UX y UI

Quien mira es diseñadora de producto y prueba la app como un manager que la abre
por primera vez. Los contrastes se calcularon desde `app/web/tokens/colors.css`.

| id | dónde | qué pasa | por qué le importa a quien la usa | impacto | esfuerzo |
|---|---|---|---|---|---|
| UX01 | `app/web/app.js:987`, `app/server.py:899-901`, `app/launcher.py:69` | «Descargar el paquete» es un `<a href download>`, y un enlace no manda la cabecera `X-App-Token`: el servidor contesta 403. Además, pywebview 6.2.1 trae `ALLOW_DOWNLOADS` apagado. Viene así desde la primera versión pública | La persona ve «Tu paquete está listo» y no se lo puede llevar | alto | bajo |
| UX02 | `app/web/app.js:545-548`, `:1205`, `:1225` | El campo del link se dibuja sin `value` y se borra en cada redibujado: al fallar, el error queda debajo de un campo vacío | No se ve qué se pegó ni qué canal se está relevando | alto | bajo |
| UX03 | `app/web/tokens/colors.css:140`, `:187`, `app/web/app.css:410` | El borde de los campos da 1,23 a 1,32 contra su fondo, y el de la casilla sin marcar 1,38 a 1,50. WCAG 1.4.11 pide 3 a 1 | Con baja visión, el campo del link y las casillas de la tabla no se ven | alto | bajo |
| UX04 | `app/web/app.css:347-348` | El botón principal es hueso fijo: en tema claro da 1,00 a 1 contra la tarjeta | En claro, el botón más importante de cada pantalla desaparece | alto | bajo |
| UX05 | `app/web/app.js:301` | Al redibujar, el foco se pierde si estaba en el chevron de una fila o en el stepper; y en los cambios de vista nada lleva el foco al título nuevo | Con teclado o lector de pantalla se vuelve al principio de la página en cada chevron | alto | medio |
| UX06 | `app/web/app.js:429-432` | Las alertas no tienen `role`: ningún error se anuncia | Con lector de pantalla, «se agotó el cupo» pasa en silencio | medio | bajo |
| UX07 | `app/web/index.html:32-33` | Los botones ES y EN no tienen nombre accesible ni `lang` | Un lector los pronuncia como sílabas | bajo | bajo |
| UX08 | `app/web/app.js:660-667`, `src/migrador/migrar_core.py:62-69` | No existe el estado «el artista no está en Deezer», que PRODUCT.md pide decir con esas palabras; tampoco se distingue de «no pediste códigos» | Se ve «ISRC 0 de 27» y parece una falla de la app | medio | medio |
| UX09 | `app/web/app.js:1162`, `:1169`, `:1188-1191` | Después de cargar la clave propia sigue a la vista el cartel de cupo agotado. Dos acciones usan `window.scrollTo` cuando lo que scrollea es `main` | El error ya resuelto sigue diciendo que hay un error | medio | bajo |
| UX10 | `app/web/app.js:1308` | Cancelar el armado del paquete se muestra como falla, en rojo, bajo «No se pudo generar» | Una acción del usuario presentada como error | bajo | bajo |
| UX11 | `app/web/app.js:1351-1352` | El estado del pie nunca se limpia: queda «Portada 3 de 4» de un trabajo terminado | El estado que tiene que estar siempre a la vista miente | bajo | bajo |
| UX12 | `app/web/app.css:522`, `:529`, `:702` | `overflow-x` en el contenedor de la tabla anula la cabecera fija, y la barra de «Continuar» queda al final de la tabla | Con quinientas filas, «Continuar» queda veintiséis mil píxeles más abajo | medio | bajo |
| UX13 | `app/web/app.js:268-289` | No se puede ordenar ni filtrar por lo que falta | En un catálogo grande, «¿qué me falta?» se contesta scrolleando | medio | medio |
| UX14 | `app/web/app.js:291-293`, `:1293` | Lo elegido que el filtro esconde no entra al ZIP, y nada lo dice | Productos que se pierden de la entrega sin aviso | medio | bajo |
| UX15 | `app/web/app.js:275`, `app/web/i18n.js:428-431` | Destildar todas las distribuidoras muestra todo; el estado vacío siempre habla de años | El filtro hace lo contrario de lo que se pidió | bajo | bajo |
| UX16 | `app/web/i18n.js:401`, `:437`, `:452`, `:494`, `:595`, `app/web/app.js:665-666`, `:708-710` | Faltan plurales («1 productos elegidos, 1 tracks») y hay cifras sin formato local | Se lee descuidado justo en los resúmenes | medio | bajo |
| UX17 | `app/web/app.js:396`, `src/migrador/audio.py:281`, `:395`, `:637`, `:662` | Textos en castellano fijo fuera de los catálogos, que se ven con la app en inglés | La regla 5 de CONTRIBUTING | bajo | bajo |
| UX18 | `app/web/i18n.js:515`, `:523`, `:552`, `:88` | Jerga sin explicar («token de origen», «DRM»), instrucciones que no se pueden seguir con doble clic (`--diagnostico`), PowerShell y `winget` sugeridos en cualquier sistema, y dos grafías del nombre de la app | Quien no es técnico se traba ahí | medio | bajo |
| UX19 | `app/web/i18n.js:383`, `:600` | Nada define ISRC ni UPC, y la pantalla final no dice qué hacer con el ZIP ni que los `<<COMPLETAR>>` hay que llenarlos | El éxito termina sin paso siguiente | medio | bajo |
| UX20 | `app/web/i18n.js:590` | «Te avisamos cuando esté» no tiene ninguna notificación detrás | Una promesa que la app no cumple | bajo | bajo |
| UX21 | `app/web/app.js:492`, `:1186` | La clave se pega en un campo de contraseña, así que no se ve lo que se pegó; «Verificando» usa una clase `.spinner` que no existe en el CSS | El mayor punto de abandono de la primera vez | medio | bajo |
| UX22 | `app/launcher.py:281-291` | Visto desde la persona que la usa, SW06: si la app cae al navegador, cerrar la pestaña no la cierra | «Mientras la app esté abierta» se vuelve ambiguo | medio | medio |
| UX23 | `app/web/app.css:190`, `:348`, `app/web/tokens/colors.css:93-94` | Un `backdrop-filter: blur` que DESIGN.md §9 prohíbe, un `#FFFFFF` suelto, seis tokens sin uso, y el «peor par de texto» escrito con tres números distintos | DESIGN.md y el código dejan de decir lo mismo | bajo | bajo |
| UX24 | `docs/capturas/`, `build/capturas.py:346` | Ver SW23. Además, el texto de ejemplo de una captura está sin tildes, y no hay ninguna en tema claro | | bajo | bajo |

Verificaciones: todo el texto pasa AA en los dos temas (el terciario da 5,4 a
6,4), el anillo de foco da 5 a 6,6, las casillas son nativas, el `lang` del
documento y el título cambian con el idioma y el paso, `prefers-reduced-motion`
apaga todo, y los valores de DESIGN.md para superficies, semánticos, tipografía
y radios coinciden con los tokens.

## Mirada 5, ciberseguridad

Quien mira asume otras pestañas abiertas y un binario bajado de un link que le
pasaron. Las pruebas corrieron contra el servidor real, con un HOME aislado.

| id | dónde | qué pasa | escenario realista | impacto | esfuerzo |
|---|---|---|---|---|---|
| SG01 | `src/migrador/audio.py:572-579` | yt-dlp se llama sin `--ignore-config` ni `cwd`, así que carga un `yt-dlp.conf` de la carpeta de trabajo. Probado: un `--exec` plantado ahí queda activo | El exe portable se abre desde Descargas, donde una página dejó un `.conf`; con el audio prendido, el primer tema de referencia ejecuta lo que diga el archivo | medio | bajo |
| SG02 | `src/migrador/paquete.py:98`, `:133`, `:235-285` | Un título, un sello o un artista que empiece con `=` entra como fórmula viva en el xlsx y tal cual en el CSV. Probado con `=HYPERLINK(...)` | Quien controla los títulos del canal relevado mete fórmulas que se activan al abrir la planilla | medio | bajo |
| SG03 | `src/migrador/productos.py:134-135` | El UPC entra crudo al nombre de la carpeta. Con `../../../../../evil` la entrada del ZIP sale de la raíz | Una API que devuelve un UPC hostil y un descompresor que no sanea | bajo | bajo |
| SG04 | `src/migrador/portadas.py:69-71`, `:141-148` | La URL de la portada que devuelve iTunes no se valida: `file://` lee un archivo local. Tampoco hay límite de tamaño | Hace falta una respuesta maliciosa de iTunes, que viaja por HTTPS | bajo | bajo |
| SG05 | `app/server.py:808-813`, `:997-1001` | Sin `frame-ancestors` en la CSP ni `X-Frame-Options`, `Cross-Origin-Opener-Policy` o `Cross-Origin-Resource-Policy` | Otra pestaña que adivine el puerto mete la app en un iframe y engaña clics | bajo | bajo |
| SG06 | `app/server.py:1034-1037` | No se mira `Origin` ni `Sec-Fetch-Site` | Capa de refuerzo sobre el token, no un agujero | bajo | bajo |
| SG07 | `app/web/app.js:987` | El mismo bug de UX01, visto desde acá: el arreglo obvio, eximir la descarga del token, debilitaría la primera defensa. Propuesta: un ticket de un solo uso que se pide con el token | | alto | medio |
| SG08 | `app/server.py:846`, `:1029-1037` | El cuerpo se parsea como JSON antes de controlar Host y token; un cuerpo demasiado grande o un `Transfer-Encoding: chunked` quedan en el socket y contaminan el pedido siguiente | Robustez del servidor | bajo | bajo |
| SG09 | `app/server.py:870-872`, `:961-963` | Un token con caracteres no ASCII da 500 con el texto de la excepción, y `GET /D:foo` también (`commonpath` de dos unidades distintas) | Errores internos a la vista | bajo | bajo |
| SG10 | `app/server.py:143-144`, `:185-191` | La carpeta y el temporal de la config se crean con los permisos por defecto y el `chmod 0600` llega después | En POSIX, la clave queda legible por otros usuarios durante esa ventana | bajo | bajo |
| SG11 | `src/migrador/relevar_core.py:64-66` | La clave viaja en la URL. Hoy ningún error la muestra (probado), pero cualquier excepción futura que cite la URL la filtraría | Una fuga latente, sin test que la cubra | bajo | bajo |
| SG12 | `build/sin_claves.py:31`, `:37` | El control de claves no mira la historia de git ni el interior de los `.xlsx` | Una clave que entró y salió en un commit viejo no se ve | bajo | bajo |
| SG13 | `requirements-audio.txt:22`, `.github/workflows/build.yml:77` | `yt-dlp>=2024.1.0` admite versiones con CVE conocidos (CVE-2024-38519, de memoria, no escaneado); `pyinstaller` sin versión; sin `pip-audit` ni Dependabot | Se publica lo que PyPI tenga ese día | medio | medio |
| SG14 | `.github/workflows/build.yml:60`, `:246`, `.github/workflows/tests.yml:22` | Todas las acciones por tag mutable, incluida `softprops/action-gh-release@v2`, de terceros y con permiso de escritura | Si alguien mueve ese tag, su código corre al publicar el release | medio | bajo |
| SG15 | `.github/workflows/build.yml:23-26`, `build/build.py:387-389` | `contents: write` a nivel del workflow, así que lo reciben los ocho jobs que hacen `pip install`; la clave de YouTube está en el entorno mientras corre pytest; `tests.yml` no declara permisos | Un paquete comprometido recibe un token con escritura sobre el repo | medio | bajo |
| SG16 | `.github/workflows/build.yml:197-204`, `SECURITY.md:34-36` | La atestación es condicional y tolera fallar (`continue-on-error`), mientras SECURITY.md y el README la presentan como garantizada | La documentación promete más que el workflow | bajo | bajo |
| SG17 | `SECURITY.md:19-23`, `:58-63`, `app/server.py:16-25`, `:101` | SECURITY.md y el docstring del servidor dicen «dos defensas» y no nombran la CSP. `"::1"` sin corchetes nunca coincide | Quien reporte no sabe que saltear la CSP entra en el alcance | bajo | bajo |
| SG18 | `docs/` | No hay modelo de amenazas escrito. Por ejemplo, cualquier proceso local obtiene el token con un `GET /`, y eso está bien pero no está dicho | El próximo cambio no sabe qué defensa no romper ni contra quién existe cada una | bajo | bajo |

Verificaciones: el token se compara en tiempo constante y es nuevo en cada
arranque; el Host rechaza `LOCALHOST`, `localhost.`, `127.0.0.1.nip.io` y
`localhost@evil.com`; los estáticos resisten `%2e%2e`, `..%5c`, rutas UNC y
`%00`; no hay SSRF porque la URL del usuario nunca se pide, sólo se extrae de
ella un id o un handle; todos los `innerHTML` pasan los datos externos por
`esc()`; ningún subproceso usa `shell=True`; el token de Tidal vive en memoria;
el CI usa `pull_request` y no `pull_request_target`, y el secreto no llega a
forks.

## Mirada 6, marketing de software y SEO

Quien mira lanzó herramientas gratuitas para nichos. Nada de métricas,
testimonios ni comparaciones inventadas. Estado del repo en GitHub: descripción
sólo en castellano, ocho topics, sin sitio web, sin imagen para redes.

| id | dónde | qué pasa | a quién no le llega | impacto | esfuerzo |
|---|---|---|---|---|---|
| MK01 | `README.md:28-29` | La descarga es una línea de texto hacia `/releases`, debajo de la captura y de cinco líneas técnicas; ahí esperan 32 archivos, la mitad `.sha256` | Al manager que no sabe qué es un `.sha256`. Los nombres no llevan versión, así que un enlace `releases/latest/download/…` sirve para siempre | alto | bajo |
| MK02 | `README.md` | No hay «para quién es y para quién no» (está en PRODUCT.md y TERMINOS.md) | Quien no tiene derechos sobre el catálogo, o necesita DDEX, se entera después de bajarla | alto | bajo |
| MK03 | `README.md:5`, `README.en.md:5` | La promesa arranca con «relevar el catálogo», jerga rioplatense de oficio; en inglés, «surveys» suena raro | El dolor real, cambiar de distribuidora sin perder códigos, recién aparece en el segundo renglón | medio | bajo |
| MK04 | `README.md:8-9`, `:211` | «Te dice qué va a ser rechazado» y «la distribuidora los rechaza», cuando PRODUCT.md dice que la validación no es un certificado y la app dice «suelen» | Si una distribuidora rechaza algo que se dio por bueno, se pierde la confianza en toda la herramienta | alto | bajo |
| MK05 | `README.md:6-7` | «Te devuelve los ISRC y los UPC», y eso depende de que Deezer los tenga | La captura principal muestra «ISRC en 13 / 27» | medio | bajo |
| MK06 | `README.md:20-21`, `:142`, `:208`, `:249`, `app/web/i18n.js:343`, `:388` | Afirmaciones sin respaldo: «la parte que más tiempo ahorra», «casi todas las distribuidoras», «la misma postura que yt-dlp», «unos 500 catálogos por día», y que las capturas no pueden quedar viejas | Cada una es una promesa que alguien puede verificar y encontrar falsa | medio | bajo |
| MK07 | `docs/INSTALAR-MAC.md:5`, `:33`, `README.md:91` | La guía de macOS sólo explica la Terminal y no menciona el `.app`; el comando del `.deb` nombra un archivo de 1.0.2 que ya no existe | Usuarios de Mac y de Linux, en el paso de instalar | alto | bajo |
| MK08 | `README.md:58` | El `.app` se presenta como «la recomendada» y nadie lo abrió en una Mac (MEJORAS.md lo dice) | Promete algo no verificado | medio | bajo |
| MK09 | `app/web/i18n.js:83`, `:88`, `README.en.md:1`, `build/migrador.spec:224` | Siete grafías del nombre: «Migrador de Catálogos», «Migrador de catálogos», «Catalog Migrator», «Migrador de Catalogos», `migrador-catalogos`, `catalog-migrator` | Quien habla inglés lee un nombre y baja archivos con otro | medio | bajo |
| MK10 | `README.md:284-560` | Las dos versiones tienen la misma estructura (24 encabezados), pero la mitad es técnica y hay técnica antes de la mitad | La parte técnica tapa a la de uso | medio | medio |
| MK11 | `build/notas_release.py:121-126`, `CHANGELOG.md:9-112` | Las notas del release ponen primero el CHANGELOG, que en 1.1.0 son cien líneas sobre pytest, pyright y TypedDict, y recién después «cuál bajar» | Es la página a la que llega el manager desde el README | alto | medio |
| MK12 | repo en GitHub | Descripción sólo en castellano, topic `distribution` ambiguo, sin sitio web | Búsquedas en inglés. Decisión del dueño | medio | bajo |
| MK13 | `docs/marca/` | No hay imagen para redes de 1280×640 | Cada link compartido muestra la tarjeta genérica de GitHub. Subirla es decisión del dueño | medio | bajo |
| MK14 | `.github/ISSUE_TEMPLATE/config.yml:4` | No hay dónde hacer una pregunta: el issue en blanco está apagado y Discussions también | «¿Funciona con mi distribuidora?» no es un bug ni una idea. Decisión del dueño | medio | bajo |
| MK15 | `README.md` | No hay preguntas frecuentes; las respuestas están repartidas entre README, TERMINOS y SECURITY, y tres no están en ningún lado: ¿funciona con mi distribuidora?, ¿necesito saber programar?, ¿es legal? | Las objeciones se responden antes de bajar o no se responden | alto | bajo |
| MK16 | `TERMINOS.md:80` | Los términos dicen que se consulta MusicBrainz y el README no; en el código es un respaldo apagado que la app no expone | Justo la pregunta de a quién se le mandan datos | bajo | bajo |
| MK17 | `app/web/index.html:2` | Verificación, no hallazgo: `lang` y `<title>` cambian con el idioma y el paso. Meta description y Open Graph no aplican a una página local con token | | — | — |
| MK18 | `pyproject.toml:20`, `:41-43` | Descripción sólo en castellano, sin `keywords`, y URLs con claves que las herramientas no reconocen | Bajo, porque no se publica en PyPI | bajo | bajo |
| MK19 | `docs/` | Una landing en GitHub Pages suma: los directorios y foros piden una URL que no sea un listado de archivos. Activarla es decisión del dueño | | medio | medio |

---

## Ranking

Primero lo que puede dañar al usuario o a su catálogo, después lo que más rinde
por esfuerzo, último lo cosmético. El orden de ejecución, con los hallazgos
agrupados en ítems que cierran en un turno, está en [MEJORAS-2.md](MEJORAS-2.md).

| # | Hallazgos | Por qué ahí |
|---|---|---|
| 1 | SW22, SW23 | Sin esto la verificación completa no puede estar en verde, y cada ítem la corre |
| 2 | UX01, SG07 | El entregable no se puede bajar |
| 3 | SG01, SG02, SG04 | Contenido hostil que entra de afuera |
| 4 | SG03, SW02, SW05 | El ZIP puede pisar archivos o no descomprimirse |
| 5 | IM01, DM04 | Falso error que empuja a romper el historial |
| 6 | IM03, DM01, DM07 | ISRC y portada de otra grabación |
| 7 | SW01, SW08 | Relevar el catálogo de otro artista |
| 8 | IM04, DM03 | Fecha falsa en la hoja |
| 9 | IM02, DM05 | UPC de otro release |
| 10 | DM02 | La hoja apunta a archivos que no existen |
| 11 | el resto de la hoja de ingesta (IM05-IM10, IM18, DM06, DM08-DM17) | Datos que la hoja inventa, descarta o pierde |
| 12 | SG05, SG06, SG08-SG11, SG13-SG18 | Endurecer lo que ya funciona |
| 13 | SW03, SW04, SW06, SW07, SW10-SW12, SW14-SW17, SW19-SW21 | Robustez, cobertura y deuda |
| 14 | UX02-UX24 | Recorrido, accesibilidad y textos |
| 15 | IM12, IM13, IM16, IM17 | La guía de migración que la app no da |
| 16 | MK01-MK19 | Que llegue a quien la necesita |
