---
op: scene_flow_lk
dim: 3d
category: motion
in: voxel × voxel
out: flow_dense
gpu: true
examples: [motion_scene]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# scene_flow_lk — 3D `motion` op

- **データ種**: `voxel × voxel` → `flow_dense`
- **呼び出し**: `import match3d; match3d.scene_flow_lk(vol0, vol1, device='cpu', win=3, levels=3, iters=3, reg=0.001)` (または `ops3d.get("scene_flow_lk")`)
- **GPU**: この op は GPU 経路あり(`device="cuda"`)

## 使い方

Lucas-Kanade scene flow(2D optical flow の 3D 版)。voxel ごとの運動場 d=(dz,dy,dx)。

テンプレ照合と違い **密な運動/変形**を推定する。明るさ一定 ∇I·d + I_t = 0 を窓内最小二乗で
per-voxel に解く(3x3 構造テンソル A=Σ∇I∇Iᵀ, b=-Σ∇I·I_t を窓和 conv3d で)。pyramid + warp の
coarse-to-fine で大変位に対応(各 level で I1 を現 flow で戻し残差を反復補正=Gauss-Newton)。
vol1(x) ≈ vol0(x - d)。返り値 flow (3,D,H,W)。並進・拡大(発散)・回転(渦)場を捉える。

実測: 一様並進 [1.5,-2,1] を中央領域平均で誤差 0.044 voxel、拡大場で外向き発散を正しく検出。
grad_scale=32 は sobel3d(deriv[-1,0,1]×smooth[1,2,1]²)の実測スケール。GPU 対応(全 conv3d)。

引数: ``vol0``, ``vol1`` は同形の 3-D(違えば ValueError。NaN/Inf や float32 桁あふれも
ValueError)。``win`` は窓の半幅(窓は一辺 ``2·win+1``)、``levels`` はピラミッド段数(各段
``avg_pool3d`` で 2 倍縮小。大変位ほど段数を増やす)、``iters`` は各段の warp 反復、``reg`` は
構造テンソル対角への正則化(平坦部の 0 除算回避。大きいほど平坦部の flow が 0 に寄る)。
1 反復の更新は各軸 ±2 voxel に clamp される。
返り値 ``(3, D, H, W)`` float32 numpy、``flow[0]``=dz, ``flow[1]``=dy, ``flow[2]``=dx
(voxel 単位)。``vol1(x) ≈ vol0(x − d)``、すなわち vol0 の構造が ``+d`` 動いて vol1 になる。
端は border 補間で埋まるので端 1〜2 voxel の値は信用しない。剛体運動の R,t が欲しいなら
点群にして ``icp_point2point_3d`` / ``fit_rigid`` へ。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [motion_scene](../../../../examples_3d/motion_scene.py) — `py -3.11 examples_3d/motion_scene.py`

## 型が繋がる次の op(`flow_dense` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`motion`)

—

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
