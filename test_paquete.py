# -*- coding: utf-8 -*-
"""Test offline del empaquetado del entregable (sin red, sin pytest).

Corré:  python test_paquete.py
Sale 0 si todo pasa, 1 si algo falla. No necesita claves ni internet.

Cubre lo que sostiene la confianza en el entregable:
  - la estructura del ZIP es una carpeta por producto
  - las planillas y el reporte están en la raíz
  - los audios lossy quedan marcados en el nombre (la marca sigue al idioma)
  - los audios lossless NO llevan esa marca
  - el reporte lista los pendientes reales (sin UPC, sin portada, sin audio)
  - el reporte avisa fuerte cuando no hubo cuenta de Tidal
  - se respetan los checkboxes (no incluir audio / portadas / planilla)
  - el paquete entero sale en el idioma elegido, nombres de archivo incluidos
"""
import os
import sys
import shutil
import tempfile
import zipfile
import importlib.util

# El idioma se fija antes de importar nada: si no, el paquete sale en el que
# tenga la máquina que corre el test y las comparaciones dependen del locale.
os.environ["MIGRADOR_IDIOMA"] = "es"

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# i18n va con un import normal y NO con _load: _load registra un módulo nuevo en
# sys.modules, y entonces el `from i18n import T` de paquete quedaba atado a otra
# instancia. Cambiarle el idioma a una no se veía en la otra.
import i18n                                                        # noqa: E402


def _load(nombre):
    path = os.path.join(HERE, f"{nombre}.py")
    spec = importlib.util.spec_from_file_location(nombre, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nombre] = mod          # para que `from audio import ...` resuelva
    spec.loader.exec_module(mod)
    return mod


def _logs_son_cp1252(carpeta):
    """True si ninguna línea que llama a log(...) trae caracteres que la consola
    de Windows (cp1252) no pueda imprimir.

    Mira el código fuente en vez de ejecutar los logs porque las rutas que los
    emiten necesitan red y credenciales.
    """
    import glob
    ok = True
    for ruta in glob.glob(os.path.join(carpeta, "*.py")):
        if os.path.basename(ruta).startswith("test_"):
            continue
        with open(ruta, encoding="utf-8") as f:
            for i, linea in enumerate(f, 1):
                if "log(" not in linea and "print(" not in linea:
                    continue
                for ch in linea:
                    if ord(ch) > 127:
                        try:
                            ch.encode("cp1252")
                        except UnicodeEncodeError:
                            print(f"    log no imprimible: {os.path.basename(ruta)}:{i} {ch!r}")
                            ok = False
    return ok


