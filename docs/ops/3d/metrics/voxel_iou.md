---
op: voxel_iou
dim: 3d
category: metrics
in: voxel × voxel
out: measurement
examples: [metrics_eval]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# voxel_iou — 3D `metrics` op

- **データ種**: `voxel × voxel` → `measurement`
- **呼び出し**: `import fullseye as fs; fs.ledger.voxel_iou(vol_a, vol_b, iso=0.5)` (実装を直接呼ぶなら `import metrics3d; metrics3d.voxel_iou(vol_a, vol_b, iso=0.5)`、台帳から引くなら `ops3d.get("voxel_iou")`)

## 使い方

voxel 占有の IoU(intersection over union)。→ [0,1]。体積一致度。

両 volume は同一 shape が必須。異形状は numpy broadcasting で見かけ上一致し
誤った IoU(例: (10,1,10) vs (1,10,10) → 1.0)を静かに返すので、fail-closed で
shape 不一致は ValueError で拒否する。

計算: 両 volume を ``>= iso`` で二値化し(``iso`` 既定 0.5、等号を含む)、
``|A∩B| / |A∪B|``。和集合が空(両方とも占有ゼロ)なら ``1.0`` を返す
(「どちらも空」は一致とみなす。エラーにしない)。

引数: ``vol_a``, ``vol_b`` は同じ shape の配列(3-D に限らず、次元数は検査しない。
bool / 0-1 / 密度 grid のいずれでもよい)。``iso`` は占有とみなす閾値で、
``fuse_to_voxel`` や ``points_to_voxel`` の密度 grid(値は点数)に使うなら
``iso=1`` 以上を明示する。NaN は ``>=`` で False(非占有)になる。

返り値: Python ``float``、``[0, 1]``。1 = 完全一致、0 = 重なりなし。

注意: 同じ格子(``bounds`` と ``size``)に載っていないと比較にならない —
``fuse_to_voxel`` / ``points_to_voxel`` には同じ ``bounds`` を渡す。薄い殻同士は
1 voxel ずれるだけで IoU が大きく落ちるので、表面の評価には
``chamfer_distance`` / ``fscore`` の方が向く。体積が小さい対象は Dice
(``voxel_dice``、同モジュールの関数)の方が慣習として使われる。

## 背景知識ガイド(この op の手前にある物理・規約)

- [blender_interop](../guides/blender_interop.md) — Blender との併用 — 形を作って fullseye で測る(軸・単位・正解データの罠)
- [measurement_uncertainty](../../math/guides/measurement_uncertainty.md) — 計測の不確かさと校正の知識 — 「測れている」を主張するために

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [metrics_eval](../../../../examples_3d/metrics_eval.py) — `py -3.11 examples_3d/metrics_eval.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

[vol_gaussian_psf](../restoration/vol_gaussian_psf.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fresnel_reflectance](../optics/fresnel_reflectance.md) · [snell_angle](../optics/snell_angle.md)

## 同カテゴリ(`metrics`)

[chamfer_distance](chamfer_distance.md) · [hausdorff_distance](hausdorff_distance.md) · [m3c2_distance](m3c2_distance.md) · [fscore](fscore.md) · [rmse_correspondence](rmse_correspondence.md) · [normal_consistency](normal_consistency.md) · [pose_error](pose_error.md)

---
*Provenance: metrics3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
