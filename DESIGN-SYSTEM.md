# Sistema visual de producto
### Marca personal de Joaquín García Oliver, aplicada a interfaz

Este documento define las condiciones estéticas de cualquier app, dashboard o herramienta que lleve tu marca. Es la extensión de la misma paleta que ya usás en carruseles de LinkedIn, CV y piezas gráficas, traducida a las necesidades de una interfaz que se usa, no que se mira.

Está escrito para pegarse entero en Claude Code, Cursor o cualquier agente de desarrollo como referencia permanente del proyecto. Guardalo en la raíz del repo como `DESIGN-SYSTEM.md`.

**Regla general.** Si una decisión no está acá, resolvela por el camino más sobrio. Este sistema prefiere quedarse corto de estilo antes que pasarse.

---

## 1. Qué es esta marca, visualmente

Tres colores, geometría recta, tipografía densa, cero decoración. La identidad no está en efectos, está en la proporción y en la disciplina del color.

El elemento firma es la **barra de acento teal**, un rectángulo de proporción 15 a 1 sin redondeo. En los carruseles mide 120 x 8 px y se usa para marcar el inicio del bloque de contenido. En la app se reinterpreta como indicador de sección activa, regla superior de módulos clave y marcador de la métrica principal. Es lo único que se repite sin variación en todas las piezas y en todas las pantallas.

La segunda condición de continuidad es la relación fondo/texto. En piezas claras el fondo es hueso y el texto grafito. En piezas oscuras se invierte, el fondo es grafito y el texto hueso. El teal nunca es fondo dominante de una pantalla, solo de superficies chicas y puntuales.

---

## 2. Principios

**1. La interfaz es una herramienta de diagnóstico, no una landing.** La densidad de información es una virtud acá. Nada de secciones de respiro, ilustraciones de relleno ni titulares grandes que no aportan un dato. Si un bloque no responde una pregunta concreta, no va.

**2. El color carga significado, nunca decora.** El teal marca lo accionable y lo destacado. Los semánticos marcan estado. Todo lo demás es neutral. Un elemento pintado de teal porque "quedaba lindo" rompe el sistema entero, porque devalúa al teal como señal.

**3. El peso y el espacio construyen jerarquía antes que el tamaño.** Preferí cambiar peso tipográfico, color de texto y aire alrededor antes que agrandar. Las pantallas con seis tamaños de letra distintos son pantallas sin jerarquía.

**4. Borde antes que sombra.** La separación entre superficies se resuelve con una línea de 1 px. Las sombras se reservan para lo que flota de verdad, o sea menús, modales y avisos.

**5. Un solo momento de audacia por pantalla.** Una pantalla tiene un elemento memorable, normalmente el dato principal. El resto se calla. Si hay dos cosas gritando, no hay ninguna.

**6. Vacíos y errores son parte del diseño.** Toda vista tiene definido su estado vacío, su estado de carga y su estado de error antes de darse por terminada.

---

## 3. Color

### 3.1 Núcleo de marca

Estos tres valores no se tocan, no se reinterpretan y no se acompañan de colores nuevos fuera de los derivados de este documento.

| Nombre | Hex | Rol |
|---|---|---|
| Grafito | `#141414` | Texto principal en claro, fondo base en oscuro |
| Hueso | `#F5F2ED` | Fondo base en claro, texto principal en oscuro |
| Teal | `#387F7E` | Acento único, ancla de toda la rampa |

### 3.2 Rampa teal

Derivada del teal de marca manteniendo el matiz exacto (194 en OKLCH). El paso 500 es el color de marca literal.

| Token | Hex | Contraste sobre hueso | Uso |
|---|---|---|---|
| `teal-50` | `#E9F7F6` | 1.02 | Fondo de fila seleccionada, hover muy sutil |
| `teal-100` | `#D2EDEC` | 1.10 | Fondo de badge informativo, relleno de gráfico |
| `teal-200` | `#B4DCDB` | 1.32 | Bordes de elementos activos en claro |
| `teal-300` | `#8CC2C0` | 1.78 | Solo gráficos y rellenos, nunca texto |
| `teal-400` | `#5DA09E` | 2.69 | Texto de acento en modo oscuro, iconos sobre grafito |
| `teal-500` | `#387F7E` | 4.17 | Color de marca, barra de acento, series de datos, iconos grandes |
| `teal-600` | `#206969` | 5.72 | Botón primario, links, texto de acento sobre hueso |
| `teal-700` | `#155251` | 7.98 | Hover del botón primario, bordes de foco |
| `teal-800` | `#0D3B3A` | 11.04 | Superficies oscuras con tinte de marca |
| `teal-900` | `#0A2929` | 13.81 | Fondos de bloque oscuro alternativo al grafito |

