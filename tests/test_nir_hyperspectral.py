# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""近赤外の分光撮像(2026-10-15)の門: Kubelka–Munk の極限と逆、InGaAs の吸収端、材料表 → 反射率、
帯域の電子数の線形性と雑音、Fisher の帯域選択の閉形式。どれも閉形式か独立の経路で採点する。"""
from __future__ import annotations

import math

import numpy as np
import pytest

import materials as M
import specops as sp
import spectralrad as S


def _at(c, x):
    return float(np.interp(x, c[:, 0], c[:, 1]))


# --------------------------------------------------------------------------- #
# Kubelka–Munk                                                                 #
# --------------------------------------------------------------------------- #
def _flat(alpha, n=11):
    return np.stack([np.linspace(1000.0, 2000.0, n), np.full(n, float(alpha))], axis=1)


def test_km_infinite_layer_matches_the_closed_form_and_its_inverse():
    for alpha, s in ((0.05, 5.0), (1.0, 2.0), (3.0, 0.5)):
        r = S.kubelka_munk_reflectance(_flat(alpha), s, None)[0, 1]
        ks = 2.0 * alpha / s
        assert r == pytest.approx(1.0 + ks - math.sqrt(ks * ks + 2.0 * ks), abs=1e-14)
        assert (1.0 - r) ** 2 / (2.0 * r) == pytest.approx(ks, rel=1e-10)      # K/S = (1 − R∞)²/(2R∞)


def test_km_finite_layer_limits():
    a = _flat(0.4)
    r_inf = S.kubelka_munk_reflectance(a, 3.0, None)[0, 1]
    thick = S.kubelka_munk_reflectance(a, 3.0, thickness_mm=50.0, background_reflectance=0.9)[0, 1]
    assert thick == pytest.approx(r_inf, abs=1e-12)                            # X → ∞
    for X in (0.01, 0.3, 2.0):                                                  # R_g = R∞ → 厚さに依らない
        assert S.kubelka_munk_reflectance(a, 3.0, X, r_inf)[0, 1] == pytest.approx(r_inf, abs=1e-12)
    for X, rg in ((0.2, 0.1), (1.0, 0.7)):                                      # K = 0(Kubelka の式 6)
        sx = 3.0 * X
        exact = (sx * (1 - rg) + rg) / (1 + sx * (1 - rg))
        assert S.kubelka_munk_reflectance(_flat(0.0), 3.0, X, rg)[0, 1] == pytest.approx(exact, abs=1e-12)
        near = S.kubelka_munk_reflectance(_flat(1e-9), 3.0, X, rg)[0, 1]
        assert near == pytest.approx(exact, abs=1e-6)                           # 吸収 → 0 で連続
    # 薄い層は背景が透け、厚くすると R∞ へ単調に近づく(黒い背景の上)
    rs = [S.kubelka_munk_reflectance(a, 3.0, X, 0.0)[0, 1] for X in (0.05, 0.2, 1.0, 5.0)]
    assert all(x < y for x, y in zip(rs, rs[1:])) and rs[-1] <= r_inf + 1e-12


def test_km_refuses_bad_input():
    with pytest.raises(ValueError):
        S.kubelka_munk_reflectance(_flat(-1.0), 3.0)
    with pytest.raises(ValueError):
        S.kubelka_munk_reflectance(_flat(1.0), 0.0)
    with pytest.raises(ValueError):
        S.kubelka_munk_reflectance(_flat(1.0), 3.0, background_reflectance=1.5)
    with pytest.raises(ValueError):
        S.kubelka_munk_reflectance(_flat(1.0), _flat(1.0, 7))                  # 波長が違う散乱の曲線


# --------------------------------------------------------------------------- #
# InGaAs                                                                       #
# --------------------------------------------------------------------------- #
def test_ingaas_edge_is_continuous_and_cuts_off_at_hc_over_eg():
    for cut in (1700.0, 2500.0):
        q = S.ingaas_photodiode_qe(cut, wl_min_nm=800.0, wl_max_nm=2700.0, n_points=19001)
        y = q[:, 1]
        assert np.all(np.isfinite(y)) and y.min() >= 0.0 and y.max() < 1.0
        assert _at(q, cut + 100.0) < 0.05 * y.max()                             # 端の 100 nm 外は 5 % 未満
        assert _at(q, cut - 150.0) > 0.6                                        # 端の手前は高い
    # 直接遷移の √ と Urbach の裾は E_g + E_u/2 で値も傾きも一致する(C¹)
    eg, eu, a, h = 0.74, 0.008, 3.1, 1e-9
    e0 = eg + 0.5 * eu
    f = lambda e: float(S._direct_gap_alpha(np.array([e]), eg, a, eu)[0])
    assert abs(f(e0 - h) - f(e0 + h)) < 1e-6 * f(e0)
    assert abs((f(e0) - f(e0 - h)) / h - (f(e0 + h) - f(e0)) / h) < 1e-3 * (f(e0 + h) - f(e0)) / h
    # 吸収層が厚いほど端の近くの QE が上がる(1 − e^{−αW})
    assert _at(S.ingaas_photodiode_qe(absorber_um=6.0), 1650.0) > _at(S.ingaas_photodiode_qe(absorber_um=1.0), 1650.0)
    # 窓を薄くすると短波長に伸びる
    assert _at(S.ingaas_photodiode_qe(window_um=0.05), 850.0) > 3 * _at(S.ingaas_photodiode_qe(window_um=2.0), 850.0)
    with pytest.raises(ValueError):
        S.ingaas_photodiode_qe(cutoff_nm=900.0, window_cutoff_nm=920.0)


# --------------------------------------------------------------------------- #
# 材料表 → 吸収と反射                                                           #
# --------------------------------------------------------------------------- #
def test_water_comes_from_the_table_and_food_adds_it_by_fraction():
    w = M.material_nir_absorption("WATER", 1400.0, 2000.0, 601)
    assert abs(_at(w, 1450.0) / 3.28 - 1.0) < 0.10                               # Kou 1993: 32.8 /cm
    assert abs(_at(w, 1930.0) / 13.67 - 1.0) < 0.10                              # 136.7 /cm
    dry = M.material_nir_absorption("NUT_KERNEL", water_fraction=0.0)
    wet = M.material_nir_absorption("NUT_KERNEL", water_fraction=0.3)
    ww = M.material_nir_absorption("WATER")
    expect = 0.7 * dry[:, 1] + 0.3 * ww[:, 1]
    assert np.allclose(wet[:, 1], expect, rtol=1e-12, atol=1e-15)
    with pytest.raises(ValueError):
        M.material_nir_absorption("WATER", water_fraction=0.1)
    with pytest.raises(ValueError):
        M.material_nir_absorption("UNOBTAINIUM")


def test_polymer_bands_sit_at_the_measured_troughs():
    """USGS splib の実測(U 印)と論文の実測(L 印): 反射率の谷の位置が ±5 nm に出る。"""
    troughs = {"PE": (1731.0, 1765.0, 2310.0, 2387.0), "PP": (1709.0, 1727.0), "PET": (1662.0,), "PS": (1682.0,)}
    for m, cs in troughs.items():
        r = S.spectral_reflectance_from_material(m, wl_min_nm=1600.0, wl_max_nm=2450.0, n_points=8501)
        for c in cs:
            win = (r[:, 0] > c - 12) & (r[:, 0] < c + 12)
            local = r[win]
            assert abs(local[np.argmin(local[:, 1]), 0] - c) <= 5.0, (m, c)


def test_reflectance_depends_on_grain_size_and_carbon_black_flattens_it():
    coarse = S.spectral_reflectance_from_material("NUT_KERNEL", particle_um=3000.0)
    fine = S.spectral_reflectance_from_material("NUT_KERNEL", particle_um=300.0)
    assert np.all(fine[:, 1] > coarse[:, 1])                                     # 細かい粉ほど明るい
    depth = lambda r: 1.0 - _at(r, 1730.0) / _at(r, 1650.0)
    assert depth(coarse) > depth(fine)                                           # 粗いほど帯が深い
    white = S.spectral_reflectance_from_material("PP")
    black = S.spectral_reflectance_from_material("PP", carbon_black_fraction=0.005)
    depth = lambda r: 1.0 - _at(r, 1727.0) / (0.5 * (_at(r, 1640.0) + _at(r, 1820.0)))   # 連続体に対する帯の深さ
    assert black[:, 1].max() < 0.12 and depth(black) < 0.1 * depth(white)
    n = M.nir_model_info("PP")["n_nir"]
    assert black[:, 1].min() > ((n - 1) / (n + 1)) ** 2                         # 鏡面の Fresnel が床
    # Saunderson の補正を外す(r_s は材料の n で残る): r_i = 0 で R = r_s + (1 − r_s) R_KM
    r0 = S.spectral_reflectance_from_material("PE", thickness_mm=None, internal_reflectance=0.0)
    km = S.kubelka_munk_reflectance(M.material_nir_absorption("PE"), 8.0, None)
    rs = ((1.51 - 1) / 2.51) ** 2
    assert np.allclose(r0[:, 1], rs + (1 - rs) * km[:, 1], atol=1e-14)


# --------------------------------------------------------------------------- #
# 帯域の電子数                                                                  #
# --------------------------------------------------------------------------- #
def test_capture_is_linear_and_the_cube_path_is_the_same_map():
    r1 = S.spectral_reflectance_from_material("NUT_KERNEL")
    r2 = S.spectral_reflectance_from_material("PE")
    c1 = S.hyperspectral_capture(r1)
    c2 = S.hyperspectral_capture(r2)
    mix = np.stack([r1[:, 0], 0.3 * r1[:, 1] + 0.7 * r2[:, 1]], axis=1)
    cm = S.hyperspectral_capture(mix)
    assert np.allclose(cm["electrons"], 0.3 * c1["electrons"] + 0.7 * c2["electrons"], rtol=1e-12)
    ones = np.stack([r1[:, 0], np.ones(len(r1))], axis=1)
    assert np.allclose(S.hyperspectral_capture(ones)["electrons"], c1["white_electrons"], rtol=1e-12)
    assert np.allclose(c1["noise_e"], np.sqrt(c1["electrons"] + 30.0 ** 2))
    # 露光を半分にすると電子数も半分
    half = S.hyperspectral_capture(r1, exposure_s=0.5e-3)
    assert np.allclose(half["electrons"], 0.5 * c1["electrons"], rtol=1e-12)
    cube = np.stack([np.stack([r1[:, 1], r2[:, 1]])] * 2)                        # (2, 2, L)
    out = S.hyperspectral_capture_cube(cube, r1[:, 0], seed=3)
    assert np.allclose(out["clean"][0, 0], c1["electrons"], rtol=1e-12)
    assert np.allclose(out["clean"][1, 1], c2["electrons"], rtol=1e-12)


def test_capture_noise_has_the_emva_variance():
    r = S.spectral_reflectance_from_material("NUT_SHELL")
    wl = r[:, 0]
    cube = np.broadcast_to(r[:, 1], (200, 200, len(wl))).copy()
    kw = dict(band_centers_nm=(1100.0, 1300.0, 1500.0, 1600.0), exposure_s=2e-6)
    out = S.hyperspectral_capture_cube(cube, wl, seed=7, read_noise_e=12.0, **kw)
    ref = S.hyperspectral_capture(r, read_noise_e=12.0, **kw)
    var = out["cube"].reshape(-1, 4).var(axis=0)
    assert np.all(np.abs(var / ref["noise_e"] ** 2 - 1.0) < 0.03)               # 分散 = 平均 + 読出し²
    mean = out["cube"].reshape(-1, 4).mean(axis=0)
    assert np.all(np.abs(mean - ref["electrons"]) < 4 * ref["noise_e"] / 200.0)


def test_capture_refuses_uncovered_bands():
    r = S.spectral_reflectance_from_material("PE", wl_min_nm=1000.0, wl_max_nm=1500.0, n_points=101)
    with pytest.raises(ValueError, match="not covered"):
        S.hyperspectral_capture(r)                                               # 既定の帯は 950〜1650 nm


# --------------------------------------------------------------------------- #
# Fisher の帯域選択                                                             #
# --------------------------------------------------------------------------- #
def test_fisher_two_class_closed_form_and_the_informative_band_wins():
    rng = np.random.default_rng(0)
    H, W, B = 40, 50, 8
    lab = np.zeros((H, W), dtype=int)
    lab[:, 25:] = 1
    lab[:3] = -1                                                                  # 無視する画素
    cube = rng.normal(0.0, 1.0, (H, W, B))
    cube[..., 5] += 3.0 * lab.clip(0)                                             # 帯 5 だけが分ける
    cube[..., 2] += 0.8 * lab.clip(0)                                             # 帯 2 は弱く分ける
    out = sp.spec_band_selection_fisher(cube, lab, n_select=3)
    assert out["single_best"] == 5 and out["selected"][0] == 5
    assert np.all(np.diff(out["criterion"]) >= -1e-12)
    m = lab >= 0
    x0, x1 = cube[..., 2][m & (lab == 0)], cube[..., 2][m & (lab == 1)]
    n0, n1 = x0.size, x1.size
    closed = n0 * n1 / (n0 + n1) * (x0.mean() - x1.mean()) ** 2 / (((x0 - x0.mean()) ** 2).sum() + ((x1 - x1.mean()) ** 2).sum())
    assert out["fisher"][2] == pytest.approx(closed, rel=1e-10)
    # 帯ごとの利得・オフセットに不変(Fisher 比は帯ごとのアフィン変換で変わらない)
    scaled = cube * np.linspace(0.5, 3.0, B) + np.arange(B)
    assert np.allclose(sp.spec_band_selection_fisher(scaled, lab, 3)["fisher"], out["fisher"], rtol=1e-9)
    with pytest.raises(ValueError):
        sp.spec_band_selection_fisher(cube, np.zeros((H, W), dtype=int))          # 1 クラス
    with pytest.raises(ValueError):
        sp.spec_band_selection_fisher(cube, lab, n_select=0)
