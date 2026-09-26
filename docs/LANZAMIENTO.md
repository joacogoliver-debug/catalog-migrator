# Material de lanzamiento

[English](LANZAMIENTO.en.md)

Todo lo que hace falta para presentar la app afuera del repositorio, listo para
usar. **Nada de esto está publicado**: subir la imagen, cambiar la descripción,
activar la página y postear son decisiones de quien administra el repositorio.
Los textos no traen cifras de uso ni testimonios, porque no hay ninguno medido.

## Lo que falta hacer, y dónde

| Qué | Dónde | Archivo |
|---|---|---|
| Subir la imagen para redes | GitHub → Settings → General → Social preview | [`redes/social-preview.png`](redes/social-preview.png), de 1280×640. Se regenera con `python build/imagen_redes.py` |
| Cambiar la descripción del repo | GitHub → la rueda de «About» | La de abajo |
| Cambiar los topics | GitHub → la rueda de «About» | La lista de abajo |
| Activar la página | GitHub → Settings → Pages → rama `main`, carpeta `/docs` | [`index.html`](index.html) y [`en.html`](en.html) |
| Poner la página como sitio del repo | La rueda de «About» → Website | `https://joacogoliver-debug.github.io/catalog-migrator/` |

## Descripción del repositorio

Una sola, en los dos idiomas, porque la búsqueda de GitHub no separa por idioma:

> Cambiá de distribuidora sin perder los códigos: ISRC, UPC, portadas, hoja de
> ingesta y validación desde el canal de YouTube del artista. · Switch music
> distributors without losing your catalog's ISRCs and UPCs.

## Topics

`music-distribution` · `music-catalog` · `catalog-migration` · `isrc` · `upc` ·
`metadata` · `youtube-api` · `deezer-api` · `music-industry` · `desktop-app` ·
`python`

`distribution` a secas, que es el que está hoy, se confunde con distribuciones
de Linux y de paquetes.

## LinkedIn

> Cambiar de distribuidora es fácil hasta que te das cuenta de que el catálogo
> tiene que llegar con los mismos ISRC y UPC, porque un código nuevo es un
> release nuevo que arranca sin sus reproducciones ni sus playlists.
>
> Hice una app gratuita y de código abierto para eso: pegás el canal de YouTube
> del artista y arma el paquete para la distribuidora nueva, con los códigos que
> se pueden recuperar, las portadas en alta resolución, una hoja de ingesta y una
> validación de lo que las distribuidoras suelen rechazar. Corre en tu
> computadora, sin cuentas.
>
> Es para sellos chicos, managers y artistas que administran su catálogo.
> Windows, macOS y Linux: https://github.com/joacogoliver-debug/catalog-migrator

## Foros y comunidades de artistas

> **Una herramienta gratis para migrar un catálogo de distribuidora sin perder
> los códigos**
>
> Si estás por cambiar de distribuidora, lo que más duele perder son los ISRC y
> los UPC: con códigos nuevos, cada release arranca de cero. Hice una app de
> código abierto que, a partir del canal Topic de YouTube del artista, recupera
> los códigos que tiene Deezer, baja las portadas de Apple Music y arma una hoja
> de ingesta, con una validación previa. No se conecta con ninguna distribuidora
> ni pide cuentas: los archivos los cargás vos.
>
> Lo que no hace, para que nadie se lleve una sorpresa: no genera DDEX, no
> inventa lo que no está publicado (género, territorios, explicit quedan para
> completar) y el audio es un módulo aparte, apagado, que usa tu propia cuenta.
>
> https://github.com/joacogoliver-debug/catalog-migrator

## Directorios de software

Para los que piden una descripción corta y una larga:

- **Corta:** Arma el paquete para migrar un catálogo musical a otra distribuidora
  sin perder ISRC ni UPC.
- **Larga:** El primer párrafo del [README](../README.md), que es la promesa, más
  «Para quién es».
