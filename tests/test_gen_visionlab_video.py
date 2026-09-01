# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""``tools/gen_visionlab_video`` の軽量な契約テスト。

動画そのものは目で見るものなので、ここで固定するのは絵ではなく**記事に書く数字が
壊れない条件**である:

  1. **決定的** — 同じ引数は同じフレームを返す(seed 固定が効いていること)。
  2. **オーバーレイの数字が実測** — 画面に出す光学限界が
     ``visiondesign.resolving_power`` の返り値そのものであること(表示のためだけの
     二重定義を持たない)。
  3. **フレーム数の検証が本当に効く** — ``_verify`` が食い違いを見逃さないこと。
     ここが甘いと「書けたつもり」の報告が通ってしまう。
"""
import os
import sys

import numpy as np
import pytest

pytest.importorskip("scipy")
pytest.importorskip("PIL")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import gen_visionlab_video as gvv                       # noqa: E402
import visiondesign as vd                               # noqa: E402


def _quiet(_msg):
    pass


def test_sweep_frames_are_deterministic_and_well_formed():
    a, facts_a = gvv.build_sweep_frames(frames=4, seeds=2, log=_quiet)
    b, facts_b = gvv.build_sweep_frames(frames=4, seeds=2, log=_quiet)
    assert len(a) == len(b) == 4
    for fa, fb in zip(a, b):
        assert fa.dtype == np.uint8 and fa.shape == (gvv.H, gvv.W, 3)
        assert np.array_equal(fa, fb), "同じ引数で違うフレームが出ている(seed 漏れ)"
    assert facts_a["optical_limit_um"] == facts_b["optical_limit_um"]
    # 幅・高さは偶数(H.264 の要求。奇数だと write_video が黙ってパディングする)
    assert gvv.W % 2 == 0 and gvv.H % 2 == 0


def test_overlaid_optical_limit_comes_from_the_optics_function():
    """画面の光学限界は resolving_power の返り値そのもの(表示用の再実装をしない)。"""
    frames, facts = gvv.build_sweep_frames(frames=3, seeds=1, log=_quiet)
    geo = facts["geometry"]
    res = vd.resolving_power(geo["focal_mm"] and 3.45, 4.0, geo["magnification"], 0.55)
    assert facts["optical_limit_um"] == pytest.approx(res["resolution_object_um"], rel=1e-12)
    assert facts["limited_by"] == res["limited_by"]
    assert facts["optical_limit_um"] > 0.0


def test_detection_onset_is_a_measurement_not_a_constant():
    """検出開始サイズは掃引の実測から出る(定数ではない)ので、系を変えれば動く。"""
    _, near = gvv.build_sweep_frames(frames=10, seeds=3, working_distance_mm=200.0,
                                     log=_quiet)
    _, far = gvv.build_sweep_frames(frames=10, seeds=3, working_distance_mm=320.0,
                                    log=_quiet)
    # 離れれば µm/画素が粗くなり、光学限界も検出も大きい欠陥側へ動く
    assert far["optical_limit_um"] > near["optical_limit_um"]
    if near["detection_start_um"] is not None and far["detection_start_um"] is not None:
        assert far["detection_start_um"] >= near["detection_start_um"]


def test_design_frames_report_the_crossing_point():
    """作動距離掃引は、光学限界が欠陥サイズを追い越す点を実測で持つこと。"""
    frames, facts = gvv.build_design_frames(frames=6, seeds=1, log=_quiet)
    assert len(frames) == 6
    assert facts["optical_um_last"] > facts["optical_um_first"]
    assert facts["um_per_pixel_last"] > facts["um_per_pixel_first"]
    assert facts["optical_cross_wd_mm"] is not None
    assert facts["optical_um_last"] > facts["defect_um"]


def test_frame_count_verification_actually_fails_on_a_mismatch(tmp_path):
    """検証が甘いと「書けたつもり」が通る — 食い違いを必ず例外にすること。"""
    imageio = pytest.importorskip("imageio")
    import video

    frames = [np.full((8, 8, 3), v, np.uint8) for v in (10, 90, 200)]
    path = str(tmp_path / "tiny.gif")
    video.write_video(path, frames, fps=5)
    ok = gvv._verify(path, 3, _quiet)
    assert ok["frames"] == 3 and ok["bytes"] > 0
    with pytest.raises(RuntimeError, match="expected 4"):
        gvv._verify(path, 4, _quiet)
    del imageio
