# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Gates for lighttransport (interreflection, direct/global separation, fringe and ToF multipath): truth through independent code.

真値の経路(テストする op とは別のコード):
  * 形態係数: V 溝の板どうしの閉形式 ``1 − sin(θ/2)`` と、核 ``cosθi cosθj / (2r)`` の
    Gauss–Legendre 二重積分(crossed-strings 則とは別の式)。開口への形態係数も同じ積分で。
  * ラジオシティ: 本テストで書いた Neumann 級数のループ、エネルギー収支(入射 = 吸収 + 開口から出る)。
  * 分離: 輸送行列で描いたパターン画像(``render_transport``)と、``n_bounces=0`` の直接光だけの
    描画 —— 分離 op は L_max / L_min しか見ない。
  * 位相: 描いた縞を ``fringe.wrapped_phase``(N ステップ公式)で復号した位相 vs フェーザ和の閉形式。
  * ToF: 時間領域で変調波形を標本化し、4 位相の相関(4-bucket)で復調した位相 vs フェーザ和。
    反射 1 回までの複素ラジオシティは、本テストで経路を 1 本ずつ数えた和と照合。

壊して確かめたこと(2026-10-13、各 1 回): crossed と uncrossed を入れ替える(20 件落ちる)/
形態係数を L_j で割る(5)/ 輸送行列の反射率の掛け忘れ(2)/ 分離の L_g を α で割り忘れ(6)/
予測の大域フェーザに直接を混ぜたまま(6)/ ToF の位相を片道で計算(6)/ 投影の n·d を落とす(6)/
複素ラジオシティの反射ごとの遅れを落とす(2)。
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np
import pytest

import fringe
import lighttransport as lt
import opsoptics

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = 240
WP = 2 * P
BETA = 20.0


def _wrap(a):
    return np.angle(np.exp(1j * a))


@pytest.fixture(scope="module")
def vee90():
    pr = lt.groove_profile("vgroove", P, angle_deg=90.0)
    return pr, lt.transport_matrix_radiosity(pr, 0.85), lt.transport_matrix_radiosity(pr, 0.85, n_bounces=0)


def _truth(tr, dtr):
    white = [np.ones((1, WP))]
    full = lt.render_transport(tr, white, BETA)[0][0]
    direct = lt.render_transport(dtr, white, BETA)[0][0]
    return direct, full - direct


# --------------------------------------------------------------------------- #
# 1. 形態係数: 閉形式・数値積分・相反性・行和
# --------------------------------------------------------------------------- #
def _quad_ff(a1, b1, n1, a2, b2, n2, order=48):
    """核 cosθi cosθj / (2r) の Gauss–Legendre 二重積分 / L1(crossed-strings とは別の式)。"""
    g, w = np.polynomial.legendre.leggauss(order)
    t, wt = 0.5 * (g + 1.0), 0.5 * w
    L1, L2 = np.linalg.norm(b1 - a1), np.linalg.norm(b2 - a2)
    p1 = a1[None, :] + t[:, None] * (b1 - a1)[None, :]
    p2 = a2[None, :] + t[:, None] * (b2 - a2)[None, :]
    d = p2[None, :, :] - p1[:, None, :]
    r = np.linalg.norm(d, axis=-1)
    c1 = (d @ n1) / r
    c2 = -(d @ n2) / r
    k = np.clip(c1, 0, None) * np.clip(c2, 0, None) / (2.0 * r)
    return float((wt[:, None] * wt[None, :] * k).sum() * L2)


@pytest.mark.parametrize("theta", [20.0, 45.0, 60.0, 90.0, 120.0, 160.0])
def test_vgroove_plate_to_plate_matches_the_closed_form(theta):
    pr = lt.groove_profile("vgroove", 64, angle_deg=theta)
    F = lt.form_factors_2d(pr)
    L = pr["lengths"]
    F12 = (L[:32, None] * F[:32, 32:]).sum() / L[:32].sum()
    assert abs(F12 - (1.0 - math.sin(math.radians(theta) / 2.0))) < 1e-12


@pytest.mark.parametrize("shape,kw", [("trough", {"angle_deg": 70.0}), ("fillet", {"angle_deg": 75.0}),
                                      ("vgroove", {"angle_deg": 70.0}),
                                      ("vgroove", {"angle_deg": 100.0, "floor_frac": 0.3}),
                                      ("trough", {"angle_deg": 50.0, "floor_frac": 0.4})])
