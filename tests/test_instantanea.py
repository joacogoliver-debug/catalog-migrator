# -*- coding: utf-8 -*-
"""El relevamiento guardado: que vuelva igual, que un archivo ajeno no pueda
hacer daño, y que la comparación diga la verdad sobre una migración."""

import json
import zipfile

import pytest

from migrador import ediciones as ED
from migrador import instantanea as INS
from migrador import paquete as PQ

UPC_A = "0885012345673"
UPC_B = "0885012345680"


def _disco(hacer_producto, hacer_track, dist="DistroKid", upc=UPC_A, isrcs=("ARAAA2000001", "ARAAA2000002")):
    ts = []
    for n, isrc in enumerate(isrcs, 1):
        t = hacer_track(track=f"Tema {n}", album="Disco", isrc=isrc, upc=upc, dur=200 + n, dist=dist)
        t["isrc_nivel"], t["isrc_como"], t["track_number"] = "confirmado", "busqueda", n
        ts.append(t)
    p = hacer_producto(title="Disco", upc=upc, tracks=ts)
    p["distributor"], p["upc_nivel"] = dist, "confirmado"
    return p


# ============================================================
# Ida y vuelta
# ============================================================


def test_lo_que_se_guarda_vuelve_igual(hacer_producto, hacer_track):
    p = _disco(hacer_producto, hacer_track)
    p["tracks"][0]["artists"] = ["Artista", "Invitada"]
    p["tracks"][0]["credits"]["composers"] = ["Nombre Legal"]
    ED.poner_datos([p], ["p001"], {"genre": "Cuarteto"})
    ED.poner_isrc([p], "p001", 1, "ARBBB2100009")
    productos, artista, info = INS.abrir(
        INS.volcar([p], "Artista Test", {"canal": "Artista - Topic", "via": "busqueda", "temas": 2})
    )
    q = productos[0]
    assert (artista, info["canal"], info["temas"]) == ("Artista Test", "Artista - Topic", 2)
    assert (q["title"], q["upc"], q.get("upc_nivel"), q["distributor"]) == (
        "Disco",
        UPC_A,
        "confirmado",
        "DistroKid",
    )
    assert q.get("datos") == {"genre": "Cuarteto"}
    assert [t["isrc"] for t in q["tracks"]] == ["ARAAA2000001", "ARBBB2100009"]
    assert q["tracks"][1].get("isrc_nivel") == "manual"
    assert (q["tracks"][1].get("isrc_previo") or {})["isrc"] == "ARAAA2000002", "se puede seguir deshaciendo"
    assert q["tracks"][0]["artists"] == ["Artista", "Invitada"]
    assert q["tracks"][0]["credits"]["composers"] == ["Nombre Legal"]
    assert q["folder"].endswith(f"[{UPC_A}]")


def test_el_paquete_trae_el_relevamiento_y_se_puede_reabrir(hacer_producto, hacer_track, tmp_path):
    p = _disco(hacer_producto, hacer_track)
    ruta = str(tmp_path / "paquete.zip")
    PQ.build_zip([p], "Artista Test", ruta, log=lambda m: None)
    with zipfile.ZipFile(ruta) as z:
        nombre = next(n for n in z.namelist() if n.endswith(PQ.nombres_archivos()["instantanea"]))
        suelto = z.read(nombre)
    # Con el archivo suelto, y con el ZIP entero.
    for datos in (suelto, open(ruta, "rb").read()):
        productos, artista, _ = INS.abrir(datos)
        assert artista == "Artista Test" and [t["track"] for t in productos[0]["tracks"]] == [
            "Tema 1",
            "Tema 2",
        ]


def test_no_se_guardan_portadas_ni_rutas_de_audio(hacer_producto, hacer_track):
    p = _disco(hacer_producto, hacer_track)
    p["cover_bytes"] = b"\xff\xd8" + b"x" * 5000
    p["tracks"][0]["audio_path"] = r"C:\Users\alguien\tmp\tidal_1.flac"
    crudo = INS.volcar([p], "Artista").decode("utf-8")
    assert "audio_path" not in crudo and "cover_bytes" not in crudo and "alguien" not in crudo


# ============================================================
# Un archivo ajeno
# ============================================================


