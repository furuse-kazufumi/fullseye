# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Gates for sfpolar (shape from polarisation): truth from the Fresnel equations through independent code.

真値の経路(逆算する側 sfpolar とは別のコード):
  * DoLP の閉形式 ↔ ``glassmirror.fresnel_dielectric`` の s / p 反射率(別の式で書かれた Fresnel)。
    無偏光の反射率は ``match3d.fresnel_reflectance``(3 本目の実装)で S0 を照合する。
  * 4 方位画像 ↔ ``optics.mueller_element``(回転子・偏光子)と ``optics.mueller_apply`` の
    Mueller 行列の経路。界面の Mueller 行列は入射面の座標で ``0.5 [[a+b, a-b], [a-b, a+b]]``
    (a = p, b = s の反射率または透過率)と書き、回転子で像の座標へ回す。
  * 法線は球・円柱・楕円体・球冠の解析式。

壊して確かめたこと(2026-10-13、各 1 回): 鏡面の AoLP のずれを 90° → 0° / 拡散の分子の
``(n − 1/n)`` を ``(n − 1)`` / Brewster の判定 ``1 − 1e-12`` を ``1 − 1e-3`` / 稜線の帯の
傾きの符号を反転 / 鏡像拡張を外す —— それぞれ下の門が落ちることを見た(コミットに記録)。
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np
import pytest

import glassmirror as gm
import match3d as m3
import optics as O
import opsoptics
import photometric as ph
import sfpolar as sf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANGLES = (0.0, 45.0, 90.0, 135.0)


# --------------------------------------------------------------------------- #
# 解析的な形と、逆算とは別のコードの順方向(Mueller 行列の経路)
# --------------------------------------------------------------------------- #
def sphere(h=96, radius=40.0, frac=0.97, centre=None):
    yy, xx = np.mgrid[0:h, 0:h].astype(float)
    cy, cx = ((h - 1) / 2.0, (h - 1) / 2.0) if centre is None else centre
    x, y = (xx - cx) / radius, (yy - cy) / radius
    r2 = x * x + y * y
    m = r2 < frac ** 2
    nz = np.sqrt(np.clip(1.0 - r2, 0.0, 1.0))
    n = np.stack([x, y, nz], axis=-1)
    n[~m] = (0.0, 0.0, 1.0)
    return n / np.linalg.norm(n, axis=-1, keepdims=True), m


def cylinder(h=64, w=96, radius=40.0, frac=0.95):
    """軸が行方向(y)の円柱。法線は (x, 0, nz) で、方位は 0° か 180° だけ。"""
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    x = (xx - (w - 1) / 2.0) / radius
    m = np.abs(x) < frac
    nz = np.sqrt(np.clip(1.0 - x * x, 0.0, 1.0))
    n = np.stack([x, np.zeros_like(x), nz], axis=-1)
    n[~m] = (0.0, 0.0, 1.0)
    return n / np.linalg.norm(n, axis=-1, keepdims=True), m


