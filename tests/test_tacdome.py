# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""tacdome の門(ドーム状の柔らかい指先を平板で押す大変形接触: arXiv:2509.18581 のスケーリング則、式 (3) の読み、連続体の厳密解、Hertz の極限)。

 1. 式 (3) の 3 つの読み: 導出 2n/(1+n) だけが円柱の厳密解・定理 κₙ ≤ κ₁・正の力をすべて満たす(活字とメモは棄却される)
 2. 式 (4) の 3 経路(積分・閉形式・不完全ベータ)、p = ∞ = 非圧縮の半径の伸び
 3. ばね列(中点則の第 2 実装)= 閉形式、係数の当てはめで 2 次 n/(2+n)(活字と一致)
 4. 線形解 = tacsim の Hertz、d → 0 の傾き、普遍形 k = 10/9 ≈ 円柱の最小二乗
 5. 順 ↔ 逆の往復、Hertz の誤差の符号と大きさ(半径から読むと球は 6 % 以内)
 6. 接触像の面積法(副画素の中心 2 つ・雑音)、fail-closed(綴り違い・範囲外・平らな像)
"""
from __future__ import annotations

import math

import numpy as np
import pytest

import tacdome as TD
import tacsim as TS

R = L = 8.0e-3
ES = 4.0e5
SPH = TD.powerlaw_linear_contact("sphere", R, ES)
CONE = TD.powerlaw_linear_contact("cone", 1.0, ES)
PUNCH = TD.powerlaw_linear_contact("punch", R, ES)
DD = np.linspace(0.01, 0.9, 60)


# ── 1. 式 (3) の読み ────────────────────────────────────────────────────────────
def test_derived_reading_matches_neohookean_cylinder_exactly():
    ex = TD.neohookean_cylinder_exact(DD)
    assert np.max(np.abs(TD.largedef_correction(DD, 1.0) / ex["kappa"] - 1)) < 1e-12
    lam = 1 - DD
    assert np.allclose(ex["nominal_stress"], lam ** -2 - lam, rtol=1e-14)            # P = μ(λ⁻² − λ)、μ = 1
    assert np.allclose(ex["cauchy_stress"], ex["nominal_stress"] * lam, rtol=1e-12)    # σ = λP(現在の断面 = A0/λ)


def test_printed_reading_gives_negative_force_and_memo_breaks_the_theorem():
    assert TD.largedef_correction(0.5, 1.0, "printed") == pytest.approx(-5.0 / 3.0, rel=1e-12)
    assert TD.largedef_c1_coefficient(1.5, "printed") == pytest.approx(2.8, rel=1e-12)          # (4+2n)/(1+n)
    memo15, memo1 = TD.largedef_correction(DD, 1.5, "memo"), TD.largedef_correction(DD, 1.0, "memo")
    assert np.any(memo15 > memo1 + 1e-9)                                               # κ₁.₅ > κ₁: 定理違反
    for n in (1.25, 1.5, 2.0):
        assert np.all(TD.largedef_correction(DD, n) <= TD.largedef_correction(DD, 1.0) + 1e-15)


@pytest.mark.parametrize("n", [1.0, 1.5, 2.0])
def test_correction_series_and_positivity(n):
    eps = 1e-7
    assert (TD.largedef_correction(eps, n) - 1) / eps == pytest.approx(2 / (1 + n), rel=1e-5)
    k = TD.largedef_correction(np.linspace(0, 0.99, 200), n)
    assert np.all(k > 0) and np.all(np.diff(k) > 0)                                    # 正で単調増加
    assert TD.largedef_correction(0.0, n) == 1.0


# ── 2. 式 (4) ──────────────────────────────────────────────────────────────────
def test_radius_ratio_three_routes():
    d = np.array([0.02, 0.2, 0.5, 0.8])
    p1 = (2 / (3 * d)) * (1 - (1 - d) ** 1.5) / np.sqrt(1 - d)
    p2 = (np.sqrt(1 - d) / 2 + np.arctan2(np.sqrt(d), np.sqrt(1 - d)) / (2 * np.sqrt(d))) / np.sqrt(1 - d)
    assert np.max(np.abs(TD.largedef_radius_ratio(d, 1.0) - p1)) < 1e-12
    assert np.max(np.abs(TD.largedef_radius_ratio(d, 2.0) - p2)) < 1e-12
    for p in (1.5, 3.0, 20.0, 400.0):
        assert np.max(np.abs(TD.largedef_radius_ratio(d, p) - TD.largedef_radius_ratio(d, p, "beta"))) < 1e-12
    ex = TD.neohookean_cylinder_exact(d)["radius_ratio"]
    assert np.max(np.abs(TD.largedef_radius_ratio(d, math.inf) - ex)) < 1e-15
    assert (TD.largedef_radius_ratio(1e-7, 2.0) - 1) / 1e-7 == pytest.approx(1 / 3, rel=1e-5)


# ── 3. 第 2 実装 ───────────────────────────────────────────────────────────────
@pytest.mark.parametrize("lin", [SPH, CONE, PUNCH], ids=["sphere", "cone", "punch"])
def test_spring_bed_matches_closed_form(lin):
    for d in (0.05, 0.3, 0.5):
        sb = TD.mdr_spring_bed(d * L, L, lin)
        fw = TD.large_deformation_contact(d * L, L, lin)
        assert sb["kappa"] == pytest.approx(fw["kappa"], rel=1e-7)
        assert sb["radius_ratio"] == pytest.approx(fw["radius_ratio"], rel=1e-7)
        assert sb["strain_max"] == pytest.approx(d, rel=1e-6 if lin is PUNCH else 1e-2)
        assert sb["x_deformed"][-1] == pytest.approx(sb["a"], rel=1e-12)


def test_fitted_coefficients_are_derived_linear_and_printed_quadratic():
    ds = np.linspace(0.02, 0.6, 10)
    k = np.array([TD.mdr_spring_bed(x * L, L, SPH, 20000)["kappa"] for x in ds])
    c2, mc1, c0 = np.polyfit(ds, k * (1 - ds) ** 2, 2)
    assert c0 == pytest.approx(1.0, abs=1e-6)
    assert -mc1 == pytest.approx(2 * 1.5 / 2.5, abs=1e-4)                              # 導出 2n/(1+n)
    assert c2 == pytest.approx(1.5 / 3.5, abs=1e-4)                                     # 活字の n/(2+n)


# ── 4. Hertz の極限と普遍形 ────────────────────────────────────────────────────
def test_linear_solution_is_tacsim_hertz():
    for delta in (1e-6, 1e-4, 5e-4):
        F = TS.hertz_force(R, ES, delta=delta)
        assert SPH["C"] * delta ** 1.5 == pytest.approx(F, rel=1e-12)
        assert SPH["D"] * delta ** 0.5 == pytest.approx(TS.hertz_sphere(F, R, ES)["a"], rel=1e-12)
    assert CONE["C"] == pytest.approx(2 * ES / math.pi, rel=1e-12) and CONE["D"] == pytest.approx(2 / math.pi, rel=1e-12)
    assert PUNCH["C"] == pytest.approx(2 * ES * R, rel=1e-12)


def test_universal_k_is_the_cylinder_least_squares():
    dk = np.linspace(1e-3, 0.999, 999)
    k1 = float(np.sum((1 - 1 / TD.largedef_correction(dk, 1.0)) * dk) / np.sum(dk * dk))
    assert abs(k1 / TD.UNIVERSAL_K - 1) < 0.005
    du = np.linspace(0.005, 0.5, 50)
    assert np.max(np.abs(TD.largedef_universal_correction(du) / TD.largedef_correction(du, 1.0) - 1)) < 0.04


# ── 5. 順 ↔ 逆、Hertz の誤差 ───────────────────────────────────────────────────
@pytest.mark.parametrize("lin", [SPH, CONE, PUNCH], ids=["sphere", "cone", "punch"])
def test_forward_inverse_round_trip(lin):
    for d in (0.03, 0.3, 0.6):
        fw = TD.large_deformation_contact(d * L, L, lin)
        inv = TD.large_deformation_inverse(fw["a"], L, lin)
        assert inv["d"] == pytest.approx(d, rel=1e-10)
        assert inv["F"] == pytest.approx(fw["F"], rel=1e-9)
        assert inv["beyond_validated"] == (d > 0.5)


def test_hertz_error_signs_by_observable():
    e = TD.hertz_small_strain_error(np.linspace(0.005, 0.5, 100), 2.0)
    assert np.all(e["force_from_delta"] < 0) and np.all(e["radius_from_delta"] < 0)
    assert TD.hertz_small_strain_error(0.3, 2.0)["force_from_delta"] == pytest.approx(-27.79, abs=0.01)
    assert 0 < np.max(e["force_from_radius"]) < 6.0                                      # 半径から読むと球は 6 % 以内
    assert TD.hertz_small_strain_error(0.5, 1.0)["force_from_radius"] < -15.0           # 円錐は外れる
    assert np.all(np.isnan(TD.hertz_small_strain_error([0.1, 0.3], math.inf)["force_from_radius"]))
    fw = TD.large_deformation_contact(np.array([0.1, 0.3]) * L, L, SPH)                  # 配列の入力
    assert fw["F"].shape == (2,) and np.all(fw["F"] > fw["F_L"])


# ── 6. 接触像と fail-closed ─────────────────────────────────────────────────────
@pytest.mark.parametrize("centre", [None, (60.0, 70.5)])
def test_contact_patch_radius_area_method(centre):
    pitch = 0.1e-3
    for a in (1.6e-3, 3.3e-3):
        img = TD.dome_contact_image(a, pitch, 128, centre=centre, footprint=5.5e-3)
        rd = TD.contact_patch_radius(img, pitch)
        assert rd["a"] == pytest.approx(a, rel=2e-4)
        if centre is not None:
            assert rd["centre"][0] == pytest.approx(centre[0], abs=0.01) and rd["centre"][1] == pytest.approx(centre[1], abs=0.01)
    noisy = TD.dome_contact_image(3.3e-3, pitch, 128, footprint=5.5e-3, noise=0.03, seed=3)
    assert TD.contact_patch_radius(noisy, pitch)["a"] == pytest.approx(3.3e-3, rel=3e-3)


def test_fail_closed():
    bad = [lambda: TD.largedef_correction(1.0, 1.5), lambda: TD.largedef_correction(-0.1, 1.5),
           lambda: TD.largedef_correction(0.3, 0.5), lambda: TD.largedef_correction(0.3, 1.5, "derivd"),
           lambda: TD.largedef_radius_ratio(0.3, 0.1), lambda: TD.largedef_radius_ratio(0.3, 2.0, "betta"),
           lambda: TD.powerlaw_linear_contact("sphre", R, ES), lambda: TD.powerlaw_linear_contact("power", 1.0, ES),
           lambda: TD.powerlaw_linear_contact("sphere", R, ES, p=2.0), lambda: TD.powerlaw_linear_contact("sphere", -R, ES),
           lambda: TD.large_deformation_contact(L, L, SPH), lambda: TD.large_deformation_contact(0.0, L, SPH),
           lambda: TD.large_deformation_contact(1e-3, L, {"p": 2}), lambda: TD.large_deformation_inverse(0.5 * R, L, PUNCH),
           lambda: TD.largedef_universal_correction(0.95), lambda: TD.mdr_spring_bed(1e-3, L, SPH, 4),
           lambda: TD.dome_contact_image(5e-3, 1e-4, 64), lambda: TD.dome_contact_image(1e-3, 1e-4, 64, fg=0.1, bg=0.2),
           lambda: TD.contact_patch_radius(np.full((64, 64), 0.3), 1e-4), lambda: TD.contact_patch_radius(np.zeros(64), 1e-4),
           lambda: TD.neohookean_cylinder_exact(1.2),
           lambda: TD.largedef_correction("0.3", 1.5), lambda: TD.powerlaw_linear_contact("sphere", "8e-3", ES)]   # 数に見える文字列も拒否
    assert len(bad) >= 23
    for fn in bad:
        with pytest.raises(ValueError):
            fn()
