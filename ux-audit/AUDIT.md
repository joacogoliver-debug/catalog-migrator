# Auditoria UI/UX del Migrador de Catalogos

Fase 2. Sobre `main` (8ab1130), 2026-09-14. Evidencia en `ux-audit/before/`
(referida por nombre de archivo sin extension; `--oscuro--1440` salvo que se
indique otro tema o ancho). Ubicaciones de codigo con archivo y linea. El mapa de
la app esta en `MAPA.md`.

Convencion de severidad: **Critico** rompe datos o deja sin salida; **Alto**
degrada de forma evidente la lectura o la accion principal; **Medio** se nota si
se mira; **Bajo** pulido.

---

## A. Lectura general

**Que es y que transmite.** Una herramienta de inventario para gente que sabe
que es un ISRC: hoy se lee como un panel de administracion correcto y algo
generico, con una tabla cuidada en el medio y demasiadas etiquetas en
versalitas alrededor.

### Tokens en uso y donde estan

| Grupo | Valores | Donde |
|---|---|---|
| Marca | grafito `#141414`, hueso `#F5F2ED`, teal 50 a 900 (`#387F7E` = 500) | `tokens/colors.css:19-31` |
| Neutrales | grises calidos 0 a 900 | `colors.css:34-44` |
| Superficies oscuro | lienzo `#000000`, fondo `#121617`, panel `#1A1F1F`, panel-alto `#222827`, flotante `#2A3130` | `colors.css:59-63` |
| Superficies claro | lienzo `#DCD7CD`, fondo `#F8F6F2`, panel `#EFECE6`, panel-alto `#E6E2DA`, flotante `#FFFFFF` | `colors.css:101-105` |
| Texto | `#F2EFEA` / `#A9ADAC` / `#828887` (oscuro); `#141414` / `#56554F` / `#65635E` (claro) | `colors.css:65-68, 107-110` |
| Semanticos | negativo `#E3645E`, atencion `#E1A536`, positivo `#60AC6D`; en claro `#A82E2F`, `#7E5500`, `#2C6539` | `colors.css:87-89, 124-126` |
| Tipografias | Archivo (display), Geist (sans), Geist Mono | `tokens/typography.css:14-16` |
| Escala | 42 / 22 / 16 / 14 / 13 / 13 / 11 / 28 (metrica) | `typography.css:19-26` |
| Interlineados | 1.0 / 1.12 / 1.6 / 1.45 / 1.2 | `typography.css:29-33` |
| Tracking | display -0.04em, mono +0.06em | `typography.css:41-43` |
| Espaciado | 4, 8, 12, 16, 24, 32, 48, 64 | `tokens/spacing.css:13-20` |
| Radios | marca 4, control 8, panel 14, shell 18 | `spacing.css:31-35` |
| Sombras | menu, modal (solo definidas, no usadas) | `spacing.css:39-40` |
| Movimiento | rapido 100 ms, base 180 ms, trabajo 600 ms, curva `(.2,0,0,1)` | `spacing.css:43-46` |
| Alturas | 28 / 34 / 42 / 40 (fila) | `spacing.css:49-52` |

**Valores fuera del sistema.**

- 44 atributos `style="..."` en `app.js` (margin-top 24 px nueve veces, 12 px
  siete, 8 px cinco, mas anchos y alturas sueltos). Duplican `--e-3`, `--e-5`,
  etc. con numeros crudos.
- Tamano de fuente 10 px en badges (`app.css:478`), numero de paso (`223`),
  numero de fila (`539`), cabecera de subtabla (`568`) y etiquetas apiladas en
  movil (`779, 792`). No existe en la escala: el piso es 11.
- Medidas en px sin token: `td-check` 58, `td-exp` 30, `detalle-inner`
  padding-left 88, etiquetas moviles 84, badge alto 18, paso 26, boton icono
  28, expandir 22, casilla 15, spinner 12, barra 3, log 180, tabla de
  validacion 340 (inline), tabla 58vh, radio de paso 5.
- `!important` en `.hidden`, en `tr.fila-detalle > td` (`563`) y en el bloque de
  reduced-motion (esos tres son aceptables; el de la fila de detalle tapa un
  problema de especificidad).
- Cero hex crudos en `app.css`: bien.

### Lectura de dials (taste-skill seccion 1)

| Dial | Hoy | Propuesto (Preserve) |
|---|---|---|
| DESIGN_VARIANCE | 3 (una columna, simetrico, sin asimetrias) | 3 |
| MOTION_INTENSITY | 2 (hover de 100 ms, barra de progreso, spinner; sin entradas ni transiciones de estado) | 3 |
| VISUAL_DENSITY | 7 (tabla a 13 px, filas de 40) | 7 |

### Modo recomendado

**Preserve.** La paleta, la tipografia y el flujo son decisiones tomadas y
buenas. Lo que falla es ejecucion: dos bugs visibles, semantica de color
inconsistente, exceso de versalitas, ritmo vertical y estados. Nada pide
empezar de cero. El propio skill reserva Overhaul para "visual debt
estructural", que no es el caso.

---

## B. Hallazgos por categoria

### 1. Consistencia de sistema

- **SYS-01** (Alto) `colors.css:59`, cualquier captura `--1440`. Lienzo
  `#000000` puro. Lo prohiben taste-skill 8.B y 9.A y redesign-skill
  ("Pure #000000 background"). Lo puse yo en la pasada de Framer. Fix
  propuesto: `#050707` en oscuro conserva el escalon contra `#121617` (que es lo
  que hace flotar al shell) sin ser negro absoluto. **Decision tuya**: el negro
  puro es defendible como eleccion de marca; si lo elegis, queda documentado
  como excepcion consciente.
