# Migrador de Catálogos — mundo visual

Decisiones durables. Lo que el producto es y no cambia está en `PRODUCT.md`.

Este documento reemplaza al sistema anterior. De aquel queda **la paleta y nada
más**: grafito, hueso y la rampa teal. Todo lo demás —tipografía, forma,
componentes, densidad— se decide acá.

---

## 1. El concepto: instrumento, no documento

La versión anterior trataba a la app como un documento: bloques blandos, mucho
aire, todo adentro de una tarjeta redondeada. Eso es lo que la volvía
intercambiable con cualquier otra cosa.

Esta versión la trata como **un instrumento de medición**. Quien la usa está
inventariando: cuenta, compara, marca lo que falta. El diseño lo dice con tres
gestos, y ninguno es decorativo.

**La regla.** Una línea de 1 px separa las secciones, y la etiqueta de la
sección se apoya sobre la regla en mono, como en un plano. Reemplaza a la
tarjeta: no hay contenedor, hay estructura.

**La escala.** El borde izquierdo de los bloques de datos lleva marcas de
registro numeradas en mono, como el eje de un gráfico o el margen de una regla.
Sirven para dos cosas a la vez: son el número de fila y son el rasgo de la
marca.

**El dígito.** Todo lo que se cuenta o se compara va en Geist Mono con
`tabular-nums`. No como disfraz de "técnico", sino porque son datos: ISRC, UPC,
años, duraciones, cantidades. Son la mitad de la pantalla, y tratarlos como
texto corrido es el error original.

Lo que **no** hacemos, aunque las referencias lo tengan: no hay grilla de fondo
de dos ejes ni trama diagonal. Eso pide un plano o un mapa abajo, y acá abajo
hay una tabla. Sería costume.

## 2. Luz

**Oscuro por defecto.** Sale de la escena de uso, no de la categoría: esta app
se abre de noche para hacer trabajo de inventario. El claro existe completo y se
elige desde la cabecera, pero el oscuro es el que se diseña primero y el que se
ve en las capturas.

## 3. Color

La paleta heredada, sin agregados.

| Rol | Valor |
|---|---|
| Grafito | `#141414` |
| Hueso | `#F5F2ED` |
| Teal | `#387F7E`, rampa 50 a 900 |
| Neutrales | grises de temperatura cálida, matiz 82 |
| Semánticos | negativo `#B63132`, atención `#B77600`, positivo `#357A43` |

Dos reglas de uso.

**El teal es el único acento.** Marca lo accionable y lo seleccionado. Nada se
pinta de teal por quedar bien.

**Los semánticos son borde y texto, no relleno.** Un badge es un borde de 1 px
con el texto del mismo tono, sobre el fondo de la superficie. El relleno pastel
—`negative-soft` y compañía— queda sólo para el bloque de alerta, al 12% de
opacidad, que es lo suficiente para teñir sin convertirse en una mancha.

## 4. Tipografía

Dos familias, no tres.

**Archivo** para titulares. Pesos 600 y 700, tracking `-0.03em` de 30 px para
arriba.

**Geist Mono** para datos, etiquetas de sección, códigos y cifras.

**Geist** sigue siendo la sans de interfaz y cuerpo. La familia display anterior
no cambia; lo que cambia es cuánto se apoya la interfaz en el mono, que pasa de
ser un detalle a ser estructural.

La escala se aprieta respecto de la anterior: el cuerpo de interfaz baja a 13 px
y las tablas a 13, porque la densidad es el punto. El titular de vista sube, para
que el contraste entre lo que se lee una vez y lo que se escanea mil sea
evidente.

| Rol | Tamaño | Familia |
|---|---|---|
| Título de vista | 40 px | Archivo 700 |
| Sección | 22 px | Archivo 600 |
| Etiqueta de sección sobre la regla | 11 px | Geist Mono 500, versalitas |
| Cuerpo | 14 px | Geist |
| Interfaz y tabla | 13 px | Geist |
| Dato y código | 13 px | Geist Mono, tabular |
| Métrica | 28 px | Geist Mono 500 |
| Micro | 11 px | Geist Mono |

Medida de lectura de 65 a 75 caracteres en texto corrido. Fuera de eso, el ancho
lo manda la tabla.

## 5. Forma

Radios bajos, porque el mundo es técnico: **2 px** en badges y marcas, **4 px**
en controles, **6 px** en paneles. Nada de píldoras salvo en el punto de estado.

**Una sola declaración de elevación por elemento.** O borde, o cambio de
superficie. Nunca las dos, y sombra sólo en lo que flota de verdad: menús,
modales y avisos.

**Cero borde lateral de color.** El acento de una alerta es su icono y su texto,
más un teñido del 12%. Una barra de color de 3 px al costado es el atajo que
usan todos.

## 6. Superficies

Cuatro niveles en oscuro, muy cerca entre sí. La diferencia entre uno y otro es
de dos o tres puntos de luminosidad, lo justo para que se lean como capas y no
como bloques distintos.

| Nivel | Oscuro | Claro |
|---|---|---|
| Fondo | `#101212` | `#F5F2ED` |
| Panel | `#161919` | `#EDEBE6` |
| Fila alterna / cabecera de tabla | `#1B1F1F` | `#E7E4DE` |
| Flotante | `#232828` | `#FDFCFA` |

## 7. Movimiento

**Un solo momento con autoría**: la barra de progreso de un trabajo largo, que
es lo único que de verdad merece atención mientras pasa. Ahí el movimiento
informa.

Todo lo demás es respuesta inmediata al puntero o al teclado, de 100 ms, sin
entrada escalonada y sin animación de aparición por sección. `prefers-reduced-
motion` apaga todo menos los cambios de opacidad.

## 8. Las superficies que no dibujé

Se tematizan, porque vienen con valores que no son de ningún sistema y se notan:
selección de texto, cursor de escritura, barras de scroll, anillo de foco,
`accent-color` de los controles nativos y el subrayado de los links.

## 9. Qué está prohibido en este mundo

No por dogma, sino porque ya lo probamos y es lo que hacía que la app se viera
igual a cualquier otra.

- Tarjetas del mismo tamaño como estructura de página, y tarjetas anidadas.
- La plantilla de métrica: número enorme, etiqueta chica, fila de stats.
- Etiqueta o versalita arriba de un título.
- Emojis como iconos.
- Degradados, vidrio esmerilado y brillos de color sin desplazamiento.
- Relleno pastel como fondo de badge.