**Regla dura de contraste.** El teal de marca `#387F7E` da 4.17 contra hueso y 4.66 contra blanco. No alcanza el mínimo de 4.5 de WCAG AA para texto chico sobre hueso. Por eso el texto en teal y los botones primarios usan `teal-600`, no el 500. El 500 queda para superficies de más de 24 px, barras, iconos grandes y series de gráficos, donde el mínimo exigible es 3.

### 3.3 Neutrales

Grises con temperatura cálida (matiz 82) para que peguen con el hueso. Un gris frío al lado del hueso se ve sucio.

| Token | Hex | Uso |
|---|---|---|
| `neutral-0` | `#F5F2ED` | Fondo de aplicación en claro |
| `neutral-50` | `#EDEBE6` | Superficie elevada, cabecera de tabla, barra lateral |
| `neutral-100` | `#E1DED8` | Bordes suaves, separadores internos |
| `neutral-200` | `#CFCCC6` | Bordes de campos, divisores fuertes |
| `neutral-300` | `#B4B1AB` | Bordes de estado deshabilitado, ejes de gráficos |
| `neutral-400` | `#94928D` | Placeholders, iconos inactivos |
| `neutral-500` | `#767471` | Texto terciario, unidades, marcas de tiempo |
| `neutral-600` | `#5C5B58` | Texto secundario, etiquetas de campo |
| `neutral-700` | `#434240` | Texto de énfasis medio |
| `neutral-800` | `#2C2B2A` | Superficie elevada en oscuro |
| `neutral-900` | `#141414` | Texto principal en claro, fondo en oscuro |

Texto secundario `neutral-600` da 6.08 sobre hueso y texto terciario `neutral-500` da 4.17. El terciario queda solo para texto de 16 px o más, o para peso 600 en tamaños chicos.

### 3.4 Semánticos

Tres estados, cada uno con un tono fuerte para texto y bordes, uno medio para iconos y rellenos, y uno claro para fondos. Ninguno compite con el teal en el matiz.

| Estado | Fuerte | Medio | Claro | Variante para modo oscuro |
|---|---|---|---|---|
| Negativo | `#B63132` | `#D54A47` | `#FFDEDB` | `#E3645E` |
| Atención | `#B77600` | `#DF9C27` | `#FCE8CA` | `#E1A536` |
| Positivo | `#357A43` | `#4E9A5B` | `#D7F0D9` | `#60AC6D` |

No existe un color "informativo" separado. Lo informativo es teal. Esa decisión mantiene la paleta en cuatro familias y refuerza el acento de marca cada vez que la app comunica algo neutro.

**Nunca uses color como único portador de significado.** Todo estado lleva además un icono, un texto o un cambio de forma. Un punto rojo y un punto verde sin etiqueta son inaccesibles para daltonismo rojo-verde, que es el caso más común.

### 3.5 Series de datos

Seis colores para gráficos, ordenados por frecuencia de uso. Empiezan en el teal de marca para que el primer dato de todo gráfico sea reconociblemente tuyo.

| Serie | Hex | Contraste sobre hueso |
|---|---|---|
| 1 | `#387F7E` | 4.17 |
| 2 | `#254A6E` | 8.24 |
| 3 | `#A66125` | 4.32 |
| 4 | `#973069` | 6.39 |
| 5 | `#50B0AF` | 2.30 |
| 6 | `#6D9358` | 3.15 |

Las series 5 y 6 tienen contraste bajo sobre hueso. Se usan con borde de 1 px del mismo color en paso más oscuro, o se reservan para áreas grandes. Nunca para líneas de 1 px ni para texto de leyenda.

Si el gráfico tiene una sola serie, va en `teal-500`. Si tiene dos, van 1 y 2. No metas la serie 3 antes de necesitarla.

### 3.6 Superficies en modo oscuro

El modo oscuro no es el modo claro invertido automáticamente. Es el esquema de los carruseles con fondo grafito, misma marca, no una marca distinta.

| Token | Hex | Rol |
|---|---|---|
| `surface-base` | `#141414` | Fondo de aplicación |
| `surface-raised` | `#1D2020` | Cards, paneles, barra lateral |
| `surface-overlay` | `#272B2B` | Menús, modales, popovers |
| `border-dark` | `#393E3E` | Bordes y divisores |
| Texto principal | `#F5F2ED` | 16.5 de contraste |
| Texto secundario | `#B4B1AB` | 8.61 |
| Acento de texto | `#67ACAB` | 7.08 |

