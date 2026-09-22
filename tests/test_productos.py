# -*- coding: utf-8 -*-
"""Agrupación del catálogo en productos, y filtros de selección. Sin red.

Cubre las reglas que sostienen la selección de la migración.
  - tracks del mismo álbum se agrupan en un producto
  - un álbum y su reedición (mismo título, otro año) NO se fusionan
  - los tracks sin álbum quedan como singles independientes
  - clasificación single / EP / álbum por cantidad de tracks
  - consolidación de sello, distribuidora y UPC despareros
  - filtros por id, por año, por fecha y por distribuidora
  - nombres de carpeta seguros en Windows
"""

import pytest

from migrador import productos as pr


# ============================================================
# Agrupación
# ============================================================


def test_tracks_del_mismo_album_son_un_producto(hacer_track):
    ps = pr.group_products(
        [
            hacer_track("Tema A", "Mi Album", 2019, date="2019-05-01"),
            hacer_track("Tema B", "Mi Album", 2019, date="2019-05-02"),
            hacer_track("Tema C", "Mi Album", 2019, date="2019-05-03"),
        ],
        artist="Artista",
    )

    assert len(ps) == 1
    assert ps[0]["track_count"] == 3
    assert ps[0]["kind"] == "single"  # 3 tracks, por convención es single
    assert ps[0]["title"] == "Mi Album"
    assert ps[0]["release_year"] == 2019
    # El orden salió de la fecha de subida, así que queda marcado sin confirmar.
    assert ps[0]["order_unconfirmed"] is True
    assert ps[0]["tracks"][0]["track"] == "Tema A"


def test_un_album_y_su_reedicion_no_se_fusionan(hacer_track):
    """Mismo título, otro año. En una migración son dos productos con UPC
    distinto, y fusionarlos perdería uno."""
    ps = pr.group_products(
        [
            hacer_track("Tema A", "Clasico", 2005, date="2005-01-01"),
            hacer_track("Tema A", "Clasico", 2020, date="2020-01-01"),
        ]
    )
    assert len(ps) == 2


def test_agrupa_sin_importar_acentos_ni_puntuacion(hacer_track):
    ps = pr.group_products(
        [
            hacer_track("T1", "Corazón Roto", 2018, date="2018-01-01"),
            hacer_track("T2", "Corazon Roto!", 2018, date="2018-01-02"),
        ]
    )
    assert len(ps) == 1


def test_cada_single_es_su_propio_producto(hacer_track):
    ps = pr.group_products(
        [
            hacer_track("Single Uno", "", 2021, vid="a1", date="2021-01-01"),
            hacer_track("Single Dos", "", 2021, vid="a2", date="2021-02-01"),
        ]
    )
    assert len(ps) == 2
    assert ps[0]["kind"] == "single"
    assert sorted(p["title"] for p in ps) == ["Single Dos", "Single Uno"]


@pytest.mark.parametrize(
    "n_tracks, esperado",
    [
        (1, "single"),
        (3, "single"),  # convención de distribuidoras, 1-3
        (4, "ep"),
        (6, "ep"),  # 4-6
        (7, "album"),
        (12, "album"),  # 7+
    ],
)
def test_formato_por_cantidad_de_tracks(hacer_track, n_tracks, esperado):
    ps = pr.group_products(
        [hacer_track(f"T{i}", "Disco", 2020, date=f"2020-01-{i:02d}") for i in range(1, n_tracks + 1)]
    )
    assert ps[0]["kind"] == esperado


def test_consolida_datos_despareros_entre_tracks(hacer_track):
    """Dos tracks traen UPC y sello, uno viene vacío. Gana el valor no vacío."""
    ps = pr.group_products(
        [
            hacer_track("T1", "Disco", 2020, upc="123", label="Sello Real", date="2020-01-01"),
            hacer_track("T2", "Disco", 2020, upc="123", label="Sello Real", date="2020-01-02"),
            hacer_track("T3", "Disco", 2020, upc="", label="", date="2020-01-03"),
        ]
    )
    assert ps[0]["upc"] == "123"
    assert ps[0]["label"] == "Sello Real"


