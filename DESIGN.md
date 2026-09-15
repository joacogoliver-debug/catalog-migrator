# Migrador de Catálogos, mundo visual

Decisiones durables. Lo que el producto es y no cambia está en `PRODUCT.md`.

De la marca queda lo que importa: **grafito, hueso y la rampa teal**. Todo lo
demás (tipografía, forma, densidad, componentes) se decide acá.

La dirección salió de una referencia concreta que trajo el cliente: una pieza de
su estudio de diseño, oscura, de negro pleno, tarjetas de hairline, etiquetas en
mono ancladas al borde y estados como relleno teñido. Lo que sigue es esa
gramática traducida a una herramienta de inventario, que es algo bastante
distinto de aquella pieza.

---

## 1. El concepto: el grafito es la superficie

La app no dibuja cajas grises sobre un fondo gris. El lienzo es **grafito
bajado casi a negro**, y las superficies de trabajo **son el grafito de la
marca**. La tarjeta principal de cada pantalla es literalmente el color de la
marca, no un gris prestado de ningún sistema.

Eso deja una consecuencia que ordena el resto: **si las superficies están tan
cerca, no se pueden separar por escalón de gris.** Se separan por un borde de un
píxel a muy baja opacidad. Es lo que permite que el negro siga siendo negro y
que la pantalla no se llene de rectángulos grises de distinto tono.

**Tres gestos lo sostienen, y ninguno es decorativo.**

**El borde.** Cada bloque es una tarjeta de hairline con una banda de título
arriba. La profundidad la da el borde, no un desenfoque: no hay sombras en
ninguna parte de la app.

**La etiqueta anclada.** Todo lo que rotula en vez de leerse va en mono,
versalitas y tracking ancho, apoyado en el borde de la pantalla: el pie, el
resumen de la barra de acción, las cabeceras de tabla, los rótulos de campo.
Es la voz de la app para lo que no es contenido.

**El dígito.** Todo lo que se cuenta o se compara va en mono con `tabular-nums`:
ISRC, UPC, años, duraciones, cantidades. Son la mitad de la pantalla, y
tratarlos como texto corrido era el error original.

**La trama.** Dos líneas de 1 px a muy baja opacidad sobre el lienzo. No está
para simular un plano: está para que el vacío tenga escala cuando una vista
tiene poco contenido.

## 2. Luz

**Oscuro por defecto.** Sale de la escena de uso, no de la categoría: esta app
se abre de noche para hacer trabajo de inventario. El claro existe completo y se
elige desde la cabecera.

El claro **no** sale de la referencia, que es sólo oscura. Se construye con la
misma gramática, invertida: el lienzo es el hueso bajado, las tarjetas son el
hueso, y los bordes son grafito a baja opacidad.

## 3. Color

| Rol | Valor |
|---|---|
| Grafito | `#141414` |
| Hueso | `#F5F2ED` |
| Teal | `#387F7E`, rampa 50 a 900 |
| Neutrales | grises de temperatura cálida, matiz 82 |
| Semánticos | negativo `#E3645E`, atención `#E1A536`, positivo `#60AC6D` (en claro bajan a `#A82E2F`, `#7E5500`, `#2C6539`) |

Tres reglas de uso.

**El teal es el único acento.** Marca lo accionable y lo que está en curso. Su
lugar más visible es el círculo del paso activo en la cabecera, que es lo que se
ve en toda pantalla.

**El primario no es de color.** El botón principal es hueso pleno sobre
grafito. Es lo más claro de la pantalla y por eso es lo primero que se ve, sin
necesidad de pintarlo.

**Los estados son relleno teñido, no borde.** Un badge es el propio semántico
mezclado al 13% en la superficie, con el texto saturado del mismo tono encima.
Ni borde de color, ni relleno pastel: la mancha plana es el atajo que hace que
todo se vea igual.

**Todo se midió.** El peor par de texto sobre superficie da 4.7 en oscuro y 4.9
en claro, los dos por encima del mínimo AA. Los neutrales 500 quedaron afuera de
los roles de texto porque daban 3.6 y 3.7.

## 4. Tipografía

Dos familias, no tres.

