# Auditoría del repositorio

Estado del código en el commit `eae6870` (v1.0.2), rama `main`, árbol limpio.
Fecha de la revisión, 21 de septiembre de 2026.

Esto es un diagnóstico, no un plan de obra. El plan sale de acá y vive en
[MEJORAS.md](MEJORAS.md). No se tocó ninguna línea de código para escribirlo.

## Qué se verificó de verdad

Antes de opinar se corrió lo que hay.

| Comprobación | Resultado |
|---|---|
| Los diez tests, uno por uno, con `MIGRADOR_IDIOMA=es` | los diez en verde |
| `python -m pytest -q --collect-only` | **no tests collected** |
| `ruff` instalado localmente | no está (sí está clavado en el CI, 0.16.8) |
| `pyright` instalado localmente | no está, y no hay configuración en el repo |
| Python local | 3.14.5. El CI y `pyproject.toml` apuntan a 3.13 |
| Anotaciones de tipo en todo el repo | cero |
| Archivos versionados | 90 |
| `ux-audit/` versionado | no, está en `.gitignore` y no tiene ningún archivo trackeado |

El segundo renglón es el hallazgo más incómodo de la lista y está desarrollado
en T1.

## Resumen

El proyecto está bastante mejor de lo que un repo de una persona suele estar.
Tiene CI que compila las cuatro plataformas y **corre el binario** antes de
publicarlo, atestación de procedencia, `SECURITY.md`, dos `CHANGELOG`, README en
dos idiomas, capturas generadas por código, licencia de cada dependencia de
terceros, y una versión con una sola fuente de verdad. Las tres defensas del
servidor local están implementadas y dos de las tres tienen test.

Lo que falta es, casi todo, andamiaje. La suite de tests es un conjunto de
scripts con `main()` y una lista de strings, no una suite. No hay tipos en
ningún lado, así que el contrato entre módulos vive en los docstrings y en la
cabeza de quien lo escribió. Los módulos están en la raíz, sin paquete, y cada
archivo se arregla solo el `sys.path`. Y la lista de tests está escrita tres
veces en tres lugares que nadie sincroniza.

Ninguno de estos problemas se le nota al usuario hoy. Todos encarecen el próximo
cambio.

---

## Eje 1, estructura

**E1. Los módulos viven en la raíz y cada uno se arma el `sys.path` a mano.**
`relevar_core.py:25`, `app/server.py:58-61`, `app/launcher.py:21-24`, y los diez
tests repiten la misma maniobra. `pyproject.toml` declara explícitamente que no
hay paquete instalable y explica por qué, lo cual es un argumento razonable, pero
el costo se paga en dieciséis `# noqa: E402` y en que importar el proyecto desde
afuera depende del directorio desde el que se llame.
*Impacto alto, esfuerzo alto.*

**E2. Los lanzadores están sueltos en la raíz.** `abrir_app.bat`,
`abrir_app.sh` y `abrir_app_con_audio.bat`. No molestan, pero la raíz tiene hoy
veinte entradas y eso es lo primero que ve alguien que llega.
*Impacto bajo, esfuerzo bajo.*

**E3. Hay seis normalizadores de texto casi iguales.** `_norm` en
`productos.py:41`, `portadas.py:43` y `audio.py:327`; `_normalize` en
`relevar_core.py:302`; `_sin_acentos` en `validar.py:308`; y dos funciones de
slug, `productos.py:67` y `paquete.py:46`, más `relevar_core.slugify:592`.
Algunas difieren a propósito (el slug de carpeta prohíbe caracteres de Windows,
el de archivo tiene otro largo), pero las tres `_norm` son idénticas palabra por
palabra. `_mmss` está duplicada exacta en `app/server.py:433` y `paquete.py:104`.
*Impacto medio, esfuerzo bajo.*

**E4. `paquete.py` importa `audio.py` sólo para una constante.**
`paquete.py:38`, `from audio import FORMATOS_LOSSLESS`. Funciona porque `audio.py`
no importa `tiddl` ni `yt-dlp` en el tope, pero ata el armado del entregable, que
es el núcleo, al módulo opcional. Un import mal puesto en `audio.py` rompería la
variante esencial.
*Impacto medio, esfuerzo bajo.*

---

## Eje 2, calidad de código