Las superficies elevadas en oscuro tienen un tinte teal casi imperceptible. Es lo que evita que el modo oscuro se vea como un gris genérico de plantilla.

---

## 4. Tipografía

### 4.1 Familias

La recomendación es una combinación de tres, cada una con un trabajo claro.

**Archivo** para titulares y números grandes. Ya es tu tipografía de marca en carruseles y CV, es una grotesca de origen editorial con formas cerradas que aguanta pesos altos sin volverse pesada. Usala en 600 y 700, con tracking negativo de 0.02 em en tamaños de 30 px para arriba.

**Geist** para toda la interfaz y el cuerpo de texto. Está diseñada específicamente para producto, tiene alternativas de números tabulares y una altura de x generosa que la mantiene legible en 13 y 14 px, que es donde vive la mayor parte de una app de datos. Pesos 400, 500 y 600.

**Geist Mono** para números en tablas, identificadores, porcentajes de variación, marcas de tiempo, IDs de assets y cualquier valor que se compare en columna. La consistencia de ancho es funcional, no estética.

Alternativas válidas si alguna no está disponible o si querés otro carácter.

| Opción | Display | Interfaz | Mono | Carácter |
|---|---|---|---|---|
| A (recomendada) | Archivo | Geist | Geist Mono | Técnica y contemporánea |
| B | Instrument Serif | Instrument Sans | IBM Plex Mono | Editorial, más humana |
| C | Archivo | Inter Tight | JetBrains Mono | Máxima compatibilidad |

No mezcles opciones entre filas. Cada combinación está pensada como conjunto.

**Instalación.** Archivo, Instrument Sans, Instrument Serif, Inter Tight y JetBrains Mono salen de Google Fonts. Geist y Geist Mono se instalan por npm con el paquete `geist` o se hospedan localmente desde el repositorio oficial de Vercel. Cargá solo los pesos que usás y en formato variable si está disponible. Tres familias son el máximo absoluto del proyecto.

### 4.2 Escala

Escala modular de razón 1.2 redondeada a valores enteros cómodos. Cada paso indica tamaño, interlineado y peso por defecto.

| Token | Tamaño | Interlineado | Peso | Familia | Uso |
|---|---|---|---|---|---|
| `display` | 48 px | 1.05 | 700 | Archivo | Dato único dominante, pantalla de resultado |
| `h1` | 38 px | 1.1 | 700 | Archivo | Título de vista |
| `h2` | 30 px | 1.15 | 600 | Archivo | Sección |
| `h3` | 24 px | 1.2 | 600 | Archivo | Subsección, título de card grande |
| `h4` | 20 px | 1.3 | 600 | Geist | Título de card, encabezado de panel |
| `body-lg` | 18 px | 1.6 | 400 | Geist | Texto introductorio, descripciones largas |
| `body` | 16 px | 1.55 | 400 | Geist | Cuerpo por defecto |
| `body-sm` | 14 px | 1.5 | 400 | Geist | Interfaz densa, tablas, formularios |
| `caption` | 13 px | 1.45 | 500 | Geist | Etiquetas de campo, ayudas |
| `micro` | 11 px | 1.4 | 600 | Geist | Badges, contadores, metadatos |
| `metric` | 30 px | 1 | 600 | Geist Mono | Valor numérico en tarjeta de métrica |
| `metric-sm` | 16 px | 1 | 500 | Geist Mono | Valores en tabla |

### 4.3 Reglas

Medida de línea máxima de 72 caracteres en texto corrido, entre 45 y 60 en columnas angostas. Todo párrafo que cruce los 80 se parte o se pone en dos columnas.

Todos los números que se comparen verticalmente llevan `font-variant-numeric: tabular-nums`. Sin eso las columnas de cifras bailan y la tabla se vuelve ilegible.

Sentence case en absolutamente todo, incluidos botones, encabezados de tabla y elementos de navegación. No hay mayúsculas sostenidas en la interfaz. El único lugar donde se permite tracking amplio en mayúsculas es el kicker de las piezas gráficas de LinkedIn, que es otro sistema.

Nada de subrayado salvo en links dentro de texto corrido. Los links de navegación se distinguen por color y posición.

Cursivas solo para nombres de obras, títulos de tracks y citas. Nunca para énfasis, para eso está el peso 600.

