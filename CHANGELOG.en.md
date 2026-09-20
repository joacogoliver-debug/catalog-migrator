# Changelog

[Español](CHANGELOG.md) · **English**

What changed in every published version. The numbers follow
[SemVer](https://semver.org/), and the downloads are in
[Releases](https://github.com/joacogoliver-debug/catalog-migrator/releases).

## Unreleased

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

### Fixed
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

[1.0.1]: https://github.com/joacogoliver-debug/catalog-migrator/releases/tag/v1.0.1
[1.0.0]: https://github.com/joacogoliver-debug/catalog-migrator/releases/tag/v1.0.0
