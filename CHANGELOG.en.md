# Changelog

[Español](CHANGELOG.md) · **English**

What changed in every published version. The numbers follow
[SemVer](https://semver.org/), and the downloads are in
[Releases](https://github.com/joacogoliver-debug/catalog-migrator/releases).

## [Unreleased]

### Changed
- **The test suite runs on pytest.** The ten files were scripts with a `main()`
  and a list of strings, and `pytest -q` collected none of them: it exited
  successfully having run nothing. They are now 267 real tests, with
  `tests/conftest.py`, shared fixtures for the sample catalog, and the language
  pinned in a single place.
- **A single list of tests.** It was written three times, in `build/build.py`,
  in the CI workflow and in the README, so a new test meant remembering three
  places, and one forgotten in `build.py` did not block a release. It now comes
  from `testpaths` in `pyproject.toml`.
- CI runs one test step instead of eleven, and `build/build.py` runs the same
  suite before packaging. If pytest collects nothing, the build aborts.

### Added
- **The engine is a package, `migrador`, and lives in `src/`.** The ten modules
  were loose in the root and every file set up `sys.path` by hand. Now `app/`
  consumes the package and that arrow points one way, so the core is tested
  without starting a server. The launchers moved to `scripts/`, and
  `pyproject.toml` declares the `[app]`, `[audio]` and `[dev]` extras, which a
  test checks against the `requirements-*.txt` files so they cannot drift apart.
- **Each release's notes come out of the CHANGELOG.** They used to be 125 lines
  written by hand inside the workflow, in two languages, and they did not say
  what had changed: the CHANGELOG existed and nobody read it when publishing.
  They are now built by `build/notas_release.py`, which also aborts if the
  CHANGELOG has no entry for the version being tagged.
- **Contract tests against real Deezer and iTunes responses.** Hand-written
  doubles prove the code is consistent with itself, not that it understands what
  the APIs return. There are now seven recorded responses in `tests/fixtures/`,
  with their URL and date, and the tests run the real client against them. They
  still touch no network.
- `texto.py`, with a single implementation of text normalization and safe file
  names. They were written six times across five modules, nearly identical but
  not quite.
- `CONTRIBUTING` and issue templates, in both languages. The six rules that are
  not up for negotiation (the three defenses, no frameworks, never invent
  metadata, the key stays out of the repository, every string translated and an
  honest README) lived in the maintainer's head and are now written down.
- **The contract between modules is written down, in `contratos.py`.** What
  the survey returns and what products, validation, artwork and packaging consume
  no longer lives in the docstrings. They are TypedDicts, so they do not exist at
  runtime and the program runs the same, but pyright checks them. The
  orchestrator contract test no longer repeats the keys by hand: it reads them
  from there.
- **The linter, the formatter and the type checker run on their own.**
  `pre-commit` runs ruff and an API-key check before every commit, and CI adds
  `ruff format --check` and `pyright`, which today runs at zero errors. The key
  check is a single script, `build/sin_claves.py`, shared between the hook and CI.
- **The CSP has a test.** Of the three local-server defenses it was the only one
  without one, and it is a loose string inside a method, so loosening it broke
  nothing. It now checks that the header is intact, that no directive opens an
  external origin, that inline scripts stay forbidden, and that the page itself
  does not break its own policy.
- **Coverage with a threshold.** `pytest -q --cov` measures the app and fails if
  it drops below the threshold in `pyproject.toml`. The threshold is set where
  we are, not where we would like to be.
- `requirements-dev.txt` with the developer tooling.
- `docs/AUDITORIA.md` and `docs/MEJORAS.md`, the repository diagnosis and the
  backlog that comes out of it.

### Fixed
- Coverage listed the modules by name, so moving one silently dropped it from
  the measurement and the percentage went up without anyone writing a test. It is
  now measured by folder.
- **An artist spelled with an accent did not find the same one spelled without
  it on Tidal.** The normalization the audio module used did not strip accents,
  unlike the other two, and with no exact match the search fell back to whatever
  Tidal returned first.
- A product's folder name could end in a dot when the title was long and the
  truncation landed there. Windows does not accept that name, and the error only
  showed up when unzipping, on somebody else's machine.
- The README had an image with no blank line before it, which split the "How it's
  built" list in two. The English version was fine.
- The docstring in `build/capturas.py` said the README screenshots come out in the
  light theme, while the code has been generating them in dark since that became
  the theme the app opens in.
- When surveying a channel that is not a Topic, the app switches to the
  artist's Topic. If YouTube returned the uploads playlist but not the channel
  title, the switch happened anyway and the whole catalog ended up credited to
  nobody. Both are now required.
- `relevar_core.py` used `urllib.error` without ever importing it. It worked by
  accident, because `urllib.request` imports it internally, but any change to
  that standard-library detail would have broken YouTube error handling with no
  warning. pyright found it.

## [1.0.2] — 2026-09-21

### Added
- **The app is in Spanish and English, all of it**: the interface, the survey
  log, the error messages, and also what gets downloaded (the names of the files
  inside the ZIP, the spreadsheet headers and the validation report). The
  Windows installer asks for the language on its first screen, and it can be
  switched any time from the selector in the header.
- `SECURITY.md` with what is in scope and what is not, and where to report
  privately.
- The linter (`ruff`) runs in CI before the tests, configured in
  `pyproject.toml`.
- CI **runs the executable** it is about to publish, on all four platforms, and
  fails the build if it does not get to serve the app. Binaries used to be
  published without anyone ever having run them.

### Fixed
- **The executable for Intel Macs was missing.** Only one was compiled, on an
  Apple Silicon runner, and it was published under the name "macos": on an Intel
  Mac it does not start. Both are now published, `macos-apple-silicon` and
  `macos-intel`, and there is a [macOS install guide](docs/INSTALAR-MAC.en.md).
- The browser in app mode was not looked up in `~/Applications`, where on a Mac
  it is just as common to have it installed.
- The artwork progress bar froze at 5 % with the app in English: it was being
  inferred from the log text with a Spanish regular expression. Progress now
  travels through a callback and nothing is parsed.
- The step 3 title band overflowed its card by 24 px on each side.
- Numbers were always formatted with the Spanish convention, so English read
  "7.000 plays" where it should say "7,000".
- One translation key was defined twice: Python silently keeps the last one, and
  the English app said "products" where the rest of the interface says
  "releases".

### Changed
- The tests live in `tests/`, and the product and design decisions in `docs/`.
- The interface audit's working material left the repository: it was the
  process, not the product.

## [1.0.1] — 2026-09-15

### Changed
- Full interface redesign: it stopped reading as a stacked document and became
  an application with its four steps in view, on the brand palette (graphite,
  bone and the teal ramp).
- The logotype, in the header and in the executable's icon.
- The distributor classification was removed: it was a list that aged by itself
  and added nothing to a migration.

### Fixed
- Packaging still asked for the old typefaces and failed to build.
- DistroKid's numeric label was being read as the release year.

## [1.0.0] — 2026-09-14

First public version.

- Survey of an artist's catalog from their YouTube channel (Topic, official
  channel or `@handle`).
- **ISRC** and **UPC** through Deezer, no key and no cost.
- Artwork through the iTunes Search API, reporting the resolution Apple returned
  and not the one that was requested.
- **Pre-delivery validation** that separates what the distributor rejects from
  what merely deserves a look.
- **Ingestion sheet** in CSV with the standard columns, and whatever cannot come
  from public sources marked `<<COMPLETAR>>`.
- ZIP with one folder per release.
- **Optional** audio module, off by default: lossless FLAC with the user's own
  paid Tidal account, and lossy reference from YouTube, every file labeled by
  what it actually is.
- Executables for Windows, macOS and Linux compiled in GitHub Actions, with
  SHA256 and a build provenance attestation.

[1.0.2]: https://github.com/joacogoliver-debug/catalog-migrator/releases/tag/v1.0.2
[1.0.1]: https://github.com/joacogoliver-debug/catalog-migrator/releases/tag/v1.0.1
[1.0.0]: https://github.com/joacogoliver-debug/catalog-migrator/releases/tag/v1.0.0
