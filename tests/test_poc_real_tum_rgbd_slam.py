# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""``examples/poc_real_tum_rgbd_slam.py`` の部品の門(入口の拒否・真値の姿勢・推定器の検算・同梱の固定)。

全編(ICP 31 組 × 4 設定)は 1 分以上かかるので ``tests/test_poc_scripts_run.py`` に任せ、ここは速い部品だけ回す。
"""
from __future__ import annotations

import hashlib
import math

import numpy as np
import pytest

import realdata
from examples import poc_real_tum_rgbd_slam as poc


def test_bundled_files_match_their_pins():
    for name, (size, digest) in poc.BUNDLED.items():
        raw = poc.load_bundled(name)
        assert len(raw) == size and hashlib.sha256(raw).hexdigest() == digest


def test_every_bundled_depth_file_is_listed_and_the_set_is_small():
    listed = [ln.split()[1] for ln in poc.load_bundled("depth_subset.txt").decode().splitlines() if ln and ln[0] != "#"]
    assert len(listed) == 32
    assert all(name in poc.BUNDLED for name in listed)
    total = sum(size for size, _ in poc.BUNDLED.values())
    assert total < 5_000_000          # Pages の容量に余裕が少ないので、数 MB に収める


def test_a_tampered_bundled_file_is_refused(tmp_path, monkeypatch):
    name = "depth_subset.txt"
    bad = tmp_path / name
    data = bytearray((poc.DATA / name).read_bytes())
    data[10] ^= 0xFF
    bad.write_bytes(bytes(data))
    monkeypatch.setattr(poc, "DATA", tmp_path)
    with pytest.raises(realdata.RealDataError, match="SHA-256"):
        poc.load_bundled(name)


def test_unlisted_file_is_a_key_error():
    with pytest.raises(KeyError):
        poc.load_bundled("not_in_the_ledger.png")


def test_loading_marks_the_real_data_read(tmp_path, monkeypatch):
    log = tmp_path / "read.log"
    monkeypatch.setenv(realdata.REAL_DATA_LOG_ENV, str(log))
    seq = poc.load_sequence()
    assert len(seq["depth"]) == 32 and seq["depth"][0].shape == poc.IMG_SHAPE
    assert "tum-rgbd-fr1-xyz" in log.read_text(encoding="utf-8").split()


def test_real_frames_have_the_expected_valid_fraction_and_scale():
    seq = poc.load_sequence()
    assert len(seq["depth"]) == 32
    for d in seq["depth"]:
        frac = poc.check_depth(d)
        assert 0.6 < frac < 0.9
        assert 0.4 < float(np.median(d[d > 0])) < 2.0      # 机の上を 0.4〜2 m で撮っている(倍率 5000 の確認)


@pytest.mark.parametrize("label", ["zeros", "mostly_zero", "nan", "negative", "shape", "int_mode"])
def test_bad_depth_is_rejected(label):
    seq = poc.load_sequence()
    d = seq["depth"][0].copy()
    if label == "zeros":
        d = np.zeros_like(d)
    elif label == "mostly_zero":
        d[60:, :] = 0.0
    elif label == "nan":
        d[3, 3] = np.nan
    elif label == "negative":
        d[3, 3] = -1.0
    elif label == "shape":
        d = d[:100]
    if label == "int_mode":
        from PIL import Image
        import io
        buf = io.BytesIO()
        Image.fromarray(np.zeros((480, 640), np.uint8)).save(buf, format="PNG")
        with pytest.raises(poc.DepthRejected, match="16 bit"):
            poc.decode_depth(buf.getvalue())
        return
    with pytest.raises(poc.DepthRejected):
        poc.check_depth(d)
    with pytest.raises(poc.DepthRejected):
        poc.make_cloud(d)


def test_quaternion_and_slerp_basics():
    assert np.allclose(poc.quat_to_matrix([0, 0, 0, 1]), np.eye(3))
    q = [0, 0, math.sin(math.radians(45)), math.cos(math.radians(45))]      # z 軸まわり 90°
    R = poc.quat_to_matrix(q)
    assert np.allclose(R @ [1, 0, 0], [0, 1, 0], atol=1e-12)
    assert abs(poc.rotation_angle_deg(R) - 90.0) < 1e-9
    mid = poc.slerp([0, 0, 0, 1], q, 0.5)
    assert abs(poc.rotation_angle_deg(poc.quat_to_matrix(mid)) - 45.0) < 1e-9


def test_ground_truth_gaps_are_small_and_out_of_range_times_are_refused():
    seq = poc.load_sequence()
    traj = poc.trajectory(seq)
    assert float(traj["gaps"].max()) <= poc.MAX_GT_GAP_S and len(traj["rel"]) == 31
    with pytest.raises(poc.DepthRejected, match="範囲の外"):
        poc.gt_pose_at(seq["gt"], float(seq["gt"][0, 0]) - 1.0)


def test_identity_baseline_equals_the_true_motion_and_perfect_estimate_has_zero_error():
    seq = poc.load_sequence()
    traj = poc.trajectory(seq)
    assert len(traj["rel"]) == 31
    assert len(traj["ident_t"]) == 31
    for rel, t_id in zip(traj["rel"], traj["ident_t"]):
        assert abs(float(np.linalg.norm(rel[:3, 3])) - t_id) < 1e-9   # 合わせない誤差 = 真値の動きの大きさ
        assert poc.pair_errors(rel, rel)[0] < 1e-12                           # 真値そのものなら誤差 0
    assert float(np.median(traj["ident_t"])) > 0.03                           # 動いている(5 枚おきで数 cm)
    ate, _ = poc.ate_rmse(poc.chain_of(traj["rel"]), traj["poses"])
    assert ate < 1e-9                                                         # 真値の鎖は ATE 0


def test_rigid_align_recovers_a_known_transform():
    rng = np.random.default_rng(0)
    a = rng.normal(size=(40, 3))
    th = 0.7
    R = np.array([[math.cos(th), -math.sin(th), 0], [math.sin(th), math.cos(th), 0], [0, 0, 1]])
    b = a @ R.T + np.array([1.0, -2.0, 0.5])
    R2, t2 = poc.rigid_align(a, b)
    assert np.allclose(R2, R, atol=1e-10) and np.allclose(t2, [1.0, -2.0, 0.5], atol=1e-10)


def test_tile_estimator_floor_and_added_noise_are_recovered():
    flat = poc.tile_residuals(poc.synthetic_plane_depth(0.0))
    assert len(flat) > 100 and float(np.median([r[1] for r in flat])) < 3e-4
    noisy = poc.tile_residuals(poc.synthetic_plane_depth(0.003))
    assert abs(float(np.median([r[1] for r in noisy])) - 3e-3) < 3e-4


def test_registration_beats_not_registering_on_one_adjacent_pair():
    seq = poc.load_sequence()
    traj = poc.trajectory(seq)
    i = 2                                       # 動きが小さい組(真値で約 60 mm)
    src, dst = poc.make_cloud(seq["depth"][i + 1]), poc.make_cloud(seq["depth"][i])
    est = poc.register_pair(src, dst, 0.2)
    err_t, err_r = poc.pair_errors(est, traj["rel"][i])
    assert err_t < 0.5 * traj["ident_t"][i] and err_r < 1.0


def test_bin_medians_requires_enough_tiles_and_frames():
    rec = [(0.6, 0.001, 0, 0, 0)] * 29 + [(0.8, 0.002, 0, 0, f) for f in range(6) for _ in range(6)]
    rows = poc.bin_medians(rec)
    assert [round(r["z"], 1) for r in rows] == [0.8]       # 0.6 は 29 個で足りず、1 枚からなので落ちる
    assert poc.bin_medians([]) == []
