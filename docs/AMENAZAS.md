# Modelo de amenazas

[English](AMENAZAS.en.md)

Qué protege la app, de quién, con qué defensa, y qué test se rompe si alguien
la debilita. Está escrito para el próximo cambio en `app/server.py`: antes de
tocar una cabecera o un control, acá dice contra quién existe.

## Qué hay que cuidar

| Qué | Dónde vive |
|---|---|
| La clave de YouTube de quien usa la app | `~/.migrador-catalogos/config.json`, con permisos 0600 en una carpeta 0700 |
| La sesión de Tidal, si se conectó | En memoria, mientras la app está abierta |
| El catálogo relevado y el ZIP armado | En memoria y en un temporal del sistema, hasta que la app se cierra o vence el trabajo |
| La máquina de quien la usa | Todo lo anterior corre ahí, con sus permisos |

## De quién

La app es un servidor HTTP en `127.0.0.1` con una interfaz web. El riesgo
propio de ese diseño no es alguien en internet, que no llega a `127.0.0.1`,
sino lo que corre en la misma máquina con menos permisos que la persona.

| Quién | Qué podría hacer | Defensa | Test que la cubre |
|---|---|---|---|
| **Una página web cualquiera** abierta en el navegador de la misma máquina | Mandarle pedidos a `localhost` y operar la app: relevar, leer el catálogo, conectar Tidal | **1. Token de sesión**: nuevo en cada arranque, inyectado en `index.html`, exigido en toda ruta `/api/` en la cabecera `X-App-Token`. Otra página no lo puede leer porque el origen es distinto. Encima, `Sec-Fetch-Site` y `Origin` cortan antes a lo que el navegador marca como ajeno | `tests/test_app.py`: `test_sin_token_no_se_toca_la_api`, `test_con_un_token_equivocado_tampoco`, `test_sin_token_ni_siquiera_se_parsea_el_cuerpo` |
| **La misma página, con rebinding de DNS**: un dominio suyo que después resuelve a `127.0.0.1`, para que el navegador la trate como del mismo origen y le deje leer el token | Saltear la defensa 1 | **2. Control de `Host`**: sólo `127.0.0.1`, `localhost` o `[::1]`. Con rebinding, el `Host` sigue siendo el dominio del atacante | `test_un_host_ajeno_se_rechaza`, `test_los_estaticos_no_piden_token_pero_si_controlan_el_host`, `test_el_ticket_no_saltea_el_control_de_host`, `test_cada_host_de_la_lista_se_puede_alcanzar` |
| **Un título hostil**: lo que viene de YouTube, Deezer o Apple, que la app muestra | Meter HTML o un script en la interfaz, que correría con el token a mano | **3. CSP** sin scripts inline ni orígenes externos, y `esc()` en todo lo que se dibuja | `test_la_pagina_declara_una_csp`, `test_la_csp_no_habilita_ningun_origen_externo`, `test_la_pagina_cumple_su_propia_csp`; `tests/js/app.test.mjs` para `esc()` |
| **Otra pestaña que adivina el puerto** | Mostrar la app adentro de un iframe y engañar clics (aceptar los términos, conectar Tidal) | `X-Frame-Options: DENY`, `frame-ancestors 'none'`, COOP y CORP. Suman a las tres, no reemplazan ninguna | `test_ninguna_respuesta_se_puede_meter_en_un_iframe` |
| **Un título hostil que llega al ZIP** | Una fórmula que Excel ejecuta al abrir la planilla, o un nombre de carpeta que se escapa de la raíz del ZIP | Las fórmulas se escriben como texto; cada ruta del ZIP se arma con partes seguras y se rechaza si sale de su raíz | `tests/test_entrada_hostil.py`, `tests/test_nombres_zip.py` |
| **Una portada que no es de Apple** | Hacer que la app pida una URL cualquiera | Sólo se aceptan `https` de `*.mzstatic.com`, con tope de tamaño | `test_solo_se_aceptan_portadas_del_cdn_de_apple`, `test_una_url_ajena_no_se_pide` |
| **Un error que muestra la clave** | Que la clave aparezca en un log, un reporte o un mensaje | La clave viaja en la cabecera `X-Goog-Api-Key`, nunca en la URL, y ningún error la repite | `tests/test_secretos.py` |
| **Una clave en el repositorio** | Que alguien la commitee | `build/sin_claves.py`, en cada commit (pre-commit) y en el CI, también sobre toda la historia | `test_una_clave_que_entro_y_salio_se_encuentra_en_la_historia` |

## Lo que queda afuera, y por qué

- **Un proceso local del mismo usuario.** Puede pedir `GET /` y leer el token de
  la página, como puede leer `config.json` con la clave. Está bien que así sea:
  quien ya corre código con los permisos de la persona tiene todo lo que la app
  podría proteger. Las defensas de arriba son contra lo que tiene *menos*
  permisos: una página web, que vive encerrada en el navegador.
- **Que se pueda extraer la clave incluida en la variante `completa`.** Está
  dicho en el README; la clave está restringida a la YouTube Data API v3 y con
  tope de cuota, y la variante `esencial` no la trae.
- **Un binario cambiado en el camino.** El binario no está firmado. Lo que se
  puede verificar es el SHA256 que publica cada release, y la atestación de
  procedencia de GitHub cuando el repositorio es público (el workflow la
  saltea en un repositorio privado, y un fallo al generarla no frena el
  release).
- **Las dependencias del módulo de audio** (`tiddl`, `yt-dlp`, `ffmpeg`). La
  app las invoca con argumentos fijos y fin de opciones, pero lo que hagan
  adentro se reporta a sus proyectos.

## Qué no romper

Las tres defensas —token, `Host` y CSP— no se debilitan (regla 1 de
[CONTRIBUTING.md](../CONTRIBUTING.md)). Si un cambio necesita una excepción, por
ejemplo una ruta que un enlace tiene que poder abrir sin cabecera, se hace como
la descarga del ZIP: un ticket de un solo uso, que vence en un minuto, que sólo
se obtiene con el token y que igual pasa por el control de `Host`.
