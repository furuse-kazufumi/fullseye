# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""lensfile(.zmx の処方の読み書き)と .agf の分散式の門。

真値は外から取る:

* **第 2・第 3 の実装** —— ray-optics(BSD-3、rayoptics 0.9.8)と optiland(MIT、0.6.3)が
  ``tests/data/lensfile/*.zmx`` を**それぞれ自分の読み手で**読み、出した EFL / BFL / F# / 入射瞳 /
  Seidel 和 / 実光線の像面座標を ``second_recorded.json`` に記録した(作り方は同じディレクトリの
  README)。CI にはどちらも無いので記録値と照合し、手元に入っていれば同じ数字をその場で計算し直す。
* **閉形式** —— 近軸は ABCD 行列(このテストで独立に書く)、放物面鏡の f = R/2、単位換算。
* **公表値** —— .agf の分散式 13 本の定義(式の形はこのテストに独立に書き下す)と、材料表の 46 硝材の
  カタログ n_d(refractiveindex.info、CC0)。

★Sellmeier 2(式番号 4)の第 2 項は ``B2/(λ²−λ2²)``(分子に λ² が無い)。Palmer の dispersion
equation 表(Univ. Arizona)とソフトの説明書の式はこの形で、OpticSim.jl(MIT)の実装だけ分子に λ² を
置いている —— 第 2 実装どうしが食い違う箇所なので、ここでは一次の式の表に従う。
"""
from __future__ import annotations

import json
import math
import os

import numpy as np
import pytest

import lensfile as L
import materials as M
import raytrace as RT

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "lensfile")
REC = json.load(open(os.path.join(DATA, "second_recorded.json"), encoding="utf-8"))
GATE_FILES = sorted(REC)


def _read(name, **kw):
    return L.lens_file_read(os.path.join(DATA, name), **kw)


# --------------------------------------------------------------------------- #
# 1. 往復(read → write → read が同じ)                                          #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("name", [None] + GATE_FILES)
def test_round_trip_is_identity(name):
    p = L.lens_file_read(None) if name is None else _read(name)
    for enc in ("ascii", "utf-16"):
        w = L.lens_file_write(p, encoding=enc)
        raw = w["text"].encode("utf-16") if enc == "utf-16" else w["text"].encode("ascii")
        q = L.lens_file_read(raw)
        assert q["surfaces"] == p["surfaces"]
        assert q["fields"] == p["fields"] and q["wavelengths"] == p["wavelengths"] and q["primary"] == p["primary"]
        assert q["aperture"]["type"] == p["aperture"]["type"]
        for a, b in zip(q["system"]["surfaces"], p["system"]["surfaces"]):
            for k in ("R", "t", "k", "asph", "mirror", "n_value"):
                assert a[k] == b[k], (name, k)
        assert q["system"]["surfaces"][q["system"]["stop"]]["ap"] == pytest.approx(
            p["system"]["surfaces"][p["system"]["stop"]]["ap"], rel=1e-14)
        # and the text itself is a fixed point after one round
        assert L.lens_file_write(q, encoding=enc)["text"] == w["text"]


def test_round_trip_of_an_edited_system_keeps_fields_and_drops_stale_solves():
    p = L.lens_file_read(None)
    s = p["system"]
    surf = [dict(x) for x in s["surfaces"]]
    surf[0]["R"] = 21.5
    surf[5]["t"] = 41.0
    edited = RT.lens_system(surf, stop=s["stop"], object_mm=s["object_mm"], wavelength_um=s["wavelength_um"])
    w = L.lens_file_write(p, system=edited)
    q = L.lens_file_read(w["text"])
    assert q["system"]["surfaces"][0]["R"] == 21.5 and q["system"]["surfaces"][5]["t"] == 41.0
    assert q["fields"] == p["fields"] and q["wavelengths"] == p["wavelengths"]
    assert RT.paraxial_trace(q["system"])["ep_radius"] == pytest.approx(RT.paraxial_trace(edited)["ep_radius"], rel=1e-12)


def test_pickups_are_verified_kept_and_dropped_when_edited():
    t = L.ZMX_EXAMPLE.replace("  CURV 0.012549633801685667 0 0 0 0 \"\"\n  DISZ 2.95208",
                              "  CURV 0.045426484276303865 4 1 1 0 \"\"\n  DISZ 3.25896\n  PZUP 1 1 0 0")
    p = L.lens_file_read(t)
    kinds = {(s["surface"], s["what"]): s["status"] for s in p["solves"]}
    assert kinds == {(5, "curvature"): "verified", (5, "thickness"): "verified"}
    assert "CURV 0.045426484276303865 4 1 1 0" in L.lens_file_write(p)["text"]
    s = p["system"]
    surf = [dict(x) for x in s["surfaces"]]
    surf[4]["R"] = 30.0
    w = L.lens_file_write(p, system=RT.lens_system(surf, stop=s["stop"]))
    assert {"surface": 5, "what": "curvature solve"} in w["dropped_solves"]
    bad = t.replace("CURV 0.045426484276303865 4 1 1 0", "CURV 0.046 4 1 1 0")
    with pytest.raises(ValueError, match="pickup"):
        L.lens_file_read(bad)


# --------------------------------------------------------------------------- #
# 2. 第 2・第 3 の実装(記録値)と閉形式                                          #
# --------------------------------------------------------------------------- #
def _abcd_efl_bfl(system):
    """Independent paraxial check: 2x2 matrices (refraction then transfer), reduced angles."""
    n_prev = system["index_object"]
    Mx = np.eye(2)
    surf = system["surfaces"]
    for i, s in enumerate(surf):
        n_next = RT.refractive_index(s["n"], system["wavelength_um"])
        c = 0.0 if s["R"] == math.inf else 1.0 / s["R"]
        Mx = np.array([[1.0, 0.0], [-(n_next - n_prev) * c, 1.0]]) @ Mx
        if i < len(surf) - 1:
            Mx = np.array([[1.0, s["t"] / n_next], [0.0, 1.0]]) @ Mx
        n_prev = n_next
    A, B, C, D = Mx.ravel()
    efl = -1.0 / C
    bfl = -A / C * n_prev
    return efl, bfl


@pytest.mark.parametrize("name", GATE_FILES)
def test_paraxial_matches_two_other_readers_and_the_abcd_matrix(name):
    p = _read(name)
    pa = RT.paraxial_trace(p["system"])
    ro = REC[name]["rayoptics"]
    assert pa["efl"] == pytest.approx(ro["efl"], rel=1e-12)
    assert pa["bfl"] == pytest.approx(ro["bfl"], abs=1e-10)
    if p["aperture"]["type"] == "FNUM":
        # the format defines image-space F/# = EFL / EPD; ray-optics sizes the pupil from its own F/#, which
        # differs from EFL / EPD in the 8th digit (also for the ENPD files below), so the pupil agrees to 1e-7
        assert pa["fno"] == pytest.approx(p["aperture"]["value"], rel=1e-13)
        assert pa["ep_radius"] == pytest.approx(ro["enp_radius"], rel=1e-7)
    else:
        assert pa["ep_radius"] == pytest.approx(ro["enp_radius"], rel=1e-12)
    assert pa["fno"] == pytest.approx(ro["fno"], rel=1e-7)
    ol = REC[name]["optiland"]
    if "error" not in ol and math.isfinite(ol["efl"]):
        assert pa["efl"] == pytest.approx(ol["efl"], rel=1e-12)
        assert 2 * pa["ep_radius"] == pytest.approx(ol["epd"], rel=1e-12)
    efl, bfl = _abcd_efl_bfl(p["system"])
    assert pa["efl"] == pytest.approx(efl, rel=1e-12) and pa["bfl"] == pytest.approx(bfl, abs=1e-10)


@pytest.mark.parametrize("name", GATE_FILES)
def test_seidel_sums_match_rayoptics_third_order(name):
    p = _read(name)
    se = RT.seidel_coefficients(L.lens_file_system(p, field_index=len(p["fields"]) - 1))["total"]
    ro = REC[name]["rayoptics"]["seidel"]
    scale = max(abs(v) for v in ro.values())
    for k, v in ro.items():
        assert abs(se[k.replace("-", "_")] - v) <= 1e-6 * scale, (name, k, se[k.replace("-", "_")], v)


@pytest.mark.parametrize("name", [n for n in GATE_FILES if "error" not in REC[n]["optiland"]
                                  and math.isfinite(REC[n]["optiland"]["efl"])])
def test_real_rays_match_optiland(name):
    p = _read(name)
    s = RT.with_wavelength(p["system"], REC[name]["optiland"]["wl"])
    ol = REC[name]["optiland"]
    e = RT.paraxial_trace(s)["ep_radius"]
    n_checked = 0
    for k, yv in ol["axis_rays"].items():
        r = RT.trace_rays(s, np.array([[0.0, float(k) * e, -1.0]]), np.array([[0.0, 0.0, 1.0]]))
        assert r["valid"][0] and abs(r["points"][0, -1, 1] - yv) < 1e-6, (name, k)
        n_checked += 1
    for fr in ol["field_rays"]:
        P1, D = np.array(fr["p1"]), np.array(fr["dir"])
        O = P1 + ((-5.0 - P1[2]) / D[2]) * D                       # back the ray off to z = -5 mm
        r = RT.trace_rays(s, O[None], D[None])
        assert r["valid"][0] and abs(r["points"][0, -1, 1] - fr["image_y"]) < 1e-6, (name, fr)
        n_checked += 1
    assert n_checked == 7


def test_live_second_implementations_if_installed(tmp_path, monkeypatch):
    """Same numbers computed now (skipped where rayoptics / optiland are not installed, e.g. CI)."""
    pytest.importorskip("rayoptics")
    monkeypatch.chdir(tmp_path)                 # rayoptics' reader opens a log file in the current directory
    from pathlib import Path
    from rayoptics.zemax import zmxread
    for name in GATE_FILES:
        opm, _ = zmxread.read_lens_file(Path(os.path.join(DATA, name)))
        opm.update_model()
        efl = opm["analysis_results"]["parax_data"].fod.efl
        assert RT.paraxial_trace(_read(name)["system"])["efl"] == pytest.approx(efl, rel=1e-12)
        # and our writer's output is read by the other program the same way
        out = tmp_path / ("w_" + name)
        L.lens_file_write(_read(name), path=str(out))
        opm2, _ = zmxread.read_lens_file(out)
        opm2.update_model()
        assert opm2["analysis_results"]["parax_data"].fod.efl == pytest.approx(efl, rel=1e-12)


def test_paraboloid_mirror_file_focuses_at_half_the_radius():
    t = """MODE SEQ
UNIT MM X W X CM MR CPMM
ENPD 50
FTYP 0 0 1 1 0 0 0
YFLN 0
WAVM 1 0.55 1
PWAV 1
SURF 0
  DISZ INFINITY
SURF 1
  STOP
  TYPE STANDARD
  CURV -0.005 0 0 0 0 ""
  DISZ -100
  GLAS MIRROR 0 0 1.5 40 0 0 0 0 0 0
  CONI -1
SURF 2
  DISZ 0
"""
    p = L.lens_file_read(t)
    s = p["system"]
    assert s["surfaces"][0]["mirror"] and s["surfaces"][0]["t"] == 100.0       # signed -> travel distance
    pa = RT.paraxial_trace(s)
    assert pa["efl"] == pytest.approx(100.0, rel=1e-12)
    st = RT.spot_stats(s, rings=6)
    assert st["rms_radius"] < 1e-9 and st["n_vignetted"] == 0                 # a paraboloid is stigmatic on axis
    q = L.lens_file_read(L.lens_file_write(p)["text"])
    assert q["surfaces"][1]["disz"] == -100.0                                   # written back with the file's sign


# --------------------------------------------------------------------------- #
# 3. .agf の分散式(13 本の定義と、材料表 46 硝材の CC0 係数)                     #
# --------------------------------------------------------------------------- #
def _closed(code, c, lam):
    """The 13 catalogue dispersion formulas written out independently (λ in µm)."""
    l2 = lam * lam
    if code == 1:
        return np.sqrt(c[0] + c[1] * l2 + c[2] / l2 + c[3] / l2 ** 2 + c[4] / l2 ** 3 + c[5] / l2 ** 4)
    if code in (2, 6, 11):
        k = {2: 3, 6: 4, 11: 5}[code]
        return np.sqrt(1.0 + sum(c[2 * i] * l2 / (l2 - c[2 * i + 1]) for i in range(k)))
    if code == 3:
        Lh = 1.0 / (l2 - 0.028)
        return c[0] + c[1] * Lh + c[2] * Lh ** 2 + c[3] * l2 + c[4] * l2 ** 2 + c[5] * l2 ** 3
    if code == 4:
        return np.sqrt(1.0 + c[0] + c[1] * l2 / (l2 - c[2] ** 2) + c[3] / (l2 - c[4] ** 2))
    if code == 5:
        return c[0] + c[1] / lam + c[2] / lam ** 3.5
    if code == 7:
        return np.sqrt(c[0] + c[1] / (l2 - c[2]) - c[3] * l2)
    if code == 8:
        return np.sqrt(c[0] + c[1] * l2 / (l2 - c[2]) - c[3] * l2)
    if code == 9:
        return np.sqrt(c[0] + c[1] * l2 / (l2 - c[2]) + c[3] * l2 / (l2 - c[4]))
    if code == 10:
        return np.sqrt(c[0] + c[1] * l2 + sum(c[1 + j] / l2 ** j for j in range(1, 7)))
    if code == 12:
        return np.sqrt(c[0] + c[1] * l2 + sum(c[1 + j] / l2 ** j for j in range(1, 5)) + c[6] * l2 ** 2 + c[7] * l2 ** 3)
    if code == 13:
        return np.sqrt(c[0] + c[1] * l2 + c[2] * l2 ** 2 + sum(c[2 + j] / l2 ** j for j in range(1, 7)))
    raise AssertionError(code)


#: Non-trivial coefficients for every formula (each term contributes ~1e-3..1e-1 to n in 0.4-1.0 µm).
_COEF = {
    1: [2.2718929, -0.010108077, 0.010592509, 0.00020816965, -7.6472538e-06, 4.9240991e-07],
    2: [1.03961212, 0.00600069867, 0.231792344, 0.0200179144, 1.01046945, 103.560653],
    3: [1.50, 0.0040, -0.0005, -0.0030, 0.0002, -1.0e-5],
    4: [0.15, 0.95, 0.09, 0.008, 0.13],
    5: [1.49, 0.0080, 0.0012],
    6: [1.0, 0.006, 0.2, 0.02, 0.9, 100.0, 0.05, 0.03],
    7: [2.28, 0.011, 0.012, 0.009],
    8: [1.30, 0.95, 0.010, 0.008],
    9: [1.25, 1.02, 0.0062, 0.9, 105.0],
    10: [2.27, -0.0101, 0.0106, 0.000208, -7.6e-06, 4.9e-07, -2.0e-08, 4.0e-10],
    11: [0.9, 0.006, 0.2, 0.02, 0.9, 100.0, 0.05, 0.03, 0.02, 0.04],
    12: [2.27, -0.0101, 0.0106, 0.000208, -7.6e-06, 4.9e-07, 0.0005, -0.0002],
    13: [2.27, -0.0101, 0.0004, 0.0106, 0.000208, -7.6e-06, 4.9e-07, -2.0e-08, 4.0e-10],
}


def test_agf_dispatch_of_all_13_formulas_matches_the_written_out_equations(tmp_path):
    txt = "".join("NM F%d %d 0 1.5 60 0 1 0\nCD %s\nLD 0.40 1.00\n" % (k, k, " ".join(repr(v) for v in c))
                  for k, c in _COEF.items())
    f = tmp_path / "all.agf"
    f.write_text(txt, encoding="ascii")
    recs = {r["name"]: r for r in M.read_glass_catalog_agf(str(f))}
    lam = np.array([0.4047, 0.48613, 0.58756, 0.65627, 0.8521, 1.0])
    for k, c in _COEF.items():
        want = _closed(k, c, lam)
        assert np.all((want > 1.3) & (want < 2.2)), k                         # the probe values are glass-like
        got = np.array([M.material_optical_constants(recs["F%d" % k], w * 1e3)["n"] for w in lam])
        assert np.max(np.abs(got - want)) < 1e-12, (k, got - want)
        # and each coefficient matters: perturbing it moves n (no term silently dropped)
        for j in range(len(c)):
            c2 = list(c)
            c2[j] = c2[j] * 1.01 + 1e-6
            assert np.max(np.abs(_closed(k, c2, lam) - want)) > 1e-9, (k, j)


@pytest.mark.parametrize("name", sorted(n for n in M.MATERIALS if M._RECORDS[n]["class"] == "glass"))
def test_agf_built_from_the_cc0_coefficients_reproduces_the_table_and_the_catalogue_nd(name, tmp_path):
    rec = M._RECORDS[name]
    ds = [d for d in rec["datasets"] if d["type"] == "formula"][0]
    c = list(ds["coefficients"])
    if ds["formula"] == 2:
        assert c[0] == 0.0
        code, cd = {7: 2, 9: 6, 11: 11}[len(c)], c[1:]
    else:
        assert ds["formula"] == 3 and [round(x) for x in c[2::2]] == [2, -2, -4, -6, -8]
        code, cd = 1, [c[0]] + c[1::2]
    lo, hi = ds["range_um"]
    f = tmp_path / "one.agf"
    f.write_text("NM %s %d 0 %r 0 0 1 0\nCD %s\nLD %r %r\n" % (name, code, rec["properties"]["nd"],
                                                            " ".join(repr(v) for v in cd), lo, hi), encoding="ascii")
    r = M.read_glass_catalog_agf(str(f))[0]
    lam_nm = np.linspace(max(lo, 0.40), min(hi, 1.0), 5) * 1e3
    for w in lam_nm:
        assert abs(M.material_optical_constants(r, w)["n"] - M.material_optical_constants(name, w)["n"]) < 1e-12
    assert abs(M.material_optical_constants(r, 587.56)["n"] - rec["properties"]["nd"]) < 1e-5   # catalogue n_d


def test_glass_from_a_user_agf_reaches_the_lens_and_its_nd_is_checked(tmp_path):
    rec = M._RECORDS["N-SK16"]
    c = list([d for d in rec["datasets"] if d["type"] == "formula"][0]["coefficients"])
    d = tmp_path / "cat"
    d.mkdir()
    (d / "user.agf").write_text("NM MYGLASS 2 0 1.62041 60.32 0 1 0\nCD %s\nLD 0.31 2.325\n" %
                                " ".join(repr(v) for v in c[1:]), encoding="ascii")
    t = L.ZMX_EXAMPLE.replace("___BLANK 1 0 1.62041 60.32", "MYGLASS 0 0 1.62041 60.32")
    p = L.lens_file_read(t, glass_dir=str(d))
    assert p["surfaces"][1]["glass"]["source"] == "user .agf catalogue"
    ref = L.lens_file_read(t.replace("MYGLASS", "N-SK16"))
    assert RT.paraxial_trace(p["system"])["efl"] == pytest.approx(RT.paraxial_trace(ref["system"])["efl"], rel=1e-14)
    with pytest.raises(ValueError, match="different glass of the same name"):
        L.lens_file_read(t.replace("MYGLASS 0 0 1.62041", "MYGLASS 0 0 1.60000"), glass_dir=str(d))


# --------------------------------------------------------------------------- #
# 4. 壊して確かめる探針                                                           #
# --------------------------------------------------------------------------- #
def test_probe_flipped_curvature_sign_is_caught_by_the_efl_gate():
    """The reader cannot know a sign is wrong; the external gate must. Flip CURV of surface 1."""
    good = L.lens_file_read(os.path.join(DATA, "triplet_const.zmx"))
    text = open(os.path.join(DATA, "triplet_const.zmx"), encoding="ascii").read()
    bad = L.lens_file_read(text.replace("CURV 0.045426484276303865", "CURV -0.045426484276303865"))
    ro = REC["triplet_const.zmx"]["rayoptics"]["efl"]
    assert abs(RT.paraxial_trace(good["system"])["efl"] - ro) < 1e-10
    assert abs(RT.paraxial_trace(bad["system"])["efl"] - ro) > 1.0              # the gate goes red


def test_probe_units():
    inch = L.lens_file_read(L.ZMX_EXAMPLE.replace("UNIT MM", "UNIT IN"))
    mm = L.lens_file_read(None)
    assert RT.paraxial_trace(inch["system"])["efl"] == pytest.approx(25.4 * RT.paraxial_trace(mm["system"])["efl"], rel=1e-12)
    a = L.lens_file_read(open(os.path.join(DATA, "asphere_singlet.zmx"), encoding="ascii").read().replace("UNIT MM", "UNIT CM"))
    b = _read("asphere_singlet.zmx")
    sa, sb = a["system"]["surfaces"][1]["asph"], b["system"]["surfaces"][1]["asph"]
    assert len(sa) == len(sb) == 3                                             # r^4, r^6, r^8
    for j in range(3):                                                         # r^(2k) term scales by 10^(1-2k)
        assert sa[j] == pytest.approx(sb[j] * 10.0 ** (-3 - 2 * j), rel=1e-12)
    with pytest.raises(ValueError, match="UNIT"):
        L.lens_file_read(L.ZMX_EXAMPLE.replace("UNIT MM", "UNIT FURLONG"))


def test_probe_encodings():
    ref = L.lens_file_read(None)
    for raw in (L.ZMX_EXAMPLE.encode("utf-16"), L.ZMX_EXAMPLE.encode("utf-16-le"), L.ZMX_EXAMPLE.encode("utf-16-be"),
                L.ZMX_EXAMPLE.encode("utf-8-sig"), L.ZMX_EXAMPLE.encode("latin-1")):
        assert L.lens_file_read(raw)["surfaces"] == ref["surfaces"]
    assert "no BOM" in L.lens_file_read(L.ZMX_EXAMPLE.encode("utf-16-le"))["encoding"]
    with pytest.raises(ValueError, match="NUL"):
        L.lens_file_read(b"MODE SEQ\n\x00\x07\x00\x00\x01\x00garbage" * 40)
    with pytest.raises(ValueError, match=".zar"):
        L.lens_file_read(b"\xec\x03" + b"\x00" * 64)
    with pytest.raises(ValueError, match="NUL characters"):
        L.lens_file_read(L.ZMX_EXAMPLE.encode("utf-16-le").decode("latin-1"))


@pytest.mark.parametrize("typ,msg", [("COORDBRK", "COORDBRK"), ("PARAXIAL", "PARAXIAL"), ("TOROIDAL", "TOROIDAL"),
                                     ("ODDASPH", "ODDASPH"), ("BICONICX", "BICONICX")])
def test_probe_unsupported_surface_types_are_refused_even_with_allow_partial(typ, msg):
    t = L.ZMX_EXAMPLE.replace("SURF 2\n  TYPE STANDARD", "SURF 2\n  TYPE %s" % typ)
    for partial in (False, True):
        with pytest.raises(ValueError, match=msg):
            L.lens_file_read(t, allow_partial=partial)


def test_probe_geometry_refusals():
    base = _read("asphere_singlet.zmx")
    text = open(os.path.join(DATA, "asphere_singlet.zmx"), encoding="ascii").read()
    assert base["system"]["surfaces"][1]["asph"][0] == 2e-5
    with pytest.raises(ValueError, match="r\\^2"):
        L.lens_file_read(text.replace("PARM 1 0", "PARM 1 0.001"), allow_partial=True)
    with pytest.raises(ValueError, match="against the light"):
        L.lens_file_read(L.ZMX_EXAMPLE.replace("DISZ 6.00755", "DISZ -6.00755"))
    with pytest.raises(ValueError, match="MODE"):
        L.lens_file_read(L.ZMX_EXAMPLE.replace("MODE SEQ", "MODE NSC"))
    with pytest.raises(ValueError, match="telecentric"):
        L.lens_file_read(L.ZMX_EXAMPLE.replace("FTYP 0 0 3 3", "FTYP 0 1 3 3"))
    with pytest.raises(ValueError, match="SCBD|tilt"):
        L.lens_file_read(L.ZMX_EXAMPLE.replace("  DISZ 6.00755\n", "  DISZ 6.00755\n  SCBD 1 0 0.5 0 0 0 0\n"),
                         allow_partial=True)
    with pytest.raises(ValueError, match="no system aperture"):
        L.lens_file_read(L.ZMX_EXAMPLE.replace("ENPD 10\n", ""))


def test_probe_glass_names_are_never_silently_substituted():
    # F2 (an old lead flint) is an alias of a lead-free glass in the material table: not followed
    t = L.ZMX_EXAMPLE.replace("___BLANK 1 0 1.62004 36.37", "F2 0 0 1.5 40")
    with pytest.raises(ValueError, match="no catalogue"):
        L.lens_file_read(t)
    t2 = L.ZMX_EXAMPLE.replace("___BLANK 1 0 1.62004 36.37", "F2 0 0 1.62004 36.37")
    with pytest.raises(ValueError, match="allow_partial"):
        L.lens_file_read(t2)
    p = L.lens_file_read(t2, allow_partial=True)
    assert p["approximate"] and p["report"]["unsupported"][0]["keyword"] == "GLAS"
    notes = p["report"]["notes"]
    assert len(notes) >= 1 and any("alias" in n for n in notes)
    # a catalogue name whose n_d on the line disagrees with the catalogue is a different glass
    with pytest.raises(ValueError, match="different glass"):
        L.lens_file_read(L.ZMX_EXAMPLE.replace("___BLANK 1 0 1.62041 60.32", "N-SK16 0 0 1.64000 60.32"))
    # the (1.5, 40) placeholder next to a catalogue name is not information
    p = L.lens_file_read(L.ZMX_EXAMPLE.replace("___BLANK 1 0 1.62041 60.32", "N-SK16 0 0 1.5 40"))
    assert p["surfaces"][1]["glass"]["source"] == "material table"


def test_approximations_need_allow_partial_and_are_marked():
    # vignetting factors are read now (raytrace applies them); only a field off the y axis is approximate
    vign = L.ZMX_EXAMPLE.replace("PWAV 2\n", "PWAV 2\nVDYN 0 0.1 0.2 0 0 0 0 0 0 0 0 0\n").replace(
        "XFLN 0 0 0", "XFLN 0 5 0")
    curved = L.ZMX_EXAMPLE.replace("SURF 7\n  TYPE STANDARD\n  CURV 0 ", "SURF 7\n  TYPE STANDARD\n  CURV -0.01 ")
    # a multi-configuration table is read now; one with an operand the reader does not know is approximate
    multi = L.ZMX_EXAMPLE + "MNUM 2 1\nAPER   0   1 5\nAPER   0   2 6\n"
    hot = L.ZMX_EXAMPLE.replace("ENVD 20 1 0", "ENVD 40 1 0")
    unknown = L.ZMX_EXAMPLE.replace("  DISZ 6.00755\n", "  DISZ 6.00755\n  ZZZZ 1 2 3\n")
    for t in (vign, curved, multi, hot, unknown):
        with pytest.raises(ValueError, match="allow_partial"):
            L.lens_file_read(t)
        p = L.lens_file_read(t, allow_partial=True)
        assert p["approximate"] is True and p["report"]["n_unsupported"] >= 1
    assert L.lens_file_read(None)["approximate"] is False
    exact = L.lens_file_read(L.ZMX_EXAMPLE.replace("PWAV 2\n", "PWAV 2\nVDYN 0 0.1 0.2 0 0 0 0 0 0 0 0 0\n"))
    assert exact["approximate"] is False and exact["system"]["vignetting"][1]["vdy"] == 0.1


def test_aperture_and_field_types():
    ref = L.lens_file_read(None)
    efl = RT.paraxial_trace(ref["system"])["efl"]
    fnum = L.lens_file_read(L.ZMX_EXAMPLE.replace("ENPD 10", "FNUM 4 0"))
    assert RT.paraxial_trace(fnum["system"])["fno"] == pytest.approx(4.0, rel=1e-12)
    floa = L.lens_file_read(L.ZMX_EXAMPLE.replace("ENPD 10", "FLOA"))
    assert floa["system"]["surfaces"][3]["ap"] == 5.0                      # the stop's semi-diameter
    # paraxial image height: a field of h mm is the angle atan(h / f) (object at infinity)
    ph = L.lens_file_read(L.ZMX_EXAMPLE.replace("FTYP 0 0 3 3", "FTYP 2 0 3 3").replace("YFLN 0 14 20", "YFLN 0 5 10"))
    assert [f["field"] for f in ph["fields"]] == pytest.approx([0.0, math.degrees(math.atan(5 / efl)),
                                                                math.degrees(math.atan(10 / efl))], rel=1e-12)
    # object height needs a finite object
    with pytest.raises(ValueError, match="finite object"):
        L.lens_file_read(L.ZMX_EXAMPLE.replace("FTYP 0 0 3 3", "FTYP 1 0 3 3"))
    fin = L.lens_file_read(L.ZMX_EXAMPLE.replace("FTYP 0 0 3 3", "FTYP 1 0 3 3").replace("DISZ INFINITY", "DISZ 500"))
    assert fin["system"]["object_mm"] == 500.0 and fin["fields"][2]["field"] == 20.0
    # x and y fields fold to the radial angle tan = hypot(tan x, tan y)
    xy = L.lens_file_read(L.ZMX_EXAMPLE.replace("XFLN 0 0 0", "XFLN 0 0 10"))
    want = math.degrees(math.atan(math.hypot(math.tan(math.radians(10)), math.tan(math.radians(20)))))
    assert xy["fields"][2]["field"] == pytest.approx(want, rel=1e-14)


def test_report_triages_without_raising():
    r = L.lens_file_report(L.ZMX_EXAMPLE.replace("SURF 2\n  TYPE STANDARD", "SURF 2\n  TYPE COORDBRK"))
    assert r["importable"] is False and r["needs_allow_partial"] is False and "COORDBRK" in r["error"]
    assert r["surface_types"] == {"STANDARD": 7, "COORDBRK": 1}
    ok = L.lens_file_report(None)
    assert ok["importable"] and ok["error"] is None and ok["read"]["SURF"] == 8
    v = L.lens_file_report(L.ZMX_EXAMPLE.replace("PWAV 2\n", "PWAV 2\nVDYN 0 0.1 0.2 0 0 0 0 0 0 0 0 0\nPOLS 1 0 1\n").replace(
        "XFLN 0 0 0", "XFLN 0 5 0"))
    assert v["needs_allow_partial"] and v["ignored"]["POLS"]["count"] == 1


def test_lens_file_system_and_argument_checks():
    p = L.lens_file_read(None)
    s = L.lens_file_system(p, field_index=2, wavelength_index=0)
    assert s["field"] == 20.0 and s["wavelength_um"] == 0.48613
    for bad in (dict(field_index=3), dict(field_index=-1), dict(field_index=True), dict(wavelength_index=3)):
        with pytest.raises(ValueError):
            L.lens_file_system(p, **bad)
    with pytest.raises(ValueError, match="lens_file_read"):
        L.lens_file_system({"surfaces": []})
    with pytest.raises(ValueError, match="encoding"):
        L.lens_file_write(p, encoding="utf-32")
    with pytest.raises(ValueError, match="neither"):
        L.lens_file_read("no_such_file.zmx")
    sell = RT.sellmeier(1.03961212, 0.231792344, 1.01046945, 0.00600069867, 0.0200179144, 103.560653, name="mine")
    s2 = RT.lens_system([{"R": 50.0, "t": 5.0, "n": sell, "ap": 10.0}, {"R": -50.0, "t": 45.0, "n": 1.0}], stop=0)
    with pytest.raises(ValueError, match="catalogue name"):
        L.lens_file_write(p, system=s2)
