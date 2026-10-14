# -*- coding: utf-8 -*-
"""deflectometry の門: 傾き → 位相 → 傾きの往復、閉形式の感度、高さと傾きの不定性、ガラスの裏面、ピント、fail-closed。

どれも真値を解析式で持つ(平面・ガウスの凹み・球の帽子)。数字は 2026-10-15 の実測(コメントに記す)。
"""
from __future__ import annotations

import math

import numpy as np
import pytest

import deflectometry as D
import fringe
import photometric

RIG = D.deflectometry_rig()
PERIOD, COARSE = 10.0, 160.0


def _grid(n, rig=RIG):
    x = (np.arange(n) - (n - 1) / 2.0) * rig["field_mm"] / (n - 1)
    XX, YY = np.meshgrid(x, x)
    return XX, YY, float(x[1] - x[0])


def _decode(h, sx, sy, rig=RIG, z_ref=0.0, **kw):
    ph = {}
    for d in "xy":
        fine = D.deflectometry_render(h, rig, PERIOD, 4, d, slope_x=sx, slope_y=sy, **kw)
        coarse = D.deflectometry_render(h, rig, COARSE, 4, d, slope_x=sx, slope_y=sy, **kw)
        ph[d] = fringe.absolute_phase(fringe.wrapped_phase(fine), fringe.wrapped_phase(coarse) * (COARSE / PERIOD))
    return D.deflectometry_phase_to_slope(ph["x"], ph["y"], rig, PERIOD, z_ref=z_ref)


def _dimple(XX, YY, dep=3e-3, s=1.2):
    g = np.exp(-(XX ** 2 + YY ** 2) / (2 * s * s))
    return -dep * g, dep * XX / s ** 2 * g, dep * YY / s ** 2 * g


def test_tilted_plane_round_trip_is_exact_when_the_height_is_known():
    XX, YY, _ = _grid(120)
    a, b = 2e-3, -1e-3
    h = a * XX + b * YY
    n = _decode(h, np.full_like(h, a), np.full_like(h, b), z_ref=h)
    p, q = photometric.normals_to_gradients(n)
    assert np.abs(p - a).max() < 1e-6 and np.abs(q - b).max() < 1e-6      # measured 4.2e-7 / 5.2e-8


def test_dimple_slopes_converge_with_the_grid():
    errs = []
    for n in (100, 200, 400):
        XX, YY, _ = _grid(n)
        h, sx, sy = _dimple(XX, YY)
        p, q = photometric.normals_to_gradients(_decode(h, sx, sy, z_ref=h))
        errs.append(max(np.abs(p - sx).max(), np.abs(q - sy).max()))
    assert errs[2] < errs[1] < errs[0]                                     # 7.7e-5 → 2.7e-5 → 7.7e-6
    assert errs[2] < 0.01 * 1.5e-3


def test_curvature_of_a_sphere_cap_is_one_over_r():
    XX, YY, sp = _grid(101)
    R = 5000.0                       # 半径 5 m の椀(上に開いた凹み)
    p, q = XX / R, YY / R
    n = np.dstack([-p, -q, np.ones_like(p)]) / np.sqrt(1 + p * p + q * q)[..., None]
    H = D.slope_to_curvature(n, sp, "mean")
    K = D.slope_to_curvature(n, sp, "gaussian")
    lap = D.slope_to_curvature(n, sp, "laplacian")
    c = (slice(10, -10), slice(10, -10))
    # z = r² / 2R は球でなく放物面: 中心で H = 1/R、K = 1/R²
    assert abs(H[50, 50] * R - 1) < 1e-9 and abs(K[50, 50] * R * R - 1) < 1e-9
    assert np.allclose(lap[c], 2.0 / R, rtol=1e-9)


def test_curvature_marks_invalid_pixels_and_their_neighbours():
    XX, YY, sp = _grid(21)
    n = np.dstack([np.zeros_like(XX), np.zeros_like(XX), np.ones_like(XX)])
    n[10, 10] = np.nan
    k = D.slope_to_curvature(n, sp)
    assert np.isnan(k[9:12, 9:12]).all() and np.isfinite(k[0:8]).all()
    ks = D.slope_to_curvature(n, sp, sigma_px=1.5)
    assert np.isfinite(ks[0:8]).all() and abs(np.nanmax(np.abs(ks))) < 1e-12