def test_crossed_strings_match_quadrature_of_the_kernel(shape, kw):
    pr = lt.groove_profile(shape, 40, **kw)
    F = lt.form_factors_2d(pr)
    v, n = pr["vertices"], pr["normals"]
    rng = np.random.default_rng(3)
    worst = 0.0
    for _ in range(40):
        i, j = rng.choice(40, 2, replace=False)
        if abs(int(i) - int(j)) < 3:                # 隣のパッチは頂点で核が特異 —— 閉形式の門で見る
            continue
        q = _quad_ff(v[i], v[i + 1], n[i], v[j], v[j + 1], n[j])
        worst = max(worst, abs(q - F[i, j]))
    assert worst < 1e-11, worst                     # 2026-10-13: 1.2e-14(Gauss–Legendre 48 点)


def test_reciprocity_and_enclosure_rows():
    for shape in ("vgroove", "trough", "fillet"):
        pr = lt.groove_profile(shape, 120)
        tr = lt.transport_matrix_radiosity(pr, 0.5)
        F, Fo, L = tr["form_factors"], tr["opening_form_factors"], pr["lengths"]
        assert np.abs(L[:, None] * F - (L[:, None] * F).T).max() < 1e-14
        assert (F.sum(axis=1) <= 1.0 + 1e-12).all()
        assert np.abs(F.sum(axis=1) + Fo - 1.0).max() < 1e-12
        # 開口への形態係数も別の経路(積分)で: 開口は最後の頂点 → 最初の頂点、法線は下向き(中へ)
        A, B = pr["vertices"][-1], pr["vertices"][0]
        t = (B - A) / np.linalg.norm(B - A)
        n_open = np.array([-t[1], t[0]])
        i = 30
        q = _quad_ff(pr["vertices"][i], pr["vertices"][i + 1], pr["normals"][i], A, B, n_open, order=64)
        # 2026-10-13: 9e-16 / 2e-15 / 2.3e-10(フィレットの床は開口の弦と浅い角で向き合い、積分の収束が遅い)
        assert abs(q - Fo[i]) < 1e-9, (shape, q, Fo[i])


# --------------------------------------------------------------------------- #
# 2. ラジオシティ
# --------------------------------------------------------------------------- #
def test_neumann_series_converges_to_the_matrix_solve(vee90):
    pr, tr, _ = vee90
    rho = tr["albedo"]
    K = rho[:, None] * tr["form_factors"]
    S, term, errs = np.diag(rho), np.diag(rho), []
    for k in range(60):                              # 本テストで書いたループ(op の n_bounces とは別)
        term = K @ term
        S = S + term
        errs.append(np.abs(S - tr["transport"]).max())
    assert all(b <= a + 1e-15 for a, b in zip(errs, errs[1:]))
    assert errs[-1] < 1e-12
    g = tr["gain_bound"]
    assert g < 1.0
    for k in (0, 3, 10):
        tk = lt.transport_matrix_radiosity(pr, 0.85, n_bounces=k)["transport"]
        # 打ち切り誤差の上界 ρ g^(k+1)/(1−g)(行和ノルム)
        assert np.abs(tk - tr["transport"]).sum(axis=1).max() <= 0.85 * g ** (k + 1) / (1 - g) + 1e-12


def test_low_albedo_leaves_only_the_direct_light():
    pr = lt.groove_profile("vgroove", 80, angle_deg=60.0)
    assert np.abs(lt.transport_matrix_radiosity(pr, 0.0)["transport"]).max() == 0.0
    ratios = []
    for rho in (0.2, 0.02, 0.002):
        T = lt.transport_matrix_radiosity(pr, rho)["transport"]
        g = (T.sum(axis=1) - rho) / rho                       # 一様照明での 大域 / 直接
        ratios.append(g.max())
    assert ratios[1] < 0.11 * ratios[0] and ratios[2] < 0.101 * ratios[1]     # ρ に比例して 0 へ


def test_energy_balance_input_equals_absorbed_plus_escaped(vee90):
    pr, tr, _ = vee90
    L, rho, F, Fo = pr["lengths"], tr["albedo"], tr["form_factors"], tr["opening_form_factors"]
    E = np.random.default_rng(1).uniform(0.2, 1.0, P)
    B = tr["transport"] @ E
    H = F @ B                                                  # 他のパッチからの照度
    power_in = (L * E).sum()
    absorbed = (L * (1.0 - rho) * (E + H)).sum()
    escaped = (L * B * Fo).sum()
    assert abs(power_in - absorbed - escaped) < 1e-12 * power_in