---

## 5. Espaciado y grilla

Base de 4 px. Toda medida del sistema es múltiplo de 4.

`2, 4, 8, 12, 16, 24, 32, 48, 64, 96`

Relación entre separación y jerarquía. Elementos de un mismo grupo se separan 8 o 12. Grupos dentro de un bloque se separan 24. Bloques entre sí se separan 48. Secciones mayores 64 o 96. Si dos cosas están a la misma distancia, se leen como del mismo nivel, y eso comunica más que cualquier título.

Padding interno estándar. Cards 24, paneles densos 16, celdas de tabla 12 vertical y 16 horizontal, botones 10 vertical y 16 horizontal.

Anchos de contenedor. Aplicación completa 1440 máximo, contenido de lectura 720, formularios 480, barra lateral 260 expandida y 64 colapsada.

Grilla de 12 columnas con canaleta de 24 en escritorio, 8 columnas y canaleta de 16 en tablet, 4 columnas y canaleta de 16 en móvil.

Alineación a la izquierda por defecto en todo. Centrado solo en estados vacíos, pantallas de carga y diálogos de confirmación cortos. Los números en tabla van alineados a la derecha, sus encabezados también.

---

## 6. Forma, borde y elevación

Radios bajos, porque la marca es geométrica y recta.

| Token | Valor | Uso |
|---|---|---|
| `radius-none` | 0 | Barra de acento, indicadores, líneas de gráfico |
| `radius-sm` | 2 px | Badges, chips, celdas seleccionadas |
| `radius-md` | 4 px | Botones, campos, menús, elementos interactivos |
| `radius-lg` | 8 px | Cards, paneles, modales |
| `radius-full` | 9999 px | Solo avatares y puntos de estado |

Bordes siempre de 1 px. `neutral-100` para divisores internos, `neutral-200` para bordes de componentes, `teal-600` para estado activo o foco.

Sombras, únicamente tres y solo para elementos flotantes.

```
--shadow-dropdown: 0 4px 12px rgba(20, 20, 20, 0.10);
--shadow-modal:    0 16px 40px rgba(20, 20, 20, 0.18);
--shadow-toast:    0 8px 24px rgba(20, 20, 20, 0.14);
```

Las cards no llevan sombra. Se separan del fondo con borde y con el cambio de superficie de hueso a `neutral-50`. En modo oscuro las sombras se reemplazan por un borde `#393E3E` más un cambio de superficie, porque una sombra negra sobre fondo casi negro no se ve.

---

## 7. Componentes

### Botones

Cuatro variantes, ninguna más.

**Primario.** Fondo `teal-600`, texto hueso, radio 4, altura 40, peso 500. Hover `teal-700`. Activo `teal-800`. Deshabilitado fondo `neutral-200` y texto `neutral-400`. Uno solo por pantalla, salvo en tablas donde puede repetirse por fila.

**Secundario.** Fondo transparente, borde 1 px `neutral-200`, texto grafito. Hover fondo `neutral-50` y borde `neutral-300`.

**Fantasma.** Sin fondo ni borde, texto `teal-600`. Hover fondo `teal-50`. Para acciones terciarias y filas de tabla.

**Destructivo.** Fondo transparente, borde y texto en negativo fuerte `#B63132`. Se rellena en sólido solo dentro del diálogo de confirmación, nunca en la vista principal.

Alturas de 32 en denso, 40 por defecto, 48 en formularios importantes. El texto del botón dice exactamente qué pasa. "Guardar cambios", no "Enviar". La acción mantiene el mismo verbo en todo el flujo, así el botón que dice "Publicar" produce un aviso que dice "Publicado".

Sin iconos de flecha al final del texto. Sin mayúsculas. Sin ancho completo salvo en móvil.

### Campos de formulario

Altura 40, radio 4, borde `neutral-200`, fondo hueso. Foco con borde `teal-600` y anillo exterior de 3 px en `teal-600` al 20 por ciento. Etiqueta arriba en 13 px peso 500 color `neutral-600`, nunca dentro del campo como placeholder.

El placeholder muestra un ejemplo de formato, no repite la etiqueta. En un campo de URL de artista el placeholder es una URL de ejemplo.

Los errores aparecen debajo del campo en 13 px color negativo fuerte, con el borde del campo también en negativo. El texto dice qué pasó y cómo se arregla. "Este canal no tiene Content ID habilitado. Verificá que el CMS sea el correcto". No dice "Error de validación".

