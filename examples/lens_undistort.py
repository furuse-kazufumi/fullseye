# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""lens_undistort — レンズの歪みを画像ごと補正する(Brown-Conrady、たる型/糸巻き型/接線)。

    py -3.11 examples/lens_undistort.py

【この例が示すこと】
直線の格子を ``distort_image`` でたる型に歪ませ、``undistort_image`` で元に戻す。滑らかな
検査像では往復が内部で一致することを assert で確かめ、格子の「直線からのずれ」が補正で桁で
減ることを数で示す。remap の場は点モデル ``distort_points`` と厳密一致(絵にする前の式が正しい)。

EXTEND: 実写では ``fs.read_image`` で読み、K の主点=歪み中心、dist=[k1,k2,p1,p2,k3] を渡す。
係数の推定(格子から)はここでは扱わない —— 係数が分かっている前提の補正。
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fullseye as fs  # noqa: E402


def _line_bow(grid_img, y0, band=8, thr=0.5):
    """``y0`` 付近の横線を列ごとに追い、その行位置の『直線からのずれ(px)』の最大値。
    端のクランプ域を避けて内部で測る(歪みで弓なりになるほど大きい)。"""
    h, w = grid_img.shape
    ys = []
    for x in range(20, w - 20):
        lo, hi = max(0, y0 - band), min(h, y0 + band + 1)
        col = np.where(grid_img[lo:hi, x] > thr)[0]
        ys.append(lo + col.mean() if col.size else np.nan)
    ys = np.array(ys, float)
    ok = np.isfinite(ys)
    return float(np.nanmax(np.abs(ys[ok] - np.median(ys[ok])))) if ok.sum() > 4 else float("nan")


def main() -> int:
    h = w = 200
    img = np.zeros((h, w))
    img[::20, :] = 1.0
    img[:, ::20] = 1.0                                   # 直線の格子
    K = fs.intrinsic_matrix(0.95 * w, 0.95 * w, (w - 1) / 2, (h - 1) / 2)
    dist = [0.28, 0.10, 0.0, 0.0, 0.0]                  # たる型

    distorted = fs.distort_image(img, K, dist)          # 直線が弓なりに
    restored = fs.undistort_image(distorted, K, dist)   # まっすぐに戻す
    print("shape:", img.shape, "->", distorted.shape, "->", restored.shape)
    assert distorted.shape == img.shape == restored.shape

    # 直線性: 中心から離れた内部の横線(y=40)で弓なりを測る。歪ませると大、戻すと小。
    bow_d = _line_bow(distorted, y0=40)
    bow_r = _line_bow(restored, y0=40)
    print("内部の横線(y=40)の弓なり(px):  歪み後=%.2f  補正後=%.2f" % (bow_d, bow_r))
    assert bow_d > bow_r + 1.0                           # 補正で直線性が回復

    # 補正画像は歪み画像より元の格子に近い(内部で直接比較)。
    c = (slice(30, h - 30), slice(30, w - 30))
    assert np.abs(restored[c] - img[c]).mean() < np.abs(distorted[c] - img[c]).mean()

    # 滑らかな検査像では往復が内部でほぼ厳密(残差は二重双線形のボケ)。
    yy, xx = np.mgrid[0:h, 0:w]
    smooth = 0.5 + 0.5 * np.sin(xx / 22.0) * np.cos(yy / 26.0)
    back = fs.undistort_image(fs.distort_image(smooth, K, dist), K, dist)
    c = (slice(30, h - 30), slice(30, w - 30))
    err = np.abs(back[c] - smooth[c])
    print("滑らか像の往復 内部: 平均=%.5f  最大=%.5f" % (err.mean(), err.max()))
    assert err.mean() < 1e-3

    # カラーも通る。歪みゼロは恒等。
    col = np.stack([smooth, smooth * 0.6, smooth * 0.3], -1)
    assert fs.undistort_image(col, K, dist).shape == col.shape
    ident = fs.undistort_image(col, K, [0.0, 0.0, 0.0, 0.0, 0.0])
    assert np.abs(ident - col).max() < 1e-6
    print("カラー可 / 歪みゼロは恒等: OK")
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
