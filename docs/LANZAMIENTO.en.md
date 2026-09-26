# Launch material

[Español](LANZAMIENTO.md)

Everything needed to present the app outside the repository, ready to use.
**None of this is published**: uploading the image, changing the description,
turning on the page and posting are decisions for whoever manages the
repository. The texts carry no usage figures or testimonials, because none has
been measured.

## What is left to do, and where

| What | Where | File |
|---|---|---|
| Upload the social image | GitHub → Settings → General → Social preview | [`redes/social-preview.png`](redes/social-preview.png), 1280×640. Regenerated with `python build/imagen_redes.py` |
| Change the repo description | GitHub → the "About" gear | The one below |
| Change the topics | GitHub → the "About" gear | The list below |
| Turn on the page | GitHub → Settings → Pages → branch `main`, folder `/docs` | [`index.html`](index.html) and [`en.html`](en.html) |
| Set the page as the repo's website | The "About" gear → Website | `https://joacogoliver-debug.github.io/catalog-migrator/` |

## Repository description

A single one, in both languages, because GitHub search does not split by
language:

> Cambiá de distribuidora sin perder los códigos: ISRC, UPC, portadas, hoja de
> ingesta y validación desde el canal de YouTube del artista. · Switch music
> distributors without losing your catalog's ISRCs and UPCs.

## Topics

`music-distribution` · `music-catalog` · `catalog-migration` · `isrc` · `upc` ·
`metadata` · `youtube-api` · `deezer-api` · `music-industry` · `desktop-app` ·
`python`

Bare `distribution`, today's topic, gets confused with Linux and package
distributions.

## LinkedIn

> Switching distributors is easy until you realize the catalog has to arrive
> with the same ISRCs and UPCs, because a new code is a new release that starts
> without its plays or its playlists.
>
> I made a free, open-source app for that: paste the artist's YouTube channel
> and it builds the package for the new distributor, with the codes that can be
> recovered, high-resolution artwork, an ingestion sheet and a check of what
> distributors usually reject. It runs on your computer, with no accounts.
>
> It is for small labels, managers and artists who manage their own catalog.
> Windows, macOS and Linux: https://github.com/joacogoliver-debug/catalog-migrator

## Forums and artist communities

> **A free tool to move a catalog to another distributor without losing the
> codes**
>
> If you are about to switch distributors, what hurts most to lose are the
> ISRCs and UPCs: with new codes, every release starts from zero. I made an
> open-source app that, from the artist's YouTube Topic channel, recovers the
> codes Deezer has, fetches the artwork from Apple Music and builds an ingestion
> sheet, with a pre-delivery check. It does not connect to any distributor or
> ask for accounts: you upload the files yourself.
>
> What it does not do, so nobody is surprised: it does not produce DDEX, it does
> not make up what is not published (genre, territories, explicit are left to
> fill in) and audio is a separate module, switched off, that uses your own
> account.
>
> https://github.com/joacogoliver-debug/catalog-migrator

## Software directories

For the ones that ask for a short and a long description:

- **Short:** Builds the package to move a music catalog to another distributor
  without losing ISRCs or UPCs.
- **Long:** The first paragraph of the [README](../README.en.md), which is the
  promise, plus "Who it is for".
