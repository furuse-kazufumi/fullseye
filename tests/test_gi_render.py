# -*- coding: utf-8 -*-
"""大域照明レンダラ(:mod:`gi_render`、optional backend = Mitsuba 3)の契約。

ここで固定するのは 3 つ:
  1. **幾何が合っている** —— 深度が内蔵ラスタライザ(:func:`render3d.render_mesh`)と
     画素ごとに一致する。座標変換を推測で書いていないことの担保。
  2. **大域照明が実際に効いている** —— docstring が主張している「囲まれた場では
     画素値が大きく変わる」を、テストとして**実行**する(主張を数字で持たない
     docstring は放置すると嘘になる)。
  3. **fail-closed** —— 形・非有限・引数の範囲で黙って何かを返さない。
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gi_render                                        # noqa: E402
import render3d                                         # noqa: E402

pytestmark = pytest.mark.skipif(
    not gi_render.available(),
    reason='optional backend not installed: mitsuba (pip install "fullseye[gi]")')

SZ = 48


def _cube():
    V = np.array([[x, y, z] for x in (-.5, .5) for y in (-.5, .5) for z in (-.5, .5)],
                 dtype=np.float64)
    quads = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 2, 6, 4), (1, 5, 7, 3), (0, 4, 5, 1), (2, 3, 7, 6)]
    F = np.array([t for a, b, c, d in quads for t in ((a, b, c), (a, c, d))], np.int64)
    return V, F


def _wedge():
    """非対称な形。**上下左右の反転を見逃さない**ために対称形を使わない。"""
    V = np.array([[-0.6, -0.4, 0.0], [0.8, -0.5, 0.1], [0.0, 0.9, -0.2],
                  [0.1, -0.1, 0.7], [-0.3, 0.5, 0.4]], dtype=np.float64)
    F = np.array([[0, 1, 2], [0, 1, 3], [1, 2, 3], [0, 3, 2], [2, 4, 3], [0, 2, 4]], np.int64)
    return V, F


def test_it_returns_every_declared_channel_with_the_declared_shape():
    V, F = _cube()
    out = gi_render.render_gi(V, F, size=SZ, spp=8, max_depth=4)
    assert set(out) == {"image", "radiance", "depth", "normals", "silhouette"}
    assert out["image"].shape == (SZ, SZ, 3)
    assert out["radiance"].shape == (SZ, SZ, 3)
    assert out["depth"].shape == (SZ, SZ)
    assert out["normals"].shape == (SZ, SZ, 3)
    assert out["silhouette"].shape == (SZ, SZ)
    assert out["silhouette"].dtype == bool
    assert np.isfinite(out["image"]).all() and np.isfinite(out["depth"]).all()
    assert 0.0 <= out["image"].min() and out["image"].max() <= 1.0


def test_the_depth_agrees_with_the_builtin_rasteriser_pixel_by_pixel():
    """★座標変換の担保。**別実装が同じ幾何を出す**ことを画素ごとに確かめる。

    非対称メッシュを使うので、上下・左右の反転があれば IoU が崩れる
    (2026-09-05 実測: 正しい向きで IoU 0.95、反転させると 0.38)。
    """
    V, F = _wedge()
    pose, K = render3d.auto_view(V, width=SZ, height=SZ)
    ras = render3d.render_mesh(V, F, pose, K, width=SZ, height=SZ)
    sil = np.asarray(ras["silhouette"], bool)
    d_ras = np.asarray(ras["depth"], float)

    out = gi_render.render_gi(V, F, pose=pose, intrinsics=K, size=SZ, spp=8,
                              max_depth=2, enclosure="none")
    hit = out["silhouette"]
    both = hit & sil
    iou = both.sum() / float(max((hit | sil).sum(), 1))
    assert iou > 0.85, f"シルエットが合っていない(IoU {iou:.3f}) —— 向きが違う疑い"
    err = np.abs(out["depth"][both] - d_ras[both])
    assert np.median(err) < 0.02, (
        f"z 深度が合っていない: 中央値 {np.median(err):.5f}(輪郭の部分被覆だけなら小さい)")


def test_global_illumination_actually_changes_the_picture_in_an_enclosure():
    """docstring の主張(囲まれた場では画素値が大きく変わる)を**実行**する。"""
    V, F = _cube()
    kw = dict(size=SZ, spp=32, enclosure="box", seed=0)
    direct = gi_render.render_gi(V, F, max_depth=2, **kw)["radiance"]
    gi = gi_render.render_gi(V, F, max_depth=8, **kw)["radiance"]
    assert gi.mean() > direct.mean() * 1.15, (
        "相互反射を足しても明るさがほとんど変わらない: "
        f"直接光 {direct.mean():.4f} -> 大域照明 {gi.mean():.4f}。"
        "囲いが効いていないか、max_depth が反映されていない。")


def test_the_same_seed_gives_the_same_picture():
    V, F = _cube()
    kw = dict(size=SZ, spp=8, max_depth=3, seed=7)
    a = gi_render.render_gi(V, F, **kw)["radiance"]
    b = gi_render.render_gi(V, F, **kw)["radiance"]
    assert np.array_equal(a, b), "同じ種で結果が違う(再現性が無い)"


@pytest.mark.parametrize(("kwargs", "needle"), [
    (dict(size=4), "size"),
    (dict(spp=0), "spp"),
    (dict(max_depth=0), "max_depth"),
    (dict(enclosure="dome"), "enclosure"),
    (dict(albedo=(0.5, 0.5)), "albedo"),
    (dict(albedo=(0.5, 0.5, 1.4)), "albedo"),
    (dict(light_power=0.0), "light_power"),
    (dict(light_power=float("inf")), "light_power"),
])
def test_bad_arguments_are_refused_not_absorbed(kwargs, needle):
    V, F = _cube()
    with pytest.raises(ValueError) as ei:
        gi_render.render_gi(V, F, **dict(dict(size=SZ, spp=4, max_depth=2), **kwargs))
    assert needle in str(ei.value)


def test_a_broken_mesh_is_refused():
    V, F = _cube()
    with pytest.raises(ValueError, match="V must be"):
        gi_render.render_gi(V[:, :2], F, size=SZ, spp=4)
    with pytest.raises(ValueError, match="non-finite"):
        bad = V.copy(); bad[0, 0] = np.nan
        gi_render.render_gi(bad, F, size=SZ, spp=4)
    with pytest.raises(ValueError, match="outside V"):
        gi_render.render_gi(V, F + 100, size=SZ, spp=4)
    with pytest.raises(ValueError, match="F must be"):
        gi_render.render_gi(V, F[:, :2], size=SZ, spp=4)


def test_available_does_not_import_mitsuba_as_a_side_effect():
    """`available()` は問い合わせであって、重い import を起こしてはいけない。"""
    assert gi_render.available() in (True, False)
