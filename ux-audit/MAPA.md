# Mapa de la app (Fase 1 de la auditoria UI/UX)

Relevado el 2026-09-14 sobre `main` (8ab1130), con la app corriendo desde el codigo
en `http://127.0.0.1:8800`. Capturas en `ux-audit/before/`.

## Stack y como se levanta

- Backend: Python 3.14, `http.server` de la biblioteca estandar (`app/server.py`),
  trabajos largos en hilos (`app/jobs.py`). Sin framework.
- Frontend: un solo `index.html`, JavaScript vanilla (`app/web/app.js`, 1493
  lineas, render por `innerHTML` a partir de un estado global `S`) y CSS plano
  (`app/web/app.css`, 796 lineas) sobre tokens en `app/web/tokens/` (colors,
  typography, spacing, fonts). Sin build step, sin CDN, sin libreria de
  componentes ni de animacion. Iconos: SVG inline escritos a mano.
- Tipografias vendorizadas: Archivo (titulares), Geist (interfaz), Geist Mono
  (datos). `font-display: swap`.
- Temas: oscuro por defecto; el claro se activa con `data-theme="claro"` en
  `<html>` y se recuerda en `localStorage`.
- Se levanta con `python app/launcher.py` (ventana pywebview) o directamente el
  servidor. No necesita variables de entorno; la clave de YouTube vive en
  `~/.migrador-catalogos/config.json` (esta maquina ya tiene una).
- Breakpoints reales en CSS: 900 px (cabecera y margen del shell) y 760 px
  (la tabla pasa a tarjetas apiladas). `prefers-reduced-motion` esta contemplado.

## Rutas del servidor

| Ruta | Que hace |
|---|---|
| `GET /` | `index.html` con el token de sesion inyectado y la CSP |
| `GET /<estatico>` | css, js, fuentes, icono (solo dentro de `app/web`) |
| `GET /api/config` | version, terminos aceptados, si hay clave, audio, tidal |
| `GET /api/catalogo` | el catalogo relevado (sobrevive a un F5) |
| `GET /api/job/<id>` | estado, progreso, log y resultado de un trabajo |
| `GET /api/descargar/<id>` | el ZIP |
| `POST /api/terminos` | aceptar terminos |
| `POST /api/clave` | verificar y guardar la clave propia |
| `POST /api/relevar` | arranca el relevamiento (trabajo largo) |
| `POST /api/validar` | valida la seleccion |
| `POST /api/preparar` | arranca el armado del paquete (trabajo largo) |
| `POST /api/tidal/iniciar`, `/confirmar`, `/desconectar` | login por device code |

Toda ruta `/api/` exige el header `X-App-Token` y un `Host` local.

## Pantallas (un solo documento; el estado `S` decide que se ve)

Fuera del flujo de cuatro pasos:

| Pantalla | Como se llega | Funcion en `app.js` | Capturas |
|---|---|---|---|
| Esqueleto de carga | al abrir, antes de `/api/config` | `vistaEsqueleto` | `X2-esqueleto` |
| Error fatal | si `/api/config` falla | `vistaFatal` | `X1-fatal` |
| Terminos, primera vez | primer arranque (`terminos_aceptados=false`) | `vistaTerminos(true)` | misma vista que la de consulta, con boton Aceptar |
| Terminos, consulta | link del pie | `vistaTerminos(false)` | `04-terminos` |
| Clave de YouTube, obligatoria | si la copia no trae clave | `vistaClave` | misma vista que la de abajo, sin Cancelar |
| Clave de YouTube, propia | "Prefiero usar mi propia clave" o el error de cupo | `vistaClave` | `03-clave-propia` |

El flujo (pasos: Pega el link, Elegi productos, Elegi que bajar, Descarga):

| Paso | Estados | Funcion | Capturas |
|---|---|---|---|
| 1. Entrada | vacio; con clave incluida; error de validacion (link vacio o invalido); error de YouTube (cupo, clave) con boton "Cargar mi propia clave" | `vistaPaso1`, `bloqueError`, `avisoClaveIncluida` | `01-entrada`, `02-entrada-error-cuota` |
| 1 a 2. Relevando | spinner, mensaje, porcentaje, barra, log, Cancelar | `bloqueProgreso` | visto en vivo con datos reales; misma pieza que `16-progreso` |
| 2. Catalogo | tabla de productos; producto expandido; seleccion parcial; filtro por fecha; por distribuidora; busqueda; vacio por filtro; avisos del relevamiento (Topic buscado, videos descartados) | `vistaPaso2`, `avisoCanal` | `05` a `11`, `R1`, `R2`, `R3` |
| 3. Que descargar | planilla + portadas; con audio; Tidal conectando; Tidal conectada; aviso de Tidal sin conectar | `vistaPaso3`, `bloqueTidal` | `12` a `15`, `R4` |
| 4. Progreso | armando el paquete | `vistaPaso4` + `bloqueProgreso` | `16-progreso`, `R5` |
| 4. Listo | metricas, boton de descarga, validacion con errores y avisos en acordeones | `vistaPaso4` | `17-listo`, `18-listo-avisos`, `R6`, `R7` |