# --------------------------------------------------------------------------- #
# 3. 直接・大域の分離
# --------------------------------------------------------------------------- #
def _sep_err(tr, d, g, period, fill=0.5):
    pats = lt.high_frequency_patterns((1, WP), period, fill=fill)
    s = lt.separate_direct_global(lt.render_transport(tr, pats, BETA), fill=fill)
    return (np.sqrt(np.mean((s["direct"][0] - d) ** 2)) / d.mean(),
            np.sqrt(np.mean((s["global"][0] - g) ** 2)) / g.mean())


def test_separation_matches_the_transport_truth_and_improves_with_frequency(vee90):
    """Measured 2026-10-13 (90° V, ρ 0.85, projector 2 px per patch):
    period 128/64/32/16/8 → direct RMS 12.1/8.5/5.8/3.7/1.35 % of the mean,
    global 35/24/17/10.5/3.9 %; period 4 → 53 % / 152 % (the resolution floor)."""
    _, tr, dtr = vee90
    d, g = _truth(tr, dtr)
    errs = [_sep_err(tr, d, g, p) for p in (128, 64, 32, 16, 8)]
    ed, eg = [e[0] for e in errs], [e[1] for e in errs]
    assert all(b < a for a, b in zip(ed, ed[1:])), ed
    assert all(b < a for a, b in zip(eg, eg[1:])), eg
    assert ed[-1] < 0.02 and eg[-1] < 0.05, (ed, eg)
    assert ed[0] > 0.05                                         # 低い周波数では仮定が崩れる(大域が低周波でない)


def test_separation_has_a_resolution_floor(vee90):
    """A pattern whose lit width is narrower than a pixel's projector footprint
    (here up to 2.7 projector px) never lights a pixel fully: L_max is too low."""
    _, tr, dtr = vee90
    d, g = _truth(tr, dtr)
    assert _sep_err(tr, d, g, 4)[0] > 0.3                       # 2026-10-13: 53 %


def test_global_light_is_largest_at_the_vertex(vee90):
    pr, tr, dtr = vee90
    d, g = _truth(tr, dtr)
    frac = g / d
    x = pr["x_centers"]
    # 2026-10-13: 頂点の隣 0.44(投影に正対する左の面)/ 1.29(斜めの右の面)、縁 0.09 / 0.31
    for face in (x < 0, x > 0):
        fx, ff = np.abs(x[face]), frac[face]
        assert ff[np.argmin(fx)] > 4.0 * ff[np.argmax(fx)]
    assert frac.max() > 1.0                                     # 頂点の近くでは大域が直接より明るい


@pytest.mark.parametrize("alpha,b", [(0.5, 0.0), (0.25, 0.0), (0.75, 0.1), (0.5, 0.2)])
def test_both_schemes_invert_their_own_model_exactly(alpha, b):
    rng = np.random.default_rng(5)
    ld, lg = rng.uniform(0.1, 1, (8, 9)), rng.uniform(0.1, 1, (8, 9))
    lg = np.minimum(lg, ld / max(1e-9, 1.0 - 2.0 * alpha) if alpha < 0.5 else lg)   # 補の形は L+ >= L− の画素だけ
    hi = alpha + b * (1 - alpha)
    shift = [ld + hi * lg, b * ld + hi * lg, 0.5 * (1 + b) * ld + hi * lg]      # 部分点灯の画像を 1 枚混ぜる
    s = lt.separate_direct_global(shift, alpha, b, "shift")
    assert np.abs(s["direct"] - ld).max() < 1e-12 and np.abs(s["global"] - lg).max() < 1e-12
    comp = [ld + hi * lg, b * ld + ((1 - alpha) + alpha * b) * lg]               # Nayar ら 式 (8)
    s = lt.separate_direct_global(comp, alpha, b, "complement")
    assert np.abs(s["direct"] - ld).max() < 1e-12 and np.abs(s["global"] - lg).max() < 1e-12


def test_complement_with_unequal_fill_is_ambiguous_where_global_dominates():
    """Nayar et al. pick α = 1/2 so that the lit image is always the brighter one.
    With α = 1/4, a pixel with L_d < (1 − 2α) L_g is brighter when *unlit*: max/min
    then swaps the two and the separation is wrong — a documented limit, not hidden."""
    ld, lg = np.array([[0.1]]), np.array([[1.0]])
    comp = [ld + 0.25 * lg, 0.75 * lg]
    s = lt.separate_direct_global(comp, 0.25, scheme="complement")
    assert abs(float(s["direct"][0, 0]) - 0.1) > 0.1


