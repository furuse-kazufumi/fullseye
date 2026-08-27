"""CTボリュームから骨表面メッシュを抽出する例(marching cubes)。

実世界の問題:
    CT のボクセル(密度場)から、骨の「表面」を三角形メッシュとして取り出す。
    3D プリント用 STL の生成、手術シミュレーション、有限要素解析メッシュ、
    可視化(サーフェスレンダリング)など、ボリューム→サーフェス変換の要になる操作。

原理:
    marching cubes (Lorensen & Cline 1987) は、スカラー場の等値面
    (iso-surface, ここでは骨/非骨の境界密度)を、各ボクセル格子セルごとに
    三角形で近似して連結する古典アルゴリズム。抽出される頂点は「占有ボクセルと
    非占有ボクセルの境界(セルの辺上)」に置かれるので、必ず骨表面のすぐ近くに乗る。

    fullseye では recon3d.marching_cubes(vol, level) を使う。これは
    skimage.measure.marching_cubes をそのまま再エクスポートしたもので、返り値は
    4 タプル (verts, faces, normals, values):
        verts   : (nv, 3) 各頂点のボクセル座標 (z, y, x) — 格子インデックス空間
        faces   : (nf, 3) 各三角形を成す頂点インデックス
        normals : (nv, 3) 頂点法線
        values  : (nv,)   各頂点での元スカラー値(≈ level)
    抽出前に軽くガウス平滑し、階段状のボクセル境界をなめらかな占有場にしておく。
"""
from __future__ import annotations

import os
import sys

import numpy as np
from scipy import ndimage

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import recon3d  # fullseye: marching_cubes(vol, level) -> (verts, faces, normals, values)


def load_volume() -> np.ndarray:
    path = os.path.join(_REPO_ROOT, "studio_assets", "sample_3d", "skeleton_ct.npy")
    return np.load(path).astype(np.float64)


def main() -> int:
    vol = load_volume()
    print(f"[GT] volume shape = {vol.shape}, "
          f"density range [{vol.min():.3f}, {vol.max():.3f}]")

    # 骨/非骨の境界を等値面レベルに。占有場を軽く平滑してから抽出。
    level = float(vol.mean() + vol.std())
    occupancy = ndimage.gaussian_filter(vol, sigma=0.8)
    print(f"[GT] iso-surface level = mean+std = {level:.3f}")

    # marching cubes で表面メッシュ抽出(返り値は 4 タプル)。
    verts, faces, normals, values = recon3d.marching_cubes(occupancy, level)
    n_verts, n_faces = verts.shape[0], faces.shape[0]
    print(f"[GT] extracted mesh: vertices = {n_verts}, faces = {n_faces}")
    print(f"[GT] verts array shape = {verts.shape}, faces array shape = {faces.shape}")

    # 抽出頂点が占有ボクセルの近傍に乗っているかを距離変換で定量評価。
    # (背景の距離変換 = 各ボクセルから最も近い占有ボクセルまでの距離)
    bone_mask = vol > level
    dist_to_bone = ndimage.distance_transform_edt(~bone_mask)
    vi = np.rint(verts).astype(int)
    vi[:, 0] = np.clip(vi[:, 0], 0, vol.shape[0] - 1)
    vi[:, 1] = np.clip(vi[:, 1], 0, vol.shape[1] - 1)
    vi[:, 2] = np.clip(vi[:, 2], 0, vol.shape[2] - 1)
    vert_dist = dist_to_bone[vi[:, 0], vi[:, 1], vi[:, 2]]
    mean_dist = float(vert_dist.mean())
    frac_near = float((vert_dist <= 1.5).mean())
    print(f"[GT] 頂点→最寄り占有ボクセル距離: mean = {mean_dist:.3f} voxel, "
          f"<=1.5voxel の割合 = {frac_near * 100:.1f}%")

    # --- 自己検証 ---
    assert n_verts > 0, "頂点が 1 つも抽出されていない"
    assert n_faces > 0, "面が 1 つも抽出されていない"
    assert faces.max() < n_verts, "面が範囲外の頂点を参照している"
    # 表面頂点は骨のすぐ近く(境界セルの辺上)にあるはず。
    assert mean_dist < 1.5, f"抽出表面が骨から離れすぎ: 平均距離 {mean_dist:.3f}"
    assert frac_near > 0.95, \
        f"占有ボクセル近傍にある頂点が少なすぎる: {frac_near * 100:.1f}%"

    print(f"PASS: 骨表面メッシュ({n_verts} 頂点 / {n_faces} 面)を抽出し、"
          f"全頂点が占有ボクセルの近傍に乗ることを確認")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
