# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""光弾性の族(photoelastic)の真値の門。

* 応力場: 円板の直径圧縮と Kirsch の閉形式を、境界条件・中心値・力の釣り合い・
  平衡方程式(差分)という**式とは独立の条件**で確かめる。
* 偏光器: 閉形式の強度 = ``optics.mueller_element`` の素子で組んだ Mueller の鎖。
* 合成 → 推定: 位相差と主軸、そして応力の場から主応力差まで戻る。
* 立方晶: 4 階テンソルを回す実装 = Stoehr ら(2020)式 (26) を書き写した閉形式。
* 単位: rad と nm の取り違え、mm / nm を m に、×10⁻⁷ MPa⁻¹ を Pa⁻¹ に渡す誤りを拒否する。
"""
import math
import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import optics  # noqa: E402
import photoelastic as P  # noqa: E402

R, T, LOAD = 0.025, 0.006, 500.0


# --------------------------------------------------------------------------- #
# 円板の直径圧縮
# --------------------------------------------------------------------------- #

def test_disc_rim_is_traction_free_except_at_the_load_points():
    phi = np.linspace(0.0, 2.0 * np.pi, 1441)[:-1]
    phi = phi[np.abs(np.cos(phi)) > 1e-3]                      # 荷重点 (0, ±R) を除く
    d = P.brazilian_disc_stress(R, T, LOAD, x=R * np.cos(phi), y=R * np.sin(phi))
    nx, ny = np.cos(phi), np.sin(phi)
    tx = d["sxx"] * nx + d["txy"] * ny
    ty = d["txy"] * nx + d["syy"] * ny
    scale = abs(d["centre_syy"])
    assert np.max(np.hypot(tx, ty)) < 1e-9 * scale


def test_disc_centre_and_force_balance():
    c = P.brazilian_disc_stress(R, T, LOAD, x=0.0, y=0.0)
    d_diam = 2 * R
    assert float(c["sxx"]) == pytest.approx(2 * LOAD / (math.pi * d_diam * T), rel=1e-12)
    assert float(c["syy"]) == pytest.approx(-6 * LOAD / (math.pi * d_diam * T), rel=1e-12)
    assert abs(float(c["txy"])) < 1e-6
    # 水平直径上の σy を積分すると −P/t(区間 [−R, R] を台形則で)
    x = np.linspace(-R, R, 40001)
    syy = P.brazilian_disc_stress(R, T, LOAD, x=x, y=np.zeros_like(x))["syy"]
    assert np.trapezoid(syy, x) * T == pytest.approx(-LOAD, rel=1e-6)
    # 荷重の通る鉛直直径の上では σx が一様な引張 2P/(πDt)(割裂試験が引張強度を測れる理由)
    y = np.linspace(-0.99 * R, 0.99 * R, 2001)
    sxx = P.brazilian_disc_stress(R, T, LOAD, x=np.zeros_like(y), y=y)["sxx"]
    assert np.allclose(sxx, 2 * LOAD / (math.pi * d_diam * T), rtol=1e-12)


def _divergence(fn, x, y, h):
    """平衡方程式 ∂σx/∂x + ∂τ/∂y, ∂τ/∂x + ∂σy/∂y を中心差分で。"""
    def at(dx, dy):
        return fn(x + dx, y + dy)
    px, mx, py, my = at(h, 0), at(-h, 0), at(0, h), at(0, -h)
    fx = (px["sxx"] - mx["sxx"]) / (2 * h) + (py["txy"] - my["txy"]) / (2 * h)
    fy = (px["txy"] - mx["txy"]) / (2 * h) + (py["syy"] - my["syy"]) / (2 * h)
    return fx, fy


def test_disc_and_kirsch_satisfy_equilibrium():
    rng = np.random.default_rng(3)
    rr = 0.7 * R * np.sqrt(rng.random(200))
    th = rng.uniform(0, 2 * np.pi, 200)
    x, y = rr * np.cos(th), rr * np.sin(th)
    h = 1e-6
    fx, fy = _divergence(lambda a, b: P.brazilian_disc_stress(R, T, LOAD, x=a, y=b), x, y, h)
    grad_scale = abs(2 * LOAD / (math.pi * 2 * R * T)) / R
    assert np.max(np.abs(fx)) < 1e-5 * grad_scale and np.max(np.abs(fy)) < 1e-5 * grad_scale
    a = 0.004
    rr = a * (1.2 + 3.0 * rng.random(200))
    x, y = rr * np.cos(th), rr * np.sin(th)
    fx, fy = _divergence(lambda u, v: P.kirsch_plate_stress(a, 1e6, 25.0, x=u, y=v), x, y, 1e-8)
    assert np.max(np.abs(fx)) < 1e-4 * 1e6 / a and np.max(np.abs(fy)) < 1e-4 * 1e6 / a


def test_disc_grid_masks_the_rim_and_load_points():
    g = P.brazilian_disc_stress(R, T, LOAD, size=65)
    assert g["sxx"].shape == (65, 65)
    assert not g["inside"][0, 32] and not g["inside"][64, 32]   # 荷重点
    assert np.all(g["sxx"][~g["inside"]] == 0.0)
    assert np.isfinite(g["syy"]).all()
    c = g["syy"][32, 32]
    assert c == pytest.approx(g["centre_syy"], rel=1e-12)


# --------------------------------------------------------------------------- #
# Kirsch
# --------------------------------------------------------------------------- #

def test_kirsch_hole_edge_and_far_field():
    a, s, alpha = 0.005, 2.0e6, 30.0
    th = np.linspace(0.0, 2 * np.pi, 721)
    k = P.kirsch_plate_stress(a, s, alpha, x=a * np.cos(th), y=a * np.sin(th))
    assert np.max(np.abs(k["srr"])) < 1e-9 * s
    assert np.max(np.abs(k["trt"])) < 1e-9 * s
    rel = th - math.radians(alpha)
    assert np.allclose(k["stt"], s * (1 - 2 * np.cos(2 * rel)), atol=1e-9 * s)
    assert k["stt"].max() == pytest.approx(3 * s, rel=1e-6)
    assert k["stt"].min() == pytest.approx(-s, rel=1e-6)
    far = P.kirsch_plate_stress(a, s, alpha, x=1e3 * np.cos(th), y=1e3 * np.sin(th))
    al = math.radians(alpha)
    assert np.allclose(far["sxx"], s * math.cos(al) ** 2, atol=1e-8 * s)
    assert np.allclose(far["syy"], s * math.sin(al) ** 2, atol=1e-8 * s)
    assert np.allclose(far["txy"], s * math.sin(al) * math.cos(al), atol=1e-8 * s)


def test_kirsch_refuses_points_in_the_hole():
    with pytest.raises(ValueError, match="inside the hole"):
        P.kirsch_plate_stress(0.005, 1e6, x=[0.001], y=[0.0])


# --------------------------------------------------------------------------- #
# 主応力
# --------------------------------------------------------------------------- #

def test_principal_stress_rotates_back_to_the_tensor():
    rng = np.random.default_rng(4)
    sx, sy, t = rng.normal(0, 1e6, (3, 100))
    p = P.principal_stress(sx, sy, t)
    a = np.radians(p["angle_deg"])
    c, s = np.cos(a), np.sin(a)
    assert np.allclose(p["s1"] * c * c + p["s2"] * s * s, sx, atol=1e-6)
    assert np.allclose(p["s1"] * s * s + p["s2"] * c * c, sy, atol=1e-6)
    assert np.allclose((p["s1"] - p["s2"]) * s * c, t, atol=1e-6)
    assert np.all(p["difference"] >= 0) and np.all((p["angle_deg"] > -90) & (p["angle_deg"] <= 90))
    iso = P.principal_stress(1.0, 1.0, 0.0)
    assert bool(iso["isotropic"]) and float(iso["angle_deg"]) == 0.0


# --------------------------------------------------------------------------- #
# 応力光学則と単位
# --------------------------------------------------------------------------- #

def test_stress_optic_law_numbers_and_units():
    # 主応力差 4 MPa、C = 5e-11 Pa^-1、厚さ 6 mm、波長 550 nm
    out = P.photoelastic_retardation(4.0e6, 0.006, 5e-11, 5.5e-7)
    r_nm = 0.006 * 5e-11 * 4.0e6 * 1e9                              # = 1200 nm
    assert float(out["retardation_nm"]) == pytest.approx(r_nm, rel=1e-12)
    assert float(out["delta_rad"]) == pytest.approx(2 * math.pi * r_nm / 550.0, rel=1e-12)
    assert float(out["fringe_order"]) == pytest.approx(r_nm / 550.0, rel=1e-12)
    assert out["fringe_value_n_per_m"] == pytest.approx(5.5e-7 / 5e-11, rel=1e-12)
    # 縞値の式 N = t Δσ / f_σ と同じ
    assert float(out["fringe_order"]) == pytest.approx(0.006 * 4e6 / out["fringe_value_n_per_m"], rel=1e-12)
    # rad ↔ nm の換算は波長を介してだけつながる
    back = P.retardation_convert(float(out["delta_rad"]), "rad", "nm", 550.0)
    assert back == pytest.approx(r_nm, rel=1e-12)
    assert P.retardation_convert(1.0, "waves", "deg", 633.0) == pytest.approx(360.0)
    assert P.retardation_convert(633.0, "nm", "rad", 633.0) == pytest.approx(2 * math.pi)


@pytest.mark.parametrize("kwargs, msg", [
    ({"thickness_m": 6.0}, "thickness_m"),            # mm を m に
    ({"wavelength_m": 550.0}, "wavelength_m"),         # nm を m に
    ({"stress_optic_coefficient": 50.0}, "stress_optic_coefficient"),   # brewster を Pa^-1 に
])
def test_unit_slips_are_refused(kwargs, msg):
    base = {"thickness_m": 0.006, "stress_optic_coefficient": 5e-11, "wavelength_m": 5.5e-7}
    base.update(kwargs)
    with pytest.raises(ValueError, match=msg):
        P.photoelastic_retardation(4e6, **base)


def test_nm_passed_as_rad_is_refused_and_wavelength_in_metres_is_refused():
    r_nm = np.full((4, 4), 1500.0 * 550.0 / 550.0 * 1000.0)          # 1.5 mm の位相差 = nm を rad と取り違えた量
    with pytest.raises(ValueError, match="retardation in nm"):
        P.polariscope_intensity(r_nm)
    with pytest.raises(ValueError, match="nanometres"):
        P.retardation_convert(1.0, "rad", "nm", 5.5e-7)
    with pytest.raises(ValueError, match="unit"):
        P.retardation_convert(1.0, "radian", "nm", 550.0)


# --------------------------------------------------------------------------- #
# 偏光器: 閉形式 = Mueller の鎖
# --------------------------------------------------------------------------- #

def _chain(mats, s_in):
    s = np.asarray(s_in, float)
    for m in mats:
        s = np.asarray(m) @ s
    return float(s[0])


def test_polariscope_closed_forms_equal_the_mueller_chain():
    worst = 0.0
    pol = lambda a: optics.mueller_element("polarizer", a)               # noqa: E731
    qwp = lambda a: optics.mueller_element("quarter_wave", a)            # noqa: E731
    for d_deg in range(0, 721, 30):
        for th in (0.0, 13.0, 45.0, 71.0, -30.0):
            for beta in (0.0, 22.5, 60.0):
                ret = optics.mueller_element("retarder", th, float(d_deg))
                b = math.radians(beta)
                s_lin = [1.0, math.cos(2 * b), math.sin(2 * b), 0.0]       # 第 1 偏光子を出た光(強度 1)
                d = math.radians(d_deg)
                cases = {
                    "plane_dark": _chain([ret, pol(beta + 90.0)], s_lin),
                    "plane_bright": _chain([ret, pol(beta)], s_lin),
                    "circular_dark": _chain([qwp(beta + 45.0), ret, qwp(beta - 45.0), pol(beta + 90.0)], s_lin),
                    "circular_bright": _chain([qwp(beta + 45.0), ret, qwp(beta - 45.0), pol(beta)], s_lin),
                }
                for setup, ref in cases.items():
                    got = float(P.polariscope_intensity(d, th, setup, beta))
                    if setup == "plane_dark":            # 既定の setup は直交平面偏光器
                        assert float(P.polariscope_intensity(d, th, polarizer_deg=beta)) == got
                    worst = max(worst, abs(got - ref))
    assert worst < 1e-12, worst


def test_polarization_images_match_mueller_chain_and_circular_dark():
    rng = np.random.default_rng(5)
    d = rng.uniform(0, 4 * np.pi, (6, 7))
    th = rng.uniform(-90, 90, (6, 7))
    im = P.photoelastic_polarization_images(d, th, "stokes6", intensity=2.0)
    assert im.shape == (6, 6, 7)
    i, j = 2, 3
    ret = optics.mueller_element("retarder", float(th[i, j]), math.degrees(float(d[i, j])))
    s = ret @ np.array([2.0, 0.0, 0.0, 2.0])
    for k, a in enumerate((0.0, 45.0, 90.0, 135.0)):
        assert im[k, i, j] == pytest.approx(float((optics.mueller_element("polarizer", a) @ s)[0]), abs=1e-12)
    # 左回り円の検光子 = 暗視野の円偏光器
    assert np.allclose(im[5], P.polariscope_intensity(d, th, "circular_dark", intensity=2.0), atol=1e-12)


# --------------------------------------------------------------------------- #
# 合成 → 推定
# --------------------------------------------------------------------------- #

def test_camera4_inverse_recovers_quarter_wave_range():
    rng = np.random.default_rng(6)
    d = rng.uniform(0.05, np.pi / 2 - 0.05, (30, 30))
    th = rng.uniform(-89.9, 90.0, (30, 30))
    e = P.photoelastic_phase_estimate(P.photoelastic_polarization_images(d, th, "camera4"))
    assert np.max(np.abs(e["delta_rad"] - d)) < 1e-9
    assert np.max(np.abs((e["axis_deg"] - th + 90.0) % 180.0 - 90.0)) < 1e-9
    assert e["axis_valid"].all()
    # 4 方位だけでは δ と π − δ が区別できない(cos δ の符号が見えない)
    e2 = P.photoelastic_phase_estimate(P.photoelastic_polarization_images(np.pi - d, th, "camera4"))
    assert np.allclose(e2["delta_rad"], d, atol=1e-9)
    # 変調が min_modulation 以下では主軸を返さない(0 と印)
    e3 = P.photoelastic_phase_estimate(P.photoelastic_polarization_images(np.full((3, 3), 0.005), 30.0))
    assert not e3["axis_valid"].any() and np.all(e3["axis_deg"] == 0.0)
    e4 = P.photoelastic_phase_estimate(P.photoelastic_polarization_images(np.full((3, 3), 0.005), 30.0),
                                       min_modulation=0.001)
    assert e4["axis_valid"].all() and np.allclose(e4["axis_deg"], 30.0)


def test_stokes6_inverse_recovers_half_wave_range_and_the_two_fold_ambiguity():
    rng = np.random.default_rng(7)
    d = rng.uniform(0.05, np.pi - 0.05, (30, 30))
    th = rng.uniform(-89.9, 90.0, (30, 30))
    e = P.photoelastic_phase_estimate(P.photoelastic_polarization_images(d, th, "stokes6"), "stokes6")
    assert np.max(np.abs(e["delta_rad"] - d)) < 1e-9
    assert np.max(np.abs((e["axis_deg"] - th + 90.0) % 180.0 - 90.0)) < 1e-9
    # (δ, θ) と (−δ, θ+90°) は同じ像
    im_a = P.photoelastic_polarization_images(d, th, "stokes6")
    im_b = P.photoelastic_polarization_images(-d, th + 90.0, "stokes6")
    assert np.allclose(im_a, im_b, atol=1e-12)


def test_stress_field_to_images_and_back_to_principal_stress_difference():
    """円板の応力 → 主応力差 → δ → 6 強度の像 → δ・主軸 → 主応力差(1e-6)。"""
    g = P.brazilian_disc_stress(R, T, LOAD, size=129)
    p = P.principal_stress(g["sxx"], g["syy"], g["txy"])
    c, lam = 5e-11, 5.5e-7
    ret = P.photoelastic_retardation(p["difference"], T, c, lam)
    delta = ret["delta_rad"]
    m = g["inside"] & (delta > 0.05) & (delta < np.pi - 0.05)
    assert m.sum() > 1000                              # 巻いていない領域が十分ある
    im = P.photoelastic_polarization_images(delta, p["angle_deg"], "stokes6")
    e = P.photoelastic_phase_estimate(im, "stokes6")
    ds = e["delta_rad"] * lam / (2 * np.pi * T * c)
    assert np.max(np.abs(ds[m] - p["difference"][m]) / p["difference"][m]) < 1e-6
    ang = (e["axis_deg"] - p["angle_deg"] + 90.0) % 180.0 - 90.0
    assert np.max(np.abs(ang[m])) < 1e-6


def test_phase_estimate_takes_the_demosaic_order_and_refuses_bad_frames():
    d = np.full((4, 4), 0.5)
    im = P.photoelastic_polarization_images(d, 10.0)
    e = P.photoelastic_phase_estimate([f for f in im])        # list でも (4,H,W) でも
    assert np.allclose(e["delta_rad"], 0.5)
    with pytest.raises(ValueError, match="frames"):
        P.photoelastic_phase_estimate(im[:3])
    swapped = im[[0, 2, 1, 3]]                                  # 0/90/45/135 の順に並べ替えた
    swapped[1] *= 1.3
    with pytest.raises(ValueError, match="not one exposure"):
        P.photoelastic_phase_estimate(swapped)
    with pytest.raises(ValueError, match="dark"):
        P.photoelastic_phase_estimate(np.zeros((4, 3, 3)))


# --------------------------------------------------------------------------- #
# 立方晶 {100} 面
# --------------------------------------------------------------------------- #

def _eq26(sx, sy, t, a, p44, n, phi_deg):
    """Stoehr ら(2020)式 (26) の書き写し(テンソルを回さない独立の経路)。"""
    d = sx - sy
    f = math.radians(phi_deg)
    b = 2 * (a * a + p44 * p44) * (4 * t * t + d * d)
    c = 2 * (a * a - p44 * p44)
    dd = (-4 * t * t + d * d) * math.cos(4 * f) + 4 * t * d * math.sin(4 * f)
    return n ** 3 / 4 * np.sqrt(b + c * dd)


@pytest.mark.parametrize("phi", [0.0, 13.0, 22.5, 45.0, 77.0, -30.0])
def test_cubic_tensor_rotation_equals_eq26(phi):
    rng = np.random.default_rng(8)
    sx, sy, t = rng.normal(0, 3e7, (3, 200))
    co = P.silicon_piezo_optic_coefficients("stoehr2020")
    r = P.cubic_photoelastic_birefringence(sx, sy, t, co["pi11_minus_pi12"], co["pi44"], 3.5, phi)
    ref = _eq26(sx, sy, t, co["pi11_minus_pi12"], co["pi44"], 3.5, phi)
    assert np.max(np.abs(r["delta_n"] / ref - 1.0)) < 1e-12


def test_cubic_reduces_to_isotropic_when_pi44_equals_pi11_minus_pi12():
    rng = np.random.default_rng(9)
    sx, sy, t = rng.normal(0, 3e7, (3, 200))
    a, n = 1.44e-12, 3.5
    p = P.principal_stress(sx, sy, t)
    for phi in (0.0, 31.0):
        r = P.cubic_photoelastic_birefringence(sx, sy, t, a, a, n, phi)
        assert np.allclose(r["delta_n"], 0.5 * n ** 3 * a * p["difference"], rtol=1e-12)
        assert np.allclose(r["effective_coefficient"], r["isotropic_coefficient"], rtol=1e-12)
        # π11 − π12 > 0 なら屈折率の大きい向き(遅相軸)は σ2 = σ1 に直交
        assert np.allclose((r["slow_axis_deg"] - p["angle_deg"]) % 180.0, 90.0, atol=1e-9)


def test_cubic_anisotropy_depends_on_crystal_orientation():
    """純粋なせん断 τ だけ: φ = 0 では π44 が、φ = 45° では π11 − π12 が効く。"""
    co = P.silicon_piezo_optic_coefficients("stoehr2020")
    a, p44, n, tau = co["pi11_minus_pi12"], co["pi44"], 3.5, 1e7
    r0 = P.cubic_photoelastic_birefringence(0.0, 0.0, tau, a, p44, n, 0.0)
    r45 = P.cubic_photoelastic_birefringence(0.0, 0.0, tau, a, p44, n, 45.0)
    assert float(r0["delta_n"]) == pytest.approx(n ** 3 * abs(p44) * tau, rel=1e-12)
    assert float(r45["delta_n"]) == pytest.approx(n ** 3 * abs(a) * tau, rel=1e-12)
    assert float(r45["delta_n"]) / float(r0["delta_n"]) == pytest.approx(14.4 / 9.4, rel=1e-12)


def test_silicon_table_is_the_published_table_and_unit_slips_are_refused():
    rows = P.silicon_piezo_optic_coefficients("all")
    # Stoehr et al. 2020, JSSS 9:209, Table 1(×1e-7 MPa^-1 = ×1e-13 Pa^-1)
    expect = {"stoehr2020": (14.4, 9.4), "he2004": (9.9, 6.5), "liang1992": (-12.2, 6.5),
              "zheng_danyluk2002": (-12.2, -6.5), "giardini1958": (-14.4, -5.0)}
    assert set(rows) == set(expect)
    for k, (a, b) in expect.items():
        assert rows[k]["pi11_minus_pi12"] == pytest.approx(a * 1e-13, rel=1e-12)
        assert rows[k]["pi44"] == pytest.approx(b * 1e-13, rel=1e-12)
        assert rows[k]["doi"] == "10.5194/jsss-9-209-2020"
    with pytest.raises(ValueError, match="source"):
        P.silicon_piezo_optic_coefficients("unknown")
    with pytest.raises(ValueError, match="Pa\\^-1"):                     # 表の数字 14.4 をそのまま
        P.cubic_photoelastic_birefringence(1e7, 0.0, 0.0, 14.4, 9.4, 3.5)
    with pytest.raises(ValueError, match="Pa\\^-1"):                     # MPa^-1 の値を Pa^-1 に
        P.cubic_photoelastic_birefringence(1e7, 0.0, 0.0, 14.4e-7, 9.4e-7, 3.5)


# --------------------------------------------------------------------------- #
# 多波長の次数決定
# --------------------------------------------------------------------------- #

def _folded(ret_nm, lam):
    p = np.mod(2 * np.pi * ret_nm / lam, 2 * np.pi)
    return np.minimum(p, 2 * np.pi - p)


def test_multiwavelength_resolves_orders_beyond_one_wave():
    rng = np.random.default_rng(10)
    ret = rng.uniform(0.0, 3000.0, (40, 40))
    lams = [450.0, 532.0, 633.0]
    u = P.retardation_unwrap_multiwavelength([_folded(ret, l) for l in lams], lams, 3000.0)
    assert np.max(np.abs(u["retardation_nm"] - ret)) < 1e-6
    assert np.allclose(u["delta_rad"], 2 * np.pi * ret / 450.0, atol=1e-8)
    assert np.max(u["residual_nm"]) < 1e-6
    assert np.min(u["margin_nm"]) > 0.5                 # 3 波長なら 3000 nm まで一意
    two = P.retardation_unwrap_multiwavelength([_folded(ret, l) for l in lams[1:]], lams[1:], 3000.0)
    assert np.min(two["margin_nm"]) < np.min(u["margin_nm"])   # 2 波長は余裕が小さい(曖昧に近い)
    # 巻いた [0, 2π) の位相でも
    w = [np.mod(2 * np.pi * ret / l, 2 * np.pi) for l in lams]
    u2 = P.retardation_unwrap_multiwavelength(w, lams, 3000.0, folded=False)
    assert np.max(np.abs(u2["retardation_nm"] - ret)) < 1e-6


def test_multiwavelength_refuses_bad_inputs():
    ph = [np.zeros((3, 3)), np.zeros((3, 3))]
    with pytest.raises(ValueError, match="distinct"):
        P.retardation_unwrap_multiwavelength(ph, [532.0, 532.0], 1000.0)
    with pytest.raises(ValueError, match="nanometres"):
        P.retardation_unwrap_multiwavelength(ph, [5.32e-7, 6.33e-7], 1000.0)
    with pytest.raises(ValueError, match="outside"):
        P.retardation_unwrap_multiwavelength([np.full((3, 3), 4.0), ph[1]], [532.0, 633.0], 1000.0)
    with pytest.raises(ValueError, match=">= 2"):
        P.retardation_unwrap_multiwavelength([ph[0]], [532.0], 1000.0)


# --------------------------------------------------------------------------- #
# fail-closed
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("call", [
    lambda: P.principal_stress([], [], []),
    lambda: P.principal_stress([np.nan], [0.0], [0.0]),
    lambda: P.principal_stress([1j], [0.0], [0.0]),
    lambda: P.brazilian_disc_stress(R, T, LOAD, x=[R * 1.01], y=[0.0]),
    lambda: P.brazilian_disc_stress(R, T, LOAD, x=[0.0], y=[R]),
    lambda: P.brazilian_disc_stress(R, T, LOAD, x=[0.0]),
    lambda: P.brazilian_disc_stress(R, T, -1.0),
    lambda: P.brazilian_disc_stress(R, T, LOAD, size=4),
    lambda: P.kirsch_plate_stress(0.01, 1e6, half_width_m=0.01),
    lambda: P.retardation_from_birefringence(0.5, 0.006, 5.5e-7),
    lambda: P.polariscope_intensity(1.0, setup="crossed"),
    lambda: P.photoelastic_polarization_images(np.ones(5), 0.0),
    lambda: P.photoelastic_phase_estimate(-np.ones((4, 3, 3))),
    lambda: P.cubic_photoelastic_birefringence(1e7, 0.0, 0.0, 1.44e-12, 9.4e-13, 0.5),
])
def test_degenerate_inputs_raise_value_error(call):
    with pytest.raises(ValueError):
        call()


def test_registry_lists_the_family():
    import opsoptics
    names = opsoptics.list_ops("photoelastic")
    assert len(names) == 12
    assert not [n for n in names if opsoptics.get(n) is None]
    assert set(names) == set(P.__all__)
