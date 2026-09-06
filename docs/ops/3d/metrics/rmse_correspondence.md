---
op: rmse_correspondence
dim: 3d
category: metrics
in: points × points
out: measurement
examples: [metrics_eval]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# rmse_correspondence — 3D `metrics` op

- **データ種**: `points × points` → `measurement`
- **呼び出し**: `import metrics3d; metrics3d.rmse_correspondence(a, b)` (または `ops3d.get("rmse_correspondence")`)

## 使い方

対応既知(同 index)の RMSE = sqrt(mean |a_i - b_i|^2)。→ scalar。登録残差の評価。

計算: ``a``, ``b`` を float 配列にし、行ごとのユークリッド距離の 2 乗
``sum((a - b)**2, axis=1)`` を平均して平方根を取る。**最近傍探索はしない** —
``a[i]`` と ``b[i]`` が同じ点の対応であることを呼び手が保証する(登録で変換した
``src @ R.T + t`` と、対応する ``dst`` の点列、合成データの GT 対応など)。

引数と検証: ``a.shape != b.shape`` なら ``ValueError``。それ以外の検査はない:
空の ``(0, 3)`` 同士は ``mean`` が空で NaN(警告付き)を返し、``(N, 3)`` 以外でも
``axis=1`` で足せる形なら値を返す。3 列の点群を渡すこと。

返り値: Python ``float``、単位は座標の単位、``[0, inf)``。同一なら 0。

注意: 対応がずれている(index が並び替わった)雲に使うと、姿勢が正しくても
大きな値が出る。対応不明なら ``chamfer_distance`` / ``fscore``、姿勢そのものを
GT と比べるなら ``pose_error``。

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

[chamfer_distance](chamfer_distance.md) · [hausdorff_distance](hausdorff_distance.md) · [fscore](fscore.md) · [normal_consistency](normal_consistency.md) · [voxel_iou](voxel_iou.md) · [pose_error](pose_error.md)

---
*Provenance: metrics3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
