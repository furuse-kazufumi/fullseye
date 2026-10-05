# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""pxrd の門(粉末 X 線回折: 2-D 検出器の環 → 較正 → 方位積分 → 山 → 指数付け → 相分率 → 未知相)。

numpy + scipy だけの門(常に走る):
 1. 散乱因子: f₀(0) = 電子の数(中性 Z、イオン Z − 価数)、s で単調に減る
 2. 外の真値 NIST SRM 640g の証明書: a = 0.543 110 9 nm と Cu Kα1 λ = 0.154 059 29 nm から Bragg で表 A1 の 11 本の 2θ
    (0.001° 刻みの公表値)を再現し、140° までに現れる線がちょうどその 11 本(他は全部消滅)
 3. 構造因子の閉形式: diamond の 200・222・420 は消える、|F(111)|² = 32 f²・|F(220)|² = 64 f²、岩塩の奇数 4|f₁ − f₂|・
    偶数 4(f₁ + f₂)、Lorentz 因子の恒等式、六方晶の面間隔の式(三斜の計量で解いた d と一致)
 4. CIF の読み: 中心化の 4 操作・不確かさの括弧・注釈・引用符・セミコロンの欄を含む手書きの CIF → 原子 8 個、原型と |F|² が一致、
    対称操作の構文解析、壊れた CIF は ValueError
 5. 密度: 教科書の X 線密度(Si 2.329、NaCl 2.165、CaF₂ 3.180、MgO 3.58 g/cm³)と 0.5 % 以内
 6. 較正: 傾き 0 と 5° の合成像で中心 < 0.05 px、距離 < 0.02 %、傾き < 0.05°・向き < 2°、rms < 画素 1/4 の角
 7. 方位積分と指数付け: 較正した幾何で Si の山の 2θ の誤差 < 0.006°、diamond と判定、a の誤差 < 0.005 %
 8. 混合物: NaCl / CaF₂ / Al(+ 辞書に無い MgO)の重量分率の誤差 < 1 wt%、無い相 < 0.5 wt%、MgO の山を残差から拾い F・a 0.05 %
 9. 相を剥がす順: 3 相を選んで止まり、段ごとに rwp が下がる
10. Scherrer: 80・300 Å の径を中央値 5 % 以内で復元、800 Å(装置の幅に埋もれる)は ValueError
11. 罠 1: 傾き 5° を無視して積分すると山が割れて数が 2 倍超・111 の FWHM が 2 倍超、傾きを解かない較正は ok にならず rms が 5 倍超
12. 罠 2: 参照より格子が 0.4 % 大きいと NaCl 50 wt% が 30 wt% 未満に化ける、格子の追い込みで 1 wt% 以内に戻る
13. 「走った」でなく中身: 像・相ごとの寄与・プロファイルが有限・非定数・空でない、相の寄与 + 背景 = 像の期待値
14. 既存 op を被験者に: match3d.polar_unwrap の半径プロファイルの環の位置、dsp.find_peaks / peak_subbin の山の位置
    (worktree が import できなければ skip)
