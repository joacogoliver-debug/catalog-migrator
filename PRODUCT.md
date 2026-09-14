# Migrador de Catálogos — verdad del producto

Qué es, para quién, y qué tiene que ser cierto pase lo que pase con el diseño.
Este archivo no decide nada visual. Eso vive en `DESIGN.md`.

## Qué hace

Toma el link del canal de YouTube de un artista y devuelve lo que hace falta para
llevar ese catálogo a otra distribuidora: los códigos **ISRC** y **UPC**, las
portadas en la mayor resolución disponible, una **hoja de ingesta** en CSV y una
**validación pre-entrega** que separa lo que va a ser rechazado de lo que sólo
conviene mirar.

Es una app de escritorio. Corre entera en la máquina de quien la usa, levanta un
servidor local en `127.0.0.1` y no tiene cuentas, registro ni backend propio.

## Para quién

Alguien que administra catálogo musical: un sello chico, un manager, una
distribuidora, o el propio artista. Sabe qué es un ISRC y por qué perderlo
duele. No es un usuario general y no hay que explicarle el dominio.

## La escena de uso real

Una persona sola, frente a la computadora, haciendo trabajo de inventario que
normalmente haría en una planilla. Suele ser de noche, fuera del horario en que
se hace el trabajo "de verdad", y la sesión dura entre veinte minutos y dos
horas. Rara vez la abre para una sola cosa: cuando la abre, migra un catálogo
entero.

De ahí salen tres consecuencias que el diseño no puede ignorar. **Oscuro por
defecto**, porque esa es la luz de la escena. **Densidad antes que respiro**,
porque quien la usa está comparando filas, no leyendo. Y **el estado tiene que
estar siempre a la vista**, porque los trabajos tardan minutos y la ventana se
deja abierta mientras se hace otra cosa.

## El recorrido

Cuatro pasos, y el orden no es negociable porque cada uno necesita el anterior.

1. **Pegar el link** del canal. Idealmente el canal Topic.
2. **Elegir productos.** Acá se pasa la mayor parte del tiempo. El catálogo
   aparece agrupado en productos (álbum, EP, single), con lo que le falta a cada
   uno marcado. Se puede filtrar por año, por distribuidora, o buscar.
3. **Elegir qué bajar.** Planilla, portadas, audios.
4. **Descargar** un ZIP con una carpeta por producto, más el informe de
   validación.

## Los estados que importan

No son casos borde: son la mitad del producto.

- **Trabajo largo en curso.** Relevar tarda de 20 segundos a varios minutos, y
  armar el paquete con audio puede tardar mucho más. Hay progreso, hay un log de
  lo que está pasando, y se puede cancelar.
- **Falta un dato.** Un producto sin UPC, un track sin ISRC, un orden de tracks
  estimado. La app tiene que mostrarlo por producto y no esconderlo en un
  resumen.
- **El cupo de la API se agotó.** Pasa, y tiene solución concreta: cargar una
  clave propia. El error tiene que ofrecerla, no sólo informarla.
- **El artista no está en la fuente.** Si Deezer no lo tiene, no hay códigos, y
  eso no es una falla de la app. Hay que decirlo con esas palabras.
- **Vacío por filtro.** Se filtró de más y no queda nada.
- **Primera vez.** Términos de uso, y la clave de la API si esta copia no trae
  una.

## Lo que no se toca

- **No inventa metadata.** Lo que no sale de una fuente pública queda marcado
  `<<COMPLETAR>>`. Un campo vacío es información; uno rellenado a ojo es una
  mentira que después alguien entrega.
- **Se reporta lo medido, no lo pedido.** Las portadas se piden en 3000×3000 y
  se informa el tamaño que Apple realmente devolvió.
- **El orden de tracks es estimado** y se dice en cada producto donde lo es.
- **La validación es una ayuda, no un certificado.** Nunca se presenta como
  garantía de que la distribuidora lo va a aceptar.
- El módulo de audio es opcional, viene apagado y necesita la cuenta paga propia
  de quien lo usa.

## Cómo se habla

Español rioplatense, voseo, directo. Los errores dicen qué pasó y qué hacer, no
piden disculpas. Las cosas se llaman como las llama quien trabaja en esto: es
"distribuidora" y "sello", no "vendor" y "label".

## Restricciones técnicas

JavaScript sin frameworks ni build step, y CSS sin preprocesador. La app se
empaqueta como un solo ejecutable, así que no puede depender de ninguna descarga
en tiempo de ejecución: las tipografías viajan adentro y la página declara una
CSP que no le permite pedir nada afuera. Cualquier decisión de diseño que
necesite un CDN está descartada de entrada.
