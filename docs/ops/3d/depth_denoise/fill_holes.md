---
op: fill_holes
dim: 3d
category: depth_denoise
in: depth
out: depth
examples: [depth_denoise]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# fill_holes — 3D `depth_denoise` op

- **データ種**: `depth` → `depth`
- **呼び出し**: `import fullseye as fs; fs.ledger.fill_holes(depth: 'np.ndarray', max_radius: 'float', *, invalid: 'float | None' = 0.0, max_iter: 'int | None' = None, rel_tol: 'float' = 1e-06) -> 'np.ndarray'` (実装を直接呼ぶなら `import depth_bilateral; depth_bilateral.fill_holes(depth: 'np.ndarray', max_radius: 'float', *, invalid: 'float | None' = 0.0, max_iter: 'int | None' = None, rel_tol: 'float' = 1e-06) -> 'np.ndarray'`、台帳から引くなら `ops3d.get("fill_holes")`)

## 使い方

無効画素(穴)を近傍有効画素から調和(ラプラス)緩和で補間。→ float64 (H,W)。

各穴画素の最寄り有効画素までの距離が max_radius 以下なら補間対象、超える深い穴は補間せず NaN で残す
(fail-closed)。補間は 4 近傍平均の反復(Dirichlet 境界=元の有効画素)で、線形場(平面)は離散
調和関数の不動点なので反復収束とともに平面を厳密復元する。初期値は最寄り有効画素値(EDT)。

max_iter 既定は穴サイズに応じて自動設定、rel_tol は深度スケール相対の収束判定。全画素無効の入力は
補間の足場が無いため ValueError(fail-closed)。

## 背景知識ガイド(この op の手前にある物理・規約)

- [blender_interop](../guides/blender_interop.md) — Blender との併用 — 形を作って fullseye で測る(軸・単位・正解データの罠)
- [depth_sensors](../guides/depth_sensors.md) — 深度センサの知識 — 測距原理・実機の値・欠測の出方

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [depth_denoise](../../../../examples_3d/depth_denoise.py) — `py -3.11 examples_3d/depth_denoise.py`

## 型が繋がる次の op(`depth` を入力に取れる)

[depth_to_points](../transform/depth_to_points.md) · [tsdf_from_depth](../transform/tsdf_from_depth.md) · [to_points](../transform/to_points.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [depth_to_organized_points](../range_image/depth_to_organized_points.md) · [normals_from_depth](../range_image/normals_from_depth.md) · [occlusion_edges](../range_image/occlusion_edges.md) · [bearing_angle_image](../range_image/bearing_angle_image.md)

## 同カテゴリ(`depth_denoise`)

[bilateral_filter_depth](bilateral_filter_depth.md) · [joint_bilateral](joint_bilateral.md)

---
*Provenance: depth_bilateral.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
