# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""`opscalib` 台帳 —— 登録の健全性と、**構造データ**による真値つき検証。

## なぜこの台帳が要るか(2026-09-16)

`calib` / `caltab` / `fit_transform` は 2026-08 から同梱されていて、
`tests/test_calib.py` と `tests/test_caltab.py` に 30 本超の試験もあった。
それでも利用者からは「無い」ものだった —— 実測で
`fullseye.<名前>` / `fullseye.ledger` / `ops.REGISTRY` / `docs/OP_INDEX.json` の
**すべてに 1 つも出ておらず**、`fs.op_find("caltab")` は 0 件を返していた。
外部の AI 2 体が独立に「カメラ校正の op は確認できなかった」と報告している。

ここでは「台帳に載った」だけでなく**公開経路から実際に引けて、呼べて、
真値に合う**ことまで見る(「登録済みを数える門」は未登録に盲目なので、
数える向きは台帳 → 公開経路 の順)。

## 乱数だけにしない

入力は**既知寸法の校正板**(閉形式で座標が決まる構造データ)を使う。
乱数だけの入力は対称性の破れを隠す —— 格子の行と列を取り違えても、
点がばらけていれば「それらしい」答えが出てしまう。
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import calib  # noqa: E402
import opscalib  # noqa: E402

K_TRUE = {"fx": 500.0, "fy": 500.0, "cx": 128.0, "cy": 128.0}


def _rotm(rx, ry, rz):
    cx, sx = np.cos(rx), np.sin(rx)
    cy, sy = np.cos(ry), np.sin(ry)
    cz, sz = np.cos(rz), np.sin(rz)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def _pose(rx, ry, rz, t):
    T = np.eye(4)
    T[:3, :3] = _rotm(rx, ry, rz)
    T[:3, 3] = t
    return T


# --------------------------------------------------------------------------- #
# 1. 台帳としての健全性                                                        #
# --------------------------------------------------------------------------- #
def test_every_registered_op_has_an_implementation():
    assert opscalib.missing() == [], opscalib.missing()
    assert len(opscalib.OPSCALIB) == 21, len(opscalib.OPSCALIB)
    assert len(opscalib.categories()) == 5


def test_every_op_declares_a_doc_and_known_sorts():
    """宣言した型語彙が**既存のもの**だけであること(新語を作らない判断の門)。

    0.2.1 は patch/minor の範囲に留める。ここが落ちたら、新しい sort を
    持ち込んだということなので、その必要性を先に記録すること。
    """
    allowed = {"points", "pose", "matrix", "table", "contour", "image2d"}
    bad = {}
    for name, meta in opscalib.OPSCALIB.items():
        assert meta["doc"], "%s に docstring 先頭行が無い" % name
        used = set(meta["in"]) | {meta["out"]}
        extra = used - allowed
        if extra:
            bad[name] = sorted(extra)
    assert not bad, "既存の型語彙に無い sort を使っている: %s" % bad


def test_the_ledger_is_reachable_from_the_public_facade():
    """★この族が存在する理由そのもの —— `fs.ledger` から 21 op 全部が引けること。"""
    import fullseye as fs

    missing = [n for n in opscalib.OPSCALIB if not hasattr(fs.ledger, n)]
    assert not missing, "fs.ledger から引けない台帳 op: %s" % missing


def test_the_search_layer_finds_the_family():
    """`fs.op_find("caltab")` が 0 件だったのが、この族を立てた直接のきっかけ。"""
    import fullseye as fs

    for stem in ("caltab", "calib", "camera_calibration"):
        hits = {h["op"] for h in fs.op_find(stem)}
        assert hits & set(opscalib.OPSCALIB), (
            "op_find(%r) が opscalib の op を 1 つも返さない" % stem)