def main():
    _load("audio")                      # paquete.py importa de audio
    pq = _load("paquete")
    pr = _load("productos")
    fails = []

    def expect(name, got, want):
        if got != want:
            fails.append(f"  [{name}] got {got!r}, want {want!r}")

    def check(name, cond, detalle=""):
        if not cond:
            fails.append(f"  [{name}] falló {detalle}")

    tmp = tempfile.mkdtemp(prefix="test_paquete_")
    try:
        # Audios falsos en disco: uno "lossless", uno "lossy".
        flac = os.path.join(tmp, "a.flac")
        m4a = os.path.join(tmp, "b.m4a")
        with open(flac, "wb") as f:
            f.write(b"FLAC-falso" * 100)
        with open(m4a, "wb") as f:
            f.write(b"AAC-falso" * 100)

        productos = [
            {
                "product_id": "p001", "title": "Album Bueno", "kind": "album",
                "release_year": 2020, "upc": "111", "label": "Sello",
                "distributor": "ONErpm", "track_count": 1,
                "total_views": 10, "order_unconfirmed": False,
                "folder": "2020 - Album Bueno [111]",
                "cover_bytes": b"\xff\xd8jpeg-falso", "cover_status": "ok 3000x3000",
                "tracks": [{
                    "track": "Tema Lossless", "track_number": 1, "isrc": "ARABC2000001",
                    "duration_s": 200, "views": 10, "url": "https://youtu.be/x",
                    "video_id": "x", "audio_path": flac, "audio_format": ".flac",
                    "audio_label": pq.ETIQUETA_LOSSLESS,
                }],
            },
            {
                "product_id": "p002", "title": "Single Flojo", "kind": "single",
                "release_year": 2021, "upc": "", "label": "", "distributor": "DistroKid",
                "track_count": 2, "total_views": 5,
                "order_unconfirmed": True, "folder": "2021 - Single Flojo",
                "cover_bytes": None, "cover_status": "sin match en iTunes",
                "tracks": [
                    {"track": "Tema Lossy", "track_number": 1, "isrc": "", "duration_s": 180,
                     "views": 5, "url": "", "video_id": "y", "audio_path": m4a,
                     "audio_format": ".m4a", "audio_label": "lossy"},
                    {"track": "Tema Sin Audio", "track_number": 2, "isrc": "", "duration_s": 90,
                     "views": 0, "url": "", "video_id": "z", "audio_path": None,
                     "audio_format": None, "audio_label": None},
                ],
            },
        ]

        # --- ZIP completo -------------------------------------------------
        zip_path = os.path.join(tmp, "salida.zip")
        ruta, tam = pq.build_zip(productos, "Artista Test", zip_path,
                                 con_tidal=True, log=lambda *_: None)
        check("zip.existe", os.path.exists(ruta))
        check("zip.pesa", tam > 0, f"tam={tam}")

        with zipfile.ZipFile(ruta) as z:
            nombres = z.namelist()
            marca = i18n.T("paq.tag_lossy")
            raiz = nombres[0].split("/")[0]

            # Archivos de raíz.
            check("raiz.leeme", f"{raiz}/_LEEME.txt" in nombres)
            check("raiz.reporte", f"{raiz}/_Reporte de migracion.txt" in nombres)
            check("raiz.maestra", f"{raiz}/_Catalogo completo.xlsx" in nombres)

            # Una carpeta por producto, con su planilla.
            check("prod1.datos", f"{raiz}/2020 - Album Bueno [111]/datos.xlsx" in nombres)
            check("prod2.datos", f"{raiz}/2021 - Single Flojo/datos.xlsx" in nombres)

            # Portada sólo donde había.
            check("prod1.portada", f"{raiz}/2020 - Album Bueno [111]/portada.jpg" in nombres)
            check("prod2.sin_portada",
                  f"{raiz}/2021 - Single Flojo/portada.jpg" not in nombres)

            # El lossless NO lleva marca; el lossy SÍ.
            check("audio.lossless_sin_marca",
                  f"{raiz}/2020 - Album Bueno [111]/01 - Tema Lossless.flac" in nombres,
                  f"nombres={[n for n in nombres if 'Lossless' in n]}")
            check("audio.lossy_marcado",
                  f"{raiz}/2021 - Single Flojo/01 - Tema Lossy {marca}.m4a" in nombres,
                  f"nombres={[n for n in nombres if 'Lossy' in n]}")
            # El track sin audio no genera archivo.
            check("audio.sin_audio_no_aparece",
                  not any("Tema Sin Audio" in n for n in nombres))

            crudo = z.read(f"{raiz}/_Reporte de migracion.txt")
            # Con BOM, para que Windows muestre bien los acentos.
            check("reporte.bom", crudo.startswith(b"\xef\xbb\xbf"))
            reporte = crudo.decode("utf-8-sig")
            # Los acentos tienen que sobrevivir el ida y vuelta.
            check("reporte.acentos_ok", "MIGRACIÓN" in reporte, reporte[:60])

        # --- Contenido del reporte ---------------------------------------
        # Se compara rótulo y valor sin fijar los espacios del medio: el reporte
        # alinea con ljust y el ancho depende del largo de la palabra, que
        # cambia con el idioma. Fijar la separación exacta hacía que el test
        # dependiera de una decisión de maquetado.
        def linea(rotulo, valor, texto=reporte):
            return any(l.strip().startswith(rotulo) and l.rstrip().endswith(f": {valor}")
                       for l in texto.splitlines())

        check("reporte.aptos", linea("Aptos para entrega (FLAC lossless)", 1), reporte[:400])
        check("reporte.referencia", linea("Sólo referencia (lossy)", 1))
        check("reporte.sin_audio", linea("Sin audio", 1))
        check("reporte.pendiente_upc", "sin UPC" in reporte)
        check("reporte.pendiente_portada", "sin portada" in reporte)
        check("reporte.pendiente_orden", "orden de tracks sin confirmar" in reporte)
        check("reporte.pendiente_isrc", "tracks sin ISRC" in reporte)

        # --- Aviso fuerte cuando no hubo Tidal ---------------------------
        rep_sin_tidal = pq.reporte_texto(productos, "Artista Test", con_tidal=False)
        check("reporte.aviso_sin_tidal",
              "NO hay audio apto" in rep_sin_tidal, rep_sin_tidal[:300])
        # Con Tidal conectado pero con lossy, avisa lo otro.
        check("reporte.aviso_sin_master",
              "no tiene máster" in reporte, reporte[:600])

        # --- Respetar los checkboxes -------------------------------------
        z2 = os.path.join(tmp, "solo_planilla.zip")
        pq.build_zip(productos, "Artista Test", z2, incluir_audio=False,
                     incluir_portadas=False, log=lambda *_: None)
        with zipfile.ZipFile(z2) as z:
            n2 = z.namelist()
        check("checkbox.sin_audio", not any(x.endswith((".flac", ".m4a")) for x in n2))
        check("checkbox.sin_portadas", not any(x.endswith("portada.jpg") for x in n2))
        check("checkbox.con_planilla", any(x.endswith("_Catalogo completo.xlsx") for x in n2))

        z3 = os.path.join(tmp, "solo_audio.zip")
        pq.build_zip(productos, "Artista Test", z3, incluir_planilla=False,
                     log=lambda *_: None)
        with zipfile.ZipFile(z3) as z:
            n3 = z.namelist()
        check("checkbox.sin_planilla", not any(x.endswith(".xlsx") for x in n3))
        # El reporte va siempre: es lo que explica qué falta.
        check("checkbox.reporte_siempre", any("Reporte de migracion" in x for x in n3))

        # --- Nombres seguros ---------------------------------------------
        expect("slug.prohibidos", pq._slug_archivo('Tema/Con:Barras*?'), "TemaConBarras")
        expect("slug.punto_final", pq._slug_archivo("Tema..."), "Tema")
        expect("slug.vacio", pq._slug_archivo(""), "sin-titulo")

        # --- Fuente corta -------------------------------------------------
        expect("fuente.lossless",
               pq._fuente_corta({"audio_path": "x", "audio_format": ".flac"}),
               "LOSSLESS (flac)")
        expect("fuente.lossy",
               pq._fuente_corta({"audio_path": "x", "audio_format": ".m4a"}),
               "LOSSY (m4a)")
        expect("fuente.sin", pq._fuente_corta({}), "sin audio")

        # --- El paquete entero sigue al idioma ----------------------------
        # Es lo que se promete: quien elige inglés abre el ZIP en inglés,
        # nombres de archivo incluidos. Al terminar se vuelve a español para
        # no contaminar lo que venga despues.
        try:
            i18n.poner_idioma("en")
            z4 = os.path.join(tmp, "en.zip")
            pq.build_zip(productos, "Artista Test", z4, con_tidal=True, log=lambda *_: None)
            with zipfile.ZipFile(z4) as z:
                n4 = z.namelist()
                raiz_en = n4[0].split("/")[0]
                rep_en = z.read(f"{raiz_en}/_Migration report.txt").decode("utf-8-sig")
            check("idioma.carpeta_raiz", raiz_en.endswith(f"Migration {pq.date.today().isoformat()}"),
                  raiz_en)
            for esperado in ("_READ ME.txt", "_Migration report.txt",
                             "_Pre-delivery validation.txt", "_Full catalog.xlsx",
                             "_Ingestion sheet.csv"):
                check(f"idioma.archivo {esperado}",
                      any(x.endswith(esperado) for x in n4),
                      f"nombres={[x for x in n4 if '/' in x and x.count('/') == 1]}")
            check("idioma.datos_xlsx", any(x.endswith("/data.xlsx") for x in n4))
            check("idioma.portada", any(x.endswith("/cover.jpg") for x in n4))
            check("idioma.reporte_en", "MIGRATION REPORT" in rep_en, rep_en[:80])
            check("idioma.reporte_sin_espanol", "PENDIENTES" not in rep_en)
            # El LEEME se arma con los nombres de archivo adentro: tienen que
            # ser los mismos que los del ZIP, o manda a buscar lo que no existe.
            with zipfile.ZipFile(z4) as z:
                leeme_en = z.read(f"{raiz_en}/_READ ME.txt").decode("utf-8-sig")
            check("idioma.leeme_nombra_bien", "_Pre-delivery validation.txt" in leeme_en,
                  leeme_en[:300])
            # Las columnas de la hoja de ingesta NO se traducen: son los nombres
            # de campo que espera la distribuidora.
            with zipfile.ZipFile(z4) as z:
                ing_en = z.read(f"{raiz_en}/_Ingestion sheet.csv").decode("utf-8-sig")
            check("idioma.ingesta_en_ingles_siempre",
                  ing_en.splitlines()[0].startswith("UPC,Release Title,Release Artist"),
                  ing_en.splitlines()[0][:80])
        finally:
            i18n.poner_idioma("es")

        # --- Logs imprimibles en consola de Windows ------------------------
        # Los mensajes de log van a stdout, y la consola de Windows usa cp1252:
        # un caracter fuera de ese set (p. ej. una flecha ->) tira
        # UnicodeEncodeError y corta la migración a mitad de camino.
        check("logs.cp1252", _logs_son_cp1252(HERE), "hay f-strings de log con caracteres no-cp1252")

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if fails:
        print("FALLARON:")
        print("\n".join(fails))
        return 1
    print("OK - empaquetado del entregable")
    return 0


if __name__ == "__main__":
    sys.exit(main())
