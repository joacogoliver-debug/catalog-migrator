# Installing the Migrator on a Mac

[Español](INSTALAR-MAC.md) · **English**

Five minutes. You have to use the Terminal for a moment, but it is copy and paste.

---

## 1. Check which Mac you have

 menu (top left) → **About This Mac**.

- If it says **Apple M1 / M2 / M3 / M4 chip** → you have an **Apple Silicon** Mac.
- If it says **Intel processor** → you have an **Intel** Mac.

This matters: they are two different files and **the wrong one will not run**.

## 2. Download the file

Go to **[Releases](https://github.com/joacogoliver-debug/catalog-migrator/releases)**
and, in the topmost version, open **Assets**. Download:

| Your Mac | The file |
|---|---|
| Apple Silicon | `Migrador-de-Catalogos-macos-apple-silicon-completa` |
| Intel | `Migrador-de-Catalogos-macos-intel-completa` |

It is a large file (around 60 MB) with no extension. It lands in **Downloads**.

> `completa` carries everything and comes with the YouTube key already
> configured: you open it and it works. `esencial` is lighter, but asks for your
> own key.

## 3. Open it from the Terminal

Open Terminal (Cmd+Space, type `Terminal`, Enter) and paste **these three lines,
one at a time**. On an Intel Mac, change `apple-silicon` to `intel` in all three.

```bash
cd ~/Downloads
chmod +x Migrador-de-Catalogos-macos-apple-silicon-completa
xattr -c Migrador-de-Catalogos-macos-apple-silicon-completa
```

And now, to open the app:

```bash
./Migrador-de-Catalogos-macos-apple-silicon-completa
```

The app opens **in its own window**, like any other program. **Leave the
Terminal open**: closing it closes the app.

From now on, opening it again only takes the last two lines (`cd ~/Downloads` and
`./Migrador...`). The `chmod` and `xattr` are a one-time thing.

---

## If something goes wrong

**`bad CPU type in executable`**
You downloaded the file for the other architecture. Go back to step 1.

**"cannot be opened because the developer cannot be verified"**
You skipped the `xattr -c` line. Run it and try again.

If it insists: **System Settings → Privacy & Security**, scroll to the bottom and
press **"Open Anyway"**. It only shows up after the first blocked attempt.

**`No such file or directory`**
The file is not in Downloads, or the name is not exactly that one. In the
Terminal type `ls ~/Downloads/Migrador*` and see what it is really called.

**`Permission denied`**
You skipped the `chmod +x` line.

**It opened in the browser instead of its own window**
It works the same. It means your Mac could not open the native window and the
app fell back to its plan B, which is opening in the browser.

**Nothing happens, or you want to know what it found**
Run this and send the result to Joaco:

```bash
./Migrador-de-Catalogos-macos-apple-silicon-completa --diagnostico
```

It writes a report of what the app can do on your machine and saves it to
`~/.migrador-catalogos/diagnostico.txt`.

---

## Why your Mac distrusts it

The program is **not signed** with an Apple certificate. Signing costs a yearly
fee and the tool is free. That does not make it unsafe: the code is public and
the executable is compiled on GitHub, in plain sight, from that code.

If you would rather not deal with any of this, it can be run from source with two
commands: see the [README](../README.en.md#running-it-from-source).
