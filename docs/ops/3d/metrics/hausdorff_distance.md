---
op: hausdorff_distance
dim: 3d
category: metrics
in: points × points
out: measurement
examples: [mesh_lod_download, pointcloud_downsampling, poisson_surface_recon]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# hausdorff_distance — 3D `metrics` op

- **データ種**: `points × points` → `measurement`
- **呼び出し**: `import fullseye as fs; fs.ledger.hausdorff_distance(a, b)` (実装を直接呼ぶなら `import metrics3d; metrics3d.hausdorff_distance(a, b)`、台帳から引くなら `ops3d.get("hausdorff_distance")`)

## 使い方

対称 Hausdorff 距離 = max(max_a min_b, max_b min_a)。→ scalar。最悪ケースの乖離。

計算: ``cKDTree`` で ``a`` の各点から ``b`` への最近傍距離と、``b`` から ``a`` への
最近傍距離を取り、両方向の **最大値** のうち大きい方を返す。「一方の雲のどの点も、
相手の雲からこの距離以内にある」を保証する最小の半径。単位は座標の単位。

入力: ``a``, ``b`` は ``(N, 3)`` / ``(M, 3)`` の点群(点数は異なってよい、対応不要)。
**この op は入口検査を持たない**(``_require_cloud`` を通らない): 空の点群を渡すと
``max()`` が numpy の ``ValueError``("zero-size array")で落ち、``(N, 2)`` など
3 列でない入力は cKDTree の次元不一致で ``ValueError`` になる — いずれも
メッセージはこの op のものではない。呼ぶ前に空でないことを確かめること。

返り値: Python ``float``、``[0, inf)``。同一点群なら 0。正規化はしない。

注意: 1 点の外れ値で値が決まる(平均ではなく最大)。ノイズを含むスキャンの
評価には ``chamfer_distance`` か ``fscore``(閾値 ``tau`` 以内の割合)の方が
安定で、Hausdorff は「最悪でもこの精度」を主張したいとき(公差検証、
LOD の ``max_error`` と同じ性格)に使う。

## 背景知識ガイド(この op の手前にある物理・規約)

- [blender_interop](../guides/blender_interop.md) — Blender との併用 — 形を作って fullseye で測る(軸・単位・正解データの罠)
- [measurement_uncertainty](../../math/guides/measurement_uncertainty.md) — 計測の不確かさと校正の知識 — 「測れている」を主張するために

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [mesh_lod_download](../../../../examples_3d/mesh_lod_download.py) — `py -3.11 examples_3d/mesh_lod_download.py`
- [pointcloud_downsampling](../../../../examples_3d/pointcloud_downsampling.py) — `py -3.11 examples_3d/pointcloud_downsampling.py`
- [poisson_surface_recon](../../../../examples_3d/poisson_surface_recon.py) — `py -3.11 examples_3d/poisson_surface_recon.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

[vol_gaussian_psf](../restoration/vol_gaussian_psf.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fresnel_reflectance](../optics/fresnel_reflectance.md) · [snell_angle](../optics/snell_angle.md)

## 同カテゴリ(`metrics`)

[chamfer_distance](chamfer_distance.md) · [m3c2_distance](m3c2_distance.md) · [fscore](fscore.md) · [rmse_correspondence](rmse_correspondence.md) · [normal_consistency](normal_consistency.md) · [voxel_iou](voxel_iou.md) · [pose_error](pose_error.md)

---
*Provenance: metrics3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
