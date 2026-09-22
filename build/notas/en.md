## Which one to download

**Windows, the recommended one**:
`Migrador-de-Catalogos-windows-completa-instalador.exe`. Double
click, Next, and it lands in the Start menu with its uninstaller. It
does not ask for administrator rights. The installer asks for the
language on its first screen, and the app —including what it
downloads— stays in whichever one you pick.

If you would rather not install anything, the portable one is the `.exe`
without `-instalador`.

**On Linux**, the `.deb` (`migrador-catalogos_...deb`) installs with
`sudo apt install ./file.deb` and lands in the applications menu. The bare
executable is still there, for any other distribution.

**On macOS**, the `...-app.zip` carries a real `.app`: drag it to Applications
and it lands in Launchpad. The first time you have to open it with right click
→ Open.

**On macOS there are two, and they are not interchangeable**: one for
Macs with an Apple chip (`-macos-apple-silicon-`) and one for Intel
Macs (`-macos-intel-`). To find out which one you need:  → "About
This Mac". Downloading the wrong one gets you `bad CPU type in
executable`. There is a step-by-step guide in
[docs/INSTALAR-MAC.en.md](https://github.com/{repo}/blob/main/docs/INSTALAR-MAC.en.md).

| Variant | What it carries |
|---|---|
| **completa** (full) | Everything, plus the audio module with ffmpeg inside and a YouTube key already configured. You open it and it works. |
| **esencial** (essential) | Survey, spreadsheet, validation, ingestion sheet and artwork. Lighter, no ffmpeg and no bundled key. |

To download the audio in FLAC you also need your own paid Tidal
account. The module ships disabled and is optional.

The YouTube key the full variant carries is shared, restricted to
YouTube Data API v3, and **anyone who downloads the binary can
extract it**. If you would rather not depend on that, use the
`esencial` variant or load your own from the app.

The full version includes FFmpeg, third-party software under the
GPLv3 license, distributed unmodified and as a separate program.

### Your system is going to say the program is "unrecognized"

That is expected: the binary is not signed because signing costs
money and this is free. The code is public and the executable is
compiled here in GitHub Actions from that code.

- **Windows**: "More info" → "Run anyway".
- **macOS**: right click → "Open", or Settings → Privacy & Security
  → "Open Anyway".

### Verifying that the binary is the one from this repo

Compare the SHA256 with the published `.sha256`, or use the
attestation:

```
gh attestation verify Migrador-de-Catalogos-windows-completa.exe --repo {repo}
```

### Terms of use

This tool is for catalog administration. It neither endorses nor
enables piracy. The detail is in `TERMS.md`, and the app shows the
terms the first time it opens.
