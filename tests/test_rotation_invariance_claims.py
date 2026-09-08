# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""「回転不変」と名乗っている量に、角度を振る門を置く(著者の指摘 2026-09-08)。

    「PoC の評価に回転成分が入っていないのが、良くない感じはありますね。」

不変性の主張は、たいてい**下請けの任意性**のところで壊れる
([[feedback_invariance_claims_break_at_the_helper]])。docstring に「回転不変」と
書いてあるだけでは、それが本当かどうか誰も測っていない。ここでは主張ごとに
角度を振る。

★**この門に歯があることを、門自身が証明する**。回転不変な量だけを見ていると、
「実は何も回っていない」「op が定数を返している」でも緑になる。だから同じ掃引に

* **負の対照**: 向きに依存すると **docstring 自身が言っている** 量
  (``xg_height_width_ratio`` = 軸並行 bbox の縦横比)が、ちゃんと大きく動くこと
* **正の対照**: ``xg_orientation`` が、掛けた角度ぶんだけ**動く**こと

を混ぜてある。この 2 つが動かなければ、掃引が回っていないということ。

★格子(画像)の量はここでは扱わない —— 画素に落とした時点で回転は厳密でなくなり、
「測り方の向き依存」と「格子に置き直す代償」が混ざるため。その分解は
``examples/poc_rotation_invariance_audit.py`` が実写で行う。ここで見るのは
**点の座標だけで決まる量**(点群記述子と輪郭の PCA)で、これらは回転が厳密。
"""
import math

import numpy as np
import pytest

import descriptors3d as D3
import fullseye as fs

ANGLES = np.arange(0.0, 360.0, 15.0)          # 24 通り


# --------------------------------------------------------------------------- #
# 素材
# --------------------------------------------------------------------------- #
def _cloud(n=800, seed=0):
    """細長い(等方でない)点群。等方だと回しても何も起きず、門が空を通す。"""
    rng = np.random.default_rng(seed)
    p = rng.normal(size=(n, 3)) * np.array([3.0, 1.0, 0.4])
    p[:n // 4] += np.array([6.0, 0.0, 0.0])   # 片側に瘤 —— 対称性も崩しておく
    return p


def _rot3(seed):
    """ランダムな回転行列(QR 分解、det=+1 に直す)。"""
    rng = np.random.default_rng(seed)
    q, r = np.linalg.qr(rng.normal(size=(3, 3)))
    q *= np.sign(np.diag(r))
    if np.linalg.det(q) < 0:
        q[:, 0] *= -1.0
    return q


def _ellipse_contour(a=40.0, b=12.0, n=256, deg=0.0):
    """(row, col) の閉輪郭。**格子に丸めない**ので回転は厳密。"""
    t = np.linspace(0.0, 2.0 * np.pi, n, endpoint=False)
    x, y = a * np.cos(t), b * np.sin(t)
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    xr, yr = c * x - s * y, s * x + c * y
    return {"shape": (256, 256), "cs": [np.column_stack([yr + 128.0, xr + 128.0])]}


# --------------------------------------------------------------------------- #
# 1. 点群記述子 —— 座標だけで決まるので、回転は厳密であるはず
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("fn,tol,what", [
    (D3.extent_signature, 1e-9, "共分散の固有値は回転で不変"),
    (D3.d2_distribution, 4e-3, "点対の距離は回転で不変(ビンの縁で数個動く)"),
    (D3.a3_distribution, 4e-3, "3 点のなす角は回転で不変(同上)"),
])
def test_point_cloud_descriptors_survive_twelve_random_rotations(fn, tol, what):
    p = _cloud()
    base = np.asarray(fn(p), dtype=np.float64)
    worst = 0.0
    for seed in range(12):
        got = np.asarray(fn(p @ _rot3(seed).T), dtype=np.float64)
        assert got.shape == base.shape
        worst = max(worst, float(np.max(np.abs(got - base))))
    assert worst <= tol, (fn.__name__, worst, tol, what)


def test_the_cloud_itself_is_not_isotropic():
    """★等方な点群だと回しても何も起きない —— 上の門が空を通さないことの担保。"""
    p = _cloud()
    w = np.linalg.eigvalsh(np.cov(p.T))
    assert w.max() / w.min() > 20.0, w


def test_describe_concatenates_the_three_and_stays_invariant():
    p = _cloud()
    base = np.asarray(D3.describe(p), dtype=np.float64)
    got = np.asarray(D3.describe(p @ _rot3(7).T), dtype=np.float64)
    assert base.shape == got.shape and base.size > 3
    assert float(np.max(np.abs(got - base))) <= 4e-3
    # 別の形とはちゃんと離れる(距離が 0 に潰れていない)
    other = np.asarray(D3.describe(_cloud(seed=1) * np.array([1.0, 1.0, 4.0])),
                       dtype=np.float64)
    assert D3.shape_distance(base, other) > 20.0 * D3.shape_distance(base, got)


# --------------------------------------------------------------------------- #
# 2. 輪郭の PCA —— docstring が「回転不変な細長さ」と名指ししている量
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("op,tol", [("xg_eccentricity", 1e-9), ("xg_elliptic_axis", 1e-6)])
def test_contour_pca_features_are_flat_across_the_whole_circle(op, tol):
    f = getattr(fs.op, op)
    vals = [float(f(_ellipse_contour(deg=float(d)))) for d in ANGLES]
    assert max(vals) - min(vals) <= tol, (op, min(vals), max(vals))


def test_the_sweep_has_teeth_the_orientation_dependent_feature_really_moves():
    """★負の対照。docstring が「向きに依存する」と言っている量が動かなければ、
    掃引が回っていない(= 上の門は何も測っていない)。"""
    vals = [float(fs.op.xg_height_width_ratio(_ellipse_contour(deg=float(d))))
            for d in ANGLES]
    assert max(vals) / max(min(vals), 1e-12) > 3.0, (min(vals), max(vals))


def test_the_sweep_has_teeth_orientation_tracks_the_angle():
    """★正の対照。主軸の向きが、掛けた角度ぶん動くこと(0..180 で折り返す)。"""
    for d in (0.0, 20.0, 55.0, 90.0, 130.0):
        got = float(fs.op.xg_orientation(_ellipse_contour(deg=d))) * 180.0
        # (row, col) 系での符号の取り方は op の都合。ここでは「180 を法として
        # ±d のどちらかに一致する」ことだけを見る(向きの符号は主張ではない)。
        near = min(abs((got - d) % 180.0), abs((got + d) % 180.0),
                   180.0 - abs((got - d) % 180.0), 180.0 - abs((got + d) % 180.0))
        assert near < 1.0, (d, got)
