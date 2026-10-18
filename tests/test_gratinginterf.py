# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""gratinginterf の門: 公表の実例、厳密な伝搬との突き合わせ、位相ステップの回収、雑音の下限、
暗視野と散乱の公表式、壊して確かめる探針、fail-closed。

外部の真値:
  * Weitkamp ら 2005(Opt. Express 13, 6296)の装置: 14.4 keV、g1 = 4 µm、d = 23.2 mm(図 4 の説明)。
  * 分数タルボ距離は、格子 1 周期を厳密に伝搬した強度(``optics.angular_spectrum_propagate``)の
    縞の振幅の極大と突き合わせる(閉形式とは別の実装)。
  * 円錐ビームの距離 d' = L·d/(L − d) は、球面波を多数周期の窓で直接伝搬した 1-D の計算と突き合わせる。
  * 位相の雑音は Poisson の下での位相の標準偏差 √2/(V·√(N·a))(N 段、1 枚の平均計数 a)と比べる。
  * 暗視野は、散乱角の分布で縞を実際にぼかした画像列から回収した値を、公表式 exp(−2π²σ²d²/p2²) と
    Strobl の積分(一様分布なら sinc)に比べる。
"""
from __future__ import annotations

import math

import numpy as np
import pytest

import gratinginterf as GI
import optics

HC = GI.HC_KEV_NM


# --------------------------------------------------------------------------- #
# 第 2 の実装: 格子 1 周期の厳密な伝搬                                          #
# --------------------------------------------------------------------------- #
def _period_field(kind, samples=256):
    x = (np.arange(samples) + 0.5) / samples
    inside = x < 0.5
    if kind == "pi":
        return np.where(inside, -1.0 + 0j, 1.0 + 0j)
    if kind == "pi_half":
        return np.where(inside, 1j, 1.0 + 0j)
    return inside.astype(np.complex128)


def _harmonic_visibility(kind, p_um, lam_um, z_um, harmonic, samples=256):
    t = _period_field(kind, samples)
    u = optics.angular_spectrum_propagate(np.vstack([t, t]), wavelength_um=lam_um, distance_um=z_um,
                                          pixel_pitch_um=p_um / samples)
    inten = np.abs(u[0]) ** 2
    spec = np.fft.fft(inten) / samples
    return 2.0 * abs(spec[harmonic]) / spec[0].real


def _harmonic_for(kind):
    return 2 if kind == "pi" else 1


def _argmax_distance(kind, p_um, lam_nm, d_guess_mm, rel_span=0.3, n=121):
    zs = np.linspace(d_guess_mm * (1 - rel_span), d_guess_mm * (1 + rel_span), n)
    vis = [_harmonic_visibility(kind, p_um, lam_nm * 1e-3, z * 1e3, _harmonic_for(kind)) for z in zs]
    k = int(np.argmax(np.round(vis, 9)))
    return zs[k], vis[k], zs[1] - zs[0]


def test_published_worked_example_weitkamp_2005():
    d = GI.talbot_grating_design(4.0, energy_kev=14.4, grating="pi", order=1)
    assert round(d["distance_mm"], 1) == 23.2            # 公表値(図 4 の説明: d = 23.2 mm)
    assert d["analyzer_period_um"] == 2.0 and d["fringe_period_um"] == 2.0
    assert abs(d["wavelength_nm"] - HC / 14.4) < 1e-15
    assert abs(d["talbot_length_mm"] - 2 * 16.0 / (HC / 14.4 * 1e-3) * 1e-3) < 1e-9
    assert abs(d["relative_bandwidth"] - 1.0) < 1e-15    # Δλ/λ = 1/(2m − 1)
    assert abs(GI.talbot_grating_design(4.0, energy_kev=14.4, order=5)["relative_bandwidth"] - 1 / 9) < 1e-15


@pytest.mark.parametrize("kind,order", [("pi", 1), ("pi", 2), ("pi", 3), ("pi_half", 1), ("pi_half", 2),
                                        ("absorption", 1), ("absorption", 2)])
def test_fractional_talbot_distance_matches_exact_propagation(kind, order):
    p, lam_nm = 4.0, HC / 28.0
    d = GI.talbot_grating_design(p, wavelength_nm=lam_nm, grating=kind, order=order)
    span = 0.3 / (2 * order - 1) if kind != "absorption" else 0.2 / order
    z, v, dz = _argmax_distance(kind, p, lam_nm, d["distance_mm"], rel_span=span)
    assert abs(z - d["distance_mm"]) <= dz, (kind, order, z, d["distance_mm"])
    assert abs(v - 4.0 / math.pi) < 1e-3                  # 方形波の基本波の可視度 4/π(縞が完全に結ぶ)
    # 縞の周期: π の格子は 2 次(周期 p/2)、他は 1 次(周期 p)が立つ
    h = _harmonic_for(kind)
    assert abs(d["fringe_period_um"] - p / h) < 1e-12


def test_pi_grating_has_no_fringe_at_the_quarter_distances():
    # 位相 π の格子は d = m·p²/(4λ)(整数倍)で縞が消える(強度が一様)
    p, lam_um = 4.0, HC / 28.0 * 1e-3
    z = p * p / (4 * lam_um)
    assert _harmonic_visibility("pi", p, lam_um, z, 2) < 1e-6


def _cone_visibility_1d(p_um, lam_um, l_mm, z_mm, n_periods=48, spp=128):
    """球面波で照らした位相 π の格子を、多数周期の窓で直接伝搬し、中央の縞の周期と可視度を測る(1-D Fresnel)。"""
    n = n_periods * spp
    dx = p_um / spp
    x = (np.arange(n) - n / 2) * dx
    l_um, z_um = l_mm * 1e3, z_mm * 1e3
    grating = np.where(np.mod(x / p_um, 1.0) < 0.5, -1.0, 1.0)
    u0 = grating * np.exp(1j * math.pi * x * x / (lam_um * l_um))
    fx = np.fft.fftfreq(n, dx)
    u = np.fft.ifft(np.fft.fft(u0) * np.exp(-1j * math.pi * lam_um * z_um * fx * fx))
    inten = np.abs(u) ** 2
    mid = slice(n // 2 - 8 * spp, n // 2 + 8 * spp)
    seg = inten[mid] - inten[mid].mean()
    spec = np.abs(np.fft.rfft(seg * np.hanning(seg.size)))
    k = int(np.argmax(spec[1:])) + 1
    period = seg.size * dx / k
    return float(2 * spec[k] / (np.hanning(seg.size).sum() * inten[mid].mean())), period


def test_cone_beam_distance_and_magnification_match_direct_propagation():
    # 縞の振幅は距離に対して sin のように変わり、極大は平らで位置が測りにくい。そこで鋭い「縞が消える距離」
    # (平面波で z0 = p²/(4λ)、円錐で L·z0/(L − z0))と、極大の距離 d' での縞の周期(= 分析格子の周期)を測る。
    p, lam_um, big_l = 4.0, HC / 28.0 * 1e-3, 300.0
    d = GI.talbot_grating_design(p, wavelength_nm=lam_um * 1e3, grating="pi", source_distance_mm=big_l)
    z0 = p * p / (4 * lam_um) * 1e-3
    z0_cone = big_l * z0 / (big_l - z0)
    zs = np.linspace(z0 * 0.95, z0_cone * 1.05, 81)
    vis = np.array([_cone_visibility_1d(p, lam_um, big_l, z)[0] for z in zs])
    zmin = zs[int(np.argmin(np.round(vis, 9)))]
    assert abs(zmin - z0_cone) <= (zs[1] - zs[0])
    assert abs(zmin - z0) > 10 * (zs[1] - zs[0])          # 平面波の式のままでは外れる(補正が効いている)
    v_at, period = _cone_visibility_1d(p, lam_um, big_l, d["distance_mm"])
    v_plane, _ = _cone_visibility_1d(p, lam_um, big_l, d["distance_plane_mm"])
    assert v_at > 0.9 * 4 / math.pi and v_at > v_plane
    assert abs(period / d["analyzer_period_um"] - 1) < 0.01
    assert abs(d["source_grating_period_um"] - d["analyzer_period_um"] * big_l / d["distance_mm"]) < 1e-12


def test_cone_beam_rejects_source_inside_self_image_distance():
    with pytest.raises(ValueError, match="source_distance_mm"):
        GI.talbot_grating_design(4.0, energy_kev=28.0, source_distance_mm=10.0)


# --------------------------------------------------------------------------- #
# 位相ステップ: 3 像の回収                                                      #
# --------------------------------------------------------------------------- #
def _maps(h=24, w=30):
    yy, xx = np.mgrid[:h, :w]
    t = np.exp(-0.02 * xx)
    phi = 1.2 * np.sin(yy / 4.0) * np.cos(xx / 9.0)
    dfm = 0.3 + 0.6 * np.cos(xx / 8.0) ** 2
    phi0 = 0.8 * xx / w - 0.4 * yy / h
    return t, phi, dfm, phi0


def test_noise_free_retrieval_is_exact_with_different_step_counts():
    t, phi, dfm, phi0 = _maps()
    s = GI.grating_stepping_simulate(t, phi, dfm, n_steps=7, ref_phase_rad=phi0)
    r = GI.grating_stepping_simulate(None, n_steps=5, ref_phase_rad=phi0, shape=t.shape)
    o = GI.grating_three_image_retrieve(s, r)
    assert np.max(np.abs(o["transmission"] - t)) < 1e-12
    assert np.max(np.abs(o["dpc_rad"] - phi)) < 1e-12
    assert np.max(np.abs(o["darkfield"] - dfm)) < 1e-12
    assert o["n_invalid"] == 0 and o["fit_residual_sample"] < 1e-12


def test_inclusive_endpoint_stepping_needs_the_true_step_period():
    # 1 周期の両端を含む走査(N = P + 1)は、P を渡せば厳密、渡さなければ残差が出て読みが狂う
    t, phi, dfm, phi0 = _maps()
    s = GI.grating_stepping_simulate(t, phi, dfm, n_steps=9, steps_per_period=8, ref_phase_rad=phi0)
    r = GI.grating_stepping_simulate(None, n_steps=8, ref_phase_rad=phi0, shape=t.shape)
    good = GI.grating_three_image_retrieve(s, r, steps_per_period_sample=8)
    assert np.max(np.abs(good["dpc_rad"] - phi)) < 1e-12
    bad = GI.grating_three_image_retrieve(s, r)
    assert bad["fit_residual_sample"] > 1e6 * max(good["fit_residual_sample"], 1e-16)
    assert np.nanmax(np.abs(bad["dpc_rad"] - phi)) > 0.05


def test_refraction_angle_from_geometry():
    g = GI.talbot_grating_design(4.0, energy_kev=14.4)
    # 設計 op の出力と**独立**に、教科書の閉形式をここで書き下す(位相 π の格子、m = 1、平面波):
    #   λ = hc / E(hc = 12.398419843 keV·Å)、d = (m − 1/2) p1² / (4λ)、p2 = p1 / 2(Weitkamp ら 2005 の式 2)
    lam_um = 12.398419843 / 14.4 * 1e-4
    d_ind_mm = 0.5 * 4.0 ** 2 / (4.0 * lam_um) * 1e-3
    p2_ind_um = 4.0 / 2.0
    assert g["distance_mm"] == pytest.approx(d_ind_mm, rel=1e-6)
    assert g["analyzer_period_um"] == pytest.approx(p2_ind_um, rel=1e-12)
    assert d_ind_mm == pytest.approx(23.2, abs=0.05)                                # 公表値(図 4 の装置): 23.2 mm、2 µm
    alpha_urad = 0.5
    # 順方向も逆変換も、設計 op ではなく独立に求めた d・p2 で行う(op の比が両辺で相殺して通ることを避ける)
    phi = 2 * math.pi * d_ind_mm * 1e3 * alpha_urad * 1e-6 / p2_ind_um
    s = GI.grating_stepping_simulate(dpc_rad=np.full((4, 4), phi))
    r = GI.grating_stepping_simulate(shape=(4, 4))
    o = GI.grating_three_image_retrieve(s, r, distance_mm=d_ind_mm, analyzer_period_um=p2_ind_um)
    assert np.max(np.abs(o["refraction_urad"] - alpha_urad)) < 1e-12
    # 設計 op の d・p2 で逆変換しても同じ角度になる(op の比が正しいことの確認)
    o2 = GI.grating_three_image_retrieve(s, r, distance_mm=g["distance_mm"], analyzer_period_um=g["analyzer_period_um"])
    assert np.max(np.abs(o2["refraction_urad"] - alpha_urad)) < 1e-5


def test_phase_noise_matches_poisson_limit():
    n, v0, flux = 8, 0.3, 400.0
    s = GI.grating_stepping_simulate(np.ones((64, 64)), n_steps=n, ref_visibility=v0, flux=flux, seed=11)
    r = GI.grating_stepping_simulate(shape=(64, 64), n_steps=n, ref_visibility=v0)   # 雑音なしの基準
    o = GI.grating_three_image_retrieve(s, r)
    sd = float(np.std(o["dpc_rad"]))
    predicted = math.sqrt(2.0) / (v0 * math.sqrt(n * flux))
    assert 0.9 < sd / predicted < 1.1, (sd, predicted)


# --------------------------------------------------------------------------- #
# 暗視野と散乱                                                                  #
# --------------------------------------------------------------------------- #
def _scattered_stack(dist_angles_urad, weights, d_mm, p2_um, n=8, v0=0.3):
    """散乱角の分布(角度と重み)で、縞を実際に横ずらしして足し合わせた画像列(1 画素)。"""
    delta = 2 * math.pi * np.arange(n) / n
    w = np.asarray(weights, float) / np.sum(weights)
    shift = 2 * math.pi * d_mm * 1e3 * np.asarray(dist_angles_urad) * 1e-6 / p2_um
    curve = np.sum(w[:, None] * (1 + v0 * np.cos(shift[:, None] - delta[None, :])), axis=0)
    return curve[:, None, None]


@pytest.mark.parametrize("sigma_urad", [0.5, 1.5, 3.0])
def test_darkfield_gaussian_scattering_matches_published_formula(sigma_urad):
    d_mm, p2 = 23.2, 2.0
    th = np.linspace(-8 * sigma_urad, 8 * sigma_urad, 4001)
    s = _scattered_stack(th, np.exp(-0.5 * (th / sigma_urad) ** 2), d_mm, p2)
    r = _scattered_stack([0.0], [1.0], d_mm, p2)
    dfm = float(GI.grating_three_image_retrieve(s, r)["darkfield"][0, 0])
    rel = GI.darkfield_scatter_relation(sigma_urad=sigma_urad, distance_mm=d_mm, analyzer_period_um=p2)
    assert abs(dfm - rel["darkfield"]) < 1e-6
    back = GI.darkfield_scatter_relation(darkfield=dfm, distance_mm=d_mm, analyzer_period_um=p2)
    assert abs(back["sigma_urad"] / sigma_urad - 1) < 1e-4


def test_darkfield_uniform_scattering_follows_strobl_integral_not_gaussian():
    # 一様分布 [−a, a] なら V/V0 = sinc(2π d a/p2)(Strobl の積分)。散乱が弱いうちは sinc ≈ exp(−x²/6) で
    # ガウスと見分けがつかないが、x = 2.2 rad まで広げると、ガウスの式で直した σ は分布の標準偏差 a/√3 と
    # 一致しない —— σ はガウス近似の量であることを門で固定する。
    d_mm, p2, a = 23.2, 2.0, 30.0
    th = -a + (np.arange(8000) + 0.5) * (2 * a / 8000)   # 中点則(端点を重く数えない)
    s = _scattered_stack(th, np.ones_like(th), d_mm, p2)
    r = _scattered_stack([0.0], [1.0], d_mm, p2)
    dfm = float(GI.grating_three_image_retrieve(s, r)["darkfield"][0, 0])
    x = 2 * math.pi * d_mm * 1e3 * a * 1e-6 / p2
    assert abs(dfm - math.sin(x) / x) < 1e-4
    sig = GI.darkfield_scatter_relation(darkfield=dfm, distance_mm=d_mm, analyzer_period_um=p2)["sigma_urad"]
    assert abs(sig / (a / math.sqrt(3)) - 1) > 0.05


def test_darkfield_relation_diffusion_and_correlation_length():
    r = GI.darkfield_scatter_relation(sigma_urad=2.0, distance_mm=23.2, analyzer_period_um=2.0,
                                      thickness_mm=4.0, wavelength_nm=HC / 14.4)
    assert abs(r["diffusion_coeff_urad2_per_mm"] - 1.0) < 1e-12
    assert abs(r["correlation_length_um"] - (HC / 14.4 * 1e-3) * 23200 / 2.0) < 1e-12
    arr = GI.darkfield_scatter_relation(darkfield=np.array([0.5, 1.2, 0.0, 1.0]))
    assert arr["n_invalid"] == 2 and np.isnan(arr["sigma_urad"][1]) and np.isnan(arr["sigma_urad"][2])
    assert arr["sigma_urad"][3] == 0.0


# --------------------------------------------------------------------------- #
# 壊して確かめる探針                                                            #
# --------------------------------------------------------------------------- #
def test_probe_wrong_talbot_formula_is_caught_by_the_propagation_gate():
    # 位相 π の格子に、よくある取り違え(吸収格子の d = p²/λ や、1/8 を落とした p²/(4λ))を入れると、
    # 厳密な伝搬の極大と合わない —— 上の門がこの取り違えを本当に捕まえられることを確かめる。
    p, lam_nm = 4.0, HC / 28.0
    right = GI.talbot_grating_design(p, wavelength_nm=lam_nm)["distance_mm"]
    for wrong in (p * p / (lam_nm * 1e-3) * 1e-3, p * p / (4 * lam_nm * 1e-3) * 1e-3):
        v_wrong = _harmonic_visibility("pi", p, lam_nm * 1e-3, wrong * 1e3, 2)
        v_right = _harmonic_visibility("pi", p, lam_nm * 1e-3, right * 1e3, 2)
        assert v_wrong < 0.5 * v_right


def test_probe_reversed_step_order_flips_the_phase_sign():
    t, phi, dfm, phi0 = _maps()
    s = GI.grating_stepping_simulate(t, phi, dfm, n_steps=8, ref_phase_rad=phi0)
    r = GI.grating_stepping_simulate(None, n_steps=8, ref_phase_rad=phi0, shape=t.shape)
    rev = GI.grating_three_image_retrieve(np.roll(s[::-1], 1, axis=0), np.roll(r[::-1], 1, axis=0))
    assert np.max(np.abs(rev["dpc_rad"] + phi)) < 1e-12      # 向きを逆にすると符号が反転する
    assert np.max(np.abs(rev["darkfield"] - dfm)) < 1e-12    # 振幅は向きに依らない


def test_probe_swapped_sample_and_reference_is_visible():
    t, phi, dfm, phi0 = _maps()
    s = GI.grating_stepping_simulate(t, phi, dfm, ref_phase_rad=phi0)
    r = GI.grating_stepping_simulate(None, ref_phase_rad=phi0, shape=t.shape)
    sw = GI.grating_three_image_retrieve(r, s)
    assert np.nanmax(sw["darkfield"]) > 1.0 + 0.5            # 取り違えると暗視野が 1 を超える(物理的にありえない)


# --------------------------------------------------------------------------- #
# fail-closed                                                                  #
# --------------------------------------------------------------------------- #
def test_fail_closed():
    with pytest.raises(ValueError):
        GI.talbot_grating_design(4.0, wavelength_nm=0.05, energy_kev=28.0)
    with pytest.raises(ValueError):
        GI.talbot_grating_design("4")
    with pytest.raises(ValueError):
        GI.talbot_grating_design(4.0, grating="sinusoid")
    with pytest.raises(ValueError):
        GI.talbot_grating_design(4.0, order=0)
    with pytest.raises(ValueError, match="at least 3"):
        GI.grating_three_image_retrieve(np.ones((2, 4, 4)), np.ones((2, 4, 4)))
    with pytest.raises(ValueError, match="no pixel"):
        GI.grating_three_image_retrieve(np.ones((4, 4, 4)), np.ones((4, 4, 4)))
    with pytest.raises(ValueError, match="differ in size"):
        GI.grating_three_image_retrieve(np.ones((4, 4, 4)), np.ones((4, 5, 4)))
    with pytest.raises(ValueError, match="condition number"):
        GI.grating_three_image_retrieve(GI.grating_stepping_simulate(n_steps=3, steps_per_period=300),
                                        GI.grating_stepping_simulate(n_steps=4),
                                        steps_per_period_sample=300)
    with pytest.raises(ValueError):
        GI.grating_stepping_simulate(darkfield=np.full((4, 4), 1.2))
    with pytest.raises(ValueError):
        GI.grating_stepping_simulate(transmission=np.full((4, 4), -0.1))
    with pytest.raises(ValueError):
        GI.grating_stepping_simulate(np.ones((4, 4)), dpc_rad=np.zeros((4, 5)))
    with pytest.raises(ValueError):
        GI.darkfield_scatter_relation(darkfield=1.2)
    with pytest.raises(ValueError):
        GI.darkfield_scatter_relation(darkfield=0.5, sigma_urad=1.0)
    with pytest.raises(ValueError):
        GI.darkfield_scatter_relation(sigma_urad=-1.0)


def test_registered_in_optics_ledger():
    import opsoptics
    names = ["talbot_grating_design", "grating_stepping_simulate", "grating_three_image_retrieve",
             "darkfield_scatter_relation", "talbot_carpet", "talbot_source_visibility",
             "grating_step_period_estimate", "dpc_integrate"]
    assert sorted(opsoptics.list_ops("grating_interf")) == sorted(names) == sorted(GI.__all__)
    assert opsoptics.missing() == []


# --------------------------------------------------------------------------- #
# タルボ絨毯(talbot_carpet)                                                    #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("kind", ["pi", "pi_half", "absorption"])
def test_carpet_visibility_matches_sampled_angular_spectrum(kind):
    # 第 2 の実装: 1 周期を 256 点で標本化した場を ``optics.angular_spectrum_propagate`` で伝搬(FFT の厳密な伝搬)。
    # 絨毯は係数の閉形式と次数の和(標本化しない)。縞の可視度を 5 つの距離で比べる。
    p, lam_nm = 4.0, HC / 28.0
    c = GI.talbot_carpet(p, wavelength_nm=lam_nm, grating=kind, n_z=6, z_max_mm=0.5 * 2 * p * p / (lam_nm * 1e-3) * 1e-3)
    zs, vs = c["z_mm"][1:], c["visibility"][1:]
    assert len(zs) == len(vs) == 5
    for z, v in zip(zs, vs):
        ref = _harmonic_visibility(kind, p, lam_nm * 1e-3, z * 1e3, c["fringe_harmonic"])
        assert abs(v - ref) < 2e-3, (kind, z, v, ref)


def test_carpet_paraxial_self_image_and_half_period_shift_are_exact():
    # 近軸の Fresnel では z_T = 2p²/λ で強度が z = 0 と同じ、z_T/2 で半周期ずれた像(Rayleigh 1881 の自己像)
    c = GI.talbot_carpet(4.0, energy_kev=28.0, grating="absorption", model="paraxial", n_z=3, n_x=64, n_periods=2)
    i0, ih, it = c["intensity"]
    assert np.max(np.abs(it - i0)) < 1e-12
    assert np.max(np.abs(ih - np.roll(i0, 32))) < 1e-12
    assert np.max(np.abs(ih - i0)) > 0.3                     # 探針: ずらさないと合わない(門が空でない)


def test_carpet_closed_form_zeros_and_maxima():
    # 吸収格子(開口 1/2)は z_T/4 で 1 次の縞が厳密に消える(2 つの半周期ずれの像が隙間なく並ぶ)。
    # 位相 π の格子は z = 0 で縞が無く(純粋な位相)、(m − 1/2)p²/(4λ) で 4/π の極大。
    a = GI.talbot_carpet(4.0, energy_kev=28.0, grating="absorption", model="paraxial", n_z=5)
    assert a["visibility"][1] < 1e-12 and abs(a["visibility"][2] - 4 / math.pi) < 1e-4
    c = GI.talbot_carpet(4.0, energy_kev=28.0, grating="pi", model="paraxial", n_z=1601)
    assert c["visibility"][0] < 1e-4
    dz = c["z_mm"][1] - c["z_mm"][0]
    v = np.round(c["visibility"], 9)
    peaks = [c["z_mm"][i] for i in range(1, v.size - 1) if v[i] >= v[i - 1] and v[i] > v[i + 1] and v[i] > 1.0]
    assert len(peaks) == len(c["self_image_mm"]) == 8
    assert max(abs(a_ - b_) for a_, b_ in zip(peaks, c["self_image_mm"])) <= dz
    assert abs(float(np.max(c["visibility"])) - 4 / math.pi) < 1e-4


def test_carpet_refuses_paraxial_when_it_is_wrong():
    # 可視光の細かい格子(p = 2 µm、λ = 633 nm)で z_T まで近軸を使うと 1 次の位相が 0.1 rad を超えて狂う
    with pytest.raises(ValueError, match="paraxial"):
        GI.talbot_carpet(2.0, wavelength_nm=633.0, model="paraxial")
    ex = GI.talbot_carpet(2.0, wavelength_nm=633.0, model="exact", n_z=5)
    assert ex["paraxial_phase_error_rad"] > 0.1
    with pytest.raises(ValueError):
        GI.talbot_carpet(4.0, duty=1.0)
    with pytest.raises(ValueError):
        GI.talbot_carpet(4.0, model="fresnel")


# --------------------------------------------------------------------------- #
# 線源の大きさと Lau の条件(talbot_source_visibility)                          #
# --------------------------------------------------------------------------- #
def _incoherent_sum(points_um, weights, d_mm, l_mm, p2_um):
    """第 2 の実装: 線源の点ごとの縞(分析格子の上で −s d/L ずれる)を非干渉に足した 1 次の可視度の比。"""
    ph = 2 * math.pi * (-np.asarray(points_um) * d_mm / l_mm) / p2_um
    w = np.asarray(weights, float)
    return float(abs(np.sum(w * np.exp(1j * ph)) / np.sum(w)))


def test_source_visibility_matches_incoherent_point_sum():
    g = GI.talbot_grating_design(4.0, energy_kev=28.0, source_distance_mm=1200.0)
    d, p2, big_l = g["distance_mm"], g["analyzer_period_um"], 1200.0
    for wd in (10.0, 60.0, 150.0, 400.0):
        xs = -wd / 2 + (np.arange(20000) + 0.5) * wd / 20000
        num = _incoherent_sum(xs, np.ones_like(xs), d, big_l, p2)
        cf = GI.talbot_source_visibility(wd, big_l, d, p2)["visibility_factor"]
        assert abs(num - cf) < 1e-6, (wd, num, cf)
        sig = wd / (2 * math.sqrt(2 * math.log(2)))
        xg = np.linspace(-8 * sig, 8 * sig, 20001)
        num_g = _incoherent_sum(xg, np.exp(-0.5 * (xg / sig) ** 2), d, big_l, p2)
        cf_g = GI.talbot_source_visibility(wd, big_l, d, p2, profile="gaussian")["visibility_factor"]
        assert abs(num_g - cf_g) < 1e-6, (wd, num_g, cf_g)


def test_source_grating_lau_condition_and_detuning_probe():
    g = GI.talbot_grating_design(4.0, energy_kev=28.0, source_distance_mm=1200.0)
    d, p2, big_l, p0 = g["distance_mm"], g["analyzer_period_um"], 1200.0, g["source_grating_period_um"]
    n = 41
    ratios = np.round(np.linspace(0.97, 1.03, 241), 9)
    num, cf = [], []
    for r in ratios:
        pp = p0 * r
        k = np.arange(n) - n // 2
        pts = (k[:, None] * pp + (np.arange(400)[None, :] + 0.5) / 400 * pp / 2 - pp / 4).ravel()
        num.append(_incoherent_sum(pts, np.ones_like(pts), d, big_l, p2))
        cf.append(GI.talbot_source_visibility(n * pp, big_l, d, p2, source_grating_period_um=pp, n_slits=n)
                  ["visibility_factor"])
    num, cf = np.array(num), np.array(cf)
    assert np.max(np.abs(num - cf)) < 1e-5
    best = ratios[int(np.argmax(np.round(cf, 9)))]
    assert abs(best - 1.0) <= ratios[1] - ratios[0]
    assert abs(cf.max() - 2 / math.pi) < 1e-4                 # 開口 1/2 の線源格子の上限 |sinc(π/2)| = 2/π
    # 探針: 周期を 1/開口数 だけずらすと配列の因子が 0(開口の縞が 1 周して打ち消す)
    off = GI.talbot_source_visibility(n * p0, big_l, d, p2, source_grating_period_um=p0 * (1 + 1 / n), n_slits=n)
    assert off["visibility_factor"] < 0.01
    # 線源格子なしでは 2 mm の焦点で縞が消える
    assert GI.talbot_source_visibility(2000.0, big_l, d, p2)["visibility_factor"] < 0.01
    lc = GI.talbot_source_visibility(100.0, big_l, d, p2, wavelength_nm=g["wavelength_nm"])["coherence_length_um"]
    assert abs(lc - g["wavelength_nm"] * 1e-3 * big_l * 1e3 / 100.0) < 1e-12
    with pytest.raises(ValueError):
        GI.talbot_source_visibility(100.0, big_l, d, p2, profile="gaussian", source_grating_period_um=p0)
    with pytest.raises(ValueError):
        GI.talbot_source_visibility(100.0, big_l, d, p2, source_grating_period_um=p0, duty=0.0)


# --------------------------------------------------------------------------- #
# 1 周期のステップ数の推定(grating_step_period_estimate)                       #
# --------------------------------------------------------------------------- #
def test_step_period_estimate_recovers_true_period():
    clean = GI.grating_stepping_simulate(None, n_steps=22, steps_per_period=20.85, shape=(20, 20))
    assert GI.grating_step_period_estimate(clean)["steps_per_period"] == 20.85
    for seed in (1, 2, 3):
        s = GI.grating_stepping_simulate(None, n_steps=22, steps_per_period=20.85, shape=(60, 60), flux=3000.0,
                                         seed=seed, ref_visibility=0.25)
        o = GI.grating_step_period_estimate(s, p_step=0.01)
        assert abs(o["steps_per_period"] - 20.85) <= 0.03, (seed, o["steps_per_period"])
        assert o["residual_at_n"] > o["residual_min"]


def test_probe_normalising_by_the_fitted_mean_biases_the_period():
    # 探針: 残差をあてた平均で割ると(素の平均でなく)、雑音の項が P の一次で傾き、最小が +0.05 段以上ずれる。
    # op がこの偏りを持たないことを、同じ画像列で 2 通りを比べて固定する。
    s = GI.grating_stepping_simulate(None, n_steps=22, steps_per_period=20.85, shape=(60, 60), flux=3000.0,
                                     seed=1, ref_visibility=0.25)
    grid = np.round(np.arange(20.5, 21.2001, 0.01), 9)
    biased = [round(float(np.sqrt(np.mean(GI._sine_fit(s, float(p), "x", "s")[3] ** 2))), 9) for p in grid]
    p_biased = float(grid[int(np.argmin(biased))])
    p_op = GI.grating_step_period_estimate(s, p_step=0.01)["steps_per_period"]
    assert p_biased - 20.85 > 0.04 and abs(p_op - 20.85) <= 0.03, (p_biased, p_op)


def test_step_period_estimate_fail_closed():
    s = GI.grating_stepping_simulate(None, n_steps=22, steps_per_period=20.85, shape=(20, 20))
    with pytest.raises(ValueError, match="edge"):
        GI.grating_step_period_estimate(s, p_min=21.5, p_max=23.0)
    with pytest.raises(ValueError, match="visibility"):
        GI.grating_step_period_estimate(np.full((12, 8, 8), 7.0))
    with pytest.raises(ValueError, match="at least 5"):
        GI.grating_step_period_estimate(s[:4])
    noisy = GI.grating_stepping_simulate(None, n_steps=22, steps_per_period=20.85, shape=(20, 20), flux=3000.0,
                                         seed=5, ref_visibility=0.25)
    with pytest.raises(ValueError, match="flat"):                # 雑音の中で 0.1 段の幅しか振らない
        GI.grating_step_period_estimate(noisy, p_min=20.8, p_max=20.9, p_step=0.01)
    with pytest.raises(ValueError, match="region"):
        GI.grating_step_period_estimate(s, region=(0, 50, 0, 5))
    sub = GI.grating_step_period_estimate(s, region=(2, 10, 3, 12))
    assert sub["steps_per_period"] == 20.85


# --------------------------------------------------------------------------- #
# 微分位相の積分(dpc_integrate)                                                #
# --------------------------------------------------------------------------- #
def _rod(h=6, w=200, r_px=60.0, px=40.0, delta=4e-7):
    """丸棒の投影の厚さ(画素の境界で閉形式)と、画素で平均した屈折角から作った微分位相。"""
    g = GI.talbot_grating_design(4.0, energy_kev=28.0)
    xb = np.arange(w + 1, dtype=float) - 0.5
    tb = 2 * np.sqrt(np.clip(r_px ** 2 - (xb - w / 2) ** 2, 0, None)) * px
    alpha = -delta * np.diff(tb) / px
    phi = np.tile(2 * math.pi * g["distance_mm"] * 1e3 * alpha / g["analyzer_period_um"], (h, 1))
    return g, phi, 0.5 * (tb[1:] + tb[:-1]), px, delta


def test_dpc_integrate_recovers_rod_thickness_exactly():
    g, phi, t_c, px, delta = _rod()
    o = GI.dpc_integrate(phi, px, g["distance_mm"], g["analyzer_period_um"], wavelength_nm=g["wavelength_nm"],
                         delta=delta)
    assert np.max(np.abs(o["thickness_um"] - t_c[None, :])) < 1e-9 * t_c.max()
    # 位相は Φ = −(2π/λ) δ t(閉形式)
    assert np.max(np.abs(o["phase_rad"][0] + 2 * math.pi / (g["wavelength_nm"] * 1e-3) * delta * t_c)) < 1e-6
    # 縦に積分しても同じ(転置)
    o2 = GI.dpc_integrate(phi.T, px, g["distance_mm"], g["analyzer_period_um"], wavelength_nm=g["wavelength_nm"],
                          axis=0, delta=delta)
    assert np.max(np.abs(o2["thickness_um"].T - o["thickness_um"])) < 1e-9


def test_dpc_integrate_baseline_both_removes_a_constant_dpc_offset():
    g, phi, t_c, px, delta = _rod()
    kw = dict(wavelength_nm=g["wavelength_nm"], delta=delta)
    left = GI.dpc_integrate(phi + 0.05, px, g["distance_mm"], g["analyzer_period_um"], **kw)
    both = GI.dpc_integrate(phi + 0.05, px, g["distance_mm"], g["analyzer_period_um"], baseline="both", **kw)
    e_left = float(np.max(np.abs(left["thickness_um"][0] - t_c)) / t_c.max())
    e_both = float(np.max(np.abs(both["thickness_um"][0] - t_c)) / t_c.max())
    assert e_left > 0.3 and e_both < 1e-9, (e_left, e_both)


def test_dpc_integrate_noisy_pipeline_within_three_percent():
    g, phi, t_c, px, delta = _rod(h=40)
    s = GI.grating_stepping_simulate(np.exp(-0.06e-3 * np.tile(t_c, (40, 1))), phi, None, n_steps=8,
                                     ref_visibility=0.25, flux=6000.0, seed=7)
    r = GI.grating_stepping_simulate(None, n_steps=8, ref_visibility=0.25, flux=6000.0, seed=8, shape=phi.shape)
    o = GI.grating_three_image_retrieve(s, r)
    th = GI.dpc_integrate(o, px, g["distance_mm"], g["analyzer_period_um"],          # 3 像の表をそのまま
                          wavelength_nm=g["wavelength_nm"], delta=delta, baseline="both")["thickness_um"]
    err = float(np.max(np.abs(th.mean(axis=0) - t_c)) / t_c.max())
    assert err < 0.03, err


def test_dpc_integrate_refuses_wrapped_phase_and_nan():
    g, phi, t_c, px, delta = _rod()
    wrapped = GI._wrap(phi * 6.0)                              # 本当の |φ| が π を超える(縞の位相を 6 倍)
    assert float(np.max(np.abs(phi * 6.0))) > math.pi
    with pytest.raises(ValueError, match="wrapped"):
        GI.dpc_integrate(wrapped, px, g["distance_mm"], g["analyzer_period_um"], wavelength_nm=g["wavelength_nm"])
    bad = phi.copy()
    bad[2, 50] = np.nan
    with pytest.raises(ValueError, match="NaN"):
        GI.dpc_integrate(bad, px, g["distance_mm"], g["analyzer_period_um"], wavelength_nm=g["wavelength_nm"])
    with pytest.raises(ValueError):
        GI.dpc_integrate(phi, px, g["distance_mm"], g["analyzer_period_um"], baseline="mean")
    with pytest.raises(ValueError, match="wavelength"):           # 位相の尺度 2π/λ に黙った既定値は無い
        GI.dpc_integrate(phi, px, g["distance_mm"], g["analyzer_period_um"])
    with pytest.raises(ValueError, match="dpc_rad"):
        GI.dpc_integrate({"darkfield": phi}, px, g["distance_mm"], g["analyzer_period_um"], energy_kev=28.0)


def test_reference_exposure_ratio_fixes_transmission_only():
    t, phi, dfm, phi0 = _maps()
    s = GI.grating_stepping_simulate(t, phi, dfm, ref_phase_rad=phi0, flux=None)
    r = GI.grating_stepping_simulate(None, ref_phase_rad=phi0, shape=t.shape) * 4.0      # 基準を 4 倍の露光で
    naive = GI.grating_three_image_retrieve(s, r)
    fixed = GI.grating_three_image_retrieve(s, r, reference_exposure=4.0)
    assert np.max(np.abs(naive["transmission"] - 0.25 * t)) < 1e-12
    assert np.max(np.abs(fixed["transmission"] - t)) < 1e-12
    assert np.max(np.abs(naive["darkfield"] - fixed["darkfield"])) < 1e-12
    assert np.max(np.abs(naive["dpc_rad"] - fixed["dpc_rad"])) < 1e-12


def test_source_visibility_refuses_grating_parameters_without_a_grating():
    # duty と n_slits は線源格子の量。周期を渡し忘れた呼び出しを黙って無視しない
    with pytest.raises(ValueError, match="source_grating_period_um"):
        GI.talbot_source_visibility(100.0, 1200.0, 45.0, 2.0, duty=0.3)
    with pytest.raises(ValueError, match="source_grating_period_um"):
        GI.talbot_source_visibility(100.0, 1200.0, 45.0, 2.0, n_slits=5)
    p0 = 2.0 * 1200.0 / 45.0
    a = GI.talbot_source_visibility(5 * p0, 1200.0, 45.0, 2.0, source_grating_period_um=p0, n_slits=5)
    b = GI.talbot_source_visibility(5 * p0, 1200.0, 45.0, 2.0, source_grating_period_um=p0, n_slits=5, duty=0.25)
    assert abs(a["visibility_factor"] - 2 / math.pi) < 1e-12                  # 既定 duty 0.5
    assert abs(b["visibility_factor"] - math.sin(math.pi / 4) / (math.pi / 4)) < 1e-12


def test_step_period_min_visibility_selects_pixels():
    # 縞の弱い列(格子の影)を残差から外す。しきい値で数える画素が変わり、P は同じに戻る
    yy, xx = np.mgrid[:12, :20]
    dfm = np.clip(0.04 + 0.06 * xx, 0.0, 1.0)
    s = GI.grating_stepping_simulate(None, None, dfm, n_steps=10, steps_per_period=10.6)
    lo = GI.grating_step_period_estimate(s, min_visibility=0.02)
    hi = GI.grating_step_period_estimate(s, min_visibility=0.1)
    assert lo["n_pixels"] > hi["n_pixels"] > 0
    assert lo["steps_per_period"] == hi["steps_per_period"] == 10.6
    assert hi["visibility_median"] > lo["visibility_median"]
    with pytest.raises(ValueError, match="no pixel"):
        GI.grating_step_period_estimate(s, min_visibility=0.9)


def test_judgement_constants_are_not_knobs():
    # 平らさの判定と Itoh の条件は数学・判定の定数(つまみにしない)
    import inspect
    assert "min_contrast" not in inspect.signature(GI.grating_step_period_estimate).parameters
    assert "max_jump_rad" not in inspect.signature(GI.dpc_integrate).parameters
    assert GI._ITOH_LIMIT == math.pi and GI._MIN_RESIDUAL_CONTRAST == 1.1
