# -*- coding: utf-8 -*-
"""Test offline de parse_description (sin red, sin pytest).

Corré:  python test_parse_description.py
Sale 0 si todo pasa, 1 si algo falla. No necesita claves ni internet.

Cubre las reglas frágiles del parseo de descripciones auto-generadas de YouTube:
  - línea ℗ con año pero SIN sello  -> captura el año, sello = None (no inventa sello)
  - línea ℗ con año + sello          -> captura ambos
  - single/EP: el 3er bloque es la línea ℗ (o "Released on:") -> NO es un álbum
  - fallback "Released on:" para el año cuando no hay ℗ con año
  - descripción vacía -> dict todo-None
"""
import os
import sys
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))


def _load_core():
    path = os.path.join(HERE, "relevar_core.py")
    spec = importlib.util.spec_from_file_location("relevar_core_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    rc = _load_core()
    parse = rc.parse_description
    fails = []

    def expect(name, got, want):
        if got != want:
            fails.append(f"  [{name}] got {got!r}, want {want!r}")

    # ℗ con año pero sin sello: el año igual se captura; el sello queda None.
    r = parse("Provided to YouTube by DistroKid\n\nMi Cancion · Artista\n\n℗ 2023")
    expect("year_only.release_year", r["release_year"], 2023)
    expect("year_only.label", r["label"], None)

    r = parse("Provided to YouTube by DistroKid\n\nMi Cancion · Artista\n\n℗ 2023 ")
    expect("year_trailing_space.release_year", r["release_year"], 2023)
    expect("year_trailing_space.label", r["label"], None)

    # ℗ con año + sello (caso normal, con bloque de álbum).
    r = parse("Provided to YouTube by DistroKid\n\nMi Cancion · Artista\n\n"
              "Album X\n\n℗ 2023 Sello Indie\n")
    expect("year_label.release_year", r["release_year"], 2023)
    expect("year_label.label", r["label"], "Sello Indie")
    expect("year_label.album", r["album"], "Album X")

    # Single/EP: el 3er bloque es la línea ℗ -> no es álbum.
    r = parse("Provided to YouTube by DistroKid\n\nMi Cancion · Artista\n\n"
              "℗ 2023 Sello Indie\n\nReleased on: 2023-05-01\n")
    expect("single.album", r["album"], None)
    expect("single.release_year", r["release_year"], 2023)
    expect("single.label", r["label"], "Sello Indie")

    r = parse("Provided to YouTube by ONErpm\n\nTema · Artista\n\n℗ 2024 Algun Sello")
    expect("single3.album", r["album"], None)
    expect("single3.release_year", r["release_year"], 2024)

    # 3er bloque es "Released on:" -> tampoco es álbum.
    r = parse("Provided to YouTube by DistroKid\n\nTema · Artista\n\n"
              "Released on: 2022-01-01\n\n℗ 2022")
    expect("releasedon.album", r["album"], None)
    expect("releasedon.release_year", r["release_year"], 2022)

    # Fallback de año por "Released on:" cuando el ℗ no trae año.
    r = parse("Provided to YouTube by DistroKid\n\nTema · Artista\n\nReleased on: 2021-03-03")
    expect("released_fallback.release_year", r["release_year"], 2021)

    # Vacío -> dict todo-None.
    expect("empty", parse(""),
           {"distributor": None, "album": None, "release_year": None, "label": None})

    if fails:
        sys.stdout.write("FAIL:\n" + "\n".join(fails) + "\n")
        return 1
    sys.stdout.write("OK: parse_description (8 grupos de asserts) pasaron.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
