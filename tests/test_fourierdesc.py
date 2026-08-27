# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""fourierdesc(楕円フーリエ記述子)のGTテスト。

beat-the-null: 「再構成が形状に収束する」「同形状は変換に不変で異形状とは乖離する」
という判別的 GT を数値で置く。ランダムな係数では通らない。
"""
import numpy as np
import pytest

import fourierdesc as F


def shp(kind, n=200, R=40, cx=0, cy=0, phi0=0.0):
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    if kind == "circle":
        x, y = R * np.cos(t), R * np.sin(t)
    elif kind == "square":
        c, s = np.cos(t), np.sin(t)
        m = np.maximum(np.abs(c), np.abs(s))
        x, y = R * c / m, R * s / m
    elif kind == "star":
        rr = R * (0.6 + 0.4 * np.cos(5 * t))
        x, y = rr * np.cos(t), rr * np.sin(t)
    elif kind == "ellipse":
        x, y = R * np.cos(t), 0.5 * R * np.sin(t)
    else:
        raise ValueError(kind)
    return np.column_stack([x * np.cos(phi0) - y * np.sin(phi0) + cx,
                            x * np.sin(phi0) + y * np.cos(phi0) + cy])


def _maxdist(pts, poly):
    P = np.vstack([poly, poly[0]])
    A, B = P[:-1], P[1:]
    AB = B - A
    L2 = (AB ** 2).sum(1) + 1e-12
    out = 0.0
    for p in pts:
        tt = np.clip(((p - A) * AB).sum(1) / L2, 0, 1)
        proj = A + tt[:, None] * AB
        out = max(out, np.sqrt(((proj - p) ** 2).sum(1)).min())
    return out


# --------------------------------------------------------------------------- #
# 係数と再構成                                                                 #
# --------------------------------------------------------------------------- #
def test_circle_is_first_harmonic():
    m = F.elliptic_fourier(shp("circle", R=50), n_harmonics=8)
    amp = F._amplitudes(m["coeffs"])[:, 0]  # 各高調波の長軸
    assert abs(amp[0] - 50.0) < 1.0            # 第1高調波 ≈ 半径
    assert amp[1:].max() < 0.05 * amp[0]       # 高次は無視できる


def test_dc_is_centroid():
    m = F.elliptic_fourier(shp("square", R=50, cx=12, cy=-7), n_harmonics=10)
    assert abs(m["a0"] - 12.0) < 0.5 and abs(m["c0"] + 7.0) < 0.5


def test_reconstruction_converges_with_harmonics():
    sq = shp("square", R=50)
    errs = [_maxdist(F.reconstruct(F.elliptic_fourier(sq, N), 300), sq)
            for N in [1, 3, 6, 12, 24]]
    # 高調波を増やすと単調に(ほぼ)減り、十分小さくなる(角の Gibbs は残る)
    assert all(errs[i] >= errs[i + 1] - 0.5 for i in range(len(errs) - 1))
    assert errs[-1] < 3.0 and errs[-1] < 0.2 * errs[0]


def test_reconstruct_truncation_smooths():
    star = shp("star", R=40)
    m = F.elliptic_fourier(star, 20)
    rough = F.reconstruct(m, 300, n_harmonics=20)
    smooth = F.reconstruct(m, 300, n_harmonics=2)  # 低次だけ = 丸い
    # 低次再構成の方が真円(半径一定)に近い = とがりが消える
    r_rough = np.std(np.hypot(rough[:, 0], rough[:, 1]))
    r_smooth = np.std(np.hypot(smooth[:, 0], smooth[:, 1]))
    assert r_smooth < r_rough


# --------------------------------------------------------------------------- #
# 不変性とマッチング(beat-the-null)                                          #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("variant", [
    dict(phi0=0.7), dict(R=68), dict(cx=120, cy=-40), dict(phi0=1.3, R=55, cx=-30, cy=25),
])
def test_descriptor_is_invariant(variant):
    base = F.elliptic_fourier(shp("star", R=40), 12)
    var = F.elliptic_fourier(np.roll(shp("star", **variant), 37, axis=0), 12)
    d_same = F.descriptor_distance(base, var, 12)
    d_diff = F.descriptor_distance(base, F.elliptic_fourier(shp("square", R=40), 12), 12)
    assert d_same < 1e-6                    # 相似変換+始点シフトに不変
    assert d_same < 0.01 * d_diff           # 異形状とは桁違いに離れる


def test_retrieval_picks_correct_shape():
    gallery = {k: F.elliptic_fourier(shp(k, R=30, cx=10, phi0=1.1), 12)
               for k in ["circle", "square", "star", "ellipse"]}
    query = F.elliptic_fourier(shp("square", R=55, cx=-40, cy=20, phi0=2.3), 12)
    dists = {k: F.descriptor_distance(query, g, 12) for k, g in gallery.items()}
    assert min(dists, key=dists.get) == "square"
    assert dists["square"] < 1e-6


# --------------------------------------------------------------------------- #
# 複素フーリエ平滑化                                                           #
# --------------------------------------------------------------------------- #
def test_fourier_smooth_identity_at_full_band():
    c = shp("circle", R=50, n=256)
    assert np.abs(F.fourier_smooth(c, keep=200) - c).max() < 1e-9


def test_fourier_smooth_denoises():
    c = shp("circle", R=50, n=256)
    rng = np.random.default_rng(0)
    noisy = c + rng.normal(0, 3, c.shape)
    sm = F.fourier_smooth(noisy, keep=3)
    dev_noisy = np.std(np.hypot(noisy[:, 0], noisy[:, 1]))
    dev_sm = np.std(np.hypot(sm[:, 0], sm[:, 1]))
    assert dev_sm < 0.5 * dev_noisy         # 高周波ノイズが落ちて半径が一定に近づく


# --------------------------------------------------------------------------- #
# XLD 連携と入力検証                                                           #
# --------------------------------------------------------------------------- #
def test_from_xld_integration():
    import contours_xld as X
    xld = X.gen_circle_contour_xld(128, 128, 40, n=120)
    m = F.elliptic_fourier(F.from_xld(xld), n_harmonics=6)
    assert m["coeffs"].shape == (6, 4)


def test_invalid_inputs_raise():
    with pytest.raises(ValueError):
        F.elliptic_fourier(np.zeros((2, 2)), 5)          # <3点
    with pytest.raises(ValueError):
        F.elliptic_fourier(np.zeros((10, 3)), 5)         # 形状不正
    with pytest.raises(ValueError):
        F.elliptic_fourier(shp("circle"), 0)             # n_harmonics<1
    with pytest.raises(ValueError):
        F.fourier_smooth(shp("circle"), 0)               # keep<1
