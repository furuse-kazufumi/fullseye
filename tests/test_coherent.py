# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""コヒーレント結像とスペックル(coherent.py)の 6 op の門。

★この回の規律: **使った式で答え合わせをしない**。真値は次のどれかに限った。

1. **定理(Goodman)**: 完全発達・単一偏光の強度は指数分布(C = 1)、独立な M 本の和は
   M 次のガンマ分布(C = 1/√M)。有限の粗さは「定数の位相子 + **非円形**のガウス雑音」の
   閉形式(円形を仮定した Rice の式では外れる —— それも門にする)。
2. **閉形式(ベッセル関数)**: 位相格子の 0 次だけを通すと強度は ``J0(a)²``、0 と ±1 で
   ``J0² + 4 J1² sin²``。強度の自己相関は ``|2 J1(x)/x|²``(scipy の j1 で独立に書く)。
3. **漸近**: 画素の積分のコントラストは ``πρc² C² → 1``(Goodman の A_c / A)。
4. **指数**: 三角測量の光条中心の標準偏差は λ に +1、sin θ に −1(比例定数は開示のみ)。
5. **厳密な恒等**: 箱で積分した強度の重心 = 強度の重心(画素を大きくしても重心は動かない)。

各門は「物理が違えば落ちる」ことを、壊した相手(違う分布・違う遮断周波数・円形の式)で
同じ検定を当てて確かめる(壊して確かめる門)。
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np
import pytest
from scipy import special

import coherent as co
import opsoptics

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _slope(x, y):
    return float(np.polyfit(np.log(x), np.log(y), 1)[0])


def _block_centroid(img, block):
    """列 ``block`` 本ずつ束ねた光条の重心の行(束ごとに 1 つ)。"""
    ny, nx = img.shape
    nb = nx // block
    b = img[:, : nb * block].reshape(ny, nb, block).sum(axis=2)
    y = np.arange(ny, dtype=float)[:, None]
    return (b * y).sum(axis=0) / b.sum(axis=0)


# --------------------------------------------------------------------------- #
# 1. コヒーレント結像(振幅で線形)
# --------------------------------------------------------------------------- #
def _phase_grating(a, period=16, n=256):
    x = np.arange(n)
    ph = a * np.sin(2 * math.pi * x / period)[None, :] * np.ones((n, 1))
    return np.ones((n, n)), ph, x


def test_a_phase_grating_with_every_order_passed_leaves_no_image():
    A, ph, _ = _phase_grating(1.3)
    I = co.coherent_image(A, ph, cutoff=0.5)
    assert np.max(np.abs(I - 1.0)) < 1e-12


def test_only_the_zeroth_order_gives_the_constant_j0_squared():
    a = 1.3
    A, ph, _ = _phase_grating(a)
    I = co.coherent_image(A, ph, cutoff=0.03)          # 1 次は 1/16 = 0.0625 で瞳の外
    assert np.max(np.abs(I - special.j0(a) ** 2)) < 1e-12
    # 壊して確かめる: インコヒーレントなら位相物体は強度 1 のまま(J0² ではない)
    assert abs(special.j0(a) ** 2 - 1.0) > 0.3


def test_zeroth_and_first_orders_give_the_bessel_fringes():
    a = 0.9
    A, ph, x = _phase_grating(a)
    I = co.coherent_image(A, ph, cutoff=0.1)           # ±1 次(0.0625)は通り、±2 次(0.125)は落ちる
    want = special.j0(a) ** 2 + 4 * special.j1(a) ** 2 * np.sin(2 * math.pi * x / 16) ** 2
    assert np.max(np.abs(I - want[None, :])) < 1e-12


def test_a_user_pupil_equal_to_the_circle_gives_the_same_image():
    rng = np.random.default_rng(0)
    A = rng.random((64, 64))
    ph = rng.uniform(0, 2 * math.pi, (64, 64))
    circ = np.fft.fftshift(co._circ_pupil(64, 64, 0.2))
    assert np.allclose(co.coherent_image(A, ph, cutoff=0.2),
                       co.coherent_image(A, ph, pupil=circ), atol=1e-12)


