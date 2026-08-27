# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""imagemorph のGTテスト: ワープの厳密性 + モーフの端点/中点 + 「素朴ブレンドとの判別」。

方針は beat-the-null: 単純な alpha ブレンドでも通ってしまう緩い検査ではなく、
「モーフは特徴を中点へ揃えて単一像にする / 素朴ブレンドは二重像になる」という
**判別的な GT** を置く。ワープは既知変換(恒等・平行移動)で数値的に厳密検証する。
"""
import numpy as np
import pytest
from scipy import ndimage

import imagemorph as M


# --------------------------------------------------------------------------- #
# ワープの厳密性                                                               #
# --------------------------------------------------------------------------- #
def _wave(H=100, W=100):
    yy, xx = np.mgrid[0:H, 0:W].astype(float)
    return (0.3 + 0.5 * np.sin(xx / 8.0) * np.cos(yy / 10.0)).clip(0, 1)


def test_piecewise_affine_identity_is_exact():
    a = _wave()
    pts = np.array([[30, 40], [70, 45], [50, 75]], float)
    p = M.add_frame_corners(pts, a.shape)
    out = M.warp_piecewise_affine(a, p, p)
    assert np.abs(out - a).max() < 1e-9  # src==dst は恒等


def test_piecewise_affine_pure_translation_matches_roll():
    a = _wave()
    gx, gy = np.meshgrid(np.linspace(0, 99, 6), np.linspace(0, 99, 6))
    src = np.column_stack([gx.ravel(), gy.ravel()])
    tx, ty = 7, 4
    dst = src + [tx, ty]
    out = M.warp_piecewise_affine(a, src, dst)
    ref = np.roll(np.roll(a, ty, axis=0), tx, axis=1)
    # 内部領域(端のクランプを避ける)で一様平行移動 == roll
    assert np.abs(out[12:88, 12:88] - ref[12:88, 12:88]).max() < 1e-9


def test_tps_image_identity_is_exact():
    a = _wave()
    pts = np.array([[25, 30], [72, 35], [40, 70], [65, 68]], float)
    p = M.add_frame_corners(pts, a.shape)
    out = M.warp_tps_image(a, p, p, lam=0.0)
    assert np.abs(out - a).max() < 1e-8  # 制御点上で厳密内挿 → 恒等


def test_tps_control_points_land_exactly():
    # lam=0 の逆写像TPSは制御点(dst)で src へ厳密に戻る(内挿の厳密性)
    dst = np.array([[20, 30], [80, 25], [50, 70], [30, 60], [70, 65]], float)
    src = dst + np.array([[3, -2], [-4, 1], [2, 5], [-1, -3], [0, 4]], float)
    inv = M._tps_fit_2d(dst, src, lam=0.0)
    got = M._tps_eval(inv, dst)
    assert np.abs(got - src).max() < 1e-6


def test_color_image_is_supported():
    a = np.stack([_wave(), _wave() * 0.5, _wave() * 0.2], axis=-1)
    pts = M.add_frame_corners(np.array([[30, 40], [60, 50], [45, 70]], float), a.shape[:2])
    out = M.warp_piecewise_affine(a, pts, pts)
    assert out.shape == a.shape
    assert np.abs(out - a).max() < 1e-9


# --------------------------------------------------------------------------- #
# モーフ: 端点と中点                                                           #
# --------------------------------------------------------------------------- #
def _dot_image(cx, cy, H=120, W=120, r=3):
    im = np.zeros((H, W))
    im[cy - r:cy + r + 1, cx - r:cx + r + 1] = 1.0
    return im


def test_morph_endpoints_return_inputs():
    A = _dot_image(35, 60)
    B = _dot_image(85, 60)
    pa = np.array([[35, 60]], float)
    pb = np.array([[85, 60]], float)
    m0 = M.morph(A, B, pa, pb, 0.0)
    m1 = M.morph(A, B, pa, pb, 1.0)
    assert np.abs(m0 - A).max() < 1e-8  # alpha=0 -> A
    assert np.abs(m1 - B).max() < 1e-8  # alpha=1 -> B


@pytest.mark.parametrize("method", ["affine", "tps"])
def test_morph_midpoint_beats_naive_blend(method):
    # beat-the-null: モーフは中点に「単一の」特徴 / 素朴ブレンドは「二重像」
    A = _dot_image(35, 60)
    B = _dot_image(85, 60)
    pa = np.array([[35, 60]], float)
    pb = np.array([[85, 60]], float)
    lam = 1.0 if method == "tps" else 0.0
    mh = M.morph(A, B, pa, pb, 0.5, method=method, lam=lam)
    bl = M.blend(A, B, 0.5)

    _, n_morph = ndimage.label(mh > 0.25)
    _, n_blend = ndimage.label(bl > 0.25)
    assert n_morph == 1, f"モーフの特徴は単一像であるべき(got {n_morph})"
    assert n_blend == 2, f"素朴ブレンドは二重像になるはず(got {n_blend})"

    ys, xs = np.where(mh > 0.5)
    cx, cy = xs.mean(), ys.mean()
    assert abs(cx - 60.0) < 3.0 and abs(cy - 60.0) < 3.0, \
        f"モーフの特徴は中点(60,60)付近に来るべき(got {cx:.1f},{cy:.1f})"


def test_morph_sequence_spans_A_to_B():
    A = _dot_image(35, 60)
    B = _dot_image(85, 60)
    pa = np.array([[35, 60]], float)
    pb = np.array([[85, 60]], float)
    seq = M.morph_sequence(A, B, pa, pb, n=5)
    assert len(seq) == 5
    assert np.abs(seq[0] - A).max() < 1e-8
    assert np.abs(seq[-1] - B).max() < 1e-8
    # 特徴の x 中心が単調に 35 -> 85 へ移動する
    centers = []
    for im in seq:
        ys, xs = np.where(im > 0.5)
        centers.append(xs.mean())
    assert centers[0] < centers[2] < centers[-1]
    assert 55 < centers[2] < 65  # 中央フレームは中点付近


# --------------------------------------------------------------------------- #
# 入力検証(fail-closed)                                                       #
# --------------------------------------------------------------------------- #
def test_invalid_inputs_raise():
    a = _wave()
    with pytest.raises(ValueError):
        M.warp_piecewise_affine(a, np.array([[1, 2], [3, 4]], float), np.array([[1, 2], [3, 4]], float))  # <3点
    with pytest.raises(ValueError):
        M.warp_piecewise_affine(a, np.array([[1, 2, 3]], float), np.array([[1, 2, 3]], float))  # 形状不正
    with pytest.raises(ValueError):
        M.morph(a, a[:, :50], np.array([[1, 2], [3, 4], [5, 6]], float),
                np.array([[1, 2], [3, 4], [5, 6]], float), 0.5)  # shape 不一致
    with pytest.raises(ValueError):
        M.blend(a, a, 0.5) if False else M.morph(a, a, np.zeros((3, 2)), np.zeros((2, 2)), 0.5)  # 点数不一致
