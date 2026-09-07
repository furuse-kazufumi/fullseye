---
op: fscore
dim: 3d
category: metrics
in: points × points
out: measurement
examples: [metrics_eval]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# fscore — 3D `metrics` op

- **データ種**: `points × points` → `measurement`
- **呼び出し**: `import metrics3d; metrics3d.fscore(a, b, tau)` (または `ops3d.get("fscore")`)
- **台帳経由の戻り値**: `fullseye.ledger.fscore(...)` は**宣言 out 型 `measurement` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.fscore.raw(...)`、または `metrics3d.fscore` を直接呼ぶ。
  - 本体の返り: `(f, precision, recall) → F 値`

## 使い方

F-score @ tau = precision と recall の調和平均。→ (f, precision, recall)。再構成の標準指標。

Raises ValueError: どちらかが空 or (N,3) でない場合(accuracy/completeness 経由)。

計算(``a`` = 再構成/推定、``b`` = 参照/GT の慣習):
- ``precision`` = ``a`` の点のうち、``b`` への最近傍距離が ``tau`` **未満**
  (``< tau``、等号は含まない)の割合。
- ``recall`` = ``b`` の点のうち、``a`` への最近傍距離が ``tau`` 未満の割合。
- ``f = 2 p r / (p + r)``、``p + r == 0`` なら ``0.0``(0 除算にしない)。

引数: ``a``, ``b`` は ``(N, 3)`` / ``(M, 3)`` 点群(対応不要、点数は異なってよい)。
``tau`` は距離閾値(座標と同じ単位、正の値を想定。``tau <= 0`` だと距離 0 の点も
``< tau`` にならず precision = recall = 0 になる。検査はしない)。

返り値: ``(f, precision, recall)`` の 3 つの ``float``、それぞれ ``[0, 1]``。
1 が完全一致。

注意: ``tau`` の選び方が結果を決める(voxel サイズ・スキャン分解能の 1〜2 倍が
目安)。片方の雲だけ密だと precision と recall が乖離する — その非対称性を見る
のがこの指標の価値で、1 数字で良ければ ``chamfer_distance``。

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

[chamfer_distance](chamfer_distance.md) · [hausdorff_distance](hausdorff_distance.md) · [rmse_correspondence](rmse_correspondence.md) · [normal_consistency](normal_consistency.md) · [voxel_iou](voxel_iou.md) · [pose_error](pose_error.md)

---
*Provenance: metrics3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
