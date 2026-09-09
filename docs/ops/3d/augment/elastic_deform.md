---
op: elastic_deform
dim: 3d
category: augment
in: points
out: points
examples: [sensor_seg]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# elastic_deform — 3D `augment` op

- **データ種**: `points` → `points`
- **呼び出し**: `import fullseye as fs; fs.ledger.elastic_deform(points, sigma: 'float', alpha: 'float', seed: 'int' = 0) -> 'np.ndarray'` (実装を直接呼ぶなら `import pcl_augment; pcl_augment.elastic_deform(points, sigma: 'float', alpha: 'float', seed: 'int' = 0) -> 'np.ndarray'`、台帳から引くなら `ops3d.get("elastic_deform")`)

## 使い方

滑らかな乱数変位場で弾性変形(相関距離 ``sigma``, RMS 振幅 ``alpha``)。

各点に独立ガウス乱数ベクトルを置き、空間ガウス重み ``exp(-d²/2σ²)`` で平滑化した
変位場を生成する(近接点は coherent に動く)。場は RMS を 1 に正規化してから
``alpha`` 倍するので、変位の RMS ノルムはちょうど ``alpha`` になる(``σ→∞`` で場は
定数=剛体並進, ``σ→0`` で各点独立)。非剛体な物体変形/柔軟物の学習に。

注意(honest): 近傍探索は ``cKDTree.query_pairs(r=3σ)``。``σ`` が雲の直径に近いほど
ペア数は O(N²) に近づくため、大規模雲では ``σ`` を局所スケールに保つこと。

``sigma < 0`` は ``ValueError``。``sigma == 0`` または 1 点だけの雲では平滑化せず各点
独立の変位になる。``alpha`` は検証しない(0 なら無変位、負なら場が反転するだけ)。
``seed`` で決定論的。返り値は float64 ``(N,3)`` で点数・順序は保たれる(変形前後の
対応が添字で分かるので、非剛体位置合わせの誤差を直接測れる)。空入力は空を返す。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [sensor_seg](../../../../examples_3d/sensor_seg.py) — `py -3.11 examples_3d/sensor_seg.py`

## 型が繋がる次の op(`points` を入力に取れる)

[points_to_voxel](../transform/points_to_voxel.md) · [gaussians_to_voxel](../transform/gaussians_to_voxel.md) · [estimate_point_normals](../transform/estimate_point_normals.md) · [to_points](../transform/to_points.md) · [match_points_ncc](../match_localize/match_points_ncc.md) · [match_pca](../match_pose/match_pca.md) · [moment_axes](../match_pose/moment_axes.md) · [icp_point2point_3d](../refine/icp_point2point_3d.md)

## 同カテゴリ(`augment`)

[jitter](jitter.md) · [random_rotation](random_rotation.md) · [random_scale](random_scale.md) · [random_dropout](random_dropout.md) · [cutout](cutout.md)

---
*Provenance: pcl_augment.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
