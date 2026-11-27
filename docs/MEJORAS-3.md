# Registro de mejoras, ciclo 3

Los ciclos 1 y 2 (`MEJORAS.md`, `MEJORAS-2.md`) dejaron la app sólida: tests,
tipos, seguridad, empaquetado, y un cruce con Deezer ajustado contra siete
catálogos reales. Éste parte de otra pregunta: **qué no puede hacer todavía
quien migra un catálogo con esta app**. Está escrito para que una próxima
sesión retome sin repetir lo medido ni volver a discutir lo decidido.

Rama `automejora/ciclo-3`, sin push y sin tocar la versión: todo va en «Sin
publicar» del CHANGELOG.

## De dónde se partió

| | Al empezar |
|---|---|
| Tests de Python | 1.018, más 45 de la interfaz |
| Cobertura | 84,95 % |
| ruff, pyright | en cero |

Y tres huecos del producto, que ningún ciclo anterior había mirado porque los
dos se ocuparon de que lo que había anduviera bien:

1. **Todos los códigos se veían igual.** `match` decía «alta» para el ISRC que
   sólo salió de una búsqueda por texto y para el que además figura con ese
   código en el tracklist de su release.
2. **La app era de sólo lectura.** Lo que el usuario sabe (el código que le
   pasó su distribuidora, el género de su disco) no tenía dónde entrar: se
   tipeaba en un Excel, después de armado el paquete.
3. **El recorrido terminaba antes de tiempo.** «Pedile los códigos a tu
   distribuidora» era una frase; la respuesta no se podía cargar. Y después de
   migrar no había cómo comprobar que los códigos se habían conservado.

## El banco de pruebas

Para medir y no opinar se grabó un catálogo real: el listado de YouTube del
canal Topic de Daft Punk (221 temas, 506 unidades de cuota, una sola vez) y lo
que contestó Deezer. Con eso el relevamiento se repite sin red y da siempre lo
mismo, que es lo que deja comparar el antes y el después de un cambio del
motor. **Vive fuera del repositorio** (son datos de un catálogo real) y hay que
volver a grabarlo para usarlo: el script hace `relevar_core._listar_canal` una
vez, guarda el resultado, y reemplaza `relevar_core._http_json` por una función
que graba y repite por URL, sin guardar las respuestas de «límite excedido».

Línea de base medida con él:

| | |
|---|---|
| ISRC | 219 de 221 temas |
| Productos con UPC | 34 de 42 |
| Tiempo del cruce con Deezer, en vivo | 52 s, 422 pedidos, **28 rechazados por exceso** |
| Pedidos repetidos | 38 de 422 |

## Lo que se hizo

| id | ítem | qué se verificó |
|---|---|---|
| C01 | **Ritmo y memoria de los pedidos a Deezer** (`relevar_core._Ritmo`, `_Memo`, `sesion_deezer`) | La app se pasaba del límite de Deezer (50 cada 5 s) y los reintentos con espera creciente eran la causa de buena parte de los «Deezer no respondió». Ventana deslizante de 45 cada 5 s, y memoria por relevamiento de lo ya contestado. Tests con reloj de mentira. Medido en vivo sobre el banco: de 52 s, 422 pedidos y 28 rechazos a **47 s, 366 pedidos y ningún rechazo**. La salida, antes y después: idéntica. |
| C02 | **Evidencia por código** (`evidencia.py`) | Tres niveles que salen del relevamiento (confirmado, inferido, dudoso) y dos del usuario (manual, importado). Sobre el banco: 205 ISRC confirmados y 14 inferidos, **los catorce remixes sueltos**; UPC, 23 confirmados y 11 inferidos. En la tabla, la planilla, la hoja de ingesta y la validación. |
| C03 | **Candidatos a la vista** (`completitud.completar_isrc`) | Cuando había dos grabaciones posibles el tema quedaba sin código y nada decía que había candidatos. Ahora quedan anotados y la interfaz los ofrece. |
| C04 | **Ediciones a mano** (`ediciones.py`) | Un ISRC o un UPC, validados antes de aceptarse, marcados y con deshacer que devuelve también el nivel. Los seis campos a completar, en lote. |
| C05 | **Importar la planilla de la distribuidora** (`importar.py`) | Lee xlsx y CSV sin pedir formato. Concilia y separa confirma / completa / conflicto / ambiguo; los dos últimos nunca se aplican solos. Probado en la app real con una planilla armada sobre el banco. |
| C06 | **Hoja de pedido** (`paquete.hoja_pedido_bytes`) | Las columnas a completar van vacías a propósito: un test comprueba que la hoja devuelta sin tocar no confirma nada, y otro, en los dos idiomas, que completada vuelve a entrar. |
| C07 | **Relevamiento guardado** (`instantanea.py`) | Va en cada paquete. Se reabre sin cuota. Se reconstruye campo por campo, porque puede venir de otra persona. |
| C08 | **Verificación post-migración** (`instantanea.comparar`) | Seis estados por release. Probado en la app real con un «antes» armado sobre el banco. |

| C09 | **Tests de propiedades** (`tests/test_propiedades.py`, Hypothesis sólo en desarrollo) | 21 reglas sobre nombres del ZIP, códigos, la planilla importada y el relevamiento guardado. **Encontraron tres fallas**: un corchete suelto en el campo del link terminaba en «Invalid IPv6 URL» (estaba desde antes del ciclo), y un retorno de carro suelto o un byte nulo tumbaban el lector de CSV nuevo. Con 2.500 ejemplos por regla no aparece nada más. |

