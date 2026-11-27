# -*- coding: utf-8 -*-
"""Qué tan comprobado está cada código: confirmado, inferido o dudoso.

Un ISRC que salió de buscar «título artista» y uno que además figura con ese
mismo código en el tracklist de su release se exportaban igual. Estos tests
fijan la diferencia, y que el ritmo y la memoria de los pedidos a Deezer no
cambien lo que se encuentra.
"""

import threading

from migrador import evidencia as E
from migrador import relevar_core as R
from migrador import validar as V
from migrador.contratos import CruceDeezer, TemaFaltante


def _cruce(discografia) -> CruceDeezer:
    """El cruce con Deezer, con los tracklists que se le pasen."""
    return {"albumes": {}, "verificados": {}, "discografia": discografia}


def _tema(titulo, isrc="", posicion=1) -> TemaFaltante:
    return {
        "titulo": titulo,
        "isrc": isrc,
        "duracion_s": 200,
        "posicion": posicion,
        "disco": 1,
        "artista": "",
        "deezer_id": 0,
    }


# ============================================================
# El nivel del ISRC
# ============================================================


def test_un_isrc_que_esta_en_el_tracklist_de_su_release_esta_confirmado(hacer_track):
    t = hacer_track(track="Uno", isrc="ARAAA2000001")
    t["isrc_como"], t["match"], t["album_deezer_id"] = "busqueda", "alta", 77
    E.clasificar([t], _cruce({77: [_tema("Uno", "ARAAA2000001")]}))
    assert t["isrc_nivel"] == "confirmado"


def test_un_isrc_que_solo_salio_de_la_busqueda_es_inferido(hacer_track):
    """La búsqueda por texto dio «alta», pero el tema no quedó en ningún álbum
    verificado: es el mejor candidato y nada más lo respalda."""
    t = hacer_track(track="Uno (Remix)", isrc="ARAAA2000002")
    t["isrc_como"], t["match"] = "busqueda", "alta"
    E.clasificar([t], {"albumes": {}, "verificados": {}})
    assert t["isrc_nivel"] == "inferido"


def test_si_el_tracklist_dice_otro_codigo_no_esta_confirmado(hacer_track):
    """Ubicado en su álbum, pero el código que trae no es el de ningún tema de
    ese álbum: la búsqueda encontró la grabación en otro release."""
    t = hacer_track(track="Uno", isrc="ARAAA2000001")
    t["isrc_como"], t["match"], t["album_deezer_id"] = "busqueda", "alta", 77
    E.clasificar([t], _cruce({77: [_tema("Uno", "ARZZZ9900009")]}))
    assert t["isrc_nivel"] == "inferido"


def test_una_coincidencia_parecida_es_dudosa(hacer_track):
    t = hacer_track(track="Uno", isrc="ARAAA2000001")
    t["isrc_como"], t["match"] = "busqueda", "media"
    E.clasificar([t], None)
    assert t["isrc_nivel"] == "dudoso"


def test_el_tema_que_vino_de_deezer_lleva_su_propio_codigo(hacer_track):
    t = hacer_track(track="Uno", isrc="ARAAA2000001", upc="0885012345673")
    t["isrc_como"], t["origen"] = "deezer", "deezer"
    E.clasificar([t], None)
    assert t["isrc_nivel"] == "confirmado"
    assert t["upc_como"] == "deezer"


def test_sin_isrc_no_hay_nivel(hacer_track):
    t = hacer_track(track="Uno")
    t["isrc_nivel"] = "inferido"  # de una clasificación anterior
    E.clasificar([t], None)
    assert "isrc_nivel" not in t


def test_clasificar_no_pisa_lo_que_cargo_el_usuario(hacer_track):
    t = hacer_track(track="Uno", isrc="ARAAA2000001")
    t["isrc_nivel"], t["isrc_como"] = "manual", "manual"
    E.clasificar([t], None)
    assert t["isrc_nivel"] == "manual"


def test_el_respaldo_del_archivo_confirma(hacer_track):
    t = hacer_track(track="Uno", isrc="ARAAA2000001")
    t["isrc_como"], t["match"], t["isrc_respaldo"] = "busqueda", "alta", "archivo"
    E.clasificar([t], None)
    assert t["isrc_nivel"] == "confirmado"


# ============================================================
# El nivel del UPC
# ============================================================


def _producto_con(hacer_producto, hacer_track, comos, upc="0885012345673", album=77, codigos=True):
    tracks = []
    for n, como in enumerate(comos, 1):
        t = hacer_track(track=f"Tema {n}", isrc=f"ARAAA20000{n:02d}" if codigos else "", upc=upc)
        t["upc_como"], t["isrc_como"], t["album_deezer_id"] = como, "busqueda", album
        tracks.append(t)
    return hacer_producto(upc=upc, tracks=tracks)


