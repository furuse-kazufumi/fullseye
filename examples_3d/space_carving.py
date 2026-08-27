# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""事例: 多視点シルエットから物体の体積を彫り出す (space carving / visual hull).

やりたいこと(素朴な言葉で): 深度センサも学習モデルも無く、既知の校正済みカメラを
何台か置いて撮った「物体の影(前景マスク=シルエット)」だけがある。この影の情報だけ
から、物体がどんな 3-D の塊なのかを voxel(3-D のマス目)の占有として復元したい。
掴む対象の当たり判定や occupancy grid の初期化に使える「形が先、テクスチャは後」の下地。

方法: 各カメラのシルエットは 3-D 空間で視錐(見えている範囲の錐)を張る。物体は必ず
すべての視錐の内側にあるので、視錐の共通部分(AND)を取れば物体を必ず内包する体積が
得られる(Laurentini 1994, visual hull)。ここでは既知の球を複数の既知視点から
``synthesize_silhouette`` でシルエット化し、``carve`` で bounding box の voxel を削って
``visual_hull`` を得る、という連鎖で 1 視点 → 多視点の収束を観察する。

正解 (GT): 復元対象は半径既知の球なので、同じ voxel 格子上で「中心が球内にある voxel」を
真の占有として厳密に計算できる。これと復元結果を比べて次の 2 つを確かめる:
  (1) recall: 真の voxel を取りこぼしていないか(= visual hull が真形状を内包=削りすぎない)。
  (2) IoU:    真形状との一致度(過剰削りが無く、視点を増やすほど締まっていくか)。

beat-the-null(なぜ多視点が要るのか): 何も情報が無いときの当てずっぽう = bounding box
全体を占有とみなす null 基準の IoU は球体積÷箱体積で決まる小さな値。1 視点だけの
visual hull は視線方向へ伸びた「柱状」の過大推定でしかなく IoU は低い。視点を足すほど
視錐の共通部分が球へ収束し IoU が単調に改善して null と 1 視点を明確に上回る — これを
実測して主張する。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

# examples_3d/ の 1 つ上(リポジトリ直下 = visualhull.py の場所)を import path へ
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import visualhull as vh  # noqa: E402


def intrinsics(f: float, size) -> np.ndarray:
    """焦点距離 f・画像中心を主点とするピンホール内部パラメータ K (3x3)。"""
    h, w = int(size[0]), int(size[1])
    cx, cy = (w - 1) / 2.0, (h - 1) / 2.0
    return np.array([[f, 0.0, cx], [0.0, f, cy], [0.0, 0.0, 1.0]])


def sphere_surface_points(radius: float, n: int) -> np.ndarray:
    """フィボナッチ格子で球面上に n 点をほぼ一様サンプル(シルエット生成の材料)。"""
    i = np.arange(n) + 0.5
    phi = np.arccos(1.0 - 2.0 * i / n)            # 極角 (0..pi)
    theta = np.pi * (1.0 + 5.0 ** 0.5) * i        # 黄金角で方位を回す
    x = np.sin(phi) * np.cos(theta)
    y = np.sin(phi) * np.sin(theta)
    z = np.cos(phi)
    return radius * np.stack([x, y, z], axis=1)


def voxel_centers(bounds, res: int) -> np.ndarray:
    """carve と同一規約(セル中心 +0.5, indexing='ij')で voxel 中心 (res^3, 3) を作る。"""
    (xmin, xmax), (ymin, ymax), (zmin, zmax) = bounds
    xs = xmin + (np.arange(res) + 0.5) * (xmax - xmin) / res
    ys = ymin + (np.arange(res) + 0.5) * (ymax - ymin) / res
    zs = zmin + (np.arange(res) + 0.5) * (zmax - zmin) / res
    X, Y, Z = np.meshgrid(xs, ys, zs, indexing="ij")
    return np.stack([X.ravel(), Y.ravel(), Z.ravel()], axis=1)


def true_sphere_occupancy(bounds, res: int, radius: float) -> np.ndarray:
    """中心が原点からの距離 <= radius に入る voxel を真の占有 (res,res,res) bool とする。"""
    centers = voxel_centers(bounds, res)
    inside = np.linalg.norm(centers, axis=1) <= radius
    return inside.reshape(res, res, res)


def iou(a: np.ndarray, b: np.ndarray) -> float:
    """2 つの占有ボリュームの Intersection-over-Union。"""
    inter = np.count_nonzero(a & b)
    union = np.count_nonzero(a | b)
    return inter / union if union else 1.0


def recall(truth: np.ndarray, hull: np.ndarray) -> float:
    """真の voxel のうち hull に含まれた割合(1.0 = 取りこぼし無し = 削りすぎ無し)。"""
    denom = np.count_nonzero(truth)
    return np.count_nonzero(truth & hull) / denom if denom else 1.0