def test_phase_noise_and_slope_noise_follow_the_closed_form():
    XX, YY, _ = _grid(200)
    h = np.zeros_like(XX)
    s = D.deflectometry_sensitivity(RIG, PERIOD, 4, 0.004, bits=8)
    clean = fringe.wrapped_phase(D.deflectometry_render(h, RIG, PERIOD, 4, "x"))
    noisy = fringe.wrapped_phase(D.deflectometry_render(h, RIG, PERIOD, 4, "x", noise_sigma=0.004, bits=8, seed=5))
    sphi = np.std(np.angle(np.exp(1j * (noisy - clean)))[5:-5, 5:-5])
    assert 0.93 < sphi / s["phase_noise_rad"] < 1.07                      # measured 1.00
    n = _decode(h, None, None, noise_sigma=0.004, bits=8, seed=5)
    p, _ = photometric.normals_to_gradients(n)
    # 面の格子点をカメラの画素の間で双線形に読む → 標準偏差 × √(4/9)
    assert 0.6 < np.std(p[5:-5, 5:-5]) / s["slope_noise_x"] < 0.8         # measured 0.67


def test_height_offset_shows_up_as_sin_theta_over_d_tilt():
    XX, YY, _ = _grid(101)
    h = np.zeros_like(XX)
    c = 50
    s = D.deflectometry_sensitivity(RIG)
    for dz in (0.1, 0.5):
        p, _ = photometric.normals_to_gradients(_decode(h + dz, None, None))
        assert abs(abs(p[c, c]) / (dz * s["height_slope_coupling"]) - 1) < 0.02   # measured 0.1 %
    # 高さを正しく知らせれば消える
    p, _ = photometric.normals_to_gradients(_decode(h + 0.5, None, None, z_ref=0.5))
    assert abs(p[c, c]) < 1e-7


def test_diffuse_fraction_scales_the_fringe_amplitude():
    h = np.zeros((64, 64))
    m0 = np.median(fringe.modulation(D.deflectometry_render(h, RIG, PERIOD, 4, "x")))
    m8 = np.median(fringe.modulation(D.deflectometry_render(h, RIG, PERIOD, 4, "x", diffuse_fraction=0.8)))
    assert abs(m8 / m0 - 0.2) < 1e-9


def test_scatter_lobe_attenuates_as_a_gaussian_mtf():
    h = np.zeros((32, 32))
    m0 = np.median(fringe.modulation(D.deflectometry_render(h, RIG, PERIOD, 4, "x")))
    sc = 2e-3
    m = np.median(fringe.modulation(D.deflectometry_render(h, RIG, PERIOD, 4, "x", scatter_rad=sc)))
    sigma = 2 * sc * RIG["screen_distance_mm"]
    assert abs(m / m0 - math.exp(-2 * math.pi ** 2 * sigma ** 2 / PERIOD ** 2)) < 0.01


def test_aperture_integration_converges_to_the_disk_mtf_and_screen_focus_is_sharp():
    rig = D.deflectometry_rig(aperture_mm=8.0)
    h = np.zeros((48, 48))
    target = D.deflectometry_sensitivity(rig, PERIOD)["contrast_focus_surface"]
    ana = np.median(fringe.modulation(D.deflectometry_render(h, rig, PERIOD, 4, "x"))) / 0.9
    assert abs(ana - target) < 1e-3
    e16 = abs(np.median(fringe.modulation(D.deflectometry_render(h, rig, PERIOD, 4, "x", aperture_samples=16))) / 0.9 - target)
    e64 = abs(np.median(fringe.modulation(D.deflectometry_render(h, rig, PERIOD, 4, "x", aperture_samples=64))) / 0.9 - target)
    assert e64 < e16 and e64 < 0.01
    sharp = np.median(fringe.modulation(D.deflectometry_render(h, rig, PERIOD, 4, "x", focus="screen"))) / 0.9
    assert sharp > 0.999


def test_glass_back_reflection_follows_the_wedge_closed_form():
    XX, YY, _ = _grid(160)
    h, sx, sy = _dimple(XX, YY)
    n_g = 1.52
    th = math.radians(RIG["incidence_deg"])
    ct = math.cos(math.asin(math.sin(th) / n_g))
    from glassmirror import fresnel_dielectric
    r1 = float(fresnel_dielectric(math.cos(th), 1.0, n_g))
    rb = float(fresnel_dielectric(ct, n_g, 1.0))
    r2 = (1 - r1) * rb * (1 - rb)
    ghost = 2 * n_g * ct / math.cos(th) - 2
    pred = (2 * r1 - ghost * r2) / (2 * (r1 + r2))
    n = _decode(h, sx, sy, back_thickness_mm=0.1, refractive_index=n_g)
    p, _ = photometric.normals_to_gradients(n)
    sel = np.isfinite(p)
    assert abs(np.polyfit(sx[sel], p[sel], 1)[0] - pred) < 0.02             # measured 0.246 / 0.246


