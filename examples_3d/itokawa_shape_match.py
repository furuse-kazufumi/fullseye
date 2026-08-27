# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""itokawa_shape_match — chamfer 距離による形状照合。

【この例が解く現実問題】
「この点群は同じ天体か、別物か」を数値で判定したい。chamfer 距離は 2 つの点群の
最近傍距離の平均で、形状の一致度を測る標準指標である。位置合わせ済みの同一形状なら
小さく、別形状なら大きくなる。小惑星の観測を照合したり、再構成結果を基準形状と比べる
ときの土台になる。ここでは (a) イトカワの回転コピーを ICP で位置合わせした自己照合と、
(b) 同じ外接サイズの球との照合を比べ、「同形状 << 別形状」を assert する。

対象データ: studio_assets/sample_3d/itokawa_points.npy(実測イトカワ点群, ~3000 点)。
使う op: metrics3d.chamfer_distance、match3d.icp_point2point_3d(位置合わせ)。

正規化: chamfer は長さの次元を持つので、外接対角で割ってスケール相対の指標にする。
"""
import sys
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import match3d    # icp_point2point_3d(回転コピーを基準へ位置合わせ)
import metrics3d  # chamfer_distance(形状一致度)

DATA = _REPO / "studio_assets" / "sample_3d" / "itokawa_points.npy"


def main():
    rng = np.random.default_rng(0)
    pts = np.load(DATA).astype(np.float64)
    pts = pts - pts.mean(axis=0)
    extent = pts.max(axis=0) - pts.min(axis=0)
    diag = float(np.linalg.norm(extent))

    # --- (a) 自己照合: 回転コピーを ICP で位置合わせしてから chamfer ---
    R_gt = Rotation.from_rotvec(np.array([0.3, 0.6, 0.74]) /
                                np.linalg.norm([0.3, 0.6, 0.74]) *
                                np.radians(25.0)).as_matrix()
    noise_sigma = 0.003 * diag
    copy_rot = pts @ R_gt.T + rng.normal(0.0, noise_sigma, pts.shape)
    R, t, info = match3d.icp_point2point_3d(copy_rot, pts, iters=80, init_R=R_gt)
    R = R.detach().cpu().numpy()
    t = t.detach().cpu().numpy()
    aligned = copy_rot @ R.T + t                    # 基準フレームへ整列
    d_same = metrics3d.chamfer_distance(aligned, pts)

    # --- (b) 別形状: 同じ外接サイズの球との chamfer ---
    n = len(pts)
    u = rng.normal(size=(n, 3))
    u /= np.linalg.norm(u, axis=1, keepdims=True)
    radius = 0.5 * float(np.mean(extent))           # 平均外接寸法の半分
    sphere = u * radius
    d_diff = metrics3d.chamfer_distance(pts, sphere)

    nd_same = d_same / diag                          # スケール相対(外接対角で正規化)
    nd_diff = d_diff / diag
    ratio = d_diff / d_same

    print("=== グラウンドトゥルース ===")
    print(f"外接寸法      : {extent[0]:.1f} x {extent[1]:.1f} x {extent[2]:.1f} m")
    print(f"外接対角      : {diag:.1f} m / ノイズσ {noise_sigma:.2f} m")
    print("\n=== chamfer 距離による照合 ===")
    print(f"(a) 同形状(回転コピーを ICP 整列): {d_same:.3f} m "
          f"(正規化 {nd_same:.4f} = ノイズ床相当)")
    print(f"(b) 別形状(同サイズの球)        : {d_diff:.3f} m "
          f"(正規化 {nd_diff:.4f})")
    print(f"比 (別形状 / 同形状)             : {ratio:.1f} 倍")

    # --- 検証: 同形状 << 別形状 ---
    assert d_same < d_diff, "同形状のほうが別形状より大きい(照合が破綻)"
    assert ratio > 5.0, f"同形状と別形状の差が不十分: 比 = {ratio:.1f} 倍"
    # 同形状の残差はノイズ床(数 m)程度に収まるべき
    assert nd_same < 0.02, f"同形状の正規化 chamfer が大きすぎる: {nd_same:.4f}"

    print("\nPASS: 位置合わせ済み同形状の chamfer は別形状(球)の 1/"
          f"{ratio:.0f} で、chamfer 距離が形状の同一/相違を正しく判定できる。")


if __name__ == "__main__":
    main()
