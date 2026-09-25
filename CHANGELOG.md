# Changelog

**Español** · [English](CHANGELOG.en.md)

Lo que cambió en cada versión publicada. Los números siguen
[SemVer](https://semver.org/lang/es/), y las descargas están en
[Releases](https://github.com/joacogoliver-debug/catalog-migrator/releases).

## [Sin publicar]

### Agregado
- **La app explica la regla número uno de una migración**: conservar el ISRC,
  el UPC y la fecha original es lo que une cada release nuevo al que ya está en
  las tiendas, con sus reproducciones y playlists, y la baja en la distribuidora
  vieja va recién cuando el catálogo nuevo está en vivo. Lo dicen la pantalla
  del catálogo, una lista de «Qué sigue» en la pantalla final y una sección
  nueva del LEEME del ZIP, con qué pedirle a la distribuidora actual.
- **La pantalla del catálogo dice por qué faltan los códigos**: si no se
  pidieron, si el artista no está en Deezer (con esas palabras, como pide
  PRODUCT.md) o si Deezer no respondió. Antes las tres se veían como «ISRC 0 de
  27».
- **«Si algo no anda» en el README**, con el comando del diagnóstico para cada
  sistema y cada forma de instalación.
- **Filtro «Sólo los que tienen algo que completar»** en la tabla del paso 2:
  deja los productos sin UPC, con ISRC faltantes o con el orden sin confirmar.
  En un catálogo grande, «¿qué me falta?» se contestaba scrolleando.
- Si Deezer no respondió, el log lo dice. Antes se veía igual que «no hay
  códigos para este artista».
- **La hoja de ingesta también viene en Excel**, `_Hoja de ingesta.xlsx`, con
  las mismas filas que el CSV, cada celda como texto y lo que falta resaltado.
  El CSV no sobrevive a pasar por Excel: el UPC pierde el cero de adelante y
  pasa a notación científica, `3:20` se lee como una hora y, con la
  configuración en castellano, todo cae en una sola columna. El LEEME lo dice, y
  nombra además los campos que una distribuidora puede pedir y que la hoja no
  trae porque no salen de ningún lado público.
- **La hoja de ingesta trae los créditos que YouTube publica.** Cada Art Track
  dice quién compuso, escribió la letra y produjo el tema, cuando la
  distribuidora original lo mandó, y la hoja lo marcaba como imposible de
  obtener. En los datos reales, 46 de 50 temas traían compositor. Ahora van en
  `Composer`, `Lyricist`, `Producer` y `Publisher`, y lo que falta sigue a
  completar.
- El artista de cada tema es el que nombra YouTube, y los demás van en la
  columna nueva `Additional Artists`. Antes todos los temas salían a nombre del
  canal y los invitados se perdían. Si el artista del canal no es el principal
  de un tema, la validación avisa que se verifique quién controla ese master.
- **El número de track y de disco son los reales cuando Deezer tiene el
  álbum.** La app ya bajaba el tracklist y lo tiraba, y la hoja llevaba el
  orden estimado por fecha de subida sin ninguna marca. Ahora, si el álbum de
  Deezer se verificó como el mismo release, cada tema toma su posición y su
  disco. Si no, el orden sigue siendo estimado y la columna `Track Order` de la
  hoja lo dice. Sobre los datos reales, un álbum doble de 22 temas queda con sus
  dos discos, y dos temas que Deezer ubica en el mismo disco dejan de aparecer
  como dos releases.
- La hoja de ingesta tiene la columna `Original Release Date`, con la misma
  fecha real que `Release Date`, porque cada distribuidora la pide en una de
  las dos. El LEEME explica cuál usar si la distribuidora nueva pide otra
  fecha de salida.
- El campo del link acepta también el ID `UC…` suelto, los links `/user/` y
  `/c/`, y el link de cualquier tema del artista (`watch?v=`, `youtu.be`,
  `/shorts/`, YouTube Music): la app busca el canal que lo subió, por una unidad
  de cuota.

### Corregido
- **Cerrar la app en el navegador la cierra de verdad.** Cerrar la pestaña no
  le avisaba a nadie y el binario no tiene consola, así que quedaba un servidor
  corriendo para siempre, uno más por cada doble clic. Ahora la página late cada
  15 segundos y la app termina sola unos tres minutos después del último latido,
  salvo que haya un trabajo corriendo, y sin cerrarse por una suspensión de la
  máquina.
- **Cerrar la ventana a mitad de un trabajo pregunta antes**, en vez de perder
  el relevamiento o el paquete sin aviso.
- **El paquete no se podía bajar desde la app.** El botón «Descargar» era un
  enlace directo a la API, y un enlace no puede mandar la cabecera con el token
  de la sesión, así que el servidor lo rechazaba. Pasaba desde la primera
  versión pública, y además la ventana nativa tenía las descargas apagadas.
  Ahora el botón pide primero un ticket de un solo uso, que vence en un minuto y
  sólo se obtiene con el token, y la descarga anda en la ventana y en el
  navegador sin aflojar ninguna de las tres defensas.
- **Afirmaciones que no se podían sostener**: la validación «marca lo que
  suele» rechazarse y no «lo que va a ser rechazado»; los ISRC y UPC son «los
  que se pueden recuperar de Deezer»; se fueron «casi todas las
  distribuidoras», «la misma postura que yt-dlp» y el cupo de «unos 500
  catálogos por día», que no salía de ninguna cuenta. La interfaz dice ahora
  cuánto gasta cada relevamiento.
- **El `.app` de Mac ya no se presenta como el recomendado**: nunca se abrió en
  una Mac real, y así lo dicen el README y la guía de Mac, que ahora lo
  menciona. Lo mismo con el `.deb`, verificado por estructura y nunca
  instalado. El probado es el ejecutable suelto, que el CI arranca en cada build.
- **El comando del `.deb` ya no nombra la versión 1.0.2**, que no existe más.
- **El README dice qué pasa con MusicBrainz**, que los términos nombran: hay un
  respaldo en el código, apagado, y hoy no se le manda nada.
- **La atestación de procedencia se describe como es**: condicional a que el
  repositorio sea público, y sin frenar el release si falla. SECURITY.md y el
  README la presentaban como garantizada.
- **El FLAC de Tidal ya no se presenta como «máster».** Es la copia sin
  pérdida que sirve la plataforma, que sirve para entregar cuando no hay otra
  cosa, pero puede tener menos resolución que el máster de estudio.
- **La instrucción para instalar ffmpeg es la de tu sistema.** Se ofrecía
  `winget` en PowerShell también en Mac y Linux.
- **Menos jerga y ninguna promesa sin respaldo**: se fueron «token de origen»
  y «DRM», la indicación de abrir la app con `--diagnostico` (que no se puede
  seguir con doble clic) y el «Te avisamos cuando esté», que no tenía ninguna
  notificación detrás. El ISRC y el UPC se definen donde se piden.
- **La cabecera de la tabla y la barra de «Continuar» quedan fijas.** La
  cabecera dejaba de serlo por un scroll horizontal del contenedor, y con
  quinientas filas «Continuar» quedaba al final de todo.
- **Lo elegido que el filtro esconde se avisa.** No entra al paquete, porque
  sale lo elegido de lo que se ve, y ahora la barra lo dice con un «Ver todos»
  al lado.
- **Destildar todas las distribuidoras ya no muestra todo**: muestra nada, y el
  cartel dice que no hay ninguna marcada en vez de hablar de años.
- **En tema claro, el botón principal no se veía**: era hueso sobre una
  tarjeta hueso, 1 a 1. Ahora en claro es grafito, que es lo que más contrasta.
- **Los bordes de los campos y de las casillas se ven.** Daban 1,3 a 1 contra
  su fondo, y con baja visión el campo del link y las casillas de la tabla no
  se distinguían. Ahora dan de 3,6 a 4,7, por encima del 3 a 1 que pide WCAG, y
  un test lo mide sobre los colores reales en los dos temas.
- **El foco no se pierde.** Al abrir el detalle de un producto o al volver a
  un paso con el teclado, el foco se iba al principio de la página; ahora se
  queda en el control, y en cada cambio de pantalla va al título nuevo.
- **Los errores se anuncian** con lector de pantalla, y los botones ES y EN
  tienen nombre («Español», «English») en vez de leerse como sílabas.
- **El link pegado ya no se borra.** Cada vez que la pantalla se redibujaba, el
  campo volvía vacío: si el relevamiento fallaba, el error quedaba debajo de un
  campo en blanco y no se veía qué se había pegado. Lo mismo con la casilla de
  los códigos, que volvía siempre marcada.
- **Cargar la clave propia saca el cartel de cupo agotado**, que era
  justamente lo que se estaba resolviendo, y la pantalla vuelve arriba.
- **Cancelar el armado del paquete ya no se muestra como una falla.** Antes
  aparecía en rojo, bajo «No se pudo generar»; ahora vuelve al paso 3 con lo
  elegido intacto y un aviso que dice que se canceló.
- **El pie de la ventana se limpia al terminar un trabajo.** Quedaba diciendo
  «Portada 3 de 4» de algo que ya había terminado.
- **La clave se pega a la vista**, así se puede ver si entró entera, y
  «Verificando» tiene su indicador animado: usaba una clase que no existía.
- Con la app en inglés, el progreso de los trabajos y el log del módulo de
  audio seguían en castellano («Listo.», «Preparando», «productos encontrados»,
  «tracks por YouTube»). Ahora salen del catálogo, y un test que lee el código
  impide que vuelva a escribirse texto por fuera.
- Faltaban plurales: con un solo producto se leía «1 productos elegidos, 1
  tracks». Los resúmenes de cada paso se reescribieron para que concuerden, y
  las cifras salen con el formato del idioma.
- La cabecera escribía el nombre de la app distinto que el resto («Migrador de
  catálogos» contra «Migrador de Catálogos»).
- Con dos ventanas abiertas, si en una se relevaba otro artista, la otra armaba
  el paquete de ése con los productos que tenía elegidos del anterior. Ahora el
  catálogo tiene un identificador y el servidor lo rechaza con un aviso.
- Cancelar el paquete a mitad de las descargas de audio dejaba varios GB en la
  carpeta temporal hasta el día siguiente, y un paquete nuevo dejaba el ZIP del
  anterior. Las dos cosas se borran ahora en el momento.
- Un pedido sin productos elegidos armaba el paquete del catálogo entero. La
  interfaz no lo manda así, pero ahora es un error.
- **«Cancelar» tardaba decenas de segundos en responder durante la búsqueda de
  códigos**, y la barra quedaba clavada en 55 %. Con 600 temas se midieron 24
  segundos, y mientras tanto la app rechazaba un relevamiento nuevo por
  «trabajo en curso». Ahora la búsqueda en Deezer, el listado de videos y la
  metadata avisan avance en cada paso, y cancelar corta ahí. El armado del
  paquete va por tramos (portadas, audio, ZIP) en vez de quedarse en 85 %
  durante la fase más larga.
- Un `Retry-After` con fecha tumbaba el relevamiento entero, con la cuota de
  YouTube ya gastada.
- Deezer reintentaba seis veces, con espera, cualquier error, también el «no
  hay datos», que es permanente: nueve segundos perdidos por consulta. Ahora
  reintenta sólo el límite de tasa y el servicio ocupado, con espera creciente.
  YouTube reintenta también su límite de tasa, que antes cortaba en el acto.
- «(En Vivo)» y «(Live Session)» salían como texto de YouTube arrastrado al
  título, y son parte del título real de una versión. En cambio se escapaban
  «(Audio)», «(Letra)», «[MV]» o «(Videoclip Oficial)», y el título del
  producto no se revisaba.
- El mismo UPC escrito con 12 y con 13 dígitos no se detectaba como duplicado,
  un UPC de todos ceros pasaba como válido, y el ISRC se exportaba con los
  guiones o las minúsculas con que hubiera venido.
- **La columna Label llevaba la línea ℗ entera, licencia incluida**: «Sello
  Chico under exclusive license to Warner». Ahora es el titular, sin la
  licencia, y en las líneas reales con más de un ℗ ya no sale «℗ Distributed
  exclusively by…». La P Line, en cambio, va entera y tal como la publicó la
  distribuidora original; antes se armaba con el año del release, y una
  edición de 2023 con grabaciones de ℗ 2013 salía con un ℗ que no es.
- `Territories` iba fijo en `Worldwide` y `Disc Number` en 1. Los dos eran
  inventar: un catálogo licenciado para una región se abría al mundo, y un
  álbum doble salía entero en el primer disco. Ahora van a completar cuando no
  se saben.
- Dos releases con el mismo título pero lanzados con años de diferencia (el
  original y su edición aniversario) se cruzaban: los temas de la edición nueva
  se quedaban con el UPC y el tracklist del original. Ahora la fecha también
  tiene que coincidir.
- **Un release podía salir partido en dos productos, o dos releases fundidos
  en uno.** Los temas se agrupaban por álbum y año ℗, y ese año es de cada
  grabación: la edición aniversario de un disco, con temas originales de ℗ 2013
  y nuevos de ℗ 2023 lanzados el mismo día, salía como dos productos con el
  mismo UPC. Y el mismo álbum entregado por dos distribuidoras se fundía en uno
  con los tracks duplicados. Ahora el release se arma por álbum, distribuidora y
  fecha de lanzamiento, su año es el del lanzamiento, y si el mismo disco está
  en dos distribuidoras se avisa, que es lo que pasa a mitad de una migración.
  Sobre cincuenta temas reales, los quince productos de antes pasaron a once,
  cada uno un release que existe.
- **La hoja de ingesta nombraba archivos que no estaban en el ZIP.** La columna
  de audio llevaba el nombre del archivo temporal (`tidal_998877.flac`) cuando
  en el ZIP se llamaba `01 - Tema.flac`, y la de portada decía `portada.jpg`
  aunque en inglés el archivo fuera `cover.jpg`, o aunque no se hubieran pedido
  portadas. En una carga masiva la distribuidora cruza cada fila con su archivo
  por ese nombre, y así no encontraba ninguno. Ahora la hoja, las planillas y el
  ZIP sacan el nombre del mismo lugar, con la ruta dentro del paquete, y queda
  vacío lo que no se incluyó.
- **Un single podía quedar con el UPC del álbum, y con su portada.** Deezer
  encuentra la grabación, que está en el single, en el álbum y en cada
  compilado, y el UPC de cualquiera de ellos terminaba en el producto sin mirar
  si era el mismo release. Como la portada se busca primero por UPC, también
  bajaba la tapa del otro. Ahora el UPC se acepta sólo si el álbum de Deezer es
  este release; si no, queda en blanco y la validación dice en cuál lo encontró.
  Sobre cincuenta temas reales, los siete que se descartan son todos de otro
  release (un single contra el álbum, la edición estándar contra la
  aniversario). También se avisa cuando los tracks de un producto traen UPC
  distintos.
- **La fecha de lanzamiento de la hoja de ingesta era la fecha de subida a
  YouTube.** Para el catálogo viejo pueden ser décadas de diferencia: en los
  datos reales, un tema de 2001 figura subido en 2024, y el release migrado
  salía con esa fecha. Cuando faltaba, además, se armaba un 1 de enero con el
  año, que es inventar el dato. Ahora se usa la fecha que publica YouTube en
  cada tema, en «Released on:», y si no está queda en `<<COMPLETAR>>`.
- **Un `@handle` con ñ o con tilde podía relevar el catálogo de otro
  artista.** El navegador copia `youtube.com/@pe%C3%B1a`, codificado, y la app
  se cortaba en el `%`: pedía `@pe`, y si ese canal existía lo relevaba sin
  ningún error. Ahora el link se decodifica antes de leerlo.
- **Una versión en vivo, un remix o un remaster se quedaban con el ISRC de la
  versión de estudio.** Antes de buscar en Deezer, la app le sacaba al título
  justo lo que dice qué versión es: «Tema (En Vivo)» quedaba como «Tema»,
  coincidía al cien por ciento con el de estudio y se quedaba con su código, con
  confianza alta, aunque la versión en vivo estuviera entre los resultados. Ahora
  sólo se limpia lo que es de YouTube, un candidato de otra versión se descarta,
  y si no hay uno de la misma versión el código queda en blanco. Lo mismo con
  las portadas: un álbum en vivo ya no recibe la del de estudio.
- La confianza «media» de un código no miraba la duración, y un resultado de
  Deezer sin artista contaba como del mismo artista.
- **La validación mandaba a «corregir» un ISRC que estaba bien.** La misma
  grabación en el single y en el álbum lleva el mismo ISRC, y así tiene que ser,
  pero la app lo marcaba como error y el paquete dejaba de ser apto. La salida
  obvia era pedir un código nuevo, que parte el historial de la grabación. Ahora
  es un aviso que dice que se conserve. Sigue siendo error si se repite adentro
  de un mismo producto, y pasa a serlo con nombre propio cuando el mismo código
  aparece en dos grabaciones que no parecen la misma, porque casi seguro vino de
  una coincidencia equivocada.
- **Un producto podía pisar los archivos de otro al descomprimir el ZIP.** Dos
  singles con el mismo título y el mismo año sin UPC, dos títulos que recién
  difieren después del carácter sesenta, o títulos en una escritura no latina,
  que al pasar a ASCII quedan todos en «Sin titulo», terminaban en la misma
  carpeta: la portada y la planilla de uno reemplazaban a las del otro. Ahora
  cada producto tiene su carpeta, con `(2)` si hace falta.
- Las rutas adentro del ZIP podían pasar los 260 caracteres que admite Windows,
  y «Extraer todo» fallaba en la máquina de quien recibía la entrega. Ahora hay
  un tope para la ruta entera, que se descuenta del título del tema sin tocar
  nunca el número de track ni la marca de audio lossy.
- El UPC entraba crudo al nombre de la carpeta. Ahora entran sólo sus dígitos, y
  el armado se niega a escribir una entrada que quede fuera de la carpeta del
  paquete.
- **Tres entradas que venían de afuera podían ejecutar algo.**
  - yt-dlp leía un `yt-dlp.conf` de la carpeta desde la que se abría la app,
    que para el ejecutable portable suele ser Descargas, y ahí un `--exec`
    plantado corría lo que dijera. Ahora se llama con `--ignore-config`, en la
    carpeta del trabajo, y nunca buscándolo en la carpeta de trabajo.
  - Un título, un sello o un artista que empezara con `=` entraba como fórmula
    viva a las planillas, y tal cual a la hoja de ingesta. En las planillas
    queda ahora como texto. En la hoja lleva un apóstrofo adelante sólo cuando
    parece una fórmula de verdad, así un disco que se llama «+» o «-Intro-» no
    se toca, y la validación avisa cada vez que cambió un dato.
  - La portada se bajaba de la URL que mandara iTunes, sin mirarla: con
    `file:///` se leía un archivo del disco, que terminaba en el ZIP. Ahora sólo
    se baja del CDN de Apple, por HTTPS y con un tope de tamaño.
- La variante completa trae yt-dlp adentro, pero la descarga lo buscaba como
  programa aparte: en una máquina sin yt-dlp instalado decía que podía bajar el
  audio de referencia y fallaba al intentarlo. Ahora usa el que trae.

### Cambiado
- **Las notas de cada release arrancan por cuál bajar**, y después dicen qué
  cambió para quien usa la app. Lo interno (tests, CI, tipos) va en la sección
  «Para quien desarrolla» del CHANGELOG, y en el release queda plegado al final.
  En la 1.1.0 eran cien líneas sobre pytest y pyright antes de decir qué bajar.
- **El README empieza por lo que importa a quien migra**: la promesa en una
  línea (cambiar de distribuidora sin perder los códigos), para quién es y para
  quién no, y la descarga directa de cada sistema, que antes era una línea hacia
  una página con treinta archivos. Suma preguntas frecuentes (¿funciona con mi
  distribuidora?, ¿necesito saber programar?, ¿es legal?) y separa con una
  línea la parte para quien quiere tocar el código.
- El piso de yt-dlp sube a 2024.07.01, que deja afuera las versiones con
  CVE-2024-38519.
- **La clave de YouTube viaja en una cabecera, no en la URL.** Hoy ningún
  mensaje de error la mostraba, pero cualquiera que citara la URL la habría
  llevado con él: ahora no está ahí. Se verificó contra la API real que Google
  la acepta igual y que una clave mala sigue dando el mismo aviso.
- La carpeta y el archivo de la config, donde vive la clave que carga el
  usuario, se crean cerrados desde el primer momento. Antes el permiso se
  cerraba después, y en un sistema con varios usuarios quedaba una ventana en
  que los demás la podían leer.
- **El servidor local suma cuatro refuerzos, sin tocar las tres defensas.**
  Ninguna otra página puede meter la app en un iframe (`frame-ancestors`,
  `X-Frame-Options`, COOP y CORP). Un pedido que el navegador marca como hecho
  por otro sitio se rechaza aunque traiga el token. El cuerpo de un pedido se
  interpreta recién después de pasar Host, token y origen, y uno que no se puede
  leer entero cierra la conexión en vez de contaminar el pedido siguiente. Y un
  token con caracteres raros o una ruta en otra unidad de disco dan 403 y 404,
  no un error interno con el texto de la excepción.
- **La validación deja de prometer lo que no mira.** «Sin errores: el catálogo
  no tiene problemas que causen rechazo» se leía como «listo para cargar», con
  los campos sin completar, el audio lossy y los códigos dudosos adentro. Ahora
  dice «sin errores de formato», aclara que no es una garantía, y el informe
  lista siempre lo que no mira (texto y logos en la portada, lo que tiene
  registrado tu distribuidora actual, las reglas de cada una). Suma avisos para
  los ISRC de confianza media, el audio que es sólo de referencia, las portadas
  en gris, con paleta o transparentes, y los campos que ninguna fuente pública
  trae. El LEEME y el README dicen «suelen rechazar» en vez de «rechazan».

### Para quien desarrolla
- **Fuera lo que no decía nada**: `cobertura_metadata` y `topic_sugerido`
  eran constantes desde que el relevamiento filtra lo que no es lanzamiento, y
  la rama de la interfaz que los usaba (con su botón y cuatro textos) no se
  ejecutaba nunca; `units` no lo leía nadie y subestimaba el costo. Los dobles
  de prueba que inventaban esos valores ya no los traen.
- **DESIGN.md y los tokens dicen lo mismo**: la cabecera deja el desenfoque que
  §9 prohíbe, se fueron siete tokens sin uso, y el «peor par de texto», que
  estaba escrito con tres números distintos, es uno solo (4,7 en oscuro y 5,1
  en claro, un estado sobre su relleno) y un test lo mide sobre `colors.css`.
- `pyproject.toml` con descripción en los dos idiomas, `keywords` y las claves
  de URL que reconocen las herramientas, y sin los comentarios del repo de
  antes (la versión «en `app/server.py`», un ignore para un archivo que ya no
  está en la raíz).
- **Modelo de amenazas escrito**, en [docs/AMENAZAS.md](docs/AMENAZAS.md) y en
  inglés: qué protege la app, de quién, con qué defensa y qué test la cubre, y
  qué queda afuera a propósito (por ejemplo, que un proceso local del mismo
  usuario puede leer el token, igual que la clave).
- **La interfaz tiene tests**, en `tests/js/`, que cargan el `app.js` real sin
  navegador y comprueban, entre otras cosas, que un título de YouTube con HTML
  adentro llegue escapado a la pantalla. Es la única barrera entre lo que viene
  de afuera y lo que se dibuja, y hasta ahora no la probaba nada. Corren con
  `node --test`, y `pytest` los lanza solo si Node está instalado.
- **Tests contra respuestas reales de la YouTube Data API.** Hasta ahora sólo
  Deezer e iTunes tenían respuestas grabadas; el relevamiento completo, la
  paginación y la lectura de las descripciones no se probaban contra lo que
  YouTube devuelve de verdad, y ahí estaban varios de los errores que este
  ciclo encontró. `build/grabar_fixtures.py --youtube` las graba con la clave
  en una cabecera y se niega a guardar si la encuentra en algún lado. Se suman
  tests de las rutas del servidor que no tenían, y el umbral de cobertura sube
  de 58 % a 75 %, con 78 % medido.
- `docs/AUDITORIA-2.md` y `docs/MEJORAS-2.md`, el diagnóstico del segundo ciclo
  de mejoras y el backlog que sale de él. Esta vez el repositorio se miró con
  seis miradas distintas (industria musical, distribución y metadata, software,
  interfaz, seguridad y difusión), cada una por separado, con la rúbrica de
  `docs/BRIEF-AUTOMEJORA.md`.
- **SECURITY.md y el servidor nombran las tres defensas.** Decían «dos» y no
  mencionaban la CSP, así que quien quisiera reportar no sabía que saltearla
  entra en el alcance.
- **La lista de hosts válidos ya no trae una entrada que nunca coincide** (un
  `::1` sin corchetes), y un test verifica que cada una se pueda alcanzar.
- **El contrato del relevamiento decía mal dos cosas**: las distribuidoras
  estaban declaradas como números cuando una trae el título del track más
  visto, y las estadísticas de códigos como «cualquier cosa». Los dobles de
  prueba copiaban esa forma incompleta y ahora tienen la real.
- «Un trabajo a la vez» se chequeaba y se registraba por separado, y dos pedidos
  simultáneos (un doble clic lento, dos ventanas) podían pasar los dos. Ahora
  las dos cosas van juntas.
- Las capturas del README mostraban la versión 1.0.1 en el pie, y la app ya era
  la 1.1.0. Se regeneraron en los dos idiomas, y sus textos de ejemplo salen
  ahora del mismo catálogo que usa la app: escritos a mano se habían desviado
  (un mensaje sin tildes, y una falta de UPC mostrada como error cuando la
  validación la da como aviso).
- `build/capturas.py` terminaba a veces con `Fatal Python error` aunque las
  capturas salieran bien. Un hilo del servidor seguía escribiendo el corte de
  conexión de Chrome mientras el programa se cerraba. Ahora el servidor de la
  app calla los cortes del cliente, que no son un error suyo, y el script espera
  a sus hilos antes de salir.
- **pyright prende 34 reglas de `strict`**, las que el código ya cumple, para
  que desde ahora no se puedan romper sin que el CI lo diga. Para llegar hubo
  que darles contrato a las funciones que devolvían diccionarios sueltos (la
  portada de Apple, las opciones de filtro, el paquete listo, el resultado de
  `migrar()`, las estadísticas del cruce con Deezer), y un test por cada una
  compara lo que devuelve de verdad contra su contrato. `pyproject.toml` dice
  qué reglas faltan y por qué.
- **El CI da permiso de escritura sólo al paso que publica el release.**
  Antes lo tenían también los ocho jobs que compilan, que instalan paquetes de
  PyPI: uno comprometido habría recibido un token con permiso para escribir en
  el repositorio. Y las acciones de GitHub van fijadas por el SHA del commit en
  vez de por un tag, que quien controla la acción puede mover.
- Dependabot propone las actualizaciones de pip y de las acciones, y un job
  nuevo corre `pip-audit` sobre todo lo que viaja adentro de los ejecutables.
  PyInstaller y pyright tienen versión fija, todos los jobs tienen timeout, y
  los tests del build corren sin la clave de YouTube en el entorno.
- El control de claves revisa también la historia entera de git, en el CI:
  una clave que entró en un commit y salió en el siguiente ya no está en
  ningún archivo, pero sigue en cada clon.

## [1.1.0] — 2026-09-22

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

[1.1.0]: https://github.com/joacogoliver-debug/catalog-migrator/releases/tag/v1.1.0
[1.0.2]: https://github.com/joacogoliver-debug/catalog-migrator/releases/tag/v1.0.2
[1.0.1]: https://github.com/joacogoliver-debug/catalog-migrator/releases/tag/v1.0.1
[1.0.0]: https://github.com/joacogoliver-debug/catalog-migrator/releases/tag/v1.0.0