def test_defocus_keeps_energy_and_changes_the_image():
    rng = np.random.default_rng(1)
    A = rng.random((64, 64))
    I0 = co.coherent_image(A, cutoff=0.25)
    I1 = co.coherent_image(A, cutoff=0.25, defocus_waves=1.0)
    assert abs(I0.sum() - I1.sum()) < 1e-9 * I0.sum()   # 位相だけの瞳は通る光の量を変えない
    assert np.max(np.abs(I0 - I1)) > 1e-3


# --------------------------------------------------------------------------- #
# 2. Goodman の一次統計
# --------------------------------------------------------------------------- #
def test_fully_developed_speckle_is_exponential_with_unit_contrast():
    Cs = []
    for seed in range(3):
        st = co.speckle_statistics(co.speckle_field((512, 512), cutoff=0.1, seed=seed))
        Cs.append(st["contrast"])
        assert st["ks_p_exponential"] > 1e-3, st["ks_p_exponential"]
        assert st["ks_n"] > 1500
    assert abs(np.mean(Cs) - 1.0) < 0.03, Cs


@pytest.mark.parametrize("pol,n", [(2, 1), (1, 4), (2, 4)])
def test_sums_of_independent_patterns_are_gamma_with_contrast_one_over_root_m(pol, n):
    M = pol * n
    st = co.speckle_statistics(co.speckle_field((512, 512), cutoff=0.1, polarizations=pol,
                                                n_patterns=n, seed=10 + M))
    assert abs(st["contrast"] * math.sqrt(M) - 1.0) < 0.03, st["contrast"]
    assert st["ks_p_gamma"] > 1e-3
    # 壊して確かめる: 同じ標本を指数分布と比べると KS は確実に拒む(検定に力がある)
    assert st["ks_p_exponential"] < 1e-6
    assert co.speckle_reduction(n_patterns=n, polarizations=pol)["contrast"] == pytest.approx(
        1 / math.sqrt(M), rel=1e-15)


@pytest.mark.parametrize("sigma", [0.6, 1.0, 1.5])
def test_finite_roughness_follows_the_non_circular_closed_form(sigma):
    """定数の位相子 m = e^{-σ²/2} + 拡散成分(分散 (1-m²)f、擬分散 (e^{-2σ²}-m²)f)。"""
    n, c = 512, 0.1
    meas = []
    for seed in range(3):
        I = co.speckle_field((n, n), cutoff=c, roughness_rad=sigma, seed=seed)
        meas.append(I.std() / I.mean())
    f = co._circ_pupil(n, n, c).sum() / n / n
    m2 = math.exp(-sigma ** 2)
    Id, p = (1 - m2) * f, (math.exp(-2 * sigma ** 2) - m2) * f
    C_true = math.sqrt(Id ** 2 + p ** 2 + 2 * m2 * (Id + p)) / (m2 + Id)
    C_circ = math.sqrt(Id ** 2 + 2 * m2 * Id) / (m2 + Id)       # 円形を仮定した Rice の式
    assert abs(np.mean(meas) / C_true - 1) < 0.05, (np.mean(meas), C_true)
    if sigma <= 1.0:
        assert abs(np.mean(meas) / C_circ - 1) > 0.2      # 壊して確かめる: 円形の式では外れる


# --------------------------------------------------------------------------- #
# 3. 粒径(二次統計)
# --------------------------------------------------------------------------- #
def test_speckle_size_scales_as_one_over_the_pupil_radius():
    cuts = np.array([0.05, 0.07, 0.1, 0.14, 0.2])
    fw = np.array([np.mean([co.speckle_statistics(co.speckle_field((512, 512), cutoff=c, seed=s))
                            ["speckle_fwhm_px"] for s in range(2)]) for c in cuts])
    assert abs(_slope(cuts, fw) + 1.0) < 0.05, _slope(cuts, fw)
    # 絶対値: 円形瞳の |2 J1(x)/x|² の半値全幅 0.5145/ρc
    assert np.max(np.abs(fw / (co.FWHM_PER_INV_CUTOFF / cuts) - 1)) < 0.03, fw