# --------------------------------------------------------------------------- #
# 2. 構造データ(既知寸法の校正板)による真値つき検証                          #
# --------------------------------------------------------------------------- #
def test_known_checkerboard_round_trips_with_small_reprojection_rms():
    """既知寸法の板を投影 → 検出 → 姿勢復元し、再投影 RMS と実寸を測る。"""
    board = opscalib.call("create_caltab", 7, 7, 10.0)
    assert np.allclose(board["points"].mean(0), 0.0), "板は中心が原点のはず"

    truth = _pose(0.2, -0.1, 0.05, [4.0, -6.0, 600.0])
    sim = opscalib.call("sim_caltab", board, K_TRUE, truth, 256)
    found = opscalib.call("find_marks_and_pose", sim["image"], K_TRUE, board)

    assert found["n_marks"] == 49
    assert found["reproj_rms"] < 0.5, found["reproj_rms"]
    # 並進は mm で合っていること(板の実寸が効いているかを見る)
    assert np.abs(found["pose"][:3, 3] - truth[:3, 3]).max() < 3.0


def test_the_declared_plate_pitch_sets_the_recovered_scale():
    """★板の**申告した**格子間隔が、そのまま復元される実寸の尺度になる。

    ★この試験は最初こう書いていた ——「格子間隔を 2 倍にすると、復元される距離も
    2 倍になる」。**それは間違いだった**(実測 600.08 → 599.92、比 1.00)。
    間隔 2 倍の板を「2 倍だ」と申告して解けば、板は実際に大きく、見かけも大きく
    なるので、距離は **600 mm のまま正しく**復元される —— 実装は正しく、
    誤っていたのは試験の主張のほうだった。

    実際に効く結合はこちら: **同じ画像**を、間隔を 2 倍だと*申告*して解くと、
    復元される距離がちょうど 2 倍になる。板の実寸を測り違えれば、距離も焦点距離も
    その比のままずれる —— `poc_camera_calibration` が「印刷や貼り付けの伸びが
    0.3 % あれば焦点距離も 0.3 % ずれる」と書いているのはこの性質のこと。
    乱数点では「実寸」という概念が無いので、この結合は測れない。
    """
    truth = _pose(0.2, -0.1, 0.0, [0.0, 0.0, 600.0])
    board = opscalib.call("create_caltab", 7, 7, 10.0)
    sim = opscalib.call("sim_caltab", board, K_TRUE, truth, 256)

    honest = opscalib.call("find_marks_and_pose", sim["image"], K_TRUE, board)
    assert honest["pose"][2, 3] == pytest.approx(600.0, rel=0.01)

    # 同じ画像を「間隔 20 mm の板だった」と申告して解く
    wrong = opscalib.call("create_caltab", 7, 7, 20.0)
    misread = opscalib.call("find_marks_and_pose", sim["image"], K_TRUE, wrong)
    assert misread["pose"][2, 3] / honest["pose"][2, 3] == pytest.approx(2.0, rel=0.02)


def test_camera_calibration_recovers_known_intrinsics_through_the_ledger():
    """台帳の `call` 経由でも Zhang 法が真値の K を返すこと。"""
    r, c = np.mgrid[0:7, 0:7]
    xy = np.column_stack([c.ravel() * 10.0, r.ravel() * 10.0])
    xy = xy - xy.mean(0)                                   # (x, y) mm
    world = np.column_stack([xy, np.zeros(len(xy))])
    poses = [_pose(0.3, -0.2, 0.1, [5, -3, 400]),
             _pose(-0.25, 0.35, -0.4, [-10, 8, 450]),
             _pose(0.15, 0.15, 0.9, [0, 0, 380]),
             _pose(-0.4, -0.1, 0.3, [12, -4, 420])]
    views = [opscalib.call("project_3d_point", world, K_TRUE, P) for P in poses]

    K = opscalib.call("camera_calibration", xy, views)
    for key in ("fx", "fy", "cx", "cy"):
        assert abs(K[key] - K_TRUE[key]) < 1e-3, (key, K[key])
    assert max(K["reproj_rms"]) < 1e-6
    assert K["orientation_rank_ratio"] > 0.0