def test_quarter_fill_stripes_separate_the_rendered_groove(vee90):
    """Measured 2026-10-13: period 16, α = 1/4 → direct 2.5 %, global 12.9 % RMS
    (α = 1/2 at the same period: 3.7 % / 10.5 %) — fewer lit stripes sample the
    global light more coarsely."""
    _, tr, dtr = vee90
    d, g = _truth(tr, dtr)
    ed, eg = _sep_err(tr, d, g, 16, fill=0.25)
    assert ed < 0.03 and eg < 0.15, (ed, eg)


def test_complement_pairs_reproduce_nayar_equation_7_on_the_render(vee90):
    _, tr, dtr = vee90
    d, g = _truth(tr, dtr)
    pats = lt.high_frequency_patterns((1, WP), 8, n_shifts=8, complement=True)
    ims = lt.render_transport(tr, pats, BETA)
    s1 = lt.separate_direct_global(ims, scheme="complement")
    s2 = lt.separate_direct_global(ims, scheme="shift")
    assert np.abs(s1["direct"] - s2["direct"]).max() < 1e-12      # α = 0.5 で 2 つの形は一致
    assert np.sqrt(np.mean((s1["direct"][0] - d) ** 2)) / d.mean() < 0.02


# --------------------------------------------------------------------------- #
# 4. 縞の位相のバイアス
# --------------------------------------------------------------------------- #
def test_phasor_sum_matches_n_step_decoding_of_two_cosines():
    rng = np.random.default_rng(7)
    a1, p1 = rng.uniform(0.5, 1, 50), rng.uniform(-np.pi, np.pi, 50)
    a2, p2 = rng.uniform(0, 1.5, 50), rng.uniform(-np.pi, np.pi, 50)
    r = lt.fringe_multipath_phase_error(a1, p1, a2, p2)
    for N in (3, 4, 7):
        d = 2 * np.pi * np.arange(N) / N
        frames = [(0.6 + 0.3 * (a1 * np.cos(p1 - dn) + a2 * np.cos(p2 - dn)))[None, :] for dn in d]
        ph = fringe.wrapped_phase(frames)[0]
        assert np.abs(_wrap(ph - r["phase"])).max() < 1e-12
    D = p2 - p1
    q = a2 / a1
    assert np.abs(_wrap(r["bias"] - np.arctan2(q * np.sin(D), 1 + q * np.cos(D)))).max() < 1e-12


@pytest.mark.parametrize("ratio", [0.05, 0.3, 0.7, 0.95])
def test_worst_case_bias_is_asin_of_the_ratio(ratio):
    D = np.linspace(-np.pi, np.pi, 200001)
    r = lt.fringe_multipath_phase_error(1.0, 0.0, ratio, D)
    assert abs(np.abs(r["bias"]).max() - math.asin(ratio)) < 1e-9
    assert abs(float(r["worst_case"][0]) - math.asin(ratio)) < 1e-15
    k = int(np.argmax(r["bias"]))
    assert abs(D[k] - (np.pi / 2 + math.asin(ratio))) < 1e-4     # 最悪は Δ = π/2 + asin r


@pytest.mark.parametrize("shape,kw,period", [("vgroove", {"angle_deg": 90.0}, 480.0),
                                             ("vgroove", {"angle_deg": 60.0}, 16.0),
                                             ("vgroove", {"angle_deg": 110.0, "floor_frac": 0.25}, 64.0),
                                             ("trough", {}, 37.5), ("fillet", {}, 8.0)])
def test_predicted_bias_equals_the_bias_decoded_from_rendered_fringes(shape, kw, period):
    pr = lt.groove_profile(shape, P, **kw)
    tr = lt.transport_matrix_radiosity(pr, 0.85)
    dtr = lt.transport_matrix_radiosity(pr, 0.85, n_bounces=0)
    pats = lt.high_frequency_patterns((1, WP), period, kind="sinusoid", n_shifts=5)
    meas = _wrap(fringe.wrapped_phase(lt.render_transport(tr, pats, BETA))[0]
                 - fringe.wrapped_phase(lt.render_transport(dtr, pats, BETA))[0])
    pred = lt.predict_fringe_phase_error(tr, period, BETA, projector_width=WP)
    assert np.abs(_wrap(pred["bias"] - meas)).max() < 1e-12
    assert (np.abs(pred["bias"]) <= pred["worst_case"] + 1e-12).all()