def test_the_intensity_autocorrelation_is_the_airy_amplitude_squared():
    c = 0.1
    acc = None
    for s in range(4):
        st = co.speckle_statistics(co.speckle_field((512, 512), cutoff=c, seed=s))
        acc = st["acf"] if acc is None else acc + st["acf"]
    acf = acc / 4
    r = st["acf_lag_px"]
    keep = r <= 2 * 0.61 / c * 1.6                         # 中心の峰と最初の側帯まで

    def airy2(cc):
        x = 2 * math.pi * cc * r[keep]
        with np.errstate(invalid="ignore", divide="ignore"):
            mu = np.where(x > 0, 2 * special.j1(x) / np.where(x > 0, x, 1), 1.0)
        return mu ** 2

    assert np.max(np.abs(acf[keep] - airy2(c))) < 0.02
    # 壊して確かめる: 遮断周波数が 1 割違う瞳の形とは合わない
    assert np.max(np.abs(acf[keep] - airy2(1.1 * c))) > 0.04
    assert np.max(np.abs(acf[keep] - airy2(0.9 * c))) > 0.04


# --------------------------------------------------------------------------- #
# 4. 画素の積分(Goodman の積分スペックル)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("cutoff", [0.25, 0.5, 1.0])
def test_pixel_integration_lowers_contrast_as_the_exact_integral_says(cutoff):
    pred = co.speckle_reduction(cutoff=cutoff)["contrast_pixel"]
    meas = np.mean([co.speckle_field((128, 128), cutoff=cutoff, pixel_oversample=16, seed=s).std()
                    for s in range(3)])          # 平均は 1 に正規化してある(期待値)
    assert abs(meas / pred - 1) < 0.03, (meas, pred)
    assert pred < 0.95                                    # 点標本(C = 1)とは区別できる


def test_the_pixel_integral_tends_to_goodmans_correlation_area():
    """ρc ≫ 1(画素に粒がたくさん)で C² → A_c / A = 1/(π ρc²)。下から単調に近づく。"""
    v = [math.pi * c * c * co.speckle_reduction(cutoff=c)["contrast_pixel"] ** 2
         for c in (4.0, 16.0, 64.0)]
    assert v[0] < v[1] < v[2] < 1.0
    assert abs(v[2] - 1) < 0.02, v


# --------------------------------------------------------------------------- #
# 5. 三角測量のスペックルの床
# --------------------------------------------------------------------------- #
_LINE = dict(shape=(160, 2040), pixel_um=1.0, line_width_um=40.0, pixel_oversample=2)
_BLOCK = 40


def _line_errors(lam, sin_u, sin_t, seeds):
    out = []
    ny = _LINE["shape"][0]
    for sd in seeds:
        h = float(np.random.default_rng(1000 + sd).uniform(-15, 15))
        img = co.laser_line_coherent(wavelength_um=lam, sin_u_obs=sin_u, sin_theta=sin_t,
                                     height_um=h, seed=sd, **_LINE)
        z = (_block_centroid(img, _BLOCK) - (ny - 1) / 2) * _LINE["pixel_um"] / sin_t
        out.append(z - h)
    return np.concatenate(out)


def test_lambda_and_sin_u_enter_only_through_their_ratio():
    a = co.laser_line_coherent(wavelength_um=0.5, sin_u_obs=0.1, seed=3, **_LINE)
    b = co.laser_line_coherent(wavelength_um=1.0, sin_u_obs=0.2, seed=3, **_LINE)
    assert np.array_equal(a, b)
    lim = [co.triangulation_speckle_limit(0.5, 0.1, 0.5), co.triangulation_speckle_limit(1.0, 0.2, 0.5)]
    assert lim[0]["delta_z_um"] == pytest.approx(lim[1]["delta_z_um"], rel=1e-15)


def test_the_centroid_floor_scales_with_wavelength_over_aperture():
    """λ を 2 倍(= sin u を半分)にすると光条中心の標準偏差は 2 倍(指数 +1 ± 0.1)。

    ★比例定数(Dorsch の δx に対する実測の比)は約 0.9 で、門にしない(開示のみ)。
    ★細格子の散乱体の密度が粗い(1 粒に 2 点)と指数は 1.13 まで反る(実測)ので、
    ``pixel_oversample=2``(1 粒に 4〜8 点)で測る。
    """
    lams = np.array([0.4, 0.5, 0.63, 0.8])
    sd = np.array([_line_errors(l, 0.1, 1.0, range(20)).std() for l in lams])
    assert abs(_slope(lams, sd) - 1.0) < 0.1, (_slope(lams, sd), sd)
    ratio = sd / np.array([co.triangulation_speckle_limit(l, 0.1, 1.0)["delta_x_um"] for l in lams])
    assert np.all((ratio > 0.6) & (ratio < 1.3)), ratio      # 桁は Dorsch の式どおり


