# Terms of use

**Catalog Migrator**, version 1.0 of these terms, in force since 14 September
2026.

This is the English translation of [TERMINOS.md](TERMINOS.md), which is the
canonical copy. Where the two differ, the Spanish text prevails.

The same text appears inside the application, which shows it the first time it
is opened and keeps it available from the footer of the window.

---

## 1. What this tool is

Catalog Migrator is a free, open-source program for **managing music
catalogs**. It surveys an artist's distributed catalog, recovers their ISRC and
UPC codes, gathers the cover art and builds the ingestion sheet a new
distributor asks for. That is its purpose and no other.

The tool queries public third-party APIs. It does not host, does not store and
does not redistribute the content of any catalog.

## 2. Who may use it, and what for

It is meant for rights holders, labels, distributors, managers and artists
working on **their own material, or material they administer with the owner's
permission**.

By using it you state that:

- you hold the rights or the permission you need over the content you process;
- you will honour the terms of service of the platforms the tool queries, among
  them YouTube, Deezer, Apple and Tidal;
- you are responsible for the API keys and the accounts you connect, and for
  their use staying within each provider's limits and conditions.

## 3. What is not allowed

This tool **neither endorses nor enables piracy**. What follows is expressly
outside its purpose and this licence of use.

- Downloading, copying or redistributing material you hold no rights to.
- Using the audio module to obtain someone else's recordings, or to get around
  technical protection measures.
- Reselling, redistributing or publishing the content obtained without the
  owner's permission.
- Sharing third-party account credentials, or using a streaming account outside
  the terms of the service that provides it.
- Getting around the restrictions of the APIs the tool queries, or automating
  requests beyond the limits those APIs set.
- Presenting the tool's output as an official certification of ownership or of
  rights.

### About the audio module

The audio module is **optional, ships turned off** and requires the user to
connect their own paid account. It exists so a catalog owner can recover their
own masters when the original file cannot be found. It does not replace the
master delivered by the artist or the label, and the documentation and the
reports the tool produces say so.

Using it on someone else's material is a misuse of the tool and a breach of
these terms, as well as, in all likelihood, of the terms of service of wherever
the audio is obtained.

## 4. Your data

The application runs entirely on your computer.

- **There are no accounts, no sign-up and no server of ours.** The app starts a
  local server on `127.0.0.1` that is not exposed to the network.
- **The API key is stored in your home folder**
  (`~/.migrador-catalogos/config.json`) and is not sent anywhere other than
  Google.
- **The surveyed catalog lives in memory** while the app is open and is
  discarded when it closes.
- Deezer, Apple and MusicBrainz are queried with public catalog data, such as
  the artist name, the title and the length.
- If you connect Tidal, access is by device code: your password never passes
  through the application. The token lives only for the session and is deleted
  when it closes.

No telemetry of any kind is collected.

## 5. No warranty

The software is provided **as is, without warranty of any kind**, express or
implied, including without limitation the warranties of merchantability,
fitness for a particular purpose and non-infringement.

The data comes from third-party public sources and may be incomplete or out of
date. **Pre-delivery validation is a help, not a certificate**, and it does not
replace the distributor's review or the judgement of whoever delivers the
material. Several fields are explicitly marked as estimated or as pending
completion, and they should be treated that way.

In no event will the author be liable for direct, indirect, incidental, special
or consequential damages arising from the use of or the inability to use the
tool, nor for decisions made from the data it produces, nor for the use each
person makes of the material they process. **Responsibility over the content
rests entirely with whoever uses it.**

## 6. Licence of the code, and third-party marks

The code is distributed under the **MIT licence**, whose full text is in the
[LICENSE](LICENSE) file. These terms describe the intended use of the tool and
do not restrict the rights the MIT licence grants over the code.

Third-party trademarks, names and services mentioned belong to their owners.
This tool is **not affiliated with, sponsored by or endorsed by** YouTube,
Google, Deezer, Apple, Tidal, MusicBrainz or any distributor.

The full build includes **FFmpeg**, third-party software under the GPLv3
licence, distributed unmodified and invoked as a separate program. The Public
Sans and DM Mono typefaces are distributed under SIL Open Font License 1.1. The
texts of those licences travel with the program, in the `licencias` folder.

## 7. Changes

These terms may be updated in later versions. The version in force is the one
shipped with the copy you are using, and it is published in the repository
alongside the code. If they change substantially, the application shows them
once again.

## 8. Contact

Questions and reports go through the
[repository Issues](https://github.com/joacogoliver-debug/catalog-migrator/issues).

Author: [Joaquín García Oliver](https://www.linkedin.com/in/joaquingarciaoliver/).
