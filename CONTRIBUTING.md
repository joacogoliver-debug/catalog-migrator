# Cómo contribuir

**Español** · [English](CONTRIBUTING.en.md)

Gracias por mirar el código. Este archivo dice lo que hace falta saber antes de
tocar algo, para que no descubras a mitad de un pull request que había una regla
que no estaba escrita en ningún lado.

Es un proyecto chico, mantenido por una persona. Si tu cambio es grande, abrí un
issue antes y charlemos: es más barato que escribirlo dos veces.

## Arrancar

```bash
pip install -e ".[app,dev]"
pre-commit install
python app/launcher.py
```

No hace falta instalar el paquete para correr la app ni los tests: `app/` y
`tests/` se arman el `sys.path` solos. Instalarlo con `-e` sirve para que los
imports no dependan de desde qué carpeta ejecutes, y para tener las tres
herramientas de una.

Con eso ya tenés la app corriendo y los controles enganchados al commit.

## Antes de mandar el pull request

En este orden, y sin saltear ninguno.

```bash
pytest -q --cov      # tests y cobertura, que no puede bajar del umbral
ruff check .         # errores y estilo
ruff format .        # formato
pyright              # tipos, hoy en cero errores
```

Si tocaste la interfaz, además:

```bash
python build/capturas.py     # regenera las capturas del README
```

Y si tocaste algo del empaquetado:

```bash
python build/build.py
# y abrir el binario que quedó en dist/ con --diagnostico
# (en Windows es "Migrador de Catalogos.exe")
```

`build/build.py` corre la suite antes de empaquetar y aborta si algo falla, así
que un binario publicado siempre pasó sus tests.

## Las reglas que no se negocian

Estas no son preferencias de estilo. Cada una está donde está por algo concreto
que pasó o que se quiso evitar.

### 1. Las tres defensas del servidor local

El servidor escucha en `127.0.0.1`, pero eso solo no alcanza: cualquier página
abierta en el navegador de esa misma máquina le puede mandar pedidos. Por eso hay
tres defensas más, y las tres tienen test.

1. **Token de sesión**, nuevo en cada arranque, inyectado en `index.html` y
   exigido en toda ruta `/api/`.
2. **Control de `Host`**, que acepta sólo `127.0.0.1` y `localhost`, y corta el
   rebinding de DNS.
3. **CSP**, que no deja a la página pedir ni ejecutar nada de afuera.

**Ninguna se debilita.** Cualquier cambio en `app/server.py` viene con un test
nuevo o modificado que cubra lo que tocaste.

### 2. Sin frameworks y sin build step

Backend sobre `http.server` de la biblioteca estándar. Frontend en JavaScript
vanilla y CSS sobre los tokens de `app/web/tokens/`. Nada de ORM, nada de
bundler, nada de CDN.

No es purismo. Empaquetar tiene que seguir siendo copiar archivos: el día que
haya un build step, el ejecutable depende de que ese paso ande en cuatro sistemas
operativos, y los imports dinámicos de un framework ASGI son la causa habitual de
que un binario ande en desarrollo y falle empaquetado.

### 3. No se inventa metadata

Lo que no sale de una fuente pública queda como `<<COMPLETAR>>` en la hoja de
ingesta. No vacío, no rellenado a ojo.

Las dos heurísticas que hay están documentadas y dichas en el README: el orden de
tracks es estimado por fecha de subida, y el formato (single / EP / álbum) se
deduce de la cantidad de tracks. **Si cambiás alguna, actualizá el README en el
mismo commit.**

### 4. La clave de YouTube nunca entra al repositorio

Ni en el código, ni en un test, ni en una fixture, ni en un log. Vive como
secreto del CI y entra recién al compilar, desde `MIGRADOR_CLAVE_YT`.

`build/sin_claves.py` lo controla en cada commit y en el CI. Si te lo bloquea,
no lo saltees: una clave que llegó a un commit ya se considera filtrada, porque
el objeto queda en la historia y en cada clon.

### 5. Todo lo que el usuario lee va en los dos idiomas

La app está en castellano y en inglés entera, incluido lo que descarga. Hay dos
catálogos porque son dos procesos.

| Dónde | Para qué |
|---|---|
| `src/migrador/i18n.py` | Lo que arma Python: el log, los errores, los archivos del ZIP |
| `app/web/i18n.js` | La interfaz |

`tests/test_i18n.py` verifica que no quede ninguna clave a medio traducir, que la
interfaz no use claves sin definir ni defina claves sin usar, y que los dos
catálogos coincidan en los nombres de archivo. Si agregás texto y no lo traducís,
el test te avisa antes que un usuario.