def test_the_height_floor_scales_as_one_over_sin_theta():
    sts = np.array([0.3, 0.5, 0.8])
    sd = np.array([_line_errors(0.5, 0.1, s, range(8)).std() for s in sts])
    assert abs(_slope(sts, sd) + 1.0) < 0.1, (_slope(sts, sd), sd)


def test_bigger_pixels_do_not_move_the_centroid():
    """箱で積分した強度の重心 = 強度の重心(厳密)。画素を 2 倍にしても同じ細格子・同じ重心。"""
    kw = dict(wavelength_um=0.65, sin_u_obs=0.08, line_width_um=30.0, height_um=7.3,
              sin_theta=0.5, seed=5)
    a = co.laser_line_coherent(shape=(96, 400), pixel_um=1.0, pixel_oversample=4, **kw)
    b = co.laser_line_coherent(shape=(48, 200), pixel_um=2.0, pixel_oversample=8, **kw)
    ya = (_block_centroid(a, 40) - (96 - 1) / 2) * 1.0
    yb = (_block_centroid(b, 20) - (48 - 1) / 2) * 2.0
    assert np.max(np.abs(ya - yb)) < 1e-9
    # 一方で見た目のコントラストは下がる(積分スペックル)
    assert b[20:28].std() / b[20:28].mean() < a[40:56].std() / a[40:56].mean()


def test_averaging_frames_of_a_static_part_does_not_help_but_moving_it_does():
    kw = dict(shape=(64, 400), wavelength_um=0.65, sin_u_obs=0.05, pixel_um=2.0,
              line_width_um=30.0, pixel_oversample=2, noise=0.02, height_um=0.0)
    ny = 64

    def err(img):
        return (_block_centroid(img, 20) - (ny - 1) / 2) * 2.0

    one = co.laser_line_coherent(seed=1, noise_seed=0, **kw)
    static = np.mean([co.laser_line_coherent(seed=1, noise_seed=k, **kw) for k in range(100)], axis=0)
    e1, e100 = err(one), err(static)
    r_static = float(np.sqrt(np.mean(e100 ** 2)) / np.sqrt(np.mean(e1 ** 2)))
    assert 0.85 < r_static < 1.1, r_static                 # 100 枚平均しても誤差はほぼそのまま
    # 静止しているので平均の誤差は「雑音なしの同じスペックル」の誤差に一致する
    clean = err(co.laser_line_coherent(seed=1, **{**kw, "noise": 0.0}))
    assert np.sqrt(np.mean((e100 - clean) ** 2)) < 0.2 * np.sqrt(np.mean(clean ** 2))
    # 部品を動かす(毎フレーム別の実現)と 1/√N
    N = 16
    moved = [err(np.mean([co.laser_line_coherent(seed=100 + 50 * t + k, noise_seed=k, **kw)
                          for k in range(N)], axis=0)) for t in range(3)]
    singles = [err(co.laser_line_coherent(seed=900 + t, noise_seed=t, **kw)) for t in range(6)]
    r_moved = float(np.sqrt(np.mean(np.concatenate(moved) ** 2))
                    / np.sqrt(np.mean(np.concatenate(singles) ** 2)))
    assert abs(r_moved * math.sqrt(N) - 1) < 0.3, r_moved


def test_the_closed_form_and_its_parts():
    t = co.triangulation_speckle_limit(0.65, 0.05, 0.5, contrast=1.0)
    assert t["delta_x_um"] == pytest.approx(0.65 / (2 * math.pi * 0.05), rel=1e-15)
    assert t["delta_z_um"] == pytest.approx(t["delta_x_um"] / 0.5, rel=1e-15)
    assert t["speckle_fwhm_um"] == pytest.approx(2 * 1.6163399 / (2 * math.pi) * 0.65 / 0.05, rel=1e-12)
    half = co.triangulation_speckle_limit(0.65, 0.05, 0.5, contrast=0.5)
    assert half["delta_z_um"] == pytest.approx(0.5 * t["delta_z_um"], rel=1e-15)
    # |2 J1(x)/x|² = 1/2 の x(定数の出どころを独立に解く)
    from scipy.optimize import brentq
    x = brentq(lambda v: (2 * special.j1(v) / v) ** 2 - 0.5, 1.0, 2.5)
    assert abs(x - co.X_HALF) < 1e-6