def ellipsoid(alpha_deg, h=96, a=40.0, b=26.0, frac=0.95):
    """主軸を alpha 回した楕円体のドーム(z 方向の半径 = a)。回転の門の題材(円対称でない)。"""
    yy, xx = np.mgrid[0:h, 0:h].astype(float)
    c = (h - 1) / 2.0
    ca, sa = math.cos(math.radians(alpha_deg)), math.sin(math.radians(alpha_deg))
    X, Y = xx - c, yy - c
    u, v = ca * X + sa * Y, -sa * X + ca * Y
    r2 = (u / a) ** 2 + (v / b) ** 2
    m = r2 < frac ** 2
    nz = np.sqrt(np.clip(1.0 - r2, 1e-12, 1.0))
    gu, gv = u / a ** 2, v / b ** 2
    n = np.stack([ca * gu - sa * gv, sa * gu + ca * gv, nz / a], axis=-1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    n[~m] = (0.0, 0.0, 1.0)
    return n, m


def spherical_cap(h=96, radius=48.0, rim=0.92):
    """球冠(レンズ・ドーム): 縁で高さ 0 に着く = 高さの門の題材(段差が無い)。"""
    yy, xx = np.mgrid[0:h, 0:h].astype(float)
    c = (h - 1) / 2.0
    r2 = ((xx - c) ** 2 + (yy - c) ** 2) / radius ** 2
    m = r2 < rim ** 2
    nz = np.sqrt(np.clip(1.0 - r2, 0.0, 1.0))
    n = np.stack([(xx - c) / radius, (yy - c) / radius, nz], axis=-1)
    n[~m] = (0.0, 0.0, 1.0)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    z = np.where(m, radius * (nz - math.sqrt(1.0 - rim ** 2)), 0.0)
    return n, m, z


def mueller_sweep(nrm, n, model, mask, angles=ANGLES):
    """sfpolar を一切使わない順方向: Fresnel(glassmirror)→ 界面の Mueller 行列 →
    回転子で像の座標へ → 偏光子(optics)→ 強度。返り = (N,H,W) と S0。"""
    H, W = nrm.shape[:2]
    theta = np.arccos(np.clip(nrm[..., 2], -1.0, 1.0))
    phi = np.degrees(np.arctan2(nrm[..., 1], nrm[..., 0]))
    c = np.cos(theta)
    rs = gm.fresnel_dielectric(c, 1.0, n, "s")
    rp = gm.fresnel_dielectric(c, 1.0, n, "p")
    a, b = (rp, rs) if model == "specular" else (1.0 - rp, 1.0 - rs)
    s_local = np.zeros((H, W, 4))
    s_local[..., 0] = 0.5 * (a + b)
    s_local[..., 1] = 0.5 * (a - b)            # +x' = 入射面の向き(p)
    rot = np.zeros((H, W, 4, 4))
    for i in range(H):
        for j in range(W):
            rot[i, j] = O.mueller_element("rotator", phi[i, j])
    s_img = O.mueller_apply(rot, s_local)
    imgs = np.stack([O.mueller_apply(O.mueller_element("polarizer", t), s_img)[..., 0] for t in angles])
    return np.where(mask[None], imgs, 0.0), s_local[..., 0]


def render(nrm, n, model, mask, rad=1.0, **kw):
    """sfp_render with a named pure model (the op itself takes the two radiances)."""
    if model == "specular":
        return sf.sfp_render(nrm, n, specular_radiance=rad, diffuse_radiance=0.0, mask=mask, **kw)
    return sf.sfp_render(nrm, n, specular_radiance=0.0, diffuse_radiance=rad, mask=mask, **kw)


def best_candidate_error(cands, truth):
    errs = np.stack([ph.angular_error_deg(cands["candidates"][k], truth)
                     for k in range(cands["candidates"].shape[0])])
    return np.min(errs, axis=0)


# --------------------------------------------------------------------------- #
# 1. 閉形式(Fresnel)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("n", [1.3, 1.5, 1.7, 2.4])
def test_the_closed_forms_match_fresnel_written_differently(n):
    th = np.linspace(0.0, 89.9, 2000)
    c = np.cos(np.radians(th))
    rs = gm.fresnel_dielectric(c, 1.0, n, "s")
    rp = gm.fresnel_dielectric(c, 1.0, n, "p")
    spec = (rs - rp) / (rs + rp)
    diff = ((1.0 - rp) - (1.0 - rs)) / ((1.0 - rp) + (1.0 - rs))
    assert np.abs(sf.sfp_dolp_model(th, n, "specular") - spec).max() < 1e-12   # 実測 1.5e-15
    assert np.abs(sf.sfp_dolp_model(th, n, "diffuse") - diff).max() < 1e-12    # 実測 2.0e-14


@pytest.mark.parametrize("n", [1.3, 1.5, 1.7, 2.4, 4.0])
def test_specular_dolp_is_exactly_one_at_brewster(n):
    tb = math.degrees(math.atan(n))
    assert abs(float(sf.sfp_dolp_model(tb, n, "specular")) - 1.0) <= 4 * np.finfo(float).eps
    # 独立経路: Brewster で R_p = 0(glassmirror の門が 1e-15 未満と言っている)
    c = math.cos(math.radians(gm.brewster_angle_deg(1.0, n)))
    rs = float(gm.fresnel_dielectric(c, 1.0, n, "s"))
    rp = float(gm.fresnel_dielectric(c, 1.0, n, "p"))
    assert abs((rs - rp) / (rs + rp) - 1.0) < 1e-14
    # 頂上は 1 点だけ: 両側では 1 未満
    assert float(sf.sfp_dolp_model(tb - 0.5, n, "specular")) < 1.0
    assert float(sf.sfp_dolp_model(tb + 0.5, n, "specular")) < 1.0


@pytest.mark.parametrize("n", [1.3, 1.5, 2.4])
def test_diffuse_dolp_is_strictly_monotone_up_to_its_closed_form_maximum(n):
    th = np.linspace(0.0, 90.0, 4001)
    d = sf.sfp_dolp_model(th, n, "diffuse")
    assert d[0] == 0.0
    assert (np.diff(d) > 0.0).all()
    assert abs(d[-1] - (n * n - 1.0) / (n * n + 1.0)) < 1e-14


def test_the_mueller_path_carries_match3d_unpolarised_reflectance():
    """S0 of the independent forward path = match3d's (R_s + R_p)/2 — a third Fresnel."""
    nrm, m = sphere(h=24, radius=10.0)
    _imgs, s0 = mueller_sweep(nrm, 1.5, "specular", m)
    c = nrm[..., 2]
    ref = np.vectorize(lambda ci: m3.fresnel_reflectance(ci, 1.0, 1.5))(c)
    assert np.abs(s0 - ref)[m].max() < 1e-15


# --------------------------------------------------------------------------- #
# 2. 逆(天頂角・方位角)と曖昧さ
# --------------------------------------------------------------------------- #
def test_specular_zenith_has_two_solutions_except_at_brewster():
    rho = np.linspace(0.0, 1.0, 1001)
    z = sf.dolp_to_zenith(rho, 1.5, "specular")
    tb = math.degrees(math.atan(1.5))
    assert z["zenith_deg"].shape == (2, 1001)
    assert (z["n_solutions"][:-1] == 2).all() and z["n_solutions"][-1] == 1
    lo, hi = z["zenith_deg"]
    assert (lo[:-1] < tb).all() and (hi[:-1] > tb).all()           # Brewster を挟む
    assert lo[-1] == hi[-1] == pytest.approx(tb, abs=1e-12)
    back = sf.sfp_dolp_model(z["zenith_deg"], 1.5, "specular")
    assert np.abs(back - rho).max() < 1e-14                         # 実測 1.1e-15


def test_diffuse_zenith_is_unique_and_unreachable_dolp_is_flagged():
    rmax = (1.5 ** 2 - 1) / (1.5 ** 2 + 1)
    rho = np.array([0.0, 0.1, 0.3, rmax, rmax + 0.01, 0.9])
    z = sf.dolp_to_zenith(rho, 1.5, "diffuse", out_of_range="nan")
    assert z["zenith_deg"].shape == (1, 6)
    assert list(z["n_solutions"]) == [1, 1, 1, 1, 0, 0]
    assert np.isnan(z["zenith_deg"][0, 4:]).all()
    assert z["zenith_deg"][0, 3] == pytest.approx(90.0, abs=1e-9)
    clamped = sf.dolp_to_zenith(rho, 1.5, "diffuse", out_of_range="clamp")
    assert np.isfinite(clamped["zenith_deg"]).all() and list(clamped["n_solutions"]) == [1, 1, 1, 1, 0, 0]
    with pytest.raises(ValueError):
        sf.dolp_to_zenith(rho, 1.5, "diffuse", out_of_range="raise")


def test_azimuth_keeps_the_pi_ambiguity_and_shifts_ninety_degrees_between_models():
    psi = np.array([0.0, 30.0, 179.0])
    d = sf.aolp_to_azimuth(psi, "diffuse")["azimuth_deg"]
    s = sf.aolp_to_azimuth(psi, "specular")["azimuth_deg"]
    assert np.allclose(d[0], psi) and np.allclose(d[1], psi + 180.0)
    assert np.allclose(s[0], np.mod(psi + 90.0, 360.0)) and np.allclose(s[1], np.mod(psi + 270.0, 360.0))


# --------------------------------------------------------------------------- #
# 3. 往復(順方向は別のコード)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("model", ["specular", "diffuse"])
def test_render_matches_the_independent_mueller_path(model):
    nrm, m = sphere(h=48, radius=20.0)
    imgs, s0 = mueller_sweep(nrm, 1.5, model, m)
    ours = render(nrm, 1.5, model, m, rad=s0)
    assert np.abs(ours - imgs).max() < 1e-14                        # 実測 1.4e-16


@pytest.mark.parametrize("shape", ["sphere", "cylinder"])
@pytest.mark.parametrize("model", ["specular", "diffuse"])
def test_round_trip_recovers_the_analytic_normals(shape, model):
    """Noise-free: the candidate set holds the truth to 1e-9 degrees; after the
    convex prior the diffuse map is exact and the specular map is exact except on
    the discrete top of the Brewster ridge, where the two branches are within
    0.1 degrees of each other (measured max 0.092 on the sphere)."""
    nrm, m = sphere() if shape == "sphere" else cylinder()
    imgs, _ = mueller_sweep(nrm, 1.5, model, m)
    c = sf.sfp_normals(imgs, 1.5, model)
    assert c["valid"][m].all()
    assert best_candidate_error(c, nrm)[m].max() < 1e-9               # 実測 3.6e-12
    d = sf.sfp_disambiguate(c, "convex", mask=m)
    e = ph.angular_error_deg(d, nrm)[m]
    if model == "diffuse":
        assert e.max() < 1e-9
    else:
        assert e.mean() < 1e-3 and e.max() < 0.1                       # 実測 1.6e-4 / 0.092
    assert np.allclose(d[~m], (0.0, 0.0, 1.0))


@pytest.mark.parametrize("model,lim_med,lim_mean", [("specular", 0.2, 0.4), ("diffuse", 1.5, 2.5)])
def test_noise_is_reported_not_hidden(model, lim_med, lim_mean):
    """0.2 % Gaussian noise on each analyser image (of the mean in-mask level).
    Measured: specular median 0.097 / mean 0.15 degrees; diffuse 0.75 / 1.26 —
    the diffuse DoLP is weak (< 0.385), so the same noise costs ~8x more."""
    nrm, m = sphere()
    imgs, _ = mueller_sweep(nrm, 1.5, model, m)
    rng = np.random.default_rng(0)
    noisy = np.clip(imgs + rng.normal(0.0, 0.002 * imgs[:, m].mean(), imgs.shape), 0.0, None) * m
    c = sf.sfp_normals(noisy, 1.5, model, out_of_range="clamp")
    d = sf.sfp_disambiguate(c, "convex", mask=m, invalid="exclude")
    e = ph.angular_error_deg(d, nrm)[m]
    assert np.median(e) < lim_med and e.mean() < lim_mean
    assert np.median(e) > 1e-3                                       # 雑音は実際に効いている


# --------------------------------------------------------------------------- #
# 4. 曖昧さの正直さ・事前情報・壊れる所
# --------------------------------------------------------------------------- #
def test_before_disambiguation_every_pixel_admits_four_specular_normals():
    nrm, m = sphere()
    imgs, _ = mueller_sweep(nrm, 1.5, "specular", m)
    c = sf.sfp_normals(imgs, 1.5, "specular")
    assert c["candidates"].shape == (4,) + nrm.shape
    assert (c["n_distinct"][m] == 4).all()
    # 方位の 2 本は互いに π 反転、天頂の 2 本は Brewster を挟む
    az = c["azimuth_deg"][:, m]
    assert np.allclose(np.mod(az[1] - az[0], 360.0), 180.0)
    zd = c["zenith_deg"][:, m]
    tb = c["brewster_deg"]
    assert (zd[0] <= tb + 1e-9).all() and (zd[1] >= tb - 1e-9).all()
    # 真値と、方位だけ反転した偽物が両方とも候補に居る
    flipped = nrm * np.array([-1.0, -1.0, 1.0])
    assert best_candidate_error(c, flipped)[m].max() < 1e-9
    # 拡散なら 2 本
    imgs_d, _ = mueller_sweep(nrm, 1.5, "diffuse", m)
    cd = sf.sfp_normals(imgs_d, 1.5, "diffuse")
    assert cd["candidates"].shape[0] == 2 and (cd["n_distinct"][m] == 2).all()


def test_a_wrong_convex_centre_is_confidently_wrong_and_a_coarse_depth_fixes_it():
    nrm, m = sphere()
    imgs, _ = mueller_sweep(nrm, 1.5, "diffuse", m)
    c = sf.sfp_normals(imgs, 1.5, "diffuse")
    wrong = sf.sfp_disambiguate(c, "convex", mask=m, center=(-500.0, 47.5))   # 「凸」の中心を外す
    ew = ph.angular_error_deg(wrong, nrm)[m]
    assert (ew > 1.0).mean() > 0.3                                  # 下半分の方位が反転
    # 粗い深度(8 画素おきの標本を線形補間 + 0.5 px の雑音 = 低解像度の距離センサ)で選ぶ。
    # その深度の法線は中央値で 17.6° 外れているが、候補どうしの距離(方位 180°)より
    # ずっと近いので選択は当たる。外れる 7 % は中央付近(θ が小さく、方位の反転が小さい角)。
    from scipy import ndimage as nd
    h = 96
    yy, xx = np.mgrid[0:h, 0:h].astype(float)
    r2 = ((xx - 47.5) ** 2 + (yy - 47.5) ** 2) / 40.0 ** 2
    z = 40.0 * np.sqrt(np.clip(1.0 - r2, 0.0, 1.0))
    zc = nd.zoom(z[::8, ::8], 8, order=1)[:h, :h] + np.random.default_rng(0).normal(0.0, 0.5, (h, h))
    prior_err = ph.angular_error_deg(ph.surface_normals(zc), nrm)[m]
    dz = sf.sfp_disambiguate(c, "depth", mask=m, coarse_depth=zc)
    ez = ph.angular_error_deg(dz, nrm)[m]
    assert np.median(prior_err) > 10.0                               # 事前情報そのものは粗い
    assert np.median(ez) < 1e-9 and (ez > 1.0).mean() < 0.1          # 実測 5.0e-14 / 0.069


def test_a_wrong_refractive_index_grows_the_error_and_the_size_is_measured():
    """Where it breaks (1): the index. Truth n = 1.5, assumed n swept.
    Measured mean / max error (degrees), specular sphere:
    n=1.5 -> 0.00016/0.092, 1.45 -> 0.67/0.93, 1.4 -> 1.36/1.93, 1.6 -> 1.25/1.78, 1.8 -> 3.47/4.73;
    diffuse sphere: 1.45 -> 2.04/2.44, 1.4 -> 4.41/5.22, 1.6 -> 3.34/4.10, 1.8 -> 8.03/10.2
    (the weak diffuse DoLP is about 3x more sensitive). It grows smoothly — no blow-up."""
    nrm, m = sphere()
    out = {}
    for model in ("specular", "diffuse"):
        imgs, _ = mueller_sweep(nrm, 1.5, model, m)
        for nw in (1.5, 1.45, 1.4, 1.6, 1.8):
            c = sf.sfp_normals(imgs, nw, model, out_of_range="clamp")
            d = sf.sfp_disambiguate(c, "convex", mask=m, invalid="exclude")
            out[model, nw] = ph.angular_error_deg(d, nrm)[m].mean()
    for model in ("specular", "diffuse"):
        assert out[model, 1.5] < 1e-3
        assert out[model, 1.5] < out[model, 1.45] < out[model, 1.4]
        assert out[model, 1.5] < out[model, 1.6] < out[model, 1.8]
    assert out["specular", 1.4] > 0.5 and out["specular", 1.8] > 2.0
    assert out["diffuse", 1.4] > 2.0 * out["specular", 1.4]


def test_a_mixed_pixel_read_as_pure_specular_is_badly_wrong():
    """Where it breaks (2): 30 % diffuse under the specular model. The two
    polarisations are 90 degrees apart and partly cancel, so both DoLP and AoLP
    lie. Measured mean 11.2 / max 46 degrees; the pure case is exact."""
    nrm, m = sphere()
    pure = sf.sfp_render(nrm, 1.5, mask=m)
    mixed = sf.sfp_render(nrm, 1.5, specular_radiance=1.0, diffuse_radiance=0.3, mask=m)
    e = {}
    for k, imgs in (("pure", pure), ("mixed", mixed)):
        c = sf.sfp_normals(imgs, 1.5, "specular", out_of_range="clamp")
        d = sf.sfp_disambiguate(c, "convex", mask=m, invalid="exclude")
        e[k] = ph.angular_error_deg(d, nrm)[m]
    assert e["pure"].mean() < 1e-3
    assert e["mixed"].mean() > 5.0 and e["mixed"].max() > 20.0


def test_noise_hurts_most_at_the_centre_and_on_the_brewster_ring():
    """Where it breaks (3): the zenith is ill-conditioned where dDoLP/dθ -> 0 —
    at Brewster's angle — and the azimuth is undefined where DoLP -> 0, at the
    centre. The error map has its peaks exactly there."""
    nrm, m = sphere()
    imgs, _ = mueller_sweep(nrm, 1.5, "specular", m)
    th = np.degrees(np.arccos(nrm[..., 2]))
    tb = math.degrees(math.atan(1.5))
    acc = np.zeros(m.shape)
    for seed in range(4):
        rng = np.random.default_rng(seed)
        noisy = np.clip(imgs + rng.normal(0.0, 0.002 * imgs[:, m].mean(), imgs.shape), 0.0, None) * m
        c = sf.sfp_normals(noisy, 1.5, "specular", out_of_range="clamp")
        acc += ph.angular_error_deg(sf.sfp_disambiguate(c, "convex", mask=m, invalid="exclude"), nrm)
    acc /= 4
    ring = m & (np.abs(th - tb) < 2.0)
    centre = m & (th < 5.0)
    calm = m & (th > 25.0) & (th < 45.0)
    assert np.median(acc[ring]) > 2.0 * np.median(acc[calm])
    assert np.median(acc[centre]) > 2.0 * np.median(acc[calm])


def test_a_frame_that_does_not_belong_to_the_sweep_is_flagged_not_clipped():
    """A DoLP above 1 is impossible for light. Noise near Brewster gives a little
    (0.2 % noise: 77 pixels just above 1 with violation_tol = 0, none at the
    default 0.05); a frame 3x too bright gives a lot (27 % of the dome), and
    those pixels are marked invalid instead of being clipped to Brewster's angle
    and read as a confident zenith."""
    nrm, m = sphere()
    sw = sf.sfp_render(nrm, 1.5, mask=m)
    rng = np.random.default_rng(3)
    noisy = np.clip(sw + rng.normal(0.0, 0.002 * sw[:, m].mean(), sw.shape), 0.0, None) * m
    assert sf.sfp_normals(noisy, 1.5)["violation"][m].sum() == 0
    assert sf.sfp_normals(noisy, 1.5, violation_tol=0.0)["violation"][m].sum() > 20
    bad = sw.copy()
    bad[1] *= 3.0
    c = sf.sfp_normals(bad, 1.5)
    assert c["violation"][m].mean() > 0.2
    assert not c["valid"][c["violation"]].any()
    assert (c["candidates"][:, c["violation"]] == 0.0).all()      # 作り話の単位法線は置かない
    with pytest.raises(ValueError):
        sf.sfp_disambiguate(c, "convex", mask=m)                  # mask の中の無効画素は拒む
    d = sf.sfp_disambiguate(c, "convex", mask=m, invalid="exclude")
    assert np.allclose(d[c["violation"]], (0.0, 0.0, 1.0))


# --------------------------------------------------------------------------- #
# 5. 屈折率の推定
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("n", [1.4, 1.5, 1.7])
def test_the_index_is_recovered_from_a_specular_sphere(n):
    nrm, m = sphere()
    th = np.degrees(np.arccos(nrm[..., 2]))
    imgs, _ = mueller_sweep(nrm, n, "specular", m)
    c = sf.sfp_normals(imgs, 1.5, "specular")             # 仮の n で読んでも DoLP は n に依らない
    r = sf.sfp_estimate_index(c["dolp"], th, "specular", mask=m)
    assert abs(r["refractive_index"] - n) < 1e-6
    assert abs(r["brewster_index"] - n) < 0.01            # 画素の離散で 0.003 程度
    rng = np.random.default_rng(1)
    noisy = np.clip(imgs + rng.normal(0.0, 0.01 * imgs[:, m].mean(), imgs.shape), 0.0, None) * m
    cn = sf.sfp_normals(noisy, 1.5, "specular", out_of_range="clamp")
    rn = sf.sfp_estimate_index(cn["dolp"], th, "specular", mask=m)
    assert abs(rn["refractive_index"] - n) < 0.01         # 実測 2.5e-4 / 2.9e-4 / 3.8e-4


def test_the_brewster_shortcut_is_biased_by_noise_and_the_fit_is_not():
    """Honest: the argmax of a noisy DoLP lands on a noise spike, not on the
    Brewster ring. Measured n=1.5 at 1 % noise: fit 1.4998, argmax 1.71."""
    nrm, m = sphere()
    th = np.degrees(np.arccos(nrm[..., 2]))
    imgs = sf.sfp_render(nrm, 1.5, mask=m)
    rng = np.random.default_rng(1)
    noisy = np.clip(imgs + rng.normal(0.0, 0.01, imgs.shape), 0.0, None) * m
    c = sf.sfp_normals(noisy, 1.5, "specular", out_of_range="clamp")
    r = sf.sfp_estimate_index(c["dolp"], th, "specular", mask=m)
    assert abs(r["refractive_index"] - 1.5) < 0.005
    assert abs(r["brewster_index"] - 1.5) > 5 * abs(r["refractive_index"] - 1.5)


# --------------------------------------------------------------------------- #
# 6. 回転(主張ごとに角度を複数振る)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("alpha", [0.0, 17.0, 45.0, 90.0, 133.0])
@pytest.mark.parametrize("model", ["specular", "diffuse"])
def test_rotating_the_scene_rotates_the_recovered_normals(model, alpha):
    nrm, m = ellipsoid(alpha)
    imgs = render(nrm, 1.5, model, m)
    c = sf.sfp_normals(imgs, 1.5, model)
    e = ph.angular_error_deg(sf.sfp_disambiguate(c, "convex", mask=m), nrm)[m]
    if model == "diffuse":
        assert e.max() < 1e-9
    else:
        assert e.mean() < 1e-3 and e.max() < 0.1             # 実測 133°: 1.0e-4 / 0.081


@pytest.mark.parametrize("delta", [7.0, 22.5, 60.0, 101.0])
def test_rotating_the_polariser_frame_changes_nothing_once_the_angles_are_declared(delta):
    nrm, m = ellipsoid(17.0)
    ang = np.array(ANGLES) + delta
    base = sf.sfp_normals(sf.sfp_render(nrm, 1.5, mask=m), 1.5, "specular")
    rot = sf.sfp_normals(sf.sfp_render(nrm, 1.5, mask=m, angles_deg=ang), 1.5, "specular",
                         angles_deg=ang)
    assert np.nanmax(np.abs(rot["candidates"] - base["candidates"])) < 1e-9
    # 角度を申告し忘れると AoLP はちょうど delta だけずれる(黙って間違う向きを固定)
    lied = sf.sfp_normals(sf.sfp_render(nrm, 1.5, mask=m, angles_deg=ang), 1.5, "specular")
    shift = np.mod(base["aolp_deg"] - lied["aolp_deg"], 180.0)[m & (base["dolp"] > 0.05)]
    assert np.allclose(shift, delta % 180.0, atol=1e-9)


# --------------------------------------------------------------------------- #
# 7. 高さ
# --------------------------------------------------------------------------- #
def test_the_height_of_a_cap_comes_back_from_disambiguated_normals():
    nrm, m, z = spherical_cap()
    c = sf.sfp_normals(mueller_sweep(nrm, 1.5, "specular", m)[0], 1.5, "specular")
    d = sf.sfp_disambiguate(c, "convex", mask=m)
    h = sf.sfp_height(d, mask=m)
    err = np.sqrt(np.mean((h - z)[m] ** 2))
    assert err < 0.02 * z.max()                              # 実測 RMS 0.135 px / 高さ 29.2 px
    assert abs(h.max() - z.max()) < 0.03 * z.max()           # 実測 29.31 vs 29.18


def test_the_mirror_extension_removes_the_periodic_wrap():
    H, W = 64, 80
    yy, xx = np.mgrid[0:H, 0:W].astype(float)
    zt = 0.3 * xx - 0.2 * yy
    n = ph.surface_normals(zt).astype(float)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    h = sf.sfp_height(n)
    mirror = np.abs((h - h.mean()) - (zt - zt.mean())).max()
    periodic = np.abs(ph.integrate_normals(n) - (zt - zt.mean())).max()
    assert mirror < 0.1 and periodic > 5.0                   # 実測 0.06 / 18.2


# --------------------------------------------------------------------------- #
# 8. fail-closed
# --------------------------------------------------------------------------- #
_N, _M = sphere(h=16, radius=6.0)


def _sw():
    return sf.sfp_render(_N, 1.5, mask=_M)


def _cands():
    # 遅延して作る: 収集時に作ると、物理を壊したときにファイル全体が収集エラーになり
    # どの門が落ちたのかが見えなくなる(2026-10-13、変異の確認で踏んだ)
    return sf.sfp_normals(_sw(), 1.5, "specular")


@pytest.mark.parametrize("call", [
    lambda: sf.sfp_dolp_model(30.0, 1.0),
    lambda: sf.sfp_dolp_model(30.0, 0.8),
    lambda: sf.sfp_dolp_model(30.0, float("nan")),
    lambda: sf.sfp_dolp_model(30.0, True),
    lambda: sf.sfp_dolp_model(95.0, 1.5),
    lambda: sf.sfp_dolp_model(-1.0, 1.5),
    lambda: sf.sfp_dolp_model(np.array([1.0, np.inf]), 1.5),
    lambda: sf.sfp_dolp_model(30.0, 1.5, "metal"),
    lambda: sf.dolp_to_zenith(1.2, 1.5),
    lambda: sf.dolp_to_zenith(-0.1, 1.5),
    lambda: sf.dolp_to_zenith(np.array([0.2, np.nan]), 1.5),
    lambda: sf.dolp_to_zenith(0.2, 1.0),
    lambda: sf.dolp_to_zenith(0.2, 1.5, out_of_range="ignore"),
    lambda: sf.dolp_to_zenith(np.array([], float), 1.5),
    lambda: sf.dolp_to_zenith(np.array([0.2 + 0j]), 1.5),
    lambda: sf.aolp_to_azimuth(np.array([np.inf])),
    lambda: sf.aolp_to_azimuth(10.0, "both"),
    lambda: sf.sfp_render(np.ones((8, 8)), 1.5),
    lambda: sf.sfp_render(np.ones((8, 8, 3)), 1.5),                       # 単位でない
    lambda: sf.sfp_render(-_N, 1.5),                                     # 裏向き
    lambda: sf.sfp_render(_N, 1.5, specular_radiance=-1.0),
    lambda: sf.sfp_render(_N, 1.5, diffuse_radiance=np.ones((3, 3))),
    lambda: sf.sfp_render(_N, 1.5, specular_radiance=0.0, diffuse_radiance=0.0),
    lambda: sf.sfp_normals(_sw(), 1.5, violation_tol=-0.1),
    lambda: sf.sfp_normals(_sw(), 1.5, out_of_range="nan"),
    lambda: sf.sfp_render(_N, 1.5, angles_deg=(0.0, 90.0)),
    lambda: sf.sfp_render(_N, 1.5, mask=np.ones((16, 16))),             # bool でない
    lambda: sf.sfp_normals(_sw()[:2], 1.5),
    lambda: sf.sfp_normals(_sw()[0], 1.5),
    lambda: sf.sfp_normals(-_sw(), 1.5),
    lambda: sf.sfp_normals(_sw(), 1.5, angles_deg=(0.0, 45.0, 90.0)),
    lambda: sf.sfp_normals(_sw(), 1.5, angles_deg=(0.0, 180.0, 360.0, 540.0)),   # 階数落ち
    lambda: sf.sfp_normals(np.where(np.isfinite(_sw()), np.nan, 0.0), 1.5),
    lambda: sf.sfp_normals(_sw(), 0.5),
    lambda: sf.sfp_disambiguate({"pre": 1, "post": 2}),
    lambda: sf.sfp_disambiguate(dict(_cands(), kind="other")),
    lambda: sf.sfp_disambiguate(_cands(), prior="concave"),
    lambda: sf.sfp_disambiguate(_cands(), prior="depth"),
    lambda: sf.sfp_disambiguate(_cands(), prior="normals", prior_normals=np.ones((3, 3, 3))),
    lambda: sf.sfp_disambiguate(_cands(), mask=np.zeros((16, 16), bool)),
    lambda: sf.sfp_disambiguate(_cands(), mask=np.ones((16, 16), bool)),      # 背景(暗い)を含む → 候補なし
    lambda: sf.sfp_disambiguate(_cands(), invalid="ignore"),
    lambda: sf.sfp_estimate_index(np.ones((4, 4)) * 0.5, np.ones((4, 5)) * 30.0),
    lambda: sf.sfp_estimate_index(np.ones((4, 4)) * 1.5, np.ones((4, 4)) * 30.0),
    lambda: sf.sfp_estimate_index(np.ones((4, 4)) * 0.5, np.ones((4, 4)) * 95.0),
    lambda: sf.sfp_estimate_index(np.ones((4, 4)) * 0.5, np.ones((4, 4)) * 30.0, n_bounds=(2.0, 1.5)),
    lambda: sf.sfp_estimate_index(np.ones((4, 4)) * 0.5, np.ones((4, 4)) * 30.0, n_bounds=(1.0, 2.0)),
    lambda: sf.sfp_estimate_index(np.ones((1, 2)) * 0.5, np.ones((1, 2)) * 30.0),
    lambda: sf.sfp_height(np.ones((8, 8, 3))),
    lambda: sf.sfp_height(_N, max_zenith_deg=90.0),
    lambda: sf.sfp_height(_N, mask=np.zeros((16, 16), bool)),
    lambda: sf.sfp_height(np.where(_M[..., None], np.nan, _N)),
])
def test_bad_inputs_are_refused(call):
    with pytest.raises(ValueError):
        call()


# --------------------------------------------------------------------------- #
# 9. 台帳と公開経路
# --------------------------------------------------------------------------- #
def test_the_ledger_lists_every_op_and_nothing_is_missing():
    listed = set(opsoptics.list_ops("shape_from_polarization"))
    assert listed == set(sf.__all__), listed
    assert not opsoptics.missing()
    for name in listed:
        assert opsoptics.info(name)["module"] == "sfpolar"
        assert len(opsoptics.info(name)["doc"]) >= 20
        assert "Raises" in (opsoptics.get(name).__doc__ or ""), name


def test_every_op_is_reachable_from_the_public_tier():
    import fullseye as fs

    for name in sf.__all__:
        assert hasattr(fs.ledger, name), name


def test_the_typed_catalog_declares_the_family():
    import typed_catalog as tc

    rows = {r[0]: r for r in tc.catalog() if r[0] in sf.__all__}
    assert set(rows) == set(sf.__all__)
    assert rows["sfp_normals"][2] == ["polsweep"] and rows["sfp_normals"][3] == "table"
    assert rows["sfp_disambiguate"][2] == ["table"] and rows["sfp_disambiguate"][3] == "normalmap"


def test_the_fuzzer_builds_arguments_that_actually_compute():
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import chain_fuzz as cf

    for name in sf.__all__:
        assert name in cf.OP_ARG_BUILDERS, name
        args, kw = cf.OP_ARG_BUILDERS[name](None, np.random.default_rng(0))
        out = opsoptics.call(name, *args, **kw)
        assert cf.TYPE_CHECKS[opsoptics.info(name)["out"]](out), name


def test_an_unmarked_table_cannot_pose_as_a_candidate_set():
    """Why no new sort: the candidate set travels as a table, and the one op
    that consumes it refuses any table without the sfp_normals mark — so a
    table from another family fails loudly instead of being read as normals."""
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import chain_fuzz as cf

    pool_table = cf.make_generators()["table"](np.random.default_rng(0))
    with pytest.raises(ValueError):
        sf.sfp_disambiguate(pool_table)
    # and the candidate array is never a normalmap: 4-D, so the normalmap predicate rejects it
    assert not cf.TYPE_CHECKS["normalmap"](_cands()["candidates"])