**C1. Cero anotaciones de tipo y cero dataclasses.** El producto es un `dict`
con dieciséis claves que nacen en `productos.group_products`, se serializan
distinto en `server.producto_json`, y se consumen en `validar`, `portadas`,
`paquete` y `audio`. Cada consumidor adivina qué claves existen. El test de
`migrar_core` fija el contrato de `relevar()` con un `set` de strings escrito a
mano, lo cual demuestra que la necesidad ya se sintió y se resolvió como se pudo.
*Impacto alto, esfuerzo medio.*

**C2. Trece `# noqa: BLE001` que no silencian nada.** `BLE` es
`flake8-blind-except` y no está en `select = ["E", "F", "W", "B"]`. Los comentarios
son inertes. Documentan una intención real (el catch amplio es deliberado), así
que el arreglo no es borrarlos sino habilitar la regla o cambiarlos por un
comentario en prosa.
*Impacto bajo, esfuerzo bajo.*

**C3. El estado del servidor es global y se calcula al importar.** `TOKEN`
(`app/server.py:83`), `AUDIO_HABILITADO` (`:117`), `WEB_DIR` (`:116`), `ESTADO`
(`:425`) y `JOBS` (`:426`). Es coherente con una app local de un usuario, y está
argumentado en el módulo. El precio es que un test que quiera probar la variante
con audio tiene que recargar el módulo entero, y por eso `tests/test_app.py` fija
`MIGRADOR_IDIOMA` antes del primer import.
*Impacto medio, esfuerzo alto. No conviene tocarlo salvo que lo pida otro ítem.*

**C4. `log=print` como valor por defecto en once funciones públicas.** Los
módulos de negocio escriben a stdout si nadie les pasa un callback. En un
ejecutable compilado sin consola eso va al vacío, lo cual es inofensivo, pero
significa que el default de la librería es un efecto de entrada y salida.
*Impacto bajo, esfuerzo bajo.*

---

## Eje 3, tests

**T1. `pytest -q` no corre nada y sale contento.** Los diez archivos exponen su
lógica dentro de `main()` y ninguno define una función `test_*`, así que pytest
colecta cero y el proceso termina sin fallar. Cualquier flujo de trabajo que
confíe en `pytest -q` como puerta de calidad está pasando por una puerta abierta.
Este es el hallazgo de mayor impacto de toda la auditoría, porque desarma la
verificación antes de cada commit.
*Impacto alto, esfuerzo medio.*

**T2. La lista de tests está escrita tres veces.** `build/build.py:32-34` (la
que decide si se empaqueta), `.github/workflows/tests.yml` (un step por test,
líneas 34 a 68) y `README.md:399-410`. Un test nuevo requiere acordarse de tres
lugares. Un test nuevo olvidado en `build.py` no bloquea un release.
*Impacto alto, esfuerzo bajo.*

**T3. La CSP no tiene test.** `tests/test_app.py` cubre el token
(`seg.get_sin_token`, `seg.post_sin_token`, `seg.token_incorrecto`,
`seg.token_en_pagina`) y el `Host`, que son dos de las tres defensas. La cabecera
`Content-Security-Policy` de `app/server.py:958-962` no se verifica en ningún
lado. Es la defensa más fácil de romper sin darse cuenta, porque es un string
suelto adentro de un método.
*Impacto alto, esfuerzo bajo.*

**T4. No se mide cobertura.** No hay umbral, ni reporte, ni forma de saber si un
cambio dejó una rama sin probar.
*Impacto medio, esfuerzo bajo, pero depende de T1.*

**T5. No hay respuestas reales grabadas de Deezer ni de iTunes.** Los tests
construyen dobles a mano con la forma que el código espera. Eso prueba que el
código es consistente consigo mismo, no que entienda lo que las APIs devuelven de
verdad. Si Deezer cambia un campo, nada avisa hasta que un usuario lo sufre.
*Impacto medio, esfuerzo medio.*

**T6. Cada test reimplementa `expect`, `check` y el acumulador `fails`.** Son
diez copias del mismo andamio, más un `_load()` por ruta en `test_portadas.py` y
un `_esperar()` por reloj en `test_app.py` que podrían compartirse.
*Impacto medio, esfuerzo bajo, se resuelve junto con T1.*

---

## Eje 4, distribución y experiencia de quien desarrolla

**D1. macOS y Linux se publican como ejecutable suelto.** No hay `.app`, ni
`.deb`, ni AppImage. El README lo dice sin maquillarlo y hasta explica el
`xattr -c`, que es lo correcto, pero son cuatro comandos de Terminal para abrir
un programa gratis. En macOS, además, doble clic en el Finder no hace lo
esperado. Un `.app` sin firmar sigue necesitando el clic derecho, pero al menos
se ve y se abre como una aplicación.
*Impacto alto, esfuerzo alto.*

