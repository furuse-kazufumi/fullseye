# -*- coding: utf-8 -*-
"""★`smooth_contours` の両端がゼロへ引かれない(2026-09-06、図が見つけたバグ)。

op ごとの「入力 → 出力」の図を初めて作ったとき、`smooth_contours` だけ輪郭
140 本ぶんの赤い筋が**左上へ収束**していた。原因は `np.convolve(x, k, "same")`
—— 端をゼロで埋めるので、各輪郭の始点・終点の w 点が原点 (0,0) と平均され、
最大 50 px 以上ずれる。**平均ずれは 0.34 px**で、平均を見る数値テストには
一度も引っかからなかった(端だけが壊れる欠陥は平均に埋もれる)。

守るもの: 直線の輪郭は平滑化しても直線のまま、**端点も動かない**。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _line(n=60, r0=100.0, c0=20.0, dr=0.0, dc=1.0):
    t = np.arange(n, dtype=np.float64)
    return np.stack([r0 + dr * t, c0 + dc * t], 1)


def test_smoothed_points_stay_inside_the_input_range():
    """★守る不変量: 出力の各座標は入力のその座標の [min, max] の**中**にある。

    等重み移動平均は入力値の凸結合なので、端を端の値で埋めれば必ずこの範囲に
    収まる。ゼロ埋めだと (100, 20) の端点が (57, 11) のように**範囲の外**へ
    出る —— それがバグの定義そのもの。端点が少し内側へ動くのは正常
    (直線でも端の w 点は ≤ w/2 px 動く)なので「端点不動」は要求しない。
    """
    import fullseye as fs

    c = _line()
    out = fs.apply({"shape": (128, 128), "cs": [c]}, "smooth_contours", 0.5, 0.5,
                   on_error="raise")
    s = np.asarray(out["cs"][0])
    assert s.shape == c.shape
    for i in (0, 1):
        assert s[:, i].min() >= c[:, i].min() - 1e-9, (i, s[:, i].min(), c[:, i].min())
        assert s[:, i].max() <= c[:, i].max() + 1e-9, (i, s[:, i].max(), c[:, i].max())
    # 内側(端から w より内)は直線のまま
    w = 1 + int(0.5 * 3)
    assert np.max(np.abs(s[w:-w] - c[w:-w])) < 1e-9
    # 端点の動きは w/2 px 以下(内側へ)。ゼロ埋めなら 40 px 以上動く
    assert np.linalg.norm(s[0] - c[0]) <= w / 2 + 1e-9
    assert np.linalg.norm(s[-1] - c[-1]) <= w / 2 + 1e-9


def test_the_maximum_displacement_is_bounded_not_just_the_mean():
    """★平均でなく**最大**を見る。端の欠陥は平均に埋もれる。"""
    import fullseye as fs

    rng = np.random.default_rng(0)
    t = np.linspace(0, np.pi, 80)
    c = np.stack([60 + 30 * np.sin(t), 20 + 90 * t / np.pi], 1) + rng.normal(0, 0.4, (80, 2))
    out = fs.apply({"shape": (128, 128), "cs": [c]}, "smooth_contours", 0.9, 0.5,
                   on_error="raise")
    d = np.linalg.norm(np.asarray(out["cs"][0]) - c, axis=1)
    assert d.max() < 3.0, "最大ずれ %.1f px —— 端がゼロへ引かれている" % d.max()
