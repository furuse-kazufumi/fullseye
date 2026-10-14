# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""薄膜 op を吸収基板・膜の分散・材料名・偏光に開いた回(2026-10-14)の門。

第二実装 = 特性行列法(Born & Wolf §1.6、層ごとの 2×2 行列の積)を下で独立に書き、Airy の閉じた式の op と比べる。
"""
from __future__ import annotations

import numpy as np
import pytest

import glassmirror as G
import materials as M
import matappear as MA
import opassist


def _tmm(lam_nm, d_nm, n0, n1, n2, cos0, pol):
    """1 層の特性行列法(s / p)。屈折率は複素(n + ik)、入射側 n0 は実数。"""
    s0 = np.sqrt(1.0 - cos0 ** 2)
    out = []
    for lam, a, b in np.broadcast(lam_nm, np.broadcast_to(n1, np.shape(lam_nm)), np.broadcast_to(n2, np.shape(lam_nm))):
        def cosj(n):
            c = np.sqrt(1.0 - (n0 * s0 / n) ** 2 + 0j)
            return -c if (n * c).imag < 0 else c
        c1, c2 = cosj(a), cosj(b)
        if pol == "s":
            eta0, eta1, eta2 = n0 * cos0, a * c1, b * c2
        else:
            eta0, eta1, eta2 = n0 / cos0, a / c1, b / c2
        delta = 2 * np.pi * a * d_nm * c1 / lam
        m = np.array([[np.cos(delta), -1j * np.sin(delta) / eta1], [-1j * eta1 * np.sin(delta), np.cos(delta)]])
        B, C = m @ np.array([1.0, eta2])
        r = (eta0 * B - C) / (eta0 * B + C)
        out.append(abs(r) ** 2)
    return np.array(out)


def test_airy_matches_the_characteristic_matrix_with_an_absorbing_substrate():
    w = np.linspace(400.0, 750.0, 36)
    n, k = M._nk(M._record("TI", "t"), w / 1000.0, "t")[:2]
    sub = n + 1j * k
    worst = 0.0
    cases = [(90.0, 2.4, 1.0), (150.0, 1.63, 0.7), (300.0, 2.0 + 0.05j, 0.5)]
    assert len(cases) == 3
    for d, nf, c in cases:
        for pol in ("s", "p"):
            a = MA.thin_film_reflectance(w, d, nf, "TI", c, polarization=pol)
            b = _tmm(w, d, 1.0, nf, sub, c, pol)
            worst = max(worst, float(np.max(np.abs(a - b))))
    assert worst < 1e-12, worst


def test_real_indices_give_the_same_reflectance_as_before():
    """実数の入力は旧式(位相 e^{-iδ})と |·|² が同じ。旧式をここに写して比べる。"""
    def old(w, d, n1, n2, c0, n0=1.0):
        s0 = np.sqrt(1 - c0 ** 2)
        c1 = np.sqrt(1 - (n0 * s0 / n1) ** 2)
        c2 = np.sqrt(1 - (n0 * s0 / n2) ** 2)
        r1s, r1p = (n0 * c0 - n1 * c1) / (n0 * c0 + n1 * c1), (n1 * c0 - n0 * c1) / (n1 * c0 + n0 * c1)
        r2s, r2p = (n1 * c1 - n2 * c2) / (n1 * c1 + n2 * c2), (n2 * c1 - n1 * c2) / (n2 * c1 + n1 * c2)
        ph = np.exp(-1j * 4 * np.pi * n1 * d * c1 / w)
        return 0.5 * sum(abs((a + b * ph) / (1 + a * b * ph)) ** 2 for a, b in ((r1s, r2s), (r1p, r2p)))
    rng = np.random.default_rng(1)
    w = np.linspace(380.0, 780.0, 41)
    worst = 0.0
    for _ in range(50):
        d, n1, n2, c = rng.uniform(0, 800), rng.uniform(1.0, 2.6), rng.uniform(1.0, 3.5), rng.uniform(0.1, 1.0)
        worst = max(worst, float(np.max(np.abs(MA.thin_film_reflectance(w, d, n1, n2, c) - old(w, d, n1, n2, c)))))
    assert worst < 1e-12, worst


def test_zero_thickness_on_a_metal_is_the_conductor_fresnel_and_half_wave_film_is_invisible():
    w = np.linspace(400.0, 750.0, 36)
    n, k = M._nk(M._record("TI", "t"), w / 1000.0, "t")[:2]
    for c in (1.0, 0.6):
        assert np.allclose(MA.thin_film_reflectance(w, 0.0, 2.4, "TI", c), G.fresnel_conductor(c, n, k), atol=1e-12)
    lam0 = 550.0
    half = MA.thin_film_reflectance(lam0, lam0 / (2 * 2.4), 2.4, "TI")
    bare = MA.thin_film_reflectance(lam0, 0.0, 2.4, "TI")
    assert abs(float(half) - float(bare)) < 1e-12


def test_thick_absorbing_film_reflects_like_its_own_surface():
    nf = 2.0 + 0.5j
    r = float(MA.thin_film_reflectance(600.0, 5000.0, nf, 1.5))
    assert abs(r - ((2 - 1) ** 2 + 0.25) / (3 ** 2 + 0.25)) < 1e-12


def test_film_dispersion_array_and_polarization_split():
    w = np.linspace(450.0, 700.0, 26)
    nf = 1.45 + 3000.0 / w ** 2                                    # Cauchy, per wavelength
    a = MA.thin_film_reflectance(w, 300.0, nf, 1.52)
    b = np.array([float(MA.thin_film_reflectance(x, 300.0, float(n), 1.52)) for x, n in zip(w, nf)])
    assert np.allclose(a, b, atol=1e-14)
    s = MA.thin_film_reflectance(w, 200.0, 1.5, "AL", 0.5, polarization="s")
    p = MA.thin_film_reflectance(w, 200.0, 1.5, "AL", 0.5, polarization="p")
    u = MA.thin_film_reflectance(w, 200.0, 1.5, "AL", 0.5)
    assert np.allclose(u, 0.5 * (s + p), atol=1e-15) and float(np.max(np.abs(s - p))) > 0.01


def test_metal_presets_use_the_metal_and_fail_closed_inputs():
    src = open(opassist.__file__, encoding="utf-8").read()
    assert '"n_sub": "TI"' in src and src.count('"n_sub": "AL"') == 2   # 金属の基板は材料名で
    r = MA.thin_film_reflectance(np.linspace(400, 700, 4), 90.0, 2.4, "TI")
    assert float(r.min()) > 0.3                                      # 誘電体扱い(n_sub=2.6)だと 0.15〜0.19
    with pytest.raises(ValueError, match="polarization"):
        MA.thin_film_reflectance(550.0, 100.0, 1.5, 1.5, polarization="circular")
    with pytest.raises(ValueError, match="k >= 0"):
        MA.thin_film_reflectance(550.0, 100.0, 1.5, 1.5 - 0.1j)
    with pytest.raises(ValueError, match="non-absorbing"):
        MA.thin_film_reflectance(550.0, 100.0, 1.5, 1.5, n_out=1.0 + 0.1j)
    assert 0.0 < float(MA.thin_film_reflectance(550.0, 100.0, "TIO2", 1.5)) < 1.0   # 表は 430 nm から: 550 は引ける
    with pytest.raises(ValueError, match="not extrapolated"):
        MA.thin_film_reflectance(400.0, 100.0, "TIO2", 1.5)
