# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""「回転不変」と名乗っている記述子が、本当に回転不変かの門。

2026-09-06、点群位置合わせの PoC が「FPFH の成功率が初期回転で 100 / 92 / 8 /
25 / 0 % と落ちる」を測った。回転不変な記述子ならありえない。切り分けると
原因は数式ではなく**法線の符号**だった:

  * ``pointcloud.estimate_normals`` は PCA の第 3 固有ベクトルをそのまま返す。
    符号は任意で、点群を回すと **42.4 %** の点で別の符号が選ばれる
    (``|cos|`` は全点 1.0000 なので、法線の向きの線自体は正しい)。
  * FPFH は Darboux 枠を法線から作るので、符号が変われば記述子が変わる
    (実測 ``max|diff| = 7.3e+02``)。
  * PPF も特徴が法線どうしの角度なので同じ。鍵の一致率が 0/37/90/143 度で
    100 / 73.6 / 69.4 / 67.2 % に落ちていた。

**同じバグが 2 つの族にあった**ので、両方を向き付き法線
(``normals_orient.estimate_oriented_normals``、Hoppe の最小全域木伝播)に
切り替えた。切り替え後は FPFH が ``1e-12``、PPF の鍵が **すべて 100 %**。

PPF にはもう 1 つ独立の非不変性があった —— 既定 ``dist_step`` が**軸平行
境界箱の対角 / 20** で、同じ箱を回すと 1.2333 と 1.5735 で **28 % 動く**。
凸包の直径(回転不変、50000 点でも 7.1 ms)に置き換えた。

門は 3 本立てる: 法線の符号、記述子の不変性、量子化幅の不変性。
どれか 1 つだけだと、直したつもりで別の経路から戻ってくる。
"""
import numpy as np
import pytest

import normals_orient
import pointcloud
import ppf

ANGLES_DEG = (37.0, 90.0, 143.0)


def _rz(deg):
    t = np.deg2rad(deg)
    return np.array([[np.cos(t), -np.sin(t), 0.0],
                     [np.sin(t), np.cos(t), 0.0],
                     [0.0, 0.0, 1.0]])


def _cloud(n=800, seed=0):
    return np.random.default_rng(seed).random((n, 3)) @ np.diag([1.0, 0.62, 0.38])


# --------------------------------------------------------------------------- #
# 1. 法線の符号 —— 問題の根っこ
# --------------------------------------------------------------------------- #
def test_plain_pca_normals_flip_sign_under_rotation():
    """直っていないほうを固定する。ここが直ったら上の説明を書き直すこと。"""
    P = _cloud()
    R = _rz(90.0)
    n1 = pointcloud.estimate_normals(P, k=20)
    n2 = pointcloud.estimate_normals(P @ R.T, k=20)
    dot = (n1 @ R.T * n2).sum(1)
    assert np.abs(dot).min() > 0.999, "法線の向きの線そのものがずれている(別の問題)"
    assert (dot < 0).mean() > 0.2, "符号の反転が消えた —— 記述子側の注記を更新せよ"


def test_oriented_normals_are_rotation_equivariant():
    P = _cloud()
    for deg in ANGLES_DEG:
        R = _rz(deg)
        n1 = normals_orient.estimate_oriented_normals(P, k=20)
        n2 = normals_orient.estimate_oriented_normals(P @ R.T, k=20)
        dot = (n1 @ R.T * n2).sum(1)
        assert (dot < 0).mean() == 0.0, (deg, (dot < 0).mean())


# --------------------------------------------------------------------------- #
# 2. 記述子の不変性
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("deg", ANGLES_DEG)
def test_fpfh_default_path_is_rotation_invariant(deg):
    P = _cloud()
    d = np.max(np.abs(pointcloud.fpfh(P) - pointcloud.fpfh(P @ _rz(deg).T)))
    assert d < 1e-8, f"FPFH が回転で {d:.3e} 動いた(既定の法線が向き付きか確認)"


def test_fpfh_with_unoriented_normals_is_not_invariant():
    """自分で法線を渡すなら向き付けは呼び出し側の責任、を固定する。

    ここが通らなくなったら「渡された法線も勝手に向き付ける」実装に変わった
    ということなので、docstring の約束を書き直すこと。
    """
    P = _cloud()
    R = _rz(90.0)
    a = pointcloud.fpfh(P, pointcloud.estimate_normals(P, k=16))
    b = pointcloud.fpfh(P @ R.T, pointcloud.estimate_normals(P @ R.T, k=16))
    assert np.max(np.abs(a - b)) > 1.0


# --------------------------------------------------------------------------- #
# 3. 量子化幅の不変性(PPF)
# --------------------------------------------------------------------------- #
def test_ppf_hash_keys_survive_rotation():
    P = _cloud(n=400)
    base = set(ppf.ppf_model(P)["table"])
    assert base
    for deg in ANGLES_DEG:
        keys = set(ppf.ppf_model(P @ _rz(deg).T)["table"])
        share = len(base & keys) / len(base)
        assert share == 1.0, (deg, share)


def test_invariant_diameter_beats_the_axis_aligned_box():
    P = _cloud()
    aabb, inv = [], []
    for deg in (0.0,) + ANGLES_DEG:
        Q = P @ _rz(deg).T
        aabb.append(float(np.linalg.norm(Q.max(0) - Q.min(0))))
        inv.append(ppf._invariant_diameter(Q))
    assert max(aabb) / min(aabb) > 1.2, "軸平行対角が回転で動かない —— 前提が変わった"
    assert max(inv) - min(inv) < 1e-9, inv


def test_invariant_diameter_falls_back_without_a_hull():
    """同一直線上の点でも落ちず、**回転不変のまま**返す(退化時の逃げ道)。"""
    line = np.linspace(0.0, 1.0, 20)[:, None] * np.array([[1.0, 2.0, 0.5]])
    d0 = ppf._invariant_diameter(line)
    d1 = ppf._invariant_diameter(line @ _rz(57.0).T)
    assert d0 > 0.0 and abs(d0 - d1) < 1e-9
