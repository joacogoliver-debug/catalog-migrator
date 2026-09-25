# -*- coding: utf-8 -*-
"""Qué tracks forman un release. Sin red.

Con los datos reales de un canal Topic, la agrupación por álbum y año ℗ partía
en dos la edición aniversario de un disco (22 temas, unos de ℗ 2013 y otros de
℗ 2023, todos lanzados el mismo día) y en dos un álbum de 1996 con un tema de
℗ 1997. Y fundía en uno el mismo álbum entregado por dos distribuidoras. Cubre:

  - que la fecha de lanzamiento, y no el año ℗, defina el release
  - que una reedición con otra fecha siga siendo otro release
  - que dos distribuidoras sean dos releases, avisados
  - el caso sin fecha, por año ℗ con años seguidos juntos
"""

from conftest import _track
from migrador import productos as P
from migrador import validar as V


def _t(n, anio, fecha="", dist="ONErpm", album="Disco", vid=None):
    return _track(n, album=album, year=anio, released=fecha, dist=dist, vid=vid or f"{n}{anio}{dist}{fecha}")


def test_la_edicion_aniversario_es_un_solo_release():
    tracks = [_t(f"Original {i}", 2013, "2023-05-12") for i in range(14)]
    tracks += [_t(f"Nuevo {i}", 2023, "2023-05-12") for i in range(8)]
    ps = P.group_products(tracks)
    assert len(ps) == 1
    assert ps[0]["track_count"] == 22
    # El año del release es el de su lanzamiento, no el ℗ más viejo.
    assert ps[0]["release_year"] == 2023


def test_una_reedicion_con_otra_fecha_sigue_siendo_otro_release():
    ps = P.group_products([_t("Uno", 2001, "2001-05-14"), _t("Uno", 2001, "2021-02-22")])
    assert len(ps) == 2
    assert sorted(p["release_year"] for p in ps) == [2001, 2021]


def test_el_mismo_album_en_dos_distribuidoras_son_dos_releases_avisados():
    tracks = [_t(n, 2020, "2020-03-01", dist=d) for n in ("Uno", "Dos") for d in ("DistroKid", "ONErpm")]
    ps = P.group_products(tracks)
    assert len(ps) == 2
    assert all(p["track_count"] == 2 for p in ps)
    assert {tuple(p.get("tambien_en", [])) for p in ps} == {("DistroKid",), ("ONErpm",)}

    # El aviso sale aunque se elija uno solo de los dos.
    hallazgos = V.validar([ps[0]])["hallazgos"]
    dos = [h for h in hallazgos if h["codigo"] == "release_en_dos_distribuidoras"]
    assert [h["nivel"] for h in dos] == ["aviso"]


def test_un_solo_release_no_lleva_aviso_de_distribuidoras():
    ps = P.group_products([_t("Uno", 2020, "2020-03-01"), _t("Dos", 2020, "2020-03-01")])
    assert "tambien_en" not in ps[0]
    assert "release_en_dos_distribuidoras" not in [h["codigo"] for h in V.validar(ps)["hallazgos"]]


def test_sin_fecha_los_anios_seguidos_son_el_mismo_disco():
    ps = P.group_products([_t("Uno", 1996), _t("Dos", 1997), _t("Tres", 1997)])
    assert [p["track_count"] for p in ps] == [3]


def test_sin_fecha_los_anios_separados_siguen_separados():
    ps = P.group_products([_t("Uno", 2001), _t("Uno (Edit)", 2021)])
    assert len(ps) == 2


def test_un_track_sin_fecha_se_suma_al_unico_release_con_fecha():
    ps = P.group_products([_t("Uno", 2020, "2020-03-01"), _t("Dos", 2019)])
    assert [p["track_count"] for p in ps] == [2]


def test_con_dos_releases_con_fecha_el_sin_fecha_no_se_adivina():
    ps = P.group_products([_t("Uno", 2001, "2001-05-14"), _t("Uno", 2021, "2021-02-22"), _t("Dos", 2010)])
    assert len(ps) == 3


def test_los_singles_siguen_siendo_uno_por_video():
    ps = P.group_products([_track("Tema", year=2020, vid="a"), _track("Tema", year=2020, vid="b")])
    assert len(ps) == 2