def test_image_points_map_back_to_millimetres():
    """画素 → ワールド平面の写像が、板の実寸をそのまま返すこと。"""
    board = opscalib.call("create_caltab", 7, 7, 10.0)
    truth = _pose(0.15, -0.1, 0.05, [0.0, 0.0, 600.0])
    xy = board["points"][:, ::-1]                          # (y,x) -> (x,y)
    world = np.column_stack([xy, np.zeros(len(xy))])
    px = opscalib.call("project_3d_point", world, K_TRUE, truth)
    back = opscalib.call("image_points_to_world_plane", K_TRUE, truth, px)
    assert np.abs(back - xy).max() < 1e-6


# --------------------------------------------------------------------------- #
# 3. 試験の無かった op に足したもの                                            #
# --------------------------------------------------------------------------- #
def test_hand_eye_calibration_recovers_a_known_transform():
    """★`hand_eye_calibration` には 2026-09-16 まで**試験が 1 本も無かった**。

    AX = XB を真値から組む: 既知の X を置き、`B_i = X⁻¹ A_i X` とすれば
    相対運動は `Ma X = X Mb` を満たす。回転軸を**わざと別々の向き**に散らす
    —— 全部同じ軸だと Procrustes の行列がランク落ちして、実装が正しくても
    解が定まらない(対称性の破れを隠さないため、構造を指定して作る)。
    """
    X = np.eye(4)
    X[:3, :3] = _rotm(0.3, -0.2, 0.15)
    X[:3, 3] = [12.0, -5.0, 30.0]

    A = [_pose(0.0, 0.0, 0.0, [0, 0, 0]),
         _pose(0.4, 0.0, 0.0, [10, 0, 5]),
         _pose(0.0, 0.5, 0.0, [0, 12, -4]),
         _pose(0.0, 0.0, 0.6, [-6, 3, 9]),
         _pose(0.25, -0.35, 0.2, [4, -8, 2])]
    Xi = np.linalg.inv(X)
    B = [Xi @ Ai @ X for Ai in A]

    got = opscalib.call("hand_eye_calibration", A, B)
    assert np.abs(got[:3, :3] - X[:3, :3]).max() < 1e-6, got[:3, :3]
    assert np.abs(got[:3, 3] - X[:3, 3]).max() < 1e-6, got[:3, 3]


def test_vector_angle_to_rigid_matches_a_known_rotation():
    """1 組の (点, 角度) から剛体変換を組む op の真値検証(構造で作る)。"""
    ang1, ang2 = 0.2, 0.9
    M = opscalib.call("vector_angle_to_rigid", 10.0, 20.0, ang1, 35.0, -4.0, ang2)
    d = ang2 - ang1
    assert np.allclose(M[:2, :2], [[np.cos(d), -np.sin(d)],
                                   [np.sin(d), np.cos(d)]])
    # 基準点は定義どおり写ること
    p = M @ np.array([10.0, 20.0, 1.0])
    assert np.allclose(p[:2], [35.0, -4.0])


def test_rigid_and_similarity_fits_are_exact_on_a_structured_grid():
    """★乱数ではなく**格子**で測る: 行と列を取り違える実装は格子でしか露見しない。"""
    r, c = np.mgrid[0:6, 0:6]
    src = np.column_stack([r.ravel() * 4.0, c.ravel() * 7.0])    # (row, col)、非等方ピッチ
    theta, scale = 0.37, 2.5
    R = np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]])
    t = np.array([13.0, -21.0])

    dst_rigid = src @ R.T + t
    M = opscalib.call("vector_to_rigid", src, dst_rigid)
    assert np.abs(M[:2, :2] - R).max() < 1e-9
    assert np.abs(M[:2, 2] - t).max() < 1e-9

    dst_sim = scale * (src @ R.T) + t
    M2 = opscalib.call("vector_to_similarity", src, dst_sim)
    assert np.abs(M2[:2, :2] - scale * R).max() < 1e-9
    assert np.abs(M2[:2, 2] - t).max() < 1e-9
