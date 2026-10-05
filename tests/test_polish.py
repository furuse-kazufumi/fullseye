# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""polish の門(研削・研磨・拭き取りを画像で測る: Preston の式・接触圧の閉形式・帯の幅・面積・弾性床・MuJoCo)。

numpy だけの門(常に走る):
 1. 圧力の窓: 平板は一様 F/(πa²)、Hertz は p0 √(1 − r²/a²)(tacsim の hertz_sphere)、正規化で Σ p res² = F
 2. 一筆の断面: 直接の積分 = 閉形式(平板・Hertz・回る平板)、体積 / 長さ = k_p F
 3. 二つの実装: 直接の積分 = FFT の畳み込み(弧の軌跡)
 4. 回る平板の閉形式: ω → 0 で回らない式に戻る、b = 0(相対速度が 0 になる線)で有限、進む側と戻る側の非対称の向き
 5. 帯の幅: 閉形式の両端(F_min で 0、力が大きいと 2a)、画像の読みと一致
 6. 平行な一筆の面積: s ≥ 2a で N 本の和、s → 0 で 1 本、lens の値(atan2)
 7. 膜の画像の往復、wipe_coverage のしきい値が意味する残膜
 8. 高さ図から深さ(傾きと高さの載せ直し)と Preston 係数
 9. 弾性床: 全面が当たる間 rms ∝ exp(−c t)、平均の下がり k_p p̄ v t
