"""Headless tests for the sensor / camera simulation suite (evis unified vision I/F):
LIDAR, focus stacking, event camera, stereo, polarization. Each asserts an honest,
measured property of the simulated sensor — not just that a file was written."""
import importlib.util
import os

import pytest


def _need_mujoco():
    if importlib.util.find_spec("mujoco") is None:
        pytest.skip("mujoco 未インストール")


def test_lidar_op_registered():
    import unified as u
    assert "lidar_scan" in u.ops


def test_lidar_returns_points(tmp_path):
    """LIDAR の実レイキャストが点群を返し、命中率が妥当な範囲に入る。"""
    _need_mujoco()
    import lidar_sim as LS
    out = str(tmp_path / "lidar.png")
    r = LS.run_lidar_demo(out, channels=16, az_steps=120, log=lambda *_: None)
    assert os.path.isfile(out) and os.path.getsize(out) > 0
    assert r["n_points"] > 100                                # beams actually hit geometry
    assert 0.05 < r["hit_ratio"] < 0.95                       # not all-miss, not all-hit
    assert r["mean_range_m"] > 0


def test_focus_stack_op_registered():
    import unified as u
    assert "focus_stack" in u.ops


def test_focus_stack_beats_single_frames(tmp_path):
    """全焦点合成が各単フレームよりシャープで、焦点由来深度が真値と相関する。"""
    _need_mujoco()
    import focus_stack as FS
    out = str(tmp_path / "fs.png")
    r = FS.run_focus_stack_demo(out, n_focus=6, log=lambda *_: None)
    assert os.path.isfile(out) and os.path.getsize(out) > 0
    assert r["beats_all_frames"] is True and r["sharpness_gain"] > 1.0
    assert r["depth_focus_corr"] > 0.5                        # focus cue tracks true depth


def test_event_camera_op_registered():
    import unified as u
    assert "event_camera" in u.ops


def test_event_camera_fires_on_edges(tmp_path):
    """DVS イベントが生成され、動くエッジに集中する(掃引エッジと相関)。"""
    _need_mujoco()
    import event_camera as EC
    out = str(tmp_path / "ev.png")
    r = EC.run_event_demo(out, n_frames=16, log=lambda *_: None)
    assert os.path.isfile(out) and os.path.getsize(out) > 0
    assert r["n_events"] > 0 and r["fires_on_edges"] is True
    assert r["edge_corr"] > 0.3


def test_stereo_op_registered():
    import unified as u
    assert "stereo_depth" in u.ops


def test_stereo_depth_matches_truth(tmp_path):
    """ブロックマッチングのステレオ深度が真値深度と一致する(中央誤差<5cm)。"""
    _need_mujoco()
    import stereo_sim as SS
    out = str(tmp_path / "st.png")
    r = SS.run_stereo_demo(out, log=lambda *_: None)
    assert os.path.isfile(out) and os.path.getsize(out) > 0
    assert r["matches_truth"] is True
    assert r["median_err_m"] < 0.05 and r["depth_corr"] > 0.4
