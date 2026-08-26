"""pcl_filter の数値検証テスト(見た目でなく ground-truth の数値で確かめる)。

各フィルタの「効いていること」を注入した既知の真値で assert する:
- SOR: 平面上のクリーン点群に明らかな飛び点を注入 → その飛び点だけが keep_mask=False。
- radius: 孤立点が落ち、密な点は残る。
- voxel: 点数が確実に減り、全出力点が入力 bbox 内に収まる。
- MLS: 平面 + ガウスノイズ → 平滑後の面残差 RMS がノイズより有意に小さい。
- resolution: 既知間隔の格子で中央値がその間隔に一致。
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

pytest.importorskip("scipy")

# imgevolve はフラット構成: モジュールは 1 つ上の階層。
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pcl_filter as F  # noqa: E402


def _plane_grid(n=40, span=2.0, noise=0.0, seed=0):
    """z=0 平面上の n×n 格子(任意でガウスノイズ)。(N,3) を返す。"""
    xs = np.linspace(0.0, span, n)
    X, Y = np.meshgrid(xs, xs)
    x = X.ravel()
    y = Y.ravel()
    rng = np.random.default_rng(seed)
    z = rng.normal(0.0, noise, x.shape) if noise > 0 else np.zeros_like(x)
    return np.column_stack([x, y, z])


# --------------------------------------------------------------------------- #
# 1. statistical_outlier_removal                                              #
# --------------------------------------------------------------------------- #
def test_sor_removes_injected_outliers():
    clean = _plane_grid(n=40, span=2.0, noise=0.005, seed=1)   # 密な平面(飛び点なし)
    n_clean = clean.shape[0]

    # 平面から明らかに離れた飛び点を数点、互いにも離して注入(近傍が平面点になるように)。
    rng = np.random.default_rng(7)
    xy = rng.uniform(0.2, 1.8, size=(5, 2))
    outliers = np.column_stack([xy[:, 0], xy[:, 1], np.full(5, 5.0)])  # z=5 は面から遠い
    pts = np.vstack([clean, outliers])
    inj_idx = np.arange(n_clean, n_clean + 5)

    filtered, keep = F.statistical_outlier_removal(pts, k=16, std_ratio=2.0)

    assert keep.shape == (pts.shape[0],)
    # 注入した飛び点は全て除去される。
    assert not keep[inj_idx].any(), "injected outliers must be removed"
    # filtered は keep マスクと整合。
    assert np.array_equal(filtered, pts[keep])
    # クリーン点の大半(>95%)は残る(誤除去が暴走していない)。
    assert keep[:n_clean].mean() > 0.95


def test_sor_small_input_kept():
    pts = np.zeros((2, 3))
    filtered, keep = F.statistical_outlier_removal(pts)
    assert keep.all() and filtered.shape == (2, 3)


# --------------------------------------------------------------------------- #
# 2. radius_outlier_removal                                                   #
# --------------------------------------------------------------------------- #
def test_radius_removes_isolated_keeps_dense():
    # 原点付近に密なクラスタ。
    rng = np.random.default_rng(3)
    dense = rng.normal(0.0, 0.05, size=(300, 3))
    # 遠方に孤立点を数点(互いにも遠い)。
    isolated = np.array([[10.0, 0.0, 0.0],
                         [0.0, -12.0, 3.0],
                         [8.0, 8.0, -9.0]])
    pts = np.vstack([dense, isolated])
    iso_idx = np.arange(300, 303)

    filtered, keep = F.radius_outlier_removal(pts, radius=0.3, min_neighbors=8)

    assert not keep[iso_idx].any(), "isolated points must be removed"
    assert keep[:300].mean() > 0.9, "dense points must mostly survive"
    assert np.array_equal(filtered, pts[keep])


def test_radius_bad_arg():
    with pytest.raises(ValueError):
        F.radius_outlier_removal(np.zeros((5, 3)), radius=0.0)


# --------------------------------------------------------------------------- #
# 3. voxel_grid_downsample                                                    #
# --------------------------------------------------------------------------- #
def test_voxel_reduces_and_stays_in_bbox():
    rng = np.random.default_rng(11)
    pts = rng.uniform(-1.0, 1.0, size=(5000, 3))
    out = F.voxel_grid_downsample(pts, voxel_size=0.25)

    # 点数は確実に減る。
    assert out.shape[0] < pts.shape[0]
    assert out.shape[1] == 3
    # 全出力点(重心)は入力 bbox 内。
    lo, hi = pts.min(axis=0), pts.max(axis=0)
    assert np.all(out >= lo - 1e-9) and np.all(out <= hi + 1e-9)


def test_voxel_deterministic():
    rng = np.random.default_rng(11)
    pts = rng.uniform(-1.0, 1.0, size=(2000, 3))
    a = F.voxel_grid_downsample(pts, 0.2)
    b = F.voxel_grid_downsample(pts, 0.2)
    assert np.array_equal(a, b)


def test_voxel_centroid_value():
    # 1 セルに 2 点だけ → 出力はその重心 1 点。
    pts = np.array([[0.1, 0.1, 0.1], [0.2, 0.2, 0.2]])
    out = F.voxel_grid_downsample(pts, voxel_size=1.0)
    assert out.shape[0] == 1
    assert np.allclose(out[0], [0.15, 0.15, 0.15])


# --------------------------------------------------------------------------- #
# 4. mls_smooth                                                               #
# --------------------------------------------------------------------------- #
def test_mls_reduces_plane_noise():
    noise = 0.02
    pts = _plane_grid(n=40, span=2.0, noise=noise, seed=5)
    sm = F.mls_smooth(pts, radius=0.18, order=2)

    assert sm.shape == pts.shape
    # 境界の片側近傍で当てはめが甘くなるので内部だけで評価。
    x, y = pts[:, 0], pts[:, 1]
    interior = (x > 0.3) & (x < 1.7) & (y > 0.3) & (y < 1.7)

    rms_before = float(np.sqrt(np.mean(pts[interior, 2] ** 2)))
    rms_after = float(np.sqrt(np.mean(sm[interior, 2] ** 2)))

    # 有意に改善(半分未満)していること。
    assert rms_after < 0.6 * rms_before, (rms_before, rms_after)


def test_mls_insufficient_neighbors_kept():
    # 半径が極小 → どの点も近傍が項数(order2=6)未満 → 原位置維持。
    pts = _plane_grid(n=10, span=2.0, noise=0.0, seed=0)
    sm = F.mls_smooth(pts, radius=1e-6, order=2)
    assert np.allclose(sm, pts)


# --------------------------------------------------------------------------- #
# 5. estimate_resolution                                                      #
# --------------------------------------------------------------------------- #
def test_resolution_matches_grid_spacing():
    s = 0.37
    a = s * np.arange(6)
    X, Y, Z = np.meshgrid(a, a, a, indexing="ij")
    pts = np.column_stack([X.ravel(), Y.ravel(), Z.ravel()])
    res = F.estimate_resolution(pts)
    assert np.isclose(res, s, rtol=1e-9, atol=1e-9)


def test_resolution_empty_is_nan():
    assert np.isnan(F.estimate_resolution(np.zeros((1, 3))))
    assert np.isnan(F.estimate_resolution(np.zeros((0, 3))))


# --------------------------------------------------------------------------- #
# shape validation                                                            #
# --------------------------------------------------------------------------- #
def test_shape_validation():
    bad = np.zeros((4, 2))
    for fn in (F.statistical_outlier_removal, F.mls_smooth, F.estimate_resolution):
        with pytest.raises(ValueError):
            if fn is F.mls_smooth:
                fn(bad, radius=0.1)
            else:
                fn(bad)