def main() -> None:
    rng_note = "球は凸なので十分な視点数で visual hull ≈ 真の球へ収束する"

    # --- 1) 既知形状(半径既知の球)と、それを囲む彫刻領域・voxel 格子 ---
    radius = 1.0
    bounds = ((-1.5, 1.5), (-1.5, 1.5), (-1.5, 1.5))
    res = 40                                       # 40^3 = 64000 voxel
    size = (128, 128)                              # 画像 (H, W)
    focal = 200.0
    K = intrinsics(focal, size)

    truth = true_sphere_occupancy(bounds, res, radius)
    surf = sphere_surface_points(radius, n=6000)   # シルエット生成用の球面点

    # --- 2) 既知の複数視点を球の周りに配置(方位×仰角 + 真上・真下)---
    dist = 5.0
    eyes = []
    for elev_deg in (30.0, -30.0):
        for azim_deg in (0.0, 90.0, 180.0, 270.0):
            el, az = np.radians(elev_deg), np.radians(azim_deg)
            eyes.append(dist * np.array([np.cos(el) * np.cos(az),
                                         np.cos(el) * np.sin(az),
                                         np.sin(el)]))
    eyes.append(dist * np.array([0.0, 0.0, 1.0]))   # 真上
    eyes.append(dist * np.array([0.0, 0.0, -1.0]))  # 真下
    eyes = np.array(eyes)                            # (10, 3)

    # --- 3) 各視点で GT シルエットを合成(synthesize_silhouette)---
    sils, Ks, Rs, ts = [], [], [], []
    for eye in eyes:
        R, t = vh.look_at(eye, target=(0.0, 0.0, 0.0))
        sil = vh.synthesize_silhouette(surf, K, R, t, size)  # fill+dilate 既定
        sils.append(sil)
        Ks.append(K)
        Rs.append(R)
        ts.append(t)

    # --- 4) 視点数を 1 → 全数まで増やしながら carve し、IoU/recall/体積比を測る ---
    n_true = int(np.count_nonzero(truth))
    n_box = res ** 3
    iou_null = n_true / n_box                        # null 基準: 何も彫らない箱全体

    ious, recalls, vol_ratios = [], [], []
    for k in range(1, len(eyes) + 1):
        hull = vh.carve(sils[:k], Ks[:k], Rs[:k], ts[:k], bounds, res)
        ious.append(iou(truth, hull))
        recalls.append(recall(truth, hull))
        vol_ratios.append(np.count_nonzero(hull) / n_true)

    hull_full = vh.visual_hull(sils, Ks, Rs, ts, bounds, res)  # 別名でも同結果

    # --- 5) GT 検証の表示 ---
    print(f"形状: 半径 {radius} の球 / 格子 {res}^3 / 画像 {size[0]}x{size[1]} / 視点 {len(eyes)}")
    print(f"補足: {rng_note}")
    print(f"真の占有 voxel 数           : {n_true} / 箱 {n_box}")
    print(f"null(箱全体)の IoU        : {iou_null:.3f}   (何も彫らない当てずっぽう)")
    print("視点数  IoU     recall  体積比(hull/真)")
    for k, (io, rc, vr) in enumerate(zip(ious, recalls, vol_ratios), start=1):
        print(f"  {k:2d}   {io:.3f}   {rc:.3f}   {vr:.2f}")

    iou_1 = ious[0]
    iou_full = ious[-1]
    recall_min = min(recalls)
    vol_ratio_full = vol_ratios[-1]

    # (a) 削りすぎ無し: 全視点で真の voxel をほぼ取りこぼさない(hull は真形状の上位集合)
    assert recall_min >= 0.99, f"recall が低い(削りすぎ)= {recall_min:.3f}"

    # (b) 過剰削りが無く体積比が妥当: hull は真形状以上だが膨れすぎない
    assert 1.0 <= vol_ratio_full < 2.0, f"体積比が非現実的: {vol_ratio_full:.2f}"

    # (c) 視点数で IoU が単調改善(carve は共通部分=単調に締まるので理論上も非減少)
    for a, b in zip(ious, ious[1:]):
        assert b >= a - 1e-9, f"IoU が単調でない: {a:.3f} -> {b:.3f}"

    # (d) beat-the-null: 全視点は null と 1 視点(柱状の過大推定)を明確に上回る
    assert iou_1 < 0.5, f"1 視点で既に締まりすぎ(柱状の過大推定のはず): {iou_1:.3f}"
    assert iou_full > 3.0 * iou_null, f"全視点が null を上回らない: {iou_full:.3f} vs {iou_null:.3f}"
    assert iou_full > 2.0 * iou_1, f"多視点が 1 視点を明確に上回らない: {iou_full:.3f} vs {iou_1:.3f}"

    print(
        f"PASS: recall {recall_min:.3f}(削りすぎ無し)、体積比 {vol_ratio_full:.2f}、"
        f"IoU が {iou_1:.3f}(1 視点)→ {iou_full:.3f}(全 {len(eyes)} 視点)へ単調収束し、"
        f"null {iou_null:.3f} を明確に上回った"
    )


if __name__ == "__main__":
    main()