def test_upc_confirmado_por_titulo_y_fecha(hacer_producto, hacer_track):
    p = _producto_con(hacer_producto, hacer_track, ["fecha"])
    assert E.nivel_upc(p) == "confirmado"


def test_upc_de_un_solo_tema_y_solo_por_el_titulo_es_inferido(hacer_producto, hacer_track):
    """Un single del que no se sabe la fecha: que el álbum de Deezer se llame
    igual no alcanza para decir que es ese release y no otro con ese nombre."""
    p = _producto_con(hacer_producto, hacer_track, ["titulo"])
    lista = {77: [_tema("Tema 1", "ARAAA2000001")]}
    assert E.nivel_upc(p, lista) == "inferido"


def test_upc_por_titulo_se_confirma_si_el_album_trae_los_temas_con_sus_isrc(hacer_producto, hacer_track):
    p = _producto_con(hacer_producto, hacer_track, ["titulo", "titulo", "titulo"])
    lista = {77: [_tema(f"Tema {n}", f"ARAAA20000{n:02d}", n) for n in (1, 2, 3)]}
    assert E.nivel_upc(p, lista) == "confirmado"


def test_upc_no_se_confirma_con_codigos_que_salieron_del_mismo_album(hacer_producto, hacer_track):
    """Si el ISRC se tomó del tracklist de ese álbum, que coincida con él no es
    una segunda prueba: es la misma, contada dos veces."""
    p = _producto_con(hacer_producto, hacer_track, ["titulo", "titulo", "titulo"])
    for t in p["tracks"]:
        t["isrc_como"] = "tracklist"
    lista = {77: [_tema(f"Tema {n}", f"ARAAA20000{n:02d}", n) for n in (1, 2, 3)]}
    assert E.nivel_upc(p, lista) == "inferido"


def test_upc_de_una_forma_floja_es_inferido(hacer_producto, hacer_track):
    p = _producto_con(hacer_producto, hacer_track, ["casi", "casi"], codigos=False)
    assert E.nivel_upc(p) == "inferido"


def test_el_release_que_vino_entero_de_deezer_tiene_su_upc(hacer_producto, hacer_track):
    t = hacer_track(track="Uno", isrc="ARAAA2000001", upc="0885012345673")
    t["origen"], t["upc_como"] = "deezer", "deezer"
    assert E.nivel_upc(hacer_producto(upc="0885012345673", tracks=[t])) == "confirmado"


def test_sin_upc_no_hay_nivel(hacer_producto, hacer_track):
    p = hacer_producto(upc="", tracks=[hacer_track(track="Uno")])
    E.marcar_productos([p])
    assert "upc_nivel" not in p


def test_marcar_productos_cuenta_los_isrc_sin_confirmar(hacer_producto, hacer_track):
    a, b, c = (hacer_track(track=x, isrc=f"ARAAA200000{n}") for n, x in enumerate("abc", 1))
    a["isrc_nivel"], b["isrc_nivel"], c["isrc_nivel"] = "confirmado", "inferido", "dudoso"
    p = hacer_producto(tracks=[a, b, c])
    E.marcar_productos([p])
    assert p["isrc_sin_confirmar"] == 2
    assert E.resumen([p])["isrc"] == {"confirmado": 1, "inferido": 1, "dudoso": 1}


# ============================================================
# La validación lo dice
# ============================================================


def test_la_validacion_avisa_los_isrc_inferidos_juntos(hacer_producto, hacer_track):
    ts = [hacer_track(track=f"Remix {n}", isrc=f"ARAAA20000{n:02d}", dur=200) for n in range(1, 4)]
    for t in ts:
        t["isrc_nivel"] = "inferido"
    res = V.validar([hacer_producto(upc="0885012345673", tracks=ts)])
    avisos = [h for h in res["hallazgos"] if h["codigo"] == "isrc_inferido"]
    assert len(avisos) == 1, "un aviso por producto, no uno por tema"
    assert "Remix 1" in avisos[0]["mensaje"] and "Remix 3" in avisos[0]["mensaje"]
    assert res["apto"], "un código inferido es un aviso: no impide entregar"


def test_la_validacion_avisa_el_upc_inferido(hacer_producto, hacer_track):
    p = hacer_producto(upc="0885012345673", tracks=[hacer_track(track="Uno", isrc="ARAAA2000001", dur=200)])
    p["upc_nivel"] = "inferido"
    assert "upc_inferido" in {h["codigo"] for h in V.validar([p])["hallazgos"]}


