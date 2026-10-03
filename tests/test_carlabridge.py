# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""carlabridge の門: CARLA の客体が返した回転行列(焼き込み)との一致、カメラ姿勢 = look_at、深度の往復 ≤ 量子化 1 段、
ラベルの往復(恒等)、場面記録の往復(自前の世界 → CARLA の規約 → 読み直して描き直すと画素単位で同じ)、閉形式の真値と
深度の中央値、車の画素数 ∝ 1/d²、fail-closed の ValueError。実際の CARLA の撮影記録は FULLSEYE_CARLA_DATA がある時だけ
(CI には無い)。examples/poc_carla_bridge.py の門を単体テストにしたもの。"""
import glob
import json
import math
import os

import numpy as np
import pytest

import carlabridge as CB
import driveworld as DW

#: carla.Transform(...).get_matrix() が返した値(0.9.16 の客体、2026-10-04)—— 同じ式の第 2 実装。
_CARLA_MATRICES = {
    (1.0, 2.0, 3.0, 10.0, 20.0, 30.0): [[0.8137976527, -0.4409696162, -0.3785222769, 1.0],
                                        [0.4698463082, 0.8825640678, -0.018028304, 2.0],
                                        [0.3420201242, -0.1631759107, 0.9254165292, 3.0]],
    (5.0, -4.0, 1.6, 0.0, -15.0, -120.0): [[-0.482962966, 0.8660253882, -0.1294095367, 5.0],
                                           [-0.8365162611, -0.5000000596, -0.2241438627, -4.0],
                                           [-0.2588190436, 0.0, 0.9659258127, 1.6]],
    (0.0, 0.0, 0.0, 0.0, 0.0, 90.0): [[0.0, -1.0, 0.0, 0.0], [1.0, 0.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0]],
}
#: 同じ客体で ``Transform.transform(Location(1, 0, 0))``(局所 +x の先)。
_CARLA_FORWARD = {
    (1.0, 2.0, 3.0, 10.0, 20.0, 30.0): (1.8137977123, 2.4698462486, 3.3420200348),
    (5.0, -4.0, 1.6, 0.0, -15.0, -120.0): (4.5170369148, -4.8365163803, 1.3411810398),
}
_DISTANCES = (8.0, 12.0, 16.0, 24.0, 32.0, 48.0, 64.0)


def test_rotation_matrix_matches_the_carla_client():
    for t, M in _CARLA_MATRICES.items():
        got = CB.carla_transform_matrix(t)
        assert np.allclose(got[:3, :], np.array(M), atol=2e-7), t
        r, p, y = CB.carla_rotation_angles(got[:3, :3])
        assert np.allclose((r, p, y), t[3:], atol=1e-6)
    for t, fwd in _CARLA_FORWARD.items():
        M = CB.carla_transform_matrix(t)
        assert np.allclose(M[:3, :3] @ [1, 0, 0] + M[:3, 3], fwd, atol=1e-6)


def test_pose_round_trips_and_mirrors_y_and_yaw():
    for t in _CARLA_MATRICES:
        T = CB.carla_pose_to_world(t)
        assert np.allclose(CB.world_pose_to_carla(T), t, atol=1e-9)
        assert np.isclose(T[1, 3], -t[1]) and np.isclose(T[0, 3], t[0]) and np.isclose(T[2, 3], t[2])
        assert abs(np.linalg.det(T[:3, :3]) - 1.0) < 1e-9          # 鏡映 2 回で固有回転のまま
    x, y, yaw = CB.carla_xy_yaw((3.0, 4.0, 0.0, 0.0, 0.0, 30.0))
    assert (x, y) == (3.0, -4.0) and np.isclose(yaw, -math.radians(30.0))


def test_camera_pose_agrees_with_look_at():
    h = 1.6
    for yaw_c, tgt in ((0.0, (1, 0, h)), (90.0, (0, -1, h)), (-90.0, (0, 1, h)), (180.0, (-1, 0, h))):
        P = CB.carla_camera_pose([0, 0, h, 0, 0, yaw_c])
        assert np.allclose(P, DW.camera_pose((0, 0, h), tgt), atol=1e-12), yaw_c
        assert np.allclose(CB.camera_pose_to_carla(P), [0, 0, h, 0, 0, yaw_c], atol=1e-9)
    P = CB.carla_camera_pose([0, 0, h, 0, 10.0, 0])                 # CARLA の pitch + = 前上がり
    L = DW.camera_pose((0, 0, h), (math.cos(math.radians(10)), 0, h + math.sin(math.radians(10))))
    assert np.allclose(P, L, atol=1e-12)
    # 任意の姿勢でも往復は恒等
    for t in _CARLA_MATRICES:
        assert np.allclose(CB.camera_pose_to_carla(CB.carla_camera_pose(t)), t, atol=1e-9)


def test_depth_round_trip_is_within_one_quantisation_step():
    rng = np.random.default_rng(3)
    d = rng.uniform(0.0, 300.0, (40, 50))
    d[0, 0] = np.inf
    d[0, 1] = 0.0
    d[0, 2] = 2000.0
    back = CB.carla_depth_decode(CB.carla_depth_encode(d))
    assert np.abs(back - np.minimum(d, 1000.0)).max() <= 0.5 * CB.DEPTH_SCALE_M / CB.DEPTH_CODE_MAX + 1e-12
    assert back[0, 0] == 1000.0 and back[0, 1] == 0.0 and back[0, 2] == 1000.0
    # 公表の復号式そのもの(R が下位)
    raw = np.zeros((1, 1, 3), np.uint8)
    raw[0, 0] = (1, 0, 0)
    assert np.isclose(CB.carla_depth_decode(raw)[0, 0], 1000.0 / CB.DEPTH_CODE_MAX)
    raw[0, 0] = (0, 0, 1)
    assert np.isclose(CB.carla_depth_decode(raw)[0, 0], 65536.0 * 1000.0 / CB.DEPTH_CODE_MAX)


def test_labels_cover_all_carla_tags_and_round_trip():
    rows = CB.carla_labels()
    assert len(rows) == 29 and {r["tag"] for r in rows} == set(range(29))
    assert {r["label"] for r in rows} <= set(DW.LABELS) | {-1}
    lab = np.array(sorted(CB.LABEL_TO_TAG))[None, :].astype(np.int64)
    back = CB.carla_label_map(CB.carla_label_unmap(lab))
    # CARLA に無いラベル(5 コーン・12 横断歩道)だけは代表タグで潰れる(障害物・路面)—— それ以外は恒等
    collapsed = {int(a) for a, b in zip(lab[0], back[0]) if a != b}
    assert collapsed == {5, 12}, collapsed
    assert back[0][lab[0] == 5] == 6 and back[0][lab[0] == 12] == 0
    sem = np.arange(29, dtype=np.uint8)[None, :]
    assert CB.carla_label_map(sem).shape == sem.shape
    with pytest.raises(ValueError):
        CB.carla_label_map(np.array([[200]], np.uint8))


def test_intrinsics_differ_only_by_half_a_pixel():
    Kc = CB.carla_intrinsics(90.0, 1280, 720)
    assert np.isclose(Kc[0, 0], 640.0) and Kc[0, 2] == 640.0 and Kc[1, 2] == 360.0
    Kf = CB.intrinsics_to_fullseye(Kc)
    assert Kf[0, 0] == Kc[0, 0] and Kf[0, 2] == 639.5 and Kf[1, 2] == 359.5
    assert np.array_equal(CB.intrinsics_to_carla(Kf), Kc)


def test_a_scene_record_round_trips_through_the_carla_conventions(tmp_path):
    sc = CB.carla_scene_synthetic(20.0, width=160, height=90)
    p = CB.carla_scene_save(sc, tmp_path / "s.npz")
    back = CB.carla_scene_load(p)
    assert back["meta"]["lead_distance_m"] == 20.0
    assert np.abs(back["depth"] - np.minimum(sc["depth"], 1000.0)).max() < 1e-4
    assert np.array_equal(CB.carla_label_map(back["semantic"]), sc["label"])
    r = CB.scene_pair_table(back)
    view = r["view"]
    assert np.array_equal(np.asarray(view["label"]), sc["label"])           # 描き直しが画素単位で同じ
    d0 = np.where(np.isfinite(sc["depth"]), sc["depth"], 1000.0)
    d1 = np.where(np.isfinite(view["depth"]) & (np.asarray(view["label"]) >= 0), view["depth"], 1000.0)
    assert np.abs(d0 - d1).max() < 1e-9
    assert np.isclose(r["truth"], 20.0) and r["carla"]["found"] and r["fullseye"]["found"]
    assert np.isclose(r["carla"]["depth_median"], r["fullseye"]["depth_median"])


def test_depth_median_tracks_the_closed_form_truth_and_pixels_follow_inverse_square():
    ns, errs, rows = [], [], []
    for d in _DISTANCES:
        sc = CB.carla_scene_synthetic(d, width=320, height=180)
        assert np.isclose(CB.lead_truth_depth(sc), d)
        K = CB.intrinsics_to_fullseye(sc["K"])
        r = CB.lead_from_depth(sc["depth"], sc["label"], K, 1.6)
        assert r["found"]
        ns.append(r["n_pixels"])
        errs.append(r["depth_median"] - d)
        # 最下行 = 後輪の接地(バンパーより ≤ 1 m 前)+ 行の量子化(1 行ぶんの距離の幅 Δd = λ/(u−½) − λ/(u+½))
        lam = K[1, 1] * 1.6
        u = lam / d
        step = lam / (u - 0.5) - lam / (u + 0.5)
        rows.append(abs(r["row_distance"] - d) - step)
    assert max(abs(e) for e in errs) < 1.0                     # セダンの後ろは曲面(≈ 0.7 m 奥)
    assert max(rows) < 1.0
    assert all(a > b for a, b in zip(ns, ns[1:]))               # 単調減少
    slope = np.polyfit(np.log(_DISTANCES), np.log(ns), 1)[0]
    assert -2.4 < slope < -1.6, slope
    none = CB.carla_scene_synthetic(0.0, width=160, height=90)
    assert CB.lead_truth_depth(none) == math.inf
    assert not CB.lead_from_depth(none["depth"], none["label"], CB.intrinsics_to_fullseye(none["K"]), 1.6)["found"]


def test_scene_check_is_fail_closed():
    sc = CB.carla_scene_synthetic(10.0, width=64, height=36)
    for k in ("rgb", "K", "meta", "lead_extent"):
        bad = dict(sc)
        del bad[k]
        with pytest.raises(ValueError):
            CB.carla_scene_check(bad)
    bad = dict(sc)
    bad["semantic"] = sc["semantic"].astype(np.int32)
    with pytest.raises(ValueError):
        CB.carla_scene_check(bad)
    bad = dict(sc)
    bad["lead_transform"] = np.array([1, 2, np.nan, 0, 0, 0.0])
    with pytest.raises(ValueError):
        CB.carla_scene_check(bad)
    bad = dict(sc)
    bad["meta"] = "{not json"
    with pytest.raises(ValueError):
        CB.carla_scene_check(bad)
    with pytest.raises(ValueError):
        CB.carla_scene_load("no/such/file.npz")
    with pytest.raises(ValueError):
        CB.carla_rotation_angles(CB.carla_rotation_matrix(0.0, 90.0, 0.0))
    with pytest.raises(ValueError):
        CB.carla_depth_encode(np.array([[-1.0]]))
    with pytest.raises(ValueError):
        CB.carla_intrinsics(180.0, 10, 10)


def _real_scenes():
    root = os.environ.get("FULLSEYE_CARLA_DATA", "")
    files = sorted(glob.glob(os.path.join(root, "lead_straight_d*.npz"))) if root else []
    return files


@pytest.mark.skipif(not _real_scenes(), reason="FULLSEYE_CARLA_DATA (CARLA の撮影記録) が無い")
def test_real_carla_depth_agrees_with_the_closed_form_truth():
    """CARLA の深度の中央値と、姿勢から出した後ろ面までの距離が 0.5 m 以内(観測 +0.10 m、箱の原点のずれ)。
    自前の世界で描き直した像も同じ門を通り、車の画素数は両方で 1/d² に乗る。"""
    files = _real_scenes()
    assert len(files) >= 5
    truths, n_c, n_f = [], [], []
    for f in files:
        sc = CB.carla_scene_load(f)
        r = CB.scene_pair_table(sc)
        assert r["carla"]["found"] and r["fullseye"]["found"], f
        assert abs(r["carla_error"]) < 0.5, (f, r["carla_error"])
        assert abs(r["fullseye_error"]) < 0.5, (f, r["fullseye_error"])
        assert abs(r["carla"]["row_distance"] - r["truth"]) < 1.0
        ratio = r["fullseye"]["n_pixels"] / r["carla"]["n_pixels"]
        assert 0.75 < ratio < 1.3, (f, ratio)
        truths.append(r["truth"])
        n_c.append(r["carla"]["n_pixels"])
        n_f.append(r["fullseye"]["n_pixels"])
    for ns in (n_c, n_f):
        slope = np.polyfit(np.log(truths), np.log(ns), 1)[0]
        assert -2.3 < slope < -1.7, slope