def test_sin_datos_no_le_gana_a_una_distribuidora_real(hacer_track):
    ps = pr.group_products(
        [
            hacer_track("T1", "Disco", 2020, dist=pr.SIN_DATOS, date="2020-01-01"),
            hacer_track("T2", "Disco", 2020, dist="ONErpm", date="2020-01-02"),
        ]
    )
    assert ps[0]["distributor"] == "ONErpm"


def test_catalogo_vacio():
    assert pr.group_products([]) == []
    assert pr.summarize([])["products"] == 0


# ============================================================
# Filtros
# ============================================================


@pytest.fixture
def catalogo(hacer_track):
    """Tres productos de años y distribuidoras distintas."""
    return pr.group_products(
        [
            hacer_track("A", "Viejo", 2010, dist="DistroKid", date="2010-06-01"),
            hacer_track("B", "Medio", 2015, dist="ONErpm", date="2015-06-01"),
            hacer_track("C", "Nuevo", 2022, dist="ONErpm", date="2022-06-01"),
        ]
    )


def test_el_catalogo_sale_ordenado_del_mas_nuevo_al_mas_viejo(catalogo):
    assert len(catalogo) == 3
    assert [p["title"] for p in catalogo] == ["Nuevo", "Medio", "Viejo"]


def test_filtro_por_rango_de_anios(catalogo):
    assert sorted(p["title"] for p in pr.filter_products(catalogo, year_from=2015)) == ["Medio", "Nuevo"]
    assert sorted(p["title"] for p in pr.filter_products(catalogo, year_to=2015)) == ["Medio", "Viejo"]
    acotado = pr.filter_products(catalogo, year_from=2015, year_to=2015)
    assert [p["title"] for p in acotado] == ["Medio"]


def test_filtro_por_distribuidora_ignora_mayusculas(catalogo):
    f = pr.filter_products(catalogo, distributors=["onerpm"])
    assert sorted(p["title"] for p in f) == ["Medio", "Nuevo"]


def test_filtro_por_fecha_de_publicacion(catalogo):
    f = pr.filter_products(catalogo, date_from="2015-01-01", date_to="2015-12-31")
    assert [p["title"] for p in f] == ["Medio"]


def test_filtro_por_ids(catalogo):
    f = pr.filter_products(catalogo, ids=[catalogo[0]["product_id"]])
    assert [p["title"] for p in f] == ["Nuevo"]


def test_los_filtros_se_combinan_con_and(catalogo):
    assert pr.filter_products(catalogo, year_from=2015, distributors=["distrokid"]) == []


def test_un_producto_sin_anio_no_se_cuela_en_un_filtro_por_anio(hacer_track):
    """Preferimos excluirlo antes que meterlo en una selección donde no sabemos
    si entra."""
    sin_anio = pr.group_products([hacer_track("X", "SinAnio", "", date="2020-01-01")])
    assert pr.filter_products(sin_anio, year_from=2000) == []


# ============================================================
# Lo que consume la interfaz
# ============================================================


def test_opciones_de_distribuidora_y_rango_de_anios(catalogo):
    assert pr.distributor_options(catalogo) == [
        {"name": "ONErpm", "count": 2},
        {"name": "DistroKid", "count": 1},
    ]
    assert pr.year_range(catalogo) == (2010, 2022)
    assert pr.year_range([]) == (None, None)


def test_resumen_de_la_seleccion(catalogo):
    s = pr.summarize(catalogo)
    assert s["products"] == 3
    assert s["tracks"] == 3
    assert s["singles"] == 3


# ============================================================
# Nombres de carpeta
# ============================================================


@pytest.mark.parametrize(
    "producto, esperado",
    [
        ({"release_year": 2019, "title": "Mi Album", "upc": "123"}, "2019 - Mi Album [123]"),
        ({"release_year": 2019, "title": "Mi Album", "upc": ""}, "2019 - Mi Album"),
        ({"release_year": "", "title": "Album", "upc": ""}, "s-f - Album"),
        # Prohibidos en Windows. Se sacan, no se escapan.
        ({"release_year": 2020, "title": 'A/B:C*D?"E<F>G|H', "upc": ""}, "2020 - ABCDEFGH"),
        # Windows no admite carpetas que terminen en punto o espacio.
        ({"release_year": 2020, "title": "Album...", "upc": ""}, "2020 - Album"),
    ],
)
def test_nombre_de_carpeta_seguro(producto, esperado):
    assert pr.folder_name(producto) == esperado