@pytest.mark.parametrize(
    "datos",
    [
        b"",
        b"no es json",
        b"[1, 2, 3]",
        b'{"formato": "otra-cosa", "version": 1, "productos": [{}]}',
        b'{"formato": "migrador-relevamiento", "version": 1, "productos": []}',
        b'{"formato": "migrador-relevamiento", "version": 1, "productos": "x"}',
        b'{"formato": "migrador-relevamiento", "version": 1, "productos": [{"title": "Sin temas"}]}',
        b"PK\x03\x04roto",
        # Cien mil corchetes abiertos: el parser no puede caerse por anidarlos.
        b"[" * 100000,
    ],
    ids=[
        "vacio",
        "texto",
        "lista",
        "otro-formato",
        "sin-productos",
        "productos-texto",
        "sin-temas",
        "zip-roto",
        "anidado",
    ],
)
def test_un_archivo_que_no_es_un_relevamiento_se_rechaza(datos):
    with pytest.raises(INS.InstantaneaInvalida):
        INS.abrir(datos)


def test_un_relevamiento_de_una_version_mas_nueva_se_dice():
    datos = json.dumps(
        {"formato": INS.FORMATO, "version": INS.VERSION_FORMATO + 1, "productos": [{}]}
    ).encode()
    with pytest.raises(INS.InstantaneaInvalida):
        INS.abrir(datos)


def test_un_archivo_enorme_se_rechaza_sin_parsearlo():
    with pytest.raises(INS.InstantaneaInvalida):
        INS.abrir(b" " * (INS.MAX_BYTES + 1))


def test_lo_que_trae_un_archivo_ajeno_no_pasa_tal_cual():
    """Claves desconocidas, tipos equivocados, una carpeta que sale de la raíz,
    un enlace a cualquier lado, un campo que no se carga por la app: nada de
    eso llega al catálogo."""
    hostil = {
        "formato": INS.FORMATO,
        "version": 1,
        "artista": "Artista",
        "productos": [
            {
                "title": "Disco",
                "kind": "cualquiera",
                "folder": "../../afuera",
                "upc": "../../evil",
                "release_year": "dos mil",
                "cover_bytes": "AAAA",
                "datos": {"genre": "Rock", "title": "Otro"},
                "tracks": [
                    {
                        "track": "Uno",
                        "duration_s": "200",
                        "views": -5,
                        "url": "javascript:alert(1)",
                        "audio_path": "C:/Windows/system32/x",
                        "artists": ["A", 7, {"x": 1}],
                        "credits": "no es un objeto",
                        "inventada": True,
                    },
                    "esto no es un tema",
                ],
            }
        ],
    }
    productos, _, _ = INS.abrir(json.dumps(hostil).encode())
    p, t = productos[0], productos[0]["tracks"][0]
    assert p["kind"] == "single" and p["release_year"] == ""
    assert ".." not in p["folder"] and "/" not in p["folder"] and "\\" not in p["folder"]
    assert "cover_bytes" not in p and p.get("datos") == {"genre": "Rock"}
    assert (t["duration_s"], t["views"], t["url"]) == (0, 0, "")
    assert "audio_path" not in t and "inventada" not in t
    assert t["artists"] == ["A"] and t["credits"]["composers"] == []
    assert len(productos[0]["tracks"]) == 1
    # Y con eso se puede armar la hoja de ingesta sin que nada se rompa.
    assert "Uno" in PQ.hoja_ingesta_csv(productos, "Artista", False, False)


# ============================================================
# Comparar: ¿salió bien la migración?
# ============================================================


def _estado(antes, ahora):
    return INS.comparar([antes], ahora)["releases"][0]


def test_migrado_con_los_mismos_codigos(hacer_producto, hacer_track):
    antes = _disco(hacer_producto, hacer_track, dist="DistroKid")
    r = _estado(antes, [_disco(hacer_producto, hacer_track, dist="Mojo")])
    assert (r["estado"], r["distribuidoras_ahora"], r["isrc_cambiados"]) == ("migrado", ["Mojo"], [])