def test_white_lambertian_groove_shows_a_large_height_error_that_shrinks_with_period(vee90):
    """Measured 2026-10-13 (1 mm wide 90° V, 0.5 mm deep, ρ 0.85, β 20°,
    480 projector px): one fringe over the field → height error RMS 73 µm,
    max 180 µm; period 240/64/32/16/8 px → RMS 23.5/3.2/1.1/0.41/0.18 µm."""
    _, tr, _ = vee90
    rms = []
    for p in (480, 240, 64, 32, 16, 8):
        h = lt.predict_fringe_phase_error(tr, p, BETA, projector_width=WP)["height_error"]
        rms.append(float(np.sqrt(np.mean(h ** 2))))
    assert all(b < a for a, b in zip(rms, rms[1:])), rms
    assert rms[0] > 0.05 and rms[4] < 0.001, rms


def test_micro_phase_shifting_cuts_the_error_by_two_orders(vee90):
    _, tr, dtr = vee90
    per = [16.0, 16.5, 15.5]
    pats = lt.high_frequency_patterns((1, WP), per, kind="sinusoid")
    m = lt.micro_phase_decode(lt.render_transport(tr, pats, BETA), per)
    md = lt.micro_phase_decode(lt.render_transport(dtr, pats, BETA), per)
    assert m["synthetic_period"] == 528.0
    err_micro = m["coordinate"][0] - md["coordinate"][0]
    low = lt.high_frequency_patterns((1, WP), float(WP), kind="sinusoid")
    err_conv = _wrap(fringe.wrapped_phase(lt.render_transport(tr, low, BETA))[0]
                     - fringe.wrapped_phase(lt.render_transport(dtr, low, BETA))[0]) * WP / (2 * np.pi)
    rm, rc = np.sqrt(np.mean(err_micro ** 2)), np.sqrt(np.mean(err_conv ** 2))
    assert rc > 100 * rm, (rc, rm)                     # 2026-10-13: 12.8 px vs 0.072 px(178 倍)
    # 直接光だけなら、micro は各パッチの足跡の中心(幾何の真値)を 0.1 px 以内で返す
    pj = lt._projector(lt._profile(vee90[0], "t"), BETA, WP, "t")
    centre = (0.5 * (pj["u"][:-1] + pj["u"][1:]) - pj["u0"]) / pj["pitch"] - 0.5
    assert np.abs(md["coordinate"][0] - centre).max() < 0.1


def test_phase_bias_vanishes_as_albedo_goes_to_zero():
    pr = lt.groove_profile("vgroove", 120, angle_deg=60.0)
    b = [np.abs(lt.predict_fringe_phase_error(lt.transport_matrix_radiosity(pr, r), 240.0, BETA)["bias"]).max()
         for r in (0.5, 0.05, 0.005)]
    assert b[1] < 0.2 * b[0] and b[2] < 0.12 * b[1], b


# --------------------------------------------------------------------------- #
# 5. ToF の多経路
# --------------------------------------------------------------------------- #
def _four_bucket(amps, lengths, f):
    """時間領域: 経路ごとに遅れた正弦の変調を足し、参照との相関を 4 位相で取る(別の経路)。"""
    T = 1.0 / f
    t = np.linspace(0.0, T, 4096, endpoint=False)
    sig = sum(a * (1 + np.cos(2 * np.pi * f * (t - L / lt.C_LIGHT))) for a, L in zip(amps, lengths))
    q = [np.mean(sig * np.cos(2 * np.pi * f * t + k * np.pi / 2)) for k in range(4)]
    return np.mod(np.arctan2(q[3] - q[1], q[0] - q[2]), 2 * np.pi)


@pytest.mark.parametrize("amps,lengths", [([1.0, 0.3], [2.0, 2.5]), ([1.0, 0.8], [5.0, 9.0]),
                                          ([1.0, 0.2, 0.1], [3.0, 3.4, 4.7]), ([1.0], [6.0])])
def test_tof_phasor_sum_matches_four_bucket_demodulation(amps, lengths):
    f = 20e6
    r = lt.tof_multipath_phase(amps, lengths, f)
    assert abs(_wrap(r["phase"] - _four_bucket(amps, lengths, f))) < 1e-9
    assert abs(r["true_depth"] - lengths[0] / 2) < 1e-15


