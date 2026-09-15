# Plan de implementacion (Fase 3)

Modo final: **Preserve**. Palancas de modernizacion del protocolo de redesign, en
orden: (1) tipografia y jerarquia, (2) espaciado y ritmo, (3) recalibracion de
color y semantica, (4) capa de movimiento, (5) recomposicion de cabecera y
paso 2. Sin reemplazo total de ningun bloque.

Cada lote es un commit propio, revisable y revertible con `git revert`.
Verificacion de cada lote: `python test_*.py` (9 suites), regeneracion de
capturas a `ux-audit/after/lote-N/` con el mismo harness del before, contraste
recalculado sobre tokens, y recorrido de las pantallas afectadas.

## Lote 1. Tokens y sistema

Cubre: SYS-01 a SYS-08, SYS-03 (10 px a 11), TYP-02, TYP-03, TYP-08, COL-02,
COL-03, COL-05, COL-07, COMP-19, COMP-20, LAY-10, LAY-11.
Archivos: `app/web/tokens/*.css`, `app/web/app.css`, `app/web/app.js` (solo
estilos inline a clases), `DESIGN.md`, `README.md`.
Riesgo: bajo. Cambian valores, no estructura. Se verifica con contraste
recalculado y capturas de las 18 vistas.

## Lote 2. Bugs y semantica

Cubre: COMP-01, COMP-02, COMP-03, COL-01, COL-04, COMP-04, COMP-05, COMP-06,
COMP-07, COMP-08, COMP-09, COMP-11, PA-01, PA-03, PA-04, PA-06, PA-07, PA-09,
COPY-01, COPY-02, COPY-03, COPY-04, COPY-05, COPY-08 a COPY-11, UX-05.
Archivos: `app/web/app.js`, `app/web/app.css`, `app/web/index.html`,
`app/server.py`, `migrar_core.py`, `relevar_core.py`, `validar.py`,
`paquete.py`, `productos.py`, `portadas.py`, `build/capturas.py`,
`TERMINOS.md`, docs.
Riesgo: medio, por tocar mensajes de Python y la fraccion de progreso. Los
tests de parseo, validacion y paquete cubren el nucleo; se agrega un test para
el sello placeholder.

## Lote 3. Composicion y jerarquia

Cubre: SLOP-01, COMP-12 / SLOP-02, LAY-01, LAY-02, LAY-03, LAY-05, TYP-01,
TYP-05 / C-6, TYP-06, TYP-07, SLOP-04, SLOP-06, COL-06 / SLOP-05, COMP-13 /
C-9, COMP-14, COMP-15, COPY-06, COPY-07, UX-03, UX-04, UX-06 (parcial).
Archivos: `app/web/app.js`, `app/web/app.css`, `app/web/index.html`,
`DESIGN.md`.
Riesgo: medio-alto, es el lote que mas cambia lo que se ve. Sin tocar ids,
`data-*` ni rutas. Se verifica con capturas de las 18 vistas mas las 7 reales.

## Lote 4. Movimiento y estados

Cubre: C-1 / UX-01 / COL-04, C-2 / MOT-03, C-3 / COMP-17 / MOT-06, C-4, C-5,
C-7, COMP-16, MOT-02 (documentar la restriccion).
Archivos: `app/web/app.css`, `app/web/app.js`.
Riesgo: bajo. Todo en CSS con `prefers-reduced-motion`; el re-render por
`innerHTML` obliga a que cada animacion arranque por clase o `@starting-style`.

## Lote 5. Responsive

Cubre: COMP-10 / RESP-01 / C-10, LAY-06, LAY-07, LAY-08, LAY-09.
Archivos: `app/web/app.css`, `app/web/app.js` (atributos `data-col`).
Riesgo: medio. Se verifica a 375, 768 y 1440 con el harness de 375 corregido.

## Lote 6. Extras

Cubre: C-8 (orden por columna), ICO-01, ICO-03, PA-06.
Archivos: `app/web/app.js`, `app/web/app.css`, `index.html`, `README.md`.
Riesgo: bajo.

## Fuera del plan, con motivo

- Cambiar la arquitectura de render (MOT-02): es el modelo de la app y anda.
- Fotografia, texturas, vidrio, marquesinas (C-11).
- Tidal real y descarga del ZIP: no se pueden ejercitar aca.