Validación al salir del campo, no mientras se escribe. La única excepción es el contador de caracteres cuando hay límite.

### Cards y paneles

Fondo `neutral-50` sobre fondo de app hueso, borde 1 px `neutral-100`, radio 8, padding 24. Título en `h4`. Si la card tiene una métrica principal, esa métrica va en `metric` con la barra de acento teal de 32 x 4 px arriba del número.

Nunca uses la misma card para todo. Una pantalla donde todo está metido en rectángulos idénticos no tiene jerarquía. Los bloques secundarios pueden vivir sueltos sobre el fondo, separados solo por espacio y por una línea.

### Tablas

El componente central de una app de datos, tratalo como tal.

Encabezado con fondo `neutral-50`, texto 13 px peso 600 color `neutral-600`, borde inferior 1 px `neutral-200`. Filas con borde inferior `neutral-100`, altura 48 en cómodo y 36 en denso, hover `teal-50`. Fila seleccionada con fondo `teal-50` y borde izquierdo de 2 px en `teal-600`.

Números a la derecha en Geist Mono con tabular-nums. Texto a la izquierda. Fechas en formato corto y consistente. Columna de acciones al final, alineada a la derecha, con botones fantasma que aparecen al hacer hover pero que existen siempre para navegación por teclado.

Sin filas cebradas. El borde inferior alcanza y el cebrado pelea con el estado de selección.

Orden, filtro y paginación siempre visibles arriba de la tabla, no escondidos en un menú.

### Estados y badges

Badge de 20 px de alto, radio 2, padding 2 y 8, texto `micro` peso 600. Fondo en el tono claro del semántico y texto en el tono fuerte. Cada badge lleva texto, nunca solo un punto de color.

Los estados del dominio se nombran por lo que entiende el usuario. "Reclamo activo", "En disputa", "Liberado", no los códigos internos del sistema.

### Navegación

Barra lateral izquierda de 260 px, fondo `neutral-50`, borde derecho 1 px `neutral-100`. Elemento activo con fondo `teal-50`, texto `teal-700` y barra vertical de 3 px en `teal-600` pegada al borde izquierdo. Es la barra de acento de marca girada 90 grados, y es lo que hace que la navegación se vea tuya y no de una plantilla.

Iconos de trazo de 1.5 px, tamaño 20, de una sola familia. Nunca emojis como iconos.

Cabecera de 56 px con el título de la vista a la izquierda y las acciones a la derecha. Migas de pan solo si la jerarquía pasa de dos niveles.

### Estados vacíos

Un título en `h4`, una línea de explicación en `body-sm` color `neutral-600` y un botón primario con la acción que corresponde. Sin ilustración, sin icono gigante, sin texto de humor.

El texto dice qué falta y cómo se llena. "Todavía no auditaste ningún artista. Empezá pegando el link de un perfil de Spotify".

### Carga

Esqueletos en `neutral-100` con las formas reales del contenido que viene, no un spinner centrado. Para cargas de más de 5 segundos, una barra de progreso con el paso actual escrito. Para operaciones sobre APIs externas, el texto dice qué se está consultando, porque la espera se tolera mucho mejor cuando se sabe por qué existe.

### Avisos y modales

Los avisos aparecen abajo a la derecha, ancho 360, duración 5 segundos, con el semántico correspondiente en el borde izquierdo de 3 px. Los avisos de error no se autodestruyen, se cierran a mano.

Los modales tienen ancho máximo 560, fondo hueso, radio 8, padding 32, y un fondo de superposición grafito al 40 por ciento. Se cierran con Escape y con clic afuera, salvo los destructivos, que exigen decisión explícita.

---

## 8. Movimiento

El movimiento responde a una acción del usuario y muestra qué cambió. No hay animaciones de entrada por scroll, ni apariciones escalonadas, ni transiciones en hover sobre cada card. Eso es el tic visual más reconocible de una interfaz generada.

| Token | Duración | Curva | Uso |
|---|---|---|---|
| `motion-instant` | 100 ms | `ease-out` | Hover, foco, cambio de color |
| `motion-fast` | 160 ms | `cubic-bezier(0.2, 0, 0, 1)` | Menús, tooltips, badges |
| `motion-base` | 240 ms | `cubic-bezier(0.2, 0, 0, 1)` | Modales, paneles laterales, expansiones |
| `motion-slow` | 400 ms | `cubic-bezier(0.4, 0, 0.2, 1)` | Entrada de gráficos, una sola vez por vista |

