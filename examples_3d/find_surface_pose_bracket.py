"""事例: L 字金具の 6-DoF 姿勢を点群から初期値なしで求める (find_surface_pose = PPF 投票 + ICP).

ピッキングの前段「既知の部品が場面のどこに、どの向きで置かれているか」。モデルは L 字の
金具(底板 3x2、立ち壁 2x1.5、円柱のボス 1 本 —— 回転対称が無いので姿勢が一意に決まる)の
表面点群。場面は同じ部品を既知の回転 R・並進 t で置き、**点の 3 割を間引き、順番を入れ替え、
0.01 の雑音を足した**点群(モデルの点がそのまま場面にあるのでは照合にならない)。

検証(GT): 求めた (R, t) と置いた (R, t) の回転誤差 [deg] と並進誤差。対照として、初期値を
単位行列にした ICP だけでは大きく外れることも測る(初期値の要らない照合が要る理由)。
"""
import math
import sys
from pathlib import Path

# リポジトリ root を最優先に(同名の example ファイルが top-level module を隠さないように)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

import fullseye as fs
from ppf import find_surface_pose  # fullseye: fs.ledger.find_surface_pose は pose の正典 (R, t) を返す
from registration import icp


def rot(axis, deg):
    a = np.asarray(axis, float)
    a = a / np.linalg.norm(a)
    t = math.radians(deg)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + math.sin(t) * K + (1 - math.cos(t)) * K @ K


def bracket(n_side=8):
    g = np.linspace(0.0, 1.0, n_side)
    base = np.array([[x * 3.0, y * 2.0, 0.0] for x in g for y in g])
    wall = np.array([[0.0, y * 2.0, z * 1.5] for y in g for z in g[1:]])
    th = np.linspace(0.0, 2 * np.pi, 16, endpoint=False)
    boss = np.array([[2.2 + 0.35 * math.cos(a), 0.6 + 0.35 * math.sin(a), z]
                     for a in th for z in (0.3, 0.6, 0.9)])
    return np.vstack([base, wall, boss])


def rot_err_deg(Ra, Rb):
    return math.degrees(math.acos(float(np.clip((np.trace(Ra.T @ Rb) - 1.0) / 2.0, -1.0, 1.0))))


def main():
    model = bracket()
    rng = np.random.default_rng(7)
    R_gt, t_gt = rot((1.0, 1.0, 0.3), 65.0), np.array([0.6, -0.4, 0.25])
    keep = rng.permutation(len(model))[: int(0.7 * len(model))]
    scene = model[keep] @ R_gt.T + t_gt + 0.01 * rng.standard_normal((len(keep), 3))

    out = find_surface_pose(model, scene)
    R, t = fs.ledger.find_surface_pose(model, scene)
    e_rot, e_t = rot_err_deg(R, R_gt), float(np.linalg.norm(t - t_gt))
    print("PPF + ICP: rotation error %.3f deg, translation error %.4f, rmse %.4f, inliers %.2f"
          % (e_rot, e_t, out["rmse"], out["inlier_fraction"]))
    R0, t0, _a, _r = icp(model, scene, init=(np.eye(3), np.zeros(3)), trim=0.2)
    print("ICP from identity (control): rotation error %.1f deg" % rot_err_deg(R0, R_gt))
    assert e_rot < 1.0 and e_t < 0.03, (e_rot, e_t)
    assert rot_err_deg(R0, R_gt) > 10.0 * max(e_rot, 0.1)
    print("PASS")


if __name__ == "__main__":
    main()