**Public Sans** para interfaz, cuerpo y titulares. **DM Mono** para datos,
códigos y las etiquetas ancladas al borde.

El titular es **grande y liviano**: 44 px en peso 300. Ese contraste contra una
interfaz de 14 en peso 400 es lo que arma la jerarquía. No hace falta gritar con
negritas si la escala ya lo dice.

| Rol | Tamaño | Familia |
|---|---|---|
| Título de vista | 44 px | Public Sans 300 |
| Título de sección | 15 px | Public Sans 500 |
| Cuerpo e interfaz | 14 px | Public Sans 400 |
| Dato y código | 13 px | DM Mono |
| Badge | 11 px | Public Sans 500 |
| Etiqueta anclada | 10 px | DM Mono, versalitas, tracking 0.14em |

El tracking negativo es sólo del titular. Las etiquetas en mono necesitan lo
contrario, y bastante: es lo que las convierte en una marca de borde y no en
texto chico.

Las dos familias son SIL Open Font License 1.1 y viajan adentro del ejecutable,
56 KB en total. El subconjunto latin cubre el español completo; el símbolo ℗,
que aparece en un mensaje de validación, lo resuelve la fuente del sistema.

## 5. Forma

Una sola familia de radios, chicos: **6 px** en badges y marcas, **8 px** en
controles, **12 px** en tarjetas. La app no flota sobre nada, así que no hay
radio de contenedor exterior.

**Cero sombras.** La separación la hace el borde de un píxel. La sombra queda
reservada para lo que flote de verdad, que hoy no es nada.

**Cero borde lateral de color.** El acento de una alerta es su relleno teñido y
su texto.

## 6. Superficies

| Nivel | Oscuro | Claro |
|---|---|---|
| Lienzo | `#0A0A09` | `#E8E4DC` |
| Tarjeta | `#141414` (grafito) | `#F5F2ED` (hueso) |
| Banda de título, hover | `#1E1D1C` | `#EDEAE3` |
| Borde | hueso al 10% | grafito al 12% |
| Borde suave | hueso al 5% | grafito al 6% |

## 7. Movimiento

**Un solo momento con autoría**: el trabajo largo. Tres puntos del logo latiendo
en secuencia mientras corre, las líneas nuevas del log entrando con un fade, y
al terminar el latido se apaga, aparece un tilde y medio segundo después cambia
la vista. Es lo que separa "terminó" de "la pantalla cambió de golpe".

Lo demás es respuesta inmediata al puntero o al teclado, de 100 ms: el tilde de
la casilla que se dibuja, el detalle que se despliega, la entrada de vista al
cambiar de paso. `prefers-reduced-motion` apaga todo.

## 8. Las superficies que no dibujé

Se tematizan, porque vienen con valores que no son de ningún sistema y se notan:
selección de texto, cursor de escritura, barras de scroll, anillo de foco,
`accent-color` de los controles nativos y el subrayado de los links.

## 9. Qué está prohibido en este mundo

No por dogma, sino porque ya lo probamos y es lo que hacía que la app se viera
igual a cualquier otra.

- Sombras para separar bloques. Lo hace el borde.
- Escalones de gris como estructura. Las superficies están casi juntas a propósito.
- Relleno pastel claro en badges, y badges de borde de color.
- La plantilla de métrica: número enorme, etiqueta chica, fila de stats.
- Versalitas como estructura de página. Van sólo en lo que rotula.
- Emojis como iconos.
- Degradados, vidrio esmerilado y brillos de color.
- Negro puro `#000000`: el lienzo es grafito bajado, y es cálido.

## 10. Lo que no se pudo traer de la referencia

Vale dejarlo escrito, porque va a volver a preguntarse.

La referencia es una **landing de marketing**: renders 3D isométricos, scroll que
fija secciones, titulares de 120 px, planes de precios. Nada de eso tiene dónde
entrar en una herramienta que muestra 46 tracks en una tabla y vive en una
ventana de escritorio con chrome fijo.

Lo que sí entró: el negro pleno con la trama, las tarjetas de hairline, el
índice numerado en círculos (que calzó exacto con los cuatro pasos), las
etiquetas mono ancladas al borde, la escala grande con peso liviano, y los chips
de relleno oscuro con texto saturado.
