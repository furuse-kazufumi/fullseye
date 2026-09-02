# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""接地影の逆投影規約と、shadow map の近傍混合(PCF)の検証。

2026-09-02 に 2 つのことが分かった:

1. ``unproject_to_world`` だけが画素中心に ``+0.5`` を足しており(``render3d`` と
   ``camera`` は足さない、と両方の docstring が明記している)、逆投影した点が
   真の平面から**深度に比例して**ずれていた。影はこの世界座標を光源カメラへ
   投げ直すので、影の引き当ても同じだけずれていた。
2. shadow map を最近傍 1 点で引いていたので、影の境目が texel に量子化されて
   階段になっていた。「ソフトシャドウ」と称していたが、実測すると半影は
   102400 画素中 283 画素・値の種類は ``samples+1`` の 7 段だけだった。
"""
import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import render3d  # noqa: E402
import render_shadow  # noqa: E402


def _plane(n=8, half=4.0, z=0.0):
    xs = np.linspace(-half, half, n + 1)
    X, Y = np.meshgrid(xs, xs, indexing="ij")
    V = np.stack([X.ravel(), Y.ravel(), np.full(X.size, z)], axis=1)
    F = []
    for i in range(n):
        for j in range(n):
            a = i * (n + 1) + j
            F.append([a, a + 1, a + n + 2])
            F.append([a, a + n + 2, a + n + 1])
    return V, np.asarray(F, np.int64)


def _scene():
    """地面 + その上に浮かぶ板。板が地面に影を落とす。"""
    Vg, Fg = _plane(8, 4.0, 0.0)
    Vb, Fb = _plane(2, 1.0, 1.5)
    V = np.vstack([Vg, Vb])
    F = np.vstack([Fg, Fb + len(Vg)])
    return V, F, len(Fg)


# --------------------------------------------------------------------------- #
# 1. 逆投影が画素中心の約束を守る                                              #
# --------------------------------------------------------------------------- #
def test_unprojected_plane_pixels_land_exactly_on_the_plane():
    """平らな地面を写して逆投影すると、**厳密に**その平面へ戻る。

    ``+0.5`` を足していた頃は深度に比例してずれ、96x96・画角 40 度・距離 ~5 の
    実測で真の平面から 1.32e-2 外れていた(許容は texel 由来の 3.5e-4)。
    半画素の話に見えて、実際には**深度が掛かるので絶対値で効く**。
    """
    Vg, Fg = _plane(6, 3.0, 0.0)
    pose = render3d.look_at([3.0, -3.6, 2.2], [0.0, 0.0, 0.0], up=(0.0, 0.0, 1.0))
    K = render3d.intrinsics_from_fov(40.0, 96, 96)
    view = render3d.render_mesh(Vg, Fg, pose=pose, intrinsics=K, width=96, height=96)
    Pw = render_shadow.unproject_to_world(view["depth"], pose, K)
    m = (view["silhouette"] > 0) & np.isfinite(Pw[..., 2])
    assert m.sum() > 500, "地面がほとんど写っていない(検査にならない)"
    err = float(np.abs(Pw[..., 2][m]).max())
    assert err < 1e-9, (
        f"逆投影が平面から {err:.3e} ずれている — 画素中心の規約が "
        "render3d / camera と食い違っている(+0.5 を足していないか)")


def test_unprojection_error_does_not_grow_with_depth():
    """カメラを 2 倍遠ざけても誤差が増えない(規約ずれなら比例して増える)。"""
    Vg, Fg = _plane(6, 3.0, 0.0)
    K = render3d.intrinsics_from_fov(40.0, 96, 96)
    errs = []
    for scale in (1.0, 2.0):
        eye = [3.0 * scale, -3.6 * scale, 2.2 * scale]
        pose = render3d.look_at(eye, [0.0, 0.0, 0.0], up=(0.0, 0.0, 1.0))
        view = render3d.render_mesh(Vg, Fg, pose=pose, intrinsics=K, width=96, height=96)
        Pw = render_shadow.unproject_to_world(view["depth"], pose, K)
        m = (view["silhouette"] > 0) & np.isfinite(Pw[..., 2])
        errs.append(float(np.abs(Pw[..., 2][m]).max()))
    assert max(errs) < 1e-9, f"深度で誤差が増えている: {errs}"


# --------------------------------------------------------------------------- #
# 2. PCF                                                                       #
# --------------------------------------------------------------------------- #
def test_pcf_default_is_off_and_changes_nothing():
    """既定 ``pcf=0`` は従来の最近傍 1 点と**ビット単位で同じ**。

    既存の呼び出しの見た目を黙って変えないこと自体が要件。
    """
    V, F, _ = _scene()
    kw = dict(pose=render3d.look_at([4.0, -5.0, 4.0], [0.0, 0.0, 0.5], up=(0, 0, 1)),
              intrinsics=render3d.intrinsics_from_fov(40.0, 96, 96),
              width=96, height=96, directional=True, penumbra=0.0, samples=1,
              shadow_res=256)
    a = render_shadow.cast_shadow(V, F, np.array([0.4, 0.5, 0.8]), **kw)
    b = render_shadow.cast_shadow(V, F, np.array([0.4, 0.5, 0.8]), pcf=0, **kw)
    assert np.array_equal(a, b)


def test_pcf_adds_gradation_between_lit_and_shadow():
    """PCF を入れると、影の値が 0/1 の 2 値でなく階調を持つ。

    ``samples=1`` にしてあるので、階調が出るとしたら**近傍混合しかない**
    (半影サンプルの平均ではない)ことが構成上保証される。
    """
    V, F, _ = _scene()
    kw = dict(pose=render3d.look_at([4.0, -5.0, 4.0], [0.0, 0.0, 0.5], up=(0, 0, 1)),
              intrinsics=render3d.intrinsics_from_fov(40.0, 128, 128),
              width=128, height=128, directional=True, penumbra=0.0, samples=1,
              shadow_res=256)
    hard = render_shadow.cast_shadow(V, F, np.array([0.4, 0.5, 0.8]), pcf=0, **kw)
    soft = render_shadow.cast_shadow(V, F, np.array([0.4, 0.5, 0.8]), pcf=2, **kw)
    n_hard = int(((hard > 1e-9) & (hard < 1 - 1e-9)).sum())
    n_soft = int(((soft > 1e-9) & (soft < 1 - 1e-9)).sum())
    assert n_hard == 0, f"samples=1 / pcf=0 は 2 値のはず(中間 {n_hard} 画素)"
    assert n_soft > 20, f"PCF を入れても階調が出ていない(中間 {n_soft} 画素)"


def test_pcf_stays_within_zero_one_and_keeps_the_core_dark():
    """階調は端を壊さない: 値域 [0,1]、影の芯は 0 のまま、外は 1 のまま。

    深度を平均する実装にすると芯まで明るくなる(手前と奥をならして存在しない
    面を作るため)。ここが両者を分ける検査。
    """
    V, F, _ = _scene()
    kw = dict(pose=render3d.look_at([4.0, -5.0, 4.0], [0.0, 0.0, 0.5], up=(0, 0, 1)),
              intrinsics=render3d.intrinsics_from_fov(40.0, 128, 128),
              width=128, height=128, directional=True, penumbra=0.0, samples=1,
              shadow_res=256)
    soft = render_shadow.cast_shadow(V, F, np.array([0.4, 0.5, 0.8]), pcf=2, **kw)
    assert float(soft.min()) >= 0.0 and float(soft.max()) <= 1.0
    assert float(soft.min()) == 0.0, "影の芯が完全な影でなくなっている"
    assert int((soft >= 1.0).sum()) > 1000, "照らされている領域が痩せている"


def test_pcf_rejects_a_silly_radius():
    """fail-closed: 負や大きすぎる半径は黙って丸めず拒否する。"""
    V, F, _ = _scene()
    kw = dict(width=48, height=48, shadow_res=128)
    with pytest.raises(ValueError, match="pcf"):
        render_shadow.cast_shadow(V, F, np.array([0.4, 0.5, 0.8]), pcf=-1, **kw)
    with pytest.raises(ValueError, match="pcf"):
        render_shadow.cast_shadow(V, F, np.array([0.4, 0.5, 0.8]), pcf=99, **kw)


def test_penumbra_width_follows_the_light_angular_radius():
    """半影の広さが角半径とともに広がる(記事の「ソフトシャドウ」の根拠)。

    既定の 2.5 度が「柔らかい」と言えるほどではないことを、数で示しておく。
    """
    V, F, n_ground = _scene()
    pose = render3d.look_at([4.0, -5.0, 4.0], [0.0, 0.0, 0.5], up=(0, 0, 1))
    K = render3d.intrinsics_from_fov(40.0, 128, 128)
    widths = []
    for pen in (2.5, 12.0):
        sm = render_shadow.cast_shadow(
            V, F, np.array([0.4, 0.5, 0.8]), pose=pose, intrinsics=K,
            width=128, height=128, directional=True, penumbra=pen, samples=16,
            shadow_res=256, pcf=1)
        widths.append(int(((sm > 0.02) & (sm < 0.98)).sum()))
    assert widths[1] > 2 * widths[0], (
        f"角半径を 4.8 倍にしても半影が広がっていない: {widths}")
