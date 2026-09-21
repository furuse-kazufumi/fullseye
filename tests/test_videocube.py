# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""videocube(動画の空間 × 時間の立方体、Video Summagator の再実装)の門: 合成クリップの真値で固定する。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import videocube as V  # noqa: E402

_OPS = ["video_spacetime_cube", "vol_render_transfer", "video_cube_cut", "video_cube_orbit", "video_summary_keyframes",
        "video_write_gif"]


def clip(T=32, H=48, W=64, row=20, vx=2.0, t0=4, noise=0.0, seed=0):
    """静止した縞の背景の上を、行 ``row`` に沿って速度 ``vx`` px/frame で右へ動く円(t0 から)。"""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:H, 0:W]
    bg = 0.4 + 0.1 * np.sin(xx / 5.0)
    out = np.empty((T, H, W))
    for t in range(T):
        f = bg.copy()
        if t >= t0:
            f[np.hypot(yy - row, xx - (6 + (t - t0) * vx)) < 4] = 0.95
        out[t] = f + noise * rng.standard_normal((H, W))
    return out


def test_motion_cube_lights_only_the_moving_object():
    v = clip()
    A = V.video_spacetime_cube(v, "motion")
    assert A.shape == v.shape and A.min() >= 0.0 and A.max() <= 1.0
    assert A[0].max() == 0.0                                  # 先頭フレームは差分なし
    yy, _xx = np.mgrid[0:48, 0:64]
    far = np.abs(yy - 20) > 8                                 # 物体の通り道(行 20 ± 半径 4)から離れた画素
    assert A[:, far].max() == 0.0                             # 静止した背景は 0(雑音なし)
    assert A[10].max() == 1.0                                 # 動いている縁は 1
    I = V.video_spacetime_cube(v, "intensity")
    assert I.min() == 0.0 and I.max() == 1.0
    # 雑音は床の下に沈む
    An = V.video_spacetime_cube(clip(noise=0.01), "motion")
    assert (An[:, far] > 0).mean() < 0.01
    with pytest.raises(ValueError, match="video_spacetime_cube: mode"):
        V.video_spacetime_cube(v, "colour")
    with pytest.raises(ValueError, match="video_spacetime_cube: video must be"):
        V.video_spacetime_cube(v[0])


def test_cut_planes_read_speed_as_slope():
    v = clip(row=20, vx=2.0, t0=4)
    xt = V.video_cube_cut(v, "xt", position=20 / 47)          # 行 20 のスリットスキャン (T, W)
    assert xt.shape == (32, 64)
    cols = np.array([int(np.argmax(xt[t])) for t in range(6, 26)])
    slope = np.polyfit(np.arange(6, 26), cols, 1)[0]
    assert abs(slope - 2.0) < 0.2                             # 傾き = 速度 px/frame
    assert V.video_cube_cut(v, "yt", 0.5).shape == (32, 48)
    assert np.array_equal(V.video_cube_cut(v, "xy", 0.0), v[0])
    assert np.array_equal(V.video_cube_cut(v, "xy", 1.0), v[-1])
    with pytest.raises(ValueError, match="video_cube_cut: plane"):
        V.video_cube_cut(v, "tz")
    with pytest.raises(ValueError, match="video_cube_cut: position"):
        V.video_cube_cut(v, "xt", 1.5)