10. 綴り壊しは ValueError、MJCF の部品
mujoco が要る門(無ければ skip):
11. 柔らかい手首の押し付けの法線力 = m g + k Δ、接線力 / 法線力 = μ
"""
from __future__ import annotations

import math

import numpy as np
import pytest

import polish as S

A, R_B, E_B = 8.0e-3, 0.05, 2.0e6
K = math.pi * A * 1e-6 / 4.0
LINE = np.array([[-0.03, 0.0], [0.03, 0.0]])


def _raises(fn, exc=ValueError):
    try:
        fn()
    except exc:
        return True
    return False


def test_pressure_kernel_closed_forms():
    import tacsim
    ker = S.preston_pressure_kernel(10.0, A, 2e-4)
    assert abs(ker.max() - 10.0 / (math.pi * A * A)) < 1e-9 * ker.max()
    kh = S.preston_pressure_kernel(10.0, R_B, 2e-4, kind="hertz", estar=E_B)
    h = tacsim.hertz_sphere(10.0, R_B, E_B)
    assert abs(kh.max() - h["p0"]) < 1e-12 * h["p0"]                    # 中心の画素 = p0
    for k_ in (ker, S.preston_pressure_kernel(10.0, A, 2e-4, normalize=True)):
        assert k_.shape[0] % 2 == 1 and k_.shape == k_.shape[::-1]
    kn = S.preston_pressure_kernel(10.0, R_B, 2e-4, kind="hertz", estar=E_B, normalize=True)
    assert abs(kn.sum() * 4e-8 - 10.0) < 1e-12


@pytest.mark.parametrize("kind,R,es,kw", [("flat", A, None, {}), ("hertz", R_B, E_B, {}), ("flat", A, None, {"spin": 60.0})])
def test_track_profile_matches_direct_integral(kind, R, es, kw):
    H, W, res = 201, 41, 1e-4
    m = S.preston_removal_map(LINE, 10.0, R, 1e-12, shape=(H, W), res=res, kind=kind, speed=1e-3, estar=es, **kw)
    y = ((H - 1) / 2.0 - np.arange(H)) * res
    th = S.preston_track_profile(y, 10.0, R, 1e-12, kind=kind, speed=1e-3, estar=es, **kw)
    assert np.max(np.abs(m[:, W // 2] - th)) < 0.005 * th.max()
    if not kw:
        assert abs(m[:, W // 2].sum() * res / (1e-12 * 10.0) - 1) < 1e-3       # 体積 / 長さ = k_p F


def test_two_implementations_agree_on_an_arc():
    arc = np.array([[0.01 * math.cos(t), 0.005 * math.sin(t)] for t in np.linspace(0, 4, 40)])
    for kind, R, es in (("flat", A, None), ("hertz", R_B, E_B)):
        md = S.preston_removal_map(arc, 5.0, R, K, shape=(81, 141), res=2e-4, kind=kind, speed=1e-2, estar=es, step=1e-4)
        mf = S.preston_removal_map(arc, 5.0, R, K, shape=(81, 141), res=2e-4, kind=kind, speed=1e-2, estar=es, method="fft")
        assert np.sqrt(np.mean((md - mf) ** 2)) < 0.01 * md.max()
        assert abs(md.sum() / mf.sum() - 1) < 2e-3


def test_spinning_profile_limits_and_asymmetry():
    y = np.linspace(-0.0079, 0.0079, 41)
    still = S.preston_track_profile(y, 10.0, A, 1e-12)
    slow = S.preston_track_profile(y, 10.0, A, 1e-12, spin=1e-6, speed=1e-3)
    assert np.max(np.abs(slow - still)) < 2e-5 * still.max()          # 1 次の差 ω a / v = 8e-6
    om, v = 60.0, 0.12                                       # b = v − ω y = 0 の線 y = 2 mm が中にある
    yy = np.array([v / om])
    val = S.preston_track_profile(yy, 10.0, A, 1e-12, spin=om, speed=v)
    assert np.all(np.isfinite(val)) and val[0] > 0
    sp = S.preston_track_profile(np.array([-4e-3, 4e-3]), 10.0, A, 1e-12, spin=om, speed=1e-3)
    assert sp[0] > sp[1]                                     # 戻る側(−y、相対速度 v + ω|y|)の方が深い


def test_band_width_closed_form_and_image():
    f = S.wipe_band_width(1.0, A, K, 1e-6)
    assert abs(f["force_min"] - 2.0) < 1e-9
    assert S.wipe_band_width(1.99, A, K, 1e-6)["width"] == 0.0
    assert abs(S.wipe_band_width(1e6, A, K, 1e-6)["width"] / (2 * A) - 1) < 1e-9
    hz = S.wipe_band_width(4.0, R_B, K, 1e-6, kind="hertz", estar=E_B)
    assert abs(hz["half_width"] ** 2 - (hz["a"] ** 2 - 1e-6 * R_B / (K * E_B))) < 1e-15
    assert S.wipe_band_width(0.9 * hz["force_min"], R_B, K, 1e-6, kind="hertz", estar=E_B)["width"] == 0.0
    m = S.preston_removal_map(LINE, 6.0, A, K, shape=(201, 41), res=1e-4, speed=5e-3)
    img = S.coat_image(m, 1e-6)
    cov = S.wipe_coverage(img, 1e-4, coat=1e-6)
    pr = S.band_width_profile(img, cov["threshold"], 1e-4)
    th = S.wipe_band_width(6.0, A, K, 1e-6 - cov["residual_at_threshold"])["width"]
    assert pr["valid"].all() and abs(pr["median"] / th - 1) < 0.005
    assert np.max(np.abs(pr["centres"])) < 1e-6


def test_raster_area_closed_form():
    single = 2 * A * 0.03 + math.pi * A * A
    assert abs(S.raster_wipe_area(A, 0.03, 2.5 * A, 3)["area"] - 3 * single) < 1e-15
    assert abs(S.raster_wipe_area(A, 0.03, 1e-12, 3)["area"] - single) < 1e-9 * single
    s = A
    xq = np.linspace(s / 2.0, A, 200001)                                   # 検算: 重なり = 4 ∫_{s/2}^{a} √(a² − x²) dx を台形で
    lens = 4.0 * np.trapezoid(np.sqrt(np.maximum(0.0, A * A - xq * xq)), xq) if hasattr(np, "trapezoid") else         4.0 * np.trapz(np.sqrt(np.maximum(0.0, A * A - xq * xq)), xq)
    assert abs(S.raster_wipe_area(A, 0.03, s, 2)["lens"] / lens - 1) < 1e-6
    ra = S.raster_wipe_area(4e-3, 0.02, 4e-3, 3, centre=(0.3e-4, 0.2e-4), step=1e-3)
    assert np.isnan(ra["path"]).any(axis=1).sum() == 2
    m = S.preston_removal_map(ra["path"], 10.0, 4e-3, K, shape=(110, 170), res=2e-4, speed=0.02)
    img = S.coat_image(m, float(m.max()) / 1000.0)
    assert abs(S.wipe_coverage(img, 2e-4)["area"] / ra["area"] - 1) < 0.01


def test_coat_round_trip_and_thresholds():
    d = np.linspace(0, 2e-6, 64).reshape(8, 8)
    t = S.coat_thickness_from_image(S.coat_image(d, 1e-6), 1e-6)
    assert np.max(np.abs(t - np.clip(1e-6 - d, 0, 1e-6))) < 1e-15
    img = S.coat_image(d, 1e-6, noise=0.0)
    assert img.min() >= 0.85 / 4 - 1e-12 and img.max() <= 0.85 + 1e-12


def test_depth_from_heights_and_preston_fit():
    H, W, res = 161, 61, 1e-4
    y = ((H - 1) / 2.0 - np.arange(H)) * res
    x = (np.arange(W) - (W - 1) / 2.0) * res
    X, Y = np.meshgrid(x, y)
    true = np.repeat(S.preston_track_profile(y, 10.0, 5e-3, 1e-12, spin=60.0, speed=1e-3)[:, None], W, axis=1)
    rng = np.random.default_rng(0)
    zb = rng.normal(0, 20e-9, (H, W))
    za = zb - true + 1e-7 + 1e-6 * Y / 0.01 - 2e-6 * X / 0.01
    d = S.removal_depth_from_heights(zb, za, ref_mask=np.abs(Y) > 6e-3)
    assert np.max(np.abs(d - true)) < 1e-12
    dw = S.preston_removal_map(np.array([[-0.05, 0.0], [0.05, 0.0]]), 10.0, 5e-3, 1.0, shape=(H, W), res=res, speed=1e-3, spin=60.0)
    fit = S.preston_coefficient_fit(d, dw)
    assert abs(fit["k_p"] / 1e-12 - 1) < 0.01 and fit["r2"] > 0.99


def test_winkler_full_contact_decay():
    rng = np.random.default_rng(1)
    z = rng.normal(0, 0.2e-6, (32, 32))
    r = S.winkler_polish_run(z, 3e4, 1e10, 1e-12, 1.0, 100.0)
    c = 1e-12 * 1e10 * 1.0
    assert r["contact"].min() == 1.0
    assert np.max(np.abs(r["rms"] / (r["rms"][0] * np.exp(-c * r["t"])) - 1)) < 0.005
    assert abs((r["mean"][0] - r["mean"][-1]) / (1e-12 * 3e4 * 100.0) - 1) < 1e-9
    rp = S.winkler_polish_run(z * 30, 3e4, 1e10, 1e-12, 1.0, 100.0)      # 山だけが当たる
    assert rp["contact"].min() < 1.0


def test_bad_inputs_raise_and_mjcf():
    P2 = np.array([[0.0, 0.0], [0.01, 0.0]])
    bad = [
        lambda: S.preston_pressure_kernel(1.0, A, 0.02), lambda: S.preston_pressure_kernel(1.0, R_B, 1e-4, kind="hertz"),
        lambda: S.preston_removal_map(P2, 1.0, A, K), lambda: S.preston_removal_map(P2, -1.0, A, K, speed=1.0),
        lambda: S.preston_removal_map(np.array([[0.0, 0.0], [np.nan, 0.0], [1.0, 1.0]]), 1.0, A, K, speed=1.0),
        lambda: S.preston_removal_map(P2, 1.0, A, K, speed=1.0, spin=1.0, method="fft"),
        lambda: S.preston_track_profile(np.zeros(2), 1.0, A, K, spin=1.0),
        lambda: S.wipe_band_width(1.0, A, K, -1.0), lambda: S.raster_wipe_area(A, 0.03, 0.01, 0),
        lambda: S.raster_wipe_area(1e200, 1e200, 1e200, 3), lambda: S.raster_wipe_area(A, 1.0, A, 2, step=1e-9),   # 溢れ・点の数(fuzz の回帰)
        lambda: S.coat_image(np.zeros(4), 1e-6), lambda: S.band_width_profile(np.zeros((8, 8)), np.nan, 1e-4),
        lambda: S.removal_depth_from_heights(np.zeros((8, 8)), np.zeros((8, 8)), frame=0.7),
        lambda: S.preston_coefficient_fit(np.ones((8, 8)), np.ones((8, 9))),
        lambda: S.winkler_polish_run(np.zeros((8, 8)), 0.0, 1e10, 1e-12, 1.0, 1.0),
        lambda: S.polish_scene_mjcf(mass=0.0),
    ]
    assert all(_raises(f) for f in bad)
    import xml.etree.ElementTree as ET
    root = ET.fromstring(S.polish_scene_mjcf())
    assert len(root.findall(".//joint")) == 3 and len(root.findall(".//position")) == 3
    assert root.find(".//geom[@name='pad']").get("type") == "cylinder"


def test_mujoco_soft_wrist_press():
    pytest.importorskip("mujoco")
    sc = S.polish_scene_build(k_z=300.0)
    try:
        r = S.polish_stroke_run(sc, np.array([[0.0, 0.0], [0.002, 0.0]]), np.array([-0.02, -0.02]), speed=0.01, settle=0.5)
        N = float(np.mean(r["normal"][-10:]))
        assert abs(N / (0.2 * 9.81 + 300.0 * 0.02) - 1) < 0.005
        assert abs(float(np.mean(np.hypot(*r["tangent"][-10:].T))) / N - 0.3) < 0.003
    finally:
        S.polish_scene_close(sc)


def test_raster_wipe_area_refuses_an_overflowing_path_or_saving():
    """chain_fuzz の 2 回目の発見(2026-10-05): 面積は有限でも、一筆の y 座標と N 本の和が溢れて inf を返していた。"""
    import polish as PO
    cases = [(1e-300, 1e-300, 1.7e308, 7),        # y = (i − 3)·pitch が溢れる
             (1e-3, 1.7e308, 1e-300, 1000)]        # overlap_saving = N·single − area が溢れる
    assert len(cases) == 2
    for args in cases:
        with pytest.raises(ValueError):
            PO.raster_wipe_area(*args)
    r = PO.raster_wipe_area(1.0, 10.0, 1.5, 3)      # 普通の入力は従来どおり
    assert np.isfinite(r["overlap_saving"]) and r["path"].shape == (3 * 2 + 2, 2)   # 一筆 2 点 × 3 + 区切りの NaN 2 行
