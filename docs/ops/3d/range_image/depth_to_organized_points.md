---
op: depth_to_organized_points
dim: 3d
category: range_image
in: depth
out: pointmap
examples: [range_image]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# depth_to_organized_points — 3D `range_image` op

- **データ種**: `depth` → `pointmap`
- **呼び出し**: `import fullseye as fs; fs.ledger.depth_to_organized_points(depth, fx=None, fy=None, cx=None, cy=None)` (実装を直接呼ぶなら `import range_image; range_image.depth_to_organized_points(depth, fx=None, fy=None, cx=None, cy=None)`、台帳から引くなら `ops3d.get("depth_to_organized_points")`)

## 使い方

organized 深度画像 → 格子整列 3D 点 (H,W,3)。

fx,fy 指定で透視逆投影 P=((u-cx)/fx*d, (v-cy)/fy*d, d)。未指定は正射(P=(x,y,depth), 格子間隔1)。

``u`` は列番号 (0..W-1)、``v`` は行番号 (0..H-1)。``fx``・``fy`` は画素単位の焦点距離、
``cx``・``cy`` は主点で、省略時は画像中心 ``((W-1)/2, (H-1)/2)``。``fx`` と ``fy`` の
どちらか一方でも None なら正射モードになり、``cx``・``cy`` は無視される。正射モードでは
x, y が画素座標そのままなので、深度の単位(mm 等)と x, y の単位(画素)が混在する点に
注意。透視モードでは 3 成分とも深度と同じ単位になる。深度 0 や NaN はそのまま伝播する
(0 の画素は x=y=0 の原点に集まる)ため、無効画素の除外は呼び出し側で行う。返り値は
float64 の ``(H,W,3)``、第 3 軸は (x, y, z) で x は右、y は下、z は奥行き(画像座標系)。
入力検証は無く、2-D 以外は ``d.shape`` の展開で失敗する。``normals_from_depth`` は
この関数の出力を内部で使う。

## 背景知識ガイド(この op の手前にある物理・規約)

- [blender_interop](../guides/blender_interop.md) — Blender との併用 — 形を作って fullseye で測る(軸・単位・正解データの罠)
- [depth_sensors](../guides/depth_sensors.md) — 深度センサの知識 — 測距原理・実機の値・欠測の出方

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [range_image](../../../../examples_3d/range_image.py) — `py -3.11 examples_3d/range_image.py`

## 型が繋がる次の op(`pointmap` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [bump_normals_fbm](../terrain/bump_normals_fbm.md)

## 同カテゴリ(`range_image`)

[normals_from_depth](normals_from_depth.md) · [occlusion_edges](occlusion_edges.md) · [bearing_angle_image](bearing_angle_image.md)

---
*Provenance: range_image.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
