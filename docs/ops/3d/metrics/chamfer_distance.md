---
op: chamfer_distance
dim: 3d
category: metrics
in: points × points
out: measurement
examples: [itokawa_pose_canonical, itokawa_shape_match, mesh_lod_download, metrics_eval, poisson_surface_recon]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# chamfer_distance — 3D `metrics` op

- **データ種**: `points × points` → `measurement`
- **呼び出し**: `import fullseye as fs; fs.ledger.chamfer_distance(a, b, squared=False)` (実装を直接呼ぶなら `import metrics3d; metrics3d.chamfer_distance(a, b, squared=False)`、台帳から引くなら `ops3d.get("chamfer_distance")`)

## 使い方

対称 Chamfer 距離 = 0.5*(mean_a min_b + mean_b min_a)。→ scalar。小さいほど一致。

Raises ValueError: どちらかが空 or (N,3) でない場合(空の平均 = 無言 NaN)。

計算: ``scipy.spatial.cKDTree`` で ``a`` の各点から ``b`` への最近傍距離 ``d_ab``
(``(Na,)``)と ``b`` から ``a`` への ``d_ba`` を取り、``0.5 * (mean(d_ab) + mean(d_ba))``。
``squared=True`` なら各距離を 2 乗してから平均する(単位が距離^2 になる。
勾配ベースの最適化で使う形)。既定は生の距離(単位 = 座標の単位)。

入力: ``a``, ``b`` は ``(N, 3)`` / ``(M, 3)`` の点群(点数は違ってよい、対応は
不要)。float に変換する。座標系・スケールは両者で揃えておくこと(登録前の
2 雲を比べると単に姿勢の差を測ることになる)。

返り値: Python ``float``。同一点群なら 0。値域は ``[0, inf)`` で正規化はしない
(雲の大きさに比例するので、比較するときは bbox 対角などで割る)。

注意: 平均なので外れ値の影響は Hausdorff より小さいが、点密度の偏りには敏感
(密な側の平均が支配的)。密度を揃えるには ``pc_poisson_disk`` /
``voxel_grid_downsample`` を先に掛ける。閾値ベースの評価は ``fscore``、最悪値は
``hausdorff_distance``、対応既知なら ``rmse_correspondence``。

## 背景知識ガイド(この op の手前にある物理・規約)

- [blender_interop](../guides/blender_interop.md) — Blender との併用 — 形を作って fullseye で測る(軸・単位・正解データの罠)
- [measurement_uncertainty](../../math/guides/measurement_uncertainty.md) — 計測の不確かさと校正の知識 — 「測れている」を主張するために

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [itokawa_pose_canonical](../../../../examples_3d/itokawa_pose_canonical.py) — `py -3.11 examples_3d/itokawa_pose_canonical.py`
- [itokawa_shape_match](../../../../examples_3d/itokawa_shape_match.py) — `py -3.11 examples_3d/itokawa_shape_match.py`
- [mesh_lod_download](../../../../examples_3d/mesh_lod_download.py) — `py -3.11 examples_3d/mesh_lod_download.py`
- [metrics_eval](../../../../examples_3d/metrics_eval.py) — `py -3.11 examples_3d/metrics_eval.py`
- [poisson_surface_recon](../../../../examples_3d/poisson_surface_recon.py) — `py -3.11 examples_3d/poisson_surface_recon.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

[vol_gaussian_psf](../restoration/vol_gaussian_psf.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fresnel_reflectance](../optics/fresnel_reflectance.md) · [snell_angle](../optics/snell_angle.md)

## 同カテゴリ(`metrics`)

[hausdorff_distance](hausdorff_distance.md) · [m3c2_distance](m3c2_distance.md) · [fscore](fscore.md) · [rmse_correspondence](rmse_correspondence.md) · [normal_consistency](normal_consistency.md) · [voxel_iou](voxel_iou.md) · [pose_error](pose_error.md)

---
*Provenance: metrics3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