def test_tof_two_path_bias_sign_and_size():
    f = 20e6
    scale = lt.C_LIGHT / (4 * np.pi * f)
    lam = lt.C_LIGHT / f
    dL = np.linspace(0.001, 0.999, 999) * lam               # 余分な経路長 → 位相差 Δ ∈ (0, 2π)
    for q in (0.1, 0.4, 0.8):
        r = lt.tof_multipath_phase(np.array([[1.0], [q]]) * np.ones((2, dL.size)),
                                   np.stack([np.full(dL.size, 4.0), 4.0 + dL]), f)
        D = 2 * np.pi * dL / lam
        assert np.abs(r["bias"] - np.arctan2(q * np.sin(D), 1 + q * np.cos(D)) * scale).max() < 1e-9
        assert (r["bias"][D < np.pi - 1e-6] > 0).all() and (r["bias"][D > np.pi + 1e-6] < 0).all()
        assert abs(np.abs(r["bias"]).max() - math.asin(q) * scale) < 1e-4 * scale
    small = lt.tof_multipath_phase([1.0, 0.1], [4.0, 4.3], f)["bias"]
    big = lt.tof_multipath_phase([1.0, 0.5], [4.0, 4.3], f)["bias"]
    assert 0 < small < big


@pytest.fixture(scope="module")
def corner():
    pr = lt.groove_profile("vgroove", 120, width=4.0, angle_deg=90.0)
    return pr, lt.transport_matrix_radiosity(pr, 0.8)


def test_one_bounce_complex_radiosity_equals_the_explicit_path_sum(corner):
    pr, tr = corner
    cam, f = np.array([0.2, 0.6]), 20e6
    k = 2 * np.pi * f / lt.C_LIGHT
    c, n, rho, F = pr["centers"], pr["normals"], tr["albedo"], tr["form_factors"]
    r = lt.tof_transport_depth(tr, cam, f, n_bounces=1)
    d = cam[None, :] - c
    dist = np.linalg.norm(d, axis=1)
    cos = (n * d).sum(1) / dist
    for i in (5, 40, 60, 100):
        amps = [rho[i] * cos[i] / dist[i]]
        lens = [2 * dist[i]]
        for j in range(len(c)):
            if F[i, j] > 0:
                amps.append(rho[i] * F[i, j] * rho[j] * cos[j] / dist[j])
                lens.append(dist[j] + np.linalg.norm(c[i] - c[j]) + dist[i])
        ref = lt.tof_multipath_phase(amps, lens, f)
        assert abs(_wrap((ref["depth"] - r["depth"][i]) * 2 * k)) < 1e-10
        assert abs(ref["bias"] - r["bias"][i]) < 1e-10


def test_corner_bias_converges_with_bounces_and_vanishes_without_reflection(corner):
    pr, tr = corner
    full = lt.tof_transport_depth(tr, (0.2, 0.6))
    errs = [np.abs(lt.tof_transport_depth(tr, (0.2, 0.6), n_bounces=k)["bias"] - full["bias"]).max()
            for k in (0, 1, 2, 5, 20, 60)]
    assert all(b <= a for a, b in zip(errs, errs[1:])) and errs[-1] < 1e-9, errs
    assert np.abs(full["bias"]).max() > 0.05             # 2026-10-13: 2-D の部屋の隅(4 m、ρ 0.8)で 0.19 m 程度
    dark = lt.transport_matrix_radiosity(pr, 1e-4)
    assert np.abs(lt.tof_transport_depth(dark, (0.2, 0.6))["bias"]).max() < 1e-4
    assert (full["bias"] > 0).mean() > 0.9                # 余分な経路は遠く見せる(Δ ≪ π)


# --------------------------------------------------------------------------- #
# 6. fail-closed
# --------------------------------------------------------------------------- #
_PR = lt.groove_profile("vgroove", 16)
_TR = lt.transport_matrix_radiosity(_PR, 0.5)