- **SYS-02** (Medio) 44 estilos inline en `app.js` (ver A). Fix: cuatro clases
  de ritmo (`.mt-2`, `.mt-3`, `.mt-5`, `.mt-6`) con tokens, y los anchos de
  campo en clases (`.field-corto`).
- **SYS-03** (Medio) Tamano 10 px repetido en cinco lugares sin token. Fix:
  subir a `--t-micro` (11) o crear `--t-nano: 10px` y usarlo; a 10 px el mono
  ya esta al limite de legibilidad en pantallas de 1x.
- **SYS-04** (Bajo) Medidas crudas listadas en A. Fix: `--w-indice`,
  `--w-expandir`, y `padding-left: calc(var(--w-indice) + var(--w-expandir))`
  en `.detalle-inner` para que el detalle siga alineado si cambia la columna.
- **SYS-05** (Bajo) `DESIGN.md` se contradice: seccion 5 dice radios 2 / 4 / 6,
  seccion 4b dice 18 / 14 / 8 / 4 (los tokens siguen a 4b); seccion 6 lista
  superficies `#101212` / `#161919` / `#1B1F1F` / `#232828` y los tokens son
  otros; seccion 4 dice titulo 40 px y el token es 42. `README.md:327` remite a
  `DESIGN-SYSTEM.md` como fuente de tokens, que ya no lo es. Fix: actualizar
  los tres documentos en el lote de tokens.