# --------------------------------------------------------------------------- #
# 6. fail-closed
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("call", [
    lambda: co.speckle_field(cutoff=0.0),
    lambda: co.speckle_field(cutoff=-0.1),
    lambda: co.speckle_field(cutoff=0.6),                 # 細格子のナイキストの外
    lambda: co.speckle_field(cutoff=float("nan")),
    lambda: co.speckle_field(polarizations=3),
    lambda: co.speckle_field(n_patterns=0),
    lambda: co.speckle_field(seed=None),
    lambda: co.speckle_field(shape=(2, 2)),
    lambda: co.coherent_image(np.ones((8, 8)), cutoff=0.0),
    lambda: co.coherent_image(-np.ones((8, 8))),
    lambda: co.coherent_image(np.full((8, 8), np.nan)),
    lambda: co.coherent_image(np.ones((8, 8)), pupil=np.zeros((8, 8))),
    lambda: co.coherent_image(np.ones((8, 8)), phase=np.ones((4, 4))),
    lambda: co.coherent_image(np.ones(8)),
    lambda: co.speckle_statistics(np.zeros((32, 32))),
    lambda: co.speckle_statistics(np.ones((32, 32))),
    lambda: co.speckle_statistics(-np.ones((32, 32))),
    lambda: co.speckle_statistics(np.full((32, 32), np.inf)),
    lambda: co.speckle_statistics(np.ones((32, 32)), roi=(0, 4, 0, 4)),
    lambda: co.laser_line_coherent(wavelength_um=0.0),
    lambda: co.laser_line_coherent(wavelength_um=-0.5),
    lambda: co.laser_line_coherent(sin_u_obs=0.0),
    lambda: co.laser_line_coherent(sin_theta=0.0),
    lambda: co.laser_line_coherent(sin_theta=-0.5),
    lambda: co.laser_line_coherent(sin_u_obs=0.9, pixel_um=5.0),   # 細格子のナイキストの外
    lambda: co.laser_line_coherent(height_um=np.ones(3)),
    lambda: co.laser_line_coherent(height_um=float("inf")),
    lambda: co.laser_line_coherent(noise=-1.0),
    lambda: co.triangulation_speckle_limit(wavelength_um=0.0),
    lambda: co.triangulation_speckle_limit(sin_u_obs=0.0),
    lambda: co.triangulation_speckle_limit(sin_theta=0.0),
    lambda: co.triangulation_speckle_limit(sin_theta=1.5),
    lambda: co.triangulation_speckle_limit(contrast=1.5),
    lambda: co.triangulation_speckle_limit(wavelength_um=float("nan")),
    lambda: co.speckle_reduction(n_patterns=0),
    lambda: co.speckle_reduction(cutoff=0.0),
    lambda: co.speckle_reduction(polarizations=True),
])
def test_bad_inputs_are_refused(call):
    with pytest.raises(ValueError):
        call()


# --------------------------------------------------------------------------- #
# 7. 台帳と公開経路
# --------------------------------------------------------------------------- #
def test_the_ledger_lists_every_op_and_nothing_is_missing():
    listed = set(opsoptics.list_ops("coherent"))
    assert listed == set(co.__all__), listed
    assert not opsoptics.missing()
    for name in listed:
        assert opsoptics.info(name)["module"] == "coherent"
        assert len(opsoptics.info(name)["doc"]) >= 20


def test_every_op_is_reachable_from_the_public_tier():
    import fullseye as fs

    for name in co.__all__:
        assert hasattr(fs.ledger, name), name


def test_the_typed_catalog_declares_the_family():
    import typed_catalog as tc

    rows = {r[0]: r for r in tc.catalog() if r[0] in co.__all__}
    assert set(rows) == set(co.__all__)
    assert rows["speckle_statistics"][2] == ["image2d"]
    assert rows["coherent_image"][2] == ["image2d", "image2d"]


def test_the_fuzzer_builds_arguments_that_actually_compute():
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import chain_fuzz as cf

    for name in co.__all__:
        assert name in cf.OP_ARG_BUILDERS, name
        args, kw = cf.OP_ARG_BUILDERS[name](None, np.random.default_rng(0))
        out = opsoptics.call(name, *args, **kw)
        assert cf.TYPE_CHECKS[opsoptics.info(name)["out"]](out), name
