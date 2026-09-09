---
op: principal_curvatures
dim: 3d
category: curvature
in: points
out: curvature
examples: [curvature_grasp, itokawa_curvature]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# principal_curvatures — 3D `curvature` op

- **データ種**: `points` → `curvature`
- **呼び出し**: `import fullseye as fs; fs.ledger.principal_curvatures(points, k=25, normals=None)` (実装を直接呼ぶなら `import curvature3d; curvature3d.principal_curvatures(points, k=25, normals=None)`、台帳から引くなら `ops3d.get("principal_curvatures")`)

## 使い方

各点の主曲率 (k1>=k2)。→ (k1 (N,), k2 (N,))。

normals(向き付き参照法線, (N,3))未指定時は凸側マグニチュード(開面の凹/凸符号は不定)。
向き付き法線を渡すと大域向きに整合し正しい符号(凹=負, 凸=正)。

手順(各点、Python ループ):
- ``cKDTree`` で自身を含む k+1 近傍を取る(k は N-1 に切り詰め)。近傍が 5 点未満なら ``k1 = k2 = 0`` を返す(5 係数の二次曲面が組めないため)。
- 近傍座標をクエリ点原点に平行移動し、``local.T @ local`` の最小固有ベクトルを法線とする(向きは ``normals`` があればそれに整合、無ければ近傍重心から離れる側)。
- 接線基底 (t1, t2) に射影し ``w = d·u + e·v + a·u² + b·uv + c·v²`` を最小二乗フィット → 第一/第二基本形式から shape operator の固有値を取り、凸を正にして ``k1 >= k2`` に並べる。

- 単位は 1/長さ(点群の単位に依存)。半径 R の球なら ``k1 = k2 = 1/R``、円柱は ``(1/R, 0)``、平面は 0。
- ``k`` は近傍点数(既定 25)。大きいほど平滑で曲率は低め、小さいほどノイズを拾う。
- ``normals`` は (N,3) で有限かつ非ゼロ行が必須(``ValueError``)。決定論的。
- 後段: ``mean_curvature`` / ``gaussian_curvature`` / ``shape_index``(いずれも内部で同じ計算を繰り返す)。shape index と曲がりの対が要るなら 2 本を ``(N,2)`` に並べて ``curvature_to_shape_index``。

## 背景知識ガイド(この op の手前にある物理・規約)

- [blas_threads_and_memory](../../math/guides/blas_threads_and_memory.md) — 行列分解が遅い理由の知識 — BLAS スレッド・キャッシュ・メモリ配置

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [curvature_grasp](../../../../examples_3d/curvature_grasp.py) — `py -3.11 examples_3d/curvature_grasp.py`
- [itokawa_curvature](../../../../examples_3d/itokawa_curvature.py) — `py -3.11 examples_3d/itokawa_curvature.py`

## 型が繋がる次の op(`curvature` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`curvature`)

[mean_curvature](mean_curvature.md) · [gaussian_curvature](gaussian_curvature.md) · [shape_index](shape_index.md) · [estimate_normals](estimate_normals.md)

---
*Provenance: curvature3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
