# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""多構成(ズーム・切替)の逐次系 —— lensconfig と .zmx の MNUM 表の門。

真値は外から取る:

* **閉形式** —— 薄肉 2 枚の合成焦点距離 ``f1·f2/(f1+f2−d)`` と後端焦点距離 ``f2·(f1−d)/(f1+f2−d)``
  (間隔 d だけが構成ごとに違う)。囲みエネルギーは Airy の 83.8 %(第 1 暗環 1.2197 λ F#)。
* **往復** —— 3 構成の系を .zmx に書き、読み戻して、構成ごとの全上書き値と EFL が一致する。
* **公開ファイルの行の形** —— 公開のズームレンズ .zmx(24 本)で確かめた行(``MNUM n active`` のあとの
  ``THIC / CRVT / GLSS / PRAM / PARn`` の表)を、そのままの形で手書きして読む。実ファイルは権利が
  はっきりしないので同梱しない(手元の非公開置き場で EFL を確かめた —— 記録は docs/capabilities)。
* **独立性** —— 構成を解決しても基の系は書き換わらない。
"""
from __future__ import annotations

import copy
import math

import pytest

import lensconfig as LC
import lensfile as LF
import raytrace as RT

INF = float("inf")
F1, F2 = 100.0, 60.0
DS = (10.0, 20.0, 30.0)


def _zoom():
    base = RT.lens_system([{"f": F1, "t": 20.0, "ap": 5.0}, {"f": F2, "t": None}], stop=0, object_mm=INF)
    base["configurations"] = [{"name": "d=%g" % d, "surfaces": {0: {"t": d}}} for d in DS]
    return base


def _thick():
    """The Cooke triplet of the bundled example with the stop moved to the first surface (so the pupil is fixed)."""
    p = LF.lens_file_read(None)
    surf = [dict(x) for x in p["system"]["surfaces"]]
    surf[0]["ap"] = 5.0
    surf[2]["asph"] = (2e-6,)
    s = RT.lens_system(surf, stop=0, object_mm=INF)
    s["configurations"] = [
        {"name": "a"},
        {"name": "b", "surfaces": {1: {"t": 4.0}, 4: {"t": 6.0}, 3: {"R": -40.0}}},
        {"name": "c", "surfaces": {1: {"t": 2.5}, 5: {"n": "N-BK7"}, 2: {"asph": (5e-6,)}}}]
    p["system"] = s
    return p


# ---------------------------------------------------------------- closed form
def test_two_thin_lens_zoom_efl_and_bfl_closed_form():
    systems = LC.lens_configurations(_zoom())
    assert len(systems) == 3
    for s, d in zip(systems, DS):
        p = RT.paraxial_trace(s)
        assert abs(p["efl"] - F1 * F2 / (F1 + F2 - d)) < 1e-9
        assert abs(p["bfl"] - F2 * (F1 - d) / (F1 + F2 - d)) < 1e-9
    efl = LC.lens_configuration_metrics(_zoom(), "efl")
    bfl = LC.lens_configuration_metrics(_zoom(), "bfl")
    assert len(efl["values"]) == 3 and len(bfl["values"]) == 3
    assert efl["values"] == pytest.approx([F1 * F2 / (F1 + F2 - d) for d in DS], abs=1e-9)
    assert bfl["values"] == pytest.approx([F2 * (F1 - d) / (F1 + F2 - d) for d in DS], abs=1e-9)


def test_probe_gate_goes_red_for_a_wrong_formula():
    """The closed form is not satisfied by the sum-of-powers mistake (separation ignored)."""
    p = RT.paraxial_trace(LC.lens_with_configuration(_zoom(), 2))
    assert abs(p["efl"] - F1 * F2 / (F1 + F2)) > 1.0


def test_encircled_energy_is_airy_for_a_single_ideal_lens_whose_f_changes():
    """A stigmatic lens: 83.8 % of the energy within 1.2197 lambda F# in every configuration (F# follows f)."""
    base = RT.lens_system([{"f": 50.0, "t": None, "ap": 5.0}], stop=0, object_mm=INF)
    fs = (40.0, 60.0, 90.0)
    base["configurations"] = [{"surfaces": {0: {"f": f}}} for f in fs]
    systems = LC.lens_configurations(base)
    assert len(systems) == 3
    vals = []
    for k, (s, f) in enumerate(zip(systems, fs)):
        assert abs(RT.paraxial_trace(s)["efl"] - f) < 1e-9
        radius_um = 1.2197 * s["wavelength_um"] * (f / 10.0)
        one = dict(base, configurations=[base["configurations"][k]])
        vals.append(LC.lens_configuration_metrics(one, "encircled_energy", field=0.0,
                                                  radius_um=radius_um)["values"][0])
    assert len(vals) == 3
    assert vals == pytest.approx([0.838] * 3, abs=0.01)
    wrong = LC.lens_configuration_metrics(dict(base, configurations=[base["configurations"][0]]),
                                          "encircled_energy", field=0.0, radius_um=1.2197 * 0.58756 * 9.0)
    assert wrong["values"][0] > 0.90                                    # probe: a radius for F/9 is far too big for F/4


def test_mtf_and_spot_metrics_are_ordered_and_finite():
    mtf = LC.lens_configuration_metrics(_zoom(), "mtf", field=0.0, frequency_cpmm=20.0)
    spot = LC.lens_configuration_metrics(_zoom(), "rms_spot", field=0.0)
    mv, sv = mtf["values"], spot["values"]
    assert len(mv) == 3 and len(sv) == 3
    assert all(0.0 < v <= 1.0 for v in mv)
    assert all(v < 1e-9 for v in sv)                             # an ideal lens: no geometric blur
    # the cut-off falls as 1/F#: a longer focal length (larger d) keeps more contrast at the same frequency
    assert mtf["values"][0] < mtf["values"][1] < mtf["values"][2]


# ---------------------------------------------------------------- the table
def test_configuration_table_rows_and_columns():
    t = LC.lens_configuration_table(_zoom())
    assert t["n_configurations"] == 3 and len(t["rows"]) == 1 and len(t["columns"]) == 3
    row = t["rows"][0]
    assert row["operand"] == "surface 0 t" and row["values"] == list(DS)
    assert [c["values"]["surface 0 t"] for c in t["columns"]] == list(DS)
    # the example (no argument) works and has two named configurations
    ex = LC.lens_configuration_table(None)
    assert ex["names"] == ["wide", "tele"] and len(ex["rows"]) == 1


def test_system_level_overrides_are_resolved_and_listed():
    z = _zoom()
    z["configurations"][1]["system"] = {"field": 2.0, "wavelength_um": 0.65}
    r = LC.lens_configurations(z)
    assert r[1]["field"] == 2.0 and r[1]["wavelength_um"] == 0.65 and r[0]["field"] == 0.0
    ops = {row["operand"] for row in LC.lens_configuration_table(z)["rows"]}
    assert {"surface 0 t", "system field", "system wavelength_um"} <= ops


def test_add_configuration_appends_and_validates():
    z = LC.lens_add_configuration(_zoom(), {0: {"t": 15.0}}, name="mid")
    assert len(z["configurations"]) == 4 and len(_zoom()["configurations"]) == 3
    assert abs(RT.paraxial_trace(LC.lens_with_configuration(z, 3))["efl"] - F1 * F2 / (F1 + F2 - 15.0)) < 1e-9
    with pytest.raises(ValueError, match="does not exist"):
        LC.lens_add_configuration(_zoom(), {7: {"t": 1.0}})


# ---------------------------------------------------------------- independence
def test_resolving_never_mutates_the_base_or_aliases_it():
    z = _thick()["system"]
    before = copy.deepcopy(z)
    res = LC.lens_configurations(z)
    assert len(res) == 3 and z == before
    res[1]["surfaces"][1]["t"] = 123.0
    res[2]["surfaces"][2]["asph"] = (9.0,)
    assert z == before
    again = LC.lens_with_configuration(z, 1)
    assert again["surfaces"][1]["t"] == 4.0
    assert "configurations" not in again and again["configuration"] == 1
    assert z["surfaces"][1]["t"] != 4.0


# ---------------------------------------------------------------- fail-closed
@pytest.mark.parametrize("cfg, msg", [
    ({"surfaces": {9: {"t": 1.0}}}, "does not exist"),
    ({"surfaces": {-1: {"t": 1.0}}}, "does not exist"),
    ({"surfaces": {0: {"thickness": 1.0}}}, "no overridable field"),
    ({"surfaces": {0: {}}}, "non-empty"),
    ({"system": {"wavelength": 0.5}}, "no overridable system field"),
    ({"surfaces": {0: {"t": -5.0}}}, "cannot be built"),
    ({"layers": 3}, "unknown key"),
    ({"surfaces": {"x": {"t": 1.0}}}, "not an integer"),
    ("not a dict", "must be a dict"),
])
def test_bad_configurations_are_refused_by_name(cfg, msg):
    z = _zoom()
    z["configurations"] = [{}, cfg]
    with pytest.raises(ValueError, match=msg):
        LC.lens_configurations(z)


def test_index_and_container_errors():
    z = _zoom()
    for k in (3, -1, True, 1.0, "0"):
        with pytest.raises(ValueError, match="configuration index"):
            LC.lens_with_configuration(z, k)
    with pytest.raises(ValueError, match="no \"configurations\""):
        LC.lens_configurations(RT.lens_system())
    with pytest.raises(ValueError, match="non-coaxial"):
        LC.lens_configurations({"elements": [], "configurations": [{}]})
    with pytest.raises(ValueError, match="metric"):
        LC.lens_configuration_metrics(z, "strehl")
    with pytest.raises(ValueError, match="frequency_cpmm"):
        LC.lens_configuration_metrics(z, "mtf")
    with pytest.raises(ValueError, match="radius_um"):
        LC.lens_configuration_metrics(z, "encircled_energy")


# ---------------------------------------------------------------- .zmx round trip
def _resolved_values(system):
    out = []
    for s in LC.lens_configurations(system):
        out.append([(x["R"], x["t"], x["k"], tuple(x["asph"]), x["mirror"]) for x in s["surfaces"]])
    return out


def test_zmx_round_trip_keeps_every_configuration():
    p = _thick()
    w = LF.lens_file_write(p)
    assert w["n_configurations"] == 3 and w["rows"] == {"GLSS": 1, "THIC": 2, "CRVT": 1, "PRAM": 1}
    assert "\nMNUM 3 1\n" in w["text"]
    q = LF.lens_file_read(w["text"])
    assert q["n_configurations"] == 3 and q["active_configuration"] == 0
    a, b = _resolved_values(p["system"]), _resolved_values(q["system"])
    assert len(a) == 3 and len(b) == 3
    for ca, cb in zip(a, b):
        assert len(ca) == len(cb) == 6
        for (r1, t1, k1, as1, m1), (r2, t2, k2, as2, m2) in zip(ca, cb):
            assert (r1 == r2 == INF) or abs(r1 - r2) <= 1e-12 * abs(r1)
            assert abs(t1 - t2) <= 1e-12 * max(1.0, abs(t1)) and k1 == k2 and m1 == m2
            assert len(as1) == len(as2) and all(abs(u - v) <= 1e-12 * abs(u) for u, v in zip(as1, as2))
    e1 = [RT.paraxial_trace(s)["efl"] for s in LC.lens_configurations(p["system"])]
    e2 = [RT.paraxial_trace(s)["efl"] for s in LC.lens_configurations(q["system"])]
    assert len(e1) == 3 and e1 == pytest.approx(e2, rel=1e-12)
    assert len({round(e, 3) for e in e1}) == 3                     # the three EFLs really differ
    assert q["system"]["surfaces"][5]["n"] == 1.0 or q["system"]["configurations"][2]["surfaces"][5]["n"]
    # write -> read -> write is a fixed point
    assert LF.lens_file_write(q)["text"].split("SURF 0", 1)[1].split("MNUM")[1] == \
        w["text"].split("SURF 0", 1)[1].split("MNUM")[1]


def test_utf16_file_round_trip(tmp_path):
    p = _thick()
    path = tmp_path / "zoom.zmx"
    LF.lens_file_write(p, path=str(path), encoding="utf-16")
    q = LF.lens_file_read(str(path))
    assert q["n_configurations"] == 3
    assert RT.paraxial_trace(LC.lens_with_configuration(q["system"], 1))["efl"] == pytest.approx(
        RT.paraxial_trace(LC.lens_with_configuration(p["system"], 1))["efl"], rel=1e-12)


def test_fnum_file_with_a_zoom_round_trips_and_keeps_the_f_number():
    text = LF.ZMX_EXAMPLE.replace("ENPD 10", "FNUM 5 0").replace("  STOP\n", "")
    text = text.replace("SURF 1\n", "SURF 1\n  STOP\n", 1)
    text += "MNUM 2 1\nTHIC   2   1 6.00755\nTHIC   2   2 3.5\nTHIC   5   1 2.95208\nTHIC   5   2 5\n"
    p = LF.lens_file_read(text)
    assert p["n_configurations"] == 2
    efls = [RT.paraxial_trace(s)["efl"] for s in LC.lens_configurations(p["system"])]
    assert len(efls) == 2 and abs(efls[0] - efls[1]) > 0.1
    w = LF.lens_file_write(p)
    assert "\nFNUM 5 0\n" in w["text"] and "\nENPD" not in w["text"]
    q = LF.lens_file_read(w["text"])
    efls2 = [RT.paraxial_trace(s)["efl"] for s in LC.lens_configurations(q["system"])]
    assert efls2 == pytest.approx(efls, rel=1e-12)
    # the stop radius follows the focal length in each configuration (F/# fixed)
    qsys = LC.lens_configurations(q["system"])
    assert len(qsys) == 2
    for s in qsys:
        pa = RT.paraxial_trace(s)
        assert abs(pa["fno"] - 5.0) < 1e-9


# ---------------------------------------------------------------- public row layout, as found in real files
def _triplet_with_table(table, head="MNUM 3 2"):
    return LF.ZMX_EXAMPLE + head + "\n" + table


ROWS_LONG = """MOFF   0   1 "" 0 0 0 1 1 0 0.0 ""
MOFF   0   2 "wide" 0 0 0 1 1 0 0.0 ""
MOFF   0   3 "" 0 0 0 1 1 0 0.0 ""
THIC   2   1 6.00755 0 0 0 1 1 1 0 0
THIC   2   2 4.5 0 0 0 1 1 1.000000000000E+000 0.000000000000E+000 0
THIC   2   3 3.0 0 0 0 1 1 1 0 0
SDIA   1   1 7 0 0 0 1 1 1 0 0
SDIA   1   2 8 0 0 0 1 1 1 0 0
SDIA   1   3 9 0 0 0 1 1 1 0 0
CRVT   4   1 0.0 0 0 0 1 1 1 0 0
CRVT   4   2 0.04928069891858434 0 0 0 1 1 1 0 0
CRVT   4   3 0.04928069891858434 0 0 0 1 1 1 0 0
GLSS   6   1 N-BK7 0 0
GLSS   6   2
GLSS   6   3 N-BK7 0 0
"""


def test_public_row_layout_is_read():
    # active configuration 2: the surface blocks of the example must agree with the configuration-2 rows,
    # so write the table the way a file would: surface blocks = configuration 2 values.
    text = LF.ZMX_EXAMPLE.replace("DISZ 6.00755", "DISZ 4.5").replace("CURV 0.04928069891858434", "CURV 0.04928069891858434")
    text += "MNUM 3 2\n" + ROWS_LONG
    p = LF.lens_file_read(text)
    assert p["n_configurations"] == 3 and p["active_configuration"] == 1
    rep = p["report"]
    assert rep["ignored"]["SDIA"]["count"] == 3 and rep["ignored"]["MOFF"]["count"] == 3
    assert rep["read"]["THIC"] == 3 and rep["read"]["CRVT"] == 3 and rep["read"]["GLSS"] == 3
    cfgs = p["system"]["configurations"]
    assert len(cfgs) == 3
    sysd = LC.lens_configurations(p["system"])
    assert [s["surfaces"][1]["t"] for s in sysd] == pytest.approx([6.00755, 4.5, 3.0], abs=1e-12)
    assert sysd[0]["surfaces"][3]["R"] == INF and sysd[1]["surfaces"][3]["R"] == pytest.approx(1 / 0.04928069891858434)
    # configuration 2 is the stored prescription: it carries no override
    assert "surfaces" not in cfgs[1] or 1 not in cfgs[1]["surfaces"]
    # air (an empty GLSS) in configuration 2 against N-BK7 in 1 and 3
    assert sysd[1]["surfaces"][5]["n"] == 1.0 and sysd[0]["surfaces"][5]["n"] != 1.0


def test_pram_and_parn_rows_set_aspheric_coefficients():
    text = LF.ZMX_EXAMPLE.replace("SURF 2\n  TYPE STANDARD\n", "SURF 2\n  TYPE EVENASPH\n  PARM 1 0\n  PARM 2 1e-06\n")
    text += ("MNUM 2 1\nPRAM   2   1 1.000000000000E-006 0 2 0 1 1 1.000000000000E+000 0.000000000000E+000 0\n"
             "PRAM   2   2 3.000000000000E-006 0 2 0 1 1 1.000000000000E+000 0.000000000000E+000 0\n"
             "PAR3   2   1 0 0 0\nPAR3   2   2 5e-12 0 0\n")
    p = LF.lens_file_read(text)
    s = LC.lens_configurations(p["system"])
    assert s[0]["surfaces"][1]["asph"] == (1e-06,) and s[1]["surfaces"][1]["asph"] == (3e-06, 5e-12)


def test_active_configuration_is_the_stored_one_and_rows_may_be_in_any_order():
    text = LF.ZMX_EXAMPLE.replace("DISZ 6.00755", "DISZ 3.0")
    text += "MNUM 3 3\nTHIC   2   3 3.0\nTHIC   2   1 6.00755\nTHIC   2   2 4.5\n"
    p = LF.lens_file_read(text)
    assert p["active_configuration"] == 2
    assert p["system"]["surfaces"][1]["t"] == 3.0
    assert [s["surfaces"][1]["t"] for s in LC.lens_configurations(p["system"])] == [6.00755, 4.5, 3.0]


@pytest.mark.parametrize("table, msg", [
    ("THIC   2   1 6.0\nTHIC   2   2 5.0\n", "expected 1..3"),                    # a row must give every configuration
    ("THIC   2   1 6.0\nTHIC   2   2 5.0\nTHIC   2   4 4.0\n", "names configuration 4"),
    ("THIC   2   1 6.0\nTHIC   2   2 5.0\nTHIC   2   3 4.0\nTHIC  99   1 1\nTHIC  99   2 1\nTHIC  99   3 1\n",
     "surface 99"),
    ("APER   0   1 5\nAPER   0   2 6\nAPER   0   3 7\n", "APER is not supported"),
    ("PRAM   2   1 1e-6 0\n", "parameter number"),
    ("THIC   2   1 abc\n", "not a number"),
])
def test_malformed_or_unsupported_tables_are_refused(table, msg):
    with pytest.raises(ValueError, match=msg):
        LF.lens_file_read(_triplet_with_table(table, "MNUM 3 1"))


def test_unsupported_operand_is_dropped_only_with_allow_partial():
    text = _triplet_with_table("APER   0   1 5\nAPER   0   2 6\nAPER   0   3 7\n", "MNUM 3 1")
    p = LF.lens_file_read(text, allow_partial=True)
    assert p["approximate"] is True and p["n_configurations"] == 3
    unsupported = p["report"]["unsupported"]
    assert len(unsupported) >= 1
    assert any(u["keyword"] == "APER" for u in unsupported)


def test_bad_mnum_header_is_refused():
    for head in ("MNUM 3 4", "MNUM 0 1", "MNUM 2 0"):
        with pytest.raises(ValueError, match="active configuration"):
            LF.lens_file_read(LF.ZMX_EXAMPLE + head + "\n")


def test_single_config_file_is_unchanged():
    p = LF.lens_file_read(None)
    assert p["n_configurations"] == 1 and "configurations" not in p["system"]
    assert LF.lens_file_read(LF.lens_file_write(p)["text"])["n_configurations"] == 1


def test_one_configuration_writes_a_plain_file():
    p = _thick()
    p["system"]["configurations"] = p["system"]["configurations"][:1]
    w = LF.lens_file_write(p)
    assert "MNUM" not in w["text"] and "n_configurations" not in w


# ---------------------------------------------------------------- the writer refuses what the lines cannot carry
def test_writer_refuses_a_changing_pupil_and_names_the_line():
    p = LF.lens_file_read(None)                        # the stop is inside the triplet: ENPD follows the spacing
    s = p["system"]
    s["configurations"] = [{}, {"surfaces": {1: {"t": 5.0}}}]
    with pytest.raises(ValueError, match="ENPD"):
        LF.lens_file_write(p)


@pytest.mark.parametrize("override, msg", [
    ({"surfaces": {1: {"ap": 4.0}}}, "clear aperture"),
    ({"surfaces": {1: {"k": -0.5}}}, "conic"),
    ({"surfaces": {1: {"n": (1.6, 50.0)}}}, "model"),
    ({"system": {"wavelength_um": 0.6}}, "system setting"),
    ({"system": {"field": 3.0}}, "system setting field"),
])
def test_writer_refuses_unrepresentable_differences(override, msg):
    p = _thick()
    p["system"]["configurations"] = [{}, override]
    with pytest.raises(ValueError, match=msg):
        LF.lens_file_write(p)
