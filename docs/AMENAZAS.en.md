# Threat model

[Español](AMENAZAS.md)

What the app protects, from whom, with which defense, and which test breaks if
someone weakens it. It is written for the next change to `app/server.py`: before
touching a header or a check, this says who it exists against.

## What needs protecting

| What | Where it lives |
|---|---|
| The user's YouTube key | `~/.migrador-catalogos/config.json`, mode 0600 inside a 0700 folder |
| The Tidal session, if connected | In memory, while the app is open |
| The surveyed catalog and the built ZIP | In memory and in a system temp folder, until the app closes or the job expires |
| The user's machine | Everything above runs there, with their permissions |

## From whom

The app is an HTTP server on `127.0.0.1` with a web interface. The risk that
comes with that design is not someone on the internet, who cannot reach
`127.0.0.1`, but whatever runs on the same machine with fewer permissions than
the person.

| Who | What they could do | Defense | Test that covers it |
|---|---|---|---|
| **Any web page** open in a browser on the same machine | Send requests to `localhost` and drive the app: survey, read the catalog, connect Tidal | **1. Session token**: new on every start, injected into `index.html`, required on every `/api/` route in the `X-App-Token` header. Another page cannot read it because the origin differs. On top, `Sec-Fetch-Site` and `Origin` cut off early whatever the browser flags as foreign | `tests/test_app.py`: `test_sin_token_no_se_toca_la_api`, `test_con_un_token_equivocado_tampoco`, `test_sin_token_ni_siquiera_se_parsea_el_cuerpo` |
| **The same page, with DNS rebinding**: a domain of theirs that later resolves to `127.0.0.1`, so the browser treats it as same-origin and lets it read the token | Get around defense 1 | **2. `Host` check**: only `127.0.0.1`, `localhost` or `[::1]`. With rebinding, `Host` is still the attacker's domain | `test_un_host_ajeno_se_rechaza`, `test_los_estaticos_no_piden_token_pero_si_controlan_el_host`, `test_el_ticket_no_saltea_el_control_de_host`, `test_cada_host_de_la_lista_se_puede_alcanzar` |
| **A hostile title**: what comes from YouTube, Deezer or Apple, which the app displays | Inject HTML or a script into the interface, which would run with the token at hand | **3. CSP** with no inline scripts and no external origins, and `esc()` on everything that is drawn | `test_la_pagina_declara_una_csp`, `test_la_csp_no_habilita_ningun_origen_externo`, `test_la_pagina_cumple_su_propia_csp`; `tests/js/app.test.mjs` for `esc()` |
| **Another tab that guesses the port** | Show the app inside an iframe and trick clicks (accept the terms, connect Tidal) | `X-Frame-Options: DENY`, `frame-ancestors 'none'`, COOP and CORP. They add to the three, they replace none | `test_ninguna_respuesta_se_puede_meter_en_un_iframe` |
| **A hostile title that reaches the ZIP** | A formula Excel runs when the sheet opens, or a folder name that escapes the ZIP root | Formulas are written as text; every ZIP path is built from safe parts and refused if it leaves its root | `tests/test_entrada_hostil.py`, `tests/test_nombres_zip.py` |
| **A cover that is not from Apple** | Make the app fetch an arbitrary URL | Only `https` from `*.mzstatic.com`, with a size cap | `test_solo_se_aceptan_portadas_del_cdn_de_apple`, `test_una_url_ajena_no_se_pide` |
| **An error that shows the key** | The key showing up in a log, a report or a message | The key travels in the `X-Goog-Api-Key` header, never in the URL, and no error repeats it | `tests/test_secretos.py` |
| **A key in the repository** | Someone committing it | `build/sin_claves.py`, on every commit (pre-commit) and in CI, also over the whole history | `test_una_clave_que_entro_y_salio_se_encuentra_en_la_historia` |

## What is left out, and why

- **A local process of the same user.** It can request `GET /` and read the
  token from the page, just as it can read `config.json` with the key. That is
  as it should be: whoever already runs code with the person's permissions has
  everything the app could protect. The defenses above are against what has
  *fewer* permissions: a web page, locked inside the browser.
- **That the bundled key in the `completa` variant can be extracted.** The
  README says so; the key is restricted to YouTube Data API v3 and capped, and
  the `esencial` variant does not carry it.
- **A binary tampered with on the way.** The binary is unsigned. What can be
  checked is the SHA256 each release publishes, and GitHub's build provenance
  attestation when the repository is public (the workflow skips it on a
  private repository, and a failure to produce it does not stop the release).
- **The audio module's dependencies** (`tiddl`, `yt-dlp`, `ffmpeg`). The app
  calls them with fixed arguments and an end-of-options marker, but what they
  do inside is reported to their projects.

## What not to break

The three defenses —token, `Host` and CSP— are not weakened (rule 1 of
[CONTRIBUTING.en.md](../CONTRIBUTING.en.md)). If a change needs an exception,
for instance a route a link has to open without a header, it is done like the
ZIP download: a single-use ticket that expires in a minute, can only be
obtained with the token, and still goes through the `Host` check.