- **SYS-06** (Bajo) Comentarios que describen lo que el CSS ya no hace:
  `app.css:579` ("Borde completo de 1 px") sobre una alerta sin borde;
  `app.css:490-492` ("sin bordes exteriores redondeados que la conviertan en
  una tarjeta") sobre `.tabla-wrap` con radio 14 y fondo panel;
  `app.css:391` ("sin redondeo") sobre una casilla con radio 4. Fix: reescribir
  o borrar.
- **SYS-07** (Bajo) `.card` es una clase vacia (`app.css:240-245`) que
  sobrevive del diseno anterior; `.fade` se usa en siete vistas y no tiene
  regla CSS. Fix: eliminar las dos o darles significado.
- **SYS-08** (Bajo) `--luz-borde` en claro es `rgba(255,255,255,.85)` sobre
  `#F8F6F2`: invisible (`01-entrada--claro--1440`). Fix: en claro, una linea
  de sombra `rgba(0,0,0,.06)` o nada.

### 2. Tipografia y jerarquia

- **TYP-01** (Alto) `app.js:614-652` y `921-950`; `05-catalogo` (y=290, 343),
  `13-descargar-audio--oscuro--1440-completa` (y=527). Las alertas del paso 2 y
  la de Tidal corren a todo el ancho: 1.250 px, unos 180 caracteres por linea.
  Fix: `.alerta > div { max-width: var(--medida) }`.
- **TYP-02** (Medio) `app.css:719-722`, `04-terminos`. `--medida: 68ch` da
  parrafos de 631 px a 14 px, que en Geist son 85 a 90 caracteres reales:
  `ch` mide el cero, que es mas ancho que la media. Fix: `--medida: 58ch` (que
  son unos 72 caracteres reales) o un valor en px.
- **TYP-03** (Medio) `app.css:73-77`. `h2` (22 px) usa `--tracking-display`
  (-0.04em), que `typography.css:40` reserva para 30 px o mas. Se ve en
  "Terminos de uso" y "La app se encontro con un problema". Fix: -0.02em en h2.
- **TYP-04** (Medio) Cinco usos de 10 px (SYS-03). En `R1-catalogo-real` los
  numeros de fila y los badges son lo mas chico de la pantalla y a la vez lo
  que mas color lleva.
- **TYP-05** (Medio) `app.css:160-167`, cabecera. "MIGRADOR DE CATALOGOS" en
  mono 11 px versalitas al lado del logo: la marca escrita como una etiqueta de
  seccion. Con el logo ya hay marca. Fix: wordmark en Archivo 13 px 600
  sentence case, o el lockup de `docs/marca` que ya existe.
- **TYP-06** (Medio) `app.css:304-317`, `05-catalogo`. En la tira de metricas
  la etiqueta esta a 11 px versalitas y la cifra a 28 px: salto de 2,5x para
  datos que se leen una vez. Ver COMP-16.
- **TYP-07** (Bajo) `app.js:816`, `R1-catalogo-real`. La subfila "15 tracks,
  5358533 Records DK" mezcla cantidad y sello en una sola linea de 11 px con
  coma; cuando el sello es largo compite con el titulo. Fix: sello en su
  columna o en el detalle.
- **TYP-08** (Bajo) `app.css:99` `.small` fija `line-height: 1.5` sobre 11 px
  mientras `--i-ui` es 1.45 y `.log` usa 1.8: tres interlineados para el mismo
  tamano. Fix: un token `--i-micro`.

### 3. Layout, grilla y espaciado

- **LAY-01** (Alto) `app.css:494-499, 629-631`, `app.js:1030`;
  `R1-catalogo-real`, `16-progreso`, `R7-listo-real-avisos--1440-completa`.
  Scroll dentro de scroll: `main` scrollea y adentro la tabla (58vh), el log
  (180 px) y la tabla de validacion (340 px) tienen su propio scroll. Con 10
  productos la tabla muestra 6 y hay que scrollear un area que a su vez
  scrollea. Fix: sin `max-height` en tabla y validacion (la cabecera sticky
  sigue funcionando porque el ancestro con scroll es `main`), y el log con
  `flex: 1` hasta el pie.
- **LAY-02** (Alto) `app.css:253, 710`; `01-entrada--oscuro--1920`,
  `03-clave-propia`. Paso 1, clave y terminos van en una columna de 760 px
  centrada mientras cabecera, pie y paso 2 usan 1.440 px alineados a la
  izquierda: a 1.920 px el 65 % del ancho y el 60 % del alto quedan vacios y el
  titulo cambia de lugar al pasar del paso 1 al 2. Fix: una sola regla de
  alineacion. Propuesta: columna de lectura alineada a la izquierda de la misma
  grilla que el paso 2, y `--ancho-app` bajado a 1.280.
- **LAY-03** (Medio) `app.css:256-262, 273`; `05-catalogo` (y=360 a 430). Entre
  los avisos y "PRODUCTOS DEL CATALOGO" hay un hueco de unos 100 px
  (`.seccion` margin-top 64 mas padding-top 12 mas margen de las alertas). Fix:
  `margin-top: var(--e-8)` y un solo margen entre alerta y seccion.
- **LAY-04** (Medio) `app.css:631`; `16-progreso`, `R5-progreso-real--claro`.
  El log mide 180 px y debajo quedan 500 px vacios. Fix: LAY-01.
- **LAY-05** (Medio) `app.js:673-678`; `05-catalogo` (x=1258, y=136). "Relevar
  otro artista" se centra verticalmente contra el bloque titulo mas subtitulo y
  queda a la altura de ninguno de los dos. Fix: `align-items: flex-start` y
  margen para alinear su caja con la linea del h1.
- **LAY-06** (Medio) `app.css:749-751`; `R1-catalogo-real--375`. En movil la
  barra de accion (resumen mas tres botones apilados) mide unos 120 px de 812:
  15 % del viewport fijo. Fix: resumen y botones compactos (`--h-denso`) en una
  fila, "Marcar todo / Desmarcar" en un solo toggle.
- **LAY-07** (Medio) `app.css:291-303`; `R1-catalogo-real--375`. Las cinco
  metricas se acomodan 2 + 2 + 1 y la quinta ("Reproducciones", la menos
  importante) queda sola a todo el ancho con la cifra mas grande. Fix: grilla
  explicita en movil o COMP-16.
- **LAY-08** (Medio) `app.css:740-748`; `01-entrada--375`, `R1-catalogo-real--375`.
  A 900 px o menos el stepper pasa a una segunda fila y se recorta ("3 Elegi
  que bajar" cortado, paso 4 fuera de vista) sin ningun indicio de que
  scrollea. Fix: en movil mostrar numeros y solo el rotulo del paso activo, o un
  degradado de borde que indique el corte.
- **LAY-09** (Medio) `05-catalogo--oscuro--768`. A 768 px la tabla conserva
  las siete columnas: los titulos parten en dos lineas y los badges tambien.
  Fix: por debajo de 1.000 px fusionar Tipo y Ano dentro de la celda Producto.
- **LAY-10** (Bajo) `app.css:564`. `padding-left: 88px` para alinear el
  detalle con la columna Producto: numero magico igual a 58 mas 30. Fix:
  SYS-04.
- **LAY-11** (Bajo) `app.css:245, 592-593`. Tres reglas de margen entre bloques
  (`.card + .card` 48, `.alerta + .card` 32, `.alerta + .alerta` 12) mas
  inline `margin-top:24px` en JS: el ritmo vertical se decide en cuatro lugares.
  Fix: SYS-02.

### 4. Color y contraste

Medido sobre los tokens (WCAG 2.x, ambos temas). Lo que pasa: texto principal
13 a 17:1, secundario 5.8 a 8:1, terciario 4.2 a 5.6:1, acento sobre boton
primario 5.7 a 6:1, foco 5.9 a 6.1:1, badges 5 a 7.6:1, alertas 6 a 15:1.

- **COL-01** (Alto) `app.js:783-785` contra `validar.py:190, 220`;
  `R1-catalogo-real` contra `R6-listo-real`. En la tabla "sin UPC" e "ISRC n de
  m" son `badge-danger` (rojo); en la validacion esas mismas condiciones son
  `aviso` (amarillo). Con el catalogo real, 9 de 10 filas quedan en rojo y el
  paquete termina con 0 errores. El rojo dice "rechazo" donde no lo hay. Fix:
  faltantes en `badge-warn`; rojo solo para lo que `validar.py` marca `error`.
- **COL-02** (Medio) `colors.css:71`, `app.css:369`. Borde de campo
  `--linea-fuerte` sobre fondo: 1.59:1 en oscuro, 1.65:1 en claro. WCAG 1.4.11
  pide 3:1 para limites de componentes. Fix: `--linea-fuerte: #4A5352` (3.0:1)
  en oscuro y `#A9A49B` en claro, o campos con fondo panel y borde solo en
  foco.
- **COL-03** (Medio) `app.css:221-226`. Numero de paso a 10 px con
  `opacity: .7` sobre texto-3: unos 2.9:1. Fix: sin opacidad, 11 px.
- **COL-04** (Alto) `app.css:495` y `530`; `R1-catalogo-real`. El hover de fila
  pinta `var(--panel)`, que es exactamente el fondo de `.tabla-wrap`: el hover
  no se ve en ninguna fila no elegida. Fix: `--panel-alto`.
- **COL-05** (Medio) `app.css:333-336`; `11-catalogo-vacio` (x=1350, y=772).
  Boton deshabilitado: transparente con borde `--linea` (1.22:1) y texto
  terciario. "Continuar" desaparece en vez de verse apagado. Fix: mismo boton
  con `opacity: .45`.
- **COL-06** (Medio) `app.css:486`, `app.js:818`. El tipo de producto (ALBUM,
  EP, SINGLE) va en badge con borde como si fuera un estado. Es un dato. Fix:
  texto mono sin borde en la celda Tipo.
- **COL-07** (Bajo) `app.css:443`. `.opcion.deshabilitada { opacity: .65 }`
  baja el contraste del texto secundario de 6.6:1 a unos 4.2:1. Fix: color
  terciario en vez de opacidad sobre todo el bloque.
- **COL-08** (Bajo) Paridad claro/oscuro: correcta en jerarquia y acento
  (medido). Sin hallazgo; queda registrado como Pass.

### 5. Componentes y estados

- **COMP-01** (Critico) `app.css:519-520`; `06-catalogo-detalle--oscuro--1440-completa`,
  `R2-catalogo-real-detalle--oscuro--1440-completa`. El numero de fila salta al
  expandir un producto (01, 02, 19, 20): `table.tabla tbody tr` tambien matchea
  las filas de `table.sub` porque son descendientes del `tbody` exterior, y la
  cabecera de la subtabla tambien cuenta. Fix:
  `table.tabla > tbody > tr:not(.fila-detalle) { counter-increment: fila }`.
- **COMP-02** (Critico) `app.js:1280-1303`. El actualizador en sitio del
  progreso cambia barra, `aria-valuenow`, mensaje, log y pie, pero no el
  `<span>` del porcentaje, que queda con el valor del primer render: en vivo se
  vio "5 %" junto a una barra al 90 %. Fix: `id="progreso-pct"` y actualizarlo.
- **COMP-03** (Alto) `app/server.py:557-568`. El armado del paquete reporta
  0.05 al empezar y 0.9 al zipear; toda la bajada de portadas (lo que mas tarda)
  transcurre con la barra clavada en 5 %. `M.preparar` recibe `log` sin
  fraccion. Fix: pasarle `progress` y repartir 0.05 a 0.85 por producto.
- **COMP-04** (Alto) `app.js:541-586`, `app.css:385`; captura en vivo del paso
  1 con link vacio (ver `02-entrada-error-cuota` para la posicion, y=643). El
  error "No se pudo relevar. Pega el link del canal." aparece 160 px debajo
  del campo, despues del aviso y del checkbox; el input no toma `.input.error`
  (definido y sin uso) ni el foco. Fix: errores de validacion como `hint` en
  negativo bajo el campo, clase `.error` y `focus()`; `bloqueError` solo para
  errores del servidor.
- **COMP-05** (Alto) `app.js:463-469`; `04-terminos`. La vista de terminos
  quita el stepper y el unico "Volver" esta al final de 1.500 px; el pie repite
  el link "Terminos de uso" que no hace nada estando ahi. Fix: Volver arriba a
  la derecha del titulo (y abajo), o terminos como panel lateral sobre la vista
  actual.
- **COMP-06** (Medio) `app.js:530-539` y `519-528`; `02-entrada-error-cuota`
  (y=585 y 718). Dos CTA con la misma intencion en pantalla: "Prefiero usar mi
  propia clave" y "Cargar mi propia clave". Fix: con error de cupo, el aviso de
  clave incluida no se muestra.
- **COMP-07** (Medio) `index.html:49`. "Terminos de uso" es `<a href="#">` con
  accion JS: para tecnologia asistiva es un link a la misma pagina, y con JS
  roto navega a `#`. Fix: `<button class="link-pie">`.
- **COMP-08** (Medio) `app.css:60-64, 375-379`. Los botones tienen anillo de
  foco de 2 px con offset; los campos lo apagan (`outline: none`) y dejan un
  cambio de borde de 1 px: el foco visible mas debil esta justo en lo que se
  tipea. Fix: `box-shadow: 0 0 0 3px color-mix(acento 25 %)` ademas del borde.
- **COMP-09** (Medio) Sin `:active` en ningun boton (`app.css:321-352`).
  Fix: `transform: translateY(1px)` con `--m-rapido`, y que la transicion
  incluya `transform`.
- **COMP-10** (Alto) `app.css:759-796`; `06-catalogo-detalle--claro--375`. La
  tabla en 760 px o menos se convierte en pares etiqueta / valor: indice,
  casilla y chevron en tres lineas, cinco lineas de datos por producto (unos
  230 px cada uno), y la subtabla de tracks en fichas de cinco lineas. Fix:
  disenar la ficha movil: casilla, titulo y badges en una linea; tipo, ano y
  UPC en una segunda linea mono; chevron a la derecha; tracks como lista de dos
  columnas.
- **COMP-11** (Medio) `app.css:396, 554, 175, 217`. Objetivos tactiles: casilla
  15 px (el `label` que la envuelve solo contiene el `.sr`, asi que el area
  real es la casilla), expandir 22 px, boton de tema 28 px, paso 26 px. WCAG
  2.5.8 pide 24 px minimos. Fix: area de 24 a 32 px con padding; ver UX-01.
- **COMP-12** (Medio) `app.js:656-662`, `app.css:291-317`; `05-catalogo`,
  `17-listo`. La tira de metricas es la "plantilla de metrica" que `DESIGN.md`
  seccion 9 prohibe y que `app.css:287` niega estar usando. Cinco cifras a 28 px
  para datos que se leen una vez y despues sobran. Fix: una linea de lectura
  ("10 productos, 46 tracks. UPC en 5, ISRC en 19 de 46.") bajo el titulo, y
  cifra grande solo donde la magnitud importa (errores y avisos del paso 4).
- **COMP-13** (Medio) `app.js:1026-1043`; `R7-listo-real-avisos--1440-completa`.
  41 avisos en filas planas, 30 de ellas "sin ISRC" repetidas; la tabla tiene
  340 px y scroll propio. Fix: agrupar por tipo con contador ("Sin ISRC, 30
  tracks en 8 productos") desplegable a los productos; sin scroll interno.
- **COMP-14** (Medio) `app.js:995-1008`; `17-listo`. La accion primaria
  ("Descargar") esta arriba, y la barra de accion de abajo lleva dos acciones
  secundarias: la barra de accion no tiene accion. Fix: Descargar tambien en
  la barra (o solo ahi), con las secundarias a la izquierda.
- **COMP-15** (Medio) `app.js:699-703`. El segmented mezcla un modo de
  seleccion ("Uno por uno") con dos filtros ("Por fecha", "Por distribuidora")
  bajo `aria-label="Modo de seleccion"`. Fix: "Todos / Por ano / Por
  distribuidora" como filtros, y la seleccion manual siempre disponible.
- **COMP-16** (Bajo) `app.js:362-369`. El esqueleto son cuatro barras que no
  imitan la pantalla que viene (titulo de 42, campo de 42, boton). Fix:
  esqueleto con la silueta real del paso 1.
- **COMP-17** (Bajo) `app.css:639-646`. Spinner de borde giratorio, el mas
  generico posible, en la unica pantalla donde la app pide paciencia. Fix: ver
  propuesta C-3.
- **COMP-18** (Bajo) `app.js:173-185`. El boton de tema es sol / luna sin
  rotulo visible. redesign-skill lo lista como cliche; es menor. Fix: tooltip
  ya existe; opcional un `aria-pressed` o un segmented "Claro / Oscuro" en el
  pie.
- **COMP-19** (Bajo) `app.css:487` y `app.js:821`. Los badges se separan con un
  espacio en el HTML y ademas con `margin-left`: doble separacion. Fix: gap en
  el contenedor.
- **COMP-20** (Bajo) `app.css:60-64`. `:focus-visible` global fuerza
  `border-radius: 8px` al anillo, incluso sobre la casilla cuadrada (radio 4) y
  sobre filas. Fix: `border-radius: inherit`.

### 6. Motion

- **MOT-01** (Medio) COL-04: el componente central no responde al puntero.
- **MOT-02** (Medio) `app.js:302-336`. Cada cambio de estado (marcar una
  casilla, tipear en el buscador) reemplaza el `innerHTML` de toda la vista; el
  foco y el scroll se restauran a mano (`tomarFoco`, `conScrollPreservado`).
  No hay transicion de nada porque no hay nada que transicionar: el DOM es
  nuevo cada vez. Es una restriccion de arquitectura, no un bug; condiciona
  las propuestas de C (todo lo que anime tiene que sobrevivir al re-render o
  animarse por CSS a partir de clases).
- **MOT-03** (Bajo) `app.css:560-561`. El chevron rota bien; la fila de
  detalle aparece de golpe. Fix: C-2.
- **MOT-04** (Bajo) `app.css:621-628`. La barra anima `transform` en 600 ms:
  correcto. Con COMP-03 el unico movimiento visible es un salto de 5 a 90.
- **MOT-05** (Pass) `app.css:730-736`. `prefers-reduced-motion` frena spinner
  y esqueleto y acorta transiciones. No hay `scroll` listeners a mano ni
  animaciones sobre `top/left/width/height`.
- **MOT-06** (Bajo) Sin feedback al completar el relevamiento: la vista cambia
  de golpe del progreso al catalogo. Fix: C-5.

### 7. Iconografia, imagenes y graficos

- **ICO-01** (Medio) `app.js:44-58`. Trece iconos SVG escritos a mano; por los
  paths son copias de Lucide (`m9 18 6-6-6-6`, el check-circle, el sol). El
  skill prohibe iconos a mano y desaconseja Lucide; aca no hay alternativa
  porque la CSP no permite CDN y una libreria entera por trece glifos no se
  justifica. Fix: mantenerlos, pero declarar origen y licencia (Lucide, ISC) en
  el comentario del bloque y en README, y unificar en un solo archivo de
  iconos.
- **ICO-02** (Bajo) `app.css:111-117`. Trazo 1.5 uniforme, tamanos 16 y 13:
  consistente. Pass.
- **ICO-03** (Bajo) `index.html:19`. El logo inline de 74 puntos a 24 px: en
  `R1-catalogo-real--375` (2x) se lee; a 1x los puntos de 0.5 de radio
  desaparecen. Fix: usar la variante compacta de `build/icono.py` por debajo de
  28 px.
- **ICO-04** (Pass) Favicon presente (`assets/icono.png`).

### 8. Microcopy y contenido

- **COPY-01** (Alto) Guiones largos (U+2014) y cortos (U+2013), contados:
  `app.js` 2 (comentarios), `app.css` 1, tokens 4, `TERMINOS.md` 1,
  `README.md` 3, `PRODUCT.md` 1, `DESIGN.md` 7, `relevar_core.py` 12 + 3,
  `validar.py` 4, `paquete.py` 7, `migrar_core.py` 3, `productos.py` 2,
  `portadas.py` 3 + 1. De estos, los de `relevar_core.py` y `paquete.py` estan
  en mensajes que llegan al log de la UI y a los reportes del ZIP. Fix: barrido
  completo con `grep -P "[\x{2014}\x{2013}]"` y reemplazo por coma, punto o dos
  puntos. **Decision tuya**: `TERMINOS.md` es texto legal preservado; tiene un
  guion largo (linea a confirmar) y la version que muestra la app
  (`app.js:381-447`) no lo tiene.
- **COPY-02** (Alto) `relevar_core.py:314, 357`; `R1-catalogo-real`. El sello
  "5358533 Records DK" aparece en las 10 filas como si fuera un sello. Es el
  placeholder que DistroKid pone cuando el artista no declara sello; el parser
  ya lo reconoce para el ano y lo deja pasar como sello. Fix: normalizar a
  sello vacio y mostrar "sin sello" en la celda y en la validacion.
- **COPY-03** (Medio) `validar.py:140-222` contra `build/capturas.py:220-230`;
  `R7-listo-real-avisos` contra `18-listo-avisos`. Los mensajes reales de
  validacion son fragmentos en minuscula con parentesis ("sin UPC: la
  distribuidora va a asignar uno nuevo (se pierde la continuidad del release)")
  y los del fixture, que son los del README, son oraciones ("Falta el UPC. Sin
  ese codigo..."). La app nunca produce lo que muestran sus capturas. Fix:
  reescribir los mensajes de `validar.py` como oraciones y regenerar fixture y
  README con los mismos textos.
- **COPY-04** (Medio) `R5-progreso-real`. El log muestra jerga de desarrollo:
  "[productos] 10 productos a partir de 46 tracks", "[zip] 2026 - Breathless
  [883369951660]", "Deezer: 19/46 matcheados", "-> ok 3000x3000 (match upc)".
  Fix: mensajes en voz de producto para las lineas que llegan a la UI
  ("Portada de Breathless: no esta en Apple Music") y prefijos fuera.
- **COPY-05** (Medio) `app.js:189, 854`. "Elegi que bajar" (stepper) y "Que
  queres descargar?" (titulo) para la misma cosa; "Descarga" (stepper) y "Tu
  paquete esta listo" (titulo). Fix: un verbo, "descargar".
- **COPY-06** (Medio) `app.js:693-695, 721-723`; `05-catalogo`. "4 DE 4" a la
  derecha de la etiqueta es productos mostrados sobre total, y "4 de 4
  productos elegidos" abajo es elegidos sobre mostrados: dos "4 de 4" con
  sentidos distintos a 300 px de distancia. Fix: "Mostrando 4 de 4" arriba.
- **COPY-07** (Medio) `app.js:833`. La columna se llama "Pendientes", que
  sugiere una tarea a hacer en la app, y no se puede hacer nada desde ahi. Fix:
  "Faltantes" mas una linea de leyenda bajo la tabla.
- **COPY-08** (Bajo) `app.js:726-727`. "Marcar todo" / "Desmarcar":
  asimetricos. Fix: "Marcar todos" / "Desmarcar todos", o un solo toggle.
- **COPY-09** (Bajo) `app.js:995-997`. El rotulo del boton primario es el
  nombre del archivo ("Descargar SanticuadoQ-migracion.zip"): largo variable y
  poco legible. Fix: "Descargar el paquete (7,8 MB)" y el nombre en el
  subtitulo.
- **COPY-10** (Bajo) `app.js:1048` y `relevar_core.py`. Punto medio como
  separador ("0 ERRORES · 41 AVISOS"; "Deezer: 19/46 matcheados · UPC de 5
  albumes..."). Dentro del limite del skill (uno por linea), pero en el log se
  suma a los puntos suspensivos. Fix: coma.
- **COPY-11** (Bajo) `app.js:1014, 1024`. "Validacion sin observaciones. No
  encontre nada de lo que las distribuidoras suelen rechazar." y "Sin errores de
  rechazo. Hay 41 avisos para revisar.": primera persona en un lugar y no en el
  otro; el resto de la app habla en segunda. Fix: quitar la primera persona.
- **COPY-12** (Pass) Tildes, vos y mayusculas de oracion: correctos en toda la
  UI revisada. Los titulos en MAYUSCULAS son del catalogo y no se tocan.

### 9. Responsive

- **RESP-01** (Alto) COMP-10, la tabla apilada.
- **RESP-02** (Medio) LAY-08, el stepper recortado.
- **RESP-03** (Medio) LAY-06, la barra de accion.
- **RESP-04** (Medio) LAY-09, las columnas a 768.
- **RESP-05** (Medio) LAY-07, las metricas a 375.
- **RESP-06** (Bajo) LAY-02, la columna a 1.920.
- **RESP-07** (Pass) Sin desborde horizontal a 375 (medido en vivo:
  `document.scrollWidth` 375). El shell pierde margen y radio por debajo de
  900, como corresponde.

### 10. Slop tells

- **SLOP-01** (Alto) Etiquetas en versalitas mono con tracking arriba de casi
  todo: `.seccion-etiqueta` (3 por flujo), `.doc h4` (7 en terminos),
  `.kpi-label` (5 + 4), `.field label`, `summary` de acordeon, `.header-title`,
  `thead th`, etiquetas moviles. Mas de veinte por pantalla. taste-skill 4.7
  ("EYEBROW RESTRAINT", una cada tres secciones) y `DESIGN.md` seccion 9
  ("Etiqueta o versalita arriba de un titulo") lo prohiben, y sin embargo
  `DESIGN.md` seccion 1 la consagra como "la regla". Fix: versalitas solo donde
  son datos (cabeceras de tabla, badges); secciones con `h2` Archivo 22;
  rotulos de campo en sentence case 13 px; terminos con `h3` sans 16 px.
- **SLOP-02** (Alto) COMP-12, la plantilla de metrica.
- **SLOP-03** (Alto) SYS-01, el negro puro.
- **SLOP-04** (Medio) `app.css:169-171`; toda cabecera. "v1.0.0" en la
  cabecera del producto compite con el stepper; el skill lo veta en marketing
  y en una app es legitimo pero no en el chrome principal. Fix: al pie, junto
  a "Hecho por".
- **SLOP-05** (Medio) COL-06, badge para un dato.
- **SLOP-06** (Medio) `app.css:537-544`; `R1-catalogo-real`. La numeracion
  "01 02 03" en teal: con la seleccion casi siempre completa, es una columna
  entera de acento a 10 px que no marca nada (todas estan elegidas). Fix:
  indice en terciario siempre; el acento queda para la casilla.
- **SLOP-07** (Bajo) ICO-01, iconos Lucide.
- **SLOP-08** (Bajo) COMP-18, sol / luna.
- **SLOP-09** (Pass) Sin gradientes, sin vidrio, sin sombras de color, sin
  tres tarjetas iguales, sin emojis, sin nombres de relleno.

### 11. UX y flujos

- **UX-01** (Alto) COL-04 y COMP-11; `R1-catalogo-real`. Para elegir un
  producto hay que apuntar a una casilla de 15 px, la fila no es clickeable y
  el hover no se ve. Es la interaccion que mas se repite en la app. Fix: fila
  entera clickeable (salvo el chevron), hover en `--panel-alto`, casilla con
  area de 32 px.
- **UX-02** (Alto) COL-01 y COPY-07. La primera impresion del catalogo real es
  una columna de rojo que no significa rechazo.
- **UX-03** (Medio) LAY-03 y COMP-12; `05-catalogo`. A 1.440 x 900 la tabla
  empieza a los 530 px: el usuario abre el paso 2 y ve titulo, cinco cifras y
  dos avisos antes del primer producto. Fix: los dos hallazgos citados.
- **UX-04** (Medio) `app.js:530-539`; `01-entrada` de la variante completa. El
  aviso de "clave incluida" con su boton se muestra en cada arranque a quien no
  tiene ningun problema. Fix: una linea en el pie de la vista con link, y el
  bloque completo solo con error de cupo.
- **UX-05** (Medio) `app.js` acciones `volver-1`. "Relevar otro artista"
  descarta un catalogo que costo cupo sin preguntar ni avisar que el servidor lo
  conserva hasta el proximo relevamiento. Fix: aviso inline de una linea con
  "Volver al catalogo" durante el paso 1, mientras `S.catalogo` exista.
- **UX-06** (Medio) `app.js:775-838`. La tabla no ordena por columna. Con 10
  productos no hace falta; con 60 (un sello) si. Ver C-8.
- **UX-07** (Medio) COMP-05, terminos sin salida arriba.
- **UX-08** (Medio) COMP-04, error de validacion lejos del campo.
- **UX-09** (Bajo) COMP-06, doble CTA.
- **UX-10** (Bajo) COMP-15, filtros y modo mezclados.
- **UX-11** (Pass) Volver atras conserva estado; Enter envia en `#url` y
  `#clave`; el catalogo sobrevive a un F5; los trabajos se pueden cancelar;
  los errores del servidor dicen que paso y que hacer (cupo, clave).

### 12. Performance percibida y accesibilidad basica

- **PA-01** (Medio) `app.js:162-176`, `index.html:56`. El tema se aplica desde
  `app.js`, al final del `body`: en tema claro el primer frame se pinta oscuro
  y cambia. La ventana es corta porque todo es local, pero es estructural.
  Fix: un `<script>` inline de tres lineas en `<head>` que lea `localStorage`
  y ponga `data-theme` antes de que cargue el CSS.
- **PA-02** (Pass) CLS medido 0 en recarga; fuentes locales con `swap`;
  `domContentLoaded` 33 ms.
- **PA-03** (Medio) `app.js:596-610`. `role="progressbar"` sin nombre
  accesible y `#progreso-mensaje` sin `aria-live`: un lector de pantalla no se
  entera del avance. Fix: `aria-label="Avance del trabajo"` y
  `aria-live="polite"` en el mensaje.
- **PA-04** (Medio) `app.js:699-703`. Botones del segmented sin
  `aria-pressed`: el estado activo es solo visual. Fix: `aria-pressed`.
- **PA-05** (Medio) COMP-11, objetivos tactiles.
- **PA-06** (Bajo) `index.html:6`. `<title>` fijo; no dice en que paso esta ni
  que artista. Fix: "Santicuado.Q, elegir productos - Migrador de Catalogos".
- **PA-07** (Bajo) `app.js:829-833`. `<th>` sin `scope="col"`. Fix: agregar.
- **PA-08** (Pass) Orden de tabulacion correcto y anillo de foco visible en
  botones, casillas y expandir (verificado en vivo); `.sr` en casillas de
  fila y expandir; `aria-expanded` en el chevron; `lang="es"`.
- **PA-09** (Bajo) `app.js:570-576`. El arbol de accesibilidad expuso la
  casilla "Buscar codigos ISRC y UPC" con nombre "on" en una lectura; las de la
  tabla, que usan `.sr`, salieron bien. Conviene `aria-labelledby` explicito
  para cerrar la duda.

---

## C. Propuestas de mejora estetica

Todas con CSS nativo, sin dependencias: la CSP no permite CDN y no hay build.
Impacto sobre la percepcion de calidad; esfuerzo S / M / L.

- **C-1. La fila como unidad viva** (impacto alto, S). Fila entera
  clickeable, hover en `--panel-alto` con transicion de 100 ms, la marca de
  registro (indice) pasa de terciario a acento solo en la fila elegida, y la
  casilla dibuja el tilde con `stroke-dashoffset` en 120 ms. Resuelve UX-01,
  COL-04, SLOP-06 y le da a la app su micro-momento propio.
- **C-2. Despliegue del detalle** (medio, S). `tr.fila-detalle > td >
  .detalle-inner` con `display: grid; grid-template-rows: 0fr` a `1fr` en
  180 ms mas opacidad; el chevron ya rota. Sobrevive al re-render porque la
  clase `abierto` la pone el render y la transicion arranca al insertarse
  (`@starting-style`).
- **C-3. El trabajo largo como el unico momento con autoria** (alto, M).
  Reemplazar el spinner por la variante compacta del logo (9 puntos) latiendo
  en secuencia; la barra con fase y porcentaje reales (COMP-02, COMP-03); el
  log ocupa el alto disponible y las lineas nuevas entran con un fade de
  120 ms; al completar, un check que se dibuja y 400 ms despues la vista
  siguiente. Es la unica animacion que `DESIGN.md` seccion 7 autoriza, y hoy es
  la mas pobre.
- **C-4. Feedback tactil** (medio, S). `:active` con `translateY(1px)` en
  botones y `scale(.98)` en casillas; 100 ms.
- **C-5. Cambio de paso** (medio, S). `#pantalla` con `@starting-style`
  `opacity: 0; translate: 0 4px` a `1; 0` en 180 ms cuando cambia `S.paso`
  (no en cada re-render: una clase `entrando` que el render pone solo al
  cambiar de paso). Apagado con reduced-motion.
- **C-6. Cabecera con el lockup** (medio, S). El lockup de `docs/marca`
  (simbolo mas nombre en Archivo) reemplaza al par simbolo mas versalitas mono
  (TYP-05). Version al pie (SLOP-04).
- **C-7. Sombra de scroll en la cabecera de la tabla** (bajo, S). Una linea
  de sombra bajo el `thead` sticky que aparece solo cuando hay contenido
  arriba, con `animation-timeline: scroll()`; da profundidad sin sombra
  decorativa.
- **C-8. Orden por columna** (medio, M). Click en cabecera para ordenar por
  titulo, ano, tipo o faltantes; flecha mono de 10 px en la cabecera activa.
- **C-9. Validacion agrupada** (alto, M). Avisos y errores como grupos con
  contador y desplegable por producto (COMP-13); chips de filtro ("Sin ISRC
  30", "Orden estimado 5") que filtran la tabla. Convierte 41 filas en cinco
  lineas legibles.
- **C-10. Ficha movil** (alto, L). COMP-10: la tabla en 760 px o menos como
  lista de fichas de dos lineas con badges, y tracks en dos columnas.
- **C-11. Lo que NO propongo.** Grano o textura de fondo, sombras de color,
  vidrio, entradas escalonadas en cada seccion y marquesinas: redesign-skill
  las sugiere y `DESIGN.md` secciones 1 y 9 las excluyen con razon para una
  herramienta de inventario. Tampoco fotografia: no hay lugar para una imagen
  en esta app.

---

## D. Lo que se preserva sin tu aprobacion explicita

- Rutas del servidor (`/api/*`) y sus cuerpos; el token y el control de `Host`.
- Nombres y orden de los campos: `#url`, `#clave`, `#buscar`, `#con-codigos`,
  `#anio-desde`, `#anio-hasta`, `#check-todos`; los `data-accion`,
  `data-prod`, `data-expandir`, `data-modo`, `data-opcion`, `data-distrib`.
- Los cuatro pasos y sus nombres en el stepper (`PASOS`, `app.js:189`).
- Los textos legales: `TERMINOS.md` y `textoTerminos()` (`app.js:381-447`).
- La logica de negocio: `relevar_core.py`, `productos.py`, `validar.py`,
  `paquete.py`, `migrar_core.py`, `portadas.py`, `audio.py`. Las unicas
  excepciones propuestas, cada una pidiendo permiso: la fraccion de progreso
  en `server.py` (COMP-03), el sello placeholder de DistroKid (COPY-02), los
  mensajes de `validar.py` (COPY-03) y los del log (COPY-04, COPY-01).
- El logo (`docs/marca`, el SVG inline y `build/icono.py`), el teal como unico
  acento, grafito y hueso, las tres tipografias.
- El link a LinkedIn y el texto "Hecho por Joaquin Garcia Oliver".
- Oscuro por defecto.
- La CSP, sin CDN ni recursos externos.
