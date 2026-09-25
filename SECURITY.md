# Security policy

[Español](#reportar-un-problema-de-seguridad) · English below in the same file.

## Reporting a vulnerability

Report it privately through GitHub's
[Report a vulnerability](https://github.com/joacogoliver-debug/catalog-migrator/security/advisories/new)
form, not as a public issue. This is a small project maintained by one person;
expect a first reply within a week.

Please include what you were running (variant and version, or the commit),
the operating system, and the steps to reproduce it.

## What is in scope

The app runs entirely on the user's machine. The things worth looking at:

- **The local API and its three defenses.** The server listens only on
  `127.0.0.1`, and on top of that: every `/api/` route demands a per-session
  token injected into `index.html`; the `Host` header is checked against a
  fixed list, which stops DNS rebinding; and the page carries a CSP that lets
  it neither fetch nor run anything from outside, because what it displays
  comes from YouTube, Deezer and Apple. They exist because a local server with
  no further protection can be driven by any page open in that machine's
  browser. A way around any of the three is in scope, and so is a way to
  frame the app (it declares `X-Frame-Options: DENY` and `frame-ancestors
  'none'`). [docs/AMENAZAS.en.md](docs/AMENAZAS.en.md) says who each defense
  exists against and what is left out on purpose.
- **Path handling when serving static files and when writing the ZIP.** A path
  that escapes its directory is in scope.
- **What the ZIP writes from outside data.** A title that turns into a formula
  Excel runs, or into a path, is in scope.
- **The bundled YouTube key** in the `completa` variant. That it can be
  extracted from the binary is **not** a vulnerability: it is stated in the
  README, the key is restricted to YouTube Data API v3 and capped, and anyone
  who prefers not to depend on it can use the `esencial` variant or load their
  own key.

## What is out of scope

- The unsigned binary and the SmartScreen or Gatekeeper warning. Signing costs
  money per year and this tool is free; instead every release publishes its
  SHA256 and, while the repository is public, a build provenance attestation.
  The workflow skips the attestation on a private repository and does not stop
  the release if producing it fails, so a release without one is possible:
  the SHA256 is always there.
- Anything that needs an attacker to already have code execution or file access
  on the user's machine, including reading the config file with their API key.
- The optional audio module's third-party dependencies (`tiddl`, `yt-dlp`,
  `ffmpeg`). Report those upstream.

---

## Reportar un problema de seguridad

Reportalo en privado, por el formulario
[Report a vulnerability](https://github.com/joacogoliver-debug/catalog-migrator/security/advisories/new)
de GitHub, y no como un issue público. Es un proyecto chico mantenido por una
sola persona: contá con una primera respuesta dentro de la semana.

Incluí con qué lo estabas corriendo (variante y versión, o el commit), el
sistema operativo, y los pasos para reproducirlo.

## Qué entra

La app corre entera en la máquina de quien la usa. Lo que vale mirar:

- **La API local y sus tres defensas.** El servidor escucha sólo en
  `127.0.0.1`, y además: toda ruta `/api/` exige un token de sesión que se
  inyecta en `index.html`; la cabecera `Host` se controla contra una lista fija,
  que corta el rebinding de DNS; y la página lleva una CSP que no la deja pedir
  ni ejecutar nada de afuera, porque lo que muestra viene de YouTube, Deezer y
  Apple. Existen porque a un servidor local sin más protección lo puede manejar
  cualquier página abierta en el navegador de esa misma máquina. Una vuelta
  para saltear cualquiera de las tres entra, y también una forma de meter la
  app en un iframe (declara `X-Frame-Options: DENY` y `frame-ancestors
  'none'`). [docs/AMENAZAS.md](docs/AMENAZAS.md) dice contra quién existe cada
  defensa y qué queda afuera a propósito.
- **El manejo de rutas** al servir los estáticos y al escribir el ZIP. Una ruta
  que se escape de su carpeta entra.
- **Lo que el ZIP escribe a partir de datos de afuera.** Un título que se
  vuelva una fórmula que Excel ejecuta, o una ruta, entra.
- **La clave de YouTube incluida** en la variante `completa`. Que se pueda sacar
  del binario **no** es una vulnerabilidad: está dicho en el README, la clave
  está restringida a la YouTube Data API v3 y con tope de cuota, y quien
  prefiera no depender de eso tiene la variante `esencial` o su propia clave.

## Qué no entra

- Que el binario no esté firmado y que Windows o macOS avisen. Firmar cuesta
  plata por año y la herramienta es gratis; a cambio, cada release publica su
  SHA256 y, mientras el repositorio sea público, una atestación de procedencia.
  El workflow la saltea en un repositorio privado y no frena el release si
  generarla falla, así que puede haber un release sin atestación: el SHA256
  está siempre.
- Todo lo que necesite que quien ataca ya tenga ejecución de código o acceso a
  los archivos de la máquina, incluido leer el archivo de configuración con la
  clave de la API.
- Las dependencias de terceros del módulo opcional de audio (`tiddl`, `yt-dlp`,
  `ffmpeg`). Eso va reportado río arriba.
