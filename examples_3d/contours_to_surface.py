# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""contours_to_surface — 複数断層の2D輪郭を積層して3D曲面(メッシュ)に変換する。

実世界の問題:
    CT/MRI や連続断面のように、各スライスで物体の **2D 輪郭** が得られている。これらを
    3D 空間で積み重ね、ひとつの **曲面メッシュ** に再構成したい(可視化・3Dプリント・
    体積計測・FEM)。これは「輪郭(2D)→ 塗り領域 → voxel 積層(3D)→ メッシュ」という
    **表現の変換の連鎖**そのもの。

原理と連鎖:
    各スライスの閉輪郭を skimage で塗って占有スライスにし、z 方向へ積んで占有 voxel を作る。
    recon3d.marching_cubes(Lorensen & Cline 1987)で等値面を三角形メッシュとして抜き出す。

グラウンドトゥルース(beat-the-null):
    既知の球(半径 R)の断面輪郭(高さ z で半径 sqrt(R^2 - z^2))を使う。
    1. 復元メッシュの頂点は球面近傍に乗る(|中心距離 - R| がスライス分解能程度に小さい)。
    2. 積層 voxel の体積が球の体積 4/3·pi·R^3 に一致する。
    beat-the-null: 断面が一定(円柱)と仮定すると体積は pi·R^2·2R = 2·pi·R^3 と 1.5 倍に
    過大評価される。断面が z で変わる輪郭を積層して初めて球の体積・形が復元できる。
"""
from __future__ import annotations

import os
import sys

import numpy as np
from skimage.draw import polygon as sk_polygon

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

import recon3d  # marching_cubes(vol, level) -> (verts, faces, normals, values)


def slice_contour(cx, cy, radius, n=72):
    """(cx,cy) 中心・半径 radius の閉輪郭(スライス断面)を (rows, cols) で返す。"""
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    return cy + radius * np.sin(t), cx + radius * np.cos(t)   # rows, cols


def main() -> int:
    N = 56
    R = 20.0
    cz = cy = cx = N / 2.0

    # --- 1) 既知の球の断面輪郭を各スライスで生成し、塗って積層(輪郭→領域→voxel)---
    vol = np.zeros((N, N, N), dtype=np.float64)
    n_slices = 0
    for z in range(N):
        rr2 = R * R - (z - cz) ** 2
        if rr2 <= 1.0:
            continue
        rad = np.sqrt(rr2)
        rows, cols = slice_contour(cx, cy, rad)
        fr, fc = sk_polygon(rows, cols, shape=(N, N))   # 閉輪郭を塗る
        vol[z, fr, fc] = 1.0
        n_slices += 1
    filled_voxels = int(vol.sum())
    print(f"[GT] 積層スライス数 = {n_slices}、塗り voxel 数 = {filled_voxels}")

    # --- 2) 積層 voxel から曲面メッシュを抽出(voxel→mesh)---
    from scipy import ndimage
    occ = ndimage.gaussian_filter(vol, sigma=0.7)
    verts, faces, _normals, _vals = recon3d.marching_cubes(occ, 0.5)
    print(f"[GT] 抽出メッシュ: 頂点 {verts.shape[0]}、三角形 {faces.shape[0]}")

    # --- 3) GT-1: メッシュ頂点が球面に乗る ---
    d = np.linalg.norm(verts - np.array([cz, cy, cx]), axis=1)   # verts は (z,y,x)
    surf_err = float(np.mean(np.abs(d - R)))
    print(f"[GT] 頂点の |中心距離 - R| 平均 = {surf_err:.3f} voxel(R={R:.0f})")
    assert surf_err < 1.5, f"復元曲面が球面から離れすぎ: {surf_err:.3f}"

    # --- 4) GT-2/beat-null: 積層体積は球、円柱仮定は 1.5 倍過大 ---
    true_sphere = 4.0 / 3.0 * np.pi * R ** 3
    cylinder = np.pi * R ** 2 * (2 * R)                          # 断面一定と誤仮定した体積
    vol_err = abs(filled_voxels - true_sphere) / true_sphere
    print(f"[GT] 積層体積 {filled_voxels} / 球 {true_sphere:.0f}(誤差 {vol_err*100:.1f}%) "
          f"/ 円柱仮定 {cylinder:.0f}(=球の {cylinder/true_sphere:.2f}倍)")
    assert vol_err < 0.10, f"積層体積が球と合わない: 誤差 {vol_err*100:.1f}%"
    assert abs(filled_voxels - cylinder) / cylinder > 0.25, "円柱仮定と区別できていない"

    print("\nPASS: 各断層の2D輪郭を塗って積層し marching cubes で曲面メッシュ化 "
          "— 頂点は球面に乗り(誤差 %.2f voxel)、体積は球に一致(円柱仮定は1.5倍過大)。"
          "輪郭(2D)→領域→voxel(3D)→メッシュの表現変換が通った。" % surf_err)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
