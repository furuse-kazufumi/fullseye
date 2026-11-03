# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""光学式 3D センサの(仮想)受入試験の門 / gates of the acceptance-test family (acceptance3d, opsacceptance).

真値はどれも評価 op の外にある: 閉形式(完全な球・平面、尺度・偏りの注入)、公表値(d2(n) の表)、
別の実装(scipy.optimize.least_squares・既存の measure3d.fit_sphere3)、雑音則の式(σ_z = z²σ_d/(f b))。
"""
import math

import numpy as np
import pytest

import acceptance3d as A
import opsacceptance


def _sphere_points(n, center, radius, seed=0, cap_deg=None):
    rng = np.random.default_rng(seed)
    u = rng.normal(size=(n, 3))
    u /= np.linalg.norm(u, axis=1)[:, None]
    if cap_deg is not None:                       # 片側から見える球冠だけ / visible cap only
        keep = u[:, 2] <= -math.cos(math.radians(cap_deg))
        u = u[keep]
    return np.asarray(center, float) + radius * u, u


# --------------------------------------------------------------------------- 閉形式
def test_perfect_sphere_has_zero_probing_errors_far_from_origin():
    P, _ = _sphere_points(3000, (1250.0, -730.0, 4800.0), 12.5)
    r = A.sphere_probing_error(P, 25.0)
    assert r["pf"] < 1e-9 and abs(r["ps"]) < 1e-9
    assert np.allclose(r["center"], (1250.0, -730.0, 4800.0), atol=1e-9)
    assert r["n_excluded"] == math.floor(0.003 * 3000) == 9


def test_radial_bias_shows_only_in_size_error():
    """半径方向に b だけ外へ押した球: PS = 2b(符号つき)、PF = 0。"""
    c = np.array([0.0, 0.0, 800.0])
    P, u = _sphere_points(2000, c, 12.5)
    for b in (+0.04, -0.07):
        r = A.sphere_probing_error(c + (12.5 + b) * u, 25.0)
        assert r["ps"] == pytest.approx(2 * b, abs=1e-10)
        assert r["pf"] < 1e-9


def test_scale_error_gives_sd_equal_s_minus_1_times_L_exactly():
    """原点まわりの尺度 s: SD = (s-1)·L、PS = (s-1)·D(閉形式)。"""
    L, D = 300.0, 25.0
    ca, cb = np.array([-100.0, 60.0, 700.0]), None
    d = np.array([0.6, -0.48, 0.64])
    cb = ca + L * d
    A_, _ = _sphere_points(1500, ca, D / 2, seed=1)
    B_, _ = _sphere_points(1500, cb, D / 2, seed=2)
    for s in (1.0005, 0.998):
        r = A.sphere_spacing_error(s * A_, s * B_, L)
        assert r["sd"] == pytest.approx((s - 1) * L, abs=1e-9)
        p = A.sphere_probing_error(s * A_, D)
        assert p["ps"] == pytest.approx((s - 1) * D, abs=1e-10)


def test_fixed_diameter_option_fits_centres_only():
    L, D = 250.0, 20.0
    A_, _ = _sphere_points(800, (0, 0, 600), D / 2, seed=3, cap_deg=70)
    B_, _ = _sphere_points(800, (L, 0, 600), D / 2, seed=4, cap_deg=70)
    r = A.sphere_spacing_error(A_, B_, L, fixed_diameter=D)
    assert abs(r["sd"]) < 1e-9 and r["diameter_a"] == pytest.approx(D)


def test_flatness_of_cosine_waviness_is_two_amplitudes():
    """周期の整数倍・対称な格子の余弦のうねり(振幅 a): 最小二乗の平面は公称面に平行で F = 2a。"""
    lam, a = 40.0, 0.03
    x = np.linspace(-80.0, 80.0, 161)               # 0 と ±λ/2 を含む / contains peaks and troughs
    X, Y = np.meshgrid(x, np.linspace(-50, 50, 101))
    Z = 900.0 + a * np.cos(2 * np.pi * X / lam)
    r = A.plane_flatness_error(np.column_stack([X.ravel(), Y.ravel(), Z.ravel()]), exclude_fraction=0.0)
    assert r["f"] == pytest.approx(2 * a, rel=1e-9)
    assert abs(abs(r["normal"][2]) - 1.0) < 1e-12


def test_exclusion_removes_outliers_up_to_the_fraction_only():
    P, u = _sphere_points(1000, (0, 0, 700), 12.5, seed=5)
    Q = P.copy()
    Q[:3] += 2.0 * u[:3]                             # 半径方向に 2 mm の外れ 3 点 / 3 radial outliers
    assert A.sphere_probing_error(Q, 25.0, exclude_fraction=0.003)["pf"] < 1e-9   # floor(3.0) = 3 除外
    Q[3] += 2.0 * u[3]                               # 4 点目 → 除けない / 4th outlier stays
    assert A.sphere_probing_error(Q, 25.0, exclude_fraction=0.003)["pf"] > 1.0
    assert A.sphere_probing_error(Q, 25.0, exclude_fraction=0.0)["n_excluded"] == 0


# --------------------------------------------------------------------------- 公表値・別実装
def test_expected_range_integral_matches_published_d2():
    """d2(n) の公表値(管理図係数の表、Tippett 1925): 2 → 1.128、10 → 3.078、25 → 3.931。"""
    for n, d2 in ((2, 1.128), (10, 3.078), (25, 3.931)):
        assert A._expected_range_of_normal(n) == pytest.approx(d2, abs=6e-4)
    assert A._expected_range_of_normal(2) == pytest.approx(2 / math.sqrt(math.pi), abs=1e-9)  # 閉形式


def test_pf_under_gaussian_noise_matches_expected_range():
    """純ガウス雑音 σ・N 点: E[PF] = σ·d2(N)(当てはめの 4 自由度ぶん O(1/N) の差、3 標準誤差で)。"""
    N, sig, R = 1500, 0.02, 12.5
    d2 = A._expected_range_of_normal(N)
    pf = []
    for k in range(120):
        P, u = _sphere_points(N, (0, 0, 800), R, seed=100 + k)
        rr = np.random.default_rng(900 + k).normal(0, sig, N)
        pf.append(A.sphere_probing_error(P + u * rr[:, None], 2 * R, exclude_fraction=0.0)["pf"])
    pf = np.asarray(pf)
    se = pf.std(ddof=1) / math.sqrt(len(pf))
    assert abs(pf.mean() - sig * d2) < 3 * se + 0.002 * sig * d2


def test_geometric_fit_agrees_with_scipy_least_squares():
    """同じ目的関数(直交距離)を scipy の別の解き方で: 中心・半径が 1e-7 で一致。Kåsa とは別物。"""
    least_squares = pytest.importorskip("scipy.optimize").least_squares
    import measure3d
    P, u = _sphere_points(600, (5.0, -3.0, 650.0), 12.5, seed=7, cap_deg=60)
    P = P + u * np.random.default_rng(8).normal(0, 0.05, len(P))[:, None]
    r = A.sphere_probing_error(P, 25.0, exclude_fraction=0.0)

    def res(x):
        return np.linalg.norm(P - x[:3], axis=1) - x[3]

    k = measure3d.fit_sphere3(P)
    x0 = np.r_[np.asarray(k["center"], float), k["r"]]
    sol = least_squares(res, x0, xtol=1e-15, ftol=1e-15, gtol=1e-15)
    assert np.allclose(r["center"], sol.x[:3], atol=1e-7)
    assert r["radius"] == pytest.approx(sol.x[3], abs=1e-7)
    # 雑音のある球冠では代数解(Kåsa)と幾何解は違う —— 同じ式の写しでないことの確認
    assert abs(k["r"] - r["radius"]) > 1e-4


# --------------------------------------------------------------------------- 配置
def test_layout_places_seven_bars_and_planes_inside_the_volume():
    lay = A.acceptance_layout()
    assert len(lay["bars"]) == 7 and len(lay["planes"]) == 7 and len(lay["probe"]) == 1
    h = lay["volume_mm"] / 2
    c0 = lay["center_mm"]
    assert len(lay["bars"]) == 7
    for b in lay["bars"]:
        assert np.linalg.norm(b["center_b"] - b["center_a"]) == pytest.approx(lay["bar_length_mm"])
        assert abs(b["direction"][2]) < 0.99                  # 光軸に平行な姿勢は無い
        for c in (b["center_a"], b["center_b"]):
            assert np.all(np.abs(c - c0) + b["diameter"] / 2 <= h + 1e-9)
    assert len(lay["planes"]) == 7
    for p in lay["planes"]:
        assert p["normal"][2] < 0                              # センサ側を向く
    with pytest.raises(ValueError):
        A.acceptance_layout(bar_length_mm=600.0)
    with pytest.raises(ValueError):
        A.acceptance_layout(center_mm=(0, 0, 100.0))


# --------------------------------------------------------------------------- 仮想受入試験
@pytest.fixture(scope="module")
def layout():
    return A.acceptance_layout()


@pytest.mark.parametrize("sensor", [{"kind": "ideal"}, {"kind": "triangulation", "noise": False},
                                    {"kind": "itof", "noise": False}])
def test_noise_free_sensor_round_trip_is_zero(layout, sensor):
    """雑音も校正の誤差も無いセンサ: 場面の解析解 → 逆投影の往復だけなので全評価量 ≈ 0。"""
    r = A.virtual_acceptance_test(sensor, layout)
    for q in ("pf", "ps", "sd", "f"):
        assert max(abs(v) for v in r[q]) < 1e-6, (q, r[q])


@pytest.mark.parametrize("kind", ["ideal", "itof"])
def test_range_scale_error_is_recovered_exactly_by_sd(layout, kind):
    s = 1.0008
    r = A.virtual_acceptance_test({"kind": kind, "noise": False, "range_scale": s}, layout)
    L, D = layout["bar_length_mm"], layout["sphere_diameter_mm"]
    assert np.allclose(r["sd"], (s - 1) * L, atol=1e-6)
    assert r["ps"][0] == pytest.approx((s - 1) * D, abs=1e-6)
    assert max(r["f"]) < 1e-6 and r["pf"][0] < 1e-6


def test_triangulation_noise_law_shows_in_frontal_plane_residual(layout):
    """正対の平面(z ≈ 800 mm)の残差 rms = σ_z = z²σ_d/(f b)(3 % 以内)。"""
    S = {"kind": "triangulation", "disparity_sigma_px": 0.05, "baseline_mm": 100.0, "fx": 900.0, "fy": 900.0}
    r = A.virtual_acceptance_test(S, layout)
    front = [p for p in r["planes"] if p["name"] == "frontal"][0]
    sig = 800.0 ** 2 * 0.05 / (900.0 * 100.0)
    assert front["residual_rms"] == pytest.approx(sig, rel=0.03)


def test_itof_dark_sphere_is_shot_noise_limited(layout):
    """反射率 1 → 0.1: ショット雑音の律速なら距離の雑音は √10 ≈ 3.2 倍。PF の比が 2.3〜4.2 に入る。"""
    bright = A.virtual_acceptance_test({"kind": "itof", "sphere_reflectivity": 1.0}, layout)
    dark = A.virtual_acceptance_test({"kind": "itof", "sphere_reflectivity": 0.1}, layout)
    ratio = dark["probe"][0]["residual_rms"] / bright["probe"][0]["residual_rms"]
    assert 2.3 < ratio < 4.2
    assert dark["pf"][0] > bright["pf"][0]


def test_flying_pixels_break_probing_unless_filtered(layout):
    """縁の混合(supersample 3、雑音なし): 既存の itof_flying_pixel_mask を外すと PF が mm 級に壊れる。"""
    lay = dict(layout)
    lay["bars"], lay["planes"] = layout["bars"][:1], layout["planes"][:1]
    on = A.virtual_acceptance_test({"kind": "itof", "noise": False, "supersample": 3}, lay)
    off = A.virtual_acceptance_test({"kind": "itof", "noise": False, "supersample": 3,
                                     "flying_pixel_filter": False}, lay)
    assert on["pf"][0] < 0.1
    assert off["pf"][0] > 10.0


# --------------------------------------------------------------------------- 合否と予算
def test_verdict_takes_the_worst_absolute_value_and_names_the_deciding_quantity():
    v = A.acceptance_verdict({"pf": [0.01, 0.03], "ps": [-0.05], "sd": [0.02, -0.09, 0.04], "f": [0.02]},
                             {"pf": 0.05, "ps": 0.04, "sd": 0.1, "f": 0.05})
    assert v["by_quantity"]["sd"]["worst"] == -0.09 and v["by_quantity"]["sd"]["worst_index"] == 1
    assert v["by_quantity"]["ps"]["passed"] is False and v["passed"] is False
    assert v["decided_by"] == "ps" and v["max_ratio"] == pytest.approx(1.25)
    with pytest.raises(ValueError):
        A.acceptance_verdict({"pf": [0.1]}, {"pf": 0.0})
    with pytest.raises(ValueError):
        A.acceptance_verdict({"pf": [0.1]}, {"xx": 1.0})
    with pytest.raises(ValueError):
        A.acceptance_verdict({"pf": []}, {"pf": 1.0})


def test_error_budget_names_scale_as_decisive_for_sd(layout):
    lay = dict(layout)
    lay["planes"] = layout["planes"][:2]
    mpe = {"pf": 2.5, "ps": 0.5, "sd": 0.15, "f": 3.0}   # 雑音の PF ≈ 1.5・F ≈ 2.1 mm は通る仕様
    b = A.acceptance_error_budget({"kind": "triangulation"},
                                  {"noise": {"noise": True}, "scale": {"range_scale": 1.001}}, mpe, lay)
    for q in ("pf", "ps", "sd", "f"):
        assert abs(b["baseline"][q]) < 1e-6
    assert b["factors"]["scale"]["sd"] == pytest.approx(0.001 * layout["bar_length_mm"], abs=1e-6)
    assert b["decisive"] == ["scale"]
    assert b["ranking"][0]["factor"] == "scale" and b["ranking"][0]["quantity"] == "sd"
    assert b["all"]["verdict"]["passed"] is False
    with pytest.raises(ValueError):
        A.acceptance_error_budget({"kind": "ideal"}, {}, mpe, lay)
    with pytest.raises(ValueError):
        A.acceptance_error_budget({"kind": "ideal"}, {"x": {"no_such_key": 1}}, mpe, lay)


# --------------------------------------------------------------------------- fail-closed
@pytest.mark.parametrize("bad", [np.zeros((5, 3)), np.zeros((20, 2)), np.full((20, 3), np.nan), "xyz", None])
def test_probing_rejects_bad_points(bad):
    with pytest.raises(ValueError):
        A.sphere_probing_error(bad, 25.0)


def test_coplanar_points_are_not_a_sphere_and_collinear_not_a_plane():
    x = np.linspace(0, 10, 30)
    with pytest.raises(ValueError):
        A.sphere_probing_error(np.column_stack([x, x ** 2, np.zeros_like(x)]), 25.0)
    with pytest.raises(ValueError):
        A.plane_flatness_error(np.column_stack([x, 2 * x, 3 * x]))


@pytest.mark.parametrize("bad", [{"kind": "lidar"}, {"kind": "ideal", "nope": 1}, {"kind": "ideal", "fx": -1.0},
                                 {"kind": "itof", "frequency_hz": 200e6}, {"kind": "itof", "supersample": 0},
                                 {"kind": "ideal", "noise": 1}, "ideal", {}, {"shape": (120, 160)}])
def test_sensor_table_is_fail_closed(layout, bad):
    with pytest.raises(ValueError):
        A.acceptance_scan(bad, layout["probe"][0])


def test_artifact_outside_the_field_of_view_is_rejected():
    with pytest.raises(ValueError):
        A.acceptance_scan({"kind": "ideal"}, {"center": (5000.0, 0.0, 800.0), "diameter": 25.0})


# --------------------------------------------------------------------------- 台帳
def test_ledger_is_complete_and_declares_existing_sorts():
    assert opsacceptance.missing() == []
    assert sorted(opsacceptance.list_ops()) == sorted([
        "acceptance_layout", "sphere_probing_error", "sphere_spacing_error", "plane_flatness_error",
        "acceptance_verdict", "acceptance_scan", "virtual_acceptance_test", "acceptance_error_budget"])
    sorts = {s for m in opsacceptance.OPSACCEPTANCE.values() for s in m["in"] + [m["out"]]}
    assert sorts <= {"points", "table"}


def test_ledger_docstring_example_runs():
    """opsacceptance の呼び出し例の数字(0.3144 mm、L = 314.4 mm)。"""
    import fullseye as fs
    layout = fs.ledger.acceptance_layout()
    ideal = fs.ledger.virtual_acceptance_test({"kind": "ideal"}, layout)
    assert max(abs(v) for v in ideal["sd"]) < 1e-6
    scaled = fs.ledger.virtual_acceptance_test({"kind": "ideal", "range_scale": 1.001}, layout)
    assert "%.4f" % scaled["sd"][0] == "0.3144" and "%.1f" % layout["bar_length_mm"] == "314.4"