def test_todavia_en_la_distribuidora_de_antes(hacer_producto, hacer_track):
    antes = _disco(hacer_producto, hacer_track)
    assert _estado(antes, [_disco(hacer_producto, hacer_track)])["estado"] == "igual"


def test_en_las_dos_a_la_vez_falta_la_baja(hacer_producto, hacer_track):
    antes = _disco(hacer_producto, hacer_track, dist="DistroKid")
    ahora = [
        _disco(hacer_producto, hacer_track, dist="DistroKid"),
        _disco(hacer_producto, hacer_track, dist="Mojo"),
    ]
    assert _estado(antes, ahora)["estado"] == "en_las_dos"


def test_un_isrc_distinto_en_la_entrega_nueva_se_dice_cual(hacer_producto, hacer_track):
    """Lo que la migración tenía que evitar: el tema se entregó con un código
    nuevo. Se encuentra por el título y la duración, y se muestra el cambio."""
    antes = _disco(hacer_producto, hacer_track, dist="DistroKid")
    nuevo = _disco(hacer_producto, hacer_track, dist="Mojo", isrcs=("ARAAA2000001", "ARNEW2600777"))
    r = _estado(antes, [nuevo])
    assert r["estado"] == "codigos_cambiados"
    assert r["isrc_cambiados"] == [{"tema": "Tema 2", "antes": "ARAAA2000002", "ahora": "ARNEW2600777"}]


def test_un_upc_distinto_en_la_entrega_nueva(hacer_producto, hacer_track):
    antes = _disco(hacer_producto, hacer_track, dist="DistroKid", upc=UPC_A)
    r = _estado(antes, [_disco(hacer_producto, hacer_track, dist="Mojo", upc=UPC_B)])
    assert (r["estado"], r["upc_antes"], r["upc_ahora"]) == ("codigos_cambiados", UPC_A, UPC_B)


def test_el_upc_de_doce_y_el_de_trece_no_son_un_cambio(hacer_producto, hacer_track):
    antes = _disco(hacer_producto, hacer_track, dist="DistroKid", upc=UPC_A)
    r = _estado(antes, [_disco(hacer_producto, hacer_track, dist="Mojo", upc=UPC_A.lstrip("0"))])
    assert r["estado"] == "migrado"


def test_un_release_que_ya_no_aparece(hacer_producto, hacer_track):
    antes = _disco(hacer_producto, hacer_track)
    otro = hacer_producto(
        title="Otra Cosa", upc=UPC_B, tracks=[hacer_track(track="Zeta", isrc="ARZZZ2000009")]
    )
    res = INS.comparar([antes], [otro])
    assert res["releases"][0]["estado"] == "falta"
    assert res["nuevos"] == [{"titulo": "Otra Cosa", "distribuidora": "ONErpm", "upc": UPC_B}]
    assert res["resumen"] == {"falta": 1}


def test_un_tema_que_la_entrega_nueva_no_trae(hacer_producto, hacer_track):
    antes = _disco(hacer_producto, hacer_track, dist="DistroKid")
    nuevo = _disco(hacer_producto, hacer_track, dist="Mojo", isrcs=("ARAAA2000001",))
    r = _estado(antes, [nuevo])
    assert r["temas_que_faltan"] == ["Tema 2"]


def test_dos_singles_que_se_llaman_igual_no_son_el_mismo_release(hacer_producto, hacer_track):
    a = hacer_producto(
        title="Intro", upc="", tracks=[hacer_track(track="Intro", isrc="ARAAA2000001", dur=60)]
    )
    b = hacer_producto(
        title="Intro", upc="", tracks=[hacer_track(track="Intro (Remix)", isrc="ARBBB2100002", dur=200)]
    )
    b["distributor"] = "Mojo"
    assert _estado(a, [b])["estado"] == "falta"


def test_lo_que_solo_esta_en_deezer_no_cuenta_como_presente(hacer_producto, hacer_track):
    antes = _disco(hacer_producto, hacer_track)
    fantasma = _disco(hacer_producto, hacer_track, dist="")
    fantasma["origen"] = "deezer"
    assert _estado(antes, [fantasma])["estado"] == "sin_youtube"
    # Y un release que en el guardado venía sólo de Deezer no se compara.
    assert INS.comparar([fantasma], [antes])["releases"] == []