def test_render_shows_the_trail_coloured_by_time_and_nothing_where_nothing_moved():
    v = clip()
    A = V.video_spacetime_cube(v)
    img = V.vol_render_transfer(A, yaw=0.0, pitch=0.0, size=96, frame=False)  # 時間軸を奥行きに = 動画を正面から
    assert img.shape == (96, 96, 3) and img.min() >= 0.0 and img.max() <= 1.0
    bg = np.array([0.04, 0.04, 0.06])
    lit = np.abs(img - bg).sum(-1) > 0.05
    assert 0.02 < lit.mean() < 0.4                            # 軌跡だけが光る
    # 物体は右へ動くので、正面から見た軌跡は左が早い(青)・右が遅い(赤)
    cols = np.nonzero(lit.any(0))[0]
    left, right = img[:, cols[:8]][lit[:, cols[:8]]].mean(0), img[:, cols[-8:]][lit[:, cols[-8:]]].mean(0)
    assert left[2] > left[0] and right[0] > right[2]
    # 側面(yaw 90)から見ると軌跡は時間軸に沿って伸び、青 → 赤の順序が横に並ぶ
    side = V.vol_render_transfer(A, yaw=90.0, pitch=0.0, size=96, frame=False)
    lit_s = np.abs(side - bg).sum(-1) > 0.05
    cols = np.nonzero(lit_s.any(0))[0]
    left, right = side[:, cols[:5]][lit_s[:, cols[:5]]].mean(0), side[:, cols[-5:]][lit_s[:, cols[-5:]]].mean(0)
    assert (left[2] - left[0]) * (right[2] - right[0]) < 0    # 片端は青寄り、もう片端は赤寄り
    # 背景の薄い層は合計の不透明度で決まる(サンプル数に依らない)
    # 静止した背景だけ(color=None → 灰 0.5)
    a = V.vol_render_transfer(np.zeros_like(A), yaw=0.0, pitch=0.0, size=32, static_alpha=0.3, frame=False, depth_samples=16)
    b = V.vol_render_transfer(np.zeros_like(A), yaw=0.0, pitch=0.0, size=32, static_alpha=0.3, frame=False, depth_samples=128)
    assert abs(float(a[16, 16].mean()) - float(b[16, 16].mean())) < 0.03
    # 正面から中心を貫く視線は t 方向の 32 サンプル分 = 最長辺 64 の半分 → 合計 1 − 0.7^0.5
    total = 1.0 - 0.7 ** (32.0 / 64.0)
    assert abs(float(b[16, 16, 0]) - (total * 0.5 + (1.0 - total) * 0.04)) < 0.03
    with pytest.raises(ValueError, match="vol_render_transfer: vol must be opacities"):
        V.vol_render_transfer(A * 2.0)
    with pytest.raises(ValueError, match="vol_render_transfer: color shape"):
        V.vol_render_transfer(A, A[:-1])
    with pytest.raises(ValueError, match="vol_render_transfer: size"):
        V.vol_render_transfer(A, size=4)


