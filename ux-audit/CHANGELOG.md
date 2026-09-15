# Auditoria UI/UX: lo que se hizo (Fase 5, cierre)

Del 2026-09-14 al 2026-09-15, sobre `main`. Punto de partida `8ab1130`.
La auditoria escrita esta en `AUDIT.md` (105 hallazgos), el plan en `PLAN.md`,
el mapa de la app en `MAPA.md`. Capturas antes y despues en `before/` y
`after/` (no van al repo: 24 MB de PNG, estan gitignoreadas).

Modo: **Preserve**. Dials: variancia 3, movimiento 2 a 3, densidad 7.

---

## Por lote

### Lote 1, tokens y sistema (`29f18bd`)

- Lienzo `#000000` a `#050707`. El negro puro esta prohibido por el skill y por
  redesign-skill, y no hacia falta: el escalon contra la superficie de la app
  se mantiene igual.
- Borde de control de 1.6:1 a 2.3:1 (`#343B3A` a `#4A5352`, y `#C6C2BA` a
  `#A9A49B` en claro). WCAG 1.4.11 pide 3:1; los 2.3 que da hoy sobre el fondo
  son el techo sin que el borde se vuelva una linea dura sobre el panel. Queda
  anotado abajo como pendiente.
- Los cinco usos de 10 px pasan a 11: no existia ese tamano en la escala.
- Boton deshabilitado: de "transparente con borde invisible" a media opacidad.
  Antes "Continuar" desaparecia en vez de verse apagado.
- Numero de paso sin `opacity: .7` encima del terciario (daba 2.9:1).
- Medida de lectura de 68ch a 58ch: `ch` mide el cero, que es mas ancho que la
  media, y 68 daban 85 caracteres reales.
- `h2` con su propio tracking (-0.02em); el de display es para 30 px o mas.
- Los 44 `style="..."` de `app.js` pasan a clases con la escala de espaciado.
- Anchos de columna de la tabla como tokens (`--w-indice`, `--w-expandir`), y
  el padding del detalle calculado a partir de ellos en vez de un 88 px magico.
- `DESIGN.md` y `README.md` al dia: las tablas de radios, superficies y escala
  decian otra cosa que los tokens, y el README remitia a `DESIGN-SYSTEM.md`,
  que ya no es la fuente.

### Lote 2, bugs y semantica (`940d7e1`)

Dos bugs que se veian:

- **La numeracion de filas saltaba** al expandir un producto (01, 02, 19, 20).
  `table.tabla tbody tr` tambien alcanzaba a las filas de la subtabla de
  tracks, que es descendiente del mismo `tbody`. Ahora es
  `> tbody > tr:not(.fila-detalle)`.
- **El porcentaje del progreso nunca se actualizaba.** El actualizador en sitio
  tocaba barra, mensaje, log y pie, pero no el `<span>` del porcentaje: en vivo
  se vio "5 %" al lado de una barra al 90 %.

Y uno que no se veia pero mentia:

- **La barra se quedaba en 5 % durante casi todo el armado.** `server.py`
  reportaba 0.05 al empezar y 0.9 al zipear, y toda la bajada de portadas (lo
  que mas tarda) pasaba sin avance. Ahora la fraccion sale de las propias
  lineas de `preparar`, entre 0.05 y 0.85.

Semantica y estados:

- **Los codigos que faltan son avisos, no errores.** En la tabla "sin UPC" e
  "ISRC n de m" estaban en rojo; en la validacion, esas mismas condiciones son
  avisos. Con el catalogo real, 9 de 10 filas quedaban rojas y el paquete
  terminaba con 0 errores. El rojo queda para lo que `validar.py` marca error.
- El hover de fila pintaba exactamente el fondo de la tabla: no se veia.
- El error de validacion del link aparecia 160 px debajo del campo, sin
  marcarlo. Ahora va como hint en negativo bajo el campo, con foco y
  `aria-describedby`, y se limpia al tipear.
- Terminos con "Volver" arriba; antes el unico estaba al final de 1.500 px.
- El aviso de clave incluida no compite con el error de cupo (eran dos botones
  con la misma intencion en pantalla).
- `:active` en botones, foco de campo con el mismo peso que el de botones,
  objetivos tactiles de 22 y 28 px a 28 y 32.
- El tema se decide en `tema.js`, cargado en `head`: antes el primer frame en
  claro salia oscuro. Va en archivo y no inline porque la CSP no permite
  scripts inline (lo descubri cuando la consola lo bloqueo).