Acciones (`data-accion`): relevar, volver-1/2/3, ir-3, generar, cancelar,
recargar, sel-todo, sel-nada, limpiar-filtro, usar-topic, ver-terminos,
aceptar-terminos, cerrar-vista, ver-clave, guardar-clave, tidal-iniciar,
tidal-confirmar, tidal-salir, cambiar-tema.

## Componentes recurrentes

- **Shell**: superficie redondeada sobre lienzo negro; cabecera y pie fijos, el
  scroll pasa dentro de `main`.
- **Cabecera**: logo + marca en mono versalitas, stepper de cuatro pasos (pill
  group), version, boton de tema (sol / luna).
- **Pie**: "Hecho por" + link a LinkedIn, "Terminos de uso" (`<a href="#">`),
  estado a la derecha (`#pie-estado`, por ejemplo "Paquete listo.").
- **Titulo de vista** (Archivo 40 px) + subtitulo.
- **Tira de metricas** `.kpis` (etiqueta mono chica + numero grande mono).
- **Alertas** `.alerta` con icono: ok, info, atencion, negativo.
- **Etiqueta de seccion sobre regla** `.seccion-etiqueta` (mono versalitas, con
  contador a la derecha).
- **Filtros**: segmented control (Uno por uno / Por fecha / Por distribuidora) +
  buscador; paneles `.panel` para rango de anos y distribuidoras.
- **Tabla** `.tabla`: cabecera sticky, checkbox por fila con label oculto,
  numero de fila por contador CSS, boton expandir con `aria-expanded`, badges
  mono en versalitas con borde de color (COMPLETO, SIN UPC, ISRC n DE m, ORDEN
  ESTIMADO), subtabla `.sub` de tracks. A 760 px o menos se apila en tarjetas
  con etiquetas por celda.
- **Barra de accion** sticky al pie del area de scroll: resumen mono + botones.
- **Botones**: primario (teal), ghost, chico, icono; links de accion en teal.
- **Opciones de descarga** `.opciones` / `.opcion`: icono + checkbox + titulo +
  descripcion.
- **Bloque de progreso**: spinner, mensaje, porcentaje, barra, log mono con
  scroll interno, Cancelar.
- **Acordeones** `details.acordeon` para errores y avisos, con tabla adentro.
- **Lista numerada** de pasos para conseguir la clave.

## Que se ejercito y que no

Ejercitado en vivo sobre la app real (1440x900, 375, 768, 1920, ambos temas):
paso 1 completo, validacion con link vacio y con basura, terminos, primera vez
(terminos y clave, forzando el estado), foco por teclado en toda la pantalla y
dentro de la tabla, toggle de tema, y un relevamiento real de punta a punta
(canal `UCASesgRftXKCrvcnpn8T6Aw`: 10 productos, 46 tracks, paquete de 7,8 MB con
0 errores y 41 avisos), con filtros, busqueda, expandir y seleccion.

No ejercitado, y por que:
- Descargar el ZIP: requiere permiso explicito para bajar archivos. El paquete
  quedo generado en el servidor.
- Cancelar un trabajo en curso: el relevamiento y el armado duraron menos de
  40 s; el boton existe y se ve en `16-progreso`.
- Tidal real: necesita una cuenta paga propia. Los tres estados se ven por
  fixture (`13` a `15`).
- Hover: el panel del navegador no llego a fotografiar los estados de puntero;
  se verifican en el CSS en la Fase 2.
- Cupo agotado o clave invalida reales: no conviene gastar el cupo de la clave.
  Se ven por fixture (`02`).

## Notas del harness de capturas

- `--375`: Chrome en Windows no abre ventanas de menos de ~500 DIP, asi que las
  capturas de 375 se hicieron acotando el documento a 375 px por CSS dentro de
  una ventana de 600 y recortando. Como los unicos breakpoints son 760 y 900, a
  375 y a 600 aplican las mismas media queries; la unica diferencia posible
  serian unidades `vw`, que la app no usa.
- `--1440-completa`: el shell desenrollado (sin scroll interno) para ver el
  contenido entero; el resto son fotos del viewport real.
- `R*`: renders con el catalogo y el resultado reales del relevamiento de esta
  sesion, pasados por la misma pagina de fixtures que usa `build/capturas.py`.
- Las capturas del panel del navegador de la app de escritorio no van a disco;
  todas las de `before/` salen de Chrome headless sobre la app real.
