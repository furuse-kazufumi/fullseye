---
op: random_dropout
dim: 3d
category: augment
in: points
out: points
examples: [augment_pointcloud]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# random_dropout — 3D `augment` op

- **データ種**: `points` → `points`
- **呼び出し**: `import pcl_augment; pcl_augment.random_dropout(points, ratio: 'float', seed: 'int' = 0) -> 'Tuple[np.ndarray, np.ndarray]'` (または `ops3d.get("random_dropout")`)
- **台帳経由の戻り値**: `fullseye.ledger.random_dropout(...)` は**宣言 out 型 `points` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.random_dropout.raw(...)`、または `pcl_augment.random_dropout` を直接呼ぶ。

## 使い方

点の ``ratio`` 割合をランダム除去し ``(kept, kept_idx)`` を返す(欠損の模倣)。

残す点数は ``round((1-ratio)*N)``。``kept_idx`` は元配列への昇順インデックスで、
``kept == points[kept_idx]`` が厳密に成り立つ。オクルージョン/疎な視点による
点欠損を学習で再現する。``0 <= ratio <= 1`` を要求。

``ratio`` が [0,1] の外なら ``ValueError``。``ratio=1`` は空 ``(0,3)`` と空インデックス、
``ratio=0`` は全点(順序は元のまま)。残す点数は Python の ``round``(偶数丸め)で決まる
ので ``.5`` 端では偶数側に寄る。``seed`` で ``permutation`` が決まり決定論的。返り値は
``(kept float64 (M,3), kept_idx int64 (M,))``。除去は空間的に一様なので、局所的な
欠損(遮蔽)を模すには ``cutout`` を使う。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [augment_pointcloud](../../../../examples_3d/augment_pointcloud.py) — `py -3.11 examples_3d/augment_pointcloud.py`

## 型が繋がる次の op(`points` を入力に取れる)

[points_to_voxel](../transform/points_to_voxel.md) · [gaussians_to_voxel](../transform/gaussians_to_voxel.md) · [estimate_point_normals](../transform/estimate_point_normals.md) · [to_points](../transform/to_points.md) · [match_points_ncc](../match_localize/match_points_ncc.md) · [match_pca](../match_pose/match_pca.md) · [moment_axes](../match_pose/moment_axes.md) · [icp_point2point_3d](../refine/icp_point2point_3d.md)

## 同カテゴリ(`augment`)

[jitter](jitter.md) · [random_rotation](random_rotation.md) · [random_scale](random_scale.md) · [elastic_deform](elastic_deform.md) · [cutout](cutout.md)

---
*Provenance: pcl_augment.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