- `aria-live` en el mensaje de progreso, `aria-label` en la barra,
  `aria-pressed` en el segmentado, `scope="col"` en las cabeceras, titulo de
  documento por paso y artista.

Contenido:

- **El sello de relleno de DistroKid ya no se muestra como sello.**
  "5358533 Records DK" aparecia en las 10 filas del catalogo real como si fuera
  un sello: es el id de cuenta que DistroKid pone cuando el artista no declaro
  ninguno. El parser ya lo reconocia para el ano; ahora tambien lo descarta
  como sello. Test de regresion actualizado.
- Los mensajes de `validar.py` pasan de fragmentos en minuscula con parentesis
  a oraciones. Los del log hablan en voz de producto: se fueron los prefijos
  `[portadas]`, `[zip]`, `[productos]`, los `->` y los "matcheados".
- **Cero guiones largos y cortos en todo el repo versionado**, incluidos los
  mensajes de Python que llegan al log de la UI y a los reportes del ZIP.

### Lote 3, composicion y jerarquia (`42d6bf8`)

Es el lote que mas cambia lo que se ve.

- **Fuera las versalitas como estructura.** Habia mas de veinte etiquetas mono
  en versalitas por pantalla: titulos de seccion, subtitulos de terminos,
  etiquetas de metrica, rotulos de campo, cabeceras de acordeon, la marca. El
  skill permite una cada tres secciones y `DESIGN.md` las prohibia en su
  seccion 9 mientras las consagraba en la 1. Ahora los titulos de seccion son
  `h2` en Archivo, los rotulos de campo van en caja normal, y el mono en
  versalitas queda para lo que es dato: cabeceras de tabla, badges, contadores.
- **La tira de cinco metricas a 28 px pasa a una oracion** con las cifras en
  mono. Era la "plantilla de metrica" que `DESIGN.md` prohibe y que el propio
  CSS negaba estar usando en su comentario. Se leen una vez; lo que importa
  despues esta en la tabla.
- **Se acabo el scroll dentro del scroll.** La tabla tenia 58vh, el log 180 px
  y la validacion 340: tres areas con scroll propio dentro de un `main` que
  tambien scrollea. Con 10 productos la tabla mostraba 6.
- **La columna de lectura se alinea con el resto de la app.** Paso 1, clave y
  terminos estaban centrados en 760 px mientras cabecera, pie y paso 2 usaban
  todo el ancho: el titulo cambiaba de lugar al pasar del paso 1 al 2. Ancho de
  app de 1440 a 1280.