15. 綴り壊しと壊れた入力は ValueError
16. 入口: __all__ が実在、docstring に Markdown のリンク記法なし、ソースに acos / asin の呼び出しなし
実データの門(環境変数 FULLSEYE_PXRD_DATA が無ければ skip):
17. COD の CIF 7 本: 展開後の原子数、密度、コランダムの d が六方晶の式と一致、Si の 200 / 222 が消える
18. 埋め込んだ散乱因子の係数 = DABAX のファイル、NIST の定数 = 証明書の本文
19. コランダム(三方晶、立方晶でない)を含む混合物の 2-D の連鎖で分率 < 1.5 wt%
"""
from __future__ import annotations

import inspect
import math
import os
import re
from pathlib import Path

import numpy as np
import pytest

import pxrd as X

LAM = 0.5                                   # Å(約 24.8 keV)
GEOM = {"cx": 261.3, "cy": 247.8, "distance": 100.0, "pixel": 0.2, "wavelength": LAM}
GEOM_TILT = dict(GEOM, tilt=5.0, tilt_dir=30.0)
#: NIST SRM 640g の証明書(2024-02-27 発行)の表 1 と付録 A の表 A1(本文から機械的に抜いた値)
SRM640G_A_NM = 0.5431109
SRM640G_U_NM = 0.0000080                    # 拡張不確かさ k = 2
SRM640G_LAMBDA_NM = 0.15405929              # Cu Kα1(表 A1 の計算に使った値)
SRM640G_TABLE_A1 = [((1, 1, 1), 28.441), ((2, 2, 0), 47.301), ((3, 1, 1), 56.120), ((4, 0, 0), 69.127),
                    ((3, 3, 1), 76.373), ((4, 2, 2), 88.026), ((5, 1, 1), 94.948), ((4, 4, 0), 106.703),
                    ((5, 3, 1), 114.086), ((6, 2, 0), 127.537), ((5, 3, 3), 136.883)]


def _raises(fn, *a, **k):
    try:
        fn(*a, **k)
    except ValueError:
        return True
    return False


def _phases():
    return {"Si": X.cubic_prototype("diamond", SRM640G_A_NM * 10, ["Si"], name="Si"),
            "NaCl": X.cubic_prototype("rocksalt", 5.6402, ["Na", "Cl"], name="NaCl"),
            "CaF2": X.cubic_prototype("fluorite", 5.4632, ["Ca", "F"], name="CaF2"),
            "Al": X.cubic_prototype("fcc", 4.0495, ["Al"], name="Al"),
            "CeO2": X.cubic_prototype("fluorite", 5.4110, ["Ce", "O"], name="CeO2"),
            "MgO": X.cubic_prototype("rocksalt", 4.2117, ["Mg", "O"], name="MgO")}


def _profile(image, geom):
    p = X.azimuthal_integrate(image, geom, polarization=0.0)
    ok = np.isfinite(p["intensity"]) & (p["count"] > 0.1 * np.nanmax(p["count"]))
    return p["two_theta"][ok], p["intensity"][ok], p["sigma"][ok]


@pytest.fixture(scope="module")
def ph():
    return _phases()


@pytest.fixture(scope="module")
def si_std(ph):
    """広がりの無い Si 標準の像(傾き 0)と、その山から測った装置の FWHM の表。"""
    im = X.debye_ring_image([ph["Si"]], [1.0], GEOM, counts=3e4, seed=4)
    x, y, s = _profile(im["image"], GEOM)
    pk = X.diffraction_peaks(x, y, noise=s)
    return {"im": im, "x": x, "y": y, "s": s, "pk": pk, "inst": (pk["two_theta"], pk["fwhm"])}


@pytest.fixture(scope="module")
def si_tilt(ph):
    return X.debye_ring_image([ph["Si"]], [1.0], GEOM_TILT, counts=3e4, seed=6)


@pytest.fixture(scope="module")
def calib(ph, si_std, si_tilt):
    """傾き 0 と 5° の Si 像の較正(何本かの門が同じ結果を使う)。"""
    d = X.powder_reflections(ph["Si"], LAM, 40.0)["d"]
    guess = {"pixel": 0.2, "wavelength": LAM}
    return {"flat": X.detector_calibrate(si_std["im"]["image"], d, guess),
            "tilt5": X.detector_calibrate(si_tilt["image"], d, guess), "d": d}


# ── 1. 散乱因子 ─────────────────────────────────────────────────────────
def test_form_factor_counts_electrons_at_zero_angle():
    for name, (Z, c) in X.FORM_FACTORS.items():
        m = re.match(r"[A-Z][a-z]?(\d*)([+-]?)$", name)
        charge = (int(m.group(1) or 1) * (1 if m.group(2) == "+" else -1)) if m.group(2) else 0
        assert X._f0(name, 0.0) == pytest.approx(Z - charge, abs=0.02), name
        f = X._f0(name, np.linspace(0, 1.5, 61))
        assert np.all(np.diff(f) < 1e-9), name


# ── 2. NIST SRM 640g ────────────────────────────────────────────────────
def test_bragg_reproduces_srm640g_table_a1():
    si = X.cubic_prototype("diamond", SRM640G_A_NM * 10, ["Si"])
    r = X.powder_reflections(si, SRM640G_LAMBDA_NM * 10, two_theta_max=140.0)
    got = {tuple(int(v) for v in h): t for h, t in zip(r["hkl"], r["two_theta"])}
    want = dict(SRM640G_TABLE_A1)
    assert set(got) == set(want), set(got) ^ set(want)          # 現れる線がちょうど 11 本
    err = max(abs(got[h] - want[h]) for h in want)
    assert err <= 0.0006, err                                    # 公表値は 0.001° 刻み
    # 格子定数の拡張不確かさ(k = 2)が 2θ に与える幅は最大でも 0.003° 程度 —— 表の丸めより大きいが、門は丸めで切る
    hi = X.powder_reflections(X.cubic_prototype("diamond", (SRM640G_A_NM + SRM640G_U_NM) * 10, ["Si"]),
                              SRM640G_LAMBDA_NM * 10, two_theta_max=140.0)
    assert 0.0005 < float(np.max(np.abs(hi["two_theta"] - r["two_theta"]))) < 0.01


# ── 3. 構造因子の閉形式 ────────────────────────────────────────────────
def test_structure_factor_closed_forms_and_extinctions():
    si = X.cubic_prototype("diamond", 5.431109, ["Si"], b_iso=0.0)
    r = X.powder_reflections(si, LAM, two_theta_max=60.0, include_extinct=True)
    F2 = {tuple(int(v) for v in h): f for h, f in zip(r["hkl"], r["F2"])}
    d = {tuple(int(v) for v in h): dd for h, dd in zip(r["hkl"], r["d"])}
    for hkl in ((2, 0, 0), (2, 2, 2), (4, 2, 0), (1, 0, 0), (1, 1, 0)):
        assert F2[hkl] < 1e-20 * F2[(1, 1, 1)], hkl
    for hkl, k in (((1, 1, 1), 32.0), ((2, 2, 0), 64.0), ((4, 0, 0), 64.0)):
        f = X._f0("Si", 0.5 / d[hkl])
        assert F2[hkl] == pytest.approx(k * f * f, rel=1e-12), hkl
    nacl = X.cubic_prototype("rocksalt", 5.6402, ["Na", "Cl"], b_iso=0.0)
    r = X.powder_reflections(nacl, LAM, two_theta_max=30.0)
    assert len(r["hkl"]) >= 10              # 30° までに 11 本(空の列で下の for を素通りさせない)
    for h, f2, dd in zip(r["hkl"], r["F2"], r["d"]):
        s = 0.5 / dd
        fa, fb = X._f0("Na", s), X._f0("Cl", s)
        want = (4 * (fa - fb)) ** 2 if h[0] % 2 else (4 * (fa + fb)) ** 2
        assert f2 == pytest.approx(want, rel=1e-12), h
    # Lorentz 因子: 環の単位立体角あたり 1/(sin θ sin 2θ) は走査型の 1/(sin² θ cos θ) の半分(同じ形)
    th = np.radians(np.linspace(5, 80, 16))
    assert np.allclose(X._lorentz(2 * np.degrees(th), "powder"), 2.0 / (np.sin(th) * np.sin(2 * th)), rtol=1e-12)
    # 六方晶の面間隔: 1/d² = 4/3 (h² + hk + k²)/a² + l²/c²
    a, c = 3.0, 5.0
    hexa = X.cif_read("data_h\n_cell_length_a 3\n_cell_length_b 3\n_cell_length_c 5\n_cell_angle_alpha 90\n"
                      "_cell_angle_beta 90\n_cell_angle_gamma 120\nloop_\n_atom_site_label\n_atom_site_fract_x\n"
                      "_atom_site_fract_y\n_atom_site_fract_z\nSi1 0 0 0\n")
    r = X.powder_reflections(hexa, 1.0, two_theta_max=80.0)
    assert len(r["hkl"]) >= 30              # 80° までに 32 本
    for h, dd in zip(r["hkl"], r["d"]):
        q = 4 / 3 * (h[0] ** 2 + h[0] * h[1] + h[1] ** 2) / a ** 2 + h[2] ** 2 / c ** 2
        assert dd == pytest.approx(1 / math.sqrt(q), rel=1e-12), h


# ── 4. CIF の読み ───────────────────────────────────────────────────────
HANDMADE_CIF = """\
# hand-written test file (not from a database)
data_rocksalt_test
_chemical_name_mineral 'rock salt'
_cell_length_a    5.6402(3)
_cell_length_b    5.6402(3)
_cell_length_c    5.6402(3)
_cell_angle_alpha 90
_cell_angle_beta  90.0
_cell_angle_gamma 90.
_publ_section_title
;
 A multi-line text field that must be skipped
 loop_ _atom_site_fract_x 9 9 9
