# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""事例: 接触した原子球が融合した分子ボリュームから原子の個数を数える (touching-atom segmentation).

実世界の問題:
    クライオ電顕・分子表面・粉体・封入物などの 3-D ラスタでは、独立した「玉」どうしが
    **接触・僅かに重なって** 1 つの連結塊に融合する。ここでは分子を **ボール&スティック**
    模型 ── シクロヘキサン(C6)の椅子型配座 ── として、6 個の炭素原子球を六角環状に
    並べ(隣接原子は結合長 < 2r で重なる/交互に z 上下=椅子型)、その和集合を
    ``sdf_ops.sphere_sdf`` でボクセル化する(occupancy = SDF<0)。隣接原子がすべて重なって
    環がつながるので、和集合は **1 個の連結成分** になる。素朴な連結成分ラベリング
    (``volops.vol_label``)はこの融合塊を 1 個としか数えられない ── 原子数 6 を復元できない。

原理:
    前景の距離変換(``volops.vol_distance_transform``、背景まで最短距離=物体の芯)を取ると、
    凸な各原子球の中心付近が極大になり、隣接原子どうしの接触面(=くびれ)は距離の谷になる。
    その距離極大を(``volops.vol_local_maxima`` の非最大抑制で)検出し、近接した極大ボクセルは
    ``volops.vol_label`` で 1 原子 1 マーカに束ね、反転距離場 −dist 上でマーカ制御分水嶺
    (``volops.vol_watershed``、skimage backend)を流す。くびれ(距離の谷)が自然な切断面に
    なり、融合塊が原子ごとの basin に割れて 6 個に分離できる。座標は sdf_ops の格子規約
    (nx,ny,nz)。

検証(GT): 復元した原子数 == K(=6)。
    真の炭素中心 6 点は解析的に既知(六角環×椅子型 z)。分水嶺ラベルについて
      1) ラベル数(=原子数)== 6
      2) 各ラベルの重心が、いずれかの真の原子中心へ一意対応で近い(< 3 voxel)
      3) 全ラベル体積の和 == 前景ボクセル数(過不足なく被覆)
    を確認する。距離変換で検出した極大が最初から丁度 6 クラスタであることも確かめる。

beat-the-null(下駄を履かせない基準):
    素朴な連結成分ラベリング ``vol_label(occ)`` は、接触して環状につながった 6 原子を
    **1 個** に融合する(count=1 < K=6)。しかもその単一連結成分の重心は環の中心=
    背景の穴に落ち、どの原子中心からも遠い。分水嶺は count==6 かつ各重心を真の炭素中心へ
    < 3 voxel で当てて、**個数で判別的に上回る**(6 vs 1)。null が K を復元してしまえば
    この例は無意味になるが、環の連結性ゆえ null は必ず 1 に潰れる。