Los gráficos animan una vez al cargar, de izquierda a derecha para líneas y desde la base para barras. No reaniman al filtrar, ahí el cambio es directo, porque la comparación importa más que el efecto.

`prefers-reduced-motion: reduce` desactiva todo excepto los cambios de opacidad de 100 ms.

---

## 9. Visualización de datos

Las reglas de arriba se aplican también acá, con estos agregados.

Ejes y grillas en `neutral-300` de 1 px. Solo grilla horizontal, nunca vertical, nunca ambas. Etiquetas de eje en 11 px color `neutral-500`.

Nada de tercera dimensión, degradados bajo la línea, sombras en las barras ni bordes redondeados en las puntas de las barras. Una barra termina donde termina el dato.

Gráficos de torta solamente para partes de un total con tres categorías o menos. Con más, barras horizontales ordenadas de mayor a menor.

Las líneas van de 2 px. Los puntos solo aparecen cuando hay menos de 15 datos o al hacer hover. El tooltip muestra el valor exacto, la fecha y la serie, en Geist Mono.

Toda cifra lleva su unidad y su período. "1.284.302 reproducciones, últimos 28 días", no un número suelto.

Formato numérico en español de Argentina. Punto para miles, coma para decimales. Los porcentajes de variación llevan signo siempre, con el tono positivo o negativo del semántico y una flecha de 12 px. Si el cambio es menor a 0,5 por ciento se muestra como "sin cambios" en `neutral-500`, porque el ruido presentado como señal es un error de diseño.

Los valores monetarios llevan moneda explícita, sin excepción. `USD 1.240,50` y `ARS 1.240,50` nunca comparten columna sin estar aclarado.

Cuando un dato viene de una API externa, la fecha de actualización va debajo del gráfico en 11 px color `neutral-500`. Un dashboard sin fecha de corte es un dashboard en el que no se puede confiar.

---

## 10. Voz y textos de interfaz

Español rioplatense, voseo, sentence case, verbos activos. La interfaz habla como vos hablás, seca y directa, sin entusiasmo comercial.

Escribí "Auditar artista", no "¡Comenzá tu análisis!". Escribí "No se pudo conectar con Spotify. Revisá el token y probá de nuevo", no "¡Ups! Algo salió mal".

Nombrá las cosas por lo que el usuario entiende, no por cómo está construido el sistema. Es "Reclamos activos", no "Claims endpoint". Es "Actualizar datos", no "Sincronizar caché".

Sin signos de exclamación. Sin emojis en la interfaz. Sin dos puntos en textos redactados, reformulá con punto o con conector. Sin guiones largos como separador de oración, usá comas, paréntesis o punto.

Los errores no piden disculpas y no son vagos. Dicen qué pasó, por qué y qué hacer ahora.

Cada texto hace un solo trabajo. Si una etiqueta y su ayuda dicen lo mismo, borrá la ayuda.

---

## 11. Accesibilidad

Piso obligatorio, no opcional.

Contraste mínimo de 4.5 para texto menor a 24 px, 3 para texto mayor y para elementos de interfaz como bordes de campo e iconos. Todos los valores de este documento ya vienen verificados contra hueso y contra grafito.

Foco visible en todo elemento interactivo, con anillo de 2 px `teal-600` más 2 px de separación. Nunca `outline: none` sin reemplazo.

Objetivos táctiles de 44 x 44 px como mínimo en móvil, 32 x 32 aceptable en escritorio con puntero.

Todo se opera con teclado. Orden de tabulación lógico, Escape cierra, Enter confirma, las flechas navegan listas y tablas.

Los gráficos tienen alternativa en tabla. Un botón "Ver datos" debajo de cada gráfico resuelve accesibilidad y además es lo que la gente de operaciones realmente quiere.

Los estados nunca se comunican solo por color. Ícono, texto o forma acompañan siempre.

Responsive real hasta 360 px de ancho. Las tablas en móvil se convierten en tarjetas apiladas, no en scroll horizontal.

---

## 12. Prohibiciones

Estas cosas no entran en ninguna pantalla de este producto.

Degradados de cualquier tipo, incluidos los fondos con manchas de color difuminadas y los textos con relleno degradado.

Vidrio esmerilado, desenfoques de fondo y transparencias decorativas.

Colores fuera de este documento. En particular nada de terracota ni naranja arcilla cercano a `#D97757`, nada de verde ácido sobre negro, nada de violeta de plantilla. Son las tres marcas registradas de la interfaz generada por defecto.

Sombras de colores, brillos, bordes luminosos y efectos de neón.

