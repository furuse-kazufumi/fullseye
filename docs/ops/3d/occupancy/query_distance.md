---
op: query_distance
dim: 3d
category: occupancy
in: sdf × points
out: signal
examples: [occupancy_esdf]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# query_distance — 3D `occupancy` op

- **データ種**: `sdf × points` → `signal`
- **呼び出し**: `import occupancy; occupancy.query_distance(esdf_grid, bounds, res, query_points, mode='trilinear')` (または `ops3d.get("query_distance")`)

## 使い方

任意 world 座標 (M,3) での ESDF 値 (M,) を返す(``mode``='trilinear' 補間 or 'nearest')。

``bounds``/``res`` は ESDF を作った格子と同じもの。world→連続ボクセル座標は
``c=(q-lo)/span*res-0.5``(voxel i の中心が c=i)。三線形補間はボクセル中心 8 近傍を
重み付け(格子外はエッジにクランプ=最近端の値で外挿)。planner がノード/経路上の任意点で
離隔を問い合わせる用途。返り値は ESDF と同じ world 単位。

Raises ValueError for res<=0, degenerate bounds, non-(M,3) query, or unknown mode.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [occupancy_esdf](../../../../examples_3d/occupancy_esdf.py) — `py -3.11 examples_3d/occupancy_esdf.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`occupancy`)

[occupancy_grid](occupancy_grid.md) · [esdf](esdf.md) · [inflate](inflate.md)

---
*Provenance: occupancy.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
