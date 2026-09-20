# Catalog Migrator — product truth

[Español](PRODUCT.md) · **English**

What it is, who it's for, and what has to stay true no matter what happens to the
design. This file decides nothing visual. That lives in `DESIGN.en.md`.

## What it does

It takes the link to an artist's YouTube channel and returns what is needed to
carry that catalog over to another distributor: the **ISRC** and **UPC** codes,
the artwork at the highest available resolution, an **ingestion sheet** in CSV
and a **pre-delivery validation** that separates what is going to be rejected
from what merely deserves a look.

It is a desktop app. It runs entirely on the machine of whoever uses it, raises a
local server on `127.0.0.1`, and has no accounts, no sign-up and no backend of
its own.

## Who it's for

Someone who administers a music catalog: a small label, a manager, a distributor,
or the artist themselves. They know what an ISRC is and why losing one hurts.
This is not a general-audience user, and the domain does not need explaining to
them.

## The real scene of use

One person alone, in front of the computer, doing inventory work they would
normally do in a spreadsheet. It is usually at night, outside the hours when the
"real" work gets done, and the session lasts between twenty minutes and two
hours. They rarely open it for a single thing: when they open it, they migrate a
whole catalog.

Three consequences follow that the design cannot ignore. **Dark by default**,
because that is the light of the scene. **Density before breathing room**,
because whoever is using it is comparing rows, not reading. And **the state has
to be visible at all times**, because the jobs take minutes and the window is
left open while something else gets done.

## The path through

Four steps, and the order is not negotiable, because each one needs the one
before it.

1. **Paste the link** to the channel. Ideally the Topic channel.
2. **Choose products.** This is where most of the time goes. The catalog shows up
   grouped into products (album, EP, single), with what each one is missing
   flagged. It can be filtered by year, by distributor, or searched.
3. **Choose what to download.** Spreadsheet, artwork, audio.
4. **Download** a ZIP with one folder per product, plus the validation report.

## The states that matter

These are not edge cases: they are half the product.

- **A long job in flight.** Surveying takes from 20 seconds to several minutes,
  and building the package with audio can take far longer. There is progress,
  there is a log of what is going on, and it can be cancelled.
- **A missing piece of data.** A product with no UPC, a track with no ISRC, an
  estimated track order. The app has to show it per product and not bury it in a
  summary.
- **The API quota ran out.** It happens, and it has a concrete fix: load your own
  key. The error has to offer that, not merely report the problem.
- **The artist is not in the source.** If Deezer does not have them, there are no
  codes, and that is not a failure of the app. It has to be said in those words.
- **Empty because of a filter.** Too much was filtered out and nothing is left.
- **First time.** Terms of use, and the API key if this copy does not carry one.

## What does not get touched

- **It does not invent metadata.** Whatever does not come from a public source is
  marked `<<COMPLETAR>>`. An empty field is information; one filled in by eye is
  a lie that someone later delivers.
- **What is reported is what was measured, not what was asked for.** Artwork is
  requested at 3000×3000 and the size Apple actually returned is what gets
  reported.
- **Track order is estimated** and that is said on every product where it is.
- **The validation is a help, not a certificate.** It is never presented as a
  guarantee that the distributor will accept the release.
- The audio module is optional, ships turned off, and needs the user's own paid
  account.

## How it talks

The app is in Spanish and in English, and the language is chosen in the installer
or in the header. It is not a partial translation: the interface, the log, the
errors and what gets downloaded (file names, spreadsheet headers, validation
report) all go in the chosen language. The two catalogs live in `i18n.py` and in
`app/web/i18n.js`, one per process, and `test_i18n.py` does not let one grow
without the other.

The Spanish is Rioplatense, voseo, direct. The English goes for the same
register: second person, short sentences, no filler politeness. Errors say what
happened and what to do; they do not apologize.

Things are called what the people who do this work call them: "distribuidora" and
"sello" in Spanish, "distributor" and "label" in English, and never "vendor". The
terms of the trade that do not get translated — ISRC, UPC, DDEX, master, lossless
— are left as they are in both languages.

## Technical constraints

JavaScript with no frameworks and no build step, and CSS with no preprocessor.
The app is packaged as a single executable, so it cannot depend on any download
at runtime: the typefaces travel inside and the page declares a CSP that does not
let it request anything outside. Any design decision that needs a CDN is ruled
out from the start.
