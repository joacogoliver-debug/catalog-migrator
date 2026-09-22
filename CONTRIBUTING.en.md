# How to contribute

[Español](CONTRIBUTING.md) · **English**

Thanks for looking at the code. This file says what you need to know before
touching anything, so that you do not find out halfway through a pull request
that there was a rule written down nowhere.

It is a small project maintained by one person. If your change is a big one, open
an issue first and let's talk: it is cheaper than writing it twice.

## Getting started

```bash
pip install -r requirements-app.txt
pip install -r requirements-dev.txt
pre-commit install
python app/launcher.py
```

That gets you the app running and the checks hooked into your commits.

## Before sending the pull request

In this order, skipping none.

```bash
pytest -q --cov      # tests and coverage, which cannot drop below the threshold
ruff check .         # errors and style
ruff format .        # formatting
pyright              # types, today at zero errors
```

If you touched the interface, also:

```bash
python build/capturas.py     # regenerates the README screenshots
```

And if you touched anything about packaging:

```bash
python build/build.py
# then open the binary left in dist/ with --diagnostico
# (on Windows it is "Migrador de Catalogos.exe")
```

`build/build.py` runs the suite before packaging and aborts if anything fails, so
a published binary has always passed its tests.

## The rules that are not up for negotiation

These are not style preferences. Each one is there because of something concrete
that happened, or that we wanted to avoid.

### 1. The three local-server defenses

The server listens on `127.0.0.1`, but that alone is not enough: any page open in
that same machine's browser can send it requests. That is why there are three
further defenses, and all three have tests.

1. **Session token**, new at every startup, injected into `index.html` and
   demanded on every `/api/` route.
2. **`Host` check**, which accepts only `127.0.0.1` and `localhost`, and cuts off
   DNS rebinding.
3. **CSP**, which does not let the page request or execute anything from outside.

**None of them gets weakened.** Any change to `app/server.py` comes with a new or
modified test covering what you touched.

### 2. No frameworks and no build step

Backend on `http.server` from the standard library. Frontend in vanilla
JavaScript and CSS over the tokens in `app/web/tokens/`. No ORM, no bundler, no
CDN.

This is not purism. Packaging has to stay a matter of copying files: the day
there is a build step, the executable depends on that step working on four
operating systems, and an ASGI framework's dynamic imports are the usual reason a
binary works in development and fails once packaged.

### 3. Metadata is never invented

Anything that does not come from a public source stays as `<<COMPLETAR>>` in the
ingestion sheet. Not empty, not filled in by eye.

The two heuristics that exist are documented and stated in the README: track
order is estimated from upload date, and the format (single / EP / album) is
derived from the track count. **If you change either, update the README in the
same commit.**

### 4. The YouTube key never enters the repository

Not in the code, not in a test, not in a fixture, not in a log. It lives as a CI
secret and enters only at build time, from `MIGRADOR_CLAVE_YT`.

`build/sin_claves.py` checks this on every commit and in CI. If it blocks you, do
not work around it: a key that made it into a commit is already considered
leaked, because the object stays in the history and in every clone.

### 5. Everything the user reads goes in both languages

The app is in Spanish and English, all of it, including what it downloads. There
are two catalogs because there are two processes.

| Where | What for |
|---|---|
| `i18n.py` | What Python builds: the log, the errors, the files in the ZIP |
| `app/web/i18n.js` | The interface |

`tests/test_i18n.py` checks that no key is half-translated, that the interface
uses no undefined keys and defines no unused ones, and that both catalogs agree
on file names. If you add text and do not translate it, the test tells you before
a user does.

Two exceptions, both deliberate. The `SIN_ALBUM` and `SIN_DATOS` sentinels in
`productos.py` are not translated, because filtering and grouping compare them by
equality. Neither are the ingestion sheet columns, because those are field names
the distributor expects, not text to read.

## Style

Formatting is settled by `ruff format` and there is nothing to argue about. On
everything else, two things this code does on purpose.

**Comments say why, not what.** A comment repeating what the line already says is
noise. One explaining why that line is the way it is, and what broke when it was
not, is what makes the code touchable six months from now. Most of the long
comments in this repository are the chronicle of a real bug.

**Names live in both languages** and there is no rule ordering them. The older
modules stayed in English (`group_products`, `build_zip`, `filter_products`) and
the newer ones are in Spanish (`empaquetar`, `relevar_catalogo`, `validar`). What
is respected is not renaming for taste: a rename is a large diff that fixes
nothing and buries the real changes.

## Commits

Conventional, with the type up front. **Commit messages and code comments are
written in Spanish**, like the rest of the repository; issues and pull request
descriptions can be in either language.

```
feat(portadas): pedir 3000x3000 y reportar lo que Apple devuelve
fix(macos): faltaba el binario para las Mac Intel
test(seguridad): la CSP, que era la unica de las tres defensas sin test
```

Types used here: `feat`, `fix`, `refactor`, `test`, `docs`, `build`, `chore`,
`style`.

The body matters more than the subject. Say what used to break, not which files
you touched: the diff already says that.

## Where everything lives

| File | What it does |
|---|---|
| `app/launcher.py` | Entry point: free port, server, window or browser |
| `app/server.py` | JSON API, static files and the three defenses |
| `app/jobs.py` | Background jobs with progress and cancellation |
| `app/web/` | The interface |
| `contratos.py` | The shape of the data that travels between modules |
| `relevar_core.py` | YouTube survey plus ISRC and UPC from Deezer |
| `productos.py` | Groups tracks into products and filters the selection |
| `validar.py` | Pre-delivery validation |
| `portadas.py` | Artwork via the iTunes Search API |
| `paquete.py` | Spreadsheets, ingestion sheet, reports and ZIP |
| `audio.py` | Optional audio module |
| `migrar_core.py` | Orchestrates the four steps |
| `build/` | Packaging, installer, icon, screenshots and the key check |
| `docs/` | Product and design decisions |

`docs/marca/` is the logo and its usage rules. It is not to be touched.

## Reporting something

- **A security problem** goes privately, through the
  [Report a vulnerability](https://github.com/joacogoliver-debug/catalog-migrator/security/advisories/new)
  form, never as a public issue. The detail is in [SECURITY.md](SECURITY.md).
- **Everything else**, as an issue. There are templates, and filling them in
  saves the round trip of asking for the version and the operating system.

If the app does not open, `--diagnostico` leaves a report of what it can do on
your machine, and attaching it usually settles the issue in one message.

## License

By contributing you accept that your work is published under the project's MIT
license, and that the intended use and its limits are those in
[TERMS.md](TERMS.md). This tool is for catalog administration, and it neither
endorses nor enables piracy.