**D2. Las notas del release están escritas a mano adentro del workflow.**
`.github/workflows/build.yml`, el bloque `body:` ocupa unas 130 líneas y repite
en dos idiomas lo que ya dice el README. Existe un `CHANGELOG.md` que nadie lee
al publicar.
*Impacto medio, esfuerzo bajo.*

**D3. No hay `CONTRIBUTING.md` ni plantillas de issue.** `.github/` sólo tiene
`workflows/`. Hay `SECURITY.md`, `LICENSE`, `TERMINOS.md` y `TERMS.md`, así que
lo que falta es el resto del andamiaje de un repo público que espera visitas.
*Impacto medio, esfuerzo bajo.*

**D4. No hay `pre-commit` ni `ruff format`.** El CI corre `ruff check` pero no
`ruff format --check`, así que el formato depende de la costumbre de quien
escribe. Nada corre antes de un commit.
*Impacto medio, esfuerzo bajo.*

**D5. Python local 3.14, CI y `target-version` en 3.13.** No hay nada roto hoy,
pero es una diferencia silenciosa entre la máquina donde se escribe y la que
produce el binario que la gente baja.
*Impacto bajo, esfuerzo bajo.*

**D6. `ux-audit/` ya está resuelto y el backlog lo arrastra.** Está en
`.gitignore` con su justificación escrita, y `git ls-files ux-audit` no devuelve
nada. Es una carpeta de trabajo local, no un problema del repositorio. Lo único
que queda es una decisión de escritorio, borrarla de la máquina o dejarla.
*Impacto nulo. Se cierra documentándolo.*

---

## Eje 5, producto y experiencia de uso

**P1. El README tiene una imagen que rompe la lista de «Cómo está hecha».**
`README.md:350`. Falta la línea en blanco antes del `![...]`, así que la imagen
queda pegada al ítem del backend y corta la lista en dos. `README.en.md:354`
tiene la línea en blanco y se ve bien. Es el mismo párrafo en los dos idiomas y
sólo uno está mal.
*Impacto bajo, esfuerzo mínimo.*

**P2. El README manda a correr los tests de a uno.** `README.md:399-410`.
Después de T1 esa sección queda mintiendo, y hay que reescribirla junto con el
cambio, no después.
*Impacto medio, esfuerzo mínimo, atado a T1.*

**P3. La heurística de formato y el orden estimado están bien declarados.** No
es un hallazgo, es una verificación. `productos.py:30-38` documenta el umbral
1-3 / 4-6 / 7+ y el README lo repite en «Qué NO hace». `order_unconfirmed` viaja
hasta la planilla y hasta la validación. Nada que corregir, y nada que cambiar
sin marcarlo en el README.

**P4. El módulo de audio sigue apagado por defecto y aislado por sesión.**
También verificación, no hallazgo. `audio.py:20-26` lo argumenta y
`app/server.py:90-101` lo implementa con las dos puertas, la variable de entorno
y el archivo `CON_AUDIO`.

---

## Ranking

Ordenado por lo que más rinde por hora invertida.

| # | Hallazgo | Impacto | Esfuerzo |
|---|---|---|---|
| 1 | T3, la CSP sin test | alto | bajo |
| 2 | T2, la lista de tests escrita tres veces | alto | bajo |
| 3 | T1, `pytest -q` no corre nada | alto | medio |
| 4 | C1, contratos entre módulos sin tipos | alto | medio |
| 5 | D3, `CONTRIBUTING.md` y plantillas | medio | bajo |
| 6 | D4, `ruff format` y `pre-commit` | medio | bajo |
| 7 | T4, cobertura con umbral | medio | bajo |
| 8 | P1 y P2, arreglos de README | bajo | mínimo |
| 9 | E3 y E4, helpers duplicados y el import de `audio` | medio | bajo |
| 10 | T5, fixtures grabadas de Deezer e iTunes | medio | medio |
| 11 | D2, notas de release desde el CHANGELOG | medio | bajo |
| 12 | E1 y E2, paquete `src/` y `scripts/` | alto | alto |
| 13 | D1, `.app` y AppImage | alto | alto |
| 14 | C2, C4, D5, detalles | bajo | bajo |

E1 queda abajo a pesar de su impacto porque toca los veinticinco archivos a la
vez y hoy no hay red de contención, ni cobertura ni tipos. Hacerlo antes que T1 y
C1 es mover todo a ciegas. Hacerlo después es una tarde con el semáforo en verde.