Dos excepciones, las dos deliberadas. Los centinelas `SIN_ALBUM` y `SIN_DATOS` de
`src/migrador/productos.py` no se traducen, porque el filtrado y la agrupación los comparan por
igualdad. Y las columnas de la hoja de ingesta tampoco, porque son nombres de
campo que espera la distribuidora, no texto para leer.

### 6. El README es honesto

Si resolvés una limitación que el README declara, borrala de ahí. Si no la
resolvés, dejala. No se promete nada que no esté hecho.

## Estilo

El formato lo arregla `ruff format` y no hace falta discutirlo. Sobre lo demás,
dos cosas que este código hace a propósito.

**Los comentarios dicen por qué, no qué.** Un comentario que repite lo que la
línea ya dice es ruido. Uno que explica por qué esa línea es así, y qué se rompió
cuando no lo era, es lo que hace que el código se pueda tocar dentro de seis
meses. La mayoría de los comentarios largos de este repositorio son la crónica de
un bug real.

**Los nombres conviven en los dos idiomas** y no hay una regla que los ordene.
Los módulos más viejos quedaron en inglés (`group_products`, `build_zip`,
`filter_products`) y los más nuevos están en castellano (`empaquetar`,
`relevar_catalogo`, `validar`). Lo que sí se respeta es no renombrar por gusto:
un rename es un diff grande que no arregla nada y tapa los cambios de verdad.

## Commits

Convencionales, con el tipo adelante.

```
feat(portadas): pedir 3000x3000 y reportar lo que Apple devuelve
fix(macos): faltaba el binario para las Mac Intel
test(seguridad): la CSP, que era la unica de las tres defensas sin test
docs: corregir la lista rota de "Como esta hecha"
```

Tipos que se usan acá: `feat`, `fix`, `refactor`, `test`, `docs`, `build`,
`chore`, `style`.

El cuerpo del mensaje importa más que el título. Contá qué se rompía antes, no
qué archivos tocaste: eso ya lo dice el diff.

## Dónde está cada cosa

| Archivo | Qué hace |
|---|---|
| `app/launcher.py` | Punto de entrada: puerto libre, servidor, ventana o navegador |
| `app/server.py` | API JSON, estáticos y las tres defensas |
| `app/jobs.py` | Trabajos en segundo plano con progreso y cancelación |
| `app/web/` | La interfaz |
| `src/migrador/` | El motor, que no sabe nada de HTTP ni de ventanas |
| `src/migrador/version.py` | La versión, escrita en un solo lugar |
| `scripts/` | Los lanzadores para abrir la app desde el código |
| `src/migrador/contratos.py` | La forma de los datos que viajan entre módulos |
| `src/migrador/texto.py` | Normalización de texto y nombres de archivo seguros |
| `src/migrador/relevar_core.py` | Relevamiento de YouTube más ISRC y UPC por Deezer |
| `src/migrador/productos.py` | Agrupa tracks en productos y filtra la selección |
| `src/migrador/validar.py` | Validación pre-entrega |
| `src/migrador/portadas.py` | Portadas por iTunes Search API |
| `src/migrador/paquete.py` | Planillas, hoja de ingesta, reportes y ZIP |
| `src/migrador/audio.py` | Módulo de audio opcional |
| `src/migrador/migrar_core.py` | Orquesta los cuatro pasos |
| `build/` | Empaquetado, instalador, icono, capturas, claves y fixtures |
| `tests/fixtures/` | Respuestas reales de Deezer e iTunes, grabadas una vez |
| `docs/` | Decisiones de producto y de diseño |

`docs/marca/` es el logotipo y sus reglas de uso. No se toca.

## Reportar algo

- **Un problema de seguridad** va en privado, por el formulario de
  [Report a vulnerability](https://github.com/joacogoliver-debug/catalog-migrator/security/advisories/new),
  nunca como issue público. El detalle está en [SECURITY.md](SECURITY.md).
- **Todo lo demás**, como issue. Hay plantillas, y llenarlas ahorra la ida y
  vuelta de pedir la versión y el sistema operativo.

Si la app no abre, `--diagnostico` deja un reporte de qué puede hacer en tu
máquina, y adjuntarlo suele resolver el issue en un mensaje.

## Licencia

Al contribuir aceptás que tu aporte se publique bajo la licencia MIT del
proyecto, y que el uso previsto y sus límites son los de [TERMINOS.md](TERMINOS.md).
Esta herramienta es para administración de catálogos, y no avala ni habilita la
piratería.