@pytest.mark.parametrize("call", [
    lambda: lt.groove_profile("bump"),
    lambda: lt.groove_profile("vgroove", 1),
    lambda: lt.groove_profile("vgroove", 16.0),
    lambda: lt.groove_profile("vgroove", 16, width=0.0),
    lambda: lt.groove_profile("vgroove", 16, width=float("nan")),
    lambda: lt.groove_profile("vgroove", 16, angle_deg=180.0),
    lambda: lt.groove_profile("trough", 16, angle_deg=90.0),
    lambda: lt.groove_profile("vgroove", 16, floor_frac=1.0),
    lambda: lt.groove_profile("fillet", 16, floor_frac=0.0),
    lambda: lt.groove_profile("fillet", 16, angle_deg=89.0),
    lambda: lt.groove_profile("polyline", vertices=[[0, 0], [1, -1], [2, 0]], angle_deg=30.0),
    lambda: lt.groove_profile("fillet", 16, floor_frac=1.0),
    lambda: lt.groove_profile("polyline"),
    lambda: lt.groove_profile("polyline", vertices=[[0, 0], [1, 1], [2, 0]]),        # 凸(山)
    lambda: lt.groove_profile("polyline", vertices=[[0, 0], [0, -1], [1, 0]]),       # x が増えない
    lambda: lt.groove_profile("polyline", vertices=np.zeros((3, 3))),
    lambda: lt.groove_profile("vgroove", 16, vertices=[[0, 0], [1, -1], [2, 0]]),
    lambda: lt.form_factors_2d({"kind": "other"}),
    lambda: lt.form_factors_2d(np.eye(3)),
    lambda: lt.transport_matrix_radiosity(_PR, 1.0),
    lambda: lt.transport_matrix_radiosity(_PR, -0.1),
    lambda: lt.transport_matrix_radiosity(_PR, float("inf")),
    lambda: lt.transport_matrix_radiosity(_PR, np.full(15, 0.5)),
    lambda: lt.transport_matrix_radiosity(_PR, 0.5, n_bounces=-1),
    lambda: lt.transport_matrix_radiosity(_PR, 0.5, n_bounces=2.5),
    lambda: lt.high_frequency_patterns((4, 32), 8, fill=0.0),
    lambda: lt.high_frequency_patterns((4, 32), 8, fill=1.0),
    lambda: lt.high_frequency_patterns((4, 32), 8, fill=0.3),        # 2.4 画素 = 端数
    lambda: lt.high_frequency_patterns((4, 32), 1),
    lambda: lt.high_frequency_patterns((4, 32), 7, kind="checker"),
    lambda: lt.high_frequency_patterns((4, 32), 8.0, kind="sinusoid", n_shifts=2),
    lambda: lt.high_frequency_patterns((4, 32), 2.0, kind="sinusoid"),
    lambda: lt.high_frequency_patterns((4, 32), 8.0, kind="sinusoid", fill=0.25),
    lambda: lt.high_frequency_patterns((4, 32), 8, kind="sinusoid", complement=True),
    lambda: lt.high_frequency_patterns((0, 32), 8),
    lambda: lt.high_frequency_patterns("ab", 8),
    lambda: lt.high_frequency_patterns((4, 32), 8, kind="dots"),
    lambda: lt.render_transport(_PR, [np.ones((1, 32))]),
    lambda: lt.render_transport(_TR, lt.high_frequency_patterns((8, 32), 8, kind="checker")),
    lambda: lt.render_transport(_TR, [np.full((1, 32), 1.5)]),
    lambda: lt.render_transport(_TR, [np.full((1, 32), np.nan)]),
    lambda: lt.render_transport(_TR, []),
    lambda: lt.render_transport(_TR, [np.ones((1, 32))], triangulation_deg=50.0),   # 片面が影
    lambda: lt.render_transport(_TR, [np.ones((1, 32))], triangulation_deg=0.0),
    lambda: lt.render_transport(_TR, [np.ones((1, 32))], black_level=1.0),
    lambda: lt.render_transport(_TR, [np.ones((1, 32))], rows=0),
    lambda: lt.separate_direct_global([np.ones((4, 4))]),
    lambda: lt.separate_direct_global([np.ones((4, 4)), np.ones((4, 5))]),
    lambda: lt.separate_direct_global(np.ones((2, 4, 4)), fill=1.0),
    lambda: lt.separate_direct_global(np.ones((2, 4, 4)), fill=0.0),
    lambda: lt.separate_direct_global(np.ones((2, 4, 4)), black_level=-0.1),
    lambda: lt.separate_direct_global(np.ones((2, 4, 4)), scheme="max"),
    lambda: lt.separate_direct_global(np.full((2, 4, 4), np.inf)),
    lambda: lt.separate_direct_global(np.ones((2, 4))),
    lambda: lt.fringe_multipath_phase_error(0.0, 0.0, 0.5, 1.0),
    lambda: lt.fringe_multipath_phase_error(1.0, 0.0, -0.5, 1.0),
    lambda: lt.fringe_multipath_phase_error(1.0, np.nan, 0.5, 1.0),
    lambda: lt.fringe_multipath_phase_error(np.ones(3), 0.0, np.ones(4), 1.0),
    lambda: lt.fringe_multipath_phase_error(1.0 + 1j, 0.0, 0.5, 1.0),
    lambda: lt.predict_fringe_phase_error(_TR, 2.0),
    lambda: lt.predict_fringe_phase_error(_TR, 16.0, projector_width=1),
    lambda: lt.predict_fringe_phase_error({"kind": "lt_transport"}, 16.0),
    lambda: lt.micro_phase_decode([np.ones((2, 2))] * 12, (16.0,)),
    lambda: lt.micro_phase_decode([np.ones((2, 2))] * 12, (16.0, 16.0, 15.0)),
    lambda: lt.micro_phase_decode([np.ones((2, 2))] * 11, (16.0, 16.5, 15.5)),
    lambda: lt.micro_phase_decode([np.ones((2, 2))] * 12, (16.0, 16.5, 15.5), n_shifts=2),
    lambda: lt.tof_multipath_phase(1.0, 2.0),
    lambda: lt.tof_multipath_phase([0.0, 1.0], [2.0, 3.0]),
    lambda: lt.tof_multipath_phase([1.0, -1.0], [2.0, 3.0]),
    lambda: lt.tof_multipath_phase([1.0, 1.0], [2.0, 0.0]),
    lambda: lt.tof_multipath_phase([1.0, 1.0], [2.0, 3.0, 4.0]),
    lambda: lt.tof_multipath_phase([1.0], [2.0], modulation_hz=0.0),
    lambda: lt.tof_transport_depth(_TR, (0.0, -1.0)),                 # 断面の下
    lambda: lt.tof_transport_depth(_TR, (5.0, 0.5)),                  # 端の外
    lambda: lt.tof_transport_depth(_TR, (0.0, 0.5, 1.0)),
    lambda: lt.tof_transport_depth(_TR, (0.0, 0.5), n_bounces=-2),
    lambda: lt.tof_transport_depth(_TR, (0.0, 0.5), modulation_hz=float("nan")),
])
def test_bad_inputs_are_refused(call):
    with pytest.raises(ValueError):
        call()