Emojis como iconos de sección o de estado.

Etiquetas en mayúsculas con tracking amplio arriba de cada título. En la app no van, ni siquiera una.

Numeración `01 / 02 / 03` salvo que el contenido sea literalmente una secuencia de pasos.

Flechas `→` pegadas al texto de botones y links.

Ilustraciones de stock, figuras isométricas y avatares genéricos.

Más de tres familias tipográficas, más de cuatro pesos en total.

Animaciones de entrada por scroll.

Cards idénticas para contenidos de jerarquía distinta.

---

## 13. Tokens listos para pegar

### CSS custom properties

```css
:root {
  /* Marca */
  --grafito: #141414;
  --hueso:   #F5F2ED;
  --teal:    #387F7E;

  /* Teal */
  --teal-50:  #E9F7F6;
  --teal-100: #D2EDEC;
  --teal-200: #B4DCDB;
  --teal-300: #8CC2C0;
  --teal-400: #5DA09E;
  --teal-500: #387F7E;
  --teal-600: #206969;
  --teal-700: #155251;
  --teal-800: #0D3B3A;
  --teal-900: #0A2929;

  /* Neutrales calidos */
  --neutral-0:   #F5F2ED;
  --neutral-50:  #EDEBE6;
  --neutral-100: #E1DED8;
  --neutral-200: #CFCCC6;
  --neutral-300: #B4B1AB;
  --neutral-400: #94928D;
  --neutral-500: #767471;
  --neutral-600: #5C5B58;
  --neutral-700: #434240;
  --neutral-800: #2C2B2A;
  --neutral-900: #141414;

  /* Semanticos */
  --negative-strong: #B63132;
  --negative-mid:    #D54A47;
  --negative-soft:   #FFDEDB;
  --warning-strong:  #B77600;
  --warning-mid:     #DF9C27;
  --warning-soft:    #FCE8CA;
  --positive-strong: #357A43;
  --positive-mid:    #4E9A5B;
  --positive-soft:   #D7F0D9;

  /* Series de datos */
  --series-1: #387F7E;
  --series-2: #254A6E;
  --series-3: #A66125;
  --series-4: #973069;
  --series-5: #50B0AF;
  --series-6: #6D9358;

  /* Roles semanticos de superficie, modo claro */
  --bg-app:        var(--neutral-0);
  --bg-surface:    var(--neutral-50);
  --bg-hover:      var(--teal-50);
  --text-primary:  var(--neutral-900);
  --text-secondary:var(--neutral-600);
  --text-tertiary: var(--neutral-500);
  --text-accent:   var(--teal-600);
  --border-subtle: var(--neutral-100);
  --border-default:var(--neutral-200);
  --border-focus:  var(--teal-600);

  /* Tipografia */
  --font-display: "Archivo", system-ui, sans-serif;
  --font-ui:      "Geist", system-ui, sans-serif;
  --font-mono:    "Geist Mono", ui-monospace, monospace;

  --text-display: 48px;
  --text-h1: 38px;
  --text-h2: 30px;
  --text-h3: 24px;
  --text-h4: 20px;
  --text-body-lg: 18px;
  --text-body: 16px;
  --text-body-sm: 14px;
  --text-caption: 13px;
  --text-micro: 11px;

  /* Espaciado */
  --space-1: 4px;   --space-2: 8px;   --space-3: 12px;
  --space-4: 16px;  --space-6: 24px;  --space-8: 32px;
  --space-12: 48px; --space-16: 64px; --space-24: 96px;

  /* Forma */
  --radius-sm: 2px;
  --radius-md: 4px;
  --radius-lg: 8px;

  --shadow-dropdown: 0 4px 12px rgba(20, 20, 20, 0.10);
  --shadow-modal:    0 16px 40px rgba(20, 20, 20, 0.18);
  --shadow-toast:    0 8px 24px rgba(20, 20, 20, 0.14);

  /* Movimiento */
  --motion-instant: 100ms ease-out;
  --motion-fast: 160ms cubic-bezier(0.2, 0, 0, 1);
  --motion-base: 240ms cubic-bezier(0.2, 0, 0, 1);
  --motion-slow: 400ms cubic-bezier(0.4, 0, 0.2, 1);
}

[data-theme="dark"] {
  --bg-app:         #141414;
  --bg-surface:     #1D2020;
  --bg-overlay:     #272B2B;
  --bg-hover:       #0D3B3A;
  --text-primary:   #F5F2ED;
  --text-secondary: #B4B1AB;
  --text-tertiary:  #94928D;
  --text-accent:    #67ACAB;
  --border-subtle:  #272B2B;
  --border-default: #393E3E;
  --border-focus:   #5DA09E;

  --negative-strong: #E3645E;
  --warning-strong:  #E1A536;
  --positive-strong: #60AC6D;
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 100ms !important;
  }
}
```