"""
from __future__ import annotations

import numpy as np

import sdf_ops
import volops

# ── 決定性: 乱数は使わないが規約に従い全 RNG を seed ──────────────────────────
np.random.seed(0)
_RNG = np.random.RandomState(0)

K = 6                       # 炭素原子数(真値)
R_ATOM = 0.62              # 原子球半径 [world]
R_RING = 1.00             # 六角環の外接半径 [world](=隣接炭素の xy 間隔)
Z_PUCKER = 0.15           # 椅子型配座の上下振幅 [world](交互に ±)

# 六角環×椅子型配座で 6 個の炭素中心(world x,y,z)を作る。
#   隣接中心間隔 = sqrt(R_RING^2 + (2 Z_PUCKER)^2) < 2 R_ATOM なので必ず重なって連結する。
_ANG = np.deg2rad(np.arange(K) * (360.0 / K))
ATOM_CENTERS = np.stack([
    R_RING * np.cos(_ANG),
    R_RING * np.sin(_ANG),
    Z_PUCKER * np.where(np.arange(K) % 2 == 0, 1.0, -1.0),
], axis=1)                                        # (K, 3)

# ボクセル格子: 分子全体(半径 R_RING+R_ATOM、z は ±(Z_PUCKER+R_ATOM))を余裕をもって覆う。
_M = R_RING + R_ATOM + 0.13
_MZ = Z_PUCKER + R_ATOM + 0.13
BOUNDS = ((-_M, _M), (-_M, _M), (-_MZ, _MZ))
RES = (150, 150, 70)                             # voxel ~0.025 world


def build_molecule_occupancy():
    """6 炭素球の和集合(min-SDF)をボクセル化し (occ, coords) を返す。"""
    coords, _ = sdf_ops.grid_coords(BOUNDS, RES)              # (nx,ny,nz,3)
    sdf = np.full(coords.shape[:-1], np.inf, dtype=np.float64)
    for c in ATOM_CENTERS:
        sdf = np.minimum(sdf, sdf_ops.sphere_sdf(coords, c, R_ATOM))  # 和集合 = min
    occ = sdf < 0.0
    return occ, coords


def world_to_index(center):
    """world 座標を grid_coords 規約のボクセル添字(連続値, ix,iy,iz)へ写す。

    grid_coords: voxel i の中心 = lo + (i+0.5)/res * span  →  i = (world-lo)/span*res - 0.5。
    """
    b = np.asarray(BOUNDS, float)
    lo, hi = b[:, 0], b[:, 1]
    res = np.asarray(RES, float)
    return (np.asarray(center, float) - lo) / (hi - lo) * res - 0.5


def region_centroids(labels):
    """ラベル配列 → {label: 重心(ix,iy,iz)} と体積 dict(背景 0 除く)。"""
    cents, vols = {}, {}
    for L in range(1, int(labels.max()) + 1):
        m = labels == L
        v = int(m.sum())
        if v == 0:
            continue
        cents[L] = np.argwhere(m).mean(axis=0)
        vols[L] = v
    return cents, vols


def match_one_to_one(measured_centroids, true_centers):
    """測定重心を真の原子中心へ最近傍で一意対応させ、最大対応距離を返す。"""
    if len(measured_centroids) != len(true_centers):
        return float("inf")
    used = [False] * len(true_centers)
    max_d = 0.0
    for mc in measured_centroids:
        best_j, best_d = -1, np.inf
        for j, g in enumerate(true_centers):
            if used[j]:
                continue
            d = float(np.linalg.norm(np.asarray(mc) - np.asarray(g)))
            if d < best_d:
                best_d, best_j = d, j
        if best_j < 0:
            return float("inf")
        used[best_j] = True
        max_d = max(max_d, best_d)
    return max_d


def main() -> int:
    occ, _coords = build_molecule_occupancy()
    true_idx = np.stack([world_to_index(c) for c in ATOM_CENTERS])   # (K,3) 添字空間の真中心

    # --- 入力の健全性(退化入力で偽の成功を出さない) ---
    if occ.ndim != 3 or not occ.any():
        raise ValueError(f"3-D 前景ボリュームが必要: ndim={occ.ndim}, any={occ.any()}")
    fg = int(occ.sum())
    print(f"[GT] 分子=シクロヘキサン C6 椅子型, grid={occ.shape}, 前景={fg} voxel, 原子数(true)={K}")
    for i, c in enumerate(ATOM_CENTERS):
        ti = true_idx[i]
        print(f"[GT] C{i}: world=({c[0]:+.2f},{c[1]:+.2f},{c[2]:+.2f})  idx=("
              f"{ti[0]:.1f},{ti[1]:.1f},{ti[2]:.1f})")

    # --- beat-the-null 基準線: 素朴な連結成分ラベリング ---
    null_labels, null_n = volops.vol_label(occ, connectivity=26)
    null_centroid = np.argwhere(null_labels > 0).mean(axis=0)
    null_min_dist = min(float(np.linalg.norm(null_centroid - ti)) for ti in true_idx)
    print(f"[null] vol_label -> count={null_n} (融合), 単一重心(ix,iy,iz)=("
          f"{null_centroid[0]:.1f},{null_centroid[1]:.1f},{null_centroid[2]:.1f}), "
          f"どの原子中心からも最短 {null_min_dist:.1f} voxel")

    # --- 距離変換 → 距離極大の検出 → 1 原子 1 マーカへ束ねる ---
    dist = volops.vol_distance_transform(occ)                        # 背景までの最短距離 [voxel]
    dmax = float(dist.max())
    peaks = volops.vol_local_maxima(dist, min_distance=15, threshold=0.70 * dmax)  # (N,3)
    peak_vol = np.zeros(occ.shape, dtype=bool)
    peak_vol[tuple(peaks.T)] = True
    markers, n_markers = volops.vol_label(peak_vol, connectivity=26)  # 近接極大を 1 クラスタに
    print(f"[seed] dist.max={dmax:.1f} voxel, 極大ボクセル={len(peaks)} 個 -> "
          f"マーカ(=原子候補)クラスタ={n_markers} 個")

    # --- マーカ制御分水嶺: 反転距離場 −dist を前景に限定して流す ---
    labels = volops.vol_watershed(-dist, markers, mask=occ)
    cents, vols = region_centroids(labels)
    count = len(cents)
    total = sum(vols.values())
    max_cen_err = match_one_to_one(list(cents.values()), list(true_idx))
    print(f"[watershed] 分離ラベル数(=原子数)={count}, 体積和={total} (前景 {fg}), "
          f"最大重心誤差={max_cen_err:.2f} voxel")

    # ═══ GT 検証(tight tolerance / beat-the-null)═══
    # null(連結成分)は環がつながって 1 個に融合しているはず(この例が意味を持つ前提)
    assert null_n == 1, f"null(連結成分)が 1 でない: {null_n}(シーン設計を見直す)"
    assert null_n < K, f"null が既に K を数えてしまい判別的でない: {null_n}"
    # 距離極大は最初から丁度 K クラスタに落ちる(=各原子の芯を 1 個ずつ拾う)
    assert n_markers == K, f"距離極大クラスタが原子数と不一致: {n_markers} vs {K}"
    # (1) 復元原子数 == K
    assert count == K, f"分水嶺の復元原子数が K と不一致: {count} vs {K}"
    # (2) 各ラベル重心が真の炭素中心へ一意対応で近い
    assert max_cen_err < 3.0, f"重心が真の原子中心から離れすぎ: {max_cen_err:.2f} voxel"
    # (3) 前景を過不足なく被覆
    assert total == fg, f"ラベルが前景を被覆していない: 体積和 {total} != 前景 {fg}"
    # beat-the-null: 個数で判別的に上回る(6 vs 1)。null 重心は原子中心から十分離れている
    assert count > null_n, f"分水嶺が null の個数を上回れていない: {count} vs {null_n}"
    assert null_min_dist > 3.0, f"null 単一重心が原子中心に近すぎ判別にならない: {null_min_dist:.1f}"

    print(f"PASS: 接触6原子(C6椅子型)の融合塊を距離変換+マーカ分水嶺で {count} 個へ分離"
          f"(復元原子数=K=6)。各重心を真の炭素中心へ最大 {max_cen_err:.2f} voxel で復元、"
          f"体積和 {total}=前景。素朴な連結成分ラベリング(null)は環の連結ゆえ count=1 に融合し"
          f"その単一重心はどの原子からも {null_min_dist:.1f} voxel 離れる — 個数 6 vs 1 で判別的に上回った")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
