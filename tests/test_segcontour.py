# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""segcontour の門: snake は巡回行列の閉形式と skimage.active_contour、GVF は Euler 方程式の残差と 2 解法の一致・U 字の凹部、
Chan–Vese は厳密な勾配(差分で検算)・単調性・既存 op sk_chan_vese、形態学的 snake は skimage と画素一致 + データ段の
単調性、再初期化は解析的な距離と距離変換、DRLSE は真円の縁で止まる、曲率流は dA/dt = −2π(凸でなくても)。"""
from __future__ import annotations

import inspect
import math

import numpy as np
import pytest
from scipy import ndimage as ndi

import segcontour as SC
import segeval as SE


# ───────────────────────── 合成の道具(構造のある入力、乱数は seed 固定) ─────────────────────────
def grid(h, w):
    return np.mgrid[0:h, 0:w].astype(np.float64)


def circle_points(cy, cx, r, n):
    th = np.linspace(0.0, 2.0 * math.pi, n, endpoint=False)
    return np.stack([cy + r * np.sin(th), cx + r * np.cos(th)], axis=1)


def ellipse_image(noise=0.2, seed=0, h=100, w=100):
    yy, xx = grid(h, w)
    truth = (yy - 50) ** 2 / 30 ** 2 + (xx - 48) ** 2 / 22 ** 2 < 1
    im = truth.astype(float) + noise * np.random.default_rng(seed).standard_normal((h, w))
    return im, truth


def u_shape(h=128, w=128):
    U = np.zeros((h, w), bool)
    U[30:100, 30:98] = True
    U[30:82, 52:76] = False
    slot = np.zeros((h, w), bool)
    slot[30:82, 52:76] = True
    return U, slot


def square_init(shape, a=20, b=80):
    m = np.zeros(shape, bool)
    m[a:b, a:b] = True
    return m


# ───────────────────────── 1. snake ─────────────────────────
@pytest.mark.parametrize("alpha,beta,gamma,n", [(0.5, 0.2, 2.0, 60), (1.0, 0.0, 1.0, 40), (0.0, 0.3, 0.5, 100)])
def test_snake_circle_follows_discrete_closed_form(alpha, beta, gamma, n):
    """外力 0: 円は巡回行列 A の第 1 Fourier モード → 1 反復で半径 γ/(γ + 4α sin²(π/N) + 16β sin⁴(π/N)) 倍(厳密)。"""
    pts = circle_points(40.0, 41.0, 20.0, n)
    r = SC.snake_evolve(np.zeros((81, 83)), pts, alpha=alpha, beta=beta, gamma=gamma, external="none", n_iter=50)
    lam = 4 * alpha * math.sin(math.pi / n) ** 2 + 16 * beta * math.sin(math.pi / n) ** 4
    f = gamma / (gamma + lam)
    assert r["radius_factor"] == pytest.approx(f, rel=1e-15)
    rad = np.hypot(r["points"][:, 0] - 40.0, r["points"][:, 1] - 41.0)
    np.testing.assert_allclose(rad, 20.0 * f ** 50, rtol=1e-10)
    centre = r["points"].mean(axis=0)
    np.testing.assert_allclose(centre, [40.0, 41.0], atol=1e-10)
    assert r["n_increase"] == 0                       # 外力 0 は二次の近接点法 = 厳密に単調


def test_snake_edge_energy_monotone_when_gamma_dominates_lipschitz():
    yy, xx = grid(64, 64)
    img = ((yy - 32) ** 2 + (xx - 32) ** 2 < 15 ** 2).astype(float)
    r = SC.snake_evolve(img, circle_points(32, 32, 20, 60), alpha=0.05, beta=0.05, gamma=1.0, external="edge",
                        sigma=2.0, kappa=20.0, n_iter=300)
    assert r["gamma_ge_lipschitz"] and r["lipschitz"] > 0
    assert r["n_increase"] == 0
    assert r["energy"][-1] < r["energy"][0]
    rad = np.hypot(r["points"][:, 0] - 32, r["points"][:, 1] - 32)
    assert abs(rad.mean() - 14.75) < 1.0 and rad.std() < 0.5          # 縁(14.5〜15)に止まる
    assert len(r["energy"]) == r["n_iter"] + 1


def test_snake_matches_skimage_active_contour():
    skseg = pytest.importorskip("skimage.segmentation")
    skf = pytest.importorskip("skimage.filters")
    yy, xx = grid(100, 100)
    img = skf.gaussian(((yy - 50) ** 2 / 30 ** 2 + (xx - 48) ** 2 / 22 ** 2 < 1).astype(float), 2)
    init = circle_points(50, 50, 40, 80)
    P = skf.sobel(img)
    for it in (10, 200):
        sk = skseg.active_contour(img, init, alpha=0.01, beta=0.1, w_line=0, w_edge=1, gamma=0.01, max_px_move=1.0,
                                  max_num_iter=it, convergence=0.0)
        me = SC.snake_evolve(P, init, alpha=0.01, beta=0.1, gamma=0.01, external="potential", kappa=1.0,
                             max_px_move=1.0, n_iter=it, spline_order=2)
        assert np.abs(sk - me["points"]).max() < 1e-8


def test_snake_gvf_has_no_energy_and_mask_is_polygon_interior():
    U, _ = u_shape()
    img = ndi.gaussian_filter(U.astype(float), 1.0)
    r = SC.snake_evolve(img, circle_points(65, 64, 52, 120), external="gvf", kappa=5.0, alpha=0.01, beta=0.01,
                        n_iter=20)
    assert r["n_increase"] is None and np.isnan(r["energy"]).all()
    assert np.isfinite(r["energy_internal"]).all()
    sq = np.array([[10.0, 10.0], [10.0, 30.0], [30.0, 30.0], [30.0, 10.0], [20.0, 10.0]])
    m = SC._polygon_mask(sq, (40, 40))
    assert m[11:30, 11:30].all() and not m[:10].max() and not m[31:].max()


def test_u_shape_gvf_enters_the_concavity_classic_does_not():
    """Xu–Prince 1998 の U 字: 古典の snake(エッジの勾配)は凹部に力が無く入れない、GVF は入る(自明でない門)。"""
    U, slot = u_shape()
    img = ndi.gaussian_filter(U.astype(float), 1.0)
    init = circle_points(65, 64, 52, 120)
    a = SC.snake_evolve(img, init, alpha=0.01, beta=0.01, gamma=1.0, external="edge", sigma=1.5, kappa=20.0,
                        n_iter=1000)
    g = SC.gvf_field(img, mu=0.2, sigma=1.0)
    b = SC.snake_evolve(img, init, alpha=0.01, beta=0.01, gamma=1.0, external="gvf", gvf=g, kappa=5.0, n_iter=1000,
                        resample_every=5)
    cover_a = np.count_nonzero(a["mask"] & slot) / slot.sum()
    cover_b = np.count_nonzero(b["mask"] & slot) / slot.sum()
    assert cover_a > 0.9 and cover_b < 0.05
    assert SE.seg_dice_jaccard(b["mask"], U)["dice"] > 0.98 > SE.seg_dice_jaccard(a["mask"], U)["dice"]


@pytest.mark.parametrize("bad", [np.zeros((4, 2)), np.zeros((10, 3)), np.full((10, 2), np.nan),
                                 circle_points(10, 10, 30, 20), "abc"])
def test_snake_rejects_bad_points(bad):
    with pytest.raises(ValueError):
        SC.snake_evolve(np.zeros((40, 40)), bad)


def test_snake_rejects_bad_knobs():
    pts = circle_points(20, 20, 10, 30)
    for kw in ({"gamma": 0.0}, {"alpha": -1.0}, {"external": "magic"}, {"n_iter": 1.5}, {"spline_order": 0},
               {"gvf": {"x": 1}, "external": "gvf"}):
        with pytest.raises(ValueError):
            SC.snake_evolve(np.zeros((40, 40)), pts, **kw)


# ───────────────────────── 2. GVF ─────────────────────────
def test_gvf_direct_solves_euler_equation_and_iteration_converges_to_it():
    yy, xx = grid(48, 48)
    img = ((yy - 24) ** 2 + (xx - 22) ** 2 < 10 ** 2).astype(float)
    d = SC.gvf_field(img, mu=0.2, method="direct")
    assert d["residual_rel"] < 1e-10
    errs = []
    for n in (1000, 5000, 20000):
        it = SC.gvf_field(img, mu=0.2, method="iterate", n_iter=n)
        errs.append(float(np.abs(it["u"] - d["u"]).max() + np.abs(it["v"] - d["v"]).max()))
    assert errs[0] > errs[1] > errs[2]
    assert errs[2] < 1e-8 * np.abs(d["u"]).max()
    assert it["residual_rel"] < 1e-8
    # 辺の上では GVF ≈ ∇f(データ項が支配)、辺から遠い中心では小さいが 0 でない(拡散で届く)
    assert np.abs(d["u"]).max() > 0


def test_gvf_flat_image_gives_zero_field_and_symmetry():
    z = SC.gvf_field(np.full((20, 20), 0.3))
    assert np.abs(z["u"]).max() == 0 and np.abs(z["v"]).max() == 0 and z["residual_max"] == 0
    yy, xx = grid(41, 41)
    img = ((yy - 20) ** 2 + (xx - 20) ** 2 < 10 ** 2).astype(float)
    d = SC.gvf_field(img)
    np.testing.assert_allclose(d["u"], -d["u"][:, ::-1], atol=1e-12)      # 左右対称な円 → u は反対称
    np.testing.assert_allclose(d["u"], d["v"].T, atol=1e-12)               # 転置対称 → u と v が入れ替わる


def test_gvf_rejects_unstable_dt_and_bad_method():
    img = np.zeros((20, 20))
    img[5:15, 5:15] = 1
    with pytest.raises(ValueError):
        SC.gvf_field(img, method="iterate", dt=10.0)
    with pytest.raises(ValueError):
        SC.gvf_field(img, method="fft")
    with pytest.raises(ValueError):
        SC.gvf_field(img, mu=0.0)


# ───────────────────────── 3. Chan–Vese ─────────────────────────
def test_chan_vese_energy_sharp_parts_closed_form():
    im = np.zeros((30, 40))
    im[5:15, 10:30] = 1.0
    m = np.zeros(im.shape, bool)
    m[5:15, 10:30] = True
    e = SC.chan_vese_energy(im, m, mu=0.5, nu=0.25)
    assert e["perimeter_sharp"] == 2 * (10 + 20)
    assert e["energy_sharp"] == pytest.approx(0.5 * 60 + 0.25 * 200)       # 当てはめは 0(2 値で真の分割)
    phi = SC._signed_distance(m)
    assert SC.chan_vese_energy(im, phi, mu=0.5)["energy"] == pytest.approx(SC.chan_vese_energy(im, m, mu=0.5)["energy"])
    shifted = np.roll(m, 3, axis=1)
    assert SC.chan_vese_energy(im, shifted)["energy_sharp"] > SC.chan_vese_energy(im, m)["energy_sharp"]
    e0 = SC.chan_vese_energy(im, m)
    assert e0["c1_sharp"] == 1.0 and e0["c2_sharp"] == 0.0
    assert e0["c1"] > 0.5 > e0["c2"]                                          # arctan の H_ε は裾が長い(滑らかな平均)


def test_chan_vese_level_set_gradient_is_exact():
    im, truth = ellipse_image()
    rng = np.random.default_rng(1)
    phi = SC._signed_distance(square_init(im.shape)) + 0.3 * rng.standard_normal(im.shape)
    args = (0.2, 0.1, 1.0, 1.3, 1.0)
    parts = SC._cv_parts(im, phi, *args[:4], args[4], 0.1)
    g = SC._cv_grad(im, phi, parts, *args)
    for k in range(3):
        d = rng.standard_normal(im.shape)
        h = 1e-5
        ep = SC._cv_parts(im, phi + h * d, *args[:4], args[4], 0.1)["energy"]
        em = SC._cv_parts(im, phi - h * d, *args[:4], args[4], 0.1)["energy"]
        assert (ep - em) / (2 * h) == pytest.approx(float(np.sum(g * d)), rel=1e-6)


def test_chan_vese_level_set_energy_monotone():
    im, truth = ellipse_image()
    c = SC.chan_vese_evolve(im, square_init(im.shape), method="level_set", mu=0.2, n_iter=100, dt=5.0)
    assert c["n_increase"] == 0 and len(c["energy"]) == c["n_iter"] + 1
    assert c["energy"][-1] < c["energy"][0]
    assert np.all(np.diff(c["energy"]) <= 0)


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_chan_vese_convex_recovers_two_valued_truth_monotonically(seed):
    im, truth = ellipse_image(seed=seed)
    c = SC.chan_vese_evolve(im, square_init(im.shape), mu=0.2, n_iter=50)
    assert c["n_guard"] == 0 and c["n_increase"] == 0 and c["converged"]
    assert np.all(np.diff(c["energy"]) <= 0)
    assert SE.seg_dice_jaccard(c["mask"], truth)["dice"] > 0.99
    assert c["c1"] == pytest.approx(1.0, abs=0.02) and c["c2"] == pytest.approx(0.0, abs=0.02)
    again = SC.chan_vese_evolve(im, c["mask"], mu=0.2, n_iter=5)               # 不動点: もう動かない
    assert np.array_equal(again["mask"], c["mask"])


def test_chan_vese_agrees_with_existing_sk_chan_vese_op():
    fs = pytest.importorskip("fullseye")
    im, truth = ellipse_image(noise=0.15, seed=3)
    imn = (im - im.min()) / (im.max() - im.min())
    mine = SC.chan_vese_evolve(imn, square_init(im.shape), mu=0.2, n_iter=50)["mask"]
    sk = fs.apply(imn, "sk_chan_vese", 0.5, 0.5) > 0.5
    dice = max(SE.seg_dice_jaccard(sk, mine)["dice"], SE.seg_dice_jaccard(~sk, mine)["dice"])   # 極性は実装ごと
    assert dice > 0.97


def test_chan_vese_rejects_bad_inputs():
    im, _ = ellipse_image()
    with pytest.raises(ValueError):
        SC.chan_vese_evolve(im, np.zeros(im.shape, bool))                   # 内側が空
    with pytest.raises(ValueError):
        SC.chan_vese_evolve(im, square_init((50, 50)))                      # 形が違う
    with pytest.raises(ValueError):
        SC.chan_vese_evolve(im, square_init(im.shape), method="graphcut")
    with pytest.raises(ValueError):
        SC.chan_vese_energy(np.full((5, 5), np.inf), np.ones((5, 5), bool))


# ───────────────────────── 4. 形態学的 snake ─────────────────────────
def _reset_skimage_cycle(MS):
    """skimage は SI∘IS / IS∘SI の交互の位相をモジュールの大域状態に持つ(呼び出しの履歴で結果が変わる)ので揃える。"""
    MS._curvop = MS._fcycle([lambda u: MS.sup_inf(MS.inf_sup(u)), lambda u: MS.inf_sup(MS.sup_inf(u))])


@pytest.mark.parametrize("smoothing,lam", [(1, (1.0, 1.0)), (2, (1.0, 1.0)), (3, (2.0, 1.0))])
def test_morph_chan_vese_matches_skimage_pixel_for_pixel(smoothing, lam):
    MS = pytest.importorskip("skimage.segmentation.morphsnakes")
    im, _ = ellipse_image()
    init = square_init(im.shape)
    _reset_skimage_cycle(MS)
    a = MS.morphological_chan_vese(im, 40, init_level_set=init.astype(np.int8), smoothing=smoothing,
                                   lambda1=lam[0], lambda2=lam[1])
    b = SC.morph_chan_vese(im, init, n_iter=40, smoothing=smoothing, lambda1=lam[0], lambda2=lam[1])
    assert np.array_equal(a.astype(bool), b["mask"])


@pytest.mark.parametrize("seed", [0, 1, 2, 3])
def test_morph_chan_vese_data_step_never_raises_fit_energy(seed):
    im, truth = ellipse_image(noise=0.3, seed=seed)
    b = SC.morph_chan_vese(im, square_init(im.shape, 10, 60), n_iter=60, smoothing=2)
    assert b["n_data_increase"] == 0
    assert np.all(b["fit_after_data"] <= b["fit_before_data"] + 1e-9)
    assert SE.seg_dice_jaccard(b["mask"], truth)["dice"] > 0.95
    assert len(b["n_changed"]) == 60


@pytest.mark.parametrize("balloon", [-1.0, 0.0, 1.0])
def test_morph_geodesic_ac_matches_skimage(balloon):
    MS = pytest.importorskip("skimage.segmentation.morphsnakes")
    yy, xx = grid(100, 100)
    img = ndi.gaussian_filter(((yy - 50) ** 2 / 30 ** 2 + (xx - 48) ** 2 / 22 ** 2 < 1).astype(float), 2)
    g = SC.edge_stop_g(img, sigma=1.0, k=0.05)["g"]
    init = (yy - 50) ** 2 + (xx - 50) ** 2 < (45 if balloon <= 0 else 8) ** 2
    _reset_skimage_cycle(MS)
    a = MS.morphological_geodesic_active_contour(g, 80, init_level_set=init.astype(np.int8), smoothing=1,
                                                 balloon=balloon)
    b = SC.morph_geodesic_ac(g, init, n_iter=80, smoothing=1, balloon=balloon)
    assert np.array_equal(a.astype(bool), b["mask"])


def test_morph_geodesic_ac_shrinks_onto_the_ellipse():
    yy, xx = grid(100, 100)
    truth = (yy - 50) ** 2 / 30 ** 2 + (xx - 48) ** 2 / 22 ** 2 < 1
    img = ndi.gaussian_filter(truth.astype(float), 1.0)
    g = SC.edge_stop_g(img, sigma=1.0, k=0.05)["g"]
    init = (yy - 50) ** 2 + (xx - 50) ** 2 < 45 ** 2
    b = SC.morph_geodesic_ac(g, init, n_iter=200, balloon=-1, threshold=0.5)
    assert SE.seg_dice_jaccard(b["mask"], truth)["dice"] > 0.97
    assert b["n_changed"][-1] == 0                                           # 止まった
    # 落とし穴: 背景が厳密に平坦だと auto(40 % 点)= 1 で風船が働かず、初期の円からほとんど動かない
    dead = SC.morph_geodesic_ac(g, init, n_iter=200, balloon=-1)
    assert dead["threshold"] == 1.0
    assert SE.seg_dice_jaccard(dead["mask"], truth)["dice"] < 0.6


# ───────────────────────── 5. エッジ停止関数 ─────────────────────────
def test_edge_stop_g_range_flat_and_scale():
    im, _ = ellipse_image()
    for s in (0.0, 1.0, 3.0):
        g = SC.edge_stop_g(im, sigma=s)
        assert 0.0 < g["g_min"] <= g["g_max"] <= 1.0
    flat = SC.edge_stop_g(np.full((16, 16), 0.7), sigma=1.0)
    assert np.array_equal(flat["g"], np.ones((16, 16)))
    a = SC.edge_stop_g(im, sigma=1.0, k=1.0)
    b = SC.edge_stop_g(2.0 * im, sigma=1.0, k=2.0)                           # g は |∇|/k だけで決まる
    np.testing.assert_allclose(a["g"], b["g"], rtol=1e-12)
    np.testing.assert_allclose(a["g"], 1.0 / (1.0 + a["grad_mag"] ** 2), rtol=1e-12)
    with pytest.raises(ValueError):
        SC.edge_stop_g(im, k=0.0)


# ───────────────────────── 6. 再初期化 ─────────────────────────
@pytest.mark.parametrize("scale", [0.005, 0.05])
def test_reinit_sussman_gives_signed_distance_without_moving_the_zero_set(scale):
    yy, xx = grid(96, 96)
    cy, cx, R = 47.6, 48.2, 25.3
    true = np.hypot(yy - cy, xx - cx) - R
    phi0 = scale * (np.hypot(yy - cy, xx - cx) ** 2 - R ** 2)                 # 距離でない(|∇φ| ≈ 0.25 か 2.5)
    r = SC.level_set_reinit(phi0, n_iter=200)
    assert abs(r["grad_before"]["q50"] - 1.0) > 0.5
    assert 0.95 < r["grad"]["q10"] <= r["grad"]["q50"] <= r["grad"]["q90"] < 1.05
    assert r["zero_hausdorff"] <= 1.0
    band = np.abs(true) <= 3
    assert np.abs(r["phi"] - true)[band].max() < 0.1
    e = SC.level_set_reinit(phi0, method="edt")                              # 第 2 実装
    assert np.abs(e["phi"] - r["phi"])[band].max() < 0.75
    assert e["zero_hausdorff"] <= 1.0


def test_reinit_of_a_distance_is_nearly_identity_and_accepts_mask():
    yy, xx = grid(60, 60)
    true = np.hypot(yy - 30.3, xx - 29.6) - 15.2
    r = SC.level_set_reinit(true, n_iter=50)
    assert np.abs(r["phi"] - true)[np.abs(true) <= 3].max() < 0.1
    m = true < 0
    rm = SC.level_set_reinit(m, method="edt")
    assert np.array_equal(rm["phi"] < 0, m)
    with pytest.raises(ValueError):
        SC.level_set_reinit(true, dt=0.9)
    with pytest.raises(ValueError):
        SC.level_set_reinit(np.ones((10, 10)))                               # 内側が無い


# ───────────────────────── 7. DRLSE ─────────────────────────
def test_drlse_stops_at_the_disk_edge_and_keeps_distance_profile():
    yy, xx = grid(96, 96)
    d = np.hypot(yy - 47.6, xx - 48.2)
    img = 0.2 + 0.6 * (d < 20)
    r = SC.drle_evolve(img, d < 32, n_iter=400, record_every=50)
    rad = math.sqrt(np.count_nonzero(r["mask"]) / math.pi)
    assert abs(rad - 20.0) < 1.0
    assert 0.85 < r["grad"]["q50"] < 1.1                                     # 2 値の段差(|∇φ| ≈ 2 の帯)から距離の形へ
    assert len(r["grad_trace"]) == 8 and len(r["history"]) == 9
    # 境界は Li の配布コードの Neumann(縁の 1 列 = 内側 2 列目)
    f = np.arange(36.0).reshape(6, 6)
    g = SC._neumann(f)
    assert g[0, 3] == f[2, 3] and g[3, -1] == f[3, -3] and g[0, 0] == f[2, 2]


def test_drlse_rejects_cfl_violation():
    img = np.zeros((30, 30))
    img[10:20, 10:20] = 1
    with pytest.raises(ValueError):
        SC.drle_evolve(img, img > 0, mu=0.3, dt=1.0)
    with pytest.raises(ValueError):
        SC.drle_evolve(img, img > 0, potential="triple_well")


# ───────────────────────── 8. 平均曲率流 ─────────────────────────
def test_curvature_flow_circle_area_rate_and_radius_law():
    yy, xx = grid(80, 80)
    phi = np.hypot(yy - 39.6, xx - 40.3) - 30.0
    c = SC.curvature_flow(phi, t_end=300.0, dt=0.2)
    assert c["area_rate"] == pytest.approx(-2 * math.pi, rel=0.005)
    r2 = c["areas"] / math.pi
    np.testing.assert_allclose(r2, 900.0 - 2.0 * c["times"], atol=3.0)       # r² = r0² − 2t


def test_curvature_flow_nonconvex_star_still_loses_2pi_per_unit_time():
    """dA/dt = −∮κ ds = −2π は凸でなくても成り立つ(回転数 1)。凹んだ部分は外へ膨らむのに総和は同じ。"""
    yy, xx = grid(96, 96)
    th = np.arctan2(yy - 47.6, xx - 48.2)
    star = np.hypot(yy - 47.6, xx - 48.2) < 28 * (1 + 0.3 * np.cos(3 * th))
    c = SC.curvature_flow(star, t_end=150.0, dt=0.2)
    assert c["area_rate"] == pytest.approx(-2 * math.pi, rel=0.01)
    grew = np.count_nonzero(c["mask"] & ~star)
    assert grew > 0                                                          # 凹部は内側から外へ動いた


def test_curvature_flow_rejects_unstable_dt():
    with pytest.raises(ValueError):
        SC.curvature_flow(square_init((40, 40), 10, 30), dt=0.3)


# ───────────────────────── 規律 ─────────────────────────
def test_deterministic_and_no_forbidden_text():
    im, _ = ellipse_image()
    a = SC.morph_chan_vese(im, square_init(im.shape), n_iter=10)["mask"]
    b = SC.morph_chan_vese(im, square_init(im.shape), n_iter=10)["mask"]
    assert np.array_equal(a, b)                                              # skimage と違い呼び出し履歴に依らない
    src = inspect.getsource(SC)
    assert "any(" not in src
    for name in SC.__all__:
        obj = getattr(SC, name)
        doc = getattr(obj, "__doc__", "") or ""
        if callable(obj):
            for bad in ("](", "{{", "{%"):
                assert bad not in doc, (name, bad)
