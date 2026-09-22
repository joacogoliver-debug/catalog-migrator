## Cuál bajar

**Windows, la recomendada**:
`Migrador-de-Catalogos-windows-completa-instalador.exe`. Doble clic,
Siguiente, y queda en el menú Inicio con su desinstalador. No pide
permisos de administrador. El instalador pregunta el idioma en la
primera pantalla, y la app —incluido lo que descarga— queda en el
que hayas elegido.

Si preferís no instalar nada, el portable es el `.exe` sin `-instalador`.

**En Linux**, el `.deb` (`migrador-catalogos_...deb`) se instala con
`sudo apt install ./archivo.deb` y queda en el menú de aplicaciones. El
ejecutable suelto sigue estando, para cualquier otra distribución.

**En macOS**, el `...-app.zip` trae un `.app` de verdad: lo arrastrás a
Aplicaciones y queda en el Launchpad. La primera vez hay que abrirlo con clic
derecho → Abrir.

**En macOS hay dos, y no son intercambiables**: uno para las Mac con
chip Apple (`-macos-apple-silicon-`) y otro para las Mac Intel
(`-macos-intel-`). Para saber cuál te toca:  → "Acerca de esta Mac".
Si bajás el que no es, la Terminal responde `bad CPU type in
executable`. Hay una guía paso a paso en
[docs/INSTALAR-MAC.md](https://github.com/{repo}/blob/main/docs/INSTALAR-MAC.md).

| Variante | Qué trae |
|---|---|
| **completa** | Todo, más el módulo de audio con ffmpeg adentro y una clave de YouTube ya configurada. Se abre y funciona. |
| **esencial** | Relevamiento, planilla, validación, hoja de ingesta y portadas. Más liviana, sin ffmpeg y sin clave incluida. |

Para bajar los audios en FLAC necesitás además tu propia cuenta paga
de Tidal. El módulo viene desactivado y es opcional.

La clave de YouTube que trae la variante completa es compartida, está
restringida a la YouTube Data API v3 y **cualquiera que baje el
binario la puede extraer**. Si preferís no depender de eso, usá la
variante `esencial` o cargá la tuya desde la app.

La versión completa incluye FFmpeg, software de terceros bajo
licencia GPLv3, que se distribuye sin modificaciones y como programa
separado.

### El sistema va a avisar que el programa "no es reconocido"

Es esperable: el binario no está firmado porque firmar cuesta plata y
esto es gratis. El código es público y el ejecutable se compila acá
en GitHub Actions desde ese código.

- **Windows**: "Más información" → "Ejecutar de todas formas".
- **macOS**: clic derecho → "Abrir", o Configuración → Privacidad y
  seguridad → "Abrir de todos modos".

### Verificar que el binario es el de este repo

Compará el SHA256 con el `.sha256` publicado, o usá la atestación:

```
gh attestation verify Migrador-de-Catalogos-windows-completa.exe --repo {repo}
```

### Términos de uso

Esta herramienta es para administración de catálogos. No avala ni
habilita la piratería. El detalle está en `TERMINOS.md`, y la app los
muestra la primera vez que se abre.