def test_orbit_and_keyframes():
    v = clip(T=24)
    fr = V.video_cube_orbit(v, n_frames=4, size=48)
    assert fr.shape == (4, 48, 48, 3) and fr.min() >= 0.0 and fr.max() <= 1.0
    assert not np.allclose(fr[0], fr[1])                      # 回っている
    # 代表フレーム: 物体が現れる t0=4 の直後が入り、間隔が min_gap 以上
    idx = V.video_summary_keyframes(v, k=3)
    assert idx.shape == (3,) and idx.dtype == np.int64 and np.all(np.diff(idx) >= 24 // 6)
    assert any(3 <= int(i) <= 6 for i in idx), idx
    assert np.array_equal(V.video_summary_keyframes(v[:2], k=5), np.array([0, 1]))
    with pytest.raises(ValueError, match="video_cube_orbit: color"):
        V.video_cube_orbit(v, n_frames=1, size=16, color="rainbow")
    with pytest.raises(ValueError, match="video_summary_keyframes: k"):
        V.video_summary_keyframes(v, k=0)


def test_dark_mode_turns_a_z_stack_of_sections_into_membranes():
    """EM の連続断面(膜 = 暗い)を同じ立方体として見る: 暗い所だけが不透明になる。"""
    yy, xx = np.mgrid[0:40, 0:40]
    stack = np.full((8, 40, 40), 0.8)
    for z in range(8):
        stack[z][np.abs(np.hypot(yy - 20, xx - 20) - (10 + z)) < 1.2] = 0.1     # z ごとに広がる暗い輪
    A = V.video_spacetime_cube(stack, "dark", sigma=0.5)
    assert A.shape == stack.shape and A.max() == 1.0
    assert A[3, 20, 20] == 0.0 and A[3][np.abs(np.hypot(yy - 20, xx - 20) - 13) < 0.6].mean() > 0.5
    B = V.video_spacetime_cube(1.0 - stack, "bright", sigma=0.5)
    assert np.allclose(A, B)
    fr = V.video_cube_orbit(stack, n_frames=2, size=32, mode="dark", color="intensity", depth_samples=8)
    assert fr.shape == (2, 32, 32, 3)
    with pytest.raises(ValueError, match="video_cube_orbit: mode"):
        V.video_cube_orbit(stack, n_frames=1, size=16, mode="intensity")


def test_write_gif_keeps_every_frame(tmp_path):
    pytest.importorskip("PIL")
    v = clip(T=6, H=16, W=20)
    p = str(tmp_path / "grey.gif")
    assert V.video_write_gif(v, p, fps=5.0) == p
    from PIL import Image
    with Image.open(p) as im:
        assert im.n_frames == 6
    rgb = V.video_cube_orbit(v, n_frames=3, size=16, depth_samples=6)
    p2 = str(tmp_path / "cube.gif")
    V.video_write_gif(rgb, p2)
    with Image.open(p2) as im:
        assert im.n_frames == 3 and im.size == (16, 16)
    with pytest.raises(ValueError, match="video_write_gif: path"):
        V.video_write_gif(v, str(tmp_path / "x.png"))
    with pytest.raises(ValueError, match="video_write_gif: frames"):
        V.video_write_gif(v[0], p)


# --------------------------------------------------------------------------- #
# 台帳と公開経路                                                               #
# --------------------------------------------------------------------------- #
def test_the_ledger_lists_every_op_and_nothing_is_missing():
    import opsvideocube

    assert opsvideocube.missing() == []
    assert set(opsvideocube.OPSVIDEOCUBE) == set(_OPS) == set(V.__all__) - {"MAX_CUBE_ELEMENTS", "CUBE_MODES", "CUT_PLANES"}
    assert len(opsvideocube.categories()) == 4


def test_every_op_is_reachable_from_the_public_tier():
    import fullseye as fs
    import opsvideocube

    for name in opsvideocube.OPSVIDEOCUBE:
        assert hasattr(fs.ledger, name), name


def test_the_typed_catalog_declares_the_family():
    import typed_catalog as tc

    rows = [r for r in tc.catalog() if r[1] == "videocube"]
    assert {r[0] for r in rows} == set(_OPS)
    assert {r[3] for r in rows} == {"voxel", "image2d", "rgb", "rgbvideo", "indices", "text"}


def test_the_fuzzer_has_predicates_and_seeds_for_every_sort():
    sys.path.insert(0, str(ROOT / "tools"))
    import chain_fuzz as cf
    import opsvideocube

    gens = cf.make_generators()
    for name, meta in opsvideocube.OPSVIDEOCUBE.items():
        assert meta["out"] in cf.TYPE_CHECKS, name
        for s in meta["in"]:
            assert s in cf.TYPE_CHECKS and s in gens, (name, s)
    vid = gens["video"](np.random.default_rng(0))
    assert cf.TYPE_CHECKS["voxel"](V.video_spacetime_cube(vid))
    assert cf.TYPE_CHECKS["rgb"](V.vol_render_transfer(V.video_spacetime_cube(vid), size=16, depth_samples=8))


def test_op_run_works_for_every_op(tmp_path):
    import fullseye as fs

    v = clip(T=12, H=24, W=32)
    run = lambda *a, **k: fs.op_run(*a, **k)[0]     # noqa: E731
    A = run("video_spacetime_cube", v)
    assert A.shape == v.shape
    assert run("vol_render_transfer", A, size=24, depth_samples=8).shape == (24, 24, 3)
    assert run("video_cube_cut", v, plane="xt").shape == (12, 32)
    fr = run("video_cube_orbit", v, n_frames=2, size=16)
    assert fr.shape == (2, 16, 16, 3)
    assert run("video_summary_keyframes", v, k=2).shape == (2,)
    pytest.importorskip("PIL")
    assert run("video_write_gif", fr, str(tmp_path / "o.gif")).endswith("o.gif")


def test_the_family_guide_exists_and_names_its_ops():
    p = ROOT / "docs" / "ops" / "videocube" / "guides" / "videocube.md"
    assert p.exists()
    md = p.read_text(encoding="utf-8")
    assert "```mermaid" in md and "vol_render_transfer" in md and "video_cube_cut" in md
    assert os.path.isdir(ROOT / "docs" / "ops" / "videocube")
