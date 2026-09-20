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

- **The local API.** The server listens only on `127.0.0.1`, and on top of that
  every `/api/` route demands a per-session token injected into `index.html`,
  and the `Host` header is checked against a fixed list. Both defenses exist
  because a local server with no further protection can be driven by any page
  open in that machine's browser. A way around either of them is in scope.
- **Path handling when serving static files and when writing the ZIP.** A path
  that escapes its directory is in scope.
- **The bundled YouTube key** in the `completa` variant. That it can be
  extracted from the binary is **not** a vulnerability: it is stated in the
  README, the key is restricted to YouTube Data API v3 and capped, and anyone
  who prefers not to depend on it can use the `esencial` variant or load their
  own key.

## What is out of scope

- The unsigned binary and the SmartScreen or Gatekeeper warning. Signing costs
  money per year and this tool is free; instead every release publishes its
  SHA256 and a build provenance attestation.
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

- **La API local.** El servidor escucha sólo en `127.0.0.1`, y además toda ruta
  `/api/` exige un token de sesión que se inyecta en `index.html`, y se controla
  la cabecera `Host` contra una lista fija. Las dos defensas existen porque a un
  servidor local sin más protección lo puede manejar cualquier página abierta en
  el navegador de esa misma máquina. Una vuelta para saltear cualquiera de las
  dos entra.
- **El manejo de rutas** al servir los estáticos y al escribir el ZIP. Una ruta
  que se escape de su carpeta entra.
- **La clave de YouTube incluida** en la variante `completa`. Que se pueda sacar
  del binario **no** es una vulnerabilidad: está dicho en el README, la clave
  está restringida a la YouTube Data API v3 y con tope de cuota, y quien
  prefiera no depender de eso tiene la variante `esencial` o su propia clave.

## Qué no entra

- Que el binario no esté firmado y que Windows o macOS avisen. Firmar cuesta
  plata por año y la herramienta es gratis; a cambio, cada release publica su
  SHA256 y una atestación de procedencia.
- Todo lo que necesite que quien ataca ya tenga ejecución de código o acceso a
  los archivos de la máquina, incluido leer el archivo de configuración con la
  clave de la API.
- Las dependencias de terceros del módulo opcional de audio (`tiddl`, `yt-dlp`,
  `ffmpeg`). Eso va reportado río arriba.