def test_screen_pattern_decodes_to_its_own_coordinate():
    pats = D.deflectometry_screen_pattern(RIG, PERIOD, 4, "x")
    assert len(pats) == 4 and pats[0].shape[1] > pats[0].shape[0]
    w = fringe.wrapped_phase(pats)
    sw = RIG["screen_size_mm"][0]
    step = int(math.ceil(round(sw / RIG["screen_pixel_mm"]) / 1024))
    u = (np.arange(0, round(sw / RIG["screen_pixel_mm"]), step) + 0.5) * RIG["screen_pixel_mm"] - sw / 2
    assert np.abs(np.angle(np.exp(1j * (w[0] - 2 * np.pi * u / PERIOD)))).max() < 1e-9
    assert len(D.deflectometry_screen_pattern(RIG, kind="softbox")) == 1


def test_uniform_screen_hides_every_defect():
    XX, YY, _ = _grid(64)
    h, sx, sy = _dimple(XX, YY)
    img = D.deflectometry_render(h, RIG, kind="uniform", slope_x=sx, slope_y=sy)[0]
    assert np.ptp(img) < 1e-12


@pytest.mark.parametrize("kw", [
    dict(diffuse_fraction=1.0), dict(diffuse_fraction=-0.1), dict(focus="lens"), dict(focus=1.5),
    dict(period_mm=0.0), dict(n_steps=2), dict(direction="z"), dict(kind="checker"), dict(bits=0),
    dict(noise_sigma=-1.0), dict(refractive_index=1.0), dict(back_thickness_mm=0.0), dict(aperture_samples=0),
    dict(scatter_rad=-1e-3), dict(slope_x=np.zeros((3, 3))),
])
def test_render_refuses_settings_it_cannot_measure(kw):
    with pytest.raises(ValueError):
        D.deflectometry_render(np.zeros((8, 8)), RIG, **kw)


def test_inputs_are_checked_at_the_boundary():
    with pytest.raises(ValueError):
        D.deflectometry_render(np.zeros((8, 8, 3)), RIG)
    with pytest.raises(ValueError):
        D.deflectometry_render(np.full((8, 8), np.nan), RIG)
    with pytest.raises(ValueError):
        D.deflectometry_rig(incidence_deg=85.0)
    with pytest.raises(ValueError):
        D.deflectometry_rig(field_mm=500.0)
    with pytest.raises(ValueError):
        D.deflectometry_rig(screen_size_mm=(1.0,))
    bad = dict(RIG)
    bad["camera"] = RIG["camera"] * 1.1
    with pytest.raises(ValueError):
        D.deflectometry_phase_to_slope(np.zeros((8, 8)), np.zeros((8, 8)), bad)
    with pytest.raises(ValueError):
        D.deflectometry_phase_to_slope(np.zeros((8, 8)), np.zeros((8, 9)), RIG)
    with pytest.raises(ValueError):
        D.deflectometry_phase_to_slope(np.zeros((8, 8)), np.zeros((8, 8)), RIG, z_ref=np.zeros((3, 3)))
    with pytest.raises(ValueError):
        D.slope_to_curvature(np.dstack([np.zeros((4, 4)), np.zeros((4, 4)), -np.ones((4, 4))]))
    with pytest.raises(ValueError):
        D.slope_to_curvature(np.zeros((4, 4)))
    with pytest.raises(ValueError):
        D.deflectometry_sensitivity(RIG, diffuse_fraction=1.0)


def test_nan_phase_gives_nan_normals_not_garbage():
    XX, YY, _ = _grid(40)
    px = np.zeros_like(XX)
    px[:, :5] = np.nan
    n = D.deflectometry_phase_to_slope(px, np.zeros_like(XX), RIG)
    assert np.isnan(n).any() and np.isfinite(n[:, 20:]).all()


def test_registered_in_the_specular_ledger_with_declared_types():
    import opsspecular
    assert set(opsspecular.list_ops("deflectometry")) == set(D.DEFLECTOMETRY)
    out = opsspecular.call("deflectometry_render", np.zeros((16, 16)))
    assert isinstance(out, list) and all(o.ndim == 2 for o in out)
    nm = opsspecular.call("deflectometry_phase_to_slope", np.zeros((16, 16)), np.zeros((16, 16)))
    assert nm.shape == (16, 16, 3)
    assert opsspecular.call("slope_to_curvature", nm).shape == (16, 16)
    assert isinstance(opsspecular.call("deflectometry_rig"), dict)
