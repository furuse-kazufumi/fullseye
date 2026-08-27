# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""事例: 回転式 LiDAR の距離画像(range image)で 3D 点群を往復させる.

やりたいこと(かみくだき):
  回転式 LiDAR(Velodyne/Ouster など)はセンサを中心に水平 360° 回りながら、
  各方向までの距離を測る。その 1 スイープを 1 枚の画像に畳んだものが
  「球面距離画像」= 行が仰角(上下)、列が方位角(ぐるり一周)、画素値が距離。
  この画像化が下流(CNN・占有格子・地面除去)を楽にする一方、往復で 3D に
  戻せなければ「画像にした瞬間に形が壊れた」ことになる。そこを確かめる。

方法:
  センサを囲む**既知の球殻**(半径が分かっている点群、方位は全周 360°)を作り、
  project_spherical で距離画像にし、unproject_spherical で 3D 点群へ戻す往復を行う。
  戻した点が元の球の上に(1 voxel 以内で)乗っていれば、画像化は形を保っている。

検証(GT):
  真値は「元の球の点群そのもの」。往復後の点群と元点群の双方向・最近傍距離
  (対称ハウスドルフ)を測り、有効画素の再構成誤差が 1 voxel 未満なら成功。
  なぜ 0 にはならないか(honest): unproject はセルの**中心角**へ戻すため、
  位置誤差はおよそ「range × 半セル角」。分解能を上げれば voxel 未満に収まる。

beat-the-null(零点):
  球面投影せず、素朴に**平面正射影**(高さ z を捨てて xy 平面へ落とす)して
  z=0 で戻す往復を零点とする。深さ(高さ)情報が消えるので点は球から大きく外れ、
  往復誤差は voxel の何十倍にもなる。実手法がこの零点を桁で上回ることを assert する。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from spherical_proj import project_spherical, unproject_spherical  # noqa: E402


def sphere_shell_band(radius, n, el_band_deg, seed=0):
    """センサを囲む半径 radius の球殻から点をサンプル(方位は全周 360°)。

    仰角は el_band_deg=(lo, hi)[度] の帯に限定する。この帯を v_fov の内側に
    取っておけば、FOV 外 drop が起きず「戻ってこない点」を GT 検証から排除でき、
    往復が純粋に「角度量子化のみ」で評価できる(honest な条件設定)。
    全点の range はちょうど radius なので、真値は「半径 radius の球面」。
    """
    rng = np.random.default_rng(seed)
    az = rng.uniform(-np.pi, np.pi, size=n)                 # 全周 360°
    lo, hi = np.radians(el_band_deg[0]), np.radians(el_band_deg[1])
    el = rng.uniform(lo, hi, size=n)                        # v_fov 内の仰角帯
    ce = np.cos(el)
    x = radius * ce * np.cos(az)
    y = radius * ce * np.sin(az)
    z = radius * np.sin(el)
    return np.stack([x, y, z], axis=1)


def max_nearest(a, b):
    """a の各点から b の最近傍までの距離の最大値(片方向ハウスドルフ)。"""
    d = np.sqrt(((a[:, None, :] - b[None, :, :]) ** 2).sum(axis=2))
    return float(d.min(axis=1).max())


def symmetric_hausdorff(a, b):
    """双方向の最近傍距離の最大(対称ハウスドルフ)。「形の一致」を判別的に測る。"""
    return max(max_nearest(a, b), max_nearest(b, a))


def main():
    radius = 5.0
    h_res, v_res = 1024, 64
    v_fov = (-25.0, 15.0)                 # モジュール既定と同じ仰角帯[度]
    # v_fov の内側に収めた帯(FOV drop を避け、往復を角度量子化のみで評価)
    el_band_deg = (-20.0, 10.0)

    # --- 1) 既知の合成データ: センサを囲む半径 5.0 の球殻(全周 360°) ---
    pts = sphere_shell_band(radius, n=1000, el_band_deg=el_band_deg, seed=0)

    # 角度量子化の理論上限 ≒ range × 半セル対角角。voxel はこれを余裕で上回る値に置く。
    half_az = np.pi / h_res                                  # 方位の半セル角[rad]
    half_el = np.radians((v_fov[1] - v_fov[0]) / v_res) / 2.0  # 仰角の半セル角[rad]
    cell_bound = radius * float(np.hypot(half_az, half_el))  # 半セル対角 × range
    voxel = 0.1                                              # 判定に使う 1 voxel[m]

    # --- 2) 実手法の往復: 点群 → 球面距離画像 → 点群(2 つの op を連鎖) ---
    range_img = project_spherical(pts, h_res=h_res, v_res=v_res, v_fov=v_fov)
    rec = unproject_spherical(range_img, v_fov=v_fov)
    occupied = int(np.count_nonzero(range_img > 0.0))
    method_err = symmetric_hausdorff(pts, rec)

    # --- 3) beat-the-null: 平面正射影(高さ z を捨てて xy へ)→ z=0 で戻す往復 ---
    rec_null = pts.copy()
    rec_null[:, 2] = 0.0
    null_err = symmetric_hausdorff(pts, rec_null)

    print(f"入力点数                    : {pts.shape[0]}")
    print(f"距離画像サイズ (v_res,h_res): ({v_res}, {h_res})")
    print(f"有効画素(占有セル)数       : {occupied}")
    print(f"往復後の点数                : {rec.shape[0]}")
    print(f"半セル角による理論誤差上限  : {cell_bound:.4f} m")
    print(f"1 voxel(判定閾値)          : {voxel:.4f} m")
    print(f"実手法の往復誤差(球面)     : {method_err:.4f} m")
    print(f"零点の往復誤差(平面正射影) : {null_err:.4f} m")

    # GT: 球面投影の往復は元の球へ 1 voxel 未満で戻る(=画像化しても形が保たれる)。
    assert method_err < voxel, \
        f"球面往復の誤差が voxel を超過: {method_err:.4f} m >= {voxel:.4f} m"
    # 実測誤差が理論上限の近傍に収まっていること(挙動の裏取り、詐称防止)。
    assert method_err <= cell_bound * 1.5, \
        f"往復誤差が理論上限から乖離: {method_err:.4f} m vs 上限 {cell_bound:.4f} m"
    # beat-the-null: 平面正射影は深さを失い往復で大きく崩れる(voxel の何十倍)。
    assert null_err > 10.0 * voxel, \
        f"零点が崩れていない(設定が甘い): {null_err:.4f} m <= {10.0 * voxel:.4f} m"
    # 実手法が零点を桁で上回る(球面投影が本質的に効いている証拠)。
    assert method_err < null_err / 10.0, \
        f"実手法が零点を桁で上回れていない: {method_err:.4f} m vs 零点 {null_err:.4f} m"

    ratio = null_err / method_err
    print(f"PASS: 球面往復 {method_err:.4f} m < voxel {voxel:.4f} m、"
          f"平面正射影(零点)は {null_err:.4f} m で崩壊、実手法が零点を {ratio:.0f} 倍上回る")


if __name__ == "__main__":
    main()