;
loop_
_space_group_symop_operation_xyz
'x,y,z'
'x,1/2+y,1/2+z'
"1/2+x,y,1/2+z"
1/2+x,1/2+y,z
loop_
_atom_site_label
_atom_site_type_symbol
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
_atom_site_B_iso_or_equiv
Na1 Na 0 0 0 0.5      # sodium
Cl1 Cl 0.5 0.5 0.5(0) 0.5
"""


def test_cif_reader_expands_and_matches_the_prototype():
    p = X.cif_read(HANDMADE_CIF)
    assert p["name"] == "rock salt" and len(p["atoms"]) == 8
    assert sorted(a["type"] for a in p["atoms"]) == ["Cl"] * 4 + ["Na"] * 4
    r1 = X.powder_reflections(p, LAM, 40.0)
    r2 = X.powder_reflections(X.cubic_prototype("rocksalt", 5.6402, ["Na", "Cl"]), LAM, 40.0)
    assert np.array_equal(r1["hkl"], r2["hkl"])
    assert np.allclose(r1["F2"], r2["F2"], rtol=1e-12)
    R, t = X._symop("1/2+x,y-x,-z+3/4")
    assert np.allclose(R, [[1, 0, 0], [-1, 1, 0], [0, 0, -1]]) and np.allclose(t, [0.5, 0, 0.75])
    for bad in ("x,y", "x,y,q", "x,,z", "2x+,y,z"):
        assert _raises(X._symop, bad), bad
    assert _raises(X.cif_read, HANDMADE_CIF.replace("_cell_length_a    5.6402(3)", ""))
    assert _raises(X.cif_read, HANDMADE_CIF.replace("Na1 Na", "Xx1 Xx"))
    assert _raises(X.cif_read, "data_x\n_cell_length_a 1\n")
    assert _raises(X.cif_read, "Z:/no/such/file.cif")


# ── 5. 密度 ─────────────────────────────────────────────────────────────
def test_density_matches_textbook_xray_density(ph):
    for k, rho in (("Si", 2.329), ("NaCl", 2.165), ("CaF2", 3.180), ("MgO", 3.58), ("Al", 2.699)):
        assert ph[k]["density"] == pytest.approx(rho, rel=0.005), k


# ── 6. 較正 ─────────────────────────────────────────────────────────────
@pytest.mark.parametrize("which", ["flat", "tilt5"])
def test_calibration_recovers_centre_distance_tilt(calib, which):
    g = GEOM if which == "flat" else GEOM_TILT
    c = calib[which]
    assert c["ok"] and c["n_rings"] >= 8, c
    assert math.hypot(c["cx"] - g["cx"], c["cy"] - g["cy"]) < 0.05
    assert abs(c["distance"] / g["distance"] - 1) < 2e-4
    assert abs(c["tilt"] - g.get("tilt", 0.0)) < 0.05
    if which == "tilt5":
        assert abs(c["tilt_dir"] - g["tilt_dir"]) < 2.0
    assert c["rms_two_theta_deg"] < 0.25 * math.degrees(0.2 / 100.0)


# ── 7. 方位積分 → 山 → 指数付け ────────────────────────────────────────
def test_integrated_peak_positions_and_cubic_index(ph, si_tilt, calib):
    d = X.powder_reflections(ph["Si"], LAM, 40.0)
    c = calib["tilt5"]
    g = {k: c[k] for k in ("cx", "cy", "distance", "pixel", "wavelength", "tilt", "tilt_dir")}
    x, y, s = _profile(si_tilt["image"], g)
    pk = X.diffraction_peaks(x, y, noise=s)
    ix = X.cubic_index(pk["two_theta"], LAM, max_unindexed=1)
    assert ix["lattice"] == "diamond", ix["candidates"][:3]
    # ★a の門 5e-5 の余裕(組み込み時 2026-10-06 に雑音の種を 12 通りずつ振って実測): 誤差は雑音でなく較正の系統で決まり、
    # この像(傾き 5°・向き 30°)では −2.7〜−4.2e-5(種 6 は −3.2e-5)。種による散らばりは ±0.5e-5 程度で、24 通りの最大は |4.2e-5|。
    # 種は固定なので結果は決定的。門を締めると系統の偏りに当たり、緩める理由も無いので 5e-5 のまま。
    assert abs(ix["a"] / (SRM640G_A_NM * 10) - 1) < 5e-5
    assert ix["hkl"][:4].tolist() == [[1, 1, 1], [2, 2, 0], [3, 1, 1], [4, 0, 0]]
    err = np.abs(ix["two_theta"] - X._two_theta_deg(SRM640G_A_NM * 10 / np.sqrt(ix["N"]), LAM))
    assert len(ix["two_theta"]) >= 9 and float(err.max()) < 0.006, err


# ── 8 / 9. 混合物 → 分率・未知相・剥がす順 ──────────────────────────────
@pytest.fixture(scope="module")
def mixture(ph, si_std):
    W = [0.40, 0.30, 0.20, 0.10]
    g = dict(GEOM, tilt=2.0, tilt_dir=-40.0)
    im = X.debye_ring_image([ph[k] for k in ("NaCl", "CaF2", "Al", "MgO")], W, g, size=400.0, counts=3e4, seed=3)
    x, y, s = _profile(im["image"], g)
    dic = X.phase_dictionary([ph[k] for k in ("Si", "NaCl", "CaF2", "Al", "CeO2")], x, LAM, size=400.0,
                             instrumental_fwhm=si_std["inst"])
    return {"W": W, "im": im, "x": x, "y": y, "s": s, "dic": dic}


def test_mixture_fractions_and_the_unknown_phase(mixture):
    f = X.phase_fractions(mixture["x"], mixture["y"], mixture["dic"], sigma=mixture["s"])
    w = dict(zip(f["names"], f["weight_fraction"]))
    known = np.array(mixture["W"][:3]) / sum(mixture["W"][:3])
    for k, t in zip(("NaCl", "CaF2", "Al"), known):
        assert abs(w[k] - t) < 0.01, (k, w[k], t)
    assert w["Si"] < 0.005 and w["CeO2"] < 0.005
    u = X.unexplained_peaks(f, noise=mixture["s"])
    mgo = X.powder_reflections(_phases()["MgO"], LAM, 40.0)["two_theta"]
    free = u["two_theta"][~u["near_known"]]
    assert free.size >= 5 and all(np.min(np.abs(mgo - t)) < 0.03 for t in free), free
    assert u["index"]["lattice"] == "F" and abs(u["index"]["a"] / 4.2117 - 1) < 5e-4


def test_peel_selects_the_three_phases_and_stops(mixture):
    pe = X.phase_peel(mixture["x"], mixture["y"], mixture["dic"], sigma=mixture["s"])
    assert sorted(pe["order"]) == ["Al", "CaF2", "NaCl"]
    rw = [st["rwp"] for st in pe["stages"]]
    assert all(b < a for a, b in zip(rw, rw[1:])) and rw[-1] < 0.5 * rw[0]


# ── 10. Scherrer ───────────────────────────────────────────────────────
def test_scherrer_recovers_crystallite_size(ph, si_std):
    inst = si_std["inst"]
    for L in (80.0, 300.0):
        im = X.debye_ring_image([ph["CeO2"]], [1.0], GEOM, counts=3e4, size=L, seed=5)
        x, y, s = _profile(im["image"], GEOM)
        q = X.diffraction_peaks(x, y, noise=s)
        m = (q["two_theta"] > inst[0][0]) & (q["two_theta"] < inst[0][-1]) & (q["snr"] > 30)
        Ls = X.scherrer_size(q["fwhm"][m], q["two_theta"][m], LAM, instrumental_fwhm=np.interp(q["two_theta"][m], *inst))
        assert m.sum() >= 8 and abs(float(np.median(Ls)) / L - 1) < 0.05, (L, Ls)
    im = X.debye_ring_image([ph["CeO2"]], [1.0], GEOM, counts=3e4, size=800.0, seed=5)
    x, y, s = _profile(im["image"], GEOM)
    q = X.diffraction_peaks(x, y, noise=s)
    m = (q["two_theta"] > inst[0][0]) & (q["two_theta"] < inst[0][-1]) & (q["snr"] > 30)
    assert _raises(X.scherrer_size, q["fwhm"][m], q["two_theta"][m], LAM,
                   instrumental_fwhm=np.interp(q["two_theta"][m], *inst))
    assert X.scherrer_size(0.2, 30.0, 1.5406) == pytest.approx(0.9 * 1.5406 / (math.radians(0.2) * math.cos(math.radians(15))))


# ── 11. 罠: 傾きを無視する ─────────────────────────────────────────────
def test_trap_ignoring_a_5_degree_tilt_splits_the_peaks(ph, si_tilt, calib):
    x, y, s = _profile(si_tilt["image"], GEOM_TILT)
    good = X.diffraction_peaks(x, y, noise=s)
    x2, y2, s2 = _profile(si_tilt["image"], GEOM)                  # 傾き 0 と思い込む
    bad = X.diffraction_peaks(x2, y2, noise=s2)
    assert len(bad["two_theta"]) > 2 * len(good["two_theta"]), (len(bad["two_theta"]), len(good["two_theta"]))
    assert bad["fwhm"][0] > 2 * good["fwhm"][0]
    ix = X.cubic_index(bad["two_theta"], LAM, max_unindexed=1)
    assert ix["lattice"] is None or abs(ix["a"] / 5.431109 - 1) > 1e-3 or ix["lattice"] != "diamond"
    c0 = X.detector_calibrate(si_tilt["image"], calib["d"], {"pixel": 0.2, "wavelength": LAM}, fit_tilt=False)
    c1 = calib["tilt5"]
    assert not c0["ok"] and c0["rms_two_theta_deg"] > 5 * c1["rms_two_theta_deg"]


# ── 12. 罠: 参照と試料の格子のずれ ─────────────────────────────────────
def test_trap_lattice_mismatch_and_its_refinement(ph, si_std):
    W = [0.5, 0.3, 0.2]
    im = X.debye_ring_image([ph["NaCl"], ph["CaF2"], ph["Al"]], W, GEOM, size=400.0, counts=3e4, seed=7,
                            lattice_scales=[1.004, 1.0, 1.0])
    x, y, s = _profile(im["image"], GEOM)
    dic = X.phase_dictionary([ph[k] for k in ("NaCl", "CaF2", "Al")], x, LAM, size=400.0, instrumental_fwhm=si_std["inst"])
    f0 = X.phase_fractions(x, y, dic, sigma=s)
    f1 = X.phase_fractions(x, y, dic, sigma=s, lattice_tolerance=0.01)
    assert f0["weight_fraction"][0] < 0.30                      # 50 wt% が化ける
    assert np.max(np.abs(f1["weight_fraction"] - W)) < 0.01
    assert f1["lattice_scale"][0] == pytest.approx(1.004, abs=3e-4)
    assert f1["rwp"] < 0.2 * f0["rwp"]


# ── 13. 中身がある ─────────────────────────────────────────────────────
def test_outputs_are_finite_nonconstant_and_consistent(ph, mixture):
    im = mixture["im"]
    for arr in (im["image"], im["per_phase"], im["background"], mixture["y"], mixture["dic"]["matrix"]):
        assert np.all(np.isfinite(arr)) and np.ptp(arr) > 0 and arr.size > 0
    assert all(np.ptp(p_) > 0 for p_ in im["per_phase"])
    expect = im["per_phase"].sum(0) + im["background"]
    assert float(im["image"].sum() / expect.sum()) == pytest.approx(1.0, abs=2e-3)
    clean = X.debye_ring_image([ph["Si"]], [1], GEOM, counts=None)
    assert np.allclose(clean["image"], clean["per_phase"].sum(0) + clean["background"])
    m = X.detector_two_theta((16, 20), dict(GEOM, cx=10.0, cy=8.0))
    assert m["two_theta"][8, 10] == pytest.approx(0.0, abs=1e-12) and m["solid_angle"][8, 10] == pytest.approx(1.0)
    assert m["two_theta"][8, 19] == pytest.approx(math.degrees(math.atan2(9 * 0.2, 100.0)), rel=1e-12)
    assert m["solid_angle"][8, 19] == pytest.approx(math.cos(math.atan2(1.8, 100.0)) ** 3, rel=1e-12)


# ── 14. 既存 op を被験者に ─────────────────────────────────────────────
def test_existing_ops_as_subjects(si_std, ph):
    try:
        import dsp
        import match3d
    except ImportError:
        pytest.skip("worktree modules (match3d / dsp) are not importable here")
    clean = X.debye_ring_image([ph["Si"]], [1], GEOM, counts=None)["image"]
    pol = match3d.polar_unwrap(clean, center=(GEOM["cy"], GEOM["cx"]), r_in=0.0, r_out=240.0, ntheta=360, nr=961)
    rad = pol.mean(axis=0).astype(np.float64)
    r = np.linspace(0.0, 240.0, 961)
    want = GEOM["distance"] * np.tan(np.radians(X.powder_reflections(ph["Si"], LAM, 40.0)["two_theta"])) / GEOM["pixel"]
    want = want[want < 235]
    idx = dsp.find_peaks(rad, height=0.05 * rad.max())
    got = r[0] + (r[1] - r[0]) * np.asarray(dsp.peak_subbin(rad, idx, mode="parabola"))
    assert len(got) == len(want) and float(np.max(np.abs(got - want))) < 0.3, (got, want)
    # 1-D の山の位置: 自前の当てはめと dsp.peak_subbin(gauss)が 0.01° で一致
    x, y, s = _profile(clean, GEOM)
    pk = X.diffraction_peaks(x, y, noise=np.maximum(s, 1e-3))
    i = np.asarray(dsp.find_peaks(y, height=0.2 * y.max()))
    sub = np.asarray(dsp.peak_subbin(y, i, mode="gauss"))
    t_sub = np.interp(sub, np.arange(x.size), x)
    assert len(t_sub) >= 5                  # 比べる山が無ければ all() は無条件に通る
    assert all(np.min(np.abs(pk["two_theta"] - t)) < 0.01 for t in t_sub)


# ── 15. 綴り壊しと壊れた入力 ───────────────────────────────────────────
def test_spelling_and_broken_inputs_raise(ph):
    si = ph["Si"]
    img = np.ones((32, 32))
    assert _raises(X.cubic_prototype, "diamand", 5.43, ["Si"])
    assert _raises(X.cubic_prototype, "rocksalt", 5.6, ["Na"])
    assert _raises(X.cubic_prototype, "fcc", -1, ["Al"])
    assert _raises(X.cubic_prototype, "fcc", 4.0, ["Unobtainium"])
    assert _raises(X.powder_reflections, si, LAM, lorentz="aera")
    assert _raises(X.powder_reflections, si, 0.0)
    assert _raises(X.powder_reflections, si, LAM, two_theta_max=190)
    assert _raises(X.powder_reflections, {"cell": 1}, LAM)
    assert _raises(X.azimuthal_integrate, img, dict(GEOM, distanse=100))
    assert _raises(X.azimuthal_integrate, img, {k: v for k, v in GEOM.items() if k != "pixel"})
    assert _raises(X.azimuthal_integrate, img, GEOM, mask=np.zeros((31, 32), bool))
    bad = img.copy()
    bad[3, 3] = np.nan
    assert _raises(X.azimuthal_integrate, bad, GEOM)
    msk = np.zeros((32, 32), bool)
    msk[3, 3] = True
    assert np.isfinite(np.nanmax(X.azimuthal_integrate(bad, dict(GEOM, cx=16, cy=16), mask=msk)["intensity"]))
    assert _raises(X.azimuthal_integrate, img, dict(GEOM, tilt=70))
    assert _raises(X.debye_ring_image, [si], [1, 2], GEOM)
    assert _raises(X.debye_ring_image, [si], [-1], GEOM)
    assert _raises(X.debye_ring_image, [si], [1], GEOM, polarization=2)
    assert _raises(X.diffraction_peaks, [1, 2, 3], [1, 2, 3, 4])
    assert _raises(X.diffraction_peaks, np.arange(1, 10.0)[::-1], np.ones(9))
    assert _raises(X.diffraction_peaks, np.arange(1, 10.0), np.r_[np.ones(8), np.inf])
    e = X.diffraction_peaks(np.linspace(5, 30, 200), np.full(200, 7.0))
    assert e["two_theta"].size == 0                               # 平らなら山なし(空 = 失敗ではない)
    assert _raises(X.cubic_index, [10.0], LAM)
    assert _raises(X.cubic_index, [10.0, 20.0], LAM, lattices=("Q",))
    assert X.cubic_index([10.0, 10.5, 33.3], LAM)["lattice"] is None      # 立方晶に合わない山 → None(例外でなく)
    assert _raises(X.scherrer_size, 0.1, 30, 1.54, instrumental_fwhm=0.2)
    assert _raises(X.scherrer_size, 0.1, 30, 1.54, combine="voigt")
    dic = X.phase_dictionary([si], np.linspace(5, 30, 100), LAM)
    assert _raises(X.phase_fractions, np.linspace(5, 30, 101), np.ones(101), dic)
    assert _raises(X.phase_fractions, np.linspace(5, 30, 100), np.ones(100), dic, phases=["Quartz"])
    assert _raises(X.phase_fractions, np.linspace(5, 30, 100), np.ones(100), dic, lattice_tolerance=0.5)
    assert _raises(X.phase_dictionary, [si, si], np.linspace(5, 30, 100), LAM)
    assert _raises(X.phase_dictionary, [si], np.linspace(5, 30, 100), LAM, instrumental_fwhm=([1, 2], [0.1]))
    assert _raises(X.unexplained_peaks, {"two_theta": [1]})
    assert _raises(X.phase_peel, np.linspace(5, 30, 100), np.ones(100), dic, min_gain=1.5)
    assert _raises(X.detector_calibrate, img, [3.1], {"pixel": 0.2})
    assert _raises(X.detector_calibrate, np.random.default_rng(0).random((64, 64)), [3.1, 1.9],
                   {"pixel": 0.2, "wavelength": LAM, "cx": 32, "cy": 32, "distance": 50})
    assert _raises(X.detector_two_theta, (16,), GEOM)


# ── 16. 入口 ───────────────────────────────────────────────────────────
def test_entry_points_docstrings_and_no_acos():
    for name in X.__all__:
        assert hasattr(X, name), name
        obj = getattr(X, name)
        if callable(obj):
            doc = inspect.getdoc(obj) or ""
            assert len(doc) > 80, name
            assert "](" not in doc, name
    assert "](" not in (X.__doc__ or "")
    src = Path(X.__file__).read_text(encoding="utf-8")
    assert not re.search(r"\b(np\.|math\.)(arccos|arcsin|acos|asin)\(", src)
    ops = [n for n in X.__all__ if callable(getattr(X, n))]
    assert len(ops) == 14


# ── 17〜19. 実データ ───────────────────────────────────────────────────
DATA = os.environ.get("FULLSEYE_PXRD_DATA", "").strip()
needs_data = pytest.mark.skipif(not DATA or not Path(DATA).is_dir(), reason="FULLSEYE_PXRD_DATA is not set")
COD = {"9008565": ("Si", 8, 2.329), "9008678": ("NaCl", 8, 2.165), "1000032": ("Al2O3", 30, 3.987),
       "9008460": ("Al", 4, 2.699), "2300449": ("CaF2", 12, 3.180), "1000053": ("MgO", 8, 3.58),
       "4343161": ("CeO2", 12, 7.215)}


@needs_data
def test_cod_cifs_expand_and_obey_closed_forms():
    for code, (nm, n_atoms, rho) in COD.items():
        p = X.cif_read(str(Path(DATA) / "cod" / ("%s.cif" % code)), name=nm)
        assert len(p["atoms"]) == n_atoms, (code, len(p["atoms"]))
        assert p["density"] == pytest.approx(rho, rel=0.006), (code, p["density"])
        if nm == "Al2O3":
            a, _b, c = p["cell"][:3]
            r = X.powder_reflections(p, 1.5405929, 70.0)
            assert len(r["hkl"]) >= 10      # Cu Kα1 で 70° までに 13 本
            for h, dd in zip(r["hkl"], r["d"]):
                q = 4 / 3 * (h[0] ** 2 + h[0] * h[1] + h[1] ** 2) / a ** 2 + h[2] ** 2 / c ** 2
                assert dd == pytest.approx(1 / math.sqrt(q), rel=1e-10)
                assert (-h[0] + h[1] + h[2]) % 3 == 0                 # R 格子の消滅則(六方晶の設定)
            assert [tuple(int(v) for v in h) for h in r["hkl"][:5]] == [(0, 1, 2), (1, 0, 4), (1, 1, 0), (0, 0, 6), (1, 1, 3)]
        if nm == "Si":
            r = X.powder_reflections(p, LAM, 40.0, include_extinct=True)
            F2 = {tuple(int(v) for v in h): f for h, f in zip(r["hkl"], r["F2"])}
            assert F2[(2, 0, 0)] < 1e-20 * F2[(1, 1, 1)] and F2[(2, 2, 2)] < 1e-20 * F2[(1, 1, 1)]


@needs_data
def test_embedded_constants_match_their_sources():
    txt = (Path(DATA) / "ff" / "f0_WaasKirf.dat").read_text(encoding="utf-8", errors="replace").splitlines()
    seen = 0
    for i, ln in enumerate(txt):
        m = re.match(r"#S\s+(\d+)\s+(\S+)\s*$", ln)
        if m and m.group(2) in X.FORM_FACTORS:
            j = i + 1
            while txt[j].startswith("#"):
                j += 1
            Z, c = X.FORM_FACTORS[m.group(2)]
            assert Z == int(m.group(1)) and tuple(float(v) for v in txt[j].split()) == c, m.group(2)
            seen += 1
    assert seen == len(X.FORM_FACTORS)
    cert = (Path(DATA) / "nist" / "640g.txt").read_text(encoding="utf-8")
    assert re.search(r"a\s+0\.543 110 9\b", cert) and "0.000 008 0" in cert and "0.154 059 29 nm" in cert
    rows = re.findall(r"^(\d) (\d) (\d) (\d+\.\d+)", cert, re.M)
    assert [((int(a), int(b), int(c)), float(t)) for a, b, c, t in rows] == SRM640G_TABLE_A1


@needs_data
def test_mixture_with_corundum_through_the_2d_chain(si_std):
    cod = Path(DATA) / "cod"
    names = {"9008678": "NaCl", "1000032": "Al2O3", "2300449": "CaF2", "9008565": "Si"}
    P = {nm: X.cif_read(str(cod / ("%s.cif" % code)), name=nm) for code, nm in names.items()}
    W = [0.35, 0.45, 0.20]
    im = X.debye_ring_image([P["NaCl"], P["Al2O3"], P["CaF2"]], W, GEOM, size=300.0, counts=3e4, seed=11)
    x, y, s = _profile(im["image"], GEOM)
    dic = X.phase_dictionary([P[k] for k in ("NaCl", "Al2O3", "CaF2", "Si")], x, LAM, size=300.0,
                             instrumental_fwhm=si_std["inst"])
    f = X.phase_fractions(x, y, dic, sigma=s)
    assert np.max(np.abs(f["weight_fraction"][:3] - W)) < 0.015 and f["weight_fraction"][3] < 0.01
