# Changelog

[Español](CHANGELOG.md) · **English**

What changed in every published version. The numbers follow
[SemVer](https://semver.org/), and the downloads are in
[Releases](https://github.com/joacogoliver-debug/catalog-migrator/releases).

## [Unreleased]

### Added
- If Deezer did not answer, the log says so. Before, it looked the same as "no
  codes for this artist".
- **The ingestion sheet also comes in Excel**, `_Ingestion sheet.xlsx`, with
  the same rows as the CSV, every cell as text and what is missing
  highlighted. The CSV does not survive going through Excel: the UPC loses its
  leading zero and turns into scientific notation, `3:20` is read as a time and,
  with some regional settings, everything falls into one column. The READ ME
  says so, and also names the fields a distributor may ask for that the sheet
  does not carry because they do not come from anywhere public.
- **The ingestion sheet carries the credits YouTube publishes.** Each Art
  Track says who composed, wrote the lyrics and produced the song, when the
  original distributor sent it, and the sheet marked it as impossible to get.
  In real data, 46 of 50 songs had a composer. They now go in `Composer`,
  `Lyricist`, `Producer` and `Publisher`, and what is missing is still to be
  filled in.
- Each song's artist is the one YouTube names, and the others go in the new
  `Additional Artists` column. Before, every song came out under the channel's
  name and the featured artists were lost. If the channel's artist is not a
  song's main artist, the validation warns to check who controls that master.
- **Track and disc numbers are the real ones when Deezer has the album.** The
  app already downloaded the tracklist and threw it away, and the sheet carried
  the order estimated from the upload date with no mark at all. Now, if the
  Deezer album was verified as the same release, each song takes its position
  and disc. Otherwise the order is still estimated and the sheet's
  `Track Order` column says so. On real data, a 22-song double album keeps its
  two discs, and two songs Deezer places on the same record stop showing up as
  two releases.
- The ingestion sheet has an `Original Release Date` column, with the same
  real date as `Release Date`, because each distributor asks for it in one of
  the two. The READ ME explains which one to use if the new distributor asks
  for a different go-live date.
- The link field also takes a bare `UC…` ID, `/user/` and `/c/` links, and
  the link of any of the artist's songs (`watch?v=`, `youtu.be`, `/shorts/`,
  YouTube Music): the app looks up the channel that uploaded it, for one unit of
  quota.
- `docs/AUDITORIA-2.md` and `docs/MEJORAS-2.md`, the diagnosis of the second
  improvement cycle and the backlog that comes out of it. This time the
  repository was looked at from six separate angles (music industry,
  distribution and metadata, software, interface, security and outreach), each
  on its own, following the rubric in `docs/BRIEF-AUTOMEJORA.md`.

### Fixed
- "One job at a time" was checked and registered separately, and two
  simultaneous requests (a slow double click, two windows) could both get
  through. Both things now happen together.
- With two windows open, if another artist was surveyed in one, the other built
  that artist's package with the releases it had picked from the previous one.
  The catalog now has an identifier and the server refuses it with a warning.
- Cancelling the package halfway through the audio downloads left several GB in
  the temporary folder until the next day, and a new package left the previous
  one's ZIP behind. Both are now removed right away.
- A request with no releases picked built the package of the whole catalog. The
  interface does not send it that way, but it is now an error.
- **"Cancel" took tens of seconds to respond during the code lookup**, and the
  bar stayed stuck at 55%. With 600 songs it measured 24 seconds, and meanwhile
  the app refused a new survey as "job in progress". The Deezer lookup, the
  video listing and the metadata now report progress at every step, and
  cancelling stops there. Building the package goes by stages (covers, audio,
  ZIP) instead of sitting at 85% during the longest phase.
- A `Retry-After` with a date brought the whole survey down, with the YouTube
  quota already spent.
- Deezer retried any error six times, with waits, including "no data", which is
  permanent: nine seconds lost per request. It now retries only the rate limit
  and a busy service, with growing waits. YouTube also retries its rate limit,
  which used to stop on the spot.
- "(En Vivo)" and "(Live Session)" showed up as YouTube text carried into
  the title, and they are part of a version's real title. Meanwhile "(Audio)",
  "(Letra)", "[MV]" or "(Videoclip Oficial)" slipped through, and the
  release title was not checked.
- The same UPC written with 12 and with 13 digits was not caught as a duplicate,
  an all-zeros UPC passed as valid, and the ISRC was exported with whatever
  dashes or lowercase it came with.
- **The Label column carried the whole ℗ line, license included**: "Small
  Label under exclusive license to Warner". It is now the holder, without the
  license, and real lines with more than one ℗ no longer give "℗ Distributed
  exclusively by…". The P Line, on the other hand, goes whole and exactly as
  the original distributor published it; before, it was built from the release
  year, and a 2023 edition with ℗ 2013 recordings came out with a ℗ that is not
  the real one.
- `Territories` was fixed to `Worldwide` and `Disc Number` to 1. Both were
  made up: a catalog licensed for one region was opened to the world, and a
  double album came out entirely on the first disc. They are now to be filled
  in when not known.
- Two releases with the same title but released years apart (the original and
  its anniversary edition) got crossed: the new edition's songs took the
  original's UPC and tracklist. The date now has to match too.
- **A release could come out split into two, or two releases merged into
  one.** Songs were grouped by album and ℗ year, and that year belongs to each
  recording: a record's anniversary edition, with original ℗ 2013 songs and new
  ℗ 2023 ones released the same day, came out as two releases with the same UPC.
  And the same album delivered by two distributors was merged into one with the
  tracks duplicated. A release is now built by album, distributor and release
  date, its year is the release year, and if the same record is at two
  distributors there is a warning, which is what happens halfway through a
  migration. On fifty real songs, the fifteen releases of before became eleven,
  each one a release that exists.
- **The ingestion sheet named files that were not in the ZIP.** The audio
  column carried the temporary file's name (`tidal_998877.flac`) while the ZIP
  called it `01 - Song.flac`, and the cover column said `portada.jpg` even when
  in English the file was `cover.jpg`, or when no covers had been asked for. In
  a bulk upload the distributor matches each row with its file by that name, so
  it found none. The sheet, the spreadsheets and the ZIP now take the name from
  the same place, with the path inside the package, and what was not included
  stays empty.
- **A single could end up with the album's UPC, and with its cover.** Deezer
  finds the recording, which is on the single, on the album and on every
  compilation, and the UPC of any of them landed on the release without checking
  it was the same one. Since the cover is looked up by UPC first, it also
  downloaded the other one's artwork. The UPC is now accepted only if the Deezer
  album is this release; otherwise it stays blank and the validation says where
  it was found. On fifty real songs, the seven that get dropped are all from
  another release (a single against the album, the standard edition against the
  anniversary one). It also warns when the tracks of one release bring different
  UPCs.
- **The release date in the ingestion sheet was the YouTube upload date.**
  For back catalog that can be decades off: in real data, a 2001 song shows as
  uploaded in 2024, and the migrated release went out with that date. When it
  was missing, a January 1st was also built from the year, which is making the
  value up. The date YouTube publishes for every song, in "Released on:", is
  used now, and if it is not there the field stays as `<<COMPLETAR>>`.
- **An `@handle` with an accent or an ñ could survey another artist's
  catalog.** The browser copies `youtube.com/@pe%C3%B1a`, encoded, and the app
  stopped at the `%`: it asked for `@pe`, and if that channel existed it surveyed
  it without any error. The link is now decoded before reading it.
- **A live version, a remix or a remaster took the studio version's ISRC.**
  Before searching Deezer, the app stripped from the title exactly what says
  which version it is: "Song (Live)" became "Song", matched the studio one one
  hundred percent and took its code, with high confidence, even with the live
  version among the results. Now only what comes from YouTube is cleaned, a
  candidate of another version is dropped, and if there is none of the same
  version the code stays blank. The same for covers: a live album no longer gets
  the studio one's cover.
- The "medium" confidence of a code did not look at the length, and a Deezer
  result with no artist counted as the same artist.
- **The validation asked to "fix" an ISRC that was right.** The same
  recording on the single and on the album carries the same ISRC, as it should,
  but the app flagged it as an error and the package stopped being fit. The
  obvious way out was to ask for a new code, which splits the recording's
  history. It is now a warning that says to keep it. It is still an error when
  repeated within one release, and it becomes one on its own when the same code
  shows up on two recordings that do not look like the same one, because it
  almost certainly came from a wrong match.
- **A release could overwrite another one's files when the ZIP was unpacked.**
  Two singles with the same title and year and no UPC, two titles that only
  differ after the sixtieth character, or titles in a non-Latin script, which all
  become "Sin titulo" when turned into ASCII, ended up in the same folder: one's
  cover and spreadsheet replaced the other's. Each release now gets its own
  folder, with `(2)` when needed.
- Paths inside the ZIP could go past the 260 characters Windows allows, and
  "Extract all" failed on the machine of whoever received the delivery. There is
  now a cap for the whole path, taken out of the song title without ever
  touching the track number or the lossy audio mark.
- The UPC went into the folder name as is. Only its digits go in now, and the
  build refuses to write an entry that would land outside the package folder.
- **Three inputs coming from outside could execute something.**
  - yt-dlp read a `yt-dlp.conf` from the folder the app was opened from, which
    for the portable executable is usually Downloads, and a planted `--exec`
    there ran whatever it said. It is now called with `--ignore-config`, in the
    job's own folder, and never looked up in the working folder.
  - A title, label or artist starting with `=` went into the spreadsheets as a
    live formula, and as is into the ingestion sheet. In the spreadsheets it is
    now plain text. In the sheet it gets a leading apostrophe only when it
    really looks like a formula, so a release called "+" or "-Intro-" is left
    alone, and the validation warns every time a value was changed.
  - The cover was downloaded from whatever URL iTunes sent, unchecked: with
    `file:///` a file on disk was read and ended up in the ZIP. It is now only
    downloaded from Apple's CDN, over HTTPS and with a size cap.
- The full variant ships yt-dlp inside, but the download looked for it as a
  separate program: on a machine without yt-dlp installed it said it could fetch
  the reference audio and failed when it tried. It now uses the one it ships.
- **The package could not be downloaded from the app.** The "Download" button
  was a direct link to the API, and a link cannot send the header with the
  session token, so the server turned it down. It had been like that since the
  first public version, and the native window also had downloads switched off.
  The button now asks first for a single-use ticket, which expires in a minute
  and can only be obtained with the token, and the download works in the window
  and in the browser without loosening any of the three defenses.
- The README screenshots showed version 1.0.1 in the footer while the app was
  already 1.1.0. They were regenerated in both languages, and their sample text
  now comes from the same catalog the app uses: written by hand, it had drifted
  (a message without accents, and a missing UPC shown as an error when the
  validation gives it as a warning).
- `build/capturas.py` sometimes ended with `Fatal Python error` even when the
  screenshots came out fine. A server thread was still writing Chrome's closed
  connection while the program shut down. The app's server now stays quiet about
  client disconnects, which are not its error, and the script waits for its
  threads before exiting.

### Changed
- **CI grants write permission only to the step that publishes the
  release.** Before, the eight build jobs had it too, and they install
  packages from PyPI: a compromised one would have received a token able to
  write to the repository. And GitHub actions are pinned by commit SHA instead
  of by a tag, which whoever controls the action can move.
- Dependabot proposes pip and action updates, and a new job runs `pip-audit` on
  everything shipped inside the executables. PyInstaller and pyright are
  pinned, every job has a timeout, and the build's tests run without the
  YouTube key in the environment.
- The yt-dlp floor goes up to 2024.07.01, which leaves out the versions with
  CVE-2024-38519.
- **The YouTube key travels in a header, not in the URL.** No error message
  showed it today, but any that quoted the URL would have carried it along: now
  it is not there. It was checked against the real API that Google accepts it
  the same way and that a bad key still gives the same warning.
- The config folder and file, where the key the user loads lives, are created
  closed from the start. Before, the permission was closed afterwards, and on a
  machine with several users there was a window in which others could read it.
- The key check also goes through the whole git history, in CI: a key that went
  into one commit and out in the next is no longer in any file, but it is still
  in every clone.
- **The local server adds four reinforcements, without touching the three
  defenses.** No other page can put the app in an iframe (`frame-ancestors`,
  `X-Frame-Options`, COOP and CORP). A request the browser marks as made by
  another site is refused even with the token. A request body is only
  interpreted after passing Host, token and origin, and one that cannot be read
  whole closes the connection instead of polluting the next request. And a token
  with odd characters or a path on another drive gives 403 and 404, not an
  internal error with the exception's text.
- **The validation stops promising what it does not look at.** "No errors:
  the catalog has nothing that would cause a rejection" read as "ready to
  load", with unfilled fields, lossy audio and doubtful codes inside. It now
  says "no format errors", makes clear it is not a guarantee, and the report
  always lists what it does not check (text and logos on the cover, what your
  current distributor has on record, each one's rules). It adds warnings for
  medium-confidence ISRCs, reference-only audio, grayscale, palette or
  transparent covers, and the fields no public source has. The READ ME and the
  README say "usually reject" instead of "reject".

## [1.1.0] — 2026-09-22

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
- CI runs the tests on Python 3.13 and 3.14. The binary is built with 3.13 and
  the code is written on 3.14, and nothing covered that gap.
- `BLE` in ruff: every `except Exception` has to be justified. There were
  thirty-four and only thirteen had a note, which silenced nothing anyway because
  the rule was off.
- **macOS gets an `.app` and Linux a `.deb`.** Until now both were published as
  a bare executable, which on macOS means four Terminal commands and on Linux
  shows up in no menu at all. The `.app` is dragged to Applications and lands in
  Launchpad; the `.deb` installs with `apt`, lands in the menu with its icon, and
  uninstalls like any package. Both are still unsigned, which is a different
  thing and costs money.
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
- The version check in `build/build.py` asked for Python 3.9 while the project
  declares 3.13. Building with 3.9 passed the check and failed afterwards, inside
  the package. The floor is now read from `requires-python`, where it was written
  correctly.
- The YouTube Data API error parser caught any exception at all. It now names the
  four that navigating a JSON can raise, so a bug of our own there stops being
  swallowed.
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

[1.1.0]: https://github.com/joacogoliver-debug/catalog-migrator/releases/tag/v1.1.0
[1.0.2]: https://github.com/joacogoliver-debug/catalog-migrator/releases/tag/v1.0.2
[1.0.1]: https://github.com/joacogoliver-debug/catalog-migrator/releases/tag/v1.0.1
[1.0.0]: https://github.com/joacogoliver-debug/catalog-migrator/releases/tag/v1.0.0