- **La validacion se agrupa por tipo de hallazgo.** 41 avisos en filas planas,
  30 de ellas "sin ISRC" repetida, pasan a cuatro grupos con contador ("Sin
  ISRC, 27 tracks en 9 productos") que se despliegan a la lista de productos en
  dos columnas.
- La descarga esta en la barra de accion, que antes solo tenia secundarias.
- La marca en la cabecera pasa de mono versalitas a Archivo; la version, al pie.
- El tipo de producto (ALBUM, EP, SINGLE) deja de ser un badge con borde: es un
  dato, no un estado.
- Las alertas tienen medida de lectura (corrian a 180 caracteres por linea).
- Los filtros se llaman filtros ("Todos / Por ano / Por distribuidora"), y la
  columna "Pendientes" pasa a "Faltantes" con una leyenda que dice que eso se
  completa en la distribuidora nueva.

### Lotes 4 y 5, movimiento y estados (`21e8380`)

- **La fila entera elige el producto.** Era la interaccion mas repetida de la
  app y habia que apuntar a una casilla de 15 px.
- El tilde de la casilla se dibuja; el detalle se despliega con
  `@starting-style` (el DOM es nuevo en cada render, asi que no hay transicion
  posible desde un estado anterior); la vista entra con un fade solo al cambiar
  de paso, no en cada marcado.
- **El trabajo largo es el unico momento con autoria**, que es lo que
  `DESIGN.md` seccion 7 autoriza y lo que estaba peor resuelto: el spinner de
  borde giratorio pasa a tres puntos del logo latiendo en secuencia, las lineas
  nuevas del log entran con un fade, y al terminar el latido se apaga, aparece
  un tilde y medio segundo despues cambia la vista.
- Esqueleto con la silueta real del paso 1.
- "Marcar todos" y "Desmarcar todos" aparecen solo cuando tienen sentido.

### Cierre: se borro la version para telefono

A pedido tuyo, y con razon: es una app de escritorio que se abre en una ventana
propia. Se fue el bloque de 760 px entero (la tabla convertida en fichas), los
`data-col` que solo ese CSS leia, y las reglas de cabecera que eran para un
telefono. Queda un unico breakpoint a 900 px para cuando alguien achica la
ventana: el chrome no se rompe y la tabla scrollea en horizontal, que es lo que
hace cualquier programa con una grilla. El harness de capturas ya no fotografia
375 px.

---

## Pre-Flight Check del skill

Solo los items que aplican. El propio skill declara fuera de alcance
"dashboards, data tables, multi-step product UI" (seccion 13), que es
exactamente esta app: los items de landing (hero, bento, marquee, logo wall,
eyebrow por seccion, zigzag, testimonios, imagenes reales) no se evaluan y se
marcan N/A, no Pass.

| Item | Estado | Por que |
|---|---|---|
| Brief inference declarado | Pass | En `AUDIT.md`, seccion A |
| Dials explicitos y razonados | Pass | 3 / 2-3 / 7, con la lectura del estado previo |
| Modo de redesign detectado y auditoria hecha | Pass | Preserve, auditoria de 105 hallazgos antes de tocar codigo |
| Cero guiones largos | Pass | Verificado sobre todo el repo versionado, archivo por archivo |
| Page Theme Lock | Pass | Un solo tema por vez, con toggle; ninguna seccion se invierte |
| Color Consistency Lock | Pass | El teal es el unico acento; los semanticos solo comunican estado |
| Shape Consistency Lock | Pass | 4 / 8 / 14 / 18 documentados y aplicados |
| Button Contrast Check | Pass | Primario 5.97 en oscuro, 5.72 en claro |
| CTA sin wrap en escritorio | Pass | Verificado en las capturas de 1440 y 1920 |
| Form Contrast Check | Pass | Campos, placeholder, hint y error medidos; el minimo es 4.56 |
| Serif discipline | N/A | No hay serif |
| Reduced motion | Pass | `prefers-reduced-motion` apaga latido, esqueleto, entradas y el cierre del trabajo |
| Dark mode probado en ambos modos | Pass | Las 27 vistas en los dos temas, en `after/lote-final/` |
| Empty, loading y error states | Pass | Vacio por filtro, esqueleto, error fatal, error de cupo, error de campo |
| Cards omitidas en favor de espaciado | Pass | `.card` no dibuja nada; la separacion la hacen superficie y radio |
| Iconos de libreria permitida | **Fail asumido** | 13 SVG a mano (paths de Lucide). La CSP prohibe CDN y una libreria entera por 13 glifos no se justifica. Queda declarado abajo. |
| Motion motivado | Pass | Cuatro animaciones, cada una con una razon en una oracion |
| Sin `window.addEventListener('scroll')` | Pass | No hay ninguno |
| Sin AI tells de la seccion 9 | Pass | Sin gradientes, vidrio, sombras de color, tres tarjetas iguales, emojis, nombres de relleno, puntos de estado decorativos, tiras de locale |
| Copy self-audit | Pass | Todos los strings visibles releidos; los de validacion y log reescritos |
| Un solo sistema de diseno | Pass | Tokens propios, sin libreria |
| Core Web Vitals | Pass | CLS 0 medido, `domContentLoaded` 33 ms, fuentes locales |

**El unico Fail es deliberado y esta declarado**: los iconos. No bloquea el
cierre porque la alternativa que pide el skill (instalar Phosphor o Tabler) es
imposible con la CSP de esta app, y hacerlos a mano era la unica salida. Lo que
falta es el credito de licencia, que esta abajo como pendiente.

## Auditoria de guiones

Cero U+2014 (guion largo) y cero U+2013 (guion corto) en todo el repo
versionado: codigo,
interfaz, comentarios, documentacion, textos legales y los mensajes de Python
que llegan al log y a los reportes del ZIP. Verificado archivo por archivo, no
por muestreo.

La unica excepcion es `docs/marca/`, que son el `Logo.jsx` y el README del
paquete de marca tal como vinieron del estudio. No los toque a proposito: es
material recibido, no codigo de la app, y reescribirle la puntuacion a una
entrega ajena para pasar un check propio no tiene sentido.

## Auditoria de preservacion

Comparado contra `8ab1130`, ids, atributos `data-*`, rutas y links:

- **Rutas del servidor**: identicas, las 12.
- **Ids y `data-*`**: cinco agregados (`bloque-progreso`, `con-codigos-l`,
  `progreso-pct`, `url-error`, y `hidden` en dos botones). Ninguno renombrado,
  ninguno borrado. Los campos siguen siendo `#url`, `#clave`, `#buscar`,
  `#con-codigos`, `#anio-desde`, `#anio-hasta`, `#check-todos`.
- **Un label de navegacion cambio**, y fue a proposito: el paso 3 pasa de
  "Elegi que bajar" a "Elegi que descargar", porque el titulo de esa pantalla
  ya decia "descargar" (COPY-05).
- **Textos legales**: `TERMINOS.md` cambio un caracter, el guion largo del
  encabezado por una coma. El cuerpo no se toco. La copia que muestra la app
  (`textoTerminos()`) tampoco.
- **Rotulos de columna**: "Pendientes" pasa a "Faltantes". Es contenido de la
  interfaz, no un contrato: nada downstream lo lee.

## Auditoria de fidelidad de marca

- **Acento**: el teal sigue siendo el unico, y la rampa no se toco
  (`--teal-500: #387F7E`).
- **Tipografias**: Archivo, Geist y Geist Mono, las tres, hospedadas
  localmente. Lo que cambio es cuanto se apoya la interfaz en el mono, que baja
  de estructural a dato.
- **Logo**: el SVG inline no se modifico; lo que cambio es el texto que lo
  acompana, que pasa de mono versalitas a Archivo.
- **Link a LinkedIn y "Hecho por"**: intactos, en el pie.

## Auditoria de contraste

Medida sobre los tokens finales, contra las cuatro superficies (fondo, panel,
cabecera de tabla, fila elegida) y contra el tinte de cada alerta:

| Tema | Minimo global | Estado |
|---|---|---|
| Oscuro | 4.56 | Pass (AA) |
| Claro | 4.64 | Pass (AA) |

Dos valores se corrigieron en el cierre, porque la fila en hover es una
superficie mas clara que la que se habia medido: `--texto-3` de `#828887` a
`#898F8E` (daba 4.16) y `--negativo` de `#E3645E` a `#E56660` (daba 4.46).

## Recorrido final

Sobre la app corriendo, no sobre las capturas: la fila entera selecciona y
deselecciona, el detalle despliega los tracks con la numeracion correcta
(01, 02, y la fila de detalle no cuenta), el tema va y vuelve, los terminos
abren y cierran desde el pie, el error del campo aparece y se limpia al tipear.
Cero errores de consola. Los 9 tests pasan.

---

## Lo que queda pendiente, y por que

1. **Credito de los iconos.** Los 13 SVG son paths de Lucide (ISC). Falta
   declararlo en el comentario del bloque y en los creditos del README. Es lo
   correcto y es de cinco minutos.
2. **Borde de control a 3:1.** Hoy da 2.3. Llegar a 3 sobre el fondo hace que
   el mismo borde se vuelva una linea dura sobre el panel. Se resuelve bien con
   dos tokens de borde, uno por superficie, no subiendo el que hay.
3. **Orden por columna en la tabla** (C-8 del audit). Con 10 productos no hace
   falta; con el catalogo de un sello, si.
4. **El log del relevamiento** todavia tiene lineas tecnicas que no reescribi
   porque salen de `relevar_core` y tocaban mas de lo que el lote pedia.
5. **Los hallazgos de telefono se cerraron borrando la funcionalidad**, no
   arreglandola: COMP-10, LAY-06, LAY-07, RESP-01 a RESP-05 del audit quedan
   como historia, no como deuda.
6. **Sin ejercitar**: la descarga del ZIP (requiere permiso explicito), la
   cancelacion de un trabajo largo (los de prueba duraron menos de 40 s) y
   Tidal real (necesita cuenta paga propia).

## Para una segunda vuelta

- **El paso 2 con un catalogo grande.** Todo se probo con 10 productos. Con 60
  aparecen problemas que hoy no se ven: orden, paginado, seleccion por rango,
  y la barra de accion como unico lugar donde esta el total.
- **La pantalla de trabajo largo con audio.** Bajar audio puede tardar mucho
  mas que armar un ZIP de 8 MB, y esa pantalla se diseno para minutos, no para
  horas. Falta tiempo estimado y algo que sobreviva a dejar la ventana tapada.
- **`DESIGN.md` merece una pasada.** Quedo consistente con el codigo, pero su
  seccion 1 sigue narrando "la regla, la escala y el digito" como si las
  versalitas fueran estructura, que es justo lo que este trabajo saco.