### Tailwind v4

```css
@import "tailwindcss";

@theme {
  --color-grafito: #141414;
  --color-hueso:   #F5F2ED;

  --color-teal-50:  #E9F7F6;
  --color-teal-100: #D2EDEC;
  --color-teal-200: #B4DCDB;
  --color-teal-300: #8CC2C0;
  --color-teal-400: #5DA09E;
  --color-teal-500: #387F7E;
  --color-teal-600: #206969;
  --color-teal-700: #155251;
  --color-teal-800: #0D3B3A;
  --color-teal-900: #0A2929;

  --color-neutral-50:  #EDEBE6;
  --color-neutral-100: #E1DED8;
  --color-neutral-200: #CFCCC6;
  --color-neutral-300: #B4B1AB;
  --color-neutral-400: #94928D;
  --color-neutral-500: #767471;
  --color-neutral-600: #5C5B58;
  --color-neutral-700: #434240;
  --color-neutral-800: #2C2B2A;
  --color-neutral-900: #141414;

  --font-display: "Archivo", system-ui, sans-serif;
  --font-sans:    "Geist", system-ui, sans-serif;
  --font-mono:    "Geist Mono", ui-monospace, monospace;

  --radius-sm: 2px;
  --radius-md: 4px;
  --radius-lg: 8px;
}
```

### La barra de acento

El elemento firma, en tres contextos.

```css
/* Sobre bloque de contenido */
.accent-bar {
  width: 120px;
  height: 8px;
  background: var(--teal-500);
  margin-bottom: 24px;
}

/* Sobre metrica en card */
.accent-bar--metric {
  width: 32px;
  height: 4px;
  background: var(--teal-500);
  margin-bottom: 12px;
}

/* Navegacion activa, la misma barra girada */
.nav-item[aria-current="page"] {
  background: var(--teal-50);
  color: var(--teal-700);
  box-shadow: inset 3px 0 0 var(--teal-600);
}
```

---

## 14. Prompt para el agente de desarrollo

Pegá esto al inicio de cualquier sesión de Claude Code sobre el proyecto, con el archivo completo adjunto o en el repo.

```
Seguí DESIGN-SYSTEM.md al pie de la letra en todo lo visual.

Reglas que no se negocian:
- Solo los colores del documento. Cero colores nuevos, cero degradados.
- Teal 600 (#206969) para texto y botones primarios. Teal 500
  (#387F7E) solo para superficies grandes, barras, iconos y graficos.
- Fondo hueso con texto grafito en claro, invertido en oscuro.
- Archivo para titulares, Geist para interfaz, Geist Mono para
  cualquier numero que se compare en columna.
- Sentence case en toda la interfaz. Nada de mayusculas sostenidas.
- Borde de 1px antes que sombra. Sombra solo en menus, modales y avisos.
- Espaciado en multiplos de 4.
- Cada vista necesita estado vacio, de carga y de error definidos.
- Foco visible siempre, contraste minimo 4.5 en texto chico.
- Sin animaciones de entrada por scroll, sin emojis, sin flechas
  pegadas al texto de los botones.

Antes de escribir codigo, decime en tres lineas que decisiones
visuales vas a tomar y contra que seccion del documento las estas
chequeando. Si algo no esta cubierto, preguntame en vez de inventar.
```

---

## 15. Control antes de dar por terminada una pantalla

Diez preguntas. Si alguna da que no, la pantalla no está lista.

1. ¿Usa solo colores de este documento?
2. ¿Hay un único elemento dominante, y es el dato que más importa?
3. ¿El teal aparece solo donde significa algo accionable o destacado?
4. ¿Todos los números que se comparan están en mono con tabular-nums?
5. ¿Las separaciones son múltiplos de 4 y agrupan por jerarquía real?
6. ¿Están definidos el estado vacío, el de carga y el de error?
7. ¿Se puede operar todo con teclado, con foco visible?
8. ¿Funciona a 360 px de ancho?
9. ¿Los textos dicen qué pasa en lugar de vender la función?
10. ¿Se le puede sacar un elemento más sin perder información?

La diez es la más importante y casi siempre da que sí.