# --------------------------------------------------------------------------- #
# 7. 台帳と公開経路
# --------------------------------------------------------------------------- #
def test_the_ledger_lists_every_op_and_nothing_is_missing():
    listed = set(opsoptics.list_ops("light_transport"))
    assert listed == set(lt.__all__), listed
    assert not opsoptics.missing()
    for name in listed:
        assert opsoptics.info(name)["module"] == "lighttransport"
        assert len(opsoptics.info(name)["doc"]) >= 20
        assert "Raises" in (opsoptics.get(name).__doc__ or ""), name


def test_every_op_is_reachable_from_the_public_tier():
    import fullseye as fs

    for name in lt.__all__:
        assert hasattr(fs.ledger, name), name


def test_the_typed_catalog_declares_the_family():
    import typed_catalog as tc

    rows = {r[0]: r for r in tc.catalog() if r[0] in lt.__all__}
    assert set(rows) == set(lt.__all__)
    assert rows["render_transport"][2] == ["table", "images"] and rows["render_transport"][3] == "images"
    assert rows["separate_direct_global"][2] == ["images"] and rows["separate_direct_global"][3] == "table"


def test_the_fuzzer_builds_arguments_that_actually_compute():
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import chain_fuzz as cf

    for name in lt.__all__:
        assert name in cf.OP_ARG_BUILDERS, name
        args, kw = cf.OP_ARG_BUILDERS[name](None, np.random.default_rng(0))
        out = opsoptics.call(name, *args, **kw)
        assert cf.TYPE_CHECKS[opsoptics.info(name)["out"]](out), name


def test_a_foreign_table_cannot_pose_as_a_profile_or_a_transport():
    """Why no new sort: profiles and transports travel as tables carrying a
    kind mark; every consumer refuses an unmarked table, so a table from
    another family fails loudly instead of being read as geometry."""
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import chain_fuzz as cf

    pool_table = cf.make_generators()["table"](np.random.default_rng(0))
    for fn in (lt.form_factors_2d, lt.transport_matrix_radiosity, lt.predict_fringe_phase_error,
               lt.tof_transport_depth):
        with pytest.raises(ValueError):
            fn(pool_table)
    with pytest.raises(ValueError):
        lt.render_transport(pool_table, [np.ones((1, 8))])