| C10 | **El ISRC de cada tema es el de su release** (`completitud.alinear_con_el_release`) | El hallazgo más serio del ciclo, y salió de medir un segundo catálogo. Un disco estaba dos veces en Deezer, entregado por dos sellos con códigos distintos; el cruce elegía bien cuál era el del canal y le dejaba a sus temas el ISRC del otro. **43 temas de 268** salían con el UPC de un release y el ISRC de otro. Ahora toman el del tracklist de su release, el otro queda anotado y la validación lo dice. Sobre el primer catálogo no cambia nada (no tenía ningún caso). |

Al cerrar: 1.173 tests de Python y 53 de la interfaz, ruff y pyright en cero.

**Un segundo catálogo, para no ajustar la regla mirando uno solo.** Se grabó
además el de un artista regional (268 temas, 707 unidades): 43 s en vivo, 357
pedidos y ningún rechazo de Deezer. ISRC, antes de C10: 192 confirmados, 49
inferidos y 27 sin código; los 28 UPC, confirmados. De esos 49 inferidos, 43
estaban ubicados en el tracklist de su release con OTRO código: no eran
códigos sin respaldo, eran códigos de otra entrega (C10). Después: 235
confirmados y 6 inferidos. «Confirmado» se define por el tracklist del release
verificado y no por «dos caminos», que es cierto para la mayoría y no para
todos.

Esto es también lo que justifica el nivel de evidencia: los 43 estaban
marcados «inferido» antes de saber por qué. La marca decía «miralos», y al
mirarlos apareció el error.

**Los ocho productos sin UPC del banco se miraron uno por uno** contra lo que
Deezer contestó: son singles que YouTube arma con una combinación de temas que
en Deezer no existe como release («Technologic» con el remix de Digitalism,
cuando el single de Deezer trae el de Peaches). Que queden en blanco es lo
correcto; no hay cobertura para ganar ahí sin inventar.

**El binario empaquetado.** `python build/build.py` (variante esencial, en
Windows) pasa, y al ejecutable se le pidió por HTTP todo lo nuevo: abrir un
relevamiento guardado, editar un código, rechazar uno inválido, importar una
planilla y validar. Los de macOS y Linux los compila y arranca el CI; acá no se
pudieron probar.

## Decisiones, y por qué

**No se dio vuelta el cruce para buscar primero en la discografía.** Se midió:
de 384 pedidos distintos, 225 son la búsqueda de cada tema, y bajar la
discografía entera primero los ahorraría casi todos. No se hizo. Esa búsqueda
no es sólo un costo: es el camino independiente contra el que se compara el
tracklist del release, y de esa independencia sale el nivel «confirmado». Con
el ritmo que impone Deezer, el piso del relevamiento es de unos 40 s para 220
temas, y eso queda dicho acá para que nadie lo vuelva a buscar por ese lado.

**El UPC que coincide sólo por el título no es «confirmado» aunque casi siempre
esté bien.** La primera regla marcaba inferidos a 16 de 34, incluido
«Discovery», y era gritar de más. Se confirma si además coincide la fecha, la
lista exacta, o si todos los temas del producto están en ese álbum y dos o más
con el ISRC que la búsqueda encontró por su cuenta. Quedan inferidos los
singles de un solo tema sin fecha, que son el caso de riesgo de verdad.

**Los pesos de la conciliación son constantes a la vista, no un modelo.** La
idea de sumar lo que aporta cada campo viene del enlace probabilístico de
registros (Fellegi y Sunter, lo que implementa splink) y de la distancia de
beets. No se estiman probabilidades: con unos cientos de filas no hay de dónde,
y un peso que se puede leer es un peso que se puede discutir.

**Ninguna dependencia nueva.** RapidFuzz acelera comparaciones que acá no son
el cuello de botella (el relevamiento entero, sin red, tarda 5 s). pandera
valida dataframes y no hay ninguno. La conciliación no necesita asignación
óptima: una fila de la planilla puede corresponder a varios temas del catálogo
(la misma grabación en el single y en el álbum), así que no es un problema de
uno a uno.

**El archivo viaja adentro del JSON, en base64, y no como un upload.** Así pasa
por las tres defensas del servidor sin una ruta que las saltee.

**Editar no recalcula el nivel del UPC.** Depende de los tracklists de Deezer,
que después del relevamiento ya no están; recalcularlo sin ellos bajaba a
«inferido» un UPC confirmado. Se encontró con un test, antes de llegar a la
interfaz.

## Lo que queda

- **MusicBrainz como segunda fuente.** Se puede listar un artista con sus ISRC
  en pocos pedidos (`/ws/2/recording?artist=…&inc=isrcs`). Falta medir la
  cobertura en catálogos de la región antes de sumarlo: si es baja, es un paso
  lento que no confirma nada.
- **Plantillas de hoja de ingesta por distribuidora.** Que el usuario suba la
  planilla que pide su distribuidora nueva y la app la llene. Es la respuesta
  de fondo a «¿funciona con mi distribuidora?».
- **Editar más que códigos.** El título, la fecha, el sello y el orden siguen
  siendo de sólo lectura.
- **Guardar el relevamiento sin armar el paquete.** Hoy lo cargado a mano
  queda a salvo recién cuando se arma un paquete (que lo trae adentro). Un
  botón que baje sólo ese archivo pide resolver la descarga en la ventana
  nativa de cada sistema, que ya dio trabajo con el ZIP.
- **Lo que no se pudo verificar acá:** el selector de archivos con un clic
  humano en la ventana nativa de cada sistema (se probó entregándole el archivo
  a la interfaz por código), y la comparación contra una migración de verdad.
