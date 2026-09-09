---
op: cutout
dim: 3d
category: augment
in: points
out: points
examples: [sensor_seg]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# cutout — 3D `augment` op

- **データ種**: `points` → `points`
- **呼び出し**: `import fullseye as fs; fs.ledger.cutout(points, extent: 'Union[float, np.ndarray]', seed: 'int' = 0) -> 'Tuple[np.ndarray, np.ndarray]'` (実装を直接呼ぶなら `import pcl_augment; pcl_augment.cutout(points, extent: 'Union[float, np.ndarray]', seed: 'int' = 0) -> 'Tuple[np.ndarray, np.ndarray]'`、台帳から引くなら `ops3d.get("cutout")`)
- **台帳経由の戻り値**: `fullseye.ledger.cutout(...)` は**宣言 out 型 `points` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.cutout.raw(...)`、または `pcl_augment.cutout` を直接呼ぶ。

## 使い方

空間的な軸平行ボックス領域を除去し ``(kept, kept_idx)`` を返す(局所欠損の模倣)。

既存の点を 1 つ一様サンプルして中心とし、辺長 ``extent``(スカラ=立方体, または
``(3,)``=各軸辺長)のボックス内の点をすべて除去する。中心点自身が必ず入るため
最低 1 点は除去される。除去点は必ず辺長 ``extent`` のボックスに収まる(空間的に
局所的 = ランダム散布とは判別可能)。``kept == points[kept_idx]``、``extent > 0``。

``extent`` に正でない値や ``(3,)`` 以外の形を渡すと ``ValueError``。空入力は空と空
インデックスを返す。中心は ``rng.integers(n)`` で選ぶ点なので、``seed`` が同じでも点の
並びが変わると別の場所が抜ける。ボックス判定は ``|P - center| <= extent/2`` の閉区間。
除去点数は密度次第で、``extent`` を雲の大きさより大きくすると全点が消える。返り値は
``(kept float64 (M,3), kept_idx int64 (M,))``、順序は元のまま。一様な欠損は
``random_dropout``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [sensor_seg](../../../../examples_3d/sensor_seg.py) — `py -3.11 examples_3d/sensor_seg.py`

## 型が繋がる次の op(`points` を入力に取れる)

[points_to_voxel](../transform/points_to_voxel.md) · [gaussians_to_voxel](../transform/gaussians_to_voxel.md) · [estimate_point_normals](../transform/estimate_point_normals.md) · [to_points](../transform/to_points.md) · [match_points_ncc](../match_localize/match_points_ncc.md) · [match_pca](../match_pose/match_pca.md) · [moment_axes](../match_pose/moment_axes.md) · [icp_point2point_3d](../refine/icp_point2point_3d.md)

## 同カテゴリ(`augment`)

[jitter](jitter.md) · [random_rotation](random_rotation.md) · [random_scale](random_scale.md) · [random_dropout](random_dropout.md) · [elastic_deform](elastic_deform.md)

---
*Provenance: pcl_augment.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