def test_el_upc_por_tracklist_no_se_avisa_dos_veces(hacer_producto, hacer_track):
    t = hacer_track(track="Uno", isrc="ARAAA2000001", dur=200)
    t["upc_por_tracklist"] = "Disco (2001-01-01)"
    p = hacer_producto(upc="0885012345673", tracks=[t])
    p["upc_nivel"] = "inferido"
    codigos = [h["codigo"] for h in V.validar([p])["hallazgos"]]
    assert "upc_por_tracklist" in codigos and "upc_inferido" not in codigos


def test_la_validacion_dice_entre_que_codigos_no_se_eligio(hacer_producto, hacer_track):
    t = hacer_track(track="Uno", dur=200)
    t["isrc_candidatos"] = [
        {"isrc": "ARAAA2000001", "titulo": "Uno", "duracion_s": 200},
        {"isrc": "ARBBB2100002", "titulo": "Uno", "duracion_s": 201},
    ]
    res = V.validar([hacer_producto(upc="0885012345673", tracks=[t])])
    ambiguos = [h for h in res["hallazgos"] if h["codigo"] == "isrc_ambiguo"]
    assert len(ambiguos) == 1
    assert "ARAAA2000001" in ambiguos[0]["mensaje"] and "ARBBB2100002" in ambiguos[0]["mensaje"]
    assert "isrc_falta" not in {h["codigo"] for h in res["hallazgos"]}


# ============================================================
# El ritmo y la memoria de los pedidos a Deezer
# ============================================================


def test_el_ritmo_no_deja_pasar_mas_de_lo_que_admite_la_ventana():
    """Con un reloj de mentira: los pedidos que no entran en la ventana esperan
    a que venza el más viejo, y ninguno sale antes."""
    reloj = [0.0]
    salidas = []

    def dormir(s):
        reloj[0] += s

    ritmo = R._Ritmo(maximo=5, ventana=5.0)
    for _ in range(12):
        ritmo.esperar(reloj=lambda: reloj[0], dormir=dormir)
        salidas.append(reloj[0])
    assert salidas[:5] == [0.0] * 5, "los que entran en la ventana salen sin esperar"
    for i in range(5, 12):
        assert salidas[i] - salidas[i - 5] >= 5.0, "nunca más de cinco en cinco segundos"


def test_el_ritmo_aguanta_varios_hilos():
    ritmo = R._Ritmo(maximo=1000, ventana=5.0)
    hilos = [threading.Thread(target=lambda: [ritmo.esperar() for _ in range(50)]) for _ in range(8)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    assert len(ritmo._marcas) == 400


def test_dentro_de_una_sesion_no_se_pide_dos_veces_lo_mismo(monkeypatch):
    pedidos = []

    def falso(url, headers=None, retries=3):
        pedidos.append(url)
        return {"id": 1, "title": "Disco"}

    monkeypatch.setattr(R, "_http_json", falso)
    with R.sesion_deezer():
        assert R._deezer_json("album/1") == R._deezer_json("album/1")
    assert len(pedidos) == 1


def test_fuera_de_una_sesion_no_se_guarda_nada(monkeypatch):
    """Dos relevamientos no comparten respuestas: el segundo vuelve a pedir."""
    pedidos = []
    monkeypatch.setattr(
        R, "_http_json", lambda url, headers=None, retries=3: pedidos.append(url) or {"id": 1}
    )
    R._deezer_json("album/1")
    with R.sesion_deezer():
        R._deezer_json("album/1")
    R._deezer_json("album/1")
    assert len(pedidos) == 3


def test_una_falla_no_queda_en_la_memoria(monkeypatch):
    respuestas = [None, {"id": 1}]
    monkeypatch.setattr(R, "_http_json", lambda url, headers=None, retries=3: respuestas.pop(0))
    with R.sesion_deezer():
        assert R._deezer_json("album/1") is None
        assert R._deezer_json("album/1") == {"id": 1}


def test_el_cruce_anota_por_que_camino_llego_cada_codigo(monkeypatch, hacer_track):
    """`isrc_como` y `upc_como` salen del cruce: sin ellos no hay qué clasificar."""
    t = hacer_track(track="Uno", album="Disco", dur=200, released="2020-05-01")
    monkeypatch.setattr(R, "deezer_match", lambda t, artist: ("ARAAA2000001", 77, "alta"))
    monkeypatch.setattr(
        R,
        "deezer_albumes",
        lambda ids: {77: {"id": 77, "upc": "0885012345673", "title": "Disco", "release_date": "2020-05-01"}},
    )
    monkeypatch.setattr(R, "tracklist_deezer", lambda info: [("Uno", 1, 1)])
    R.enrich_with_codes([t], "Artista", log=lambda m: None)
    assert (t["isrc_como"], t["upc_como"]) == ("busqueda", "fecha")
